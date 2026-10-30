# Auction training resumed — 29 October 2026

The user removed the automatic objective and explicitly asked to continue
research and training in this chat. Do not recreate an objective. The separate
confirmation finisher stopped on a missing HF log receipt; its frozen policies,
deals and selection criteria are unchanged. No game deployment is part of this work.

## 30 October, 18:22 Paris — six-player check complete; end this candidate iteration

All four latest original jobs completed in **98.0–100.2 minutes**. Their 384 games
passed independent raw auditing, with zero game or rollout caps. Reusing the
previously audited d1-all1 pilot gives **480 six-player games**, and **960 audited
games overall**. Every assigned job is terminal; no new jobs were launched.

| Arm | Two-player credit / 32 | Four-player credit / 64 | Six-player credit / 96 | Six-player Recharged sealed / 24 |
| --- | ---: | ---: | ---: | ---: |
| Parent | 19 | 32.5 | 51 | 11 |
| d0-all0 | 18 | 30 | 51 | 9 |
| d0-all1 | 19 | 31 | 53 | 9 |
| d1-all0 | 20 | 31 | 48.5 | 8 |
| d1-all1 | 19 | 32.5 | 51 | 10 |

The six-player maximum, d0-all1, is **55.21% vs parent 53.13%**: 15 improved
outcomes and 13 worsened, net +2 wins. It improves on two deal seeds and worsens
on two, and its four-player result was below parent. No candidate consistently
improves across counts. Every candidate is below parent in Recharged sealed at
four and six players. The policy changes do affect games (35–67 changed final
states out of 96 at six players), but there is no convincing net strength gain.

These are descriptive development results against search_geo on Germany with
public money, four independent deal seeds per count reused across all seats and
rules. They neither establish a statistically reliable regression nor confirm
the best observed arm as stronger. Prior win rates from different experiments
are not directly comparable. Reserved final seeds remain unused.

**Stop this nomination-only candidate iteration; keep the parent.** The remaining
**35 shards / 2,240 games** stay deferred. More epochs on the same targets are not
justified. The next investigation should examine sealed-bid decisions and the
reliability of simulated training targets, including their opponent population,
using existing traces first. These are proposed diagnoses, not established
causes. The broader AI research has not been abandoned, but no new training or
evaluation was launched during this check, and no model is selected or qualified.

Evidence: `strong/nomination-discount-6p-search-geo-results-v1.json` and
`strong/nomination-discount-six-player-complete-v1.json`. The completion report
binds all five original six-player handles, audit hashes, raw bucket archives,
measured times, and the earlier two/four-player comparisons. The separately
stopped confirmation finisher and missing log receipt are unchanged.

## 30 October, 14:42 Paris — no four-player gain; final count-endpoint cross-check running

All five original four-player jobs completed in **30.6–35.3 minutes** and all
**320 games** passed independent raw audits with zero caps. The frozen parent
remains at least as good as every candidate on this small paired screen:

| Arm | Win credit / 64 | Rate | Recharged sealed / 16 |
| --- | ---: | ---: | ---: |
| Parent | 32.5 | 50.78% | 4 |
| d0-all0 | 30 | 46.88% | 2 |
| d0-all1 | 31 | 48.44% | 2 |
| d1-all0 | 31 | 48.44% | 3 |
| d1-all1 | 32.5 | 50.78% | 3 |

Fractional credit reflects shared wins. There are four independent deals with
all seats/rules, so do not treat the 64 repetitions as independent observations.
The d1-all0 candidate that had a +1 two-player margin regresses by 1.5 win credits
here; its final state differs from the parent in 52/64 games. Its changes therefore
affect play, but the learned corrections have not delivered a net improvement.
All candidates are lower in the small Recharged sealed subgroup.

Comparison and proofs: `strong/nomination-discount-4p-search-geo-results-v1.json`,
`strong/nomination-discount-four-player-complete-v1.json`. Each binds all original
handles, raw bucket receipts, immutable hashes and independent audits. This is
not evidence of a statistically established regression, nor evidence that any
candidate is stronger. **Current nomination-only training appears stalled**;
the user was informed. More epochs on these same targets is not the next action.

One bounded endpoint check remains: four original **six-player/search_geo** shards
for parent, d0-all0, d0-all1 and d1-all0, **384 games** on parallel HF cpu-upgrade
jobs. Reuse the previously completed/audited 96-game d1-all1 pilot; no games are
repeated. Exact handles: `strong/nomination-discount-six-player-launch-v1.json`.
Original source, heads, settings, seeds, legal menus and rules remain unchanged.

Submitted around **14:40 Paris, 30 October**. Expected **2.5–4 hours plus queue
delay**, based on the matching pilot's 3.08-hour runtime; five-hour hard timeout.
Suggested user ping **19:00 Paris today**. Collect with the existing bounded HF
collector, then compare via `strong/compare_nomination_multiplayer_v1.py --players 6`.
This closes the two/four/six-player search comparison across all five arms.
If gains remain absent, finish this candidate iteration and diagnose sealed-bid
decisions and simulated-target reliability before new training or more evaluation.
Remaining **35 shards / 2,240 games** are deferred, not silently completed.
**576 audited / 960 assigned / 3,200 planned**. No candidate qualification, final
seed use, new gradients, mini-PC jobs, automatic objective or deployment.

## 30 October, 11:09 Paris — two-player results audited, four-player comparison submitted

The finite mini-PC queue completed all 96 original games in **9m41s**, finishing
at **09:39:57 Paris**. The same independent raw auditor used for HF passed every
game with zero caps. Original output is archived in the private model repo;
`strong/nomination-discount-minipc-batch-results-v1.json` binds all three immutable
archive revisions/hashes and audit hashes. The queue is terminal; do not restart it.

All five arms now have the same 32 two-player/search games:

| Arm | Win credit / 32 | Paired gains / losses vs parent |
| --- | ---: | ---: |
| Parent | 19 | — |
| No discount input, old shortlist (d0-all0) | 18 | 4 / 5 |
| No discount input, all choices (d0-all1) | 19 | 0 / 0 |
| Discount input, old shortlist (d1-all0) | 20 | 7 / 6 |
| Discount input, all choices (d1-all1) | 19 | 0 / 0 |

Report: `strong/nomination-discount-two-player-results-v1.json`, generated from
all five verified original raw outputs. All paired keys, seats, rules and model
identities checked. There are only **four independent deals**, with eight
seat/rule repetitions each. The apparent +1 win does not establish superiority;
the leading arm changes many trajectories and has both positive and negative
deal-level differences. No model was selected or qualified. Current evidence
does not justify claiming that training has delivered a strength improvement.

The next bounded allocation retains **all five frozen arms at four players**:
five HF `cpu-upgrade` jobs, four workers each, **320 games** against search_geo.
Exact handles/configuration checks are in
`strong/nomination-discount-four-player-launch-v1.json`. Only the existing fixed
protocol names were submitted; the source, models, seeds and game rules are
unchanged. The launcher now supports an explicit `--name` filter; three focused
tests check exact selection, rejection of invalid/duplicate names and unchanged
default ordering. Earlier handles remain in the aggregate launch file.

Expected **45–75 minutes plus queue delay**, based on eight previous current-engine
parent/search/4p shards taking 32.9–41.2 minutes for 64 games. Suggested user ping:
**12:30 Paris, 30 October**. Use the existing bounded HF collector with `--collect`;
do not resubmit originals. After collection, audit and compare all arms at four
players before another allocation. **256 audited / 576 assigned / 3,200 planned**;
39 shards / 2,624 games remain unsubmitted. No new mini-PC jobs, gradients,
reserved final seeds, automatic objective, candidate qualification or deployment.

## 30 October, 09:31 Paris — mini-PC pilot audited, next three arms running

The parent comparison shard finished in **172.37 seconds** on the actual 8840U;
all **32 games** passed independent raw auditing, with zero caps. The paired
parent and d1-all1 two-player/search screen both won **19/32**; every paired
win-credit difference is zero. No strength gain is established by this small
four-deal screen. See `strong/nomination-discount-parent-2p-comparison-v1.json`.

The next finite queue runs **d0-all0, d0-all1 and d1-all0 vs search_geo, 2p**:
three original shards / **96 games**, four workers within each shard, sequential
shards. It started at **09:30:15 Paris, 30 October**, PID **126379** on `minipc`.
Estimated **10–20 minutes**, suggested ping **09:50 Paris** (supersedes the earlier
09:40 suggestion). Six games had completed at 09:31. **160 games audited** so far;
**256 games assigned**, with **44 shards / 2,944 games unsubmitted**.

The copied runtime, models, seeds and auditor are byte-identical to the frozen
screen. The new queue changes only which already-authorized names may execute.
All three runner contracts passed non-executing validation with the dependency
fix before launch; the copied artifact retains the prior 2,010 exact-choice proof.
It stops on first failure, never retries, and cannot expand its three-name list.
Five focused tests cover reservations, progress accounting and failure stopping.

Use `strong/manage_nomination_minipc_batch_v1.py status` / `collect` with the usual
Python/PYTHONPATH prefix. Active handles:
`strong/nomination-discount-minipc-batch-launch-v1.json`.
Remote root: `/home/coyotte508/powergrid-ai-nomination-development-minipc-batch-v1/`.
Check `state.json`, `run.log` and `outputs/<name>/runner.log`; keep original logs,
intents and partial evidence on any failure. No new HF jobs or automatic objective.

## 30 October, earlier — HF endpoints audited, mini-PC parent comparison started

All 128 games from the two original HF endpoint jobs passed independent raw
auditing with zero caps. The 32-game two-player shard took 318.74 worker seconds;
the 96-game six-player shard took 11,097.73 seconds. The runtime difference matters
for allocation; saved-position inference speed alone does not predict game speed.
`strong/nomination-discount-development-pilots-v1.json` retains exact original
handles, immutable bucket receipts and independent audit contents/hashes.

At the user's request, the next original shard runs on the 8840U mini PC:
`pg-nom-dev-v1-parent-search-geo-2p`, 32 games, four workers, unchanged protocol,
seeds, model, opponents, engine, legal menus and independent audit. This supplies
the matching parent comparison and a whole-game throughput measurement. All 2,010
saved choices (402 for each of five policies) matched before game execution.
Node remains 24.14.0; remote Python 3.12.3, NumPy 2.5.3, ONNX Runtime 1.30.0.

Actual game supervisor **PID 118285**, started **30 October at 09:23:23 Paris**;
4/32 games completed by 09:23:58. Estimated duration **5–15 minutes** based on the
matching HF shard, still provisional. User advised to ping at **09:40 Paris**.
No further automatic dispatch. The five-hour safety timeout is not the expected
duration. After launch, 160 games are assigned in total and 3,040 games / 47
shards remain unsubmitted. Only the original HF 128 are independently audited.

The first mini-PC supervisor (PID 118249) stopped on a missing huggingface_hub
import in the runner's non-executing validation, before its output existed.
Zero games ran. Original failure log, intent and launch record remain intact.
An explicit recovery added the already installed dependency directory to
PYTHONPATH, passed non-executing contract validation, and started the game process.
It did not replace, rerun or discard game results. Frozen runtime/package unchanged.

Use `PYTHONPATH=ai/strong ai/.venv/bin/python -u -B
ai/strong/manage_nomination_minipc_v1.py status`, then `collect` after completion.
The latter downloads original output, checks the complete file manifest and runs
the same independent raw auditor as the HF collector. Active launch and progress:
`strong/nomination-discount-minipc-launch-recovery-v1.json` and
`strong/nomination-discount-minipc-progress-v1.json`.
Remote logs are under `/home/coyotte508/powergrid-ai-nomination-development-minipc-v1/`.
The shared reservation prevents the HF launcher from duplicating this shard.
Do not repeat prepare/launch/recovery or assume these results establish improvement.

## 29 October — GPU training audited, full-game screen prepared

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
The user's subsequent compute preference permits running these CPU evaluations
on `minipc`. Leave the original two HF jobs intact. Before releasing the other
48 to HF, assess mini-PC whole-game throughput on an original unsubmitted shard
using an adapter with the same pinned inputs and raw audit. Existing 8840U
saved-position timings support trying this, but do not establish batch duration.
The current launcher below is HF-specific; no mini-PC game was launched when
recording this preference, and the frozen protocol/source were not changed.
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
