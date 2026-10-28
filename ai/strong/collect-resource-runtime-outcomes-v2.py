"""Bounded collection of the six original pilots, retaining terminal failures.

Collection only: no submit, cancel, retry, simulation or policy-selection path.
Uses the original collection lock and frozen successful-job auditor. A failed
job can never satisfy the 96-game gate or prevent collecting another original.
"""
from datetime import datetime, timezone
import fcntl
import importlib.util
import json
from pathlib import Path
import re

from huggingface_hub import HfApi, hf_hub_download
from public_policy_development_job_v1 import digest, read, write
from population_policy_verification import extract_verified

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'ai/runs/resource-turn-runtime-outcomes-v2'
RESULT=ROOT/'ai/strong/resource-turn-runtime-outcomes-v2.json'
MANAGER=Path(__file__).with_name('manage-resource-turn-runtime-v1.py')
HANDLES={
    'corrected-2p':'6ae20c1241e90535df775236',
    'corrected-6p':'6ae20c123fb22a235dd4146d',
    'anchored-2p':'6ae20c133fb22a235dd4146f',
    'anchored-6p':'6ae20c1341e90535df775238',
    'whole-2p':'6ae20c133fb22a235dd41471',
    'whole-6p':'6ae20c1341e90535df77523a',
}
LIVE={'SCHEDULING','RUNNING','QUEUED','STARTING'}
FAILED={'ERROR','STOPPED','CANCELED','CANCELLED','DELETED'}


def now():return datetime.now(timezone.utc).isoformat()


def load_manager():
    spec=importlib.util.spec_from_file_location('original_resource_runtime_collector',MANAGER)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def raw_checked(folder,source,row,evidence):
    """Validate provenance and bytes without treating partial games as audited."""
    pins=read(folder/'manifest.json')
    assert digest(folder/'manifest.json')==evidence['manifest_sha256']
    assert set(pins)|{'manifest.json'}=={str(p.relative_to(folder)) for p in folder.rglob('*') if p.is_file()}
    assert all(digest(folder/name)==sha for name,sha in pins.items())
    assert len(pins)+1==evidence['archived_files']
    status=read(folder/'status.json');job=row['job']
    expected={k:source[k] for k in ('source_manifest_sha256','protocol_sha256','entry_sha256',
        'artifact_descriptor_sha256','artifact_manifest_sha256')}
    expected.update(job_spec_sha256=row['job_spec_sha256'],source_revision=source['revision'],
        source_archive_sha256=source['sha256'],job=job)
    assert status['provenance']==expected and status['case']==job['name'] and status['scope']=='runtime-only'
    assert status['gradient_updates']==status['new_strength_games']==0
    assert status['automatic_retries'] is status['qualification_eligible'] is status['reserved_final_seeds_used'] is False
    assert digest(folder/'source-manifest.json')==source['source_manifest_sha256']
    assert digest(folder/'job-spec.json')==row['job_spec_sha256']
    return status


def cached_checked(path,folder,guard,source,row,manager):
    value=read(path)
    assert value['verified'] and value['job_id']==guard['job_id'] and value['row']==row
    assert value['guard_sha256']==digest(folder/'launch.json')
    assert value['source_sha256']==digest(manager.SOURCE)
    assert value['review']['independent_audit_sha256']==digest(path.parent/'independent-audit/result.json')
    assert value['review']['games']==row['job']['games']
    assert value['review']['audit']['counts']['rollout_caps']==0
    return value


def collect_one(api,source,row,manager,output,download=hf_hub_download):
    name=row['job']['name'];original=manager.OUT/name;guard=read(original/'launch.json')
    assert guard['stage']=='launched' and guard['source']==source and guard['row']==row
    suffix=name.removeprefix('pg-resource-turn-runtime-v1-')
    assert guard['job_id']==HANDLES[suffix]
    output.mkdir(exist_ok=True)
    info=api.inspect_job(job_id=guard['job_id']);stage=info.status.stage
    assert info.command==['bash','-lc',manager.BOOTSTRAP] and info.docker_image=='python:3.11-slim-bookworm'
    assert info.flavor==source['flavor']
    assert all(info.environment.get(k)==v for k,v in manager.environment(source,row).items())
    observation={'checked_at':now(),'name':name,'job_id':guard['job_id'],'stage':stage}
    write(output/'status.json',observation)
    if stage in LIVE:return {**observation,'outcome':'pending','verified':False}
    if stage not in FAILED|{'COMPLETED'}:
        return {**observation,'outcome':'unknown_stage','verified':False}
    cached=next((p for p in (output/'verified.json',original/'verified.json') if p.exists()),None)
    if cached is not None:
        assert stage=='COMPLETED','Cached success conflicts with authoritative stage'
        value=cached_checked(cached,original,guard,source,row,manager)
        raw=next(p for p in (output/'artifacts',original/'artifacts') if p.exists())
        status=raw_checked(raw,source,row,value['evidence']);assert status['stage']=='complete'
        return {**observation,'outcome':'verified_success','verified':True,'reused_audit':True,
            'verified_receipt':str(cached.relative_to(ROOT)),'verified_receipt_sha256':digest(cached),
            'review':value['review'],'evidence':value['evidence']}
    log=original/'job.log' if (original/'job.log').exists() else output/'job.log'
    if not log.exists():
        # Fetch completely before writing, so interrupted network observation is
        # not mistaken for a complete terminal log on a subsequent collection.
        lines=list(api.fetch_job_logs(job_id=guard['job_id'],follow=False))
        with log.open('x') as stream:stream.write('\n'.join(str(line) for line in lines))
    receipts=[]
    for line in log.read_text().splitlines():
        if not line.startswith('{'):continue
        try:value=json.loads(line)
        except json.JSONDecodeError:continue
        if set(value)=={'case','status','evidence'} and value['case']==name:receipts.append(value)
    if len(receipts)!=1:
        return {**observation,'outcome':'unverified_terminal','verified':False,
            'archive_receipts':len(receipts),'log_sha256':digest(log)}
    evidence=receipts[0]['evidence']
    assert evidence['repo']=='coyotte508/powergrid-ai-germany-v1'
    assert evidence['archive_path']=='archives/'+name+'.tgz'
    assert evidence['remote_archive_verified'] and re.fullmatch('[a-f0-9]{40}',evidence['revision'])
    archive=Path(download(evidence['repo'],evidence['archive_path'],revision=evidence['revision']))
    assert digest(archive)==evidence['archive_sha256']
    raw=original/'artifacts' if (original/'artifacts').exists() else output/'artifacts'
    if not raw.exists():extract_verified(archive,raw)
    status=raw_checked(raw,source,row,evidence)
    assert status==receipts[0]['status']
    if stage!='COMPLETED' or status['stage']!='complete':
        report=raw/'evaluation/evaluation.json'
        partial=read(report) if report.exists() else None
        if partial is not None:
            assert partial['expected_games']==row['job']['games']
            assert partial['completed_games']==len(partial['results'])
            episodes=[r['episode'] for r in partial['results']]
            assert len(set(episodes))==len(episodes)
        result={**observation,'outcome':'failed_preserved','verified':False,'evidence':evidence,
            'raw_artifacts_verified':True,'wrapper_stage':status['stage'],'measurement':status.get('measurement'),
            'partial_complete_games_reported':partial['completed_games'] if partial else None,
            'partial_games_independently_audited':False,'failure_type':status.get('failure_type'),
            'original_success_gate_passed':False}
        write(output/'failure-evidence.json',result)
        return result
    audit=output/'independent-audit'
    assert not audit.exists(),'Inspect interrupted independent audit before retrying; do not rerun blindly'
    review=manager.verify_artifacts(raw,source,row,evidence,audit)
    verified={**observation,'row':row,'review':review,'evidence':evidence,'verified':True,
        'source_sha256':digest(manager.SOURCE),'guard_sha256':digest(original/'launch.json')}
    manager.save(output/'verified.json',verified)
    return {**observation,'outcome':'verified_success','verified':True,'reused_audit':False,
        'verified_receipt':str((output/'verified.json').relative_to(ROOT)),
        'verified_receipt_sha256':digest(output/'verified.json'),'review':review,'evidence':evidence}


def summarize(records):
    assert len(records)==6 and {r['job_id'] for r in records}==set(HANDLES.values())
    succeeded=[r for r in records if r['outcome']=='verified_success']
    failures=[r for r in records if r['outcome']=='failed_preserved']
    terminal=all(r['stage'] in FAILED|{'COMPLETED'} for r in records)
    verified_games=sum(r['review']['games'] for r in succeeded)
    passed=len(succeeded)==6 and verified_games==96
    return {'checked_at':now(),'all_originals_terminal':terminal,'success_gate_passed':passed,
        'verified_successful_jobs':len(succeeded),'verified_successful_games':verified_games,
        'failed_jobs_preserved':len(failures),'expected_jobs':6,'expected_games':96,
        'pending_jobs':sum(r['outcome']=='pending' for r in records),
        'unverified_jobs':sum(r['outcome'] not in ('verified_success','failed_preserved','pending') for r in records),
        'jobs':records,'scope':'runtime-only','new_hf_jobs':0,'new_inference':0,'new_full_games':0,
        'automatic_retries':False,'new_strength_games':0,'qualification_eligible':False,
        'reserved_final_seeds_used':False}


def collect():
    manager=load_manager();source=manager.source_checked()
    OUT.mkdir(exist_ok=True)
    with (manager.OUT/'.collect.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        rows=[]
        for row in source['rows']:
            result=collect_one(HfApi(),source,row,manager,OUT/row['job']['name'])
            rows.append(result)
            print(json.dumps({k:result[k] for k in ('name','job_id','stage','outcome')}),flush=True)
        report=summarize(rows)
        report.update(source_sha256=digest(manager.SOURCE),collector_sha256=digest(__file__))
        write(OUT/'state.json',report)
        if report['all_originals_terminal']:
            if RESULT.exists():
                previous=read(RESULT)
                assert [(r['job_id'],r['outcome']) for r in previous['jobs']]==[(r['job_id'],r['outcome']) for r in rows]
            else:manager.save(RESULT,report)
        return {k:report[k] for k in ('all_originals_terminal','success_gate_passed',
            'verified_successful_jobs','verified_successful_games','failed_jobs_preserved','pending_jobs','unverified_jobs')}


if __name__=='__main__':print(json.dumps(collect()),flush=True)
