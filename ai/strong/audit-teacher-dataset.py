"""Read-only audit of immutable HF teacher shards before GPU training."""

import argparse
from collections import Counter
import gzip
import json
from pathlib import Path
from huggingface_hub import hf_hub_download
from teacher_contract import validate_game, validation_seeds

p = argparse.ArgumentParser()
p.add_argument("--revision", required=True)
p.add_argument("--version", default="multiplayer-teacher-v1")
p.add_argument("--output", required=True)
a = p.parse_args()
summary = {}
metadata = []
seen = set()
for shard, n in enumerate(range(2, 7)):
    path = hf_hub_download(
        "coyotte508/powergrid-ai-training-v1",
        f"{a.version}/{a.version}-{shard}.jsonl.gz",
        repo_type="dataset",
        revision=a.revision,
    )
    stats = dict(
        games=0,
        positions=0,
        truncated=0,
        search_rollouts=0,
        search_rollouts_truncated=0,
        teacher_win_credit=0.0,
        disagreements=0,
    )
    cells = Counter()
    phases = Counter()
    opponents = {}
    with gzip.open(path, "rt") as source:
        for line in source:
            game = json.loads(line)
            validate_game(game)
            assert game["playerCount"] == n
            assert game["seed"] not in seen
            seen.add(game["seed"])
            stats["games"] += 1
            stats["truncated"] += game["truncated"]
            stats["positions"] += len(game["rows"])
            stats["search_rollouts"] += game["searchStats"]["evaluations"]
            stats["search_rollouts_truncated"] += game["searchStats"]["truncated"]
            if game["truncated"]:
                continue
            assert game["rows"]
            seat = game["rows"][0]["seat"]
            win = game["value"][seat]
            stats["teacher_win_credit"] += win
            opponent = ["economic", "heuristic", "rush"][game["id"] // (4 * n) % 3]
            opp = opponents.setdefault(opponent, dict(games=0, win_credit=0.0))
            opp["games"] += 1
            opp["win_credit"] += win
            cells[(seat, game["variant"], game["sealed"])] += 1
            for row in game["rows"]:
                phases[row["phase"]] += 1
                stats["disagreements"] += not row["teacherAgrees"]
            metadata.append(
                {
                    **{
                        k: game[k] for k in ["seed", "playerCount", "variant", "sealed"]
                    },
                    "rows": [{"seat": seat}],
                }
            )
    assert stats["games"] == 240 and len(cells) == n * 4
    summary[str(n)] = {
        **stats,
        "seat_rule_cells": len(cells),
        "phases": dict(phases),
        "opponents": opponents,
    }
selected = validation_seeds(metadata)
for n, stats in summary.items():
    stats["validation_games"] = sum(
        g["playerCount"] == int(n) and g["seed"] in selected for g in metadata
    )
    stats["training_games"] = sum(
        g["playerCount"] == int(n) and g["seed"] not in selected for g in metadata
    )
report = dict(
    revision=a.revision,
    version=a.version,
    counts=summary,
    unique_games=len(seen),
    validated=True,
    scope="Teacher-generated development data; not held-out strength evidence",
)
Path(a.output).write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report))
