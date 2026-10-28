"""Collect and independently audit the two corrected v4 runtime pilots.

No submission, retries, new inference or policy selection. Failure and unknown
outcomes remain explicit; only two complete audited jobs can pass the 32-game
runtime gate. The original six v1 pilots use their separate original collector.
"""
from datetime import datetime,timezone
import fcntl
import importlib.util
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import sys

from huggingface_hub import HfApi,hf_hub_download
from public_policy_development_job_v1 import digest,read,write
from population_policy_verification import extract_verified

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'ai/runs/resource-turn-runtime-collected-v2'
RESULT=ROOT/'ai/strong/resource-turn-runtime-results-v2.json'
TERMINAL=ROOT/'ai/strong/resource-turn-runtime-terminal-v2.json'
TEST=ROOT/'ai/runs/resource-turn-runtime-collector-tests-v2/assessment.json'
spec=importlib.util.spec_from_file_location('corrected_resource_launcher',
    Path(__file__).with_name('launch-resource-turn-runtime-v2.py'))
launcher=importlib.util.module_from_spec(spec);spec.loader.exec_module(launcher)
LIVE={'SCHEDULING','RUNNING','QUEUED','STARTING'}
FAILED={'ERROR','STOPPED','CANCELED','CANCELLED','DELETED'}


def now():return datetime.now(timezone.utc).isoformat()


def guards_checked(source):
    assert len(source['rows'])==2 and sum(row['job']['games'] for row in source['rows'])==32
    guards={}
    for row in source['rows']:
        name=row['job']['name'];guard=read(launcher.OUT/name/'launch.json')
        assert guard['stage']=='launched' and guard['source']==source and guard['row']==row
        assert row['job']['control'] is False and re.fullmatch('[a-f0-9]{24}',guard['job_id'])
        guards[name]=guard
    assert len(guards)==2 and len({v['job_id'] for v in guards.values()})==2
    return guards


def raw_checked(folder,source,row,evidence):
    manifest=read(folder/'manifest.json')
    assert digest(folder/'manifest.json')==evidence['manifest_sha256']
    assert set(manifest)|{'manifest.json'}=={str(p.relative_to(folder)) for p in folder.rglob('*') if p.is_file()}
    assert all(not (folder/n).is_symlink() and digest(folder/n)==sha for n,sha in manifest.items())
    assert len(manifest)+1==evidence['archived_files']
    status=read(folder/'status.json');job=row['job']
    expected={k:source[k] for k in ('source_manifest_sha256','protocol_sha256','entry_sha256',
        'artifact_descriptor_sha256','artifact_manifest_sha256','admission_sha256')}
    expected.update(job_spec_sha256=row['job_spec_sha256'],source_revision=source['revision'],
        source_archive_sha256=source['sha256'],job=job)
    assert status['provenance']==expected and status['case']==job['name'] and status['scope']=='runtime-only'
    assert status['gradient_updates']==status['new_strength_games']==0
    assert status['automatic_retries'] is status['qualification_eligible'] is status['reserved_final_seeds_used'] is False
    assert digest(folder/'source-manifest.json')==source['source_manifest_sha256']
    assert digest(folder/'job-spec.json')==row['job_spec_sha256']
    assert digest(folder/'admission.json')==source['admission_sha256']
    measurement=status['measurement']
    assert all(math.isfinite(measurement[k]) and measurement[k]>=0
        for k in ('seconds','cpu_seconds','sampled_peak_total_rss_bytes','memory_samples'))
    assert measurement['seconds']>0
    # A failure immediately after startup can precede the first CPU/RSS sample.
    # Keep its raw evidence; require positive measurements only for success.
    if status['stage']=='complete':
        assert all(measurement[k]>0 for k in ('cpu_seconds','sampled_peak_total_rss_bytes','memory_samples'))
    assert measurement['memory_sampling_period_seconds']==.2 and measurement['includes_startup_and_validation'] is True
    return status


def independent_audit(folder,source,row,evidence,audit_directory):
    status=raw_checked(folder,source,row,evidence);job=row['job']
    assert status['stage']=='complete' and status['games']==job['games'] and status['replay'] is None
    report=read(folder/'evaluation/evaluation.json');remote_audit=read(folder/'evaluation/independent-audit.json')
    assert digest(folder/'evaluation/evaluation.json')==status['evaluation_sha256']
    assert digest(folder/'evaluation/independent-audit.json')==status['audit_sha256']
    assert report['all_complete'] is True and not report['errors']
    assert report['completed_games']==report['expected_games']==len(report['results'])==job['games']
    expected={k:job[k] for k in ('mode','players','opponent','seed','start','deals','workers')}
    expected.update(artifact='/workspace/source/artifact',output=f"/workspace/output/{job['name']}/evaluation",
        descriptor_sha256=source['artifact_descriptor_sha256'])
    assert report['config']==expected
    assert not audit_directory.exists(), 'Inspect interrupted independent audit before retrying'
    audit_directory.mkdir()
    for path in (folder/'evaluation').glob('decisions-*.jsonl'):shutil.copy2(path,audit_directory/path.name)
    artifact=launcher.preflight.OUT/'source/artifact'
    code="""import json,sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.argv[1])/'policy'))
from resource_turn_full_audit_v4 import audit
report=json.loads(Path(sys.argv[2]).read_text())
config={**report['config'],'artifact':sys.argv[1],'output':sys.argv[3]}
result=audit(config,report['results'])
Path(sys.argv[3],'result.json').write_text(json.dumps(result,indent=2)+'\\n')
"""
    with (audit_directory/'driver.log').open('x') as log:
        subprocess.run([sys.executable,'-u','-B','-c',code,str(artifact),
            str(folder/'evaluation/evaluation.json'),str(audit_directory)],
            cwd='/tmp',stdout=log,stderr=subprocess.STDOUT,check=True)
    review=read(audit_directory/'result.json')
    assert review==remote_audit and review['passed'] is True and review['paired_schedule_checked'] is True
    assert review['games']==job['games'] and review['counts']==status['counts'] and review['counts']['rollout_caps']==0
    return {'games':job['games'],'audit':review,'measurement':status['measurement'],
        'independent_audit_sha256':digest(audit_directory/'result.json')}


def cached_checked(output,source,row,guard):
    value=read(output/'verified.json')
    assert value['verified'] is True and value['job_id']==guard['job_id'] and value['row']==row
    assert value['guard_sha256']==digest(launcher.OUT/row['job']['name']/'launch.json')
    assert value['source_sha256']==digest(launcher.SOURCE)
    assert value['collector_sha256']==digest(__file__)
    assert value['review']['independent_audit_sha256']==digest(output/'independent-audit/result.json')
    status=raw_checked(output/'artifacts',source,row,value['evidence'])
    assert status['stage']=='complete' and status['games']==value['review']['games']==row['job']['games']
    assert status['measurement']==value['review']['measurement']
    audit=value['review']['audit']
    assert audit==read(output/'independent-audit/result.json')
    assert audit['passed'] is True and audit['paired_schedule_checked'] is True
    assert audit['counts']==status['counts'] and audit['counts']['rollout_caps']==0
    return value


def collect_one(api,source,row,guard,output,download=hf_hub_download):
    name=row['job']['name'];info=api.inspect_job(job_id=guard['job_id']);stage=info.status.stage
    assert info.command==['bash','-lc',launcher.BOOTSTRAP]
    assert info.docker_image=='python:3.11-slim-bookworm' and info.flavor==source['flavor']
    assert all(info.environment.get(k)==v for k,v in launcher.environment(source,row).items())
    output.mkdir(exist_ok=True)
    observation={'checked_at':now(),'name':name,'job_id':guard['job_id'],'stage':stage}
    write(output/'status.json',observation)
    if stage in LIVE:return {**observation,'outcome':'pending','verified':False}
    if stage not in FAILED|{'COMPLETED'}:return {**observation,'outcome':'unknown_stage','verified':False}
    if (output/'verified.json').exists():
        assert stage=='COMPLETED', 'Cached audit conflicts with current remote stage'
        value=cached_checked(output,source,row,guard)
        return {**observation,'outcome':'verified_success','verified':True,'reused_audit':True,
            'verified_receipt':str((output/'verified.json').relative_to(ROOT)),
            'verified_receipt_sha256':digest(output/'verified.json'),'review':value['review'],'evidence':value['evidence']}
    log=output/'job.log'
    if not log.exists():
        # Network failure must not leave a partial log that looks terminal.
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
    assert evidence['archive_path']=='archives/'+name+'.tgz' and evidence['remote_archive_verified'] is True
    assert re.fullmatch('[a-f0-9]{40}',evidence['revision'])
    archive=Path(download(evidence['repo'],evidence['archive_path'],revision=evidence['revision']))
    assert digest(archive)==evidence['archive_sha256']
    raw=output/'artifacts'
    if not raw.exists():extract_verified(archive,raw)
    status=raw_checked(raw,source,row,evidence)
    assert status==receipts[0]['status']
    if stage!='COMPLETED' or status['stage']!='complete':
        report=raw/'evaluation/evaluation.json';partial=read(report) if report.exists() else None
        if partial is not None:
            assert partial['expected_games']==row['job']['games']
            assert partial['completed_games']==len(partial['results'])
            episodes=[r['episode'] for r in partial['results']]
            assert len(set(episodes))==len(episodes)
        result={**observation,'outcome':'failed_preserved','verified':False,'evidence':evidence,
            'raw_artifacts_verified':True,'wrapper_stage':status['stage'],'measurement':status['measurement'],
            'partial_complete_games_reported':partial['completed_games'] if partial else None,
            'partial_games_independently_audited':False,'failure_type':status.get('failure_type'),
            'runtime_success_gate_passed':False}
        write(output/'failure-evidence.json',result);return result
    review=independent_audit(raw,source,row,evidence,output/'independent-audit')
    verified={**observation,'row':row,'review':review,'evidence':evidence,'verified':True,
        'source_sha256':digest(launcher.SOURCE),'guard_sha256':digest(launcher.OUT/name/'launch.json'),
        'collector_sha256':digest(__file__)}
    launcher.save(output/'verified.json',verified)
    return {**observation,'outcome':'verified_success','verified':True,'reused_audit':False,
        'verified_receipt':str((output/'verified.json').relative_to(ROOT)),
        'verified_receipt_sha256':digest(output/'verified.json'),'review':review,'evidence':evidence}


def summarize(records,source,guards):
    assert len(records)==len(guards)==2
    assert len({r['name'] for r in records})==2
    assert {r['name']:r['job_id'] for r in records}=={name:g['job_id'] for name,g in guards.items()}
    assert len({r['job_id'] for r in records})==2
    jobs={r['job']['name']:r['job'] for r in source['rows']}
    assert set(jobs)==set(guards)
    successes=[r for r in records if r['outcome']=='verified_success']
    for row in successes:
        assert row['stage']=='COMPLETED' and row['verified'] is True
        assert row['review']['games']==jobs[row['name']]['games']
    games=sum(r['review']['games'] for r in successes)
    return {'checked_at':now(),'all_terminal':all(r['stage'] in FAILED|{'COMPLETED'} for r in records),
        'complete':len(successes)==2 and games==32,'verified_jobs':len(successes),'verified_games':games,
        'failed_jobs_preserved':sum(r['outcome']=='failed_preserved' for r in records),
        'pending_jobs':sum(r['outcome']=='pending' for r in records),
        'unverified_jobs':sum(r['outcome'] not in ('verified_success','failed_preserved','pending') for r in records),
        'expected_jobs':2,'expected_games':32,'jobs':records,'scope':'runtime-only','new_hf_jobs':0,
        'new_inference':0,'new_full_games':0,'new_strength_games':0,'automatic_retries':False,
        'qualification_eligible':False,'reserved_final_seeds_used':False}


def collect():
    source,_,_=launcher.source_checked();guards=guards_checked(source)
    proof=read(TEST)
    assert proof['passed'] and proof['new_hf_jobs']==proof['network_calls']==0
    assert all(digest(ROOT/n)==v for n,v in proof['code_hashes'].items())
    OUT.mkdir(exist_ok=True)
    with (OUT/'.collect.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);records=[]
        for row in source['rows']:
            name=row['job']['name'];record=collect_one(HfApi(),source,row,guards[name],OUT/name)
            records.append(record)
            print(json.dumps({k:record[k] for k in ('name','job_id','stage','outcome')}),flush=True)
        report=summarize(records,source,guards)
        report.update(source_sha256=digest(launcher.SOURCE),admission_sha256=source['admission_sha256'],collector_sha256=digest(__file__))
        write(OUT/'state.json',report)
        if report['all_terminal'] and report['unverified_jobs']==0:
            if TERMINAL.exists():
                previous=read(TERMINAL)
                assert previous['source_sha256']==report['source_sha256']
                assert [(r['job_id'],r['outcome']) for r in previous['jobs']]==[(r['job_id'],r['outcome']) for r in records]
            else:launcher.save(TERMINAL,report)
        if report['complete'] and not RESULT.exists():launcher.save(RESULT,report)
        return {k:report[k] for k in ('all_terminal','complete','verified_jobs','verified_games',
            'failed_jobs_preserved','pending_jobs','unverified_jobs')}


if __name__=='__main__':print(json.dumps(collect()),flush=True)
