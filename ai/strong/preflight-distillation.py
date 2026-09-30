"""Offline CPU inference and target checks; no gradients or optimizer steps."""

import argparse
from collections import Counter
import gzip
import json
from pathlib import Path
import numpy as np
import torch
from model import tensors
from model_v4 import MultiplayerPolicy
from distillation_targets import policy_targets

p = argparse.ArgumentParser()
p.add_argument("dataset_directory")
p.add_argument("--output", required=True)
p.add_argument("--ordered-players", action="store_true")
a = p.parse_args()
selected = []
cells = Counter()
files = sorted(Path(a.dataset_directory).glob("multiplayer-teacher-v1-*.jsonl.gz"))
if len(files) != 5:
    raise ValueError("Need all five immutable teacher shards")
for path in files:
    with gzip.open(path, "rt") as source:
        for line in source:
            game = json.loads(line)
            if game["truncated"]:
                raise ValueError("Dataset contains truncated games")
            for row in game["rows"]:
                move_type = int(np.argmax(row["actions"][row["target"]][:10]))
                cell = (
                    game["playerCount"],
                    game["variant"],
                    game["sealed"],
                    row["phase"],
                    move_type,
                )
                if cells[cell] >= 2:
                    continue
                cells[cell] += 1
                selected.append({**row, "playerCount": game["playerCount"]})
# Mix counts in each batch to exercise padding and masked-value targets.
np.random.default_rng(742).shuffle(selected)
torch.set_num_threads(1)
net = MultiplayerPolicy(ordered_players=a.ordered_players).eval()
losses = {mode: [] for mode in ["hard", "soft"]}
with torch.inference_mode():
    for start in range(0, len(selected), 64):
        rows = selected[start : start + 64]
        x = tensors(rows, "cpu")
        logits, values = net(*x)
        assert torch.isfinite(logits).all() and torch.isfinite(values).all()
        np.testing.assert_allclose(values.sum(-1).numpy(), 1, atol=1e-6)
        for index, row in enumerate(rows):
            n = row["playerCount"]
            assert torch.all(values[index, n:] == 0)
            assert row["value"][n:] == [0] * (6 - n)
        for mode in losses:
            targets = policy_targets(rows, logits.shape[1], soft=mode == "soft")
            assert np.isfinite(targets).all() and np.all(targets >= 0)
            np.testing.assert_allclose(targets.sum(-1), 1, atol=1e-6)
            assert np.all(targets[~x[2].numpy()] == 0)
            ce = -(torch.from_numpy(targets) * logits.log_softmax(-1)).sum(-1)
            assert torch.isfinite(ce).all()
            losses[mode].extend(ce.tolist())
report = {
    "purpose": "Offline CPU preflight only; no training",
    "architecture": "multiplayer_ordered" if a.ordered_players else "multiplayer",
    "parameters": sum(p.numel() for p in net.parameters()),
    "shards": len(files),
    "positions": len(selected),
    "counts": dict(Counter(r["playerCount"] for r in selected)),
    "seat_rule_phase_action_cells": len(cells),
    "hard_soft_targets_valid": True,
    "inactive_values_zero": True,
    "mean_initial_cross_entropy": {
        mode: float(np.mean(xs)) for mode, xs in losses.items()
    },
}
Path(a.output).write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report))
