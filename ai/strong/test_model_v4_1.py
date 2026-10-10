"""Inference-only model-contract tests; optimization belongs on HF Jobs."""
import unittest
import torch
from model import policy_from_checkpoint
from model_v4 import MultiplayerPolicy
from model_v4_1 import transfer_from_v4, FEATURE_REVISION, ARCHITECTURE, FivePlantPolicy


class FivePlantTests(unittest.TestCase):
    def setUp(self):
        torch.set_num_threads(1)
        self.parent = MultiplayerPolicy(ordered_players=True).eval()
        self.checkpoint = dict(architecture="multiplayer_ordered", feature_revision="4.0-multiplayer",
                               state_dim=1149, action_dim=98, state_dict=self.parent.state_dict())

    def test_transfer_preserves_logits_values_masks_and_old_parameter_shapes(self):
        new = transfer_from_v4(self.checkpoint).eval()
        state = torch.rand(5, 1215)
        state[:, :6] = torch.tensor([[int(i < n) for i in range(6)] for n in range(2, 7)])
        actions = torch.rand(5, 17, 100)
        mask = torch.ones(5, 17, dtype=torch.bool)
        mask[0, 3:] = False
        with torch.inference_mode():
            expected = self.parent(state[:, :1149].contiguous(), actions[:, :, :98].contiguous(), mask)
            actual = new(state, actions, mask)
        for a, b in zip(expected, actual):
            self.assertTrue(torch.equal(a, b))
        self.assertEqual(actual[1][0, 2:].sum().item(), 0)
        self.assertLess(actual[0][0].argmax().item(), 3)
        for name, value in self.parent.state_dict().items():
            self.assertTrue(torch.equal(value, new.state_dict()[name]))
        restored = policy_from_checkpoint(dict(architecture=ARCHITECTURE, feature_revision=FEATURE_REVISION,
                                               state_dim=1215, action_dim=100, state_dict=new.state_dict()))
        self.assertIsInstance(restored, FivePlantPolicy)

    def test_rejects_silent_or_unordered_transfer(self):
        for mutation in [dict(feature_revision="3.0"), dict(architecture="multiplayer"), dict(state_dim=1215)]:
            with self.assertRaises(ValueError):
                transfer_from_v4({**self.checkpoint, **mutation})
        with self.assertRaises(ValueError):
            policy_from_checkpoint({**self.checkpoint, "architecture": ARCHITECTURE})

    def test_new_plant_input_reaches_each_relative_player_before_pooling(self):
        net = transfer_from_v4(self.checkpoint).eval()
        # Controlled nonzero weights establish signal routing, not a learned policy.
        with torch.no_grad():
            net.extra_player.weight[:, 0] = torch.linspace(-1, 1, 128)
        state = torch.zeros(2, 1215)
        state[:, :6] = 1
        state[1, 1149 + 5 * 11] = 1
        captured = []
        hook = net.player[1].register_forward_pre_hook(lambda module, args: captured.append(args[0].clone()))
        with torch.inference_mode():
            net(state, torch.zeros(2, 1, 100), torch.ones(2, 1, dtype=torch.bool))
        hook.remove()
        self.assertTrue(torch.equal(captured[0][0, :5], captured[0][1, :5]))
        self.assertFalse(torch.equal(captured[0][0, 5], captured[0][1, 5]))


if __name__ == "__main__":
    unittest.main()
