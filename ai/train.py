import os, json, random, hashlib, subprocess, time, copy
from pathlib import Path
import numpy as np
import torch
from torch import nn
from torch.distributions import Categorical

random.seed(7)
np.random.seed(7)
torch.manual_seed(7)
torch.set_num_threads(4)
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "256"))
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"


class Policy(nn.Module):
    def __init__(self, sd, ad):
        super().__init__()
        self.state = nn.Sequential(
            nn.Linear(sd, 512), nn.Tanh(), nn.Linear(512, 256), nn.Tanh()
        )
        self.action = nn.Sequential(nn.Linear(ad, 128), nn.Tanh())
        self.score = nn.Sequential(nn.Linear(384, 128), nn.Tanh(), nn.Linear(128, 1))
        self.value = nn.Linear(256, 3)

    def forward(self, state, actions, mask):
        s = self.state(state)
        a = self.action(actions)
        logits = self.score(
            torch.cat((s[:, None, :].expand(-1, a.shape[1], -1), a), -1)
        ).squeeze(-1)
        return logits.masked_fill(~mask, -1e9), self.value(s).softmax(-1)


def tensors(rows):
    states = torch.tensor(
        np.asarray([r["state"] for r in rows], dtype=np.float32), device=DEVICE
    )
    m = max(len(r["actions"]) for r in rows)
    a = np.zeros((len(rows), m, AD), np.float32)
    mask = np.zeros((len(rows), m), bool)
    for i, r in enumerate(rows):
        a[i, : len(r["actions"])] = r["actions"]
        mask[i, : len(r["actions"])] = True
    return states, torch.tensor(a, device=DEVICE), torch.tensor(mask, device=DEVICE)


def split(game):
    return int(hashlib.sha256(game.encode()).hexdigest()[:8], 16) % 5 == 0


if __name__ == "__main__":
    out = Path(os.environ.get("OUT", "ai/runs/baseline"))
    out.mkdir(parents=True, exist_ok=True)
    if not Path("dataset.jsonl").exists():
        subprocess.run(["node", "ai/generate.cjs", "dataset.jsonl"], check=True)
    rows = [json.loads(l) for l in open("dataset.jsonl")]
    SD = len(rows[0]["state"])
    AD = len(rows[0]["actions"][0])
    train = [r for r in rows if not split(r["game"])]
    valid = [r for r in rows if split(r["game"])]
    net = Policy(SD, AD).to(DEVICE)
    opt = torch.optim.Adam(net.parameters(), lr=3e-4)
    metrics = []

    def save(name):
        torch.save(
            {"state_dim": SD, "action_dim": AD, "state_dict": net.cpu().state_dict()},
            out / (name + ".pt"),
        )
        net.to(DEVICE)

    print(
        json.dumps(
            {
                "device": DEVICE,
                "training": len(train),
                "validation": len(valid),
                "parameters": sum(p.numel() for p in net.parameters()),
            }
        ),
        flush=True,
    )
    for epoch in range(int(os.getenv("BC_EPOCHS", "12"))):
        random.shuffle(train)
        net.train()
        losses = []
        for k in range(0, len(train), BATCH_SIZE):
            b = train[k : k + BATCH_SIZE]
            logits, v = net(*tensors(b))
            target = torch.tensor([r["target"] for r in b], device=DEVICE)
            value = torch.tensor([r["value"] for r in b], device=DEVICE)
            w = torch.tensor([r["weight"] for r in b], device=DEVICE)
            loss = (
                nn.functional.cross_entropy(logits, target, reduction="none") * w
            ).mean() + 0.5 * ((v - value) ** 2).mean()
            opt.zero_grad()
            loss.backward()
            nn.utils.clip_grad_norm_(net.parameters(), 1)
            opt.step()
            losses.append(loss.item())
        correct = total = 0
        vl = []
        net.eval()
        with torch.no_grad():
            for k in range(0, len(valid), 256):
                b = valid[k : k + 256]
                l, v = net(*tensors(b))
                correct += (
                    (l.argmax(-1).cpu().numpy() == [r["target"] for r in b])
                    .sum()
                    .item()
                )
                total += len(b)
                vl.append(
                    ((v.cpu().numpy() - np.array([r["value"] for r in b])) ** 2)
                    .mean()
                    .item()
                )
        entry = {
            "stage": "bc",
            "epoch": epoch,
            "loss": float(np.mean(losses)),
            "heldout_action_accuracy": correct / total,
            "heldout_value_mse": float(np.mean(vl)),
        }
        metrics.append(entry)
        print(json.dumps(entry), flush=True)
    save("imitation")
    teacher = copy.deepcopy(net).eval()
    from pool import EnginePool

    pool = EnginePool(int(os.getenv("WORKERS", "1")))
    rpc = pool.call
    nenv = int(os.getenv("ENVS", "24"))
    current = rpc({"op": "reset", "n": nenv})["observations"]
    pending = [[] for _ in range(nenv)]
    completed = 0
    for update in range(int(os.getenv("RL_UPDATES", "24"))):
        batch = []
        start = time.time()
        truncated = 0
        while len(batch) < int(os.getenv("ROLLOUT_SAMPLES", "8000")):
            with torch.no_grad():
                x = tensors(current)
                logits, v = net(*x)
                dist = Categorical(logits=logits)
                actions = dist.sample()
                logps = dist.log_prob(actions)
            for i, r in enumerate(current):
                pending[i].append(
                    {
                        **r,
                        "choice": actions[i].item(),
                        "oldlogp": logps[i].item(),
                        "oldvalue": v[i, 0].item(),
                    }
                )
            result = rpc({"op": "step", "actions": actions.tolist()})
            current = result["observations"]
            for end in result["ended"]:
                i = end["env"]
                completed += 1
                if end["truncated"]:
                    truncated += 1
                else:
                    for r in pending[i]:
                        seat = r["seat"]
                        r["value"] = [end["value"][(seat + j) % 3] for j in range(3)]
                        r["advantage"] = r["value"][0] - r["oldvalue"]
                        batch.append(r)
                pending[i] = []
        # Freeze the rollout policy during collection; never reuse unfinished episodes across updates.
        current = rpc({"op": "reset", "n": nenv})["observations"]
        pending = [[] for _ in range(nenv)]
        rollout_seconds = time.time() - start
        optimization_start = time.time()
        adv = np.array([r["advantage"] for r in batch])
        mean, std = float(adv.mean()), float(adv.std() + 1e-6)
        for epoch in range(3):
            random.shuffle(batch)
            for k in range(0, len(batch), BATCH_SIZE):
                b = batch[k : k + BATCH_SIZE]
                x = tensors(b)
                logits, v = net(*x)
                dist = Categorical(logits=logits)
                act = torch.tensor([r["choice"] for r in b], device=DEVICE)
                old = torch.tensor([r["oldlogp"] for r in b], device=DEVICE)
                advantage = torch.tensor(
                    [(r["advantage"] - mean) / std for r in b], device=DEVICE
                )
                target = torch.tensor([r["value"] for r in b], device=DEVICE)
                ratio = (dist.log_prob(act) - old).exp()
                policy = -torch.minimum(
                    ratio * advantage, ratio.clamp(0.8, 1.2) * advantage
                ).mean()
                with torch.no_grad():
                    tl, _ = teacher(*x)
                kl = nn.functional.kl_div(
                    logits.log_softmax(-1), tl.softmax(-1), reduction="batchmean"
                )
                loss = (
                    policy
                    + 0.5 * ((v - target) ** 2).mean()
                    - 0.005 * dist.entropy().mean()
                    + 0.05 * kl
                )
                opt.zero_grad()
                loss.backward()
                nn.utils.clip_grad_norm_(net.parameters(), 1)
                opt.step()
        entry = {
            "stage": "selfplay_ppo",
            "update": update,
            "episodes_total": completed,
            "truncated": truncated,
            "samples": len(batch),
            "seconds": round(time.time() - start, 2),
            "rollout_seconds": rollout_seconds,
            "optimization_seconds": time.time() - optimization_start,
        }
        metrics.append(entry)
        print(json.dumps(entry), flush=True)
        if update % 4 == 3:
            save("selfplay-" + str(update + 1))
    pool.close()
    save("selfplay")
    net.cpu().eval()
    # Export both imitation and final RL checkpoints; evaluation selects the serving model.
    for name in ["imitation", "selfplay"]:
        ck = torch.load(out / (name + ".pt"), map_location="cpu", weights_only=True)
        net.load_state_dict(ck["state_dict"])
        net.eval()
        torch.onnx.export(
            net,
            (
                torch.zeros(1, SD),
                torch.zeros(1, 8, AD),
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
    (out / "metrics.json").write_text(json.dumps(metrics, indent=2))
    (out / "schema.json").write_text(
        json.dumps(
            {
                "version": 2,
                "state_dim": SD,
                "action_dim": AD,
                "map": "Germany",
                "players": 3,
                "variants": ["original", "recharged"],
                "fastBid": [False, True],
                "money": "all players visible",
                "hidden": [
                    "seed",
                    "deck order",
                    "opponent bids when sealed",
                    "queued moves",
                ],
            },
            indent=2,
        )
    )
    if os.getenv("HF_MODEL_REPO"):
        from huggingface_hub import HfApi

        HfApi().upload_folder(
            repo_id=os.environ["HF_MODEL_REPO"],
            folder_path=str(out),
            path_in_repo="runs/" + os.environ.get("RUN_NAME", "baseline"),
        )
