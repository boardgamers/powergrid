"""Guarded HF labeling in two waves with pinned independent verification."""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tarfile

from huggingface_hub import HfApi, get_token, hf_hub_download
from strategic_collection import ROOT, read, write, digest

PROTOCOL = ROOT/'ai/strong/policy-iteration-labels-protocol-v2.json'
SOURCE = ROOT/'ai/strong/policy-iteration-labels-source-v2.json'
PREFLIGHT = ROOT/'ai/strong/policy-iteration-labels-preflight-v2.json'
GUARDS = ROOT/'ai/runs/policy-iteration-labels-launches-v2'
VERIFIED = ROOT/'ai/runs/policy-iteration-labels-verified-v2'
STATUS = ROOT/'ai/strong/policy-iteration-labels-status-v2.json'
RESULTS = ROOT/'ai/strong/policy-iteration-labels-results-v2.json'
PREFIX = 'runs/policy-iteration-labels-v2-'

BOOTSTRAP = '''
set -euo pipefail
apt-get update -qq
apt-get install -y --no-install-recommends libstdc++6 libgomp1 ca-certificates >/dev/null
python -m pip install --quiet --timeout 120 --retries 5 huggingface_hub==2.0.0 onnxruntime==1.30.0 numpy==2.4.6
mkdir -p /workspace
python - <<'INNER'
import urllib.request,tarfile,os,hashlib
from pathlib import Path
from huggingface_hub import hf_hub_download
urllib.request.urlretrieve('https://nodejs.org/dist/v24.14.0/node-v24.14.0-linux-x64.tar.xz','/tmp/node.tar.xz')
with tarfile.open('/tmp/node.tar.xz') as bundle:bundle.extractall('/opt')
p=hf_hub_download('coyotte508/powergrid-ai-training-v1',os.environ['SOURCE_ARCHIVE'],repo_type='dataset',revision=os.environ['SOURCE_REVISION'])
assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==os.environ['SOURCE_SHA256']
with tarfile.open(p) as bundle:bundle.extractall('/workspace',filter='data')
INNER
export PATH=/opt/node-v24.14.0-linux-x64/bin:$PATH
cd /workspace
python -u ai/strong/policy_iteration_labels.py "$LABEL_SHARD" ai/runs/full-labels --upload
'''


def first_wave(p):
    groups = {}
    for shard in p['shards']:
        key = tuple(shard[k] for k in ['players', 'behavior', 'opponent', 'mode'])
        groups.setdefault(key, shard['id'])
    assert len(groups) == 60
    return set(groups.values())


def verify_local(out, source, shard):
    v = read(out/'verified.json')
    assert v['verified'] and v['source'] == source and v['shard'] == shard
    for file, sha in v['artifacts'].items():
        assert digest(out/file) == sha
    return v


def launch(wave, execute, limit):
    p, s, preflight = read(PROTOCOL), read(SOURCE), read(PREFLIGHT)
    assert preflight['passed'] and preflight['source'] == s
    assert digest(PROTOCOL) == s['protocol_sha256']
    for file, sha in s['overlays'].items():
        assert digest(ROOT/file) == sha
    first = first_wave(p)
    if wave == 'remaining':
        for shard in p['shards']:
            if shard['id'] in first:
                verify_local(VERIFIED/shard['id'], s, shard)
    wanted = [r for r in p['shards'] if (r['id'] in first) == (wave == 'first')]
    GUARDS.mkdir(exist_ok=True)
    with (GUARDS/'.launch.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        pending = []
        for shard in wanted:
            assert shard['admission']['conservative_seconds'] <= 21600
            path = GUARDS/(shard['id'] + '.json')
            if path.exists():
                old = read(path)
                assert old['stage'] == 'launched' and re.fullmatch('[a-f0-9]{24}', old['job_id']), 'Reconcile an ambiguous launch before any retry'
                assert old['shard'] == shard and old['source'] == s
            else:
                pending.append(shard)
        if limit is not None:
            assert limit > 0
            pending = pending[:limit]
        print({'wave': wave, 'execute': execute, 'new_jobs': len(pending), 'new_root_mode_pairs': sum(len(r['root_ids']) for r in pending)}, flush=True)
        if not execute:
            return
        env = os.environ.copy()
        env['HF_TOKEN'] = get_token() or env.get('HF_TOKEN') or ''
        assert env['HF_TOKEN']
        for shard in pending:
            path = GUARDS/(shard['id'] + '.json')
            record = {'stage': 'launch_intent', 'shard': shard, 'source': s, 'wave': wave,
                      'protocol_sha256': digest(PROTOCOL), 'created_at': datetime.now(timezone.utc).isoformat(),
                      'qualification_eligible': False}
            with path.open('x') as f:
                json.dump(record, f, indent=2)
            command = ['hf', 'jobs', 'run', '--detach', '--flavor', 'cpu-performance', '--timeout', '8h',
                       '--secrets', 'HF_TOKEN', '--label', 'project=powergrid-ai', '--label', 'stage=policy-labels-v2-' + shard['id']]
            for key, value in {'SOURCE_ARCHIVE': s['archive'], 'SOURCE_REVISION': s['revision'], 'SOURCE_SHA256': s['sha256'],
                               'LABEL_SHARD': shard['id'], 'HF_HUB_DISABLE_PROGRESS_BARS': '1'}.items():
                command += ['--env', key + '=' + value]
            command += ['--', 'python:3.11-slim-bookworm', 'bash', '-lc', BOOTSTRAP]
            try:
                result = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True, check=True)
                path.with_suffix('.log').write_text(result.stdout + result.stderr)
                ids = set(re.findall(r'\b[a-f0-9]{24}\b', result.stdout))
                assert len(ids) == 1
                record.update(stage='launched', job_id=ids.pop())
            except BaseException as error:
                record.update(stage='launch_unknown', error=type(error).__name__ + ': ' + str(error))
                raise
            finally:
                write(path, record)
            print({'shard': shard['id'], 'job_id': record['job_id']}, flush=True)


def status():
    api = HfApi()
    def inspect(path):
        row = read(path)
        assert row['stage'] == 'launched'
        job = api.inspect_job(job_id=row['job_id'])
        return {**row, 'guard': str(path.relative_to(ROOT)), 'authoritative_status': job.status.stage,
                'message': job.status.message, 'started_at': str(job.started_at), 'finished_at': str(job.finished_at)}
    with ThreadPoolExecutor(max_workers=8) as pool:
        jobs = list(pool.map(inspect, sorted(GUARDS.glob('*.json'))))
    result = {'checked_at': datetime.now(timezone.utc).isoformat(), 'artifact_revision': api.model_info(read(PROTOCOL)['repo']).sha,
              'jobs': jobs, 'status_counts': dict(Counter(j['authoritative_status'] for j in jobs)), 'qualification_eligible': False}
    write(STATUS, result)
    print({k: v for k, v in result.items() if k != 'jobs'})


def collect():
    VERIFIED.mkdir(exist_ok=True)
    with (VERIFIED/'.collect.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        p, s, snapshot = read(PROTOCOL), read(SOURCE), read(STATUS)
        archive = Path(hf_hub_download('coyotte508/powergrid-ai-training-v1', s['archive'], repo_type='dataset', revision=s['revision']))
        assert digest(archive) == s['sha256']
        runtime = ROOT/'ai/runs/policy-iteration-labels-collector-v2'
        if not runtime.exists():
            runtime.mkdir()
            with tarfile.open(archive) as bundle:
                bundle.extractall(runtime, filter='data')
        with tarfile.open(archive) as bundle:
            for member in bundle.getmembers():
                if member.isfile():
                    assert digest(runtime/member.name) == hashlib.sha256(bundle.extractfile(member).read()).hexdigest()

        def one(job):
            shard = job['shard']
            out = VERIFIED/shard['id']
            assert job['source'] == s and job['protocol_sha256'] == digest(PROTOCOL)
            if out.exists():
                intent = read(out/'collection-intent.json')
                assert intent['shard'] == shard and intent['source'] == s
            else:
                out.mkdir()
                intent = {'shard': shard, 'source': s, 'revision': snapshot['artifact_revision']}
                write(out/'collection-intent.json', intent)
            revision = intent['revision']
            assert re.fullmatch('[a-f0-9]{40}', revision)

            def fetch(file):
                assert Path(file).name == file
                data = Path(hf_hub_download(p['repo'], PREFIX + shard['id'] + '/' + file, revision=revision)).read_bytes()
                if (out/file).exists():
                    assert (out/file).read_bytes() == data
                else:
                    (out/file).write_bytes(data)

            fetch('label-check.json')
            check = read(out/'label-check.json')
            assert check['status'] == 'complete' and check['source_revision'] == s['revision'] and check['source_sha256'] == s['sha256']
            for file, sha in check['artifacts'].items():
                fetch(file)
                assert digest(out/file) == sha
            command = [sys.executable, str(runtime/'ai/strong/policy_iteration_labels.py'), shard['id'], str(out), '--verify']
            result = subprocess.run(command, cwd=runtime, capture_output=True, text=True)
            (out/'independent-check.log').write_text(result.stdout + result.stderr)
            result.check_returncode()
            summary = json.loads(result.stdout)
            assert summary == check['summary']
            write(out/'verified.json', {'verified': True, 'shard': shard, 'source': s, 'revision': revision,
                                       'prefix': PREFIX + shard['id'], 'summary': summary,
                                       'artifacts': {f.name: digest(f) for f in out.iterdir() if f.is_file()}, 'qualification_eligible': False})
            return {'shard': shard['id'], 'roots': summary['roots'], 'rollouts': summary['rollouts']}

        jobs = [j for j in snapshot['jobs'] if j['authoritative_status'] == 'COMPLETED'
                and not (VERIFIED/j['shard']['id']/'verified.json').exists()]
        print({'collecting': len(jobs)}, flush=True)
        with ThreadPoolExecutor(max_workers=4) as pool:
            for result in pool.map(one, jobs):
                print(result, flush=True)


def summarize():
    p, s = read(PROTOCOL), read(SOURCE)
    cases = {}
    pending = []
    for shard in p['shards']:
        out = VERIFIED/shard['id']
        if not (out/'verified.json').exists():
            pending.append(shard['id'])
            continue
        v = verify_local(out, s, shard)
        cases[shard['id']] = {**v, 'verified_sha256': digest(out/'verified.json')}
    # Reused labels are checked against the original pilot provenance, never
    # rewritten under the new source identity.
    reused_rollouts = 0
    for old in p['reuse_pilot']:
        out = ROOT/'ai/runs/policy-iteration-teacher-pilot-verified-v2'/old['id']
        assert digest(out/'verified.json') == old['verified_sha256']
        v = read(out/'verified.json')
        assert v['verified'] and v['revision'] == old['revision'] and v['prefix'] == old['prefix']
        assert v['case'] == old['case']
        for file, sha in old['artifacts'].items():
            assert digest(out/file) == sha
        assert set(v['summary']['options_by_root']) == set(old['root_ids'])
        reused_rollouts += v['summary']['rollouts']
    pairs = [(rid, r['case'][-1]) for r in p['reuse_pilot'] for rid in r['root_ids']]
    pairs += [(rid, c['shard']['mode']) for c in cases.values() for rid in c['shard']['root_ids']]
    assert len(pairs) == len(set(pairs))
    if not pending:
        assert len(pairs) == 34560 and len({rid for rid, mode in pairs}) == 17280
    result = {'complete': not pending, 'source': s, 'protocol_sha256': digest(PROTOCOL),
              'planned_shards': len(p['shards']), 'complete_shards': len(cases), 'pending': pending,
              'cases': cases, 'reused_pilot': p['reuse_pilot'], 'verified_root_mode_pairs': len(pairs),
              'rollouts': reused_rollouts + sum(c['summary']['rollouts'] for c in cases.values()),
              'trained': False, 'qualification_eligible': False}
    write(RESULTS, result)
    print({k: result[k] for k in ['complete', 'planned_shards', 'complete_shards', 'verified_root_mode_pairs', 'rollouts']})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('command', choices=['launch', 'status', 'collect', 'summarize'])
    parser.add_argument('--wave', choices=['first', 'remaining'], default='first')
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--limit', type=int)
    args = parser.parse_args()
    if args.command == 'launch':
        launch(args.wave, args.execute, args.limit)
    else:
        globals()[args.command]()
