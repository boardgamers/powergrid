import os, json, subprocess, concurrent.futures
from pathlib import Path
from huggingface_hub import HfApi


def run(pair):
    seed, opponent = pair
    result = subprocess.run(
        ["node", "ai/strong/tournament.cjs", "search", opponent],
        env={**os.environ, "SEEDS": "1", "SEED_START": str(seed)},
        text=True,
        capture_output=True,
        check=True,
    )
    report = json.loads(result.stdout)
    print(
        json.dumps({"seed": seed, "opponent": opponent, "win": report["win"]}),
        flush=True,
    )
    return report


with concurrent.futures.ThreadPoolExecutor(24) as pool:
    reports = list(
        pool.map(
            run,
            [
                (seed, opponent)
                for seed in range(20)
                for opponent in ["economic", "heuristic"]
            ],
        )
    )
p = Path("search-evaluation.json")
p.write_text(json.dumps(reports))
HfApi().upload_file(
    repo_id=os.environ["HF_MODEL_REPO"],
    path_or_fileobj=str(p),
    path_in_repo="runs/search-reference-v1/evaluation.json",
)
