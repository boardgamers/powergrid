"""Audit the frozen held-out protocol against raw matches and CPU artifacts."""

import argparse
import json
from pathlib import Path
import sys
from arena_statistics import win_summary, search_summary, validate_pairs

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


multiplayer = isinstance(protocol.get("scope"), dict)
expected = (
    {
        f"{x['name']}/{n}p": {**x, **spec, "player_count": int(n)}
        for x in protocol["opponents"]
        for n, spec in x["counts"].items()
    }
    if multiplayer
    else {x["name"]: {**x, "player_count": 3} for x in protocol["opponents"]}
)
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
                report.get("player_count", 3) == x["player_count"]
                and report.get("opponent_sha256") == x.get("model_sha256")
                if "model_sha256" in x
                else report.get("player_count", 3) == x["player_count"]
                and report.get("opponent") == x["name"]
                and not report.get("opponent_sha256")
            )
        ),
        None,
    )
    if spec is None:
        errors.append(f"Unknown opponent report: {path}")
        continue
    n = spec["player_count"]
    name = f"{spec['name']}/{n}p" if multiplayer else spec["name"]
    if multiplayer:
        source = candidate.get("source") or {}
        require(
            all(source.get(k) for k in ["archive", "revision", "sha256"])
            and report.get("source") == {k: source.get(k) for k in ["archive", "revision", "sha256"]},
            f"{name}: wrong or missing frozen runtime provenance",
        )
        require(
            bool(candidate.get("arena_runner_sha256"))
            and report.get("arena_runner_sha256") == candidate["arena_runner_sha256"],
            f"{name}: wrong arena runner",
        )
        require(report.get("model_repository_revision") == candidate.get("model_revision"), f"{name}: wrong model repository revision")
        require(report.get("opponent_repository_revision") == spec.get("model_revision"), f"{name}: wrong opponent repository revision")
        require(candidate.get("async_rollout") is False and report.get("async_rollout") is False,
                f"{name}: scheduling differs from the verified runtime")
        require(report.get("seed") == f"{protocol['seed_prefix']}-{n}p", f"{name}: wrong reserved seed namespace")
        require(report.get("deal_offset") == 0, f"{name}: aggregate must cover deals starting at zero")
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
        report.get("search_max_steps", 1200) == candidate.get("search_max_steps", 1200),
        f"{name}: wrong search simulation horizon",
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
    require(
        report.get("candidate_search_model_proposal", True) is True,
        f"{name}: search proposal ablation is not the deployment configuration",
    )
    rows = report["results"]
    require(
        len(rows) == report["games"] == spec["games"], f"{name}: incomplete game count"
    )
    try:
        validate_pairs(rows, n)
    except ValueError as error:
        errors.append(f"{name}: {error}")
    pairs = set()
    deals = {}
    for row in rows:
        if multiplayer:
            e = row.get("episode", -1)
            require(isinstance(e, int) and e >= 0
                    and row["gameSeed"] == f"{protocol['seed_prefix']}-{n}p-{e//(4*n)}"
                    and row["seat"] == (e//4) % n
                    and row["variant"] == ("recharged" if e % 2 else "original")
                    and row["sealed"] == (e % 4 < 2), f"{name}: episode pairing metadata mismatch")
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
        role = "snapshot0" if "model_path" in spec else spec["name"]
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
        for seat in range(n)
    }
    require(
        all(x == required_pairs for x in deals.values()),
        f"{name}: missing seat/rule combinations",
    )
    require(
        len(deals) == spec["games"] // (4 * n), f"{name}: wrong independent-deal count"
    )
    if multiplayer:
        require(set(deals) == {f"{protocol['seed_prefix']}-{n}p-{i}" for i in range(spec['games']//(4*n))},
                f"{name}: wrong exact reserved deal set")
        require({r.get("episode") for r in rows} == set(range(spec['games'])),
                f"{name}: wrong exact episode set")
    summary = win_summary(rows)
    require(
        summary["win_rate"] >= spec["minimum_win_rate"],
        f"{name}: win rate below {spec['minimum_win_rate']:.1%}",
    )
    interval = summary["seed_bootstrap_95_interval"]
    require(
        interval is not None
        and interval[0]
        > (
            1 / n
            if multiplayer
            else protocol["requirements"]["overall_interval_lower_bound_above"]
        ),
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
                > (
                    1 / n
                    if multiplayer
                    else protocol["requirements"][
                        "each_rule_interval_lower_bound_above"
                    ]
                ),
                f"{name}: advantage not established for {variant}, sealed={sealed}",
            )
            groups.append({"variant": variant, "sealed": sealed, **group})
    search = search_summary(rows)
    require(
        search["search_rollouts_reported"],
        f"{name}: search rollout diagnostics missing",
    )
    stats = search.get("search_stats", {})
    require(all(v["truncated"] == 0 for v in stats.values()), f"{name}: truncated search rollouts")
    if candidate["search_samples"]:
        require(stats.get("learner", {}).get("evaluations", 0) > 0, f"{name}: candidate search was not executed")
    if spec["name"] == "search_geo":
        require(stats.get("search_geo", {}).get("evaluations", 0) > 0, f"{name}: independent search was not executed")
    audited[name] = {"source": path, **summary, **search, "by_rules": groups}
require(set(audited) == set(expected), "Missing required opponent evaluations")
parity, cpu, package = read(a.parity), read(a.cpu), read(a.package)
for label, artifact in [("parity", parity), ("cpu", cpu), ("package", package)]:
    require(artifact["model_sha256"] == sha, f"{label}: wrong model hash")
require(
    parity["positions"] == (2553 if multiplayer else 427)
    and parity["all_actions_match"],
    "Checkpoint/export parity did not cover all fixtures",
)
require(
    cpu["positions"] == (2553 if multiplayer else 427) and cpu["all_moves_legal"],
    "CPU worker did not pass all legal fixtures",
)
require("8840U" in cpu.get("processor_model", ""), "CPU benchmark was not on the 8840U")
require(cpu.get("search_truncated_rollouts", 0) == 0, "CPU benchmark truncated search rollouts")
require(
    cpu["search_samples"] == candidate["search_samples"]
    and cpu.get("search_scope", "all") == candidate.get("search_scope", "all")
    and cpu["geographic_search"] == candidate["geographic_search"],
    "CPU benchmark configuration differs from final candidate",
)
require(
    package["all_hashes_match"]
    and package["files_verified"] > 0
    and (
        package.get("positions_verified") == 80
        and package.get("player_counts") == [2, 3, 4, 5, 6]
        if multiplayer
        else package["legal_fixture_responses"] == 427
    ),
    "Standalone archive verification incomplete",
)
if multiplayer:
    require(
        set(cpu.get("by_player_count", {})) == {"2", "3", "4", "5", "6"},
        "CPU benchmark missing player counts",
    )
    require(
        set(parity.get("by_player_count", {})) == {"2", "3", "4", "5", "6"}
        and parity.get("inactive_values_zero"),
        "Parity missing counts or inactive-value checks",
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
