# Power Grid AI — active continuation, 10 October 2026

**No candidate has passed the full strength gate. Nothing is deployed. Reserved
final-test seeds remain unused.** The separate UI redesign was reverted.

Use `/home/eliheros/Documents/Codex/2026-09-26/je-x20-2/work/powergrid-ai`, branch
`ai/germany-baseline`. The preceding AI goal turn implemented and launched the
sealed-menu experiment below: **progress**. The intervening UI reply only confirmed
the requested revert; it made no AI progress. This continuation recovered and
authoritatively inspected the actual HF handles, reviewed the experiment,
verified its saved validation hashes, and independently collected another
3,680-game final-checkpoint screen. This turn is **progress**. No candidate is
qualified and there is no external blocker.

## New result: homogeneous final checkpoint, primary pair available

Independent collection from coordinator snapshot
**`0935d49415181c52eb30e8d3da4ab2fa62e96f53`** verifies homogeneous update19:
all training/checkpoint hashes and provenance, 2,553 strict parity requests,
six complete arena cells, **3,680 games with zero truncations**. Checkpoint
revision **`cc86f7a36392c829e44fd81d9dbf362cb74a0b1b`**; raw result revision
**`af1a3e2cda076beee87483d0a38178e045dceffe`**. Local artifacts are under
`ai/runs/population-homogeneous-u19-v1`; tracked full count/rule results and all
paired contrasts are `strong/population-homogeneous-u19-screen-v1.json`.

| Final homogeneous win share | Econ 2p | 3p | 4p | 5p | 6p | A260 3p |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| % | 61.875 | 61.25 | 60.156 | 75.75 | 74.896 | 41.667 |

Two-player rule cells are original/open65%, original/sealed60%,
Recharged/open67.5%, Recharged/sealed55%. The two-player economic floor66.25%
still fails. Against the same parent/deals, overall gains of4.53pp in2p
([-2.34,11.41]) and5.10pp againstA260 ([-1.88,12.29]) are inconclusive.

The predeclared primary **heterogeneous-minus-homogeneous update19** pair is now
available: economic2–6p differences are -6.56,+2.60,+3.59,0,-0.73pp; A2603p
is+2.81pp. **All six overall95% whole-deal intervals include zero.** In2p the
interval is[-14.06,+0.94]pp, and A260[-3.23,+8.96]pp. This is one training-seed
pilot with exploratory marginal intervals; do not claim a clear superior
population recipe, pool player counts, or select update9 in place of prescribed
update19. All rule strata and regressions are retained in the report.

Population control update19 and the full three-arm comparison remain pending;
the existing population coordinator owns their evaluation. The four H200 runs
are a separate paired input ablation with heterogeneous opponents fixed in both
conditions, not evidence that heterogeneous training has won this comparison.

## Latest: frozen-weight sealed-bid experiment running

HF job **`6aca28c7fee2c90070187151`** was launched successfully at 12:00 UTC,
10 October. Inspected RUNNING at 12:03 UTC; subsequent logs reached the control
economic 5p cell. **Do not rerun `launch-sealed-menu-pair.py`**: persistent launch
intent is `ai/runs/sealed-menu-pair-launch-v1.json`, mirrored by
`strong/sealed-menu-status-v1.json`. An observation timeout is not a failed job.

This is an inference experiment, with **no optimizer updates**. It holds original
H200 u79 tensors and ONNX graph fixed, and adds revision `4.0-sealed-all-bids` to
allow every engine-legal sealed bid. The menu-relative best-heuristic flag retains
its definition but is recomputed on the larger menu. Open menus and other model
revisions stay unchanged. Neural actions now dispatch through the acting model's
menu; search with the new revision is explicitly rejected because its proposal
indices have not been adapted. The experiment does not change either running
training cohort, older opponent identities, final gates, or published UI.

Validation, saved at model revision **`42593c73c1f2d778c9eea8ec0c71bb8e408d6228`**,
prefix `runs/sealed-menu-initial-v1`:

- All 2,553 original encoder outputs and actor menus match their pre-edit
  references exactly; hidden deck/seed/sealed bids/queued plans do not affect the
  new encoding. All added 3,002 bids apply successfully on independent engine
  copies. Of these fixtures, 42 sealed menus expand. This is fixture coverage,
  not a prevalence estimate or evidence of better play.
- Separate engine-legal fixtures preserve all requests, leaving the original
  pruned fixture file untouched. New fixture SHA256 is
  `0a43c0234b810253d07ef7281ee3e83c8fe7a4fa27e8aa05bd6589c024661883`.
- 176 complete integration games, every count/rule/seat against a frozen neural
  opponent plus new heuristic modes: no caps; 155 formerly omitted bids actually
  played; all 40 paired open-game result records exactly identical. Records
  include terminal player summaries and action counts, not entire trajectories
  or the complete terminal engine state.
- All 2,553 strict single-request export checks and engine-legal serving checks
  pass. Saved initial files' hashes were reverified in this continuation. No
  batch16 parity or current-model AMD8840U latency claim is made.

Frozen protocol: `strong/sealed-menu-protocol-v1.json`. Each condition plays
**7,520 fresh development games**, 40 deals/count × every seat × four rule cells:
economic 2–6p, capacity-aware economic 2p, A260 3p, plus separately named
full-sealed-menu economic 2–6p and capacity-aware 2p references. The latter are
additional references, not assumed stronger or replacements for existing gates.
Both conditions run sequentially on one CPU-performance host (24 workers, four
hour limit) to avoid CPU-host differences in the required 3,760 paired open-game
record identity check. Seed prefix `sealed-menu-development-v1-{players}p`;
20,000 whole-deal bootstrap samples, seed10041. Report every count/rule/reference
contrast and regression; intervals are exploratory and not multiplicity-adjusted.

Source archive `strong-source-sealed-menu-20261010-v1.tgz`, dataset revision
**`e571f96d453a4b148a3185b99cb047655b6a4f75`**, SHA256
`e9de0cc444c843d5b298d5070298902f613a19aa1fab7d568093fa939871b993`.
All source/model/fixture pins are in `strong/sealed-menu-{source,initial}-v1.json`.
The expanded PT/ONNX carry a distinct revision tag and an explicit untrained
transfer record. They are not a newly trained or qualified model.

When complete, pin a model-repo revision and independently run
`collect-sealed-menu-screen.py {control|expanded} REV OUTPUT`, then
`compare-sealed-menu-screens.py CONTROL EXPANDED --output REPORT`. Compare the
reproduced report to `runs/sealed-menu-pair-v1/comparison.json`; screen evidence
lives at `runs/sealed-menu-screen-v1-{control,expanded}`. The pair wrapper uploads
failure evidence too. Any open-game mismatch invalidates an isolated-menu effect
claim and must be diagnosed before interpretation. Reserved final seeds unused.

At 12:03 UTC the four H200 ablation trainers, population control trainer and both
coordinators were all authoritatively RUNNING. Population homogeneous training
was COMPLETED, with its six update19 screens still being collected by the old
coordinator. Do not manually duplicate those screens. H200 logs subsequently
showed completed updates14–15 and ongoing updates15–16; final update19 evaluation
is still owned by `6aca236f095c578089311e41`.

## Latest: parent reference complete, automatic final evaluations, bid-menu audit

The parent screen **COMPLETED**, HF job `6aca2110095c578089311b47`. Independent
collection at model revision **`616b253875d3219667a3041ae192a2d46f2fbb92`** verified
all artifact/source/protocol hashes, all 2,553 strict export and legal serving
checks, and all 4,000 game outcomes with zero truncations. Exact 40 deals, every
seat and all four rules in each of seven cells; final reserved seeds unused.
`strong/five-plant-parent-screen-v1.json` contains all count/rule cells and
20,000-bootstrap whole-deal intervals. Raw local data is
`ai/runs/five-plant-comparison-v1/parent`.

| Parent on fresh ablation deals | Econ 2p | 3p | 4p | 5p | 6p | Corrected econ 2p | A260 3p |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Win share (%) | 54.06 | 62.81 | 56.56 | 75.75 | 73.70 | 50.63 | 38.96 |

The original/open 2p subgroup against economic is 38.75%. These are different
fresh deals from prior screens, not a change in the frozen parent. Compare each
new model against these same paired deals; never compare unpaired percentages
across seed sets as a training effect. This is an unqualified reference, not a
new candidate or evidence the two-player gap has closed.

### Evaluation ownership: do not manually duplicate any new ablation screen

New CPU-basic coordinator **`6aca236f095c578089311e41`** is RUNNING (confirmed
11:38–11:39 UTC). It has collected the existing parent without starting any new
parent games. It owns **all four final update19 ablation evaluations**. It waits
for each named trainer to be authoritatively COMPLETED, validates the final
wrapper/checkpoint/metrics, pins an immutable model revision, and launches one
CPU-performance screen per final model. Intermediate checkpoints/internal best
are never selected. It independently collects the seven cells and compares
both training seeds after all five reference/candidate screens are verified.

- State: model repo `runs/five-plant-coordinator-v1/state.json` (pin a repo revision).
- Config/source/status: `strong/five-plant-coordinator-{config,source,status}-v1.json`.
- Source archive: `strong-source-five-plant-coordinator-20261010-v1.tgz`.
- Dataset revision: **`f9097a2f61eeeef636b13f9f92a9320149c1ff64`**.
- Source SHA: `aad13711f2ebfdeb27b9f5ed089a28ef23a7dc56a6793b83530534f64d7fdba1`.
- Persistent launch intent: `ai/runs/five-plant-coordinator-launch-v1.json`.
- Four local screen intents are reserved as `coordinator_owned` under
  `ai/runs/five-plant-screen-launches-v1`; do not delete or bypass these guards.

It persists intents before submission, never retries an ambiguous POST, keeps
observing the same handle after a read timeout, and only treats explicit HF
terminal stages as terminal. Failures do not abandon live peers. State-only
recovery rehydrates exact pinned artifacts before comparison. Ten focused
failure/recovery tests pass; the five screen-validation tests and existing
80-game mixed-revision integration test also pass (16 tests total). Its startup
tests passed on HF, then parent collection succeeded. Final learner collection
is still pending and must not be inferred from parent success.

The old population coordinator `6aca0d29095c578089310fca` separately retains
ownership of homogeneous/control update19 and all-arm comparisons. Do not mix
their states or manually duplicate either coordinator's work.

### Confirmed action-menu limitation; diagnostic only, not a strength result

`ai/core.cjs::candidates` prunes bids when more than 48 are legal: first 8,
multiples of 10, and maximum. The exact current runtime was checked against the
immutable training source. Audited all 2,553 serving fixtures: 564 bid positions,
142 pruned (100 open,42 sealed), all non-bid legal moves preserved. In 14 sealed
positions, all bids preferred by the economic heuristic were omitted. Both
original and capacity-aware heuristic preferences had the same omission counts.
This is a stratified fixture corpus, **not a prevalence estimate**.

A separate read-only encoding/inference audit evaluated all legal bids on those
142 positions using frozen original u79 weights. State and all existing action
features except the menu-relative best-heuristic flag (index 75) remained exact;
the temporary candidate override was restored exactly and no game state changed.
The model changed 13 sealed choices, 12 to bids absent from its original menu
(4 of these were in 2p). All 100 pruned open-auction choices stayed unchanged.
PyTorch/ONNX strict single-request logits/values and chosen actions agreed on
both original and expanded sets of 142 positions. Example changes 40→48 or 8→9 are model
preferences, **not proof of better play**. No games or gradients ran for this
audit, and no production encoder/baseline/training job was changed.

Raw coverage, per-position choices, encoded pairs and runnable audit scripts are
persistent in model repo `runs/bid-candidate-audit-v1`, revision
**`4b8c97343d4be022d003002e5781bdfdca527041`**. Tracked summary/provenance:
`strong/bid-candidate-audit-v1.json`. It supports a future separately frozen
full-legal sealed-bid experiment with unchanged weights, paired outcomes, all
existing baselines plus appropriate unpruned opposition. Do not alter the
running two-seed input ablation or call this a demonstrated strength gain.

**Fixture caveat for that future experiment:** existing fixture `legal` lists
are `c.candidates`, a pruned subset of engine legality. An expanded-menu encoder
needs a separate fixture manifest built from exact engine `allLegal` lists and
identical requests, plus a versioned per-actor action-menu/encoder contract.
Do not weaken current checks, mutate existing fixtures, apply a global override
in actual games, or silently change retained opponents. The diagnostic override
in `encode-full-bid-audit.cjs` is for isolated read-only inference only.

## Previous: final population result and two-seed input ablation (11:29 UTC)

The original **heterogeneous update19** trainer has COMPLETED. Its prescribed
final development screen is independently verified: 3,680 complete games, all
40 deals × every seat × four rules, no caps, all 2,553 strict export checks.
Checkpoint revision **`3a71c9d1d7300a2d2169e059e8d9242167e73625`**; result revision
**`7055d120f9e503694fd58575d0e91e118e18dfa3`**. Local raw data:
`ai/runs/population-heterogeneous-u19-v1/heterogeneous-u19`. Source/metrics/export
hashes are in its `checkpoint.json`, with independent evidence in the parent
`verified.json`. `strong/population-heterogeneous-u19-screen-v1.json` preserves
all absolute cells and paired comparisons against both original parent and u9,
including every rule subgroup.

| Final heterogeneous | Econ 2p | 3p | 4p | 5p | 6p | A260 3p |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Win share (%) | 55.31 | 63.85 | 63.75 | 75.75 | 74.17 | 44.48 |

Against parent: A260 +7.92 pp [2.50,13.33], economic4p +3.67 pp [0.16,7.19],
but economic2p -2.03 pp [-8.44,4.38]. These are marginal exploratory paired-deal
intervals, one training seed, not multiplicity-adjusted. Original/sealed economic2p
is **48.75%**, and overall two-player performance misses the unchanged 66.25%
floor. Do not promote this model or select u9 instead based on these outcomes.
All-arm primary comparison is still pending; the original coordinator owns it.
At 11:22 UTC the other two original trainers and coordinator were confirmed
RUNNING. At 11:27 the coordinator snapshot (`528bf019eee9f0aa9d16ae59e72f65327d381d38`)
still had only heterogeneous-u19 collected; all u9 arms are complete. Inspect
actual job states before any recovery. Never duplicate coordinator-owned screens.

### Four independent H200 training jobs, final checkpoints only

`strong/five-plant-ablation-protocol-v1.json` is immutable and authoritative.
Both conditions start from **identical weights transferred from original H200u79**,
not an unfinished population winner. Same 985,346-parameter architecture, full
encoder work, optimizer, retained opponent mixture, seeds and schedules; the
control masks only the appended 66 state and 2 action inputs. Existing feature
prefixes, priors and teacher labels are unchanged. Two seeds (10031,10032),
20 updates × 240 complete games, 48/count/update: **4,800 games/run**, 19,200 total.
Four independent H200 learners (not four GPUs on one learner); measured full-update
speedup over optimized CPU is 1.39×. All gradients remain on HF Jobs.

| Run key | HF job |
| --- | --- |
| control-s10031 | `6aca1efa095c578089311a40` |
| full-s10031 | `6aca1efa095c578089311a42` |
| control-s10032 | `6aca1efb095c578089311a44` |
| full-s10032 | `6aca1efcfee2c90070186af2` |

All four confirmed RUNNING at 11:27 UTC, update2 in progress or just completed,
with no caps in the observed completed batches. Full final validation is pending.
`strong/five-plant-ablation-status-v1.json` records launch intents and observations;
`ai/runs/five-plant-ablation-launches-v1` holds local no-duplicate launch guards.
Do not rerun launchers. Training source is `strong-source-five-plant-ablation-20261010-v1.tgz`,
dataset revision **`8349b1348a9d6d7fd9efe4382d77619d75fcc14d`**, SHA
`aeaf45968ec6054009a546ff22a01cb4ae32487c3be3b43025530284aabfc104`.
Initial weights and audit files: model revision
**`22fe3c03faaae01225cab24e9ecedda654df835b`**, `runs/five-plant-ablation-initial-v1`.
Exact hashes are in `strong/five-plant-ablation-initial-v1.json`.

**Inherited numerical limitation:** original u79 and its full-input transfer both
fail strict ONNX batch16 tolerance on the same one logit; all actions agree.
All 2,553 strict single-request checks pass for original/full/control. PyTorch
transfer is exact at both batch1 and16; training uses PyTorch. No tolerance was
weakened. Preserve `initial-numerical-audit.json`; do not claim all batched export
checks passed. The earlier u9 diagnostic transfer passed both batch sizes, a
different checkpoint. New final candidates must pass strict single-request export
and legal serving checks. Initializers are not deployment candidates.

### New development evaluation and next steps

`strong/five_plant_screen.py` validates all final artifact hashes, initialization,
frozen opponents, all 20 balanced batches, game/search caps, snapshot admission,
finite weights and zero/nonzero extra projections. It then runs strict parity and
legal serving on all 2,553 fixtures before seven independent evaluation cells.
Each final candidate and original parent gets **4,000 games**: economic2–6,
capacity-aware economic2p, frozenA2603p, on the same40 fresh development deals per
count (`five-plant-ablation-screen-v1-{players}p`), all seats/rules. No search added
to candidate. Only final latest update19 is compared; update9 is recovery-only.
Original economic remains a separate baseline; corrected economic is evaluation-only.

The parent's evaluation is RUNNING as CPU-performance job
**`6aca2110095c578089311b47`**, run `five-plant-screen-v1-parent`. At 11:29 UTC
all 2,553 strict export and legal serving checks had passed; economic2p/3p/4p
game cells completed, remaining cells running. No aggregate result collected yet.
The original homogeneous/control trainers were at updates16/14 and coordinator
RUNNING (see `strong/population-and-screen-observed-20261010-v3.json`). Check actual
status; `strong/five-plant-screen-status-v1.json` is only the last observation.
Immutable evaluator source `strong-source-five-plant-screen-20261010-v1.tgz`,
dataset revision **`79480a2c32e9ecdffce00440e1150cb857c18d1e`**, SHA
`2540dd5ccaee671baf47467c9e184dd7dda602de98cf07b898fff15f7ccc96b0`.
Five evidence-rejection tests pass (wrong encoder/model/opponent, missing paired
seat/rule/deal, actual/search caps, repeated deals). All six old final population
cell verifications reproduce unchanged after optional encoder-tag support.

The new coordinator described above now owns every final screen. Do not manually
launch `launch-five-plant-screen.py` while it is live, and never bypass recorded
intents after observation timeouts. Only reconcile recovery against authoritative
job state and persisted remote intent/job IDs. Its collector pins each completed result revision and runs
`collect-five-plant-screen.py KEY REV ai/runs/five-plant-comparison-v1/KEY`.
The collector verifies source/protocol provenance, retraces all training artifact
hashes and rechecks all raw outcomes. Preserve all seven cells and rule subgroups.
Once parent plus four finals are collected, run `compare-five-plant-screens.py
ai/runs/five-plant-comparison-v1 --output PATH`. It reports full-minus-control
separately for both training seeds and against parent, using 20,000 whole-deal
bootstrap draws with seed10031. Reused 40 deals do **not** become 80 independent
deals across training seeds. Assess consistent two-player gains and regressions
in both seeds, references and every other count; do not select a convenient cell.

Final reserved seeds remain unused. Default-bot, heuristic, rush, independent
search, retained neural opposition, serving package, engine compatibility and
actual AMD8840U delivery remain required for eventual qualification. This ablation
is a development experiment, not a replacement for the full strength gate.

## Earlier completed evidence (11:06 UTC)

All **three update9 arms** are now collected and independently reverified:
11,040 candidate games plus 3,680 previously pinned parent outcomes, exact
40-deal/seat/rule coverage in each cell, zero caps. `strong/collect-population-comparison.py`
rechecks checkpoint bytes/provenance, all balanced training batches, complete
export reports, raw game reports and all six contrasts; it exactly reproduces
the coordinator's 20,000-bootstrap whole-deal comparisons. Source snapshot:
**`4669fed94f8882e55eac3e3ff7bfb186c92ad36c`**. Local artifacts are
`ai/runs/population-comparison-u9-v1`; full verified results including every
rule/count cell are in `strong/population-comparison-u9-v1.json`.

| Update9 arm | Econ 2p | 3p | 4p | 5p | 6p | A260 3p |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Parent (u79) | 57.34 | 60.00 | 60.08 | 76.25 | 73.13 | 36.56 |
| Control | 53.44 | 58.96 | 53.91 | 73.19 | 70.00 | 38.13 |
| Homogeneous | 60.00 | 63.54 | 58.67 | 76.31 | 77.08 | 39.38 |
| Heterogeneous | 58.44 | 60.42 | 64.06 | 76.06 | 73.18 | 45.52 |

Heterogeneous minus control: economic4p +10.16 pp [5.16,15.31]; A2603p +7.40 pp
[1.56,13.33]. Heterogeneous minus homogeneous: economic4p +5.39 pp [1.09,9.84],
but economic6p -3.91 pp [-7.24,-0.63]. Its A260 advantage over homogeneous is
+6.15 pp [0,12.29]. These are **intermediate, marginal exploratory intervals,
one training seed and many contrasts**; no universally best recipe is established.
None clears the economic2p floor. Keep primary update19 comparisons unchanged.

The additional opponent **`economic_capacity_v1`** is implemented and wired into
the arena bridge/CLI. It uses the schema4.1 pure auction valuation helper, with
four plant slots in two-player portfolios; every existing opponent identity and
all training mixtures remain unchanged. A 16-game / 9,535-decision equivalence
test confirms identical choices and RNG consumption at 3–6 players. A focused
rule/information test also passes. This is a separately named reference, not a
replacement for old economic/search opponents or a presumed stronger teacher.

`strong/capacity-reference-protocol-v1.json` froze 40 new development deals,
all seats × four rule combinations, 320 games/cell before outcomes. All five
cells completed with no caps (1,600 total), independently verified by
`strong/collect-capacity-reference.py`. Results:

- Capacity-aware bot vs original economic: **52.50%**, whole-deal interval
  [48.59,56.56]; not clearly stronger. 321 candidate-turn deterministic choices
  differed. Its original/sealed subgroup was 48.13%; all subgroups are retained.
- Parent vs original/corrected economic: **57.81 / 59.38%**.
- Heterogeneous u9 vs original/corrected economic: **52.66 / 51.56%**.
- Against corrected economic, heterogeneous minus parent is **-7.81 pp**,
  paired whole-deal marginal interval [-15.00,-0.63]. Against original economic
  it is -5.16 pp [-12.81,2.66]. Do not hide this fresh two-player regression
  behind the A260 gain or the earlier screening seed results.

These results reinforce the need for a controlled two-player repair. They do
not establish that correcting the heuristic alone improves its strength or that
schema4.1 learning is better (no strength test of a trained schema4.1 candidate
has been conducted). Preserve both old and corrected reference opponents in
future relevant evaluations. No new teacher labels or training jobs this turn.

Persistent source: `strong-source-capacity-reference-20261010-v1.tgz`, dataset
revision **`7c1514ddf4a8f94cd0baebe0e733275b62678cdb`**, SHA
`c4cf7694a5cd86a7decb9f581c7ca824a1be7741c121a652063ce0289a18af7f`.
Raw reports/protocol/source/summary: model repo `runs/capacity-reference-v1`,
revision **`76e207f4ee444dd4e4f4ee13177eb460d2071125`**. See tracked
`capacity-reference-{protocol,source,artifacts,results}-v1.json`; local raw data
`ai/runs/capacity-reference-v1`. Local inference only, no gradients.

At **11:06 UTC**, all three trainers and coordinator were confirmed RUNNING:
heterogeneous update19 (233/240 complete), homogeneous update13 (226/240),
control update11 (220/240). State snapshot at model revision
`76e207f4ee444dd4e4f4ee13177eb460d2071125`; all u9 arms collected and comparison
ready, no u19 checkpoint recorded yet. Exact job IDs/progress are in
`strong/population-observed-status-20261010-v2.json`. Inspect live state before
collecting later results; coordinator owns all u19 screens. Do not duplicate,
restart, or alter the running cohort. No primary comparison yet.

## Validated five-plant implementation for the next controlled training run

The five-plant HF gradient smoke is **COMPLETED and independently verified**.
Job `6aca192dfee2c900701863fd`, H200, run `five-plant-gradient-smoke-v1`;
terminal status confirmed at 10:57 UTC. One update / 80 complete games (16 per
count), heterogeneous retained opponents, schema4.1 learner/snapshots with
schema4.0 frozen opponents. Both new projections changed from zero (norms
0.02661736 / 0.003502778), all parameters finite, all frozen roles present,
zero actual-game caps and **81,872 search rollouts / zero caps**. Update took
76.85 s. The trained ONNX passed all 2,553 strict export checks and all actions
matched its checkpoint. **This is correctness evidence, not playing strength or
candidate selection.** No local gradients ran. Do not launch this smoke again.

Immutable model-repo result revision:
**`4669fed94f8882e55eac3e3ff7bfb186c92ad36c`**.
`strong/collect-five-plant-smoke.py REV OUTPUT` independently verified every
artifact hash, source/protocol/init provenance, actual checkpoint dimensions,
new parameter norms, balanced metrics, frozen opponent pins, snapshot admission
and export report. See `strong/five-plant-smoke-results-v1.json` and local raw
files `ai/runs/five-plant-smoke-collected-v1`. Trained PT SHA
`f7c4771038a0470b30680f7c8325f62969f2e4e0a22c0724bc5f39cef77f28cc`;
ONNX SHA `574ad0af7e3c9df95bb9c28c6bb99ed1ac6a2f9e1eee5d069461db45d1eb42a2`.
Retain this smoke as integration evidence. The later fixed-parent two-seed
ablation above supersedes the earlier plan to wait for population recipe
selection; the original population experiment and strength gates are unchanged.

Schema **4.1-five-plants** is implemented as `features-v4_1.cjs` and
`model_v4_1.py`; the architecture is `multiplayer_ordered_plants`. State/action
sizes are **1215/100**: unchanged old 1149/98 prefixes plus six fifth-plant slots
and two capacity-aware economic action cues. Extra cues are learned inputs;
old residual prior and teacher index remain unchanged. Pure `economics-v4_1.cjs`
uses the four-plant limit for two-player purchase valuations. Old encoders,
network code, economic/search opponents and running experiments remain unchanged.
Trainer, model loader, evaluator and package builder support the new revision;
old/new neural opponents keep their own encoders. The explicit CPU transfer adds
1,664 zero-initialized parameters, preserving old weights and matrix shapes.
Contiguous legacy input slices are necessary for exact CPU transfer numerics.

Verified local evidence is in `strong/five-plant-validation-v1.json`:

- All 2,553 fixtures preserve every old feature exactly; fifth plants are explicit
  in the 8 relevant discard states; 8 positions have changed added auction cues.
  Deck order, sealed bids, seed and injected queued plans do not affect inputs.
- Parent and transferred PyTorch outputs match **exactly** on all 2,553 positions
  at batch sizes 1 and 16 (5,106 comparisons); strict ONNX tolerances and all
  decisions match. Six model-contract unit tests pass.
- Eighty complete mixed-revision games cover every count/rule/learner seat with
  zero truncations. Ten existing information/population Node tests pass.
- All 2,553 real serving requests return legal moves. The extracted package works
  from `/`, passes all 1,205 file hashes and 80 count/phase/rule cases. Local
  latency is a contended HX370 diagnostic, **not an AMD8840U qualification**.

Diagnostic transfer parent is heterogeneous update9, pinned by the prior audit;
this is not selection of the next full-training parent. Initial artifact revision
**`bbbbd1ac091651f8854386a476cb42617d9c095a`**, under
`runs/five-plant-transfer-v1` in the model repo. Initial PT SHA
`5bd9cef9b6a419c39f2d461d549393c5f046bb8b084ddd7d92221090a279d227`;
ONNX SHA `ded16c0977cea50049df0cea58d238b96655d32eddb1766ab849ad284055b11b`.
See `strong/five-plant-transfer-artifacts-v1.json` for further validation revision
and exact package/report hashes. Local outputs are `ai/runs/five-plant-transfer-v1`
and `ai/runs/five-plant-fixtures-v1.jsonl`.

Immutable source: `strong-source-five-plants-20261010-v1.tgz`, dataset revision
**`9691971d63d556b542647137291d19cfce750808`**, SHA
`877a58929a6eb2141f46cc96ba5ebb7b20f7078bbc51aad5d652b8f6cacf9055`.
`strong/five-plant-source-v1.json` lists all overlays and unchanged base provenance;
`strong/five-plant-smoke-protocol-v1.json` freezes exact job settings.
Use the actual update19 population comparison to choose the next parent/recipe;
require controlled strength evaluation of this feature change. Preserve all
existing baseline identities/gates and retain the separately named capacity-aware
reference when evaluating two-player strength. No new expert hard labels.

At 10:54 UTC, all three population trainers and coordinator were confirmed
RUNNING. Heterogeneous was on update17, homogeneous update11, control completed
update9. Coordinator owns every scheduled screen and had launched control-u9.
Its state was pinned at `bdbd57a81517231658d791f0c984d7cbb95d123e`, copied to
`ai/runs/population-coordinator-observed-state-v1.json` (wrapper with `revision`
and `state`). Inspect live jobs and refreshed state before collecting results;
never manually duplicate its screens. Reserved final seeds remain untouched.

## Diagnostic rationale for the new two-player plant context

Two-player terminal audit (`strong/two-player-terminal-audit-v1.json`): the first
population screen has 187 wins and 133 strict losses. Among losses, 29 are
tiebreaks; 63 have both cities and rated capacity below the winner's powered
total; 28 have enough cities but insufficient capacity; 10 have insufficient
cities despite sufficient capacity; 3 have both but lower actual powered count.
These are terminal constraints, not proof of earlier causal mistakes.

Sixteen preselected wins/losses (one each per rule/seat cell, first numeric deal)
replayed exactly with the frozen v32 arena engine and the pinned heterogeneous
update9 model. The public move traces remained byte-identical after adding the
plant diagnostics. See `strong/two-player-replay-selection-v1.json`,
`strong/two-player-plant-audit-v1.json` and
`strong/two-player-plant-audit-source-v1.json`. Full traces, reports and diagnostic
source are persistent in HF model repo under `runs/two-player-plant-audit-v1`,
revision **`f06dc7d6e26646ec92f9afeef6ba69df54f02b59`**.

Confirmed issues:

- `economics.cjs::plantValue` assumes replacement at three held plants. Germany
  two-player games allow four. Changing only the portfolio limit changes 151
  of 172 observed valuation queries (both players; queries are not independent
  games), by -14 to +10. The direction is not uniformly beneficial: these are
  heuristic values, not true action values. A corrected helper still needs
  strategic evaluation.
- Schema4 has four explicit plant slots per player. All 192 observed discard
  states held five plants and had `chosenPowerPlant` cleared. Aggregate capacity
  and the fifth plant's own discard action row retain partial information, but
  other candidate scores and the state-only value head lack a fifth plant slot.
  Do not call the fifth plant completely invisible. This is a confirmed input
  limitation; its strength impact still needs a controlled experiment.

Schema4.0 and the current cohort are immutable. The append-only implementation
and its validation are described above. The diagnostic helper in
`audit-two-player-plants.cjs` remains a read-only preload hook, not a production
module. The separate `economics-v4_1.cjs` is the new pure helper. Corrected
heuristic values still need playing-strength evaluation; input correctness and
exact transfer do not establish strategy improvement.

## First population checkpoint — verified intermediate result

The heterogeneous arm's update 9 passed full 2,553-position export parity and
provenance validation for its ten complete, balanced training batches. All six
screen jobs completed and their raw outcomes were independently reverified.
Checkpoint revision: `3f56f692fc5204140257538099e1ec50a2b4fb09`.
Result revision: `116032eed805e92e1c30a7d1f1192c2704e8f8f6`.
Exact hashes and details: `strong/population-heterogeneous-u9-checkpoint-v1.json`
and `strong/population-heterogeneous-u9-screen-v1.json`. Local raw reports:
`ai/runs/population-observed/heterogeneous-u9`; also retained by the coordinator
in HF. No game/search truncations or missing pairs in the 3,680 outcomes.

Economic win shares at 2–6 players: **58.44 / 60.42 / 64.06 / 76.06 / 73.18%**.
Against frozen A260 at 3 players: **45.52%**, versus the starting policy's 36.56%.
The paired whole-deal improvement is +8.96 percentage points, marginal exploratory
95% interval [+2.91, +15.00]. All four A260 rule subgroups improved in point
estimate; only Recharged/open's subgroup interval excludes zero. Report the
uncertainty and all regressions: 5p economic fell by 0.19 points, and three of
the four 2p rule subgroups fell in point estimate. The aggregate 2p gain is only
+1.09 points, interval [-5.31, +7.50], still below the 66.25% economic target.

This is the prescribed intermediate checkpoint from **one arm**, not evidence
yet for the advantage of heterogeneous tables over homogeneous/control training.
The primary update19 comparison and other arms remain pending. The A260 point
estimate clearing its target does not qualify this model. Keep the experiment
unchanged until the prescribed comparisons are available; prioritize the
remaining two-player weakness when choosing the next training change.

## Full training throughput — separate from candidate selection

Two three-update HF probes use the verified faster economics runtime, identical
H200 update79 initialization, retained heterogeneous opponents, seed 10021,
240 complete games/update, all player counts, four Torch threads and batch 512.
The actual trainer is unchanged. Gradients run on HF only. These runs do not
alter the three-arm population experiment and are not candidate selection.

- CPU-performance: `6aca0ec4fee2c90070185e12`, run
  `multiplayer-throughput-v1-cpu-performance`.
- H200: `6aca0ec5fee2c90070185e14`, run `multiplayer-throughput-v1-h200`.

Inspect exact live statuses in HF; `strong/full-throughput-status-v1.json` is
only a last observation. Source and frozen settings are in
`strong/full-throughput-source-v1.json` and
`strong/full-throughput-protocol-v1.json`. Source dataset revision:
`13aaf16eb754b17fd6a4efb4c84b14d248c2b82e`.
Each run uploads `metrics.json`, checkpoints and `throughput.json` under its run
prefix. Require actual completion, exact source/protocol/checkpoint provenance,
updates 0–2, 720 complete games, balanced counts, and zero search/game caps before
using its timing. Recompute aggregates from metrics. Benchmark checkpoints must
not be presented as qualified candidates.

**Both probes completed and were independently verified.** Artifact revision:
`1e826b625d324245d2b64a9f2979c70b2e637b3b`. Full results and hashes are in
`strong/full-throughput-results-v1.json`; raw files are in
`ai/runs/full-throughput-collected-v1`. The collector
`strong/collect-full-throughput.py REV OUTPUT` verified exact provenance,
720 complete games/platform, updates 0–2, balanced counts, no search/game caps,
and recomputed stored aggregates from the raw metrics. It also pinned and
rechecked the first three original-runtime updates.

Observed update times (seconds): optimized CPU 225.18 / 218.06 / 236.33;
optimized H200 160.30 / 162.79 / 161.96. Medians: original CPU 308.34,
optimized CPU **225.18**, optimized H200 **161.96**. The observed ratios are
1.37× for original/optimized CPU and **1.39×** for optimized CPU/H200.
Median optimizer portions: CPU 60.28 s, H200 8.45 s; rollout portions:
CPU 161.83 s, H200 153.50 s. H200's sampled whole-process GPU utilization was
2.35%; rollout work dominates total update time. This supports the optimized
H200 runtime for a future cohort, not adding multiple GPUs to one small learner.
Keep the existing three-arm strength experiment unchanged. Workload counts,
processor differences, and timing limitations are retained in the report.

Compare all three update times, rollout/optimization components and actual
search/sample workloads. Also retain first three original heterogeneous updates
as an observational reference. Their median is 308.34 s/update; their full
metrics are now pinned by the verified heterogeneous update9 checkpoint above.
The collector uses that exact revision/hash. GPU and CPU hosts differ, and async scheduling/CUDA
numerics can change trajectories. These are platform throughput measurements,
not a pure GPU causal estimate. Isolated kernel timings alone were insufficient
to justify a scale-up. The wrapper rejects incomplete/truncated/count-imbalanced
batches or missing search diagnostics; those four rejection checks passed using
mutations of the actual 720-game reference.

## Automatic checkpoint evaluation — inspect before any manual launch

Coordinator job: `6aca0d29095c578089310fca` (CPU-basic, 12-hour timeout),
verified RUNNING with all startup tests passed at 10:03 UTC on October 10.
Inspect its actual status and `strong/population-coordinator-status-v1.json`.
It owns **all six scheduled candidate screens** (three arms × updates 9 and 19).
Do not launch duplicate screens while it is active. It does not train, change
the population experiment, use final-test seeds, or promote any model.

Remote state and reports live in model repo `coyotte508/powergrid-ai-germany-v1`,
under `runs/population-coordinator-v1/`. Pin the current repository revision
before reading `state.json`, candidate folders, or `comparison-u9/u19.json`.
Child screen job IDs are recorded there. A waiting checkpoint has no strength
result yet. On any failure, inspect its exact validation/launch/collection log;
never restart a job solely because observation timed out. An unresolved launch
intent means its POST may have succeeded and requires reconciliation first.

Frozen coordinator source: `strong-source-population-coordinator-20261010-v1.tgz`,
training dataset revision `68ac8b3a6dbc9706f69206df84ac4e98c25b551e`.
Exact hashes are in `strong/population-coordinator-source-v1.json`. It packages
the original population runtime, all 2,553 raw export fixtures, and all six
verified parent reports. Eleven failure/recovery tests passed locally and again on HF at startup. Packaged parent reports were independently
rechecked: 3,680 complete paired games and matching artifact hashes.

The coordinator waits for matching metrics/latest checkpoint updates, recovers
missed update 9 from immutable history, requires full strict export parity,
then runs the prescribed six cells. It records launch intent before POST and
never automatically retries an ambiguous launch. Failed trainers or screens do
not cause it to abandon already-running peer screens. After all three arms for
an update are collected, it produces the paired comparisons. Terminal failures
give a nonzero exit; they are evidence to inspect, not successful qualification.

## Current training — inspect exact jobs before taking action

`strong/population-status-v1.json` has exact job IDs, latest observed progress,
and first complete update records. The three runs are
`multiplayer-population-v1-{control,homogeneous,heterogeneous}`. All remain on
their original immutable runtime. No restarts or source/hardware changes were
made to this cohort. All observed complete batches contain 240 games, 48 per
player count, and zero game or search truncations. Training outcomes are not
independent strength evidence. A polling timeout is not job termination.

`strong/population-training-protocol-v1.json` freezes: H200 update79 parent,
three retained neural opponents, 20 PPO updates × 240 complete games, 2–6
players, original/Recharged and open/sealed, seed 10021, initial-policy anchor,
periodic snapshots every 5 updates. Population arms have identical opponent
marginals, assigning either one family per table or independently per opposing
seat. Two-player assignments match. The third arm retains the prior mixture.
This is a single-seed pilot. Source/revision/hash are in
`strong/population-source-v1.json`; gradients run only on HF Jobs.

## Completed evidence and runtime work

- Parent benchmark: all 3,680 games verified at artifact revision
  `29f232e329f05ce6a93ea92006a271d9ea292147`, 40 complete paired deals/count,
  zero truncations. Economic win shares at 2–6 players:
  57.34 / 60.00 / 60.08 / 76.25 / 73.13%; A260 at 3 players: 36.56%.
  The two priority weaknesses remain. Full report and hashes:
  `strong/population-parent-screen-v1.json`; raw reports:
  `ai/runs/population-parent-screen-v1`. Parent export parity passed all 2,553
  positions. Collector rejects wrong hashes/deals/opponents and missing or
  truncated matches.
- Neural-continuation audit: all five jobs completed, 30,048 continuations,
  zero truncated, pinned revision `577ecd7d834c64741db9cda715bd1db3c3dddbd9`.
  Across 60 reused positions, 11 had disjoint A/B winner sets and 27 tied every
  action in discovery. Selection depends on continuation policy. No teacher
  promotion or new hard labels. See `strong/neural-continuation-summary-v1.json`
  and `strong/neural-continuation-status-2026-10-10.json`.
- Compute probe: both HF Jobs completed; manifests and exact paired batch hashes
  verified. `strong/compute-protocol-v1.json`, `strong/compute-results-v1.json`
  and `strong/compute-source-v1.json` preserve everything. Artifact revision:
  `f6a3a7e98ee55501190c1acc4371eb85494557df`. At 4 Torch threads, optimizer batch
  512 took 254.88 ms on CPU versus 28.70 ms on H200 (8.88×). Eight-row inference
  changed only 1.58 → 1.51 ms. These isolated timings exclude concurrent engine
  work and search stragglers; no end-to-end training speed claim. Benchmark
  gradient targets were synthetic timing inputs; no weights were saved.
- Simulation profile: fuel cost calculation was the largest sampled hotspot
  (~28% self time). `strong/economics.cjs` now caches costs only within a production
  planning call and hoists repeated price/holding reads. **Only future runtimes
  use this change.** Equality checks passed for 5,760 production plans, all
  20,705 decisions and terminal states in 40 complete games, every outcome in
  1,252 search continuations on 60 positions, and all state/action features in
  2,553 serving positions. Ten existing Node tests passed. Three alternating
  timing pairs gave median 9.62 → 5.98 seconds (1.61×) on this local search probe.
  See `strong/economics-optimization-v1.json` for exact scope and provenance.
  The first four-pair attempt ended with SIGTERM; its partial timings were
  excluded. The recorded three-pair run finished successfully.
- Faster future source is saved independently in HF; see
  `strong/economics-fast-source-v1.json`. Do not overwrite the active cohort's
  source reference with it. `strong/verify-economics-optimization.cjs` compares
  the two extracted runtimes. Encoded public compute fixtures are inside the
  immutable compute source; original serving fixtures remain locally in
  `ai/runs/multiplayer-serving-fixtures.jsonl` (SHA in the reports).

## Next actions

1. Inspect the three training jobs and verify further completed batches. The
   original control performs more search rollouts than the population arms;
   raw update times are not a clean hardware comparison. Keep all prescribed
   checkpoints and regressions, including runs slower than the others.
2. Let the coordinator preserve immutable model-repository revisions at updates
   9 and 19 before later uploads replace `latest`. Its underlying tools are
   `strong/prepare-population-screen.py ARM UPDATE REV OUTPUT` to validate
   training provenance and full 2,553-position checkpoint/export parity, then
   launch its `screen-plan.json`. Internal `best` is not the scheduled candidate.
   If needed, recover update 9 from immutable repository history rather than
   substituting a later checkpoint.
3. Once each six-cell screen is complete, pin its artifact revision and run
   `strong/collect-population-screen.py OUTPUT REV`. Fresh development prefix:
   `multiplayer-population-screen-v1-{players}p`, offsets 0–39, every seat and all
   four rule combinations. Then `strong/compare-population-screens.py` compares
   all three arms and the parent at each scheduled update. It resamples whole
   deals, reports every rule/count cell, and does not pool away weaknesses.
   Sanity checks passed: identical actual reports give zero difference; missing
   pairs fail; 400 correlated synthetic rows retain only 4 independent deals.
4. If strength screens justify further training, consider the verified faster
   economics runtime and H200, with a full training-throughput check and a second
   training seed. Current source and hardware stay fixed. Only then proceed to
   stronger independent search/mixed tables and the unchanged final strength
   protocol, followed by export/legality/latency/package checks on the 8840U.
5. Training still freezes source-v36; independent screens use source-v32.
   Verify newer production-engine compatibility before any deployment. Public
   money is allowed; hidden deck, sealed bid values, RNG seed and queued plans
   stay excluded. Do not present value-head output as calibrated analysis.

The historical October 4 handoff follows; its paused status and old job snapshots
are historical, not the current state.

---

# Power Grid AI — saved research handoff, 4 October 2026

**Start here when resuming. Research is paused at the user's request. No model
has passed the complete strength gate; nothing is routed into production bot
moves. Reserved final-test seeds remain unused.** This document supersedes the
outdated “running / pending / active” statements in the earlier READMEs and
`strong/multiplayer-progress.json`. Those files remain useful historical notes.

This handoff was reconstructed from the checked-in experiment ledger, local
artifacts and read-only Hugging Face queries. The last five diagnostic jobs are
now COMPLETED. `hf jobs ps --format json` returned `[]` on 4 October. No training
or evaluation jobs were launched for this handoff.

## Objective and information contract

Build a **really strong** Power Grid bot, not just one that beats the default
engine bot. Train on HF Jobs; serve platform requests on the AMD 8840U. Browser
ONNX inference is a possible later use, not a completed integration. Later
analysis of players' decisions/win probabilities requires separately validated
and calibrated values; the current value head is not ready for that claim.

The user explicitly allows all players' money to be visible to the bot. Include
opponents' cities, plants, fuel, turn order and players still to act; resource
replenishment by step, available stock and prices; region/island presence and
remaining building slots. Building more cities can improve income but worsen
turn order, so optimize terminal winning, not an unconditional city reward.
Never expose actual hidden deck order, RNG seed, submitted sealed bids or queued
plans. Search samples public-consistent worlds rather than reading these secrets.

Validated training scope is **Germany, automatic setup, 2–6 players, original
and Recharged rules, open and sealed auctions**. Early policies were Germany/3p
only. Generic topology/territory export and UK/Ireland feature tests exist, but
there is no demonstrated trained strength on other maps. Do not advertise
multi-map support based on feature encoding alone.

## Where everything lives

| Material                                             | Location                                                                                                                         |
| ---------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| Canonical source                                     | [boardgamers/powergrid](https://github.com/boardgamers/powergrid), `ai/` and `ai/strong/`                                        |
| Complete experiment ledger                           | [strong/experiments.json](strong/experiments.json): source/model revisions, job IDs, reports, counterexamples and decisions      |
| Strong-policy background                             | [strong/README.md](strong/README.md), historical and partly stale                                                                |
| Baseline background                                  | [README.md](README.md)                                                                                                           |
| Private checkpoints, ONNX, reports, serving archives | [coyotte508/powergrid-ai-germany-v1](https://huggingface.co/coyotte508/powergrid-ai-germany-v1) (name predates multiplayer work) |
| Private immutable source bundles and data            | [coyotte508/powergrid-ai-training-v1](https://huggingface.co/datasets/coyotte508/powergrid-ai-training-v1)                       |
| Multiplayer final gate                               | [strong/final-protocol-multiplayer.json](strong/final-protocol-multiplayer.json)                                                 |
| Earlier 3p gate                                      | [strong/final-protocol.json](strong/final-protocol.json)                                                                         |
| Latest admission comparison protocol                 | [strong/league-admission-protocol-v1.json](strong/league-admission-protocol-v1.json)                                             |
| Collected diagnostic summary                         | [strong/handoff/teacher-reliability-v2-summary.json](strong/handoff/teacher-reliability-v2-summary.json)                         |
| Sanitized resume manifest                            | [strong/handoff/status-2026-10-04.json](strong/handoff/status-2026-10-04.json)                                                   |

Local canonical checkout: `/home/eliheros/code/powergrid`. Source before this
handoff was `face347f258a057c2ed3fb4e4606fce2003ab4c1`; AI research was integrated
by `1e73e53`. Old research checkout:
`/home/eliheros/Documents/Codex/2026-09-26/je-x20-2/work/powergrid-ai`, HEAD
`4bc256a8b126c0da977b9a728df9356e201ed815`. Its ignored `ai/runs/` contains large
local artifacts; do not assume those are present in a fresh clone. The previously
untracked `summarize-search-budgets.py` has been rescued into canonical source.

The research-only 8840U installation is `~/powergrid-ai-strong` on SSH alias
`minipc` (fallback `minipc-wg`). SSH configuration was updated previously. No
production routing was installed. Recheck host/runtime state when resuming.
The authenticated HF CLI is `/home/eliheros/.local/bin/hf`; its Python is
`/home/eliheros/.hf-cli/venv/bin/python`. Use cached authentication; never put
tokens or raw historical game data in Git.

## What was implemented and learned

1. **Baseline and historical-data audit.** Of 4,007 BGS records, 3,978 were ended;
   66 candidate Germany/3p games yielded 33 exact replays (7 sealed), then 32
   usable games / 11,366 decisions after excluding a colour-draft game. Failed,
   interrupted and incompatible replays were excluded explicitly. A 600-game
   synthetic + human baseline ran BC and PPO. It beat a weak heuristic but scored
   0% against the default bot: not useful evidence of strength.
2. **Corrected opponent and observations.** A heuristic read nonexistent
   `BuyResource.data.price`, producing NaN and suppressing fuel buying; stock-based
   resource pricing was also wrong. The corrected heuristic scored 85.1% against
   the default bot over 960 games. Default-bot wins are only a sanity check.
3. **Schema 3 strong policies.** 738 state / 96 action features; economic prior
   plus learned residual action scores, complete-episode PPO, frozen opponents,
   public-information search, CPU arenas and ONNX serving. Preserve frozen
   revision `3.0`; `3.1-uranium39` fixes persistent replenishment after plant 39
   has been purchased (even if later discarded). Unknown feature revisions fail.
4. **3p training/search/distillation.** A/B leagues completed 300 updates;
   high-exploration C/D were stopped after regression. Search-teacher datasets
   progressed from 512 games / 25,268 strategic positions to corrected v3's
   2,048 complete games / 247,104 decisions. More distillation did not reliably
   improve independent play. Corrected A260 refinement update 40 and A299 were
   useful references, but sealed-auction weaknesses remained.
5. **3p specialist.** Corrected A40 for three rule combinations and corrected-input
   B160 + 48-sample search for Recharged/sealed: 76.7% versus economic, 94.6%
   versus legacy, 46.7% versus frozen A260, each 480 development matches. SHA:
   `b4cae14eb6e1aff72b16e5056983b2a57ad42984f4a27cf99dd70bb63e86be32`.
   This is a research candidate, not a qualified universal bot. See ledger
   `specialist_candidate`, `specialists_remaining_results` and the other screens.
6. **Schema 4 multiplayer.** Revision `4.0-multiplayer`: 1,149 state / 98 action
   features, six ordered player slots (74 features each), inactive value slots
   masked to zero. `multiplayer_ordered` has 983,682 parameters and supersedes the
   earlier pooled prototype. Tested encoding and legal responses at every count;
   2,553 fixtures cover 2–6p. Initial teacher: 1,200 games / 142,804 positions /
   4,746,464 search rollouts with no truncations. Subsequent distillation, PPO,
   asynchronous environment workers, stronger-opponent replay and league
   admission comparisons are all recorded in the ledger.
7. **Later PPO.** H200 refinement and geographic-opponent asynchronous training
   each completed 80 updates / 19,200 games. These improved some development
   matchups, especially 5–6p, but did not qualify. A stronger teacher replay
   experiment did not translate prediction agreement into better independent
   play. Do not simply extend the same recipe or assume harder labels help.

## Latest completed strength screens

All numbers below are percentage win credit, including fractional ties, on
**reused development screening deals**, not untouched final tests. Each row has
3,680 completed matches: economic at 2/3/4/5/6 players (320/480/640/800/960 games)
plus frozen A260 at 3p (480). Full rule-level breakdowns and deal-cluster intervals
are in each corresponding ledger entry. Aggregate rates cannot override a weak
rule cell. Search is off for these candidates.

| Candidate                           | Econ 2p |    3p |    4p |    5p |    6p | Frozen A260 3p |
| ----------------------------------- | ------: | ----: | ----: | ----: | ----: | -------------: |
| H200 update 79                      |   63.44 | 60.83 | 59.69 | 77.69 | 73.28 |          33.54 |
| Geographic league update 79         |   52.34 | 59.90 | 54.53 | 71.44 | 65.99 |          33.33 |
| Admission “best” update 19          |   52.81 | 56.67 | 57.66 | 79.19 | 74.58 |          39.58 |
| Admission periodic-anchor update 19 |   60.31 | 57.40 | 61.72 | 74.94 | 70.16 |          36.04 |

None passes the 66.25% economic/2p and 40% A260/3p floors together. Geographic
update 79 also fails the strict export tolerance on one logit (although all
2,553 selected actions agree). Its training had four capped search rollouts;
the screening games/rollouts above were untruncated. Other three exports pass
their recorded parity checks. “Internal best” was not a reliable universal
external-strength selector; admission comparison had one training seed.

Pinned checkpoints in the private model repo:

| Candidate               | HF revision                                | File                                                               | SHA256                                                             |
| ----------------------- | ------------------------------------------ | ------------------------------------------------------------------ | ------------------------------------------------------------------ |
| H200 u79                | `0aeacd5b8e36ece36ba06a77ddfd7b86110d4f3a` | `runs/multiplayer-refine-hard-v1/latest.onnx`                      | `2f1dd42625ea86404155e63124e55d95d07016027a0ceda4e08164357b554927` |
| Geographic u79          | `035345f5f05bbbb55af5e0f4884d07f9087b1e32` | `runs/multiplayer-refine-geoleague-async-v1/latest.onnx`           | `35deffdacefdc3d3638417b1590432b84a86f3fb302958e273f5eeea9ad7ce34` |
| Admission best u19      | `efdb82f2712b8c6648100d7ad99b6941102f7001` | `runs/multiplayer-league-admission-v1-best/latest.onnx`            | `691a91ae58d5946a396fe595ffba2f866b5bfba6533ec504da9e6a134c07750e` |
| Periodic-anchor u19     | `efdb82f2712b8c6648100d7ad99b6941102f7001` | `runs/multiplayer-league-admission-v1-periodic-anchor/latest.onnx` | `08ad0042e548e9b871e9f4178626d405637fb55f3f42b0d580b2bd6979ac7f67` |
| Frozen 3p A260 opponent | `b38515c29e57826de05b55b645c29591e4a886bf` | `runs/strong-league-v2-a/best.onnx`                                | `9b46db558669a0c3085412fe2544359eda55ed9f092dffb67bead6af3c409ecd` |

Earlier H200 update 29 (revision
`fbdf2bf24c968bff99ab2d7d9ff9a7d97047db2b`, same hard-refinement model path,
SHA `d3d2ee88a0940f079a4b38879c8154dbab55951abc7b295a7db17bdf22e52c5f`)
remains a useful retained comparison; do not replace it just because later
updates exist. Its raw policy transferred gains over the distillation warm start
against independent `search_geo`, but 2–4p rates missed floors, with sealed-rule
weaknesses at 5–6p. Single-deal auction counterfactuals did not support the simple
explanation “pass or buy a cheaper plant”; no tested round-4 nomination won the
second investigated losing deal. Those are local diagnoses, not causal proof
about the whole policy.

## Diagnostics completed after the pause

Jobs `teacher-reliability-v2-{2..6}p`, CPU-performance, submitted 1 October:

| Players | Completed job                                                                               |
| ------- | ------------------------------------------------------------------------------------------- |
| 2       | [6abe1df0fbc85ba682360bd8](https://huggingface.co/jobs/coyotte508/6abe1df0fbc85ba682360bd8) |
| 3       | [6abe1df1404719ba3761721e](https://huggingface.co/jobs/coyotte508/6abe1df1404719ba3761721e) |
| 4       | [6abe1df2fbc85ba682360bda](https://huggingface.co/jobs/coyotte508/6abe1df2fbc85ba682360bda) |
| 5       | [6abe1df2fbc85ba682360bdc](https://huggingface.co/jobs/coyotte508/6abe1df2fbc85ba682360bdc) |
| 6       | [6abe1df3fbc85ba682360be0](https://huggingface.co/jobs/coyotte508/6abe1df3fbc85ba682360be0) |

Immutable source: dataset revision `d07e072058ee877112d609280980fc806ee8ce28`,
`strong-source-v36.tgz`, SHA256
`6c4170317a74a5148c2a576ad93d1170441e0d8e791a7e6c23197c51dad69109`.
Fixtures: 60 reused development positions, 2–6p × four rules × nomination/bid/build.
Fixture SHA `855b34ad7f07665dfcb012a673147f0780820a9e7560fda268a9a39478c60ff4`.

Downloaded model-repo revision `daef30ae69d6a96f21e46abd8a30909689682364`,
`runs/teacher-reliability-v1/` and `runs/teacher-reliability-v2/`. The summary
script verified every shard hash, all 360 searches / **721,152 rollouts**, zero
truncations, 2,400-step horizon, exact nested 48-sample prefixes and shared public
scenarios across continuation policies. It compares independent batches A/B and
budgets 48/96/192/384 under mixed/economic/heuristic continuations.

At 384 mixed samples, selected action agreed on 47/60 positions (v1: 39/60 at
48). Same unique winner rose from 19/60 to 29/60; disjoint winning sets fell from
16/60 to 10/60, but the intermediate budgets were not monotonic. Fourteen positions
had opposite economic/heuristic preferences in confirmation batch B for actions
selected in batch A. **Descriptive only:** this small reused fixture set establishes
neither playing strength nor which continuation policy is realistic. Larger
budgets alone do not resolve the teacher-policy mismatch. No gradients were run.

Reproduce this local audit without submitting jobs (from repo root):

```sh
hf download coyotte508/powergrid-ai-germany-v1 \
  --revision daef30ae69d6a96f21e46abd8a30909689682364 \
  --include 'runs/teacher-reliability-v1/*' 'runs/teacher-reliability-v2/*' \
  --local-dir ai/runs/resume-snapshot
python3 ai/strong/summarize-search-budgets.py \
  ai/runs/resume-snapshot/runs/teacher-reliability-v2 \
  ai/runs/resume-snapshot/runs/teacher-reliability-v1/results.jsonl \
  --output ai/runs/resume-snapshot/summary.json
```

## Runtime, implementation and resumption order

The JavaScript engine is still authoritative. No Rust rewrite was completed.
Profiling found repeated economics/territory calculations to be a bigger cost;
hoisting them out of action loops sped feature generation 2.2× with identical
outputs over 1,786 positions. Batching and asynchronous environment workers were
added. A tested cache regressed runtime and was removed. Low GPU utilization by
itself is not a reason to allocate more GPUs to CPU-bound simulation.

Actual 8840U measurements: schema-3 raw full-worker p95 around 3.5–3.8 ms;
multiplayer prototype p95 4.69 ms over 2,553 legal requests. Optional search is
much slower: roughly 0.7 s at 16 samples on a small fixture subset, 2–3 s at 48.
The specialist's 33 searched decisions had p95 2.36 s, max 2.57 s, no capped
rollouts. These measurements belong to their exact archived candidates/configs;
they are not latency guarantees for all later policies or browsers.

When the user explicitly resumes:

1. Read this file and relevant ledger entries; inspect HF jobs before launching
   anything, to avoid duplicates. Fetch exact HF revisions and verify hashes.
   Use immutable source bundles to reproduce old experiments; current engine
   code includes later UI/game fixes and is not automatically equivalent.
2. Start from the saved teacher-reliability summary. Design an explicit comparison
   of continuation quality/opponent coverage, especially sealed auctions, and
   evaluate uncertain targets before another large hard-label distillation run.
   More samples helped repeatability but did not make all labels reliable.
3. Retain H200 u29/u49/u79, specialist and frozen opponents as comparisons. Use
   paired development deals, every player count and rule cell, diverse opponents,
   and report all actual-game/search truncations. Search horizon must explicitly
   be 2,400 for the newer multiplayer runtime; older 1,200-step results remain
   separate. `six_player_search_horizon_investigation` documents the rare cap.
4. Re-run meaningful information-boundary, encoder and export checks when code
   changes. Key entry points: `test.cjs`, `test-v4.cjs`, `test-search-samples.cjs`,
   `test-search-horizon.cjs`, Python tests, `check-export.py`,
   `benchmark-serving.py`, `package-serving.py`, `verify-package.py`. Check each
   script's CLI and candidate feature contract before use. Standalone archives
   expose `serve.py`, which verifies the frozen model hash and configuration.
5. Freeze a candidate only after development evidence warrants it. The multiplayer
   gate requires each count/rule interval lower bound above 1/N, complete paired
   deals, no illegal moves, explicit rollout counters, strict ONNX parity, all
   2,553 legal serving requests and actual 8840U measurements. Minimum economic
   rates for 2–6p are 66.25/55/49.375/46/43.75%; default bot is 90% at every count;
   other opponent thresholds are in the protocol. Do not lower gates after results.
6. Only then use reserved prefix `strong-multiplayer-final-reserved-v1` under a
   frozen multiplayer evaluator. The existing `launch-final.py` / `verify-final.py`
   were built for the earlier 3p protocol: inspect/adapt their count support before
   invoking, rather than assuming the new protocol JSON is sufficient. Failed
   qualification stays failed; a new candidate requires new final seeds.
7. After qualification, integrate bot requests, then separately investigate
   browser ONNX and calibrated per-round analysis. Expand maps with per-map
   training/evaluation; UK/Ireland geography is particularly important.

Historical BGS data remains useful for legal-action replay, realistic positions,
imitation warm starts and diagnostics. It is small, selected and not evidence
that its players are expert. Keep whole games separated across splits and never
substitute training fit for independent playing-strength tests.
