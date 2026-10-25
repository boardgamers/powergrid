"""Independent saved-training/behaviour audit; never performs gradient updates."""
import importlib.util
import math
from pathlib import Path
import shutil

import numpy as np
import torch
from strategic_collection import ROOT, read, digest
from model_opponent_surrogate_v1 import OpponentSurrogate, from_checkpoint
from opponent_surrogate_training_v1 import load_bundle, metrics


def same(actual, expected):
    if isinstance(expected, torch.Tensor):
        assert isinstance(actual, torch.Tensor) and actual.dtype == expected.dtype
        assert actual.shape == expected.shape and torch.equal(actual, expected)
    elif isinstance(expected, dict):
        assert isinstance(actual, dict) and actual.keys() == expected.keys()
        for key in expected: same(actual[key], expected[key])
    elif isinstance(expected, list):
        assert isinstance(actual, list) and len(actual) == len(expected)
        for a, e in zip(actual, expected): same(a, e)
    elif isinstance(expected, float):
        assert type(actual) in (int, float) and math.isfinite(actual) and math.isfinite(expected)
        assert abs(actual - expected) <= 1e-10
    else:
        assert type(actual) is type(expected) and actual == expected


def validate_metrics(result, data):
    active = data['mask'].sum(1) > 1
    counts = np.bincount(data['group'][active], minlength=60)
    assert (counts > 0).all() and set(result['groups']) == set(map(str, range(60)))
    assert result['rows'] == len(active) and result['nonforced_rows'] == int(active.sum())
    assert result['forced_rows'] == int((~active).sum())
    groups = [result['groups'][str(g)] for g in range(60)]
    for g, row in enumerate(groups):
        assert row['rows'] == int(counts[g])
        assert math.isfinite(row['nll']) and row['nll'] >= 0
        assert 0 <= row['agreement'] <= row['top3'] <= 1
        assert math.isfinite(row['teacher_sample_regret']) and 0 <= row['teacher_sample_regret'] <= 1
    for field in ('nll', 'agreement'):
        same(result['macro_'+field], float(np.mean([g[field] for g in groups])))
        same(result[field], float(np.average([g[field] for g in groups], weights=counts)))


def verify_history(history, report, design, seed, data):
    nonforced = int((data['train']['mask'].sum(1) > 1).sum())
    per_epoch = math.ceil(nonforced / design['batch_size'])
    assert [row['epoch'] for row in history] == list(range(design['epochs'] + 1))
    assert all(type(row['updates']) is int and row['updates'] == row['epoch'] * per_epoch for row in history)
    assert all(math.isfinite(row['seconds']) and row['seconds'] >= 0 for row in history)
    assert all(b['seconds'] >= a['seconds'] for a, b in zip(history, history[1:]))
    for row in history:
        assert (row['training_loss'] is None) is (row['epoch'] == 0)
        if row['epoch']:
            assert math.isfinite(row['training_loss']) and row['training_loss'] >= 0
        validate_metrics(row['validation'], data['validation'])
        assert ('train' in row) is (row['epoch'] in (0, design['epochs']))
        if 'train' in row: validate_metrics(row['train'], data['train'])
    best = min(history, key=lambda row: row['validation']['macro_nll'])
    assert report['seed'] == seed and report['best_epoch'] == best['epoch']
    assert report['updates'] == design['epochs'] * per_epoch
    same(report['best_validation_macro_nll'], best['validation']['macro_nll'])
    assert report['train_rows'] == len(data['train']['target']) and report['nonforced_train_rows'] == nonforced
    assert report['validation_rows'] == len(data['validation']['target'])
    # Device is recorded in each checkpoint; training.json records GPU identity.
    assert report['training_location'] == 'HF Jobs'
    assert report['tf32'] is False and report['test_labels_used'] is False and report['qualification_eligible'] is False
    assert isinstance(report['gpu'], str) and report['gpu'] and isinstance(report['torch_version'], str)
    assert math.isfinite(report['seconds']) and report['seconds'] >= history[-1]['seconds']
    assert type(report['gpu_resident_inputs']) is bool and report['max_allocated_bytes'] > 0
    expected_bytes = sum(data[s][k].nbytes for s in data for k in ('state', 'actions', 'mask', 'target'))
    assert report['input_bytes'] == expected_bytes
    return best['epoch'], per_epoch


def verify_checkpoint(cp, design, source, pin, seed, epoch, updates):
    expected = {'architecture': 'opponent_surrogate_v1', 'model_args': design['model_args'],
                'feature_revision': design['feature_revision'], 'state_dim': 1217, 'action_dim': 101,
                'max_candidates': 6, 'seed': seed, 'epoch': epoch, 'updates': updates,
                'design_sha256': source['design_sha256'], 'data_check_sha256': pin['data_check_sha256'],
                'collection_index_sha256': pin['collection_index_sha256'],
                'training_location': 'HF Jobs', 'training_device': 'cuda', 'test_labels_used': False,
                'qualification_eligible': False,
                'purpose': 'Opponent behaviour inside simulated continuations; not a qualified focal-player policy.'}
    assert set(cp) == set(expected) | {'state_dict'}, 'Unexpected inference/calibration/fixture checkpoint'
    same({k: cp[k] for k in expected}, expected)
    assert all(v.dtype == torch.float32 and torch.isfinite(v).all() for v in cp['state_dict'].values())
    net = from_checkpoint(cp)
    assert sum(p.numel() for p in net.parameters()) == design['parameters']


def verify(out, source, pin, data_path, local_checks):
    torch.set_num_threads(1)
    design_path = ROOT/'ai/strong/opponent-surrogate-training-design-v1.json'
    design = read(design_path)
    assert digest(design_path) == source['design_sha256'] == pin['design_sha256']
    data, data_report = load_bundle(data_path, design)
    assert digest(data_path/'data-check.json') == source['data_check_sha256'] == pin['data_check_sha256']
    assert data_report['collection_index_sha256'] == pin['collection_index_sha256']
    manifest = read(out/'manifest.json')
    expected = {'job.json'} | {f'{seed}/{file}' for seed in design['seeds'] for file in (
        'best.pt', 'latest.pt', 'optimizer.pt', 'metrics.json', 'training.json',
        'derivative/inference64.pt', 'derivative/inference64.onnx', 'derivative/derivative.json', 'derivative/parity.json')}
    assert set(manifest) == expected
    assert {str(p.relative_to(out)) for p in out.rglob('*') if p.is_file()} == expected | {'manifest.json'}
    assert all(digest(out/name) == sha for name, sha in manifest.items())
    status = read(out/'job.json')
    assert status['stage'] == 'complete' and status['seeds'] == design['seeds']
    assert status['source_revision'] == source['revision'] and status['source_sha256'] == source['sha256']
    assert status['design_sha256'] == source['design_sha256'] and status['data_check_sha256'] == pin['data_check_sha256']
    assert status['training_location'] == 'HF Jobs' and status['test_labels_used'] is False and status['qualification_eligible'] is False
    assert set(status['runs']) == set(status['exports']) == set(map(str, design['seeds']))
    baseline = {s: metrics(2 * d['actions'][:, :, 74], d) for s, d in data.items()}
    spec = importlib.util.spec_from_file_location('surrogate_local_export_audit', Path(__file__).with_name('export-opponent-surrogate-v1.py'))
    exporter = importlib.util.module_from_spec(spec); spec.loader.exec_module(exporter)
    seeds = {}
    for seed in design['seeds']:
        directory = out/str(seed); history = read(directory/'metrics.json'); report = read(directory/'training.json')
        same(report, status['runs'][str(seed)])
        best_epoch, per_epoch = verify_history(history, report, design, seed, data)
        for split in data: same(history[0][split], baseline[split])
        for filename, epoch in [('best.pt', best_epoch), ('latest.pt', design['epochs'])]:
            cp = torch.load(directory/filename, map_location='cpu', weights_only=True)
            verify_checkpoint(cp, design, source, pin, seed, epoch, per_epoch * epoch)
        best = torch.load(directory/'best.pt', map_location='cpu', weights_only=True)
        latest = torch.load(directory/'latest.pt', map_location='cpu', weights_only=True)
        assert report['best_checkpoint_sha256'] == digest(directory/'best.pt')
        with torch.random.fork_rng(devices=[]):
            torch.manual_seed(seed); initial = OpponentSurrogate(**design['model_args']).state_dict()
        assert any(not torch.equal(initial[k], v) for k, v in latest['state_dict'].items()), 'Latest model has not changed from initialization'
        if best_epoch == 0: same(best['state_dict'], initial)
        optimizer = torch.load(directory/'optimizer.pt', map_location='cpu', weights_only=True)
        assert len(optimizer['param_groups']) == 1
        group = optimizer['param_groups'][0]; parameters = list(from_checkpoint(latest).parameters())
        assert group['params'] == list(range(len(parameters))) and set(optimizer['state']) == set(group['params'])
        same(group['lr'], design['learning_rate'] * .05); same(group['weight_decay'], design['weight_decay'])
        for key, parameter in enumerate(parameters):
            state = optimizer['state'][key]
            assert float(state['step']) == report['updates']
            for name in ('exp_avg', 'exp_avg_sq'):
                assert state[name].shape == parameter.shape and state[name].dtype == torch.float32 and torch.isfinite(state[name]).all()
            assert (state['exp_avg_sq'] >= 0).all()
        derivative_dir = directory/'derivative'; descriptor = read(derivative_dir/'derivative.json')
        derivative = torch.load(derivative_dir/'inference64.pt', map_location='cpu', weights_only=True)
        for key in best: same(derivative[key], best[key])
        assert derivative['inference_only'] is True and derivative['inference_precision'] == 'float64'
        assert derivative['inference_transform'] == 'float64-exp-div-silu-v1'
        numeric = derivative['numerical_derivative']
        assert numeric['source_checkpoint_sha256'] == digest(directory/'best.pt')
        assert numeric['trained'] is False and numeric['stored_weights_unchanged'] is True
        for key, value in numeric.items(): same(descriptor[key], value)
        assert set(descriptor['files']) == {'inference64.pt', 'inference64.onnx'}
        assert all(digest(derivative_dir/name) == sha for name, sha in descriptor['files'].items())
        remote = read(derivative_dir/'parity.json'); saved = status['exports'][str(seed)]
        assert saved['parity_sha256'] == digest(derivative_dir/'parity.json')
        same({k: saved[k] for k in ('complete', 'positions', 'exact_choices', 'max_absolute_logit_error')},
             {k: remote[k] for k in ('complete', 'positions', 'exact_choices', 'max_absolute_logit_error')})
        check_dir = local_checks/str(seed); check_dir.mkdir(parents=True, exist_ok=True)
        for filename in ('inference64.pt', 'inference64.onnx', 'derivative.json'):
            target = check_dir/filename
            if target.exists(): assert digest(target) == digest(derivative_dir/filename)
            else: shutil.copy2(derivative_dir/filename, target)
        local = exporter.verify(check_dir, data)
        # Max numerical residuals vary across CPUs; all exact choices, supplied
        # positions and independently recomputed behaviour metrics must match.
        same({k: v for k, v in local.items() if k != 'max_absolute_logit_error'},
             {k: v for k, v in remote.items() if k != 'max_absolute_logit_error'})
        assert local['positions'] == local['exact_choices'] == sum(len(d['target']) for d in data.values())
        behaviour = local['exported_behaviour_metrics']; validation = behaviour['validation']
        seeds[str(seed)] = {'best_epoch': best_epoch, 'updates': report['updates'],
            'best_checkpoint_sha256': digest(directory/'best.pt'), 'files': descriptor['files'],
            'local_parity_sha256': digest(check_dir/'parity.json'), 'behaviour': behaviour,
            'validation_macro_nll_change_from_prior': validation['macro_nll'] - baseline['validation']['macro_nll'],
            'validation_macro_agreement_change_from_prior': validation['macro_agreement'] - baseline['validation']['macro_agreement'],
            'validation_groups_with_worse_nll': [g for g, m in validation['groups'].items() if m['nll'] > baseline['validation']['groups'][g]['nll'] + 1e-10]}
        print({'seed': seed, 'verified': True, 'best_epoch': best_epoch, 'positions': local['positions']}, flush=True)
    assert all(digest(out/name) == sha for name, sha in manifest.items()), 'Remote artifacts changed during host audit'
    return {'verified': True, 'seeds': seeds, 'baseline': baseline,
            'design_sha256': digest(design_path), 'data_check_sha256': pin['data_check_sha256'],
            'collection_index_sha256': pin['collection_index_sha256'], 'gradients_during_verification': False,
            'test_labels_used': False, 'qualification_eligible': False, 'reserved_final_seeds_used': False,
            'scope': 'Complete four-seed training/export/validation audit. No test evaluation, serving-policy selection, downstream continuation proof or playing-strength qualification.'}
