"""Read-only verification of extracted frozen CPU workers from an unrelated cwd."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

p = argparse.ArgumentParser()
p.add_argument("package")
p.add_argument("fixtures")
p.add_argument("--output", required=True)
a = p.parse_args()
root = Path(a.package).resolve()
manifest = json.loads((root / "manifest.json").read_text())
for relative, expected in manifest["files"].items():
    assert hashlib.sha256((root / relative).read_bytes()).hexdigest() == expected, (
        relative
    )
worker = subprocess.Popen(
    [sys.executable, str(root / "serve.py")],
    cwd="/",
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    text=True,
)
seen = set()
try:
    for line in Path(a.fixtures).read_text().splitlines():
        fixture = json.loads(line)
        q = fixture["request"]
        g = q["state"]
        n = len(g["players"])
        key = (n, g["phase"], g["options"].get("variant"), g["options"].get("fastBid"))
        if key in seen:
            continue
        seen.add(key)
        worker.stdin.write(json.dumps(q) + "\n")
        worker.stdin.flush()
        result = json.loads(worker.stdout.readline())
        assert "error" not in result, result
        assert result["move"] in fixture["legal"]
        assert result["modelSha256"] == manifest["model_sha256"]
        assert (
            result["requestId"] == q["requestId"]
            and result["revision"] == q["revision"]
        )
        assert result["playerOrder"] == [(q["player"] + j) % n for j in range(n)]
        assert len(result["winProbabilities"]) == n
        assert abs(sum(result["winProbabilities"]) - 1) < 1e-5
finally:
    worker.stdin.close()
    worker.wait(timeout=10)
    worker.stdout.close()
report = dict(
    all_hashes_match=True,
    files_verified=len(manifest["files"]),
    positions_verified=len(seen),
    player_counts=sorted({key[0] for key in seen}),
    all_moves_legal=True,
    model_sha256=manifest["model_sha256"],
)
Path(a.output).write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report))
