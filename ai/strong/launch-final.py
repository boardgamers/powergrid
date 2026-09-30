"""Launch or resume one frozen final evaluation plan; default is a dry run."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

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
if multiplayer and candidate.get("feature_revision") != "4.0-multiplayer":
    raise ValueError("Multiplayer final requires a schema-4 candidate")
from huggingface_hub import hf_hub_download

model = Path(
    hf_hub_download(
        "coyotte508/powergrid-ai-germany-v1",
        candidate["model_path"],
        revision=candidate["model_revision"],
    )
)
assert hashlib.sha256(model.read_bytes()).hexdigest() == candidate["model_sha256"]
manifest_path = root / "ai/strong/experiments.json"
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
        print("Already dispatched", item["name"], run["jobs"][item["name"]], flush=True)
        continue
    opponent = item["opponent"]
    env = os.environ.copy()
    env.pop("OPPONENT_MODEL_PATH", None)
    env.pop("OPPONENT_MODEL_REVISION", None)
    env["SEARCH_SCOPE"] = candidate.get("search_scope", "all")
    env["DISABLE_SEARCH_PROPOSAL"] = "0"
    if multiplayer:
        env["ASYNC_ARENA"] = "1"
    env["PLAYER_COUNT"] = str(item["player_count"])
    env["DEAL_OFFSET"] = str(item["deal_offset"])
    if "model_path" in opponent:
        env.update(
            OPPONENT_MODEL_PATH=opponent["model_path"],
            OPPONENT_MODEL_REVISION=opponent["model_revision"],
        )
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
    ids = re.findall(r"\b[0-9a-f]{24}\b", result.stdout)
    if not ids:
        raise RuntimeError(
            "Launch response was ambiguous; inspect HF job labels before retrying: "
            + result.stdout
        )
    run["jobs"][item["name"]] = ids[-1]
    manifest["jobs"][item["name"]] = ids[-1]
    manifest_path.write_text(json.dumps(manifest, indent=4) + "\n")
    print(item["name"], ids[-1], flush=True)
