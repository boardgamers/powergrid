import json, sys, subprocess, argparse, time, hashlib
from pathlib import Path
import numpy as np
import onnxruntime as ort

ROOT = Path(__file__).resolve().parents[1]


class Model:
    def __init__(self, path, threads=1):
        self.sha256 = hashlib.sha256(Path(path).read_bytes()).hexdigest()
        options = ort.SessionOptions()
        options.intra_op_num_threads = threads
        options.inter_op_num_threads = 1
        self.session = ort.InferenceSession(
            str(path), sess_options=options, providers=["CPUExecutionProvider"]
        )

    def predict(self, state, actions):
        a = np.asarray(actions, dtype=np.float32)[None]
        s = np.asarray(state, dtype=np.float32)[None]
        mask = np.ones(a.shape[:2], dtype=bool)
        scores, values = self.session.run(
            None, {"state": s, "actions": a, "mask": mask}
        )
        return int(scores[0].argmax()), values[0].tolist()


class Node:
    def __init__(self, script):
        self.proc = subprocess.Popen(
            ["node", str(ROOT / "ai" / script)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
            bufsize=1,
        )

    def call(self, q):
        self.proc.stdin.write(json.dumps(q) + "\n")
        self.proc.stdin.flush()
        line = self.proc.stdout.readline()
        if not line:
            raise RuntimeError("Engine worker exited")
        return json.loads(line)

    def close(self):
        self.proc.terminate()
        self.proc.wait(timeout=5)
        self.proc.stdin.close()
        self.proc.stdout.close()


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("model")
    args = p.parse_args()
    model = Model(args.model)
    node = Node("features.cjs")
    try:
        for line in sys.stdin:
            q = {}
            try:
                decoded = json.loads(line)
                if not isinstance(decoded, dict):
                    raise ValueError("Request must be a JSON object")
                q = decoded
                begin = time.perf_counter()
                o = node.call(q)
                if "error" in o:
                    raise ValueError(o["error"])
                index, value = model.predict(o["state"], o["actions"])
                print(
                    json.dumps(
                        {
                            "requestId": q.get("requestId"),
                            "revision": q.get("revision"),
                            "move": o["moves"][index],
                            "winProbabilities": value,
                            "valueStatus": "uncalibrated-selfplay-estimate",
                            "playerOrder": o["playerOrder"],
                            "model": Path(args.model).name,
                            "modelSha256": model.sha256,
                            "elapsedMs": (time.perf_counter() - begin) * 1000,
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
