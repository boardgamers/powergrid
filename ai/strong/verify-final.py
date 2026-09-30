"""Audit the frozen held-out protocol against raw matches and CPU artifacts."""

import argparse
import json
from pathlib import Path
import sys
from arena_statistics import win_summary, search_summary

p = argparse.ArgumentParser()
p.add_argument("candidate")
p.add_argument("reports", nargs="+")
p.add_argument("--protocol", default="ai/strong/final-protocol.json")
p.add_argument("--parity", required=True)
p.add_argument("--cpu", required=True)
p.add_argument("--package", required=True)
p.add_argument("--output", required=True)
a = p.parse_args()
read = lambda path: json.loads(Path(path).read_text())
candidate, protocol = read(a.candidate), read(a.protocol)
errors, audited = [], {}


def require(condition, message):
    if not condition:
        errors.append(message)


expected = {x["name"]: x for x in protocol["opponents"]}
sha = candidate["model_sha256"]
require(
    candidate.get("status") == "selected", "Candidate was not frozen before validation"
)
for path in a.reports:
    report = read(path)
    spec = next(
        (
            x
            for x in expected.values()
            if (
                report.get("opponent_sha256") == x.get("model_sha256")
                if "model_sha256" in x
                else report.get("opponent") == x["name"]
                and not report.get("opponent_sha256")
            )
        ),
        None,
    )
    if spec is None:
        errors.append(f"Unknown opponent report: {path}")
        continue
    name = spec["name"]
    require(name not in audited, f"{name}: duplicate opponent report")
    require(report["model_sha256"] == sha, f"{name}: wrong checkpoint")
    require(
        report["model_feature_revision"]
        == candidate["feature_revision"]
        == report["encoder_feature_revision"],
        f"{name}: feature contract mismatch",
    )
    require(
        report["candidate_search_samples"] == candidate["search_samples"],
        f"{name}: wrong search budget",
    )
    require(
        report["candidate_geographic_search"] == candidate["geographic_search"],
        f"{name}: wrong geographic search setting",
    )
    require(
        report.get("candidate_search_scope", "all")
        == candidate.get("search_scope", "all"),
        f"{name}: wrong search scope",
    )
    rows = report["results"]
    require(
        len(rows) == report["games"] == spec["games"], f"{name}: incomplete game count"
    )
    pairs = set()
    deals = {}
    for row in rows:
        require(
            row["gameSeed"].startswith(protocol["seed_prefix"] + "-"),
            f"{name}: non-final seed {row['gameSeed']}",
        )
        key = (row["variant"], row["sealed"], row["seat"])
        pair = (row["gameSeed"], *key)
        require(pair not in pairs, f"{name}: duplicate paired match {pair}")
        pairs.add(pair)
        deals.setdefault(row["gameSeed"], set()).add(key)
        require(not row["truncated"], f"{name}: truncated match {pair}")
        require(
            row["roles"].count("learner") == 1
            and row["roles"][row["seat"]] == "learner",
            f"{name}: incorrect learner seat",
        )
        role = "snapshot0" if "model_path" in spec else name
        require(
            all(r in ["learner", role] for r in row["roles"]),
            f"{name}: wrong opponent roles",
        )
        require(
            abs(sum(row["value"]) - 1) < 1e-8
            and abs(row["win"] - row["value"][row["seat"]]) < 1e-8,
            f"{name}: inconsistent terminal credit",
        )
    required_pairs = {
        (v, s, seat)
        for v in ["original", "recharged"]
        for s in [False, True]
        for seat in range(3)
    }
    require(
        all(x == required_pairs for x in deals.values()),
        f"{name}: missing seat/rule combinations",
    )
    require(len(deals) == spec["games"] // 12, f"{name}: wrong independent-deal count")
    summary = win_summary(rows)
    require(
        summary["win_rate"] >= spec["minimum_win_rate"],
        f"{name}: win rate below {spec['minimum_win_rate']:.1%}",
    )
    interval = summary["seed_bootstrap_95_interval"]
    require(
        interval is not None
        and interval[0]
        > protocol["requirements"]["overall_interval_lower_bound_above"],
        f"{name}: overall advantage is not established",
    )
    groups = []
    for variant in ["original", "recharged"]:
        for sealed in [False, True]:
            subset = [
                r for r in rows if r["variant"] == variant and r["sealed"] == sealed
            ]
            if not subset:
                errors.append(f"{name}: missing rule subset {variant}/{sealed}")
                continue
            group = win_summary(subset)
            interval = group["seed_bootstrap_95_interval"]
            require(
                interval is not None
                and interval[0]
                > protocol["requirements"]["each_rule_interval_lower_bound_above"],
                f"{name}: advantage not established for {variant}, sealed={sealed}",
            )
            groups.append({"variant": variant, "sealed": sealed, **group})
    search = search_summary(rows)
    require(
        search["search_rollouts_reported"],
        f"{name}: search rollout diagnostics missing",
    )
    audited[name] = {"source": path, **summary, **search, "by_rules": groups}
require(set(audited) == set(expected), "Missing required opponent evaluations")
parity, cpu, package = read(a.parity), read(a.cpu), read(a.package)
for label, artifact in [("parity", parity), ("cpu", cpu), ("package", package)]:
    require(artifact["model_sha256"] == sha, f"{label}: wrong model hash")
require(
    parity["positions"] == 427 and parity["all_actions_match"],
    "Checkpoint/export parity did not cover all fixtures",
)
require(
    cpu["positions"] == 427 and cpu["all_moves_legal"],
    "CPU worker did not pass all legal fixtures",
)
require("8840U" in cpu.get("processor_model", ""), "CPU benchmark was not on the 8840U")
require(
    cpu["search_samples"] == candidate["search_samples"]
    and cpu.get("search_scope", "all") == candidate.get("search_scope", "all")
    and cpu["geographic_search"] == candidate["geographic_search"],
    "CPU benchmark configuration differs from final candidate",
)
require(
    package["all_hashes_match"]
    and package["files_verified"] > 0
    and package["legal_fixture_responses"] == 427,
    "Standalone archive verification incomplete",
)
result = {
    "passed": not errors,
    "errors": errors,
    "candidate": candidate,
    "protocol": protocol,
    "evaluations": audited,
    "parity": parity,
    "cpu": cpu,
    "package": package,
}
Path(a.output).write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps({"passed": not errors, "errors": errors, "opponents": list(audited)}))
sys.exit(0 if not errors else 1)
