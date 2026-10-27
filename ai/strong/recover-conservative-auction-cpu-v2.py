"""Recover only 27 missing local parity requests after inspected termination.

Preserve the interrupted prefix and immutable package. This is a two-segment
local correctness reference; target timing still requires a full original run.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

from conservative_auction_cpu_v2 import read, digest, write

ROOT = Path(__file__).resolve().parents[2]
OLD = ROOT/'ai/runs/conservative-auction-8840u-local-v2'
OUT = ROOT/'ai/runs/conservative-auction-8840u-local-recovered-v2'
PREP = ROOT/'ai/runs/conservative-auction-8840u-prepared-v2'
GUARD = ROOT/'ai/strong/conservative-auction-cpu-local-recovery-launch-v2.json'
PREFIX_SHA = '47e67e187499b03adc77f19ad5485f17a5cb5fca7aaaf1bc4254d9f78a39d1e4'
STATUS_SHA = '21d45c7e81ac14bea9c7505bc0273cafe844a95a2ab8fdff11932fbf6db7729f'


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec); spec.loader.exec_module(value); return value


def validate_prefix(rows, cases, original, live, stop, status_sha, prefix_sha):
    assert status_sha == STATUS_SHA and prefix_sha == PREFIX_SHA, 'Inspect changed original evidence'
    assert not live and not stop, 'Original process or explicit stop still present'
    assert original['pid'] == 1904528 and original['stage'] == 'running' and original['completed_requests'] == 273
    expected = [(arm, c['name']) for arm in ('filter', 'conservative_population', 'conservative_dual') for c in cases]
    assert len(expected) == 300 and len(set(expected)) == 300
    assert len(rows) == 273 and [(r['arm'], r['case']) for r in rows] == expected[:273], 'Prefix incomplete/duplicated/out of order'
    assert all(arm == 'conservative_dual' for arm, _ in expected[273:])
    return expected[273:]


def admission():
    package = PREP/'package'; bench = module('exact_cpu_benchmark', package/'benchmark.py')
    manifest = bench.checked_package(package); cases = read(package/'cases.json')
    assert manifest['runner_sha256'] == digest(package/'benchmark.py')
    original = read(OLD/'status.json'); rows = [json.loads(l) for l in (OLD/'receipts.jsonl').read_text().splitlines()]
    needle = str(package).encode(); live = []
    for path in Path('/proc').glob('[0-9]*/cmdline'):
        try:
            if needle in path.read_bytes(): live.append(int(path.parent.name))
        except (FileNotFoundError, PermissionError): pass
    missing = validate_prefix(rows, cases, original, live, (OLD/'STOP').exists() or (PREP/'STOP').exists(),
                              digest(OLD/'status.json'), digest(OLD/'receipts.jsonl'))
    assert all(p.stat().st_size == 0 for p in OLD.glob('*.stderr.log')), 'Inspect original stderr before recovery'
    assert not (ROOT/'ai/strong/conservative-auction-8840u-launch-v2.json').exists(), 'Target already launched; inspect original owner'
    return bench, manifest, cases, original, rows, missing


def launch_local():
    assert not GUARD.exists() and not OUT.exists(), 'Inspect original recovery, never repeat'
    admission()
    tests = (ROOT/'ai/runs/conservative-auction-cpu-recovery-tests-v2.log').read_text()
    assert 'Ran 3 tests' in tests and tests.rstrip().endswith('OK')
    guard = {'stage': 'launch_intent', 'runner_sha256': digest(__file__), 'original_status_sha256': STATUS_SHA,
        'original_receipts_sha256': PREFIX_SHA, 'original_exit_code': 143, 'requests_preserved': 273,
        'missing_requests': 27, 'output': str(OUT), 'new_hf_jobs': 0, 'new_strength_games': 0}
    with GUARD.open('x') as stream: json.dump(guard, stream, indent=2)
    try:
        with (PREP/'local-recovery.log').open('x') as log:
            child = subprocess.Popen([sys.executable, '-u', '-B', str(Path(__file__).resolve()), 'run'],
                cwd=str(ROOT), stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        guard.update(stage='launched', pid=child.pid)
    except BaseException as error:
        guard.update(stage='launch_unknown', failure_type=type(error).__name__); raise
    finally: write(GUARD, guard)
    print(json.dumps(guard), flush=True)


def run():
    guard = read(GUARD); assert guard['runner_sha256'] == digest(__file__) and not OUT.exists()
    bench, manifest, cases, original, rows, missing = admission()
    sys.path.insert(0, str(PREP/'package/artifact/ai/strong'))
    from public_policy_arena_v1 import PublicPolicyProcess
    lookup = {c['name']: c for c in cases}; counts = Counter()
    for row in rows: counts.update(bench.verify_response(lookup[row['case']], row['arm'], row['response'], manifest['identities'][row['arm']]))
    OUT.mkdir()
    write(OUT/'original-interruption.json', {'original_status': original, 'original_status_sha256': STATUS_SHA,
        'original_receipts_sha256': PREFIX_SHA, 'original_exit_code': 143, 'surviving_original_workers': 0,
        'prefix_requests_independently_reaudited': 273, 'missing_requests': missing})
    shutil.copyfile(OLD/'receipts.jsonl', OUT/'receipts.jsonl')
    state = {**original, 'stage': 'running', 'pid': os.getpid(), 'started_at': datetime.now(timezone.utc).isoformat(),
        'recovery': True, 'execution_segments': 2, 'original_pid': 1904528, 'preserved_requests': 273,
        'new_requests': 0, 'scope': 'Recovered local correctness reference: 273 original audited responses plus 27 previously unfinished saved requests. Not an uninterrupted latency benchmark. Target timing requires its complete separate run.'}
    write(OUT/'status.json', state); started = time.perf_counter()
    try:
        with (OUT/'conservative_dual.stderr.log').open('x') as stderr, (OUT/'receipts.jsonl').open('a') as receipts:
            cold = time.perf_counter(); process = PublicPolicyProcess(PREP/'package/artifact', 'policies/conservative_dual.json', stderr)
            try:
                for i, (arm, name) in enumerate(missing):
                    case = lookup[name]; start = time.perf_counter(); response = process.call(case['fixture']['request']); end = time.perf_counter()
                    counts.update(bench.verify_response(case, arm, response, manifest['identities'][arm]))
                    row = {'case': name, 'arm': arm, 'first_request': False, 'round_trip_ms': 1000*(end-start),
                        'cold_process_plus_request_ms': None, 'recovery_process_first_request': i == 0,
                        'recovery_process_plus_request_ms': 1000*(end-cold) if i == 0 else None, 'response': response}
                    receipts.write(json.dumps(row, allow_nan=False)+'\n'); receipts.flush()
                    state['new_requests'] += 1; state['completed_requests'] += 1
                    write(OUT/'status.json', state)
                    print(json.dumps({'case': name, 'completed_requests': state['completed_requests']}), flush=True)
            finally: process.close()
        assert state['completed_requests'] == 300 and state['new_requests'] == 27 and counts.get('rollout_caps', 0) == 0
        assert (OUT/'receipts.jsonl').read_bytes().startswith((OLD/'receipts.jsonl').read_bytes())
        assert digest(OLD/'status.json') == STATUS_SHA and digest(OLD/'receipts.jsonl') == PREFIX_SHA
        bench.checked_package(PREP/'package'); state.update(stage='completed', passed=True)
    except BaseException as error:
        state.update(stage='failed', passed=False, failure_type=type(error).__name__, failure=str(error)); raise
    finally:
        state.update(recovery_seconds=time.perf_counter()-started, counts=dict(counts), finished_at=datetime.now(timezone.utc).isoformat())
        state['output_hashes'] = {p.name: digest(p) for p in OUT.iterdir() if p.is_file() and p.name != 'status.json'}
        write(OUT/'status.json', state)


def target(operation):
    manager = module('original_cpu_manager', Path(__file__).with_name('benchmark-conservative-auction-8840u-v2.py'))
    assert digest(__file__) == read(GUARD)['runner_sha256']
    reference = read(OUT/'status.json')
    assert reference['stage'] == 'completed' and reference['passed'] and reference['completed_requests'] == 300
    assert reference['execution_segments'] == 2 and reference['new_requests'] == 27
    assert digest(OLD/'status.json') == STATUS_SHA and digest(OLD/'receipts.jsonl') == PREFIX_SHA
    manager.LOCAL = OUT  # Original package, target guard and full target runner remain unchanged.
    return getattr(manager, operation)()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__); parser.add_argument('operation', choices=['launch-local', 'run', 'launch-target', 'inspect-target', 'collect-target'])
    op = parser.parse_args().operation
    if op == 'launch-local': launch_local()
    elif op == 'run': run()
    else: target(op.removesuffix('-target'))
