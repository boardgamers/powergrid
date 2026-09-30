"""Combine disjoint paired arena shards without treating seat repeats as independent."""

import argparse
import json
from pathlib import Path
from arena_statistics import win_summary, search_summary, validate_pairs

p = argparse.ArgumentParser()
p.add_argument("reports", nargs="+")
p.add_argument("--output", required=True)
a = p.parse_args()
reports = [json.loads(Path(x).read_text()) for x in a.reports]
keys = [
    "model_sha256",
    "model_feature_revision",
    "encoder_feature_revision",
    "opponent",
    "opponent_sha256",
    "opponent_feature_revision",
    "paired_seats",
    "candidate_search_samples",
    "candidate_geographic_search",
    "search_max_steps",
]
for report in reports:
    report.setdefault("candidate_search_scope", "all")
    report.setdefault("search_max_steps", 1200)
    report.setdefault("player_count", 3)
    report.setdefault("candidate_search_model_proposal", True)
keys.extend(
    ["candidate_search_scope", "player_count", "candidate_search_model_proposal"]
)
config = {k: reports[0][k] for k in keys}
rows = []
seen = set()
for report in reports:
    assert {k: report[k] for k in keys} == config, "Incompatible arena settings"
    assert report["paired_seats"] and len(report["results"]) == report["games"]
    for row in report["results"]:
        key = (row["gameSeed"], row["variant"], row["sealed"], row["seat"])
        assert key not in seen, f"Duplicate match: {key}"
        seen.add(key)
        rows.append(row)
validate_pairs(rows, config["player_count"])
result = {
    **config,
    "sources": a.reports,
    **win_summary(rows),
    **search_summary(rows),
    "by_rules": [],
    "results": rows,
}
for variant in ["original", "recharged"]:
    for sealed in [False, True]:
        group = [r for r in rows if r["variant"] == variant and r["sealed"] == sealed]
        result["by_rules"].append(
            {"variant": variant, "sealed": sealed, **win_summary(group)}
        )
Path(a.output).write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps({k: v for k, v in result.items() if k != "results"}))
