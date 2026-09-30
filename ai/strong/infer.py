"""Persistent CPU ONNX worker for versioned public-information states."""

import sys, json, argparse, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from infer import Model, Node
from feature_contract import check_revision, model_revision
from search_scope import SCOPES, search_enabled

p = argparse.ArgumentParser()
p.add_argument("model")
p.add_argument("--search-scope", choices=SCOPES, default="all")
p.add_argument("--search-samples", type=int, default=0)
p.add_argument("--geographic-search", action="store_true")
args = p.parse_args()
if not 0 <= args.search_samples <= 64:
    p.error("--search-samples must be 0..64")
if args.geographic_search and not args.search_samples:
    p.error("--geographic-search requires positive --search-samples")
model = Model(args.model)
node = Node("strong/worker.cjs")
try:
    for line in sys.stdin:
        q = {}
        try:
            obj = json.loads(line)
            if not isinstance(obj, dict):
                raise ValueError("Expected object")
            q = obj
            start = time.perf_counter()
            r = node.call({**q, "op": "rank", "featureRevision": model_revision(model)})
            if "error" in r:
                raise ValueError(r["error"])
            check_revision(model, r.get("featureRevision", "3.0"))
            index, values = model.predict(r["state"], r["actions"])
            search = None
            if args.search_samples and search_enabled(
                args.search_scope,
                q["state"]["options"].get("variant"),
                q["state"]["options"].get("fastBid"),
            ):
                search = node.call(
                    {
                        **q,
                        "op": "search",
                        "proposal": index,
                        "samples": args.search_samples,
                        "featureRevision": model_revision(model),
                        "geography": args.geographic_search,
                    }
                )
                if "error" in search:
                    raise ValueError(search["error"])
                index = search["index"]
            print(
                json.dumps(
                    {
                        "requestId": q.get("requestId"),
                        "revision": q.get("revision"),
                        "move": r["moves"][index],
                        "winProbabilities": values[: len(r["playerOrder"])],
                        "valueStatus": "uncalibrated-training-opponents",
                        "playerOrder": r["playerOrder"],
                        "schema": r["schema"],
                        "featureRevision": r["featureRevision"],
                        "search": {
                            k: v
                            for k, v in search.items()
                            if k in ["evaluations", "truncated", "winEstimate"]
                        }
                        if search
                        else None,
                        "modelSha256": model.sha256,
                        "elapsedMs": 1000 * (time.perf_counter() - start),
                    }
                ),
                flush=True,
            )
        except Exception as e:
            print(
                json.dumps({"requestId": q.get("requestId"), "error": str(e)}),
                flush=True,
            )
finally:
    node.close()
