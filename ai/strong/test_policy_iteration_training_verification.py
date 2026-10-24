"""Reject incorrect training provenance and epoch selection without gradients."""
from copy import deepcopy
import unittest

import torch
from huggingface_hub import hf_hub_download
from strategic_collection import ROOT, read, digest
from model_policy_iteration import PolicyIterationPolicy
from policy_iteration_training_verification import verify_history, verify_member, same_tree, expected_artifacts


class VerificationContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(1)
        cls.path = ROOT/'ai/strong/policy-iteration-training-design-v2.json'
        cls.design = read(cls.path)
        pin = cls.design['parent']
        path = hf_hub_download(pin['repo'], pin['path'], revision=pin['revision'])
        assert digest(path) == pin['sha256']
        cls.parent = torch.load(path, map_location='cpu', weights_only=True)
        # Entirely synthetic, untrained fixture. No optimizer or backward pass.
        net = PolicyIterationPolicy('public', 1)
        net.parent.load_state_dict(cls.parent['state_dict'])
        cls.cp = {'architecture': 'policy_iteration_head', 'seed': 12101, 'epoch': 5, 'updates': 255,
            'model_args': {'head_type': 'public', 'heads': 1, 'margin': .025, 'parent_margin': .025, 'disagreement_penalty': 0.},
            'feature_revision': '4.3-strategic-correction', 'state_dim': 1217, 'action_dim': 101,
            'parent': pin, 'parent_frozen': True, 'design_sha256': digest(cls.path),
            'data_check_sha256': 'fixture-only', 'training_device': 'cuda', 'qualification_eligible': False,
            'state_dict': net.state_dict()}

    def history(self):
        history = []
        for epoch in range(0, 121, 5):
            row = {'epoch': epoch, 'updates': epoch*51, 'seconds': epoch+1.}
            for split in ['train', 'validation']:
                row[split] = {'roots': self.design[split+'_roots'], 'negative_changes': 1, 'changes': 2,
                              'mean_simulated_regret': .2 if epoch == 0 else .1}
            history.append(row)
        report = {'head_type': 'public', 'seed': 12101, 'best_epoch': 5, 'updates': 6120,
                  'train_roots': 12960, 'validation_roots': 4320, 'training_device': 'cuda',
                  'training_location': 'HF Jobs', 'parent_tensors_identical': True, 'tf32': False,
                  'qualification_eligible': False, 'head_parameters': 482497,
                  'gpu': 'synthetic fixture only', 'max_allocated_bytes': 1, 'seconds': 125.}
        return history, report

    def member(self, cp):
        verify_member(cp, self.design, digest(self.path), 'fixture-only', self.parent, 'public', 12101, 5, 255)

    def test_best_epoch_is_earliest_validation_minimum_and_run_is_complete(self):
        history, report = self.history()
        self.assertEqual(verify_history(history, report, self.design, 'public', 12101), (5, 51))
        for field, value in [('best_epoch', 10), ('updates', 6069), ('train_roots', 4320),
                             ('training_device', 'cpu'), ('parent_tensors_identical', False)]:
            bad = {**report, field: value}
            with self.subTest(field=field), self.assertRaises(AssertionError):
                verify_history(history, bad, self.design, 'public', 12101)
        for bad in [history[:-1], history+[history[-1]]]:
            with self.assertRaises(AssertionError):
                verify_history(bad, report, self.design, 'public', 12101)
        bad = deepcopy(history)
        bad[1]['validation']['mean_simulated_regret'] = float('nan')
        with self.assertRaises(AssertionError):
            verify_history(bad, report, self.design, 'public', 12101)

    def test_member_rejects_wrong_seed_data_epoch_transform_and_parent(self):
        self.member(self.cp)
        for field, value in [('seed', 12102), ('epoch', 10), ('updates', 6120), ('data_check_sha256', 'different'),
                             ('inference_only', True), ('synthetic_untrained', True), ('state_dim', 1216)]:
            with self.subTest(field=field), self.assertRaises(AssertionError):
                self.member({**self.cp, field: value})
        parent_key = next(k for k in self.cp['state_dict'] if k.startswith('parent.'))
        head_key = next(k for k in self.cp['state_dict'] if k.startswith('heads.'))
        for key, value in [(parent_key, self.cp['state_dict'][parent_key]+.1),
                           (head_key, torch.full_like(self.cp['state_dict'][head_key], float('nan'))),
                           (head_key, self.cp['state_dict'][head_key].double())]:
            bad = {**self.cp, 'state_dict': {**self.cp['state_dict'], key: value}}
            with self.subTest(tensor=key), self.assertRaises(AssertionError):
                self.member(bad)

    def test_ensemble_comparison_requires_every_tensor_and_metadata(self):
        same_tree(self.cp, self.cp)
        bad = {**self.cp, 'state_dict': dict(self.cp['state_dict'])}
        bad['state_dict'].pop(next(iter(bad['state_dict'])))
        with self.assertRaises(AssertionError):
            same_tree(bad, self.cp)
        with self.assertRaises(AssertionError):
            same_tree({**self.cp, 'seed': 12102}, self.cp)
        files = expected_artifacts(self.design)
        self.assertEqual(len(files), 32)
        self.assertIn('ensemble-1/derivative/inference64.onnx', files)
        self.assertIn('12104/latest.pt', files)


if __name__ == '__main__':
    unittest.main()
