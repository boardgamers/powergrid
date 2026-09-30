"""Measure ambiguity in held-out search labels; estimates are not true win values."""

import argparse
from collections import defaultdict
import gzip
import json
from pathlib import Path
from teacher_contract import validation_seeds

p = argparse.ArgumentParser()
p.add_argument("dataset_directory", type=Path)
p.add_argument("--output", type=Path, required=True)
a = p.parse_args()
paths = sorted(a.dataset_directory.glob("*.jsonl.gz"))
assert len(paths) == 5
metadata = []
for path in paths:
    with gzip.open(path, "rt") as source:
        for line in source:
            game = json.loads(line)
            metadata.append(
                {
                    **{
                        k: game[k] for k in ["seed", "playerCount", "variant", "sealed"]
                    },
                    "rows": [{"seat": r["seat"]} for r in game["rows"]],
                }
            )
held_out = validation_seeds(metadata)
groups = defaultdict(lambda: defaultdict(int))
for path in paths:
    with gzip.open(path, "rt") as source:
        for line in source:
            game = json.loads(line)
            if game["seed"] not in held_out:
                continue
            for row in game["rows"]:
                for key in [
                    str(game["playerCount"]),
                    f"{game['playerCount']}/{row['phase']}",
                ]:
                    g = groups[key]
                    g["positions"] += 1
                    values = sorted([v for _, v in row["searchValues"]], reverse=True)
                    if len(values) < 2:
                        g["fewer_than_two_searched_candidates"] += 1
                        continue
                    g["search_comparisons"] += 1
                    margin = values[0] - values[1]
                    g["tied_top_estimates"] += margin < 1e-9
                    g["top_gap_at_most_one_of_16_rollouts"] += margin <= 1 / 16 + 1e-9
                    if not row["teacherAgrees"]:
                        g["teacher_disagreements"] += 1
                        g["disagreements_with_tied_top"] += margin < 1e-9
report = {
    "scope": "Held-out teacher states; finite 16-rollout estimates, not calibrated confidence or true action quality.",
    "validation_games": len(held_out),
    "groups": dict(groups),
}
a.output.write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps({k: v for k, v in groups.items() if "/" not in k}))
