"""Guarded HF development jobs and collection through the frozen verifier."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import tarfile

from huggingface_hub import HfApi, get_token, hf_hub_download
from policy_iteration_development import ROOT, PROTOCOL, SOURCE, read, write, digest, validate_pin, pin_hash, contract, case_key, prefix

GUARDS = ROOT/'ai/runs/policy-iteration-development-launches-v2'
VERIFIED = ROOT/'ai/runs/policy-iteration-development-verified-v2'

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
with tarfile.open('/tmp/node.tar.xz') as bundle: bundle.extractall('/opt')
path=hf_hub_download('coyotte508/powergrid-ai-training-v1',os.environ['SOURCE_ARCHIVE'],repo_type='dataset',revision=os.environ['SOURCE_REVISION'])
assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==os.environ['SOURCE_SHA256']
with tarfile.open(path) as bundle: bundle.extractall('/workspace',filter='data')
INNER
export PATH=/opt/node-v24.14.0-linux-x64/bin:$PATH
cd /workspace
python -u ai/strong/policy_iteration_development.py "$MODEL_KEY" "$PLAYERS" "$OPPONENT" "$START" "$END" ai/runs/development-job --mode "$EVALUATION_MODE" --upload
'''


def get_pin(key):
    protocol = read(PROTOCOL)
    pin = protocol['parent_pin'] if key == 'parent' else read(ROOT/'ai/strong/policy-iteration-development-pins-v2'/(key+'.json'))
    validate_pin(pin, key, protocol)
    return pin


def source_check():
    source = read(SOURCE)
    check = read(ROOT/'ai/strong/policy-iteration-development-preflight-v2.json')
    assert check['passed'] and check['games'] == 160 and check['nonzero_deal_offset_verified'] == 4
    assert check['synthetic_admission_rejected'] and len(check['corruptions_rejected']) == 12
    assert check['source'] == source and source['protocol_sha256'] == check['protocol_sha256'] == digest(PROTOCOL)
    assert source['unchanged_base_files'] == 1434
    assert all(digest(ROOT/file) == sha for file, sha in source['overlays'].items())
    return source


def runtime_admission(key, pin, source):
    probes = []
    for n in [2, 6]:
        directory = VERIFIED/case_key(key, n, 'search_geo', 0, 1, 'smoke')
        report = read(directory/'verified.json')
        assert report['verified'] and report['model_pin_sha256'] == pin_hash(pin) and report['source'] == source
        assert report['protocol_sha256'] == digest(PROTOCOL) and report['flavor'] == 'cpu-upgrade'
        for file, sha in report['artifacts'].items():
            assert digest(directory/file) == sha
        seconds = report['summary']['seconds']
        assert math.isfinite(seconds) and seconds > 0
        probes.append({'players': n, 'seconds': seconds, 'verified_sha256': digest(directory/'verified.json')})
    projected = 120 + 2*4*max(p['seconds'] for p in probes)
    hours = max(4, math.ceil(projected/(.75*3600)))
    return {'probes': probes, 'projected_seconds': projected, 'timeout_hours': hours, 'admitted': hours <= 12,
            'scope': 'Same candidate/source/hardware;2x slower endpoint for four whole deals plus120s setup and25% timeout headroom. Never shorten games or search.'}


def launch(args):
    source, protocol, pin = source_check(), read(PROTOCOL), get_pin(args.key)
    contract(protocol, args.players, args.opponent, args.start, args.end, args.mode)
    admission = {'timeout_hours': 4, 'admitted': True, 'scope': 'One whole-deal runtime probe'} if args.mode == 'smoke' else runtime_admission(args.key, pin, source)
    assert admission['admitted'], 'Partition the execution further; do not weaken the game or rollout horizon'
    name = case_key(args.key, args.players, args.opponent, args.start, args.end, args.mode)
    record = {'stage': 'launch_intent', 'created_at': datetime.now(timezone.utc).isoformat(), 'case': name,
              'key': args.key, 'players': args.players, 'opponent': args.opponent, 'start': args.start, 'end': args.end,
              'mode': args.mode, 'source': source, 'model_pin': pin, 'model_pin_sha256': pin_hash(pin),
              'protocol_sha256': digest(PROTOCOL), 'flavor': 'cpu-upgrade', 'runtime_admission': admission,
              'timeout_hours': admission['timeout_hours'], 'bootstrap_sha256': hashlib.sha256(BOOTSTRAP.encode()).hexdigest(),
              'qualification_eligible': False}
    if not args.execute:
        print({'admitted': True, 'case': name, 'execute': False, 'timeout_hours': admission['timeout_hours']})
        return
    env = os.environ.copy()
    env['HF_TOKEN'] = get_token() or env.get('HF_TOKEN') or ''
    assert env['HF_TOKEN']
    GUARDS.mkdir(exist_ok=True)
    guard = GUARDS/(name+'.json')
    with guard.open('x') as stream:
        json.dump(record, stream, indent=2)
    command = ['hf', 'jobs', 'run', '--detach', '--flavor', 'cpu-upgrade', '--timeout', str(admission['timeout_hours'])+'h',
               '--secrets', 'HF_TOKEN', '--label', 'project=powergrid-ai', '--label', 'stage=policy-development-v2', '--label', 'case='+name]
    for field, value in {'SOURCE_ARCHIVE': source['archive'], 'SOURCE_REVISION': source['revision'],
                         'SOURCE_SHA256': source['sha256'], 'MODEL_KEY': args.key, 'PLAYERS': str(args.players),
                         'OPPONENT': args.opponent, 'START': str(args.start), 'END': str(args.end),
                         'EVALUATION_MODE': args.mode, 'MODEL_PIN': json.dumps(pin, sort_keys=True, separators=(',', ':')),
                         'MODEL_PIN_SHA256': pin_hash(pin), 'HF_HUB_DISABLE_PROGRESS_BARS': '1'}.items():
        command += ['--env', field+'='+value]
    command += ['--', 'python:3.11-slim-bookworm', 'bash', '-lc', BOOTSTRAP]
    try:
        result = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True, check=True)
        guard.with_suffix('.log').write_text(result.stdout+result.stderr)
        ids = set(re.findall(r'\b[a-f0-9]{24}\b', result.stdout))
        assert len(ids) == 1, 'Reconcile an ambiguous submission before retrying'
        record.update(stage='launched', job_id=ids.pop())
    except BaseException as error:
        record.update(stage='launch_unknown', error=type(error).__name__+': '+str(error))
        raise
    finally:
        write(guard, record)
    print({'case': name, 'job_id': record['job_id']}, flush=True)


def collect(args):
    source, protocol, pin = source_check(), read(PROTOCOL), get_pin(args.key)
    contract(protocol, args.players, args.opponent, args.start, args.end, args.mode)
    name = case_key(args.key, args.players, args.opponent, args.start, args.end, args.mode)
    guard = read(GUARDS/(name+'.json'))
    assert guard['stage'] == 'launched' and guard['source'] == source and guard['model_pin'] == pin
    api = HfApi()
    job = api.inspect_job(job_id=guard['job_id'])
    print({'case': name, 'job_id': guard['job_id'], 'stage': job.status.stage}, flush=True)
    if job.status.stage != 'COMPLETED':
        return
    archive = Path(hf_hub_download('coyotte508/powergrid-ai-training-v1', source['archive'], repo_type='dataset', revision=source['revision']))
    assert digest(archive) == source['sha256']
    runtime = ROOT/'ai/runs/policy-iteration-development-collector-v2'
    if not runtime.exists():
        runtime.mkdir()
        with tarfile.open(archive) as bundle:
            bundle.extractall(runtime, filter='data')
    with tarfile.open(archive) as bundle:
        for member in bundle.getmembers():
            if member.isfile():
                assert digest(runtime/member.name) == hashlib.sha256(bundle.extractfile(member).read()).hexdigest()
    out = VERIFIED/name
    remote = prefix(args.key, args.players, args.opponent, args.start, args.end, args.mode)
    if out.exists():
        intent = read(out/'collection-intent.json')
        assert intent['job_id'] == guard['job_id'] and intent['source'] == source and intent['prefix'] == remote
    else:
        out.mkdir(parents=True)
        intent = {'job_id': guard['job_id'], 'source': source, 'revision': api.model_info(protocol['repo']).sha, 'prefix': remote}
        write(out/'collection-intent.json', intent)
    def fetch(file):
        assert Path(file).name == file
        data = Path(hf_hub_download(protocol['repo'], remote+'/'+file, revision=intent['revision'])).read_bytes()
        if (out/file).exists():
            assert (out/file).read_bytes() == data
        else:
            (out/file).write_bytes(data)
    fetch('development-check.json')
    status = read(out/'development-check.json')
    for file, sha in status['artifacts'].items():
        fetch(file)
        assert digest(out/file) == sha
    verification = {'out': str(out), 'key': args.key, 'n': args.players, 'opponent': args.opponent,
                    'start': args.start, 'end': args.end, 'mode': args.mode, 'pin': pin, 'source': source}
    script = '''
import sys,json
from pathlib import Path
sys.path.insert(0,sys.argv[1])
from policy_iteration_development import verify_local
a=json.loads(sys.argv[2])
print(json.dumps(verify_local(Path(a['out']),a['key'],a['n'],a['opponent'],a['start'],a['end'],a['mode'],a['pin'],a['source'])))
'''
    result = subprocess.run([sys.executable, '-c', script, str(runtime/'ai/strong'), json.dumps(verification)],
                            cwd=runtime, capture_output=True, text=True, check=True)
    summary = json.loads(result.stdout)
    saved = {'verified': True, **intent, 'model_pin_sha256': pin_hash(pin), 'model_pin': pin,
             'protocol_sha256': digest(PROTOCOL), 'summary': summary, 'flavor': guard['flavor'],
             'artifacts': {f.name: digest(f) for f in out.iterdir() if f.is_file() and f.name != 'verified.json'},
             'qualification_eligible': False}
    if (out/'verified.json').exists():
        assert read(out/'verified.json') == saved
    else:
        write(out/'verified.json', saved)
    print({'verified': True, 'case': name, 'games': summary['games'], 'seconds': summary['seconds']}, flush=True)


def status():
    api = HfApi()
    def inspect(path):
        guard = read(path)
        assert guard['stage'] == 'launched'
        job = api.inspect_job(job_id=guard['job_id'])
        return {**guard, 'authoritative_status': job.status.stage, 'message': job.status.message,
                'started_at': str(job.started_at), 'finished_at': str(job.finished_at)}
    with ThreadPoolExecutor(max_workers=4) as pool:
        jobs = list(pool.map(inspect, sorted(GUARDS.glob('*.json'))))
    result = {'checked_at': datetime.now(timezone.utc).isoformat(), 'jobs': jobs,
              'status_counts': dict(Counter(j['authoritative_status'] for j in jobs)), 'qualification_eligible': False}
    write(ROOT/'ai/strong/policy-iteration-development-status-v2.json', result)
    print({k: v for k, v in result.items() if k != 'jobs'})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    for name in ['launch', 'collect']:
        p = sub.add_parser(name)
        p.add_argument('key', choices=['parent', 'frozen-0', 'frozen-1', 'public-0', 'public-1'])
        p.add_argument('players', type=int, choices=range(2, 7))
        p.add_argument('opponent')
        p.add_argument('start', type=int)
        p.add_argument('end', type=int)
        p.add_argument('--mode', choices=['development', 'smoke'], default='development')
        if name == 'launch':
            p.add_argument('--execute', action='store_true')
    sub.add_parser('status')
    args = parser.parse_args()
    if args.command == 'launch':
        launch(args)
    elif args.command == 'collect':
        collect(args)
    else:
        status()
