"""Aggregate arenas with confidence intervals clustered by shared game seed."""

import argparse, json
from pathlib import Path
import numpy as np

p = argparse.ArgumentParser()
p.add_argument("files", nargs="+")
args = p.parse_args()
summaries = []
for file in args.files:
    r = json.loads(Path(file).read_text())
    groups = {}
    for row in r["results"]:
        groups.setdefault(row["seed"], []).append(row["win"])
    means = np.array([np.mean(xs) for xs in groups.values()])
    rng = np.random.default_rng(171)
    ci = np.percentile(
        rng.choice(means, (10000, len(means))).mean(axis=1), [2.5, 97.5]
    ).tolist()
    degenerate = bool(np.all(means == means[0]))
    if degenerate:
        ci = None
    summaries.append(
        {
            **{k: v for k, v in r.items() if k != "results"},
            "seed_cluster_bootstrap_95pct": ci,
            "interval_note": "Not estimated: identical seed outcomes make percentile bootstrap degenerate"
            if degenerate
            else "Percentile bootstrap over shared seeds",
            "by_rules": [
                {
                    "variant": variant,
                    "sealed": sealed,
                    "win_share": float(
                        np.mean(
                            [
                                x["win"]
                                for x in r["results"]
                                if x["variant"] == variant and x["sealed"] == sealed
                            ]
                        )
                    ),
                }
                for variant in ["original", "recharged"]
                for sealed in [False, True]
            ],
        }
    )
print(json.dumps(summaries, indent=2))
