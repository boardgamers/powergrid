"""Compare transferred checkpoints and ONNX on every encoded fixture; no gradients."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import onnxruntime as ort
import torch
from model import tensors, policy_from_checkpoint
from feature_contract import METADATA_KEY

p = argparse.ArgumentParser(__doc__)
for name in ["parent", "checkpoint", "onnx", "fixtures", "output"]:
    p.add_argument(name)
a = p.parse_args()
torch.set_num_threads(1)
parent = torch.load(a.parent, map_location="cpu", weights_only=True)
checkpoint = torch.load(a.checkpoint, map_location="cpu", weights_only=True)
assert checkpoint["transfer"]["source_sha256"] == hashlib.sha256(Path(a.parent).read_bytes()).hexdigest()
assert checkpoint["transfer"]["trained"] is False
old = policy_from_checkpoint(parent).eval()
new = policy_from_checkpoint(checkpoint).eval()
for name, value in parent["state_dict"].items():
    assert torch.equal(value, checkpoint["state_dict"][name]), name
for name in checkpoint["transfer"]["new_parameters"]:
    assert torch.count_nonzero(checkpoint["state_dict"][name]).item() == 0
options = ort.SessionOptions()
options.intra_op_num_threads = 1
session = ort.InferenceSession(a.onnx, options, providers=["CPUExecutionProvider"])
assert session.get_modelmeta().custom_metadata_map[METADATA_KEY] == checkpoint["feature_revision"]
rows = [json.loads(line) for line in Path(a.fixtures).read_text().splitlines()]
errors = [0., 0.]
tests = 0
for batchsize in [1, 16]:
    for start in range(0, len(rows), batchsize):
        batch = rows[start:start + batchsize]
        old_batch = [{"state": r["state"][:1149], "actions": [v[:98] for v in r["actions"]]} for r in batch]
        inputs = tensors(batch, "cpu")
        with torch.inference_mode():
            expected = [x.numpy() for x in old(*tensors(old_batch, "cpu"))]
            transferred = [x.numpy() for x in new(*inputs)]
        actual = session.run(None, dict(zip(["state", "actions", "mask"], [v.numpy() for v in inputs])))
        for i in range(2):
            np.testing.assert_array_equal(transferred[i], expected[i])
            np.testing.assert_allclose(actual[i], expected[i], rtol=1e-4, atol=1e-5)
            errors[i] = max(errors[i], float(np.abs(actual[i] - expected[i]).max()))
        np.testing.assert_array_equal(actual[0].argmax(-1), expected[0].argmax(-1))
        for i, row in enumerate(batch):
            n = len(row["playerOrder"])
            assert np.all(actual[1][i, n:] == 0)
            assert np.isclose(actual[1][i].sum(), 1.)
            assert actual[0][i].argmax() < len(row["moves"])
        tests += len(batch)
report = dict(positions=len(rows), position_checks=tests, batch_sizes=[1, 16],
              transferred_torch_outputs_exact=True, all_actions_match=True,
              max_onnx_logit_error=errors[0], max_onnx_value_error=errors[1],
              parameters=sum(v.numel() for v in new.parameters()),
              additional_parameters=sum(v.numel() for v in new.parameters()) - sum(v.numel() for v in old.parameters()),
              hashes={key: hashlib.sha256(Path(getattr(a, key)).read_bytes()).hexdigest()
                      for key in ["parent", "checkpoint", "onnx", "fixtures"]})
Path(a.output).write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report))
