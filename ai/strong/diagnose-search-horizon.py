"""Replay the one capped arena match without changing its actual policy decisions."""

import json
import os
from pathlib import Path
import sys
import time

from huggingface_hub import HfApi, hf_hub_download

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from infer import Model
from pool import EnginePool

repo = "coyotte508/powergrid-ai-germany-v1"
model = Model(
    hf_hub_download(
        repo,
        "runs/multiplayer-distillation-v2-hard/best.onnx",
        revision="ab34dd266010ded1c9a6c818c721e5505dd1ddeb",
    )
)
expected_file = hf_hub_download(
    repo,
    "runs/multiplayer-hard-e10-search48-search_geo-6p-probe-4/evaluation.json",
    revision=os.environ["REPORT_REVISION"],
)
expected = next(
    r
    for r in json.loads(Path(expected_file).read_text())["results"]
    if r["gameSeed"] == "multiplayer-search-strong-probe-v1-6p-5"
    and r["variant"] == "recharged"
    and not r["sealed"]
    and r["seat"] == 1
)
out = Path("ai/runs/search-horizon-diagnostic-v1")
out.mkdir(parents=True, exist_ok=True)
os.environ["NODE_OPTIONS"] = "--require " + str(
    Path("ai/strong/diagnose-search-horizon.cjs").resolve()
)
os.environ["SEARCH_DIAGNOSTIC_PATH"] = str((out / "capped-searches.jsonl").resolve())
pool = EnginePool(
    1, seed="multiplayer-search-strong-probe-v1-6p", script="ai/strong/bridge.cjs"
)
start = last = time.monotonic()
try:
    current = pool.call(
        dict(
            op="reset",
            n=1,
            playerCount=6,
            offset=127,
            mode="search_geo",
            arenaSeed="multiplayer-search-strong-probe-v1-6p",
            featureRevisions={"learner": "4.0-multiplayer"},
        )
    )["observations"]
    ends = []
    while current[0] is not None:
        x = current[0]
        action, _ = model.predict(x["state"], x["actions"])
        reply = pool.call(
            dict(
                op="step",
                actions=[dict(proposal=action, searchSamples=48, geography=True)],
            )
        )
        current = reply["observations"]
        ends.extend(reply["ended"])
        if time.monotonic() - last >= 30:
            print(
                json.dumps(
                    dict(
                        stage="diagnostic_replay",
                        seconds=time.monotonic() - start,
                        round=x["round"],
                    )
                ),
                flush=True,
            )
            last = time.monotonic()
finally:
    pool.close()
assert len(ends) == 1
actual = ends[0]
keys = [
    "episode",
    "gameSeed",
    "truncated",
    "value",
    "playerCount",
    "variant",
    "sealed",
    "steps",
    "roles",
    "policyMoves",
    "searchStats",
    "final",
]
assert all(actual[k] == expected[k] for k in keys), (
    "Diagnostic replay diverged from original match"
)
captured = [
    json.loads(line)
    for line in (out / "capped-searches.jsonl").read_text().splitlines()
]
assert sum(r["original"]["truncated"] for r in captured) == 1
report = dict(
    exact_terminal_replay=True,
    original=actual,
    captures=[{k: v for k, v in r.items() if k != "state"} for r in captured],
    seconds=time.monotonic() - start,
)
(out / "report.json").write_text(json.dumps(report, indent=2) + "\n")
HfApi().upload_folder(
    repo_id=repo, folder_path=str(out), path_in_repo="runs/search-horizon-diagnostic-v1"
)
print(json.dumps({k: v for k, v in report.items() if k != "original"}), flush=True)
