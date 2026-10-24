"""Offline exact-policy engineering benchmark; no HF client, jobs or gradients."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time


def read(path):return json.loads(Path(path).read_text())
def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def write(path,data):Path(path).write_text(json.dumps(data,indent=2,allow_nan=False)+'\n')


def run(package,output,required_cpu):
    manifest=read(package/'manifest.json')
    assert all(digest(package/name)==sha for name,sha in manifest['files'].items())
    processor=next(line.split(':',1)[1].strip() for line in Path('/proc/cpuinfo').read_text().splitlines() if line.startswith('model name'))
    assert not required_cpu or required_cpu in processor
    sys.path.insert(0,str(package/'ai/strong'))
    from hybrid_search import Model
    from population_hybrid_policy import PopulationPolicy
    from population_policy_verification import verify_decision
    import numpy,onnxruntime
    output.mkdir(parents=True,exist_ok=False)
    status={'stage':'running','pid':os.getpid(),'processor':processor,'required_cpu':required_cpu,
        'manifest_sha256':digest(package/'manifest.json'),'started_at':datetime.now(timezone.utc).isoformat(),
        'host':platform.node(),'python':platform.python_version(),'numpy':numpy.__version__,
        'onnxruntime':onnxruntime.__version__,'node':subprocess.check_output(['node','--version'],text=True).strip(),
        'gradients':False,'qualification_eligible':False,'reserved_final_seeds_used':False}
    write(output/'status.json',status)
    counts={'model_positions':0,'filter_positions':0,'search_cases':0,'rollouts':0,'caps':0}
    def verify(result,fixture):
        # Verify the exact JSON receipt representation used by the HF arena.
        result=json.loads(json.dumps(result,allow_nan=False))
        q=fixture['request'];assert result['move']==fixture['legal'][result['index']]
        assert result['modelSha256']==manifest['model_pin']['files']['inference64.onnx']
        verify_decision(result,{'players':len(q['state']['players']),'arm':result['arm'],
            'samples':8,'model_sha256':result['modelSha256']},q['player'])
    def semantic(result):return {k:v for k,v in result.items() if k!='elapsedMs'}
    start=time.perf_counter();policies=[]
    try:
        init=time.perf_counter();model=Model(package/'policy.onnx',threads=1)
        status['model_load_ms']=1000*(time.perf_counter()-init)
        worker=package/'ai/strong/population-hybrid-policy.cjs'
        policies=[PopulationPolicy(model,worker,arm=arm,samples=8,workers=1,max_steps=2400) for arm in ['model','filter']]
        with (package/'fixtures.jsonl').open() as fixtures,(output/'model-filter.jsonl').open('x') as stream:
            for index,line in enumerate(fixtures):
                fixture=json.loads(line);q=fixture['request'];results={}
                for policy in policies:
                    result=policy.choose(q);verify(result,fixture);results[policy.arm]=result
                    counts[policy.arm+'_positions']+=1
                stream.write(json.dumps({'index':index,'requestId':q['requestId'],'revision':q['revision'],
                    'results':results},allow_nan=False)+'\n')
        assert counts['model_positions']==counts['filter_positions']==2553
        for policy in policies:policy.close()
        policies=[]
        print({'model_filter_positions':5106},flush=True)
        selected=read(package/'selected-fixtures.json')
        assert set(selected)=={'2p-bid','2p-building','6p-bid','6p-building'}
        baseline={}
        with (output/'search.jsonl').open('x') as stream:
            for threads,workers in [(1,1),(4,4)]:
                model=Model(package/'policy.onnx',threads=threads)
                policy=PopulationPolicy(model,worker,arm='combined',samples=8,workers=workers,max_steps=2400)
                policies=[policy]
                for name,entry in selected.items():
                    fixture=entry['fixture'];result=policy.choose(fixture['request']);verify(result,fixture)
                    assert result['search'] and result['search']['usable'] and result['search']['truncated']==0
                    if threads==1:baseline[name]=semantic(result)
                    else:assert semantic(result)==baseline[name],'Thread/worker settings changed policy results'
                    counts['search_cases']+=1;counts['rollouts']+=result['search']['evaluations']
                    counts['caps']+=result['search']['truncated']
                    stream.write(json.dumps({'fixture':name,'threads':threads,'workers':workers,'result':result},allow_nan=False)+'\n');stream.flush()
                    print({'fixture':name,'threads':threads,'workers':workers,'seconds':result['elapsedMs']/1000},flush=True)
                policy.close();policies=[]
        assert counts['search_cases']==8 and counts['caps']==0
        assert all(digest(package/name)==sha for name,sha in manifest['files'].items())
        status.update(stage='completed',passed=True)
    except BaseException as error:
        status.update(stage='failed',passed=False,error=type(error).__name__+': '+str(error));raise
    finally:
        for policy in policies:policy.close()
        status.update(counts=counts,seconds=time.perf_counter()-start,finished_at=datetime.now(timezone.utc).isoformat())
        status['scope']='Engineering parity on 2553 existing model/filter positions and four existing endpoint Recharged/sealed search positions, with two execution settings. No fresh strength games or representative gameplay latency distribution.'
        status['output_hashes']={p.name:digest(p) for p in output.iterdir() if p.is_file() and p.name!='status.json'}
        write(output/'status.json',status)


if __name__=='__main__':
    parser=argparse.ArgumentParser(__doc__);parser.add_argument('--package',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True);parser.add_argument('--require-cpu',default='')
    args=parser.parse_args();run(args.package.resolve(),args.output.resolve(),args.require_cpu)
