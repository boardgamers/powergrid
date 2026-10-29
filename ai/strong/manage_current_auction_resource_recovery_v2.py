"""Prepare/launch/check/collect only the one original failed recovery shard.

No background coordinator, batch dispatch or automatic resubmissions. Original
source and original launch records remain immutable. HF responses are projected
to public binding checks; credentials and raw JobInfo/environment are not saved.
"""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import json
from pathlib import Path
import re
import shutil
import tarfile

from huggingface_hub import HfApi, get_token, hf_hub_download
from huggingface_hub.utils import get_session, hf_raise_for_status
import current_auction_resource_collection_v2 as collection
import current_auction_resource_job_v2 as worker
from policy_iteration_evidence_archive import upload_evidence
from population_policy_verification import extract_verified

ROOT = Path(__file__).resolve().parents[2]
STRONG = ROOT/'ai/strong'
PRE = ROOT/'ai/runs/current-auction-resource-recovery-prepared-v2'
OUT = ROOT/'ai/runs/current-auction-resource-recovery-hf-v2'
ORIGINAL = ROOT/'ai/runs/current-auction-grid-prepared-v1/source'
PREFLIGHT_DIR = ROOT/'ai/runs/current-auction-resource-worker-preflight-v2'
PREFLIGHT = STRONG/'current-auction-resource-worker-preflight-v2.json'
PREP_EVIDENCE = STRONG/'current-auction-resource-preparation-evidence-v2.json'
SOURCE = STRONG/'current-auction-resource-supervisor-source-v2.json'
RESULT = STRONG/'current-auction-resource-recovery-results-v2.json'
OWNER_CONTEXT = ROOT/'ai/runs/current-auction-timeout-collection-v1/admitted-context.json'
REPO = 'coyotte508/powergrid-ai-training-v1'
NAMESPACE = 'coyotte508'
IMAGE = 'python:3.11-slim-bookworm'
SETUP_SHA = 'acaa414b8e917cbfd5642b28c45802c7673f18e1f08c1a6a33d02396bd435f68'
read, digest, save, require = worker.read, worker.digest, worker.save, worker.require


def now(): return datetime.now(timezone.utc).isoformat()
def sha_text(value): return hashlib.sha256(value.encode()).hexdigest()


def bootstrap():
    original = collection.original.m.base.BOOTSTRAP
    marker = 'python -u -B /workspace/source/public_policy_measured_job_v1.py'
    require(original.count(marker) == 1, 'Original bootstrap structure changed')
    prefix = original.split(marker)[0]
    require(sha_text(prefix) == SETUP_SHA, 'Original dependency/source setup changed')
    return prefix + r'''python -B - <<'RECOVERY_BUNDLE'
import hashlib,json,os,tarfile
from pathlib import Path
from huggingface_hub import hf_hub_download
archive=hf_hub_download('coyotte508/powergrid-ai-training-v1',os.environ['SUPERVISOR_ARCHIVE'],repo_type='dataset',revision=os.environ['SUPERVISOR_REVISION'])
assert hashlib.sha256(Path(archive).read_bytes()).hexdigest()==os.environ['SUPERVISOR_SHA256']
root=Path('/workspace/recovery-supervisor');assert not root.exists()
with tarfile.open(archive) as bundle:
    members=bundle.getmembers();names=[m.name for m in members]
    assert len(names)==len(set(names)) and all(m.isfile() and not Path(m.name).is_absolute() and '..' not in Path(m.name).parts for m in members)
    manifest=bundle.extractfile('manifest.json').read()
    assert hashlib.sha256(manifest).hexdigest()==os.environ['SUPERVISOR_MANIFEST_SHA256']
    pins=json.loads(manifest);assert 'manifest.json' not in pins and set(names)==set(pins)|{'manifest.json'}
    assert all(hashlib.sha256(bundle.extractfile(name).read()).hexdigest()==sha for name,sha in pins.items())
    root.mkdir();bundle.extractall(root,filter='data')
Path('/workspace/recovery-output').mkdir()
RECOVERY_BUNDLE
python -u -B /workspace/recovery-supervisor/current_auction_resource_job_v2.py \
 --bundle /workspace/recovery-supervisor --bundle-manifest-sha256 "$SUPERVISOR_MANIFEST_SHA256" \
 --source /workspace/source --output /workspace/recovery-output/pg-current-recover-v2-pop-search-4p-05 --execute --upload
'''


def originals_unchanged():
    context = read(OWNER_CONTEXT)
    require(all(digest(ROOT/p) == sha for p,sha in {**context['owner_pins'], **context['guard_hashes']}.items()),
        'Original controls or launch guards changed')
    state = read(ROOT/'ai/runs/current-auction-timeout-collection-v1/state.json')
    require(state['verified_jobs'] == 620 and state['failed_originals'] == 1 and state['active_originals'] == 0,
        'Original terminal accounting changed')
    require(not Path('/proc/3788704').exists() and not Path(f"/proc/{state['pid']}").exists(),
        'Inspect original owner process before execution')
    return digest(OWNER_CONTEXT)


def tests_checked():
    paths = []
    for name, count, suffix in [('job',14,'first'),('collection',11,'first'),('manager',10,'first')]:
        test = STRONG/('test_current_auction_resource_'+('recovery_v2' if name == 'manager' else name+'_v2')+'.py')
        log = ROOT/f'ai/runs/current-auction-resource-{name}-tests-v2-{suffix}.log'
        require(f'Ran {count} tests' in log.read_text() and log.read_text().rstrip().endswith('OK'), 'Incomplete '+name+' tests')
        paths.extend((test,log))
    return paths


def prepare():
    require(not any(p.exists() for p in (PRE,OUT,PREP_EVIDENCE,SOURCE,RESULT)), 'Inspect prior preparation or execution')
    owner_sha = originals_unchanged(); tests = tests_checked(); preflight = read(PREFLIGHT)
    require(preflight['passed'] and preflight['worker_sha256'] == digest(worker.__file__)
        and preflight['retention_sha256'] == digest(worker.retention.__file__)
        and preflight['test_sha256'] == digest(tests[0]) and preflight['test_log_sha256'] == digest(tests[1]),
        'Actual source preflight no longer binds worker')
    require(all(digest(ROOT/p) == sha for p,sha in preflight['validation_hashes'].items()), 'Original validation changed')
    candidate = PREFLIGHT_DIR/'bundle'
    config = worker.inspect(candidate,preflight['bundle_manifest_sha256'],ORIGINAL,PRE/'NEVER-EXECUTED')
    require(config['core_files_sha256'] == preflight['core_files_sha256'], 'Core preflight differs')
    bootstrap_text = bootstrap()
    api = HfApi(); require(api.model_info(worker.retention.REPO).private, 'Evidence repository must be private')
    archive_name = 'current-auction-resource-preparation-evidence-v2'
    require(not api.file_exists(worker.retention.REPO,'archives/'+archive_name+'.tgz'), 'Inspect prior remote evidence')
    PRE.mkdir(); evidence_dir = PRE/archive_name; evidence_dir.mkdir()
    code = [Path(__file__),Path(worker.__file__),Path(worker.retention.__file__),Path(collection.__file__),
        STRONG/'policy_iteration_evidence_archive.py',STRONG/'population_policy_verification.py',
        STRONG/'collect_current_auction_originals_after_timeout_v1.py']
    paths = set(code+tests+[PREFLIGHT,OWNER_CONTEXT,STRONG/'current-auction-original-terminal-evidence-v1.json',
        STRONG/'current-auction-recovery-retention-evidence-v2.json',
        STRONG/'current-auction-recovery-retention-preflight-v2.json',
        ROOT/'ai/runs/preflight-current-auction-resource-worker-v2.py',PREFLIGHT_DIR/'intent.json'])
    paths.update(ROOT/p for p in preflight['validation_hashes'])
    paths.update(candidate.iterdir())
    for path in sorted(paths):
        target = evidence_dir/path.relative_to(ROOT); target.parent.mkdir(parents=True,exist_ok=True)
        require(path.is_file() and not path.is_symlink(), 'Expected regular preparation input')
        shutil.copyfile(path,target); require(digest(path) == digest(target), 'Preparation copy changed')
    save(evidence_dir/'manifest.json',{str(p.relative_to(evidence_dir)):digest(p)
        for p in sorted(evidence_dir.rglob('*')) if p.is_file()})
    save(PRE/'evidence-upload-intent.json',{'created_at':now(),'manifest_sha256':digest(evidence_dir/'manifest.json'),
        'automatic_retries':False})
    evidence = upload_evidence(evidence_dir)
    save(PREP_EVIDENCE,{'archive':evidence,'passed':True,'tests':35,'unit_positive_controls':'synthetic; remote APIs/raw game audit mocked',
        'actual_original_source_validation':True,'preflight_sha256':digest(PREFLIGHT),
        'new_hf_jobs':0,'new_games':0,'qualified':False})
    bundle = PRE/'bundle'; shutil.copytree(candidate,bundle)
    admission = {'passed':True,'scope':config['control']['scope'],'core_files_sha256':config['core_files_sha256'],
        'control_sha256':digest(bundle/'control.json'),'decision_sha256':worker.DECISION_SHA,
        'source_descriptor_sha256':worker.SOURCE_SHA,'preflight_sha256':digest(PREFLIGHT),
        'test_log_sha256':digest(tests[1]),'preparation_archive_sha256':evidence['archive_sha256'],
        'new_hf_jobs':0,'new_games':0,'qualified':False,'reserved_final_seeds_used':False}
    save(bundle/'admission.json',admission)
    (bundle/'manifest.json').unlink()
    save(bundle/'manifest.json',{p.name:digest(p) for p in sorted(bundle.iterdir())})
    manifest_sha = digest(bundle/'manifest.json')
    worker.inspect(bundle,manifest_sha,ORIGINAL,PRE/'NEVER-EXECUTED',execute=True)
    archive = PRE/'strong-source-current-auction-resource-supervisor-v2.tgz'
    with tarfile.open(archive,'w:gz') as stream:
        for path in sorted(bundle.iterdir()):
            info = stream.gettarinfo(path,arcname=path.name); info.uid=info.gid=info.mtime=0; info.uname=info.gname=''
            with path.open('rb') as data: stream.addfile(info,data)
    proof = extract_verified(archive,PRE/'archive-check')
    require(proof['manifest_sha256'] == manifest_sha, 'Supervisor archive differs')
    save(PRE/'prepared.json',{'created_at':now(),'attempt_id':worker.ATTEMPT,'original_failed_handle':worker.FAILED_HANDLE,
        'archive':archive.name,'sha256':digest(archive),'manifest_sha256':manifest_sha,
        'core_files_sha256':config['core_files_sha256'],'admission_sha256':digest(bundle/'admission.json'),
        'preparation_evidence':evidence,'preparation_descriptor_sha256':digest(PREP_EVIDENCE),
        'owner_context_sha256':owner_sha,'bootstrap_sha256':sha_text(bootstrap_text),
        'code_hashes':{str(p.relative_to(ROOT)):digest(p) for p in code+tests},
        'preflight_sha256':digest(PREFLIGHT),'original_source_sha256':worker.SOURCE_SHA,
        'decision_sha256':worker.DECISION_SHA,'allocation':worker.ALLOCATION,
        'admitted_jobs':1,'admitted_games':16,'remaining_rows_admitted':False,
        'qualified':False,'reserved_final_seeds_used':False})
    return {'prepared':True,'admitted_jobs':1,'admitted_games':16,'preparation_evidence':evidence}


def prepared():
    p = read(PRE/'prepared.json')
    require(p['attempt_id'] == worker.ATTEMPT and p['allocation'] == worker.ALLOCATION
        and p['admitted_jobs'] == 1 and p['admitted_games'] == 16 and p['remaining_rows_admitted'] is False,
        'Only first failed shard can run')
    require(p['original_source_sha256'] == worker.SOURCE_SHA and p['decision_sha256'] == worker.DECISION_SHA
        and p['owner_context_sha256'] == originals_unchanged(), 'Original recovery inputs changed')
    require(p['bootstrap_sha256'] == sha_text(bootstrap()) and all(digest(ROOT/name)==sha for name,sha in p['code_hashes'].items()),
        'Prepared code/tests changed')
    require(p['sha256'] == digest(PRE/p['archive']) and p['preflight_sha256'] == digest(PREFLIGHT)
        and p['preparation_descriptor_sha256'] == digest(PREP_EVIDENCE), 'Prepared evidence changed')
    config = worker.inspect(PRE/'bundle',p['manifest_sha256'],ORIGINAL,collection.REMOTE_OUTPUT,execute=True)
    require(config['core_files_sha256'] == p['core_files_sha256'] and config['admission_sha256'] == p['admission_sha256'],
        'Prepared control admission differs')
    return p


@contextmanager
def exclusive(directory, name):
    directory.mkdir(parents=True,exist_ok=True)
    with (directory/('.'+name+'.lock')).open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        yield


def upload():
    p = prepared()
    with exclusive(PRE,'upload'):
        require(not SOURCE.exists() and not (PRE/'source-upload-intent.json').exists(), 'Inspect existing source upload outcome')
        api = HfApi(); require(api.dataset_info(REPO).private, 'Supervisor repository must be private')
        require(not api.file_exists(REPO,p['archive'],repo_type='dataset'), 'Existing source requires inspection')
        save(PRE/'source-upload-intent.json',{'created_at':now(),'archive':p['archive'],'sha256':p['sha256'],'automatic_retries':False})
        commit = api.upload_file(repo_id=REPO,repo_type='dataset',path_or_fileobj=PRE/p['archive'],path_in_repo=p['archive'])
        receipt = {'repo':REPO,'revision':commit.oid,'archive':p['archive'],'sha256':p['sha256']}
        save(PRE/'source-upload-receipt.json',receipt)
        require(digest(hf_hub_download(REPO,p['archive'],repo_type='dataset',revision=commit.oid))==p['sha256'], 'Remote source differs')
        source = {**receipt,'manifest_sha256':p['manifest_sha256'],'preparation_sha256':digest(PRE/'prepared.json'),'remote_archive_verified':True}
        save(SOURCE,source); return source


def source_checked():
    p = prepared(); source = read(SOURCE)
    require(source['repo'] == REPO and source['remote_archive_verified'] is True
        and source['preparation_sha256'] == digest(PRE/'prepared.json')
        and all(source[k] == p[k] for k in ('archive','sha256','manifest_sha256'))
        and re.fullmatch('[a-f0-9]{40}',source['revision']), 'Supervisor publication differs')
    return source


def public_environment(source):
    original = read(PRE/'bundle/original-source.json')
    row = next(r for r in original['rows'] if r['name'] == worker.FAILED_NAME)
    return {'SOURCE_ARCHIVE':original['archive'],'SOURCE_REVISION':original['revision'],
        'SOURCE_SHA256':original['sha256'],'SOURCE_MANIFEST_SHA256':original['source_manifest_sha256'],
        'PROTOCOL_SHA256':original['protocol_sha256'],'PILOT_JOB':row['job'],'PILOT_NAME':row['name'],
        'HF_HUB_DISABLE_PROGRESS_BARS':'1','PYTHONDONTWRITEBYTECODE':'1',
        'SUPERVISOR_ARCHIVE':source['archive'],'SUPERVISOR_REVISION':source['revision'],
        'SUPERVISOR_SHA256':source['sha256'],'SUPERVISOR_MANIFEST_SHA256':source['manifest_sha256']}


def launch_once(api, directory, source, token):
    with exclusive(directory,'launch'):
        path = directory/'launch.json'; intent = directory/'launch-intent.json'
        if path.exists():
            saved = read(path)
            require(saved['source'] == source and saved['attempt_id'] == worker.ATTEMPT
                and re.fullmatch('[a-f0-9]{24}',saved['job_id']), 'Prior attempt binding differs')
            return saved
        require(not intent.exists(), 'Unresolved launch intent; never resubmit')
        save(intent,{'created_at':now(),'attempt_id':worker.ATTEMPT,'source':source,'allocation':worker.ALLOCATION,
            'original_failed_handle':worker.FAILED_HANDLE,'automatic_retries':False})
        job = api.run_job(image=IMAGE,command=['bash','-lc',bootstrap()],env=public_environment(source),
            secrets={'HF_TOKEN':token},flavor='cpu-upgrade',timeout='24h',
            labels={'name':worker.ATTEMPT,'project':'powergrid-ai','stage':'current-auction-resource-recovery-v2'})
        require(re.fullmatch('[a-f0-9]{24}',job.id), 'Unknown submission handle; inspect intent')
        guard = {'attempt_id':worker.ATTEMPT,'job_id':job.id,'source':source,'created_at':now(),
            'allocation':worker.ALLOCATION,'original_failed_handle':worker.FAILED_HANDLE,'automatic_retries':False}
        save(path,guard); return guard


def bind_remote(raw, guard, source):
    """Validate private response, return only nonsecret checks/status."""
    require(raw['id'] == guard['job_id'] and guard['attempt_id'] == worker.ATTEMPT and guard['source'] == source, 'HF handle differs')
    require(raw['dockerImage'] == IMAGE and raw['flavor'] == 'cpu-upgrade'
        and raw['timeout'] == 86400, 'Actual HF allocation differs from admitted 24h CPU attempt')
    require(raw['command'] == ['bash','-lc',bootstrap()] and raw['arguments'] == [], 'Actual HF command differs')
    require(raw['environment'] == public_environment(source), 'Actual HF public environment differs')
    require(raw['labels']['name'] == worker.ATTEMPT, 'HF name differs')
    return {'checked_at':now(),'job_id':guard['job_id'],'attempt_id':worker.ATTEMPT,
        'stage':raw['status']['stage'],'timeout_seconds':raw['timeout'],'flavor':raw['flavor'],
        'image':raw['dockerImage'],'bootstrap_sha256':sha_text(bootstrap()),
        'environment_sha256':worker.object_hash(public_environment(source)),
        'public_configuration_verified':True,'original_failed_handle':worker.FAILED_HANDLE}


def check(source=None):
    source = source or source_checked(); guard = read(OUT/'launch.json'); api=HfApi()
    response = get_session().get(f'{api.endpoint}/api/jobs/{NAMESPACE}/{guard["job_id"]}',headers=api._build_hf_headers())
    hf_raise_for_status(response)
    status = bind_remote(response.json(),guard,source)
    checks = OUT/'checks'; checks.mkdir(exist_ok=True)
    save(checks/(status['checked_at'].replace(':','-')+'.json'),status)
    return status


def launch(execute=False):
    source = source_checked()
    if not execute: return {'execute':False,'admitted_jobs':1,'admitted_games':16,'remaining_rows_admitted':False}
    token = get_token(); require(bool(token), 'HF authentication missing')
    launch_once(HfApi(),OUT,source,token)
    return check(source)


def download(evidence, directory):
    archive = hf_hub_download(evidence['repo'],evidence['archive_path'],revision=evidence['revision'])
    require(digest(archive) == evidence['archive_sha256'], 'Remote evidence archive differs')
    if not directory.exists(): extract_verified(archive,directory)
    worker.tree(directory,'manifest.json',evidence['manifest_sha256'])
    return directory


def collect():
    source = source_checked()
    with exclusive(OUT,'collection'):
        status = check(source)
        if status['stage'] in ('PENDING','RUNNING'): return status
        require(status['stage'] in ('COMPLETED','ERROR','CANCELED','DELETED'), 'Unknown HF status; preserve and inspect')
        log = OUT/'original-recovery.log'
        if not log.exists():
            lines = '\n'.join(str(s) for s in HfApi().fetch_job_logs(job_id=status['job_id'],follow=False))
            with log.open('x') as stream: stream.write(lines)
        if not (OUT/'terminal.json').exists(): save(OUT/'terminal.json',{**status,'log_sha256':digest(log)})
        receipts=[]
        for line in log.read_text().splitlines():
            try: value=json.loads(line)
            except (ValueError,TypeError): continue
            if isinstance(value,dict) and 'recovery_final_evidence' in value: receipts.append(value)
        require(len(receipts)==1, 'Missing/ambiguous final evidence; preserve failure, no resubmission')
        receipt=receipts[0]; require(receipt['attempt_id']==worker.ATTEMPT,'Foreign final receipt')
        evidence=receipt['recovery_final_evidence']; collection.checked_evidence(evidence,worker.ATTEMPT+'-final')
        folder=download(evidence,OUT/'artifacts')
        require(status['stage']=='COMPLETED', 'Preserved failed HF attempt; independent review required')
        checkpoints=OUT/'checkpoints';checkpoints.mkdir(exist_ok=True)
        def reader(value):
            name=Path(value['archive_path']).name.removesuffix('.tgz')
            return download(value,checkpoints/name)
        if RESULT.exists():
            saved=read(RESULT); require(saved['job_id']==status['job_id'] and saved['envelope_evidence']==evidence,'Existing result differs')
            return {'already_collected':True,'job_id':status['job_id'],'games':saved['games']}
        report=collection.audit_envelope(folder,evidence,PRE/'bundle',source['manifest_sha256'],ORIGINAL,reader)
        save(RESULT,{**report,'job_id':status['job_id'],'terminal':read(OUT/'terminal.json'),
            'source_descriptor_sha256':digest(SOURCE),'collector_sha256':digest(collection.__file__),
            'manager_sha256':digest(__file__),'remaining_rows_admitted':False})
        return {'verified':True,'job_id':status['job_id'],'games':report['games'],'qualified':False,'remaining_rows_admitted':False}


if __name__=='__main__':
    parser=argparse.ArgumentParser(__doc__)
    parser.add_argument('operation',choices=['prepare','upload','launch','check','collect'])
    parser.add_argument('--execute',action='store_true'); args=parser.parse_args()
    result=launch(args.execute) if args.operation=='launch' else globals()[args.operation]()
    print(json.dumps(result),flush=True)
