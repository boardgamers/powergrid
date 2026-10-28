"""Exercise the bundled admission checks in validation-only subprocesses.

Synthetic admission fixtures are explicitly dry-test data, never actual HF
admissions. No job submission, model inference or game simulation is possible.
"""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys

from public_policy_development_job_v1 import read,digest

ROOT=Path(__file__).resolve().parents[2]
PREP=ROOT/'ai/runs/resource-turn-runtime-prepared-v2'
OUT=ROOT/'ai/runs/resource-runtime-admission-checks-v2'


def save(path,value):
    with path.open('x') as stream:
        json.dump(value,stream,indent=2);stream.write('\n')


def main():
    assert not OUT.exists(),'Inspect existing check before retry'
    source=PREP/'source';prepared=read(PREP/'prepared.json');protocol=read(source/'runtime-protocol.json')
    assert digest(source/'source-manifest.json')==prepared['source_manifest_sha256']
    pins=read(source/'source-manifest.json');assert all(digest(source/n)==v for n,v in pins.items())
    jobs={n:digest(source/n) for n,j in protocol['jobs'].items() if not j['control']}
    assert len(jobs)==2
    dry={'revision':'resource-turn-runtime-admission-v2','source_manifest_sha256':prepared['source_manifest_sha256'],
        'protocol_sha256':digest(source/'runtime-protocol.json'),'all_originals_terminal':True,
        'original_outcomes_sha256':'0'*64,'source_evidence_preserved':True,'scope':'runtime-only',
        'automatic_retries':False,'job_specs':jobs,'flavor':'cpu-upgrade','max_concurrent_jobs':2,
        'timeout_seconds':21600,'fixture_only':'Synthetic validation input; NOT an actual runtime admission.'}
    cases=[('valid-shape-dry-only',None),('wrong-source',lambda d:d.update(source_manifest_sha256='1'*64)),
        ('originals-live',lambda d:d.update(all_originals_terminal=False)),
        ('invalid-original-evidence',lambda d:d.update(original_outcomes_sha256='missing')),
        ('evidence-not-preserved',lambda d:d.update(source_evidence_preserved=False)),
        ('wrong-scope',lambda d:d.update(scope='development')),
        ('automatic-retries',lambda d:d.update(automatic_retries=True)),
        ('wrong-job-set',lambda d:d['job_specs'].update({'extra.job.json':'2'*64})),
        ('wrong-budget',lambda d:d.update(timeout_seconds=43201)),
        ('wrong-concurrency',lambda d:d.update(max_concurrent_jobs=3)),
        ('changed-admission-bytes',None)]
    OUT.mkdir();(OUT/'dry-fixtures').mkdir();results=[]
    for name,change in cases:
        value=deepcopy(dry)
        if change is not None:change(value)
        path=OUT/'dry-fixtures'/(name+'.json');save(path,value)
        sha=digest(path) if name!='changed-admission-bytes' else '3'*64
        output=OUT/'must-not-exist'/name
        command=[sys.executable,'-u','-B',str(source/'resource_turn_runtime_job_v2.py'),
            '--source',str(source),'--manifest-sha256',prepared['source_manifest_sha256'],
            '--job',next(iter(jobs)),'--output',str(output),'--admission',str(path),'--admission-sha256',sha]
        # Intentionally no --execute or --upload, even for the synthetic positive.
        result=subprocess.run(command,cwd='/tmp',capture_output=True,text=True)
        (OUT/(name+'.log')).write_text(result.stdout+result.stderr)
        assert not output.exists()
        if name=='valid-shape-dry-only':
            assert result.returncode==0
            response=json.loads(result.stdout)
            assert response['valid_job'] and response['execute'] is False
            assert response['provenance']['admission_sha256']==digest(path)
        else:assert result.returncode!=0 and 'ValueError:' in result.stderr
        results.append({'case':name,'expected_acceptance':name=='valid-shape-dry-only',
            'exit_code':result.returncode,'no_output_created':True,'log_sha256':digest(OUT/(name+'.log'))})
    control=next(n for n,j in protocol['jobs'].items() if j['control']);output=OUT/'must-not-exist'/'control-upload'
    result=subprocess.run([sys.executable,'-u','-B',str(source/'resource_turn_runtime_job_v2.py'),
        '--source',str(source),'--manifest-sha256',prepared['source_manifest_sha256'],
        '--job',control,'--output',str(output),'--execute','--upload'],cwd='/tmp',capture_output=True,text=True)
    (OUT/'control-upload.log').write_text(result.stdout+result.stderr)
    assert result.returncode!=0 and 'Recorded control is local-only' in result.stderr and not output.exists()
    results.append({'case':'control-upload-rejected','exit_code':result.returncode,'no_output_created':True,
        'log_sha256':digest(OUT/'control-upload.log')})
    assert all(digest(source/n)==v for n,v in pins.items())
    report={'passed':True,'checks':len(results),'results':results,'source_manifest_sha256':prepared['source_manifest_sha256'],
        'checker_sha256':digest(__file__),'actual_hf_admission_created':False,
        'synthetic_fixtures_only':True,'new_hf_jobs':0,'new_inference':0,'new_full_game_trajectories':0,
        'qualification_eligible':False,'reserved_final_seeds_used':False,
        'output_hashes':{str(p.relative_to(OUT)):digest(p) for p in OUT.rglob('*') if p.is_file()}}
    save(OUT/'assessment.json',report)
    print(json.dumps({k:report[k] for k in ('passed','checks','actual_hf_admission_created','new_hf_jobs','new_inference')}),flush=True)


if __name__=='__main__':main()
