import argparse, json, time, platform
from pathlib import Path
import numpy as np
from infer import Model, Node

p = argparse.ArgumentParser()
p.add_argument("model")
p.add_argument("--seeds", type=int, default=10)
p.add_argument("--opponent", default="heuristic", choices=["heuristic", "legacy"])
p.add_argument("--output", default="evaluation.json")
args = p.parse_args()
net = None if args.model == "heuristic" else Model(args.model)
node = Node("arena.cjs")
results = []
latency = []
start = time.perf_counter()
try:
    for variant in ["original", "recharged"]:
        for sealed in [False, True]:
            for seed in range(args.seeds):
                for seat in range(3):
                    config = {
                        "op": "reset",
                        "seed": "heldout-arena-v1-" + str(seed),
                        "variant": variant,
                        "sealed": sealed,
                        "seat": seat,
                        "opponent": args.opponent,
                    }
                    o = node.call(config)
                    while not o["done"]:
                        t = time.perf_counter()
                        action = (
                            net.predict(o["state"], o["actions"])[0]
                            if net
                            else o["heuristic"]
                        )
                        latency.append((time.perf_counter() - t) * 1000)
                        o = node.call({"op": "step", "action": action})
                    results.append({**config, **o})
            group = [
                r for r in results if r["variant"] == variant and r["sealed"] == sealed
            ]
            print(
                json.dumps(
                    {
                        "variant": variant,
                        "sealed": sealed,
                        "games": len(group),
                        "win_rate": np.mean([r["win"] for r in group]),
                        "truncated": sum(r["truncated"] for r in group),
                    }
                ),
                flush=True,
            )
finally:
    node.close()
report = {
    "model": args.model,
    "opponent": args.opponent,
    "platform": platform.platform(),
    "games": len(results),
    "win_rate": np.mean([r["win"] for r in results]),
    "truncated": sum(r["truncated"] for r in results),
    "seconds": time.perf_counter() - start,
    "inference_ms": {
        k: float(np.percentile(latency, v))
        for k, v in [("p50", 50), ("p95", 95), ("p99", 99)]
    },
    "results": results,
}
Path(args.output).write_text(json.dumps(report, indent=2))
print(json.dumps({k: v for k, v in report.items() if k != "results"}))
