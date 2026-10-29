"""Bounded first executions of the 258 untouched confirmation rows.

Uses the completed, independently audited bucket worker unchanged. Prior failed
jobs stay failed and outside this grant. No automatic job retries or statistics.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

from huggingface_hub import HfApi, get_token, hf_hub_download
from huggingface_hub.utils import get_session, hf_raise_for_status
import manage_current_auction_first_bucket_v3 as first
import current_auction_bucket_pack_v3 as packer

old, originals, worker, collection = first.old, first.originals, first.worker, first.collection
ROOT, STRONG, ORIGINAL = first.ROOT, first.STRONG, first.ORIGINAL
PRE=ROOT/'ai/runs/current-auction-bucket-remaining-prepared-v3'
OUT=ROOT/'ai/runs/current-auction-bucket-remaining-hf-v3'
DECISION=STRONG/'current-auction-bucket-remaining-decision-v3.json'
SOURCE=STRONG/'current-auction-bucket-remaining-source-v3.json'
PREFLIGHT=STRONG/'current-auction-bucket-remaining-preflight-v3.json'
PREP_EVIDENCE=STRONG/'current-auction-bucket-remaining-preparation-evidence-v3.json'
TEST=STRONG/'test_current_auction_bucket_remaining_v3.py'
TEST_LOG=ROOT/'ai/runs/current-auction-bucket-remaining-tests-v3-first.log'
FIRST_RESULT_SHA='c596072e97c8ffda2969697c8e783fd41541a3807f7925325bfb9586a8c3fa5a'
STOP_SHA='07a47d46a5cfb7e36b217f82b33632dd878b3b9deb56120cb8353db12e84ed53'
MAX_ACTIVE=64
read,digest,save,require=first.read,first.digest,first.save,first.require
now,exclusive,durable=first.now,first.exclusive,first.durable
WAITING,TERMINAL=first.WAITING,first.TERMINAL


def attempt(name):return name.replace('pg-current-confirm-v1-','pg-current-bucket-v3-',1).replace('_','-')


def plan():
    original,rows=old.plan();registry=read(originals.REGISTRY)
    require(digest(first.RESULT)==FIRST_RESULT_SHA,'Completed first bucket audit changed')
    result=read(first.RESULT)
    require(result['verified'] is True and result['games']==16 and result['terminal']['stage']=='COMPLETED'
        and result['versioned_archive_pending'] is False and result['versioned_collection_archive']['remote_archive_verified'] is True
        and result['source_descriptor_sha256']==digest(first.SOURCE)
        and result['manager_sha256']==digest(first.__file__) and result['collector_sha256']==digest(collection.__file__),
        'First bucket execution is not fully audited and archived')
    require(registry['submitted_jobs']==64 and registry['submitted_games']==1280
        and digest(old.OUT/'STOP.json')==STOP_SHA,'Original registry/STOP changed')
    excluded={r['name'] for r in registry['records']}|{first.NAME}
    selected=[r for r in rows if r['name'] not in excluded]
    require(len(selected)==len({attempt(r['name']) for r in selected})==258
        and sum(r['shard']['games'] for r in selected)==5804,'Untouched fixed coverage differs')
    return original,selected


def bootstrap():
    marker='python -u -B /workspace/recovery-supervisor/current_auction_resource_job_v2.py'
    previous=old.first.bootstrap();require(previous.count(marker)==1,'Frozen bootstrap changed')
    return previous.split(marker)[0]+r'''python -u -B /workspace/recovery-supervisor/current_auction_bucket_pack_v3.py \
 --pack /workspace/recovery-supervisor --pack-manifest-sha256 "$SUPERVISOR_MANIFEST_SHA256" \
 --name "$PILOT_NAME" --destination /workspace/selected-bucket-bundle \
 --source /workspace/source --output "/workspace/recovery-output/$BUCKET_ATTEMPT" --execute
'''


def code_paths():
    return [Path(__file__),Path(packer.__file__),Path(first.__file__),Path(collection.__file__),
        Path(worker.__file__),TEST,*[Path(module.__file__) for module in worker.CODE.values()]]


def manifest(folder):
    path=folder/'manifest.json';path.unlink(missing_ok=True)
    save(path,{str(p.relative_to(folder)):digest(p) for p in sorted(folder.rglob('*')) if p.is_file()})
    return digest(path)


def prepare():
    require(not any(p.exists() for p in (PRE,OUT,DECISION,SOURCE,PREFLIGHT,PREP_EVIDENCE)),
        'Inspect prior preparation/submission before retry')
    original,rows=plan();first.source_checked()
    test_text=TEST_LOG.read_text()
    require('Ran 25 tests' in test_text and test_text.rstrip().endswith('OK'),'Manager/pack tests incomplete')
    subprocess.run(['bash','-n'],input=bootstrap(),text=True,check=True)
    decision={'created_at':now(),'status':'transport_recovery_recorded_execution_not_admitted',
        'strength_outcomes_used_for_decision':False,'reserved_final_seeds_used':False,
        'source_descriptor_sha256':worker.base.SOURCE_SHA,'allocation':worker.ALLOCATION,'transport':worker.TRANSPORT,
        'rows':[{'name':r['name'],'original_row_sha256':worker.base.object_hash(r),'prior_failed_attempts':[],
            'reason':'never_submitted','attempt_id':attempt(r['name'])} for r in rows],
        'purpose':'Complete the untouched fixed confirmation rows using the fully audited bucket worker unchanged.',
        'original_v2_stop_sha256':STOP_SHA,'original_v2_registry_sha256':digest(originals.REGISTRY),
        'first_bucket_result_sha256':FIRST_RESULT_SHA,'jobs':258,'games':5804,'max_active_including_originals':MAX_ACTIVE,
        'automatic_job_retries':False,'prior_failed_attempts_preserved':True,'failed_jobs_to_resubmit':0,
        'failed_job_recovery_requires_separate_decision':True,'preflight_only':False,'production_execution_admitted':False}
    save(DECISION,decision);PRE.mkdir();pack=PRE/'pack';pack.mkdir()
    for name,module in worker.CODE.items():shutil.copyfile(module.__file__,pack/name)
    shutil.copyfile(worker.__file__,pack/worker.ENTRY);shutil.copyfile(packer.__file__,pack/Path(packer.__file__).name)
    shutil.copyfile(STRONG/'current-auction-grid-source-v1.json',pack/'original-source.json')
    shutil.copyfile(DECISION,pack/'decision.json')
    common={name:digest(pack/name) for name in packer.COMMON};validation=[]
    # Validate every actual spec/policy/contract with the frozen worker, before admission.
    for row in rows:
        name=row['name'];dest=PRE/'validation'/attempt(name);dest.mkdir(parents=True)
        for filename in packer.COMMON:shutil.copyfile(pack/filename,dest/filename)
        control={'version':3,'scope':'fixed_confirmation_bucket_retention','attempt_id':attempt(name),
            'original_name':name,'original_row_sha256':worker.base.object_hash(row),'prior_failed_attempts':[],
            'reason':'never_submitted','allocation':worker.ALLOCATION,'transport':worker.TRANSPORT,
            'source_descriptor_sha256':worker.base.SOURCE_SHA,'decision_sha256':digest(DECISION)}
        save(dest/'control.json',control);sha=manifest(dest)
        checked=worker.inspect(dest,sha,ORIGINAL,PRE/'NEVER-EXECUTED'/attempt(name))
        validation.append({'name':name,'players':row['players'],'games':row['shard']['games'],
            'core_files_sha256':checked['core_files_sha256'],'control_sha256':digest(dest/'control.json')})
    preflight={'passed':True,'created_at':now(),'rows':validation,'actual_original_specs_validated':258,
        'games':5804,'first_bucket_result_sha256':FIRST_RESULT_SHA,'decision_sha256':digest(DECISION),
        'code_hashes':{str(p.relative_to(ROOT)):digest(p) for p in code_paths()},'test_log_sha256':digest(TEST_LOG),
        'new_jobs':0,'new_games':0,'qualified':False,'reserved_final_seeds_used':False}
    save(PREFLIGHT,preflight)
    evidence_dir=PRE/'current-auction-bucket-remaining-preparation-evidence-v3';evidence_dir.mkdir()
    paths=set(code_paths()+[TEST_LOG,DECISION,PREFLIGHT,first.RESULT,first.SOURCE,originals.REGISTRY,old.OUT/'STOP.json'])
    paths.update(pack.iterdir())
    for path in sorted(paths):
        target=evidence_dir/path.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(path,target);require(digest(path)==digest(target),'Preparation input changed')
    manifest(evidence_dir);api=HfApi()
    require(api.model_info(worker.base.retention.REPO).private,'Private evidence required')
    require(not api.file_exists(worker.base.retention.REPO,'archives/'+evidence_dir.name+'.tgz'),'Inspect prior preparation upload')
    save(PRE/'evidence-upload-intent.json',{'manifest_sha256':digest(evidence_dir/'manifest.json'),'automatic_retries':False})
    evidence=old.first.upload_evidence(evidence_dir);save(PRE/'evidence-upload-receipt.json',evidence)
    save(PREP_EVIDENCE,{'archive':evidence,'preflight_sha256':digest(PREFLIGHT),'tests':25,
        'first_bucket_result_sha256':FIRST_RESULT_SHA,'new_jobs':0,'qualified':False})
    index={'version':3,'scope':'untouched_fixed_confirmation_rows','automatic_job_retries':False,'rows':{}}
    for item in validation:
        name=item['name'];dest=PRE/'validation'/attempt(name)
        admission={'passed':True,'scope':'fixed_confirmation_bucket_retention',
            'core_files_sha256':item['core_files_sha256'],'control_sha256':item['control_sha256'],
            'decision_sha256':digest(DECISION),'source_descriptor_sha256':worker.base.SOURCE_SHA,
            'preflight_sha256':digest(PREFLIGHT),'test_log_sha256':digest(TEST_LOG),
            'preparation_archive_sha256':evidence['archive_sha256'],
            'new_jobs':0,'new_games':0,'qualified':False,'reserved_final_seeds_used':False}
        save(dest/'admission.json',admission);sha=manifest(dest)
        target=pack/'rows'/attempt(name);target.mkdir(parents=True)
        for filename in packer.ROW_FILES:shutil.copyfile(dest/filename,target/filename)
        index['rows'][name]={'attempt_id':attempt(name),'bundle_manifest_sha256':sha}
    save(pack/'index.json',index);pack_sha=manifest(pack);checks=[]
    for n in (2,3,5,6):
        row=next(r for r in rows if r['players']==n);dest=PRE/'actual-cli'/attempt(row['name'])
        command=[sys.executable,'-u','-B',str(pack/Path(packer.__file__).name),'--pack',str(pack),
            '--pack-manifest-sha256',pack_sha,'--name',row['name'],'--destination',str(dest),
            '--source',str(ORIGINAL),'--output',str(PRE/'NEVER-EXECUTED'/attempt(row['name']))]
        completed=subprocess.run(command,capture_output=True,text=True,check=True)
        require(not completed.stderr and not (PRE/'NEVER-EXECUTED').exists(),'Unexpected validation execution')
        value=json.loads(completed.stdout);require(value['valid'] and value['execute'] is False,'Pack CLI executed')
        config=collection.reference_configuration(dest,index['rows'][row['name']]['bundle_manifest_sha256'],ORIGINAL)
        checks.append({'name':row['name'],'players':n,'validation':value,'command_sha256':worker.base.object_hash(config['command'])})
    save(PRE/'actual-admitted-validation.json',checks)
    archive=worker.archives.archive_directory(pack);target=PRE/'strong-source-current-auction-bucket-remaining-v3.tgz';archive.rename(target)
    proof=old.first.extract_verified(target,PRE/'archive-check');require(proof['manifest_sha256']==pack_sha,'Archive changed')
    save(PRE/'prepared.json',{'created_at':now(),'archive':target.name,'sha256':digest(target),'manifest_sha256':pack_sha,
        'admitted_jobs':258,'admitted_games':5804,'max_active':MAX_ACTIVE,'first_bucket_result_sha256':FIRST_RESULT_SHA,
        'preparation_evidence':evidence,'decision_sha256':digest(DECISION),'preflight_sha256':digest(PREFLIGHT),
        'test_log_sha256':digest(TEST_LOG),'code_hashes':preflight['code_hashes'],'bootstrap_sha256':old.first.sha_text(bootstrap()),
        'actual_admitted_validation_sha256':digest(PRE/'actual-admitted-validation.json'),
        'rows':{r['name']:worker.base.object_hash(r) for r in rows},'qualified':False,'reserved_final_seeds_used':False})
    return {'prepared':True,'jobs':258,'games':5804,'archive':evidence}


def prepared():
    _,rows=plan();p=read(PRE/'prepared.json')
    require(p['admitted_jobs']==258 and p['admitted_games']==5804 and p['max_active']==MAX_ACTIVE
        and p['first_bucket_result_sha256']==FIRST_RESULT_SHA and p['decision_sha256']==digest(DECISION)
        and p['preflight_sha256']==digest(PREFLIGHT) and p['test_log_sha256']==digest(TEST_LOG)
        and p['actual_admitted_validation_sha256']==digest(PRE/'actual-admitted-validation.json')
        and p['bootstrap_sha256']==old.first.sha_text(bootstrap()),'Preparation inputs changed')
    require(all(digest(ROOT/name)==sha for name,sha in p['code_hashes'].items())
        and p['rows']=={r['name']:worker.base.object_hash(r) for r in rows}
        and p['sha256']==digest(PRE/p['archive']),'Prepared code/source/rows changed')
    worker.base.tree(PRE/'pack','manifest.json',p['manifest_sha256']);return p


def upload():
    p=prepared()
    with exclusive(PRE,'upload'):
        require(not SOURCE.exists() and not (PRE/'source-upload-intent.json').exists(),'Inspect previous source upload')
        api=HfApi();require(api.dataset_info(first.REPO).private,'Private source required')
        require(not api.file_exists(first.REPO,p['archive'],repo_type='dataset'),'Inspect existing source')
        save(PRE/'source-upload-intent.json',{'archive':p['archive'],'sha256':p['sha256'],'automatic_retries':False})
        commit=api.upload_file(repo_id=first.REPO,repo_type='dataset',path_or_fileobj=PRE/p['archive'],path_in_repo=p['archive'])
        receipt={'repo':first.REPO,'revision':commit.oid,'archive':p['archive'],'sha256':p['sha256']}
        save(PRE/'source-upload-receipt.json',receipt)
        require(digest(hf_hub_download(first.REPO,p['archive'],repo_type='dataset',revision=commit.oid))==p['sha256'],'Uploaded source differs')
        source={**receipt,'manifest_sha256':p['manifest_sha256'],'preparation_sha256':digest(PRE/'prepared.json'),'remote_archive_verified':True}
        save(SOURCE,source);return source


def source_checked():
    p=prepared();s=read(SOURCE)
    require(s['repo']==first.REPO and s['remote_archive_verified'] is True and re.fullmatch('[a-f0-9]{40}',s['revision'])
        and s['preparation_sha256']==digest(PRE/'prepared.json')
        and all(s[k]==p[k] for k in ('archive','sha256','manifest_sha256')),'Published source differs')
    return s


def bundle_for(row,source):
    name=row['name'];entry=read(PRE/'pack/index.json')['rows'][name];dest=PRE/'selected'/attempt(name)
    if not dest.exists():packer.materialize(PRE/'pack',source['manifest_sha256'],name,dest)
    worker.base.tree(dest,'manifest.json',entry['bundle_manifest_sha256'])
    return dest,entry['bundle_manifest_sha256']


def public_environment(source,row):
    original,_=plan()
    return {'SOURCE_ARCHIVE':original['archive'],'SOURCE_REVISION':original['revision'],
        'SOURCE_SHA256':original['sha256'],'SOURCE_MANIFEST_SHA256':original['source_manifest_sha256'],
        'PROTOCOL_SHA256':original['protocol_sha256'],'PILOT_JOB':row['job'],'PILOT_NAME':row['name'],
        'HF_HUB_DISABLE_PROGRESS_BARS':'1','PYTHONDONTWRITEBYTECODE':'1','BUCKET_ATTEMPT':attempt(row['name']),
        'SUPERVISOR_ARCHIVE':source['archive'],'SUPERVISOR_REVISION':source['revision'],
        'SUPERVISOR_SHA256':source['sha256'],'SUPERVISOR_MANIFEST_SHA256':source['manifest_sha256']}


def binding(source,row):
    _,rows=plan();require(row in rows,'Only untouched fixed rows may launch')
    return {'source':source,'original_name':row['name'],'original_row_sha256':worker.base.object_hash(row),
        'attempt_id':attempt(row['name']),'allocation':worker.ALLOCATION,'transport':worker.TRANSPORT,
        'first_bucket_result_sha256':FIRST_RESULT_SHA,'prior_failed_attempts':[],'automatic_job_retries':False}


def checked_guard(directory,source,row):
    guard=read(directory/'launch.json');intent=read(directory/'launch-intent.json');expected=binding(source,row)
    require(all(guard.get(k)==v and intent.get(k)==v for k,v in expected.items())
        and re.fullmatch('[a-f0-9]{24}',guard['job_id']),'Launch binding differs')
    return guard


def launch_once(api,directory,source,row,token):
    with exclusive(directory,'launch'):
        if (directory/'launch.json').exists():return checked_guard(directory,source,row)
        require(not (directory/'launch-intent.json').exists(),'Unresolved launch intent; never resubmit')
        expected=binding(source,row);durable(directory/'launch-intent.json',{**expected,'created_at':now()})
        job=api.run_job(image=first.IMAGE,command=['bash','-lc',bootstrap()],env=public_environment(source,row),
            secrets={'HF_TOKEN':token},flavor='cpu-upgrade',timeout='24h',
            labels={'name':expected['attempt_id'],'project':'powergrid-ai','stage':'current-auction-bucket-remaining-v3'})
        require(re.fullmatch('[a-f0-9]{24}',job.id),'Unknown submission handle; preserve intent')
        guard={**expected,'job_id':job.id,'created_at':now()};durable(directory/'launch.json',guard);return guard


def bind_remote(raw,guard,source,row):
    require(all(guard.get(k)==v for k,v in binding(source,row).items()) and raw['id']==guard['job_id'],'HF handle differs')
    require(raw['dockerImage']==first.IMAGE and raw['flavor']=='cpu-upgrade' and raw['timeout']==86400,'HF allocation differs')
    require(raw['command']==['bash','-lc',bootstrap()] and raw['arguments']==[]
        and raw['environment']==public_environment(source,row) and raw['labels']['name']==guard['attempt_id'],'HF command/source differs')
    stage=raw['status']['stage'];require(stage in WAITING|TERMINAL,'Unknown HF stage')
    return {'checked_at':now(),'job_id':guard['job_id'],'stage':stage,'attempt_id':guard['attempt_id'],
        'original_name':row['name'],'timeout_seconds':86400,'flavor':'cpu-upgrade','image':first.IMAGE,
        'bootstrap_sha256':old.first.sha_text(bootstrap()),'environment_sha256':worker.base.object_hash(public_environment(source,row)),
        'public_configuration_verified':True}


def check_one(api,directory,source,row):
    guard=checked_guard(directory,source,row)
    response=get_session().get(f'{api.endpoint}/api/jobs/{old.first.NAMESPACE}/{guard["job_id"]}',headers=api._build_hf_headers(),timeout=60)
    hf_raise_for_status(response);status=bind_remote(response.json(),guard,source,row)
    durable(directory/'checks'/(status['checked_at'].replace(':','-')+'.json'),status);return status


def result_checked(directory,source,row):
    report=read(directory/'review.json');guard=checked_guard(directory,source,row)
    require(report['verified'] is True and report['games']==row['shard']['games']
        and report['job_id']==guard['job_id'] and report['original_name']==row['name']
        and report['launch_guard_sha256']==digest(directory/'launch.json')
        and report['source_descriptor_sha256']==digest(SOURCE)
        and report['manager_sha256']==digest(__file__) and report['collector_sha256']==digest(collection.__file__)
        and report['terminal']==read(directory/'terminal.json') and report['terminal']['stage']=='COMPLETED'
        and report['versioned_archive_pending'] is False and report['versioned_collection_archive']['remote_archive_verified'],
        'Saved raw review differs')
    return report


def collect_one(api,directory,source,row,status):
    if status['stage'] in WAITING:return status
    with exclusive(directory,'collection'):
        guard=checked_guard(directory,source,row)
        require(status['stage'] in TERMINAL and status['job_id']==guard['job_id']
            and status['public_configuration_verified'] is True,'Unbound terminal status')
        if (directory/'review.json').exists():return result_checked(directory,source,row)
        log=directory/'original.log'
        if not log.exists():log.write_text('\n'.join(str(line) for line in api.fetch_job_logs(job_id=status['job_id'],follow=False)))
        terminal={**status,'log_sha256':digest(log)}
        if not (directory/'terminal.json').exists():durable(directory/'terminal.json',terminal)
        else:require(all(read(directory/'terminal.json')[k]==terminal[k] for k in ('job_id','stage','log_sha256')),'Terminal changed')
        receipts=[]
        for line in log.read_text().splitlines():
            try:value=json.loads(line)
            except (ValueError,TypeError):continue
            if isinstance(value,dict) and 'bucket_final_evidence' in value:receipts.append(value)
        require(len(receipts)==1 and receipts[0]['attempt_id']==guard['attempt_id'],'Missing/ambiguous final receipt')
        evidence=receipts[0]['bucket_final_evidence'];folder=first.collected_tree(evidence,guard['attempt_id']+'-final',directory/'envelope',api)
        require(status['stage']=='COMPLETED','Failed attempt preserved; no retry')
        bundle,bundle_sha=bundle_for(row,source)
        def reader(receipt):
            name=receipt['path'].split('/')[1]
            return first.collected_tree(receipt,name,directory/'checkpoints'/name,api)
        review_path=directory/'raw-review.json'
        if not review_path.exists():
            audit=collection.audit_envelope(folder,evidence,bundle,bundle_sha,ORIGINAL,reader)
            audit.update(job_id=status['job_id'],manager_sha256=digest(__file__),collector_sha256=digest(collection.__file__),
                source_descriptor_sha256=digest(SOURCE))
            save(review_path,audit)
        audit=read(review_path)
        require(audit['verified'] is True and audit['games']==row['shard']['games'] and audit['envelope_evidence']==evidence
            and audit['job_id']==status['job_id'] and audit['original_name']==row['name']
            and audit['manager_sha256']==digest(__file__) and audit['collector_sha256']==digest(collection.__file__)
            and audit['source_descriptor_sha256']==digest(SOURCE),'Saved independent audit changed')
        package=directory/(guard['attempt_id']+'-collected');receipt_path=directory/'promotion-receipt.json';intent=directory/'promotion-intent.json'
        if not receipt_path.exists():
            require(not package.exists() and not intent.exists(),'Inspect prior promotion intent/outcome')
            package.mkdir();worker.base.snapshot_tree(folder,package/'envelope')
            for item in audit['checkpoint_archives']:
                receipt=item['evidence'];worker.base.snapshot_tree(reader(receipt),package/'checkpoints'/receipt['path'].split('/')[1])
            shutil.copyfile(review_path,package/'raw-review.json')
            save(package/'origin.json',{'job_id':status['job_id'],'terminal':read(directory/'terminal.json'),
                'launch_guard_sha256':digest(directory/'launch.json'),'source':source,'bucket_envelope':evidence,
                'bucket_checkpoints':[r['evidence'] for r in audit['checkpoint_archives']],'new_games':0,'qualified':False})
            manifest(package);require(api.model_info(worker.base.retention.REPO).private,'Private archive required')
            require(not api.file_exists(worker.base.retention.REPO,'archives/'+package.name+'.tgz'),'Inspect prior archive')
            save(intent,{'manifest_sha256':digest(package/'manifest.json'),'raw_review_sha256':digest(review_path),'automatic_retries':False})
            promoted=old.first.upload_evidence(package);save(receipt_path,promoted)
        promoted=read(receipt_path);worker.base.tree(package,'manifest.json',promoted['manifest_sha256'])
        require(promoted['remote_archive_verified'] and read(intent)['raw_review_sha256']==digest(review_path),'Archive proof differs')
        save(directory/'review.json',{**audit,'terminal':read(directory/'terminal.json'),
            'launch_guard_sha256':digest(directory/'launch.json'),'versioned_collection_archive':promoted,
            'versioned_archive_pending':False,'qualified':False,'reserved_final_seeds_used':False})
        return result_checked(directory,source,row)


def choose(rows,records,external_active,limit):
    require(type(limit) is int and 0<=limit<=MAX_ACTIVE and type(external_active) is int and external_active>=0,'Invalid capacity')
    require(set(records)<={r['name'] for r in rows},'Foreign execution record')
    require(all(r['stage'] in WAITING|{'COMPLETED'} for r in records.values()),'Failed/unknown attempt blocks dispatch')
    active=external_active+sum(r['stage'] in WAITING for r in records.values())
    require(active<=MAX_ACTIVE,'Active capacity exceeded')
    return [r for r in rows if r['name'] not in records][:min(limit,MAX_ACTIVE-active)]


def external_status(api):
    source,rows,records=originals.original_bindings();observed=[]
    for item in records:
        observed.append(old.check_one(api,old.OUT/'jobs'/item['attempt_id'],source,rows[item['name']]))
    live=first.check();require(live['stage']=='COMPLETED','First completed proof changed')
    return observed


def cycle(execute=False,launch_limit=64,collect_limit=4):
    source=source_checked();_,rows=plan()
    if not execute:return {'execute':False,'admitted_jobs':258,'admitted_games':5804,'max_active':MAX_ACTIVE}
    require(type(collect_limit) is int and 0<=collect_limit<=64,'Invalid collection limit');choose(rows,{},0,launch_limit)
    with exclusive(old.OUT,'cycle'),exclusive(OUT,'cycle'):
        require(not (OUT/'STOP.json').exists(),'Dispatch stopped; inspect preserved evidence')
        api=HfApi();externals=external_status(api);external_active=sum(s['stage'] in WAITING for s in externals)
        jobs=OUT/'jobs';jobs.mkdir(exist_ok=True);expected={attempt(r['name']) for r in rows}
        require(all(p.is_dir() and p.name in expected for p in jobs.iterdir()),'Foreign job directory')
        records={};verified=[];collected=0;launched=[]
        for row in rows:
            directory=jobs/attempt(row['name'])
            if not directory.exists():continue
            require((directory/'launch.json').exists(),'Unresolved launch intent; never resubmit')
            if (directory/'review.json').exists():
                review=result_checked(directory,source,row);verified.append(review);records[row['name']]=review['terminal'];continue
            status=check_one(api,directory,source,row);records[row['name']]=status
            if status['stage'] in TERMINAL and (collected<collect_limit or status['stage']!='COMPLETED'):
                try:review=collect_one(api,directory,source,row,status)
                except BaseException as error:
                    durable(OUT/'STOP.json',{'created_at':now(),'original_name':row['name'],'job_id':status['job_id'],
                        'stage':status['stage'],'collection_error_type':type(error).__name__,'automatic_job_retries':False})
                    raise
                verified.append(review);collected+=1
        selected=choose(rows,records,external_active,launch_limit);token=get_token() if selected else None
        require(not selected or bool(token),'HF credentials unavailable')
        for row in selected:
            directory=jobs/attempt(row['name']);guard=launch_once(api,directory,source,row,token)
            status=check_one(api,directory,source,row);records[row['name']]=status;launched.append(guard['job_id'])
            require(status['stage'] in WAITING|{'COMPLETED'},'New attempt failed; stop dispatch')
            print(json.dumps({'submitted':guard['job_id'],'name':row['name'],'stage':status['stage'],'allocation_verified':True}),flush=True)
        state={'checked_at':now(),'source_descriptor_sha256':digest(SOURCE),'submitted':len(records),
            'stages':dict(Counter(s['stage'] for s in records.values())),'original_v2_stages':dict(Counter(s['stage'] for s in externals)),
            'external_active':external_active,'max_active':MAX_ACTIVE,'original_v2_observations':externals,
            'verified_jobs':len(verified),'verified_games':sum(r['games'] for r in verified),
            'remaining_unsubmitted':258-len(records),'launched_this_cycle':launched,'collected_this_cycle':collected,
            'jobs':records,'review_hashes':{r['original_name']:digest(jobs/r['attempt_id']/'review.json') for r in verified},
            'automatic_job_retries':False,'qualified':False,'reserved_final_seeds_used':False}
        durable(OUT/'cycles'/(state['checked_at'].replace(':','-')+'.json'),state);durable(OUT/'state.json',state)
        return {k:v for k,v in state.items() if k not in ('jobs','review_hashes','original_v2_observations')}


if __name__=='__main__':
    p=argparse.ArgumentParser(__doc__);p.add_argument('operation',choices=('prepare','upload','cycle'))
    p.add_argument('--execute',action='store_true');p.add_argument('--launch-limit',type=int,default=64)
    p.add_argument('--collect-limit',type=int,default=4);a=p.parse_args()
    result=cycle(a.execute,a.launch_limit,a.collect_limit) if a.operation=='cycle' else globals()[a.operation]()
    print(json.dumps(result),flush=True)
