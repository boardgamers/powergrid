"""Independent, bounded audit of the immutable residual-PPO v1 pilot.

Run from the repository root:
    PYTHONPATH=ai/multimap ai/.venv/bin/python ai/multimap/audit_ppo.py

Only the explicitly enumerated small artifacts are downloaded, into the HF cache.
Metric aggregation and checkpoint selection are implemented here, not imported
from training. The original source is checked with git show so later PPO fixes
do not silently redefine this pilot's protocol. No trajectories are written.
"""
import argparse
from collections import defaultdict
import hashlib
import itertools
import json
import math
from pathlib import Path
import subprocess

import numpy as np
from huggingface_hub import HfApi, hf_hub_download

REPO = "coyotte508/powergrid-ai-multimap-v1"
REVISION = "b1392c4dea3eb956b0e171d558f2f642c0367831"
PREFIX = "runs/multimap-ppo-20261102-v1/"
JOB = "6ae8d46bc78863f9c630dd8f"
SOURCE_REVISION = "a3b492b650dec51c34b6f9322d87088b1e863f0e"
ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
SELECTION_UPDATES = (0, 4, 8, 12, 16)
BOOTSTRAP_SEED = 20261102508
BOOTSTRAP_RESAMPLES = 10000
TOLERANCE = 1e-12
SOURCE_NAMES = (
    "data.py", "model.py", "features.cjs", "teacher.cjs", "game.cjs",
    "game_rl.cjs", "residual.py", "rollout.py", "ppo.py",
    "ppo-protocol-v1.json", "requirements-cpu.txt",
)


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def digest(path):
    return sha256(Path(path).read_bytes())


def read_json(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, f"Duplicate JSON key: {key}")
            result[key] = value
        return result
    return json.loads(Path(path).read_text(), object_pairs_hook=unique)


def equal(actual, expected, label="value"):
    """Structural equality, allowing only absolute floating summation error."""
    if isinstance(expected, dict):
        require(isinstance(actual, dict) and actual.keys() == expected.keys(), f"{label}: keys")
        for key in expected:
            equal(actual[key], expected[key], f"{label}.{key}")
    elif isinstance(expected, list):
        require(isinstance(actual, list) and len(actual) == len(expected), f"{label}: length")
        for i, value in enumerate(expected):
            equal(actual[i], value, f"{label}[{i}]")
    elif isinstance(expected, float):
        require(isinstance(actual, (int, float)) and math.isfinite(actual)
                and math.isclose(actual, expected, rel_tol=0, abs_tol=TOLERANCE),
                f"{label}: {actual!r} != {expected!r}")
    else:
        require(type(actual) is type(expected) and actual == expected, f"{label}: mismatch")


def mean(values):
    values = list(values)
    require(bool(values), "Empty mean")
    return math.fsum(values) / len(values)


def download_artifacts():
    api = HfApi()
    job = api.inspect_job(job_id=JOB)
    require(job.status.stage == "COMPLETED", "HF job is not COMPLETED")
    info = api.model_info(REPO, revision=REVISION, files_metadata=True)
    require(info.sha == REVISION and info.private, "Wrong or nonprivate HF repository revision")
    expected = {"status.json"} | {"ppo/" + name for name in (
        "config.json", "selection-plan.json", "confirmation-plan.json",
        "initial.pt", "best.pt", "last.pt", "history.json", "result.json",
        "confirmation-selected.json", "confirmation-teacher.json",
    )}
    expected.update(f"ppo/train-{i}.json" for i in range(1, 17))
    expected.update(f"ppo/selection-{i}.json" for i in SELECTION_UPDATES)
    metadata = {s.rfilename[len(PREFIX):]: s for s in info.siblings if s.rfilename.startswith(PREFIX)}
    require(set(metadata) == expected | {"artifacts.json"}, "Unexpected/missing run artifacts")
    total_bytes = sum(s.size for s in metadata.values())
    require(total_bytes <= 128 * 1024**2, "Artifact download budget exceeded")
    manifest_path = Path(hf_hub_download(REPO, PREFIX + "artifacts.json", revision=REVISION))
    manifest = read_json(manifest_path)
    require(set(manifest) == expected, "Artifact manifest does not cover exactly the bounded run files")
    files = {}
    for name in sorted(manifest):
        path = Path(hf_hub_download(REPO, PREFIX + name, revision=REVISION))
        require(path.stat().st_size == metadata[name].size, f"Size mismatch: {name}")
        require(digest(path) == manifest[name], f"SHA256 mismatch: {name}")
        files[name] = path
    return files, manifest, digest(manifest_path), total_bytes


def verify_source(config):
    require(config["smoke"] is False, "Smoke run is not a completed pilot")
    require(set(config["sourceFiles"]) == set(SOURCE_NAMES), "Source manifest coverage changed")
    current_differences = {}
    for name, expected in config["sourceFiles"].items():
        original = subprocess.check_output(
            ["git", "show", f"{SOURCE_REVISION}:ai/multimap/{name}"], cwd=ROOT)
        require(sha256(original) == expected, f"Frozen source hash mismatch: {name}")
        current = digest(HERE / name)
        if current != expected:
            current_differences[name] = current
    # Reconstruct the frozen generator manifest independently of data.py.
    paths = [ROOT / "ai/core.cjs", ROOT / "ai/strong/economics.cjs"]
    paths += [HERE / name for name in ("features.cjs", "game.cjs", "teacher.cjs", "protocol.json")]
    engine = sorted((ROOT / "engine/dist").rglob("*.js"))
    require(bool(engine), "Missing frozen engine/dist JavaScript")
    paths += engine
    generator = {str(p.relative_to(ROOT)): digest(p) for p in sorted(paths)}
    generated_hash = sha256(json.dumps(generator, sort_keys=True).encode())
    require(generated_hash == config["generatorDigest"], "Frozen engine/generator mismatch")
    # Python APIs can evolve; the JS replay environment and v1 protocol cannot.
    for name in ("game_rl.cjs", "ppo-protocol-v1.json", "model.py"):
        require(name not in current_differences, f"Replay dependency changed: {name}")
    return dict(matchingGitRevision=SOURCE_REVISION, sourceFilesVerified=len(SOURCE_NAMES),
                generatorDigest=generated_hash, engineFilesVerified=len(engine),
                currentSourceDifferences=current_differences,
                note="Config hashes match git-show bytes at matchingGitRevision; later Python changes do not redefine v1 selection.")


def game_key(spec):
    return spec["seed"], spec["focalSeat"]


def verify_games(games, tasks, label):
    expected = {game_key(s): s for s in tasks}
    require(len(expected) == len(tasks), f"{label}: duplicate planned deal/seat")
    actual = {}
    fields = {"spec", "terminal", "credit", "steps", "rounds", "decisions", "featureMs", "inferenceMs", "seconds"}
    for game in games:
        require(set(game) == fields, f"{label}: unexpected game fields")
        spec = game["spec"]
        key = game_key(spec)
        require(key not in actual and key in expected, f"{label}: duplicate or unplanned deal/seat {key}")
        equal(spec, expected[key], f"{label}.spec")
        require(game["terminal"] is True and math.isfinite(game["credit"])
                and 0 <= game["credit"] <= 1, f"{label}: nonterminal/invalid credit")
        require(type(game["steps"]) is int and 0 < game["steps"] < spec["maxSteps"], f"{label}: cap/invalid steps")
        require(type(game["rounds"]) is int and 0 < game["rounds"] <= game["steps"], f"{label}: invalid rounds")
        require(type(game["decisions"]) is int and 0 <= game["decisions"] <= game["steps"], f"{label}: invalid decisions")
        for field in ("featureMs", "inferenceMs", "seconds"):
            require(math.isfinite(game[field]) and game[field] >= 0, f"{label}: invalid timing")
        actual[key] = game
    require(actual.keys() == expected.keys(), f"{label}: missing games")
    return actual


def recompute(games):
    """Equal configuration weights, not an average of differently sized seats."""
    grouped = defaultdict(list)
    for game in games:
        grouped[game["spec"]["cell"]].append(game["credit"])
    cells = {key: mean(grouped[key]) for key in sorted(grouped)}
    maps = {m: mean(v for cell, v in cells.items() if cell.split("|")[0] == m)
            for m in sorted({cell.split("|")[0] for cell in cells})}
    return dict(games=len(games), failures=0, macroCredit=mean(cells.values()), cells=cells, maps=maps)


def select_checkpoint(selection, protocol):
    """Reconstruct v1 selection, including the baseline and map-regression veto."""
    baseline = selection[0]
    best_update, best_score = 0, baseline["macroCredit"]
    candidates = []
    for update in sorted(selection):
        metrics = selection[update]
        require(metrics["maps"].keys() == baseline["maps"].keys(), "Selection map coverage changed")
        map_deltas = {m: metrics["maps"][m] - baseline["maps"][m] for m in baseline["maps"]}
        eligible = metrics["failures"] == 0 and all(
            metrics["maps"][m] >= baseline["maps"][m] - protocol["selectionMaxMapRegression"]
            for m in baseline["maps"])
        if eligible and metrics["macroCredit"] > best_score + TOLERANCE:
            best_update, best_score = update, metrics["macroCredit"]
        candidates.append(dict(update=update, macroCredit=metrics["macroCredit"],
                               differenceFromBaseline=metrics["macroCredit"] - baseline["macroCredit"],
                               mapDifferencesFromBaseline=map_deltas, eligible=eligible))
    return best_update, best_score, candidates


def check_plan_structure(tasks, protocol, split, deals, all_seats):
    maps = protocol["trainMaps"] + (protocol["transferMaps"] if split == "confirmation" else [])
    cells = {f"{m}|{n}|{v}|{int(f)}" for m, n, v, f in itertools.product(
        maps, protocol["players"], protocol["variants"], protocol["fastBids"])}
    grouped = defaultdict(lambda: defaultdict(set))
    for task in tasks:
        require(task["split"] == split, "Wrong split in plan")
        grouped[task["cell"]][task["seed"]].add(task["focalSeat"])
    require(set(grouped) == cells, f"{split}: configuration coverage")
    for cell, seeds in grouped.items():
        require(len(seeds) == deals, f"{split}: independent-deal coverage")
        for seats in seeds.values():
            expected = set(range(int(cell.split("|")[1]))) if all_seats else None
            require(seats == expected if all_seats else len(seats) == 1, f"{split}: seat coverage")


def paired_confirmation(selected, teacher, protocol):
    """Two paired seed clusters per cell; all focal-seat rotations stay together."""
    require(selected.keys() == teacher.keys(), "Confirmation pairing mismatch")
    grouped = defaultdict(lambda: defaultdict(list))
    for key in sorted(selected):
        s, t = selected[key], teacher[key]
        grouped[s["spec"]["cell"]][s["spec"]["seed"]].append((s["credit"], t["credit"]))
    cells = sorted(grouped)
    require(len(cells) == 120, "Expected 120 confirmation configurations")
    clusters = []
    for cell in cells:
        deals = grouped[cell]
        require(len(deals) == 2, "Bootstrap requires exactly two independent deals per configuration")
        rows = []
        for seed in sorted(deals):
            pairs = deals[seed]
            require(len(pairs) == int(cell.split("|")[1]), "Cluster must contain every seat")
            rows.append([mean(p[i] for p in pairs) for i in (0, 1)])
        clusters.append(rows)
    values = np.asarray(clusters, dtype=np.float64)  # cell, deal, policy
    differences = values[:, :, 0] - values[:, :, 1]
    rng = np.random.Generator(np.random.PCG64(BOOTSTRAP_SEED))
    # Draw two deals WITH replacement independently within EACH configuration;
    # use identical indices for both policies, and never resample seats alone.
    draws = rng.integers(0, 2, size=(BOOTSTRAP_RESAMPLES, len(cells), 2))
    boot_cells = differences[np.arange(len(cells))[None, :, None], draws].mean(axis=2)

    def indices(predicate):
        return [i for i, cell in enumerate(cells) if predicate(cell.split("|"))]

    def group(index):
        scores = [mean(values[i, :, p].mean() for i in index) for p in (0, 1)]
        interval = np.quantile(boot_cells[:, index].mean(axis=1), [0.025, 0.975], method="linear")
        return dict(configurations=len(index), independentDeals=2 * len(index),
                    pairedSeatGames=sum(2 * int(cells[i].split("|")[1]) for i in index),
                    selected=scores[0], teacher=scores[1], difference=scores[0] - scores[1],
                    pairedDifference95PercentileInterval=interval.tolist())

    train = indices(lambda c: c[0] in protocol["trainMaps"])
    transfer = indices(lambda c: c[0] in protocol["transferMaps"])
    result = dict(aggregate=group(list(range(len(cells)))),
                  byMap={m: group(indices(lambda c: c[0] == m)) for m in sorted(protocol["trainMaps"] + protocol["transferMaps"])},
                  byPlayers={str(n): group(indices(lambda c: int(c[1]) == n)) for n in protocol["players"]},
                  trainMaps=group(train), transferMaps=group(transfer))
    contrast = boot_cells[:, train].mean(axis=1) - boot_cells[:, transfer].mean(axis=1)
    result["trainMinusTransferDifference"] = dict(
        difference=result["trainMaps"]["difference"] - result["transferMaps"]["difference"],
        percentile95Interval=np.quantile(contrast, [0.025, 0.975], method="linear").tolist(),
        note="Contrast of the two paired policy improvements, not a matched-map experiment.")
    result["seatWeightedDescriptive"] = dict(
        selected=mean(g["credit"] for g in selected.values()),
        teacher=mean(g["credit"] for g in teacher.values()))
    result["seatWeightedDescriptive"]["difference"] = (
        result["seatWeightedDescriptive"]["selected"] - result["seatWeightedDescriptive"]["teacher"])
    return result


def replay_sample(tasks, model, original, protocol, workers):
    from rollout import collect
    sample = []
    maps = sorted(protocol["trainMaps"] + protocol["transferMaps"])
    for i, map_name in enumerate(maps):
        for j in range(2):
            players = protocol["players"][(2 * i + j) % len(protocol["players"])]
            candidates = [s for s in tasks if s["map"] == map_name and s["players"] == players]
            sample.append(min(candidates, key=lambda s: sha256(
                f"ppo-audit-replay-v1|{s['seed']}|{s['focalSeat']}".encode())))
    require(len({game_key(s) for s in sample}) == 12, "Replay sample is not unique")
    require({s["players"] for s in sample} == set(protocol["players"]), "Replay player coverage")
    rows, games = collect(model, sample, workers=workers, training=False)
    require(not rows, "Evaluation replay unexpectedly produced trajectories")
    replayed = verify_games(games, sample, "replay")
    result = []
    for task in sample:
        key = game_key(task)
        for field in ("terminal", "credit", "steps", "rounds"):
            require(replayed[key][field] == original[key][field], f"Replay mismatch: {key} {field}")
        result.append(dict(seed=task["seed"], seat=task["focalSeat"],
                           credit=original[key]["credit"], steps=original[key]["steps"],
                           rounds=original[key]["rounds"], matched=True))
    return dict(games=12, workers=workers, policy="selected", matched=True,
                sampling="Outcome-blind SHA256 minimum per cyclic player-count group; two games per alphabetically sorted map, all five player counts.",
                records=result)


def audit(output, workers=4):
    require(1 <= workers <= 4, "Replay workers must be in 1..4")
    files, manifest, manifest_sha, total_bytes = download_artifacts()
    config = read_json(files["ppo/config.json"])
    source = verify_source(config)
    protocol = config["protocol"]
    from residual import PROTOCOL, load
    from rollout import plans
    import torch
    equal(PROTOCOL, protocol, "runtime v1 protocol")
    require(protocol["updates"] == 16 and protocol["selectionEvery"] == 4
            and protocol["selectionMaxMapRegression"] == 0.1, "Unexpected v1 selection protocol")
    status = read_json(files["status.json"])
    result = read_json(files["ppo/result.json"])
    history = read_json(files["ppo/history.json"])
    require(status["run"] == "multimap-ppo-20261102-v1" and status["stage"] == "complete"
            and status["qualified"] is False and "error" not in status, "Run status is not complete/unqualified")
    equal(status["protocol"], protocol, "status.protocol")
    equal(status["result"], result, "status.result")
    require(result["qualified"] is False and result["trainedUpdates"] == 16, "Unexpected pilot result")
    require([r["update"] for r in history] == list(range(1, 17)), "History is incomplete/duplicated")
    require([r["stage"] for r in status["receipts"]] ==
            [f"update-{i}" for i in range(17)] + ["confirmation-selected", "confirmation-teacher"],
            "Selection/confirmation upload order mismatch")

    selection_tasks = plans("selection")
    confirmation_tasks = plans("confirmation")
    equal(read_json(files["ppo/selection-plan.json"]), selection_tasks, "selection plan")
    equal(read_json(files["ppo/confirmation-plan.json"]), confirmation_tasks, "confirmation plan")
    require(len(selection_tasks) == 320 and len(confirmation_tasks) == 960, "Evaluation task counts")
    check_plan_structure(selection_tasks, protocol, "selection", 1, True)
    check_plan_structure(confirmation_tasks, protocol, "confirmation", 2, True)
    seeds = {"train": set(), "selection": {s["seed"] for s in selection_tasks},
             "confirmation": {s["seed"] for s in confirmation_tasks}}
    all_games = []
    training_scores = []
    for record in history:
        update = record["update"]
        tasks = plans("train", update)
        require(len(tasks) == 80, f"Training task count at update {update}")
        check_plan_structure(tasks, protocol, "train", 1, False)
        current_seeds = {s["seed"] for s in tasks}
        require(not seeds["train"] & current_seeds, "Training deal repeated across updates")
        seeds["train"].update(current_seeds)
        games = read_json(files[f"ppo/train-{update}.json"])["games"]
        verify_games(games, tasks, f"train-{update}")
        metrics = recompute(games)
        equal(metrics, record["training"], f"history.training-{update}")
        optimization = record["optimization"]
        require(optimization["rows"] == sum(g["decisions"] for g in games)
                and 0 < optimization["rows"] <= protocol["maxRolloutRows"], "Training row count mismatch")
        require(optimization["optimizerSteps"] > 0 and all(math.isfinite(v) for v in optimization.values()),
                "Invalid optimization metrics")
        training_scores.append(metrics["macroCredit"])
        all_games.extend(games)
    for a, b in itertools.combinations(seeds, 2):
        require(not seeds[a] & seeds[b], f"Seed leakage: {a}/{b}")

    selection = {}
    for update in SELECTION_UPDATES:
        artifact = read_json(files[f"ppo/selection-{update}.json"])
        verify_games(artifact["games"], selection_tasks, f"selection-{update}")
        metrics = recompute(artifact["games"])
        equal(metrics, artifact["summary"], f"selection-{update}.summary")
        if update:
            equal(metrics, history[update - 1]["selection"], f"history.selection-{update}")
        selection[update] = metrics
        all_games.extend(artifact["games"])
    require(all(("selection" in r) == (r["update"] in SELECTION_UPDATES) for r in history), "Unexpected selection rounds")
    baseline = selection[0]
    best_update, best_score, candidates = select_checkpoint(selection, protocol)
    require(best_update == result["selectedUpdate"] == 8, "Incorrect selected checkpoint")
    equal(best_score, result["selectionScore"], "selection score")
    equal(baseline["macroCredit"], result["baselineSelectionScore"], "baseline selection score")

    checkpoints = {}
    selected_model = None
    for name, update in (("initial", 0), ("best", 8), ("last", 16)):
        model, saved = load(files[f"ppo/{name}.pt"])
        require(saved["update"] == update and saved["schema"] == protocol["schema"], f"Wrong {name} checkpoint")
        equal(saved["config"], config, f"{name}.config")
        require(saved["bound"] == protocol["residualBound"], f"Wrong {name} residual bound")
        require(all(torch.isfinite(t).all().item() for t in saved["state_dict"].values()), f"Nonfinite {name} weights")
        if name == "initial":
            require(all(torch.count_nonzero(p).item() == 0 for p in model.network.action[-1].parameters()),
                    "Baseline checkpoint does not have a zero residual actor")
        if name == "best":
            selected_model = model
        if name == "last":
            require(saved["bestUpdate"] == best_update, "last.pt bestUpdate mismatch")
            equal(saved["bestScore"], best_score, "last.bestScore")
            equal(saved["baseline"], baseline, "last.baseline")
            equal(saved["history"], history, "last.history")
            require(saved["bestSha256"] == manifest["ppo/best.pt"]
                    and sha256(saved["bestArtifact"]) == manifest["ppo/best.pt"]
                    and saved["bestArtifact"] == files["ppo/best.pt"].read_bytes(), "Embedded best artifact mismatch")
            require(bool(saved["optimizer"]["state"]) and saved["torchRng"].dtype == torch.uint8,
                    "Missing resumable optimizer/RNG state")
        checkpoints[name] = dict(update=update, sha256=manifest[f"ppo/{name}.pt"])

    confirmation = {}
    for policy in ("selected", "teacher"):
        artifact = read_json(files[f"ppo/confirmation-{policy}.json"])
        tasks = [dict(s, focalTeacher=True) for s in confirmation_tasks] if policy == "teacher" else confirmation_tasks
        confirmation[policy] = verify_games(artifact["games"], tasks, f"confirmation-{policy}")
        metrics = recompute(artifact["games"])
        equal(metrics, artifact["summary"], f"confirmation-{policy}.summary")
        equal(metrics, result["confirmation"][policy], f"result.confirmation-{policy}")
        all_games.extend(artifact["games"])
    paired = paired_confirmation(confirmation["selected"], confirmation["teacher"], protocol)
    for policy in ("selected", "teacher"):
        equal(paired["aggregate"][policy], result["confirmation"][policy]["macroCredit"], f"paired.{policy}")
    replay = replay_sample(confirmation_tasks, selected_model, confirmation["selected"], protocol, workers)
    # Recheck frozen replay dependencies after the run, in case the tree was edited.
    source_after = verify_source(config)
    require(source_after["generatorDigest"] == source["generatorDigest"], "Generator changed during replay")
    source = source_after
    require(len(all_games) == 4800, "Unexpected total audited outcomes")
    report = dict(
        schema="multimap-ppo-audit-v1", repo=REPO, revision=REVISION, prefix=PREFIX,
        jobId=JOB, jobStage="COMPLETED", artifactManifestSha256=manifest_sha,
        artifactsVerified=len(manifest), downloadedArtifactBytes=total_bytes,
        checkpoints=checkpoints, embeddedBestArtifactVerified=True,
        source={**source, "hfSourceRevision": status["sourceRevision"], "hfSourceArchiveSha256": status["sourceSha256"]},
        verification=dict(outcomes=4800, terminalOutcomes=4800, failures=0, capped=0,
                          maxObservedSteps=max(g["steps"] for g in all_games),
                          uniqueDealSeatPerBatch=True, splitSeedOverlap=0,
                          splitIndependentDeals={k: len(v) for k, v in seeds.items()},
                          metricAbsoluteTolerance=TOLERANCE, outcomeMetricsIndependentlyRecomputed=True),
        training=dict(updates=16, gamesPerUpdate=80, games=1280,
                      macroCreditByUpdate=training_scores,
                      rolloutRows=sum(r["optimization"]["rows"] for r in history),
                      optimizerSteps=sum(r["optimization"]["optimizerSteps"] for r in history),
                      elapsedUpdateSeconds=math.fsum(r["seconds"] for r in history)),
        selection=dict(gamesPerCheckpoint=320, independentDeals=80, configurations=80,
                       selectedUpdate=best_update, baselineEligible=True,
                       maxMapRegression=protocol["selectionMaxMapRegression"],
                       rule="v1: zero-residual baseline participates; each map >= baseline minus 0.1; strict macro improvement >1e-12; earliest tie wins; confirmation excluded.",
                       candidates=candidates),
        confirmation=paired,
        uncertainty=dict(method="Stratified paired independent-deal cluster percentile bootstrap",
                         strata="map|players|variant|fastBid", clustersPerStratum=2,
                         clusterUnit="One seed, with all focal seats and both policies kept together",
                         weighting="Equal configuration weight; equal deal weight within configuration",
                         resamples=BOOTSTRAP_RESAMPLES, seed=BOOTSTRAP_SEED, rng="numpy.PCG64",
                         intervalLevel=0.95, quantileMethod="linear", numpyVersion=np.__version__,
                         caveat="Only two independent deals per cell: within-cell variance is poorly estimated. Intervals are exploratory, conditional on these configurations/opponents and this selected checkpoint; no multiple-comparison or selection-uncertainty adjustment. Seats are not independent extra deals."),
        replay=replay, qualified=False,
        decision="Promising exploratory aggregate improvement, with map regressions; retain as a pilot, not a qualified or production-promoted policy.",
        caveats=[
            "960 paired seat games are 240 independent deal clusters, not 960 independent trials; selection reuses only 80 deals across checkpoints.",
            "Selected and geographic teacher focal policies face fixed economic heuristic opponents; this is not head-to-head play or evidence of human-level strength.",
            "Training-map and transfer-map confirmation were not used for checkpoint selection. No final-test seeds were consumed.",
            "Hash verification and terminal-outcome checks cover all persisted outcomes, but deterministic engine replay covers only 12 selected games, not every game or the training run.",
            "Optimization losses cannot be independently recomputed without RAM-only trajectories; row counts and checkpoint/history consistency are checked instead.",
            "The HF source archive hash is recorded provenance, not a downloaded/rehashed archive; config source-file hashes and the frozen local engine generator were verified independently.",
        ])
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    temp = output.with_suffix(output.suffix + ".tmp")
    temp.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    temp.replace(output)
    print(json.dumps(dict(output=str(output), artifactsVerified=len(manifest), outcomes=4800,
                          selectedUpdate=best_update, confirmation=paired["aggregate"], replays=12), indent=2))
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=HERE / "ppo-results-v1.json")
    parser.add_argument("--workers", type=int, choices=range(1, 5), default=4)
    args = parser.parse_args()
    audit(args.output, args.workers)
