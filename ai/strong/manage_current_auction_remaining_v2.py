"""Bounded first executions of the 323 frozen, never-submitted confirmation rows.

No retries, policy changes, replacement seeds or partial strength comparisons.
An intent without a saved handle blocks dispatch. Remote observation failures
do not declare a job dead. Successful raw collection is separate from HF exit.
"""
import argparse
from collections import Counter
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tarfile
import tempfile

from huggingface_hub import HfApi, get_token, hf_hub_download
from huggingface_hub.utils import get_session, hf_raise_for_status
import current_auction_remaining_collection_v2 as collection
import current_auction_remaining_resource_job_v2 as worker
import manage_current_auction_resource_recovery_v2 as first

ROOT, STRONG, ORIGINAL = first.ROOT, first.STRONG, first.ORIGINAL
PRE = ROOT/'ai/runs/current-auction-remaining-prepared-v2'
OUT = ROOT/'ai/runs/current-auction-remaining-hf-v2'
PREFLIGHT = STRONG/'current-auction-remaining-worker-preflight-v2.json'
GATE = STRONG/'current-auction-remaining-worker-first-gate-v2.json'
PREP_EVIDENCE = STRONG/'current-auction-remaining-preparation-evidence-v2.json'
SOURCE = STRONG/'current-auction-remaining-source-v2.json'
FIRST_RESULT_SHA = 'b83b2dfa755d3bc0ea6500461a6ca8166724c6ce2b6071dab282798378a91940'
MAX_ACTIVE = 64
WAITING = {'PENDING', 'SCHEDULING', 'STARTING', 'RUNNING'}
TERMINAL = {'COMPLETED', 'ERROR', 'CANCELED', 'DELETED'}
read, digest, save, require = worker.read, worker.digest, worker.save, worker.require
now, exclusive = first.now, first.exclusive


def durable(path, value):
    """Atomic, fsynced local control record; caller holds the operation lock."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.'+path.name+'.', dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as stream:
            json.dump(value, stream, indent=2, allow_nan=False)
            stream.write('\n'); stream.flush(); os.fsync(stream.fileno())
        os.replace(temporary, path)
        parent = os.open(path.parent, os.O_DIRECTORY)
        try: os.fsync(parent)
        finally: os.close(parent)
    finally:
        if Path(temporary).exists(): Path(temporary).unlink()


def plan():
    original_path = STRONG/'current-auction-grid-source-v1.json'
    decision_path = STRONG/'current-auction-resource-recovery-decision-v2.json'
    require(digest(original_path) == worker.base.SOURCE_SHA
        and digest(decision_path) == worker.base.DECISION_SHA, 'Original source/decision changed')
    original, decision = read(original_path), read(decision_path)
    rows = [worker.remaining_row(original, decision, row['name'])
        for row in decision['fixed_recovery_rows'] if row['reason'] == 'never_submitted']
    require(len(rows) == len({worker.attempt_name(r['name']) for r in rows}) == 323
        and sum(r['shard']['games'] for r in rows) == 7100, 'Remaining fixed coverage differs')
    return original, rows


def bootstrap():
    previous = first.bootstrap()
    marker = 'python -u -B /workspace/recovery-supervisor/current_auction_resource_job_v2.py'
    require(previous.count(marker) == 1, 'First supervisor bootstrap structure changed')
    return previous.split(marker)[0] + r'''python -u -B /workspace/recovery-supervisor/current_auction_remaining_resource_job_v2.py \
 --bundle /workspace/recovery-supervisor --bundle-manifest-sha256 "$SUPERVISOR_MANIFEST_SHA256" \
 --source /workspace/source --name "$PILOT_NAME" \
 --output "/workspace/recovery-output/$RETAINED_ATTEMPT" --execute --upload
'''


def first_checked():
    first.prepared()
    require(digest(first.RESULT) == FIRST_RESULT_SHA, 'First completed raw audit changed')
    original, rows = plan()
    require(worker.first_recovery_gate(read(first.RESULT), original, read(first.SOURCE)), 'First audit missing')
    gate = read(GATE)
    require(gate['passed'] is True and gate['first_recovery_result_sha256'] == FIRST_RESULT_SHA
        and gate['worker_sha256'] == digest(worker.__file__), 'Actual first-result gate changed')
    return original, rows


def tests_checked():
    files = []
    for stem, count, module in [('worker', 10, 'resource_job'), ('collection', 12, 'collection'), ('manager', 18, 'manager')]:
        test = STRONG/f'test_current_auction_remaining_{module}_v2.py'
        suffix = 'second' if stem == 'manager' else 'first'
        log = ROOT/f'ai/runs/current-auction-remaining-{stem}-tests-v2-{suffix}.log'
        require(f'Ran {count} tests' in log.read_text() and log.read_text().rstrip().endswith('OK'), 'Incomplete '+stem+' tests')
        files.extend((test, log))
    return files


def prepare():
    require(not any(p.exists() for p in (PRE, OUT, SOURCE, PREP_EVIDENCE)), 'Inspect prior preparation/submission state')
    original, rows = first_checked(); tests = tests_checked(); preflight = read(PREFLIGHT)
    require(preflight['passed'] is True and preflight['actual_specs_policies_contracts_checked'] == 323
        and preflight['worker_sha256'] == digest(worker.__file__)
        and preflight['test_sha256'] == digest(tests[0]) and preflight['test_log_sha256'] == digest(tests[1]),
        'Actual remaining-worker preflight changed')
    require(all(digest(ROOT/name) == sha for name, sha in preflight['validation_hashes'].items()), 'Original validation changed')
    pins = worker.base.tree(ORIGINAL, 'source-manifest.json', original['source_manifest_sha256'])
    for row in rows: worker.original_job_controls(ORIGINAL, original, row, pins)
    subprocess.run(['bash', '-n'], input=bootstrap(), text=True, check=True)
    preview = ROOT/'ai/runs/current-auction-remaining-worker-preflight-v2/bundle'
    worker.base.tree(preview, 'manifest.json', preflight['bundle_manifest_sha256'])
    api = HfApi(); archive_name = 'current-auction-remaining-preparation-evidence-v2'
    require(api.model_info(worker.base.retention.REPO).private, 'Evidence repository must remain private')
    require(not api.file_exists(worker.base.retention.REPO, 'archives/'+archive_name+'.tgz'), 'Inspect prior remote preparation')
    PRE.mkdir(); evidence_dir = PRE/archive_name; evidence_dir.mkdir()
    code = [Path(__file__), Path(collection.__file__), Path(worker.__file__), Path(first.__file__),
        Path(worker.base.__file__), Path(worker.base.retention.__file__),
        STRONG/'policy_iteration_evidence_archive.py', STRONG/'population_policy_verification.py',
        STRONG/'collect_current_auction_originals_after_timeout_v1.py',
        STRONG/'preflight_current_auction_remaining_worker_v2.py']
    paths = set(code+tests+[PREFLIGHT, GATE, first.RESULT, first.SOURCE,
        ROOT/'ai/runs/current-auction-remaining-manager-tests-v2-first.log',
        STRONG/'current-auction-remaining-worker-evidence-v2.json', first.OWNER_CONTEXT])
    paths.update(preview.iterdir()); paths.update(ROOT/name for name in preflight['validation_hashes'])
    for path in sorted(paths):
        require(path.is_file() and not path.is_symlink(), 'Expected regular preparation input')
        target = evidence_dir/path.relative_to(ROOT); target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target); require(digest(target) == digest(path), 'Preparation copy differs')
    save(evidence_dir/'manifest.json', {str(p.relative_to(evidence_dir)):digest(p)
        for p in sorted(evidence_dir.rglob('*')) if p.is_file()})
    durable(PRE/'evidence-upload-intent.json', {'created_at':now(), 'manifest_sha256':digest(evidence_dir/'manifest.json'), 'automatic_retries':False})
    evidence = first.upload_evidence(evidence_dir)
    durable(PRE/'evidence-upload-receipt.json', evidence)
    save(PREP_EVIDENCE, {'passed':True, 'archive':evidence, 'tests':40,
        'unit_positive_controls':'synthetic; HF APIs and raw auditor mocked',
        'actual_original_specs_validated':323, 'first_completed_raw_audit_sha256':FIRST_RESULT_SHA,
        'new_hf_jobs':0, 'new_games':0, 'qualified':False})
    bundle = PRE/'bundle'; shutil.copytree(preview, bundle)
    shutil.copyfile(first.RESULT, bundle/'first-recovery-result.json')
    (bundle/'manifest.json').unlink()
    core = {p.name:digest(p) for p in sorted(bundle.iterdir())}
    admission = {'passed':True, 'scope':'remaining_fixed_confirmation_first_executions',
        'core_files_sha256':worker.base.object_hash(core), 'first_recovery_result_sha256':FIRST_RESULT_SHA,
        'decision_sha256':worker.base.DECISION_SHA, 'source_descriptor_sha256':worker.base.SOURCE_SHA,
        'allocation':worker.base.ALLOCATION, 'jobs':323, 'games':7100,
        'preflight_sha256':digest(PREFLIGHT), 'test_log_sha256':digest(tests[-1]),
        'preparation_archive_sha256':evidence['archive_sha256'],
        'new_hf_jobs':0, 'new_games':0, 'qualified':False, 'reserved_final_seeds_used':False}
    save(bundle/'admission.json', admission)
    save(bundle/'manifest.json', {p.name:digest(p) for p in sorted(bundle.iterdir())})
    manifest_sha = digest(bundle/'manifest.json')
    checks = []
    for n in (2,3,5,6):
        row = next(row for row in rows if row['players'] == n)
        config = collection.reference_configuration(bundle, manifest_sha, ORIGINAL, row['name'])
        require(config['first_recovery_gate_verified'] is True and config['admission_sha256'] == digest(bundle/'admission.json'), 'Actual prepared command invalid')
        checks.append({'name':row['name'], 'players':n, 'command_sha256':worker.base.object_hash(config['command']), 'execution':False})
    archive = PRE/'strong-source-current-auction-remaining-retained-v2.tgz'
    with tarfile.open(archive, 'w:gz') as stream:
        for path in sorted(bundle.iterdir()):
            info = stream.gettarinfo(path, arcname=path.name); info.uid=info.gid=info.mtime=0; info.uname=info.gname=''
            with path.open('rb') as data: stream.addfile(info, data)
    proof = first.extract_verified(archive, PRE/'archive-check')
    require(proof['manifest_sha256'] == manifest_sha, 'Supervisor tar differs')
    save(PRE/'prepared.json', {'created_at':now(), 'archive':archive.name, 'sha256':digest(archive),
        'manifest_sha256':manifest_sha, 'admission_sha256':digest(bundle/'admission.json'),
        'core_files_sha256':admission['core_files_sha256'], 'preparation_evidence':evidence,
        'preparation_descriptor_sha256':digest(PREP_EVIDENCE), 'bootstrap_sha256':first.sha_text(bootstrap()),
        'code_hashes':{str(p.relative_to(ROOT)):digest(p) for p in code+tests},
        'preflight_sha256':digest(PREFLIGHT), 'first_gate_sha256':digest(GATE),
        'first_result_sha256':FIRST_RESULT_SHA, 'original_source_sha256':worker.base.SOURCE_SHA,
        'decision_sha256':worker.base.DECISION_SHA, 'allocation':worker.base.ALLOCATION,
        'rows':{r['name']:worker.base.object_hash(r) for r in rows}, 'admitted_jobs':323, 'admitted_games':7100,
        'max_active':MAX_ACTIVE, 'actual_prepared_validation':checks, 'qualified':False, 'reserved_final_seeds_used':False})
    return {'prepared':True, 'admitted_jobs':323, 'admitted_games':7100, 'archive':evidence}


def prepared():
    original, rows = first_checked(); p = read(PRE/'prepared.json')
    require(p['admitted_jobs'] == 323 and p['admitted_games'] == 7100 and p['max_active'] == MAX_ACTIVE
        and p['allocation'] == worker.base.ALLOCATION and p['rows'] == {r['name']:worker.base.object_hash(r) for r in rows}, 'Prepared fixed grid differs')
    require(all(digest(ROOT/name) == sha for name,sha in p['code_hashes'].items())
        and p['bootstrap_sha256'] == first.sha_text(bootstrap()), 'Prepared dispatcher/tests changed')
    require(p['sha256'] == digest(PRE/p['archive']) and p['preflight_sha256'] == digest(PREFLIGHT)
        and p['first_gate_sha256'] == digest(GATE) and p['first_result_sha256'] == FIRST_RESULT_SHA
        and p['preparation_descriptor_sha256'] == digest(PREP_EVIDENCE), 'Prepared evidence changed')
    pins = worker.base.tree(PRE/'bundle', 'manifest.json', p['manifest_sha256'])
    require(pins['admission.json'] == p['admission_sha256'] and pins['first-recovery-result.json'] == FIRST_RESULT_SHA,
        'Prepared admission changed')
    config = worker.inspect(PRE/'bundle', p['manifest_sha256'], ORIGINAL, PRE/'NEVER-EXECUTED', rows[0]['name'], execute=True)
    require(config['core_files_sha256'] == p['core_files_sha256'], 'Prepared source changed')
    return p


def upload():
    p = prepared()
    with exclusive(PRE, 'upload'):
        require(not SOURCE.exists() and not (PRE/'source-upload-intent.json').exists(), 'Inspect previous source upload outcome')
        api = HfApi(); require(api.dataset_info(first.REPO).private, 'Source repository must remain private')
        require(not api.file_exists(first.REPO, p['archive'], repo_type='dataset'), 'Inspect existing remote source')
        durable(PRE/'source-upload-intent.json', {'created_at':now(), 'sha256':p['sha256'], 'archive':p['archive'], 'automatic_retries':False})
        commit = api.upload_file(repo_id=first.REPO, repo_type='dataset', path_or_fileobj=PRE/p['archive'], path_in_repo=p['archive'])
        receipt = {'repo':first.REPO, 'revision':commit.oid, 'archive':p['archive'], 'sha256':p['sha256']}
        durable(PRE/'source-upload-receipt.json', receipt)
        require(digest(hf_hub_download(first.REPO, p['archive'], repo_type='dataset', revision=commit.oid)) == p['sha256'], 'Published source differs')
        source = {**receipt, 'manifest_sha256':p['manifest_sha256'], 'preparation_sha256':digest(PRE/'prepared.json'), 'remote_archive_verified':True}
        durable(SOURCE, source); return source


def source_checked():
    p = prepared(); source = read(SOURCE)
    require(source['repo'] == first.REPO and source['remote_archive_verified'] is True
        and source['preparation_sha256'] == digest(PRE/'prepared.json')
        and all(source[k] == p[k] for k in ('archive','sha256','manifest_sha256'))
        and re.fullmatch('[a-f0-9]{40}', source['revision']), 'Supervisor publication differs')
    return source


def public_environment(source, row):
    env = first.public_environment(source)
    env.update(PILOT_NAME=row['name'], PILOT_JOB=row['job'], RETAINED_ATTEMPT=worker.attempt_name(row['name']))
    return env


def binding(source, row):
    _, rows = plan()
    require(row in rows, 'Only fixed never-submitted rows may launch')
    return {'original_name':row['name'], 'original_row_sha256':worker.base.object_hash(row),
        'attempt_id':worker.attempt_name(row['name']), 'source':source, 'allocation':worker.base.ALLOCATION,
        'original_failed_handle':None, 'first_recovery_job_id':worker.FIRST_HANDLE,
        'first_recovery_result_sha256':FIRST_RESULT_SHA, 'automatic_retries':False}


def checked_guard(directory, source, row):
    guard = read(directory/'launch.json'); expected = binding(source, row)
    require(all(guard.get(k) == v for k,v in expected.items()) and re.fullmatch('[a-f0-9]{24}', guard['job_id']), 'Prior launch binding differs')
    intent = read(directory/'launch-intent.json')
    require(all(intent.get(k) == v for k,v in expected.items()), 'Launch intent differs')
    return guard


def launch_once(api, directory, source, row, token):
    expected = binding(source, row)
    with exclusive(directory, 'launch'):
        if (directory/'launch.json').exists(): return checked_guard(directory, source, row)
        require(not (directory/'launch-intent.json').exists(), 'Unresolved launch intent; never resubmit')
        durable(directory/'launch-intent.json', {**expected, 'created_at':now()})
        job = api.run_job(image=first.IMAGE, command=['bash','-lc',bootstrap()], env=public_environment(source,row),
            secrets={'HF_TOKEN':token}, flavor='cpu-upgrade', timeout='24h',
            labels={'name':expected['attempt_id'], 'project':'powergrid-ai', 'stage':'current-auction-remaining-v2'})
        require(re.fullmatch('[a-f0-9]{24}', job.id), 'Unknown submission handle; inspect durable intent')
        guard = {**expected, 'job_id':job.id, 'created_at':now()}
        durable(directory/'launch.json', guard)
        return guard


def bind_remote(raw, guard, source, row):
    require(all(guard.get(k) == v for k,v in binding(source,row).items()) and raw['id'] == guard['job_id'], 'HF handle binding differs')
    require(raw['dockerImage'] == first.IMAGE and raw['flavor'] == 'cpu-upgrade' and raw['timeout'] == 86400, 'HF allocation differs')
    require(raw['command'] == ['bash','-lc',bootstrap()] and raw['arguments'] == []
        and raw['environment'] == public_environment(source,row) and raw['labels']['name'] == guard['attempt_id'], 'HF source/command differs')
    stage = raw['status']['stage']; require(stage in WAITING | TERMINAL, 'Unknown HF stage; preserve and inspect')
    return {'checked_at':now(), 'job_id':guard['job_id'], 'attempt_id':guard['attempt_id'], 'original_name':row['name'],
        'stage':stage, 'timeout_seconds':86400, 'flavor':'cpu-upgrade', 'image':first.IMAGE,
        'bootstrap_sha256':first.sha_text(bootstrap()), 'environment_sha256':worker.base.object_hash(public_environment(source,row)),
        'public_configuration_verified':True}


def check_one(api, directory, source, row):
    guard = checked_guard(directory, source, row)
    response = get_session().get(f'{api.endpoint}/api/jobs/{first.NAMESPACE}/{guard["job_id"]}',
        headers=api._build_hf_headers(), timeout=60)
    hf_raise_for_status(response)
    status = bind_remote(response.json(), guard, source, row)
    durable(directory/'checks'/(status['checked_at'].replace(':','-')+'.json'), status)
    return status


def result_checked(directory, source, row):
    report = read(directory/'review.json'); guard = checked_guard(directory, source, row)
    require(report['verified'] is True and report['games'] == row['shard']['games']
        and report['job_id'] == guard['job_id'] and report['attempt_id'] == guard['attempt_id']
        and report['original_name'] == row['name'] and report['original_row_sha256'] == worker.base.object_hash(row)
        and report['launch_guard_sha256'] == digest(directory/'launch.json')
        and report['source_descriptor_sha256'] == digest(SOURCE)
        and report['collector_sha256'] == digest(collection.__file__) and report['manager_sha256'] == digest(__file__)
        and report['first_recovery_result_sha256'] == FIRST_RESULT_SHA
        and report['terminal'] == read(directory/'terminal.json') and report['terminal']['stage'] == 'COMPLETED', 'Saved raw review differs')
    return report


def collect_one(api, directory, source, row, status):
    with exclusive(directory, 'collection'):
        if status['stage'] in WAITING: return status
        require(status['stage'] in TERMINAL, 'Unknown terminal observation')
        guard = checked_guard(directory, source, row)
        require(status['job_id'] == guard['job_id'] and status['public_configuration_verified'] is True, 'Unbound terminal observation')
        if (directory/'review.json').exists(): return result_checked(directory, source, row)
        log = directory/'original.log'
        if not log.exists():
            lines = '\n'.join(str(line) for line in api.fetch_job_logs(job_id=status['job_id'], follow=False))
            with log.open('x') as stream: stream.write(lines)
        terminal = {**status, 'log_sha256':digest(log)}
        if not (directory/'terminal.json').exists(): durable(directory/'terminal.json', terminal)
        else:
            previous = read(directory/'terminal.json')
            require(all(previous[k] == terminal[k] for k in ('job_id','stage','log_sha256')), 'Terminal evidence changed')
        receipts = []
        for line in log.read_text().splitlines():
            try: value = json.loads(line)
            except (ValueError,TypeError): continue
            if isinstance(value,dict) and 'recovery_final_evidence' in value: receipts.append(value)
        require(len(receipts) == 1, 'Missing/ambiguous final evidence; preserve failure')
        receipt = receipts[0]; require(receipt['attempt_id'] == guard['attempt_id'], 'Foreign final receipt')
        evidence = receipt['recovery_final_evidence']; collection.checked_evidence(evidence, guard['attempt_id']+'-final')
        folder = first.download(evidence, directory/'artifacts')
        require(status['stage'] == 'COMPLETED', 'Failed HF attempt preserved; no resubmission')
        def reader(value):
            return first.download(value, directory/'checkpoints'/Path(value['archive_path']).name.removesuffix('.tgz'))
        report = collection.audit_envelope(folder, evidence, PRE/'bundle', source['manifest_sha256'], ORIGINAL, row['name'], reader)
        durable(directory/'review.json', {**report, 'job_id':status['job_id'], 'terminal':read(directory/'terminal.json'),
            'original_row_sha256':worker.base.object_hash(row), 'launch_guard_sha256':digest(directory/'launch.json'),
            'source_descriptor_sha256':digest(SOURCE), 'collector_sha256':digest(collection.__file__), 'manager_sha256':digest(__file__)})
        return result_checked(directory, source, row)


def dispatch_plan(rows, records, limit):
    require(type(limit) is int and 0 <= limit <= MAX_ACTIVE, 'Invalid bounded dispatch limit')
    require(set(records) <= {r['name'] for r in rows}, 'Foreign execution record')
    stages = [record['stage'] for record in records.values()]
    require(all(stage in WAITING | {'COMPLETED'} for stage in stages), 'Failed/ambiguous attempt blocks dispatch')
    active = sum(stage in WAITING for stage in stages)
    require(active <= MAX_ACTIVE, 'Active-job limit already exceeded')
    pending = [row for row in rows if row['name'] not in records]
    return pending[:min(limit, MAX_ACTIVE-active)]


def cycle(execute=False, launch_limit=64, collect_limit=4):
    source = source_checked(); _, rows = plan()
    if not execute: return {'execute':False, 'admitted_jobs':323, 'admitted_games':7100, 'max_active':MAX_ACTIVE}
    require(type(collect_limit) is int and 0 <= collect_limit <= 64, 'Invalid collection bound')
    dispatch_plan(rows, {}, launch_limit)
    with exclusive(OUT, 'cycle'):
        require(not (OUT/'STOP.json').exists(), 'Dispatch stopped; inspect preserved failure')
        api = HfApi(); records = {}; verified = []; collected = 0
        jobs = OUT/'jobs'; jobs.mkdir(exist_ok=True)
        expected = {worker.attempt_name(row['name']) for row in rows}
        require(all(p.is_dir() and p.name in expected for p in jobs.iterdir()), 'Unknown job directory; inspect')
        for row in rows:
            directory = jobs/worker.attempt_name(row['name'])
            if not directory.exists(): continue
            require((directory/'launch.json').exists(), 'Unresolved launch intent/directory; never resubmit')
            if (directory/'review.json').exists():
                report = result_checked(directory, source, row); verified.append(report)
                records[row['name']] = report['terminal']; continue
            status = check_one(api, directory, source, row); records[row['name']] = status
            if status['stage'] in TERMINAL and (collected < collect_limit or status['stage'] != 'COMPLETED'):
                try:
                    report = collect_one(api, directory, source, row, status)
                except BaseException as error:
                    durable(OUT/'STOP.json', {'created_at':now(), 'original_name':row['name'], 'job_id':status['job_id'],
                        'stage':status['stage'], 'failure_type':type(error).__name__, 'automatic_retries':False})
                    raise
                verified.append(report); collected += 1
        chosen = dispatch_plan(rows, records, launch_limit)
        token = get_token() if chosen else None
        require(not chosen or bool(token), 'HF authentication missing')
        launched = []
        for row in chosen:
            directory = jobs/worker.attempt_name(row['name'])
            guard = launch_once(api, directory, source, row, token)
            status = check_one(api, directory, source, row)
            records[row['name']] = status; launched.append(guard['job_id'])
            require(status['stage'] in WAITING | {'COMPLETED'}, 'New attempt already failed; stop dispatch')
            print(json.dumps({'submitted':guard['job_id'], 'name':row['name'], 'stage':status['stage'], 'allocation_verified':True}), flush=True)
        summary = {'checked_at':now(), 'source_descriptor_sha256':digest(SOURCE),
            'submitted':len(records), 'stages':dict(Counter(r['stage'] for r in records.values())),
            'verified_jobs':len(verified), 'verified_games':sum(r['games'] for r in verified),
            'remaining_unsubmitted':323-len(records), 'launched_this_cycle':launched, 'collected_this_cycle':collected,
            'jobs':records, 'review_hashes':{r['original_name']:digest(jobs/r['attempt_id']/'review.json') for r in verified},
            'automatic_retries':False, 'qualified':False, 'reserved_final_seeds_used':False}
        durable(OUT/'cycles'/(summary['checked_at'].replace(':','-')+'.json'), summary)
        durable(OUT/'state.json', summary)
        return {k:v for k,v in summary.items() if k not in ('jobs','review_hashes')}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('operation', choices=['prepare','upload','cycle'])
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--launch-limit', type=int, default=64)
    parser.add_argument('--collect-limit', type=int, default=4)
    args = parser.parse_args()
    value = cycle(args.execute,args.launch_limit,args.collect_limit) if args.operation == 'cycle' else globals()[args.operation]()
    print(json.dumps(value), flush=True)
