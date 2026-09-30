"""Complete real engine episodes through the exact training subprocess protocol."""

import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pool import EnginePool
from multiplayer import ROLE_REVISIONS, rotate_outcome


class BridgeTests(unittest.TestCase):
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
