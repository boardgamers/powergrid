"""Independent learners on four GPUs; each learns against a frozen-policy league."""

import os, subprocess, json

configs = [
    ("a", "0.0001", ".01", ".01"),
    ("b", "0.0003", ".01", ".01"),
    ("c", "0.0001", ".025", ".003"),
    ("d", "0.0003", ".025", ".003"),
]
processes = []
for i, (name, lr, entropy, anchor) in enumerate(configs):
    env = {
        **os.environ,
        "CUDA_VISIBLE_DEVICES": str(i),
        "RUN_NAME": "strong-league-v1-" + name,
        "TRAIN_SEED": str(201 + i),
        "LR": lr,
        "ENTROPY": entropy,
        "ANCHOR": anchor,
    }
    processes.append(
        (name, subprocess.Popen(["python", "-u", "ai/strong/train.py"], env=env))
    )
failed = []
for name, p in processes:
    code = p.wait()
    if code:
        failed.append({"learner": name, "exit": code})
print(json.dumps({"population_completed": not failed, "failures": failed}), flush=True)
if failed:
    raise SystemExit(1)
