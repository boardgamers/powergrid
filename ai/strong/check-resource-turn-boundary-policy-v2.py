"""Exercise the corrected pinned policy with actual inference and continuations.

Twenty predetermined old roots check exact search parity. Four observed
false-commit phase entries run through the complete focal resource turn.
No new complete games, jobs, training, strength selection or final seeds.
"""
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
import shutil
import sys
import time

from public_policy_development_job_v1 import read,digest

ROOT=Path(__file__).resolve().parents[2]
ARTIFACT=ROOT/'ai/runs/resource-turn-full-artifact-v4'
OUT=ROOT/'ai/runs/resource-turn-boundary-policy-v2'
RESULT=ROOT/'ai/strong/resource-turn-boundary-policy-results-v2.json'
PASS={'name':'Pass','data':True}
ROOT_FILES={
    'resource-turn-full-integration-v1':'0451d6e1189a9c0008386efc13cbcff0d54ab28290a521b19f42fb243b86f227',
    'resource-turn-full-integration-recovered-v1':'61e59190b8084292d757e06febe9a6fa847a183bf6ce1fc80c71bab5ec77b40a'}


def semantic(value):
    if isinstance(value,dict):return {k:semantic(v) for k,v in value.items() if k!='elapsedMs'}
    if isinstance(value,list):return [semantic(v) for v in value]
    return value


def main():
    assert not OUT.exists() and not RESULT.exists(),'Inspect prior outcome before retry'
    sys.path.insert(0,str(ARTIFACT/'policy'))
    from resource_turn_full_policy_v4 import load_artifact,DESCRIPTOR,MODES
    from resource_turn_full_arena_v4 import Process,description_checked,action_checked,write
    root,spec,hashes=load_artifact(ARTIFACT);runtime=root/spec['runtime']['directory']
    sys.path.insert(0,str(runtime/'ai/strong'))
    from resource_turn_anchor_verification_v2 import SamplingAudit,original_plan,verify_plan
    inputs={};controls=[]
    def checked(path,sha):
        assert digest(path)==sha;inputs[str(path.relative_to(ROOT))]=sha
        return [json.loads(line) for line in path.read_text().splitlines()]
    for name,sha in ROOT_FILES.items():controls.extend(checked(ROOT/'ai/runs'/name/'search-roots.jsonl',sha))
    assert [(r['players'],r['episode']) for r in controls]==[(n,e) for n in range(2,7) for e in range(4)]
    mechanism=read(ROOT/'ai/strong/resource-turn-boundary-results-v2.json')
    assert mechanism['passed'] and mechanism['counts']['old_boundary_rejections']==4
    exceptional=[]
    selections=[('whole-2p',3,'3:350'),('corrected-2p',2,'2:332'),('corrected-2p',2,'2:365')]
    for family,episode,request_id in selections:
        path=ROOT/'ai/runs/resource-turn-runtime-hf-v1'/('pg-resource-turn-runtime-v1-'+family)/'artifacts/evaluation'/f'decisions-{episode}.jsonl'
        rows=checked(path,mechanism['input_hashes'][str(path.relative_to(ROOT))])
        row=next(r for r in rows if r['request']['requestId']==request_id)
        plan=(row['response']['diagnostics']['searchResult'] if family=='whole-2p'
              else row['response']['decision']['resourcePlan'])
        exceptional.append({'label':family+'-'+request_id,'request':row['request'],'original_plan':plan})
    failed=ROOT/'ai/runs/resource-turn-boundary-failure-v1/failed-request.json'
    assert digest(failed)=='966cd4a7e99b90cc4fade18a322fed1adaf95f938ca1f08ed1da0b9fda926cdf'
    inputs[str(failed.relative_to(ROOT))]=digest(failed)
    exceptional.append({'label':'original-failed-entry','request':read(failed),'original_plan':None})
    for case in exceptional:
        assert case['request']['state']['phase']=='Resources' and case['request']['state']['newTurn'] is False
    prefix=ROOT/'ai/runs/resource-turn-runtime-hf-v1/pg-resource-turn-runtime-v1-anchored-2p/artifacts/evaluation/decisions-7.jsonl'
    rows=checked(prefix,'a25de80c6585d70bfd7fa4cca963af1419655b56d92000c86321c9f1f859ffc1')
    other_phases=[r for r in rows if r['request']['state']['phase']!='Resources']
    OUT.mkdir();(OUT/'sources').mkdir();code={}
    for name in ('check-resource-turn-boundary-policy-v2.py','check-resource-turn-anchored-policy-v1.cjs'):
        path=ROOT/'ai/strong'/name;code[str(path.relative_to(ROOT))]=digest(path);shutil.copy2(path,OUT/'sources'/name)
    write(OUT/'design.json',{'selection':'All 20 predetermined early roots, all four real false-commit entries found in the boundary audit, and every recorded non-resource decision in the failed episode prefix.',
        'artifact_descriptor_sha256':digest(root/DESCRIPTOR),'artifact_manifest_sha256':digest(root/'manifest.json'),
        'input_hashes':inputs,'code_hashes':code,'normal_roots':20,'exceptional_turns':4,
        'non_resource_decisions':len(other_phases),'new_hf_jobs':0,'new_full_game_trajectories':0,
        'qualification_eligible':False,'reserved_final_seeds_used':False})
    active=[];counts=Counter();began=time.perf_counter();completed=[];saved=[]
    def service(label,mode='atomic-search-anchored'):
        p=Process([sys.executable,'-u','-B',str(root/'policy/resource_turn_full_policy_v4.py'),
            '--artifact',str(root),'--mode',mode],OUT/(label+'.stderr.log'));active.append(p)
        d=p.call({'op':'describe'});description_checked(d,root,spec,mode);return p,d
    def close(p):p.close();active.remove(p)
    try:
        descriptions={}
        for mode in MODES:
            p,d=service('describe-'+mode,mode);descriptions[mode]=d
            if mode=='atomic-search-anchored':policy,description=p,d
            else:close(p)
        write(OUT/'descriptions.json',descriptions)
        fixture=Process(['node',str(ROOT/'ai/strong/check-resource-turn-anchored-policy-v1.cjs'),str(runtime)],
            OUT/'fixture.stderr.log');active.append(fixture)
        def config(q):return {'players':len(q['state']['players']),'samples':8,
            'model_sha256':spec['model']['sha256'],'arm':'resource-filter','sealed':q['state']['options']['fastBid']}
        with (OUT/'decisions.jsonl').open('x') as stream:
            def decide(q,audit,label):
                expected,prepared=audit.expected(q)
                value=policy.call({'op':'decide','request':q})
                _,actions=action_checked(value,q,prepared['moves'],description,'atomic-search-anchored')
                assert actions==[value['move']]
                checked_counts=audit.verify(q,value['decision'],config(q));counts.update(checked_counts)
                counts['actual_policy_requests']+=1
                stream.write(json.dumps({'label':label,'request':q,'response':value,
                    'expected_sampling':expected,'counts':checked_counts})+'\n');stream.flush()
                return value,expected
            for case in controls:
                q=case['request'];audit=SamplingAudit(fixture.call)
                value,expected=decide(q,audit,f"normal-{case['players']}p-{case['episode']}")
                assert semantic(original_plan(value['decision']['resourcePlan'],expected))==semantic(case['recorded_atomic_decision']['resourcePlan'])
                counts['normal_first_searches_exact']+=1
                print(json.dumps({'normal_first_searches_exact':counts['normal_first_searches_exact'],'rollouts':counts['rollouts']}),flush=True)
            for case in exceptional:
                q=deepcopy(case['request']);audit=SamplingAudit(fixture.call);actions=[]
                bound=1+sum(q['state'][r+'Market'] for r in ('coal','oil','garbage','uranium'))
                for step in range(bound):
                    value,expected=decide(q,audit,case['label']+f'-purchase-{step}')
                    plan=value['decision']['resourcePlan']
                    if step==0:
                        assert plan is not None and expected['sampling']['anchor']['boundaryCommitted'] is False
                        if case['original_plan'] is not None:
                            assert semantic(original_plan(plan,expected))==semantic(case['original_plan'])
                            counts['exceptional_first_searches_exact']+=1
                        for key in ('seed','currentSeed','boundaryCommitted','purchasesRewound','costRewound'):
                            bad=deepcopy(plan)
                            if key=='seed':bad['search']['seed']='hybrid-public-v1-'+'0'*64
                            elif key=='currentSeed':bad['search']['sampling']['currentSeed']='hybrid-public-v1-'+'0'*64
                            elif key=='boundaryCommitted':bad['search']['sampling']['anchor'][key]=True
                            else:bad['search']['sampling']['anchor'][key]+=1
                            try:verify_plan(bad,config(q),q['player'],expected)
                            except AssertionError:counts['tampered_receipts_rejected']+=1
                            else:raise AssertionError('Tampered corrected sampling receipt accepted')
                    if step==1 and plan is not None:
                        saved.append({'label':case['label'],'request':deepcopy(q),'response':value,'expected':expected})
                    actions.append(value['move'])
                    if value['move']==PASS:
                        assert audit.origin is None;break
                    q=fixture.call({'op':'purchase','request':q,'move':value['move']})
                assert actions[-1]==PASS
                completed.append({'label':case['label'],'actions':actions})
                print(json.dumps({'exceptional_turns':len(completed),'rollouts':counts['rollouts'],'caps':counts['rollout_caps']}),flush=True)
            for row in other_phases:
                q=row['request'];value=policy.call({'op':'decide','request':q})
                action_checked(value,q,row['arenaMoves'],description,'atomic-search-anchored')
                assert semantic(value['decision'])==semantic(row['response']['decision'])
                counts['non_resource_decisions_exact']+=1
                stream.write(json.dumps({'label':'non-resource-parity','request':q,'response':value})+'\n');stream.flush()
        # A real selected intermediate request after a false-commit entry must
        # survive stale ordering, cold restart and an intentionally invalid call.
        assert saved,'No selected intermediate purchase; inspect before adding a synthetic lifecycle case'
        case=saved[-1];write(OUT/'lifecycle-input.json',case);q=case['request']
        with (OUT/'lifecycle-results.jsonl').open('x') as stream:
            for kind in ('after-other-turns','cold-restart','after-invalid-history'):
                if kind=='cold-restart':close(policy);policy,description=service('cold-restart')
                if kind=='after-invalid-history':
                    bad=deepcopy(q);bad['state']['log']=[]
                    try:policy.call({'op':'decide','request':bad})
                    except ValueError as error:
                        assert 'Engine worker exited' in str(error);counts['invalid_history_errors']+=1
                    else:raise AssertionError('Invalid history accepted')
                value=policy.call({'op':'decide','request':q})
                assert semantic(value)==semantic(case['response'])
                counts.update(verify_plan(value['decision']['resourcePlan'],config(q),q['player'],case['expected']))
                counts['lifecycle_replays']+=1
                stream.write(json.dumps({'kind':kind,'response':value})+'\n');stream.flush()
        for p in list(active):close(p)
        assert counts['normal_first_searches_exact']==20 and counts['exceptional_first_searches_exact']==3
        assert len(completed)==4 and counts['tampered_receipts_rejected']==20
        assert counts['lifecycle_replays']==3 and counts['invalid_history_errors']==1 and counts['rollout_caps']==0
        assert all(digest(ROOT/name)==sha for name,sha in {**inputs,**code}.items())
        assert all(digest(root/name)==sha for name,sha in hashes.items())
        report={'passed':True,'exceptional_resource_turns':4,'counts':dict(counts),'cases':completed,
            'artifact':str(root),'descriptor_sha256':digest(root/DESCRIPTOR),'manifest_sha256':digest(root/'manifest.json'),
            'input_hashes':inputs,'code_hashes':code,'seconds':time.perf_counter()-began,
            'output_hashes':{str(p.relative_to(OUT)):digest(p) for p in OUT.rglob('*') if p.is_file()},
            'new_hf_jobs':0,'new_full_game_trajectories':0,'new_gradients':0,
            'qualification_eligible':False,'reserved_final_seeds_used':False,
            'interpretation':'Corrected v4 policy executes actual search through all four observed false-commit resource turns with independent receipts, historical first-search parity and service recovery. No fresh complete game, runtime admission or strength improvement is established.'}
        write(OUT/'assessment.json',report);write(RESULT,{**report,'assessment_sha256':digest(OUT/'assessment.json')})
        print(json.dumps({k:report[k] for k in ('passed','exceptional_resource_turns','counts','seconds')}),flush=True)
    except BaseException as error:
        for p in list(active):
            try:close(p)
            except Exception:pass
        write(OUT/'failure.json',{'error':type(error).__name__+': '+str(error),'completed_turns':len(completed),'counts':dict(counts)})
        raise


if __name__=='__main__':main()
