"""Balance replay sources without changing their per-player-count coverage."""

from collections import Counter


def source_count_weights(rows, player_counts):
    sizes = Counter((r.get("dataset_source", 0), r["player_count"]) for r in rows)
    sources = {source for source, _ in sizes}
    expected = {(source, n) for source in sources for n in player_counts}
    if not rows or set(sizes) != expected:
        raise ValueError("Every teacher source must cover every player count")
    return {key: len(rows) / (len(sizes) * size) for key, size in sizes.items()}


def validate_initial_checkpoint(
    checkpoint, architecture, revision, state_dim, action_dim
):
    expected = dict(
        architecture=architecture,
        feature_revision=revision,
        state_dim=state_dim,
        action_dim=action_dim,
    )
    if any(checkpoint.get(key) != value for key, value in expected.items()):
        raise ValueError(
            "Distillation warm start requires the exact architecture and feature contract"
        )
