"""Create the user-facing report from completed, measured runs."""

import argparse, json, hashlib, html, shutil, tarfile
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument("output")
args = p.parse_args()
out = Path(args.output)
out.mkdir(parents=True, exist_ok=True)
root = Path(__file__).resolve().parents[1]
runs = root / "ai/runs"
model = runs / "download/runs/baseline-v2"
summary = json.loads((runs / "v2-summary.json").read_text())
profile = json.loads((runs / "download/runs/baseline-v1/profile.json").read_text())
smoke = json.loads((runs / "8840u-serving-v2.json").read_text().split("\n", 1)[1])
cpu = json.loads((runs / "8840u-evaluation-v2.json").read_text())
parity = json.loads((runs / "parity-v2.json").read_text())
bench = json.loads((runs / "8840u-simulation-v2.json").read_text())
for name in [
    "v2-summary.json",
    "8840u-evaluation-v2.json",
    "8840u-serving-v2.json",
    "8840u-simulation-v2.json",
    "parity-v2.json",
]:
    shutil.copy2(runs / name, out / name)
shutil.copy2(root / "ai/README.md", out / "README.md")
shutil.copy2(model / "metrics.json", out / "training-metrics.json")
shutil.copy2(model / "schema.json", out / "schema.json")
bundle = runs / "serving-bundle"
for name in [
    "core.cjs",
    "arena.cjs",
    "features.cjs",
    "infer.py",
    "evaluate.py",
    "benchmark.cjs",
    "test.cjs",
    "serving-smoke.py",
    "requirements-serve.txt",
    "README.md",
]:
    shutil.copy2(root / "ai" / name, bundle / "ai" / name)
shutil.copy2(model / "selfplay.onnx", bundle / "selfplay.onnx")
shutil.copy2(model / "schema.json", bundle / "schema.json")
with tarfile.open(out / "powergrid-ai-serving-v2.tgz", "w:gz") as tf:
    for item in sorted(bundle.rglob("*")):
        if item.is_file() and "__pycache__" not in item.parts:
            tf.add(item, arcname=str(item.relative_to(bundle)))
manifest = {
    "engine_revision": "365fc519903fa2b4e8c593eed6cc5f5f77b5332a",
    "source_dataset_commit": "65ecfa063c272bd72a805d45f4ba55dc84a28f42",
    "source_archive": "source-v4.tgz",
    "source_sha256": hashlib.sha256((runs / "source-v4.tgz").read_bytes()).hexdigest(),
    "job": "https://huggingface.co/jobs/coyotte508/6abd0cba404719ba3761324e",
    "schema": 2,
    "model_sha256": hashlib.sha256((model / "selfplay.onnx").read_bytes()).hexdigest(),
    "deployment": "Research worker only; production bot unchanged",
    "files": {
        f.name: hashlib.sha256(f.read_bytes()).hexdigest()
        for f in out.iterdir()
        if f.is_file() and f.name not in ["report.html", "manifest.json"]
    },
}
(out / "manifest.json").write_text(json.dumps(manifest, indent=2))
rows = "".join(
    f"<tr><td>{html.escape(Path(r['model']).stem)}</td><td>{html.escape(r['opponent'])}</td><td>{r['win_rate']:.1%}</td><td>{(format(r['seed_cluster_bootstrap_95pct'][0], '.1%') + '–' + format(r['seed_cluster_bootstrap_95pct'][1], '.1%')) if r['seed_cluster_bootstrap_95pct'] else 'Not estimated (identical outcomes)'}</td><td>{r['truncated']}</td></tr>"
    for r in summary
)
rollouts = profile["rollouts"]
speed = rollouts[2]["decisions_per_second"] / rollouts[0]["decisions_per_second"]
train_speed = (
    profile["training"][1]["samples_per_second"]
    / profile["training"][0]["samples_per_second"]
)
report = f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Powergrid AI baseline</title><style>body{{font:17px/1.6 system-ui,sans-serif;max-width:1050px;margin:40px auto;padding:0 24px;color:#19302a;background:#f5f7f2}}h1,h2{{line-height:1.2}}.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:16px}}.card,section{{background:white;padding:22px;border:1px solid #d4e1d8;border-radius:12px;margin:16px 0}}.metric{{font-size:30px;font-weight:700}}table{{width:100%;border-collapse:collapse;font-size:15px}}th,td{{padding:10px;text-align:left;border-bottom:1px solid #d4e1d8}}.scroll{{overflow:auto}}a{{color:#176145}}code{{overflow-wrap:anywhere}}.note{{background:#fff4da;padding:18px;border-radius:8px}}</style><h1>Powergrid AI: executable baseline</h1><p>30 September 2026 · Germany · 3 players · original / Recharged · open / sealed auctions</p><p class="note"><b>CPU deployment is feasible. Playing strength is not ready for production.</b> The existing engine bot remains the baseline to beat. These value estimates are not calibrated for player analysis.</p><div class="cards"><div class="card"><div class="metric">{speed:.1f}×</div>Rollout throughput improvement in the HF microbenchmark</div><div class="card"><div class="metric">{train_speed:.1f}×</div>Optimizer sample throughput with batch 1,024 versus 256</div><div class="card"><div class="metric">{smoke["warm_end_to_end_ms"]["p95"]:.2f} ms</div>8840U persistent worker p95, including state encoding and IPC</div></div>
<section><h2>Measured playing strength</h2><p>Each row is 480 games: 40 unseen seeds × 3 seat rotations × 4 rule combinations. One model faces two bots of the listed type. Ties split win credit. The intervals resample whole seed groups, retaining correlations between seats and rule variants.</p><div class="scroll"><table><tr><th>Model</th><th>Opponents</th><th>Win share</th><th>95% seed-bootstrap interval</th><th>Truncated</th></tr>{rows}</table></div><p>This remains a small baseline experiment. Beating the new heuristic does not establish human-level play; performance against the existing bot is the relevant deployment gate.</p></section>
<section><h2>What was built and checked</h2><ul><li>Reproducible JavaScript simulator, heuristic, masked candidate-scoring policy, whole-game imitation split, multi-player self-play, ONNX export and CPU worker.</li><li>All 4,007 game records counted. 66 candidate Germany replays inspected; 33 match the current engine exactly. Corrected training uses 32 supported historical games, with one color-draft game excluded.</li><li>Schema v2 covers both Germany city lists (44 cities), including the Recharged replacements Mainz and Stralsund. Bids remain sealed in model observations; other players’ money is intentionally visible.</li><li>{smoke["requests"]} end-to-end worker requests returned legal actions; {cpu["games"]} CPU arena games completed on the 8840U. Pure model inference p95: {cpu["inference_ms"]["p95"]:.3f} ms. Cold first request: {smoke["first_request_including_startup_ms"]:.0f} ms.</li><li>PyTorch / ONNX maximum absolute error: {max(x["max_abs_error"] for x in parity.values()):.2g}; all checked action choices agree.</li><li><code>minipc-wg</code> now reaches the verified 8840U at WireGuard address <code>10.90.0.3</code>.</li></ul></section>
<section><h2>Why resource utilization was low</h2><p>The initial configuration used one Node worker, 24 environments and optimizer batches of 256. This compact model alternates simulation and optimization, so GPU work arrives in bursts. Four workers and 256 environments reached {rollouts[2]["decisions_per_second"]:,.0f} decisions/s versus {rollouts[0]["decisions_per_second"]:,.0f}; eight workers offered no gain. Python feature packing and JSON communication still take substantial time.</p><p>These are component microbenchmarks, not an end-to-end speedup guarantee. Larger optimizer batches also reduce gradient updates per epoch. The replacement training run uses four workers, 64 environments and batch 1,024; 256 environments are more suitable when collecting substantially larger completed-episode batches.</p></section>
<section><h2>Recommendation</h2><p>Keep the JS engine authoritative and train on HF Jobs. Run persistent ONNX workers on the 8840U; this model needs neither its GPU nor NPU. Before production, train against the existing bot and a mixture of frozen opponents, use more completed games, and gate releases on held-out arena results. Expand maps/player counts with a new variable-size representation and retraining.</p><p>For round-by-round analysis, train and calibrate that target separately. The current three-way value output estimates outcomes under its training opponents; it is not an objective score evaluation.</p></section>
<section><h2>Artifacts</h2><p><a href="powergrid-ai-serving-v2.tgz">Serving bundle</a> · <a href="README.md">Setup and worker contract</a> · <a href="v2-summary.json">Evaluation details</a> · <a href="throughput-profile.json">Throughput profile</a> · <a href="manifest.json">Hashes and provenance</a> · <a href="{manifest["job"]}">HF training job</a></p><p>One JSONL request chooses one atomic move. The platform must check the game revision, validate the move and commit it through its normal server path. No production routing was changed.</p></section></html>'''
(out / "report.html").write_text(report)
print(
    json.dumps(
        {"report": str(out / "report.html"), "model_sha256": manifest["model_sha256"]}
    )
)
