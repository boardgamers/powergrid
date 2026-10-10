"""Complete-episode PPO against a mixture of economic bots and self-play.
All optimization runs on HF Jobs. No unfinished episodes cross policy updates.
"""

import os, sys, json, time, random, copy, hashlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
import torch
from torch.distributions import Categorical
from model import Policy, tensors
from model_v4 import MultiplayerPolicy
from model_v4_1 import FivePlantPolicy
from multiplayer import ROLE_REVISIONS, rotate_outcome, balance_training_rows
from pool import EnginePool
from arena_statistics import search_summary
from snapshot_league import SnapshotLeague
from frozen_population import load_population, actor_for_role
from huggingface_hub import HfApi, hf_hub_download
from feature_contract import FEATURE_REVISION, embed_revision

architecture = os.getenv("ARCHITECTURE", "policy")
five_plants = architecture == "multiplayer_ordered_plants"
multiplayer = five_plants or architecture in ["multiplayer", "multiplayer_ordered"]
ordered_players = architecture == "multiplayer_ordered"
if multiplayer:
    FEATURE_REVISION = "4.0-multiplayer"
state_dim, action_dim = (1149, 98) if multiplayer else (738, 96)
if five_plants:
    FEATURE_REVISION = "4.1-five-plants"
    state_dim, action_dim = 1215, 100
if os.getenv("ZERO_NEW_PLANT_INPUTS") == "1":
    if not five_plants:
        raise ValueError("Input ablation requires the five-plant architecture")
    FEATURE_REVISION = "4.1-five-plants-zero-inputs"
player_counts = [2, 3, 4, 5, 6] if multiplayer else [3]
feature_revisions = dict(ROLE_REVISIONS) if multiplayer else {}
if five_plants:
    feature_revisions = {role: FEATURE_REVISION for role in ROLE_REVISIONS}
mix_player_counts = multiplayer and os.getenv("MIX_PLAYER_COUNTS") == "1"

seed = int(os.getenv("TRAIN_SEED", "101"))
random.seed(seed)
np.random.seed(seed)
torch.manual_seed(seed)
torch.set_num_threads(int(os.getenv("TORCH_THREADS", "2")))
device = os.getenv("TRAIN_DEVICE", "cuda")
if device not in ["cuda", "cpu"]:
    raise ValueError("TRAIN_DEVICE must be cuda or cpu")
if device == "cuda":
    assert torch.cuda.is_available(), "CUDA training requires a GPU HF Job"
initial_checkpoint = os.getenv("INIT_CHECKPOINT")
initial_revision = os.getenv("INIT_REVISION")
initial_sha256 = os.getenv("INIT_SHA256")
checkpoint = None
if initial_checkpoint:
    if not initial_revision:
        raise ValueError("Pin INIT_REVISION when continuing a checkpoint")
    initial_path = hf_hub_download(
        os.environ["HF_MODEL_REPO"], initial_checkpoint, revision=initial_revision
    )
    if initial_sha256 and hashlib.sha256(Path(initial_path).read_bytes()).hexdigest() != initial_sha256:
        raise ValueError("Initial checkpoint hash mismatch")
    checkpoint = torch.load(
        initial_path,
        map_location="cpu",
        weights_only=True,
    )
    if checkpoint.get("inference_only"):
        raise ValueError("Resume training from the source checkpoint, not an inference-only derivative")
    initial_feature_revision = checkpoint.get("feature_revision", "3.0")
    if initial_feature_revision != FEATURE_REVISION:
        allowed_transfer = (
            os.getenv("ALLOW_URANIUM39_TRANSFER") == "1"
            and initial_feature_revision == "3.0"
            and FEATURE_REVISION == "3.1-uranium39"
        )
        if not allowed_transfer:
            raise ValueError("Initial checkpoint requires a different feature encoder")
        print(
            json.dumps(
                {
                    "stage": "explicit_feature_transfer",
                    "from": initial_feature_revision,
                    "to": FEATURE_REVISION,
                }
            ),
            flush=True,
        )
strategic_only = (
    os.getenv(
        "STRATEGIC_ONLY",
        "1" if checkpoint and checkpoint.get("strategic_only", False) else "0",
    )
    == "1"
)
if multiplayer and strategic_only:
    raise ValueError("Strategic-only schema-3 routing cannot be used with schema 4")
net = (
    FivePlantPolicy() if five_plants else MultiplayerPolicy(ordered_players=ordered_players)
    if multiplayer
    else Policy(strategic_only=strategic_only)
).to(device)
if checkpoint:
    if five_plants and (checkpoint.get("architecture") != architecture
                       or checkpoint.get("state_dim") != state_dim or checkpoint.get("action_dim") != action_dim):
        raise ValueError("Use an explicitly transferred five-plant checkpoint")
    net.load_state_dict(checkpoint["state_dict"])
population_config = os.getenv('FROZEN_OPPONENTS')
population_mode = os.getenv('OPPONENT_MODE', 'mixed') in ['population_homogeneous', 'population_heterogeneous']
if bool(population_config) != population_mode or (population_config and not multiplayer):
    raise ValueError('Frozen population config requires a schema-4 population mode')
frozen_opponents, frozen_specs = load_population(population_config, os.environ['HF_MODEL_REPO'], device)
feature_revisions.update({spec['role']: spec['feature_revision'] for spec in frozen_specs})
initial_anchor = (
    copy.deepcopy(net).eval() if os.getenv("ANCHOR_POLICY") == "initial" else None
)
optimizer = torch.optim.AdamW(
    net.parameters(), lr=float(os.getenv("LR", "0.00015")), weight_decay=1e-5
)
run = os.getenv("RUN_NAME", "strong-smoke")
out = Path("ai/runs") / run
out.mkdir(parents=True, exist_ok=True)
workers = int(os.getenv("WORKERS", "4"))
nenv = int(os.getenv("ENVS", "64"))
batchsize = int(os.getenv("BATCH_SIZE", "512"))
updates = int(os.getenv("UPDATES", "10"))
async_rollout = os.getenv("ASYNC_ROLLOUT") == "1"
rollout_class = EnginePool
if async_rollout:
    from async_pool import AsyncEnginePool

    if workers != nenv:
        raise ValueError("Async rollout requires WORKERS == ENVS")
    rollout_class = AsyncEnginePool
league = SnapshotLeague(
    net,
    os.getenv("SNAPSHOT_ADMISSION", "best"),
    int(os.getenv("SNAPSHOT_INTERVAL", "10")),
)
rollout = rollout_class(
    workers, seed=f"strong-train-{seed}", script="ai/strong/bridge.cjs"
)
metrics = []
best = -1
update = -1


def save(name, export=False):
    torch.save(
        {
            "state_dim": state_dim,
            "action_dim": action_dim,
            "schema": 4 if multiplayer else 3,
            "architecture": architecture if multiplayer else "policy",
            "feature_revision": FEATURE_REVISION,
            "strategic_only": strategic_only,
            "update": update,
            "mixed_player_counts": mix_player_counts,
            "training_device": device,
            "async_rollout": async_rollout,
            "snapshot_admission": league.admission,
            "snapshot_interval": league.interval,
            "snapshot_updates": league.updates,
            "frozen_opponents": frozen_specs,
            "opponent_mode": os.getenv('OPPONENT_MODE', 'mixed'),
            "initial_checkpoint": initial_checkpoint,
            "initial_revision": initial_revision,
            "initial_sha256": initial_sha256,
            "initial_transfer": checkpoint.get("transfer") if checkpoint else None,
            "initial_feature_revision": checkpoint.get("feature_revision", "3.0")
            if checkpoint
            else None,
            "state_dict": {k: v.detach().cpu() for k, v in net.state_dict().items()},
        },
        out / (name + ".pt"),
    )
    if export:
        clone = copy.deepcopy(net).cpu().eval()
        torch.onnx.export(
            clone,
            (
                torch.zeros(1, state_dim),
                torch.zeros(1, 8, action_dim),
                torch.ones(1, 8, dtype=torch.bool),
            ),
            str(out / (name + ".onnx")),
            input_names=["state", "actions", "mask"],
            output_names=["logits", "value"],
            dynamic_axes={
                "state": {0: "batch"},
                "actions": {0: "batch", 1: "candidates"},
                "mask": {0: "batch", 1: "candidates"},
                "logits": {0: "batch", 1: "candidates"},
                "value": {0: "batch"},
            },
            opset_version=17,
            dynamo=False,
        )
        embed_revision(out / (name + ".onnx"), FEATURE_REVISION)
    (out / "metrics.json").write_text(json.dumps(metrics, indent=2))
    (out / "schema.json").write_text(
        json.dumps(
            {
                "version": 4 if multiplayer else 3,
                "feature_revision": FEATURE_REVISION,
                "state_dim": state_dim,
                "action_dim": action_dim,
                "players": player_counts if multiplayer else 3,
                "mixed_player_counts": mix_player_counts,
                "map": "Germany",
                "information": "all money public, sealed bids/deck/queued plans excluded",
                "run": run,
                "seed": seed,
                "initial_checkpoint": initial_checkpoint,
                "initial_revision": initial_revision,
                "initial_feature_revision": checkpoint.get("feature_revision", "3.0")
                if checkpoint
                else None,
                "strategic_only": strategic_only,
                "frozen_opponents": frozen_specs,
                "opponent_mode": os.getenv('OPPONENT_MODE', 'mixed'),
            }
        )
    )
    HfApi().upload_folder(
        repo_id=os.environ["HF_MODEL_REPO"],
        folder_path=str(out),
        path_in_repo="runs/" + run,
        ignore_patterns=["*.tmp"],
    )


def evaluate(update):
    pool = EnginePool(4, seed="strong-development-v1", script="ai/strong/bridge.cjs")
    result = {}
    try:
        for player_count in player_counts:
            for mode in ["economic", "heuristic", "rush", "legacy"]:
                current = pool.call(
                    {
                        "op": "reset",
                        "n": 8 * player_count if multiplayer else 96,
                        "mode": mode,
                        "playerCount": player_count,
                        "featureRevisions": feature_revisions,
                        **(
                            {"arenaSeed": f"multiplayer-development-{player_count}-v1"}
                            if multiplayer
                            else {}
                        ),
                    }
                )["observations"]
                ends = []
                while any(x is not None for x in current):
                    live = [i for i, x in enumerate(current) if x is not None]
                    rows = [current[i] for i in live]
                    with torch.no_grad():
                        logits, _ = net(*tensors(rows, device))
                        chosen = logits.argmax(-1).cpu().tolist()
                    actions = [None] * len(current)
                    for i, a in zip(live, chosen):
                        actions[i] = a
                    r = pool.call({"op": "step", "actions": actions})
                    current = r["observations"]
                    ends.extend(r["ended"])
                wins = [
                    sum(
                        e["value"][i]
                        for i, role in enumerate(e["roles"])
                        if role == "learner"
                    )
                    for e in ends
                ]
                result[f"{player_count}p/{mode}" if multiplayer else mode] = {
                    "player_count": player_count,
                    "by_rule": {
                        f"{variant}/{sealed}": {
                            "games": len(group),
                            "win": float(
                                np.mean(
                                    [
                                        e["value"][e["roles"].index("learner")]
                                        for e in group
                                    ]
                                )
                            ),
                        }
                        for variant in ["original", "recharged"]
                        for sealed in [False, True]
                        if (
                            group := [
                                e
                                for e in ends
                                if e["variant"] == variant and e["sealed"] == sealed
                            ]
                        )
                    },
                    "win": float(np.mean(wins)),
                    "truncated": sum(e["truncated"] for e in ends),
                    "games": len(ends),
                }
    finally:
        pool.close()
    print(
        json.dumps(
            {"stage": "evaluation", "run": run, "update": update, "results": result}
        ),
        flush=True,
    )
    return result


def selection_score(evaluation):
    if not multiplayer:
        return float(
            np.mean([evaluation[x]["win"] for x in ["economic", "heuristic", "rush"]])
        )
    return float(
        np.mean(
            [
                (v["win"] - 1 / v["player_count"]) / (1 - 1 / v["player_count"])
                for k, v in evaluation.items()
                if not k.endswith("/legacy")
            ]
        )
    )


try:
    print(
        json.dumps(
            {
                "run": run,
                "parameters": sum(p.numel() for p in net.parameters()),
                "workers": workers,
                "envs": nenv,
                "device": device,
                "torch_threads": torch.get_num_threads(),
                "async_rollout": async_rollout,
                "frozen_opponents": frozen_specs,
                "opponent_mode": os.getenv('OPPONENT_MODE', 'mixed'),
                "gpu": torch.cuda.get_device_name() if device == "cuda" else None,
            }
        ),
        flush=True,
    )
    if initial_checkpoint or multiplayer:
        net.eval()
        evaluation = evaluate(-1)
        metrics.append({"stage": "evaluation", "update": -1, **evaluation})
        best = selection_score(evaluation)
        save("best", export=True)
    for update in range(updates):
        start = time.perf_counter()
        engine_start = start
        current = rollout.call(
            {
                "op": "reset",
                "n": nenv,
                "mode": os.getenv("OPPONENT_MODE", "mixed"),
                "playerCount": player_counts[update % len(player_counts)],
                **(
                    {"playerCounts": player_counts, "offset": update * nenv}
                    if mix_player_counts
                    else {}
                ),
                "featureRevisions": feature_revisions,
            }
        )["observations"]
        engine_seconds = time.perf_counter() - engine_start
        policy_seconds = 0.0
        last_progress = time.perf_counter()
        pending = [[] for _ in range(nenv)]
        batch = []
        endings = []
        decisions = 0
        net.eval()
        while any(x is not None for x in current):
            live = [i for i, x in enumerate(current) if x is not None]
            rows = [current[i] for i in live]
            choice = [0] * len(rows)
            logps = [0.0] * len(rows)
            values = [[0.0] * (6 if multiplayer else 3)] * len(rows)
            roles = {r["roles"][r["seat"]] for r in rows}
            policy_start = time.perf_counter()
            for role in roles:
                indices = [
                    j for j, r in enumerate(rows) if r["roles"][r["seat"]] == role
                ]
                actor = actor_for_role(role, net, league, frozen_opponents)
                with torch.no_grad():
                    logits, vs = actor(*tensors([rows[j] for j in indices], device))
                    distribution = Categorical(logits=logits)
                    selected = (
                        distribution.sample()
                        if role == "learner"
                        else logits.argmax(-1)
                    )
                    logs = distribution.log_prob(selected).cpu().tolist()
                    vals = vs.cpu().tolist()
                    selected = selected.cpu().tolist()
                for j, a, lp, v in zip(indices, selected, logs, vals):
                    choice[j] = a
                    logps[j] = lp
                    values[j] = v
            policy_seconds += time.perf_counter() - policy_start
            actions = [None] * nenv
            for j, i in enumerate(live):
                actions[i] = choice[j]
                if current[i]["roles"][current[i]["seat"]] != "learner":
                    continue
                pending[i].append(
                    {
                        **current[i],
                        "choice": choice[j],
                        "oldlogp": logps[j],
                        "oldvalue": values[j][0],
                    }
                )
                decisions += 1
            engine_start = time.perf_counter()
            reply = rollout.call({"op": "step", "actions": actions})
            engine_seconds += time.perf_counter() - engine_start
            current = reply["observations"]
            for end in reply["ended"]:
                endings.append(end)
                if not end["truncated"]:
                    for r in pending[end["env"]]:
                        r["value"] = (
                            rotate_outcome(end["value"], r["seat"])
                            if multiplayer
                            else [end["value"][(r["seat"] + j) % 3] for j in range(3)]
                        )
                        r["advantage"] = r["value"][0] - r["oldvalue"]
                        batch.append(r)
                pending[end["env"]] = []
            if time.perf_counter() - last_progress >= 60:
                active = [r for r in current if r is not None]
                print(
                    json.dumps(
                        {
                            "stage": "rollout_progress",
                            "run": run,
                            "update": update,
                            "completed_games": len(endings),
                            "requested_games": nenv,
                            "decisions": decisions,
                            "unfinished_games": nenv - len(endings),
                            "ready_games": len(active),
                            "in_flight_games": nenv - len(endings) - len(active),
                            "ready_round_min": min(
                                (r["round"] for r in active), default=None
                            ),
                            "ready_round_max": max(
                                (r["round"] for r in active), default=None
                            ),
                            "engine_seconds": engine_seconds,
                            "engine_timing": "blocking_call_wall_time",
                            "async_rollout": async_rollout,
                            "policy_seconds": policy_seconds,
                            "seconds": time.perf_counter() - start,
                        }
                    ),
                    flush=True,
                )
                last_progress = time.perf_counter()
        rollout_seconds = time.perf_counter() - start
        if len(endings) != nenv or {e["env"] for e in endings} != set(range(nenv)):
            raise RuntimeError("Every training environment must finish exactly once")
        if not batch:
            raise RuntimeError("No completed training episodes")
        advantages = np.array([r["advantage"] for r in batch])
        mean = advantages.mean()
        std = advantages.std() + 1e-6
        if mix_player_counts:
            balance_training_rows(batch)
        losses = []
        net.train()
        for epoch in range(3):
            random.shuffle(batch)
            for k in range(0, len(batch), batchsize):
                rows = batch[k : k + batchsize]
                x = tensors(rows, device)
                logits, value = net(*x)
                dist = Categorical(logits=logits)
                act = torch.tensor([r["choice"] for r in rows], device=device)
                old = torch.tensor([r["oldlogp"] for r in rows], device=device)
                adv = torch.tensor(
                    [
                        r["normalized_advantage"]
                        if mix_player_counts
                        else (r["advantage"] - mean) / std
                        for r in rows
                    ],
                    device=device,
                    dtype=torch.float32,
                )
                target = torch.tensor([r["value"] for r in rows], device=device)
                ratio = (dist.log_prob(act) - old).exp()
                weights = torch.tensor(
                    [r["training_weight"] if mix_player_counts else 1.0 for r in rows],
                    device=device,
                )
                weighted_mean = lambda values: (values * weights).sum() / weights.sum()
                pg = -weighted_mean(
                    torch.minimum(ratio * adv, ratio.clamp(0.8, 1.2) * adv)
                )
                if initial_anchor is not None:
                    with torch.no_grad():
                        anchor = initial_anchor(*x)[0].softmax(-1)
                else:
                    anchor = (x[1][:, :, 74] * 2).masked_fill(~x[2], -1e9).softmax(-1)
                kl = weighted_mean(
                    torch.nn.functional.kl_div(
                        logits.log_softmax(-1), anchor, reduction="none"
                    ).sum(-1)
                )
                loss = (
                    pg
                    + 0.5
                    * (
                        weighted_mean(
                            ((value - target) ** 2).sum(-1) / x[0][:, :6].sum(-1)
                        )
                        if multiplayer
                        else ((value - target) ** 2).mean()
                    )
                    - float(os.getenv("ENTROPY", ".01")) * weighted_mean(dist.entropy())
                    + float(os.getenv("ANCHOR", ".01")) * kl
                )
                optimizer.zero_grad()
                loss.backward()
                torch.nn.utils.clip_grad_norm_(net.parameters(), 1)
                optimizer.step()
                losses.append(float(loss.detach()))
        metric = {
            "stage": "train",
            "run": run,
            "update": update,
            "episodes": len(endings),
            "player_count": "mixed"
            if mix_player_counts
            else player_counts[update % len(player_counts)],
            "by_player_count": {
                n: {
                    "episodes": sum(e["playerCount"] == n for e in endings),
                    "truncated": sum(
                        e["playerCount"] == n and e["truncated"] for e in endings
                    ),
                    "samples": sum(r["playerCount"] == n for r in batch),
                }
                for n in player_counts
            },
            "truncated": sum(x["truncated"] for x in endings),
            "samples": len(batch),
            "rollout_seconds": rollout_seconds,
            "engine_seconds": engine_seconds,
            "engine_timing": "blocking_call_wall_time",
            "async_rollout": async_rollout,
            "policy_seconds": policy_seconds,
            "seconds": time.perf_counter() - start,
            "loss": float(np.mean(losses)),
        }
        opponent_outcomes = {}
        for ending in endings:
            if ending["roles"].count("learner") != 1:
                continue
            opponents = [r for r in ending['roles'] if r != 'learner']
            opponent = opponents[0] if len(set(opponents)) == 1 else 'mixed:' + '|'.join(sorted(opponents))
            group = opponent_outcomes.setdefault(
                opponent, {"games": 0, "wins": 0, "truncated": 0}
            )
            group["games"] += 1
            group["wins"] += ending["value"][ending["roles"].index("learner")]
            group["truncated"] += ending["truncated"]
        metric["training_opponents"] = opponent_outcomes
        metric['opponent_seats'] = {role: sum(e['roles'].count(role) for e in endings)
                                    for role in sorted({r for e in endings for r in e['roles']})}
        metric["snapshot_updates"] = list(league.updates)
        if league.admission == "periodic_anchor":
            league.admit(net, update)
        metric.update(search_summary(endings))
        metrics.append(metric)
        print(json.dumps(metric), flush=True)
        if (update + int(multiplayer)) % int(
            os.getenv("EVAL_EVERY", "10")
        ) == 0 or update == updates - 1:
            net.eval()
            evaluation = evaluate(update)
            metrics.append({"stage": "evaluation", "update": update, **evaluation})
            score = selection_score(evaluation)
            if score > best:
                best = score
                if league.admission == "best":
                    league.admit(net, update, improved=True)
                save("best", export=True)
            save("latest", export=True)
finally:
    rollout.close()
