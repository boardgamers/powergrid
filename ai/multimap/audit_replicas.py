"""Bounded independent audit of both immutable PPO replicas (not seed selection).

Run from repository root:
    PYTHONPATH=ai/multimap ai/.venv/bin/python -B ai/multimap/audit_replicas.py

Only enumerated artifacts are fetched into the HF cache, after size inspection.
No trajectories, checkpoint copies, training, production changes, or uploads.
Legacy audit helpers are reused as pure functions; no module globals are changed.
The original pilot is rechecked for outcome/namespace and comparison consistency,
not replayed or presented as a third sample of one fixed selected policy.
"""
import argparse
from collections import defaultdict
import itertools
import json
import math
from pathlib import Path
import re
import subprocess

import numpy as np
from huggingface_hub import HfApi, hf_hub_download
from audit_ppo import (
    BOOTSTRAP_RESAMPLES, BOOTSTRAP_SEED, SELECTION_UPDATES, SOURCE_NAMES, TOLERANCE,
    check_plan_structure, digest, equal, game_key, mean, paired_confirmation,
    read_json, recompute, require, select_checkpoint, sha256, verify_games,
)

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
REPO = "coyotte508/powergrid-ai-multimap-v1"
SOURCE_REVISION = "6f5a5e01e062c6b7c6d5b4dd99dff13829620c11"
BUDGET = 128 * 1024**2  # also enforce across all three runs, not just each run
REPLICAS = (
    dict(replica=1, run="multimap-ppo-20261102-replica-1",
         job="6ae8dcabc78863f9c630e46a", revision="4a7f94fca8a2bdcbb9256c730edc83c64a5d17e9",
         source=SOURCE_REVISION),
    dict(replica=2, run="multimap-ppo-20261102-replica-2",
         job="6ae8dcb9c78863f9c630e47a", revision="af87f0b46382e4f06d420f339fd1a65a4ba9ef45",
         source=SOURCE_REVISION),
)
PILOT = dict(replica=0, run="multimap-ppo-20261102-v1",
             job="6ae8d46bc78863f9c630dd8f", revision="b1392c4dea3eb956b0e171d558f2f642c0367831",
             source="a3b492b650dec51c34b6f9322d87088b1e863f0e")


def expected_artifacts():
    names = {"status.json"} | {"ppo/" + name for name in (
        "config.json", "selection-plan.json", "confirmation-plan.json", "initial.pt",
        "best.pt", "last.pt", "history.json", "result.json",
        "confirmation-selected.json", "confirmation-teacher.json",
    )}
    names.update(f"ppo/train-{i}.json" for i in range(1, 17))
    names.update(f"ppo/selection-{i}.json" for i in SELECTION_UPDATES)
    return names


def inspect_artifacts(api, identity):
    """Validate complete allowlist and budget BEFORE any download."""
    job = api.inspect_job(job_id=identity["job"])
    require(job.status.stage == "COMPLETED", "HF job is not COMPLETED")
    environment = job.environment
    for key, value in (("RUN_ID", identity["run"]), ("MODEL_REPO", REPO), ("WORKFLOW", "ppo")):
        require(environment.get(key) == value, f"Job identity mismatch: {key}")
    require(environment.get("REPLICA", "0") == str(identity["replica"]), "Wrong job replica")
    require(not environment.get("RESUME_RUN"), "Unexpected resumed job")
    info = api.model_info(REPO, revision=identity["revision"], files_metadata=True)
    require(info.sha == identity["revision"] and info.private, "Wrong/nonprivate model revision")
    prefix = f"runs/{identity['run']}/"
    metadata = {s.rfilename[len(prefix):]: s for s in info.siblings if s.rfilename.startswith(prefix)}
    require(set(metadata) == expected_artifacts() | {"artifacts.json"}, "Unexpected/missing run artifacts")
    require(all(type(s.size) is int and 0 < s.size <= BUDGET for s in metadata.values()), "Invalid artifact size")
    total = sum(s.size for s in metadata.values())
    require(total <= BUDGET, "Artifact download budget exceeded")
    print(json.dumps(dict(stage="size-inspection", run=identity["run"], files=len(metadata), bytes=total)), flush=True)
    # Deliberately retain only public provenance fields, never job secrets.
    return dict(metadata=metadata, bytes=total, sourceRevision=environment["SOURCE_REVISION"],
                sourceSha256=environment["SOURCE_SHA256"])


def download_artifacts(identity, inspected):
    prefix = f"runs/{identity['run']}/"
    metadata = inspected["metadata"]

    def fetch(name):
        path = Path(hf_hub_download(REPO, prefix + name, revision=identity["revision"]))
        data = path.read_bytes()
        meta = metadata[name]
        require(len(data) == meta.size, f"Size mismatch: {name}")
        if meta.lfs:
            require(sha256(data) == meta.lfs.sha256, f"HF LFS SHA256 mismatch: {name}")
        else:
            blob = b"blob " + str(len(data)).encode() + b"\0" + data
            import hashlib
            require(hashlib.sha1(blob).hexdigest() == meta.blob_id, f"HF git blob mismatch: {name}")
        return path

    manifest_path = fetch("artifacts.json")
    manifest = read_json(manifest_path)
    require(set(manifest) == expected_artifacts(), "Manifest must exactly cover the allowlist")
    require(all(isinstance(v, str) and re.fullmatch(r"[0-9a-f]{64}", v) for v in manifest.values()),
            "Invalid manifest SHA256")
    files = {}
    for name in sorted(manifest):
        path = fetch(name)
        require(digest(path) == manifest[name], f"SHA256 mismatch: {name}")
        files[name] = path
    return dict(files=files, manifest=manifest, manifestSha256=digest(manifest_path),
                inspected=inspected, manifestPath=manifest_path)


def git_bytes(revision, relative):
    return subprocess.check_output(["git", "show", f"{revision}:{relative}"], cwd=ROOT)


def verify_protocol(actual, frozen, replica):
    expected = dict(frozen)
    if replica:
        expected.update(seed=frozen["seed"] + replica,
                        seedNamespace=f"{frozen['seedNamespace']}:replica-{replica}")
    equal(actual, expected, "exact frozen protocol plus only declared replica overrides")
    return {k: dict(frozen=frozen[k], actual=actual[k]) for k in frozen if actual[k] != frozen[k]}


def verify_source(config, identity):
    require(config["smoke"] is False, "Smoke run")
    require(set(config["sourceFiles"]) == set(SOURCE_NAMES), "Source manifest coverage changed")
    current_differences = {}
    for name, expected in config["sourceFiles"].items():
        require(sha256(git_bytes(identity["source"], f"ai/multimap/{name}")) == expected,
                f"Exact git source hash mismatch: {name}")
        current = digest(HERE / name)
        if current != expected:
            current_differences[name] = current
    # Replica replay must use the exact source, including Python serving helpers.
    if identity["replica"]:
        require(not current_differences, "Replica runtime/source changed")
    paths = [ROOT / "ai/core.cjs", ROOT / "ai/strong/economics.cjs"]
    paths += [HERE / n for n in ("features.cjs", "game.cjs", "teacher.cjs", "protocol.json")]
    engine = sorted((ROOT / "engine/dist").rglob("*.js"))
    require(bool(engine), "Missing engine/dist")
    paths += engine
    generator = {str(p.relative_to(ROOT)): digest(p) for p in sorted(paths)}
    generated_hash = sha256(json.dumps(generator, sort_keys=True).encode())
    require(generated_hash == config["generatorDigest"], "Generator/engine hash mismatch")
    return dict(matchingGitRevision=identity["source"], sourceFilesVerified=len(SOURCE_NAMES),
                generatorDigest=generated_hash, engineFilesVerified=len(engine),
                currentSourceDifferences=current_differences)


def independent_plan(protocol, split, update=0):
    """Reconstruct frozen deal/seat/style enumeration, independent of trainer."""
    require(split in ("train", "selection", "confirmation"), "No final/smoke seed access")
    maps = protocol["trainMaps"] + (protocol["transferMaps"] if split == "confirmation" else [])
    deals = protocol["gamesPerCellPerUpdate"] if split == "train" else protocol[split + "DealsPerCell"]
    tasks = []
    for ci, (m, n, v, f) in enumerate(itertools.product(maps, protocol["players"], protocol["variants"], protocol["fastBids"])):
        cell = f"{m}|{n}|{v}|{int(f)}"
        for deal in range(deals):
            seed = f"{protocol['seedNamespace']}:{split}:{update if split == 'train' else 0}:{cell}:{deal}"
            seats = [(ci + update - 1) % n] if split == "train" else range(n)
            style = protocol["opponentStyles"][(ci + update) % len(protocol["opponentStyles"])] if split == "train" else protocol["evaluationOpponent"]
            tasks.extend(dict(map=m, players=n, variant=v, fastBid=f, cell=cell, seed=seed,
                              split=split, deal=deal, focalSeat=seat, opponentStyle=style,
                              maxSteps=protocol["maxSteps"]) for seat in seats)
    return tasks


def verify_namespaces(runs):
    """All nine split/run sets must be disjoint, not merely different labels."""
    groups = {(run, split): seeds for run, splits in runs.items() for split, seeds in splits.items()}
    for a, b in itertools.combinations(groups, 2):
        require(not groups[a] & groups[b], f"Seed leakage: {a}/{b}")
    return dict(splitRunGroups=len(groups), pairwiseComparisons=math.comb(len(groups), 2),
                seedOverlap=0, independentDeals=sum(map(len, groups.values())),
                counts={run: {split: len(seeds) for split, seeds in splits.items()} for run, splits in runs.items()},
                note="Actual persisted game specs match independently reconstructed namespaces. Selection deals repeat intentionally across checkpoints; paired confirmation policies share deals and seats.")


def check_terminal_credits(games):
    """Persisted credits must be losses or a possible equal split among winners.

    Final player scores are not persisted, so only engine replay can establish
    the winner independently; never sum rotations that are different games.
    """
    for game in games:
        credit = game["credit"]
        require(type(credit) in (int, float) and math.isfinite(credit), "Invalid credit type/value")
        possible = [0.0] + [1 / winners for winners in range(1, game["spec"]["players"] + 1)]
        require(any(math.isclose(credit, value, rel_tol=0, abs_tol=TOLERANCE) for value in possible),
                "Credit is not a possible terminal win/tie/loss")


def verify_outcomes(bundle, identity, frozen):
    files = bundle["files"]
    config = read_json(files["ppo/config.json"])
    protocol = config["protocol"]
    differences = verify_protocol(protocol, frozen, identity["replica"])
    source = verify_source(config, identity)
    status, result, history = [read_json(files[f"{n}.json"]) for n in ("status", "ppo/result", "ppo/history")]
    require(status["run"] == identity["run"] and status["stage"] == "complete"
            and status["qualified"] is False and "error" not in status, "Incomplete/qualified/error status")
    require(status.get("replica", 0) == identity["replica"], "Status replica mismatch")
    equal(status["protocol"], protocol, "status.protocol")
    equal(status["result"], result, "status.result")
    for field in ("sourceRevision", "sourceSha256"):
        equal(status[field], bundle["inspected"][field], "job/status source provenance")
    require(result["qualified"] is False and result["trainedUpdates"] == 16, "Wrong result")
    require([r["update"] for r in history] == list(range(1, 17)), "History missing/duplicated")
    require([r["stage"] for r in status["receipts"]] ==
            [f"update-{i}" for i in range(17)] + ["confirmation-selected", "confirmation-teacher"], "Upload stage order")
    revisions = [r["revision"] for r in status["receipts"]]
    require(len(set(revisions)) == len(revisions) and all(re.fullmatch(r"[0-9a-f]{40}", r) for r in revisions), "Invalid upload revisions")
    from rollout import plans
    selection_tasks = independent_plan(protocol, "selection")
    confirmation_tasks = independent_plan(protocol, "confirmation")
    for split, tasks, count, deals in (("selection", selection_tasks, 320, 1), ("confirmation", confirmation_tasks, 960, 2)):
        require(len(tasks) == count, f"{split}: task count")
        equal(tasks, plans(split, protocol=protocol), f"runtime {split} plan")
        equal(read_json(files[f"ppo/{split}-plan.json"]), tasks, f"persisted {split} plan")
        check_plan_structure(tasks, protocol, split, deals, True)
    seeds = dict(train=set(), selection={s["seed"] for s in selection_tasks},
                 confirmation={s["seed"] for s in confirmation_tasks})
    all_games, training_scores = [], []
    for record in history:
        update = record["update"]
        tasks = independent_plan(protocol, "train", update)
        equal(tasks, plans("train", update, protocol=protocol), "runtime training plan")
        require(len(tasks) == 80, "Training task count")
        check_plan_structure(tasks, protocol, "train", 1, False)
        current_seeds = {s["seed"] for s in tasks}
        require(not seeds["train"] & current_seeds, "Repeated training deal across updates")
        seeds["train"].update(current_seeds)
        games = read_json(files[f"ppo/train-{update}.json"])["games"]
        verify_games(games, tasks, f"train-{update}")
        metrics = recompute(games)
        equal(metrics, record["training"], f"history.training-{update}")
        opt = record["optimization"]
        require(type(opt["rows"]) is int and opt["rows"] == sum(g["decisions"] for g in games)
                and 0 < opt["rows"] <= protocol["maxRolloutRows"], "Training row count")
        require(type(opt["optimizerSteps"]) is int and 0 < opt["optimizerSteps"] <=
                protocol["epochsPerUpdate"] * math.ceil(opt["rows"] / protocol["batchSize"]), "Optimizer step count")
        require(all(math.isfinite(v) for v in opt.values()) and math.isfinite(record["seconds"])
                and record["seconds"] >= 0, "Nonfinite optimization/timing")
        training_scores.append(metrics["macroCredit"])
        all_games.extend(games)
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
    best_update, best_score, candidates = select_checkpoint(selection, protocol)
    equal(best_update, result["selectedUpdate"], "Independently derived selected update")
    equal(best_score, result["selectionScore"], "selection score")
    equal(selection[0]["macroCredit"], result["baselineSelectionScore"], "baseline selection score")
    confirmation = {}
    for policy in ("selected", "teacher"):
        artifact = read_json(files[f"ppo/confirmation-{policy}.json"])
        tasks = [dict(s, focalTeacher=True) for s in confirmation_tasks] if policy == "teacher" else confirmation_tasks
        confirmation[policy] = verify_games(artifact["games"], tasks, f"confirmation-{policy}")
        metrics = recompute(artifact["games"])
        equal(metrics, artifact["summary"], f"confirmation-{policy}.summary")
        equal(metrics, result["confirmation"][policy], f"result.confirmation-{policy}")
        all_games.extend(artifact["games"])
    require(len(all_games) == 4800, "Wrong outcome count")
    check_terminal_credits(all_games)
    paired = paired_confirmation(confirmation["selected"], confirmation["teacher"], protocol)
    for policy in ("selected", "teacher"):
        equal(paired["aggregate"][policy], result["confirmation"][policy]["macroCredit"], f"paired.{policy}")
    return dict(config=config, protocol=protocol, differences=differences, source=source, status=status,
                history=history, baseline=selection[0], bestUpdate=best_update, bestScore=best_score,
                candidates=candidates, seeds=seeds, paired=paired, confirmation=confirmation,
                confirmationTasks=confirmation_tasks, trainingScores=training_scores,
                maxSteps=max(g["steps"] for g in all_games))


def stratified_standard_error(deal_differences):
    """Unbiased variance estimator of equal-cell paired mean (not unbiased SE)."""
    values = np.asarray(deal_differences, dtype=np.float64)
    require(values.ndim == 2 and values.shape[0] > 0 and values.shape[1] == 2
            and np.isfinite(values).all(), "Expected finite cell-by-two-deal differences")
    se = math.sqrt(float((values.var(axis=1, ddof=1) / 2).sum())) / len(values)
    estimate = float(values.mean())
    return dict(stratifiedPairedStandardError=se,
                pairedDifferenceApproxNormal95Interval=[estimate - 1.959963984540054 * se,
                                                        estimate + 1.959963984540054 * se])


def add_standard_errors(paired, selected, teacher, protocol):
    grouped = defaultdict(lambda: defaultdict(list))
    for key in sorted(selected):
        spec = selected[key]["spec"]
        grouped[spec["cell"]][spec["seed"]].append(selected[key]["credit"] - teacher[key]["credit"])
    cells = sorted(grouped)
    values = np.asarray([[mean(grouped[cell][seed]) for seed in sorted(grouped[cell])] for cell in cells])

    def add(target, predicate):
        indices = [i for i, cell in enumerate(cells) if predicate(cell.split("|"))]
        target.update(stratified_standard_error(values[indices]))

    add(paired["aggregate"], lambda c: True)
    for m, group in paired["byMap"].items():
        add(group, lambda c: c[0] == m)
    for n, group in paired["byPlayers"].items():
        add(group, lambda c: c[1] == n)
    add(paired["trainMaps"], lambda c: c[0] in protocol["trainMaps"])
    add(paired["transferMaps"], lambda c: c[0] in protocol["transferMaps"])
    se = math.hypot(paired["trainMaps"]["stratifiedPairedStandardError"], paired["transferMaps"]["stratifiedPairedStandardError"])
    contrast = paired["trainMinusTransferDifference"]
    contrast.update(stratifiedPairedStandardError=se, approximateNormal95Interval=[
        contrast["difference"] - 1.959963984540054 * se, contrast["difference"] + 1.959963984540054 * se])


def verify_checkpoints(bundle, checked):
    from residual import load
    import torch
    protocol, config = checked["protocol"], checked["config"]
    checkpoints, states = {}, {}
    best_model = None
    for name, update in (("initial", 0), ("best", checked["bestUpdate"]), ("last", 16)):
        model, saved = load(bundle["files"][f"ppo/{name}.pt"])
        require(saved["update"] == update and saved["schema"] == protocol["schema"], f"Wrong {name} checkpoint")
        equal(saved["config"], config, f"{name}.config")
        require(saved["bound"] == protocol["residualBound"], f"Wrong {name} bound")
        require(all(torch.isfinite(t).all().item() for t in saved["state_dict"].values()), f"Nonfinite {name} weights")
        states[name] = saved["state_dict"]
        if name == "initial":
            require(all(torch.count_nonzero(p).item() == 0 for p in model.network.action[-1].parameters()), "Initial actor not zero")
        elif name == "best":
            best_model = model
        else:
            equal(saved["history"], checked["history"], "last.history")
            equal(saved["baseline"], checked["baseline"], "last.baseline")
            equal(saved["bestScore"], checked["bestScore"], "last.bestScore")
            equal(saved["bestUpdate"], checked["bestUpdate"], "last.bestUpdate")
            best_sha = bundle["manifest"]["ppo/best.pt"]
            require(saved["bestSha256"] == best_sha and sha256(saved["bestArtifact"]) == best_sha
                    and saved["bestArtifact"] == bundle["files"]["ppo/best.pt"].read_bytes(), "Embedded best bytes mismatch")
            # Load resumable AdamW state without taking an optimizer step.
            optimizer = torch.optim.AdamW(model.parameters(), lr=protocol["learningRate"], weight_decay=protocol["weightDecay"])
            optimizer.load_state_dict(saved["optimizer"])
            require(len(optimizer.param_groups) == 1, "Unexpected optimizer groups")
            group = optimizer.param_groups[0]
            require(group["lr"] == protocol["learningRate"] and group["weight_decay"] == protocol["weightDecay"]
                    and group["betas"] == (0.9, 0.999) and group["eps"] == 1e-8 and not group["amsgrad"], "Optimizer recipe mismatch")
            parameters = list(model.parameters())
            require(len(optimizer.state) == len(parameters) and set(optimizer.state) == set(parameters), "Missing/extra optimizer state")
            steps = sum(r["optimization"]["optimizerSteps"] for r in checked["history"])
            for parameter, state in optimizer.state.items():
                require(set(state) == {"step", "exp_avg", "exp_avg_sq"}, "Unexpected AdamW state")
                require(state["step"].numel() == 1 and state["step"].item() == steps, "Optimizer/history steps mismatch")
                for field in ("exp_avg", "exp_avg_sq"):
                    tensor = state[field]
                    require(tensor.shape == parameter.shape and torch.isfinite(tensor).all().item(), "Invalid optimizer moments")
                require((state["exp_avg_sq"] >= 0).all().item(), "Negative second moment")
            rng = saved["torchRng"]
            require(rng.dtype == torch.uint8 and rng.ndim == 1, "Invalid torch RNG state")
            torch.Generator().set_state(rng)  # validate without changing global RNG
            optimizer_report = dict(loadable=True, parametersWithState=len(parameters), cumulativeSteps=steps,
                                    momentsFiniteAndShapeMatched=True, rngStateValidated=True,
                                    rngStateSha256=sha256(rng.numpy().tobytes()))
        checkpoints[name] = dict(update=update, sha256=bundle["manifest"][f"ppo/{name}.pt"])
    same = all(torch.equal(states["best"][k], states["last"][k]) for k in states["best"])
    require(same == (checked["bestUpdate"] == 16), "Unexpected best/latest weight identity")
    return checkpoints, optimizer_report, best_model, states["initial"]


def replay_sample(checked, model, workers):
    from rollout import collect
    protocol, tasks = checked["protocol"], checked["confirmationTasks"]
    sample = []
    for i, map_name in enumerate(sorted(protocol["trainMaps"] + protocol["transferMaps"])):
        for j in range(2):
            players = protocol["players"][(2 * i + j) % len(protocol["players"])]
            candidates = [s for s in tasks if s["map"] == map_name and s["players"] == players]
            sample.append(min(candidates, key=lambda s: sha256(f"ppo-audit-replay-v1|{s['seed']}|{s['focalSeat']}".encode())))
    require(len({game_key(s) for s in sample}) == 12 and {s["players"] for s in sample} == set(protocol["players"]), "Replay coverage")
    rows, games = collect(model, sample, workers=workers, training=False,
                          seed=protocol["seed"], protocol=protocol)
    require(not rows, "Evaluation generated trajectories")
    replayed = verify_games(games, sample, "replay")
    fields = ("terminal", "credit", "steps", "rounds", "decisions")
    records = []
    for task in sample:
        key = game_key(task)
        original = checked["confirmation"]["selected"][key]
        for field in fields:
            equal(replayed[key][field], original[field], f"Replay {key}.{field}")
        records.append(dict(map=task["map"], players=task["players"], seed=task["seed"], seat=task["focalSeat"],
                            credit=original["credit"], steps=original["steps"], rounds=original["rounds"], matched=True))
    return dict(games=12, workers=workers, policy="selected", matched=True, matchedFields=list(fields),
                sampling="Outcome-blind legacy SHA256 minimum per cyclic player-count group; two games per alphabetically sorted map, all five player counts.", records=records)


def replica_report(identity, bundle, checked, workers):
    checkpoints, optimizer, model, initial = verify_checkpoints(bundle, checked)
    replay = replay_sample(checked, model, workers)
    equal(verify_source(checked["config"], identity), checked["source"], "source after replay")
    add_standard_errors(checked["paired"], checked["confirmation"]["selected"], checked["confirmation"]["teacher"], checked["protocol"])
    report = dict(replica=identity["replica"], run=identity["run"], revision=identity["revision"],
                  prefix=f"runs/{identity['run']}/", jobId=identity["job"], jobStage="COMPLETED",
                  artifactManifestSha256=bundle["manifestSha256"], artifactsVerified=len(bundle["manifest"]),
                  artifactBytesIncludingManifest=bundle["inspected"]["bytes"], protocolDifferencesFromFrozenV1=checked["differences"],
                  source={**checked["source"], "hfSourceRevision": checked["status"]["sourceRevision"],
                          "hfSourceArchiveSha256": checked["status"]["sourceSha256"]}, checkpoints=checkpoints,
                  embeddedBestArtifactVerified=True, optimizer=optimizer,
                  verification=dict(outcomes=4800, terminalOutcomes=4800, failures=0, capped=0,
                                    maxObservedSteps=checked["maxSteps"], uniqueDealSeatPerBatch=True,
                                    splitIndependentDeals={k: len(v) for k, v in checked["seeds"].items()},
                                    metricAbsoluteTolerance=TOLERANCE, outcomeMetricsIndependentlyRecomputed=True),
                  training=dict(updates=16, gamesPerUpdate=80, games=1280, macroCreditByUpdate=checked["trainingScores"],
                                rolloutRows=sum(r["optimization"]["rows"] for r in checked["history"]),
                                optimizerSteps=optimizer["cumulativeSteps"]),
                  selection=dict(gamesPerCheckpoint=320, independentDeals=80, configurations=80,
                                 selectedUpdate=checked["bestUpdate"], baselineEligible=True,
                                 maxMapRegression=checked["protocol"]["selectionMaxMapRegression"], candidates=checked["candidates"]),
                  confirmation=checked["paired"], replay=replay, qualified=False)
    return report, initial


def audit(output, workers=4):
    require(1 <= workers <= 4, "Workers must be 1..4")
    frozen = json.loads(git_bytes(SOURCE_REVISION, "ai/multimap/ppo-protocol-v1.json"))
    equal(read_json(HERE / "ppo-protocol-v1.json"), frozen, "unchanged frozen protocol")
    equal(json.loads(git_bytes(PILOT["source"], "ai/multimap/ppo-protocol-v1.json")), frozen, "pilot frozen protocol")
    pilot_path = HERE / "ppo-results-v1.json"
    protected = [HERE / n for n in SOURCE_NAMES] + [HERE / "audit_ppo.py", pilot_path]
    protected_before = {str(p.relative_to(ROOT)): digest(p) for p in protected}
    api = HfApi()
    identities = [PILOT, *REPLICAS]
    inspected = {i["run"]: inspect_artifacts(api, i) for i in identities}
    total = sum(i["bytes"] for i in inspected.values())
    require(total <= BUDGET, "Combined artifact budget exceeded")
    bundles = {i["run"]: download_artifacts(i, inspected[i["run"]]) for i in identities}
    checked = {i["run"]: verify_outcomes(bundles[i["run"]], i, frozen) for i in identities}
    namespaces = verify_namespaces({run: c["seeds"] for run, c in checked.items()})
    pilot = read_json(pilot_path)
    p = checked[PILOT["run"]]
    require(pilot["repo"] == REPO and pilot["revision"] == PILOT["revision"] and pilot["qualified"] is False, "Wrong pilot report")
    equal(pilot["artifactManifestSha256"], bundles[PILOT["run"]]["manifestSha256"], "pilot manifest")
    equal(pilot["confirmation"], p["paired"], "independently rechecked pilot confirmation")
    equal(pilot["selection"]["selectedUpdate"], p["bestUpdate"], "pilot selected update")
    reports, initials = [], []
    for identity in REPLICAS:
        print(json.dumps(dict(stage="replay", run=identity["run"])), flush=True)
        report, initial = replica_report(identity, bundles[identity["run"]], checked[identity["run"]], workers)
        reports.append(report)
        initials.append(initial)
    import torch
    require(initials[0].keys() == initials[1].keys() and all(torch.equal(initials[0][k], initials[1][k]) for k in initials[0]), "Replica initial weights differ")
    add_standard_errors(p["paired"], p["confirmation"]["selected"], p["confirmation"]["teacher"], p["protocol"])
    for identity in identities:
        bundle = bundles[identity["run"]]
        require(all(digest(bundle["files"][n]) == h for n, h in bundle["manifest"].items())
                and digest(bundle["manifestPath"]) == bundle["manifestSha256"], "Cached artifacts changed during audit")
        equal(verify_source(checked[identity["run"]]["config"], identity), checked[identity["run"]]["source"], "source after all replays")
    equal({str(p.relative_to(ROOT)): digest(p) for p in protected}, protected_before, "protected source/report files unchanged")
    report = dict(
        schema="multimap-ppo-replica-audit-v1", repo=REPO,
        auditCodeSha256=digest(Path(__file__)), pureAuditHelpersSha256=digest(HERE / "audit_ppo.py"),
        frozenProtocolSha256=sha256(git_bytes(SOURCE_REVISION, "ai/multimap/ppo-protocol-v1.json")),
        storage=dict(cacheOnly=True, trajectoriesWritten=False, sizeInspectionBeforeDownload=True,
                     perRunAndCombinedByteCap=BUDGET, artifactsIncludingManifestsBytes=total,
                     originalPilotArtifactsRechecked=32, replicaArtifactsVerified=64,
                     manifestHashesAlsoCheckedAgainstImmutableHfGitBlobs=True),
        selectionRule="Zero-residual baseline participates; each map >= baseline minus 0.1; strict macro improvement >1e-12; earliest tie wins. Confirmation excluded. Updates derived, not hard-coded.",
        namespaces=namespaces, identicalReplicaInitialWeights=True, protectedSourceAndServingFilesUnchanged=True,
        replicas=reports,
        originalPilotComparison=dict(report="ai/multimap/ppo-results-v1.json", reportSha256=digest(pilot_path),
                                     revision=PILOT["revision"], selectedUpdate=p["bestUpdate"],
                                     artifactManifestSha256=bundles[PILOT["run"]]["manifestSha256"],
                                     originalOutcomesRechecked=4800, confirmation=p["paired"],
                                     interpretation="Descriptive comparison only: three separately selected policies on disjoint deal namespaces. No best-seed selection, no pooled qualified-policy estimate, no cross-run causal claim."),
        uncertainty=dict(method="Same legacy stratified paired independent-deal cluster percentile bootstrap",
                         strata="map|players|variant|fastBid", clustersPerStratum=2,
                         clusterUnit="One seed; all focal-seat rotations and both policies kept together",
                         weighting="Equal configuration and within-configuration deal weights",
                         resamples=BOOTSTRAP_RESAMPLES, seed=BOOTSTRAP_SEED, rng="numpy.PCG64",
                         intervalLevel=0.95, quantileMethod="linear", numpyVersion=np.__version__,
                         additionalEstimator="SE = sqrt(sum_c sampleVar(deal-paired-differences_c, ddof=1)/2)/numberOfCells; approximate normal interval = estimate +/- 1.959964 SE. Variance estimator is unbiased under independent deals; SE itself need not be.",
                         caveat="Only TWO independent deals per cell. Empirical within-cell bootstrap variance is half the unbiased variance estimate here and percentile intervals can be optimistic. Both methods are exploratory, conditional on these cells/opponents/selected checkpoints, with unstable cell variances and no multiplicity or selection/training uncertainty adjustment. Normal intervals are approximations, not qualification."),
        qualified=False,
        decision="Both replicas show positive aggregate held-out differences; retain all three as exploratory pilots, not qualified or production-promoted policies.",
        caveats=[
            "Each replica has 960 paired seat games but only 240 independent deal clusters; seat rotations are not independent trials. Selection reuses 80 deals across five checkpoints.",
            "Independent RNG/deal namespaces establish distinct run inputs, not a proof of statistical independence of pseudorandom outcomes; two training replicas do not characterize training-seed uncertainty.",
            "Policies play fixed economic heuristic opponents, not each other, humans, or a broad opponent population. Report all replicas; do not choose the best training seed using confirmation.",
            "Training-map/transfer-map confirmation is held out from checkpoint selection. No final-test seeds are used. Do not pool three different selected policies into one qualified policy.",
            "Hash/coverage/terminal checks cover every persisted outcome; deterministic replay covers 12 selected confirmation games per replica, not all outcomes or a rerun of training. Terminal credits outside the sample are validated structurally and reaggregated, not engine-replayed.",
            "Optimization losses cannot be independently reproduced without RAM-only trajectories. Row counts, finite/loadable optimizer moments, cumulative steps and checkpoint/history consistency are checked instead.",
            "Source-file hashes match git show at exact commits, generator matches the local frozen engine, and job/status source provenance agrees. Source archive SHA256 is recorded, not independently downloaded/rehashed; HF job logs/receipt ancestry are not a cryptographic proof of execution.",
        ])
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    temp = output.with_suffix(output.suffix + ".tmp")
    temp.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    temp.replace(output)
    print(json.dumps(dict(output=str(output), sha256=digest(output), replicas=[
        dict(replica=r["replica"], selectedUpdate=r["selection"]["selectedUpdate"],
             confirmation=r["confirmation"]["aggregate"], replays=r["replay"]["games"]) for r in reports]), indent=2))
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=HERE / "replica-results-v1.json")
    parser.add_argument("--workers", type=int, choices=range(1, 5), default=4)
    args = parser.parse_args()
    audit(args.output, args.workers)
