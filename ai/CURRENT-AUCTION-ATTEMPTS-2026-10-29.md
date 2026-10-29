# Mixed-attempt confirmation — 29 October 2026

**20,676 / 26,880 games independently audited; 80 added this turn.**
At 12:46:07 UTC the bucket batch had **54 submitted jobs / 1,080 games**:
46 RUNNING, four COMPLETED/audited and four SCHEDULING. Four new fixed rows /
80 games were submitted this turn. The original retained batch still had
40 COMPLETED/audited (800 games), 14 RUNNING and ten preserved ERROR attempts.
The shared 64-active-job limit includes those older jobs. **204 untouched rows /
4,724 games** remain, plus the ten failed transport attempts requiring recovery.

Exact handles, launch hashes, immutable archives and measured runtime are in
`strong/current-auction-attempt-comparison-status-v3.json`. Original collection
session 37907, bounded collection/dispatch session 69256 and integration check
session 82021 completed. No background coordinator was started. Verify actual
process ownership before another collection cycle. Do not restart the old
dispatcher or clear its STOP marker.

## What changed

`strong/current_auction_attempt_comparison_v3.py` integrates the 620 preserved
originals with the timeout recovery, retained-v2 jobs and both bucket-v3 sources.
It requires complete canonical coverage before loading recovery reviews or
running analysis. Four isolated workers reuse the unchanged full raw verifiers;
preparation checks are cached within each worker. Immutable archives must already
be locally cached: this analysis cannot submit jobs, download, upload, simulate,
call a model, or rewrite an old coordinator's completion state.

After all independent audits match the complete saved reviews, the CLI applies
the unchanged coverage gate, paired statistics and confirmation requirements.
It checks original policy/seed/rule identities, exact game coverage, original
failure history, checkpoints, source/command bindings and archived raw bytes.
Inputs, reviews and raw files are checked again before the exclusive result write.
Its output is confirmation evidence, never final qualification or selection.

**15 tests passed.** The actual integration check independently re-audited five
existing jobs / **120 games**: an original ERROR job with complete recovered data,
the original timeout recovery, a retained-v2 result, the first bucket result and
a result from the larger bucket batch. All complete reviews match exactly. This
also exercises the previously untested actual remaining-bucket authentication.
The four-worker check took **22.65 seconds**. These are repeated audits needed to
test the new integration, not newly generated games or additional coverage.
Do not repeat the successful preflight without an implementation change.

The actual incomplete-study entry rejected before building context, loading
recovery reviews, starting raw audits or computing statistics. A successful full
26,880-game comparison has **not** run. The existing final-selection adapter also
still assumes the old coordinator; it must be adapted to the completed explicit
attempt comparison without weakening any scientific requirements.

Reports: `strong/current-auction-attempt-comparison-preflight-v3.json` and
`strong/current-auction-attempt-comparison-status-v3.json`. Evidence descriptor:
`strong/current-auction-attempt-comparison-evidence-v3.json`. Prior authentication
proof and snapshots remain unchanged in their original v3 files.

## Harness observations

The older checkpoint transport had ten terminal failures: six HTTP 500 errors
and four HTTP 429 concurrency-queue rejections during model-repository commits.
All handles, logs and available partial data remain preserved. There is no
evidence here that these were model failures. Frequent shared Git commits were
an unsuitable checkpoint path; new execution uses the previously verified bucket
transport and serial versioned promotion after collection.

The first four audited jobs from the larger bucket batch completed **80 games**
with **69 checkpoints and 69 upload calls**, no repeated application upload calls.
They took 26.35–34.19 minutes each and averaged 4.49–5.19 CPU cores over their
measured workflow. Per-job checkpoint-transfer intervals summed to 18.43–23.90
seconds, with the longest individual transfer 1.87 seconds. Transfers overlap
child execution; their summed durations are not measured blocking overhead.
These four completed five-player heuristic-opponent jobs are not a representative
throughput benchmark, and no speedup against the old transport is claimed.

## Continue

Use frozen `strong/manage_current_auction_bucket_remaining_v3.py` with
`cycle --execute --launch-limit 64 --collect-limit 4` for a bounded collection and
fixed-order dispatch pass. `--launch-limit 0` disables new submissions. Use the
separate original collection-only helper
`collect_current_auction_retained_after_transport_failure_v2.py --limit 8`.
Both share the original cycle lock; never run competing collectors.

All commands use `ai/.venv/bin/python -u -B`, `PYTHONPATH=ai/strong` and
`HF_HUB_DISABLE_PROGRESS_BARS=1`. Latest logs are
`runs/current-auction-retained-collection-v2-thirteenth.log` and
`runs/current-auction-bucket-cycle-v3-fourth.log`. Original STOP SHA remains
`07a47d46a5cfb7e36b217f82b33632dd878b3b9deb56120cb8353db12e84ed53`.
Remote observation errors are unknown, not job death. Inspect ambiguous
submission/collection/promotion intents and outcomes before acting.

Next priority: explicitly admit bucket-based recovery for the ten failed
transport attempts, keeping the same canonical games and all original evidence.
The current routing intentionally still marks those rows missing. Extend its
authentication and comparison routing for the exact admitted recoveries; never
pretend failed v2 jobs completed or automatically retry them. Continue the fixed
untouched rows, then run the complete comparison and adapt final selection.
The CLI defaults to inventory only; `--execute` refuses incomplete coverage.

Goal ACTIVE. Previous and current turns made progress. No candidate selected or
qualified, no new training updates, no failed jobs restarted, no final seeds used,
and no deployment. User updates should focus on new findings/actionable blockers;
do not repeat the engine-language recap or other settled background.
