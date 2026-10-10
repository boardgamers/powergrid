"""Launch or resume one frozen final evaluation plan; default is a dry run."""

import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tarfile

p = argparse.ArgumentParser()
p.add_argument("candidate")
p.add_argument("--protocol", default="ai/strong/final-protocol.json")
p.add_argument("--launch", action="store_true")
a = p.parse_args()
root = Path(__file__).resolve().parents[2]
protocol = json.loads(Path(a.protocol).read_text())
candidate = json.loads(Path(a.candidate).read_text())
plan = []
prefix = protocol["seed_prefix"]
multiplayer = isinstance(protocol.get("scope"), dict)
launcher = (
    "ai/strong/launch-multiplayer-arena.sh"
    if multiplayer
    else "ai/strong/launch-arena.sh"
)
for opponent in protocol["opponents"]:
    counts = opponent["counts"] if multiplayer else {"3": {"games": opponent["games"]}}
    for count, spec in counts.items():
        n = int(count)
        shard_games = 4 * n * 4
        assert spec["games"] % shard_games == 0
        for shard in range(spec["games"] // shard_games):
            plan.append(
                {
                    "name": f"{prefix}-{opponent['name']}-{n}p-{shard:02}"
                    if multiplayer
                    else f"{prefix}-{opponent['name']}-{shard:02}",
                    "seed": f"{prefix}-{n}p" if multiplayer else f"{prefix}-{shard}",
                    "player_count": n,
                    "deal_offset": shard * 4 if multiplayer else 0,
                    "opponent": opponent,
                    "games": shard_games,
                }
            )
print(
    json.dumps(
        {
            "candidate": candidate,
            "jobs": len(plan),
            "games": sum(x["games"] for x in plan),
            "launch": a.launch,
        }
    ),
    flush=True,
)
if not a.launch:
    raise SystemExit(0)
if candidate.get("status") != "selected":
    raise ValueError("Select and freeze the candidate before spending final seeds")
if multiplayer and candidate.get("feature_revision") not in {
    "4.0-multiplayer", "4.1-five-plants", "4.1-five-plants-zero-inputs", "4.2-discard-correction"
}:
    raise ValueError("Multiplayer final requires a schema-4 candidate")
from huggingface_hub import hf_hub_download

source = candidate.get("source")
if multiplayer:
    if not isinstance(source, dict) or not re.fullmatch("[a-f0-9]{40}", source.get("revision", "")) or not re.fullmatch("[a-f0-9]{64}", source.get("sha256", "")):
        raise ValueError("Freeze an immutable runtime archive before final evaluation")
    archive = Path(hf_hub_download("coyotte508/powergrid-ai-training-v1", source["archive"],
                                   repo_type="dataset", revision=source["revision"]))
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == source["sha256"]
    with tarfile.open(archive) as tar:
        runner_hash = hashlib.sha256(tar.extractfile("ai/strong/arena-job.py").read()).hexdigest()
    assert runner_hash == hashlib.sha256((root/"ai/strong/arena-job.py").read_bytes()).hexdigest(), "Runtime lacks the current provenance-aware arena runner"
    assert candidate.get("arena_runner_sha256") == runner_hash
    assert isinstance(candidate.get("arena_timeout_hours"), int) and 1 <= candidate["arena_timeout_hours"] <= 12
    assert candidate.get("async_rollout") is False, "Final scheduling must match the verified synchronous development runtime"

model = Path(
    hf_hub_download(
        "coyotte508/powergrid-ai-germany-v1",
        candidate["model_path"],
        revision=candidate["model_revision"],
    )
)
assert hashlib.sha256(model.read_bytes()).hexdigest() == candidate["model_sha256"]
manifest_path = root / "ai/strong/experiments.json"
with (root / "ai/strong/.final-launch.lock").open("a") as launch_lock:
    try:
        fcntl.flock(launch_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        raise RuntimeError("Another final launcher owns the ledger; inspect it before retrying")
    manifest = json.loads(manifest_path.read_text())
    launcher_sha256 = hashlib.sha256((root / launcher).read_bytes()).hexdigest()
    fingerprint = hashlib.sha256(
        json.dumps(
            {
                "candidate": candidate,
                "protocol": protocol,
                "launcher_sha256": launcher_sha256,
            },
            sort_keys=True,
        ).encode()
    ).hexdigest()
    run = manifest.setdefault("final_runs", {}).setdefault(
        prefix,
        {
            "fingerprint": fingerprint,
            "launcher_sha256": launcher_sha256,
            "candidate": candidate,
            "protocol": protocol,
            "jobs": {},
        },
    )
    if run["fingerprint"] != fingerprint:
        raise ValueError(
            "Final seeds were already assigned to a different candidate or protocol"
        )
    manifest["final_seed_prefix_used"] = True
    manifest_path.write_text(json.dumps(manifest, indent=4) + "\n")
    for item in plan:
        if item["name"] in run["jobs"]:
            prior = run["jobs"][item["name"]]
            if isinstance(prior, dict) and prior.get("stage") != "launched":
                raise RuntimeError("Unresolved launch intent; inspect the existing HF handle/labels before resuming: " + item["name"])
            print("Already dispatched", item["name"], prior, flush=True)
            continue
        opponent = item["opponent"]
        env = os.environ.copy()
        env.pop("OPPONENT_MODEL_PATH", None)
        env.pop("OPPONENT_MODEL_REVISION", None)
        env.pop("OPPONENT_MODEL_SHA256", None)
        env["SEARCH_SCOPE"] = candidate.get("search_scope", "all")
        env["DISABLE_SEARCH_PROPOSAL"] = "0"
        if multiplayer:
            env.update(ASYNC_ARENA="0", SOURCE_ARCHIVE=source["archive"],
                       SOURCE_REVISION=source["revision"], SOURCE_SHA256=source["sha256"],
                       MODEL_SHA256=candidate["model_sha256"], TIMEOUT_HOURS=str(candidate["arena_timeout_hours"]))
        env["PLAYER_COUNT"] = str(item["player_count"])
        env["DEAL_OFFSET"] = str(item["deal_offset"])
        if "model_path" in opponent:
            env.update(
                OPPONENT_MODEL_PATH=opponent["model_path"],
                OPPONENT_MODEL_REVISION=opponent["model_revision"],
                OPPONENT_MODEL_SHA256=opponent["model_sha256"],
            )
        # Preserve an intent before submission; an ambiguous response must never
        # result in silently dispatching the same reserved-seed shard again.
        run["jobs"][item["name"]] = {"stage": "launch_intent", "deal_offset": item["deal_offset"],
                                    "player_count": item["player_count"], "games": item["games"]}
        manifest_path.write_text(json.dumps(manifest, indent=4) + "\n")
        result = subprocess.run(
            [
                "bash",
                launcher,
                item["name"],
                candidate["model_path"],
                candidate["model_revision"],
                "economic" if "model_path" in opponent else opponent["name"],
                str(candidate["search_samples"]),
                str(int(candidate["geographic_search"])),
                str(item["games"]),
                item["seed"],
            ],
            cwd=root,
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        ids = set(re.findall(r"\b[0-9a-f]{24}\b", result.stdout))
        if len(ids) != 1:
            raise RuntimeError(
                "Launch response was ambiguous; inspect HF job labels before retrying: "
                + result.stdout
            )
        job_id = ids.pop()
        run["jobs"][item["name"]].update(stage="launched", job_id=job_id)
        manifest["jobs"][item["name"]] = job_id
        manifest_path.write_text(json.dumps(manifest, indent=4) + "\n")
        print(item["name"], job_id, flush=True)
