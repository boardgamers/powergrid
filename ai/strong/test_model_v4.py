import json
from pathlib import Path
import subprocess
import unittest

import torch
from model import tensors
from model_v4 import MultiplayerPolicy


class MultiplayerTests(unittest.TestCase):
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
        net = MultiplayerPolicy().eval()
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
