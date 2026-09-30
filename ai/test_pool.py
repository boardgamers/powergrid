"""Exercise uneven sharding and terminal episode ownership without training."""

import unittest
from pool import EnginePool


class PoolTest(unittest.TestCase):
    def test_uneven_shards_complete_legal_games(self):
        pool = EnginePool(4, seed="pool-regression")
        try:
            reply = pool.call({"op": "reset", "n": 25})
            finished = set()
            for _ in range(1000):
                self.assertEqual(len(reply["observations"]), 25)
                reply = pool.call(
                    {
                        "op": "step",
                        "actions": [o["heuristic"] for o in reply["observations"]],
                    }
                )
                for end in reply["ended"]:
                    self.assertFalse(end["truncated"])
                    self.assertTrue(0 <= end["env"] < 25)
                    self.assertAlmostEqual(sum(end["value"]), 1)
                    finished.add(end["env"])
            self.assertEqual(finished, set(range(25)))
        finally:
            pool.close()


if __name__ == "__main__":
    unittest.main()
