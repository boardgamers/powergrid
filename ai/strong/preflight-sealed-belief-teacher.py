"""Frozen-parent/public-prompt parity and full-game controls before HF pilot."""
import gzip,json,time
from pathlib import Path
from strategic_collection import ROOT,read,write,digest,get_model
from strategic_teacher import evaluate as old_evaluate, predict_batch
from sealed_belief_teacher import evaluate,Node,prepare,REVISION


def terminal(rows):
    return sorted([{k:v for k,v in r.items() if k!='initialBelief'} for r in rows],key=lambda r:r['env'])


def main():
    protocol=read(ROOT/'ai/strong/sealed-belief-pilot-protocol-v1.json');model=get_model(protocol)
    pin=read(ROOT/'ai/strong/strategic-teacher-training-roots-v1.json');path=ROOT/pin['file'];assert digest(path)==pin['sha256']
    with gzip.open(path,'rt') as f:roots=list(map(json.loads,f))
    out=ROOT/'ai/runs/sealed-belief-preflight-v1';out.mkdir(exist_ok=False)
    node=Node('strong/sealed-belief-continuations.cjs');prompts={};root_count=prior_count=0
    try:
        for root in roots:
            if not root['sealed'] or root['decision']!='bid':continue
            q=node.call({'op':'prepare',**root['request'],'featureRevision':REVISION})
            assert q['moves']==root['legal'];x=q['observation']
            assert model.predict(x['state'],x['actions'])[0]==root['model_proposal']
            prompts[root['rootId']]=q['prior'];root_count+=1
            xs=[p['encoded'] for p in q['prior']]
            if xs:
                assert predict_batch(model,xs)==[model.predict(x['state'],x['actions'])[0] for x in xs]
                prior_count+=len(xs)
        assert root_count==320 and prior_count==317
        choices=[]
        for n in [2,6]:
            for variant in ['original','recharged']:
                choices.append(next(r for r in roots if r['players']==n and r['variant']==variant and r['sealed'] and r['decision']=='bid' and prompts[r['rootId']]))
            choices.append(next(r for r in roots if r['players']==n and r['sealed'] and r['decision']=='bid' and not prompts[r['rootId']]))
            choices.append(next(r for r in roots if r['players']==n and not r['sealed'] and r['decision']=='building'))
        results=[];started=time.monotonic()
        with gzip.open(out/'controls.jsonl.gz','wt') as f:
            for root in choices:
                options=prepare(node,model,root);options=list(dict.fromkeys([root['model_proposal'],next(i for i in options if i!=root['model_proposal'])]))
                for mode in ['neural','neural_economic']:
                    old=old_evaluate(model,root,options,mode,'a',2,4)
                    control=evaluate(model,root,options,mode,'a',2,4,belief='uniform_control')
                    policy=evaluate(model,root,options,mode,'a',2,4,belief='policy')
                    for row in [old,control,policy]:assert row['usable'] and len(row['rollouts'])==4
                    assert terminal(old['rollouts'])==terminal(control['rollouts'])
                    for field in ['sample_outcomes','paired_advantages_over_proposal','seed','options','nested_search']:
                        assert old[field]==control[field]
                    affected=bool(prompts.get(root['rootId'],[]))
                    if not affected:
                        assert terminal(old['rollouts'])==terminal(policy['rollouts'])
                        assert old['sample_outcomes']==policy['sample_outcomes']
                    f.write(json.dumps({'root':root['rootId'],'old':old,'control':control,'policy':policy})+'\n');f.flush()
                    results.append({'rootId':root['rootId'],'players':root['players'],'variant':root['variant'],'mode':mode,
                        'affected':affected,'old_control_identical':True,'policy_unchanged_when_unaffected':not affected,
                        'rollouts':12,'policy_seconds':policy['timing']['seconds']})
                    print(results[-1],flush=True)
    finally:node.close()
    report={'passed':True,'model_sha256':model.sha256,'protocol_sha256':digest(ROOT/'ai/strong/sealed-belief-pilot-protocol-v1.json'),
        'root_sha256':pin['sha256'],'public_roots_verified':root_count,'batched_prior_prompts_verified':prior_count,
        'rollouts':sum(r['rollouts'] for r in results),'cases':results,'seconds':time.monotonic()-started,
        'artifacts':{'controls.jsonl.gz':digest(out/'controls.jsonl.gz')},'gradients':False,'qualification_eligible':False}
    write(out/'preflight.json',report);print({'passed':True,'rollouts':report['rollouts']},flush=True)


if __name__=='__main__':main()
