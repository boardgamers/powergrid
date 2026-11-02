"""Reproducible deal-level splits and atomic, resumable game collection."""
import concurrent.futures
import gzip
import hashlib
import itertools
import multiprocessing
import json
import os
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
PROTOCOL = json.loads((Path(__file__).parent / "protocol.json").read_text())


def digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def atomic_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(data, indent=2) + "\n")
    temp.replace(path)


def specs(split, deals=None):
    if split not in ("train", "validation", "transfer", "development", "smoke"):
        raise ValueError("Unknown split; reserved final split is not callable")
    maps = PROTOCOL["transferMaps"] if split == "transfer" else PROTOCOL["trainMaps"]
    if split in ("development", "smoke"):
        maps = PROTOCOL["trainMaps"] + PROTOCOL["transferMaps"]
    count = deals if deals is not None else PROTOCOL.get(split + "DealsPerCell", 1)
    result = []
    for map_name, players, variant, fast in itertools.product(maps, PROTOCOL["players"], PROTOCOL["variants"], PROTOCOL["fastBids"]):
        for deal in range(count):
            cell = f"{map_name}|{players}|{variant}|{int(fast)}"
            # Namespace includes all configuration. Seat rotations share an evaluation deal.
            seed = f"{PROTOCOL['seedNamespace']}:{split}:{cell}:{deal}"
            result.append(dict(map=map_name, players=players, variant=variant, fastBid=fast,
                               deal=deal, cell=cell, split=split, seed=seed,
                               samplesPerPhase=PROTOCOL["samplesPerPhase"], maxSteps=PROTOCOL["maxSteps"]))
    assert len({s["seed"] for s in result}) == len(result)
    return result


class Bridge:
    def __init__(self):
        self.process = subprocess.Popen(["node", str(ROOT / "ai/multimap/game.cjs")],
                                        stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                        text=True, bufsize=1, cwd=ROOT)

    def call(self, request):
        self.process.stdin.write(json.dumps(request) + "\n")
        self.process.stdin.flush()
        line = self.process.stdout.readline()
        if not line:
            raise RuntimeError(f"Engine process exited: {self.process.poll()}")
        result = json.loads(line)
        if "error" in result:
            raise RuntimeError(result["error"])
        return result

    def close(self):
        self.process.terminate()
        self.process.wait(timeout=10)
        self.process.stdin.close()
        self.process.stdout.close()


def collect_one(args):
    spec, directory = args
    path = Path(directory) / (hashlib.sha256(spec["seed"].encode()).hexdigest() + ".json.gz")
    if path.exists():
        with gzip.open(path, "rt") as f:
            result = json.load(f)
        if result["spec"] != spec or not result["terminal"]:
            raise RuntimeError(f"Stale/invalid game {path}")
    else:
        # Bounded subprocess: a worker crash or hang fails the entire collection.
        proc = subprocess.run(["node", str(ROOT / "ai/multimap/game.cjs")],
                              input=json.dumps({"op": "collect", "spec": spec}) + "\n",
                              text=True, capture_output=True, timeout=180, cwd=ROOT, check=True)
        result = json.loads(proc.stdout)
        if "error" in result:
            raise RuntimeError(result["error"])
        if not result["terminal"] or not result["rows"]:
            raise RuntimeError("Nonterminal or empty data")
        temp = path.with_suffix(".tmp")
        with gzip.open(temp, "wt", compresslevel=3) as f:
            json.dump(result, f, separators=(",", ":"))
        temp.replace(path)
    return dict(file=path.name, sha256=digest(path), spec=spec, steps=result["steps"],
                rows=len(result["rows"]), credit=result["credit"], terminal=True)


def collect(directory, split, workers=6, deals=None):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    plan = specs(split, deals)
    atomic_json(directory / "plan.json", plan)
    start = time.monotonic()
    results = []
    with concurrent.futures.ProcessPoolExecutor(max_workers=workers, mp_context=multiprocessing.get_context('spawn')) as pool:
        futures = [pool.submit(collect_one, (spec, directory)) for spec in plan]
        for future in concurrent.futures.as_completed(futures):
            results.append(future.result())
            if len(results) % 40 == 0 or len(results) == len(plan):
                print(json.dumps(dict(stage="collection", split=split, done=len(results), total=len(plan),
                                      seconds=round(time.monotonic() - start, 1))), flush=True)
                atomic_json(directory / "progress.json", results)
    results.sort(key=lambda r: r["spec"]["seed"])
    manifest = dict(schema=PROTOCOL["schema"], split=split, games=results,
                    totalRows=sum(r["rows"] for r in results), seconds=time.monotonic()-start)
    atomic_json(directory / "manifest.json", manifest)
    return manifest


def read_games(directory):
    directory = Path(directory)
    manifest = json.loads((directory / "manifest.json").read_text())
    for item in manifest["games"]:
        path = directory / item["file"]
        if digest(path) != item["sha256"]:
            raise RuntimeError(f"Data checksum mismatch: {path}")
        with gzip.open(path, "rt") as f:
            game = json.load(f)
        assert game["terminal"] and game["spec"] == item["spec"]
        yield game


def audit_splits(base):
    fingerprints, seeds, report = {}, set(), {}
    for split in ("train", "validation", "transfer"):
        duplicate = 0
        games = rows = 0
        for game in read_games(Path(base) / split):
            seed = game["spec"]["seed"]
            if seed in seeds:
                raise RuntimeError("Deal overlap")
            seeds.add(seed)
            for row in game["rows"]:
                fingerprint = row["fingerprint"]
                if fingerprint in fingerprints and fingerprints[fingerprint] != split:
                    duplicate += 1
                fingerprints[fingerprint] = split
                rows += 1
            games += 1
        report[split] = dict(games=games, rows=rows, crossSplitDuplicates=duplicate)
    atomic_json(Path(base) / "split-audit.json", report)
    if any(r["crossSplitDuplicates"] for r in report.values()):
        raise RuntimeError("Identical public features across splits: inspect before training")
    return report
