"""Mini-PC adapter for unchanged, already planned development shards; no retries."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import signal
import subprocess
import sys
import tarfile
import time


def read(p): return json.loads(Path(p).read_text())
def digest(p):
    with Path(p).open('rb') as f: return hashlib.file_digest(f, 'sha256').hexdigest()
def save(p, value):
    with Path(p).open('x') as f: json.dump(value, f, indent=2, allow_nan=False); f.write('\n')
def now(): return datetime.now(timezone.utc).isoformat()


def checked(root):
    config = read(root/'adapter.json')
    assert all(digest(root/n) == h for n, h in config['files'].items())
    assert digest(root/'bundle/protocol.json') == config['protocol_sha256']
    protocol = read(root/'bundle/protocol.json')
    assert digest(root/'artifact/manifest.json') == protocol['runtime_manifest_sha256']
    assert all(digest(root/'artifact'/n) == h for n, h in read(root/'artifact/manifest.json').items())
    assert digest(root/'node/bin/node') == config['node']['node_executable_sha256']
    return config, protocol


def environment(root):
    return {**os.environ, 'PATH': str(root/'node/bin')+':'+os.environ['PATH'],
            'OMP_NUM_THREADS': '1', 'OPENBLAS_NUM_THREADS': '1', 'MKL_NUM_THREADS': '1',
            'PYTHONDONTWRITEBYTECODE': '1', 'HF_HUB_OFFLINE': '1'}


def command(root, row, protocol, output):
    cmd = [sys.executable, '-u', '-B', str(root/'artifact/ai/strong/public_policy_final_runner_v1.py'),
           '--artifact', str(root/'artifact'), '--descriptor', row['descriptor'],
           '--candidate', str(root/'bundle'/row['candidate']), '--contract', str(root/'bundle'/row['contract']),
           '--workers', str(protocol['workers']), '--output', str(output/'evaluation')]
    if row['opponent_model']: cmd += ['--opponent-model', str(root/'artifact'/row['opponent_model'])]
    return cmd


def prepare(root):
    config = read(root/'adapter.json')
    assert all(digest(root/n) == h for n, h in config['files'].items())
    base = Path(config['remote_base']); overlay = read(root/'bundle/overlay.json')
    assert digest(base/'manifest.json') == overlay['expected_base_manifest_sha256']
    assert all(digest(base/n) == h for n, h in read(base/'manifest.json').items())
    assert not (root/'artifact').exists() and not (root/'node').exists()
    shutil.copytree(base, root/'artifact')
    for name, pin in overlay['files'].items():
        target = root/'artifact'/name
        assert (digest(target) if target.exists() else None) == pin['before']
        assert digest(root/'bundle/overlay'/name) == pin['after']
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(root/'bundle/overlay'/name, target)
    assert digest(root/'node.tar.xz') == config['node']['sha256']
    with tarfile.open(root/'node.tar.xz') as archive:
        archive.extractall(root/'node-extracted', filter='data')
    (root/'node-extracted/node-v24.14.0-linux-x64').rename(root/'node')
    checked(root)
    cpu = next(s.split(':', 1)[1].strip() for s in Path('/proc/cpuinfo').read_text().splitlines() if s.startswith('model name'))
    assert '8840U' in cpu and not os.environ.get('NODE_OPTIONS')
    import numpy, onnxruntime
    versions = {'cpu': cpu, 'python': platform.python_version(), 'numpy': numpy.__version__,
                'onnxruntime': onnxruntime.__version__, 'node': subprocess.check_output(
                    [str(root/'node/bin/node'), '--version'], text=True).strip()}
    # Compare the original saved serving choices; no games are generated here.
    cases = [json.loads(s) for s in (root/'cases.jsonl').read_text().splitlines()]
    protocol = read(root/'bundle/protocol.json'); reports = []
    for arm in protocol['arms']:
        expected = [json.loads(s) for s in (root/'references'/(arm+'.jsonl')).read_text().splitlines()]
        assert len(cases) == len(expected) == 402
        with (root/(arm+'.preflight.stderr.log')).open('x') as err, (root/(arm+'.preflight.jsonl')).open('x') as trace:
            proc = subprocess.Popen([sys.executable, '-u', '-B', str(root/'artifact/ai/strong/public_policy_runtime_v1.py'),
                str(root/'artifact'), '--descriptor', f'policies/nomination-{arm}.json', '--diagnostics'],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=err, text=True, env=environment(root))
            try:
                for case, reference in zip(cases, expected):
                    index = case['index']; assert index == reference['case']
                    q = {**case['request'], 'requestId': f'fixture:{index}', 'revision': index}
                    proc.stdin.write(json.dumps(q)+'\n'); proc.stdin.flush()
                    result = json.loads(proc.stdout.readline())
                    assert all(result[k] == v for k, v in protocol['identities'][arm].items())
                    assert result['requestId'] == q['requestId'] and result['revision'] == index
                    assert result['playerOrder'] == case['player_order']
                    assert result['move'] == reference['move'] == case['legal'][reference['choice']]
                    assert result['decision']['index'] == reference['choice']
                    assert result['decision']['filterApplied'] == reference['filter_applied']
                    trace.write(json.dumps({'case': index, 'choice': reference['choice']})+'\n')
                proc.stdin.close(); assert proc.wait(timeout=30) == 0
            finally:
                if proc.poll() is None: proc.kill(); proc.wait()
        reports.append({'arm': arm, 'exact_choices': len(cases), 'trace_sha256': digest(root/(arm+'.preflight.jsonl'))})
        print(reports[-1], flush=True)
    save(root/'ready.json', {'complete': True, 'created_at': now(), 'versions': versions,
        'adapter_sha256': digest(root/'adapter.json'), 'protocol_sha256': config['protocol_sha256'],
        'reports': reports, 'new_games': 0, 'new_gradients': 0})


def run(root, name):
    config, protocol = checked(root); ready = read(root/'ready.json')
    assert ready['complete'] and ready['adapter_sha256'] == digest(root/'adapter.json')
    assert name in config['authorized_names']
    row = next(r for r in protocol['rows'] if r['name'] == name)
    assert row['shard']['seed'] == f"nomination-discount-development-v1-{row['shard']['players']}p"
    out = root/'outputs'/name; out.parent.mkdir(exist_ok=True)
    cmd = command(root, row, protocol, out)
    subprocess.run(cmd, check=True, env=environment(root), stdout=subprocess.DEVNULL)
    out.mkdir()
    save(out/'origin.json', {'name': name, 'protocol_sha256': config['protocol_sha256'], 'row': row,
        'executor': 'minipc', 'adapter_sha256': digest(root/'adapter.json'),
        'ready_sha256': digest(root/'ready.json'), 'qualified': False, 'reserved_final_seeds_used': False})
    code = None; failure = None; timed_out = False; start = time.monotonic()
    try:
        with (out/'runner.log').open('x') as log:
            proc = subprocess.Popen([*cmd, '--execute'], stdout=log, stderr=subprocess.STDOUT,
                                    env=environment(root), start_new_session=True)
            save(out/'execution.json', {'pid': proc.pid, 'supervisor_pid': os.getpid(), 'started_at': now(),
                'command': cmd+['--execute'], 'timeout_seconds': 18000, 'versions': ready['versions']})
            try: code = proc.wait(timeout=18000)
            except subprocess.TimeoutExpired:
                timed_out = True; os.killpg(proc.pid, signal.SIGTERM)
                try: proc.wait(timeout=10)
                except subprocess.TimeoutExpired: pass
                # Also reap descendants if the group leader exited first.
                try: os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError: pass
                code = proc.wait()
    except BaseException as error:
        failure = type(error).__name__+': '+str(error); raise
    finally:
        save(out/'status.json', {'returncode': code, 'complete': code == 0 and not timed_out and failure is None,
            'seconds': time.monotonic()-start, 'finished_at': now(), 'timed_out': timed_out, 'failure': failure,
            'qualified': False, 'raw_independently_audited': False})
        save(out/'manifest.json', {str(p.relative_to(out)): digest(p) for p in sorted(out.rglob('*')) if p.is_file()})
    assert code == 0 and not timed_out, 'Original failure retained; do not rerun'


def progress(log):
    completed = set(); expected = None
    for line in log.splitlines():
        try: row = json.loads(line)
        except json.JSONDecodeError: continue
        if isinstance(row, dict) and 'episode' in row and 'expected' in row:
            completed.add(row['episode']); expected = row['expected']
    return {'completed_games': len(completed), 'expected_games': expected}


def status(root, name):
    out = root/'outputs'/name
    result = {'name': name, 'checked_at': now(), **progress((out/'runner.log').read_text() if (out/'runner.log').exists() else '')}
    if (root/(name+'.launch.json')).exists():
        launch = read(root/(name+'.launch.json')); pid = launch['pid']; proc = Path(f'/proc/{pid}')
        try:
            args = (proc/'cmdline').read_bytes().split(b'\0')
            result['supervisor_alive'] = str(root/'worker.py').encode() in args and name.encode() in args and b'run' in args
        except (FileNotFoundError, ProcessLookupError): result['supervisor_alive'] = False
        result['pid'] = pid; result['started_at'] = launch['started_at']
    if (out/'status.json').exists(): result['terminal'] = read(out/'status.json')
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(__doc__); p.add_argument('operation', choices=['prepare', 'run', 'status'])
    p.add_argument('--root', type=Path, required=True); p.add_argument('--name'); a = p.parse_args()
    if a.operation == 'prepare': prepare(a.root.resolve())
    elif a.operation == 'run': run(a.root.resolve(), a.name)
    else: print(json.dumps(status(a.root.resolve(), a.name)))
