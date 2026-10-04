"""Validation and independent-game splitting for schema-4 search supervision."""

import hashlib
import numpy as np
from multiplayer import FEATURE_REVISION, PLAYER_COUNTS, rotate_outcome


def validation_game(seed):
    return int.from_bytes(hashlib.sha256(seed.encode()).digest()[:8], "big") % 5 == 0


def validate_game(game):
    n = game["playerCount"]
    if game["featureRevision"] != FEATURE_REVISION or n not in PLAYER_COUNTS:
        raise ValueError("Wrong teacher feature revision or player count")
    if game["variant"] not in ["original", "recharged"] or not isinstance(
        game["sealed"], bool
    ):
        raise ValueError("Missing teacher rules")
    if not isinstance(game["seed"], str) or not game["seed"]:
        raise ValueError("Missing independent game seed")
    if game["truncated"]:
        if game["rows"]:
            raise ValueError("Truncated episodes cannot carry training targets")
        return
    if len(game["value"]) != n:
        raise ValueError("Wrong terminal vector length")
    for row in game["rows"]:
        state = np.asarray(row["state"])
        actions = np.asarray(row["actions"])
        if (
            state.shape != (1149,)
            or actions.ndim != 2
            or actions.shape[1] != 98
            or not len(actions)
        ):
            raise ValueError("Wrong teacher feature dimensions")
        if not np.isfinite(state).all() or not np.isfinite(actions).all():
            raise ValueError("Nonfinite teacher features")
        if state[:6].tolist() != [1] * n + [0] * (6 - n):
            raise ValueError("Wrong active-player mask")
        if not 0 <= row["target"] < len(actions):
            raise ValueError("Teacher target is not a candidate")
        if row["value"] != rotate_outcome(game["value"], row["seat"]):
            raise ValueError("Value target does not match the observing seat")
        seen = set()
        for index, value in row["searchValues"]:
            if (
                index in seen
                or not 0 <= index < len(actions)
                or not np.isfinite(value)
                or not 0 <= value <= 1
            ):
                raise ValueError("Invalid search estimate")
            seen.add(index)


def validation_seeds(games):
    """Hold out whole games in every count/seat/rule cell, by stable seed rank."""
    groups = {}
    seen = set()
    for game in games:
        if game["seed"] in seen:
            raise ValueError("Duplicate independent game seed")
        seen.add(game["seed"])
        seat = game["rows"][0]["seat"] if game["rows"] else None
        if seat is None or any(row["seat"] != seat for row in game["rows"]):
            raise ValueError("Expected one teacher seat per game")
        key = (game["playerCount"], seat, game["variant"], game["sealed"])
        groups.setdefault(key, []).append(game["seed"])
    selected = set()
    for seeds in groups.values():
        if len(seeds) < 2:
            raise ValueError(
                "Each teacher seat/rule cell needs train and validation games"
            )
        seeds.sort(key=lambda seed: hashlib.sha256(seed.encode()).digest())
        selected.update(seeds[: max(1, round(len(seeds) * 0.2))])
    return selected
