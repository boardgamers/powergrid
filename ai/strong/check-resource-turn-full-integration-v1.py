"""Actual-inference replays of predetermined original games and search roots."""
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
PRIOR=ROOT/'ai/runs/resource-replanning-development-collected-v1'
ARCHIVE_MANIFEST=ROOT/'ai/runs/resource-replanning-development-complete-evidence-v1/manifest.json'
ARCHIVE_SHA='fb4cab7da560d86fe1bad88a363c9e83d3bb0aa86344de12368317dc95ae1839'


def digest(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def semantic(value):
    if isinstance(value,dict):return {k:semantic(v) for k,v in value.items() if k!='elapsedMs'}
    if isinstance(value,list):return [semantic(v) for v in value]
    return value


def arena_semantic(value):
    result=json.loads(json.dumps(value))
    for row in result['observations']:
        if row is None:continue
        for player in row['request']['state']['players']:
            player.pop('clockStartedAt',None);player.pop('totalTimeUsed',None)
            if isinstance(player.get('lastMove'),dict):
                player['lastMove'].pop('time',None);player['lastMove'].pop('serverTime',None)
        for event in row['request']['state'].get('log',[]):
            if isinstance(event.get('move'),dict):
                event['move'].pop('time',None);event['move'].pop('serverTime',None)
    return result


def main(artifact,out):
    sys.path.insert(0,str(artifact/'policy'))
    from resource_turn_full_arena_v1 import play,Process,write,description_checked,action_checked
    from resource_turn_full_audit_v1 import audit
    from resource_turn_full_policy_v1 import load_artifact,DESCRIPTOR
    root,spec,hashes=load_artifact(artifact)
    assert digest(ARCHIVE_MANIFEST)==ARCHIVE_SHA
    manifest=json.loads(ARCHIVE_MANIFEST.read_text());inputs={}
    def recorded(path):
        name=str(path.relative_to(ROOT));sha=digest(path)
        assert sha==manifest[name],name
        inputs[name]=sha
        return json.loads(path.read_text()) if path.suffix=='.json' else [json.loads(l) for l in path.read_text().splitlines()]
    def original(arm,n,opponent):
        folder=PRIOR/f'resource-replanning-development-v1-{arm}-{n}p-{opponent}-0-4/artifacts/evaluation'
        evaluation=recorded(folder/'evaluation.json')
        assert evaluation['all_complete'] and not evaluation['errors']
        assert evaluation['config']['model_sha256']==spec['model']['sha256']
        return folder,evaluation
    out.mkdir(exist_ok=False);began=time.perf_counter()
    report={'passed':False,'original_games':33,'actual_inference_replays':0,'complete_search_turn_checks':0,
        'atomic_search_controls':0,'new_full_game_trajectories':0,'new_hf_jobs':0,'gradients':False,
        'qualification_eligible':False,'reserved_final_seeds_used':False,'cases':[]}
    active=[]
    try:
        work=[];groups={}
        for opponent,counts in [('economic',range(2,7)),('legacy',[2,6])]:
            for n in counts:
                folder,evaluation=original('filter',n,opponent)
                episodes=[0,1,2,3]+([4*(n-1)] if opponent=='economic' else [])
                for mode in ('filter','model-turn'):
                    name=f'{mode}-{n}p-{opponent}';target=out/name;target.mkdir()
                    config={'artifact':str(root),'descriptor_sha256':digest(root/DESCRIPTOR),'output':str(target),
                        'mode':mode,'players':n,'opponent':opponent,'seed':evaluation['config']['seed']}
                    groups[name]={'config':config,'results':[]}
                    for episode in episodes:
                        reference={'decisions':recorded(folder/f'decisions-{episode}.jsonl'),
                            'terminal':next(r['terminal'] for r in evaluation['results'] if r['episode']==episode)}
                        work.append((name,config,episode,reference))
        assert len(work)==66
        with ProcessPoolExecutor(max_workers=2) as pool:
            pending={pool.submit(play,config,episode,reference):(name,episode) for name,config,episode,reference in work}
            for future in as_completed(pending):
                name,episode=pending[future];record=future.result()
                groups[name]['results'].append(record);report['actual_inference_replays']+=1
                print(json.dumps({'original_game_replays':report['actual_inference_replays'],'expected':66}),flush=True)
        totals=Counter()
        for name,group in groups.items():
            group['results'].sort(key=lambda r:r['episode'])
            checked=audit(group['config'],group['results'],require_pairs=False)
            write(out/name/'independent-audit.json',checked)
            write(out/name/'evaluation.json',{**group,'all_complete':True,'errors':[],
                'expected_games':len(group['results']),'completed_games':len(group['results']),
                'qualification_eligible':False,'reserved_final_seeds_used':False})
            totals.update(checked['counts']);report['cases'].append({'name':name,'audit':checked})
        report['replay_counts']=dict(totals)

        # First recorded resource-search request at seat zero in all 20 count/rule
        # cells. These old roots are fixed before examining the chosen plan/outcome.
        policies={};descriptions={}
        for mode in ('search-turn','atomic-search'):
            worker=Process([sys.executable,'-u','-B',str(root/'policy/resource_turn_full_policy_v1.py'),
                '--artifact',str(root),'--mode',mode],out/f'{mode}.stderr.log')
            active.append(worker);policies[mode]=worker
            descriptions[mode]=worker.call({'op':'describe'})
            description_checked(descriptions[mode],root,spec,mode)
        arenas=[]
        for label in ('commit','reference'):
            arena=Process(['node',str(root/'policy/resource-turn-arena-bridge-v1.cjs'),
                str(root/spec['runtime']['directory'])],out/f'search-{label}.stderr.log')
            active.append(arena);arenas.append(arena)
        from resource_policy_verification_v1 import verify_plan
        with (out/'search-roots.jsonl').open('x') as stream:
            for n in range(2,7):
                folder,evaluation=original('resource-filter',n,'economic')
                for episode in range(4):
                    old=recorded(folder/f'decisions-{episode}.jsonl')
                    reset={'op':'reset','n':1,'offset':episode,'arenaSeed':evaluation['config']['seed'],
                        'playerCount':n,'mode':'economic','featureRevisions':{'learner':'4.3-strategic-correction'},
                        'publicMoves':True,'publicResourceTurns':True,
                        'policyIdentity':descriptions['search-turn']['resourceIdentity']}
                    states=[arena.call(reset) for arena in arenas]
                    chosen=False
                    for row in old:
                        assert arena_semantic(states[0])==arena_semantic(states[1])
                        obs=states[0]['observations'][0];q=obs['request']
                        assert obs['moves'][row['index']]==row['move']
                        if row.get('resourcePlan') is not None:
                            chosen=True;outputs={mode:worker.call({'op':'decide','request':q}) for mode,worker in policies.items()}
                            full=outputs['search-turn'];atomic=outputs['atomic-search']
                            action,actions=action_checked(full,q,obs['moves'],descriptions['search-turn'],'search-turn')
                            action_checked(atomic,q,obs['moves'],descriptions['atomic-search'],'atomic-search')
                            assert semantic(atomic['decision'])==semantic({k:v for k,v in row.items() if k not in ('decision','round')})
                            plan=full['diagnostics']['searchResult']
                            assert semantic(plan)==semantic(row['resourcePlan'])
                            verify_plan(plan,{'players':n,'samples':8,'model_sha256':spec['model']['sha256']},q['player'])
                            states[0]=arenas[0].call({'op':'step','actions':[action]})
                            for move in actions:
                                states[1]=arenas[1].call({'op':'step','actions':[{'publicMove':move}]})
                            assert arena_semantic(states[0])==arena_semantic(states[1])
                            stream.write(json.dumps({'players':n,'episode':episode,'request':q,'outputs':outputs,
                                'recorded_atomic_decision':row,'full_turn_equals_atomic_execution':True},allow_nan=False)+'\n');stream.flush()
                            report['complete_search_turn_checks']+=1;report['atomic_search_controls']+=1
                            print(json.dumps({'search_turn_checks':report['complete_search_turn_checks'],'expected':20}),flush=True)
                            break
                        states=[arena.call({'op':'step','actions':[{'publicMove':row['move']}]}) for arena in arenas]
                    assert chosen,'Recorded game lacks a resource-search root'
        for worker in active:worker.close()
        active=[]
        assert report['actual_inference_replays']==66 and report['complete_search_turn_checks']==20
        assert all(digest(root/name)==sha for name,sha in hashes.items())
        report.update(passed=True,seconds=time.perf_counter()-began,artifact=str(root),
            descriptor_sha256=digest(root/DESCRIPTOR),manifest_sha256=digest(root/'manifest.json'),
            original_archive_manifest_sha256=ARCHIVE_SHA,input_hashes=inputs,
            checker_sha256=digest(__file__),
            output_hashes={str(p.relative_to(out)):digest(p) for p in out.rglob('*') if p.is_file()},
            scope='Actual inference reproduces recorded complete games in filter/model-turn controls. Complete search plans and atomic control reproduce first recorded resource-search roots; fresh search-policy full games and causal strength study remain unadmitted.')
        write(out/'assessment.json',report)
        print(json.dumps({k:v for k,v in report.items() if k not in ('cases','input_hashes','output_hashes')}),flush=True)
    except BaseException as error:
        for worker in active:
            try:worker.close()
            except Exception:pass
        write(out/'failure.json',{'error':type(error).__name__+': '+str(error),'partial_report':report})
        raise


if __name__=='__main__':
    main(Path(sys.argv[1]).resolve(),Path(sys.argv[2]).resolve())
