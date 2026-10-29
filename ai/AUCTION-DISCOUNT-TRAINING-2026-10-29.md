# Auction training resumed — 29 October 2026

The user removed the automatic objective and explicitly asked to continue
research and training in this chat. Do not recreate an objective. The separate
confirmation finisher stopped on a missing HF log receipt; its frozen policies,
deals and selection criteria are unchanged. No game deployment is part of this work.

## Latest continuation — GPU training audited, full-game screen prepared

All four original GPU jobs **COMPLETED**. All 16 prescribed seed fits ran their
120 epochs: **32,640 optimizer updates**. Independent collection verified the
four bucket archives, all retained heads, selected epochs, training/data hashes,
unchanged parent tensors, actual update counts and independently recomputed CPU
metrics. Each trained model also preserved the parent exactly on 256 actual
non-nomination rows. No model has been selected or qualified.

Training itself took 94.51 aggregate worker seconds (23.2–24.1 seconds per arm),
excluding scheduling, environment setup, downloads and upload. More GPU compute
is not currently the bottleneck: generating useful teacher continuations and
measuring whole-game strength dominate.

The exported policies' validation choices are:

| Arm | Changed choices / 1,444 | Positive / negative sampled changes | Average sampled advantage |
| --- | ---: | ---: | ---: |
| d0-all0 | 56 | 27 / 21 | +0.000844 |
| d0-all1 | 36 | 18 / 12 | +0.001369 |
| d1-all0 | 177 | 83 / 47 | +0.002862 |
| d1-all1 | 14 | 9 / 3 | +0.001012 |

These are conditional terminal-credit margins on saved validation positions
already used for checkpoint selection, **not measured full-game win-rate gains**.
The apparent gains are small; the full-coverage ensemble is especially reluctant
to intervene. Keep all four arms for the planned game screen. If actual games
remain flat, revisit target quality/representation and ensemble selection rather
than simply spending more epochs or GPUs. Per-count/rule/category diagnostics are
in `strong/nomination-discount-validation-analysis-v1.json`.

Full trained outputs, logs, original bucket receipts and independent audits are
archived in private dataset `coyotte508/powergrid-ai-training-v1`, revision
`f0ff1b85261a875d1df5dfd39dd8c783fe559aad`,
`evidence/nomination-discount-training-v1.tgz`.
Descriptor: `strong/nomination-discount-training-evidence-v1.json`.
Report: `strong/nomination-discount-training-results-v1.json`.
Do not rerun the completed training or repeat its collector.

All four float64 ONNX exports preserve the stored weights and passed strict
native/ONNX checks on 5,770 nomination + 256 other-phase positions each. Choices
matched throughout; maximum absolute output error was below 2e-10. The original
parent's other-phase choices/outputs also matched. These are local inference
checks, not simulations or new training.

The isolated development runtime adds schema 4.4 registration only; original
engine rules, legal menus, loss filter, historical artifacts and confirmation
policies remain unchanged. It explicitly rejects final-game contracts. Public
serving passed 402 existing fixtures per policy, spanning all 20 player-count /
rule combinations and first/last cases for each phase/menu group. The copied
parent matched the original on all 402; all four trained policies matched the
parent on all 332 non-nomination cases. The first preflight caught an omitted
schema registration in `hybrid-continuations.cjs`; its failure is preserved under
`runs/nomination-discount-development-v1-preflight-failure-01/`. It was repaired
before source upload or any HF game execution.

**Development screen: 3,200 Germany games / 50 jobs.** The unchanged parent and all four
trained arms face fixed `search_geo` and a260 opponents, at every count 2–6,
Original/Recharged × open/sealed. Four independent deals per cell, all seat
rotations, shared seeds across arms. Compare paired deal-level differences, and
treat four deals as a screen rather than precise qualification. New seed namespace
`nomination-discount-development-v1-{players}p` is separate from training,
confirmation and reserved final seeds. No candidate search is enabled; the
existing building-loss filter is retained identically.

Source overlay is archived at private dataset revision
`b2f0cc2e891f63efd0772376132328520659fef9`,
`strong-source-nomination-discount-development-v1.tgz`. It pins the unchanged
current-engine source separately and verifies every overlay before applying it.
All 50 actual runner contracts passed non-executing validation.

The first two original endpoint jobs were submitted and effective configuration
checked (4 CPU workers, one inference thread, `cpu-upgrade`, five-hour timeout):

- `6ae3c67c0e0338d1bb7c3def` — d1-all1 vs search_geo, 2 players, 32 games.
- `6ae3c67d0e0338d1bb7c3df2` — d1-all1 vs search_geo, 6 players, 96 games.

The other 48 shards remain unsubmitted until both originals pass collection.
Use `strong/collect_nomination_development_v1.py --collect` with the usual
`PYTHONPATH=ai/strong ai/.venv/bin/python -u -B` prefix. It observes only original
handles, verifies retained archives and reruns the raw game/decision audit in the
isolated runtime. Once both endpoints are verified, use
`strong/manage_nomination_development_v1.py --launch 48`. Never overwrite launch
intents, retry ambiguous submissions or silently replace failed games. This is a
finite fixed screen, not a recreated objective or background automation.

Exact controls and handles: `strong/nomination-discount-development-protocol-v1.json`,
`strong/nomination-discount-development-source-v1.json`,
`strong/nomination-discount-development-launch-v1.json`.
Read `runs/nomination-discount-development-collected-v1/state.json` for the latest
observation. Final comparison and archival collection remain pending.

The older confirmation collector's missing-log failure remains separate and
unresolved; its STOP and original data are preserved. Do not let this new screen
stand in for that unfinished study or claim it qualifies either old or new models.

## Previous continuation — teacher audit complete, GPU training submitted

All **60 original teacher jobs completed**. The independent collector checked
**5,770 roots / 1,940,544 action-world continuations**, with **zero truncations**.
Aggregate worker-program time was **615,244.39 seconds / 170.90 job-hours**;
continuation computation accounted for 607,289.66 seconds. These are summed job
times, not elapsed wall time or a monetary bill.

The two fixed 32-world halves share a best action on **3,844 / 5,770 roots (66.6%)**.
For nonbaseline margins exceeding 0.025 in magnitude, **12,451 / 16,734 (74.4%)**
have the same sign in both halves. All ten natural low-cash roots have zero sampled
advantages. Targets therefore remain soft, uncertainty-weighted paired advantages;
there are no forced winner labels or claims that these targets establish strength.

Full raw evidence is downloaded, independently audited, and archived immutably in
private dataset `coyotte508/powergrid-ai-training-v1`, revision
`f1d17a40e4ff6a188617a5dc7fac43cc20735393`,
`evidence/auction-discount-teacher-complete-v2.tgz` (139,419,264 bytes).
The descriptor `strong/auction-discount-teacher-evidence-v2.json` binds archive,
manifest and revision; do not re-upload or regenerate the completed teacher set.

The frozen four-way comparison trains a **new nomination-only correction** over
the unchanged parent. Its inputs are explicit Recharged discount off/on crossed
with old/all-legal nomination coverage. Other phases and value outputs remain
the frozen parent. Every arm starts with identical hidden weights and zero new
outputs; four seeds vary minibatch order. The old coverage mask matches all
historical option sets available for comparison. There are 4,326 training roots
and 1,444 validation roots, split by whole deal as before.

| Arm | Discount inputs | Nomination menu | Original HF job |
| --- | --- | --- | --- |
| d0-all0 | Off | Old shortlist + parent | `6ae3ac9d0e0338d1bb7c2560` |
| d0-all1 | Off | Every legal choice | `6ae3ad90c78863f9c62dd3cd` |
| d1-all0 | On | Old shortlist + parent | `6ae3ad98c78863f9c62dd3db` |
| d1-all1 | On | Every legal choice | `6ae3ad9c0e0338d1bb7c26c8` |

All four effective source/resource configurations were independently verified.
They request one L4 each with a three-hour timeout. **At submission they were
SCHEDULING, waiting for requested hardware; no gradients were observed yet.**
Check `runs/nomination-discount-training-collected-v1/state.json` for the latest
bounded observation rather than assuming they are running. No failed-job retries,
automatic objective, or background collector was started.

Recipe: seeds 15101–15104; 120 epochs each; batch 256; AdamW learning rate 0.0003,
weight decay 0.001; gradient norm limit 1. Checkpoint selection is each seed's
lowest validation simulated regret, with earliest ties. All four seeds enter
their arm's ensemble, using mean minus seed standard deviation and margin 0.025.
This penalty is not calibrated confidence. Expected updates are 2,040 per seed /
8,160 per arm / 32,640 total if all runs finish; verify actual counts.
The complete frozen recipe is `strong/nomination-discount-training-design-v1.json`.

Initialization and scope checks passed on **23,080 actual nomination cases** and
**1,024 non-nomination cases after changing the new heads**. All values and other
phases stayed exact; discount-off arms ignore the appended discount features.
Twenty-five tests passed, covering teacher corruption rejection, legal menus,
uncertainty routing, negative outcomes and transport identity checks.

Training source, data and parent are archived at private dataset revision
`e534cbd61c2bfa1f506c37dd195be9725f376639`,
`strong-source-nomination-discount-training-v1.tgz`, SHA-256
`1fa646d432ce7ae34f04328b317fb3ae56aa883a7c7a3d1ed88e66a5e5609682`.
Descriptor: `strong/nomination-discount-training-source-v1.json`.
Exact handles: `strong/nomination-discount-training-launch-v1.json`.
Original intents/configuration checks: `runs/nomination-discount-training-source-v1/launches/`.

Next resume, use `PYTHONPATH=ai/strong ai/.venv/bin/python -u -B
ai/strong/collect_nomination_training_v1.py` for a bounded status check, or add
`--collect` for completed original jobs. It never submits jobs. Inspect existing
reports/receipts first; preserve partial work and failures. The collector verifies
remote hashes, all four retained members, frozen parent tensors, optimizer counts,
checkpoint selection and independently recomputed CPU metrics. It also checks
trained non-nomination routing on actual stored inputs. **This collector has unit
coverage but has not yet been exercised on completed training output.**

After all four training audits, archive outputs immutably, verify export/serving
parity and run fresh whole-game development comparisons across 2–6 players and
all four rule combinations. Do not select a winner from target fit alone or reuse
the frozen confirmation/reserved final deals. No candidate is qualified.

The sections below describe the original teacher launch and its recovery paths;
the completion figures above supersede their in-flight snapshots.

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

The separate fixed confirmation finisher, former PID **502682**, stopped at
**19:22:01 UTC**. HF marks original job `6ae381225ddcdc083026324a` COMPLETED but
returns `No logs available`, so its final receipt was unavailable. Preserve
`runs/current-auction-failed-bucket-hf-v3/STOP.json`, original logs and terminal
records. An independently discovered final archive was downloaded and all 253
manifest files verified; its 24 games have **not** passed the full independent
audit or been admitted by the frozen comparison. See
`strong/current-auction-log-availability-recovery-v1.json` and
`runs/current-auction-log-availability-recovery-v1/`. No games were rerun and the
finisher was not restarted. Resolve this collection provenance separately from
the new training experiment.

Do not stage the pre-existing modified `policy-iteration-development-status-v2`,
`policy-iteration-labels-results-v2` or `policy-iteration-labels-status-v2` JSON
files. Keep original dispatcher STOP markers and failure histories intact.
