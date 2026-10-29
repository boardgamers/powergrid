"""Continue the unchanged grid using original data, never rerunning failed jobs.

Normal jobs retain the original verifier. A separate verified receipt may admit
complete terminal data after the narrowly tested shutdown failure. HF ERROR is
never relabelled COMPLETED; original artifacts and failed reports stay intact.
"""
import argparse
import fcntl
import importlib.util
import json
from pathlib import Path
import re

from huggingface_hub import HfApi, get_token, hf_hub_download
from public_policy_development_job_v1 import digest, read, write
from public_policy_final_audit_v1 import same
from public_policy_final_contract_v1 import object_hash
from population_policy_verification import extract_verified
import current_auction_shutdown_recovery_v1 as recovery

spec = importlib.util.spec_from_file_location('unchanged_current_grid', Path(__file__).with_name('manage-current-auction-grid-v1.py'))
base = importlib.util.module_from_spec(spec); spec.loader.exec_module(base)
ROOT, LOCAL, OUT, SOURCE = base.ROOT, base.LOCAL, base.OUT, base.SOURCE
RESULT = ROOT/'ai/strong/current-auction-grid-results-recovered-v1.json'
READINESS = ROOT/'ai/strong/current-auction-confirmation-recovery-readiness-v1.json'
ADMISSION = ROOT/'ai/strong/current-auction-confirmation-recovery-admission-v1.json'
planning = base.planning
pilots = base.pilots
write_new, now = base.write_new, base.now


def source_checked():
    ready = read(READINESS)
    assert ready['ready_for_collection'] and ready['recovery_rule'] == recovery.RULE
    assert all(digest(ROOT/n) == h for n,h in ready['input_hashes'].items())
    return base.source_checked()


def admitted():
    source_checked(); a = read(ADMISSION)
    assert a['admitted'] and a['rule'] == recovery.RULE and a['no_game_reruns'] is True
    assert a['source_sha256'] == digest(SOURCE) and a['readiness_sha256'] == digest(READINESS)
    assert digest(ROOT/a['stopped_owner_state']) == a['stopped_owner_state_sha256']
    assert a['planned_games'] == 26880 and a['planned_jobs'] == 944 and a['max_active_jobs'] == 64
    assert digest(ROOT/a['initial_collection']) == a['initial_collection_sha256']
    initial = read(ROOT/a['initial_collection'])
    assert initial['verified_jobs'] == len(initial['jobs']) == 64
    assert {j['job_id'] for j in initial['jobs']} == set(a['original_handles'])
    assert all(recovery.complete_data(j) for j in initial['jobs'])
    assert all(digest(ROOT/n) == h for n,h in a['original_guard_hashes'].items())
    assert a['qualified'] is False and a['reserved_final_seeds_used'] is False
    return a


def verified_path(folder):
    ordinary = folder/'verified.json'; recovered = folder/'verified-terminal-recovery-v1.json'
    assert not (ordinary.exists() and recovered.exists()), 'Ambiguous original verification'
    return recovered if recovered.exists() else ordinary


def evaluation_directory(folder, job):
    return folder/'terminal-recovery-v1/evaluation' if job['stage']=='ERROR' else folder/'artifacts/job/evaluation'


def cached(folder, source, row):
    path = verified_path(folder)
    if not path.exists(): return None
    job = read(path); guard = read(folder/'launch.json')
    assert job['source_sha256'] == digest(SOURCE) and same(job['row'], row)
    assert job['guard_sha256'] == digest(folder/'launch.json') and job['job_id'] == guard['job_id']
    assert guard['stage']=='launched' and same(guard['row'],row) and guard['source_fingerprint']==object_hash(source)
    assert recovery.complete_data(job), 'Original data not completely verified'
    assert digest(folder/'artifacts/manifest.json') == job['evidence']['manifest_sha256']
    if job['stage']=='ERROR':
        assert path.name=='verified-terminal-recovery-v1.json'
        assert job['recovery_validator_sha256']==digest(recovery.__file__)
        assert digest(folder/'terminal-recovery-v1/review.json')==job['recovery_audit_sha256']
        assert same(read(folder/'terminal-recovery-v1/review.json'),job['review'])
        assert digest(evaluation_directory(folder,job)/'evaluation.json')==job['review']['recovery']['derived_evaluation_sha256']
    return job


def verify_result(folder, source, row, job):
    """Read-only full audit used again by the final comparison."""
    assert recovery.complete_data(job)
    if job['stage']=='ERROR':
        review = recovery.audit(folder/'artifacts', LOCAL/'source/artifact', source, row,
                                job['evidence'], folder/'terminal-recovery-v1')
        assert same(read(folder/'terminal-recovery-v1/review.json'),review)
        assert digest(folder/'terminal-recovery-v1/review.json') == job['recovery_audit_sha256']
    else:
        review = base.verify_artifacts(folder/'artifacts',source,row,job['evidence'])
    assert same(review,job['review']); return review


def collect():
    with base.exclusive_operation():
        return collect_originals()


def collect_originals():
    source=source_checked(); api=HfApi(); results=[]; states=[]
    for row in source['rows']:
        folder=OUT/row['name']
        if not (folder/'launch.json').exists(): continue
        saved=cached(folder,source,row)
        if saved is not None: results.append(saved); continue
        status=base.original_status(api,source,row); states.append(status)
        if status['stage'] in ('RUNNING','SCHEDULING'): continue
        logs='\n'.join(str(x) for x in api.fetch_job_logs(job_id=status['job_id'],follow=False))
        log=folder/'original-recovery-collection.log'
        if log.exists(): assert log.read_text()==logs, 'Inspect changed original log before retry'
        else: log.write_text(logs)
        receipts=[]
        for line in logs.splitlines():
            if not line.startswith('{'): continue
            try: receipt=json.loads(line)
            except json.JSONDecodeError: continue
            if set(receipt)=={'case','status','evidence'} and receipt['case']==row['name']: receipts.append(receipt)
        assert len(receipts)==1, 'Preserve missing/ambiguous original archive; never resubmit'
        evidence=receipts[0]['evidence']
        assert evidence['repo']=='coyotte508/powergrid-ai-germany-v1'
        assert evidence['archive_path']=='archives/'+row['name']+'.tgz' and evidence['remote_archive_verified']
        assert re.fullmatch('[a-f0-9]{40}',evidence['revision'])
        archive=Path(hf_hub_download(evidence['repo'],evidence['archive_path'],revision=evidence['revision']))
        assert digest(archive)==evidence['archive_sha256']
        if not (folder/'artifacts').exists(): extract_verified(archive,folder/'artifacts')
        extra={}
        if status['stage']=='COMPLETED':
            review=base.verify_artifacts(folder/'artifacts',source,row,evidence); destination=folder/'verified.json'
        elif status['stage']=='ERROR':
            failure=folder/'preserved-terminal-error-v1.json'
            if not failure.exists(): write_new(failure,{**status,'evidence':evidence,'original_failed':True})
            review=recovery.prepare(folder/'artifacts',LOCAL/'source/artifact',source,row,evidence,folder/'terminal-recovery-v1')
            extra={'recovery_validator_sha256':digest(recovery.__file__),
                   'recovery_audit_sha256':digest(folder/'terminal-recovery-v1/review.json')}
            destination=folder/'verified-terminal-recovery-v1.json'
        else:
            raise RuntimeError('Unadmitted terminal original; preserve without retry: '+status['stage'])
        saved={**status,'row':row,'verified':True,'review':review,'evidence':evidence,
               'source_sha256':digest(SOURCE),'guard_sha256':digest(folder/'launch.json'),**extra}
        assert recovery.complete_data(saved); write_new(destination,saved); results.append(saved)
        print(json.dumps({'verified':row['name'],'original_hf_stage':status['stage'],'games':review['games']}),flush=True)
    report={'checked_at':now(),'complete':len(results)==len(source['rows']),
        'verified_jobs':len(results),'expected_jobs':len(source['rows']),'jobs':results,
        'original_unverified_statuses':states,'source_sha256':digest(SOURCE),
        'recovered_original_errors':sum(j['stage']=='ERROR' for j in results),
        'recovery_rule':recovery.RULE,'qualified':False,'reserved_final_seeds_used':False}
    write(OUT/'collection-state-recovered-v1.json',report)
    if report['complete'] and not RESULT.exists():
        assert sum(j['review']['games'] for j in results)==26880;write_new(RESULT,report)
    return {k:report[k] for k in ('complete','verified_jobs','expected_jobs','recovered_original_errors')}


def launch(execute=False,limit=64):
    with base.exclusive_operation(): return launch_batch(execute,limit)


def launch_batch(execute=False,limit=64):
    source=source_checked();assert type(limit) is int and 1<=limit<=source['max_active_jobs']
    if not execute:return {'execute':False,'jobs':len(source['rows']),'games':26880}
    admitted()
    with (OUT/'.batch-launch.lock').open('a') as owner:
        fcntl.flock(owner,fcntl.LOCK_EX|fcntl.LOCK_NB)
        api=HfApi();pending=[];active=0;awaiting=[]
        for row in source['rows']:
            folder=OUT/row['name']
            if not (folder/'launch.json').exists():pending.append(row);continue
            if cached(folder,source,row) is not None:continue
            status=base.original_status(api,source,row)
            assert status['stage'] in ('RUNNING','SCHEDULING','COMPLETED','ERROR'), 'Inspect unadmitted original status'
            if status['stage'] in ('COMPLETED','ERROR'):awaiting.append(row['name'])
            else:active+=1
        if awaiting:
            return {'new_jobs':[],'active_jobs':active,'remaining_unsubmitted':len(pending),'awaiting_collection':awaiting}
        token=get_token();assert token;launched=[]
        for row in pending[:max(0,min(limit,source['max_active_jobs']-active))]:
            folder=OUT/row['name'];folder.mkdir(exist_ok=True)
            guard=base.launch_once(api,folder,source,row,token)
            item={'name':row['name'],'job_id':guard['job_id']};launched.append(item);print(json.dumps(item),flush=True)
        return {'new_jobs':launched,'active_jobs':active+len(launched),'remaining_unsubmitted':len(pending)-len(launched)}


if __name__=='__main__':
    p=argparse.ArgumentParser(__doc__);p.add_argument('operation',choices=['collect','launch']);p.add_argument('--execute',action='store_true');p.add_argument('--limit',type=int,default=64)
    args=p.parse_args();print(json.dumps(collect() if args.operation=='collect' else launch(args.execute,args.limit)),flush=True)
