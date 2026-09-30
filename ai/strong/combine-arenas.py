"""Combine disjoint paired arena shards without treating seat repeats as independent."""

import argparse
import json
from pathlib import Path
from arena_statistics import win_summary, search_summary

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
]
for report in reports:
    report.setdefault("candidate_search_scope", "all")
keys.append("candidate_search_scope")
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
for deal in {r["gameSeed"] for r in rows}:
    assert sum(r["gameSeed"] == deal for r in rows) == 12, "Incomplete paired deal"
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
