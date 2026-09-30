"""Complete-episode PPO against a mixture of economic bots and self-play.
All optimization runs on HF Jobs. No unfinished episodes cross policy updates.
"""

import os, sys, json, time, random, copy
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
import torch
from torch.distributions import Categorical
from model import Policy, tensors
from pool import EnginePool
from huggingface_hub import HfApi, hf_hub_download
from feature_contract import FEATURE_REVISION, embed_revision

seed = int(os.getenv("TRAIN_SEED", "101"))
random.seed(seed)
np.random.seed(seed)
torch.manual_seed(seed)
torch.set_num_threads(2)
device = "cuda"
assert torch.cuda.is_available(), "Training must run on a GPU HF Job"
initial_checkpoint = os.getenv("INIT_CHECKPOINT")
initial_revision = os.getenv("INIT_REVISION")
checkpoint = None
if initial_checkpoint:
    if not initial_revision:
        raise ValueError("Pin INIT_REVISION when continuing a checkpoint")
    checkpoint = torch.load(
        hf_hub_download(
            os.environ["HF_MODEL_REPO"], initial_checkpoint, revision=initial_revision
        ),
        map_location="cpu",
        weights_only=True,
    )
    if checkpoint.get("feature_revision", "3.0") != FEATURE_REVISION:
        raise ValueError("Initial checkpoint requires a different feature encoder")
strategic_only = os.getenv("STRATEGIC_ONLY", "0") == "1"
net = Policy(strategic_only=strategic_only).to(device)
if checkpoint:
    net.load_state_dict(checkpoint["state_dict"])
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
rollout = EnginePool(
    workers, seed=f"strong-train-{seed}", script="ai/strong/bridge.cjs"
)
snapshots = [copy.deepcopy(net).eval()]
metrics = []
best = -1
update = -1


def save(name, export=False):
    torch.save(
        {
            "state_dim": 738,
            "action_dim": 96,
            "schema": 3,
            "feature_revision": FEATURE_REVISION,
            "strategic_only": strategic_only,
            "update": update,
            "initial_checkpoint": initial_checkpoint,
            "initial_revision": initial_revision,
            "state_dict": {k: v.detach().cpu() for k, v in net.state_dict().items()},
        },
        out / (name + ".pt"),
    )
    if export:
        clone = copy.deepcopy(net).cpu().eval()
        torch.onnx.export(
            clone,
            (
                torch.zeros(1, 738),
                torch.zeros(1, 8, 96),
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
        embed_revision(out / (name + ".onnx"))
    (out / "metrics.json").write_text(json.dumps(metrics, indent=2))
    (out / "schema.json").write_text(
        json.dumps(
            {
                "version": 3,
                "feature_revision": FEATURE_REVISION,
                "state_dim": 738,
                "action_dim": 96,
                "players": 3,
                "map": "Germany",
                "information": "all money public, sealed bids/deck/queued plans excluded",
                "run": run,
                "seed": seed,
                "initial_checkpoint": initial_checkpoint,
                "initial_revision": initial_revision,
                "strategic_only": strategic_only,
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
        for mode in ["economic", "heuristic", "rush", "legacy"]:
            current = pool.call({"op": "reset", "n": 96, "mode": mode})["observations"]
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
            result[mode] = {
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


try:
    print(
        json.dumps(
            {
                "run": run,
                "parameters": sum(p.numel() for p in net.parameters()),
                "workers": workers,
                "envs": nenv,
                "gpu": torch.cuda.get_device_name(),
            }
        ),
        flush=True,
    )
    if initial_checkpoint:
        net.eval()
        evaluation = evaluate(-1)
        metrics.append({"stage": "evaluation", "update": -1, **evaluation})
        best = float(
            np.mean([evaluation[x]["win"] for x in ["economic", "heuristic", "rush"]])
        )
        save("best", export=True)
    for update in range(updates):
        start = time.perf_counter()
        current = rollout.call(
            {"op": "reset", "n": nenv, "mode": os.getenv("OPPONENT_MODE", "mixed")}
        )["observations"]
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
            values = [[0.0, 0.0, 0.0]] * len(rows)
            roles = {r["roles"][r["seat"]] for r in rows}
            for role in roles:
                indices = [
                    j for j, r in enumerate(rows) if r["roles"][r["seat"]] == role
                ]
                actor = (
                    net
                    if role == "learner"
                    else snapshots[int(role[-1]) % len(snapshots)]
                )
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
            reply = rollout.call({"op": "step", "actions": actions})
            current = reply["observations"]
            for end in reply["ended"]:
                endings.append(end)
                if not end["truncated"]:
                    for r in pending[end["env"]]:
                        r["value"] = [
                            end["value"][(r["seat"] + j) % 3] for j in range(3)
                        ]
                        r["advantage"] = r["value"][0] - r["oldvalue"]
                        batch.append(r)
                pending[end["env"]] = []
        rollout_seconds = time.perf_counter() - start
        if not batch:
            raise RuntimeError("No completed training episodes")
        advantages = np.array([r["advantage"] for r in batch])
        mean = advantages.mean()
        std = advantages.std() + 1e-6
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
                    [(r["advantage"] - mean) / std for r in rows],
                    device=device,
                    dtype=torch.float32,
                )
                target = torch.tensor([r["value"] for r in rows], device=device)
                ratio = (dist.log_prob(act) - old).exp()
                pg = -torch.minimum(ratio * adv, ratio.clamp(0.8, 1.2) * adv).mean()
                if initial_anchor is not None:
                    with torch.no_grad():
                        anchor = initial_anchor(*x)[0].softmax(-1)
                else:
                    anchor = (x[1][:, :, 74] * 2).masked_fill(~x[2], -1e9).softmax(-1)
                kl = torch.nn.functional.kl_div(
                    logits.log_softmax(-1), anchor, reduction="batchmean"
                )
                loss = (
                    pg
                    + 0.5 * ((value - target) ** 2).mean()
                    - float(os.getenv("ENTROPY", ".01")) * dist.entropy().mean()
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
            "truncated": sum(x["truncated"] for x in endings),
            "samples": len(batch),
            "rollout_seconds": rollout_seconds,
            "seconds": time.perf_counter() - start,
            "loss": float(np.mean(losses)),
        }
        opponent_outcomes = {}
        for ending in endings:
            if ending["roles"].count("learner") != 1:
                continue
            opponent = next(r for r in ending["roles"] if r != "learner")
            group = opponent_outcomes.setdefault(
                opponent, {"games": 0, "wins": 0, "truncated": 0}
            )
            group["games"] += 1
            group["wins"] += ending["value"][ending["roles"].index("learner")]
            group["truncated"] += ending["truncated"]
        metric["training_opponents"] = opponent_outcomes
        metrics.append(metric)
        print(json.dumps(metric), flush=True)
        if update % int(os.getenv("EVAL_EVERY", "10")) == 0 or update == updates - 1:
            net.eval()
            evaluation = evaluate(update)
            metrics.append({"stage": "evaluation", "update": update, **evaluation})
            score = np.mean(
                [evaluation[x]["win"] for x in ["economic", "heuristic", "rush"]]
            )
            if score > best:
                best = score
                snapshots.append(copy.deepcopy(net).eval())
                snapshots = snapshots[-3:]
                save("best", export=True)
            save("latest", export=True)
finally:
    rollout.close()
