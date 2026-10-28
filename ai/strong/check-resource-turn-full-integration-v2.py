"""Corrected full-game replays, later-round input checks and two search roots.

Replay only the predetermined 33 original games with the changed model-turn
implementation. Do not repeat unchanged filter controls or infer playing strength.
"""
from collections import Counter
from concurrent.futures import ProcessPoolExecutor,as_completed
import json
from pathlib import Path
import sys
import time

from public_policy_development_job_v1 import read,digest

ROOT=Path(__file__).resolve().parents[2]
ARTIFACT=ROOT/'ai/runs/resource-turn-full-artifact-v2'
OUT=ROOT/'ai/runs/resource-turn-full-integration-v2'
RESULT=ROOT/'ai/strong/resource-turn-full-integration-results-v2.json'
PRIOR=ROOT/'ai/runs/resource-replanning-development-collected-v1'
MANIFEST=ROOT/'ai/runs/resource-replanning-development-complete-evidence-v1/manifest.json'
MANIFEST_SHA='fb4cab7da560d86fe1bad88a363c9e83d3bb0aa86344de12368317dc95ae1839'


def semantic(value):
    if isinstance(value,dict):return {k:semantic(v) for k,v in value.items() if k!='elapsedMs'}
    if isinstance(value,list):return [semantic(v) for v in value]
    return value


def main():
    assert not OUT.exists() and not RESULT.exists(),'Inspect previous integration before retrying'
    sys.path.insert(0,str(ARTIFACT/'policy'))
    from resource_turn_full_policy_v2 import load_artifact,DESCRIPTOR,MODES
    from resource_turn_full_arena_v2 import play,Process,description_checked,action_checked,write
    from resource_turn_full_audit_v2 import audit
    root,spec,hashes=load_artifact(ARTIFACT)
    assert digest(MANIFEST)==MANIFEST_SHA;manifest=read(MANIFEST);inputs={}
    assert digest(root/'policy/resource-model-turn-v2.cjs')==digest(ROOT/'ai/strong/resource-model-turn-v2.cjs')
    def original(path):
        name=str(path.relative_to(ROOT));sha=digest(path);assert manifest[name]==sha;inputs[name]=sha
        return read(path) if path.suffix=='.json' else [json.loads(l) for l in path.read_text().splitlines()]
    work=[];groups={}
    for opponent,counts in [('economic',range(2,7)),('legacy',[2,6])]:
        for n in counts:
            folder=PRIOR/f'resource-replanning-development-v1-filter-{n}p-{opponent}-0-4/artifacts/evaluation'
            evaluation=original(folder/'evaluation.json')
            episodes=[0,1,2,3]+([4*(n-1)] if opponent=='economic' else [])
            name=f'model-turn-{n}p-{opponent}';target=OUT/name
            config={'artifact':str(root),'descriptor_sha256':digest(root/DESCRIPTOR),'output':str(target),
                'mode':'model-turn','players':n,'opponent':opponent,'seed':evaluation['config']['seed']}
            groups[name]={'config':config,'results':[]}
            for episode in episodes:
                reference={'decisions':original(folder/f'decisions-{episode}.jsonl'),
                    'terminal':next(r['terminal'] for r in evaluation['results'] if r['episode']==episode)}
                work.append((name,config,episode,reference))
    assert len(work)==33
    OUT.mkdir();began=time.perf_counter();active=[]
    code={str((ROOT/'ai/strong'/n).relative_to(ROOT)):digest(ROOT/'ai/strong'/n) for n in (
        'check-resource-turn-full-integration-v2.py','check-resource-model-turn-v2.cjs','resource-model-turn-v2.cjs')}
    write(OUT/'design.json',{'purpose':'Corrected model-turn integration and intermediate public-input verification, not strength evaluation',
        'original_games':33,'selection':'All previously selected model-turn games: economic 2–6p all rules at seat zero plus last seat original sealed; legacy 2p/6p all rules seat zero.',
        'artifact_descriptor_sha256':digest(root/DESCRIPTOR),'artifact_manifest_sha256':digest(root/'manifest.json'),
        'input_hashes':inputs,'code_hashes':code,'search_roots':[[2,0],[6,3]],
        'samples_per_input_check':8,'new_hf_jobs':0,'new_full_game_trajectories':0,
        'unchanged_filter_games_repeated':0,'qualification_eligible':False,'reserved_final_seeds_used':False})
    report={'passed':False,'actual_inference_replays':0,'groups_audited':0,
        'public_input_turns':0,'public_input_decisions':0,'private_feature_checks':0,
        'search_mode_checks':0,'new_hf_jobs':0,'new_full_game_trajectories':0,
        'qualification_eligible':False,'reserved_final_seeds_used':False}
    try:
        for group in groups.values():Path(group['config']['output']).mkdir()
        with ProcessPoolExecutor(max_workers=2) as pool:
            futures={pool.submit(play,config,episode,reference):(name,episode) for name,config,episode,reference in work}
            for future in as_completed(futures):
                name,episode=futures[future];record=future.result();groups[name]['results'].append(record)
                write(OUT/name/f'completed-{episode}.json',record)
                report['actual_inference_replays']+=1
                print(json.dumps({'corrected_game_replays':report['actual_inference_replays'],'expected':33}),flush=True)
        totals=Counter()
        for name,group in groups.items():
            group['results'].sort(key=lambda r:r['episode'])
            verified=audit(group['config'],group['results'],require_pairs=False)
            write(OUT/name/'independent-audit.json',verified)
            write(OUT/name/'evaluation.json',{**group,'all_complete':True,'errors':[],
                'expected_games':len(group['results']),'completed_games':len(group['results']),
                'qualification_eligible':False,'reserved_final_seeds_used':False})
            totals.update(verified['counts']);report['groups_audited']+=1
        report['replay_counts']=dict(totals)
        write(OUT/'replay-assessment.json',report)

        # Inspect each intermediate model input against eight complete sampled
        # states. Recorded model choices are replayed; no second inference pass.
        worker=Process(['node',str(ROOT/'ai/strong/check-resource-model-turn-v2.cjs'),str(root/spec['runtime']['directory'])],
            OUT/'private-input-check.stderr.log');active.append(worker)
        steps=Counter();rounds=Counter();by_count=Counter();by_rule=Counter()
        with (OUT/'public-input-checks.jsonl').open('x') as stream:
            for name,group in groups.items():
                for game in group['results']:
                    path=OUT/name/f'decisions-{game["episode"]}.jsonl'
                    assert digest(path)==game['decision_receipt_sha256']
                    for line in path.read_text().splitlines():
                        record=json.loads(line)
                        if record['response']['kind']!='resource-turn':continue
                        q=record['request'];state=q['state'];trace=record['response']['diagnostics']['baselineDecisions']
                        seed=f'public-resource-input-v2-{name}-{game["episode"]}-{state["round"]}'
                        value=worker.call({'op':'reset','request':q,'seed':seed,'samples':8})
                        for chosen in trace:
                            assert not value['done'] and value['moves'][chosen['index']]==chosen['move']
                            assert value['publicMetadata']=={'cardsLeft':state['cardsLeft'],'nextCardWeak':state['nextCardWeak']}
                            value=worker.call({'op':'step','index':chosen['index']})
                        assert value['done'] and value['actions']==record['executedActions']
                        assert value['privateStateFeatureChecks']==len(trace)*8
                        event={'case':name,'episode':game['episode'],'requestId':q['requestId'],
                            'round':state['round'],'step':state['step'],'players':group['config']['players'],
                            'variant':state['options']['variant'],'sealed':state['options']['fastBid'],
                            'decisions':len(trace),'privateFeatureChecks':value['privateStateFeatureChecks'],
                            'publicMetadata':value['publicMetadata'],'seed':seed}
                        stream.write(json.dumps(event)+'\n');stream.flush()
                        report['public_input_turns']+=1;report['public_input_decisions']+=len(trace)
                        report['private_feature_checks']+=value['privateStateFeatureChecks']
                        steps[state['step']]+=1;rounds[state['round']]+=1;by_count[group['config']['players']]+=1
                        by_rule[f'{state["options"]["variant"]}/{"sealed" if state["options"]["fastBid"] else "open"}']+=1
                print(json.dumps({'public_input_turns_checked':report['public_input_turns'],'completed_group':name}),flush=True)
        worker.close();active.remove(worker)
        report['input_coverage']={'steps':dict(steps),'rounds':dict(rounds),'player_counts':dict(by_count),'rules':dict(by_rule)}
        assert set(steps)=={1,2,3} and set(by_count)==set(range(2,7)) and len(by_rule)==4
        write(OUT/'public-input-assessment.json',report)

        roots=[]
        root_files={ROOT/'ai/runs/resource-turn-full-integration-v1/search-roots.jsonl':'0451d6e1189a9c0008386efc13cbcff0d54ab28290a521b19f42fb243b86f227',
            ROOT/'ai/runs/resource-turn-full-integration-recovered-v1/search-roots.jsonl':'61e59190b8084292d757e06febe9a6fa847a183bf6ce1fc80c71bab5ec77b40a'}
        for path,sha in root_files.items():
            assert digest(path)==sha;inputs[str(path.relative_to(ROOT))]=sha
            roots.extend(json.loads(l) for l in path.read_text().splitlines())
        policies={};descriptions={}
        for mode in MODES:
            process=Process([sys.executable,'-u','-B',str(root/'policy/resource_turn_full_policy_v2.py'),
                '--artifact',str(root),'--mode',mode],OUT/f'describe-{mode}.stderr.log');active.append(process)
            desc=process.call({'op':'describe'});description_checked(desc,root,spec,mode);descriptions[mode]=desc
            if mode in ('search-turn','atomic-search-corrected'):policies[mode]=process
            else:process.close();active.remove(process)
        write(OUT/'descriptions.json',descriptions)
        from resource_policy_verification_v1 import verify_plan
        search_counts=Counter()
        with (OUT/'search-checks.jsonl').open('x') as stream:
            for n,episode in ((2,0),(6,3)):
                original_root=next(r for r in roots if (r['players'],r['episode'])==(n,episode));q=original_root['request']
                expected=original_root['recorded_atomic_decision']['resourcePlan']
                outputs={}
                for mode,process in policies.items():
                    value=process.call({'op':'decide','request':q});outputs[mode]=value
                    plan=value['diagnostics']['searchResult'] if mode=='search-turn' else value['decision']['resourcePlan']
                    assert semantic(plan)==semantic(expected),'Changed search root requires independent review'
                    checked=verify_plan(plan,{'players':n,'samples':8,'model_sha256':spec['model']['sha256']},q['player'])
                    search_counts.update(checked);report['search_mode_checks']+=1
                assert outputs['atomic-search-corrected']['move']==outputs['search-turn']['resource']['transaction']['actions'][0]
                stream.write(json.dumps({'players':n,'episode':episode,'request':q,'outputs':outputs})+'\n');stream.flush()
                print(json.dumps({'corrected_search_mode_checks':report['search_mode_checks'],'expected':4}),flush=True)
        for process in active:process.close()
        active=[]
        assert report['actual_inference_replays']==33 and report['groups_audited']==7 and report['search_mode_checks']==4
        assert all(digest(ROOT/name)==sha for name,sha in {**inputs,**code}.items())
        assert all(digest(root/name)==sha for name,sha in hashes.items())
        report.update(passed=True,seconds=time.perf_counter()-began,artifact=str(root),
            descriptor_sha256=digest(root/DESCRIPTOR),manifest_sha256=digest(root/'manifest.json'),
            input_hashes=inputs,code_hashes=code,search_counts=dict(search_counts),
            output_hashes={str(p.relative_to(OUT)):digest(p) for p in OUT.rglob('*') if p.is_file()},
            interpretation='Corrected model turns match 33 existing complete games. Intermediate inputs/menus match eight complete sampled states per decision across all steps; two predetermined search roots reproduce original continuations. No fresh strength games, training, stable-seed policy or final qualification.')
        write(OUT/'assessment.json',report);write(RESULT,{**report,'assessment_sha256':digest(OUT/'assessment.json')})
        print(json.dumps({k:v for k,v in report.items() if k not in ('input_hashes','code_hashes','output_hashes')}),flush=True)
    except BaseException as error:
        for process in active:
            try:process.close()
            except Exception:pass
        write(OUT/'failure.json',{'error':type(error).__name__+': '+str(error),'partial_report':report})
        raise


if __name__=='__main__':main()
