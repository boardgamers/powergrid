"""Recheck, package and archive the complete opponent-model runtime pilot once."""
import importlib.util
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile

from huggingface_hub import HfApi
from strategic_collection import ROOT, read, write, digest
from policy_iteration_evidence_archive import upload_evidence

STRONG = ROOT/'ai/strong'
spec = importlib.util.spec_from_file_location('reference_probe',STRONG/'probe-reference-opponents-v1.py')
probe = importlib.util.module_from_spec(spec); spec.loader.exec_module(probe)
EVIDENCE = ROOT/'ai/runs/reference-opponent-pilot-evidence-v1'
DESCRIPTOR = STRONG/'reference-opponent-pilot-evidence-v1.json'
LAYOUT = ROOT/'ai/runs/reference-opponent-clean-layout-v1'


def main():
    p=read(probe.OUT/'protocol.json');probe.validate(p)
    complete=read(probe.OUT/'pilot-complete.json')
    assert complete['complete'] and complete['controls']==896 and complete['reference_rollouts']==16
    assert complete['protocol_sha256']==digest(probe.OUT/'protocol.json')
    assert len(complete['rejection_checks'])==7 and complete['caps']==0
    assert not EVIDENCE.exists() and not EVIDENCE.with_suffix('.tgz').exists() and not DESCRIPTOR.exists()
    assert not LAYOUT.exists()
    controls=[];pilots=[]
    for i in range(7):
        r=read(probe.OUT/f'control-{i}.json')
        check=probe.verify_rows(p,i,'neural_population',0,64,r['rows'])
        assert check==read(probe.OUT/f'control-{i}.check.json')
        controls.append({k:v for k,v in r.items() if k!='rows'})
    for i in p['pilot_roots']:
        r=read(probe.OUT/f'pilot-{i}.json')
        check=probe.verify_rows(p,i,'reference_opponent_v1',0,2,r['rows'])
        assert check==read(probe.OUT/f'pilot-{i}.check.json')
        pilots.append({k:v for k,v in r.items() if k!='rows'} | {'checks':check})
    tests=read(probe.OUT/'worker-test-receipt.json')
    assert tests['tests_passed']==4 and tests['tests_failed']==0
    assert tests['test_sha256']==digest(probe.TEST) and tests['worker_sha256']==digest(probe.WORKER)
    source=read(STRONG/'population-hybrid-development-source-v1.json')
    source_archive=ROOT/'ai/runs'/source['archive']
    assert digest(source_archive)==source['sha256']
    plan=read(STRONG/'population-hybrid-development-plan-v1.json')
    assert all(digest(ROOT/name)==sha for name,sha in plan['dependency_hashes'].items())
    assert digest(STRONG/'strategic_collection.py')==p['runtime_hashes']['ai/strong/strategic_collection.py']
    hardware=next(row for row in HfApi().list_jobs_hardware() if row.name=='cpu-basic')
    assert hardware.cpu=='2 vCPU' and hardware.ram=='16 GB'
    # Runtime admission uses only cost and completeness, never the pilot outcomes.
    max_cpu_per_rollout=max(r['cpu_seconds']/4 for r in pilots)
    predicted_cpu_seconds_per_root=max_cpu_per_rollout*128
    worlds_per_job=16
    def timeout_for(worlds):return max(1,math.ceil((max_cpu_per_rollout*(worlds*2)/2*4+600)/3600))
    while timeout_for(worlds_per_job)>6 and worlds_per_job>4:worlds_per_job//=2
    timeout_hours=timeout_for(worlds_per_job)
    assert timeout_hours<=6,'Measured per-world cost is too high for this admission; review before launching'
    rss=max(r['sampled_peak_total_rss_bytes'] for r in [*controls,*pilots])
    assert rss*4<16*1024**3,'Insufficient measured RAM headroom'
    admission={'purpose':'Seven fixed roots, 64 worlds and two fixed actions each; 896 reference continuations. Diagnostic only.',
               'flavor':hardware.name,'cpu':hardware.cpu,'ram':hardware.ram,'ephemeral_storage':hardware.ephemeral_storage,
               'workers_per_job':4,'jobs':7*(64//worlds_per_job),'max_concurrent_jobs':7,
               'worlds_per_job':worlds_per_job,'timeout_hours':timeout_hours,
               'max_pilot_cpu_seconds_per_rollout':max_cpu_per_rollout,
               'estimated_max_cpu_seconds_per_root':predicted_cpu_seconds_per_root,
               'timeout_rule':'Start at 16 worlds/job. Measured maximum CPU per rollout × (2 × worlds/job) / 2 vCPU × 4 margin + 600 seconds setup; round up to hours. Halve worlds/job if above six hours, down to four. This is an admission estimate, not a runtime guarantee.',
               'sampled_peak_total_rss_bytes':rss,'memory_limitations':'100 ms sampled sum of process RSS, including shared pages; not a hard upper bound. Fourfold headroom required.',
               'workers_note':'Four independent worker processes share the two vCPUs; unchanged simulation partitioning, no GPU required.',
               'automatic_retries':False,'jobs_launched':0,'gradients':False,
               'qualification_eligible':False,'reserved_final_seeds_used':False}
    EVIDENCE.mkdir();LAYOUT.mkdir()
    with tarfile.open(source_archive) as archive: archive.extractall(LAYOUT,filter='data')
    inputs=list(probe.OUT.glob('*.json'))+list(probe.OLD.glob('*.json'))
    inputs += [probe.WORKER,probe.TEST,Path(probe.__file__),Path(__file__),
               STRONG/'reference-opponent-job-v1.py',STRONG/'launch-reference-opponents-v1.py',
               STRONG/'population-hybrid-development-source-v1.json',
               STRONG/'auction-world-generalization-evidence-v1.json']
    for file in inputs:
        relative=file.relative_to(ROOT)
        for dest in (EVIDENCE,LAYOUT):
            target=dest/relative;target.parent.mkdir(parents=True,exist_ok=True)
            assert not target.exists() or digest(target)==digest(file),'Overlay changed a frozen file'
            shutil.copy2(file,target);assert digest(target)==digest(file)
    # Exercise imports and model preparation in a clean package, with only path relocation.
    cmd=[sys.executable,str(LAYOUT/'ai/strong/reference-opponent-job-v1.py'),'6',
         '--runtime',str(LAYOUT),'--model',p['model_path'],'--check-layout']
    result=subprocess.run(cmd,cwd=LAYOUT,text=True,capture_output=True,check=True)
    assert all(digest(LAYOUT/name)==sha for name,sha in p['runtime_hashes'].items())
    write(EVIDENCE/'layout-check.json',{'exit_code':result.returncode,'stdout':result.stdout,
                                     'stderr':result.stderr,'unchanged_frozen_files':len(p['runtime_hashes'])})
    write(EVIDENCE/'runtime-admission.json',admission)
    review={'protocol_sha256':digest(probe.OUT/'protocol.json'),'controls':controls,'pilot':pilots,
            'frozen_dependency_checks':len(plan['dependency_hashes']),
            'collector_sha256':digest(__file__),'admission':admission,
            'limitations':p['limitations'],'no_pilot_strength_claim':True,'new_hf_jobs':0}
    write(EVIDENCE/'review.json',review)
    write(EVIDENCE/'manifest.json',{str(f.relative_to(EVIDENCE)):digest(f) for f in sorted(EVIDENCE.rglob('*')) if f.is_file()})
    descriptor={**review,**upload_evidence(EVIDENCE)}
    write(DESCRIPTOR,descriptor)
    print(json.dumps(descriptor,indent=2))


if __name__=='__main__':main()
