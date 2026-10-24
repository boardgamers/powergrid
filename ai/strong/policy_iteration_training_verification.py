"""Independent checks of completed HF training outputs; never runs gradients."""
import importlib.util
import math
from pathlib import Path

import numpy as np
import torch
from huggingface_hub import hf_hub_download
from strategic_collection import ROOT, read, digest
from model_policy_iteration import policy_from_checkpoint
from policy_iteration_training import load_bundle, assemble, metrics
from policy_iteration_check import check


def same_tree(actual, expected):
    if isinstance(expected, torch.Tensor):
        assert isinstance(actual, torch.Tensor) and actual.dtype == expected.dtype
        assert actual.shape == expected.shape and torch.equal(actual, expected)
    elif isinstance(expected, dict):
        assert isinstance(actual, dict) and actual.keys() == expected.keys()
        for key in expected:
            same_tree(actual[key], expected[key])
    elif isinstance(expected, list):
        assert isinstance(actual, list) and len(actual) == len(expected)
        for a, e in zip(actual, expected):
            same_tree(a, e)
    elif isinstance(expected, float):
        assert math.isfinite(actual) and math.isfinite(expected)
        assert abs(actual-expected) <= 1e-10
    else:
        assert actual == expected


def expected_artifacts(design):
    files = {f'{seed}/{file}' for seed in design['seeds']
             for file in ['best.pt', 'latest.pt', 'optimizer.pt', 'metrics.json', 'training.json']}
    files |= {f'ensemble-{int(penalty)}/{file}' for penalty in design['ensemble_disagreement_penalties']
              for file in ['best.pt', 'calibration.json', 'parity-scope.json',
                           'derivative/inference64.pt', 'derivative/inference64.onnx', 'derivative/derivative.json']}
    return files


def verify_history(history, report, design, head_type, seed):
    updates_per_epoch = math.ceil(design['train_roots']/design['batch_size'])
    assert [r['epoch'] for r in history] == list(range(0, design['epochs']+1, design['evaluate_every']))
    assert all(r['updates'] == r['epoch']*updates_per_epoch for r in history)
    assert all(math.isfinite(r['seconds']) and r['seconds'] >= 0 for r in history)
    assert all(b['seconds'] >= a['seconds'] for a, b in zip(history, history[1:]))
    for row in history:
        for split in ['train', 'validation']:
            result = row[split]
            assert result['roots'] == design[split+'_roots']
            assert 0 <= result['negative_changes'] <= result['changes'] <= result['roots']
            assert 0 <= result['mean_simulated_regret'] <= 2
            assert math.isfinite(result['mean_simulated_regret'])
    best = min(history, key=lambda row: row['validation']['mean_simulated_regret'])
    assert report['best_epoch'] == best['epoch']
    assert report['head_type'] == head_type and report['seed'] == seed
    assert report['updates'] == design['epochs']*updates_per_epoch
    assert report['train_roots'] == design['train_roots'] and report['validation_roots'] == design['validation_roots']
    assert report['training_device'] == 'cuda' and report['training_location'] == 'HF Jobs'
    assert report['parent_tensors_identical'] and report['tf32'] is False and report['qualification_eligible'] is False
    assert report['head_parameters'] == design['representations'][head_type]['parameters_per_head']
    assert report['gpu'] and report['max_allocated_bytes'] > 0 and math.isfinite(report['seconds'])
    return best['epoch'], updates_per_epoch


def verify_member(cp, design, design_sha, data_sha, parent, head_type, seed, epoch, updates):
    expected = {'architecture': 'policy_iteration_head', 'seed': seed, 'epoch': epoch, 'updates': updates,
        'model_args': {'head_type': head_type, 'heads': 1, 'margin': design['margin'],
                       'parent_margin': design['parent_margin'], 'disagreement_penalty': 0.},
        'feature_revision': design['feature_revision'], 'state_dim': design['state_dim'], 'action_dim': design['action_dim'],
        'parent': design['parent'], 'parent_frozen': True, 'design_sha256': design_sha,
        'data_check_sha256': data_sha, 'training_device': 'cuda', 'qualification_eligible': False}
    assert not cp.get('inference_only', False) and not cp.get('synthetic_untrained', False)
    assert set(cp) == set(expected) | {'state_dict'}
    same_tree({k: cp[k] for k in expected}, expected)
    tensors = cp['state_dict']
    assert all(v.dtype == torch.float32 and torch.isfinite(v).all() for v in tensors.values())
    same_tree({k.removeprefix('parent.'): v for k, v in tensors.items() if k.startswith('parent.')}, parent['state_dict'])
    policy_from_checkpoint(cp).eval()  # Strict state-dict loading.


def verify(out, head_type, source, data_pin, data_dir):
    torch.set_num_threads(1)
    design_path = ROOT/'ai/strong/policy-iteration-training-design-v2.json'
    design, design_sha = read(design_path), digest(design_path)
    data, metadata, data_report = load_bundle(data_dir, design)
    data_sha = digest(data_dir/'data-check.json')
    assert data_sha == source['data_check_sha256'] == data_pin['files']['data-check.json']
    assert source['design_sha256'] == design_sha
    status = read(out/'training-check.json')
    assert status['status'] == 'complete' and status['head_type'] == head_type
    assert status['source_revision'] == source['revision'] and status['source_sha256'] == source['sha256']
    assert status['design_sha256'] == design_sha and status['data_check_sha256'] == data_sha
    assert status['training_location'] == 'HF Jobs' and status['qualification_eligible'] is False
    assert set(status['artifacts']) == expected_artifacts(design)
    for file, sha in status['artifacts'].items():
        assert digest(out/file) == sha
    assert set(status['runs']) == set(map(str, design['seeds']))
    assert set(status['ensembles']) == {'ensemble-0', 'ensemble-1'}
    parent_pin = design['parent']
    parent_path = hf_hub_download(parent_pin['repo'], parent_pin['path'], revision=parent_pin['revision'])
    assert digest(parent_path) == parent_pin['sha256']
    parent = torch.load(parent_path, map_location='cpu', weights_only=True)
    members, seed_reports = [], {}
    for seed in design['seeds']:
        directory = out/str(seed)
        history, report = read(directory/'metrics.json'), read(directory/'training.json')
        same_tree(report, status['runs'][str(seed)])
        epoch, updates_per_epoch = verify_history(history, report, design, head_type, seed)
        for file, expected_epoch in [('best.pt', epoch), ('latest.pt', design['epochs'])]:
            cp = torch.load(directory/file, map_location='cpu', weights_only=True)
            verify_member(cp, design, design_sha, data_sha, parent, head_type, seed,
                          expected_epoch, expected_epoch*updates_per_epoch)
            if file == 'best.pt':
                members.append(cp)
        optimizer = torch.load(directory/'optimizer.pt', map_location='cpu', weights_only=True)
        assert optimizer['state'] and all(int(v['step']) == report['updates'] for v in optimizer['state'].values())
        seed_reports[str(seed)] = {'best_epoch': epoch, 'updates': report['updates'],
                                  'checkpoint_sha256': digest(directory/'best.pt')}
    spec = importlib.util.spec_from_file_location('frozen_training', ROOT/'ai/strong/train-policy-iteration.py')
    training = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(training)
    ensembles = {}
    for penalty in design['ensemble_disagreement_penalties']:
        key = 'ensemble-'+str(int(penalty))
        directory = out/key
        assembled = assemble(members, design, head_type, penalty, design_sha)
        assembled['members'] = [{'seed': seed, 'checkpoint_sha256': digest(out/str(seed)/'best.pt')} for seed in design['seeds']]
        cp = torch.load(directory/'best.pt', map_location='cpu', weights_only=True)
        same_tree(cp, assembled)
        derivative = torch.load(directory/'derivative/inference64.pt', map_location='cpu', weights_only=True)
        for field in cp:
            same_tree(derivative[field], cp[field])
        assert derivative['inference_only'] and derivative['inference_precision'] == 'float64'
        assert derivative['inference_transform'] == 'float64-exp-div-silu-v1'
        numerical = derivative['numerical_derivative']
        assert numerical['source_checkpoint_sha256'] == digest(directory/'best.pt')
        assert numerical['trained'] is False and numerical['stored_weights_unchanged']
        descriptor = read(directory/'derivative/derivative.json')
        for field, value in numerical.items():
            assert descriptor[field] == value
        for file, sha in descriptor['files'].items():
            assert digest(directory/'derivative'/file) == sha
        parity = check(directory/'derivative/inference64.pt', directory/'derivative/inference64.onnx', data_dir)
        stored = read(directory/'parity-scope.json')
        # Numerical maxima may differ across CPU hardware; exact choices/counts must not.
        for field in ['max_logit_error', 'max_value_error']:
            assert math.isfinite(stored[field]) and stored[field] < 1e-8
        same_tree({k: v for k, v in parity.items() if not k.startswith('max_')},
                  {k: v for k, v in stored.items() if not k.startswith('max_')})
        native = policy_from_checkpoint(derivative).eval()
        scores = training.raw_scores(native.policy, data, 'cpu')
        calibration = {}
        for split in ['train', 'validation']:
            ids = np.asarray([i for i, row in enumerate(metadata) if row['split'] == split])
            calibration[split] = metrics(scores[ids], {k: v[ids] for k, v in data.items()},
                                         [metadata[i] for i in ids], design['margin'])
        same_tree(calibration, read(directory/'calibration.json'))
        saved = status['ensembles'][key]
        assert saved['penalty'] == penalty and saved['member_seeds'] == design['seeds']
        assert saved['qualification_eligible'] is False
        same_tree(saved['calibration'], calibration)
        same_tree(saved['parity'], stored)
        ensembles[key] = {'model_args': cp['model_args'], 'parity': parity, 'calibration': calibration,
                          'files': {file: digest(directory/'derivative'/file) for file in ['inference64.pt', 'inference64.onnx']}}
    return {'verified': True, 'head_type': head_type, 'seeds': design['seeds'], 'members': seed_reports,
            'design_sha256': design_sha, 'data_check_sha256': data_sha, 'ensembles': ensembles,
            'gradients_during_verification': False, 'qualification_eligible': False}
