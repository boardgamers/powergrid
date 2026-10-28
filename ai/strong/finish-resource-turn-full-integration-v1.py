"""Finish only the three unrecorded integration checks after the host interruption.

Preserves the 66 completed replay executions, 14 audits, 17 complete search roots
and separate eight-game CLI check. No complete game or HF job is restarted.
"""
from collections import Counter
import importlib.util
import json
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
STRONG=ROOT/'ai/strong'
ORIGINAL=ROOT/'ai/runs/resource-turn-full-integration-v1'
OUT=ROOT/'ai/runs/resource-turn-full-integration-recovered-v1'
CLI=ROOT/'ai/runs/resource-turn-full-cli-v1'
ARTIFACT=ROOT/'ai/runs/resource-turn-full-artifact-v1'
CHECKER_SHA='1674dc9e7670c29b8d4a089783c0f91b30785fc749e548a6b1a0cbaa056aa541'
SEARCH_SHA='0451d6e1189a9c0008386efc13cbcff0d54ab28290a521b19f42fb243b86f227'


def main():
    assert not OUT.exists(),'Inspect previous recovery before retrying'
    for path in Path('/proc').glob('[0-9]*/cmdline'):
        try:
            assert not any(x.endswith(b'check-resource-turn-full-integration-v1.py')
                for x in path.read_bytes().split(b'\x00')), 'Original integration checker is still alive'
        except (FileNotFoundError,PermissionError,ProcessLookupError):pass
    spec=importlib.util.spec_from_file_location('original_integration_checker',STRONG/'check-resource-turn-full-integration-v1.py')
    original=importlib.util.module_from_spec(spec);spec.loader.exec_module(original)
    sha=original.digest;read=lambda p:json.loads(p.read_text())
    assert sha(STRONG/'check-resource-turn-full-integration-v1.py')==CHECKER_SHA
    assert sha(ORIGINAL/'search-roots.jsonl')==SEARCH_SHA
    assert not (ORIGINAL/'assessment.json').exists() and not (ORIGINAL/'failure.json').exists()
    sys.path.insert(0,str(ARTIFACT/'policy'))
    from resource_turn_full_policy_v1 import load_artifact,DESCRIPTOR
    from resource_turn_full_arena_v1 import Process,write,description_checked,action_checked
    root,artifact,hashes=load_artifact(ARTIFACT)
    assert sha(root/DESCRIPTOR)=='8e97c0165eee793dd3be7aefd1849281f36e88ac537c20b5906308f0a8fec723'
    sys.path.insert(0,str(root/'runtime/ai/strong'))
    from resource_policy_verification_v1 import verify_plan
    assert sha(original.ARCHIVE_MANIFEST)==original.ARCHIVE_SHA
    manifest=read(original.ARCHIVE_MANIFEST);inputs={}
    def recorded(path):
        key=str(path.relative_to(ROOT));digest=sha(path);assert manifest[key]==digest
        inputs[key]=digest
        return read(path) if path.suffix=='.json' else [json.loads(x) for x in path.read_text().splitlines()]
    def prior(arm,n,opponent):
        folder=original.PRIOR/f'resource-replanning-development-v1-{arm}-{n}p-{opponent}-0-4/artifacts/evaluation'
        return folder,recorded(folder/'evaluation.json')
    before={str(p.relative_to(ROOT)):sha(p) for p in ORIGINAL.rglob('*') if p.is_file()}
    before.update({str(p.relative_to(ROOT)):sha(p) for p in CLI.rglob('*') if p.is_file()})
    totals=Counter();cases=[];executions=0
    for opponent,counts in [('economic',range(2,7)),('legacy',[2,6])]:
        for n in counts:
            folder,evaluation=prior('filter',n,opponent)
            expected=[0,1,2,3]+([4*(n-1)] if opponent=='economic' else [])
            for mode in ('filter','model-turn'):
                name=f'{mode}-{n}p-{opponent}';case=read(ORIGINAL/name/'evaluation.json');audit=read(ORIGINAL/name/'independent-audit.json')
                assert case['all_complete'] and not case['errors'] and audit['passed']
                assert [r['episode'] for r in case['results']]==expected and audit['games']==len(expected)
                local=Counter()
                for record in case['results']:
                    episode=record['episode'];receipt=ORIGINAL/name/f'decisions-{episode}.jsonl'
                    assert sha(receipt)==record['decision_receipt_sha256'] and record['recorded_reference_checked']
                    rows=[json.loads(x) for x in receipt.read_text().splitlines()]
                    gold=recorded(folder/f'decisions-{episode}.jsonl')
                    assert [a for r in rows for a in r['executedActions']]==[r['move'] for r in gold]
                    assert record['terminal']==next(r['terminal'] for r in evaluation['results'] if r['episode']==episode)
                    local.update(record['counts']);executions+=1
                assert dict(local)==audit['counts'];totals.update(local);cases.append({'name':name,'audit':audit})
    assert executions==66 and len(cases)==14
    cli=read(CLI/'reference-audit.json');assert cli['passed'] and cli['cli_games']==8
    assert cli['evaluation_sha256']==sha(CLI/'evaluation.json') and cli['audit_sha256']==sha(CLI/'independent-audit.json')
    for name,digest in cli['original_input_hashes'].items():assert sha(ROOT/name)==digest==manifest[name];inputs[name]=digest
    old_search=[json.loads(x) for x in (ORIGINAL/'search-roots.jsonl').read_text().splitlines()]
    expected=[(n,e) for n in range(2,7) for e in range(4)]
    assert [(r['players'],r['episode']) for r in old_search]==expected[:17]
    def verify_saved(row):
        n,episode=row['players'],row['episode'];folder,_=prior('resource-filter',n,'economic')
        gold=next(x for x in recorded(folder/f'decisions-{episode}.jsonl') if x.get('resourcePlan') is not None)
        assert row['recorded_atomic_decision']==gold and row['full_turn_equals_atomic_execution']
        full,atomic=row['outputs']['search-turn'],row['outputs']['atomic-search']
        assert original.semantic(atomic['decision'])==original.semantic({k:v for k,v in gold.items() if k not in ('decision','round')})
        plan=full['diagnostics']['searchResult'];assert original.semantic(plan)==original.semantic(gold['resourcePlan'])
        assert full['resource']['transaction']['actions']==plan['actions']
        return verify_plan(plan,{'players':n,'samples':8,'model_sha256':artifact['model']['sha256']},row['request']['player'])
    search_counts=Counter()
    for row in old_search:search_counts.update(verify_saved(row))
    OUT.mkdir();active=[];began=time.perf_counter();new_rows=[]
    write(OUT/'predecessor.json',{'original_checker_sha256':CHECKER_SHA,'original_process_absent':True,
        'original_search_sha256':SEARCH_SHA,'preserved_output_hashes':before,'completed_replays':66,
        'completed_audits':14,'completed_search_checks':17,'completed_cli_games':8,
        'remaining_cases':expected[17:],'interruption_cause':'Not established; host rebooted since original execution.'})
    try:
        policies={};descriptions={}
        for mode in ('search-turn','atomic-search'):
            worker=Process([sys.executable,'-u','-B',str(root/'policy/resource_turn_full_policy_v1.py'),
                '--artifact',str(root),'--mode',mode],OUT/f'{mode}.stderr.log')
            active.append(worker);policies[mode]=worker
            descriptions[mode]=worker.call({'op':'describe'});description_checked(descriptions[mode],root,artifact,mode)
        arenas=[]
        for label in ('commit','reference'):
            arena=Process(['node',str(root/'policy/resource-turn-arena-bridge-v1.cjs'),str(root/'runtime')],OUT/f'{label}.stderr.log')
            active.append(arena);arenas.append(arena)
        with (OUT/'search-roots.jsonl').open('x') as stream:
            for n,episode in expected[17:]:
                folder,evaluation=prior('resource-filter',n,'economic');old=recorded(folder/f'decisions-{episode}.jsonl')
                reset={'op':'reset','n':1,'offset':episode,'arenaSeed':evaluation['config']['seed'],
                    'playerCount':n,'mode':'economic','featureRevisions':{'learner':'4.3-strategic-correction'},
                    'publicMoves':True,'publicResourceTurns':True,'policyIdentity':descriptions['search-turn']['resourceIdentity']}
                states=[a.call(reset) for a in arenas];chosen=False
                for row in old:
                    assert original.arena_semantic(states[0])==original.arena_semantic(states[1])
                    obs=states[0]['observations'][0];q=obs['request'];assert obs['moves'][row['index']]==row['move']
                    if row.get('resourcePlan') is not None:
                        chosen=True;outputs={m:w.call({'op':'decide','request':q}) for m,w in policies.items()}
                        action,actions=action_checked(outputs['search-turn'],q,obs['moves'],descriptions['search-turn'],'search-turn')
                        action_checked(outputs['atomic-search'],q,obs['moves'],descriptions['atomic-search'],'atomic-search')
                        states[0]=arenas[0].call({'op':'step','actions':[action]})
                        for move in actions:states[1]=arenas[1].call({'op':'step','actions':[{'publicMove':move}]})
                        assert original.arena_semantic(states[0])==original.arena_semantic(states[1])
                        result={'players':n,'episode':episode,'request':q,'outputs':outputs,
                            'recorded_atomic_decision':row,'full_turn_equals_atomic_execution':True}
                        search_counts.update(verify_saved(result));new_rows.append(result)
                        stream.write(json.dumps(result,allow_nan=False)+'\n');stream.flush()
                        print(json.dumps({'remaining_cases_completed':len(new_rows),'expected':3}),flush=True)
                        break
                    states=[a.call({'op':'step','actions':[{'publicMove':row['move']}]}) for a in arenas]
                assert chosen
        for worker in active:worker.close()
        active=[]
        assert [(r['players'],r['episode']) for r in old_search+new_rows]==expected
        assert all(sha(ROOT/name)==digest for name,digest in before.items())
        assert all(sha(root/name)==digest for name,digest in hashes.items())
        report={'passed':True,'original_games_in_replay_grid':33,'actual_inference_replays':66,'cli_replays':8,
            'replay_counts':dict(totals),'cli_counts':read(CLI/'independent-audit.json')['counts'],
            'complete_search_turn_checks':20,'atomic_search_controls':20,'search_turn_counts':dict(search_counts),
            'recovery_repeated_completed_checks':0,'recovery_cases':expected[17:],'recovery_seconds':time.perf_counter()-began,
            'artifact':str(root.relative_to(ROOT)),'descriptor_sha256':sha(root/DESCRIPTOR),'manifest_sha256':sha(root/'manifest.json'),
            'checker_sha256':CHECKER_SHA,'finisher_sha256':sha(__file__),'input_hashes':inputs,'preserved_output_hashes':before,
            'recovery_output_hashes':{str(p.relative_to(OUT)):sha(p) for p in OUT.rglob('*') if p.is_file()},
            'cases':cases,'new_full_game_trajectories':0,'new_hf_jobs':0,'gradients':False,
            'qualification_eligible':False,'reserved_final_seeds_used':False,
            'scope':'Pinned full-game execution controls verified on original recorded games and roots. Full-game search-policy runtime admission, stable-sampling causal control and fresh strength games remain pending.'}
        write(OUT/'assessment.json',report)
        print(json.dumps({k:report[k] for k in ('passed','actual_inference_replays','cli_replays','complete_search_turn_checks','search_turn_counts','recovery_seconds')}),flush=True)
    except BaseException as error:
        for worker in active:
            try:worker.close()
            except Exception:pass
        write(OUT/'failure.json',{'error':type(error).__name__+': '+str(error),'remaining_checks_completed':len(new_rows)})
        raise


if __name__=='__main__':main()
