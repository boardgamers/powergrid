"""Explicit checkpoint transfer, no gradients; source bytes and ancestry retained."""
import argparse
import hashlib
from pathlib import Path
import torch
from model_v4_1 import transfer_from_v4, ARCHITECTURE, FEATURE_REVISION, STATE_DIM, ACTION_DIM


def main():
    p = argparse.ArgumentParser(__doc__)
    p.add_argument("source")
    p.add_argument("output")
    p.add_argument("--source-sha256", required=True)
    p.add_argument("--source-revision", required=True)
    args = p.parse_args()
    source = Path(args.source)
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    if digest != args.source_sha256:
        p.error("Source checkpoint hash mismatch")
    checkpoint = torch.load(source, map_location="cpu", weights_only=True)
    torch.set_num_threads(1)
    net = transfer_from_v4(checkpoint)
    # Do not carry old update/league/optimizer metadata into a new training run.
    artifact = dict(schema=4, architecture=ARCHITECTURE, feature_revision=FEATURE_REVISION,
                    state_dim=STATE_DIM, action_dim=ACTION_DIM, model_args={"width": net.context[0].out_features},
                    update=-1, state_dict=net.state_dict(), transfer={
                        "kind": "zero-initialized-extra-inputs", "source_revision": args.source_revision,
                        "source_sha256": digest, "source_feature_revision": checkpoint["feature_revision"],
                        "source_architecture": checkpoint["architecture"], "source_update": checkpoint.get("update"),
                        "new_parameters": ["extra_player.weight", "extra_action.weight"],
                        "trained": False})
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    torch.save(artifact, args.output)


if __name__ == "__main__":
    main()
