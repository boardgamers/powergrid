"""Uncertainty over independent deals, keeping seat/rule repeats together."""

import numpy as np


def win_summary(rows, key="gameSeed"):
    groups = {}
    for row in rows:
        groups.setdefault(row[key], []).append(float(row["win"]))
    totals = np.asarray([sum(v) for v in groups.values()])
    counts = np.asarray([len(v) for v in groups.values()])
    result = {
        "games": len(rows),
        "independent_seeds": len(groups),
        "win_rate": float(totals.sum() / counts.sum()),
        "truncated": sum(row["truncated"] for row in rows),
    }
    if len(groups) >= 2:
        rng = np.random.default_rng(8501)
        picks = rng.integers(len(groups), size=(10000, len(groups)))
        draws = totals[picks].sum(axis=1) / counts[picks].sum(axis=1)
        result["seed_bootstrap_95_interval"] = np.quantile(
            draws, [0.025, 0.975]
        ).tolist()
    else:
        result["seed_bootstrap_95_interval"] = None
    return result
