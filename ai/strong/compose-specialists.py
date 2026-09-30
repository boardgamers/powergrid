"""CPU-only composition of frozen specialists; no training or gradients."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import torch
from model import RuleSpecialists, policy_from_checkpoint
from feature_contract import FEATURE_REVISION

p = argparse.ArgumentParser()
p.add_argument("default_checkpoint")
p.add_argument("sealed_checkpoint")
p.add_argument("output")
p.add_argument("--default-revision", required=True)
p.add_argument("--sealed-revision", required=True)
p.add_argument("--allow-uranium39-transfer", action="store_true")
a = p.parse_args()
torch.set_num_threads(1)
components = []
checkpoints = []
for path, revision in [
    (a.default_checkpoint, a.default_revision),
    (a.sealed_checkpoint, a.sealed_revision),
]:
    ck = torch.load(path, map_location="cpu", weights_only=True)
    source_features = ck.get("feature_revision", "3.0")
    if source_features != FEATURE_REVISION and not (
        source_features == "3.0" and a.allow_uranium39_transfer
    ):
        raise ValueError(
            "Explicit authorization required for 3.0 to corrected-feature transfer"
        )
    assert ck.get("architecture", "policy") == "policy"
    checkpoints.append(ck)
    components.append(
        {
            "checkpoint_sha256": hashlib.sha256(Path(path).read_bytes()).hexdigest(),
            "repository_revision": revision,
            "source_feature_revision": source_features,
            "input_feature_revision": FEATURE_REVISION,
        }
    )
args = {
    "default_strategic_only": checkpoints[0].get("strategic_only", False),
    "sealed_strategic_only": checkpoints[1].get("strategic_only", False),
}
net = RuleSpecialists(**args).eval()
net.default_policy.load_state_dict(policy_from_checkpoint(checkpoints[0]).state_dict())
net.recharged_sealed_policy.load_state_dict(
    policy_from_checkpoint(checkpoints[1]).state_dict()
)
out = Path(a.output)
out.mkdir(parents=True, exist_ok=False)
checkpoint = {
    "architecture": "rule_specialists",
    "model_args": args,
    "schema": 3,
    "state_dim": 738,
    "action_dim": 96,
    "feature_revision": FEATURE_REVISION,
    "components": components,
    "state_dict": net.state_dict(),
}
torch.save(checkpoint, out / "specialists.pt")
(out / "composition.json").write_text(
    json.dumps(
        {
            "architecture": "rule_specialists",
            "default": "corrected A260 refinement update 40",
            "recharged_sealed": "B160 weights with explicit uranium-feature correction",
            "training": "none; frozen-weight composition",
            "components": components,
        },
        indent=2,
    )
    + "\n"
)
subprocess.run(
    [
        sys.executable,
        str(Path(__file__).with_name("export.py")),
        str(out / "specialists.pt"),
        str(out / "specialists.onnx"),
    ],
    check=True,
)
print(
    json.dumps(
        {
            "model": str(out / "specialists.onnx"),
            "sha256": hashlib.sha256(
                (out / "specialists.onnx").read_bytes()
            ).hexdigest(),
        }
    )
)
