"""Exact frozen-policy CPU replay on saved public positions; no new games."""
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

ARMS = ('filter', 'conservative_population', 'conservative_dual')
STAGES = {'choose': 'ChoosePowerPlant', 'bid': 'Bid', 'resources': 'BuyResource',
          'building': 'Build', 'bureaucracy': 'UsePowerPlant'}
FIXTURES_SHA = 'f1c97bf909e38e5df372a89d169d80f5a6f24c00dccefacd60b10b767f1fcfa0'
RUNTIME_SHA = 'a2047543f5f6a8065dd9b868dd4551531147185068c665900691c5b13c278619'


def read(path): return json.loads(Path(path).read_text())
def digest(path):
    with Path(path).open('rb') as stream: return hashlib.file_digest(stream, 'sha256').hexdigest()


def write(path, value):
    temp = Path(str(path)+'.tmp')
    temp.write_text(json.dumps(value, indent=2, allow_nan=False)+'\n'); temp.replace(path)


def select_fixtures(path):
    """First non-forced saved menu in each count/rule/stage cell; no outcomes."""
    assert digest(path) == FIXTURES_SHA, 'Saved fixture pool changed'
    found = {}
    with Path(path).open() as stream:
        for ordinal, line in enumerate(stream):
            fixture = json.loads(line); q = fixture['request']; s = q['state']
            n, variant, sealed = len(s['players']), s['options']['variant'], s['options']['fastBid']
            assert type(sealed) is bool and n in range(2, 7) and variant in ('original', 'recharged')
            if len(fixture['legal']) <= 1: continue
            names = {m['name'] for m in fixture['legal']}
            for stage, move in STAGES.items():
                key = n, variant, sealed, stage
                if move in names and key not in found:
                    found[key] = {'name': f'{n}p-{variant}-'+('sealed' if sealed else 'open')+'-'+stage,
                        'players': n, 'variant': variant, 'sealed': sealed, 'stage': stage,
                        'source_ordinal': ordinal, 'source_line_sha256': hashlib.sha256(line.encode()).hexdigest(),
                        'fixture': fixture}
    expected = {(n, v, s, stage) for n in range(2, 7) for v in ('original', 'recharged')
                for s in (False, True) for stage in STAGES}
    assert set(found) == expected and len(found) == 100, 'Incomplete saved-fixture coverage'
    # Identical deterministic order on both hosts; first call per policy is cold.
    return [found[key] for key in sorted(found)]


def assert_public_state(state):
    assert state['seed'] == 'secret' and state['powerPlantsDeck'] == [] and not state.get('hiddenLog')
    assert 'powerPlantDeckAfterStep3' not in state and 'automation' not in state
    assert state['options']['showMoney'] is True
    if state['options']['fastBid']: assert all(p['bid'] == 0 for p in state['players'])


def project_cases(cases, artifact):
    # Historical model-only fixtures contain simulator state. Use the identical
    # frozen projection used by public-arena-bridge, never hand-redact fields.
    script = '''const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const root=process.argv[1], beliefs=require(path.join(root,'ai/strong/sealed-policy-beliefs.cjs'));
const encoder=require(path.join(root,'ai/strong/encoders.cjs')).forRevision('4.3-strategic-correction');
const cases=JSON.parse(fs.readFileSync(0,'utf8'));
for(const item of cases){const q=item.fixture.request; q.state=beliefs.publicState(q.state,q.player);
 const encoded=encoder.encode(q.state,q.player); assert.deepEqual(encoded.moves,item.fixture.legal);
 item.player_order=encoded.playerOrder;}
process.stdout.write(JSON.stringify(cases));'''
    result = subprocess.run(['node', '-e', script, str(Path(artifact).resolve())],
                            input=json.dumps(cases), capture_output=True, text=True, check=True)
    projected = json.loads(result.stdout)
    assert [c['name'] for c in projected] == [c['name'] for c in cases]
    for case in projected:
        assert_public_state(case['fixture']['request']['state'])
    return projected


def checked_package(package):
    manifest = read(package/'benchmark-manifest.json')
    assert manifest['fixture_pool_sha256'] == FIXTURES_SHA and manifest['runtime_manifest_sha256'] == RUNTIME_SHA
    assert manifest['arms'] == list(ARMS) and manifest['positions'] == 100 and manifest['requests'] == 300
    assert all(digest(package/name) == sha for name, sha in manifest['files'].items())
    assert digest(package/'artifact/manifest.json') == RUNTIME_SHA
    return manifest


def verify_response(case, arm, response, identity):
    from public_policy_arena_v1 import validate_response
    from opponent_auction_verification_v1 import verify_decision as auction_audit
    from population_policy_verification import verify_decision as population_audit
    q = case['fixture']['request']; legal = case['fixture']['legal']; n = case['players']
    order = response['playerOrder']
    assert order == case['player_order'] and order[0] == q['player'] and sorted(order) == list(range(n))
    assert_public_state(q['state'])
    validate_response(response, q, legal, order, identity)
    row = {**response['decision'], 'arenaMoves': legal}
    config = {'players': n, 'arm': 'filter' if arm == 'filter' else 'opponent-auction-v1',
              'samples': 8, 'model_sha256': identity['modelSha256'], 'sealed': case['sealed'], 'identity': identity}
    counts = (population_audit if arm == 'filter' else auction_audit)(row, config, q['player'])
    assert counts.get('rollout_caps', 0) == 0
    return counts


def run(package, output, required_cpu):
    manifest = checked_package(package)
    assert digest(__file__) == manifest['runner_sha256']
    cpu = next(l.split(':', 1)[1].strip() for l in Path('/proc/cpuinfo').read_text().splitlines() if l.startswith('model name'))
    assert not required_cpu or required_cpu in cpu, 'Wrong physical target processor'
    assert not os.environ.get('NODE_OPTIONS')
    artifact = package/'artifact'; sys.path.insert(0, str(artifact/'ai/strong'))
    from public_policy_arena_v1 import PublicPolicyProcess, wire_json
    from public_policy_final_audit_v1 import artifact_identity
    import numpy, onnxruntime, huggingface_hub
    identities = {a: artifact_identity(artifact, f'policies/{a}.json') for a in ARMS}
    assert identities == manifest['identities']
    cases = read(package/'cases.json'); assert len(cases) == 100
    output.mkdir(parents=True, exist_ok=False)
    state = {'stage': 'running', 'pid': os.getpid(), 'started_at': datetime.now(timezone.utc).isoformat(),
        'processor': cpu, 'required_cpu': required_cpu, 'host': platform.node(), 'python': platform.python_version(),
        'numpy': numpy.__version__, 'onnxruntime': onnxruntime.__version__, 'huggingface_hub': huggingface_hub.__version__,
        'node': subprocess.check_output(['node', '--version'], text=True).strip(),
        'manifest_sha256': digest(package/'benchmark-manifest.json'), 'completed_requests': 0,
        'new_hf_jobs': 0, 'new_strength_games': 0, 'gradients': False,
        'qualification_eligible': False, 'reserved_final_seeds_used': False,
        'scope': '100 fixed historical public positions: every 2–6p/rule cell and five decision stages. Exact policies/menus/worlds; engineering latency and parity only. Not a representative gameplay latency distribution.'}
    write(output/'status.json', state); started = time.perf_counter(); cpu0 = os.times(); counts = Counter()
    try:
        with (output/'receipts.jsonl').open('x') as receipts:
            for arm in ARMS:
                with (output/(arm+'.stderr.log')).open('x') as stderr:
                    cold_started = time.perf_counter(); policy = PublicPolicyProcess(artifact, f'policies/{arm}.json', stderr)
                    try:
                        for i, case in enumerate(cases):
                            q = case['fixture']['request']; before = wire_json(q); start = time.perf_counter()
                            response = policy.call(q); returned = time.perf_counter()
                            assert before == wire_json(q)
                            counts.update(verify_response(case, arm, response, identities[arm]))
                            row = {'case': case['name'], 'arm': arm, 'first_request': i == 0,
                                'round_trip_ms': 1000*(returned-start),
                                'cold_process_plus_request_ms': 1000*(returned-cold_started) if i == 0 else None,
                                'response': response}
                            receipts.write(json.dumps(row, allow_nan=False)+'\n'); receipts.flush()
                            state['completed_requests'] += 1
                            write(output/'status.json', state)
                            print(json.dumps({'arm': arm, 'case': case['name'], 'completed': state['completed_requests'],
                                              'seconds': row['round_trip_ms']/1000}), flush=True)
                    finally: policy.close()
        assert state['completed_requests'] == 300 and counts.get('rollout_caps', 0) == 0
        checked_package(package)
        state.update(stage='completed', passed=True)
    except BaseException as error:
        state.update(stage='failed', passed=False, failure_type=type(error).__name__, failure=str(error)); raise
    finally:
        cpu1 = os.times()
        state.update(seconds=time.perf_counter()-started, cpu_seconds=sum(cpu1[:4])-sum(cpu0[:4]),
                     counts=dict(counts), finished_at=datetime.now(timezone.utc).isoformat())
        state['output_hashes'] = {p.name: digest(p) for p in output.iterdir() if p.is_file() and p.name != 'status.json'}
        write(output/'status.json', state)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__); parser.add_argument('--package', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True); parser.add_argument('--require-cpu', default='')
    args = parser.parse_args(); run(args.package.resolve(), args.output.resolve(), args.require_cpu)
