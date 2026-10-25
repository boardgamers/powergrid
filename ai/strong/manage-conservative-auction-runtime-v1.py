"""Four bounded HF runtime pilots; never submits the development/final grid."""
import argparse
from datetime import datetime, timezone
import fcntl
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re
import subprocess
import sys
import tarfile

from huggingface_hub import HfApi, get_token, hf_hub_download
from public_policy_development_job_v1 import read, write, digest
from public_policy_final_audit_v1 import audit_shard
from public_policy_final_contract_v1 import audit_execution_binding
from population_policy_verification import extract_verified

ROOT = Path(__file__).resolve().parents[2]
LOCAL = ROOT/'ai/runs/conservative-auction-runtime-prepared-v1'
OUT = ROOT/'ai/runs/conservative-auction-runtime-hf-v1'
SOURCE = ROOT/'ai/strong/conservative-auction-runtime-source-v1.json'
RESULT = ROOT/'ai/strong/conservative-auction-runtime-results-v1.json'
ARCHIVE = ROOT/'ai/runs/strong-source-conservative-auction-runtime-v1.tgz'
REPO = 'coyotte508/powergrid-ai-training-v1'


def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(filename))
    result = importlib.util.module_from_spec(spec); spec.loader.exec_module(result)
    return result


original = module('original_portability', 'manage-public-policy-development-hf-v1.py')
preflight = module('conservative_preflight', 'prepare-conservative-auction-runtime-v1.py')
# Keep the previously exercised dependency and archive verification bootstrap.
BOOTSTRAP = original.BOOTSTRAP.split('python -u -B /workspace/source/public_policy_development_job_v1.py')[0] + r'''
python -u -B /workspace/source/public_policy_measured_job_v1.py \
  --source /workspace/source --manifest-sha256 "$SOURCE_MANIFEST_SHA256" \
  --protocol-sha256 "$PROTOCOL_SHA256" --job "$PILOT_JOB" \
  --output "/workspace/output/$PILOT_NAME" --scope runtime \
  --source-revision "$SOURCE_REVISION" --source-archive-sha256 "$SOURCE_SHA256" --upload
'''


def now(): return datetime.now(timezone.utc).isoformat()


def write_new(path, value):
    with Path(path).open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False); stream.write('\n')


def prerequisites():
    prep = preflight.pinned(); check = read(LOCAL/'verified.json')
    assert check['complete'] and check['fixtures'] == 72 and check['caps'] == 0
    assert check['continuations_exact_to_archived_components'] == 1992
    assert check['prepared_sha256'] == digest(LOCAL/'prepared.json')
    assert check['decisions_sha256'] == digest(LOCAL/'decisions.jsonl')
    assert check['source_manifest_sha256'] == prep['source_manifest_sha256']
    return prep


def prepare():
    prep = prerequisites()
    assert not OUT.exists() and not ARCHIVE.exists() and not SOURCE.exists()
    OUT.mkdir(); root = LOCAL/'source'; pins = read(root/'source-manifest.json')
    with tarfile.open(ARCHIVE, 'w:gz') as bundle:
        for name in sorted(set(pins)|{'source-manifest.json'}):
            path = root/name; assert path.is_file() and not path.is_symlink()
            info = bundle.gettarinfo(path, arcname=name)
            info.uid = info.gid = info.mtime = 0; info.uname = info.gname = ''
            with path.open('rb') as stream: bundle.addfile(info, stream)
    calibration = []
    for n in (2, 6):
        path = ROOT/f'ai/runs/population-hybrid-runtime-collected-v2/population-hybrid-runtime-v2-{n}p/verified.json'
        calibration.append({'path': str(path.relative_to(ROOT)), 'sha256': digest(path),
                            'seconds': read(path)['summary']['wall_seconds']})
    bound = 900 + 4*max(row['seconds'] for row in calibration)
    timeout = math.ceil(bound/(.75*3600))
    assert timeout == 5
    p = {'created_at': now(), 'archive': ARCHIVE.name, 'sha256': digest(ARCHIVE),
         'bytes': ARCHIVE.stat().st_size, 'source_manifest_sha256': prep['source_manifest_sha256'],
         'protocol_sha256': prep['protocol_sha256'], 'source_files': len(pins),
         'entry_sha256': digest(root/'public_policy_development_job_v1.py'),
         'measured_entry_sha256': digest(root/'public_policy_measured_job_v1.py'),
         'runner_sha256': digest(root/'artifact/ai/strong/public_policy_final_runner_v1.py'),
         'rows': [row for row in prep['rows'] if row['execute_pilot']],
         'preflight_sha256': digest(LOCAL/'verified.json'), 'launcher_sha256': digest(__file__),
         'bootstrap_sha256': hashlib.sha256(BOOTSTRAP.encode()).hexdigest(),
         'flavor': 'cpu-upgrade', 'timeout': f'{timeout}h', 'workers': 4, 'games': 64,
         'calibration': calibration, 'estimated_seconds_with_setup': bound,
         'resource_reason': '900s setup plus four times the older measured worst endpoint, within 75% of the timeout. Allowance covers added population and changed concurrency; pilots measure the actual recipes.',
         'grid_admitted': False, 'qualification_eligible': False, 'reserved_final_seeds_used': False}
    assert len(p['rows']) == 4 and sum(r['shard']['games'] for r in p['rows']) == 64
    write_new(OUT/'prepared.json', p)
    return {'prepared': True, 'jobs': 4, 'games': 64, 'timeout': p['timeout']}


def prepared():
    prerequisites(); p = read(OUT/'prepared.json')
    assert digest(ARCHIVE) == p['sha256'] and digest(__file__) == p['launcher_sha256']
    assert digest(LOCAL/'verified.json') == p['preflight_sha256']
    assert hashlib.sha256(BOOTSTRAP.encode()).hexdigest() == p['bootstrap_sha256']
    return p


def upload():
    p = prepared()
    with (OUT/'.upload.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if SOURCE.exists():
            source = read(SOURCE); assert source['preparation_sha256'] == digest(OUT/'prepared.json')
            return {'existing_source_revision': source['revision']}
        write_new(OUT/'upload-intent.json', {'created_at': now(), 'archive': p['archive'], 'sha256': p['sha256']})
        commit = HfApi().upload_file(repo_id=REPO, repo_type='dataset', path_or_fileobj=ARCHIVE, path_in_repo=p['archive'])
        receipt = {'repo': REPO, 'revision': commit.oid, 'archive': p['archive'], 'sha256': p['sha256']}
        write_new(OUT/'upload-receipt.json', receipt)
        assert digest(hf_hub_download(REPO, p['archive'], repo_type='dataset', revision=commit.oid)) == p['sha256']
        source = {**p, **receipt, 'preparation_sha256': digest(OUT/'prepared.json'), 'remote_archive_verified': True}
        write_new(SOURCE, source)
        return receipt


def source_checked():
    p = prepared(); source = read(SOURCE)
    assert source['preparation_sha256'] == digest(OUT/'prepared.json') and source['remote_archive_verified']
    assert all(source[k] == value for k, value in p.items())
    return source


def local_check():
    """Repeat eight existing engineering games solely to exercise measurement."""
    source = source_checked(); root = LOCAL/'source'; dest = OUT/'local-measured-smoke'
    assert not dest.exists() and not (OUT/'local-check.json').exists(), 'Preserve original measurement check'
    with (OUT/'local-check.log').open('x') as log:
        subprocess.run([sys.executable, '-u', '-B', str(root/'public_policy_measured_job_v1.py'),
            '--source', str(root), '--manifest-sha256', source['source_manifest_sha256'],
            '--protocol-sha256', source['protocol_sha256'], '--job', 'filter-offset-2p.job.json',
            '--output', str(dest), '--scope', 'runtime', '--source-revision', source['revision'],
            '--source-archive-sha256', source['sha256']], stdout=log, stderr=subprocess.STDOUT, check=True)
    spec = read(root/'filter-offset-2p.job.json'); contract = read(root/spec['contract'])
    expected = {**source, 'job_spec_sha256': digest(root/'filter-offset-2p.job.json'),
                'candidate_sha256': digest(root/spec['candidate']), 'contract_sha256': digest(root/spec['contract']),
                'identity': contract['identity'], 'shard': contract['shard']}
    result = original.verify_artifacts(dest/'job', expected, {'manifest_sha256': digest(dest/'job/manifest.json')})
    measurement = read(dest/'measurement.json'); check_measurement(measurement)
    assert measurement['provenance'] == read(dest/'job/job-status.json')['provenance']
    assert '"game_progress"' in (OUT/'local-check.log').read_text()
    write_new(OUT/'local-check.json', {'complete': True, 'review': result,
        'measurement': measurement['measurement'], 'source_sha256': digest(SOURCE),
        'manifest_sha256': digest(dest/'manifest.json')})
    return {'measurement_check': 'complete', 'games': result['games'], 'exact_decisions': result['decisions']}


def launch_once(api, directory, source, row, token):
    assert row in source['rows'] and row['execute_pilot'] and row['arm'] != 'filter'
    directory = Path(directory)
    with (directory/'.launch.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        path = directory/'launch.json'
        if path.exists():
            guard = read(path)
            assert guard['stage'] == 'launched' and guard['source'] == source and guard['row'] == row, 'Reconcile original uncertain launch'
            assert re.fullmatch('[a-f0-9]{24}', guard['job_id'])
            return guard
        guard = {'stage': 'launch_intent', 'created_at': now(), 'source': source, 'row': row}
        write_new(path, guard)
        try:
            env = {'SOURCE_ARCHIVE': source['archive'], 'SOURCE_REVISION': source['revision'],
                   'SOURCE_SHA256': source['sha256'], 'SOURCE_MANIFEST_SHA256': source['source_manifest_sha256'],
                   'PROTOCOL_SHA256': source['protocol_sha256'], 'PILOT_JOB': row['job'], 'PILOT_NAME': row['name'],
                   'HF_HUB_DISABLE_PROGRESS_BARS': '1', 'PYTHONDONTWRITEBYTECODE': '1'}
            remote = api.run_job(image='python:3.11-slim-bookworm', command=['bash', '-lc', BOOTSTRAP],
                flavor=source['flavor'], timeout=source['timeout'], name=row['name'], env=env,
                secrets={'HF_TOKEN': token}, labels={'project': 'powergrid-ai', 'stage': 'conservative-auction-runtime-v1'})
            guard.update(stage='launched', job_id=remote.id)
        except BaseException as error:
            guard.update(stage='launch_unknown', failure_type=type(error).__name__); raise
        finally: write(path, guard)
        return guard


def launch(execute=False):
    source = source_checked(); proof = read(OUT/'local-check.json')
    assert proof['complete'] and proof['source_sha256'] == digest(SOURCE)
    assert proof['manifest_sha256'] == digest(OUT/'local-measured-smoke/manifest.json')
    test = ROOT/'ai/runs/conservative-auction-runtime-tests-v1.log'
    assert 'Ran 7 tests' in test.read_text() and test.read_text().rstrip().endswith('OK')
    if not execute: return {'execute': False, 'jobs': 4, 'games': 64}
    token = get_token(); assert token; submitted = []
    for row in source['rows']:
        directory = OUT/row['name']; directory.mkdir(exist_ok=True)
        guard = launch_once(HfApi(), directory, source, row, token)
        submitted.append({'name': row['name'], 'job_id': guard['job_id'], 'stage': guard['stage']})
        print(json.dumps(submitted[-1]), flush=True)
    return {'original_jobs': submitted, 'grid_admitted': False}


def check_measurement(status):
    assert status['stage'] == 'complete' and not status['qualified'] and not status['reserved_final_seeds_used']
    m = status['measurement']
    assert all(math.isfinite(m[k]) and m[k] > 0 for k in ('seconds', 'cpu_seconds', 'sampled_peak_total_rss_bytes', 'memory_samples'))
    assert m['memory_sampling_period_seconds'] == .2 and m['includes_startup_and_validation']


def verify_artifacts(folder, source, row, evidence):
    pins = read(folder/'manifest.json')
    assert digest(folder/'manifest.json') == evidence['manifest_sha256']
    assert set(pins)|{'manifest.json'} == {str(p.relative_to(folder)) for p in folder.rglob('*') if p.is_file()}
    assert all(digest(folder/name) == sha for name, sha in pins.items())
    measurement = read(folder/'measurement.json'); check_measurement(measurement)
    assert measurement['case'] == row['name'] and measurement['scope'] == 'runtime'
    assert measurement['experiment_protocol_sha256'] == source['protocol_sha256']
    assert measurement['measured_entry_sha256'] == source['measured_entry_sha256']
    expected = {k: source[k] for k in ('source_manifest_sha256', 'entry_sha256')}
    expected.update({k: row[k] for k in ('job_spec_sha256', 'candidate_sha256', 'contract_sha256', 'identity', 'shard')})
    expected.update(source_revision=source['revision'], source_archive_sha256=source['sha256'])
    assert measurement['provenance'] == expected
    inner = folder/'job'; status = read(inner/'job-status.json')
    assert status['stage'] == 'complete' and status['provenance'] == expected
    assert digest(inner/'job-status.json') == measurement['job_status_sha256']
    assert digest(inner/'source-manifest.json') == source['source_manifest_sha256']
    assert digest(inner/'job-spec.json') == row['job_spec_sha256']
    target = inner/'evaluation'
    assert digest(target/'evaluation.json') == status['evaluation_sha256']
    assert digest(target/'audit.json') == status['audit_sha256']
    audit = audit_shard(target, row['shard'], row['identity'], reserved=False)
    binding = audit_execution_binding(target, row['identity'], source['runner_sha256'])
    assert read(target/'audit.json') == {**audit, 'execution_binding': binding}
    assert status['counts'] == measurement['counts'] == audit['counts']
    assert status['games'] == measurement['games'] == row['shard']['games']
    return {'games': status['games'], 'audit': audit, 'measurement': measurement['measurement']}


def collect():
    source = source_checked(); results = []
    for row in source['rows']:
        directory = OUT/row['name']; guard = read(directory/'launch.json')
        assert guard['stage'] == 'launched' and guard['source'] == source and guard['row'] == row
        if (directory/'verified.json').exists():
            result = read(directory/'verified.json')
            assert result['job_id'] == guard['job_id'] and result['row'] == row
            assert verify_artifacts(directory/'artifacts', source, row, result['evidence']) == result['review']
            results.append(result); continue
        api = HfApi(); stage = api.inspect_job(job_id=guard['job_id']).status.stage
        status = {'checked_at': now(), 'job_id': guard['job_id'], 'stage': stage, 'name': row['name']}
        write(directory/'status.json', status); print(json.dumps(status), flush=True)
        if stage in ('SCHEDULING', 'RUNNING'): continue
        lines = '\n'.join(str(line) for line in api.fetch_job_logs(job_id=guard['job_id'], follow=False))
        (directory/'job.log').write_text(lines); receipts = []
        for line in lines.splitlines():
            if not line.startswith('{'): continue
            try: receipt = json.loads(line)
            except json.JSONDecodeError: continue
            if set(receipt) == {'case', 'status', 'evidence'} and receipt['case'] == row['name']: receipts.append(receipt)
        if len(receipts) == 1:
            evidence = receipts[0]['evidence']
            assert evidence['repo'] == 'coyotte508/powergrid-ai-germany-v1'
            assert evidence['archive_path'] == 'archives/'+row['name']+'.tgz' and evidence['remote_archive_verified']
            assert re.fullmatch('[a-f0-9]{40}', evidence['revision'])
            archive = Path(hf_hub_download(evidence['repo'], evidence['archive_path'], revision=evidence['revision']))
            assert digest(archive) == evidence['archive_sha256']
            if not (directory/'artifacts').exists(): extract_verified(archive, directory/'artifacts')
        if stage != 'COMPLETED' or len(receipts) != 1:
            write(directory/'failure.json', {**status, 'receipts': len(receipts), 'logs_preserved': True})
            raise RuntimeError('Inspect original incomplete or ambiguous job; no automatic retry')
        review = verify_artifacts(directory/'artifacts', source, row, evidence)
        result = {**status, 'row': row, 'evidence': evidence, 'review': review,
                  'guard_sha256': digest(directory/'launch.json'), 'verified': True}
        write_new(directory/'verified.json', result); results.append(result)
    report = {'checked_at': now(), 'verified_jobs': len(results), 'jobs': results,
              'complete': len(results) == 4, 'source_sha256': digest(SOURCE), 'grid_admitted': False}
    write(OUT/'collection-state.json', report)
    if report['complete'] and not RESULT.exists():
        assert sum(r['review']['games'] for r in results) == 64
        write_new(RESULT, report)
    return {'verified_jobs': len(results), 'complete': report['complete'], 'grid_admitted': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('operation', choices=['prepare', 'upload', 'local-check', 'launch', 'collect'])
    parser.add_argument('--execute', action='store_true'); args = parser.parse_args()
    result = launch(args.execute) if args.operation == 'launch' else globals()[args.operation.replace('-', '_')]()
    print(json.dumps(result), flush=True)
