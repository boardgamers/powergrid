"""Shared schema-4 training contracts, also exercised without gradient training."""

FEATURE_REVISION = "4.0-multiplayer"
PLAYER_COUNTS = (2, 3, 4, 5, 6)
ROLE_REVISIONS = {
    role: FEATURE_REVISION
    for role in ("learner", "snapshot0", "snapshot1", "snapshot2")
}


def rotate_outcome(outcome, seat):
    n = len(outcome)
    if n not in PLAYER_COUNTS or not 0 <= seat < n:
        raise ValueError("Invalid terminal outcome shape or seat")
    if abs(sum(outcome) - 1) > 1e-6 or any(x < 0 for x in outcome):
        raise ValueError("Expected complete terminal win credits")
    return [outcome[(seat + j) % n] for j in range(n)] + [0.0] * (6 - n)


def balance_training_rows(rows):
    """Normalize advantages within a count and give each count equal loss mass."""
    import numpy as np

    groups = {}
    for row in rows:
        groups.setdefault(row["playerCount"], []).append(row)
    for group in groups.values():
        advantages = np.asarray([row["advantage"] for row in group])
        mean, std = advantages.mean(), advantages.std() + 1e-6
        weight = len(rows) / (len(groups) * len(group))
        for row in group:
            row["normalized_advantage"] = float((row["advantage"] - mean) / std)
            row["training_weight"] = weight
