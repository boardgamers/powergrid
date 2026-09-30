"""Complete real engine episodes through the exact training subprocess protocol."""

import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pool import EnginePool
from multiplayer import ROLE_REVISIONS, rotate_outcome


class BridgeTests(unittest.TestCase):
    def test_stronger_mixture_retains_selfplay_and_all_opponent_families(self):
        # Fixed independent RNG seeds exercise every league family through reset.
        cases = [
            (8, "economic"),
            (2, "heuristic"),
            (7, "rush"),
            (1, "search_geo"),
            (10, "learner"),
            (3, "snapshot0"),
            (0, "snapshot1"),
            (9, "snapshot2"),
        ]
        for seed, expected in cases:
            pool = EnginePool(
                1, seed=f"league-mixture-{seed}", script="ai/strong/bridge.cjs"
            )
            try:
                for n in range(2, 7):
                    for mode in ["mixed_search_geo", "mixed_search"]:
                        row = pool.call(
                            {
                                "op": "reset",
                                "n": 1,
                                "mode": mode,
                                "playerCounts": [n],
                                "offset": 0,
                                "featureRevisions": ROLE_REVISIONS,
                            }
                        )["observations"][0]
                        opponent = (
                            "search"
                            if expected == "search_geo" and mode == "mixed_search"
                            else expected
                        )
                        self.assertEqual(
                            row["roles"], ["learner"] + [opponent] * (n - 1)
                        )
                        self.assertEqual(row["playerCount"], n)
            finally:
                pool.close()

    def test_mixed_training_schedule_covers_every_seat_and_rule(self):
        pool = EnginePool(3, seed="mixed-count-protocol", script="ai/strong/bridge.cjs")
        seen = {n: set() for n in range(2, 7)}
        try:
            for cycle in range(6):
                reply = pool.call(
                    {
                        "op": "reset",
                        "n": 20,
                        "mode": "economic",
                        "playerCounts": [2, 3, 4, 5, 6],
                        "featureRevisions": ROLE_REVISIONS,
                        "offset": cycle * 20,
                    }
                )
                current = reply["observations"]
                self.assertEqual(len(current), 20)
                for row in current:
                    n = row["playerCount"]
                    self.assertEqual(row["seat"], cycle % n)
                    seen[n].add((row["seat"], row["variant"], row["sealed"]))
                self.assertEqual(
                    [sum(r["playerCount"] == n for r in current) for n in range(2, 7)],
                    [4] * 5,
                )
            ends = []
            for _ in range(1800):
                reply = pool.call(
                    {
                        "op": "step",
                        "actions": [r["teacher"] if r else None for r in current],
                    }
                )
                ends.extend(reply["ended"])
                current = reply["observations"]
                if all(r is None for r in current):
                    break
            self.assertEqual(len(ends), 20)
            self.assertFalse(any(e["truncated"] for e in ends))
            for n, cells in seen.items():
                self.assertEqual(len(cells), 4 * n)
        finally:
            pool.close()

    def test_complete_paired_counts_and_rotate_terminal_targets(self):
        pool = EnginePool(3, seed="multiplayer-protocol", script="ai/strong/bridge.cjs")
        try:
            for n in range(2, 7):
                current = pool.call(
                    {
                        "op": "reset",
                        "n": 4 * n,
                        "mode": "selfplay",
                        "playerCount": n,
                        "featureRevisions": ROLE_REVISIONS,
                        "arenaSeed": f"protocol-{n}",
                        "offset": 4 * n,
                    }
                )["observations"]
                ends = []
                seats = set()
                for _ in range(1800):
                    for row in current:
                        if row:
                            self.assertEqual(row["playerCount"], n)
                            self.assertEqual(row["featureRevision"], "4.0-multiplayer")
                            seats.add(row["seat"])
                    reply = pool.call(
                        {
                            "op": "step",
                            "actions": [r["teacher"] if r else None for r in current],
                        }
                    )
                    ends.extend(reply["ended"])
                    current = reply["observations"]
                    if all(r is None for r in current):
                        break
                self.assertEqual(len(ends), 4 * n)
                self.assertEqual(seats, set(range(n)))
                self.assertEqual({e["episode"] for e in ends}, set(range(4 * n, 8 * n)))
                self.assertEqual({e["gameSeed"] for e in ends}, {f"protocol-{n}-1"})
                for e in ends:
                    self.assertFalse(e["truncated"])
                    self.assertEqual(len(e["roles"]), n)
                    for seat in range(n):
                        rotated = rotate_outcome(e["value"], seat)
                        self.assertEqual(rotated[0], e["value"][seat])
                        self.assertEqual(rotated[n:], [0.0] * (6 - n))
                        self.assertAlmostEqual(sum(rotated), 1)
        finally:
            pool.close()


if __name__ == "__main__":
    unittest.main()
