"""Admit fresh whole-deal collection from both completed HF calibration jobs."""
import argparse
from datetime import datetime, timezone
import fcntl
import hashlib
import importlib.util
import json
import math
from pathlib import Path

from huggingface_hub import HfApi, get_token
from strategic_collection import ROOT,read,write,digest
from opponent_surrogate_collection_v1 import contract

STRONG=ROOT/'ai/strong'
spec=importlib.util.spec_from_file_location('surrogate_runtime_launch',STRONG/'launch-opponent-surrogate-runtime-v1.py')
runtime=importlib.util.module_from_spec(spec);spec.loader.exec_module(runtime)
SOURCE,PROTOCOL=runtime.SOURCE,runtime.PROTOCOL
CALIBRATION=STRONG/'opponent-surrogate-calibration-evidence-v1.json'
PLAN=STRONG/'opponent-surrogate-collection-plan-v1.json'
GUARDS=ROOT/'ai/runs/opponent-surrogate-collection-launches-v1'
OLD='python -u ai/strong/opponent-surrogate-collection-job-v1.py "$PLAYERS" 0 1 --mode runtime'
NEW='python -u ai/strong/opponent-surrogate-collection-job-v1.py "$PLAYERS" "$START" "$END" --mode collection'
assert runtime.BOOTSTRAP.count(OLD)==1
BOOTSTRAP=runtime.BOOTSTRAP.replace(OLD,NEW)


def case_rows(protocol,deals):
    assert type(deals) is int and deals in (1,2,4)
    rows=[]
    for n in protocol['player_counts']:
        for start in range(0,32,deals):
            end=start+deals
            contracts=[contract(protocol,n,d,seat,rule,'collection')
                       for d in range(start,end) for seat in range(n) for rule in range(4)]
            splits={q['split'] for q in contracts};assert len(splits)==1
            rows.append({'case':f'opponent-surrogate-collection-v1-{n}p-{start}-{end}',
                         'players':n,'start':start,'end':end,'split':splits.pop(),
                         'games':len(contracts),'twins':sum(q['twin'] for q in contracts)})
    assert sum(r['games'] for r in rows)==protocol['planned_games']==2560
    assert sum(r['twins'] for r in rows)==protocol['planned_twin_replays']==640
    return rows


def measured_admission(cells,max_in_flight):
    assert type(max_in_flight) is int and 1<=max_in_flight<=32
    assert set(cells)=={'2','6'}
    for n,cell in cells.items():
        assert cell['games']==cell['twin_games']==4*int(n) and cell['caps']==0
        for value in [cell['raw_evidence_bytes'],*[cell['runtime'][k] for k in ('seconds','cpu_seconds','sampled_peak_total_rss_bytes')]]:
            assert type(value) in (int,float) and math.isfinite(value) and value>0
    peak=max(c['runtime']['sampled_peak_total_rss_bytes'] for c in cells.values())
    assert 2*peak<=32*10**9, 'Measured memory requires a new hardware calibration'
    worst=max(max(c['runtime']['seconds'],c['runtime']['cpu_seconds']/8) for c in cells.values())
    raw=max(c['raw_evidence_bytes'] for c in cells.values())
    for deals in (4,2,1):
        estimate=900+2*deals*worst
        hours=math.ceil(estimate/(.75*3600))
        if hours<=12 and 4*deals*raw<=50*10**9:break
    else:raise AssertionError('Need a new measured runtime/storage plan; never shorten games or teacher search')
    return {'flavor':'cpu-upgrade','vcpus':8,'ram_gb':32,'disk_gb':50,'workers':8,
            'deals_per_shard':deals,'timeout_hours':hours,'max_in_flight':max_in_flight,
            'estimated_seconds':estimate,'measurements':cells,
            'calculation':'15 min setup plus twice the worst full HF endpoint time per deal; choose 4/2/1 whole deals with 25% timeout reserve, 2x sampled RSS and 4x raw evidence storage. Calibration pairs every game; main collection pairs every fourth deal, so this deliberately retains that extra time margin.',
            'limitation':'Measured endpoints are not hard bounds for every fresh deal/count. Any cap/failure remains a failure; no automatic replacements or selective exclusions.'}


def dependencies():
    paths=[Path(__file__),Path(runtime.__file__),STRONG/'collect-opponent-surrogate-calibration-v1.py',
           STRONG/'collect-opponent-surrogate-runtime-v1.py',STRONG/'opponent_surrogate_verification_v1.py',
           STRONG/'opponent_surrogate_collection_v1.py',STRONG/'population_policy_verification.py',
           STRONG/'strategic_collection.py']
    return {str(p.relative_to(ROOT)):digest(p) for p in paths}


def prerequisites():
    assert CALIBRATION.exists(), 'Both original HF endpoints must be audited and archived before collection admission'
    source,protocol=runtime.prerequisites()
    calibration=read(CALIBRATION)
    assert calibration['complete'] and calibration['remote_archive_verified']
    assert calibration['jobs']==2 and calibration['games']==calibration['twin_games']==32 and calibration['caps']==0
    assert calibration['source']==source and calibration['protocol_sha256']==digest(PROTOCOL)
    assert calibration['admission']==read(runtime.PLAN) and calibration['admission_sha256']==digest(runtime.PLAN)
    assert calibration['collector_sha256']==digest(STRONG/'collect-opponent-surrogate-calibration-v1.py')
    assert all(digest(ROOT/name)==sha for name,sha in calibration['endpoint_code_hashes'].items())
    folder=ROOT/'ai/runs/opponent-surrogate-calibration-evidence-v1'
    assert digest(folder.with_suffix('.tgz'))==calibration['archive_sha256']
    assert digest(folder/'manifest.json')==calibration['manifest_sha256']
    assert all(digest(folder/name)==sha for name,sha in read(folder/'manifest.json').items())
    cells={n:c['review'] for n,c in calibration['cells'].items()}
    return source,protocol,calibration,cells


def validate_plan(plan,protocol):
    rows=case_rows(protocol,plan['admission']['deals_per_shard'])
    assert sorted(plan['shards'],key=lambda r:r['case'])==sorted(rows,key=lambda r:r['case'])
    assert plan['games']==2560 and plan['twins']==640
    assert len({r['case'] for r in plan['shards']})==len(rows)
    for key in ('automatic_retries','gradients','qualification_eligible','reserved_final_seeds_used'):
        assert plan[key] is False


def prepare(max_in_flight):
    source,protocol,calibration,cells=prerequisites()
    admission=measured_admission(cells,max_in_flight)
    rows=case_rows(protocol,admission['deals_per_shard'])
    rows.sort(key=lambda r:(-r['players'],r['start']))
    plan={'created_at':datetime.now(timezone.utc).isoformat(),'source':source,
          'source_descriptor_sha256':digest(SOURCE),'protocol_sha256':digest(PROTOCOL),
          'calibration_descriptor_sha256':digest(CALIBRATION),'admission':admission,
          'shards':rows,'games':2560,'twins':640,'dependency_hashes':dependencies(),
          'bootstrap_sha256':hashlib.sha256(BOOTSTRAP.encode()).hexdigest(),
          'automatic_retries':False,'gradients':False,'qualification_eligible':False,'reserved_final_seeds_used':False}
    validate_plan(plan,protocol)
    with PLAN.open('x') as f:json.dump(plan,f,indent=2);f.write('\n')
    print({'plan':str(PLAN),'shards':len(rows),'games':2560,'twins':640,'admission':admission})


def admission(case):
    source,protocol,calibration,cells=prerequisites()
    plan=read(PLAN);validate_plan(plan,protocol)
    assert plan['source']==source and plan['source_descriptor_sha256']==digest(SOURCE)
    assert plan['protocol_sha256']==digest(PROTOCOL) and plan['calibration_descriptor_sha256']==digest(CALIBRATION)
    assert plan['admission']==measured_admission(cells,plan['admission']['max_in_flight'])
    assert plan['dependency_hashes']==dependencies()
    assert plan['bootstrap_sha256']==hashlib.sha256(BOOTSTRAP.encode()).hexdigest()
    rows=[r for r in plan['shards'] if r['case']==case];assert len(rows)==1
    return plan,source,rows[0]


def launch(case,execute):
    plan,source,row=admission(case)
    if not execute:
        print({'case':case,'admitted':True,'execute':False,'row':row});return
    token=get_token();assert token
    GUARDS.mkdir(exist_ok=True)
    with (GUARDS/'.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        guard=GUARDS/(case+'.json')
        if guard.exists():
            prior=read(guard)
            assert prior['stage']=='launched' and prior['plan_sha256']==digest(PLAN)
            stage=HfApi().inspect_job(job_id=prior['job_id']).status.stage
            print({'case':case,'existing_job_id':prior['job_id'],'authoritative_status':stage});return
        active=0
        for path in GUARDS.glob('*.json'):
            old=read(path)
            assert old['stage']=='launched' and old['plan_sha256']==digest(PLAN)
            stage=HfApi().inspect_job(job_id=old['job_id']).status.stage
            assert stage in ('RUNNING','SCHEDULING','COMPLETED'), 'Review original failed/uncertain jobs before further submissions'
            active+=stage!='COMPLETED'
        assert active<plan['admission']['max_in_flight']
        record={'case':case,'row':row,'stage':'launch_intent','created_at':datetime.now(timezone.utc).isoformat(),
                'plan_sha256':digest(PLAN),'source':source,'admission':plan['admission'],
                'protocol_sha256':digest(PROTOCOL),'qualification_eligible':False}
        with guard.open('x') as f:json.dump(record,f,indent=2)
        try:
            env={'SOURCE_ARCHIVE':source['archive'],'SOURCE_REVISION':source['revision'],'SOURCE_SHA256':source['sha256'],
                 'SOURCE_MANIFEST_SHA256':source['manifest_sha256'],'SOURCE_MANIFEST_FILES':str(source['manifest_files']),
                 'PROTOCOL_SHA256':digest(PROTOCOL),'HF_HUB_DISABLE_PROGRESS_BARS':'1',
                 **{k.upper():str(row[k]) for k in ('players','start','end')}}
            job=HfApi().run_job(image='python:3.11-slim-bookworm',command=['bash','-lc',BOOTSTRAP],
                flavor=plan['admission']['flavor'],timeout=f"{plan['admission']['timeout_hours']}h",name=case,
                secrets={'HF_TOKEN':token},env=env,
                labels={'project':'powergrid-ai','stage':'opponent-surrogate-collection-v1','case':case})
            record.update(stage='launched',job_id=job.id)
        except BaseException as error:
            record.update(stage='launch_unknown',error=type(error).__name__+': '+str(error));raise
        finally:write(guard,record)
    print({'case':case,'job_id':record['job_id']},flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(__doc__);sub=p.add_subparsers(dest='command',required=True)
    cmd=sub.add_parser('prepare');cmd.add_argument('--max-in-flight',type=int,required=True)
    cmd=sub.add_parser('launch');cmd.add_argument('case');cmd.add_argument('--execute',action='store_true')
    a=p.parse_args()
    if a.command=='prepare':prepare(a.max_in_flight)
    else:launch(a.case,a.execute)
