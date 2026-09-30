"""Independent CPU arena, with reserved seeds and per-rule results."""

import sys, argparse, json, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
from infer import Model
from pool import EnginePool
from arena_statistics import win_summary, search_summary
from search_scope import SCOPES, search_enabled
from feature_contract import FEATURE_REVISION, check_revision, model_revision

p = argparse.ArgumentParser()
p.add_argument("model")
p.add_argument("--search-scope", choices=SCOPES, default="all")
p.add_argument(
    "--opponent",
    default="economic",
    choices=["economic", "heuristic", "rush", "legacy", "search", "search_geo"],
)
p.add_argument("--opponent-model", help="Frozen ONNX policy in both opponent seats")
p.add_argument("--workers", type=int, default=4)
p.add_argument("--geographic-search", action="store_true")
p.add_argument(
    "--search-samples",
    type=int,
    default=0,
    help="Public-belief search guided by the candidate model",
)
p.add_argument("--games", type=int, default=480)
p.add_argument("--seed", default="strong-screening-v1")
p.add_argument("--output", required=True)
p.add_argument(
    "--allow-feature-transfer",
    action="store_true",
    help="Explicit research-only encoder transfer",
)
args = p.parse_args()
if not 0 <= args.search_samples <= 64:
    p.error("--search-samples must be 0..64")
if args.geographic_search and not args.search_samples:
    p.error("--geographic-search requires positive --search-samples")
model = Model(args.model)
if args.games < 12 or args.games % 12:
    p.error("--games must be a positive multiple of 12 for paired rules and seats")
opponent_model = Model(args.opponent_model) if args.opponent_model else None
pool = EnginePool(args.workers, seed=args.seed, script="ai/strong/bridge.cjs")
feature_revision = (
    FEATURE_REVISION if args.allow_feature_transfer else model_revision(model)
)
feature_revisions = (
    {} if args.allow_feature_transfer else {"learner": model_revision(model)}
)
if opponent_model and not args.allow_feature_transfer:
    feature_revisions["snapshot0"] = model_revision(opponent_model)
try:
    current = pool.call(
        {
            "op": "reset",
            "n": args.games,
            "mode": "snapshot0" if opponent_model else args.opponent,
            "arenaSeed": args.seed,
            "featureRevisions": feature_revisions,
        }
    )["observations"]
except BaseException:
    pool.close()
    raise
rows = []
latency = []
start = time.perf_counter()
last_progress = start
try:
    while any(x is not None for x in current):
        actions = []
        for x in current:
            if x is None:
                actions.append(None)
                continue
            t = time.perf_counter()
            actor = model if x["roles"][x["seat"]] == "learner" else opponent_model
            check_revision(
                actor, x.get("featureRevision", "3.0"), args.allow_feature_transfer
            )
            a, _ = actor.predict(x["state"], x["actions"])
            if actor is model:
                latency.append(1000 * (time.perf_counter() - t))
            actions.append(
                {
                    "proposal": a,
                    "searchSamples": args.search_samples,
                    "geography": args.geographic_search,
                }
                if actor is model
                and args.search_samples
                and search_enabled(args.search_scope, x["variant"], x["sealed"])
                else a
            )
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
        if time.perf_counter() - last_progress >= 30:
            print(
                json.dumps(
                    {
                        "stage": "arena_progress",
                        "completed_games": len(rows),
                        "requested_games": args.games,
                        "seconds": time.perf_counter() - start,
                        "seed": args.seed,
                    }
                ),
                flush=True,
            )
            last_progress = time.perf_counter()
finally:
    pool.close()
report = {
    "model": args.model,
    "model_sha256": model.sha256,
    "model_feature_revision": model_revision(model),
    "encoder_feature_revision": feature_revision,
    "opponent": args.opponent_model or args.opponent,
    "opponent_sha256": opponent_model.sha256 if opponent_model else None,
    "opponent_feature_revision": model_revision(opponent_model)
    if opponent_model
    else None,
    "paired_seats": True,
    "candidate_search_samples": args.search_samples,
    "candidate_search_scope": args.search_scope,
    "candidate_geographic_search": args.geographic_search,
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
report.update(win_summary(rows))
report.update(search_summary(rows))
for group in report["by_rules"]:
    group.update(
        win_summary(
            [
                r
                for r in rows
                if r["variant"] == group["variant"] and r["sealed"] == group["sealed"]
            ]
        )
    )
Path(args.output).write_text(json.dumps(report, indent=2))
print(json.dumps({k: v for k, v in report.items() if k != "results"}))
