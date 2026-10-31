"""HF-only tree learning probe; public inputs, existing targets, no serving change."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import time

import numpy as np


def read(path): return json.loads(Path(path).read_text())
def digest(path):
    with Path(path).open('rb') as f: return hashlib.file_digest(f, 'sha256').hexdigest()
def save(path, value):
    with Path(path).open('x') as f: json.dump(value, f, indent=2, allow_nan=False); f.write('\n')


def inputs(data, metadata):
    """No target, root ID, seed, deal or opponent identity enters model features."""
    rows, actions = np.nonzero(data['mask']); parent = data['proposal_index']
    # Exclude discard/eligibility and shortlist flags; retain the public discount inputs.
    state_indices = [*range(1215), 1217]; action_indices = [*range(100), 101, 102]
    state = data['state'][rows][:, state_indices]
    candidate = data['actions'][rows, actions][:, action_indices]
    baseline = data['actions'][rows, parent[rows]][:, action_indices]
    x = np.concatenate((state, candidate, baseline, candidate-baseline), axis=1).astype(np.float32)
    assert x.shape[1] == 1522 and np.isfinite(x).all()
    nonparent = data['mask'] & (np.arange(data['mask'].shape[1])[None] != parent[:, None])
    weight = data['precision'] * nonparent
    weight /= np.maximum(weight.sum(1, keepdims=True), 1e-12)
    train = np.array([r['split'] == 'train' for r in metadata])
    tune = train & np.array([r['deal'] in (11, 13) for r in metadata])
    groups = {'fit': np.flatnonzero(train & ~tune), 'tune': np.flatnonzero(tune),
              'legacy_validation': np.flatnonzero(~train)}
    game_groups = {}; public_groups = {}
    for group, ids in groups.items():
        for i in ids:
            m = metadata[i]
            assert m['split'] == ('validation' if m['deal'] in (0, 4, 8, 12) else 'train')
            assert game_groups.setdefault(m['source_game_seed'], group) == group
            assert public_groups.setdefault(m['public_root_sha256'], group) == group
    assert np.array_equal(train, data['train'])
    return x, rows, actions, weight[rows, actions].astype(np.float32), groups


def route(scores, mask, parent, margin=.025):
    assert np.isfinite(scores).all()
    scores = scores.copy(); scores[np.arange(len(scores)), parent] = 0.
    choice = np.where(mask, scores, -np.inf).argmax(1)
    return np.where(scores[np.arange(len(scores)), choice] > margin, choice, parent)


def dense(prediction, rows, actions, data):
    out = np.zeros(data['mask'].shape, np.float64); out[rows, actions] = prediction
    out[np.arange(len(out)), data['proposal_index']] = 0.
    return out


def metrics(scores, data, ids):
    parent = data['proposal_index'][ids]; mask = data['mask'][ids]
    choice = route(scores[ids], mask, parent); row = np.arange(len(ids))
    target = data['target'][ids]; achieved = target[row, choice]
    w = data['precision'][ids]*mask*(np.arange(mask.shape[1])[None] != parent[:, None])
    mse = ((scores[ids]-target)**2*w).sum(1)/np.maximum(w.sum(1), 1e-12)
    return {'roots': len(ids), 'weighted_mse': float(mse.mean()),
        'changes': int((choice != parent).sum()), 'mean_sampled_advantage': float(achieved.mean()),
        'positive_changes': int(((choice != parent) & (achieved > 0)).sum()),
        'negative_changes': int(((choice != parent) & (achieved < 0)).sum()),
        'mean_sampled_regret': float((np.where(mask, target, -np.inf).max(1)-achieved).mean()),
        'half_a_advantage': float(data['target_a'][ids][row, choice].mean()),
        'half_b_advantage': float(data['target_b'][ids][row, choice].mean())}


def json_predict(model, x):
    """Independent CPU evaluator for finite, numeric, single-output gbtree models."""
    learner = model['learner']; params = learner['learner_model_param']
    assert learner['objective']['name'] == 'reg:squarederror' and params['num_target'] == '1'
    assert params['num_class'] == '0' and int(params['num_feature']) == x.shape[1]
    booster = learner['gradient_booster']; assert booster['name'] == 'gbtree'
    trees = booster['model']; assert set(trees['tree_info']) == {0}
    assert trees['gbtree_model_param']['num_parallel_tree'] == '1'
    assert len(trees['trees']) == int(trees['gbtree_model_param']['num_trees'])
    assert np.isfinite(x).all()
    result = np.full(len(x), float(params['base_score']), np.float32)
    row = np.arange(len(x))
    for tree in trees['trees']:
        assert not tree['categories'] and set(tree['split_type']) <= {0}
        left = np.asarray(tree['left_children']); right = np.asarray(tree['right_children'])
        feature = np.asarray(tree['split_indices']); value = np.asarray(tree['split_conditions'], np.float32)
        node = np.zeros(len(x), np.int64)
        for _ in range(len(left)):
            live = left[node] != -1
            if not live.any(): break
            old = node[live]
            node[live] = np.where(x[row[live], feature[old]] < value[old], left[old], right[old])
        else: raise AssertionError('Tree traversal failed to terminate')
        assert (right[node] == -1).all()
        result += value[node]
    return result


def train(bundle, out):
    import xgboost as xgb
    import torch
    assert os.environ.get('POWERGRID_HF_TRAINING') == '1' and torch.cuda.is_available()
    assert xgb.__version__ == '2.1.4' and xgb.build_info()['USE_CUDA']
    assert not out.exists()
    design = read(bundle/'design.json'); data_report = read(bundle/'data/report.json')
    assert digest(bundle/'data/report.json') == design['data_report_sha256']
    assert all(digest(bundle/'data'/f) == sha for f, sha in data_report['files'].items())
    data = dict(np.load(bundle/'data/data.npz', allow_pickle=False)); meta = read(bundle/'data/metadata.json')
    x, rows, actions, weights, groups = inputs(data, meta)
    assert {k: len(v) for k, v in groups.items()} == design['split_counts']
    assert digest(__file__) == design['worker_sha256']
    fit = np.isin(rows, groups['fit']) & (weights > 0)
    tune = np.isin(rows, groups['tune']) & (weights > 0)
    target = data['target'][rows, actions].astype(np.float32)
    # Test/legacy-validation targets never enter these training/evaluation matrices.
    dfit = xgb.DMatrix(x[fit], label=target[fit], weight=weights[fit], nthread=4)
    dtune = xgb.DMatrix(x[tune], label=target[tune], weight=weights[tune], nthread=4)
    dall = xgb.DMatrix(x, nthread=4)
    out.mkdir(); start = time.monotonic(); records = []; saved_predictions = {}
    for depth in design['depths']:
        members = []
        for seed in design['seeds']:
            name = f'd{depth}-s{seed}'; history = {}; begin = time.monotonic()
            params = {**design['parameters'], 'max_depth': depth, 'seed': seed}
            model = xgb.train(params, dfit, num_boost_round=design['max_rounds'],
                evals=[(dfit, 'fit'), (dtune, 'tune')], evals_result=history,
                early_stopping_rounds=design['early_stopping_rounds'], verbose_eval=False)
            config = json.loads(model.save_config())
            assert config['learner']['generic_param']['device'].startswith('cuda')
            best = model.best_iteration; fitted = model.num_boosted_rounds()
            assert best == int(np.argmin(history['tune']['rmse']))
            model = model[:best+1]; model.set_param({'device': 'cpu', 'nthread': 1})
            path = out/f'{name}.json'; model.save_model(path)
            raw = model.predict(dall)
            independent = json_predict(read(path), x)
            assert np.max(np.abs(independent-raw)) < 1e-5
            predictions = dense(raw, rows, actions, data)
            np.testing.assert_array_equal(route(predictions, data['mask'], data['proposal_index']),
                route(dense(independent, rows, actions, data), data['mask'], data['proposal_index']))
            saved_predictions[name] = predictions; members.append(predictions)
            records.append({'name': name, 'depth': depth, 'seed': seed, 'fit_rounds': fitted, 'selected_rounds': best+1,
                'seconds': time.monotonic()-begin, 'model_sha256': digest(path),
                'cpu_json_max_abs_error': float(np.max(np.abs(independent-raw))),
                'metrics': {g: metrics(predictions, data, ids) for g, ids in groups.items()}})
            save(out/f'{name}-history.json', history)
            print(json.dumps({'member_complete': name, 'fit_rounds': fitted, 'selected_rounds': best+1}), flush=True)
        saved_predictions[f'd{depth}-mean'] = np.mean(members, axis=0)
    np.savez_compressed(out/'predictions.npz', **saved_predictions)
    result = {'complete': True, 'training_location': 'HF Jobs', 'training_device': 'cuda',
        'gpu': torch.cuda.get_device_name(), 'xgboost': xgb.__version__, 'seconds': time.monotonic()-start,
        'members': records, 'ensembles': {f'd{d}': {g: metrics(saved_predictions[f'd{d}-mean'], data, ids)
            for g, ids in groups.items()} for d in design['depths']},
        'design_sha256': digest(bundle/'design.json'), 'data_report_sha256': digest(bundle/'data/report.json'),
        'new_simulations': 0, 'qualified': False, 'reserved_final_seeds_used': False,
        'scope': 'Learner-class diagnostic on existing nomination targets; previously used legacy validation, not untouched strength evidence. Original models unchanged.'}
    save(out/'training.json', result)
    save(out/'manifest.json', {p.name: digest(p) for p in sorted(out.iterdir()) if p.is_file()})
    import sys; sys.path.insert(0, str(bundle/'transport'))
    from checkpoint_bucket_archives_v3 import upload_directory
    from huggingface_hub import HfApi
    receipt = upload_directory(out, bundle/'upload-ledgers', HfApi())
    print(json.dumps({'target_learner_complete': True, 'bucket_evidence': receipt}), flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(__doc__); p.add_argument('--bundle', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True); a = p.parse_args()
    train(a.bundle.resolve(), a.output.resolve())
