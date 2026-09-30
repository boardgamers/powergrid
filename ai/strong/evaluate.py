"""Independent CPU arena, with reserved seeds and per-rule results."""

import sys, argparse, json, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
from infer import Model
from pool import EnginePool

p = argparse.ArgumentParser()
p.add_argument("model")
p.add_argument(
    "--opponent",
    default="economic",
    choices=["economic", "heuristic", "rush", "legacy"],
)
p.add_argument("--games", type=int, default=480)
p.add_argument("--seed", default="strong-screening-v1")
p.add_argument("--output", required=True)
args = p.parse_args()
model = Model(args.model)
pool = EnginePool(4, seed=args.seed, script="ai/strong/bridge.cjs")
current = pool.call({"op": "reset", "n": args.games, "mode": args.opponent})[
    "observations"
]
rows = []
latency = []
start = time.perf_counter()
try:
    while any(x is not None for x in current):
        actions = []
        for x in current:
            if x is None:
                actions.append(None)
                continue
            t = time.perf_counter()
            a, _ = model.predict(x["state"], x["actions"])
            latency.append(1000 * (time.perf_counter() - t))
            actions.append(a)
        r = pool.call({"op": "step", "actions": actions})
        current = r["observations"]
        for e in r["ended"]:
            seat = e["roles"].index("learner")
            rows.append(
                {
                    **e,
                    "seat": seat,
                    "variant": "recharged" if e["episode"] % 2 else "original",
                    "sealed": e["episode"] % 4 < 2,
                    "win": e["value"][seat],
                }
            )
finally:
    pool.close()
report = {
    "model": args.model,
    "model_sha256": model.sha256,
    "opponent": args.opponent,
    "seed": args.seed,
    "games": len(rows),
    "win_rate": float(np.mean([r["win"] for r in rows])),
    "truncated": sum(r["truncated"] for r in rows),
    "seconds": time.perf_counter() - start,
    "inference_p95_ms": float(np.percentile(latency, 95)),
    "by_rules": [
        {
            "variant": v,
            "sealed": s,
            "games": len([r for r in rows if r["variant"] == v and r["sealed"] == s]),
            "win_rate": float(
                np.mean(
                    [r["win"] for r in rows if r["variant"] == v and r["sealed"] == s]
                )
            ),
        }
        for v in ["original", "recharged"]
        for s in [False, True]
    ],
    "results": rows,
}
Path(args.output).write_text(json.dumps(report, indent=2))
print(json.dumps({k: v for k, v in report.items() if k != "results"}))
