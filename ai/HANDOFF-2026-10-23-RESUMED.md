# Power Grid AI — resumed 23 October 2026

The user explicitly requested “resume powergrid trainnig”. The existing goal is
active. HF Jobs are authorized for training and evaluation. No candidate has
passed the full strength gate, and no AI has been published to production.
This document supersedes the pause instruction in the
[10 October handoff](HANDOFF-2026-10-10-PAUSED.md), which retains the earlier history.

## Workspace and authoritative records

- Research checkout: `/home/eliheros/Documents/Codex/2026-09-26/je-x20-2/work/powergrid-ai`.
- Branch: `ai/germany-baseline`, remote `git@github.com:boardgamers/powergrid`.
- Interpreter: `ai/.venv/bin/python`. Use cached HF and SSH authentication;
  never print tokens or include them in documents, source archives or Git.
- Artifact repo: `coyotte508/powergrid-ai-germany-v1` (private).
- Source dataset: `coyotte508/powergrid-ai-training-v1`.
- Target: `ssh minipc`, AMD 8840U. The local HX370 is not the target benchmark.
- Latest explicit job snapshot: [full-data labels](strong/policy-iteration-labels-status-v2.json).
  During remaining-wave submission this snapshot covers only the original 60
  completed jobs. Read the live-launch note below before interpreting it. Guards are in
  `ai/runs/policy-iteration-labels-launches-v2/`; use
  `ai/.venv/bin/python ai/strong/manage-policy-iteration-labels.py status`.
  Older teacher, collection, inference-profile and development jobs are complete;
  their failed/replaced historical handles must not be retried.
- Production/UI checkout remains separate. Do not merge or publish research
  there as part of resuming training. Do not comment on GitHub issues.

## Latest checkpoint: larger data and representation comparison prepared

This continuation made **progress**. The first full-data labels are independently
verified, all 17,280 public inputs are cached and archived, and the next training
design is fixed. **No new gradients, qualified model, production changes, or
reserved final-test use.** The existing goal remains active.

### Label jobs and collection

At `2026-10-24T02:52:53.617474+00:00`, HF reported **all 60 original jobs COMPLETED**.
All 60 then independently verified: **3,212,352 new continuations**; including
the pilot, **3,917,760 continuations / 4,038 root-mode pairs**. No caps were
accepted. This is partial training-label coverage, not strength evidence.

First-wave evidence: model-repo revision
`cd0ec1a2b4feaf8d5279c9aafb31291a7f3eb8ea`, prefix
`runs/policy-iteration-labels-first-wave-evidence-v2`. The manifest still says
`complete: false` because only 60 of the full 948 new shards are verified.

The immutable 20-shard checkpoint is at model-repo revision
`84079ae01a877988a59e8aab38c4e18f3131d51b`, prefix
`runs/policy-iteration-labels-first-progress-evidence-v2`.
It includes the precise seven-shard snapshot used for the new parser check:
195,072 terminal records, 402 searches and 19 positions with both modes,
all accepted without dropping negative targets.

No local collector remains active. Five collection passes finished; the latest
manifest includes all 60. The dry-run admission for the remaining wave passed:
**888 new jobs / 30,522 new root-mode pairs**.

**LIVE submission:** unified exec session **62283**, command
`ai/.venv/bin/python ai/strong/manage-policy-iteration-labels.py launch --wave remaining --execute`,
log `ai/runs/policy-iteration-labels-remaining-launch-v2.log`.
It is still submitting sequentially. At `2026-10-24T03:00:52.691575+00:00`, 205 new
handles were confirmed; this is a lower bound, not the final total. Read the log,
wait/poll that session, and check guards before doing anything else. Do not start
a second launcher while its `.launch.lock` is held. A transient `launch_intent`
is normal during an active submission; `launch_unknown` after a failed process
must be reconciled with HF before retrying. **The status JSON currently predates
these new jobs and must not be interpreted as an idle fleet.** After submission
finishes, refresh status and archive all launch guards before collecting.
The 205-handle partial remaining-wave snapshot is already persistent at revision
`0453e0f985962b8a2a17c86a94339f66ca8a6f03`, prefix
`runs/policy-iteration-labels-remaining-launch-progress-v2` (it also retains all first60 guards).
Later handles remain in local guards until the complete launch archive is saved.

The source/protocol and first-wave launch plan below remain unchanged. The
60-shard admission gate is passed. All 948 new shards plus the 60 reused pilot
shards must verify before gradient training. No live job was duplicated/retried.

### Complete public feature cache

`ai/runs/policy-iteration-features-v2/` contains `features.npz`, `metadata.json`
and `feature-check.json`. Row order is the frozen selected index, not gzip order.
Arrays are state `[17280,1217]`, shortlisted actions `[17280,7,101]`, mask,
parent proposal index within that shortlist, and original legal-menu indices.
Splits remain 12,960 train / 4,320 validation by whole deal.

All 17,280 full-menu parent proposals and public/model input hashes were
reproduced. Every old 4.2 prefix matches, all 360 reused pilot menus match, and
global public/model input deduplication remains intact. Cache generation took
67.25 seconds locally with **no gradients**.

Immutable private artifact pin:

- Revision `213dcd7400f643fde7368b7c140bd5b7f7b79a55`.
- Prefix `runs/policy-iteration-feature-cache-evidence-v2`.
- Descriptor `strong/policy-iteration-feature-cache-evidence-v2.json`.
- Feature check SHA `49fbc46d87259ca45893e98cca1e47228b477c67c16e9806f96bf4801f792b93`.

The archived cache-generation code and frozen teacher/profile overlays must not
be silently edited. Recover the pinned cache rather than regenerating it.

### Prespecified next experiment, not yet trained

`strong/policy-iteration-training-design-v2.json`, SHA
`987698dc90f5b8807f18fde8770dcc365509a3381ec87f83361df1796cb98d3e`, fixes:

- The old **97,473-parameter** head as the data-expansion control, and a new
  **482,497-parameter** head with direct access to all 1,215 raw public state
  features plus the frozen ordered-player context and action embeddings.
- Four seeds per representation: **12101, 12102, 12103, 12104**.
- Four development candidates: each representation with the mean of all four
  heads, and the mean minus one population standard deviation. Seed disagreement
  is **not** a calibrated confidence interval. No best-seed selection.
- The fixed 0.025 switching margin, original scope (nomination/bid/build), same
  teacher shortlist plus parent fallback, and unchanged parent values/other phases.
- Soft paired targets: average the two continuation modes within each world,
  then concatenate A/B into 192 samples. Retain adverse/uncertain evidence.
- 120 epochs, batch256, AdamW learning rate0.0003/weight decay0.001, gradient
  norm1, evaluation every fifth epoch, epoch0 included. Each seed selects the
  lowest validation simulated regret, ties keeping the earlier checkpoint.
- Fresh development prefix `policy-iteration-development-v2`. Parent preservation
  is insufficient: the parent itself is unqualified. Independent full-game tests,
  actual8840U measurements and the untouched final gate remain mandatory.

`model_policy_iteration.py` adds the representations/ensembles without changing
historical factories. `policy_iteration_data.py` requires the complete exact label
manifest before downloading/reducing raw data. `prepare-policy-iteration-training-data.py`
will create the compact bundle only after that admission. It has **not** produced
a full training bundle yet. `archive-policy-iteration-training-data.py` is ready
to revalidate/upload the complete bundle and refuses the current incomplete grid.
`policy_iteration_training.py` and
`train-policy-iteration.py` implement loading, calibration, four-seed HF training
and strict member assembly; the gradient loop has **not** run. A pinned HF training
source, data bundle pin and job launcher/admission still need preparation after
the full labels finish. The future source must include the explicit
`policy-iteration-labels-source-v2.json` descriptor as well as the new modules;
the base archive cannot contain its own subsequently written descriptor.
Do not run gradients locally.

Checks completed:

- New reduction independently matched all 705,408 original pilot terminal
  records; common-world covariance, negative evidence and malformed-input
  rejection were exercised. Incomplete data fails before downloads/output.
- Four inference-only synthetic ensembles (two representations × two penalties)
  each passed **2,553 full-menu fixtures + 17,280 cached positions**. Actual changed
  decisions were exercised; every native/ONNX choice and parent fallback matched,
  values and out-of-scope actions remained preserved. No trained strength claim.
- Four model tests and three metric/assembly/calibration tests passed. Missing,
  duplicated or inconsistent seed members are rejected. Calibration decisions
  match exported policy decisions on 512 additional synthetic cases.
- The trainer refuses local gradient entry. Full gradient behavior and learned
  candidate strength remain untested, explicitly recorded in the preflight.

Preparation evidence: model-repo revision
`1fc7d8eb321fd39d882fb9cdd432436035108b63`, prefix
`runs/policy-iteration-training-preparation-evidence-v2`, 20 files. Descriptor:
`strong/policy-iteration-training-preparation-evidence-v2.json`. This is a
reproducible preparation archive, **not an admitted HF training source**.

Next: finish the active remaining-wave submission and archive its guards;
collect the entire label grid; reduce and pin the compact bundle; build/preflight
the actual training source; run the two representation jobs on HF, four seeds each;
independently collect/check all four ensembles before fresh whole-game evaluation.

## Previous checkpoint: full pilot verified; larger labeling wave launched

This goal turn made **progress**: completed and assessed the full pilot, measured
and verified faster inference, froze the full-data source, and launched its
first 60 HF jobs. The goal remains active. **No new gradient training, qualified
model, production publication, or reserved final-test use.** Both old strategic
candidates remain rejected by the complete 20,160-game screen.

### Completed pilot and label quality

All 60 original pilot jobs are COMPLETED and independently verified:
**360 positions / 705,408 full continuations**, with exact recorded first-two
probe outcomes, steps and beliefs. The complete pilot evidence is at model-repo
revision `c01dd8c0498d53f3f2723bb5658f98633511f10f`, prefix `runs/policy-iteration-teacher-pilot-complete-evidence-v2`.

At the fixed .025 margin, disjoint A-select/B-evaluate (then reversed) yields
mean conditional simulated gain .03871166 terminal win credit; validation
positions 0.05881305. All five marginal player-count means are positive.
There are still **36 negative changed directions out of 231 changes**, and
six negative count/decision/edition/auction intersections beyond numerical
roundoff. Every adverse result is retained. These six-root intersection cells
are descriptive, not confidence statements. Batch choice agreement is 76.1%.
**These are simulated label diagnostics, not whole-game model improvements.**
Reports: `policy-iteration-teacher-pilot-assessment-v2.json` and
`policy-iteration-teacher-pilot-intersections-v2.json`. All old pilot and probe
jobs are finished; do not relaunch them.

### Verified throughput improvement

HF profiling job `6adc0c1d046eb82b1ecd9459` is COMPLETED, not running.
Four concurrent inference batches retain the same 64-row batches, with the
same frozen parent, full simulation horizon and engine. The HF checks compared
all raw scores/values on **2,553 fixtures**, and exact complete model-choice
transcripts plus terminal outcomes on **3,072 continuations**, 2p/6p and both
continuation modes. End-to-end wall speedup: **1.6868x** overall (1.655–1.695x
across the four cases); inference alone roughly 2.4x. The HF CPU had 32 CPUs
in its affinity. This is not an AMD 8840U serving benchmark or model strength.

- Raw profile revision `c777f3d7a1d510713fa8a491216c786c0488a2ca`, prefix `runs/policy-iteration-inference-hf-profile-v2`.
- Complete evidence revision `32dc9270fea8a850b08ba15db2b5eb6442bdc0ff`, prefix
  `runs/policy-iteration-inference-profile-complete-evidence-v2`.
- The exact tested helper is included in the full-data source; do not edit it
  or any other frozen overlay. The old pilot engine/evaluator files stay intact.
- Clarification: prior pilot “trajectory” wording referred to complete recorded
  terminal records, steps, outcomes and initial beliefs. The concurrency profile
  additionally hashes every model choice and call boundary.

### Live larger labeling work

The full dataset is still exactly **17,280 positions** (12,960 train / 4,320
validation). It reuses the original 360 pilot positions and all their immutable
pins. The 16,920 remaining positions require 33,840 new root/mode pairs, partitioned
into **948 planned shards**. Every selected position remains included; no gain,
uncertainty or disagreement filtering.

- **First 60 shards submitted**, one per count/behavior/source-opponent/mode.
  They contain 3,318 new root/mode pairs, 2,538 distinct new positions.
- At `2026-10-24T02:01:22.708263+00:00`: `{'SCHEDULING': 27, 'RUNNING': 33}`.
  Inspect these exact handles before recovery. Scheduling/quiet logs are not
  failures; do not duplicate jobs. No local collector is currently running.
- Each job: cpu-performance, 24 engine workers, four concurrent fixed inference
  batches, **8h timeout**. The plan conservatively uses the slower serial pilot:
  twice the slowest same-count/mode A+B position, plus 600s overhead, within 75%
  of the timeout. Max projected cost is 21,540.42s. No horizon is shortened.
- The remaining **888 shards are blocked by a launch guard until all first 60
  independently verify**. A deliberate dry admission attempt was rejected.
- Source preflight passed **1,364 full continuations**: eight exact pilot-prefix
  cases, two genuinely new root-routing cases, and one production-size 96-world
  A/B case exactly matching the old serial pilot terminal records. All 34,560
  total root/mode assignments are covered exactly once including reused data.
- Source dataset revision `716d70b1e8049c95f9575cd27799c9359e7b3e7a`.
  Archive `strong-source-policy-iteration-labels-20261024-v2.tgz`.
  SHA256 `aaacd650c2059721b394ef65f9e8f28602789d43888ccb5a9aa1b0b487706598`.
  All 1,430 base files unchanged; four new frozen overlays.
- Protocol SHA256 `9dc68ed389d96c8421a02231dd51875b7887c7dbe0fceba81abc40c30381a271`.
- Launch/admission evidence revision `075183b8d5733737a43e47db6759ec02e62b9c63`, prefix
  `runs/policy-iteration-labels-launch-evidence-v2` (78 files).

```bash
ai/.venv/bin/python ai/strong/manage-policy-iteration-labels.py status
ai/.venv/bin/python ai/strong/manage-policy-iteration-labels.py collect
ai/.venv/bin/python ai/strong/manage-policy-iteration-labels.py summarize
# Only once every first-wave shard verifies; dry-run first:
ai/.venv/bin/python ai/strong/manage-policy-iteration-labels.py launch --wave remaining
ai/.venv/bin/python ai/strong/manage-policy-iteration-labels.py launch --wave remaining --execute
```

The launcher supports `--limit N` to submit a subset of pending planned shards;
existing guards prevent duplicate submissions. Paths:
`ai/runs/policy-iteration-labels-launches-v2`,
`ai/runs/policy-iteration-labels-verified-v2`,
`ai/runs/policy-iteration-labels-collector-v2` (created on collection),
`strong/policy-iteration-labels-status-v2.json` and
`strong/policy-iteration-labels-results-v2.json`.
The source builder and launch process have finished. No local collector is
active. Results currently contain only the 720 reused pilot root/mode pairs;
none of the new first-wave shards has been independently collected yet.

Next: verify the existing first wave; admit/finish remaining labels; then freeze
an HF-only gradient-training design and evaluate fresh models on untouched
`policy-iteration-development-v2` deals. No new training design is frozen yet.
Actual full-game strength and an exact-model AMD 8840U benchmark still gate
qualification. The final protocol SHA256 remains
`7f0336c8784faf8f18e046b95b88e0ab1be7c2de1c0ec4d3eec96f0a415286ce`;
the reserved final seeds are unspent. The original teacher manifest also remains
byte-identical (`6135dba264e18bdc0d8002ca50719bb3340f94b05e22221812864295fe651e57`).

## Historical: balanced data complete; larger teacher pilot running

The previous goal turn made **progress** (complete old evaluations and new
collection/selection machinery). This turn also made **progress**: all fresh
positions are verified, the balanced selection is frozen, every runtime probe
passed, and all 60 larger label jobs were submitted. The goal remains active.
**No new model has been gradient-trained or qualified, and nothing is deployed.**
The original 20,160-game model comparison still rejects both 11101/11102;
the parent also remains below the full strength requirements.

### Completed collection and selection

- All 30 collection jobs completed: **7,680 unique games / 15,360 capture-control
  executions / 383,135 public positions**. Every recorded behavior and parent
  proposal was independently reproduced with the frozen runtime. No caps.
- Complete collection evidence: model-repo revision
  `483afab378c99ff6d33710e5bcbc1eb7130e6da0`, prefix
  `runs/policy-iteration-collection-complete-evidence-v2` (66 files).
- Selection is exactly **17,280 roots: 12,960 train / 4,320 validation**.
  All 720 count/behavior/opponent/edition/auction/decision/split cells hit their
  quota. All early/middle/late round quotas also hit exactly; no fallback.
  Each player count contributes 3,456 roots, 1,152 per round band.
- Global input de-duplication removed 9,147 duplicate occurrences from the raw
  collection. Identical public requests and equivalent float32 parent inputs
  cannot cross the split. A validation occurrence excludes the equivalent
  input from training; whole deal assignments remain fixed.
- Selected data: revision `96d59920f004d85016c063eb466a1a66611ec593`,
  prefix `runs/policy-iteration-selected-v2`. Root gzip SHA256:
  `09e138bd61c8e52092f77c1c63cf47df32e78b58375960ab8d04915afd813902`.
  Descriptor: `strong/policy-iteration-selected-roots-v2.json`.
  Full selection and provenance: `strong/policy-iteration-selection-results-v2.json`.
- All local collection/index/selection processes have finished. The local
  outputs under `ai/runs/policy-iteration-selected-v2` are frozen; do not rerun
  selection into the same directory or regenerate old teacher manifests.

### New teacher pilot and live work

The first pilot uses 360 fixed hash-selected positions, one per
count/behavior/opponent/edition/auction/decision cell, with 265 train and 95
validation positions. It preserves the fixed parent, six-proposal shortlist
plus parent, both continuation modes and 2,400-step full-game horizon.
The policy-consistent sealed-bid belief correction includes legal passes and
uses public balances; no real hidden submissions or future deck are replayed.

This is a controlled data/teacher iteration, not a permanent restriction on
what a strong model may do. The current menu still has historical bid pruning.
A previous unchanged-weight expanded-menu experiment (`sealed_menu_v1` in the
ledger, 15,040 paired games) had no robust benefit and was not promoted; do not
blindly reapply it or claim that every legal bid is covered here.

- Source dataset revision: `e661d2f43fcedec24ffff4bf1180758e614e2a8f`.
- Archive: `strong-source-policy-iteration-teacher-20261024-v2.tgz`.
- SHA256: `40cc40e24f4bf70b48d73a29a26479fdc0250e26d16f837851f4135c6e233fbc`.
- Protocol SHA256: `b9fc9807172a518b019a5bdc30f6cb1b04b643c75adc7af9d0f6ac59f9678bce`.
- Five new files/assets; all 1,425 base files preserved byte-for-byte.
- Preflight passed **584 full control continuations**, including nomination,
  open/sealed bidding and building at 2p/6p, both modes, exact old-control
  trajectories, unaffected-policy equivalence, 96-world belief traces and
  first-two-world equality across larger inference batches/worker offsets.
  A complete 12-root probe shard (236 rollouts) was independently checked too.
- All **60 runtime probe jobs are complete and independently verified**:
  **14,696 full continuations**, 2 samples per A/B batch, all 360 positions/modes.
  Probe evidence revision `85952b6ff5e002880e10d0b7ad8d035e3452ada9`,
  prefix `runs/policy-iteration-teacher-probe-complete-evidence-v2` (123 files).
- All **60 larger pilot jobs** are submitted: 96 samples per A/B batch,
  192 paired worlds after mixing modes, **705,408 planned continuations**.
  Each uses 24 workers on cpu-performance and a 4h timeout. Per-case admission
  multiplies exact measured probe runtime by 96/2 and a 2x margin, plus 300s;
  the largest projection is 7,212.55s. No horizon was shortened.
- At `2026-10-24T01:15:48.386961+00:00` the authoritative pilot snapshot is
  `{'RUNNING': 41, 'COMPLETED': 19}`. Inspect those exact handles before any recovery;
  do not duplicate jobs because logs are quiet or an observation times out.
- Pilot launch/admission/scorer evidence: revision `25e42c503449e8f69601aa4eb0225640bcad3f78`,
  prefix `runs/policy-iteration-teacher-pilot-launch-evidence-v2` (67 files).

The first **19 pilot cases / 223,296 continuations** are
independently verified, including exact first-two-probe trajectory agreement.
This partial snapshot is archived at revision `39c34c637642fcbc2ee340eefca2d4228b97df29`,
prefix `runs/policy-iteration-teacher-pilot-partial-evidence-v2` (41 files).
The full pilot remains incomplete; do not run its assessment early or infer
whole-pilot quality from the faster completed cases. Completed-case throughput
is recorded in `strong/policy-iteration-teacher-throughput-partial-v2.json`:
median runtime grows 24.86x for 48x as many samples. Engine RPC timing includes
serialization, pipe waits and JS computation; it does not isolate the bottleneck.
The first collector finished successfully, so no local collector is currently
active. Its log is `ai/runs/policy-iteration-teacher-pilot-collection-v2.log`.

The collector independently reconstructs beliefs and parent proposals, checks
all terminal samples and paired arithmetic, and requires every large pilot
batch to reproduce its exact first two probe trajectories. A mismatch fails
verification; do not waive it or rewrite frozen results. The assessment uses
A to select/B to evaluate and then reverses, with fixed 0/.025 margins. Its
adverse-cross-batch and tie-routing contracts passed. It reports conditional
simulation diagnostics only, never real-game improvement or final qualification.

```bash
ai/.venv/bin/python ai/strong/manage-policy-iteration-teacher.py pilot status
ai/.venv/bin/python ai/strong/manage-policy-iteration-teacher.py pilot collect
ai/.venv/bin/python ai/strong/manage-policy-iteration-teacher.py pilot summarize
# Only after every pilot case verifies:
ai/.venv/bin/python ai/strong/manage-policy-iteration-teacher.py pilot assess
```

Guards: `ai/runs/policy-iteration-teacher-pilot-launches-v2`.
Verified results: `ai/runs/policy-iteration-teacher-pilot-verified-v2`.
Frozen collector runtime: `ai/runs/policy-iteration-teacher-collector-v2`.
The probe directories use `probe` instead of `pilot`; all 60 probes are already
complete and should never be relaunched. Job handles and all immutable pins
are also preserved in the evidence archives. No GPU training job is running.

Next: finish this pilot, retain every adverse count/phase/rule cell, inspect
label stability and measured throughput, then separately freeze/admit labels
for the full 17,280-root dataset and the next HF-only training design. The 360
pilot roots already belong to that dataset; reuse their verified labels when
compatible rather than silently resimulating them. No full-data label job or
new training design has been admitted yet. Keep fresh development prefix
`policy-iteration-development-v2` and all original reserved final seeds unused
until their proper stages. Actual full-game strength and the final exact-model
8840U benchmark remain required before qualification.

## Historical collection checkpoint earlier on24October

This turn made **progress**. The original fixed comparison is now complete:
**20,160 verified games**, 6,720 per model across all 27 opponent/count cells.
Both candidates are rejected for promotion. Model 11101 has 11 negative and no
positive marginal 95% contrasts; model 11102 has 17 negative and one positive
contrast (4p geographic search). These are exploratory development intervals.
The parent itself is still below the strength requirements. The exact 6p retry
completed successfully; no original arena, teacher, phase-ablation or GPU job
remains active. Do not repeat those jobs or spend reserved final-test seeds.

Complete arena assessment: `strong/strategic-correction-development-assessment-v2.json`.
Evidence: model-repo revision `d07927e1d1862d33e95fc20d413c474ee9db1f8f`,
prefix `runs/strategic-correction-complete-arena-evidence-v1` (667 files).
This preserves every positive/adverse cell and the historical exit137 failure.

The sealed-belief pilot is also **complete**: all 20 jobs, 39 positions,
312 searches and 88,320 full continuations independently checked, including
44,160 uniform-control continuations exactly reproducing historical results.
Cross-batch recommendation gain under policy-consistent worlds is +.013488
terminal win credit overall; by count: 2p +.029948, 3p +.028646,
4p −.001302, 5p +.009673, 6p 0. Validation positions average +.014940. Recommendations change
in 31/78 A-to-B/B-to-A directions. This is a small conditional diagnostic,
**not real-game improvement or a newly trained model**. The correction is
principled but cannot explain or repair all nomination/open-auction/building
regressions. Complete evidence: revision `9dd714c9b1fe94bff256fb6a6cf6be3c3c8035a3`,
prefix `runs/sealed-belief-pilot-complete-evidence-v1` (66 files).

A new collection now covers states visited by **all three fixed behavior
policies** (parent, 11101, 11102), versus economic or parent opponents, at every
player count from 2 through 6, edition, auction variant and focal seat. Opponents are always the
frozen parent in self-play-source cases, never inadvertently the changed model.
Every position records the actual behavior action and independently recomputed
parent action. Public cash is retained; hidden bids/deck/seed/log/plans and all
lastMove fields are removed. Each game is executed with and without capture;
every observation, action and terminal result must agree. No outcome filters
which positions are captured.

All **30 HF cpu-performance jobs** completed (4h timeout, 24 workers each).
Planned work: 7,680 unique games/15,360 control+capture executions, 16 fresh deals
per case. At `2026-10-24T00:35:40.804912+00:00` the authoritative snapshot is
{'COMPLETED': 30}. Locally verified at this document checkpoint:
21 cases / 4,800 games / 246,426 positions. All HF collection jobs completed successfully. Collection and input
indexing may still be running locally: inspect their processes and logs before
starting another collector/indexer. A quiet log is not a job failure.

Frozen source:

- Dataset revision `f430e2269d37d1e705eeffe25e87f007530db920`.
- Archive `strong-source-policy-iteration-collection-20261024-v2.tgz`.
- SHA256 `64dc537f5386bb6690a7f673d8bdcd14f22de250b2156b096fec4a250b6ada75`.
- Six new files; all 1,419 historical base files retained byte-for-byte.
- Preflight: 5,106 capture/privacy checks, 192 complete games/384 twins,
  9,408 independently reproduced positions; parent cases also match the original
  historical bridge before its actor metadata addition.
- Launch/preflight evidence: revision `c77189f294e79f4f1747dcd08acb742d0fc31140`,
  prefix `runs/policy-iteration-collection-launch-evidence-v2` (47 files).

The outcome-blind selection protocol is also frozen. It targets at most
**17,280 positions** (12,960 train/4,320 validation), balanced by count,
behavior, opponent, edition, auction mode and nomination/bid/build decision.
Within cells it balances early/middle/late rounds and deals/seats; shortages
are reported, never fabricated or filled by reassigning validation deals.
Public-request duplicates and equivalent float32 model inputs are globally
removed. Any duplicate appearing in validation is excluded from training.
Action-row order and signed zero cannot hide identical inputs. Four held-out
collection deals per case stay together across seats and rules.

Selection code/protocol/tests are frozen at model-repo revision
`6f57f383d84fe1095455371ffa6a0b3c3d6f0809`, prefix `runs/policy-iteration-selection-source-v2`;
protocol SHA `fc3da9fd41f2bf41a6e264c867ac163882a704b1f4d82049d333a74cddccc010`. Preflight compares 192
actual archived inputs to an independent Python hash, and checks split leakage,
order/outcome independence, balancing and explicit shortages. This is data
preparation only: **no new labels, gradient runs, selected model or deployment**.

Resume in order:

1. Inspect existing processes and job handles. Collection guards are
   `ai/runs/policy-iteration-collection-launches-v2`; the manager below only
   collects completed jobs and preserves immutable revisions for partial downloads.
2. Finish independent collection verification, then index remaining verified
   cases with the frozen encoder and complete balanced selection. Never run two
   collectors or indexers concurrently against the same directories.
3. Archive verified results and selected positions with exact hashes and
   update these checkpoint counts. Do not regenerate old teacher manifests.
4. Freeze a separate teacher-label protocol on these new positions, use the
   checked policy-consistent belief worker, and first run full-horizon runtime/
   correctness probes. Decide candidate coverage and uncertainty before scaling
   labels or selecting a new training design. The old 4.3 serving mask only
   allows its fixed six-proposal shortlist plus parent; expanding teacher
   actions alone would not expand what that model can choose at runtime.
5. Train only on HF Jobs, with fresh development prefix
   `policy-iteration-development-v2` and the original reserved final gate intact.
   Broader data is a response to coverage/generalization failures, not proof of
   a stronger model. No architecture, loss or new gradient run has been admitted yet.

```bash
ai/.venv/bin/python ai/strong/manage-policy-iteration-collection.py status
ai/.venv/bin/python ai/strong/manage-policy-iteration-collection.py collect
ai/.venv/bin/python ai/strong/manage-policy-iteration-collection.py summarize
ai/.venv/bin/python ai/strong/policy_iteration_selection.py index
ai/.venv/bin/python ai/strong/policy_iteration_selection.py select
```

Verified data: `ai/runs/policy-iteration-collection-verified-v2`.
Frozen verifier runtime: `ai/runs/policy-iteration-collection-collector-v2`.
Index: `ai/runs/policy-iteration-selection-index-v2`.
Selected output (only after all 30 cases verify): `ai/runs/policy-iteration-selected-v2`.
The first local collector finished 21 cases; its results are in
`strong/policy-iteration-collection-results-v2.json`. The second collector is
verifying the remaining nine cases with 8 independent processes (one ORT thread
each), logged at `ai/runs/policy-iteration-collection-collect-pass2-v2.log`.
The third indexing pass is logged at
`ai/runs/policy-iteration-selection-index-pass3-v2.log`. Earlier passes finished.
The collector now holds an exclusive local lock; indexers still require a
process check before resuming. Do not run the selection until all 30 cases have
verified and every case has its checked input index.

## 24 October continuation: revised teacher and 20-job paired pilot

The previous goal turn was **progress** (phase ablations, calibration and the
sealed-bid audit). This turn also made **progress**: a separate belief teacher is
implemented and tested, and all 20 diagnostic jobs were submitted. There are no
new gradient-trained models or production changes. The goal remains active.

The new teacher reconstructs each earlier bidder's public prompt and uses the
same frozen neural or economic policy as its continuation. It includes legal
passes. It clears current sealed bids, private deck/seed/log/plans and `lastMove`,
and preserves permitted public cash. Economic tie-breaking gets a separate
public sample/actor seed, shared across all candidate actions. This is an
inferred opponent model, not access to actual historical sealed submissions.
The helper explicitly requires the simulator's canonical submission order;
it rejects non-prefix submission orders. It is research teacher code, not a
new general-purpose live-game analysis API.

The historical engine and teacher remain unchanged. The new source overlays
eight files while retaining **1,411 base files byte-for-byte**. It passed:

- Five Node contracts, including all 320 public prompt reconstructions, private
  field mutations, legal passes, invalid inputs, worker-offset parity and
  old-control transition parity.
- Batched versus individual inference for all 317 reconstructed opponent prompts.
- **192 complete rollout checks** at 2p/6p, both editions and both continuation
  modes, with the full 2,400-step horizon and no caps. Uniform controls match the
  old worker; unchanged positions reproduce it under both belief variants.
- 64 terminal trajectories matching their immutable original teacher labels and
  128 independently checked initial-belief traces.

Frozen pilot source:

- Dataset revision `08ebc7df7a4d221fc04a0f4e2b99be59dbf046fc`.
- Archive `strong-source-sealed-belief-pilot-20261024-v1.tgz`.
- SHA256 `5e31ebbdbba9cf8f035f7339fbc763e536912fb5c77a72b2ada417dc69a47ff4`.
- Protocol SHA256 `6cf77cd0d0055ad776f91524ac4758855fd5df5f211e3e58e4ab84a668789912`.
- Descriptor `strong/sealed-belief-pilot-source-v1.json`; preflight and exact
  work plan are in the matching `preflight-v1` and `plan-v1` JSON files.

The diagnostic selects **39 affected positions**, one fixed root-ID hash per
count/source/edition/train-or-validation cell. The 5p/economic/original/validation
cell has no affected root and is explicitly absent. No outcome influenced
selection. These are diagnostic roots, not a newly enlarged training set.

There are **20 HF cpu-performance jobs**, each with a 4h timeout and 24 workers:
2–6 players × economic/self-play root source × neural/neural-economic continuation.
Both old uniform controls and new policy beliefs use the same 48 worlds per A/B batch and
all original candidate actions. Planned work is **312 searches / 88,320 complete
continuations**. Every job must reproduce its old-control sample outcomes and
terminal traces exactly before it can finish successfully. Collector rechecks
those artifacts against immutable original labels and the archived runtime.
No old labels, existing models or validation splits are overwritten.

At `2026-10-24T00:07:10.411047+00:00`: 6 completed,
14 running and 0 queued.
**25,920 rollouts are independently verified**.
Only roots with both continuation modes enter the recommendation comparison;
the current report has 0 complete-mixture roots, so no recommendation
quality conclusion is available yet. Read the timestamped status for current
handles, not these historical counts. Do not duplicate or restart live jobs.

```bash
ai/.venv/bin/python ai/strong/manage-sealed-belief-pilot.py status
ai/.venv/bin/python ai/strong/manage-sealed-belief-pilot.py collect
ai/.venv/bin/python ai/strong/manage-sealed-belief-pilot.py compare
```

Launch guards: `ai/runs/sealed-belief-pilot-launches-v1/`. Verified artifacts:
`ai/runs/sealed-belief-pilot-verified-v1/`. `launch` defaults to a dry run; all 20
jobs are already submitted. Preserve partial collections' pinned revisions and
inspect unknown/failed handles before any recovery. The manager uses the frozen
source for verification, not current-checkout engine or feature files.

The comparer selects on batch A and evaluates on B, then reverses, using an equal
mixture of both continuation modes and fixed original candidate-list order for
ties. It reports old versus new recommendations under policy-consistent beliefs.
These are conditional simulation diagnostics, never real-game strength or a
reason to select a trained candidate. Keep every negative or uncertain result.

Launch/preflight and first-three-shard verification evidence is archived at
model-repo revision `584a19ffe3fa83092f8afca81bd141430c77d882`, prefix
`runs/sealed-belief-pilot-evidence-v1` (50 files). Later
verified results have their own exact immutable model-repo revisions in the
results/verification records. The first archive is a partial snapshot.

The original fixed candidate screen now has **19,776/20,160 complete-cell
games**. Only `11101-6p-search_geo-0-4` remains, on its exact replacement
`6adbed2f046eb82b1ecd8532`. The original exit137 failure remains recorded.
Model 11102 is fully evaluated across all 27 cells: at 6p against geographic search,
win share is 28.52%, down 13.15pp from parent (paired 95% interval [-19.40,-7.16]pp).
It also has a positive 4p search contrast; retain the full report rather than
cherry-picking either direction. Neither candidate is selected or qualified.

The broader learning problem is still unresolved: sealed-bid consistency alone
cannot fix open-auction, nomination or building regressions. Next training data
should cover states reached by the changing policies, all counts and all three
decision types, using **fresh training seeds and fresh development holdouts**.
Do not quietly train on the phase-diagnostic development deals and then reuse
them as evidence of generalization. Pilot the corrected teacher and data
coverage first; do not simply retrain the same small head on the same old roots.

## 24 October checkpoint: regressions isolated, teacher assumption audited

This goal turn made **progress**. No model is selected or qualified, no final
seeds were used, and no production files were changed. Both trained models are
rejected for promotion on current development evidence; the previous parent
also remains below the full strength requirements.

The original fixed screen now has **19,392/20,160 complete-cell games**:
27 parent cells and 26 cells for each candidate. Only each candidate's 6p
geographic-search cell remains incomplete. At `2026-10-23T23:41:45.784875+00:00`, the
331 recorded handles comprise 322 completed, eight running and one historical
error. Do not relaunch the eight live jobs. Consult the timestamped status file
and exact guards before future collection or recovery.

The original `11101-6p-search_geo-0-4` job `6adbe72b1e112550ce7d9c7b` failed
with exit 137 and no result artifact. Resource metrics were unavailable (HTTP 406),
so OOM is **not established**. One exact clone replacement,
`6adbed2f046eb82b1ecd8532`, is running. It retains the same source, seed, model,
hardware, 24 workers, 4h timeout and full horizons. Original failure and guards
are preserved in `strong/strategic-correction-screen-retry1-v1.json`.

### Calibration diagnostic

`strong/strategic-correction-calibration-v1.json` uses the immutable 1,920-root
labels and fixed exported weights, without gradients or threshold fitting.
On 480 validation roots, 11101 changes 113 decisions and predicts +0.01552 mean
advantage, versus +0.00518 in the simulation labels. 11102 changes 144 decisions,
predicts +0.01820 and achieves +0.00686 on those labels. Of changed validation
actions, 28.3% and 33.3% respectively have negative teacher targets. These
post-hoc diagnostics suggest overconfidence; they do not validate teacher
realism or measure full-game improvement.

### Completed causal phase isolation

All **120 HF diagnostic jobs / 7,680 full games** completed and are independently
verified. There are 30 complete cells: two models, 2–6 players, and nomination,
bid or building changes alone. Each arm uses the unchanged parent outside its
named phase. Every cell has 16 paired development deals, all seats and all four
rules against the economic opponent. None uses reserved final deals.

Preflight proved exact complete-game parity for `all` versus the original
candidate and `none` versus parent (128 games across both models at 2p/6p).
Another 48 games exercised all six named model/phase arms. Full collection
reencoded **104,641 public disagreement states** with the frozen runtime and
reproduced both models' choices, while checking every routing ledger and cap.
These are encountered states, not a count of independent games or unique boards.

No model/phase/count cell has a positive marginal 95% improvement interval
against parent. At 6p, 11101's isolated nomination/bid/build changes lose
5.86/8.98/8.07 percentage points; all three marginal intervals are wholly
negative. For 11102, wholly negative cells include nomination at 2p/4p/5p,
bidding at 2p, and building at 5p. All other results and uncertainties remain in
`strong/strategic-correction-ablation-results-v1.json` and its assessment.
The regression is not confined to bidding. These are exploratory, reused
development deals; no simultaneous-confidence or post-hoc candidate claim.

Frozen diagnostic source: dataset revision
`8da026471210f9f8beb2c23a9289d764d8982c3b`, archive
`strong-source-strategic-correction-ablation-20261024-v1.tgz`, SHA256
`1d2e5c1daad55f630b03d5070f49ab91eab7d272d9eee7bd8f36f106be73109f`.
Only the runner and protocol were overlaid on the original screen archive;
1,400 base files are unchanged. Do not edit those frozen overlays. The manager
collects with the frozen archive, not the drifting current engine/encoder.
A local collector missing-import failure was fixed and partial folders were
reconciled to their original immutable artifact revisions; no HF job was rerun.

All verified records, full comparison, job guards and independent check logs
are archived at model-repo revision `53a9f6dd70a3e6eb2a24c060f0989f7c3197c8f4`,
prefix `runs/strategic-correction-ablation-evidence-v1` (373 files).
Earlier launch/preflight/calibration evidence is at
`c9c75161f47d0e107ecdcb6052c6a77e11246879`,
prefix `runs/strategic-correction-diagnostics-evidence-v1`.

### Sealed-bid belief mismatch

The frozen `createAnalysisScenario` samples an already-committed affordable
opponent's bid uniformly between minimum and all available cash, with no pass.
This is independent of whether the continuation uses neural or economic bots.
A read-only audit covered all 320 sealed-bid teacher roots. 184 have earlier
committed opponents, giving 317 reconstructed public opponent prompts. The
uniform assumption's mean is 49.22 Elektro, while the frozen parent and economic
policy choose 24.51 and 26.94 respectively, including passes as zero. They choose
42 and 22 passes where the sampler forces a positive bid.

These are **hypothetical policy choices at reconstructed prompts**, not reads
of historical hidden bids. The diagnostic clears bids, private logs/deck/seed,
plans and `lastMove`. All 320 cases passed engine-forward public-feature parity
and invariance to deliberately changed private fields. No gradients, production
engine changes or old-label edits were made. This establishes a mismatch with
the specified continuation policies, not its causal contribution to losses.
It cannot explain regressions in open auctions or all isolated phases.

Report: `strong/strategic-sealed-belief-audit-v1.json`. Audit code and raw rows
are archived at `961287c89bc32f388b3ed384624b707b24b0b7b1`,
prefix `runs/strategic-sealed-belief-evidence-v1`.

## Recovered evidence

No HF jobs were active at resume. All intended jobs left at the pause completed.
The three old image-pull errors already have completed replacement jobs and
must not be retried again. Recovered raw artifacts are pinned to model-repo
revision `7240a51338ba19cc47c437c955a61bb46f1ea70e`.

1. All 20 teacher pilot shards are independently verified: 240 roots with both
   continuation modes, 230,592 full counterfactual rollouts, no caps. The
   independent-batch validation diagnostic is +0.0743 mean paired advantage
   selecting on A/evaluating on B, and +0.0732 in reverse, with 65.8% agreement.
   These are conditional simulation diagnostics, not whole-game strength.
2. The full collection is verified and merged: 3,840 unique games, 7,680 twin
   executions and 200,775 public decision states. All 12 remaining 4–6p geographic
   search slices were checked, and original records and indices preserved.
   This collection contains more states than the fixed 1,920-root label design;
   do not silently change the selected roots or train/validation split.
3. All three 6p guided-search comparisons are verified: 192 games per model,
   eight paired deals with every seat and all four rule combinations. Every
   model lost 9.375 percentage points relative to its raw policy; the paired
   deal 95% interval is [-17.1875,-1.5625] points. Guided search remains unqualified.
   Preserve the earlier 5p Recharged/open regression as well.

Machine-readable results:

- `strong/strategic-teacher-training-results-v1.json`
- `strong/strategic-training-collection-combined-results-v1.json`
- `strong/multiplayer-search-transfer-results-v1.json`

## Latest verified state

- All 160 teacher shards are verified: **1,836,672 completed rollouts**, 1,920
  complete-mixture roots, 1,440 train and 480 validation. Each player count has
  384 positions; nomination, bid and building each have 640. No truncations.
- Complete manifest SHA256:
  `6135dba264e18bdc0d8002ca50719bb3340f94b05e22221812864295fe651e57`.
  It is frozen into the training source; do not edit it.
- Training job **`6adbddc9046eb82b1ecd7ac0`** completed on NVIDIA L4. Both
  seeds completed 120 epochs/720 updates; fixed validation selection chose
  epoch 30 for 11101 and epoch 50 for 11102. No retraining is needed for this cohort.
- Both models passed independent collection at
  `ai/runs/strategic-correction-verified-v1`: frozen parent tensors, optimizer
  steps, epoch selection, strict exports, all 2,553 serving requests and all
  1,920 labeled positions. Values and 1,457 out-of-scope actions are preserved.
  These checks establish correctness, not strength.
- Parent reference is complete: **27/27 cells and 6,720/6,720 games**, all
  independently verified. Both trained models' 2p and 6p runtime probes are
  verified. Their **216 full arena shards / 13,440 games** are submitted;
  inspect the existing handles before any retry.
- Both standalone packages were benchmarked on the actual AMD 8840U. All
  5,106 requests were legal and every move matched the frozen evaluation
  runtime. Warm p95 was 6.52ms/6.63ms. This establishes serving feasibility,
  not strength; neither candidate is selected.
- The alternate A10G startup probe `6adbdfa7046eb82b1ecd7b29` was cancelled
  while still queued once the L4 started. It performed no training and needs
  no retry (`strong/strategic-correction-hardware-probe-v1.json`).
- No model is qualified. The parent versus A260 result is 27.6% over 192 games/
  16 deals, 95% interval [21.88%,33.85%], below the 40% floor. Versus geographic
  search, parent win shares at 2/3/4/5 players are 49.22/25/23.05/38.125%; sealed
  weaknesses remain (5p Recharged/sealed is 20%). Preserve all adverse cells.
- The historical 23:07 UTC collection checkpoint verified 95 of 216 candidate shards.
  The 24 October section above supersedes this partial count.
  Complete cells total 10,944 games: all 27 parent cells, 14 for 11101 and 3 for
  11102. **Both candidates show regressions.** Against economic at 4p, their
  paired differences are -16.41pp and -16.80pp; both marginal 95% intervals are
  wholly negative. 11101 also loses 17.06pp at 6p economic and 15pp at 5p rush.
  All positive and negative results remain in the report. These candidates
  must not be promoted from modest teacher-validation improvements.
  See `strong/strategic-correction-development-assessment-v1.json` and its
  immutable source snapshot in `strong/strategic-correction-candidate-arena-evidence-v1.json`.

## Work resumed

All 140 remaining teacher shards (deals 2–16) were submitted using the original
guarded launcher. Each of the seven 20-job batches covers 2–6 players, both root
sources and both continuation modes. Exact handles and timeouts are saved in
the status snapshot and launch guards. The first full snapshot had 67 running,
72 scheduling and one completed; this is historical, not a live count.

The first resumption checkpoint had 30/160 independently verified shards.
The live verified counts are in `strong/strategic-teacher-training-results-v1.json`.
The faster economic-opponent jobs finishing first does not make a partial dataset
ready for gradients; all 160 shards and 1,920 complete-mixture roots are required.

These are CPU simulation jobs, using 24 engine workers and single-thread FP64
ONNX inference. The lighter CPU image checks batching parity on all 2,553
serving fixtures before generating labels. Each shard retains 48 independent
worlds per A/B batch and the full 2,400-step continuation horizon. Runtime
admission uses all 20 verified pilots, twice the slowest matching root and 25%
timeout headroom. Timeouts are 4h or 5h; do not shorten games or samples to fit.

Frozen teacher source:

- Dataset revision: `837d94e14272163c33e5e55fa9c24b24686a28ae`
- Archive: `strong-source-strategic-teacher-training-20261010-v1.tgz`
- SHA256: `a011f9ee4b8116b99220913a7db9d00849e9e593137cdb7e435e116fcafdd6c3`
- Protocol SHA256: `3c39786cc6c44a3838d3c4183c312c94a26563222b2720572010b76bbdd62a76`
- Roots SHA256: `f0fd62b4dd75c6b6c0936adeb1ffc75a2747cb2c62debe6b5d0aba60dbb4a091`

Never edit those frozen overlays. Preserve errors and ambiguous launch intents.
Inspect exact existing handles before any retry; never treat a delayed tool
response or absence of artifacts as evidence that a job did not start.

## Next training stage

The design remains `strong/strategic-correction-design-v1.json`: freeze the
complete discard-correction 10102 parent and train a 97,473-parameter head on
paired advantages for nominations, bids and building. All other decisions and
the value head remain unchanged. The exact public shortlist plus the parent
proposal is used; the fixed margin is 0.025. Seeds 11101/11102 are fixed before
gradients. Keep negative and uncertain evidence and whole-deal data splits.

New source builder and launcher:

```bash
ai/.venv/bin/python ai/strong/build-strategic-correction-source.py
ai/.venv/bin/python ai/strong/launch-strategic-correction.py
```

The builder rejects incomplete manifests before upload. It preserves the
teacher engine, parent and base features byte-for-byte, overlays only explicit
correction/serving files, checks all 1,920 roots, and uploads an immutable source
archive. The launcher requires that full source/data check and an exclusive
launch guard before submitting one L4 GPU job for both seeds. Supply the cached
token through the environment only. The guarded job above is complete and verified; do not rerun the launcher.

Code-only checks use `build-strategic-correction-source.py --code-only` and
never upload a training source or admit training. The zero correction passed
strict parent/ONNX checks on 2,553 positions. The arena whitelist now recognizes
feature revision 4.3 at all player counts. A separate 160-game plumbing check
passed across 2–6 players: every complete game record was identical between
zero correction and parent. Evidence is in
`strong/strategic-correction-source-code-preflight-v1.json`.

The public-information check now also mutates opponents' submitted sealed bids:
422 sealed-auction fixtures pass, with identical features and shortlists. Actual
trained exports must pass `strategic_correction_check.py`: all 2,553 serving
positions, unchanged parent values and out-of-scope actions, and native/ONNX
parity over all 1,920 labeled roots. The independent training collector additionally
checks parent tensors, optimizer steps, fixed validation selection, checkpoint
hashes and actual exported actions before writing evaluation model pins.

The trainable parent is pinned to model-repo revision
`b115a2d78aae095e51fb72a5535b3507abdf90c0`,
`runs/discard-correction-v1/10102/best.pt`, SHA256
`66a10b831a54843063bbca89743a542ed1f89515a16452a40483eef369c59bd8`.
Its serving ONNX SHA256 is
`57f8255e79b991ba466f91e953d0bca6868144bb543577fc0dad8ade387ebf68`.

## Frozen training source and collection

- Descriptor: `strong/strategic-correction-source-v1.json`.
- Dataset revision: `46d6986a28db0db26122b7188d833bcfb2ce8c8b`.
- Archive: `strong-source-strategic-correction-20261023-v1.tgz`.
- SHA256: `bea355639fa669217bd2636d8aa755976f4a291c0abb7daa9c4a00f35462cce5`.
- Full preflight: `strong/strategic-correction-source-preflight-v1.json`.
- Launch guard: `ai/runs/strategic-correction-launch-v1/launch.json`.
- Live snapshot: `strong/strategic-correction-job-status-v1.json`.
- Expected outputs: model repository prefix `runs/strategic-correction-v1`.
- Complete admission evidence: model-repo revision
  `67bb0d978b404ca49dfd034cb19c9dfc4ea8721d`, prefix
  `runs/strategic-correction-training-admission-v1` (178 files).

Do not edit training source overlays, design, or full label manifest while the
job runs. On completion, pin the model-repo revision and independently collect:

```bash
ai/.venv/bin/python ai/strong/collect-strategic-correction.py REVISION NEW_OUTPUT_DIRECTORY
```

The collector must pass for both seeds before either enters evaluation. A failed
job or check remains failed; inspect its original logs and uploaded status rather
than silently retrying or weakening tolerances. The source package intentionally
keeps the pre-gradient design/manifest flags unchanged as historical metadata.

## Verified trained models and completed probes

Raw training/export revision: `6be6f2af36d3382d43013621eab382c16a4cc1ae`,
model-repo prefix `runs/strategic-correction-v1`. Independent result:
`strong/strategic-correction-training-results-v1.json`. Exact immutable model pins
are `strong/strategic-correction-screen-pins-v1/{11101,11102}.json`.

| Seed | Selected epoch | ONNX SHA256 | Held-out simulated advantage |
| --- | --- | --- | --- |
| 11101 | 30 | `9f8d87b28dc1ed76770e7ffe8457a87fb3fb014d866b43b571ce838b87ff0f32` | +0.0051812 |
| 11102 | 50 | `85a8885a0f30b32f7f4c131f2d07003724ee4cd5e8c682c4d20d2842ef60ec09` | +0.0068631 |

Those are modest conditional simulation-target gains, **not real-game win-rate
improvements**. All negative rule/count cells remain in the result. Native/ONNX
choices match exactly; 225/257 eligible serving fixtures changed respectively.
Gradient optimization took 1.91s/1.76s; simulation, data and verification dominate
this stage. Local serving timing belongs to the HX370, not the target 8840U.

Independent evidence is archived at model-repo revision
`f0a838c5e61534c6f39504dd70639b59aed15ea7`, prefix
`runs/strategic-correction-verified-evidence-v1` (39 files). Raw PT/ONNX files stay
pinned to the original training revision. Keep the original verified result and
pins; the collector intentionally refuses to overwrite existing model pins.

All four exact-model runtime probes were submitted at 22:38 UTC. Both 2p probes
are independently verified at artifact revision
`3b3044a49826467fd78c389e5166c99b12d52b35`: eight games each, 103.41s/108.54s,
no caps. Both 6p probes also completed and were independently verified:
11101 took 1,205.15s (artifact revision
`35a34845b207ce4bb667aee632270b010edcfe1e`); 11102 took 1,314.32s
(`d2de0a061a7f6c844f2ee4ad3ef4d6dcc962d7cd`). Each contains 24 complete
games without game or search truncation.

| Seed | Players | HF job |
| --- | --- | --- |
| 11101 | 6 | `6adbe1d5046eb82b1ecd7c5c` |
| 11101 | 2 | `6adbe1d61e112550ce7d9755` |
| 11102 | 6 | `6adbe1d81e112550ce7d9757` |
| 11102 | 2 | `6adbe1d9046eb82b1ecd7c5e` |

Do not duplicate them. Both automatic admission reports permit four-deal
shards with a four-hour timeout, without reducing any game/search horizon:
`strong/strategic-correction-screen-{11101,11102}-admission-v1.json`.
All 108 full shards per candidate were submitted by 23:05:08 UTC. The batch
launcher `strong/launch-strategic-correction-screens.py` checks existing guards,
pins and source hashes and stops on ambiguous launches; its default is dry-run.

## Fresh whole-game evaluation

The evaluation implementation and frozen source are ready. All **108 parent
reference shards** are independently verified, covering 6,720 games. Do not
duplicate those launches. The two runtime probes also completed and were independently
verified: 8 two-player games in 119.84s and 24 six-player games in 1,258.66s,
both against geographic search, without truncation. The conservative admission
calculation permits four-deal shards with a four-hour job timeout.

- Source descriptor: `strong/strategic-correction-screen-source-v1.json`.
- Dataset revision: `2c33a8878a742eabf54b94b7e2148a63223318e8`.
- Archive: `strong-source-strategic-correction-screen-20261023-v1.tgz`.
- SHA256: `162f93944f508853dcf446af74f2ba9a331e557d337a5b7193e2f764817562fb`.
- Protocol SHA256: `cd038070dcf7f875cecab0a9ecfa095447675cfd75bc3584c157fd1d4261787a`.
- Results: `strong/strategic-correction-screen-results-v1.json`.
- Exact model manifests: `strong/strategic-correction-screen-pins-v1/`.

Do not modify frozen evaluation overlays while these jobs run. The runtime
retains the original engine and features; seven explicit overlays support the
new correction and audited deal offsets. Preflight verified 40 plumbing games,
nonzero deal offsets and nine rejected corruptions. The arena outer cap remains
1,600 steps and search horizon 2,400; a cap invalidates the result, never turns it
into a scored ordinary game.

Collect a completed shard at an immutable model-repo revision:

```bash
ai/.venv/bin/python ai/strong/manage-strategic-correction-screen.py collect parent N OPPONENT START END REVISION
ai/.venv/bin/python ai/strong/manage-strategic-correction-screen.py compare
```

Only complete cells enter comparison, retaining all missing cells explicitly.
Both trained seeds remain separate contrasts with the parent. Training collection
uses `collect-strategic-correction.py REVISION NEW_OUTPUT_DIRECTORY`; only after
independent verification does it produce pins for 11101/11102. Each then needs
its own verified 2p and 6p search runtime probe before launching its 108 shards.
Both trained seeds have verified probes and their full 108-shard screens are
submitted. The local launch logs are
`ai/runs/strategic-correction-{11101,11102}-full-launch-v1.log`.

Independent verification records and preflight logs are also archived in the
private model repository at revision `141ef2843681c3edb883ef79debe8462cf943c70`,
prefix `runs/strategic-correction-resume-evidence-v1` (258 files). This snapshot
contains partial results, not a completed training or strength claim. See
`strong/strategic-correction-resume-evidence-v1.json` for the manifest hash.

Complete parent-reference evidence: model-repo revision
`f44c5dde6958d322aae908982e02279fb55a0c47`, prefix
`runs/strategic-correction-parent-reference-evidence-v1` (113 files). The immutable
snapshot preserves the report used by `strong/strategic-correction-parent-assessment-v1.json`.
Seven development point estimates fall below the corresponding final reference
floors: search at 2/3/4p, heuristic at 2p, legacy at 4/5p, and A260 at 3p. Some
rule-specific intervals also fail to exclude chance, including Recharged/sealed
at 5/6p. The 6p search overall share is 41.67%, interval [36.98%,46.35%]. These
are development diagnostics; final required deal counts and all gates still apply.

## Final runtime and standalone target packages

The old readiness report remains as an audit of the wrapper mismatch. The new
`strong/final-strategic-runtime-readiness-v2.json` resolves it:

- Source dataset revision `b279b0e8fca796d8a726de2d20b8340ddd13d52e`, archive
  `strong-source-final-strategic-runtime-20261023-v1.tgz`, SHA256
  `85eeb02b4a25eb0a652bba453325ff8958a0629bf40396c21d12e223222afe51`.
- Only the provenance-aware `arena-job.py` wrapper changed; 1,399 other base
  files retain their hashes. Both models passed the real wrapper/evaluator on
  64 separate plumbing games, including nonzero deal offset 4. No final seeds.
- Evidence revision `35a34845b207ce4bb667aee632270b010edcfe1e`, prefix
  `runs/final-strategic-runtime-evidence-v1`, 18 files.

The standalone package builder initially caught current-checkout runtime drift
and stopped before anything ran on the target. Preserve that rejected local
attempt at `ai/runs/strategic-packages-8840u-v1`. The corrected package preparation
at `ai/runs/strategic-packages-8840u-v2` uses the frozen source directly; only the
packager and serving dependency declaration were added/updated. Every packaged
engine/worker/encoder file was compared with the frozen source.

Both packages completed all 2,553 fixtures from an unrelated working directory
on `ssh minipc`, with full per-request responses retained. Independent local
collection rechecked legality, request/revision identity, schema, value ordering,
timing summaries and **all 5,106 moves against the frozen evaluation runtime**.

| Model | Warm median | Warm p95 | First request |
| --- | --- | --- | --- |
| 11101 | 3.81ms | 6.52ms | 217.85ms |
| 11102 | 3.89ms | 6.63ms | 206.71ms |

These are sequential engineering timings, not statistically ranked model
performance. Exact reports: `strong/strategic-packages-8840u-results-v1.json`.
Remote directory `/home/coyotte508/powergrid-ai-strategic-packages-v1` completed;
no target process remains to restart. Packages and raw evidence are archived at
model-repo revision `555d4ab983369dfe183fc68b9d555690f5f3d583`, prefix
`runs/strategic-packages-8840u-evidence-v1`. No production routing was installed.

## Ordered continuation

1. Inspect and collect the existing replacement 6p search job
   `6adbed2f046eb82b1ecd8532`. All other fixed screen cells are verified. The one failed job has exactly
   one live replacement; never rerun either merely because it is quiet. Refresh
   with `ai/.venv/bin/python ai/strong/refresh-strategic-correction-jobs.py`, then
   collect complete cases at immutable revisions and regenerate the comparison.
   `ai/runs/collect-completed-resume.py` is a local convenience wrapper. The
   committed manager supports per-case collection. Do not regenerate the frozen
   teacher label manifest or edit source archives.
2. Phase isolation is fully complete. Do not relaunch its 120 jobs. Read
   `strong/strategic-correction-ablation-assessment-v1.json`, calibration and the
   sealed-belief audit. Neither candidate or phase-gated derivative is selected.
3. The separate policy-consistent sealed-belief teacher is now implemented and
   its 20 paired diagnostic jobs are submitted. Collect them with the committed
   manager, inspect complete-mixture A/B results, and preserve all old control
   checks and negative findings. Do not restart live jobs or overwrite old labels.
   Full training is not yet admitted by this diagnostic alone.
4. Address the broader repeated-policy/generalization problem too. Capture new
   policy-visited public states, including all three decision types and every
   count/rule, with new whole-deal train/validation splits. Keep parent proposals
   and uncertainty, and account for the rollout-policy versus deployed-policy
   mismatch. The frozen 1,440-root training set and modest simulation gains did
   not transfer to actual games. Do not use an auction-only fix or threshold
   fitting on reused development deals as evidence of strong play.
5. Any next gradients run on HF Jobs only. Establish source/data/policy checks,
   train under a predeclared small pilot design, and test complete games on fresh
   development deals before scaling. Preserve adverse cells and both seeds.
   Leave the final protocol and final seeds unchanged until a candidate merits it.
6. Final 4.3 wrapper readiness and exact AMD8840U packages for these two models
   are verified; runtime readiness does not qualify them. A changed model/runtime
   needs its own serving checks and target benchmark. The reserved final gate
   is still mandatory and unused.

Scope remains Germany, automatic setup, 2–6 players, original/Recharged and
open/sealed auctions. All players' money is allowed. Hidden deck order, random
seeds, submitted sealed bids and queued plans stay excluded. Other maps and
calibrated round-by-round value analysis remain future work.
