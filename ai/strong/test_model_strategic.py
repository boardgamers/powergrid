"""Inference-only scope and candidate restrictions; gradients run only on HF."""
import unittest
import torch
from model_strategic import StrategicPolicy, route


class StrategicRouting(unittest.TestCase):
    def test_scope_margin_and_unsampled_actions(self):
        parent = torch.tensor([[4., 3., 2., -1e9]]).repeat(4, 1)
        mask = torch.tensor([[True, True, True, False]]).repeat(4, 1)
        shortlist = torch.tensor([[False, True, False, True]]).repeat(4, 1)
        q = torch.tensor([[0., .1, 100., 1000.], [0., .02, 100., 1000.],
                          [0., .04, 100., 1000.], [.3, .3, 100., 1000.]])
        result = route(parent, q, mask, shortlist, torch.tensor([False, True, True, True]), .025)
        self.assertEqual(result.argmax(1).tolist(), [0, 0, 1, 0])
        self.assertTrue(torch.equal(result[[0, 1, 3]], parent[[0, 1, 3]]))
        self.assertEqual(result[2, 2].item(), -1e9)
        self.assertTrue((result[:, 3] == -1e9).all())

    def test_zero_correction_preserves_both_outputs(self):
        torch.set_num_threads(1)
        torch.manual_seed(105)
        net = StrategicPolicy().eval()
        self.assertFalse(any(p.requires_grad for p in net.parent.parameters()))
        self.assertTrue(all(p.requires_grad for p in net.head.parameters()))
        state, actions = torch.randn(5, 1217), torch.randn(5, 7, 101)
        state[:, :6] = 1
        state[:, 1216] = 1
        actions[:, :, 100] = 1
        mask = torch.ones(5, 7, dtype=torch.bool)
        with torch.inference_mode():
            expected = net.parent(state[:, :1216], actions[:, :, :100], mask)
            actual = net(state, actions, mask)
        self.assertTrue(all(torch.equal(a, b) for a, b in zip(expected, actual)))


if __name__ == '__main__':
    unittest.main()
