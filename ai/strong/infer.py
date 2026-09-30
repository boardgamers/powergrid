"""Persistent CPU ONNX worker for schema 3 public-information states."""

import sys, json, argparse, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from infer import Model, Node

p = argparse.ArgumentParser()
p.add_argument("model")
args = p.parse_args()
model = Model(args.model)
node = Node("strong/worker.cjs")
try:
    for line in sys.stdin:
        q = {}
        try:
            obj = json.loads(line)
            if not isinstance(obj, dict):
                raise ValueError("Expected object")
            q = obj
            start = time.perf_counter()
            r = node.call(q)
            if "error" in r:
                raise ValueError(r["error"])
            index, values = model.predict(r["state"], r["actions"])
            print(
                json.dumps(
                    {
                        "requestId": q.get("requestId"),
                        "revision": q.get("revision"),
                        "move": r["moves"][index],
                        "winProbabilities": values,
                        "valueStatus": "uncalibrated-training-opponents",
                        "playerOrder": r["playerOrder"],
                        "schema": 3,
                        "modelSha256": model.sha256,
                        "elapsedMs": 1000 * (time.perf_counter() - start),
                    }
                ),
                flush=True,
            )
        except Exception as e:
            print(
                json.dumps({"requestId": q.get("requestId"), "error": str(e)}),
                flush=True,
            )
finally:
    node.close()
