"""Publish, launch and collect only the frozen current-engine confirmation."""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import tarfile

from huggingface_hub import HfApi, get_token, hf_hub_download
from public_policy_development_job_v1 import digest, read, write
from public_policy_final_audit_v1 import audit_shard
from public_policy_final_contract_v1 import audit_execution_binding, object_hash
from population_policy_verification import extract_verified

ROOT = Path(__file__).resolve().parents[2]
LOCAL = ROOT/'ai/runs/current-auction-grid-prepared-v1'
OUT = ROOT/'ai/runs/current-auction-grid-hf-v1'
SOURCE = ROOT/'ai/strong/current-auction-grid-source-v1.json'
RESULT = ROOT/'ai/strong/current-auction-grid-results-v1.json'
ARCHIVE = ROOT/'ai/runs/strong-source-current-auction-grid-v1.tgz'
REPO = 'coyotte508/powergrid-ai-training-v1'
READINESS = ROOT/'ai/strong/current-auction-grid-readiness-v1.json'


def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(filename))
    value = importlib.util.module_from_spec(spec); spec.loader.exec_module(value); return value


pilots = module('original_runtime_pilots', 'manage-current-auction-runtime-v1.py')
planning = module('development_source_preparer', 'prepare-current-auction-grid-v1.py')
assert pilots.BOOTSTRAP.count('--scope runtime') == 1
BOOTSTRAP = pilots.BOOTSTRAP.replace('--scope runtime', '--scope development')


def now(): return datetime.now(timezone.utc).isoformat()


def write_new(path, value):
    with Path(path).open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False); stream.write('\n')


def prerequisites():
    ready = read(READINESS)
    assert ready['passed'] and all(digest(ROOT/name) == sha for name, sha in ready['input_hashes'].items())
    p = read(LOCAL/'prepared.json'); root = LOCAL/'source'
    assert p['preparer_sha256'] == digest(planning.__file__)
    assert p['protocol_sha256'] == planning.PROTOCOL_SHA == digest(planning.PROTOCOL)
    assert p['runtime_results_sha256'] == digest(pilots.RESULT)
    assert p['runtime_source_sha256'] == digest(pilots.SOURCE)
    assert read(pilots.RESULT)['complete'] and read(pilots.RESULT)['verified_jobs'] == 4
    assert digest(root/'source-manifest.json') == p['source_manifest_sha256']
    assert digest(root/'confirmation-admission.json') == p['admission_sha256']
    pins = read(root/'source-manifest.json')
    assert set(pins)|{'source-manifest.json'} == {str(f.relative_to(root)) for f in root.rglob('*') if f.is_file()}
    assert all(digest(root/name) == sha for name, sha in pins.items())
    assert p['games'] == sum(r['shard']['games'] for r in p['rows']) == 26880
    return p


def prepare():
    p = prerequisites(); root = LOCAL/'source'; pins = read(root/'source-manifest.json')
    for part, count in (('plan', 6), ('manager', 7)):
        test = ROOT / f'ai/runs/current-auction-grid-{part}-tests-v1.log'
        assert f'Ran {count} tests' in test.read_text() and test.read_text().rstrip().endswith('OK')
    assert not OUT.exists() and not ARCHIVE.exists() and not SOURCE.exists(), 'Preserve original source/upload outcome'
    OUT.mkdir()
    with tarfile.open(ARCHIVE, 'w:gz') as bundle:
        for name in sorted(set(pins)|{'source-manifest.json'}):
            path = root/name; assert not path.is_symlink()
            info = bundle.gettarinfo(path, arcname=name)
            info.uid = info.gid = info.mtime = 0; info.uname = info.gname = ''
            with path.open('rb') as stream: bundle.addfile(info, stream)
    prepared = {**p, 'created_at': now(), 'archive': ARCHIVE.name, 'sha256': digest(ARCHIVE),
        'bytes': ARCHIVE.stat().st_size, 'entry_sha256': digest(root/'public_policy_development_job_v1.py'),
        'measured_entry_sha256': digest(root/'public_policy_measured_job_v1.py'),
        'runner_sha256': digest(root/'artifact/ai/strong/public_policy_final_runner_v1.py'),
        'launcher_sha256': digest(__file__), 'bootstrap_sha256': hashlib.sha256(BOOTSTRAP.encode()).hexdigest(),
        'prepared_source_sha256': digest(LOCAL/'prepared.json'), 'max_active_jobs': 64,
        'readiness_sha256': digest(READINESS),
        'dependency_hashes': {str(Path(p).resolve().relative_to(ROOT)): digest(p) for p in
            (pilots.__file__, planning.__file__,
             Path(__file__).with_name('test_current_auction_grid_plan_v1.py'),
             Path(__file__).with_name('test_current_auction_grid_manager_v1.py'))},
        'test_log_hashes': {f'ai/runs/current-auction-grid-{part}-tests-v1.log':
            digest(ROOT / f'ai/runs/current-auction-grid-{part}-tests-v1.log') for part in ('plan','manager')},
        'qualification_eligible': False, 'reserved_final_seeds_used': False}
    write_new(OUT/'prepared.json', prepared)
    return {'prepared': True, 'jobs': len(p['rows']), 'games': p['games']}


def prepared():
    prerequisites(); p = read(OUT/'prepared.json')
    assert p['launcher_sha256'] == digest(__file__) and p['sha256'] == digest(ARCHIVE)
    assert p['prepared_source_sha256'] == digest(LOCAL/'prepared.json')
    assert p['readiness_sha256'] == digest(READINESS)
    assert p['bootstrap_sha256'] == hashlib.sha256(BOOTSTRAP.encode()).hexdigest()
    assert all(digest(ROOT/name) == sha for name, sha in {**p['dependency_hashes'], **p['test_log_hashes']}.items())
    return p


def upload():
    p = prepared()
    with (OUT/'.upload.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if SOURCE.exists():
            source = read(SOURCE); assert source['preparation_sha256'] == digest(OUT/'prepared.json')
            return {'existing_revision': source['revision']}
        assert p['archive'] not in HfApi().list_repo_files(REPO, repo_type='dataset'), 'Inspect existing remote source before upload'
        write_new(OUT/'upload-intent.json', {'created_at': now(), 'archive': p['archive'], 'sha256': p['sha256']})
        commit = HfApi().upload_file(repo_id=REPO, repo_type='dataset', path_or_fileobj=ARCHIVE, path_in_repo=p['archive'])
        receipt = {'repo': REPO, 'revision': commit.oid, 'archive': p['archive'], 'sha256': p['sha256']}
        write_new(OUT/'upload-receipt.json', receipt)
        assert digest(hf_hub_download(REPO, p['archive'], repo_type='dataset', revision=commit.oid)) == p['sha256']
        write_new(SOURCE, {**p, **receipt, 'preparation_sha256': digest(OUT/'prepared.json'), 'remote_archive_verified': True})
        return receipt


def source_checked():
    p = prepared(); source = read(SOURCE)
    assert all(source[k] == value for k, value in p.items())
    assert source['preparation_sha256'] == digest(OUT/'prepared.json') and source['remote_archive_verified']
    return source


def launch_once(api, directory, source, row, token):
    assert row in source['rows'] and row['shard']['seed'] == f"current-auction-confirmation-v1-{row['players']}p"
    assert row['players'] in range(2, 7) and row['shard']['players'] == row['players']
    assert row['shard']['deals'] in (1,2,4,8,16,32) and 0 <= row['shard']['start'] < 32
    assert row['shard']['start'] % row['shard']['deals'] == 0
    assert row['shard']['start'] + row['shard']['deals'] <= 32
    directory = Path(directory); fingerprint = object_hash(source)
    with (directory/'.launch.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        path = directory/'launch.json'
        if path.exists():
            guard = read(path)
            assert guard['stage'] == 'launched' and guard['source_fingerprint'] == fingerprint and guard['row'] == row, 'Reconcile original uncertain launch'
            assert re.fullmatch('[a-f0-9]{24}', guard['job_id']); return guard
        guard = {'stage': 'launch_intent', 'created_at': now(), 'source_fingerprint': fingerprint, 'row': row}
        write_new(path, guard)
        try:
            env = {'SOURCE_ARCHIVE': source['archive'], 'SOURCE_REVISION': source['revision'],
                'SOURCE_SHA256': source['sha256'], 'SOURCE_MANIFEST_SHA256': source['source_manifest_sha256'],
                'PROTOCOL_SHA256': source['protocol_sha256'], 'PILOT_JOB': row['job'], 'PILOT_NAME': row['name'],
                'HF_HUB_DISABLE_PROGRESS_BARS': '1', 'PYTHONDONTWRITEBYTECODE': '1'}
            job = api.run_job(image='python:3.11-slim-bookworm', command=['bash', '-lc', BOOTSTRAP],
                flavor=row['flavor'], timeout=row['timeout'], name=row['name'], env=env,
                secrets={'HF_TOKEN': token}, labels={'project': 'powergrid-ai', 'stage': 'current-auction-grid-v1'})
            guard.update(stage='launched', job_id=job.id)
        except BaseException as error:
            guard.update(stage='launch_unknown', failure_type=type(error).__name__); raise
        finally: write(path, guard)
        return guard


def original_status(api, source, row):
    directory = OUT/row['name']; guard = read(directory/'launch.json')
    assert guard['stage'] == 'launched' and guard['source_fingerprint'] == object_hash(source) and guard['row'] == row
    stage = api.inspect_job(job_id=guard['job_id']).status.stage
    status = {'checked_at': now(), 'job_id': guard['job_id'], 'stage': stage, 'name': row['name']}
    write(directory/'status.json', status); return status


@contextmanager
def exclusive_operation():
    assert OUT.is_dir(), 'Prepare and admit the source before any operation'
    with (OUT / '.operation.lock').open('a') as owner:
        fcntl.flock(owner, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield


def launch(execute=False, limit=64):
    with exclusive_operation():
        return launch_batch(execute, limit)


def launch_batch(execute=False, limit=64):
    source = source_checked(); assert type(limit) is int and 1 <= limit <= source['max_active_jobs']
    if not execute: return {'execute': False, 'jobs': len(source['rows']), 'games': 26880}
    test = ROOT/'ai/runs/current-auction-grid-manager-tests-v1.log'
    assert 'Ran 7 tests' in test.read_text() and test.read_text().rstrip().endswith('OK')
    # A batch lock protects the total concurrency allowance as well as each job.
    with (OUT/'.batch-launch.lock').open('a') as owner:
        fcntl.flock(owner, fcntl.LOCK_EX | fcntl.LOCK_NB)
        api = HfApi(); pending, active, awaiting_collection = [], 0, []
        for row in source['rows']:
            directory = OUT/row['name']
            if not (directory/'launch.json').exists(): pending.append(row); continue
            if (directory/'verified.json').exists():
                saved = read(directory/'verified.json')
                assert saved['source_sha256'] == digest(SOURCE) and saved['row'] == row
                assert saved['guard_sha256'] == digest(directory/'launch.json')
                assert saved['stage'] == 'COMPLETED' and saved['verified']
                continue
            status = original_status(api, source, row)
            assert status['stage'] in ('SCHEDULING', 'RUNNING', 'COMPLETED'), 'Inspect terminal original job before adding more work'
            if status['stage'] == 'COMPLETED': awaiting_collection.append(row['name'])
            active += status['stage'] != 'COMPLETED'
        if awaiting_collection:
            # A job may finish between collection and this fresh status read.
            # Defer new submissions; the next bounded collect verifies it.
            return {'new_jobs': [], 'active_jobs': active, 'remaining_unsubmitted': len(pending),
                    'awaiting_collection': awaiting_collection}
        token = get_token(); assert token; launched = []
        for row in pending[:max(0, min(limit, source['max_active_jobs']-active))]:
            directory = OUT/row['name']; directory.mkdir(exist_ok=True)
            guard = launch_once(api, directory, source, row, token)
            info = {'name': row['name'], 'job_id': guard['job_id']}; launched.append(info)
            print(json.dumps(info), flush=True)
        return {'new_jobs': launched, 'active_jobs': active+len(launched), 'remaining_unsubmitted': len(pending)-len(launched)}


def verify_artifacts(folder, source, row, evidence):
    pins = read(folder/'manifest.json')
    assert digest(folder/'manifest.json') == evidence['manifest_sha256']
    assert set(pins)|{'manifest.json'} == {str(p.relative_to(folder)) for p in folder.rglob('*') if p.is_file()}
    assert all(digest(folder/name) == sha for name, sha in pins.items())
    m = read(folder/'measurement.json'); pilots.previous.check_measurement(m)
    assert m['case'] == row['name'] and m['scope'] == 'development'
    assert m['experiment_protocol_sha256'] == source['protocol_sha256'] and m['measured_entry_sha256'] == source['measured_entry_sha256']
    expected = {k: source[k] for k in ('source_manifest_sha256', 'entry_sha256')}
    expected.update({k: row[k] for k in ('job_spec_sha256', 'candidate_sha256', 'contract_sha256', 'identity', 'shard')})
    expected.update(source_revision=source['revision'], source_archive_sha256=source['sha256'])
    assert m['provenance'] == expected
    inner = folder/'job'; status = read(inner/'job-status.json')
    assert status['stage'] == 'complete' and status['provenance'] == expected
    assert digest(inner/'job-status.json') == m['job_status_sha256']
    assert digest(inner/'source-manifest.json') == source['source_manifest_sha256']
    assert digest(inner/'job-spec.json') == row['job_spec_sha256']
    target = inner/'evaluation'
    assert digest(target/'evaluation.json') == status['evaluation_sha256'] and digest(target/'audit.json') == status['audit_sha256']
    audit = audit_shard(target, row['shard'], row['identity'], reserved=False)
    binding = audit_execution_binding(target, row['identity'], source['runner_sha256'])
    assert read(target/'audit.json') == {**audit, 'execution_binding': binding}
    assert status['counts'] == m['counts'] == audit['counts']
    assert status['games'] == m['games'] == row['shard']['games']
    return {'games': status['games'], 'audit': audit, 'measurement': m['measurement']}


def collect():
    with exclusive_operation():
        return collect_originals()


def collect_originals():
    source = source_checked(); results = []; states = []; api = HfApi()
    for row in source['rows']:
        directory = OUT/row['name']
        if not (directory/'launch.json').exists(): continue
        if (directory/'verified.json').exists():
            saved = read(directory/'verified.json')
            assert saved['source_sha256'] == digest(SOURCE) and saved['row'] == row
            assert saved['guard_sha256'] == digest(directory/'launch.json')
            assert digest(directory/'artifacts/manifest.json') == saved['evidence']['manifest_sha256']
            results.append(saved); continue
        status = original_status(api, source, row); states.append(status)
        if status['stage'] in ('SCHEDULING', 'RUNNING'): continue
        log = '\n'.join(str(s) for s in api.fetch_job_logs(job_id=status['job_id'], follow=False))
        (directory/'job.log').write_text(log); receipts = []
        for line in log.splitlines():
            if not line.startswith('{'): continue
            try: receipt = json.loads(line)
            except json.JSONDecodeError: continue
            if set(receipt) == {'case', 'status', 'evidence'} and receipt['case'] == row['name']: receipts.append(receipt)
        if len(receipts) == 1:
            evidence = receipts[0]['evidence']; assert evidence['repo'] == 'coyotte508/powergrid-ai-germany-v1'
            assert evidence['archive_path'] == 'archives/'+row['name']+'.tgz' and evidence['remote_archive_verified']
            assert re.fullmatch('[a-f0-9]{40}', evidence['revision'])
            archive = Path(hf_hub_download(evidence['repo'], evidence['archive_path'], revision=evidence['revision']))
            assert digest(archive) == evidence['archive_sha256']
            if not (directory/'artifacts').exists(): extract_verified(archive, directory/'artifacts')
        if status['stage'] != 'COMPLETED' or len(receipts) != 1:
            write(directory/'failure.json', {**status, 'receipts': len(receipts), 'logs_preserved': True})
            raise RuntimeError('Original job incomplete or ambiguous; inspect without rerunning')
        review = verify_artifacts(directory/'artifacts', source, row, evidence)
        saved = {**status, 'row': row, 'verified': True, 'review': review, 'evidence': evidence,
            'source_sha256': digest(SOURCE), 'guard_sha256': digest(directory/'launch.json')}
        write_new(directory/'verified.json', saved); results.append(saved)
        print(json.dumps({'verified': row['name'], 'games': review['games']}), flush=True)
    report = {'checked_at': now(), 'complete': len(results) == len(source['rows']),
        'verified_jobs': len(results), 'expected_jobs': len(source['rows']), 'jobs': results,
        'original_unverified_statuses': states, 'source_sha256': digest(SOURCE),
        'qualified': False, 'reserved_final_seeds_used': False}
    write(OUT/'collection-state.json', report)
    if report['complete'] and not RESULT.exists():
        assert sum(r['review']['games'] for r in results) == 26880; write_new(RESULT, report)
    return {k: report[k] for k in ('complete', 'verified_jobs', 'expected_jobs')}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__); parser.add_argument('operation', choices=['prepare', 'upload', 'launch', 'collect'])
    parser.add_argument('--execute', action='store_true'); parser.add_argument('--limit', type=int, default=64)
    args = parser.parse_args()
    result = launch(args.execute, args.limit) if args.operation == 'launch' else globals()[args.operation]()
    print(json.dumps(result), flush=True)
