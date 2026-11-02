"""Bounded graph-policy bootstrap. Best epoch selected on in-map validation only."""
import argparse
import json
from pathlib import Path
import random
import time

import numpy as np
import torch
from torch.nn import functional as F
from torch.utils.data import DataLoader

from data import atomic_json, read_games, PROTOCOL, audit_splits, digest
from model import GraphPolicy, SCHEMA, tensor_row, collate


def load_rows(directory, exclude=()):
    rows, metadata = [], []
    for game in read_games(directory):
        relations = torch.tensor(game["relations"], dtype=torch.float32)
        for row in game["rows"]:
            if row['fingerprint'] in exclude:
                continue
            rows.append(tensor_row(row, relations))
            metadata.append({"cell": game["spec"]["cell"], "phase": row["phase"],
                             "seed": game["spec"]["seed"], "fingerprint": row["fingerprint"]})
    return rows, metadata


@torch.no_grad()
def evaluate(model, rows, metadata, device, batch_size=128):
    model.eval()
    totals = {}
    offset = 0
    for batch in DataLoader(rows, batch_size=batch_size, collate_fn=collate):
        batch = {k: v.to(device) for k, v in batch.items()}
        logits, value = model(batch)
        ce = -(batch["targets"] * F.log_softmax(logits, -1)).sum(-1)
        correct = batch["targets"].gather(1, logits.argmax(-1).unsqueeze(-1)).squeeze(-1) > 0
        mse = (value.sigmoid() - batch["value"]).square()
        for i, (loss, hit, error) in enumerate(zip(ce.tolist(), correct.tolist(), mse.tolist())):
            meta = metadata[offset + i]
            for key in ("all", "cell:" + meta["cell"], "phase:" + meta["phase"]):
                v = totals.setdefault(key, {"count": 0, "policyLoss": 0, "agreement": 0, "valueMSE": 0})
                v["count"] += 1
                v["policyLoss"] += loss
                v["agreement"] += hit
                v["valueMSE"] += error
        offset += len(ce)
    for row in totals.values():
        for key in ("policyLoss", "agreement", "valueMSE"):
            row[key] /= row["count"]
    cells = [v for k, v in totals.items() if k.startswith("cell:")]
    totals["macroCellPolicyLoss"] = sum(v["policyLoss"] for v in cells) / len(cells)
    return totals


def train(data, output, epochs=20, seed=508, width=64, device=None, batch_size=64, checkpoint_callback=None):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.set_num_threads(4)
    device = device or ("cuda" if torch.cuda.is_available() else "cpu")
    if device == "cuda":
        torch.cuda.manual_seed_all(seed)
    audit = audit_splits(data)
    excluded = set(json.loads((Path(data)/'excluded-train-fingerprints.json').read_text()))
    train_rows, train_meta = load_rows(Path(data) / "train", excluded)
    val_rows, val_meta = load_rows(Path(data) / "validation")
    if {r["seed"] for r in train_meta} & {r["seed"] for r in val_meta}:
        raise RuntimeError("Train/validation deal leak")
    if {r["fingerprint"] for r in train_meta} & {r["fingerprint"] for r in val_meta}:
        raise RuntimeError("Train/validation duplicate feature leak")
    model = GraphPolicy(width).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=3e-4, weight_decay=1e-3)
    generator = torch.Generator().manual_seed(seed)
    loader = DataLoader(train_rows, batch_size=batch_size, shuffle=True, collate_fn=collate,
                        generator=generator)
    config = dict(schema=SCHEMA, seed=seed, width=width, device=device, epochs=epochs,
                  batchSize=batch_size, trainRows=len(train_rows), validationRows=len(val_rows),
                  parameters=sum(p.numel() for p in model.parameters()), protocol=PROTOCOL, splitAudit=audit,
                  dataManifests={s:digest(Path(data)/s/'manifest.json') for s in ('train','validation','transfer')},
                  objective="teacher-policy CE + 0.1 terminal-credit BCE; not calibrated values")
    history = []
    best = float("inf")
    first_epoch = 0
    if (output / "last.pt").exists():
        previous = torch.load(output / "last.pt", map_location=device, weights_only=True)
        if previous["config"] != config:
            raise RuntimeError('Resume configuration changed; use a new run')
        model.load_state_dict(previous["state_dict"])
        optimizer.load_state_dict(previous["optimizer"])
        generator.set_state(previous["generatorState"].cpu())
        torch.set_rng_state(previous["torchState"].cpu())
        history = previous["history"]
        first_epoch = previous["epoch"] + 1
        history = [r for r in history if r["epoch"] < first_epoch]
        best = min(r["validation"]["macroCellPolicyLoss"] for r in history)
    atomic_json(output / "config.json", config)
    started = time.monotonic()
    for epoch in range(first_epoch, epochs):
        model.train()
        total, count = 0, 0
        for batch in loader:
            batch = {k: v.to(device) for k, v in batch.items()}
            optimizer.zero_grad(set_to_none=True)
            logits, value = model(batch)
            policy_loss = -(batch["targets"] * F.log_softmax(logits, -1)).sum(-1).mean()
            value_loss = F.binary_cross_entropy_with_logits(value, batch["value"])
            loss = policy_loss + .1 * value_loss
            if not torch.isfinite(loss):
                raise RuntimeError("Nonfinite training loss")
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.)
            optimizer.step()
            total += policy_loss.item() * len(value)
            count += len(value)
        metrics = evaluate(model, val_rows, val_meta, device)
        score = metrics["macroCellPolicyLoss"]
        record = dict(epoch=epoch, trainPolicyLoss=total/count, validation=metrics,
                      elapsedSeconds=time.monotonic()-started)
        history.append(record)
        checkpoint = dict(schema=SCHEMA, width=width, state_dict={k:v.cpu() for k,v in model.state_dict().items()},
                          epoch=epoch, seed=seed, config=config, optimizer=optimizer.state_dict(),
                          generatorState=generator.get_state(), torchState=torch.get_rng_state(), history=history)
        tmp = output / "last.tmp"
        torch.save(checkpoint, tmp)
        if score < best:
            best = score
            torch.save(checkpoint, output / "best.tmp")
            (output / "best.tmp").replace(output / "best.pt")
        tmp.replace(output / "last.pt")
        atomic_json(output / "history.json", history)
        if checkpoint_callback and (epoch == 0 or (epoch + 1) % 5 == 0):
            checkpoint_callback(epoch)
        print(json.dumps(dict(stage="training", epoch=epoch, trainPolicyLoss=total/count,
                              validationPolicyLoss=score, agreement=metrics["all"]["agreement"],
                              seconds=round(time.monotonic()-started))), flush=True)
    # Transfer outcomes are evaluated once, after selection is irrevocably fixed.
    selected = torch.load(output / "best.pt", map_location="cpu", weights_only=True)
    model.load_state_dict(selected["state_dict"])
    del train_rows, train_meta, loader
    transfer_rows, transfer_meta = load_rows(Path(data) / "transfer")
    transfer = evaluate(model, transfer_rows, transfer_meta, device)
    atomic_json(output / "transfer.json", {"selectedEpoch":selected["epoch"], "metrics":transfer,
                                          "usedForSelection":False})
    print(json.dumps(dict(stage="trained", selectedEpoch=selected["epoch"],
                          transferAgreement=transfer["all"]["agreement"])), flush=True)
    return selected["epoch"]


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--data", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--epochs", type=int, default=20)
    p.add_argument("--seed", type=int, default=508)
    p.add_argument("--device", choices=["cpu", "cuda"])
    args = p.parse_args()
    train(args.data, args.output, args.epochs, args.seed, device=args.device)
