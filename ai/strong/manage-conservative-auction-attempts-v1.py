"""Account explicitly for reviewed bootstrap retries in the frozen study.

Original failed directories stay unchanged. Only retry-bootstrap can create the
two authorized attempt guards; the continuing owner never retries a failed job.
"""
import argparse
from contextlib import contextmanager, ExitStack
from datetime import datetime,timezone
import fcntl
import json
import os
from pathlib import Path
import re

from huggingface_hub import HfApi,get_token,hf_hub_download
import conservative_auction_bootstrap_recovery_v1 as recovery
from public_policy_development_job_v1 import read,digest,write
from public_policy_final_contract_v1 import object_hash
from population_policy_verification import extract_verified

original=recovery.manager()
ROOT=original.ROOT
OUT=ROOT/'ai/runs/conservative-auction-development-attempts-v1'
SOURCE=original.SOURCE
LOCAL=original.LOCAL
RESULT=ROOT/'ai/strong/conservative-auction-development-results-with-attempts-v1.json'
planning=original.planning
verify_artifacts=original.verify_artifacts
OWNER=ROOT/'ai/runs/conservative-auction-development-attempts-coordinator-v1'
TEST_RESULT=ROOT/'ai/runs/conservative-auction-attempts-tests-v1.json'
TEST_PINS=('manage-conservative-auction-attempts-v1.py',
    'coordinate-conservative-auction-attempts-v1.py',
    'compare-conservative-auction-attempts-v1.py',
    'test_conservative_auction_attempts_v1.py',
    'conservative_auction_bootstrap_recovery_v1.py')


def tests_checked():
    result=read(TEST_RESULT)
    assert result['passed'] is True and result['tests']>=15
    assert result['code_hashes']=={name:digest(Path(__file__).with_name(name)) for name in TEST_PINS}
    return result


@contextmanager
def exclusive_execution():
    """Exclude old owners and direct collectors as well as the new owner."""
    old=ROOT/'ai/runs/conservative-auction-development-coordinator-recovery-v3'
    state=read(old/'state.json')
    assert state['stage']=='stopped_for_inspection'
    assert all(digest(ROOT/name)==sha for name,sha in state['code_hashes'].items())
    names={b'coordinate-conservative-auction-development-v2.py',
        b'recover-conservative-auction-development-v2.py',b'recover-conservative-auction-development-v3.py',
        b'manage-conservative-auction-development-v2.py',b'manage-conservative-auction-attempts-v1.py',
        b'coordinate-conservative-auction-attempts-v1.py'}
    with ExitStack() as stack:
        for path in (old/'.owner.lock',old.with_name('conservative-auction-development-coordinator-recovery-v2')/'.owner.lock',
                     old.with_name('conservative-auction-development-coordinator-v2')/'.owner.lock',original.OUT/'.reviewed-execution.lock'):
            lock=stack.enter_context(path.open('a'));fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        for path in Path('/proc').glob('[0-9]*/cmdline'):
            if int(path.parent.name)==os.getpid():continue
            try:parts=path.read_bytes().split(b'\x00')
            except (FileNotFoundError,PermissionError,ProcessLookupError):continue
            assert not any(p.rsplit(b'/',1)[-1] in names for p in parts),'Another owner or collector is live'
        yield state


def now():return datetime.now(timezone.utc).isoformat()
def write_new(path,value):original.write_new(path,value)
def source_checked():
    source=original.source_checked();recovery.checked_approval(source);return source


def execution_folder(name):
    if name in recovery.TARGETS:return OUT/name/'attempt-1'
    return original.OUT/name


def guard_checked(source,row,guard):
    assert guard['stage']=='launched' and guard['row']==row and guard['source_fingerprint']==object_hash(source)
    assert re.fullmatch('[a-f0-9]{24}',guard['job_id'])
    if 'bootstrap_recovery_sha256' in guard:
        approval,bootstrap=recovery.checked_approval(source)
        assert guard['bootstrap_recovery_sha256']==digest(recovery.APPROVAL)
        assert guard['actual_bootstrap_sha256']==recovery.sha_text(bootstrap)
        assert guard['node_cache_descriptor_sha256']==digest(recovery.CACHE)
        target=recovery.TARGETS.get(row['name'])
        assert guard['retry_of']==(target['job_id'] if target else None)
        assert guard['execution_attempt']==(1 if target else 0)
    else:
        assert row['name'] not in recovery.TARGETS,'Reviewed retry must declare its original failed attempt'


def source_environment(source,row):
    return {'SOURCE_ARCHIVE':source['archive'],'SOURCE_REVISION':source['revision'],'SOURCE_SHA256':source['sha256'],
        'SOURCE_MANIFEST_SHA256':source['source_manifest_sha256'],'PROTOCOL_SHA256':source['protocol_sha256'],
        'PILOT_JOB':row['job'],'PILOT_NAME':row['name'],
        'HF_HUB_DISABLE_PROGRESS_BARS':'1','PYTHONDONTWRITEBYTECODE':'1'}


def launch_once(api,directory,source,row,token):
    assert row in source['rows'] and row['shard']['seed'].startswith('conservative-auction-development-v1-')
    approval,bootstrap=recovery.checked_approval(source)
    directory=Path(directory);assert directory==execution_folder(row['name'])
    directory.mkdir(parents=True,exist_ok=True)
    with (directory/'.launch.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        path=directory/'launch.json'
        if path.exists():
            guard=read(path);guard_checked(source,row,guard);return guard
        target=recovery.TARGETS.get(row['name'])
        guard={'stage':'launch_intent','created_at':now(),'source_fingerprint':object_hash(source),'row':row,
            'bootstrap_recovery_sha256':digest(recovery.APPROVAL),'actual_bootstrap_sha256':recovery.sha_text(bootstrap),
            'node_cache_descriptor_sha256':digest(recovery.CACHE),'execution_attempt':1 if target else 0,
            'retry_of':target['job_id'] if target else None}
        write_new(path,guard)
        try:
            job=api.run_job(image='python:3.11-slim-bookworm',command=['bash','-lc',bootstrap],
                flavor=row['flavor'],timeout=row['timeout'],name=row['name'],env=source_environment(source,row),
                secrets={'HF_TOKEN':token},labels={'project':'powergrid-ai','stage':'conservative-auction-development-v2',
                'runtime-setup':'cached-node-v1','execution-attempt':str(guard['execution_attempt'])})
            guard.update(stage='launched',job_id=job.id)
        except BaseException as error:
            guard.update(stage='launch_unknown',failure_type=type(error).__name__);raise
        finally:write(path,guard)
        return guard


def retry_bootstrap(execute=False):
    source=source_checked();approval,_=recovery.checked_approval(source)
    if not execute:return {'execute':False,'reviewed_retries':list(recovery.TARGETS),'new_hf_jobs':0}
    tests_checked()
    assert all(not (execution_folder(name)/'launch.json').exists() for name in recovery.TARGETS), 'Inspect existing retry outcomes; no automatic resubmission'
    with (original.OUT/'.batch-launch.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        api=HfApi();active=0
        for row in source['rows']:
            path=original.OUT/row['name']/'launch.json'
            if not path.exists() or (path.parent/'verified.json').exists():continue
            guard=read(path);assert guard['stage']=='launched' and guard['row']==row and guard['source_fingerprint']==object_hash(source)
            stage=api.inspect_job(job_id=guard['job_id']).status.stage
            if row['name'] in recovery.TARGETS:
                assert guard['job_id']==recovery.TARGETS[row['name']]['job_id'] and stage=='ERROR'
                assert not api.file_exists('coyotte508/powergrid-ai-germany-v1','archives/'+row['name']+'.tgz')
            else:
                assert stage in ('RUNNING','SCHEDULING','COMPLETED'),'Review any other terminal failure before launching'
                active+=stage!='COMPLETED'
        assert active+len(recovery.TARGETS)<=64
        token=get_token();assert token
        launched=[]
        for row in source['rows']:
            if row['name'] in recovery.TARGETS:
                guard=launch_once(api,execution_folder(row['name']),source,row,token)
                item={'name':row['name'],'job_id':guard['job_id'],'retry_of':guard['retry_of']}
                launched.append(item);print(json.dumps(item),flush=True)
        return {'manual_reviewed_retries':launched,'active_jobs':active+len(launched),'original_failed_guards_preserved':True}


def cached_checked(source,row,folder):
    guard=read(folder/'launch.json');guard_checked(source,row,guard);saved=read(folder/'verified.json')
    assert saved['source_sha256']==digest(SOURCE) and saved['row']==row
    assert saved['guard_sha256']==digest(folder/'launch.json') and saved['job_id']==guard['job_id']
    assert saved['stage']=='COMPLETED' and saved['verified']
    assert digest(folder/'artifacts/manifest.json')==saved['evidence']['manifest_sha256']
    if 'bootstrap_recovery_sha256' in guard:
        setup=saved['execution_setup']
        assert setup['command_sha256']==guard['actual_bootstrap_sha256']
        assert setup['bootstrap_recovery_sha256']==guard['bootstrap_recovery_sha256']
        assert setup['api_command_and_environment_verified'] is True
    return saved


def launch(execute=False,limit=64):
    source=source_checked();assert type(limit) is int and 1<=limit<=64
    if not execute:return {'execute':False,'planned_jobs':648,'games':10080}
    tests_checked()
    assert all((execution_folder(name)/'launch.json').exists() for name in recovery.TARGETS), 'Run the explicit reviewed retry operation first'
    with (original.OUT/'.batch-launch.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        api=HfApi();active=0;pending=[]
        for row in source['rows']:
            folder=execution_folder(row['name']);path=folder/'launch.json'
            if not path.exists():
                assert row['name'] not in recovery.TARGETS,'Owner cannot create another retry'
                pending.append(row);continue
            if (folder/'verified.json').exists():cached_checked(source,row,folder);continue
            guard=read(path);guard_checked(source,row,guard)
            stage=api.inspect_job(job_id=guard['job_id']).status.stage
            assert stage in ('SCHEDULING','RUNNING','COMPLETED'),'Inspect failed/unknown selected attempt; never retry automatically'
            active+=stage!='COMPLETED'
        token=get_token();assert token;launched=[]
        for row in pending[:max(0,min(limit,64-active))]:
            guard=launch_once(api,execution_folder(row['name']),source,row,token)
            item={'name':row['name'],'job_id':guard['job_id']};launched.append(item);print(json.dumps(item),flush=True)
        return {'new_jobs':launched,'active_jobs':active+len(launched),'remaining_unsubmitted':len(pending)-len(launched)}


def collect():
    source=source_checked();approval,bootstrap=recovery.checked_approval(source)
    OUT.mkdir(exist_ok=True);results=[];states=[];index={};api=HfApi()
    for row in source['rows']:
        name=row['name'];folder=execution_folder(name);path=folder/'launch.json'
        if not path.exists():continue
        guard=read(path);guard_checked(source,row,guard)
        index[name]={'directory':str(folder.relative_to(ROOT)),'job_id':guard['job_id'],
            'guard_sha256':digest(path),'execution_attempt':guard.get('execution_attempt',0),
            'retry_of':guard.get('retry_of'),'bootstrap_recovery_sha256':guard.get('bootstrap_recovery_sha256')}
        if (folder/'verified.json').exists():results.append(cached_checked(source,row,folder));continue
        job=api.inspect_job(job_id=guard['job_id'])
        status={'checked_at':now(),'job_id':guard['job_id'],'stage':job.status.stage,'name':name}
        write(folder/'status.json',status);states.append(status)
        if status['stage'] in ('RUNNING','SCHEDULING'):continue
        log='\n'.join(str(line) for line in api.fetch_job_logs(job_id=guard['job_id'],follow=False))
        (folder/'job.log').write_text(log);receipts=[]
        for line in log.splitlines():
            if not line.startswith('{'):continue
            try:r=json.loads(line)
            except json.JSONDecodeError:continue
            if set(r)=={'case','status','evidence'} and r['case']==name:receipts.append(r)
        if status['stage']!='COMPLETED' or len(receipts)!=1:
            write(folder/'failure.json',{**status,'receipts':len(receipts),'logs_preserved':True})
            raise RuntimeError('Selected attempt failed or is ambiguous; preserve it without resubmission')
        evidence=receipts[0]['evidence']
        assert evidence['repo']=='coyotte508/powergrid-ai-germany-v1'
        assert evidence['archive_path']=='archives/'+name+'.tgz' and evidence['remote_archive_verified']
        assert re.fullmatch('[a-f0-9]{40}',evidence['revision'])
        archive=Path(hf_hub_download(evidence['repo'],evidence['archive_path'],revision=evidence['revision']))
        assert digest(archive)==evidence['archive_sha256']
        if not (folder/'artifacts').exists():extract_verified(archive,folder/'artifacts')
        actual_bootstrap=bootstrap if 'bootstrap_recovery_sha256' in guard else original.BOOTSTRAP
        assert job.command==['bash','-lc',actual_bootstrap]
        assert job.docker_image=='python:3.11-slim-bookworm' and job.flavor==row['flavor']
        assert all(job.environment.get(k)==v for k,v in source_environment(source,row).items())
        setup={'kind':'hf-cached-node-v1' if 'bootstrap_recovery_sha256' in guard else 'original-node-origin',
            'command_sha256':recovery.sha_text(actual_bootstrap),
            'bootstrap_recovery_sha256':guard.get('bootstrap_recovery_sha256'),
            'api_command_and_environment_verified':True}
        review=verify_artifacts(folder/'artifacts',source,row,evidence)
        saved={**status,'row':row,'verified':True,'review':review,'evidence':evidence,
            'source_sha256':digest(SOURCE),'guard_sha256':digest(path),'execution_setup':setup}
        write_new(folder/'verified.json',saved);results.append(saved)
        print(json.dumps({'verified':name,'games':review['games'],'attempt':guard.get('execution_attempt',0)}),flush=True)
    report={'checked_at':now(),'complete':len(results)==len(source['rows']),'verified_jobs':len(results),
        'expected_jobs':len(source['rows']),'jobs':results,'selected_unverified_statuses':states,
        'source_sha256':digest(SOURCE),'execution_index':index,'bootstrap_recovery_sha256':digest(recovery.APPROVAL),
        'failed_original_attempts':approval['allowed_retries'],'qualified':False,'reserved_final_seeds_used':False}
    write(OUT/'collection-state.json',report)
    if report['complete'] and not RESULT.exists():
        assert len(index)==648 and sum(r['review']['games'] for r in results)==10080
        assert len({r['job_id'] for r in results})==648
        write_new(RESULT,report)
    return {k:report[k] for k in ('complete','verified_jobs','expected_jobs')}


if __name__=='__main__':
    parser=argparse.ArgumentParser(__doc__)
    parser.add_argument('operation',choices=('retry-bootstrap','collect','launch'))
    parser.add_argument('--execute',action='store_true');args=parser.parse_args()
    function=retry_bootstrap if args.operation=='retry-bootstrap' else launch if args.operation=='launch' else collect
    with exclusive_execution():
        print(json.dumps(function(args.execute) if args.operation!='collect' else function()),flush=True)
