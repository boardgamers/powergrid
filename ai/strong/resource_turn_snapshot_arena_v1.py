"""Separate neural-opponent adapter around the immutable v3 resource policy.

The frozen A260 qualification opponent is a three-player model. This adapter
preserves its own encoder and records every opponent decision for engine replay.
It does not modify the v3 artifact, select a policy, or launch an experiment.
"""
from collections import Counter
import hashlib
import importlib
import json
import math
from pathlib import Path
import sys
import time
from types import SimpleNamespace

DESCRIPTOR_SHA='f41f16f64bf4e9b068e09e15116a6f02c5254ef60c01bd7650a0d7ad356a2e57'
MANIFEST_SHA='91c52c3ba66dde260b8dfedac1e4d227472193f82757a0317fe079c4ccba38cb'
OPPONENT_SHA='9b46db558669a0c3085412fe2544359eda55ed9f092dffb67bead6af3c409ecd'


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def wire(value):return json.dumps(value,separators=(',',':'),allow_nan=False)
def object_hash(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def read(path):return json.loads(Path(path).read_text())
def write(path,value):
    with Path(path).open('x') as stream:json.dump(value,stream,indent=2,allow_nan=False);stream.write('\n')


def context(config):
    root=Path(config['artifact']).resolve();opponent=Path(config['opponent_model']).resolve()
    assert config['players']==3 and config['opponent']=='a260','A260 is the frozen three-player opponent'
    assert config['opponent_sha256']==digest(opponent)==OPPONENT_SHA
    assert digest(root/'resource-full-descriptor.json')==config['descriptor_sha256']==DESCRIPTOR_SHA
    assert digest(root/'manifest.json')==MANIFEST_SHA
    pins=read(root/'manifest.json')
    for name,sha in pins.items():
        path=(root/name).resolve();assert path.is_relative_to(root) and path.is_file() and digest(path)==sha
    assert 'reserved' not in config['seed'].lower() and 'final' not in config['seed'].lower()
    assert config['seed'].startswith(('resource-turn-','resource-replanning-development-v1-'))
    assert config['mode'] in read(root/'resource-full-descriptor.json')['frozen_modes']
    sys.path.insert(0,str(root/'policy'));sys.path.insert(1,str(root/'runtime/ai/strong'))
    arena=importlib.import_module('resource_turn_full_arena_v3')
    audit=importlib.import_module('resource_turn_full_audit_v3')
    runtime=importlib.import_module('hybrid_search')
    for module,relative in ((arena,'policy/resource_turn_full_arena_v3.py'),
            (audit,'policy/resource_turn_full_audit_v3.py'),(runtime,'runtime/ai/strong/hybrid_search.py')):
        assert Path(module.__file__).resolve()==root/relative
    model=runtime.Model(opponent,threads=1);revision=runtime.model_revision(model)
    # This historical checkpoint has no feature metadata; the frozen runtime's
    # contract correctly identifies its original 738/96 encoder as revision 3.0.
    assert revision=='3.0' and model.sha256==OPPONENT_SHA
    return SimpleNamespace(root=root,arena=arena,auditor=audit,model=model,revision=revision)


def roles(episode):return ['learner' if seat==episode//4%3 else 'snapshot0' for seat in range(3)]


def reset(config,episode,description,revision):
    return {'op':'reset','n':1,'offset':episode,'arenaSeed':config['seed'],'playerCount':3,
        'mode':'snapshot0','featureRevisions':{'learner':'4.3-strategic-correction','snapshot0':revision},
        'publicMoves':True,'publicResourceTurns':True,'policyIdentity':description['resourceIdentity']}


def inputs(row):
    # Only encoded/public data; the caller never forwards this opponent record
    # or the arena's role labels to the learner policy process.
    result={key:row[key] for key in ('state','actions','moves','featureRevision','seat','roles')}
    # Revision 3.0 has no explicit playerOrder field. Preserve the actual
    # encoder contract rather than inventing an ordering for an older model.
    if 'playerOrder' in row:result['playerOrder']=row['playerOrder']
    return result


def predict(ctx,row):
    assert row['featureRevision']==ctx.revision and row['roles'][row['seat']]=='snapshot0'
    choice,value=ctx.model.predict(row['state'],row['actions'])
    assert type(choice) is int and 0<=choice<len(row['moves'])==len(row['actions'])
    assert len(value)==3 and all(math.isfinite(x) for x in value)
    return choice


def play(config,episode,reference=None):
    ctx=context(config);out=Path(config['output']);arena=policy=None
    receipt=out/f'decisions-{episode}.jsonl';trace=out/f'snapshot-trace-{episode}.jsonl'
    counts=Counter(policy_requests=0,atomic_moves=0,resource_turns=0,root_filter_overrides=0,
        rollouts=0,rollout_caps=0,neural_decisions=0)
    opponent_decisions=reference_index=0;began=time.perf_counter()
    try:
        policy=ctx.arena.Process([sys.executable,'-u','-B',str(ctx.root/'policy/resource_turn_full_policy_v3.py'),
            '--artifact',str(ctx.root),'--mode',config['mode']],out/f'policy-{episode}.stderr.log')
        description=policy.call({'op':'describe'})
        ctx.arena.description_checked(description,ctx.root,read(ctx.root/'resource-full-descriptor.json'),config['mode'])
        arena=ctx.arena.Process(['node',str(ctx.root/'policy/resource-turn-arena-bridge-v1.cjs'),str(ctx.root/'runtime')],
            out/f'arena-{episode}.stderr.log')
        state=arena.call(reset(config,episode,description,ctx.revision))
        with receipt.open('x') as stream,trace.open('x') as events:
            while not state['ended']:
                row=state['observations'][0];assert row is not None and row['roles']==roles(episode)
                q=row['request'];assert q['requestId']==f'{episode}:{q["revision"]}' and q['player']==row['seat']
                assert q['state']['seed']=='secret' and q['state']['powerPlantsDeck']==[]
                assert not q['state'].get('hiddenLog') and 'powerPlantDeckAfterStep3' not in q['state']
                if q['state']['options']['fastBid']:assert all(p['bid']==0 for p in q['state']['players'])
                if row['roles'][row['seat']]=='learner':
                    value=policy.call({'op':'decide','request':q})
                    action,actions=ctx.arena.action_checked(value,q,row['moves'],description,config['mode'])
                    if reference is not None:
                        gold=reference['decisions'][reference_index:reference_index+len(actions)]
                        assert actions==[d['move'] for d in gold],'Learner replay changed recorded moves'
                        if value['kind']=='atomic':
                            assert {k:v for k,v in value['decision'].items() if k!='elapsedMs'}=={
                                k:v for k,v in gold[0].items() if k not in ('elapsedMs','decision','round')}
                        else:
                            assert value['diagnostics']['baselineDecisions']==[{'index':d['index'],'move':d['move']} for d in gold]
                        reference_index+=len(actions)
                    record={'request':q,'response':value,'arenaMoves':row['moves'],
                        'arenaPlayerOrder':row['playerOrder'],'executedActions':actions}
                    stream.write(wire(record)+'\n');stream.flush()
                    event={'actor':'learner','revision':q['revision'],'decision_sha256':object_hash(record)}
                    counts.update(ctx.arena.response_counts(value,actions))
                else:
                    choice=predict(ctx,row);action={'publicMove':row['moves'][choice]};opponent_decisions+=1
                    event={'actor':'snapshot0','revision':q['revision'],'seat':row['seat'],
                        'input_sha256':object_hash(inputs(row)),'index':choice,'move':row['moves'][choice],
                        'model_sha256':OPPONENT_SHA,'feature_revision':ctx.revision}
                events.write(wire(event)+'\n');events.flush()
                state=arena.call({'op':'step','actions':[action]})
        assert len(state['ended'])==1 and state['observations']==[None]
        terminal=state['ended'][0];seat=episode//4%3
        terminal={**terminal,'seat':seat,'win':terminal['value'][seat]}
        assert terminal['roles']==roles(episode) and not terminal['truncated'] and not terminal['searchStats']
        assert terminal['steps']==counts['atomic_moves']+opponent_decisions and counts['rollout_caps']==0
        if reference is not None:
            assert reference_index==len(reference['decisions']) and terminal==reference['terminal']
        record={'episode':episode,'terminal':terminal,'counts':dict(counts),'description':description,
            'seconds':time.perf_counter()-began,'decision_receipt_sha256':digest(receipt),
            'recorded_reference_checked':reference is not None,'qualification_eligible':False,
            'reserved_final_seeds_used':False,'snapshot':{'opponent_sha256':OPPONENT_SHA,
                'feature_revision':ctx.revision,'decisions':opponent_decisions,'trace_sha256':digest(trace)}}
        write(out/f'game-{episode}.json',record);return record
    except BaseException as error:
        write(out/f'failure-{episode}.json',{'episode':episode,'failure_type':type(error).__name__,
            'partial_counts':dict(counts),'opponent_decisions':opponent_decisions});raise
    finally:
        try:
            if policy is not None:policy.close()
        finally:
            if arena is not None:arena.close()


def audit_snapshot(config,record,output):
    """Replay the entire game independently, checking the opponent's real model.

    Learner actions are replayed without learner inference or search. The pinned
    v3 auditor separately checks those policy receipts and transaction legality.
    """
    ctx=context(config);episode=record['episode'];out=Path(config['output'])
    assert record['snapshot']['opponent_sha256']==config['opponent_sha256']==OPPONENT_SHA
    assert record['snapshot']['feature_revision']==ctx.revision
    trace=out/f'snapshot-trace-{episode}.jsonl';decisions=out/f'decisions-{episode}.jsonl'
    assert digest(trace)==record['snapshot']['trace_sha256']
    assert digest(decisions)==record['decision_receipt_sha256']
    arena=ctx.arena.Process(['node',str(ctx.root/'policy/resource-turn-arena-bridge-v1.cjs'),str(ctx.root/'runtime')],
        Path(output)/f'snapshot-audit-{episode}.stderr.log')
    learner=opponents=0
    try:
        state=arena.call(reset(config,episode,record['description'],ctx.revision))
        with decisions.open() as stream:
            for line in trace.read_text().splitlines():
                event=json.loads(line);assert not state['ended']
                row=state['observations'][0];assert row['roles']==roles(episode)
                q=row['request'];assert q['revision']==event['revision']
                assert event['actor']==row['roles'][row['seat']]
                if event['actor']=='learner':
                    item=json.loads(next(stream));assert object_hash(item)==event['decision_sha256']
                    assert q==item['request'] and row['moves']==item['arenaMoves'] and row['playerOrder']==item['arenaPlayerOrder']
                    action,actions=ctx.arena.action_checked(item['response'],q,row['moves'],record['description'],config['mode'])
                    assert actions==item['executedActions'];learner+=1
                else:
                    assert event['seat']==row['seat'] and event['model_sha256']==OPPONENT_SHA
                    assert event['feature_revision']==row['featureRevision']==ctx.revision
                    assert event['input_sha256']==object_hash(inputs(row))
                    choice=predict(ctx,row)
                    assert event['index']==choice and event['move']==row['moves'][choice]
                    action={'publicMove':event['move']};opponents+=1
                state=arena.call({'op':'step','actions':[action]})
            assert not stream.read(),'Unused learner receipts'
        assert len(state['ended'])==1 and state['observations']==[None]
        actual=state['ended'][0];seat=episode//4%3
        assert {**actual,'seat':seat,'win':actual['value'][seat]}==record['terminal']
        assert learner==record['counts']['policy_requests'] and opponents==record['snapshot']['decisions']
        result={'passed':True,'episode':episode,'learner_requests_replayed':learner,
            'opponent_predictions_verified':opponents,'new_learner_inference':0,'new_search_rollouts':0,
            'terminal_exact':True,'qualification_eligible':False}
        write(Path(output)/f'snapshot-audit-{episode}.json',result);return result
    finally:arena.close()
