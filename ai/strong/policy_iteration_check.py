"""Strict export, public-input cache, legal choice, and frozen-parent checks."""
from collections import Counter
import json
import numpy as np
import torch
from huggingface_hub import hf_hub_download
from strategic_collection import ROOT, read, digest
from strategic_correction_check import serving_fixtures
from model_policy_iteration import policy_from_checkpoint
from infer import Model, Node


def check(checkpoint, model, feature_cache):
    torch.set_num_threads(1)
    cp = torch.load(checkpoint, map_location='cpu', weights_only=True)
    assert cp['inference_precision'] == 'float64' and cp['inference_only']
    assert cp['feature_revision'] == '4.3-strategic-correction'
    native = policy_from_checkpoint(cp).eval()
    candidate = Model(model, threads=1)
    p = read(ROOT/'ai/strong/policy-iteration-labels-protocol-v2.json')
    pin = p['model']
    parent = Model(hf_hub_download(p['repo'], pin['path'], revision=pin['revision']), threads=1)
    assert parent.sha256 == pin['sha256']
    positions = eligible = changed = labels = label_changed = 0
    errors = [0., 0.]
    counts = Counter()

    def compare(batch, proposals=None):
        actual = candidate.session.run(None, batch)
        with torch.inference_mode():
            expected = [x.numpy() for x in native(*(torch.from_numpy(batch[k]) for k in ['state', 'actions', 'mask']))]
        original = parent.session.run(None, {'state': batch['state'][:, :1216],
            'actions': batch['actions'][:, :, :100], 'mask': batch['mask']})
        for i, (a, b) in enumerate(zip(actual, expected)):
            assert np.isfinite(a).all()
            np.testing.assert_allclose(a, b, atol=1e-8, rtol=1e-10)
            errors[i] = max(errors[i], float(np.abs(a-b).max()))
        selected = actual[0].argmax(1)
        np.testing.assert_array_equal(selected, expected[0].argmax(1))
        np.testing.assert_allclose(actual[1], original[1], atol=1e-10, rtol=1e-10)
        # No inference may move the parent fallback to a different menu action.
        proposal = original[0].argmax(1)
        if proposals is not None:
            np.testing.assert_array_equal(proposal, proposals)
        ids = np.arange(len(selected))
        assert batch['mask'][ids, selected].all()
        active = batch['state'][:, -1] == 1
        assert ((selected == proposal) | (active & (batch['actions'][ids, selected, -1] == 1))).all()
        np.testing.assert_allclose(actual[0][~active], original[0][~active], atol=1e-10, rtol=1e-10)
        active_players = batch['state'][:, :6] > .5
        assert (actual[1][~active_players] == 0).all()
        np.testing.assert_allclose(actual[1].sum(1), 1., atol=1e-10, rtol=1e-10)
        return selected, proposal, active

    fixtures = serving_fixtures()
    worker = Node('strong/worker.cjs')
    try:
        with fixtures.open() as source:
            for line in source:
                fixture = json.loads(line)
                row = worker.call({**fixture['request'], 'featureRevision': cp['feature_revision']})
                assert row['moves'] == fixture['legal']
                batch = {'state': np.asarray([row['state']], np.float32),
                         'actions': np.asarray([row['actions']], np.float32),
                         'mask': np.ones((1, len(row['actions'])), bool)}
                selected, proposal, active = compare(batch)
                n = len(fixture['request']['state']['players'])
                assert row['playerOrder'] == [(fixture['request']['player'] + i) % n for i in range(n)]
                positions += 1
                eligible += int(active.sum())
                changed += int((selected != proposal).sum())
                counts[n] += 1
    finally:
        worker.close()
    assert positions == 2553 and eligible == 1096
    feature_report = read(feature_cache/'feature-check.json')
    assert feature_report['complete'] and feature_report['positions'] == 17280
    for file, sha in feature_report['artifacts'].items():
        assert digest(feature_cache/file) == sha
    with np.load(feature_cache/'features.npz', allow_pickle=False) as f:
        data = dict(f)
    for start in range(0, 17280, 64):
        batch = {k: data[k][start:start+64] for k in ['state', 'actions', 'mask']}
        selected, proposal, active = compare(batch, data['proposal_index'][start:start+64])
        labels += len(selected)
        label_changed += int((selected != proposal).sum())
    return {'complete': True, 'positions': positions, 'by_player_count': dict(counts),
            'eligible': eligible, 'changed_eligible': changed, 'outside_scope_actions_preserved': positions-eligible,
            'parent_values_preserved': True, 'all_moves_legal': True, 'all_native_onnx_actions_equal': True,
            'cached_positions_checked': labels, 'cached_parent_proposals_equal': True, 'cached_changed': label_changed,
            'max_logit_error': errors[0], 'max_value_error': errors[1],
            'checkpoint_sha256': digest(checkpoint), 'model_sha256': candidate.sha256,
            'feature_check_sha256': digest(feature_cache/'feature-check.json'),
            'qualification_eligible': False, 'scope': 'Inference plumbing only; no model strength evidence.'}
