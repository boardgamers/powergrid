"""Bounded residual PPO pilot. No replay files; all nonterminal failures are fatal."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import time
import torch
from data import ROOT, atomic_json, digest, generator_digest
from residual import PROTOCOL, batch, warm_start, save, load
from rollout import collect, plans, summary


# Keep the frozen recipe independent of mutable caller/global dictionaries.
_FROZEN_PROTOCOL=json.loads((Path(__file__).parent/'ppo-protocol-v1.json').read_text())


def make_protocol(replica=0):
    """Copy v1 unchanged except for independent replica RNG and deal namespaces."""
    if type(replica) is not int or not 0<=replica<=99:
        raise ValueError('Replica must be an integer from 0 to 99')
    protocol=copy.deepcopy(_FROZEN_PROTOCOL)
    if replica:
        protocol['seed']+=replica
        protocol['seedNamespace']+=f':replica-{replica}'
    return protocol


def optimize(model,optimizer,rows,update,protocol=PROTOCOL):
    torch.set_num_threads(4)
    model.train()
    weights=torch.tensor([r['weight'] for r in rows]);weights/=weights.mean()
    returns=torch.tensor([r['return'] for r in rows])
    advantages=returns-torch.tensor([r['oldValue'] for r in rows])
    center=(weights*advantages).mean()
    scale=(weights*(advantages-center).square()).mean().sqrt().clamp_min(1e-6)
    advantages=(advantages-center)/scale
    generator=torch.Generator().manual_seed(protocol['seed']+update*1009)
    stats=[];stopped=False
    for epoch in range(protocol['epochsPerUpdate']):
        order=torch.randperm(len(rows),generator=generator)
        for indices in order.split(protocol['batchSize']):
            selected=[rows[int(i)] for i in indices]
            b=batch(selected);logits,values=model(b)
            logps=logits.log_softmax(-1);prob=logps.exp()
            action=torch.tensor([r['chosen'] for r in selected])
            chosen=logps.gather(1,action[:,None]).squeeze(1)
            old=torch.tensor([r['oldLog'] for r in selected])
            delta=chosen-old;ratio=delta.exp();w=weights[indices];adv=advantages[indices]
            approximate_kl=(w*((ratio-1)-delta)).mean()
            if float(approximate_kl.detach())>protocol['targetKl']:
                stopped=True;break
            actor=-(w*torch.minimum(ratio*adv,ratio.clamp(1-protocol['clip'],1+protocol['clip'])*adv)).mean()
            value=(w*(values-returns[indices]).square()).mean()
            entropy=-(w*(prob*logps).sum(-1)).mean()
            prior_log=b['prior'].log_softmax(-1)
            prior_kl=(w*(prob*(logps-prior_log)).sum(-1)).mean()
            loss=actor+protocol['valueCoefficient']*value-protocol['entropyCoefficient']*entropy+protocol['priorKlCoefficient']*prior_kl
            if not torch.isfinite(loss):raise FloatingPointError('Nonfinite PPO objective')
            optimizer.zero_grad(set_to_none=True);loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(),protocol['maxGradNorm'],error_if_nonfinite=True)
            optimizer.step()
            stats.append(dict(loss=float(loss.detach()),actor=float(actor.detach()),value=float(value.detach()),entropy=float(entropy.detach()),
                              priorKl=float(prior_kl.detach()),approxKl=float(approximate_kl.detach())))
        if stopped:break
    if not stats:raise RuntimeError('PPO made no optimizer steps')
    return dict(rows=len(rows),optimizerSteps=len(stats),earlyStopped=stopped,
                **{k:sum(s[k] for s in stats)/len(stats) for k in stats[0]})


def eligible(candidate,baseline,protocol=PROTOCOL):
    return candidate['failures']==0 and all(candidate['maps'][m]>=baseline['maps'][m]-protocol['selectionMaxMapRegression'] for m in baseline['maps'])


def config(smoke,protocol=PROTOCOL):
    names=['data.py','model.py','features.cjs','teacher.cjs','game.cjs','game_rl.cjs','residual.py','rollout.py','ppo.py','ppo-protocol-v1.json','requirements-cpu.txt']
    return dict(protocol=protocol,smoke=smoke,generatorDigest=generator_digest(),
                sourceFiles={name:digest(Path(__file__).parent/name) for name in names})


def run(checkpoint,output,smoke=False,stop_after=None,callback=None,*,replica=0):
    protocol=make_protocol(replica)
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    identity=config(smoke,protocol)
    identity_path=output/'config.json'
    if identity_path.exists() and json.loads(identity_path.read_text())!=identity:
        raise RuntimeError('Existing run config/source mismatch')
    atomic_json(identity_path,identity)
    workers=2 if smoke else protocol['workers']
    updates=2 if smoke else protocol['updates']
    every=1 if smoke else protocol['selectionEvery']
    selection_plan=plans('selection',protocol=protocol)
    if smoke:
        selection_plan=[s for s in selection_plan if s['players']==2 and s['variant']=='original' and not s['fastBid']]
        selection_plan=[dict(s,seed=s['seed'].replace(':selection:',':smoke-selection:')) for s in selection_plan]
    atomic_json(output/'selection-plan.json',selection_plan)
    torch.manual_seed(protocol['seed'])
    model=warm_start(checkpoint)
    optimizer=torch.optim.AdamW(model.parameters(),lr=protocol['learningRate'],weight_decay=protocol['weightDecay'])
    history=[];best_update=0;first=1
    if (output/'last.pt').exists():
        model,saved=load(output/'last.pt')
        assert saved['config']==identity
        optimizer=torch.optim.AdamW(model.parameters(),lr=protocol['learningRate'],weight_decay=protocol['weightDecay'])
        optimizer.load_state_dict(saved['optimizer'])
        torch.set_rng_state(saved['torchRng'])
        first=saved['update']+1;history=saved['history'];best_update=saved['bestUpdate']
        baseline=saved['baseline'];best_score=saved['bestScore']
        # last.pt is the transaction commit. A newer best.pt may have been
        # written just before an interruption, so restore the committed bytes.
        best_artifact=saved['bestArtifact']
        assert hashlib.sha256(best_artifact).hexdigest()==saved['bestSha256']
        if not (output/'best.pt').exists() or digest(output/'best.pt')!=saved['bestSha256']:
            temp=output/'best.tmp';temp.write_bytes(best_artifact);temp.replace(output/'best.pt')
    else:
        _,initial=collect(model,selection_plan,workers,seed=protocol['seed'],protocol=protocol)
        _,teacher=collect(model,[dict(s,focalTeacher=True) for s in selection_plan],workers,seed=protocol['seed'],protocol=protocol)
        # Verify zero-residual full-game parity, not just a matching aggregate score.
        key=lambda r:(r['spec']['seed'],r['spec']['focalSeat'])
        reference={key(r):r for r in teacher}
        for r in initial:
            assert all(r[k]==reference[key(r)][k] for k in ('credit','steps','rounds','terminal')),'Initial teacher parity failed'
        baseline=summary(initial);best_score=baseline['macroCredit']
        atomic_json(output/'selection-0.json',dict(summary=baseline,games=initial))
        save(output/'initial.pt',model,update=0,config=identity)
        save(output/'best.pt',model,update=0,config=identity)
    def checkpoint_last(update):
        save(output/'last.pt',model,optimizer=optimizer.state_dict(),torchRng=torch.get_rng_state(),update=update,
             config=identity,history=history,bestUpdate=best_update,bestScore=best_score,baseline=baseline,
             bestSha256=digest(output/'best.pt'),bestArtifact=(output/'best.pt').read_bytes())
        atomic_json(output/'history.json',history)
        if callback:callback(f'update-{update}')
    if first==1:checkpoint_last(0)
    for update in range(first,updates+1):
        if stop_after is not None and update>stop_after:return None
        began=time.monotonic()
        train_plan=plans('train',update,protocol=protocol)
        if smoke:train_plan=[dict(s,seed=s['seed'].replace(':train:',':smoke-train:')) for s in train_plan[::20]]
        rows,outcomes=collect(model,train_plan,workers,training=True,seed=protocol['seed']+update*7919,protocol=protocol)
        metrics=optimize(model,optimizer,rows,update,protocol=protocol)
        del rows  # The only trajectory window; never serialized to disk.
        record=dict(update=update,training=summary(outcomes),optimization=metrics)
        atomic_json(output/f'train-{update}.json',dict(games=outcomes))
        if update%every==0 or update==updates:
            _,games=collect(model,selection_plan,workers,seed=protocol['seed'],protocol=protocol)
            selected=summary(games)
            atomic_json(output/f'selection-{update}.json',dict(summary=selected,games=games))
            record['selection']=selected
            if eligible(selected,baseline,protocol=protocol) and selected['macroCredit']>best_score+1e-12:
                best_score=selected['macroCredit'];best_update=update
                save(output/'best.pt',model,update=update,config=identity)
        record['seconds']=time.monotonic()-began
        history.append(record);checkpoint_last(update)
        print(json.dumps(dict(stage='ppo',update=update,trainCredit=record['training']['macroCredit'],rows=metrics['rows'],bestUpdate=best_update,seconds=record['seconds'])),flush=True)
    if stop_after is not None:return None
    # Selection is finished before any confirmation/transfer outcomes are consumed.
    model,saved=load(output/'best.pt')
    confirm=plans('confirmation',protocol=protocol)
    if smoke:confirm=[dict(s,seed=s['seed'].replace(':confirmation:',':smoke-confirmation:')) for s in confirm if s['map'] in protocol['trainMaps'] and s['players']==2 and s['variant']=='original' and not s['fastBid'] and s['deal']==0]
    atomic_json(output/'confirmation-plan.json',confirm)
    confirmation={}
    for label,policy in (('selected',False),('teacher',True)):
        tasks=[dict(s,focalTeacher=True) for s in confirm] if policy else confirm
        _,games=collect(model,tasks,workers,seed=protocol['seed'],protocol=protocol)
        confirmation[label]=summary(games)
        atomic_json(output/f'confirmation-{label}.json',dict(summary=confirmation[label],games=games))
        if callback:callback(f'confirmation-{label}')
    result=dict(selectedUpdate=best_update,selectionScore=best_score,baselineSelectionScore=baseline['macroCredit'],
                confirmation=confirmation,qualified=False,trainedUpdates=updates,
                note='Exploratory pilot, fixed heuristic opponents and small heldout deal count. Not final qualification; zero residual is an eligible fallback.')
    atomic_json(output/'result.json',result)
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--checkpoint',required=True);p.add_argument('--output',required=True);p.add_argument('--smoke',action='store_true')
    p.add_argument('--replica',type=int,default=0)
    a=p.parse_args();print(json.dumps(run(a.checkpoint,a.output,a.smoke,replica=a.replica),indent=2))
