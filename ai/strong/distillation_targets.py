"""Targets retain uncertainty across sampled counterfactual search actions."""

import numpy as np


def policy_targets(rows, candidates, soft=False):
    targets = np.zeros((len(rows), candidates), dtype=np.float32)
    for i, row in enumerate(rows):
        estimates = row.get("searchValues", [])
        if not soft or not estimates:
            targets[i, row["target"]] = 1
            continue
        indices = np.asarray([x[0] for x in estimates], dtype=np.int64)
        values = np.asarray([x[1] for x in estimates], dtype=np.float32)
        assert len(set(indices.tolist())) == len(indices)
        assert np.all((indices >= 0) & (indices < len(row["actions"])))
        prior = np.asarray(row["actions"], dtype=np.float32)[indices, 74]
        # When rollouts cannot distinguish the actions, retain the economic prior.
        scores = (
            prior * 2 if values.max() == values.min() else values * 8 + prior * 0.15
        )
        weights = np.exp(scores - scores.max())
        targets[i, indices] = weights / weights.sum()
    return targets
