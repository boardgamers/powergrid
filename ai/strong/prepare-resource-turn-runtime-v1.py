"""Prepare a pinned 96-game runtime pilot and replay the job wrapper locally.

No job submission or strength selection. The seven job specifications include
one local-only eight-game recorded filter control, excluded from the HF pilots.
"""
import argparse
from datetime import datetime,timezone
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys

from public_policy_development_job_v1 import digest,read

ROOT=Path(__file__).resolve().parents[2]
ARTIFACT=ROOT/'ai/runs/resource-turn-full-artifact-v3'
OUT=ROOT/'ai/runs/resource-turn-runtime-prepared-v1'
PROTOCOL=ROOT/'ai/strong/resource-turn-runtime-protocol-v1.json'
PROOF=ROOT/'ai/strong/resource-turn-anchored-policy-evidence-v1.json'
MODES={'corrected':'atomic-search-corrected','anchored':'atomic-search-anchored','whole':'search-turn'}
ENTRY='resource_turn_runtime_job_v1.py'


def save(path,value):
    with path.open('x') as stream:json.dump(value,stream,indent=2,allow_nan=False);stream.write('\n')


def prepare():
    assert not OUT.exists() and not PROTOCOL.exists(),'Inspect existing preparation before retrying'
    assert digest(PROOF)=='79c41324d08cbf618b465bc9d07a0717ebfcbf552e69b0e5a4a13de3b6cf8d04'
    proof=read(PROOF);assert proof['archive']['remote_archive_verified']
    assert proof['counts']['rollout_caps']==0 and proof['counts']['first_searches_matching_history']==20
    assert proof['counts']['lifecycle_replays']==6 and proof['counts']['invalid_history_errors']==2
    assert digest(ARTIFACT/'resource-full-descriptor.json')==proof['descriptor_sha256']
    assert digest(ARTIFACT/'manifest.json')==proof['artifact_manifest_sha256']
    hashes=read(ARTIFACT/'manifest.json')
    assert all(digest(ARTIFACT/name)==sha for name,sha in hashes.items())
    calibration=[]
    for n in (2,6):
        path=ROOT/'ai/runs/resource-replanning-hf-runtime-collected-v1'/f'resource-replanning-hf-runtime-v1-{n}p-resource-filter/verified.json'
        row=read(path);assert row['verified'] and row['authoritative_status']=='COMPLETED'
        calibration.append({'players':n,'job_id':row['job_id'],'path':str(path.relative_to(ROOT)),
            'sha256':digest(path),'measurement':row['runtime']})
    bound=900+4*max(row['measurement']['seconds'] for row in calibration)
    timeout=math.ceil(bound/(.75*3600));assert timeout==4
    jobs={}
    for label,mode in MODES.items():
        for n in (2,6):
            name=f'pg-resource-turn-runtime-v1-{label}-{n}p'
            jobs[name+'.job.json']={'name':name,'mode':mode,'players':n,'games':4*n,'workers':4,
                'seed':f'resource-turn-runtime-v1-{n}p','opponent':'search_geo','start':0,'deals':1,
                'control':False,'reference':None}
    assert len(jobs)==6 and sum(j['games'] for j in jobs.values())==96
    name='pg-resource-turn-runtime-v1-control-2p'
    jobs[name+'.job.json']={'name':name,'mode':'filter','players':2,'games':8,'workers':4,
        'seed':'resource-replanning-development-v1-2p','opponent':'economic','start':0,'deals':1,
        'control':True,'reference':'control-reference.json'}
    archive=ROOT/'ai/runs/resource-replanning-development-complete-evidence-v1/manifest.json'
    assert digest(archive)=='fb4cab7da560d86fe1bad88a363c9e83d3bb0aa86344de12368317dc95ae1839'
    original=read(archive);folder=ROOT/'ai/runs/resource-replanning-development-collected-v1/resource-replanning-development-v1-filter-2p-economic-0-4/artifacts/evaluation'
    selected={};inputs={}
    def original_file(path):
        name=str(path.relative_to(ROOT));sha=digest(path);assert original[name]==sha;inputs[name]=sha
        return read(path) if path.suffix=='.json' else [json.loads(line) for line in path.read_text().splitlines()]
    report=original_file(folder/'evaluation.json')
    for episode in range(8):
        selected[str(episode)]={'terminal':next(r['terminal'] for r in report['results'] if r['episode']==episode),
            'decisions':original_file(folder/f'decisions-{episode}.jsonl')}
    protocol={'revision':'resource-turn-runtime-v1','created_at':datetime.now(timezone.utc).isoformat(),
        'scope':'runtime-only','purpose':'Measure full-game execution and audit boundaries for corrected atomic, anchored atomic and whole-turn resource search. Exclude all pilot outcomes from strength and candidate selection.',
        'artifact_descriptor_sha256':proof['descriptor_sha256'],'artifact_manifest_sha256':proof['artifact_manifest_sha256'],
        'integration_evidence_sha256':digest(PROOF),'integration_archive':proof['archive'],
        'jobs':jobs,'hf_jobs':6,'hf_games':96,'local_recorded_replay_games':8,
        'flavor':'cpu-upgrade','timeout':f'{timeout}h','max_concurrent_jobs':6,
        'resource_estimate':{'calibration':calibration,'estimated_seconds_with_setup':bound,
            'reason':'900 seconds setup plus four times the previous largest measured HF endpoint wall time: factor two for reducing game concurrency from eight to four, and factor two for changed-policy overhead. Planning bound only; 75% timeout target, no guarantee.',
            'prior_memory_peak_bytes':max(row['measurement']['sampled_peak_total_rss_bytes'] for row in calibration)},
        'reference_inputs':inputs,'preparer_sha256':digest(__file__),
        'automatic_retries':False,'development_admitted':False,'new_strength_games':0,
        'gradients':False,'qualification_eligible':False,'reserved_final_seeds_used':False}
    save(PROTOCOL,protocol)
    source=OUT/'source';source.mkdir(parents=True)
    for name in (*hashes,'manifest.json','resource-full-descriptor.json'):
        dest=source/'artifact'/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ARTIFACT/name,dest)
    for name in (ENTRY,'public_policy_development_job_v1.py'):
        shutil.copy2(ROOT/'ai/strong'/name,source/name)
    shutil.copy2(PROTOCOL,source/'runtime-protocol.json')
    for name,job in jobs.items():save(source/name,job)
    save(source/'control-reference.json',selected)
    pins={str(p.relative_to(source)):digest(p) for p in sorted(source.rglob('*')) if p.is_file()}
    save(source/'source-manifest.json',pins)
    prepared={'created_at':protocol['created_at'],'protocol_sha256':digest(PROTOCOL),
        'source_manifest_sha256':digest(source/'source-manifest.json'),'source_files':len(pins),
        'entry_sha256':digest(source/ENTRY),'preparer_sha256':digest(__file__),
        'artifact_descriptor_sha256':proof['descriptor_sha256'],'artifact_manifest_sha256':proof['artifact_manifest_sha256'],
        'integration_evidence_sha256':digest(PROOF),'jobs':jobs,'hf_jobs':6,'hf_games':96,'new_hf_jobs':0,
        'qualification_eligible':False,'reserved_final_seeds_used':False}
    save(OUT/'prepared.json',prepared)
    print(json.dumps({'prepared':True,'source_files':len(pins),'hf_jobs':6,'hf_games':96,'timeout':protocol['timeout']}),flush=True)


def pinned():
    p=read(OUT/'prepared.json');source=OUT/'source'
    assert digest(__file__)==p['preparer_sha256'] and digest(PROTOCOL)==p['protocol_sha256']
    assert digest(PROOF)==p['integration_evidence_sha256']
    assert digest(source/'source-manifest.json')==p['source_manifest_sha256']
    pins=read(source/'source-manifest.json')
    assert set(pins)|{'source-manifest.json'}=={str(f.relative_to(source)) for f in source.rglob('*') if f.is_file()}
    assert all(digest(source/name)==sha for name,sha in pins.items())
    return p


def verify():
    p=pinned();source=OUT/'source'
    assert not (OUT/'verification-intent.json').exists(),'Inspect previous verification before retrying'
    save(OUT/'verification-intent.json',{'prepared_sha256':digest(OUT/'prepared.json'),
        'started_at':datetime.now(timezone.utc).isoformat()})
    for name in p['jobs']:
        output=OUT/'dry'/name
        with (OUT/(name+'.validation.log')).open('x') as log:
            subprocess.run([sys.executable,'-u','-B',str(source/ENTRY),'--source',str(source),
                '--manifest-sha256',p['source_manifest_sha256'],'--job',name,'--output',str(output)],
                cwd='/tmp',stdout=log,stderr=subprocess.STDOUT,check=True)
        assert not output.exists()
    control=next(name for name,job in p['jobs'].items() if job['control']);out=OUT/'local-control'
    with (OUT/'local-control.log').open('x') as log:
        subprocess.run([sys.executable,'-u','-B',str(source/ENTRY),'--source',str(source),
            '--manifest-sha256',p['source_manifest_sha256'],'--job',control,'--output',str(out),'--execute'],
            cwd='/tmp',stdout=log,stderr=subprocess.STDOUT,check=True)
    status=read(out/'status.json')
    assert status['stage']=='complete' and status['games']==status['replay']['exact_games']==8
    assert status['counts']['rollouts']==status['counts']['rollout_caps']==0
    assert status['measurement']['seconds']>0 and status['measurement']['cpu_seconds']>0
    assert status['measurement']['memory_samples']>0 and status['measurement']['sampled_peak_total_rss_bytes']>0
    assert pinned()==p
    result={'passed':True,'jobs_dry_validated':7,'recorded_games_replayed':8,
        'exact_decisions':status['replay']['exact_decisions'],'measurement':status['measurement'],
        'source_manifest_sha256':p['source_manifest_sha256'],'prepared_sha256':digest(OUT/'prepared.json'),
        'control_manifest_sha256':digest(out/'manifest.json'),'control_status_sha256':digest(out/'status.json'),
        'new_hf_jobs':0,'new_full_game_trajectories':0,'qualification_eligible':False,'reserved_final_seeds_used':False}
    save(OUT/'verified.json',result);print(json.dumps(result),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(__doc__);parser.add_argument('operation',choices=['prepare','verify'])
    globals()[parser.parse_args().operation]()
