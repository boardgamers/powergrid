"""Exercise the full persistent JSONL worker; validate returned engine actions."""

import json, subprocess, sys, time
from pathlib import Path
import numpy as np

root = Path(__file__).resolve().parents[1]
generate = """const c=require('./ai/core.cjs');for(const variant of ['original','recharged'])for(const sealed of [false,true]){let g=c.start('serving-smoke',variant,sealed),rng=c.seedrandom('smoke'),seen=new Set();for(let n=0;n<1600&&!c.E.ended(g);n++){const p=g.currentPlayers[0],key=g.phase+':'+Math.min(g.round,3);if(!seen.has(key)){seen.add(key);console.log(JSON.stringify({state:g,player:p,revision:n,requestId:variant+'-'+sealed+'-'+n}));}g=c.E.move(g,c.heuristic(g,p,rng).action,p);}}"""
requests = [
    json.loads(l)
    for l in subprocess.check_output(
        ["node", "-e", generate], cwd=root, text=True
    ).splitlines()
]
p = subprocess.Popen(
    [sys.executable, str(root / "ai/infer.py"), sys.argv[1]],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    text=True,
)
latency = []
checks = []
for q in requests:
    t = time.perf_counter()
    p.stdin.write(json.dumps(q) + "\n")
    p.stdin.flush()
    r = json.loads(p.stdout.readline())
    latency.append((time.perf_counter() - t) * 1000)
    assert "error" not in r, r
    assert r["requestId"] == q["requestId"] and r["revision"] == q["revision"]
    assert abs(sum(r["winProbabilities"]) - 1) < 1e-5
    checks.append({"state": q["state"], "player": q["player"], "move": r["move"]})
p.stdin.close()
p.wait(timeout=10)
validate = """const c=require('./ai/core.cjs'),fs=require('fs');for(const q of JSON.parse(fs.readFileSync(0,'utf8'))){if(!c.allLegal(q.state,q.player).some(x=>JSON.stringify(x)===JSON.stringify(q.move)))throw Error('Illegal move');c.E.move(q.state,q.move,q.player);}console.log('all legal');"""
subprocess.run(
    ["node", "-e", validate], input=json.dumps(checks), cwd=root, text=True, check=True
)
report = {
    "requests": len(requests),
    "first_request_including_startup_ms": latency[0],
    "warm_end_to_end_ms": {
        k: float(np.percentile(latency[1:], v))
        for k, v in [("p50", 50), ("p95", 95), ("p99", 99)]
    },
    "all_moves_legal": True,
}
print(json.dumps(report, indent=2))
