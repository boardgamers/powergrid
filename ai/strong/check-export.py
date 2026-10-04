"""Check an exported policy against its checkpoint on real engine positions."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import numpy as np
import onnxruntime as ort
import torch
from feature_contract import METADATA_KEY
from model import policy_from_checkpoint, tensors

p = argparse.ArgumentParser()
p.add_argument("checkpoint")
p.add_argument("model")
p.add_argument("fixtures")
p.add_argument("--output", required=True)
a = p.parse_args()
torch.set_num_threads(1)
checkpoint = torch.load(a.checkpoint, map_location="cpu", weights_only=True)
net = policy_from_checkpoint(checkpoint).eval()
options = ort.SessionOptions()
options.intra_op_num_threads = 1
session = ort.InferenceSession(a.model, options, providers=["CPUExecutionProvider"])
revision = session.get_modelmeta().custom_metadata_map.get(METADATA_KEY, "3.0")
assert revision == checkpoint.get("feature_revision", "3.0")
worker = subprocess.Popen(
    ["node", str(Path(__file__).with_name("worker.cjs"))],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    text=True,
)
errors = [0.0, 0.0]
count = 0
route_counts = {}
by_count = {}
inactive_values_zero = True
try:
    for line in Path(a.fixtures).read_text().splitlines():
        request = json.loads(line)["request"]
        request["featureRevision"] = revision
        worker.stdin.write(json.dumps(request) + "\n")
        worker.stdin.flush()
        row = json.loads(worker.stdout.readline())
        assert "error" not in row, row
        inputs = tensors([row], "cpu")
        with torch.inference_mode():
            expected = [x.numpy() for x in net(*inputs)]
            if checkpoint.get("architecture") == "rule_specialists":
                options = request["state"]["options"]
                use_sealed = options.get("variant") == "recharged" and bool(
                    options.get("fastBid")
                )
                route = "recharged-sealed" if use_sealed else "default"
                route_counts[route] = route_counts.get(route, 0) + 1
                component = (
                    net.recharged_sealed_policy if use_sealed else net.default_policy
                )
                component_outputs = [x.numpy() for x in component(*inputs)]
                for selected, correct in zip(expected, component_outputs):
                    np.testing.assert_array_equal(selected, correct)
        actual = session.run(
            None, dict(zip(["state", "actions", "mask"], [x.numpy() for x in inputs]))
        )
        for i in range(2):
            errors[i] = max(errors[i], float(np.max(np.abs(expected[i] - actual[i]))))
            np.testing.assert_allclose(actual[i], expected[i], rtol=1e-4, atol=1e-5)
        n = len(request["state"]["players"])
        by_count[str(n)] = by_count.get(str(n), 0) + 1
        assert row["playerOrder"] == [(request["player"] + i) % n for i in range(n)]
        assert np.all(actual[1][:, n:] == 0)
        assert np.isfinite(actual[1]).all() and np.isclose(actual[1].sum(), 1)
        assert np.argmax(actual[0]) == np.argmax(expected[0])
        count += 1
finally:
    worker.stdin.close()
    worker.wait(timeout=10)
    worker.stdout.close()
report = {
    "positions": count,
    "by_player_count": by_count,
    "inactive_values_zero": inactive_values_zero,
    "feature_revision": revision,
    "model_sha256": hashlib.sha256(Path(a.model).read_bytes()).hexdigest(),
    "max_logit_error": errors[0],
    "max_value_error": errors[1],
    "all_actions_match": True,
    "specialist_route_counts": route_counts,
}
Path(a.output).write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report))
