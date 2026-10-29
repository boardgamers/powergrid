# Explicit transport recovery and current confirmation — 29 October 2026

**21,076 / 26,880 games independently audited; 400 added this turn.**
At **13:27:27 UTC**, all ten explicitly admitted recovery jobs were **RUNNING**.
The untouched bucket batch had 81 submitted jobs: 29 COMPLETED and 52 RUNNING;
10 jobs / 200 games were independently collected. The older retained batch is
fully terminal: **54 COMPLETED/audited / 1,080 games**, ten preserved ERROR attempts.
Total active jobs: **62 / 64**. **177 untouched rows / 4,128 games** remain.

This turn submitted **37 jobs / 796 games**: ten recoveries / 200 games and
27 untouched rows / 596 games (13 five-player and 14 six-player rows). All new
handles and effective source/resource configurations were checked. Newly submitted
or merely completed-but-uncollected games do not count toward audited coverage.
No policy, seed, rule, search budget or inference setting changed. No gradients,
reserved final seeds, candidate selection, qualification or deployment.

Exact handles, original failed-attempt bindings, current stages, all collected
bucket archives and source revisions/hashes are in
`strong/current-auction-failed-bucket-launch-v3.json`.
The source is immutable and all prepared manager/worker/test files are now frozen.

## Dispatch and recovery

Use **`strong/manage_current_auction_failed_bucket_v3.py`** for both active batches.
It prioritizes the ten explicitly admitted recoveries, then follows the unchanged
untouched-row order, counting every active job in both batches and the originals.
The old dispatcher cannot count the new recovery batch, so its new STOP marker
records a transfer to this combined dispatcher. Do not remove either STOP or run
`manage_current_auction_bucket_remaining_v3.py cycle --execute` independently.

Original v2 STOP: `07a47d46a5cfb7e36b217f82b33632dd878b3b9deb56120cb8353db12e84ed53`.
Untouched-batch transfer STOP: `9c1fc27a7be4c59390f1ace09b3ef5b8830fdd14175edf2beaecde1653e690b6`.
Current combined state: `runs/current-auction-failed-bucket-hf-v3/state.json`.
The old untouched manager's `state.json` is historical; it does not include the
latest launches or audits. The combined state and individual immutable receipts
are authoritative. Original failure logs, partial data and ERROR handles remain
unchanged, with exact terminal/log hashes attached to each new attempt.

**32 tests passed**, covering pack integrity, explicit failure history, launch
idempotency, ambiguous submissions, effective HF configuration, shared capacity,
recovery priority, transferred ownership and preservation of existing STOPs.
All ten actual original game specifications/policies were validated, followed by
an actual non-executing five-player CLI check. Preparation evidence is verified
in private model revision `eeda45ebceb7149638e90ef4544a7bdf09b374e4`, archive
`archives/current-auction-failed-bucket-preparation-evidence-v3.tgz`, SHA-256
`20a622530cb053d39d88b62b0bc1211e9d576dcdd36790b1a0dbb8f6b4f57432`.

Private dataset source revision `7774c71319ccf9c3304469576176b2003c00b7fd`,
`strong-source-current-auction-failed-bucket-v3.tgz`, SHA-256
`46d9c517e00b0ac5c411c31f6e027201caee35718832d0a21824d0056ac40c1f`,
manifest `248906df37670e9c56edebc4662febe5f1ca2025c0bdc17d32068b6e5b8e9c49`.
Do not repeat preparation/upload or change frozen code. Restore the exact archives.

## Collection interruption and bounded continuation

Local collection session **87384 / PID 152949** ended with exit 143 after five
complete new audits / 100 games, before any submissions. The process was confirmed
absent. Its last partial folder was `pg-current-bucket-v3-pop-heuristic-5p-06`:
12 downloaded checkpoints were verified; no raw-review/promotion intent existed.
No job was restarted. A later bounded pass reused those downloads and completed
that original job's full audit and archive. Preserve the interrupted log/report.

The old retained collector session **61621** also reported exit 143 after writing
its complete durable summary. PID 99384 was absent; a separate read-only check
bound all 54 saved receipts / 1,080 games to that summary. No recollection occurred.
These are local process observations, not failed HF game jobs or inferred causes.

Separate dispatch from small collection passes to stay bounded:

- `cycle --execute --launch-limit 64 --collect-limit 0` fills available slots.
- `cycle --execute --launch-limit 0 --collect-limit 1` collects one terminal job.
- `cycle` without `--execute` only validates preparation; it makes no HF calls.

Use `exec env HF_HUB_DISABLE_PROGRESS_BARS=1 PYTHONPATH=ai/strong
ai/.venv/bin/python -u -B ...` in shell commands. Do not run competing collectors.
Dispatch session **92690** and single-job collection session **67342** completed
normally and their actual processes exited. No background coordinator was started.
Check actual process ownership before another pass; a session return alone is
insufficient. Inspect ambiguous intents/outcomes and preserve failures before
retrying any collection operation. Never automatically resubmit a game job.

## Complete-study comparison

Use the new `current_auction_attempt_authentication_v4.py` and
`current_auction_attempt_comparison_v4.py`. Their routing changes only the exact
ten failed v2 rows: 54 retained successes remain, plus the one timeout recovery,
one first-bucket result, 258 untouched bucket rows and ten admitted recoveries.
All 620 preserved earlier originals remain unchanged. Original failure history
must match across admission, launch, status, raw review and archive.

**44 additional tests passed.** Actual preflight verified the ten-row routing,
preserved original failure records, a real existing bucket receipt and 144 frozen
comparison inputs. Incomplete coverage still rejects before loading reviews,
raw auditing or statistics. This preflight made no new games, inference calls or
repeated raw audits. The new recovery backend has **no completed real receipt yet**;
its first actual authentication/full raw re-audit remains to be exercised after
one of the ten jobs finishes. Do not confuse synthetic tests with that proof.

Reports: `strong/current-auction-attempt-authentication-preflight-v4.json` and
`runs/current-auction-failure-routing-preflight-v4/`. Previous v3 integration
(15 tests and 120 existing games independently re-audited) stays preserved.
Do not repeat successful previous profiles, tests, preparation or source uploads.

Next: continue bounded collection/dispatch, exercise the first actual recovery
receipt, finish all canonical coverage, then execute the complete comparison
with unchanged paired statistics and strength requirements. Adapt the existing
final-selection layer to this explicit-attempt comparison; it still expects the
old original coordinator. No candidate has qualified and final seeds remain unused.

## Persistent evidence

`strong/current-auction-failed-bucket-launch-evidence-v3.json` describes the
verified private metadata archive. It references existing immutable raw job
archives instead of rerunning or duplicating them. Goal ACTIVE; previous and
current turns made progress. User updates should focus on new findings and
necessary actions, without repeating settled engine-language background.
