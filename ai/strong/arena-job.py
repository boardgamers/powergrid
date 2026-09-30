"""Pinned-checkpoint CPU evaluation on HF Jobs."""

import os
from pathlib import Path
import subprocess
import sys
from huggingface_hub import HfApi, hf_hub_download

repo = os.environ["HF_MODEL_REPO"]
model = hf_hub_download(
    repo, os.environ["MODEL_PATH"], revision=os.environ["MODEL_REVISION"]
)
command = [
    sys.executable,
    "ai/strong/evaluate.py",
    model,
    "--opponent",
    os.environ.get("OPPONENT", "search_geo"),
    "--games",
    os.environ.get("GAMES", "48"),
    "--workers",
    os.environ.get("WORKERS", "24"),
    "--seed",
    os.environ["EVAL_SEED"],
    "--search-samples",
    os.environ.get("SEARCH_SAMPLES", "0"),
    "--output",
    "evaluation.json",
]
if os.getenv("GEOGRAPHY") == "1":
    command.append("--geographic-search")
if os.getenv("OPPONENT_MODEL_PATH"):
    opponent = hf_hub_download(
        repo,
        os.environ["OPPONENT_MODEL_PATH"],
        revision=os.environ["OPPONENT_MODEL_REVISION"],
    )
    command.extend(["--opponent-model", opponent])
subprocess.run(command, check=True)
assert Path("evaluation.json").exists()
HfApi().upload_file(
    repo_id=repo,
    path_or_fileobj="evaluation.json",
    path_in_repo=f"runs/{os.environ['RUN_NAME']}/evaluation.json",
)
