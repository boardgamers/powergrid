# First live bucket-backed confirmation shard — 29 October 2026

**One admitted HF job is RUNNING: `6ae32f6741e90535df78a8a6`.**
The 11:39:55 UTC read-only check independently downloaded its first checkpoint,
verified the archive/member hashes and exact frozen configuration, and confirmed
the job remained RUNNING before and after. It contains one completed game; this
is retention proof, not a full raw-game audit or additional counted coverage.

The separate original-batch collection finished at 11:41:31 UTC with **31
COMPLETED and independently audited, 23 RUNNING, 10 ERROR** among its original
64 handles. Total confirmation coverage is now **20,400 / 26,880**. This turn
added 16 audits / 320 games. The new 16-game job is still uncounted. After its
single submission, **258 rows / 5,804 games** remain never submitted.

## Exact admitted execution

- Canonical row: `pg-current-confirm-v1-pop-economic_capacity_v1-2p-00`.
- Attempt: `pg-current-bucket-v3-pop-economic-capacity-v1-2p-00`.
- Games: **16**, two original deals, both seats, all four original/Recharged ×
  open/sealed combinations. Original weights, source, policies, seeds and search
  budgets are unchanged. This was the first untouched two-player row in the fixed
  order; no outcomes were consulted to choose it.
- Effective HF configuration was independently verified: **86,400 seconds,
  cpu-upgrade, python:3.11-slim-bookworm**, four game workers, four search workers,
  one inference thread. Bootstrap SHA-256:
  `30e41103dbc196e1755277d1c0db5f99c717d0b6be1f9450787ee6ec3661b310`.
- Source descriptor: `strong/current-auction-first-bucket-source-v3.json`.
  Private dataset revision `9b7af77ac6f60b08c99ace23acd076163b60cad0`, file
  `strong-source-current-auction-first-bucket-v3.tgz`, SHA-256
  `4ede6d6445e5b7eb9e1d3330a6fc70ab24e350203720d98a87ed2309de08ee62`;
  manifest `7cdd4b3ef12f6340cf42e84dcc7f8744ddd5acbfbb9b4abf041debccd94d779c`.
- Decision: `strong/current-auction-first-bucket-decision-v3.json`.
  It records this one first execution, not a failed-job replacement or broader
  dispatch. Its design status remains immutable; the separately prepared bundle's
  admission is the actual execution grant. The old preflight-only bundles were
  not reused as production grants.

The source, control, command and admission were verified before submission. The
26-file preparation archive is upload/download-verified at private model revision
`9a06f55cc5bca62ba5ce9a5ff58e7eef272dc17b`, path
`archives/current-auction-first-bucket-preparation-evidence-v3.tgz`, SHA-256
`a61b546ccb257aa8dc3bacc4539323f16731523529a26ac1619e4631b131c5df`.
All **14 new manager tests** passed: durable one-time submission, ambiguity/lock
handling, exact effective HF allocation/source checks, credential-free projections,
waiting behavior, saved-intent integrity and duplicate final-receipt rejection.
The previous 48 worker/collector tests and actual storage proofs were reused.

## Manager and collection

`strong/manage_current_auction_first_bucket_v3.py` is now frozen with the prepared
source. Its default `launch` is validation-only; the one `launch --execute` call
created the handle above. Do not launch another attempt, change the frozen code,
repeat preparation/source uploads or restart the v2 dispatcher. Original STOP:
`07a47d46a5cfb7e36b217f82b33632dd878b3b9deb56120cb8353db12e84ed53`.

Use `check` for bounded read-only status on that exact handle, and `collect` once
terminal. A remote observation failure is unknown, not a reason to restart. While
waiting, `collect` returns without fetching logs or producing results. Actual
terminal collection first preserves the worker's original log and final bucket
envelope; an HF ERROR remains failed and is never silently counted as success.

For a COMPLETED job, the independent collector validates every checkpoint and
upload ledger, live-child observations, original configuration, complete episode
coverage and exact checkpoint/final bytes, then runs the unchanged full raw-game
and decision verifier. It saves that audit before promotion, so a subsequent
archive problem does not rerun games or discard a successful audit.

One serialized versioned archive contains the **exact worker envelope, all original
checkpoint trees, the independent raw review and execution provenance**. Future
audits can recover the entire proof without depending solely on mutable bucket
objects. Compression/member hashes are checked by the existing evidence helper.
An ambiguous promotion leaves its intent and package for explicit reconciliation;
the collector does not blindly upload again. Success creates
`strong/current-auction-first-bucket-results-v3.json`. That file does not exist yet.

## Live-checkpoint proof and recovery

`strong/current-auction-first-bucket-live-checkpoint-v3.json` pins the first
checkpoint receipt, two real RUNNING observations, downloaded bytes and expected
configuration. The retained episode is **1**; its archive is **614,676 bytes**.
Its final live-child transport timestamps and complete raw game legality audit
are still pending final collection. Do not interpret retention as a win result.

Exact guard and recovery paths:

- `runs/current-auction-first-bucket-prepared-v3/`
- `runs/current-auction-first-bucket-hf-v3/launch-intent.json` and `launch.json`
- `runs/current-auction-first-bucket-hf-v3/checks/`
- `runs/current-auction-first-bucket-hf-v3/first-live-checkpoint/`
- `strong/current-auction-first-bucket-launch-v3.json`
- `strong/current-auction-first-bucket-launch-evidence-v3.json`

The last original-batch collector (session 98561, PID 3635476) completed. No
background coordinator was started. Continue bounded collection of the original
64 through the existing collection-only helper, after checking actual process
ownership. Preserve its 10 failed attempts and partial evidence. This turn
submitted exactly **one new HF job**, requested its 16 fixed games, retried zero
jobs and made zero training updates or policy changes.

Next, collect and fully audit this first live attempt. Only after its actual
success should the remaining transport/recovery decision and bounded batch manager
be prepared. The 258 untouched rows and 10 failures remain outside this grant.
Then finish complete explicit-attempt confirmation, unchanged paired/strength
gates, and the separate reserved final test. No candidate is selected/qualified;
final seeds remain unused. Both previous and current goal turns made progress.
