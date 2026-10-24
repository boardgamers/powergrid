"""Reduce the complete independently verified grid once, before HF gradients."""
from collections import Counter
from pathlib import Path
import shutil
import time

import numpy as np
from strategic_collection import ROOT, read, write, digest
from policy_iteration_data import load_labels, target_arrays, validate_manifest, PROTOCOL, SOURCE


def main():
    manifest_path = ROOT/'ai/strong/policy-iteration-labels-results-v2.json'
    manifest = read(manifest_path)
    validate_manifest(manifest, read(PROTOCOL), read(SOURCE))
    features = ROOT/'ai/runs/policy-iteration-features-v2'
    check = read(features/'feature-check.json')
    assert check['complete'] and check['positions'] == 17280
    assert check['label_protocol_sha256'] == digest(PROTOCOL)
    for file, sha in check['artifacts'].items():
        assert digest(features/file) == sha
    metadata = read(features/'metadata.json')
    with np.load(features/'features.npz', allow_pickle=False) as f:
        inputs = dict(f)
    assert inputs['state'].shape == (17280, 1217) and inputs['actions'].shape == (17280, 7, 101)
    assert inputs['mask'].shape == (17280, 7) and inputs['mask'].dtype == bool
    assert (inputs['state'][:, -1] == 1).all()
    for i, meta in enumerate(metadata):
        n = len(meta['options'])
        assert inputs['legal_indices'][i, :n].tolist() == meta['options']
        assert inputs['legal_indices'][i, n:].tolist() == [-1]*(7-n)
        assert inputs['proposal_index'][i] == meta['options'].index(meta['model_proposal'])
    started = time.monotonic()
    bank = load_labels(manifest, metadata)
    reduced = target_arrays(bank, metadata, inputs['mask'])
    del bank
    parent = np.arange(17280), inputs['proposal_index']
    assert (reduced['target'][parent] == 0).all() and (reduced['variance_of_mean'][parent] == 0).all()
    for values in reduced.values():
        assert np.isfinite(values).all() and (values[~inputs['mask']] == 0).all()
    weight = reduced['precision'][inputs['mask']]
    assert (weight >= .25).all() and (weight <= 1).all()
    out = ROOT/'ai/runs/policy-iteration-training-data-v2'
    out.mkdir(exist_ok=False)
    shutil.copy2(features/'features.npz', out/'features.npz')
    shutil.copy2(features/'metadata.json', out/'metadata.json')
    shutil.copy2(features/'feature-check.json', out/'feature-check.json')
    shutil.copy2(manifest_path, out/'label-manifest.json')
    np.savez_compressed(out/'targets.npz', **reduced)
    report = {'complete': True, 'positions': 17280, 'split_counts': dict(Counter(m['split'] for m in metadata)),
              'label_manifest_sha256': digest(manifest_path), 'label_protocol_sha256': digest(PROTOCOL),
              'label_source': read(SOURCE), 'feature_check_sha256': digest(features/'feature-check.json'),
              'samples_per_root': 192, 'continuation_modes': ['neural', 'neural_economic'],
              'negative_advantages_retained': int((reduced['target'][inputs['mask']] < 0).sum()),
              'parent_targets_zero': True, 'uncertainty_weight_range': [float(weight.min()), float(weight.max())],
              'seconds': time.monotonic() - started,
              'code': {file: digest(ROOT/file) for file in ['ai/strong/policy_iteration_data.py', 'ai/strong/prepare-policy-iteration-training-data.py', 'ai/strong/strategic_correction_targets.py']},
              'artifacts': {f.name: digest(f) for f in out.iterdir()}, 'gradients': False, 'qualification_eligible': False}
    write(out/'data-check.json', report)
    write(ROOT/'ai/strong/policy-iteration-training-data-results-v2.json', report)
    print({k: report[k] for k in ['complete', 'positions', 'negative_advantages_retained', 'seconds']}, flush=True)


if __name__ == '__main__':
    main()
