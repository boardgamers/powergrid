"""Prepare, launch once and independently collect one fixed bucket-backed shard.

No broad dispatch, job retries, policy changes or qualification. The original v2
STOP and exact handles are preserved. HF responses are projected before saving.
"""
import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

from huggingface_hub import HfApi, get_token, hf_hub_download
from huggingface_hub.utils import get_session, hf_raise_for_status
import manage_current_auction_remaining_v2 as old
import collect_current_auction_retained_after_transport_failure_v2 as originals
import current_auction_bucket_worker_v3 as worker
import current_auction_bucket_collection_v3 as collection

ROOT,STRONG,ORIGINAL=old.ROOT,old.STRONG,old.ORIGINAL
NAME='pg-current-confirm-v1-pop-economic_capacity_v1-2p-00'
ATTEMPT=NAME.replace('pg-current-confirm-v1-','pg-current-bucket-v3-',1).replace('_','-')
PRE=ROOT/'ai/runs/current-auction-first-bucket-prepared-v3'
OUT=ROOT/'ai/runs/current-auction-first-bucket-hf-v3'
DECISION=STRONG/'current-auction-first-bucket-decision-v3.json'
SOURCE=STRONG/'current-auction-first-bucket-source-v3.json'
RESULT=STRONG/'current-auction-first-bucket-results-v3.json'
TEST_LOG=ROOT/'ai/runs/current-auction-first-bucket-manager-tests-v3-first.log'
TEST=STRONG/'test_current_auction_first_bucket_manager_v3.py'
REPO=old.first.REPO
IMAGE=old.first.IMAGE
WAITING,TERMINAL=old.WAITING,old.TERMINAL
read,digest,save,require=worker.read,worker.digest,worker.save,worker.require
now,exclusive,durable=old.now,old.exclusive,old.durable


def plan():
    original,rows=old.plan()
    row=next(r for r in rows if r['name']==NAME)
    registry=read(originals.REGISTRY)
    require(NAME not in {r['name'] for r in registry['records']} and row['players']==2
        and row['shard']['games']==16 and row['shard']['opponent']=='economic_capacity_v1',
        'Selected fixed row was already submitted or changed')
    require(digest(old.OUT/'STOP.json')=='07a47d46a5cfb7e36b217f82b33632dd878b3b9deb56120cb8353db12e84ed53',
        'Original dispatch STOP changed')
    return original,row


def bootstrap():
    marker='python -u -B /workspace/recovery-supervisor/current_auction_resource_job_v2.py'
    text=old.first.bootstrap();require(text.count(marker)==1,'Frozen bootstrap structure changed')
    return text.split(marker)[0]+r'''python -u -B /workspace/recovery-supervisor/current_auction_bucket_worker_v3.py \
 --bundle /workspace/recovery-supervisor --bundle-manifest-sha256 "$SUPERVISOR_MANIFEST_SHA256" \
 --source /workspace/source --output "/workspace/recovery-output/$BUCKET_ATTEMPT" --execute
'''


def code_paths():
    return [Path(__file__),Path(worker.__file__),Path(collection.__file__),TEST,
        *[Path(module.__file__) for module in worker.CODE.values()]]


def prepare():
    require(not any(p.exists() for p in (PRE,OUT,DECISION,SOURCE,RESULT)),'Inspect prior preparation/attempt')
    original,row=plan();preflight=read(STRONG/'current-auction-bucket-worker-preflight-v3.json')
    evidence=read(STRONG/'current-auction-bucket-worker-evidence-v3.json')
    require(preflight['passed'] and preflight['new_tests']==48 and evidence['archive']['remote_archive_verified'],
        'Worker/collector preparation missing')
    require(all(digest(STRONG/name)==sha for name,sha in preflight['code_sha256'].items()),'Preflight code changed')
    require(evidence['worker_sha256']==digest(worker.__file__) and evidence['collector_sha256']==digest(collection.__file__),
        'Archived worker/collector changed')
    require('Ran 14 tests' in TEST_LOG.read_text() and TEST_LOG.read_text().rstrip().endswith('OK'),'Manager tests incomplete')
    subprocess.run(['bash','-n'],input=bootstrap(),text=True,check=True)
    control={'version':3,'scope':'fixed_confirmation_bucket_retention','attempt_id':ATTEMPT,'original_name':NAME,
        'original_row_sha256':worker.base.object_hash(row),'prior_failed_attempts':[],'reason':'never_submitted',
        'allocation':worker.ALLOCATION,'transport':worker.TRANSPORT,'source_descriptor_sha256':worker.base.SOURCE_SHA}
    decision={'created_at':now(),'status':'transport_recovery_recorded_execution_not_admitted',
        'strength_outcomes_used_for_decision':False,'reserved_final_seeds_used':False,
        'source_descriptor_sha256':worker.base.SOURCE_SHA,'allocation':worker.ALLOCATION,'transport':worker.TRANSPORT,
        'rows':[{'name':NAME,**{k:control[k] for k in ('original_row_sha256','prior_failed_attempts','reason','attempt_id')}}],
        'purpose':'First untouched two-player fixed confirmation row; prove live bucket retention, independent audit and versioned collection before broader execution.',
        'original_v2_stop_sha256':digest(old.OUT/'STOP.json'),'original_v2_registry_sha256':digest(originals.REGISTRY),
        'original_failed_attempts_preserved':True,'failed_jobs_to_resubmit':0,'admitted_later_only_after_actual_preparation':True,
        'jobs':1,'games':16,'max_active_including_originals':64,'broad_remaining_dispatch_admitted':False,
        'worker_evidence_descriptor_sha256':digest(STRONG/'current-auction-bucket-worker-evidence-v3.json'),
        'preflight_only':False,'production_execution_admitted':False}
    save(DECISION,decision);PRE.mkdir();bundle=PRE/'bundle';bundle.mkdir()
    for name,module in worker.CODE.items():shutil.copyfile(module.__file__,bundle/name)
    shutil.copyfile(worker.__file__,bundle/worker.ENTRY)
    shutil.copyfile(STRONG/'current-auction-grid-source-v1.json',bundle/'original-source.json')
    shutil.copyfile(DECISION,bundle/'decision.json');control['decision_sha256']=digest(DECISION)
    save(bundle/'control.json',control);save(bundle/'manifest.json',{p.name:digest(p) for p in sorted(bundle.iterdir())})
    config=worker.inspect(bundle,digest(bundle/'manifest.json'),ORIGINAL,PRE/'NEVER-EXECUTED')
    command=[sys.executable,'-u','-B',str(bundle/worker.ENTRY),'--bundle',str(bundle),'--bundle-manifest-sha256',
        digest(bundle/'manifest.json'),'--source',str(ORIGINAL),'--output',str(PRE/'NEVER-EXECUTED')]
    completed=subprocess.run(command,capture_output=True,text=True,check=True)
    require(not completed.stderr and not (PRE/'NEVER-EXECUTED').exists(),'Unexpected preflight execution')
    (PRE/'actual-cli-validation.log').write_text(completed.stdout)
    actual=json.loads(completed.stdout);require(actual['valid'] and actual['execute'] is False and actual['games']==16,'Invalid CLI probe')
    save(PRE/'preflight.json',{'passed':True,'actual_validation':actual,'command_sha256':worker.base.object_hash(command),
        'decision_sha256':digest(DECISION),'manager_tests_sha256':digest(TEST_LOG),'new_jobs':0,'new_games':0})
    metadata=PRE/'current-auction-first-bucket-preparation-evidence-v3';metadata.mkdir()
    paths=set(code_paths()+[TEST_LOG,DECISION,PRE/'preflight.json',PRE/'actual-cli-validation.log',
        STRONG/'current-auction-bucket-worker-evidence-v3.json',STRONG/'current-auction-bucket-worker-preflight-v3.json'])
    paths.update(bundle.iterdir())
    for path in sorted(paths):
        dest=metadata/path.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,dest)
        require(digest(path)==digest(dest),'Preparation changed during copy')
    save(metadata/'manifest.json',{str(p.relative_to(metadata)):digest(p) for p in sorted(metadata.rglob('*')) if p.is_file()})
    api=HfApi();require(api.model_info(worker.base.retention.REPO).private,'Private preparation required')
    require(not api.file_exists(worker.base.retention.REPO,'archives/'+metadata.name+'.tgz'),'Inspect prior preparation upload')
    save(PRE/'evidence-upload-intent.json',{'manifest_sha256':digest(metadata/'manifest.json'),'automatic_retries':False})
    archived=old.first.upload_evidence(metadata);save(PRE/'evidence-upload-receipt.json',archived)
    admission={'passed':True,'scope':control['scope'],'core_files_sha256':config['core_files_sha256'],
        'control_sha256':digest(bundle/'control.json'),'decision_sha256':digest(DECISION),
        'source_descriptor_sha256':worker.base.SOURCE_SHA,'preflight_sha256':digest(PRE/'preflight.json'),
        'test_log_sha256':digest(TEST_LOG),'preparation_archive_sha256':archived['archive_sha256'],
        'new_jobs':0,'new_games':0,'qualified':False,'reserved_final_seeds_used':False}
    save(bundle/'admission.json',admission);(bundle/'manifest.json').unlink()
    save(bundle/'manifest.json',{p.name:digest(p) for p in sorted(bundle.iterdir())})
    manifest_sha=digest(bundle/'manifest.json')
    reference=collection.reference_configuration(bundle,manifest_sha,ORIGINAL)
    require(reference['control']==control and reference['row']==row,'Actual admitted command differs')
    archive=worker.archives.archive_directory(bundle)
    target=PRE/'strong-source-current-auction-first-bucket-v3.tgz';archive.rename(target)
    check=old.first.extract_verified(target,PRE/'archive-check');require(check['manifest_sha256']==manifest_sha,'Source extraction differs')
    prepared={'created_at':now(),'archive':target.name,'sha256':digest(target),'manifest_sha256':manifest_sha,
        'admission_sha256':digest(bundle/'admission.json'),'core_files_sha256':config['core_files_sha256'],
        'decision_sha256':digest(DECISION),'row_sha256':worker.base.object_hash(row),'preparation_evidence':archived,
        'preflight_sha256':digest(PRE/'preflight.json'),'tests_sha256':digest(TEST_LOG),'bootstrap_sha256':old.first.sha_text(bootstrap()),
        'code_hashes':{str(p.relative_to(ROOT)):digest(p) for p in code_paths()},
        'jobs':1,'games':16,'attempt_id':ATTEMPT,'allocation':worker.ALLOCATION,'transport':worker.TRANSPORT,
        'remaining_rows_admitted':False,'qualified':False,'reserved_final_seeds_used':False}
    save(PRE/'prepared.json',prepared)
    return {'prepared':True,'jobs':1,'games':16,'attempt_id':ATTEMPT,'preparation_evidence':archived}


def prepared():
    _,row=plan();p=read(PRE/'prepared.json')
    require(p['jobs']==1 and p['games']==16 and p['attempt_id']==ATTEMPT and not p['remaining_rows_admitted'],
        'Only the first fixed bucket row is admitted')
    require(p['row_sha256']==worker.base.object_hash(row) and p['decision_sha256']==digest(DECISION)
        and p['sha256']==digest(PRE/p['archive']) and p['tests_sha256']==digest(TEST_LOG)
        and p['preflight_sha256']==digest(PRE/'preflight.json'),'Prepared input changed')
    require(p['allocation']==worker.ALLOCATION and p['transport']==worker.TRANSPORT
        and p['bootstrap_sha256']==old.first.sha_text(bootstrap())
        and all(digest(ROOT/name)==sha for name,sha in p['code_hashes'].items()),'Prepared code/settings changed')
    expected=collection.reference_configuration(PRE/'bundle',p['manifest_sha256'],ORIGINAL)
    require(expected['core_files_sha256']==p['core_files_sha256'] and expected['admission_sha256']==p['admission_sha256'],
        'Prepared admission differs')
    return p


def upload():
    p=prepared()
    with exclusive(PRE,'upload'):
        require(not SOURCE.exists() and not (PRE/'source-upload-intent.json').exists(),'Inspect previous source upload')
        api=HfApi();require(api.dataset_info(REPO).private,'Private source required')
        require(not api.file_exists(REPO,p['archive'],repo_type='dataset'),'Inspect existing source')
        save(PRE/'source-upload-intent.json',{'archive':p['archive'],'sha256':p['sha256'],'automatic_retries':False})
        commit=api.upload_file(repo_id=REPO,repo_type='dataset',path_or_fileobj=PRE/p['archive'],path_in_repo=p['archive'])
        receipt={'repo':REPO,'revision':commit.oid,'archive':p['archive'],'sha256':p['sha256']}
        save(PRE/'source-upload-receipt.json',receipt)
        require(digest(hf_hub_download(REPO,p['archive'],repo_type='dataset',revision=commit.oid))==p['sha256'],'Uploaded source differs')
        source={**receipt,'manifest_sha256':p['manifest_sha256'],'preparation_sha256':digest(PRE/'prepared.json'),'remote_archive_verified':True}
        save(SOURCE,source);return source


def source_checked():
    p=prepared();s=read(SOURCE)
    require(s['repo']==REPO and s['remote_archive_verified'] is True and re.fullmatch('[a-f0-9]{40}',s['revision'])
        and s['preparation_sha256']==digest(PRE/'prepared.json')
        and all(s[k]==p[k] for k in ('archive','sha256','manifest_sha256')),'Published source differs')
    return s


def public_environment(source):
    original,row=plan()
    return {'SOURCE_ARCHIVE':original['archive'],'SOURCE_REVISION':original['revision'],
        'SOURCE_SHA256':original['sha256'],'SOURCE_MANIFEST_SHA256':original['source_manifest_sha256'],
        'PROTOCOL_SHA256':original['protocol_sha256'],'PILOT_JOB':row['job'],'PILOT_NAME':NAME,
        'HF_HUB_DISABLE_PROGRESS_BARS':'1','PYTHONDONTWRITEBYTECODE':'1','BUCKET_ATTEMPT':ATTEMPT,
        'SUPERVISOR_ARCHIVE':source['archive'],'SUPERVISOR_REVISION':source['revision'],
        'SUPERVISOR_SHA256':source['sha256'],'SUPERVISOR_MANIFEST_SHA256':source['manifest_sha256']}


def binding(source):
    _,row=plan()
    return {'source':source,'original_name':NAME,'original_row_sha256':worker.base.object_hash(row),'attempt_id':ATTEMPT,
        'allocation':worker.ALLOCATION,'transport':worker.TRANSPORT,'prior_failed_attempts':[],'automatic_job_retries':False}


def checked_guard(directory,source):
    expected=binding(source);guard=read(directory/'launch.json');intent=read(directory/'launch-intent.json')
    require(all(guard.get(k)==v and intent.get(k)==v for k,v in expected.items())
        and re.fullmatch('[a-f0-9]{24}',guard['job_id']),'Launch binding differs')
    return guard


def launch_once(api,directory,source,token):
    with exclusive(directory,'launch'):
        if (directory/'launch.json').exists():return checked_guard(directory,source)
        require(not (directory/'launch-intent.json').exists(),'Unresolved launch intent; never resubmit')
        expected=binding(source);save(directory/'launch-intent.json',{**expected,'created_at':now()})
        job=api.run_job(image=IMAGE,command=['bash','-lc',bootstrap()],env=public_environment(source),
            secrets={'HF_TOKEN':token},flavor='cpu-upgrade',timeout='24h',
            labels={'name':ATTEMPT,'project':'powergrid-ai','stage':'current-auction-first-bucket-v3'})
        require(re.fullmatch('[a-f0-9]{24}',job.id),'Unknown handle; preserve launch intent')
        guard={**expected,'job_id':job.id,'created_at':now()};save(directory/'launch.json',guard);return guard


def bind_remote(raw,guard,source):
    require(all(guard.get(k)==v for k,v in binding(source).items()) and raw['id']==guard['job_id'],'HF handle binding differs')
    require(raw['dockerImage']==IMAGE and raw['flavor']=='cpu-upgrade' and raw['timeout']==86400,'HF allocation differs')
    require(raw['command']==['bash','-lc',bootstrap()] and raw['arguments']==[]
        and raw['environment']==public_environment(source) and raw['labels']['name']==ATTEMPT,'HF command/source differs')
    require(raw['status']['stage'] in WAITING|TERMINAL,'Unknown HF stage')
    return {'checked_at':now(),'job_id':guard['job_id'],'stage':raw['status']['stage'],'attempt_id':ATTEMPT,
        'original_name':NAME,'timeout_seconds':86400,'flavor':'cpu-upgrade','image':IMAGE,
        'bootstrap_sha256':old.first.sha_text(bootstrap()),'environment_sha256':worker.base.object_hash(public_environment(source)),
        'public_configuration_verified':True}


def check(source=None):
    source=source or source_checked();guard=checked_guard(OUT,source);api=HfApi()
    response=get_session().get(f'{api.endpoint}/api/jobs/{old.first.NAMESPACE}/{guard["job_id"]}',headers=api._build_hf_headers(),timeout=60)
    hf_raise_for_status(response);status=bind_remote(response.json(),guard,source)
    durable(OUT/'checks'/(status['checked_at'].replace(':','-')+'.json'),status);return status


def launch(execute=False):
    source=source_checked()
    if not execute:return {'execute':False,'admitted_games':16,'attempt_id':ATTEMPT}
    with exclusive(old.OUT,'cycle'):
        if not (OUT/'launch.json').exists():
            old_source,rows,records=originals.original_bindings();api=HfApi();active=0
            for item in records:
                status=old.check_one(api,old.OUT/'jobs'/item['attempt_id'],old_source,rows[item['name']])
                active+=status['stage'] in WAITING
            require(active<64,'Original jobs fill active capacity')
            worker.transport.BucketTransport(api).private(worker.archives.BUCKET)
            token=get_token();require(bool(token),'HF credentials unavailable')
            launch_once(api,OUT,source,token)
        return check(source)


def read_final(log):
    values=[]
    for line in Path(log).read_text().splitlines():
        try:value=json.loads(line)
        except (ValueError,TypeError):continue
        if isinstance(value,dict) and 'bucket_final_evidence' in value:values.append(value)
    require(len(values)==1 and values[0]['attempt_id']==ATTEMPT,'Missing/ambiguous final bucket receipt')
    evidence=values[0]['bucket_final_evidence'];worker.archives.checked_receipt(evidence,ATTEMPT+'-final')
    return evidence


def collected_tree(evidence,name,directory,api):
    if directory.exists():
        worker.archives.checked_receipt(evidence,name)
        worker.base.tree(directory,'manifest.json',evidence['manifest_sha256']);return directory
    return worker.archives.download_archive(evidence,name,directory,api)


def collect():
    source=source_checked();status=check(source)
    if status['stage'] in WAITING:return status
    with exclusive(old.OUT,'cycle'),exclusive(OUT,'collection'):
        if RESULT.exists():
            result=read(RESULT)
            require(result['job_id']==status['job_id'] and result['source_descriptor_sha256']==digest(SOURCE)
                and result['manager_sha256']==digest(__file__) and result['collector_sha256']==digest(collection.__file__),
                'Saved result binding differs')
            return {'verified':True,'games':result['games'],'job_id':result['job_id']}
        api=HfApi();log=OUT/'original.log'
        if not log.exists():log.write_text('\n'.join(str(line) for line in api.fetch_job_logs(job_id=status['job_id'],follow=False)))
        terminal={**status,'log_sha256':digest(log)}
        if not (OUT/'terminal.json').exists():save(OUT/'terminal.json',terminal)
        else:require(all(read(OUT/'terminal.json')[k]==terminal[k] for k in ('job_id','stage','log_sha256')),'Terminal evidence changed')
        evidence=read_final(log);folder=collected_tree(evidence,ATTEMPT+'-final',OUT/'envelope',api)
        require(status['stage']=='COMPLETED','Failed job preserved; no retry')
        def reader(receipt):
            name=receipt['path'].split('/')[1]
            return collected_tree(receipt,name,OUT/'checkpoints'/name,api)
        raw_review=OUT/'raw-review.json'
        if raw_review.exists():
            audit=read(raw_review)
            require(audit['envelope_evidence']==evidence and audit['manager_sha256']==digest(__file__)
                and audit['collector_sha256']==digest(collection.__file__) and audit['source_descriptor_sha256']==digest(SOURCE)
                and audit['job_id']==status['job_id'] and audit['games']==16 and audit['verified'] is True,'Saved raw audit differs')
        else:
            audit=collection.audit_envelope(folder,evidence,PRE/'bundle',source['manifest_sha256'],ORIGINAL,reader)
            audit.update(job_id=status['job_id'],manager_sha256=digest(__file__),collector_sha256=digest(collection.__file__),
                source_descriptor_sha256=digest(SOURCE))
            save(raw_review,audit)
        # One versioned archive includes the exact worker envelope, all original
        # checkpoint trees and independent review. No future audit depends solely
        # on mutable bucket objects; the archived worker manifests stay unchanged.
        package=OUT/(ATTEMPT+'-collected');receipt_path=OUT/'promotion-receipt.json';intent=OUT/'promotion-intent.json'
        if not receipt_path.exists():
            require(not package.exists() and not intent.exists(),'Inspect prior promotion intent/outcome')
            package.mkdir();worker.base.snapshot_tree(folder,package/'envelope')
            checkpoint_evidence=[]
            for checkpoint in audit['checkpoint_archives']:
                item=checkpoint['evidence'];name=item['path'].split('/')[1];tree=reader(item)
                worker.base.snapshot_tree(tree,package/'checkpoints'/name);checkpoint_evidence.append(item)
            shutil.copyfile(raw_review,package/'raw-review.json')
            save(package/'origin.json',{'job_id':status['job_id'],'terminal':read(OUT/'terminal.json'),
                'launch_guard_sha256':digest(OUT/'launch.json'),'source':source,'bucket_envelope':evidence,
                'bucket_checkpoints':checkpoint_evidence,'new_games':0,'qualified':False})
            save(package/'manifest.json',{str(p.relative_to(package)):digest(p) for p in sorted(package.rglob('*')) if p.is_file()})
            require(api.model_info(worker.base.retention.REPO).private,'Private final archive required')
            require(not api.file_exists(worker.base.retention.REPO,'archives/'+package.name+'.tgz'),'Inspect existing final archive')
            save(intent,{'manifest_sha256':digest(package/'manifest.json'),'raw_review_sha256':digest(raw_review),'automatic_retries':False})
            promoted=old.first.upload_evidence(package);save(receipt_path,promoted)
        promoted=read(receipt_path);worker.base.tree(package,'manifest.json',promoted['manifest_sha256'])
        require(promoted['remote_archive_verified'] and read(intent)['raw_review_sha256']==digest(raw_review),'Promotion proof differs')
        result={**audit,'terminal':read(OUT/'terminal.json'),'launch_guard_sha256':digest(OUT/'launch.json'),
            'versioned_collection_archive':promoted,'versioned_archive_pending':False,
            'remaining_rows_admitted':False,'qualified':False,'reserved_final_seeds_used':False}
        save(RESULT,result);return {'verified':True,'games':16,'job_id':status['job_id'],'versioned_archive':promoted}


if __name__=='__main__':
    p=argparse.ArgumentParser(__doc__);p.add_argument('operation',choices=('prepare','upload','check','launch','collect'))
    p.add_argument('--execute',action='store_true');args=p.parse_args()
    result=launch(args.execute) if args.operation=='launch' else globals()[args.operation]()
    print(json.dumps(result),flush=True)
