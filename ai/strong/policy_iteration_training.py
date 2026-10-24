"""Compact immutable training inputs and diagnostic metrics, without gradients."""
from collections import Counter, defaultdict
import numpy as np
from strategic_collection import read, digest
from policy_iteration_data import validate_manifest, PROTOCOL, SOURCE


def load_bundle(directory, design):
    report = read(directory/'data-check.json')
    assert report['complete'] and report['positions'] == 17280 and report['samples_per_root'] == 192
    assert report['split_counts'] == {'train': 12960, 'validation': 4320}
    assert report['label_protocol_sha256'] == design['label_protocol_sha256']
    assert report['label_source'] == design['label_source']
    assert digest(directory/'label-manifest.json') == report['label_manifest_sha256']
    validate_manifest(read(directory/'label-manifest.json'), read(PROTOCOL), read(SOURCE))
    assert report['feature_check_sha256'] == design['features']['files']['feature-check.json']
    for file, sha in report['artifacts'].items():
        assert digest(directory/file) == sha
    feature_report = read(directory/'feature-check.json')
    for file, sha in feature_report['artifacts'].items():
        assert digest(directory/file) == sha == design['features']['files'][file]
    with np.load(directory/'features.npz', allow_pickle=False) as f:
        data = dict(f)
    with np.load(directory/'targets.npz', allow_pickle=False) as f:
        assert not set(f.files) & set(data)
        data.update(dict(f))
    metadata = read(directory/'metadata.json')
    assert len(metadata) == len({r['rootId'] for r in metadata}) == 17280
    assert len({r['public_root_sha256'] for r in metadata}) == 17280
    assert len({r['policy_input_sha256'] for r in metadata}) == 17280
    assert Counter(r['split'] for r in metadata) == report['split_counts']
    assert data['state'].shape == (17280, 1217) and data['actions'].shape == (17280, 7, 101)
    assert data['state'].dtype == data['actions'].dtype == np.float32
    assert data['mask'].shape == (17280, 7) and data['mask'].dtype == bool
    assert data['proposal_index'].dtype == np.int64 and data['proposal_index'].shape == (17280,)
    assert np.isfinite(data['state']).all() and np.isfinite(data['actions']).all()
    assert (data['state'][:, -1] == 1).all()
    for i, meta in enumerate(metadata):
        assert meta['split'] == ('validation' if meta['deal'] in [0, 4, 8, 12] else 'train')
        n = len(meta['options'])
        assert 2 <= n <= 7 and meta['options'] == sorted(set(meta['options']))
        assert data['mask'][i].tolist() == [True]*n + [False]*(7-n)
        assert data['legal_indices'][i].tolist() == meta['options'] + [-1]*(7-n)
        assert data['proposal_index'][i] == meta['options'].index(meta['model_proposal'])
    for key in ['target', 'precision', 'variance_of_mean', 'target_a', 'target_b']:
        assert data[key].shape == (17280, 7) and data[key].dtype == np.float64
        assert np.isfinite(data[key]).all() and (data[key][~data['mask']] == 0).all()
    parent = np.arange(17280), data['proposal_index']
    for key in ['target', 'variance_of_mean', 'target_a', 'target_b']:
        assert (data[key][parent] == 0).all()
    assert (np.abs(data['target']) <= 1).all() and (data['variance_of_mean'] >= 0).all()
    np.testing.assert_allclose(data['target'], (data['target_a']+data['target_b'])/2, atol=1e-15, rtol=1e-15)
    expected = np.clip(.05**2/(.05**2 + data['variance_of_mean']), .25, 1.)
    np.testing.assert_array_equal(data['precision'][data['mask']], expected[data['mask']])
    return data, metadata, report


def metrics(scores, data, metadata, margin):
    """Report the fixed rule, including overconfidence and adverse simulated outcomes."""
    scores = np.asarray(scores, np.float64)
    proposal = data['proposal_index']
    ids = np.arange(len(proposal))
    assert scores.shape == data['mask'].shape and np.isfinite(scores).all()
    delta = scores - scores[ids, proposal, None]
    allowed = np.where(data['mask'], delta, -1e9)
    chosen = np.where(allowed.max(1) > margin, allowed.argmax(1), proposal)
    assert data['mask'][ids, chosen].all()
    achieved = data['target'][ids, chosen]
    predicted = delta[ids, chosen]
    best = np.where(data['mask'], data['target'], -1e9).max(1)
    changed = chosen != proposal
    nonparent = data['mask'] & (np.arange(scores.shape[1])[None] != proposal[:, None])
    assert nonparent.any(1).all()
    root_mse = (((delta-data['target'])**2)*nonparent).sum(1)/nonparent.sum(1)
    groups = defaultdict(list)
    for i, row in enumerate(metadata):
        for name in [f"players/{row['players']}", f"decision/{row['decision']}",
                     f"rules/{row['variant']}/{'sealed' if row['sealed'] else 'open'}",
                     f"intersection/{row['players']}/{row['decision']}/{row['variant']}/{row['sealed']}"]:
            groups[name].append(i)
    def summary(ix):
        ix = np.asarray(ix)
        switched = ix[changed[ix]]
        return {'roots': len(ix), 'mean_simulated_regret': float((best[ix]-achieved[ix]).mean()),
                'mean_advantage_over_parent': float(achieved[ix].mean()),
                'mean_predicted_advantage': float(predicted[ix].mean()),
                'mean_prediction_bias': float((predicted[ix]-achieved[ix]).mean()),
                'root_normalized_rmse': float(np.sqrt(root_mse[ix].mean())),
                'changes': len(switched), 'changed_fraction': float(changed[ix].mean()),
                'negative_changes': int((achieved[switched] < -1e-12).sum()),
                'advantage_a': float(data['target_a'][ix, chosen[ix]].mean()),
                'advantage_b': float(data['target_b'][ix, chosen[ix]].mean())}
    return {**summary(ids), 'groups': {k: summary(ix) for k, ix in sorted(groups.items())},
            'scope': 'Conditional continuation targets; seed disagreement is not a confidence interval, and these are not full-game strength results.'}


def assemble(checkpoints, design, head_type, penalty, design_sha256):
    """Every prespecified seed participates; shared parent tensors must match exactly."""
    import torch
    from model_policy_iteration import PolicyIterationPolicy
    assert len(checkpoints) == design['heads_per_ensemble'] == 4
    assert [cp['seed'] for cp in checkpoints] == design['seeds']
    assert penalty in design['ensemble_disagreement_penalties']
    original = {k: v for k, v in checkpoints[0]['state_dict'].items() if k.startswith('parent.')}
    args = {'head_type': head_type, 'heads': 4, 'margin': design['margin'],
            'parent_margin': design['parent_margin'], 'disagreement_penalty': penalty}
    combined = dict(original)
    data_sha = checkpoints[0]['data_check_sha256']
    for index, cp in enumerate(checkpoints):
        assert cp['architecture'] == 'policy_iteration_head' and not cp.get('inference_only', False)
        assert cp['design_sha256'] == design_sha256 and cp['data_check_sha256'] == data_sha
        assert cp['parent'] == design['parent'] and cp['parent_frozen']
        assert cp['feature_revision'] == design['feature_revision']
        assert cp['state_dim'] == design['state_dim'] and cp['action_dim'] == design['action_dim']
        assert cp['model_args'] == {**args, 'heads': 1, 'disagreement_penalty': 0.}
        parents = {k: v for k, v in cp['state_dict'].items() if k.startswith('parent.')}
        assert set(parents) == set(original) and all(torch.equal(parents[k], v) for k, v in original.items())
        for k, v in cp['state_dict'].items():
            assert v.dtype == torch.float32
            if not k.startswith('parent.'):
                assert k.startswith('heads.0.')
                combined[k.replace('heads.0.', f'heads.{index}.', 1)] = v
    # Strict loading rejects a missing/extra tensor before any export.
    PolicyIterationPolicy(**args).load_state_dict(combined)
    return {'architecture': 'policy_iteration_ensemble', 'state_dict': combined, 'model_args': args,
            'feature_revision': design['feature_revision'], 'state_dim': design['state_dim'], 'action_dim': design['action_dim'],
            'seeds': design['seeds'], 'epochs': [cp['epoch'] for cp in checkpoints],
            'parent': design['parent'], 'parent_frozen': True, 'design_sha256': design_sha256,
            'data_check_sha256': data_sha, 'qualification_eligible': False}
