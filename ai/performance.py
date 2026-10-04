"""Run on HF Jobs: profile real engine rollouts, GPU batches and ONNX parity."""

import concurrent.futures, json, os, subprocess, time
from pathlib import Path
import numpy as np
import torch
import onnxruntime as ort
from huggingface_hub import hf_hub_download, HfApi
import train

repo = "coyotte508/powergrid-ai-germany-v1"
ck = torch.load(
    hf_hub_download(repo, "runs/baseline-v1/imitation.pt"),
    map_location="cpu",
    weights_only=True,
)
train.AD = ck["action_dim"]
net = train.Policy(ck["state_dim"], train.AD).cuda().eval()
net.load_state_dict(ck["state_dict"])


class Worker:
    def __init__(self, i):
        self.p = subprocess.Popen(
            ["node", "ai/bridge.cjs"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
            env={**os.environ, "SEED": f"profile-{i}"},
        )

    def call(self, q):
        self.p.stdin.write(json.dumps(q) + "\n")
        self.p.stdin.flush()
        return json.loads(self.p.stdout.readline())


results = []
sample = None
for workers, envs in [(1, 24), (1, 256), (4, 256), (8, 256)]:
    pool = concurrent.futures.ThreadPoolExecutor(workers)
    ws = [Worker(i) for i in range(workers)]
    n = envs // workers
    current = list(pool.map(lambda w: w.call({"op": "reset", "n": n}), ws))
    timing = {"packing_gpu": 0.0, "engine_ipc": 0.0}
    started = time.perf_counter()
    decisions = 0
    for step in range(120):
        rows = [r for x in current for r in x["observations"]]
        t = time.perf_counter()
        with torch.no_grad():
            logits, _ = net(*train.tensors(rows))
            choices = (
                torch.distributions.Categorical(logits=logits).sample().cpu().tolist()
            )
        timing["packing_gpu"] += time.perf_counter() - t
        t = time.perf_counter()
        current = list(
            pool.map(
                lambda pair: pair[1].call(
                    {"op": "step", "actions": choices[pair[0] * n : (pair[0] + 1) * n]}
                ),
                enumerate(ws),
            )
        )
        timing["engine_ipc"] += time.perf_counter() - t
        decisions += len(rows)
    seconds = time.perf_counter() - started
    entry = {
        "workers": workers,
        "envs": envs,
        "decisions_per_second": decisions / seconds,
        "seconds": seconds,
        **timing,
    }
    results.append(entry)
    print(json.dumps(entry), flush=True)
    sample = rows
    for w in ws:
        w.p.terminate()
        w.p.wait()
    pool.shutdown()
# Compare GPU optimization throughput including normal data packing.
optimizer = torch.optim.Adam(net.parameters(), lr=3e-4)
training = []
for size in [256, 1024]:
    rows = (sample * ((size + len(sample) - 1) // len(sample)))[:size]
    torch.cuda.synchronize()
    t = time.perf_counter()
    for _ in range(30):
        logits, v = net(*train.tensors(rows))
        loss = -logits.log_softmax(-1)[:, 0].mean() + v.square().mean()
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
    torch.cuda.synchronize()
    seconds = time.perf_counter() - t
    training.append({"batch": size, "samples_per_second": 30 * size / seconds})
# Validate original checkpoint export with real observations and varying masks.
net.load_state_dict(ck["state_dict"])
net.eval()
session = ort.InferenceSession(
    hf_hub_download(repo, "runs/baseline-v1/imitation.onnx"),
    providers=["CPUExecutionProvider"],
)
errors = []
for n in [1, 7, 24]:
    x = train.tensors(sample[:n])
    feed = dict(zip(["state", "actions", "mask"], [a.cpu().numpy() for a in x]))
    actual = session.run(None, feed)
    with torch.no_grad():
        expected = [a.cpu().numpy() for a in net(*x)]
    errors.append(max(float(np.max(np.abs(a - b))) for a, b in zip(actual, expected)))
assert max(errors) < 1e-4, errors
out = Path("profile.json")
out.write_text(
    json.dumps(
        {"rollouts": results, "training": training, "onnx_max_abs_error": max(errors)},
        indent=2,
    )
)
print(out.read_text(), flush=True)
HfApi().upload_file(
    repo_id=repo, path_or_fileobj=str(out), path_in_repo="runs/baseline-v1/profile.json"
)
