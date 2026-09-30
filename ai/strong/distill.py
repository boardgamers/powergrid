"""HF GPU job: distill public-belief search, then measure actual playing strength."""

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
from distillation_targets import policy_targets

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
net = Policy().to(device)
train, validation = [], []
dataset_revisions = []
version = os.getenv("DATA_VERSION", "search-teacher-v1")
target_mode = os.getenv("TARGET_MODE", "hard")
assert target_mode in ["hard", "soft"]
for shard in range(int(os.getenv("SHARDS", "4"))):
    path = hf_hub_download(
        os.environ["HF_DATA_REPO"],
        f"{version}/{version}-{shard}.jsonl.gz",
        repo_type="dataset",
    )
    dataset_revisions.append({"shard": shard, "revision": Path(path).parents[1].name})
    with gzip.open(path, "rt") as source:
        for line in source:
            game = json.loads(line)
            if game["truncated"]:
                continue
            # Keep whole games together, never split positions from one game.
            target = validation if game["id"] % 5 == 0 else train
            for row in game["rows"]:
                row["state"] = np.asarray(row["state"], np.float32)
                row["actions"] = np.asarray(row["actions"], np.float32)
                target.append(row)
assert train and validation
optimizer = torch.optim.AdamW(
    net.parameters(), lr=float(os.getenv("LR", ".0003")), weight_decay=1e-4
)
metrics = []
best = -1
batchsize = int(os.getenv("BATCH_SIZE", "256"))


def export(name):
    torch.save(
        {
            "schema": 3,
            "state_dim": 738,
            "action_dim": 96,
            "state_dict": {k: v.detach().cpu() for k, v in net.state_dict().items()},
        },
        out / f"{name}.pt",
    )
    clone = copy.deepcopy(net).cpu().eval()
    torch.onnx.export(
        clone,
        (
            torch.zeros(1, 738),
            torch.zeros(1, 8, 96),
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


def validate():
    correct, disagreement_correct, disagreements, count = 0, 0, 0, 0
    with torch.no_grad():
        for k in range(0, len(validation), batchsize):
            rows = validation[k : k + batchsize]
            predicted = net(*tensors(rows, device))[0].argmax(-1).cpu().tolist()
            for row, chosen in zip(rows, predicted):
                correct += chosen == row["target"]
                count += 1
                if not row["teacherAgrees"]:
                    disagreements += 1
                    disagreement_correct += chosen == row["target"]
    return {
        "positions": count,
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
                    1.0
                    if r["teacherAgrees"]
                    else float(os.getenv("DISAGREEMENT_WEIGHT", "3"))
                    for r in rows
                ],
                device=device,
            )
            ce = -(targets * logits.log_softmax(-1)).sum(-1)
            returns = torch.tensor([r["value"] for r in rows], device=device)
            loss = (ce * weights).sum() / weights.sum() + 0.2 * (
                (value - returns) ** 2
            ).mean()
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
        for opponent in ["economic", "heuristic", "rush"]:
            result = subprocess.run(
                [
                    sys.executable,
                    "ai/strong/evaluate.py",
                    str(out / "latest.onnx"),
                    "--opponent",
                    opponent,
                    "--games",
                    "96",
                    "--workers",
                    "4",
                    "--seed",
                    "search-distill-development-v1",
                    "--output",
                    str(out / f"{opponent}.json"),
                ],
                text=True,
                capture_output=True,
                check=True,
            )
            results[opponent] = json.loads(result.stdout)
        metric["arena"] = results
        score = np.mean([r["win_rate"] for r in results.values()])
        if score > best:
            best = score
            export("best")
        metrics.append(metric)
        (out / "metrics.json").write_text(json.dumps(metrics, indent=2))
        (out / "schema.json").write_text(
            json.dumps(
                {
                    "version": 3,
                    "players": 3,
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
