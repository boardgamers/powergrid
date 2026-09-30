"""CPU-only checkpoint conversion; no gradient updates."""

import argparse
import json
from pathlib import Path
import torch
from model import policy_from_checkpoint
from feature_contract import embed_revision

p = argparse.ArgumentParser()
p.add_argument("checkpoint")
p.add_argument("output")
p.add_argument("--strategic-only", action="store_true")
args = p.parse_args()
torch.set_num_threads(1)
checkpoint = torch.load(args.checkpoint, map_location="cpu", weights_only=True)
strategic_only = args.strategic_only or checkpoint.get("strategic_only", False)
if args.strategic_only and checkpoint.get("architecture", "policy") != "policy":
    p.error("Strategic-only override requires a single policy")
checkpoint["strategic_only"] = strategic_only
net = policy_from_checkpoint(checkpoint).eval()
torch.onnx.export(
    net,
    (torch.zeros(1, 738), torch.zeros(1, 8, 96), torch.ones(1, 8, dtype=torch.bool)),
    args.output,
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
embed_revision(args.output, checkpoint.get("feature_revision", "3.0"))
Path(args.output + ".json").write_text(
    json.dumps(
        {"source": args.checkpoint, "strategic_only": strategic_only, "schema": 3}
    )
)
