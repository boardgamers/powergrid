# Auction training resumed — 29 October 2026

The user removed the automatic objective and explicitly asked to continue
research and training in this chat. Do not recreate an objective. The existing
confirmation finisher continues independently; its frozen policies, deals and
selection criteria are unchanged. No game deployment is part of this work.

## New experiment

The immediate learning problem has two parts: the existing model cannot see the
Recharged discount explicitly, and the old teacher shortlist omitted **397 of
2,496 legally available discounted nominations**. Training just the previously
prepared discount inputs would leave the second problem intact.

We are regenerating current-engine nomination targets for **all 5,760 saved
nomination roots**, plus the ten naturally recovered low-cash roots. Every legal
nomination and Pass receives **64 sampled-world continuations** with the frozen
neural/opponent population. This covers Germany, 2–6 players, Original/Recharged
and open/sealed auctions. It is teacher-data generation, not a new trained model
or a playing-strength result.

- **5,770 positions**, **1,940,544 planned action/world continuations**.
- **4,326 training / 1,444 validation positions**, preserving original whole-deal
  splits (validation deals 0, 4, 8, 12). No confirmation or reserved final seeds.
- 2,880 Original controls; 384 Recharged roots with no active discount;
  2,099 previously included discounted choices; 397 previously omitted choices;
  ten naturally recovered low-cash positions.
- **60 HF CPU jobs**, four simulation workers and one inference thread each,
  24-hour timeouts, no automatic failed-job retries. All 60 were submitted and
  their effective source/resource configurations verified.
- Exact original handles: `strong/auction-discount-teacher-launch-v2.json`.
  A bounded status snapshot is `strong/auction-discount-teacher-launch-status-v2.json`.
  Source and protocol are frozen; do not mutate a running worker or relaunch a
  shard with an existing intent/receipt.

The pilot cost extrapolation was 147.8 aggregate CPU-job hours (about 2.46 hours
per balanced shard), excluding setup/upload overhead. This is a rough estimate,
not a promise. The first full-budget positions batch much more efficiently:
1,344 continuations took 78.44 seconds, versus the pilot's smaller inference
batches. Do not extrapolate three roots into a precise completion time.

## Evidence already checked

HF pilot `6ae35877ad9610e5cb311717` completed all **70 positions / 1,444
continuations**, with zero caps. Its independent audit recomputed terminal tie
credits, complete action/world coverage and paired margins. There were 290,780
simulated steps and 123,409 neural decisions; continuation computation took
393.03 seconds and the worker program including retention took 456.16 seconds.
The four-world pilot is **not admitted as reliable training targets**.

Every one of the 5,770 full-batch inputs passed current-runtime legality,
shortlist and baseline checks in a local preflight: 5,770 policy forwards, no
local simulations or gradients. The actual shard-0 CLI was also checked without
execution. The first full-budget job, `6ae35d96ad9610e5cb311e8e`, has already
produced **three independently audited roots / 1,344 continuations**, with zero
caps. These are a small verified subset, not completion of the full batch.

Fifteen audit tests passed, including rejection of altered terminal credits,
unpaired sampled worlds/opponent roles, missing actions, altered margins,
truncations and incorrect train/validation assignments. Reports:

- `strong/auction-discount-teacher-results-v1.json` — complete pilot audit.
- `strong/auction-discount-teacher-preflight-v2.json` — all-root preflight.
- `strong/auction-discount-teacher-initial-audit-v2.json` — first three full-budget roots.
- `strong/audit_auction_discount_teacher_v2.py` — independent full-budget audit,
  exact paired margins, standard errors and fixed 32-world-half diagnostics.

## Collection and next learning step

Each job prints one `bucket_evidence` JSON receipt per retained root. The raw
root, full terminal outcomes, current shortlist and exact summary are retained
in the private `coyotte508/powergrid-ai-checkpoints` bucket. Names are
`pg-discount-teacher-v2-SS-root-NNN`. Receipts bind SHA-256, manifest and Xet hashes;
bucket storage is **not versioned**, so verify all pins and promote the completed
collection to an immutable HF dataset/model revision. A transport receipt alone
is not a semantic raw audit.

Use `checkpoint_bucket_archives_v3.download_archive` for checked downloads and
`audit_auction_discount_teacher_v2.audit` against the pinned prepared root,
protocol and preflight identity. Verify all expected roots, option/world pairs,
split counts and original handles. Preserve failed/capped/partial outputs.
Do not silently replace failures or convert truncations into losses.

Review target stability across the fixed halves (worlds 0–31 / 32–63), especially
the previously omitted discounted actions, and retain uncertainty and negative
advantages. Sixty-four sampled worlds reduce noise; they do not guarantee that
all action rankings are reliable. No optimizer has run in this continuation.

Then implement the controlled training comparison on HF: discount inputs off/on
crossed with old/all-legal nomination coverage, starting from identical frozen
parent weights. Keep changes confined to nomination decisions so this focused
experiment cannot accidentally alter other phases. The existing schema-4.4
warm start is available, but its inherited shortlist/routing needs explicit
implementation for this comparison; it is not already a trained solution.
Freeze the training recipe before inspecting fresh development-game outcomes.

Evaluate the trained arms on new whole-game development deals across all five
player counts and four rule combinations, against the unchanged model and
independent opponents. Keep the existing confirmation study separate. No
candidate has been selected or qualified; reserved final seeds remain unused.

## Persistent recovery

Private dataset: `coyotte508/powergrid-ai-training-v1`.

- Audited pilot evidence: revision `4d7a1b2232ae6bb2dcb5da6c9591165645f8bd75`,
  `evidence/auction-discount-teacher-pilot-v1.tgz`.
  Descriptor: `strong/auction-discount-teacher-evidence-v1.json`.
- Full immutable source: revision `b25682a3bcf7d3e33eedc5a1e0d9107036848d9a`,
  `strong-source-auction-discount-teacher-v2.tgz`, archive SHA-256
  `8009081e73344d37856d83afd12953b9f5238600a2c96c1d9e364501531a23f8`.
  Descriptor: `strong/auction-discount-teacher-source-v2.json`.
- The source pins the existing current-engine artifact, model and opponent
  population. It contains all prepared roots, shard assignments, worker and
  transport dependencies, with a complete verified manifest.
- Local preparation, immutable launch intents and receipt checks:
  `runs/auction-discount-teacher-prepared-v2/`.
- Pilot raw collection: `runs/auction-discount-teacher-collected-v1/`.
  First full-budget raw audit: `runs/auction-discount-teacher-first-v2/`.

The separate fixed confirmation finisher is PID **502682**. Verify its actual
process and `runs/current-auction-confirmation-finisher-v1/state.json` before
acting; do not run a competing collector. At 14:52 UTC, **21,756 / 26,880** games
were independently audited, with 64 confirmation jobs active. That count
excludes the new teacher continuations and is a timestamped snapshot.

Do not stage the pre-existing modified `policy-iteration-development-status-v2`,
`policy-iteration-labels-results-v2` or `policy-iteration-labels-status-v2` JSON
files. Keep original dispatcher STOP markers and failure histories intact.
