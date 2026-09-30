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


def search_summary(rows):
    if not all("searchStats" in row for row in rows):
        return {"search_rollouts_reported": False}
    totals = {}
    for row in rows:
        for role, stats in row["searchStats"].items():
            target = totals.setdefault(
                role, {"decisions": 0, "evaluations": 0, "truncated": 0}
            )
            for key in target:
                target[key] += stats[key]
    return {"search_rollouts_reported": True, "search_stats": totals}


def validate_pairs(rows, players):
    """Reject missing seats/rules and malformed outcomes, including in old reports."""
    if players not in range(2, 7) or not rows:
        raise ValueError("Expected nonempty 2–6 player arena")
    expected = {
        (seat, variant, sealed)
        for seat in range(players)
        for variant in ["original", "recharged"]
        for sealed in [False, True]
    }
    deals = {}
    for row in rows:
        if row.get("playerCount", players) != players:
            raise ValueError("Mixed player counts")
        key = (row["seat"], row["variant"], row["sealed"])
        seen = deals.setdefault(row["gameSeed"], set())
        if key in seen or key not in expected:
            raise ValueError("Duplicate or invalid paired match")
        seen.add(key)
        if len(row["value"]) != players or len(row["roles"]) != players:
            raise ValueError("Wrong terminal vector or role count")
        if row["roles"].count("learner") != 1 or row["roles"][row["seat"]] != "learner":
            raise ValueError("Wrong candidate seat")
        if any(not np.isfinite(v) or v < 0 or v > 1 for v in row["value"]):
            raise ValueError("Invalid terminal credits")
        if not row["truncated"] and not np.isclose(sum(row["value"]), 1):
            raise ValueError("Terminal credits must sum to one")
        if row["win"] != row["value"][row["seat"]]:
            raise ValueError("Candidate win differs from terminal credit")
    if any(seen != expected for seen in deals.values()):
        raise ValueError("Incomplete paired deal")
