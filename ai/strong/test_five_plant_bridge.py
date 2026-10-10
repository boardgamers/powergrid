"""Exercise mixed feature sizes through real complete games, without training."""
import sys
from pathlib import Path
import unittest
import torch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pool import EnginePool
from model import tensors
from model_v4 import MultiplayerPolicy
from model_v4_1 import transfer_from_v4


class MixedRevisionTests(unittest.TestCase):
    def test_complete_paired_games_with_new_learner_and_old_opponents(self):
        torch.set_num_threads(1)
        old = MultiplayerPolicy(ordered_players=True).eval()
        new = transfer_from_v4(dict(architecture="multiplayer_ordered", feature_revision="4.0-multiplayer",
                                   state_dim=1149, action_dim=98, state_dict=old.state_dict())).eval()
        pool = EnginePool(4, seed="five-plant-integration-v1", script="ai/strong/bridge.cjs")
        complete = 0
        try:
            for n in range(2, 7):
                rows = pool.call(dict(op="reset", n=4*n, playerCount=n, mode="snapshot0",
                                      arenaSeed=f"five-plant-integration-{n}",
                                      featureRevisions={"learner": "4.1-five-plants", "snapshot0": "4.0-multiplayer"}))["observations"]
                ends, seen = [], set()
                while any(rows):
                    actions = [None] * len(rows)
                    for role, actor, dims, revision in [
                        ("learner", new, (1215, 100), "4.1-five-plants"),
                        ("snapshot0", old, (1149, 98), "4.0-multiplayer")]:
                        indices = [i for i, r in enumerate(rows) if r and r["roles"][r["seat"]] == role]
                        if not indices:
                            continue
                        batch = [rows[i] for i in indices]
                        for r in batch:
                            seen.add(role)
                            self.assertEqual(r["featureRevision"], revision)
                            self.assertEqual((len(r["state"]), len(r["actions"][0])), dims)
                        with torch.inference_mode():
                            logits, _ = actor(*tensors(batch, "cpu"))
                        for i, choice in zip(indices, logits.argmax(-1).tolist()):
                            actions[i] = choice
                    reply = pool.call(dict(op="step", actions=actions))
                    ends.extend(reply["ended"])
                    rows = reply["observations"]
                self.assertEqual(len(ends), 4*n)
                self.assertEqual(seen, {"learner", "snapshot0"})
                self.assertFalse(any(e["truncated"] for e in ends))
                self.assertEqual(len({(e["roles"].index("learner"), e["variant"], e["sealed"]) for e in ends}), 4*n)
                complete += len(ends)
        finally:
            pool.close()
        self.assertEqual(complete, 80)
        print({"mixed_revision_games": complete, "truncated": 0})


if __name__ == "__main__":
    unittest.main()
