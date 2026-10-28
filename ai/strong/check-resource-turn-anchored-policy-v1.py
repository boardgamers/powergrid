"""Actual inference/search integration and lifecycle checks from 20 saved roots.

Execute only the focal resource turn, never a new complete game. Continuations
are actual new searches needed to validate the changed policy, not strength data.
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
ARTIFACT=ROOT/'ai/runs/resource-turn-full-artifact-v3'
OUT=ROOT/'ai/runs/resource-turn-anchored-policy-v1'
RESULT=ROOT/'ai/strong/resource-turn-anchored-policy-results-v1.json'
ROOT_FILES={
    'resource-turn-full-integration-v1':'0451d6e1189a9c0008386efc13cbcff0d54ab28290a521b19f42fb243b86f227',
    'resource-turn-full-integration-recovered-v1':'61e59190b8084292d757e06febe9a6fa847a183bf6ce1fc80c71bab5ec77b40a'}
PASS={'name':'Pass','data':True}


def semantic(value):
    if isinstance(value,dict):return {k:semantic(v) for k,v in value.items() if k!='elapsedMs'}
    if isinstance(value,list):return [semantic(v) for v in value]
    return value


def main():
    assert not OUT.exists() and not RESULT.exists(),'Inspect existing run before retrying'
    sys.path.insert(0,str(ARTIFACT/'policy'))
    from resource_turn_full_policy_v3 import load_artifact,DESCRIPTOR,MODES
    from resource_turn_full_arena_v3 import Process,description_checked,action_checked,write
    root,spec,hashes=load_artifact(ARTIFACT);runtime=root/spec['runtime']['directory']
    sys.path.insert(0,str(runtime/'ai/strong'))
    from resource_turn_anchor_verification_v1 import SamplingAudit,original_plan,verify_plan
    inputs={};roots=[]
    for name,sha in ROOT_FILES.items():
        path=ROOT/'ai/runs'/name/'search-roots.jsonl';assert digest(path)==sha
        inputs[str(path.relative_to(ROOT))]=sha
        roots.extend(json.loads(line) for line in path.read_text().splitlines())
    assert [(r['players'],r['episode']) for r in roots]==[(n,e) for n in range(2,7) for e in range(4)]
    OUT.mkdir();(OUT/'sources').mkdir();code={}
    for name in ('check-resource-turn-anchored-policy-v1.py','check-resource-turn-anchored-policy-v1.cjs'):
        path=ROOT/'ai/strong'/name;code[str(path.relative_to(ROOT))]=digest(path)
        shutil.copy2(path,OUT/'sources'/name)
    write(OUT/'design.json',{'selection':'The same 20 preselected round-one economic-opponent roots, every 2–6 player/rule cell. Execute each new anchored resource policy through Pass. No selection by wins.',
        'artifact_descriptor_sha256':digest(root/DESCRIPTOR),'artifact_manifest_sha256':digest(root/'manifest.json'),
        'root_inputs':inputs,'code_hashes':code,'lifecycle_cases':[[2,0],[6,3]],
        'controls':['Exact first-search historical parity','Independent first-request seed tracking',
            'Public engine purchase replay','Corrupted seed/anchor receipt rejection',
            'Duplicate after other turns','Cold restart at intermediate purchase','Invalid-history service recovery'],
        'new_hf_jobs':0,'new_full_game_trajectories':0,'qualification_eligible':False,'reserved_final_seeds_used':False})
    began=time.perf_counter();active=[];counts=Counter();completed=[];saved=[]
    def service(label,mode='atomic-search-anchored'):
        p=Process([sys.executable,'-u','-B',str(root/'policy/resource_turn_full_policy_v3.py'),
            '--artifact',str(root),'--mode',mode],OUT/(label+'.stderr.log'));active.append(p)
        d=p.call({'op':'describe'});description_checked(d,root,spec,mode)
        return p,d
    def close(p):
        p.close();active.remove(p)
    try:
        descriptions={}
        for mode in MODES:
            p,d=service('describe-'+mode,mode);descriptions[mode]=d
            if mode=='atomic-search-anchored':policy,description=p,d
            else:close(p)
        write(OUT/'descriptions.json',descriptions)
        fixture=Process(['node',str(ROOT/'ai/strong/check-resource-turn-anchored-policy-v1.cjs'),str(runtime)],
            OUT/'fixture.stderr.log');active.append(fixture)
        with (OUT/'decisions.jsonl').open('x') as stream:
            for number,case in enumerate(roots):
                n,episode=case['players'],case['episode'];q=case['request'];audit=SamplingAudit(fixture.call)
                config={'players':n,'samples':8,'model_sha256':spec['model']['sha256'],
                    'arm':'resource-filter','sealed':q['state']['options']['fastBid']}
                maximum=1+sum(q['state'][r+'Market'] for r in ('coal','oil','garbage','uranium'))
                moves=[]
                for step in range(maximum):
                    expected,prepared=audit.expected(q)
                    value=policy.call({'op':'decide','request':q})
                    _,actions=action_checked(value,q,prepared['moves'],description,'atomic-search-anchored')
                    assert actions==[value['move']]
                    decision=value['decision'];plan=decision['resourcePlan']
                    checked=audit.verify(q,decision,config);counts.update(checked)
                    if step==0:
                        assert plan is not None
                        assert semantic(original_plan(plan,expected))==semantic(case['recorded_atomic_decision']['resourcePlan'])
                        counts['first_searches_matching_history']+=1
                        for change in ('seed','currentSeed','purchasesRewound','costRewound'):
                            bad=deepcopy(plan)
                            if change=='seed':bad['search']['seed']='hybrid-public-v1-'+'0'*64
                            elif change=='currentSeed':bad['search']['sampling']['currentSeed']='hybrid-public-v1-'+'0'*64
                            else:bad['search']['sampling']['anchor'][change]+=1
                            try:verify_plan(bad,config,q['player'],expected)
                            except AssertionError:counts['tampered_receipts_rejected']+=1
                            else:raise AssertionError('Tampered sampling receipt was accepted')
                    if step==1 and (n,episode) in ((2,0),(6,3)):
                        assert plan is not None
                        saved.append({'players':n,'episode':episode,'request':deepcopy(q),'response':value,
                            'expected':expected,'config':config})
                    event={'case':number,'players':n,'episode':episode,'purchase_index':step,
                        'request':q,'response':value,'expected_sampling':expected,'counts':checked}
                    stream.write(json.dumps(event,allow_nan=False)+'\n');stream.flush()
                    moves.append(value['move']);counts['atomic_requests']+=1
                    if value['move']==PASS:
                        assert audit.origin is None
                        break
                    q=fixture.call({'op':'purchase','request':q,'move':value['move']})
                assert moves[-1]==PASS
                completed.append({'players':n,'episode':episode,'actions':moves})
                print(json.dumps({'anchored_resource_turns':len(completed),'expected':20,
                    'rollouts':counts['rollouts'],'caps':counts['rollout_caps']}),flush=True)
        assert len(saved)==2
        write(OUT/'lifecycle-inputs.json',saved)
        with (OUT/'lifecycle-results.jsonl').open('x') as stream:
            for case in reversed(saved):
                q=case['request']
                for kind in ('same-process-after-other-turns','cold-process','after-invalid-history'):
                    if kind=='cold-process':
                        close(policy);policy,description=service('restart-'+str(case['players']))
                    if kind=='after-invalid-history':
                        bad=deepcopy(q);bad['state']['log']=[]
                        try:policy.call({'op':'decide','request':bad})
                        except ValueError as error:
                            assert 'Engine worker exited' in str(error);counts['invalid_history_errors']+=1
                        else:raise AssertionError('Malformed history did not fail closed')
                    value=policy.call({'op':'decide','request':q})
                    assert semantic(value)==semantic(case['response']), 'Lifecycle changed the anchored decision'
                    checked=verify_plan(value['decision']['resourcePlan'],case['config'],q['player'],case['expected'])
                    counts.update(checked);counts['lifecycle_replays']+=1
                    stream.write(json.dumps({'players':case['players'],'kind':kind,'response':value,'counts':checked})+'\n');stream.flush()
        for p in list(active):close(p)
        assert len(completed)==20 and counts['first_searches_matching_history']==20
        assert counts['tampered_receipts_rejected']==80 and counts['lifecycle_replays']==6
        assert counts['rollout_caps']==0
        assert all(digest(ROOT/name)==sha for name,sha in {**inputs,**code}.items())
        assert all(digest(root/name)==sha for name,sha in hashes.items())
        report={'passed':True,'resource_turns':len(completed),'counts':dict(counts),'cases':completed,
            'artifact':str(root),'descriptor_sha256':digest(root/DESCRIPTOR),
            'manifest_sha256':digest(root/'manifest.json'),'input_hashes':inputs,'code_hashes':code,
            'seconds':time.perf_counter()-began,
            'output_hashes':{str(p.relative_to(OUT)):digest(p) for p in OUT.rglob('*') if p.is_file()},
            'new_hf_jobs':0,'new_full_game_trajectories':0,'qualification_eligible':False,'reserved_final_seeds_used':False,
            'interpretation':'Stable public-history sampling is integrated into a separately pinned atomic policy. First-search receipts match frozen history, complete focal resource turns are legal and independently seed-audited, and intermediate decisions survive cold restarts, reordered requests and malformed-history service recovery. New search rollouts are engineering checks, not independent strength data. Full-game runtime admission and strength testing remain due.'}
        write(OUT/'assessment.json',report);write(RESULT,{**report,'assessment_sha256':digest(OUT/'assessment.json')})
        print(json.dumps({k:report[k] for k in ('passed','resource_turns','counts','seconds')}),flush=True)
    except BaseException as error:
        for p in list(active):
            try:close(p)
            except Exception:pass
        write(OUT/'failure.json',{'error':type(error).__name__+': '+str(error),'completed_turns':len(completed),'counts':dict(counts)})
        raise


if __name__=='__main__':main()
