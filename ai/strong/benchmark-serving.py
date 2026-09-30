"""Validate legal responses and time the complete persistent CPU worker."""

import argparse
import json
from pathlib import Path
import subprocess
import sys
import time
import platform
import numpy as np
from search_scope import SCOPES

p = argparse.ArgumentParser()
p.add_argument("model")
p.add_argument("--search-scope", choices=SCOPES, default="all")
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
        "--search-scope",
        args.search_scope,
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
search_latencies = []
search_evaluations = 0
search_truncations = 0
by_phase = {}
by_count = {}
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
            assert result["schema"] in [3, 4]
            n = len(request["state"]["players"])
            assert len(result["winProbabilities"]) == n
            assert result["playerOrder"] == [
                (request["player"] + j) % n for j in range(n)
            ]
            by_count.setdefault(str(n), []).append(latencies[-1])
            assert result["playerOrder"][0] == request["player"]
            assert abs(sum(result["winProbabilities"]) - 1) < 1e-5
            assert sha is None or sha == result["modelSha256"]
            sha = result["modelSha256"]
            inner.append(result["elapsedMs"])
            by_phase.setdefault(str(request["state"]["phase"]), []).append(
                latencies[-1]
            )
            search_evaluations += (result.get("search") or {}).get("evaluations", 0)
            search_truncations += (result.get("search") or {}).get("truncated", 0)
            if (result.get("search") or {}).get("evaluations", 0):
                search_latencies.append(latencies[-1])
finally:
    worker.stdin.close()
    worker.wait(timeout=10)
    worker.stdout.close()
cpu_info = Path("/proc/cpuinfo")
processor_model = platform.processor()
if cpu_info.exists():
    processor_model = next(
        (
            line.split(":", 1)[1].strip()
            for line in cpu_info.read_text().splitlines()
            if line.startswith("model name")
        ),
        processor_model,
    )
report = {
    "hostname": platform.node(),
    "processor_model": processor_model,
    "python_version": platform.python_version(),
    "positions": len(latencies),
    "by_player_count": {
        n: {"positions": len(xs), "p95_ms": float(np.percentile(xs, 95))}
        for n, xs in by_count.items()
    },
    "model_sha256": sha,
    "all_moves_legal": True,
    "search_samples": args.search_samples,
    "search_scope": args.search_scope,
    "geographic_search": args.geographic_search,
    "cold_start_ms": latencies[0],
    "warm_roundtrip_p50_ms": float(np.percentile(latencies[1:], 50)),
    "warm_roundtrip_p95_ms": float(np.percentile(latencies[1:], 95)),
    "worker_p95_ms": float(np.percentile(inner[1:], 95)),
    "max_roundtrip_ms": max(latencies),
    "search_decisions": len(search_latencies),
    "search_evaluations": search_evaluations,
    "search_truncated_rollouts": search_truncations,
    "search_roundtrip_p50_ms": float(np.percentile(search_latencies, 50))
    if search_latencies
    else None,
    "search_roundtrip_p95_ms": float(np.percentile(search_latencies, 95))
    if search_latencies
    else None,
    "by_phase": {
        phase: {
            "positions": len(times),
            "p50_ms": float(np.percentile(times, 50)),
            "p95_ms": float(np.percentile(times, 95)),
            "max_ms": max(times),
        }
        for phase, times in by_phase.items()
    },
}
Path(args.output).write_text(json.dumps(report, indent=2))
print(json.dumps(report))
