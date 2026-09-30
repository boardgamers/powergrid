"""HF GPU job: distill public-belief search, then measure actual playing strength."""

from collections import Counter
import copy
import gzip
import json
import os
from pathlib import Path
import random
import subprocess
import sys

import numpy as np
import torch
from huggingface_hub import HfApi, hf_hub_download

from model import Policy, tensors
from model_v4 import MultiplayerPolicy
from teacher_contract import validate_game, validation_seeds
from distillation_targets import policy_targets
from feature_contract import FEATURE_REVISION, embed_revision

multiplayer = os.getenv("ARCHITECTURE") == "multiplayer"
if multiplayer:
    FEATURE_REVISION = "4.0-multiplayer"
    if not os.getenv("DATA_REVISION"):
        raise ValueError("Pin DATA_REVISION for the multiplayer teacher dataset")
state_dim, action_dim = (1149, 98) if multiplayer else (738, 96)
player_counts = [2, 3, 4, 5, 6] if multiplayer else [3]

assert torch.cuda.is_available(), "Training must run on a GPU HF Job"
torch.set_num_threads(2)
seed = int(os.getenv("TRAIN_SEED", "310"))
random.seed(seed)
np.random.seed(seed)
torch.manual_seed(seed)
run = os.getenv("RUN_NAME", "search-distillation-v1")
out = Path("ai/runs") / run
out.mkdir(parents=True, exist_ok=True)
device = "cuda"
net = (MultiplayerPolicy() if multiplayer else Policy()).to(device)
train, validation = [], []
dataset_revisions = []
seen_games = set()
complete_games = []
version = os.getenv("DATA_VERSION", "search-teacher-v1")
target_mode = os.getenv("TARGET_MODE", "hard")
assert target_mode in ["hard", "soft"]
for shard in range(int(os.getenv("SHARDS", "4"))):
    path = hf_hub_download(
        os.environ["HF_DATA_REPO"],
        f"{version}/{version}-{shard}.jsonl.gz",
        repo_type="dataset",
        revision=os.getenv("DATA_REVISION"),
    )
    dataset_revisions.append({"shard": shard, "revision": Path(path).parents[1].name})
    with gzip.open(path, "rt") as source:
        for line in source:
            game = json.loads(line)
            if game.get("featureRevision", "3.0") != FEATURE_REVISION:
                raise ValueError(
                    "Dataset uses a different feature revision; use its archived encoder or regenerate"
                )
            if multiplayer:
                validate_game(game)
                if game["seed"] in seen_games:
                    raise ValueError("Duplicate teacher game")
                seen_games.add(game["seed"])
            if game["truncated"]:
                continue
            for row in game["rows"]:
                row["player_count"] = game.get("playerCount", 3)
                row["variant"] = game.get("variant")
                row["sealed"] = game.get("sealed")
                row["state"] = np.asarray(row["state"], np.float32)
                row["actions"] = np.asarray(row["actions"], np.float32)
            complete_games.append(game)
held_out = (
    validation_seeds(complete_games)
    if multiplayer
    else {g["seed"] for g in complete_games if g["id"] % 5 == 0}
)
for game in complete_games:
    (validation if game["seed"] in held_out else train).extend(game["rows"])
assert train and validation
count_sizes = Counter(r["player_count"] for r in train)
validation_sizes = Counter(r["player_count"] for r in validation)
if multiplayer and (
    set(count_sizes) != set(player_counts)
    or set(validation_sizes) != set(player_counts)
):
    raise ValueError("Every player count must appear in training and validation")
print(
    json.dumps(
        {
            "stage": "dataset_loaded",
            "train_counts": dict(count_sizes),
            "validation_counts": dict(validation_sizes),
        }
    ),
    flush=True,
)
optimizer = torch.optim.AdamW(
    net.parameters(), lr=float(os.getenv("LR", ".0003")), weight_decay=1e-4
)
metrics = []
best = -1
batchsize = int(os.getenv("BATCH_SIZE", "256"))


def export(name):
    torch.save(
        {
            "schema": 4 if multiplayer else 3,
            "architecture": "multiplayer" if multiplayer else "policy",
            "feature_revision": FEATURE_REVISION,
            "state_dim": state_dim,
            "action_dim": action_dim,
            "state_dict": {k: v.detach().cpu() for k, v in net.state_dict().items()},
        },
        out / f"{name}.pt",
    )
    clone = copy.deepcopy(net).cpu().eval()
    torch.onnx.export(
        clone,
        (
            torch.zeros(1, state_dim),
            torch.zeros(1, 8, action_dim),
            torch.ones(1, 8, dtype=torch.bool),
        ),
        str(out / f"{name}.onnx"),
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
    embed_revision(out / f"{name}.onnx", FEATURE_REVISION)


def validate():
    correct, disagreement_correct, disagreements, count = 0, 0, 0, 0
    by_count = {
        n: {"positions": 0, "correct": 0, "disagreements": 0, "disagreement_correct": 0}
        for n in player_counts
    }
    with torch.no_grad():
        for k in range(0, len(validation), batchsize):
            rows = validation[k : k + batchsize]
            predicted = net(*tensors(rows, device))[0].argmax(-1).cpu().tolist()
            for row, chosen in zip(rows, predicted):
                group = by_count[row["player_count"]]
                group["positions"] += 1
                group["correct"] += chosen == row["target"]
                if not row["teacherAgrees"]:
                    group["disagreements"] += 1
                    group["disagreement_correct"] += chosen == row["target"]
                correct += chosen == row["target"]
                count += 1
                if not row["teacherAgrees"]:
                    disagreements += 1
                    disagreement_correct += chosen == row["target"]
    return {
        "positions": count,
        "by_player_count": by_count,
        "accuracy": correct / count,
        "search_disagreements": disagreements,
        "disagreement_accuracy": disagreement_correct / max(1, disagreements),
    }


for epoch in range(int(os.getenv("EPOCHS", "30")) + 1):
    losses = []
    if epoch:
        net.train()
        random.shuffle(train)
        for k in range(0, len(train), batchsize):
            rows = train[k : k + batchsize]
            logits, value = net(*tensors(rows, device))
            targets = torch.from_numpy(
                policy_targets(rows, logits.shape[1], soft=target_mode == "soft")
            ).to(device)
            weights = torch.tensor(
                [
                    (
                        1.0
                        if r["teacherAgrees"]
                        else float(os.getenv("DISAGREEMENT_WEIGHT", "3"))
                    )
                    * (
                        len(train)
                        / (len(player_counts) * count_sizes[r["player_count"]])
                        if multiplayer
                        else 1.0
                    )
                    for r in rows
                ],
                device=device,
            )
            ce = -(targets * logits.log_softmax(-1)).sum(-1)
            returns = torch.tensor([r["value"] for r in rows], device=device)
            value_error = ((value - returns) ** 2).sum(-1) / torch.tensor(
                [r["player_count"] for r in rows], device=device
            )
            balance = torch.tensor(
                [
                    len(train) / (len(player_counts) * count_sizes[r["player_count"]])
                    if multiplayer
                    else 1.0
                    for r in rows
                ],
                device=device,
            )
            loss = (ce * weights).sum() / weights.sum() + 0.2 * (
                value_error * balance
            ).sum() / balance.sum()
            optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(net.parameters(), 1)
            optimizer.step()
            losses.append(float(loss.detach()))
    net.eval()
    metric = {
        "epoch": epoch,
        "loss": float(np.mean(losses)) if losses else None,
        "validation": validate(),
    }
    if epoch % 5 == 0:
        export("latest")
        results = {}
        for player_count in player_counts:
            for opponent in ["economic", "heuristic", "rush"]:
                result = subprocess.run(
                    [
                        sys.executable,
                        "ai/strong/evaluate.py",
                        str(out / "latest.onnx"),
                        "--opponent",
                        opponent,
                        "--players",
                        str(player_count),
                        "--games",
                        str(8 * player_count if multiplayer else 96),
                        "--workers",
                        "4",
                        "--seed",
                        f"multiplayer-distill-development-{player_count}-v1"
                        if multiplayer
                        else "search-distill-development-v1",
                        "--output",
                        str(out / f"{player_count}p-{opponent}.json"),
                    ],
                    text=True,
                    capture_output=True,
                    check=True,
                )
                results[f"{player_count}p/{opponent}" if multiplayer else opponent] = (
                    json.loads(result.stdout.strip().splitlines()[-1])
                )
        metric["arena"] = results
        score = np.mean(
            [
                (r["win_rate"] - 1 / r["player_count"]) / (1 - 1 / r["player_count"])
                if multiplayer
                else r["win_rate"]
                for r in results.values()
            ]
        )
        if score > best:
            best = score
            export("best")
        metrics.append(metric)
        (out / "metrics.json").write_text(json.dumps(metrics, indent=2))
        (out / "schema.json").write_text(
            json.dumps(
                {
                    "version": 4 if multiplayer else 3,
                    "feature_revision": FEATURE_REVISION,
                    "players": player_counts if multiplayer else 3,
                    "training_positions_by_count": dict(count_sizes),
                    "validation_positions_by_count": dict(validation_sizes),
                    "split": "within each count/seat/rule cell, hold out 20% of whole games ranked by sha256(seed)"
                    if multiplayer
                    else "game id modulo 5",
                    "map": "Germany",
                    "run": run,
                    "training_positions": len(train),
                    "validation_positions": len(validation),
                    "dataset_revisions": dataset_revisions,
                    "dataset_version": version,
                    "target_mode": target_mode,
                }
            )
        )
        HfApi().upload_folder(
            repo_id=os.environ["HF_MODEL_REPO"],
            folder_path=str(out),
            path_in_repo="runs/" + run,
        )
    else:
        metrics.append(metric)
    print(json.dumps(metric), flush=True)
