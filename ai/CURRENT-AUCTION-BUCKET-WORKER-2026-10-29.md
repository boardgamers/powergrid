# Bucket-backed worker and collector — 29 October 2026

**Research active; the new worker is implemented and tested, not admitted for HF execution.**
The latest bounded original-job observation, 11:20:28 UTC, found **15 COMPLETED
and independently audited, 39 RUNNING, 10 ERROR** among the same 64 handles.
The current batch has 300 audited games, taking total confirmation coverage to
**20,080 / 26,880**. This turn added eight audits / 160 games. No HF jobs, new
simulation games, inference, policy changes, candidate selection or final seeds.

## Implemented path

- `strong/current_auction_bucket_worker_v3.py` validates a per-attempt frozen
  source/control/decision bundle and defaults to validation only. Actual execution
  requires a prepared admission. It runs the unchanged original evaluator, with
  original policies, seeds, seats, rules, four game/search workers and one inference
  thread. It uploads both checkpoints and the final envelope to the private bucket;
  it makes no model-repository Git commits and cannot submit HF jobs.
- `strong/current_auction_bucket_checkpoints_v3.py` retains v2's complete-pair
  capture, identity checks, child ownership and failure behavior. Only the receipt
  contract and checkpoint metadata version change. Unresolved transport failure
  still stops the child and preserves evidence; it never restarts games. The outer
  capture's `automatic_retries: false` refers to capture/child operations; the
  separately recorded bucket transport has at most three upload calls per object.
- `strong/checkpoint_bucket_archives_v3.py` seals manifest-checked archives and
  independently downloads, checks and extracts content-pinned bucket objects.
  Missing, changed, corrupt, foreign and unsafe archives are rejected.
- `strong/current_auction_bucket_collection_v3.py` verifies configuration, prior
  failure history, complete episode coverage, live-child transport observations,
  upload ledgers and checkpoint/final byte identity. It calls the unchanged full
  raw-game/decision verifier. Its result still requires versioned archive promotion.
- `strong/promote_bucket_evidence_v3.py` uses the existing verified archive uploader
  once per collected final tree. The calling manager must serialize these commits.
  Unknown Git outcomes retain their intent and require reconciliation, not another
  blind upload. Both bucket and Git archive hashes are retained; their compression
  bytes may differ, but their manifest and member bytes must be identical.

All original v2 modules, source bundles, running jobs and STOP markers are unchanged.
The original v2 dispatcher remains stopped; do not clear its STOP.

## Verified evidence and its limits

**48 new tests passed:** 13 capture/child tests, 15 independent collector tests,
8 archive/promotion tests, 10 source/control tests and 2 worker lifecycle tests.
The latter use a mocked evaluator and fake storage with real archive code: they
prove final evidence is retained on both success and failure, not actual game play.
The earlier transport's 19 tests and real 64-client concurrency result are reused.

The actual v3 CLI validated existing untouched rows for **2, 3, 5 and 6 players**.
Every invocation created no execution output; enabling execution in its preflight
bundle was rejected for missing admission. These four bundles are explicitly
preflight-only, not a new production recovery decision. Do not publish them as
admitted sources. Report: `strong/current-auction-bucket-worker-preflight-v3.json`.

A real storage integration probe chose the first four canonical audited job
directories without reading outcomes. The v3 retention core captured **80 existing
games** as files. Four different compressed archives, **19,023,168 / 18,506,854 /
19,752,032 / 18,660,389 bytes**, were concurrently uploaded, independently downloaded
and compared against every original game/decision hash. A repeat capture made no
additional upload. The whole probe took **37.86 seconds**. No games or inference
were generated; these 80 records do not add strength evidence or coverage.

One checkpoint was also promoted through the actual final-archive helper, with
identical manifest/member bytes at model revision
`9352b13e317ba7f756b2eaf6c25df7be346a16e5`, path
`archives/pg-bucket-integration-proof-v3-00-checkpoint-0001.tgz`, SHA-256
`6f0e0b6262eceef2cfc28edc08678fd9e7de2058ae881e3b6f1875404730699f`.
Report: `strong/current-auction-bucket-integration-probe-v3.json`.
This is a storage proof, not a fabricated completed v3 job. A live HF evaluator
using this new supervisor has not yet run. The full new envelope audit has
synthetic fault-injection coverage; the actual storage probe checks raw-pair
transport against previously audited data rather than redoing those raw audits.

## Resume from here

1. Continue bounded collection of the original 64 handles, using the existing
   collection-only helper after checking the actual local process. The last
   collector session 11451 is complete; no background coordinator was started.
   Preserve the 10 errors, partial data and original STOP. The 259 never-submitted
   rows / 5,820 games remain untouched. Prior failure diagnostics and immutable
   archives are in the preceding checkpoint-storage handoff.
2. Build the actual execution manager and explicit transport/recovery decision.
   Bind every proposed attempt to its original row, all previous failed handles,
   terminal/log hashes, effective HF resources, and the immutable reviewed worker
   source. Preserve uncertainty after submission; no automatic job retries.
   Do not use preflight fixture decisions as production authorization.
3. Prepare/archive the real bundle and independently check its execution controls.
   Start with one fixed canonical row to establish actual live-child checkpoint
   retention, final bucket collection, full raw audit and immutable promotion.
   The broad user goal authorizes this research once the concrete controls are
   ready; no additional user confirmation is required merely by this document.
4. After that real proof, finish the remaining fixed confirmation rows using the
   new recorded transport decision. Never quietly overwrite failed attempts or
   select convenient partial outcomes. Complete the explicit-attempt comparator
   and unchanged paired/strength gates before using reserved final seeds.

The metadata archive descriptor is `strong/current-auction-bucket-worker-evidence-v3.json`.
It preserves the code, original tests, read-only bundles, probe receipts and latest
job audit metadata, referencing existing raw archives instead of duplicating them.
Inspect its existing intent/outcome before any retry. Do not rerun successful
tests, probes, collection audits or archive operations without a concrete change.

Previous goal turn: **progress** (storage implementation/concurrency proof).
This turn: **progress** (160 newly audited games, worker/collector integration,
48 passing checks, real larger-archive transfer and promotion). Research remains
active; no candidate is selected or qualified, and final seeds remain unused.
