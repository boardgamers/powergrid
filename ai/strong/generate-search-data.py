"""HF CPU job: independent games produce a versioned, private teacher shard."""

import concurrent.futures
import gzip
import json
import os
from pathlib import Path
import subprocess
from huggingface_hub import HfApi

shard = int(os.environ["SHARD"])
games = int(os.getenv("GAMES", "128"))
version = os.getenv("DATA_VERSION", "search-teacher-v1")
output = Path(f"{version}-{shard}.jsonl.gz")
counts = {"games": 0, "positions": 0, "teacher_disagreements": 0, "truncated": 0}


def generate(game):
    result = subprocess.run(
        ["node", "ai/strong/search-teacher.cjs", str(game)],
        text=True,
        capture_output=True,
        check=True,
    )
    return json.loads(result.stdout)


with concurrent.futures.ThreadPoolExecutor(
    int(os.getenv("DATA_WORKERS", "24"))
) as pool:
    futures = [pool.submit(generate, shard * games + i) for i in range(games)]
    with gzip.open(output, "wt") as stream:
        for future in concurrent.futures.as_completed(futures):
            game = future.result()
            counts["games"] += 1
            counts["truncated"] += game["truncated"]
            # Keep truncated metadata, but never turn incomplete outcomes into targets.
            if game["truncated"]:
                game["rows"] = []
            counts["positions"] += len(game["rows"])
            counts["teacher_disagreements"] += sum(
                not r["teacherAgrees"] for r in game["rows"]
            )
            stream.write(json.dumps(game, separators=(",", ":")) + "\n")
            print(json.dumps({"shard": shard, **counts}), flush=True)
api = HfApi()
repo = os.environ["HF_DATA_REPO"]
api.upload_file(
    repo_id=repo,
    repo_type="dataset",
    path_or_fileobj=str(output),
    path_in_repo=version + "/" + output.name,
)
api.upload_file(
    repo_id=repo,
    repo_type="dataset",
    path_or_fileobj=json.dumps({"shard": shard, "schema": 3, **counts}).encode(),
    path_in_repo=f"{version}/shard-{shard}-metrics.json",
)
