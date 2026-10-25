"""Standalone engineering check on existing runtime fixtures, not strength seeds."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'ai/runs/opponent-auction-runtime-preflight-v1'
SOURCE = ROOT / 'ai/runs/surrogate-continuation-study-source-prepared-v1/layout'
ENTRY = 'ai/strong/public_policy_runtime_v1.py'
OPPONENT = 'ai/strong/fixtures/surrogate-continuation-selected-members-v1/policy.json'
ROOTS = 'ai/strong/fixtures/surrogate-continuation-runtime-roots-v1.json'
OVERLAYS = [ENTRY, 'ai/strong/public_policy_arena_v1.py', 'ai/strong/public-arena-bridge.cjs',
            'ai/strong/opponent_auction_policy_v1.py', 'ai/strong/opponent_auction_verification_v1.py']


def read(path):
    return json.loads(path.read_text())


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def copy(source, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    assert digest(source) == digest(target)


def prepare():
    assert not OUT.exists(), 'Inspect the original run before any repair/retry'
    source = read(ROOT / 'ai/strong/surrogate-continuation-study-source-v1.json')
    source_manifest = SOURCE / 'surrogate-continuation-study-source-manifest.json'
    assert digest(source_manifest) == source['manifest_sha256']
    hashes = read(source_manifest)
    assert all(digest(SOURCE / name) == sha for name, sha in hashes.items())
    package = OUT / 'package'
    package.mkdir(parents=True)
    for name in hashes:
        copy(SOURCE / name, package / name)
    for name in OVERLAYS:
        copy(ROOT / name, package / name)
    copy(ROOT / 'ai/runs/policy-iteration-trained-8840u-prepared-v2/local-package-frozen-1/policy.onnx', package / 'policy.onnx')
    copy(SOURCE / 'ai/strong/fixtures/surrogate-continuation-study-inputs-v1/policy.json', package / OPPONENT)
    manifest = {str(p.relative_to(package)): digest(p) for p in package.rglob('*') if p.is_file()}
    write(package / 'manifest.json', manifest)
    common = {'version': 1, 'feature_revision': '4.3-strategic-correction',
              'model': {'path': 'policy.onnx', 'sha256': manifest['policy.onnx']},
              'runtime_manifest': {'path': 'manifest.json', 'sha256': digest(package / 'manifest.json')}}
    settings = {'arm': 'auction', 'samples': 8, 'workers': 4, 'threads': 1, 'max_steps': 2400,
                'population_modes': ['neural_population', 'surrogate_opponent_v1'], 'minimum_advantage': '1/8'}
    specification = {**common, 'backend': 'opponent-auction-v1',
                     'opponent': {'path': OPPONENT, 'sha256': manifest[OPPONENT]}, 'settings': settings}
    write(package / 'policy.json', specification)
    write(package / 'cap.json', {**specification, 'settings': {**settings, 'max_steps': 1}})
    bad = {**specification, 'opponent': {**specification['opponent'], 'sha256': '0' * 64}}
    write(package / 'bad-opponent.json', bad)
    for arm in ('model', 'filter'):
        write(package / (arm + '.json'), {**common, 'backend': 'population-v1',
            'settings': {'arm': arm, 'samples': 8, 'workers': 1, 'threads': 1, 'max_steps': 2400}})
    # Verify the old evidence manifests before copying their fixed-action gold.
    pop_descriptor = read(ROOT / 'ai/strong/surrogate-continuation-cost-complete-evidence-v1.json')
    pop_manifest_path = ROOT / 'ai/runs/surrogate-continuation-cost-complete-evidence-v1/manifest.json'
    assert digest(pop_manifest_path) == pop_descriptor['manifest_sha256']
    pop_manifest = read(pop_manifest_path)
    selected = ROOT / 'ai/runs/surrogate-continuation-selected-cost-collected-v1/artifacts'
    selected_descriptor = read(ROOT / 'ai/strong/surrogate-continuation-selected-cost-results-v1.json')
    assert digest(selected / 'manifest.json') == selected_descriptor['evidence']['manifest_sha256']
    selected_manifest = read(selected / 'manifest.json')
    roots = read(package / ROOTS)['roots']
    assert len(roots) == 24 and all(r['identity']['mode'] == 'runtime' for r in roots.values())
    gold_hashes = {}
    for name in roots:
        population = ROOT / f'ai/runs/surrogate-continuation-cost-collected-v1/surrogate-continuation-cost-v1-{name}/artifacts/neural_population/result.json'
        surrogate = selected / name / 'result.json'
        assert digest(population) == pop_manifest[str(population.relative_to(ROOT))]
        assert digest(surrogate) == selected_manifest[str(surrogate.relative_to(selected))]
        for mode, path in [('neural_population', population), ('surrogate_opponent_v1', surrogate)]:
            target = OUT / 'reference' / name / (mode + '.json')
            copy(path, target)
            gold_hashes[str(target.relative_to(OUT))] = digest(target)
    # One saved model/filter fixture for each count exercises the old backend.
    old = ROOT / 'ai/runs/population-policy-8840u-prepared-v2/package'
    fixture_path = old / 'fixtures.jsonl'
    old_manifest = read(old / 'manifest.json')
    assert digest(fixture_path) == old_manifest['files']['fixtures.jsonl']
    chosen = {}
    with fixture_path.open() as stream:
        for i, line in enumerate(stream):
            row = json.loads(line)
            n = len(row['request']['state']['players'])
            chosen.setdefault(n, {'index': i, 'fixture': row})
            if len(chosen) == 5:
                break
    reference = ROOT / 'ai/runs/population-policy-local-reference-v2'
    old_status = read(reference / 'status.json')
    assert digest(reference / 'model-filter.jsonl') == old_status['output_hashes']['model-filter.jsonl']
    indices = {value['index']: value for value in chosen.values()}
    with (reference / 'model-filter.jsonl').open() as stream:
        for line in stream:
            row = json.loads(line)
            if row['index'] in indices:
                indices[row['index']]['gold'] = row['results']
    write(OUT / 'legacy-fixtures.json', list(chosen.values()))
    write(OUT / 'prepared.json', {'source': source, 'checker_sha256': digest(Path(__file__)),
          'manifest_sha256': digest(package / 'manifest.json'), 'policy_sha256': digest(package / 'policy.json'),
          'unchanged_source_files': sum(manifest.get(name) == sha for name, sha in hashes.items()),
          'overlays': {name: manifest[name] for name in OVERLAYS}, 'gold_hashes': gold_hashes,
          'scope': 'Engineering settings only: equal populations, eight worlds each, strict 1/8 margin plus per-population nonnegative margin. No recipe selection or strength claim; full fidelity results remain pending.',
          'new_hf_jobs': 0, 'gradients': False, 'qualification_eligible': False, 'reserved_final_seeds_used': False})
    with (OUT / 'verify.log').open('x') as log:
        subprocess.run([sys.executable, '-u', '-B', str(Path(__file__).resolve()), 'verify'], cwd='/tmp',
                       stdout=log, stderr=subprocess.STDOUT, check=True,
                       env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'})


def verify():
    package = OUT / 'package'
    prepared = read(OUT / 'prepared.json')
    assert prepared['checker_sha256'] == digest(Path(__file__))
    assert prepared['manifest_sha256'] == digest(package / 'manifest.json')
    assert all(digest(OUT / name) == sha for name, sha in prepared['gold_hashes'].items())
    sys.path.insert(0, str(package / 'ai/strong'))
    from public_policy_arena_v1 import PublicPolicyProcess, semantic
    from public_policy_runtime_v1 import load_artifact
    from opponent_auction_verification_v1 import verify_decision
    spec = read(package / 'policy.json')
    direct = load_artifact(package)
    identity = direct.identity
    roots = read(package / ROOTS)['roots']
    result = {'complete': False, 'fixtures': 0, 'auction_searches': 0, 'unchanged_nonauction': 0,
              'continuations': 0, 'exact_archived_continuations': 0, 'overrides': 0,
              'legacy_backend_checks': 0, 'caps': 0, 'new_hf_jobs': 0, 'new_strength_games': 0,
              'gradients': False, 'qualification_eligible': False, 'reserved_final_seeds_used': False}
    stderr = (OUT / 'policy.stderr.log').open('x')
    process = PublicPolicyProcess(package, 'policy.json', stderr)
    try:
        with (OUT / 'decisions.jsonl').open('x') as stream:
            for name, root in sorted(roots.items()):
                q = {**root['request'], 'requestId': name, 'revision': 1}
                response = process.call(q)
                assert 'error' not in response, response
                assert response['requestId'] == name and response['revision'] == 1
                assert all(response[k] == v for k, v in identity.items())
                legal = direct.prepare(q)['moves']
                assert legal == root['moves']
                row = {**response['decision'], 'arenaMoves': legal}
                assert response['move'] == legal[row['index']]
                assert row['modelProposal'] == root['model_proposal']
                config = {'players': len(q['state']['players']), 'arm': 'opponent-auction-v1',
                          'samples': 8, 'model_sha256': identity['modelSha256'], 'identity': identity}
                checked = verify_decision(row, config, q['player'])
                result['caps'] += checked['rollout_caps']
                result['continuations'] += checked['rollouts']
                result['overrides'] += checked['search_changes']
                if row['search']:
                    assert root['phase'] in ('plant', 'bid')
                    assert row['search']['priorActors'] == root['prior_actors']
                    result['auction_searches'] += 1
                    for component in row['search']['components']:
                        expected = read(OUT / 'reference' / name / (component['mode'] + '.json'))
                        actual = {(r['sample'], r['actionIndex']): r for r in component['rows']}
                        for gold in expected['rows']:
                            receipt = actual[gold['sample'], gold['actionIndex']]
                            assert {k: v for k, v in receipt.items() if k != 'env'} == {
                                k: v for k, v in gold.items() if k != 'env'}, (name, component['mode'], gold['sample'])
                            result['exact_archived_continuations'] += 1
                else:
                    assert root['phase'] == 'building' and row['index'] == root['options'][0]
                    result['unchanged_nonauction'] += 1
                stream.write(json.dumps({'name': name, 'request': q, 'response': response, 'verification': checked}) + '\n')
                stream.flush()
                result['fixtures'] += 1
                print({'fixture': name, 'search': row['search'] is not None, 'overrides': result['overrides']}, flush=True)
        # Direct/standalone and changed-metadata parity on one existing auction root.
        name = sorted(name for name, root in roots.items() if root['phase'] == 'bid')[0]
        q = {**roots[name]['request'], 'requestId': 'repeat', 'revision': 2, 'referenceOpponent': 'ignored'}
        response = process.call(q)
        gold = direct.choose(q)
        assert semantic(response['decision']) == semantic(gold)
        write(OUT / 'repeat.json', {'request': q, 'response': response, 'direct': gold})
        process.close(); process = None
        for arm in ('model', 'filter'):
            process = PublicPolicyProcess(package, arm + '.json', stderr)
            for entry in read(OUT / 'legacy-fixtures.json'):
                response = process.call(entry['fixture']['request'])
                assert 'error' not in response, response
                assert semantic(response['decision']) == semantic(entry['gold'][arm])
                result['legacy_backend_checks'] += 1
            process.close(); process = None
        process = PublicPolicyProcess(package, 'cap.json', stderr)
        capped = process.call(q)
        assert 'error' not in capped and capped['decision']['search']['truncated'] > 0
        assert capped['decision']['index'] == capped['decision']['modelProposal']
        assert capped['decision']['search']['selection']['fallbackReason'] == 'incomplete-rollouts'
        write(OUT / 'intentional-cap.json', capped)
        process.close(); process = None
        process = PublicPolicyProcess(package, 'bad-opponent.json', stderr)
        invalid = process.call(q)
        assert 'Artifact pin mismatch: opponent' in invalid['error']
        write(OUT / 'invalid-opponent.json', invalid)
        assert result['fixtures'] == 24 and result['auction_searches'] == 16 and result['unchanged_nonauction'] == 8
        assert result['exact_archived_continuations'] == 512 and result['legacy_backend_checks'] == 10 and result['caps'] == 0
        result.update(complete=True, manifest_sha256=prepared['manifest_sha256'], policy_sha256=prepared['policy_sha256'],
                      direct_and_standalone_exact=True, intentional_caps_keep_model=True, invalid_opponent_pin_rejected=True,
                      settings_selected_for_strength=False, final_adapter_ready=False,
                      scope=prepared['scope'])
        write(OUT / 'result.json', result)
        print(result, flush=True)
    finally:
        if process is not None:
            process.close()
        stderr.close()
        direct.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('operation', choices=['prepare', 'verify'])
    globals()[parser.parse_args().operation]()
