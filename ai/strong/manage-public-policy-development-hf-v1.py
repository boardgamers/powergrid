"""One HF portability smoke using the exact locally verified development source.

This is an eight-game engineering repeat, not a new strength screen or final
evaluation. Source uploads and job submissions have durable exclusive intents;
unknown outcomes must be reconciled instead of retried.
"""
import argparse
from datetime import datetime, timezone
import fcntl
import hashlib
import json
from pathlib import Path
import re
import tarfile

from huggingface_hub import HfApi, get_token, hf_hub_download
from public_policy_development_job_v1 import read, write, digest
from public_policy_final_audit_v1 import audit_shard
from public_policy_final_contract_v1 import audit_execution_binding
from public_policy_arena_v1 import semantic, arena_semantic
from population_policy_verification import extract_verified

ROOT = Path(__file__).resolve().parents[2]
LOCAL = ROOT/'ai/runs/public-policy-development-job-preflight-v1'
OUT = ROOT/'ai/runs/public-policy-development-hf-v1'
SOURCE = ROOT/'ai/strong/public-policy-development-hf-source-v1.json'
RESULT = ROOT/'ai/strong/public-policy-development-hf-result-v1.json'
REPO = 'coyotte508/powergrid-ai-training-v1'
NAME = 'public-policy-development-hf-v1'
JOB = 'filter-offset-2p.job.json'
ARCHIVE = ROOT/'ai/runs/strong-source-public-policy-development-hf-v1.tgz'
BOOTSTRAP = r'''
set -euo pipefail
apt-get update -qq
apt-get install -y --no-install-recommends libstdc++6 libgomp1 ca-certificates >/dev/null
python -m pip install --quiet --timeout 120 --retries 5 huggingface_hub==2.0.0 onnxruntime==1.30.0 numpy==2.4.6
python - <<'INNER'
import hashlib,json,os,tarfile,urllib.request
from pathlib import Path
from huggingface_hub import hf_hub_download
urllib.request.urlretrieve('https://nodejs.org/dist/v24.14.0/node-v24.14.0-linux-x64.tar.xz','/tmp/node.tar.xz')
with tarfile.open('/tmp/node.tar.xz') as bundle: bundle.extractall('/opt',filter='data')
file=hf_hub_download('coyotte508/powergrid-ai-training-v1',os.environ['SOURCE_ARCHIVE'],repo_type='dataset',revision=os.environ['SOURCE_REVISION'])
assert hashlib.sha256(Path(file).read_bytes()).hexdigest()==os.environ['SOURCE_SHA256']
root=Path('/workspace/source'); root.mkdir(parents=True,exist_ok=False)
with tarfile.open(file) as bundle:
    members=bundle.getmembers(); names=[m.name for m in members]
    assert len(names)==len(set(names))
    assert all(m.isfile() and not Path(m.name).is_absolute() and '..' not in Path(m.name).parts for m in members)
    manifest=bundle.extractfile('source-manifest.json').read()
    assert hashlib.sha256(manifest).hexdigest()==os.environ['SOURCE_MANIFEST_SHA256']
    pins=json.loads(manifest); assert set(names)==set(pins)|{'source-manifest.json'}
    assert all(hashlib.sha256(bundle.extractfile(name).read()).hexdigest()==sha for name,sha in pins.items())
    bundle.extractall(root,filter='data')
INNER
export PATH=/opt/node-v24.14.0-linux-x64/bin:$PATH
python -u -B /workspace/source/public_policy_development_job_v1.py \
  --source /workspace/source --manifest-sha256 "$SOURCE_MANIFEST_SHA256" \
  --job filter-offset-2p.job.json --output /workspace/output/public-policy-development-hf-v1 \
  --source-revision "$SOURCE_REVISION" --source-archive-sha256 "$SOURCE_SHA256" --execute --upload
'''


def now(): return datetime.now(timezone.utc).isoformat()


def write_new(path, value):
    with Path(path).open('x') as stream:
        json.dump(value, stream, indent=2); stream.write('\n')


def prerequisites():
    proof = read(ROOT/'ai/strong/public-policy-development-job-evidence-v1.json')
    prep, result = read(LOCAL/'prepared.json'), read(LOCAL/'result.json')
    assert proof['complete'] and proof['archive']['remote_archive_verified']
    assert result['complete'] and result['games'] == 8 and result['decisions'] == 1607
    assert result['all_public_decisions_and_terminals_exact'] and result['runtime_manifest_unchanged']
    assert prep['source_manifest_sha256'] == proof['source_manifest_sha256'] == digest(LOCAL/'source/source-manifest.json')
    assert all(digest(LOCAL/'source'/name) == sha for name, sha in read(LOCAL/'source/source-manifest.json').items())
    spec = read(LOCAL/'source'/JOB); assert spec['descriptor'] == 'policy-filter.json' and spec['workers'] == 4
    contract = read(LOCAL/'source'/spec['contract'])
    assert contract['purpose'] == 'engineering' and contract['shard']['start'] == 4 and contract['shard']['games'] == 8
    return proof, prep, spec, contract


def prepare():
    proof, prep, spec, contract = prerequisites()
    assert not SOURCE.exists() and not ARCHIVE.exists() and not OUT.exists(), 'Inspect original source/upload outcome'
    OUT.mkdir()
    root = LOCAL/'source'; pins = read(root/'source-manifest.json')
    with tarfile.open(ARCHIVE, 'w:gz') as bundle:
        for name in sorted(set(pins)|{'source-manifest.json'}):
            path = root/name; assert path.is_file() and not path.is_symlink()
            info = bundle.gettarinfo(path, arcname=name)
            info.uid = info.gid = info.mtime = 0; info.uname = info.gname = ''
            with path.open('rb') as stream: bundle.addfile(info, stream)
    preparation = {'created_at': now(), 'archive': ARCHIVE.name, 'sha256': digest(ARCHIVE),
        'bytes': ARCHIVE.stat().st_size, 'source_manifest_sha256': prep['source_manifest_sha256'],
        'source_files': len(pins), 'job': JOB, 'job_spec_sha256': digest(root/JOB),
        'local_evidence': proof['archive'], 'local_result_sha256': digest(LOCAL/'result.json'),
        'entry_sha256': digest(root/'public_policy_development_job_v1.py'),
        'candidate_sha256': digest(root/spec['candidate']), 'contract_sha256': digest(root/spec['contract']),
        'identity': contract['identity'], 'shard': contract['shard'],
        'launcher_sha256': digest(__file__), 'bootstrap_sha256': hashlib.sha256(BOOTSTRAP.encode()).hexdigest(),
        'flavor': 'cpu-upgrade', 'timeout': '1h', 'games': 8, 'workers': 4,
        'scope': 'Single filtered-policy engineering repeat for HF source/job/upload/collector portability.',
        'reserved_final_seeds_used': False, 'qualification_eligible': False, 'gradient_updates': 0}
    write_new(OUT/'prepared.json', preparation)
    print(json.dumps({k: preparation[k] for k in ('archive', 'sha256', 'source_files', 'games')}), flush=True)


def prepared():
    prerequisites(); p = read(OUT/'prepared.json')
    assert digest(ARCHIVE) == p['sha256'] and digest(LOCAL/'result.json') == p['local_result_sha256']
    assert digest(__file__) == p['launcher_sha256']
    assert hashlib.sha256(BOOTSTRAP.encode()).hexdigest() == p['bootstrap_sha256']
    return p


def upload():
    p = prepared()
    with (OUT/'.upload.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if SOURCE.exists():
            source = read(SOURCE); assert source['preparation_sha256'] == digest(OUT/'prepared.json')
            return source
        write_new(OUT/'upload-intent.json', {'created_at': now(), 'archive': p['archive'], 'sha256': p['sha256']})
        commit = HfApi().upload_file(repo_id=REPO, repo_type='dataset', path_or_fileobj=ARCHIVE, path_in_repo=p['archive'])
        receipt = {'repo': REPO, 'revision': commit.oid, 'archive': p['archive'], 'sha256': p['sha256']}
        write_new(OUT/'upload-receipt.json', receipt)
        assert digest(hf_hub_download(REPO, p['archive'], repo_type='dataset', revision=commit.oid)) == p['sha256']
        source = {**p, **receipt, 'preparation_sha256': digest(OUT/'prepared.json'), 'remote_archive_verified': True}
        write_new(SOURCE, source)
        return source


def launch_once(api, directory, source, token):
    """Single-submission primitive; unknown handles remain a hard stop."""
    directory = Path(directory)
    with (directory/'.launch.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        path = directory/'launch.json'
        if path.exists():
            guard = read(path)
            assert guard['stage'] == 'launched' and guard['source'] == source, 'Reconcile original uncertain launch'
            assert re.fullmatch('[a-f0-9]{24}', guard['job_id'])
            return guard
        guard = {'stage': 'launch_intent', 'created_at': now(), 'name': NAME, 'source': source}
        write_new(path, guard)
        try:
            env = {'SOURCE_ARCHIVE': source['archive'], 'SOURCE_REVISION': source['revision'],
                   'SOURCE_SHA256': source['sha256'], 'SOURCE_MANIFEST_SHA256': source['source_manifest_sha256'],
                   'HF_HUB_DISABLE_PROGRESS_BARS': '1', 'PYTHONDONTWRITEBYTECODE': '1'}
            remote = api.run_job(image='python:3.11-slim-bookworm', command=['bash', '-lc', BOOTSTRAP],
                flavor=source['flavor'], timeout=source['timeout'], name=NAME, env=env,
                secrets={'HF_TOKEN': token}, labels={'project': 'powergrid-ai', 'stage': NAME})
            guard.update(stage='launched', job_id=remote.id)
        except BaseException as error:
            guard.update(stage='launch_unknown', failure_type=type(error).__name__); raise
        finally:
            write(path, guard)
        return guard


def launch(execute=False):
    p = prepared(); source = read(SOURCE)
    assert source['preparation_sha256'] == digest(OUT/'prepared.json') and source['remote_archive_verified']
    assert source['sha256'] == p['sha256']
    test = ROOT/'ai/runs/public-policy-development-hf-tests-v1.log'
    assert 'Ran 5 tests' in test.read_text() and test.read_text().rstrip().endswith('OK')
    if not execute: return {'execute': False, 'jobs': 1, 'games': 8}
    token = get_token(); assert token
    return launch_once(HfApi(), OUT, source, token)


def verify_artifacts(folder, source, evidence):
    pins = read(folder/'manifest.json')
    assert digest(folder/'manifest.json') == evidence['manifest_sha256']
    assert set(pins)|{'manifest.json'} == {str(p.relative_to(folder)) for p in folder.rglob('*') if p.is_file()}
    assert all(digest(folder/name) == sha for name, sha in pins.items())
    assert digest(folder/'source-manifest.json') == source['source_manifest_sha256']
    assert digest(folder/'job-spec.json') == source['job_spec_sha256']
    status = read(folder/'job-status.json'); assert status['stage'] == 'complete' and status['games'] == 8
    expected = {k: source[k] for k in ('source_manifest_sha256', 'job_spec_sha256', 'entry_sha256',
                'candidate_sha256', 'contract_sha256', 'identity', 'shard')}
    expected.update(source_revision=source['revision'], source_archive_sha256=source['sha256'])
    assert status['provenance'] == expected
    target = folder/'evaluation'
    assert digest(target/'evaluation.json') == status['evaluation_sha256']
    assert digest(target/'audit.json') == status['audit_sha256']
    audit = audit_shard(target, source['shard'], source['identity'], reserved=False)
    binding = audit_execution_binding(target, source['identity'],
        digest(LOCAL/'source/artifact/ai/strong/public_policy_final_runner_v1.py'))
    assert read(target/'audit.json') == {**audit, 'execution_binding': binding}
    current = read(target/'evaluation.json'); gold = LOCAL/'filter-offset-2p/evaluation'
    original = read(gold/'evaluation.json'); decisions = 0
    for a, b in zip(current['results'], original['results'], strict=True):
        assert a['episode'] == b['episode'] and a['terminal'] == b['terminal']
        n = a['episode']; count = 0
        with (target/f'decisions-{n}.jsonl').open() as left, (gold/f'decisions-{n}.jsonl').open() as right:
            for x, y in zip(left, right, strict=True):
                x, y = json.loads(x), json.loads(y)
                request = lambda row: arena_semantic({'observations': [{'request': row['publicRequest']}], 'ended': []})
                assert request(x) == request(y)
                assert semantic(x['publicResponse']['decision']) == semantic(y['publicResponse']['decision'])
                assert x['arenaMoves'] == y['arenaMoves'] and x['arenaPlayerOrder'] == y['arenaPlayerOrder']
                count += 1
        assert count == a['decisions'] == b['decisions']; decisions += count
    assert decisions == 1607
    return {'audit': audit, 'games': 8, 'decisions': decisions, 'exact_local_comparison': True,
            'seconds': status['seconds'], 'reserved_final_seeds_used': False, 'qualification_eligible': False}


def collect():
    prepared(); source = read(SOURCE); guard = read(OUT/'launch.json')
    assert guard['stage'] == 'launched' and guard['source'] == source
    if RESULT.exists():
        result = read(RESULT)
        assert result['job_id'] == guard['job_id'] and result['source'] == source
        assert verify_artifacts(OUT/'artifacts', source, result['evidence']) == result['review']
        return result
    api = HfApi(); stage = api.inspect_job(job_id=guard['job_id']).status.stage
    status = {'checked_at': now(), 'job_id': guard['job_id'], 'authoritative_status': stage}
    write(OUT/'status.json', status)
    if stage in ('SCHEDULING', 'RUNNING'): return status
    lines = '\n'.join(str(line) for line in api.fetch_job_logs(job_id=guard['job_id'], follow=False))
    (OUT/'job.log').write_text(lines); receipts = []
    for line in lines.splitlines():
        if not line.startswith('{'): continue
        try: row = json.loads(line)
        except json.JSONDecodeError: continue
        if set(row) == {'evidence'}: receipts.append(row['evidence'])
    if stage != 'COMPLETED' or len(receipts) != 1:
        failure = {**status, 'verified': False, 'upload_receipts_found': len(receipts), 'logs_preserved': True}
        write(OUT/'failure.json', failure)
        raise RuntimeError('Original HF job not complete or upload ambiguous; inspect preserved logs, do not rerun')
    evidence = receipts[0]
    assert evidence['repo'] == 'coyotte508/powergrid-ai-germany-v1' and evidence['archive_path'] == 'archives/'+NAME+'.tgz'
    assert evidence['remote_archive_verified'] and re.fullmatch('[a-f0-9]{40}', evidence['revision'])
    archive = Path(hf_hub_download(evidence['repo'], evidence['archive_path'], revision=evidence['revision']))
    assert digest(archive) == evidence['archive_sha256']
    if not (OUT/'artifacts').exists(): extract_verified(archive, OUT/'artifacts')
    review = verify_artifacts(OUT/'artifacts', source, evidence)
    result = {**status, 'verified': True, 'source': source, 'evidence': evidence, 'review': review,
              'guard_sha256': digest(OUT/'launch.json'), 'collector_sha256': digest(__file__),
              'scope': 'Actual HF filtered-policy portability, not new strength or selected auction runtime admission.'}
    write_new(RESULT, result)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('operation', choices=['prepare', 'upload', 'launch', 'collect'])
    parser.add_argument('--execute', action='store_true'); args = parser.parse_args()
    assert not args.execute or args.operation == 'launch'
    result = launch(args.execute) if args.operation == 'launch' else globals()[args.operation]()
    if result is not None:
        print(json.dumps({k: result[k] for k in ('stage', 'job_id', 'revision', 'sha256', 'execute', 'jobs', 'games',
                          'authoritative_status', 'verified', 'review') if k in result}), flush=True)
