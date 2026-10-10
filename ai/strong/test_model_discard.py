"""Inference-only checks; gradient steps are restricted to HF Jobs."""
import unittest
import torch
from model_discard import DiscardPolicy, corrected_logits


class DiscardRouting(unittest.TestCase):
    def test_scope_threshold_and_mask(self):
        parent = torch.tensor([[4., 3., -1e9]]).repeat(4, 1)
        mask = torch.tensor([[True, True, False]]).repeat(4, 1)
        score = torch.tensor([[0., 100., 1000.], [0., .02, 1000.], [0., .04, 1000.], [.3, .3, 1000.]])
        result = corrected_logits(parent, score, mask, torch.tensor([False, True, True, True]), .025)
        self.assertEqual(result.argmax(1).tolist(), [0, 0, 1, 0])
        self.assertTrue(torch.equal(result[[0, 1, 3]], parent[[0, 1, 3]]))
        self.assertTrue((result[:, 2] == -1e9).all())

    def test_zero_head_exactly_retains_parent(self):
        torch.set_num_threads(1)
        net = DiscardPolicy().eval()
        self.assertFalse(any(p.requires_grad for p in net.parent.parameters()))
        self.assertTrue(all(p.requires_grad for p in net.head.parameters()))
        torch.manual_seed(17)
        state, actions = torch.randn(5, 1216), torch.randn(5, 4, 100)
        state[:, :6] = 1; state[:, 1215] = 1
        mask = torch.ones(5, 4, dtype=torch.bool)
        with torch.inference_mode():
            original = net.parent(state[:, :1149], actions[:, :, :98], mask)
            actual = net(state, actions, mask)
        self.assertTrue(all(torch.equal(a, b) for a, b in zip(actual, original)))


if __name__ == '__main__':
    unittest.main()
