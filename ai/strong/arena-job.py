"""Pinned-checkpoint CPU evaluation on HF Jobs."""

import os
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from huggingface_hub import HfApi, hf_hub_download

repo = os.environ["HF_MODEL_REPO"]
model = hf_hub_download(
    repo, os.environ["MODEL_PATH"], revision=os.environ["MODEL_REVISION"]
)
digest = lambda path: hashlib.sha256(Path(path).read_bytes()).hexdigest()
if os.getenv("MODEL_SHA256"):
    assert digest(model) == os.environ["MODEL_SHA256"], "Wrong candidate bytes"
command = [
    sys.executable,
    "ai/strong/evaluate.py",
    model,
    "--players",
    os.getenv("PLAYER_COUNT", "3"),
    "--deal-offset",
    os.getenv("DEAL_OFFSET", "0"),
    "--opponent",
    os.environ.get("OPPONENT", "search_geo"),
    "--games",
    os.environ.get("GAMES", "48"),
    "--workers",
    os.environ.get("WORKERS", "24"),
    "--seed",
    os.environ["EVAL_SEED"],
    "--search-scope",
    os.environ.get("SEARCH_SCOPE", "all"),
    "--search-samples",
    os.environ.get("SEARCH_SAMPLES", "0"),
    "--output",
    "evaluation.json",
]
if os.getenv("ASYNC_ARENA") == "1":
    command.append("--async-rollout")
if os.getenv("DISABLE_SEARCH_PROPOSAL") == "1":
    command.append("--disable-search-proposal")
if os.getenv("GEOGRAPHY") == "1":
    command.append("--geographic-search")
if os.getenv("OPPONENT_MODEL_PATH"):
    opponent = hf_hub_download(
        repo,
        os.environ["OPPONENT_MODEL_PATH"],
        revision=os.environ["OPPONENT_MODEL_REVISION"],
    )
    if os.getenv("OPPONENT_MODEL_SHA256"):
        assert digest(opponent) == os.environ["OPPONENT_MODEL_SHA256"], "Wrong opponent bytes"
    command.extend(["--opponent-model", opponent])
subprocess.run(command, check=True)
assert Path("evaluation.json").exists()
if os.getenv("SOURCE_SHA256"):
    report = json.loads(Path("evaluation.json").read_text())
    report["source"] = {
        "archive": os.environ["SOURCE_ARCHIVE"],
        "revision": os.environ["SOURCE_REVISION"],
        "sha256": os.environ["SOURCE_SHA256"],
    }
    report["arena_runner_sha256"] = digest(__file__)
    report["run_name"] = os.environ["RUN_NAME"]
    report["model_repository_revision"] = os.environ["MODEL_REVISION"]
    report["opponent_repository_revision"] = os.getenv("OPPONENT_MODEL_REVISION")
    Path("evaluation.json").write_text(json.dumps(report, indent=2) + "\n")
HfApi().upload_file(
    repo_id=repo,
    path_or_fileobj="evaluation.json",
    path_in_repo=f"runs/{os.environ['RUN_NAME']}/evaluation.json",
)
