"""Four bounded runtime pilots for the frozen current-engine confirmation.

Reuse the exercised source uploader and independent game collector. The new
launcher accepts only the four prepared controls, keeps exclusive durable
intents, and cannot retry an ambiguous or failed submission or launch the grid.
"""
import argparse
from datetime import datetime, timezone
import fcntl
import importlib.util
import json
from pathlib import Path
import re
import tarfile

from huggingface_hub import HfApi, get_token
import conservative_auction_bootstrap_recovery_v1 as bootstrap_cache
from public_policy_development_job_v1 import digest, read, write

ROOT = Path(__file__).resolve().parents[2]
LOCAL = ROOT / 'ai/runs/current-auction-runtime-prepared-v1'
OUT = ROOT / 'ai/runs/current-auction-runtime-hf-v1'
SOURCE = ROOT / 'ai/strong/current-auction-runtime-source-v1.json'
RESULT = ROOT / 'ai/strong/current-auction-runtime-results-v1.json'
ARCHIVE = ROOT / 'ai/runs/strong-source-current-auction-runtime-v1.tgz'
PROTOCOL = ROOT / 'ai/strong/current-auction-confirmation-protocol-v1.json'


def module(filename):
    spec = importlib.util.spec_from_file_location('current_auction_previous_runtime', Path(__file__).with_name(filename))
    value = importlib.util.module_from_spec(spec); spec.loader.exec_module(value); return value


previous = module('manage-conservative-auction-runtime-v2.py')
BOOTSTRAP = bootstrap_cache.cached_bootstrap(previous.BOOTSTRAP, read(bootstrap_cache.CACHE))


def now(): return datetime.now(timezone.utc).isoformat()


def save(path, value):
    with Path(path).open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False); stream.write('\n')


def prerequisites():
    prep = read(LOCAL / 'prepared.json'); valid = read(LOCAL / 'validated.json')
    assert valid['passed'] and valid['jobs_validated'] == 4 and valid['games_executed'] == 0
    assert valid['prepared_sha256'] == digest(LOCAL / 'prepared.json')
    assert prep['preparer_sha256'] == digest(Path(__file__).with_name('prepare-current-auction-confirmation-v1.py'))
    assert digest(PROTOCOL) == prep['protocol_sha256']
    assert digest(LOCAL / 'source/source-manifest.json') == prep['source_manifest_sha256']
    pins = read(LOCAL / 'source/source-manifest.json')
    assert set(pins) | {'source-manifest.json'} == {str(p.relative_to(LOCAL / 'source')) for p in (LOCAL / 'source').rglob('*') if p.is_file()}
    assert all(digest(LOCAL / 'source' / p) == sha for p, sha in pins.items())
    assert digest(ROOT / 'ai/strong/current-engine-auction-evidence-v2.json') == prep['runtime_evidence_sha256']
    assert len(prep['rows']) == 4 and sum(r['shard']['games'] for r in prep['rows']) == prep['games'] == 64
    assert {(r['arm'], r['players']) for r in prep['rows']} == {(a,n) for a in ('filter','conservative_population') for n in (2,6)}
    return prep


def prepare():
    prep = prerequisites()
    for path in (OUT, ARCHIVE, SOURCE, RESULT):
        assert not path.exists(), 'Inspect existing source or execution before retrying'
    OUT.mkdir(); source = LOCAL / 'source'; pins = read(source / 'source-manifest.json')
    with tarfile.open(ARCHIVE, 'w:gz') as bundle:
        for name in sorted(set(pins) | {'source-manifest.json'}):
            path = source / name; assert path.is_file() and not path.is_symlink()
            info = bundle.gettarinfo(path, arcname=name)
            info.uid = info.gid = info.mtime = 0; info.uname = info.gname = ''
            with path.open('rb') as stream: bundle.addfile(info, stream)
    code_paths = [Path(__file__), Path(previous.__file__), Path(bootstrap_cache.__file__), bootstrap_cache.CACHE,
        Path(__file__).with_name('test_current_auction_runtime_v1.py')]
    p = {**prep, 'archive': ARCHIVE.name, 'sha256': digest(ARCHIVE), 'bytes': ARCHIVE.stat().st_size,
        'entry_sha256': digest(source / 'public_policy_development_job_v1.py'),
        'measured_entry_sha256': digest(source / 'public_policy_measured_job_v1.py'),
        'runner_sha256': digest(source / 'artifact/ai/strong/public_policy_final_runner_v1.py'),
        'code_hashes': {str(path.relative_to(ROOT)): digest(path) for path in code_paths},
        'bootstrap_sha256': bootstrap_cache.sha_text(BOOTSTRAP),
        'prepared_source_sha256': digest(LOCAL / 'prepared.json'),
        'tests_sha256': digest(ROOT / 'ai/runs/current-auction-runtime-tests-v1.log')}
    test = (ROOT / 'ai/runs/current-auction-runtime-tests-v1.log').read_text()
    assert 'Ran 5 tests' in test and test.rstrip().endswith('OK')
    save(OUT / 'prepared.json', p)
    return {'prepared': True, 'jobs': 4, 'games': 64}


def prepared():
    prerequisites(); p = read(OUT / 'prepared.json')
    assert p['sha256'] == digest(ARCHIVE) and p['prepared_source_sha256'] == digest(LOCAL / 'prepared.json')
    assert p['bootstrap_sha256'] == bootstrap_cache.sha_text(BOOTSTRAP)
    assert all(digest(ROOT / name) == sha for name, sha in p['code_hashes'].items())
    assert p['tests_sha256'] == digest(ROOT / 'ai/runs/current-auction-runtime-tests-v1.log')
    return p


def source_checked():
    p = prepared(); source = read(SOURCE)
    assert source['preparation_sha256'] == digest(OUT / 'prepared.json') and source['remote_archive_verified']
    assert all(source[k] == value for k, value in p.items())
    return source


def launch_once(api, directory, source, row, token):
    assert row in source['rows'] and row['shard']['seed'] == f"current-auction-runtime-v1-{row['players']}p"
    assert row['arm'] in ('filter', 'conservative_population') and row['players'] in (2, 6)
    assert row['shard']['start'] == 0 and row['shard']['deals'] == 1 and row['shard']['games'] == 4*row['players']
    assert row['flavor'] == 'cpu-upgrade' and row['timeout'] in ('2h', '5h')
    directory = Path(directory); directory.mkdir(parents=True, exist_ok=True)
    with (directory / '.launch.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        path = directory / 'launch.json'
        if path.exists():
            guard = read(path)
            assert guard['stage'] == 'launched' and guard['source'] == source and guard['row'] == row, 'Reconcile original unknown launch; no retries'
            assert re.fullmatch('[a-f0-9]{24}', guard['job_id'])
            return guard
        guard = {'stage': 'launch_intent', 'created_at': now(), 'source': source, 'row': row}
        save(path, guard)
        try:
            env = {'SOURCE_ARCHIVE': source['archive'], 'SOURCE_REVISION': source['revision'],
                'SOURCE_SHA256': source['sha256'], 'SOURCE_MANIFEST_SHA256': source['source_manifest_sha256'],
                'PROTOCOL_SHA256': source['protocol_sha256'], 'PILOT_JOB': row['job'], 'PILOT_NAME': row['name'],
                'HF_HUB_DISABLE_PROGRESS_BARS': '1', 'PYTHONDONTWRITEBYTECODE': '1'}
            job = api.run_job(image='python:3.11-slim-bookworm', command=['bash', '-lc', BOOTSTRAP],
                env=env, secrets={'HF_TOKEN': token}, flavor=row['flavor'], timeout=row['timeout'],
                labels={'project': 'powergrid-ai', 'stage': 'current-auction-runtime-v1'})
            guard.update(stage='launched', job_id=job.id)
        except BaseException as error:
            guard.update(stage='launch_unknown', failure_type=type(error).__name__); raise
        finally: write(path, guard)
        return guard


def launch(execute=False):
    source = source_checked()
    if not execute: return {'execute': False, 'jobs': 4, 'games': 64, 'grid_admitted': False}
    token = get_token(); assert token
    output = []
    for row in source['rows']:
        guard = launch_once(HfApi(), OUT / row['name'], source, row, token)
        item = {'name': row['name'], 'job_id': guard['job_id'], 'stage': guard['stage']}
        output.append(item); print(json.dumps(item), flush=True)
    return {'original_jobs': output, 'grid_admitted': False}


# Only redirect the generic uploader/collector in this freshly loaded module.
# Its historical files, source constants on disk and run directories stay intact.
previous.LOCAL, previous.OUT, previous.SOURCE, previous.RESULT, previous.ARCHIVE = LOCAL, OUT, SOURCE, RESULT, ARCHIVE
previous.prepared, previous.source_checked = prepared, source_checked


def collect():
    OUT.mkdir(exist_ok=True)
    with (OUT / '.collection.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return previous.collect()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('operation', choices=['prepare', 'upload', 'launch', 'collect'])
    parser.add_argument('--execute', action='store_true'); args = parser.parse_args()
    value = launch(args.execute) if args.operation == 'launch' else previous.upload() if args.operation == 'upload' else globals()[args.operation]()
    print(json.dumps(value), flush=True)
