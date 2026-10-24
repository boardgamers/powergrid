"""Exact resource-policy stress benchmark with passive timing; no jobs or gradients."""
import argparse
from contextlib import contextmanager
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time


def read(p):return json.loads(p.read_text())
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,d):p.write_text(json.dumps(d,indent=2,allow_nan=False)+'\n')
def semantic(d):
    if isinstance(d,dict):return {str(k):semantic(v) for k,v in d.items() if k!='elapsedMs'}
    if isinstance(d,list):return [semantic(v) for v in d]
    return d


@contextmanager
def observe():
    import resource_turn_search_v1 as resource
    import population_hybrid_policy as population
    from hybrid_search import EnginePool,Node
    totals={'prediction_seconds':0.,'prediction_calls':0,'predicted_rows':0,
        'engine_pool_seconds':0.,'engine_pool_calls':0,'engine_observation_rows':0,
        'root_node_seconds':0.,'root_node_calls':0}
    saved=[]
    for module in [resource,population]:
        original=module.predict_batch
        def measured(model,rows,*args,_original=original,**kwargs):
            started=time.perf_counter()
            result=_original(model,rows,*args,**kwargs)
            totals['prediction_seconds']+=time.perf_counter()-started
            totals['prediction_calls']+=1;totals['predicted_rows']+=len(rows)
            return result
        saved.append((module,'predict_batch',original));module.predict_batch=measured
    original_pool=EnginePool.call
    def pool_call(self,request):
        started=time.perf_counter();result=original_pool(self,request)
        totals['engine_pool_seconds']+=time.perf_counter()-started;totals['engine_pool_calls']+=1
        totals['engine_observation_rows']+=sum(o is not None for o in result['observations'])
        return result
    saved.append((EnginePool,'call',original_pool));EnginePool.call=pool_call
    original_node=Node.call
    def node_call(self,request):
        started=time.perf_counter();result=original_node(self,request)
        totals['root_node_seconds']+=time.perf_counter()-started;totals['root_node_calls']+=1
        return result
    saved.append((Node,'call',original_node));Node.call=node_call
    try:yield totals
    finally:
        for obj,name,original in reversed(saved):setattr(obj,name,original)


def run(package,output,required_cpu):
    manifest=read(package/'manifest.json')
    for name,sha in manifest['files'].items():assert digest(package/name)==sha
    processor=next(l.split(':',1)[1].strip() for l in Path('/proc/cpuinfo').read_text().splitlines() if l.startswith('model name'))
    assert not required_cpu or required_cpu in processor
    sys.path.insert(0,str(package/'ai/strong'))
    from hybrid_search import Model
    from resource_replanning_policy_v1 import ResourceReplanningPolicy
    import numpy,onnxruntime
    output.mkdir(parents=True,exist_ok=False)
    status={'stage':'running','pid':os.getpid(),'processor':processor,'required_cpu':required_cpu,
        'host':platform.node(),'python':platform.python_version(),'numpy':numpy.__version__,
        'onnxruntime':onnxruntime.__version__,'node':subprocess.check_output(['node','--version'],text=True).strip(),
        'started_at':datetime.now(timezone.utc).isoformat(),'manifest_sha256':digest(package/'manifest.json'),
        'gradients':False,'new_hf_jobs':0,'qualification_eligible':False,'reserved_final_seeds_used':False}
    write(output/'status.json',status)
    start=time.perf_counter();policy=None;rows=[];controls={};rollouts=0
    try:
        selected=read(package/'slow-roots.json');assert len(selected)==4
        with (output/'results.jsonl').open('x') as stream:
            for threads,workers in manifest['execution_settings']:
                began=time.perf_counter();model=Model(package/'policy.onnx',threads=threads)
                load_ms=1000*(time.perf_counter()-began);assert model.sha256==manifest['model_sha256']
                policy=ResourceReplanningPolicy(model,package/'ai/strong/population-hybrid-policy.cjs',
                    arm='resource-filter',samples=manifest['samples'],workers=workers,max_steps=2400)
                for label,entry in selected.items():
                    with observe() as timings:
                        began=time.perf_counter();result=policy.choose(entry['request']);wall=time.perf_counter()-began
                    assert result['search']['usable'] and result['search']['truncated']==0
                    expected={k:v for k,v in entry['reference'].items() if k not in ['round','decision']}
                    assert semantic(result)==semantic(expected),'Original atomic decision changed: '+label
                    if label in controls:assert semantic(result)==controls[label],'Execution settings changed the policy'
                    else:controls[label]=semantic(result)
                    accounted=sum(timings[k] for k in ['prediction_seconds','engine_pool_seconds','root_node_seconds'])
                    assert 0<=accounted<=wall
                    profile={**timings,'wall_seconds':wall,'python_other_seconds':wall-accounted,
                        'scope':'Prediction includes array packing and ONNX execution. Engine pool includes JS work, IPC and JSON handling. Timers are serial outer-call durations, not CPU utilization.'}
                    record={'case':label,'threads':threads,'workers':workers,'model_load_ms':load_ms,
                        'profile':profile,'result':result}
                    stream.write(json.dumps(record,allow_nan=False)+'\n');stream.flush();rows.append(record)
                    rollouts+=result['search']['evaluations']
                    print({'case':label,'threads':threads,'workers':workers,'seconds':wall,
                        'prediction_seconds':timings['prediction_seconds'],'engine_pool_seconds':timings['engine_pool_seconds']},flush=True)
                policy.close();policy=None
        assert len(rows)==12
        for name,sha in manifest['files'].items():assert digest(package/name)==sha
        status.update(stage='completed',passed=True)
    except BaseException as error:
        status.update(stage='failed',passed=False,error=type(error).__name__+': '+str(error));raise
    finally:
        if policy is not None:policy.close()
        status.update(searches=len(rows),rollouts=rollouts,seconds=time.perf_counter()-start,
            finished_at=datetime.now(timezone.utc).isoformat())
        status['scope']='Four slow public roots selected from four engineering games; 4-world resource-filter, three thread/worker settings. Stress sample, not representative gameplay latency or strength.'
        status['output_hashes']={p.name:digest(p) for p in output.iterdir() if p.is_file() and p.name!='status.json'}
        write(output/'status.json',status)


if __name__=='__main__':
    parser=argparse.ArgumentParser(__doc__);parser.add_argument('--package',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path);parser.add_argument('--require-cpu',default='')
    args=parser.parse_args();run(args.package.resolve(),args.output.resolve(),args.require_cpu)
