"""Inference/metric assembly tests only; no optimizer or backward pass."""
from copy import deepcopy
import importlib.util
import unittest
import numpy as np
import torch
from model_policy_iteration import PolicyIterationPolicy, policy_from_checkpoint
from policy_iteration_training import metrics, assemble
from strategic_collection import ROOT, read, digest


class TrainingContracts(unittest.TestCase):
    def test_export_calibration_uses_same_decisions_as_actual_policy(self):
        torch.set_num_threads(1)
        spec = importlib.util.spec_from_file_location('training', ROOT/'ai/strong/train-policy-iteration.py')
        training = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(training)
        with np.load(ROOT/'ai/runs/policy-iteration-features-v2/features.npz', allow_pickle=False) as file:
            data = {k: v[:128] for k, v in dict(file).items()}
        for head_type in ['frozen', 'public']:
            for penalty in [0, 1]:
                cp = torch.load(ROOT/f'ai/runs/policy-iteration-model-preflight-v2/{head_type}-{penalty}/inference64.pt', map_location='cpu', weights_only=True)
                native = policy_from_checkpoint(cp).eval()
                scores = training.raw_scores(native.policy, data, 'cpu', batch_size=17)
                allowed = np.where(data['mask'], scores, -1e9)
                chosen = np.where(allowed.max(1) > .025, allowed.argmax(1), data['proposal_index'])
                with torch.inference_mode():
                    actual = native(*(torch.from_numpy(data[k]) for k in ['state', 'actions', 'mask']))[0].argmax(1).numpy()
                np.testing.assert_array_equal(chosen, actual)

    def test_metrics_keep_adverse_changes_and_ignore_padding(self):
        data = {'proposal_index': np.zeros(3, np.int64),
                'mask': np.asarray([[1, 1, 0]]*3, bool),
                'target': np.asarray([[0, -.1, 0], [0, .1, 0], [0, .2, 0]]),
                'target_a': np.asarray([[0, -.15, 0], [0, .15, 0], [0, .25, 0]]),
                'target_b': np.asarray([[0, -.05, 0], [0, .05, 0], [0, .15, 0]])}
        scores = np.asarray([[0, .2, 1000], [0, .025, 1000], [0, .2, 1000]])
        metadata = [{'players': n, 'decision': 'bid', 'variant': 'original', 'sealed': True} for n in [2, 4, 6]]
        result = metrics(scores, data, metadata, .025)
        self.assertEqual(result['changes'], 2)
        self.assertEqual(result['negative_changes'], 1)
        self.assertAlmostEqual(result['mean_advantage_over_parent'], .1/3)
        self.assertAlmostEqual(result['mean_prediction_bias'], .1)
        self.assertAlmostEqual(result['mean_simulated_regret'], .2/3)
        self.assertAlmostEqual(result['advantage_a'], .1/3)
        self.assertAlmostEqual(result['advantage_b'], .1/3)
        self.assertEqual(result['groups']['players/4']['changes'], 0)

    def test_assemble_all_prespecified_heads_and_reject_inconsistent_members(self):
        torch.set_num_threads(1)
        design_path = ROOT/'ai/strong/policy-iteration-training-design-v2.json'
        design, sha = read(design_path), digest(design_path)
        torch.manual_seed(304)
        original = PolicyIterationPolicy('public', 1)
        members = []
        for i, seed in enumerate(design['seeds']):
            net = deepcopy(original)
            with torch.no_grad():
                net.heads[0].score[-1].weight.fill_(.1*(i+1))
            members.append({'architecture': 'policy_iteration_head', 'seed': seed, 'epoch': 5*i,
                'model_args': {'head_type': 'public', 'heads': 1, 'margin': .025, 'parent_margin': .025, 'disagreement_penalty': 0.},
                'feature_revision': design['feature_revision'], 'state_dim': 1217, 'action_dim': 101,
                'design_sha256': sha, 'data_check_sha256': 'synthetic-plumbing-only',
                'parent': design['parent'], 'parent_frozen': True, 'state_dict': net.state_dict()})
        combined = assemble(members, design, 'public', 1., sha)
        restored = policy_from_checkpoint(combined)
        for i, cp in enumerate(members):
            for k, v in restored.heads[i].state_dict().items():
                self.assertTrue(torch.equal(v, cp['state_dict']['heads.0.'+k]))
        self.assertEqual(combined['epochs'], [0, 5, 10, 15])
        with self.assertRaises(AssertionError): assemble(members[:3], design, 'public', 1., sha)
        bad = deepcopy(members)
        bad[1]['seed'] = bad[0]['seed']
        with self.assertRaises(AssertionError): assemble(bad, design, 'public', 1., sha)
        bad = deepcopy(members)
        key = next(k for k in bad[1]['state_dict'] if k.startswith('parent.'))
        bad[1]['state_dict'][key].add_(.1)
        with self.assertRaises(AssertionError): assemble(bad, design, 'public', 1., sha)
        bad = deepcopy(members)
        bad[1]['data_check_sha256'] = 'different-labels'
        with self.assertRaises(AssertionError): assemble(bad, design, 'public', 1., sha)
        with self.assertRaises(AssertionError): assemble(members, design, 'frozen', 1., sha)


if __name__ == '__main__':
    unittest.main()
