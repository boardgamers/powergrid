"""Recover public discount inputs from the existing training split, without labels or gradients.

The new cache preserves the old menus and target-column identities. It is not an
admission to reuse old continuation targets for a changed engine or new options.
"""
from collections import Counter, defaultdict
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'ai/runs/auction-discount-features-v1'
RESULT = ROOT / 'ai/strong/auction-discount-features-results-v1.json'


def read(path):
    return json.loads(path.read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')


def main():
    assert not OUT.exists() and not RESULT.exists(), 'Inspect any prior preparation before retrying'
    protocol_path = ROOT / 'ai/strong/policy-iteration-labels-protocol-v2.json'
    protocol = read(protocol_path)
    selected = ROOT / 'ai/runs/policy-iteration-selected-v2'
    for name, sha in protocol['roots']['files'].items():
        assert digest(selected / name) == sha
    old = ROOT / 'ai/runs/policy-iteration-features-v2'
    check = read(old / 'feature-check.json')
    assert check == read(ROOT / 'ai/strong/policy-iteration-feature-cache-results-v2.json')
    assert check['label_protocol_sha256'] == digest(protocol_path)
    for name, sha in check['artifacts'].items():
        assert digest(old / name) == sha
    metadata = read(old / 'metadata.json')
    index = read(selected / 'selected-index.json')
    assert len(index) == len(metadata) == 17280
    assert all(all(meta[k] == v for k, v in row.items()) for row, meta in zip(index, metadata))
    slots = {row['rootId']: i for i, row in enumerate(metadata)}
    assert len(slots) == 17280
    with np.load(old / 'features.npz', allow_pickle=False) as inputs:
        original = dict(inputs)
    assert original['state'].shape == (17280, 1217)
    assert original['actions'].shape == (17280, 7, 101)
    artifact = ROOT / 'ai/runs/resource-turn-full-artifact-v4'
    assert digest(artifact / 'manifest.json') == 'ce05c01a314305f5f0b3f7b55f6a8e13355ee0edb9bf5cae2c9688efd55cf795'
    for name, sha in read(artifact / 'manifest.json').items():
        assert digest(artifact / name) == sha
    engine = ROOT / 'ai/runs/current-engine-compatibility-v1'
    proof = read(ROOT / 'ai/strong/current-engine-compatibility-evidence-v1.json')
    assert digest(engine / 'build.json') == proof['build_sha256']
    for name, sha in read(engine / 'build.json')['compiled_files'].items():
        assert digest(engine / 'source/engine' / name) == sha

    OUT.mkdir()
    worker = Path(__file__).with_suffix('.cjs').with_name('auction-discount-feature-cache-v1.cjs')
    design = {'created_at': datetime.now(timezone.utc).isoformat(),
        'scope': 'Existing training-root input recovery and pricing coverage; no outcome-based selection.',
        'roots': protocol['roots'], 'parent_features_sha256': digest(old / 'features.npz'),
        'parent_metadata_sha256': digest(old / 'metadata.json'),
        'parent_feature_check_sha256': digest(old / 'feature-check.json'),
        'frozen_artifact_manifest_sha256': digest(artifact / 'manifest.json'),
        'current_engine_commit': proof['current_engine_commit'],
        'current_engine_build_sha256': digest(engine / 'build.json'),
        'feature_revision': '4.4-auction-discount', 'state_dim': 1218, 'action_dim': 103,
        'state_append': ['public plantDiscountActive bit'],
        'action_append': ['nomination opening bid / 50', 'nomination discount / 50'],
        'non_nomination_append': [0, 0],
        'code': {str(p.relative_to(ROOT)): digest(p) for p in [Path(__file__), worker,
            ROOT / 'ai/strong/features-v4_4.cjs', ROOT / 'ai/strong/policy-iteration-input-hashes.cjs']},
        'new_hf_jobs': 0, 'new_inference': 0, 'new_games': 0, 'new_gradients': 0,
        'qualification_eligible': False, 'reserved_final_seeds_used': False}
    save(OUT / 'design.json', design)
    extended = {k: v.copy() for k, v in original.items()}
    extended['state'] = np.zeros((17280, 1218), np.float32)
    extended['actions'] = np.zeros((17280, 7, 103), np.float32)
    counts = Counter()
    groups = defaultdict(Counter)
    missing_options = []
    seen = set()
    started = time.monotonic()
    with (OUT / 'worker.stderr.log').open('x') as log:
        process = subprocess.Popen(['node', str(worker), str(artifact / 'runtime'), str(engine / 'source/engine')],
            cwd='/tmp', stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=log, text=True)
        try:
            with gzip.open(selected / 'roots.jsonl.gz', 'rt') as source:
                while True:
                    batch = []
                    for _ in range(32):
                        line = source.readline()
                        if not line:
                            break
                        root = json.loads(line)
                        assert root['rootId'] not in seen
                        i = slots[root['rootId']]
                        meta = metadata[i]
                        assert hashlib.sha256(json.dumps(root['request'], sort_keys=True).encode()).hexdigest() == meta['public_root_sha256'] == root['public_root_sha256']
                        assert all(root[k] == meta[k] for k in ['players', 'behavior', 'mode', 'deal', 'split', 'variant', 'sealed', 'decision', 'round'])
                        assert root['split'] == ('validation' if root['deal'] in [0, 4, 8, 12] else 'train')
                        assert root['gameSeed'].startswith('policy-iteration-training-v2-')
                        assert type(root['request']['state'].get('plantDiscountActive')) is bool
                        batch.append(root)
                        seen.add(root['rootId'])
                    if not batch:
                        break
                    process.stdin.write(json.dumps([{k: r[k] for k in ['rootId', 'request', 'legal']} for r in batch]) + '\n')
                    process.stdin.flush()
                    response = process.stdout.readline()
                    assert response, 'Feature worker failed; inspect preserved stderr log'
                    answers = json.loads(response)
                    assert len(answers) == len(batch)
                    for root, answer in zip(batch, answers):
                        assert answer['rootId'] == root['rootId']
                        i = slots[root['rootId']]
                        meta = metadata[i]
                        assert answer['policy_input_sha256'] == meta['policy_input_sha256']
                        options = meta['options']
                        n = len(options)
                        assert original['legal_indices'][i, :n].tolist() == options
                        state = np.asarray(answer['state'], np.float32)
                        actions = np.asarray(answer['actions'], np.float32)
                        assert state.shape == (1218,) and actions.shape == (len(root['legal']), 103)
                        np.testing.assert_array_equal(state[:1217], original['state'][i])
                        np.testing.assert_array_equal(actions[options, :101], original['actions'][i, :n])
                        extended['state'][i] = state
                        extended['actions'][i, :n] = actions[options]
                        g = root['request']['state']
                        flags = {'positions': 1, 'discount_active': int(g['plantDiscountActive']),
                            'nomination': int(root['decision'] == 'nomination')}
                        if root['decision'] == 'nomination':
                            discounted = [j for j, move in enumerate(root['legal']) if move['name'] == 'ChoosePowerPlant' and actions[j, 102] > 0]
                            flags['discounted_nomination_in_old_menu'] = int(bool(discounted))
                            flags['discounted_nomination_labelled'] = int(any(j in options for j in discounted))
                            flags['discounted_nomination_excluded_by_shortlist'] = int(bool(discounted) and not any(j in options for j in discounted))
                            old_choices = {m['data'] for m in root['legal'] if m['name'] == 'ChoosePowerPlant'}
                            additions = sorted(set(answer['current_nominations']) - old_choices)
                            removals = sorted(old_choices - set(answer['current_nominations']))
                            flags['current_nomination_menu_has_additions'] = int(bool(additions))
                            flags['current_nomination_menu_has_removals'] = int(bool(removals))
                            if additions or removals:
                                missing_options.append({'rootId': root['rootId'], 'split': root['split'],
                                    'players': root['players'], 'variant': root['variant'], 'sealed': root['sealed'],
                                    'round': root['round'], 'money': g['players'][root['request']['player']]['money'],
                                    'additions': additions, 'removals': removals})
                        counts.update(flags)
                        key = f"{root['split']}/{root['players']}p/{root['variant']}/{'sealed' if root['sealed'] else 'open'}/{root['decision']}"
                        groups[key].update(flags)
                    if len(seen) % 2048 == 0:
                        print({'encoded_roots': len(seen), 'seconds': time.monotonic() - started}, flush=True)
        finally:
            process.stdin.close()
            try:
                code = process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                process.terminate()
                process.wait(timeout=5)
                raise
            process.stdout.close()
    assert code == 0 and len(seen) == 17280
    assert all(np.isfinite(v).all() for v in extended.values())
    np.testing.assert_array_equal(extended['state'][:, :1217], original['state'])
    np.testing.assert_array_equal(extended['actions'][:, :, :101], original['actions'])
    assert (extended['actions'][~extended['mask']] == 0).all()
    np.savez_compressed(OUT / 'features.npz', **extended)
    save(OUT / 'current-menu-differences.json', missing_options)
    report = {'complete': True, 'counts': dict(counts), 'groups': dict(groups),
        'split_counts': dict(Counter(m['split'] for m in metadata)),
        'parent_prefixes_and_full_input_hashes_exact': 17280,
        'old_target_column_mapping_preserved': True,
        'current_engine_pricing_checked_for_all_old_nominations': True,
        'design_sha256': digest(OUT / 'design.json'), 'seconds': time.monotonic() - started,
        'artifacts': {p.name: digest(p) for p in OUT.iterdir() if p.is_file()},
        'training_ready': False, 'qualification_eligible': False, 'reserved_final_seeds_used': False,
        'new_hf_jobs': 0, 'new_inference': 0, 'new_games': 0, 'new_gradients': 0,
        'interpretation': 'Append-only candidate inputs on the unchanged historical training/validation roots. No outcomes were inspected or new targets generated. The saved targets use old continuation policies/engine and a restricted shortlist; new actions have no saved labels. Engine/teacher/target compatibility and a separately designed training experiment remain required. No playing-strength claim.'}
    save(OUT / 'assessment.json', report)
    save(RESULT, report)
    print(json.dumps({k: report[k] for k in ['complete', 'counts', 'split_counts', 'seconds', 'training_ready']}), flush=True)


if __name__ == '__main__':
    main()
