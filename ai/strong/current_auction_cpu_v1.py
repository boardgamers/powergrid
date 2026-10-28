"""Replay the exact current-engine policies on saved positions on the 8840U."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time

ARMS = ('filter', 'conservative_population')
RUNTIME_SHA = 'fc135130689140b6fd72a76e6e14c59a7fea59717b858d330bac0c7f6aad93df'


def read(path): return json.loads(Path(path).read_text())
def digest(path):
    with Path(path).open('rb') as stream: return hashlib.file_digest(stream, 'sha256').hexdigest()


def semantic(value):
    if isinstance(value, dict): return {k: semantic(v) for k, v in value.items() if k != 'elapsedMs'}
    if isinstance(value, list): return [semantic(v) for v in value]
    return value


def response_hash(value):
    return hashlib.sha256(json.dumps(semantic(value), sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def write(path, value):
    temporary = Path(str(path) + '.tmp')
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n'); temporary.replace(path)


def validate_cases(cases, reference):
    assert len(cases) == 160 and len({c['name'] for c in cases}) == 160
    assert Counter(c['group'] for c in cases) == {'canonical': 100, 'discount': 40, 'wrapper': 20}
    canonical = {(c['players'], c['variant'], c['sealed'], c['stage']) for c in cases if c['group'] == 'canonical'}
    assert canonical == {(n,v,s,t) for n in range(2,7) for v in ('original','recharged') for s in (False,True)
                         for t in ('choose','bid','resources','building','bureaucracy')}
    wrappers={(c['players'],c['variant'],c['sealed'],c['name'].split('-',2)[2]) for c in cases if c['group']=='wrapper'}
    assert wrappers == {(n,v,True,k) for n in range(2,7) for v in ('original','recharged')
                        for k in ('pending-actor','wrapper-auto-pass')}
    assert set(reference) == set(ARMS)
    for arm in ARMS:
        assert set(reference[arm]) == {c['name'] for c in cases}
        assert all(isinstance(h,str) and len(h)==64 and all(c in '0123456789abcdef' for c in h) for h in reference[arm].values())
    for case in cases:
        q = case['request']; s = q['state']; n = case['players']
        assert n in range(2,7) and case['variant'] in ('original','recharged') and case['legal']
        assert len(s['players']) == n and s['options']['variant'] == case['variant']
        assert s['options']['fastBid'] is case['sealed'] and s['options']['showMoney'] is True
        assert s['seed'] == 'secret' and s['powerPlantsDeck'] == [] and not s.get('hiddenLog')
        assert 'powerPlantDeckAfterStep3' not in s and 'automation' not in s
        if case['sealed']: assert all(p['bid'] == 0 for p in s['players'])
        order = case['player_order']; assert order[0] == q['player'] and sorted(order) == list(range(n))


def checked_package(package):
    manifest = read(package / 'benchmark-manifest.json')
    assert manifest['runtime_manifest_sha256'] == RUNTIME_SHA and manifest['arms'] == list(ARMS)
    assert manifest['positions'] == 160 and manifest['requests'] == 320
    assert all(digest(package / name) == sha for name, sha in manifest['files'].items())
    assert digest(package / 'artifact/manifest.json') == RUNTIME_SHA
    validate_cases(read(package / 'cases.json'), read(package / 'reference.json'))
    return manifest


def verify_response(case, arm, response, identity):
    from public_policy_arena_v1 import validate_response
    from opponent_auction_verification_v1 import verify_decision as auction_audit
    from population_policy_verification import verify_decision as population_audit
    q = case['request']; n = case['players']; legal = case['legal']
    validate_response(response, q, legal, case['player_order'], identity)
    row = {**response['decision'], 'arenaMoves': legal}
    config = {'players': n, 'arm': 'filter' if arm == 'filter' else 'opponent-auction-v1',
              'samples': 8, 'model_sha256': identity['modelSha256'], 'identity': identity, 'sealed': case['sealed']}
    counts = (population_audit if arm == 'filter' else auction_audit)(row, config, q['player'])
    assert counts.get('rollout_caps', 0) == 0
    return counts


def run(package, output, required_cpu):
    manifest = checked_package(package); assert digest(__file__) == manifest['runner_sha256']
    cpu = next(x.split(':',1)[1].strip() for x in Path('/proc/cpuinfo').read_text().splitlines() if x.startswith('model name'))
    assert required_cpu in cpu and required_cpu == '8840U', 'This benchmark is only for the actual target'
    assert not os.environ.get('NODE_OPTIONS')
    artifact = package / 'artifact'; sys.path.insert(0, str(artifact / 'ai/strong'))
    from public_policy_arena_v1 import PublicPolicyProcess, wire_json
    from public_policy_final_audit_v1 import artifact_identity
    import numpy, onnxruntime, huggingface_hub
    identities = {a: artifact_identity(artifact, f'policies/{a}.json') for a in ARMS}
    assert identities == manifest['identities']
    cases = read(package / 'cases.json'); reference = read(package / 'reference.json')
    output.mkdir(parents=True, exist_ok=False)
    state = {'stage': 'running', 'pid': os.getpid(), 'started_at': datetime.now(timezone.utc).isoformat(),
        'processor': cpu, 'host': platform.node(), 'python': platform.python_version(),
        'numpy': numpy.__version__, 'onnxruntime': onnxruntime.__version__, 'huggingface_hub': huggingface_hub.__version__,
        'node': subprocess.check_output(['node','--version'],text=True).strip(),
        'manifest_sha256': digest(package / 'benchmark-manifest.json'), 'completed_requests': 0,
        'expected_requests': 320, 'new_hf_jobs': 0, 'new_full_games': 0, 'gradients': False,
        'qualification_eligible': False, 'reserved_final_seeds_used': False,
        'scope': '160 saved current-engine cases / two exact policies. Fixed-position latency and parity, not representative gameplay percentiles or final 2553-position qualification.'}
    write(output / 'status.json', state); began = time.perf_counter(); cpu0 = os.times(); counts = Counter()
    try:
        with (output / 'receipts.jsonl').open('x') as receipts:
            for arm in ARMS:
                with (output / (arm + '.stderr.log')).open('x') as stderr:
                    cold = time.perf_counter(); process = PublicPolicyProcess(artifact, f'policies/{arm}.json', stderr)
                    try:
                        for i, case in enumerate(cases):
                            before = wire_json(case['request']); start = time.perf_counter()
                            response = process.call(case['request']); returned = time.perf_counter()
                            assert before == wire_json(case['request'])
                            counts.update(verify_response(case, arm, response, identities[arm]))
                            sha = response_hash(response); assert sha == reference[arm][case['name']], 'Cross-host semantic mismatch: ' + case['name']
                            row = {'arm': arm, 'case': case['name'], 'group': case['group'], 'stage': case['stage'],
                                'players': case['players'], 'first_request': i == 0, 'response': response,
                                'semantic_sha256': sha, 'round_trip_ms': 1000*(returned-start),
                                'cold_process_plus_request_ms': 1000*(returned-cold) if i == 0 else None}
                            receipts.write(json.dumps(row, allow_nan=False) + '\n'); receipts.flush()
                            state['completed_requests'] += 1; write(output / 'status.json', state)
                            print(json.dumps({'arm':arm,'case':case['name'],'completed':state['completed_requests']}),flush=True)
                    finally: process.close()
        assert state['completed_requests'] == 320 and counts.get('rollout_caps',0) == 0
        checked_package(package); state.update(stage='completed', passed=True)
    except BaseException as error:
        state.update(stage='failed', passed=False, failure_type=type(error).__name__, failure=str(error)); raise
    finally:
        cpu1 = os.times(); state.update(seconds=time.perf_counter()-began, cpu_seconds=sum(cpu1[:4])-sum(cpu0[:4]),
            counts=dict(counts), finished_at=datetime.now(timezone.utc).isoformat())
        state['output_hashes'] = {p.name:digest(p) for p in output.iterdir() if p.is_file() and p.name!='status.json'}
        write(output / 'status.json', state)


if __name__ == '__main__':
    p = argparse.ArgumentParser(__doc__); p.add_argument('--package',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True); p.add_argument('--require-cpu',default='8840U')
    args=p.parse_args(); run(args.package.resolve(),args.output.resolve(),args.require_cpu)
