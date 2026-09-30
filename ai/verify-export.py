"""CPU inference-only parity check of trained checkpoints versus exported ONNX."""

import argparse, json, subprocess
from pathlib import Path
import numpy as np
import torch
import onnxruntime as ort
import train

p = argparse.ArgumentParser()
p.add_argument("directory")
args = p.parse_args()
root = Path(__file__).resolve().parents[1]
script = """const c=require('./ai/core.cjs');for(const variant of ['original','recharged'])for(const sealed of [false,true]){let g=c.start('parity',variant,sealed),rng=c.seedrandom('parity');for(let i=0;i<240&&!c.E.ended(g);i++){const p=g.currentPlayers[0],a=c.candidates(g,p);if(i%10===0)console.log(JSON.stringify({state:c.observe(g,p),actions:a.map(x=>c.actionFeatures(g,p,x))}));g=c.E.move(g,c.heuristic(g,p,rng).action,p);}}"""
rows = [
    json.loads(l)
    for l in subprocess.check_output(
        ["node", "-e", script], cwd=root, text=True
    ).splitlines()
]
train.DEVICE = "cpu"
results = {}
for name in ["imitation", "selfplay"]:
    ck = torch.load(
        Path(args.directory) / (name + ".pt"), map_location="cpu", weights_only=True
    )
    train.AD = ck["action_dim"]
    net = train.Policy(ck["state_dim"], train.AD).eval()
    net.load_state_dict(ck["state_dict"])
    opts = ort.SessionOptions()
    opts.intra_op_num_threads = 1
    session = ort.InferenceSession(
        str(Path(args.directory) / (name + ".onnx")),
        sess_options=opts,
        providers=["CPUExecutionProvider"],
    )
    errors = []
    matches = 0
    for n in [1, 7, 24, len(rows)]:
        x = train.tensors(rows[:n])
        actual = session.run(
            None, dict(zip(["state", "actions", "mask"], [t.numpy() for t in x]))
        )
        with torch.no_grad():
            expected = [t.numpy() for t in net(*x)]
        errors.append(
            max(float(np.max(np.abs(a - b))) for a, b in zip(actual, expected))
        )
        assert np.array_equal(actual[0].argmax(-1), expected[0].argmax(-1))
        matches += n
    assert max(errors) < 1e-4, errors
    results[name] = {
        "max_abs_error": max(errors),
        "matching_decisions": matches,
        "batch_sizes": [1, 7, 24, len(rows)],
    }
print(json.dumps(results, indent=2))
