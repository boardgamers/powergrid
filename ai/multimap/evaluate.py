"""Paired full games, fresh development deals, all seats; never final seeds."""
import argparse
import concurrent.futures
import json
import multiprocessing
from pathlib import Path
import statistics
import time

import torch

from data import Bridge, specs, atomic_json, digest
from model import GraphPolicy, SCHEMA, collate, tensor_row

_MODEL = None


def init_worker(checkpoint):
    global _MODEL
    torch.set_num_threads(1)
    saved = torch.load(checkpoint, map_location="cpu", weights_only=True)
    assert saved["schema"] == SCHEMA
    _MODEL = GraphPolicy(saved["width"]).eval()
    _MODEL.load_state_dict(saved["state_dict"])


def one_game(task):
    spec, seat, policy = task
    spec = dict(spec, focalSeat=seat)
    if policy == "teacher":
        spec["focalTeacher"] = "geographic"
    bridge = Bridge()
    start = time.monotonic()
    timings = []
    result = dict(spec=spec, seat=seat, policy=policy, terminal=False, credit=0.)
    try:
        state = bridge.call({"op":"start", "spec":spec})
        with torch.inference_mode():
            while not state["terminal"]:
                begin = time.perf_counter()
                logits, _ = _MODEL(collate([tensor_row(state["observation"])]))
                index = int(logits[0].argmax())
                timings.append(1000*(time.perf_counter()-begin))
                state = bridge.call({"op":"step", "index":index})
        result.update(terminal=True, credit=state["credit"][seat], steps=state["steps"], rounds=state["rounds"])
    except Exception as error:
        # Keep failures in the denominator at zero credit and refuse promotion.
        result["error"] = str(error)
    finally:
        bridge.close()
    result.update(seconds=time.monotonic()-start, requests=len(timings),
                  inferenceMsMedian=statistics.median(timings) if timings else None,
                  inferenceMsP95=sorted(timings)[min(len(timings)-1,int(.95*len(timings)))] if timings else None)
    return result


def summarize(results):
    cells = {}
    pairs = {}
    for r in results:
        cell = cells.setdefault(r["spec"]["cell"], {})
        rows = cell.setdefault(r["policy"], dict(games=0, completed=0, failures=0, credit=0.))
        rows["games"] += 1
        rows["completed"] += r["terminal"]
        rows["failures"] += not r["terminal"]
        rows["credit"] += r["credit"]
        pairs.setdefault((r["spec"]["seed"],r["seat"]),{})[r["policy"]]=r
    for cell in cells.values():
        for value in cell.values():
            value["winCredit"] = value["credit"] / value["games"]
        cell["difference"] = cell["model"]["winCredit"] - cell["teacher"]["winCredit"]
    complete_pairs = [r for r in pairs.values() if set(r)=={"model","teacher"}]
    return dict(cells=cells, macroCellDifference=sum(c["difference"] for c in cells.values())/len(cells),
                pairs=len(complete_pairs), games=len(results), failures=sum(not r["terminal"] for r in results),
                qualified=False, note="Engineering/development screen only. Small deal count; no final or human-strength claim. Failures receive zero credit; any failure blocks promotion.")


def run(checkpoint, output, workers=6, deals=2, max_cells=None, checkpoint_callback=None):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    plan = specs("development",deals)
    if max_cells:
        keys=list(dict.fromkeys(s["cell"] for s in plan))[:max_cells]
        plan=[s for s in plan if s["cell"] in keys]
    tasks=[(s,seat,policy) for s in plan for seat in range(s["players"]) for policy in ("model","teacher")]
    identity=dict(checkpointSha256=digest(checkpoint),tasks=tasks)
    plan_path=output/"plan.json"
    if plan_path.exists() and json.loads(plan_path.read_text())!=json.loads(json.dumps(identity)):
        raise RuntimeError("Existing evaluation directory belongs to another plan/model")
    atomic_json(plan_path,identity)
    results=[]
    result_path=output/"games.jsonl"
    if result_path.exists():
        results=[json.loads(line) for line in result_path.read_text().splitlines()]
    done={(r["spec"]["seed"],r["seat"],r["policy"]) for r in results}
    with concurrent.futures.ProcessPoolExecutor(max_workers=workers, mp_context=multiprocessing.get_context('spawn'), initializer=init_worker, initargs=(str(checkpoint),)) as pool:
        futures=[pool.submit(one_game,t) for t in tasks if (t[0]["seed"],t[1],t[2]) not in done]
        with result_path.open("a") as log:
            for future in concurrent.futures.as_completed(futures):
                r=future.result(); results.append(r)
                log.write(json.dumps(r)+"\n");log.flush()
                if checkpoint_callback and len(results)%80==0:
                    checkpoint_callback(len(results))
                if len(results)%20==0 or len(results)==len(tasks):
                    print(json.dumps(dict(stage="development",done=len(results),total=len(tasks),failures=sum(not x["terminal"] for x in results))),flush=True)
    if len(results)!=len(tasks):
        raise RuntimeError("Incomplete evaluation")
    summary=summarize(results)
    atomic_json(output/"summary.json",summary)
    return summary


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--checkpoint",required=True)
    p.add_argument("--output",required=True)
    p.add_argument("--workers",type=int,default=6)
    p.add_argument("--deals",type=int,default=2)
    p.add_argument("--max-cells",type=int)
    a=p.parse_args()
    run(a.checkpoint,a.output,a.workers,a.deals,a.max_cells)
