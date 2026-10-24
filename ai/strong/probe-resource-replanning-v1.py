"""Verify actual atomic resource replanning and unchanged outside-phase decisions."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[2];BASE=ROOT/'ai/runs/resource-replanning-v1'
def read(p):return json.loads(p.read_text())
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,d):p.write_text(json.dumps(d,indent=2,allow_nan=False)+'\n')
def semantic(d):
    if isinstance(d,dict):return {str(k):semantic(v) for k,v in d.items() if k!='elapsedMs'}
    if isinstance(d,list):return [semantic(v) for v in d]
    return d


def main():
    prep=read(BASE/'preparation.json');runtime=BASE/'runtime'
    for name,sha in {**prep['runtime_hashes'],**prep['new_files']}.items():assert digest(runtime/name)==sha
    for name,sha in read(ROOT/'ai/strong/population-hybrid-development-plan-v1.json')['dependency_hashes'].items():assert digest(ROOT/name)==sha
    sys.path.insert(0,str(runtime/'ai/strong'))
    from resource_replanning_policy_v1 import ResourceReplanningPolicy
    from population_hybrid_policy import PopulationPolicy
    from hybrid_search import Model,Node
    model_path=ROOT/'ai/runs/policy-iteration-trained-8840u-prepared-v2/local-package-frozen-1/policy.onnx'
    model=Model(model_path);assert model.sha256=='55331f43379e8fe89025d93b1a7a48c88e0ea39b4ebd3a7ef8240d4b62753530'
    worker=runtime/'ai/strong/population-hybrid-policy.cjs'
    policy=ResourceReplanningPolicy(model,worker,arm='resource-filter',samples=4)
    reference=PopulationPolicy(model,worker,arm='filter',samples=4)
    engine=Node(str(runtime/'ai/strong/resource-execution-probe-v1.cjs'))
    out=BASE/'checks-v2';out.mkdir(exist_ok=False);selection=read(BASE/'selection.json')
    report={'passed':False,'checker_sha256':digest(Path(__file__)),'preparation_sha256':digest(BASE/'preparation.json'),
        'selection_sha256':digest(BASE/'selection.json'),'model_sha256':model.sha256,
        'outside_resource_positions':0,'turns':0,'decisions':0,'searched_decisions':0,'rollouts':0,
        'caps':0,'initial_plan_quantity_changes':0,'initial_plan_sequence_changes':0,
        'new_hf_jobs':0,'new_strength_games':0,'qualification_eligible':False,'reserved_final_seeds_used':False}
    started=time.perf_counter();retained={}
    try:
        fixture=runtime/'ai/strong/fixtures/multiplayer-serving-v1.jsonl'
        assert digest(fixture)==selection['fixture_sha256']
        control_hash=hashlib.sha256()
        for line in fixture.open():
            q=json.loads(line)['request']
            if q['state']['phase']=='Resources':continue
            actual=policy.choose(q);expected=reference.choose(q)
            assert actual['resourcePlan'] is None
            clean={k:v for k,v in actual.items() if k not in ['executionMode','resourcePlan']};clean['arm']='filter'
            assert semantic(clean)==semantic(expected)
            control_hash.update(json.dumps(semantic(clean),sort_keys=True).encode());report['outside_resource_positions']+=1
        assert report['outside_resource_positions']==1798
        report['outside_phase_trace_sha256']=control_hash.hexdigest()
        print({'outside_resource_positions':report['outside_resource_positions']},flush=True)
        with (out/'turns.jsonl').open('x') as stream:
            for label,entry in selection['selected'].items():
                state=engine.call({'op':'reset','request':entry['request'],'seed':'resource-execution-'+label})
                initial=copy.deepcopy(state);decisions=[];actual_actions=[];total_ms=0
                bound=1+sum(state['summary']['market'])
                while not state['done']:
                    q={**state['request'],'requestId':label+'-'+str(len(decisions)),'revision':len(decisions)}
                    unchanged=json.dumps(q);result=policy.choose(q);assert json.dumps(q)==unchanged
                    assert result['move']==state['legal'][result['index']]
                    assert result['executionMode']=='stateless-atomic-resource-replanning-v1'
                    if result['resourcePlan']:
                        plan=result['resourcePlan'];assert result['move']==plan['actions'][0]
                        assert result['search']['truncated']==0
                        assert result['modelProposal']==plan['baselineDecisions'][0]['index']
                        report['searched_decisions']+=1;report['rollouts']+=result['search']['evaluations']
                    else:assert len(state['legal'])==1
                    before=state['summary'];state=engine.call({'op':'step','move':result['move']})
                    actual_actions.append(result['move']);decisions.append({'request':q,'before':before,'result':result,'after':state['summary']})
                    total_ms+=result['elapsedMs'];assert len(decisions)<=bound
                resources=['coal','oil','garbage','uranium']
                counts=[sum(a=={'name':'BuyResource','data':{'resource':r}} for a in actual_actions) for r in resources]
                assert actual_actions[-1]=={'name':'Pass','data':True}
                assert counts==[b-a for a,b in zip(initial['summary']['resources'],state['summary']['resources'])]
                price=0;g=initial['request']['state']
                for r,n in zip(resources,counts):
                    prices=g[r+'Prices'];market=g[r+'Market'];price+=sum(prices[len(prices)-market:len(prices)-market+n])
                assert price==initial['summary']['money']-state['summary']['money']
                first=decisions[0]['result']['resourcePlan'];planned=first['actions'] if first else [actual_actions[0]]
                planned_counts=[sum(a=={'name':'BuyResource','data':{'resource':r}} for a in planned) for r in resources]
                row={'label':label,'initial':initial['summary'],'final':state['summary'],'actual_actions':actual_actions,
                    'actual_counts':counts,'initial_planned_counts':planned_counts,'quantity_changed':counts!=planned_counts,
                    'sequence_changed':actual_actions!=planned,'price':price,'total_ms':total_ms,'decisions':decisions}
                stream.write(json.dumps(row,allow_nan=False)+'\n');stream.flush();retained[label]=row
                report['turns']+=1;report['decisions']+=len(decisions)
                report['initial_plan_quantity_changes']+=int(row['quantity_changed']);report['initial_plan_sequence_changes']+=int(row['sequence_changed'])
                print({'turn':label,'decisions':len(decisions),'planned':planned_counts,'actual':counts,'seconds':total_ms/1000},flush=True)
        label='late-6p-recharged-sealed';q=retained[label]['decisions'][0]['request'];expected=retained[label]['decisions'][0]['result']
        # No game ID or previous calls are required, including when a process is recreated.
        fresh=ResourceReplanningPolicy(model,worker,arm='resource-filter',samples=4)
        try:assert semantic(fresh.choose({**q,'requestId':'unrelated','revision':987654}))==semantic(expected)
        finally:fresh.close()
        assert semantic(policy.choose(q))==semantic(expected)
        cap=ResourceReplanningPolicy(model,worker,arm='resource-filter',samples=4,max_steps=1)
        try:capped=cap.choose(q)
        finally:cap.close()
        assert capped['search']['truncated']>0 and capped['index']==capped['modelProposal']
        write(out/'cap.json',capped)
        command=[sys.executable,str(runtime/'ai/strong/resource_replanning_policy_v1.py'),
            '--model',str(model_path),'--runtime',str(runtime),'--samples','4','--diagnostics']
        requests=[[],{**q,'requestId':'first-cli','revision':17},{**q,'requestId':'retry-cli','revision':18}]
        process=subprocess.run(command,input=''.join(json.dumps(x)+'\n' for x in requests),
            text=True,capture_output=True,check=True,cwd='/tmp')
        responses=[json.loads(line) for line in process.stdout.splitlines()];assert len(responses)==3
        assert 'error' in responses[0] and 'move' not in responses[0]
        for request,response in zip(requests[1:],responses[1:]):
            assert response['requestId']==request['requestId'] and response['revision']==request['revision']
            assert response['move']==expected['move'] and semantic(response['decision'])==semantic(expected)
        write(out/'standalone.json',{'responses':responses,'stderr':process.stderr})
        report.update(passed=True,fresh_process_exact=True,interleaved_request_exact=True,
            request_metadata_invariant=True,standalone_exact=True,deliberate_cap_fallback=True)
    finally:
        policy.close();reference.close();engine.close();report['seconds']=time.perf_counter()-started
        report['artifacts']={p.name:digest(p) for p in out.iterdir() if p.is_file()}
        report['scope']='23 existing engineering resource turns. Actual replanning can differ from initial macro plans; no strength or target-latency claim. Existing canonical sealed-order limitation outside resource phase remains.'
        write(out/'assessment.json',report)
    print(json.dumps(report),flush=True)


if __name__=='__main__':main()
