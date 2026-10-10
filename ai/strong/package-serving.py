"""Package a frozen CPU policy and its exact engine/runtime dependencies."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
import onnxruntime as ort
from feature_contract import METADATA_KEY
from search_scope import SCOPES

p = argparse.ArgumentParser()
p.add_argument("model")
p.add_argument("--search-scope", choices=SCOPES, default="all")
p.add_argument("output")
p.add_argument("--model-revision", required=True)
p.add_argument("--search-samples", type=int, default=0)
p.add_argument("--geographic-search", action="store_true")
a = p.parse_args()
if not 0 <= a.search_samples <= 64 or (a.geographic_search and not a.search_samples):
    p.error("Search samples must be 0..64; geography requires positive samples")
root = Path(__file__).resolve().parents[2]
model = Path(a.model).resolve()
session = ort.InferenceSession(str(model), providers=["CPUExecutionProvider"])
revision = session.get_modelmeta().custom_metadata_map.get(METADATA_KEY, "3.0")
if revision not in ["3.0", "3.1-uranium39", "4.0-multiplayer", "4.1-five-plants", "4.1-five-plants-zero-inputs", "4.2-discard-correction", "4.3-strategic-correction"]:
    raise ValueError("Unknown feature revision")
multiplayer = revision in ["4.0-multiplayer", "4.1-five-plants", "4.1-five-plants-zero-inputs", "4.2-discard-correction", "4.3-strategic-correction"]
out = Path(a.output).resolve()
out.mkdir(parents=True, exist_ok=False)
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
with tempfile.TemporaryDirectory() as tmp:
    bundle = Path(tmp)
    shutil.copytree(root / "source-bundle/engine", bundle / "engine")
    common = ["core.cjs", "infer.py", "requirements-serve.txt"]
    strong = [
        "infer.py",
        "worker.cjs",
        "encoders.cjs",
        "feature_contract.py",
        "search_scope.py",
        "features.cjs",
        "features-v3_0.cjs",
        "features-v4.cjs",
        "features-v4_1.cjs",
        "features-v4_1_control.cjs",
        "features-v4_2.cjs",
        "features-v4_3.cjs",
        "economics.cjs",
        "economics-v3_0.cjs",
        "economics-v4_1.cjs",
        "spatial.cjs",
        "public-graph.cjs",
        "geographic-proposals.cjs",
        "search.cjs",
    ]
    (bundle / "ai/strong").mkdir(parents=True)
    for name in common:
        shutil.copy2(root / "ai" / name, bundle / "ai" / name)
    for name in strong:
        shutil.copy2(root / "ai/strong" / name, bundle / "ai/strong" / name)
    shutil.copy2(model, bundle / "policy.onnx")
    (bundle / "serve.py").write_text(
        """import hashlib, json, os, sys
from pathlib import Path
root = Path(__file__).resolve().parent
if len(sys.argv) != 1:
    raise SystemExit("Invoke this frozen worker without arguments; send JSONL on stdin.")
manifest = json.loads((root / "manifest.json").read_text())
model = root / "policy.onnx"
if hashlib.sha256(model.read_bytes()).hexdigest() != manifest["model_sha256"]:
    raise SystemExit("Model hash differs from the frozen manifest")
command = [sys.executable, str(root / "ai/strong/infer.py"), str(model), "--search-samples", str(manifest["search_samples"]), "--search-scope", manifest.get("search_scope", "all")]
if manifest["geographic_search"]:
    command.append("--geographic-search")
os.execv(sys.executable, command)
"""
    )
    command = (
        f"python ai/strong/infer.py policy.onnx --search-samples {a.search_samples} --search-scope {a.search_scope}"
        + (" --geographic-search" if a.geographic_search else "")
    )
    (bundle / "START.txt").write_text(
        "Powergrid CPU research worker\n\nRequires Node.js 24 and Python 3.11 or 3.12.\nCreate a virtual environment and install: pip install -r ai/requirements-serve.txt\nRun the frozen configuration from any directory: python /path/to/package/serve.py\nEquivalent direct command: "
        + command
        + "\n\nSend one JSON object per line with requestId, revision, player (seat index), and state (engine game state). Keep the process alive between requests. Each response proposes one atomic move. The platform must check the game revision and validate the move through the authoritative engine before committing it. Errors must not be committed as moves.\n\nScope: Germany, "
        + ("2–6 players" if multiplayer else "three players")
        + ", automatic setup; original/Recharged and open/sealed auctions. Other players’ money is intentionally visible. Hidden deck order and sealed bids are excluded from policy inputs and search beliefs. Value outputs are uncalibrated training-opponent estimates, not objective player-analysis scores.\n\nThis archive makes no strength claim by itself. Consult the accompanying measured evaluations. No production routing is installed.\n"
    )
    manifest = {
        "model_sha256": sha(model),
        "model_repository_revision": a.model_revision,
        "feature_revision": revision,
        "schema": 4 if multiplayer else 3,
        "engine_revision": "365fc519903fa2b4e8c593eed6cc5f5f77b5332a",
        "runtime_git_revision": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=root, text=True
        ).strip(),
        "runtime_git_dirty": bool(
            subprocess.check_output(
                ["git", "status", "--porcelain"], cwd=root, text=True
            ).strip()
        ),
        "search_samples": a.search_samples,
        "search_scope": a.search_scope,
        "geographic_search": a.geographic_search,
        "scope": {
            "map": "Germany",
            "players": [2, 3, 4, 5, 6] if multiplayer else 3,
            "automatic_setup": True,
            "variants": ["original", "recharged"],
            "auctions": ["open", "sealed"],
        },
        "files": {
            str(f.relative_to(bundle)): sha(f)
            for f in sorted(bundle.rglob("*"))
            if f.is_file()
        },
    }
    (bundle / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    shutil.copy2(bundle / "manifest.json", out / "manifest.json")
    with tarfile.open(out / "powergrid-cpu-worker.tgz", "w:gz") as t:
        for f in sorted(bundle.rglob("*")):
            if f.is_file():
                t.add(f, arcname=str(f.relative_to(bundle)))
print(
    json.dumps(
        {"archive": str(out / "powergrid-cpu-worker.tgz"), "model_sha256": sha(model)}
    )
)
