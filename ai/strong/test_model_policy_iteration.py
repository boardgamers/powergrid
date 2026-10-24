"""Inference-only tests for public inputs, fallback, and seed disagreement."""
import unittest
import torch
from model_policy_iteration import PolicyIterationPolicy, PublicStateHead, ensemble_advantages, policy_from_checkpoint
from model_strategic import route


class PolicyIteration(unittest.TestCase):
    def setUp(self):
        torch.set_num_threads(1)
        torch.manual_seed(204)

    def test_disagreement_is_relative_to_each_parent_score(self):
        scores = torch.tensor([[[5., 5.2, 5.1]], [[-3., -2.8, -3.1]],
                               [[1., 1.2, 1.1]], [[9., 9.2, 8.9]]], dtype=torch.float64)
        proposal = torch.tensor([0])
        mean = ensemble_advantages(scores, proposal, 0.)
        conservative = ensemble_advantages(scores, proposal, 1.)
        torch.testing.assert_close(mean, torch.tensor([[0., .2, 0.]], dtype=torch.float64))
        torch.testing.assert_close(conservative, torch.tensor([[0., .2, -.1]], dtype=torch.float64))
        shifted = scores + torch.tensor([12., -4., 30., 1.], dtype=torch.float64)[:, None, None]
        torch.testing.assert_close(ensemble_advantages(shifted, proposal, 1.), conservative)

    def test_disagreement_can_keep_fallback_without_changing_scope(self):
        parent = torch.tensor([[4., 3., 2., -1e9]]).repeat(3, 1)
        mask = torch.tensor([[True, True, True, False]]).repeat(3, 1)
        shortlist = torch.tensor([[False, True, False, True]]).repeat(3, 1)
        scores = torch.tensor([[[0., .2, 100., 1000.]], [[0., -.1, 100., 1000.]],
                               [[0., .2, 100., 1000.]], [[0., -.1, 100., 1000.]]]).expand(-1, 3, -1)
        for penalty, expected in [(0., [1, 0, 1]), (1., [0, 0, 0])]:
            q = ensemble_advantages(scores, torch.zeros(3, dtype=torch.int64), penalty)
            result = route(parent, q, mask, shortlist, torch.tensor([True, False, True]), .025)
            self.assertEqual(result.argmax(1).tolist(), expected)

    def test_zero_heads_preserve_parent_and_values_for_all_configurations(self):
        for head_type in ['frozen', 'public']:
            for heads, penalty in [(1, 0.), (4, 0.), (4, 1.)]:
                net = PolicyIterationPolicy(head_type, heads, disagreement_penalty=penalty).eval()
                self.assertFalse(any(p.requires_grad for p in net.parent.parameters()))
                self.assertTrue(all(p.requires_grad for p in net.heads.parameters()))
                state, actions = torch.randn(5, 1217), torch.randn(5, 7, 101)
                state[:, :6] = 1
                state[:, 1216] = 1
                actions[:, :, 100] = 1
                mask = torch.ones(5, 7, dtype=torch.bool)
                with torch.inference_mode():
                    expected = net.parent(state[:, :1216], actions[:, :, :100], mask)
                    actual = net(state, actions, mask)
                self.assertTrue(all(torch.equal(a, b) for a, b in zip(expected, actual)))
                cp = {'architecture': 'policy_iteration_head' if heads == 1 else 'policy_iteration_ensemble',
                      'feature_revision': '4.3-strategic-correction', 'state_dim': 1217, 'action_dim': 101,
                      'model_args': {'head_type': head_type, 'heads': heads, 'disagreement_penalty': penalty},
                      'state_dict': net.state_dict()}
                restored = policy_from_checkpoint(cp).eval()
                with torch.inference_mode():
                    self.assertTrue(all(torch.equal(a, b) for a, b in zip(actual, restored(state, actions, mask))))

    def test_raw_public_inputs_can_affect_head_even_when_frozen_context_cannot(self):
        net = PublicStateHead().eval()
        # Synthetic nonzero final layer exercises the path without training.
        with torch.no_grad():
            net.score[-1].weight.fill_(.1)
        state = torch.zeros(2, 1217)
        state[1, 264] = 1  # Ordered focal-player public data, outside old 66-feature suffix.
        actions = torch.zeros(2, 3, 101)
        with torch.inference_mode():
            result = net(torch.zeros(2, 384), torch.zeros(2, 3, 128), state, actions)
        self.assertFalse(torch.equal(result[0], result[1]))


if __name__ == '__main__':
    unittest.main()
