# Checkpoint storage and original-job collection — 29 October 2026

**Research remains active; new execution is stopped while storage is repaired.**
At 11:02:07 UTC the collection-only pass observed the exact original 64 attempts:
**7 COMPLETED and independently audited, 47 RUNNING, 10 ERROR.** The seven successful
jobs add 140 games, taking verified confirmation coverage to **19,920 / 26,880**.
There are still **259 never-submitted rows / 5,820 games**. No outcome comparison,
candidate selection, reserved final seeds, new HF jobs or new inference this turn.

## What failed and what is preserved

Six jobs failed on HF model-repository HTTP 500 responses. Four explicitly failed
with HTTP 429 and `maximum time in concurrency queue reached`. Frequent checkpoint
Git commits are a proven concurrency bottleneck; the six 500 responses alone do
not establish an identical server-side cause. There is no evidence here of an
illegal-move or model failure. The frozen supervisor stops its evaluator after
an unresolved checkpoint upload rather than silently losing evidence.

Preserve `runs/current-auction-remaining-hf-v2/STOP.json` exactly, SHA-256
`07a47d46a5cfb7e36b217f82b33632dd878b3b9deb56120cb8353db12e84ed53`.
Do not clear it or restart the v2 dispatcher. No failed job was resubmitted.
Nine failed envelopes were downloaded from immutable model-repository revisions;
they contain 46 partial raw game files and 29 checkpoint receipts. These partial
files have not passed the complete raw-game audit and contribute **zero** games
to confirmation coverage. The tenth job has no final upload receipt. Keep its
original logs and existing checkpoint references; do not treat it as complete.

Exact handles and all current launch/review/archive identities are recorded in
`strong/current-auction-checkpoint-storage-status-v3.json` and the unchanged
`strong/current-auction-remaining-dispatch-v2.json`. Each raw job retains its own
original source and policy identity. The earlier completed 16-game recovery and
620 audited originals remain unchanged. No old coordinator was restarted.

## Storage implementation and actual proof

`strong/checkpoint_bucket_transport_v3.py` stores an existing archive under a unique
prefix and content hash in the private bucket `coyotte508/powergrid-ai-checkpoints`.
It writes a durable intent before network calls, checks visibility, downloads and
hashes the uploaded bytes, and records the Xet identity. A lost acknowledgement
is reconciled against the original path before another upload is considered.
Transient transport retries are bounded across process restarts; permanent errors,
corrupt or changed objects, and missing objects with existing receipts fail closed.
One local ledger has a single writer. Errors are recorded as class/status only.
This code cannot create buckets, submit jobs or run games.

**19 fault-injection tests passed.** The initial test invocation failed because
it imported `httpx`; the installed HF 2.0.0 SDK uses `httpx2`. The import was corrected
without installing packages; both logs are preserved. The successful tests cover
server/rate-limit failures before and after commit, interrupted uploads, resumed
retry budgets, read/download failures, corruption, mutation, deletion, public
visibility, conflicting writers and intent ordering.

The actual storage probe uploaded the same existing 1,735,235-byte checkpoint to
**64 disjoint paths concurrently**, with a measured peak of 64 upload calls.
All 64 were downloaded and verified in **13.04 seconds**. Eight clients deliberately
lost their acknowledgement after the real upload returned. There were exactly
64 application upload calls, zero repeat uploads and zero actual upload exceptions.
The local injected failures are not real network failures. Original report:
`strong/checkpoint-bucket-concurrency-v3.json`.

This proves concurrent transport from one host for one repeated small archive.
It does not prove sustained distributed-worker throughput or large, diverse
checkpoint behavior. Buckets are mutable and have no Git revision history, so
hash-pinned independent collection and final versioned evidence promotion remain
necessary. See [HF bucket documentation](https://huggingface.co/docs/huggingface_hub/main/en/guides/buckets).
No new supervisor is integrated, prepared or admitted yet. Live workers are unchanged.

## Safe continuation

1. Check the actual process before starting collection. The latest bounded local
   collector (session 72436 / PID 3348116) completed; no background collector was
   started. Use `strong/collect_current_auction_retained_after_transport_failure_v2.py`
   with a bounded `--limit`. It observes only the exact original 64 handles,
   preserves STOP, reuses the original raw verifier and cannot submit jobs.
   Observation failures remain unknown, not failed jobs. Do not repeat already
   successful raw audits, probe uploads, tests or archive operations.
2. Integrate bucket retention into a new supervisor and independent collector.
   Keep the v2 source frozen. Bind manifests, complete episode/decision coverage,
   original engine/policies/seeds/budgets, live-child uploads, immutable final
   promotion and actual resource settings. Exercise larger distinct existing
   archives and failures before admitting production use.
3. Record an explicit new transport/recovery decision before any execution.
   Keep every failed attempt and partial evidence. Any recovered canonical row
   must have exact full coverage; never select convenient partial outcomes or
   substitute seeds. The 259 untouched rows stay unsubmitted until that decision.
4. Finish the complete confirmation comparator/selection integration and the
   unchanged paired and strength gates. Reserved final seeds are still unused;
   no candidate is selected or qualified. The completed AMD 8840U replay remains
   technical serving evidence only.

## Persistent recovery

`strong/current-auction-checkpoint-storage-evidence-v3.json` identifies the one
private versioned metadata archive. It includes this handoff, the current snapshot,
all 64 launch records, latest observations, successful audits, failure diagnostics,
original raw archive references, transport code/tests and original probe ledgers.
It references existing immutable raw archives instead of duplicating their data.
Inspect `runs/current-auction-checkpoint-storage-evidence-v3.intent.json` and the
remote path before any archive retry. Never blindly repeat an ambiguous upload.

Previous goal turn: **no progress** (informational engine recap). This turn:
**progress** (140 newly audited games, concrete storage implementation and actual
64-client transport proof). Goal remains active; this is not a strength result.
