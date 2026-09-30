"""Validate legal responses and time the complete persistent CPU worker."""

import argparse
import json
from pathlib import Path
import subprocess
import sys
import time
import numpy as np

p = argparse.ArgumentParser()
p.add_argument("model")
p.add_argument("fixtures")
p.add_argument("--output", required=True)
p.add_argument("--search-samples", type=int, default=0)
p.add_argument("--stride", type=int, default=1)
p.add_argument("--geographic-search", action="store_true")
args = p.parse_args()
worker = subprocess.Popen(
    [
        sys.executable,
        str(Path(__file__).with_name("infer.py")),
        args.model,
        "--search-samples",
        str(args.search_samples),
    ]
    + (["--geographic-search"] if args.geographic_search else []),
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    text=True,
    bufsize=1,
)
latencies, inner = [], []
sha = None
try:
    with open(args.fixtures) as source:
        for i, line in enumerate(source):
            if i % args.stride:
                continue
            fixture = json.loads(line)
            request = fixture["request"]
            start = time.perf_counter()
            worker.stdin.write(json.dumps(request) + "\n")
            worker.stdin.flush()
            result = json.loads(worker.stdout.readline())
            latencies.append(1000 * (time.perf_counter() - start))
            assert "error" not in result, result
            assert result["move"] in fixture["legal"], result
            assert result["requestId"] == request["requestId"]
            assert result["revision"] == request["revision"]
            assert result["schema"] == 3
            assert result["playerOrder"][0] == request["player"]
            assert abs(sum(result["winProbabilities"]) - 1) < 1e-5
            assert sha is None or sha == result["modelSha256"]
            sha = result["modelSha256"]
            inner.append(result["elapsedMs"])
finally:
    worker.stdin.close()
    worker.wait(timeout=10)
    worker.stdout.close()
report = {
    "positions": len(latencies),
    "model_sha256": sha,
    "all_moves_legal": True,
    "search_samples": args.search_samples,
    "geographic_search": args.geographic_search,
    "cold_start_ms": latencies[0],
    "warm_roundtrip_p50_ms": float(np.percentile(latencies[1:], 50)),
    "warm_roundtrip_p95_ms": float(np.percentile(latencies[1:], 95)),
    "worker_p95_ms": float(np.percentile(inner[1:], 95)),
}
Path(args.output).write_text(json.dumps(report, indent=2))
print(json.dumps(report))
