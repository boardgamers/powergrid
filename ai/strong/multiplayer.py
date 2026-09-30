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
