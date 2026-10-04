"""HF CPU job: preserve clean teacher games and replay capped games at 2400 moves."""

from concurrent.futures import ThreadPoolExecutor
from collections import Counter
import gzip
import json
import os
from pathlib import Path
import subprocess

from huggingface_hub import HfApi, hf_hub_download
from teacher_contract import validate_game

repo = os.environ["HF_DATA_REPO"]
revision = os.environ["REPAIR_INPUT_REVISION"]
version = os.environ["REPAIR_INPUT_VERSION"]
target = os.environ["REPAIR_OUTPUT_VERSION"]
assert len(revision) == 40 and all(c in "0123456789abcdef" for c in revision)
assert version != target
assert all(c.isalnum() or c in "-_" for c in target)
limit = int(
    subprocess.check_output(
        [
            "node",
            "-e",
            "console.log(require('./ai/strong/search.cjs').DEFAULT_MAX_STEPS)",
        ],
        text=True,
    )
)
assert limit == 2400
out = Path("ai/runs") / target
out.mkdir(parents=True, exist_ok=True)
manifest = dict(
    input_revision=revision,
    input_version=version,
    output_version=target,
    repaired_search_max_steps=limit,
    shards=[],
)
seen = set()


def capped(g):
    return bool(
        g["truncated"]
        or g["searchStats"]["truncated"]
        or g.get("opponentSearchStats", {}).get("truncated", 0)
    )


def regenerate(old):
    env = {
        **os.environ,
        "DATA_VERSION": version,
        "PLAYER_COUNT": str(old["playerCount"]),
        "FEATURE_REVISION": "4.0-multiplayer",
        "TEACHER_OPPONENTS": "search_geo",
        "OPPONENT_SEARCH_SAMPLES": "16",
        "SEARCH_SAMPLES": "48",
        "GEOGRAPHY": "1",
        "INCLUDE_ALL_PHASES": "1",
    }
    result = subprocess.run(
        ["node", "ai/strong/search-teacher.cjs", str(old["id"])],
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )
    new = json.loads(result.stdout)
    validate_game(new)
    assert not capped(new), "Corrected game still truncated; keep it out of training"
    for key in ["seed", "id", "playerCount", "variant", "sealed", "opponent"]:
        assert old[key] == new[key], f"Replay identity changed: {key}"
    new["searchMaxSteps"] = limit
    print(
        json.dumps(dict(stage="repaired_teacher_game", id=new["id"], seed=new["seed"])),
        flush=True,
    )
    return new


for shard, n in enumerate(range(2, 7)):
    path = hf_hub_download(
        repo,
        f"{version}/{version}-{shard}.jsonl.gz",
        repo_type="dataset",
        revision=revision,
    )
    with gzip.open(path, "rt") as f:
        games = [json.loads(line) for line in f]
    assert len(games) == 240 and len({g["id"] for g in games}) == 240
    for g in games:
        validate_game(g)
        assert g["playerCount"] == n and g["opponent"] == "search_geo"
        assert g["seed"] not in seen
        seen.add(g["seed"])
    bad = [g for g in games if capped(g)]
    with ThreadPoolExecutor(int(os.getenv("DATA_WORKERS", "24"))) as pool:
        replacements = {g["id"]: g for g in pool.map(regenerate, bad)}
    repaired = [replacements.get(g["id"], g) for g in games]
    cells = Counter((g["rows"][0]["seat"], g["variant"], g["sealed"]) for g in repaired)
    assert len(cells) == 4 * n and set(cells.values()) == {240 // (4 * n)}
    assert all(not capped(g) for g in repaired)
    with gzip.open(out / f"{target}-{shard}.jsonl.gz", "wt") as f:
        for g in repaired:
            f.write(json.dumps(g, separators=(",", ":")) + "\n")
    info = dict(
        shard=shard,
        player_count=n,
        games=240,
        preserved_games=240 - len(bad),
        regenerated_games=len(bad),
        positions=sum(len(g["rows"]) for g in repaired),
        original_capped_games=[
            dict(
                id=g["id"],
                seed=g["seed"],
                truncated=g["truncated"],
                searchStats=g["searchStats"],
                opponentSearchStats=g.get("opponentSearchStats"),
            )
            for g in bad
        ],
    )
    manifest["shards"].append(info)
    print(json.dumps(dict(stage="repaired_shard", **info)), flush=True)
assert len(seen) == 1200
(out / "repair-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
HfApi().upload_folder(
    repo_id=repo, repo_type="dataset", folder_path=str(out), path_in_repo=target
)
