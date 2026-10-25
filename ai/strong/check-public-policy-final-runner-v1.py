"""Frozen engineering execution for final wrapper; never spend final seeds."""
import argparse
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from public_policy_final_audit_v1 import artifact_identity, audit_shard, digest, read, PROTOCOL_SHA
from public_policy_final_contract_v1 import audit_execution_binding
from public_policy_arena_v1 import semantic, arena_semantic

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'ai/runs/public-policy-final-runner-preflight-v1'
BASE = ROOT/'ai/runs/opponent-auction-runtime-preflight-v1/package'
FILTER_GOLD = ROOT/'ai/runs/public-policy-arena-preflight-v1'
AUCTION_GOLD = ROOT/'ai/runs/opponent-auction-engineering-games-v1'
ADDITIONS = ['public_policy_final_audit_v1.py', 'public_policy_final_contract_v1.py', 'public_policy_final_runner_v1.py']


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False)+'\n')


def now():
    return datetime.now(timezone.utc).isoformat()


def pinned(prepared):
    package = OUT/'package'
    assert digest(package/'manifest.json') == prepared['runtime_manifest_sha256']
    assert all(digest(package/name) == sha for name, sha in read(package/'manifest.json').items())
    assert all(digest(ROOT/name) == sha for name, sha in prepared['source_hashes'].items())
    assert all(digest(ROOT/name) == sha for name, sha in prepared['original_input_hashes'].items())
    assert all(digest(OUT/name) == sha for name, sha in prepared['control_hashes'].items())


def prepare():
    assert not OUT.exists(), 'Inspect original package/run before any replacement'
    original_manifest = read(BASE/'manifest.json')
    assert all(digest(BASE/name) == sha for name, sha in original_manifest.items())
    original_proof = read(ROOT/'ai/strong/opponent-auction-runtime-preflight-v1.json')
    assert digest(BASE/'manifest.json') == original_proof['manifest_sha256']
    assert digest(BASE/'policy.json') == original_proof['policy_sha256']
    package = OUT/'package'; package.parent.mkdir()
    shutil.copytree(BASE, package)
    for name in ADDITIONS:
        target = package/'ai/strong'/name
        assert not target.exists()
        shutil.copy2(ROOT/'ai/strong'/name, target)
    opponent = Path(read(FILTER_GOLD/'3p/evaluation.json')['config']['opponent_model'])
    shutil.copy2(opponent, package/'final-opponent-a260.onnx')
    manifest = {str(p.relative_to(package)): digest(p) for p in sorted(package.rglob('*'))
                if p.is_file() and str(p.relative_to(package)) not in ('manifest.json', 'policy.json')}
    assert all(manifest[name] == sha for name, sha in original_manifest.items())
    write(package/'manifest.json', manifest)
    spec = read(package/'policy.json'); spec['runtime_manifest']['sha256'] = digest(package/'manifest.json')
    write(package/'policy.json', spec)
    filtered = {k: v for k, v in spec.items() if k != 'opponent'}
    filtered.update(backend='population-v1', settings={k: v for k, v in spec['settings'].items()
                                                    if k not in ('population_modes', 'minimum_advantage')})
    filtered['settings']['arm'] = 'filter'; write(package/'policy-filter.json', filtered)
    identities = {name: artifact_identity(package, name) for name in ('policy.json', 'policy-filter.json')}
    original_inputs = {}
    cases = []
    for n in range(2, 7):
        directory = FILTER_GOLD/f'{n}p'; report = read(directory/'evaluation.json'); cfg = report['config']
        original_inputs.update({str(p.relative_to(ROOT)): digest(p) for p in directory.iterdir() if p.is_file()})
        cases.append({'name': f'filter-{n}p', 'descriptor': 'policy-filter.json', 'reference': str(directory),
                      **{k: cfg[k] for k in ('players', 'opponent', 'opponent_sha256', 'seed', 'start', 'deals')}})
    original_inputs.update({str(p.relative_to(ROOT)): digest(p) for p in AUCTION_GOLD.iterdir() if p.is_file()})
    cases.append({'name': 'filter-offset-2p', 'descriptor': 'policy-filter.json', 'reference': str(OUT/'reference-offset'),
                  'players': 2, 'opponent': 'legacy', 'opponent_sha256': None,
                  'seed': 'final-wrapper-engineering-offset-v1', 'start': 4, 'deals': 1})
    cases.append({'name': 'auction-2p', 'descriptor': 'policy.json', 'reference': str(AUCTION_GOLD),
                  'players': 2, 'opponent': 'economic', 'opponent_sha256': None,
                  'seed': 'opponent-auction-engineering-v1-2p', 'start': 0, 'deals': 1})
    controls = OUT/'controls'; controls.mkdir()
    for name, identity in identities.items():
        write(controls/(name+'.candidate.json'), {'status': 'engineering', 'frozen_at': now(),
              'identity': identity, 'protocol_sha256': PROTOCOL_SHA, 'selection_evidence': None})
    for case in cases:
        n = case['players']; name = case['name']
        shard = {'name': name, 'group': case['opponent']+'/'+str(n)+'p',
                 **{k: case[k] for k in ('players', 'start', 'deals', 'seed', 'opponent', 'opponent_sha256')}, 'games': 4*n}
        candidate = controls/(case['descriptor']+'.candidate.json')
        contract = controls/(name+'.contract.json')
        write(contract, {'version': 1, 'purpose': 'engineering', 'created_at': now(),
              'candidate_sha256': digest(candidate), 'protocol_sha256': PROTOCOL_SHA,
              'identity': identities[case['descriptor']], 'shard': shard, 'launch_authorization': None})
        command = [sys.executable, '-u', '-B', str(package/'ai/strong/public_policy_final_runner_v1.py'),
                   '--artifact', str(package), '--descriptor', case['descriptor'],
                   '--candidate', str(candidate), '--contract', str(contract),
                   '--workers', '4', '--output', str(OUT/name)]
        if case['opponent'] == 'a260':
            command += ['--opponent-model', str(package/'final-opponent-a260.onnx')]
        case.update(shard=shard, command=command)
    source_paths = [ROOT/'ai/strong'/name for name in [*ADDITIONS, 'check-public-policy-final-runner-v1.py',
                    'test_public_policy_final_runner_v1.py', 'final-protocol-multiplayer.json']]
    tests = ROOT/'ai/runs/public-policy-final-runner-tests-v1.log'
    assert 'Ran 8 tests' in tests.read_text() and tests.read_text().rstrip().endswith('OK')
    source_paths.append(tests)
    prepared = {'prepared_at': now(), 'cases': cases, 'identities': identities,
                'runtime_manifest_sha256': digest(package/'manifest.json'),
                'unchanged_original_runtime_files': len(original_manifest),
                'base_runtime_archive': original_proof['archive'],
                'source_hashes': {str(p.relative_to(ROOT)): digest(p) for p in source_paths},
                'original_input_hashes': original_inputs,
                'control_hashes': {str(p.relative_to(OUT)): digest(p) for p in controls.iterdir()},
                'new_wrapper_games': 96, 'new_offset_reference_games': 8,
                'gradients': False, 'new_hf_jobs': 0, 'new_strength_games': 0,
                'candidate_selected': False, 'reserved_final_seeds_used': False, 'qualification_eligible': False}
    prepared['control_hashes'].update({str((package/name).relative_to(OUT)): digest(package/name) for name in identities})
    write(OUT/'prepared.json', prepared); pinned(prepared)
    print(json.dumps({'prepared': True, 'unchanged_runtime_files': len(original_manifest),
                      'wrapper_games': 96, 'reference_games': 8}), flush=True)


def run():
    prepared = read(OUT/'prepared.json'); pinned(prepared)
    with (OUT/'.owner.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        assert not (OUT/'state.json').exists(), 'Original execution has an owner; inspect it rather than retry'
        state = {'pid': os.getpid(), 'started_at': now(), 'stage': 'validating', 'completed': [], 'new_hf_jobs': 0,
                 'reserved_final_seeds_used': False}; write(OUT/'state.json', state)
        try:
            for case in prepared['cases']:
                with (OUT/(case['name']+'.validation.log')).open('x') as log:
                    subprocess.run(case['command'], cwd='/tmp', stdout=log, stderr=subprocess.STDOUT, check=True)
                assert not (OUT/case['name']).exists(), 'Dry run executed games'
            state.update(stage='reference-offset', updated_at=now()); write(OUT/'state.json', state)
            original = FILTER_GOLD/'package'
            command = [sys.executable, '-u', '-B', str(original/'ai/strong/public_policy_arena_v1.py'),
                       '--artifact', str(original), '--players', '2', '--opponent', 'legacy',
                       '--seed', 'final-wrapper-engineering-offset-v1', '--start', '4', '--deals', '1',
                       '--workers', '4', '--output', str(OUT/'reference-offset')]
            with (OUT/'reference-offset.log').open('x') as log:
                subprocess.run(command, cwd='/tmp', stdout=log, stderr=subprocess.STDOUT, check=True)
            state['completed'].append('reference-offset')
            for case in prepared['cases']:
                pinned(prepared); state.update(stage=case['name'], updated_at=now()); write(OUT/'state.json', state)
                with (OUT/(case['name']+'.execution.log')).open('x') as log:
                    subprocess.run([*case['command'], '--execute'], cwd='/tmp', stdout=log, stderr=subprocess.STDOUT, check=True)
                state['completed'].append(case['name'])
            pinned(prepared); state.update(stage='complete', updated_at=now()); write(OUT/'state.json', state)
        except BaseException as error:
            state.update(stage='stopped_for_inspection', error=type(error).__name__+': '+str(error), updated_at=now())
            write(OUT/'state.json', state)
            raise


def comparable_request(request):
    return arena_semantic({'observations': [{'request': request}], 'ended': []})


def verify():
    assert not (OUT/'result.json').exists(), 'Preserve the original verification'
    prepared = read(OUT/'prepared.json'); pinned(prepared)
    state = read(OUT/'state.json'); assert state['stage'] == 'complete'
    assert state['completed'] == ['reference-offset', *[case['name'] for case in prepared['cases']]]
    runner_sha = digest(OUT/'package/ai/strong/public_policy_final_runner_v1.py')
    results = {}; games = decisions = continuations = 0
    for case in prepared['cases']:
        directory = OUT/case['name']; identity = prepared['identities'][case['descriptor']]
        audit = audit_shard(directory, case['shard'], identity, reserved=False)
        binding = audit_execution_binding(directory, identity, runner_sha)
        assert read(directory/'audit.json') == {**audit, 'execution_binding': binding}
        report = read(directory/'evaluation.json'); reference = Path(case['reference']); gold = read(reference/'evaluation.json')
        assert gold['passed'] and gold['all_complete'] and not gold['errors']
        assert {r['episode'] for r in report['results']} == {r['episode'] for r in gold['results']}
        for current, original in zip(report['results'], gold['results']):
            assert current['terminal'] == original['terminal'], 'Wrapper changed complete-game outcome'
            episode = current['episode']; local_count = 0
            with (directory/f'decisions-{episode}.jsonl').open() as left, (reference/f'decisions-{episode}.jsonl').open() as right:
                for a, b in zip(left, right, strict=True):
                    a, b = json.loads(a), json.loads(b)
                    assert comparable_request(a['publicRequest']) == comparable_request(b['publicRequest'])
                    assert semantic(a['publicResponse']['decision']) == semantic(b['publicResponse']['decision'])
                    assert a['arenaMoves'] == b['arenaMoves'] and a['arenaPlayerOrder'] == b['arenaPlayerOrder']
                    local_count += 1
            assert local_count == current['decisions'] == original['decisions']; decisions += local_count
        results[case['name']] = {'games': len(report['results']), 'counts': audit['counts'],
                                'evaluation_sha256': digest(directory/'evaluation.json'),
                                'audit_sha256': digest(directory/'audit.json')}
        games += len(report['results']); continuations += audit['counts']['rollouts']
    assert games == 96 and continuations == 22048
    pinned(prepared)
    result = {'complete': True, 'checked_at': now(), 'games': games, 'offset_reference_games': 8,
              'exact_public_decisions': decisions, 'exact_continuations': continuations,
              'all_game_terminals_exact': True, 'caps': 0, 'cases': results,
              'prepared_sha256': digest(OUT/'prepared.json'), 'contract_tests': 8,
              'candidate_selected': False, 'qualified': False, 'reserved_final_seeds_used': False,
              'remaining': ['HF source/launch admission with original intent reconciliation',
                            'actual selected-policy strength and export/8840U/package qualification']}
    write(OUT/'result.json', result); print(json.dumps(result), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('operation', choices=['prepare', 'run', 'verify'])
    globals()[parser.parse_args().operation]()
