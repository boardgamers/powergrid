"""Profile four predetermined recorded roots; no jobs, policy changes or selection.

HF phase timings come from the complete audited whole-turn two-player pilot.
Component timings are new local replays of the first Resources request in
episodes 0..3, one per rule. Every returned diagnostic and continuation must
match the original receipt, except elapsed time. No completed game is rerun.
"""
from collections import defaultdict
from datetime import datetime,timezone
import hashlib
import importlib
import json
import math
from pathlib import Path
import statistics
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
PILOT=ROOT/'ai/runs/resource-turn-runtime-hf-v1/pg-resource-turn-runtime-v1-whole-2p'
ARTIFACT=ROOT/'ai/runs/resource-turn-full-artifact-v3'
OUT=ROOT/'ai/runs/resource-runtime-profile-v2'
FAILED=ROOT/'ai/runs/resource-runtime-profile-v1'
RESULT=ROOT/'ai/strong/resource-runtime-profile-results-v1.json'
DESCRIPTOR_SHA='f41f16f64bf4e9b068e09e15116a6f02c5254ef60c01bd7650a0d7ad356a2e57'


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path):return json.loads(Path(path).read_text())
def write(path,value):
    with Path(path).open('x') as stream:json.dump(value,stream,indent=2,allow_nan=False);stream.write('\n')
def semantic(value):
    if isinstance(value,dict):return {k:semantic(v) for k,v in value.items() if k!='elapsedMs'}
    if isinstance(value,list):return [semantic(v) for v in value]
    return value
def quantile(values,p):
    values=sorted(values);index=p*(len(values)-1);lo=math.floor(index);hi=math.ceil(index)
    return values[lo]+(values[hi]-values[lo])*(index-lo)
def summary(values):
    assert values and all(math.isfinite(v) and v>=0 for v in values)
    return {'calls':len(values),'sum_seconds':sum(values)/1000,'median_ms':statistics.median(values),
        'p95_ms':quantile(values,.95),'max_ms':max(values)}


def inputs():
    verified=read(PILOT/'verified.json');artifacts=PILOT/'artifacts';pins=read(artifacts/'manifest.json')
    assert verified['verified'] and verified['job_id']=='6ae20c133fb22a235dd41471'
    assert digest(artifacts/'manifest.json')==verified['evidence']['manifest_sha256']
    assert digest(PILOT/'independent-audit/result.json')==verified['review']['independent_audit_sha256']
    assert read(PILOT/'independent-audit/result.json')==verified['review']['audit']
    assert verified['review']['games']==8 and verified['review']['audit']['counts']['rollout_caps']==0
    paths=sorted((artifacts/'evaluation').glob('decisions-*.jsonl'));assert len(paths)==8
    roots={};phases=defaultdict(list);hashes={};rollouts=neural=0;search_ms=0
    for path in paths:
        relative=str(path.relative_to(artifacts));sha=digest(path);assert pins[relative]==sha
        hashes[str(path.relative_to(ROOT))]=sha;episode=int(path.stem.split('-')[-1])
        for line in path.read_text().splitlines():
            row=json.loads(line);value=row['response'];whole=value['kind']=='resource-turn'
            detail=value['diagnostics'] if whole else value['decision']
            phases[row['request']['state']['phase']].append(detail['elapsedMs'])
            if whole:
                plan=detail['searchResult'];rollouts+=plan['search']['evaluations'];neural+=plan['search']['neuralDecisions']
                search_ms+=plan['elapsedMs']
                if episode in range(4) and episode not in roots:roots[episode]=row
    counts=verified['review']['audit']['counts']
    assert set(roots)==set(range(4)) and sum(map(len,phases.values()))==counts['policy_requests']
    assert rollouts==counts['rollouts'] and neural==counts['neural_decisions']
    phase={key:summary(values) for key,values in phases.items()};total=sum(v['sum_seconds'] for v in phase.values())
    timing={'source':'original_hf_job','job_id':verified['job_id'],'games':8,'phase_timings':phase,
        'summed_policy_seconds':total,'summed_search_seconds':search_ms/1000,
        'resource_fraction_of_summed_policy_time':phase['Resources']['sum_seconds']/total,
        'search_fraction_of_resource_policy_time':search_ms/1000/phase['Resources']['sum_seconds'],
        'rollouts':rollouts,'neural_decisions':neural,'workflow_measurement':verified['review']['measurement'],
        'interpretation':'Summed per-request wall intervals across four concurrent games; not job wall time, CPU attribution, production percentiles or AMD 8840U latency.'}
    return verified,roots,hashes,timing


def profile(policy_class,episode,row):
    policy=policy_class(ARTIFACT,'search-turn');module=importlib.import_module('resource_turn_search_v1')
    assert Path(module.__file__).resolve()==ARTIFACT/'runtime/ai/strong/resource_turn_search_v1.py'
    timings=defaultdict(float);calls=defaultdict(int)
    original_node=module.Node.call;original_pool=module.EnginePool.call;original_predict=module.predict_batch
    model=policy.producer.model;original_session=model.session
    def timed(key,function,*args,**kwargs):
        start=time.perf_counter()
        try:return function(*args,**kwargs)
        finally:timings[key]+=time.perf_counter()-start;calls[key]+=1
    def node(self,request):return timed('node_setup_baseline_exchange',original_node,self,request)
    def pool(self,request):return timed('rollout_engine_and_ipc',original_pool,self,request)
    def predict(*args,**kwargs):return timed('batch_prediction_inclusive',original_predict,*args,**kwargs)
    class Session:
        def __getattr__(self,name):return getattr(original_session,name)
        def run(self,*args,**kwargs):return timed('onnx_run',original_session.run,*args,**kwargs)
    module.Node.call=node;module.EnginePool.call=pool;module.predict_batch=predict;model.session=Session()
    try:
        began=time.perf_counter();value=policy.decide(row['request']);seconds=time.perf_counter()-began
    finally:
        module.Node.call=original_node;module.EnginePool.call=original_pool
        module.predict_batch=original_predict;model.session=original_session;policy.close()
    write(OUT/f'response-{episode}.json',value)
    # Public transport serializes integer world IDs into JSON object keys.
    # Compare that actual wire representation, not the pre-serialization dict.
    assert semantic(read(OUT/f'response-{episode}.json'))==semantic(row['response']),'Instrumentation replay differs from original complete receipt'
    split={'onnx_run':timings['onnx_run'],
        'batch_preparation_and_postprocessing':timings['batch_prediction_inclusive']-timings['onnx_run'],
        'rollout_engine_and_ipc':timings['rollout_engine_and_ipc'],
        'node_setup_baseline_exchange':timings['node_setup_baseline_exchange']}
    split['other_python_and_process_startup']=seconds-sum(split.values())
    assert all(v>=0 and math.isfinite(v) for v in split.values())
    plan=value['diagnostics']['searchResult'];assert plan['search']['truncated']==0
    result={'episode':episode,'rule':{'variant':row['request']['state']['options']['variant'],
        'sealed':row['request']['state']['options']['fastBid']},'request_revision':row['request']['revision'],
        'seconds':seconds,'component_seconds':split,'inclusive_timer_seconds':dict(timings),'timer_calls':dict(calls),
        'rollouts':plan['search']['evaluations'],'neural_decisions':plan['search']['neuralDecisions'],
        'exact_original_receipt':True,'response_sha256':digest(OUT/f'response-{episode}.json')}
    write(OUT/f'profile-{episode}.json',result);print(json.dumps(result),flush=True);return result


def main():
    assert not OUT.exists() and not RESULT.exists(),'Inspect any previous profiling intent/outcome before retrying'
    prior=read(FAILED/'failure-summary.json')
    assert prior['saved_public_json_receipt_matches_original'] and prior['completed_profiles']==0
    assert digest(FAILED/'original-profiler.py')==prior['original_profiler_sha256']
    verified,roots,hashes,timing=inputs()
    assert digest(ARTIFACT/'resource-full-descriptor.json')==DESCRIPTOR_SHA
    assert digest(ARTIFACT/'manifest.json')=='91c52c3ba66dde260b8dfedac1e4d227472193f82757a0317fe079c4ccba38cb'
    assert all(digest(ARTIFACT/name)==sha for name,sha in read(ARTIFACT/'manifest.json').items())
    OUT.mkdir();plan={'created_at':datetime.now(timezone.utc).isoformat(),'scope':'runtime_profiling_only',
        'selection':'First resource request in original episodes 0,1,2,3, fixed before local profiling; no win outcomes used.',
        'source_sha256':digest(__file__),'verified_pilot_sha256':digest(PILOT/'verified.json'),
        'original_archive':verified['evidence'],'input_hashes':hashes,'artifact_descriptor_sha256':DESCRIPTOR_SHA,
        'preserved_failed_profile':{'directory':str(FAILED.relative_to(ROOT)),
            'summary_sha256':digest(FAILED/'failure-summary.json'),'original_profiler_sha256':prior['original_profiler_sha256']},
        'local_environment':{'python':sys.version.split()[0],
            'node':subprocess.check_output(['node','--version'],text=True).strip()},
        'new_hf_jobs':0,'new_full_game_trajectories':0,'new_strength_games':0,
        'qualification_eligible':False,'reserved_final_seeds_used':False}
    write(OUT/'plan.json',plan);write(OUT/'hf-phase-timings.json',timing)
    for episode,row in roots.items():write(OUT/f'input-{episode}.json',row)
    sys.path.insert(0,str(ARTIFACT/'policy'));module=importlib.import_module('resource_turn_full_policy_v3')
    assert Path(module.__file__).resolve()==ARTIFACT/'policy/resource_turn_full_policy_v3.py'
    profiles=[profile(module.FullResourcePolicy,episode,roots[episode]) for episode in range(4)]
    totals={key:sum(p['component_seconds'][key] for p in profiles) for key in profiles[0]['component_seconds']}
    seconds=sum(p['seconds'] for p in profiles)
    report={'passed':True,'plan_sha256':digest(OUT/'plan.json'),'hf_phase_timings':timing,
        'local_replays':profiles,'local_summed_seconds':seconds,'local_component_seconds':totals,
        'local_component_fractions':{k:v/seconds for k,v in totals.items()},
        'rollouts_replayed':sum(p['rollouts'] for p in profiles),
        'neural_decisions_replayed':sum(p['neural_decisions'] for p in profiles),
        'exact_original_receipts':4,'rollout_caps':0,
        'interpretation':'Instrumentation replays on the local research host, not the AMD 8840U target. Engine timing includes transport/serialization and thread coordination; ONNX timing includes CPU session execution. No claim of pure JavaScript CPU or GPU speedup.',
        'new_hf_jobs':0,'new_full_game_trajectories':0,'new_strength_games':0,'new_gradients':0,
        'qualification_eligible':False,'reserved_final_seeds_used':False}
    write(OUT/'assessment.json',report)
    write(RESULT,{**report,'assessment_sha256':digest(OUT/'assessment.json'),
        'output_hashes':{str(p.relative_to(OUT)):digest(p) for p in sorted(OUT.iterdir()) if p.is_file()}})
    print(json.dumps({'passed':True,'local_component_fractions':report['local_component_fractions'],
        'exact_original_receipts':4,'rollouts_replayed':report['rollouts_replayed']}),flush=True)


if __name__=='__main__':main()
