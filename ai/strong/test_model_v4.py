import json
from pathlib import Path
import subprocess
import unittest

import torch
from model import tensors, policy_from_checkpoint
from model_v4 import MultiplayerPolicy
from multiplayer import balance_training_rows


class MultiplayerTests(unittest.TestCase):
    def test_opponent_holdings_remain_attached_to_relative_seats(self):
        state = torch.zeros(2, 1149)
        state[:, :3] = 1
        state[0, 338:412] = torch.linspace(0, 1, 74)
        state[0, 412:486] = torch.linspace(1, 0, 74)
        state[1] = state[0]
        state[1, 338:412] = state[0, 412:486]
        state[1, 412:486] = state[0, 338:412]
        actions = torch.zeros(2, 1, 98)
        mask = torch.ones(2, 1, dtype=torch.bool)
        for ordered in [False, True]:
            net = MultiplayerPolicy(ordered_players=ordered).eval()
            captured = []
            hook = net.context[0].register_forward_pre_hook(
                lambda module, args: captured.append(args[0].clone())
            )
            with torch.inference_mode():
                net(state, actions, mask)
            hook.remove()
            if ordered:
                self.assertFalse(torch.allclose(captured[0][0], captured[0][1]))
            else:
                torch.testing.assert_close(captured[0][0], captured[0][1])
            checkpoint = {
                "architecture": "multiplayer_ordered" if ordered else "multiplayer",
                "state_dict": net.state_dict(),
            }
            restored = policy_from_checkpoint(checkpoint)
            self.assertEqual(restored.ordered_players, ordered)

    def test_training_balance_does_not_favor_longer_counts(self):
        rows = [
            dict(playerCount=n, advantage=float(i % 2))
            for n in range(2, 7)
            for i in range(n * 4)
        ]
        balance_training_rows(rows)
        for n in range(2, 7):
            group = [r for r in rows if r["playerCount"] == n]
            self.assertAlmostEqual(
                sum(r["training_weight"] for r in group), len(rows) / 5
            )
            self.assertAlmostEqual(sum(r["normalized_advantage"] for r in group), 0)

    def test_all_counts_mask_values_and_legal_actions(self):
        root = Path(__file__).resolve().parents[2]
        rows = json.loads(
            subprocess.check_output(
                [
                    "node",
                    "-e",
                    "const c=require('./ai/core.cjs'),f=require('./ai/strong/features-v4.cjs');"
                    "console.log(JSON.stringify([2,3,4,5,6].map(n=>{const g=c.E.setup(n,{map:'Germany'},'mask-test');return f.encode(g,g.currentPlayers[0]);})));",
                ],
                cwd=root,
            )
        )
        for ordered in [False, True]:
            net = MultiplayerPolicy(ordered_players=ordered).eval()
            with torch.inference_mode():
                logits, values = net(*tensors(rows, "cpu"))
            self.assertEqual(tuple(values.shape), (5, 6))
            for row, n in enumerate(range(2, 7)):
                self.assertTrue(torch.isfinite(logits[row]).all())
                self.assertTrue(torch.isfinite(values[row]).all())
                self.assertEqual(values[row, n:].sum().item(), 0)
                self.assertAlmostEqual(values[row, :n].sum().item(), 1, places=6)
                self.assertLess(logits[row].argmax().item(), len(rows[row]["actions"]))
                expected = torch.tensor(rows[row]["prior"]).argmax().item()
                self.assertEqual(logits[row].argmax().item(), expected)


if __name__ == "__main__":
    unittest.main()
