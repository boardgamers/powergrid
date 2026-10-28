"""Independently audit whole-turn receipts, counters and terminal credits."""
import argparse
from collections import Counter
import importlib
import json
from pathlib import Path
import sys

from resource_turn_full_policy_v4 import load_artifact
from resource_turn_full_arena_v4 import Process, description_checked, write
from resource_turn_public_policy_v2 import digest


def audit(config, records, *, require_pairs=True):
    root, spec, _ = load_artifact(config['artifact'])
    runtime = root/spec['runtime']['directory']
    sys.path.insert(0,str(runtime/'ai/strong'))
    verifier = importlib.import_module('resource_policy_verification_v1')
    assert Path(verifier.__file__).resolve() == runtime/'ai/strong/resource_policy_verification_v1.py'
    totals = Counter(); out = Path(config['output'])
    exchange = Process(['node',str(root/'policy/resource-turn-exchange-worker-v1.cjs')],out/'audit.stderr.log')
    anchor_process = None
    try:
        if config['mode'] == 'atomic-search-anchored':
            from resource_turn_anchor_verification_v2 import SamplingAudit
            anchor_process = Process(['node',str(runtime/'ai/strong/population-hybrid-policy.cjs')],
                out/'sampling-audit.stderr.log')
        for record in records:
            sampling_audit = SamplingAudit(anchor_process.call) if anchor_process is not None else None
            episode = record['episode']; terminal = record['terminal']; seat = terminal['seat']
            path = out/f'decisions-{episode}.jsonl'
            assert digest(path) == record['decision_receipt_sha256']
            description_checked(record['description'],root,spec,config['mode'])
            counts = Counter(policy_requests=0,atomic_moves=0,resource_turns=0,
                root_filter_overrides=0,rollouts=0,rollout_caps=0,neural_decisions=0)
            moves = Counter(); previous_revision = -1; previous_length = 0
            check = {'players':config['players'],'samples':spec['settings']['samples'],
                     'model_sha256':spec['model']['sha256'],
                     'arm':'resource-filter' if config['mode'] in ('atomic-search','atomic-search-corrected','atomic-search-anchored') else 'filter',
                     'sealed':terminal['sealed']}
            for line in path.read_text().splitlines():
                row = json.loads(line); q = row['request']; value = row['response']
                assert q['player'] == seat and q['requestId'] == f'{episode}:{q["revision"]}'
                assert type(q['revision']) is int and q['revision'] >= previous_revision+previous_length
                assert q['revision'] > previous_revision
                assert q['state']['seed'] == 'secret' and q['state']['powerPlantsDeck'] == []
                assert not q['state'].get('hiddenLog') and 'powerPlantDeckAfterStep3' not in q['state']
                if terminal['sealed']:
                    assert all(p['bid']==0 for p in q['state']['players'])
                assert all(value[k]==q[k] for k in ('requestId','revision'))
                assert value['identity']==record['description']['identity'] and value['qualification_eligible'] is False
                whole = q['state']['phase']=='Resources' and config['mode'] in ('model-turn','search-turn')
                assert value['kind']==('resource-turn' if whole else 'atomic')
                if whole:
                    response = value['resource']; actions = response['transaction']['actions']
                    assert response['identity']==record['description']['resourceIdentity']
                    expected = exchange.call({'op':'respond','runtime':str(runtime),'request':q,
                        'actions':actions,'identity':record['description']['resourceIdentity']})
                    assert response == expected, 'Resource cost, legality, final Pass or binding mismatch'
                    detail = value['diagnostics']; plan = detail['searchResult']
                    assert detail['specification']==record['description']['specification']['resourcePolicy']
                    assert (plan is None)==(config['mode']=='model-turn')
                    if plan is None:
                        assert actions==[d['move'] for d in detail['baselineDecisions']]
                    else:
                        result = verifier.verify_plan(plan,check,seat)
                        assert actions==plan['actions'] and detail['baselineDecisions']==plan['baselineDecisions']
                        counts.update(result)
                    counts['resource_turns']+=1
                else:
                    decision = value['decision']; actions=[value['move']]
                    matches=[i for i,m in enumerate(row['arenaMoves']) if m==value['move']]
                    assert matches==[decision['index']] and decision['move']==value['move']
                    checked=(sampling_audit.verify(q,decision,check) if sampling_audit is not None
                        else verifier.verify_decision(decision,check,seat))
                    for key in ('root_filter_overrides','rollouts','rollout_caps','neural_decisions'):
                        counts[key]+=checked[key]
                assert actions==row['executedActions']
                counts['policy_requests']+=1; counts['atomic_moves']+=len(actions)
                moves.update(m['name'] for m in actions)
                previous_revision, previous_length=q['revision'],len(actions)
            if sampling_audit is not None:assert sampling_audit.origin is None
            assert dict(counts)==record['counts'] and counts['rollout_caps']==0
            assert dict(moves)==terminal['policyMoves']
            assert terminal['episode']==episode and terminal['playerCount']==config['players']
            assert terminal['gameSeed']==config['seed']+'-'+str(episode//(4*config['players']))
            assert seat==episode//4%config['players'] and terminal['roles'][seat]=='learner'
            assert terminal['variant']==('recharged' if episode%2 else 'original')
            assert terminal['sealed']==(episode%4<2) and not terminal['truncated']
            scores=[]
            for player in terminal['final']['players']:
                assert all(type(player[k]) is int and player[k]>=0 for k in ('powered','money','cities','capacity'))
                assert player['powered']<=min(player['cities'],player['capacity'])
                scores.append(tuple(player[k] for k in ('powered','money','cities')))
            best=max(scores); credits=[1/scores.count(best) if score==best else 0 for score in scores]
            assert terminal['value']==credits and terminal['win']==credits[seat]
            assert all(s['truncated']==0 for s in terminal['searchStats'].values())
            assert record['qualification_eligible'] is False and record['reserved_final_seeds_used'] is False
            totals.update(counts)
        if require_pairs:
            from arena_statistics import validate_pairs
            validate_pairs([r['terminal'] for r in records],config['players'])
        else:
            assert all(r['recorded_reference_checked'] for r in records), 'Unpaired checks require original recorded references'
    finally:
        try:exchange.close()
        finally:
            if anchor_process is not None:anchor_process.close()
    return {'passed':True,'games':len(records),'counts':dict(totals),
        'paired_schedule_checked':require_pairs,'new_inference':0,'new_hf_jobs':0,
        'qualification_eligible':False,'reserved_final_seeds_used':False}


if __name__=='__main__':
    parser=argparse.ArgumentParser(__doc__)
    parser.add_argument('evaluation',type=Path)
    args=parser.parse_args(); report=json.loads(args.evaluation.read_text())
    assert report['all_complete'] and not report['errors']
    assert report['completed_games']==report['expected_games']==len(report['results'])
    result=audit(report['config'],report['results'])
    write(args.evaluation.parent/'independent-audit.json',result)
    print(json.dumps(result),flush=True)
