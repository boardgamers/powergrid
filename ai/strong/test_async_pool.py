"""Check scheduling and complete-game equivalence without local optimization."""

from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pool import EnginePool
from async_pool import AsyncEnginePool
from multiplayer import ROLE_REVISIONS


class AsyncPoolTests(unittest.TestCase):
    def play(self, cls):
        pool = cls(20, seed="async-equivalence", script="ai/strong/bridge.cjs")
        try:
            reply = pool.call(
                {
                    "op": "reset",
                    "n": 20,
                    "playerCounts": [2, 3, 4, 5, 6],
                    "offset": 20,
                    "mode": "selfplay",
                    "featureRevisions": ROLE_REVISIONS,
                }
            )
            endings = []
            decisions = 0
            while any(r is not None for r in reply["observations"]):
                actions = [r["teacher"] if r else None for r in reply["observations"]]
                decisions += sum(a is not None for a in actions)
                reply = pool.call({"op": "step", "actions": actions})
                endings.extend(reply["ended"])
            self.assertEqual(len(endings), 20)
            self.assertFalse(any(e["truncated"] for e in endings))
            return sorted(endings, key=lambda e: e["env"]), decisions
        finally:
            pool.close()

    def test_complete_games_match_synchronous_pool(self):
        self.assertEqual(self.play(EnginePool), self.play(AsyncEnginePool))

    def test_pending_game_survives_other_game_completion(self):
        with tempfile.TemporaryDirectory() as directory:
            script = Path(directory) / "fake.cjs"
            script.write_text("""const r=require('readline').createInterface({input:process.stdin});
const slow=process.env.SEED.endsWith('-1');r.on('line',line=>{const q=JSON.parse(line);
setTimeout(()=>console.log(JSON.stringify(q.op==='reset'?{observations:[{teacher:0}],ended:[]}:
{observations:[null],ended:[{env:0}]})),slow?100:0);});""")
            pool = AsyncEnginePool(2, script=str(script))
            try:
                reply = pool.call({"op": "reset", "n": 2})
                ended = []
                while any(r is not None for r in reply["observations"]):
                    reply = pool.call(
                        {
                            "op": "step",
                            "actions": [
                                0 if r else None for r in reply["observations"]
                            ],
                        }
                    )
                    ended.extend(reply["ended"])
                self.assertEqual(sorted(e["env"] for e in ended), [0, 1])
            finally:
                pool.close()


if __name__ == "__main__":
    unittest.main()
