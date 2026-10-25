# Power Grid AI — ACTIVE, resumed 23 October 2026

**Start with [the current resumption handoff](HANDOFF-2026-10-23-RESUMED.md).**
The October 23 policy-iteration HF jobs completed. All eight trained seeds and four ensembles are verified
and archived. Actual 8840U benchmarking passed 10,212 requests with exact moves:
median 4.3–5.9 ms, 95th percentile 7.0–8.8 ms, cold start 214–255 ms. These are
model-only timings. No candidate is qualified or published; final seeds are unused.

**Latest — 25 October, 06:20 UTC: data prepared; complete-study coordinator and archive ready.**

The original training coordinator **PID 2825298 / session 39111** completed data
preparation at **06:19:32 UTC**: **313,783 training rows / 52,543 validation rows**
from 1,920 / 320 whole-deal-split games. All 320 held-out test games remain excluded.
The report records **451 validation rows with naturally identical training inputs**;
no rows or outcomes were removed or used to alter the frozen design. Data-check
SHA256: `db17a5421fe63d450bdac9843ac067b49e8e43f7979f42dace17d8d485b368eb`.

The original owner is now executing `archive_data`; child **PID 3165802** was
directly observed running. Do not duplicate the packaging/upload or launch stages.
All 30 pinned execution files remain unchanged. No GPU job or gradient update yet
at this checkpoint. Data checkpoint:
`ai/runs/opponent-surrogate-data-preparation-checkpoint-v1.json`, SHA256
`0b03bd84d3876b05bcdef335a5f3cdf7ab2d2e8070e1f53402d069c7799310b3`. The complete raw collection index is already committed.

`strong/coordinate-surrogate-continuation-study-v1.py` now owns a complete admitted
study, with eight passing tests. It requires actual trained selection, selected
surrogate timing and the measured study admission before creating execution state.
It submits at most the admitted concurrency, collects before further submission,
keeps each original handle, and indexes only after all 480 planned jobs verify.
Caps retain all records and finish as `complete_with_caps`; remote failures stop
for inspection. Uncertain submission/collection operations retain their operation
state and cannot silently retry or replace jobs. Observation errors are not marked
as remote job failures. Changed code/admission or existing original submissions
prevent a second owner. Dry runs do not create output or submit work.

The coordinator is **implemented but not started**. Once actual learned selection,
source packaging and separate selected-opponent calibration complete, use the
study launcher `prepare`, then start this coordinator once with `--execute
--interval-seconds 180 --max-hours 48`, preserving its returned session/PID. Do not
also manually call `launch-ready`. If the user later asks for no more jobs, stop
this local coordinator before any further study submissions. It never owns
training, source preparation, calibration, policy selection or full-game strength.

`strong/archive-surrogate-continuation-study-v1.py` is also ready. It requires the
full original index, reproduces the complete comparison, independently recomputes
terminal tie credit, deduplicates physical prior-search work, and preserves all
raw receipts, paired records, adverse groups and caps in a single private archive.
A capped complete corpus may be archived with `complete: false` and no aggregate;
a failed or missing root cannot become a survivor-only result. The helper preserves
an original upload/output and refuses automatic replacement. Three tests pass,
including independent score/tie calculations, all **48 saved real-engine preflight
outcomes**, and refusal to create/archive a partial corpus. No new simulations,
scientific-root executions, uploads or actual study archive were created.

- Coordinator preflight: `ai/runs/surrogate-continuation-study-coordinator-preflight-v1.json`,
  SHA256 `df8b6b32ff576e97de6270ffc428128d0280c953e8c5f1089b5beda89f0acd3b`.
- Coordinator checkpoint: `ai/runs/surrogate-continuation-study-coordinator-checkpoint-v1.json`,
  SHA256 `af33916ab96d112152a3ebe4c8773005d8cd47dd71e149192ccf7647fed7fc99`.
- Archive preflight: `ai/runs/surrogate-continuation-study-archive-preflight-v1.json`,
  SHA256 `716ee56b929c4fb4acf9fabde8bba5d13dcd87ea0c3e69e0f1fddb398c827ae4`.

Next: let the existing training owner finish data packaging and launch its original
L4 calibration. Inspect that original job and measured admission, not a replacement.
Then full four-seed HF training, independent audit and validation-only selection.
If a learned policy wins, run the prepared held-out imitation evaluation without
reselection; freeze study inputs and source; run the selected-surrogate timing;
then the measured full-study coordinator and final archive helper. Fresh hybrid
full-game evaluation, selected-policy final adapter and actual 8840U hybrid latency
are still required. No selected candidate, publication or final-seed use. Goal active.

**Previous — 25 October, 06:10 UTC: complete collection indexed; training data preparation running.**

The original collection coordinator finished and exited normally at **06:08:27
UTC**. Its complete index now verifies **2,560 games / 640 exact twins / 418,686
teacher rows / 34,306,096 teacher rollouts**, all 40 unique original jobs and all
180 split/count/rule/phase groups. Whole-deal splits: **1,920 training, 320
validation, 320 held-out test games**. Each original raw archive stays pinned to
its own immutable private HF revision and digest. Index:
`strong/opponent-surrogate-collection-results-v1.json`, SHA256
`1e7cfb2ddd9c160fe0bc1dfdff08f0da38a0641ee51e3e012b6bc41a0229c83e`.
Do not restart original PID 2009367 / session 80214.

Original training coordinator **PID 2825298 / session 39111** began `prepare_data`
at **06:08:36 UTC**, with child **PID 3098617** directly observed running. Its log
is `ai/runs/opponent-surrogate-training-coordinator-v1/prepare_data.log` and output
is `ai/runs/opponent-surrogate-training-data-v1`. Let this owner finish all stages;
do not run them manually alongside it. No GPU job or gradient update yet at this
checkpoint. All 30 pinned execution files remain unchanged. Test labels remain
excluded from training and selection. This completes collection, not model quality.

Completion checkpoint: `ai/runs/opponent-surrogate-collection-complete-checkpoint-v1.json`, SHA256 `3f6d470453e0d1a1a458789bc1510fd95150e51269fc9e6d614d41a41949fbe1`.

**Previous — 25 October, 06:07 UTC: all collection jobs complete; full-study management ready.**

All **40 original opponent-data jobs have completed**, and every shard has a
verified receipt. The last seven original handles were directly inspected as
COMPLETED. Original coordinator **PID 2009367 / session 80214** is alive in
`indexing` (40 verified, no failures), independently rechecking the full collection
before its combined index appears. Original training coordinator **PID 2825298 /
session 39111** is alive, waiting for that complete index. Neither coordinator's
pinned code changed. Do not run their stages concurrently or start replacements.

The complete paired-study launcher and collector are implemented:
`strong/launch-surrogate-continuation-study-v1.py` and
`strong/manage-surrogate-continuation-study-v1.py`. The launcher requires the actual
selected-surrogate timing result, independently reaudits it, and binds the same
frozen source, roots, policy, protocol and tested management code. There is no
actual admission file, source upload or study submission yet.

Every planned root has one job containing all **three modes × eight worlds × two
actions**: **480 jobs / 23,040 continuations** over the full fixed corpus. At most
32 run concurrently, each with eight CPU workers. The allowance uses 15 minutes
setup plus twice the largest measured sum of all three modes on the same separate
timing root, with 25% timeout reserve; every player count receives the global
allowance. Memory is twice measured peak plus 4 GB. It refuses demands above the
12-hour / 32 GB envelope. No samples, roots or search budgets are reduced to fit.
The actual timeout cannot be admitted before the learned timing result exists.

Submission keeps exclusive guards and original job handles; failures, unknown
submissions and observation errors prevent blind replacement or further launches.
The collector preserves logs and any partial archive from failed jobs. Completed
capped jobs retain all modes and paired records. Indexing requires all 480 original
jobs and invokes the existing paired analysis on every record; any cap suppresses
aggregate estimates instead of retaining only successful cases. The full study is
continuation-fidelity evidence, not full-game strength or deployment latency.

**Eleven management tests pass**, with no network submissions or new simulations:
actual frozen root-grid coverage, measured-resource inputs and invalid inputs,
premature preparation refusal, launcher/collector code binding, dry runs and
capacity, uncertain submissions, failed/unknown original handles, partial-failure
archive retention, complete 480-record synthetic aggregation, cap retention and
missing-job/receipt refusal. The first ten-test run is also preserved. The synthetic
timing and aggregation fixtures do not claim actual learned-surrogate measurements.
A code-read check corrected the collector's list/dict call boundary before testing;
the full synthetic aggregation test exercises the real analysis call.

- Preflight: `ai/runs/surrogate-continuation-study-management-preflight-v1.json`,
  SHA256 `62f72675685facd2b80fb4e11fd2f9412401f01ae82eb57b3d73bb16f4298996`.
- Checkpoint: `ai/runs/surrogate-continuation-study-management-checkpoint-v1.json`,
  SHA256 `cf393f383f3706d51bafa5684e530de205c64d6dd290791a666095339efe64f3`.

Next: let the original collection/training owners finish indexing, data preparation,
HF calibration, four-seed training, audit and validation selection. After a learned
selection, freeze full-study inputs, prepare/check/upload its source, run and collect
the separate selected-opponent timing job, then use the new study launcher `prepare`
and `launch-ready --execute` and manager `collect-ready` / `index`. Implement a
single coordinator for those complete-study jobs before sustained submission; it
must preserve all original handles and not auto-retry. Archive the complete study,
inspect fidelity/adverse groups, then evaluate a heterogeneous hybrid on fresh
full games and actual 8840U hardware. No new HF jobs, gradients, candidate,
publication or reserved final seeds in this checkpoint. Goal remains active.

**Previous — 25 October, 05:59 UTC: source packaging and selected-opponent timing ready.**

The full-study source builder and selected-surrogate runtime runner are now
implemented. The builder requires the actual audited validation-selected learned
policy and the complete 160-game / 480-root manifest before creating any source
output. It preserves all 1,463 base-runtime files, bundles only selected ONNX
members, binds roots/policy/training/source hashes, and requires isolated inference
checks on all 480 study positions plus the 24 separate timing positions. Uploads
retain an intent and exact receipt; no actual package has been created or uploaded.

The selected-only timing runner keeps the original 24 separate runtime roots and
all eight worlds / two actions: **384 continuations**. It does not repeat reference
or population measurements. It preserves caps and partial failures, verifies saved
records, and records wall time, CPU and summed process RSS. Seven tests pass. The
original local engineering preflight completed **16 continuations, zero caps**,
exactly matching all saved records, with all 1,463 runtime files unchanged. This
uses an explicitly **untrained fixture**, not an actual trained-surrogate timing
or playing-strength result. Its output already exists; do not rerun it. The initial
failed test-harness argument-index log is preserved separately; corrected tests pass.

`strong/manage-surrogate-continuation-selected-cost-v1.py` implements preparation,
one guarded HF launch, inspection and independent collection. Seven additional
tests pass: measured allowance, dry run, exact source/model environment, uncertain
submission without retry, failed-job/observation handling without replacement,
pending collection, and ambiguous/failed evidence retention. Exception receipts
record only the error type. No tests contact HF or run additional games.

The prospective timing allowance is **one CPU-upgrade job, eight workers, two-hour
timeout**: 15 minutes setup plus 24 times eight times the slowest completed mixture
root, with 25% reserve; memory allowance is twice previous peak plus 4 GB. This is
a conservative calibration allowance, not a speed guarantee. No admission file or
job has been created; the actual trained selection and checked source are still
required. The full 23,040-continuation study remains unadmitted and needs its own
measured launcher/collector after this calibration.

- Package preflight: `ai/runs/surrogate-continuation-study-package-preflight-v1.json`,
  SHA256 `0089e359c72f1476074dc244a250ccb82295279da6d2b13001c1077a87a08303`.
- Manager preflight: `ai/runs/surrogate-continuation-selected-cost-manager-preflight-v1.json`,
  SHA256 `6851f3aadcdc9f7c8547a5701871f457c3a4e59595f660eaf5063cb6cbedec8a`.
- Checkpoint: `ai/runs/surrogate-continuation-study-package-checkpoint-v1.json`,
  SHA256 `901bdaaa5670529c7f1bf440a5f7763bfac3cb4716d19422f8ba57a210446053`.

Original opponent-data coordinator PID **2009367** remains alive at **33/40
verified**, no failures. Original 6p job `6add73271e112550ce7e6a20` was directly
observed **COMPLETED**; let the coordinator collect it. Training coordinator PID
**2825298 / session 39111** remains alive waiting for complete collection, with no
GPU jobs launched. All pinned coordinator code is unchanged. Do not duplicate
preparation, submissions or collection ownership.

Next: let those original coordinators finish collection and own training through
validation selection. If a learned policy is selected, run
`prepare-surrogate-continuation-study-v1.py`, then builder `prepare`, `check`,
`upload`, then the selected-cost manager `prepare`, `launch --execute`, and collect
the same original handle. A prior-winning selection must remain a valid negative
result. Implement full-study admission/launch/collection using actual timings;
then test a heterogeneous hybrid on fresh full games and the real 8840U. No new
HF jobs, gradients, candidate, publication or reserved final seeds this checkpoint.
Selective auction search remains promising; unchanged resource/building search
should not be scaled. No general plateau is established.

**Previous — 25 October, 05:42 UTC: complete cost evidence and paired HF job runner.**

The full reference/mixture runtime calibration is complete: **24 original jobs /
768 continuations / zero caps**, all independently verified and all terminal
credits recomputed. Private archive: HF `e81e65d011c6d9017f49410034025e66cfc765be`, SHA256
`1fe448c5ba27ea2338f5631a2b4318ecb0deb30f21acd16bbaf6fcca7d2ec4ac` (**394 files**). Original index/archive session **36341**
completed; do not repeat it. Descriptors: `strong/surrogate-continuation-cost-results-v1.json`
and `strong/surrogate-continuation-cost-complete-evidence-v1.json`.

Actual reference search: **110.92 s median**, **2,314.70 s maximum** (6p Recharged/open
bid), **29,143.79 CPU seconds total**, **2.899 GB maximum sampled summed RSS**.
Existing mixture: **3.29 s median**, **14.25 s maximum**, **259.63 CPU seconds total**,
**1.006 GB maximum RSS**. These measure diagnostic continuations on HF CPU-upgrade,
not 8840U bot decisions. Physical nested work is **2,162,384 evaluations**, comprising
2,161,104 forward and 1,280 shared prior-bid evaluations. The unchanged raw action
receipts attribute those shared priors twice (2,163,664); both counters are retained.
No full-study admission is implied; the actual selected surrogate still needs timing.

`strong/surrogate_continuation_job_v1.py` now executes all three modes for one frozen
root: **8 worlds × 2 actions × 3 modes = 48 continuations**, sequential modes with
eight workers. The HF entry requires the full frozen 160-game corpus, fixed task
grid, selected learned policy/member hashes, source manifest and environment pins.
It records time, CPU, RSS and physical search work; independently verifies every
saved chunk; preserves action/world/role pairing; and continues the other modes
when one has a simulation cap. Capped comparisons retain all records with no
margin. Exceptions retain partial artifacts, and existing outputs are never rerun.
Post-execution source failures are marked failed before the evidence upload.

**Seven tests pass**: complete envelopes using actual saved records, capped and
failed execution retention, no retries, resealed bad terminal rejection, shared
prior accounting across all collected reference receipts, input/scope/model gates.
A local real-engine execution through the new wrapper completed **48 continuations,
zero caps**, exactly reproducing all 48 saved records across worker partitions.
It used a separate **runtime root and explicitly untrained fixture**; no fresh
scientific root or gradient update was used. All **1,463** base-runtime files remain
unchanged. Original local session **96109** completed; do not rerun it.
Preflight: `ai/runs/surrogate-continuation-job-preflight-proof-v1.json`, SHA256
`55e94a35f33e2f916c4de81568556736c6cca6d796d9dafffc9127b189eb2f36`. Integration outputs: `ai/runs/surrogate-continuation-job-preflight-v1`.

Original data collection remains **32/40 verified**. The inspected 6p original job
`6add73271e112550ce7e6a20` is directly RUNNING at **78/96 games**, no errors.
Training coordinator **PID 2825298 / session 39111** is alive, waiting for complete
collection; it still owns all subsequent preparation/calibration/training/selection
stages. Its code and the original data coordinator's pinned code are unchanged.
No new HF jobs this checkpoint. Checkpoint:
`ai/runs/surrogate-continuation-job-checkpoint-v1.json`, SHA256
`9c3050d0e1ae3f1477a060b719f79d96b1c4b4cb985046bcb1660dda9ca58230`.

Next: let the original data/training coordinators advance. Build the full study
source packager (not yet implemented) from all 1,463 unchanged base files plus
study/analysis/job modules, the actual prepared frozen roots/policy and selected
ONNX members. It must verify the actual trained validation selection, execute an
isolated layout check on all 480 public roots, and preserve upload intent/receipt.
Measure the actual selected surrogate on separate runtime roots; use that plus the
completed reference cost evidence for job sizing/timeouts. Implement the measured
launcher/collector and run the full paired study only after both inputs are frozen.
The job runner and aggregate analysis are now available; no full-study jobs have
been admitted or submitted. A heterogeneous hybrid, fresh full-game strength,
selected-policy final adapter and actual 8840U hybrid benchmark remain required.
No candidate, qualification, publication, final-seed use or general plateau claim.

**Previous — 25 October, 05:28 UTC: fresh roots archived; training coordinator running.**

All five original fresh-root jobs completed. Their original coordinator
**PID 2536982 / session 93486** reached `collection_complete` at **05:19:21 UTC**
and exited normally; do not restart it. The frozen manifest has **160 games /
480 roots / all 60 count-rule-phase groups / 8,813 eligible decisions**, no missing
phases or game/search caps. Every game contributes each phase. Manifest SHA256
`d5f865cd63836dad11f3aeff216b6b8910e389ff8d85fce34206a358fe0fc3b1`.

The new `collect-surrogate-continuation-roots-evidence-v1.py` reproduces the full
manifest from the original verified receipts, checks its coverage with the paired
analysis, and independently recomputes all **720 terminal player credits** after
root selection is frozen. The complete **876-file** evidence archive is privately
verified at HF revision `8d62c24b75a76b8424e2fd4d231c407f5dfb51ce`, archive SHA256
`fcaaf681be3a03fc825e80476492656a1bd0b3569b9e065e092048a6f03ced61`. Descriptor:
`strong/surrogate-continuation-roots-complete-evidence-v1.json`. Original archive
session **15481** completed; never re-upload it. The index is
`strong/surrogate-continuation-roots-results-v1.json`; frozen inputs are under
`ai/runs/surrogate-continuation-roots-frozen-v1`.

The training coordinator is implemented and running: **PID 2825298 / session
39111**, `ai/strong/coordinate-opponent-surrogate-training-v1.py --execute
--interval-seconds 180 --max-hours 48`. It pins **30 source files**, waits for the
complete 40-shard collection, then owns data preparation, private data/source
packaging, exactly one L4 calibration, measured full four-seed training, independent
artifact verification, and validation-only selection. Existing launcher memory,
time, export and complete-data checks remain authoritative. It never retries a
failed/uncertain action, replaces a job after an observation timeout, runs local
gradients, opens held-out labels for selection, or launches fidelity/strength jobs.
It finishes normally even if the economic prior wins validation, preserving that
negative result and leaving the test split closed.

**Ten orchestration tests pass**, covering complete-data gating, exact action order,
original job reuse, observation errors, failed jobs, uncertain submissions/uploads,
changed source/evidence, competing owners, read-only dry run and prior-winning
selection. These tests submit no HF jobs. Preflight:
`ai/runs/opponent-surrogate-training-coordinator-preflight-v1.json`, SHA256
`3efc2cbd06b0d83341ba3d63b221f2f33754996c1c3baaaf19e572066644c9d9`. State/log:
`ai/runs/opponent-surrogate-training-coordinator-v1/state.json` and
`ai/runs/opponent-surrogate-training-coordinator-v1.log`.
**If the user asks to pause or stop new jobs, stop this local coordinator first:**
it is authorized to launch the two GPU stages once their prerequisites pass.
Do not start a second coordinator or run its stages concurrently by hand.

At the checkpoint it is alive, waiting for complete collection, with no GPU jobs
launched. The original collection coordinator remains alive at **32/40 verified**;
original job `6add73271e112550ce7e6a20` is directly RUNNING at **65/96 games**, no
errors. Cost calibration advanced to **22/24 verified / 704 continuations / zero
caps**. Only original `6add8b4f046eb82b1ece257f` and
`6add8b601e112550ce7e74df` remain; both directly RUNNING. No replacements or new HF
jobs at this checkpoint. Checkpoint:
`ai/runs/opponent-surrogate-training-coordinator-checkpoint-v1.json`, SHA256
`aa31a9a0e606eacefa83b3d231c1c04054126622f037ea4625063d8ca139335a`.

Next: collect those two original cost jobs, index and archive the full calibration.
Let the original data and training coordinators advance; inspect their original
handles rather than duplicating stages. After the learned selection is frozen,
prepare the fixed full-study inputs, measure surrogate runtime, and package/launch
and collect the paired fidelity study using the implemented analysis. A verified
heterogeneous hybrid, fresh full-game strength, selected-policy final adapter and
actual 8840U hybrid timings remain required. No candidate, qualification,
publication, final-seed use or general plateau claim.

**Previous — 25 October, 05:17 UTC: paired fidelity analysis verified.**

The full paired fidelity analysis is implemented in
`strong/surrogate_continuation_analysis_v1.py`, with the fixed details in
`strong/surrogate-continuation-analysis-design-v1.json`. It recomputes exact margins
from every world/action credit, averages all **60 count/rule/phase groups equally**,
retains adverse cells and three-way preference ties, and reports action-credit
error plus separate with/without-prior-bid summaries. No policy is selected.

The existing population mixture rotates four opponent-role assignments by world
index modulo four. Within-root uncertainty preserves the fixed strata **[0,4],
[1,5], [2,6], [3,7]** and uses identical resamples for both actions and all modes:
**81 exact multiplicity patterns**. Whole-deal uncertainty keeps all seats, rules
and phases together, stratifies by player count, and enumerates **243 patterns**.
If a positive-probability replicate lacks a group, its mass is reported and the
interval is withheld rather than dropping or reweighting that replicate. Any
simulation cap retains all records but suppresses aggregate fidelity estimates.
Two deals/count and two worlds/role stratum provide limited uncertainty evidence.

**Eight tests pass**: equal-group weighting, hand-calculated binomial interval,
missing-deal group probability 1/4, role-stratum and mode/action pairing, exact tie
credits and metric definitions, cap retention, omitted/duplicated/altered inputs,
and all **96 saved real-engine preflight continuations**. Those preflight records
use an explicitly **untrained fixture**, so this is engineering verification only.
No simulations or gradients were rerun; all 1,463 frozen runtime files are unchanged.
Preflight: `ai/runs/surrogate-continuation-analysis-preflight-v1.json`, SHA256
`203f955bc62050efbc8c42c53a4dbc5763926b1a99a30dfeab6414fa90eb6077`.

Original jobs remain in progress: opponent-data **32/40 verified**, fresh-root
**4/5**, continuation-cost **20/24 (640 continuations, zero caps)**.
The four remaining cost handles were directly RUNNING. Earlier direct observations
showed opponent job `6add73271e112550ce7e6a20` at 50/96 games and fresh-root job
`6add8752046eb82b1ece239e` at 40/48, no errors. Both original coordinators remain
responsible for their collections; their pinned code is unchanged. No new jobs.
Checkpoint: `ai/runs/surrogate-continuation-analysis-checkpoint-v1.json`, SHA256
`8b88279c1f23fff76e72ebd4f1cfb0188da6bed58794f8defe99b6a935a3b3ad`.

Next: finish the original cost collection/index and archive; finish original
training-data and fresh-root collection; run the prepared HF GPU calibration,
training, independent audit and validation-only selection. Then freeze study
inputs and implement the measured HF study packaging/launch/collection, using
`paired_record` plus `analyze` for the complete report. The real learned-surrogate
fidelity result, heterogeneous hybrid policy, fresh full-game strength, exact final
adapter and actual 8840U hybrid benchmark remain outstanding. No candidate,
qualification, final-seed use or general plateau claim.

**Previous — 25 October, 05:09 UTC: hybrid research checkpoint.**

The continuation-cost collector now verifies **20/24 original jobs, 640 continuations,
zero caps**. The four remaining original 6p jobs were directly RUNNING; no jobs
were replaced or submitted. Opponent training-data collection remains **29/40**
and fresh-root collection **4/5**, with both original coordinators alive.

The complete-cost archive helper is implemented and **three tests pass**, including
independent exact terminal tie credit, actual saved reference receipts and refusal
to archive a partial experiment. Its independent search-work accounting deduplicates
prior sealed-bid searches: each worker/world computes them once but both action
receipts contain their counters. Preserve the original row-attributed counters and
raw receipts; use separately named physical-work counts. No complete cost archive
or full-study admission exists yet. The paired aggregate fidelity analysis is also
still pending; no trained opponent surrogate or fresh hybrid strength claim exists.

Next: collect the four original cost handles and create the full index, then run
`ai/.venv/bin/python ai/strong/collect-surrogate-continuation-cost-evidence-v1.py --archive`
once. Finish original data/root collection, run the prepared HF training pipeline,
and freeze its validation-selected policy before the continuation-fidelity study.
The recommendation remains a selective auction hybrid with improved opponent
simulation and conservative overrides; unchanged building/resource search is not
worth scaling. No general plateau is established.

Checkpoint: `ai/runs/surrogate-continuation-cost-evidence-checkpoint-v1.json`, SHA256
`c69d22ec7d35c19f26712f752e846acaf2bb5bdadc2eb6bf01f2d60c2117ff5e`. No new jobs or gradient updates in this checkpoint.

**Previous — 25 October, 04:56 UTC: resource search rejected; reference-cost calibration running.**

The original resource watcher completed normally at **04:47:44 UTC**. All **54 jobs /
3,360 games** are independently audited and privately archived: the full comparison
reproduces, all terminal tie credits were recomputed, and the paired aggregate /
bootstrap were reconstructed. Zero game or rollout caps. Archive: private HF
`637202d691efc8121f95b7ff3954d4f20bfa54dd`, SHA256
`e6e93cf4bf858f9afada6576654aaf021c2d455e50471319488de2d1c3831cc3` (**7,290 files**).
Original watcher PID 2444260 / session 56315 is complete; do not restart or re-upload.

**Decision: do not adopt, distill or scale the unchanged resource-search policy.**
Its primary equal-count difference against search is **−9.1875 pp**, exploratory
whole-deal 95% interval **[−16.3648, −1.5518] pp**. Point estimates regress at all
five counts. Economic secondary: **+6.25 pp [−0.42, +12.29]**, with important
2p improvements but other regressions. Only four independent deals per cell; no
post-hoc routing is selected. All **16 adverse overall cells and 41 adverse rule
cells** are retained. The arm used **5,151,608 continuations / 69,624 search decisions**,
changing **17,637** baseline choices. Shared-HF search median/p95 **13.13/54.51 s**
are not 8840U serving timings. Read [the complete assessment](RESOURCE-SEARCH-SCREEN-2026-10-25.md)
and `strong/resource-replanning-development-review-v1.json`. This rejects this
implementation; it is not a general plateau or an optimal-action training set.

The separate **reference-continuation runtime calibration** is implemented and
launched. It uses the already audited runtime-prefix source games, never the fresh
scientific roots. Select the minimum existing rank across seats in each **2p/6p ×
four rules × plant/bid/building** group: **24 roots**, without reading terminal
outcomes for selection. Each root runs the fixed action pair on **eight worlds**
under actual reference search and the original population mixture: **24 CPU jobs /
768 continuations**. No learned or untrained surrogate participates in this cost
calibration, and no gradients run. Actual surrogate timing still needs its own
check once the trained policy is frozen.

New code: `surrogate_continuation_runtime_v1.py`,
`build-surrogate-continuation-runtime-source-v1.py`,
`launch-surrogate-continuation-cost-v1.py`,
`manage-surrogate-continuation-cost-v1.py`, and
`test_surrogate_continuation_runtime_v1.py`. **Nine tests pass**: actual 24-group
selection and ordering, missing/resealed ranks, no terminal parsing for selection,
invalid scopes/private-root hashes/changed-source boundaries, resource allowance,
independent audit of 32 packaged-engine outcomes, resealed bad terminal rejection,
and existing/unknown submission guards. No live job was resubmitted.

The clean source contains **1,477 files**, preserving all **1,463 base files**.
It imports its own package, independently rechecks all 24 focal pairs, and passed
a complete local **32-continuation / zero-cap** job through the exact packaged
wrapper and collector. This is engineering verification, not a timing guarantee.
Source dataset revision **`954e14c072a297dca7a101eb8264c78176f6ae3d`**,
archive SHA256 **`45e4fcf26983ef39baf1f1a97a569282ba7a47c15711d602031673e45cf27253`**.
Descriptor: `strong/surrogate-continuation-cost-source-v1.json`.
Preflight: `ai/runs/surrogate-continuation-cost-preflight-v1.json`, SHA256
`a4f9e168d95fafd160d9a8d019b12107f8c1ef2a8f0d09d78db1ae16bab913f9`.

The bounded calibration allowance is **CPU-upgrade / eight workers / six-hour
maximum per root**, derived conservatively from the previous complete nested-search
measurement, including extra setup/time/memory reserve. It is not admission of the
full scientific experiment. The fixed 768-continuation workload is unchanged.
All 24 launch dry-runs passed. The sole submitter **PID 2635183 / session 41430**
completed all 24 submissions; do not rerun it. The original upload session **37797**
also completed and is remotely verified. Guards:
`ai/runs/surrogate-continuation-cost-launches-v1/*.json`.
Plan: `strong/surrogate-continuation-cost-admission-v1.json`.

At **04:56 UTC**, direct HF inspection showed **13 completed / 11 running**, no
failed original handles. The first collection cycle **session 79023** completed:
**8 jobs / 256 continuations independently verified**, zero caps, immutable raw
archives retained. Some actual positions require no further strategic search;
retain those alongside difficult positions without outcome-based replacement.
Checkpoint: `ai/runs/surrogate-continuation-cost-checkpoint-v1.json`, SHA256
`11f19ecc6bdf0aa76ffd38a8bf736ec3eb9de9ab34a821dee080b68c641cdc2f`.

Next cost collection command: `ai/.venv/bin/python ai/strong/manage-surrogate-continuation-cost-v1.py collect-ready`, then `index`
only when all 24 original cases verify. There is no cost-collection coordinator;
use the original guards. The complete calibration archive/admission for the full
study still needs implementation after all measurements arrive. No full-study
continuations or frozen trained-surrogate policy exist yet.

The other original work remains live with unchanged code: opponent-data collection
**40 submitted / 29 verified**; full fresh-root collection **5 submitted / 4 verified**.
Their original representative 6p handles were directly RUNNING. At 04:53:14 UTC,
opponent job `6add73271e112550ce7e6a20` had **37/96 games**, no errors. Keep PID
2009367 / session 80214 and PID 2536982 / session 93486; do not replace slow games.

**Next:** finish original cost and full-root collection; finish opponent collection,
then the prepared HF GPU calibration/training/audit/validation-selection pipeline.
Freeze both inputs before the full fidelity study, implement its measured launch
and aggregate paired analysis, and keep heterogeneous auction policy/fresh full-game
strength separate. The exact final adapter and actual 8840U hybrid benchmark remain
required. No candidate, publication, final-seed use or general plateau conclusion.

**Previous — 25 October, 04:39 UTC: paired continuation runner verified; full fresh-root jobs running.**

The fixed-action continuation runner, independent saved-result checks and full-study
input gate are implemented. They re-encode each public root and rerun the frozen
focal model, bind the loaded opponent policy to its saved descriptor, retain exact
rational tie credits, and require all eight sampled worlds / two actions / three
modes. Missing, duplicated or mismatched worlds are rejected. Capped simulations
remain in the record without an aggregate margin. No action selection occurs.
The input gate requires the complete 160-game root manifest and independently
audited, validation-selected learned surrogate before creating study inputs.

**Eight tests pass**, including all 24 actual 2p calibration roots, altered private
inputs/action pairs/ranks, missing/duplicated worlds and changed sealed-bid beliefs,
terminal credit/counter checks, explicit outer/nested caps, resealed bad receipts,
wrong loaded policy and premature full-study refusal. A real-engine preflight on
two separate runtime roots (one with prior sealed bids, one without) completed
**96 continuations, zero caps**, across actual reference search, the existing
mixture and an explicitly **untrained** surrogate. Sample partitions and cross-mode
worlds match; all 1,463 frozen runtime files remain unchanged. Saved reports were
independently rechecked, normalizing JSON object keys when comparing saved worlds.
The first successful 96-continuation run is preserved under the `initial-v1`
directory with its source; the final run adds loaded-policy digest binding. These
are engineering executions, not trained-model fidelity or fresh strength results.

Preflight proof: `ai/runs/surrogate-continuation-study-preflight-proof-v1.json`,
SHA256 `9195c10c9f75b21309800e35b48b7db7ab03d8a6bc4a793444206fccf63fdf13`.
Checkpoint: `ai/runs/surrogate-continuation-study-checkpoint-v1.json`, SHA256
`9522f9f03077badcb86177c90caaddd69f4e00932cb1b89485b1b9d4346d920d`.
Original final preflight session **10581** completed successfully; do not restart it.

The original 6p root calibration `6add7f8b1e112550ce7e6eff` completed and passed
independent verification: **24 games / 24 exact twins / 72 roots / 1,317 eligible
decisions**, zero caps or missing phases; 1,794.50 s wall, 12,079.90 CPU seconds,
6.30 GB sampled summed RSS. Both endpoints are now jointly audited and archived:
**32 games / 64 executions / 96 roots / 1,792 eligible decisions**. Private HF
revision `8324de32af3df755e38793b803bdd3c7ae92e4e3`, archive SHA256
`5417904d1cf5ac07125f75dd67df6ea1f67dd1c97e90469f0d1d0a74e4de9333`
(221 files). Original archive session **84131** completed; do not repeat it.
Descriptor: `strong/surrogate-continuation-roots-calibration-evidence-v1.json`.

Measured admission selected **five CPU-upgrade jobs, eight workers each, three-hour
timeouts**, preserving both whole deals at every count: 160 games / up to 480 roots.
All five launch dry runs and coordinator dry run pass. The initial inline dry-run
invocation omitted the Python module path; its log is preserved, the invocation
was corrected, and no submission occurred before the corrected checks passed.
Original full-root coordinator: **PID 2536982 / session 93486**, launched 04:36 UTC.
All five original handles were directly RUNNING at the checkpoint:

| Players | Original HF job |
|---|---|
| 2 | `6add87561e112550ce7e7267` |
| 3 | `6add8754046eb82b1ece23a5` |
| 4 | `6add8753046eb82b1ece23a2` |
| 5 | `6add8752046eb82b1ece23a0` |
| 6 | `6add8752046eb82b1ece239e` |

Plan: `strong/surrogate-continuation-roots-plan-v1.json`. Guards:
`ai/runs/surrogate-continuation-roots-launches-v1`. Coordinator state:
`ai/runs/surrogate-continuation-roots-coordinator-v1/state.json`; log:
`ai/runs/surrogate-continuation-roots-coordinator-v1.log`. Preserve source pins and
original handles. The coordinator collects all shards and freezes the manifest;
no full-study continuation jobs have been admitted or launched.

At the checkpoint, opponent-data collection remained **40 submitted / 29 verified**,
no failures. The original resource coordinator completed **54/54** and wrote its
full **3,360-game** comparison at 04:37:55 UTC, then exited normally. Its original
archive watcher **PID 2444260 / session 56315** still owns independent reproduction,
terminal-credit audit and archival. Inspect that watcher; do not start another
collector or restart the completed resource coordinator. The comparison currently
shows a **−9.1875 percentage-point** resource-search difference against search,
equal-weighted across counts (four-deal bootstrap interval **−16.3648 to −1.5518 pp**).
This is the complete comparator result; its separate audit/archive is still pending
at the checkpoint. Do not call it independently archived until the descriptor exists.

**Next:** collect/freeze the original full-root jobs; finish the original opponent
collection, train on HF, independently audit and freeze validation-only selection.
Then `prepare-surrogate-continuation-study-v1.py` can freeze study inputs. Still
implement measured HF nested-reference continuation calibration, study packaging /
launch / full audit and aggregate paired analysis. A heterogeneous hybrid with
cautious overrides, fresh full-game strength, exact selected-policy adapter and
actual 8840U hybrid benchmark remain separate required steps. No gradient updates
ran this turn. No candidate, publication, final-seed use or general plateau claim.

**Previous — 25 October, 04:22 UTC: full root-collection controls verified; resource archive watcher live.**

The previous turn pushed `8eaa45b`, started both root-calibration jobs and
independently verified the 2p endpoint. This turn implemented the complete fresh-root
collection controls: generalized shard verification, joint calibration archival,
measured admission, original-handle launch/collection, all-shard root freezing and
a coordinator. No new HF jobs or gradients ran.

The fixed design stays **160 games / up to 480 roots / all 60 count-rule-phase
groups**. Measured endpoint time/memory/storage chooses one or two whole deals per
shard (10 or 5 jobs); it never reduces coverage or search depth. The root manifest
and its fixed action pairs are frozen only after every original shard verifies.
The manifest builder reads no terminal outcomes or surrogate scores. Missing
count/rule/phase coverage prevents freezing; missing phases within individual
games remain explicitly recorded. Interrupted final index writes recover the same
already-written manifest and provenance, without selecting a different corpus.

**Nine tests pass:** the new verifier reproduces the original independent audit of
8 real HF calibration games / 24 roots; resealed incomplete shards and private-root
injection are rejected; whole-grid coverage and resource admission; a synthetic
160-game / 480-root / 60-group freeze and interrupted-index recovery; changed
provenance or selected ranks; missing phase coverage; and coordinator capacity,
existing-handle and failure boundaries. The synthetic grid is a format fixture,
not real source games. The initial interrupted-index test used a temporary path
outside the repository; it now uses `ai/runs`, matching the production relative-path
contract. Its original failed log is retained. Actual premature joint archival
and full admission both refused before output creation.

Preflight: `ai/runs/surrogate-continuation-root-collection-preflight-v1.json`, SHA256
`5c82ed749c74ec7f11414feac0693500eda37b382fe1fc0e3857926e8369a43e`.
Checkpoint: `ai/runs/surrogate-continuation-root-collection-checkpoint-v1.json`, SHA256
`e0797dad5ce7ed4eea988640e7fde4ea8f8708090c00c54e4fba8516a4be2351`.
No full-root plan, collection/index or reference-continuation jobs exist yet.

At **04:19:08 UTC**, original handles were directly RUNNING: 6p root calibration
`6add7f8b1e112550ce7e6eff` **9/24 games**; representative 6p opponent-data shard
`6add73271e112550ce7e6a20` **18/96**; final resource/search shard
`6add573a046eb82b1ece167a` **87/96**, zero reported caps. At **04:22:09 UTC**,
the original coordinators were live with unchanged code: opponent-data collection
**40 submitted / 28 verified**, resource screen **54 / 53 verified**, no failures.

A single complete-resource archive watcher is now live: **PID 2444260 / session
56315**, `coordinate-resource-complete-archive-v1.py`. It watches original
coordinator PID 1291091, waits for all 54 batches and `comparison_complete`, then
runs the existing full independent auditor and private HF archive exactly once.
It checks source hashes and never retries or replaces jobs/uploads. Its observation
window is six hours, with no remote cancellations. **Do not manually start a second
resource archive while this watcher is active.** Inspect its original handle first.
State/logs: `ai/runs/resource-complete-archive-watcher-v1/{state.json,collector.log}`
and `ai/runs/resource-complete-archive-watcher-v1.log`.
Launch proof: `ai/runs/resource-complete-archive-watcher-launched-v1.json`, SHA256
`04b64aeac106dcf9268e4fc3bebbe1072f76d34989bed9b89f2619b76814364f`.
The final collector log is created only when the complete audit starts. Preserve
this watcher and all of its pinned resource source files unchanged.

**Next:** collect the original 6p root-calibration handle. Once both endpoints pass,
run `collect-surrogate-continuation-roots-calibration-v1.py --archive`, then
`launch-surrogate-continuation-roots-v1.py prepare`, launch dry-runs and
`coordinate-surrogate-continuation-roots-v1.py --execute --interval-seconds 180
--max-hours 48`. Joint calibration, actual full-mode HF execution and final root
freezing remain untested with real full-study data. The resource watcher owns its
full audit/archive; inspect and interpret that result when ready. Finish the
original opponent-data collection and its GPU training/audit/frozen-selection
pipeline. Still implement/admit fresh paired reference-versus-surrogate evaluation,
heterogeneous hybrid policy, fresh full-game strength, exact final adapter and
actual 8840U hybrid validation. No candidate, publication or plateau conclusion.

**Previous — 25 October, 04:07 UTC: fresh-root capture verified; HF calibration launched.**

The previous turn completed and pushed continuation integration as `d47de74`.
This turn fixed the fresh diagnostic design and implemented outcome-independent
focal-root capture, independent root checks, isolated HF packaging, bounded
calibration launch and original-handle collection. The full root collection and
continuation experiment are not launched or admitted yet.

`strong/surrogate-continuation-protocol-v1.json` fixes **160 fresh source games**:
Germany 2–6 players, two whole deals per count, all seats and all four rules.
The frozen filtered focal model plays actual search_geo16 opponents. Each game
retains at most one plant-choice, bid and building decision by a deterministic
hash of its identity/decision ordinal. Neither outcomes nor surrogate predictions
choose roots. The fixed action pair is the filtered focal move and the highest
existing economic-prior alternative in the safe public shortlist. Missing phases
are reported, never replaced using outcomes. The maximum is 480 roots.

After root/source and trained-surrogate selection are frozen, the specified
comparison uses **eight shared sampled worlds and two fixed actions per root**
under actual reference search, the learned surrogate, and the existing population
mixture. This is up to 7,680 continuations per mode. Primary diagnostic: error in
the alternative-minus-focal margin relative to reference search, preserving every
count/rule/phase group and clustering by whole count/deal. Two independent deals
per count provide limited uncertainty support. Prior sealed-bid beliefs and future
play change jointly; roots without prior bids are reported separately. These are
not calibrated win probabilities, optimal-action labels or strength qualification.
Reference-continuation cost still needs its own measured runtime admission.

**Five root-sampling tests and four job-boundary tests pass.** Public roots cover
all 60 count/rule/phase contexts. Submission timeouts do not cause resubmission.
Complete local 2p/6p Recharged-sealed endpoint games matched exact unobserved twins:
**2 games / 4 executions, 93 eligible decisions, 6 roots, zero caps**. Independent
root checks and a resealed duplicate rejection pass. All 1,463 frozen engine files
remain unchanged; a clean package reproduces 20 focal decisions exactly. The first
unit run correctly rejected raw private canonical fixture states; the test now
applies the same public boundary as the arena, and its initial log is retained.
Original endpoint preflight session **91118** exited successfully.

The immutable **1,469-file** HF source is remotely verified at dataset revision
`c39d101a6c7c3ecec7065752bf61e1b22cc31b63`, archive SHA256
`9a6c10ebfaa80def4033d15854b289f408a1ea0051e979f77b982decf42fc4c4`.
Descriptor: `strong/surrogate-continuation-roots-source-v1.json`.
Two bounded **CPU-upgrade / 8-worker / 4-hour** calibration jobs were submitted:

- **2p `6add7f861e112550ce7e6ef5` — COMPLETED and independently verified:**
  8 games / 16 executions, 475 eligible decisions, 24 roots, zero caps/missing
  phases. 115.69 s wall / 794.44 s CPU / 5.41 GB sampled summed RSS. Raw 45-file
  archive: private HF revision `541327b97fcec55968556c85ace13f9e5cd40df6`, SHA256
  `5096921f7e21944b93bca34043c906314bb61b35bf2a8fefbde6031a76618cbe`.
- **6p `6add7f8b1e112550ce7e6eff` — directly RUNNING** at 04:07:06 UTC.
  Keep this original handle; do not replace it on an observation timeout.

Collect with `ai/.venv/bin/python ai/strong/collect-surrogate-continuation-roots-runtime-v1.py 6`.
Guards: `ai/runs/surrogate-continuation-roots-runtime-launches-v1`.
Collected artifacts: `ai/runs/surrogate-continuation-roots-runtime-collected-v1`.
Admission: `strong/surrogate-continuation-roots-runtime-admission-v1.json`.
Checkpoint: `ai/runs/surrogate-continuation-roots-checkpoint-v1.json`, SHA256
`72c8ff8e90d821e2d21c76682b2f35ea76c31eff8df86a9acf92d61ac38077c4`.

At that checkpoint, both original coordinators were live with unchanged code:
opponent-data collection **40 submitted / 24 verified**; resource screen **54 /
53 verified**, no failures. No gradients ran this turn. Actual surrogate training,
model selection and held-out behaviour evaluation remain pending collection.

**Next:** finish and independently archive the full resource comparison; finish
opponent collection and run its already implemented HF GPU training/audit/selection
pipeline. Collect the original 6p root calibration, archive both endpoints and
implement/admit full root collection from measured costs. Freeze its complete root
manifest before evaluating the learned surrogate; benchmark nested reference
continuations before scaling that comparison. Heterogeneous hybrid integration,
fresh full-game strength, the selected-policy final adapter and actual 8840U hybrid
validation remain required. No candidate, publication or general plateau claim.

**Previous — 25 October, 03:48 UTC: surrogate continuation integration verified.**

The separate surrogate continuation worker and Python/ONNX probe are now
implemented and verified. Historical population and reference-search workers
remain unchanged. The new diagnostic mode uses the frozen focal model and asks
the opponent model only for public shortlisted strategic choices; other opponent
moves retain the reference economic policy. It preserves the reference RNG draw
at each replaced search decision and validates actions before changing any world.
This mode compares all-reference and all-surrogate opponents; it is not yet the
heterogeneous serving mixture or a selected action policy.

**Five worker tests pass:** all 80 population control contexts remain exact; 60
strategic contexts emit 1,244 public queries unchanged by valid hidden-state
mutations; intentional caps and invalid shortlist actions are checked. Supplying
actual reference choices reproduces states and subsequent RNG draws on five
roots covering 2–6 players (11 nested search calls, three prior bids). Partitioning
and malformed-input handling also pass. Initial test failures are preserved:
legacy wall-clock metadata required a fixed test clock, and the private automation
fixture needed its required `plans` field. No production runtime was changed.

The full Python/ONNX preflight completed **40 continuations over all 20 count/rule
combinations**, with **4,399 focal and 5,205 surrogate inference decisions**, zero
caps. One- versus two-worker output is exact, including a separate eight-world/action
intentional-cap check. All **1,463 frozen runtime files** and pinned dependencies
remain unchanged. The surrogate weights were explicitly random and untrained:
this establishes integration only, not imitation fidelity or stronger play.
Original preflight session **62222** exited successfully and must not be restarted.

Preflight: `ai/runs/surrogate-opponent-integration-preflight-v1.json`, SHA256
`b6810d3981dd9f87da45a8bd140c0a6ee862d8cdfacdf032517d71e60b421b2a`.
Complete local output: `ai/runs/surrogate-opponent-integration-v1`.
Checkpoint: `ai/runs/surrogate-opponent-integration-checkpoint-v1.json`.
At **03:47:55 UTC**, both original coordinators were alive with unchanged code:
collection **40 submitted / 20 verified**, resource screen **54 / 49 verified**,
no reported failures. The original six-player collection and resource/search
handles were directly RUNNING. No new HF jobs or gradients ran in this turn.

**Next:** preserve the original jobs. Finish and independently archive the complete
resource comparison. Finish collection, prepare/package train+validation, run the
measured HF GPU calibration and full four-seed training, then audit/freeze/evaluate
the selected opponent model. The new continuation probe enables, but does not yet
implement, a fresh paired reference-versus-surrogate experiment; specify its roots
without selecting on outcomes and measure runtime before scaling exact nested
search. Heterogeneous hybrid integration, fresh full-game strength, the exact
selected-policy final adapter and actual 8840U hybrid validation remain required.
No candidate, publication, final-seed use or general plateau conclusion.

**Previous — 25 October, 03:26 UTC: frozen selection and held-out evaluation pipeline implemented.**

Previous turn pushed `ba8feed` and started the original full collection. This turn
implemented public-feature surrogate inference, validation-only policy selection,
and separately gated held-out preparation/evaluation. No new jobs or gradients ran.

`strong/opponent-surrogate-selection-design-v1.json` now fixes the comparison:
the economic prior, each of four verified best checkpoints, and their equal-weight
probability ensemble. Select minimum validation macro-NLL over all 60 count/rule/
phase groups; numerical ties within 1e-10 retain fixed order, prior first. No
fitted temperatures, weights or rule routing. If the prior wins, report no learned
validation improvement and keep model test evaluation closed. Selection is not
adoption into search and its validation metrics are not unbiased generalization.

`opponent_surrogate_policy_v1.py` verifies model/checkpoint pins, uses only public
state/action/mask inputs, and returns legal shortlisted indices. `select-opponent-surrogate-v1.py` requires independently audited training, recomputes validation
metrics, preserves every candidate and freezes policy/data/source hashes. The
separate `evaluate-opponent-surrogate-heldout-v1.py prepare` command then checks
all 320 test games/deals 28..31 and writes test-only tensors. Its `evaluate` command
compares only the frozen choice and economic prior, with natural training-input
overlap reported separately without dropping primary test rows. Test labels may
already have been read for collection integrity, never for model selection.

**Ten tests pass:** four random, untrained singleton models plus their ensemble
match checkpoint/probability choices on **382 real calibration positions** (1,910
policy-choice checks); masking, provenance and private metadata boundaries; selection
and changed-freeze rejection; and a synthetic complete 320-game/960-row test bundle.
No real trained selection/test evaluation or complete raw held-out preparation has
run. Actual premature selection and test preparation both refused before creating
outputs. Preflight: `ai/runs/opponent-surrogate-selection-preflight-v1.json`, SHA256
`ee537ccfca3741327b2ac901650993c2d6ffdecc676ddafca5906701a0b02a2a`.

At **03:25:53 UTC**, both original coordinators and representative HF handles were
live. Collection: **32/40 submitted, 0 verified**, PID **2009367 / session 80214**.
Its original six-player job `6add73271e112550ce7e6a20` showed 63%, 59%, 58% CPU in
three noninitial live samples, about 4.73 GB RAM. Resource screen: **54 submitted /
45 verified**, PID **1291091 / session 11670**; original 6p/search resource job
`6add573a046eb82b1ece167a` advanced to 58/96 games, zero reported caps. No failed
jobs in either coordinator. Frozen source/code hashes match. Checkpoint:
`ai/runs/opponent-surrogate-selection-checkpoint-v1.json`.

**Next:** preserve the original jobs/coordinators. Finish and independently archive
the complete resource comparison when ready. Finish collection, prepare/package
train+validation, run and collect measured HF GPU calibration/full training, then
run the trained-result auditor and new selection/test commands. Still implement
and verify the surrogate's continuation-worker integration and fresh paired
continuation evaluation; good imitation does not prove stronger search. Full fresh
strength, the exact selected-policy final adapter and actual 8840U hybrid validation
remain required. No candidate selection, production publication or plateau claim.

**Previous — 25 October, 03:12 UTC: full opponent collection started; training-result audit implemented.**

Both original HF calibration jobs are now complete and independently verified:
**32 games / 64 paired executions, 5,826 teacher decisions, 474,704 teacher
continuations, 192 public replays on HF and 192 independent local replays, zero caps**.
These runtime-only games stay excluded from training and strength. The six-player
endpoint took 3,929.18 s wall / 26,466.66 s CPU, with 6.23 GB sampled summed RSS.
The complete 398-file calibration archive is remotely verified at private HF
revision `bc2206ce31f0015e1ad3737530e1f30dbbda1951`, archive SHA256
`eb29e0575984f6f23a0af16525bc0fcdb57d3e86a067a3ee1f533b9ccc412c29`.

The measured plan admits **40 CPU-upgrade jobs**, four whole deals per shard,
8 workers, a 12-hour timeout and at most 32 concurrent jobs. It fixes **2,560 fresh
games plus 640 twin replays**, Germany 2–6 players/all four rules/all seats, with
whole-deal training/validation/test splits. All 40 launch dry-runs and the coordinator
dry-run passed. The original coordinator is running: **session 80214 / PID 2009367**,
started **03:10:30 UTC**. At **03:11:57 UTC**, its first 21 original handles were
directly RUNNING; the initial batch was still being submitted. Inspect its original
process and guards, never restart on an observation timeout. No surrogate gradients
or trained models exist yet. The resource coordinator remains live, **54 submitted /
41 verified**, no failures at the same checkpoint; no partial strength comparison.

New `collect-opponent-surrogate-training-v1.py` and
`opponent_surrogate_training_verification_v1.py` independently audit all four seeds,
81 history entries, earliest best validation checkpoint, optimizer steps, stored
weights/provenance and exported predictions on every train/validation record. The
raw remote archive remains unchanged. Audit receipts survive an interrupted result
index write. **Eight tests pass**, including resealed false export metrics, incomplete
seed sets, incorrect optimizer steps and interruption recovery. Their full artifact
fixture uses synthetic histories and manually perturbed weights, with 242 forward
positions per seed; no gradients, HF training success or strength is inferred.
Actual trained-job integration remains pending. The trainer/package source was not
changed. Preflight: `ai/runs/opponent-surrogate-trained-audit-preflight-v1.json`.

Plan: `strong/opponent-surrogate-collection-plan-v1.json`.
Checkpoint: `ai/runs/opponent-surrogate-full-collection-checkpoint-v1.json`.
Live state: `ai/runs/opponent-surrogate-collection-coordinator-v1/state.json`.
Live log: `ai/runs/opponent-surrogate-collection-coordinator-v1.log`.

**Next:** let the original collection finish and verify/index every shard, then
prepare/immutably package train+validation only. Run the bounded L4 calibration,
collect its original handle, admit full four-seed training from measured costs,
and collect with the new trained-result auditor. Select the serving policy using
validation only; test held-out behaviour and fresh continuations against actual
reference search before fresh full-game comparisons. The selected-policy final
adapter and actual 8840U hybrid benchmark remain outstanding. No candidate or
plateau claim; final reserved seeds remain unused.

**Previous — 25 October, 02:56 UTC: HF packaging and measured training launch path implemented.**

The previous turn pushed the training pipeline in `bccc417`. This turn added a
minimal **14-file isolated Python runtime**, immutable train/validation packaging,
a bounded HF GPU benchmark, and original-handle calibration/full-training launch
and calibration collection. **Seven new tests pass**; all nine earlier core tests'
source hashes remain unchanged. No new HF jobs, archives/uploads or gradients ran.
The persistent package in `ai/runs/opponent-surrogate-training-code-v1` is code-only.

HF currently lists L4×1 as **8 vCPU / 30 GB RAM / 24 GB VRAM / 400 GB disk**.
After complete data packaging, the first L4 job has a two-hour calibration limit:
16 warmup + 128 measured gradient updates, full train/validation forward timings,
and exact export checks. Its checkpoint is explicitly runtime-only. Full training
requires that original job's verified evidence, independently recomputes the fixed
four-seed/80-epoch cost, and applies time/memory reserves. It refuses insufficient
capacity instead of shortening data or training. Actual GPU integration is pending.

At **02:55:11 UTC**, original 6p collection calibration
`6add610d1e112550ce7e64e1` was RUNNING, **21/24 complete**, no logged errors.
Four live CPU samples after the initial measurement were **48%, 60%, 60%, 55%**,
with roughly 3.9 GB RAM: the remaining games are actively computing. Resource
coordinator PID **1291091** was live, **54 submitted / 34 verified**, no failures.

Preflight: `ai/runs/opponent-surrogate-hf-preflight-v1.json`, SHA256
`49fcb2fda0f4d948c22e13fbb942a14f623b742e0156a6825ddb8f9870ad8828`.
Checkpoint: `ai/runs/opponent-surrogate-hf-preparation-checkpoint-v1.json`.

**Next:** finish the original 6p calibration, archive joint evidence and launch the
full fresh collection as described below. Then prepare training tensors; run
`package-opponent-surrogate-training-v1.py archive-data` and its `source` command
without `--code-only`. Dry-run/execute `launch-opponent-surrogate-training-v1.py
calibration`, collect the same handle with `collect-calibration`, then dry-run/execute
`full` only after admission. Full-training result collection and independent trained
model review still need implementation. No strength result, candidate or plateau claim.

**Previous — 25 October, 02:41 UTC: surrogate training/data/export pipeline implemented.**

The previous turn pushed the full collection orchestration in `0571cd7`. This turn
implemented a **433,217-parameter** opponent model, train/validation preparation,
HF-only four-seed trainer and standalone float64 ONNX export/verification. Design:
`strong/opponent-surrogate-training-design-v1.json`. No gradients or new HF jobs
have run; actual GPU training and the full-data preparation remain untested.

The model consumes the existing public state/action features and ranks exactly the
public six-candidate teacher shortlist. Teacher scores/seeds, deal identifiers,
terminal results and opponent identities are excluded from inputs. Cross-entropy
imitates the observed choice, with equal weight for all 60 count/rule/phase groups;
forced shortlists have no gradient. Four fixed seeds train for 80 epochs, retaining
each best validation macro-NLL checkpoint. The training bundle physically excludes
test records. All model/data/export files are separate from the live frozen source.

**Nine tests pass** on 382 real 2p calibration records plus synthetic boundary
checks. The random, unoptimized-weight ONNX export matched its float64 checkpoint
on **382/382 choices**, with maximum logit error below 1e-10. This is an engineering
proof, not a trained model or target-hardware benchmark. Actual incomplete-corpus
preparation was refused before output creation. Preflight:
`ai/runs/opponent-surrogate-training-preflight-v1.json`, SHA256
`edafe0ebf89591c90f980644fbb03b91277f331c722efca454ff5e182fc6c6f1`.

At **02:40:08 UTC**, original 6p calibration `6add610d1e112550ce7e64e1` remained
RUNNING, **17/24 complete**, no logged errors. Resource coordinator PID **1291091**
remained live with **54 submitted / 31 verified**, no failures. Checkpoint:
`ai/runs/opponent-surrogate-training-preparation-checkpoint-v1.json`.

**Next:** finish original 6p calibration and the full collection workflow below.
Then run `prepare-opponent-surrogate-training-v1.py` on the complete corpus,
package immutable training data/source and implement/admit its HF GPU launcher.
The implemented trainer must first exercise real gradients on HF; no local
training. Freeze a serving rule using validation only, evaluate test behaviour,
and compare fresh paired continuations with actual reference search before any
hybrid adoption. Full-game strength and actual 8840U hybrid validation still follow.

**Previous — 25 October, 02:26 UTC: full opponent-surrogate collection orchestration tested.**

The launcher, collector/indexer and coordinator are implemented. Seven tests pass:
complete 2,560-game coverage and whole-deal splits for every supported shard size;
measured time/memory/storage admission boundaries; incomplete calibration refusal;
382 real teacher records through an explicitly synthetic collection envelope;
and preservation of existing job handles after failures or uncertain submissions.
The envelope fixture is not fresh collection data and is never training eligible.
Proof: `ai/runs/opponent-surrogate-orchestration-preflight-v1.json`.

No full-collection plan, jobs or gradients were started. The actual admission check
correctly refuses until both original calibration endpoints are audited/archived.
At **02:25:37 UTC**, the original 6p job `6add610d1e112550ce7e64e1` was RUNNING,
**15/24 games completed**, no logged errors. Resource coordinator PID **1291091**
was live with **54 submitted / 29 verified**, no failures. Its pinned code and the
surrogate runtime source remain unchanged. Checkpoint:
`ai/runs/opponent-surrogate-orchestration-checkpoint-v1.json`.

**Next:** collect the original 6p endpoint, then audit/archive the joint calibration.
Run `strong/launch-opponent-surrogate-collection-v1.py prepare --max-in-flight 32`;
the completed measurements choose 4/2/1 whole deals per shard and a bounded timeout.
Dry-run every fixed shard and the coordinator before starting
`strong/coordinate-opponent-surrogate-collection-v1.py --execute` once. Keep its
original process/job handles. The collector checks every raw record and writes
the training/validation/test index only after all 2,560 games and 640 twins verify.
HF-only surrogate training still needs implementation and downstream validation.

**Recommendation to the user:** pursue selective auction search with stronger
opponent coverage and cautious overrides. The cited 30.9% overall / 15.6% Recharged
sealed baseline is old: frozen-1 reached **51.56% / 39.06%** in the larger 4p
development comparison (16 deals). The separate four-deal hybrid screen improved
Recharged sealed **43.75% → 68.75%**, but regressed original/open
**81.25% → 31.25%**. These are distinct datasets, not one longitudinal comparison.
Do not advance unchanged building/combined search. No general plateau, selected
candidate or new strength result is established by this tooling work.

**Previous — 25 October, 02:08 UTC: first surrogate HF endpoint verified; complete audit tools prepared.**

The previous turn archived the 20-case capture proof, prepared fresh collection and
launched the two HF runtime endpoints (`8b4e38f`, handoff `a0a9770`). This turn
verified the first real remote endpoint and implemented the complete calibration
and resource-screen archive audits. No new HF jobs or gradients were started.

**2p surrogate calibration COMPLETE and VERIFIED:** original job
`6add610c1e112550ce7e64df`, **8 games / 16 paired executions**, **382 teacher
choices / 30,784 teacher continuations**, zero caps. Every remote input and target
was checked; **48 public teacher calls** were independently repeated locally and
matched exactly. Measured HF execution: **145.19 s wall / 920.87 s CPU**, **5.41 GB
sampled summed RSS**, **26.21 MB raw evidence**. Runtime deals remain excluded from
training and strength. The original 60-file job archive is remotely verified at
HF revision `7c649ba97830254364bab6f380d8f6ca0deaccca`, SHA256
`5e31f7c797095074135994473814525aaeca841bf2afa8ea5d033de43828d9f6`.
Receipt: `ai/runs/opponent-surrogate-runtime-collected-v1/opponent-surrogate-runtime-v1-2p-0-1/verified.json`.

The first local collector pass rejected HF's valid content-addressed model cache
path because it assumed the filename stayed `inference64.onnx`. The collector now
accepts an absolute/common cache path while preserving the exact model-content hash
checks. The original failure log is retained. No remote job/source changed or was
restarted. **Five tests pass**, including ten corrupt public/teacher examples,
false terminal credit after re-sealing its file hash, runtime-as-training rejection,
and incomplete calibration refusal. Preflight:
`ai/runs/opponent-surrogate-collector-preflight-v1.json`.

New host-side tools (do not alter the pinned collection runtime):

- `strong/collect-opponent-surrogate-runtime-v1.py 6` collects the existing six-player
  handle only when complete, verifies every game and repeats its public teacher
  checks locally. `opponent_surrogate_verification_v1.py` supplies the independent
  raw-record, split, score and complete-grid checks.
- `strong/collect-opponent-surrogate-calibration-v1.py` audits both verified
  endpoints; `--archive` uploads their complete evidence once. The joint archive is
  still pending and full data collection is not admitted.
- `strong/collect-resource-replanning-development-v1.py` waits for all 54 original
  batches and the completed comparison. It reproduces the full comparison,
  recomputes all terminal credits and independently checks the primary/secondary
  whole-deal bootstrap using rational credits and bootstrap multiplicities. Then
  `--archive` preserves every cell and raw receipt. Its **three tests pass**, using
  96 actual terminal rows plus synthetic statistical/partial-run fixtures.
  Preflight: `ai/runs/resource-development-archive-preflight-v1.json`.

At **02:07:59 UTC**, original 6p job `6add610d1e112550ce7e64e1` was directly
RUNNING, **8/24 games completed**, no logged errors. Resource coordinator
**11670 / PID 1291091** was live with **54 submitted / 27 verified**, no failures;
an original resource handle was directly RUNNING. Checkpoint:
`ai/runs/opponent-surrogate-collector-checkpoint-v1.json`.

**Next:** finish the original six-player calibration, collect/audit/archive both
endpoints, then use measured costs for full fresh-collection admission and implement
its launcher/coordinator. Source, protocol and runtime launcher are already frozen;
no replacements after observation timeouts. Prepare HF-only surrogate training after
collection integrity/coverage. Require held-out behaviour, downstream continuation
checks against actual search, and full fresh strength evaluation before adoption.
For resources, let the existing coordinator finish and use the new complete audit
before interpreting/archiving results. Final selected-policy integration and actual
8840U hybrid validation remain outstanding. No candidate selection or plateau claim.

**Previous — 25 October, 01:54 UTC: capture proof archived; fresh-data HF calibration running.**

The previous turn completed and pushed the capture collector and its corruption
checks (`b597b1d`). This turn completed the remaining capture cases, audited and
archived all results, built/tested the fresh-data pipeline and started two bounded
HF calibration jobs. This is concrete research progress; no new model has trained
or qualified.

**Passive capture proof COMPLETE:** all **20 twins / 40 executions**, 2–6 players
and all four rules, passed. The audit verified **2,931 teacher decisions / 239,936
teacher continuations / 120 public teacher replays**, zero caps, all **1,463 source
files unchanged**, and the 2,553 canonical privacy/feature checks. Private HF
revision `4cbf90bc4cacf3c5db289f7be156f06604607432`, archive SHA256
`ffd4e0aebfc23117f2bae1e8d9cc0655b4a6cd4e5ea8553b5432996d52d78e04`,
**124 files**, remotely verified. Descriptor:
`strong/reference-opponent-capture-evidence-v1.json`. Session **40805** ended with
exit 0; do not restart or rearchive. These engineering records stay excluded from
training and strength results.

**Fresh opponent-behaviour collection prepared, not launched:** protocol
`strong/opponent-surrogate-collection-protocol-v1.json` fixes **2,560 games** over
Germany 2–6 players, every seat and all four rules, with **640 exact twin replays**.
For each count, deals 0–23 train, 24–27 validate, 28–31 test; every rule/seat/decision
from a deal stays in one split. Test labels are for integrity checking and later
held-out evaluation, never checkpoint selection. Every actual search_geo16
auction/building choice is recorded independently of outcomes. Non-strategic
opponent play can retain the exact economic policy. This is an approximation of
opponent behaviour inside continuations, not a new optimal-action teacher.

Three split/coverage tests and two wrapper boundary/failure tests passed. The latter
use synthetic wrappers, not real HF execution. A real fresh **8-game / 16-execution
2p preflight** covered both focal seats and all rules: **418 captured decisions,
48 public teacher replays**, exact twins and no caps. The isolated package matched
20 additional existing public requests exactly. Receipt/logs:
`ai/runs/opponent-surrogate-source-preflight-v1.json`,
`ai/runs/opponent-surrogate-source-prepared-v1/layout-check.json`.

Code/protocol/source/admission pushed in **8b4e38f**. Source dataset revision
`6d16cd796ce391b94326d31654866c2aae66769c`, archive SHA256
`7d88c611a50ccf69b0877550bbdf113b23d410cca71c5219acf90414def4d5ec`,
1,472 manifest files including the 1,463 unchanged base files. Do not edit these
pinned collection/source/launcher files while the calibration is running.

**HF calibration RUNNING:** both original handles directly confirmed at
**01:54:06 UTC**, each on **cpu-upgrade, 8 vCPU / 32 GB**, eight game workers and a
**4-hour timeout**. They cover 32 games / 64 paired executions in total and measure
CPU/wall/memory before full collection admission. Their records and outcomes are
excluded from training/strength.

- 2p: `6add610c1e112550ce7e64df`.
- 6p: `6add610d1e112550ce7e64e1`.
- Guards: `ai/runs/opponent-surrogate-runtime-launches-v1/`.
- Checkpoint: `ai/runs/opponent-surrogate-runtime-launched-v1.json`.
- No runtime coordinator exists; inspect the two original handles, never launch
  replacements after an observation timeout or ambiguous result.

**Existing resource screen:** coordinator **11670 / PID 1291091** remains live,
**54/54 submitted / 23 verified**, no reported failures at the same checkpoint.
An original resource handle was directly confirmed RUNNING. Do not alter its
source, restart it or compare incomplete results.

**Next:** implement collection/audit for the two surrogate HF endpoints; measure
complete jobs and review their raw games before admitting the full 2,560-game data
collection. The full collection launcher/coordinator and the surrogate trainer are
not implemented. All future gradients remain on HF Jobs. Require held-out behaviour
and downstream continuation comparisons against actual search before adopting a
surrogate, then fresh complete strength evaluation. Independently, complete the
resource-screen audit/archive collector and review only after all 54 batches verify.
The exact selected-policy final adapter and full target 8840U hybrid benchmark
remain outstanding. No candidate selection, production changes, final seeds or
plateau claim.

**Previous — 25 October, 01:40 UTC: capture collector prepared; existing experiments continue.**

Added `strong/collect-reference-opponent-capture-v1.py` and its three passing
collection tests. The collector independently checks every saved target, public
input, terminal credit, replay selection, source identity and complete 20-case grid
before allowing an archive. Ten deliberate privacy/target corruptions are rejected;
an actual incomplete run was refused. Preflight audited **14 completed cases /
1,524 teacher decisions / 84 public teacher replays**. This is capture engineering
evidence, not new training or playing-strength evidence. The archive also preserves
the original test log and preflight receipt; its only post-test code change adds
those two files to the archive list.

At **01:40:32 UTC**, the original capture process **40805 / PID 1384087** is live:
**18/20 twin cases**, **2,376 teacher decisions / 108 public replays**, zero reported
errors. The final two six-player cases are still running. Resource coordinator
**11670 / PID 1291091** is live with **50/54 jobs submitted, 18 verified**, no failures;
two original resource handles were also directly confirmed RUNNING on HF. Checkpoint:
`ai/runs/reference-opponent-capture-collector-checkpoint-v1.json`. No new standalone
jobs or gradients were started by this collector work. The existing resource
coordinator continues filling its already admitted fixed plan.

**Next:** preserve both existing processes. Once all 20 capture cases finish, run
`ai/.venv/bin/python ai/strong/collect-reference-opponent-capture-v1.py` to audit,
then `--archive` once after checking for an existing archive/descriptor. The capture
archive is still pending. Only then prepare fresh, whole-deal-separated collection
for a potential fast opponent-policy surrogate; the probe records remain excluded
from training. For resources, wait for all 54 batches before comparing and implement
the complete resource-screen archive collector. No candidate selection, final
qualification, production change or plateau claim.

**Previous — 25 October, 01:30 UTC: passive strong-opponent capture probe running.**

The previous goal turn completed both HF calibration endpoints and the reference
opponent diagnostic, archived their raw evidence, launched the fixed resource
screen, and verified its first four batches. That was concrete progress, not a
status-only wait. This turn leaves that experiment's source and policy unchanged.
Resource coordinator **11670 / PID 1291091** is live with **45/54 submitted,
13 verified**, no failures at this checkpoint; original HF handles were also
rechecked directly. The complete resource comparison remains pending.

The reference diagnostic consumed **85,247 CPU seconds for 896 continuations**.
Before putting nested reference search into every hypothetical opponent turn, a
potential cheaper route is to learn its behavior from public positions and test
that approximation inside continuations. This would be an **opponent-policy
surrogate**, not evidence that copying its choices makes the focal bot optimal.
No surrogate has been trained, no training dataset prepared, and no new opponent
policy has been inserted into the running experiment.

Added and pushed in **854d270**:

- `strong/capture-reference-opponent-v1.cjs` wraps the actual arena's original
  `search.choose` call once, preserving its arguments, result and game state. It
  records public feature/menu inputs and the actual choice. The wrapper installs
  only in its dedicated arena process; non-strategic economic decisions need not
  be approximated. Teacher seeds/results are label provenance, not model inputs.
- `strong/test-reference-opponent-capture-v1.cjs` passed all **2,553 canonical
  positions**, including hidden deck/bid/plan mutations, exact feature/menu equality,
  public money preservation and unchanged source state.
- `strong/probe-reference-opponent-capture-v1.py` is running **20 exact twin cases /
  40 game executions** at 2–6 players, all four rules, last focal seat. One bridge
  records and one does not; every observed transition and terminal must match.
  All probe games/records are excluded from future training and strength. This is
  a local engineering probe with eight workers, no gradients or new HF jobs.
- `strong/verify-reference-opponent-capture-v1.cjs` checks every recorded public
  input/menu and target, matches teacher totals to actual-game search counters, and
  replays the first/last choice of each strategic kind using only public state and
  the original search settings. Teacher configuration remains 16 samples, six
  candidates, geographic proposals and the 2,400-step horizon.

Live probe: **session 40805 / PID 1384087**, output
`ai/runs/reference-opponent-capture-probe-v1/`, console
`ai/runs/reference-opponent-capture-probe-v1.log`. At the checkpoint, **8/20 twin
cases** passed, with **551 captured teacher decisions / 48 exact public teacher
replays**, zero errors. The remaining cases are still running; do not restart the
existing process after an observation timeout. All **1,463 frozen runtime files**
still match their source. The separate capture code hashes are pinned in the
probe intent/status. Checkpoint: `ai/runs/reference-opponent-capture-checkpoint-v1.json`.

**Next:** continue both existing processes. For resources, verify all 54 batches
before comparing or archiving the full strength screen. For capture, finish all
20 twin cases, audit every source/receipt and archive the complete probe before
preparing fresh training collection. At that checkpoint the complete capture-probe collector/archive
script was not yet implemented; the 01:40 update above supplies it. If the capture proof succeeds, preregister fresh
collection and whole-deal train/validation splits, measure HF execution, and train
only on HF Jobs. Validate held-out action behavior and downstream continuation
comparisons against real search before adopting a surrogate. Cautious auction
overrides remain a separate unimplemented experiment. Do not use the seven
outcome-selected diagnostic roots as training answers. No candidate selection,
production changes, reserved final seeds or plateau claim.

**Previous — 25 October, 01:15 UTC: calibration complete, resource screen launched, auction diagnostic audited.**

The previous goal turn made concrete progress: resource collection/comparison and
coordinator implementation, ten passing tests and push `fa1f681`. This turn completed
both pending experiments' verification, archived their evidence and started the
fresh resource-strength screen. No candidate is selected or qualified.

**Resource calibration:** both original jobs are complete. All **32 games / 4,072
learner decisions / 1,228 resource searches / 89,632 continuations** match the local
pilot exactly, zero caps. The 6p endpoint used **1,896.21 s wall / 12,197.48 s CPU**,
with **8.15 GB sampled summed RSS**; resource-only median/p95 **7.80 / 21.02 s** under
parallel HF execution. These are runtime-only deals, not strength or 8840U latency.
Full 106-file archive: private HF revision `06103b8b9a50a391d51e4e00b2f2ba8e8d34bb5f`,
SHA256 `274743522941e5d6d0065ebbb719aebec76a6a8bd2b74a99aac00fcc0120565a`.
Descriptor: `strong/resource-hf-calibration-evidence-v1.json`. Do not rearchive.

**Resource screen is RUNNING:** the measured plan fixes **54 jobs / 3,360 games**,
2 arms, 27 count/opponent cells, all 2–6-player seats and all four rule combinations.
Each job covers four whole deals on **cpu-upgrade (8 vCPU / 32 GB)**, eight game
workers, one search worker, eight worlds, 2,400/1,600 horizons, **6-hour timeout**,
maximum **32 concurrent jobs**. The first 32 were submitted once. At the 01:15:01 UTC
checkpoint, direct HF inspection showed **30 RUNNING / 2 COMPLETED**; completed
shards were not yet collected. No partial strength comparison has been made.

Coordinator **session 11670 / PID 1291091**:
`ai/runs/resource-replanning-development-coordinator-v1/{state.json,coordinator.log,latest-status.json}`.
Original IDs and guards: `ai/runs/resource-replanning-development-launches-v1/`.
Plan: `strong/resource-replanning-development-plan-v1.json`, SHA256
`19be586eb881b2c065a5f79454ec858a0c1e750f281f713c4be513b3d46badbf`.
All 54 shard dry runs plus coordinator passed before submission; receipt:
`ai/runs/resource-development-admission-preflight-v1/receipt.json`.
The first inline preflight driver stopped on a missing `ai/strong` import path
before any outputs or job guards; correcting its PYTHONPATH passed without changing
frozen code. Evidence/plan pushed in `6bc5d5d` before dispatch. New jobs use the
unchanged pinned source and policy; no batching optimization was injected.
Checkpoint: `ai/runs/resource-development-launched-checkpoint-v1.json`.

**Auction opponent diagnostic is COMPLETE:** coordinator **76600 / PID 443128**
ended successfully, **28/28 verified**, 896 reference continuations plus 896 mixture
controls, zero caps. All terminal credits, fixed world/action grids and paired
bootstrap summaries were independently audited. Full 301-file archive: private HF
revision `baa0e390312c92e9bde3a2979e1e310a1a9330e4`, SHA256
`131837afcf38a3dde522fa0810551d744cf309670ec1d475fcf8359d9293f1c6`.
Descriptors: `strong/reference-opponent-comparison-v2.json` and
`strong/reference-opponent-complete-evidence-v2.json`. Do not restart/rearchive.

Replacing the simulated opponent policies reversed the sign of selected-minus-model
advantages in **four of seven outcome-selected positions**. The held-out paired
intervention intervals exclude zero at roots **3** and **4**, with opposite signs.
This establishes sensitivity to opponent assumptions at these positions, not a
universally better search or fresh playing-strength gain. Known arena opponent
identity was diagnostic-only; prior-bid inference and future-policy changes are
confounded where prior inference is present. No action was reselected. Full table
and interpretation are in `HYBRID-SCREEN-2026-10-24.md`.

**Next:** continue the existing resource coordinator, collect/verify all 54 batches,
then inspect its full comparison and archive raw evidence. Failed or ambiguous jobs
must be reconciled using original handles, never automatically replaced. Use the
auction diagnostic to design a fresh-position experiment for stronger opponent
coverage and uncertainty-aware overrides; do not train on these selected positions
as answers or expose arena opponent identity in deployment. No current plateau
claim. The exact selected-policy final adapter and full 8840U hybrid benchmark
remain unimplemented/unproven; the old final launcher still evaluates the older
search path. Reserved final seeds remain unused.

**Live collection update — 2026-10-25T01:17 UTC:** the coordinator has
verified its first **4 real development shards / 384 games / 42,624
learner decisions**, zero caps, and is filling the released slots using new planned
cases. These are the 6p filter baseline cells (economic, heuristic, legacy, rush);
resource-arm results and the complete strength comparison remain pending. No
partial outcome ranking. Receipt: `ai/runs/resource-development-first-collection-v1.json`.

**Previous — 25 October, 01:05 UTC: resource-screen orchestration prepared and tested.**

The resource development screen now has a collector, complete comparator and
lock-protected coordinator, alongside the measured launcher. These are host-side
orchestration only: no frozen game/search/model source changed. **No development
plan or jobs exist yet.** The original 6p HF calibration is still RUNNING; 2p is
already verified. The previous goal turn was a verified wait (original remote job
and coordinator checked live), followed by an answer to the user's hybrid question.

- `strong/manage-resource-replanning-development-v1.py` verifies immutable job,
  source, seed, model and manifest identities, then every actual-game/decision
  receipt. A runtime-only job cannot pass as fresh development evidence.
- `strong/compare-resource-replanning-development-v1.py` requires the full
  **3,360-game / two-arm / 27-cell** grid before writing a comparison. It reports
  every count/rule/opponent contrast, resource/request latency and runtime. The
  primary search-opponent summary gives each count equal weight; bootstrap draws
  retain each whole deal's seats and rules and resample independently by count.
- `strong/coordinate-resource-replanning-development-v1.py` uses the admitted
  concurrency, preserves original handles, collects completed jobs and stops on
  failures or uncertain observations. No retries/cancellations or partial ranking.

**Ten tests passed.** Collection was exercised with the real archived 2p receipts
(8 games, 1,306 decisions, 41,632 resource continuations) under a **synthetic outer
development envelope**, not new game execution. Tests reject re-sealed false win
values, wrong source/seed/search identities, incomplete/duplicate grids and failed
job states; they check whole-deal statistics, equal count weights and reuse of live
or completed handles. Statistics and coordinator fixtures are synthetic, not
strength or HF execution evidence. Source hashes and log are saved in
`ai/runs/resource-development-orchestration-preflight-v1/{receipt.json,tests.log}`.

At checkpoint **2026-10-25T01:04:48 UTC**, the original 6p calibration job
`6add4e781e112550ce7e5a74` and final reference shard
`6add4b5c046eb82b1ece10c5` were authoritatively RUNNING. Reference coordinator
**76600 / PID 443128** was live with **27/28 verified**, no failures. The 6p log
had **23/24 games complete**, no observed caps/tracebacks; a short metric sample
showed 12.5% of eight vCPUs and 2.94 GB memory, consistent with one remaining game.
This is a tail observation, not a total runtime/memory bound. Raw observation and
observer code remain in its collected folder. Full checkpoint:
`ai/runs/resource-development-orchestration-preflight-v1/checkpoint.json`.

**Next:** collect/verify the existing 6p job, then audit/archive both calibration
endpoints with `collect-resource-hf-calibration-v1.py --archive`. Prepare the measured
plan using `launch-resource-replanning-development-v1.py prepare --max-in-flight 32`,
review its actual budget/partition and dry-run every case plus the coordinator.
Only then dispatch the fixed screen once with the coordinator. Collect/audit the
reference diagnostic only after its existing coordinator verifies all 28 batches.
No new gradients, candidate selection, production changes or final seeds.

**Previous — 25 October: full resource-screen launcher prepared; HF utilization sampled.**

**Update — 00:54 UTC:** the original **2p HF calibration job completed and verified**.
All **8 games / 1,306 learner decisions / 450 resource searches / 41,632 continuations**
match the archived local pilot exactly, zero caps. HF evaluation wall time was
**1,204.86 s**, CPU **4,932.77 s**, sampled summed RSS **7,253,655,552 bytes**;
resource-search median/p95 **7.65 / 28.16 s** under parallel HF execution.
Its 22-file artifact is verified at private HF revision
`07a4f71ad7f231fbd7f5afb86484deb706c74b57`, archive SHA256
`7b46ff822eaa42a623f4233211df49ba92d40a023097acec0bc6e1e89eff9c54`. Local receipt:
`ai/runs/resource-replanning-hf-runtime-collected-v1/resource-replanning-hf-runtime-v1-2p-resource-filter/verified.json`.
The 6p job is still running; complete calibration/archive and development admission
remain pending. These runtime-only outcomes are excluded from strength.

`strong/launch-resource-replanning-development-v1.py` now prepares immutable measured
admission only after both HF calibration endpoints are verified and archived. It
preserves the full **3,360-game / two-arm / 27-cell** screen. Completed HF timings
choose **4/2/1 whole deals per shard**, retaining all seats/rules and fixed horizons;
CPU/RAM/storage headroom determines the budget. Submission guards stop duplicates,
ambiguous submissions, failed jobs and excess concurrency. The uploaded source and
live experiments are unchanged. **No development plan or jobs exist yet.**

Six tests passed using a fake HF API and synthetic measurements, including all
54/108/216-shard partitions, complete 3,360-game coverage, missing calibration,
runtime/memory/storage limits and submission failures. The actual missing complete
calibration archive also refuses admission. Receipt:
`ai/runs/resource-development-launcher-preflight-v1.json`. These checks are not
actual development execution or measured admission.

Read-only live samples at about **00:47 UTC** confirmed both calibration jobs on
**cpu-upgrade (8 vCPU)**. The 6p job was at **8/24 completed**, then sampled
**100% CPU**, maximum observed memory **6,512,885,760 bytes**. The 2p job was at
**7/8 completed**, then sampled **12.5% CPU**, memory **2,489,208,832 bytes**;
one remaining game explains the idle workers at the tail. Each observation retains
all three raw frames (including any initial zero), bounded logs and observer source
under its `resource-replanning-hf-runtime-collected-v1/<case>/` directory; the full
calibration collector will include these files. These short windows are not runtime
or memory bounds. The measurements support keeping eight workers and grouping
multiple whole deals when the complete endpoint budgets permit it.

At checkpoint **2026-10-25T00:53:15.317952+00:00**, reference coordinator **76600 / PID 443128**
was checked alive with **26/28 verified**, no failures. Both calibration
jobs' latest SDK status was RUNNING; timestamps and metric snapshots are preserved
in `ai/runs/resource-development-launcher-checkpoint-v1.json`.

**Next:** collect the two original calibration jobs when complete, require exact
local/HF parity, then audit/archive with `collect-resource-hf-calibration-v1.py`.
Finish the development shard collector, full comparison and coordinator before
launching the full screen. The new launcher is prepared, but that orchestration is
still unimplemented and no admission has been created. After calibration and these
checks, prepare/review the measured plan and dry runs before dispatch. Continue the
existing reference coordinator and audit all seven roots only after all 28 shards
verify. No new gradients, production changes, candidate selection or final seeds.

**Previous — 25 October: full resource pilot archived; two HF calibration jobs running.**
The existing local pilot **session 75756 / PID 559327 ended successfully**. All
**64 games / 8,241 learner decisions / 89,632 continuations** passed, zero caps.
All **16 independent replays** matched (**2,252 learner decisions**, including
344 resource decisions). The final audit rechecked all 1,481 source files and
complete paired endpoint records. Archive verified once at private HF revision
`8c92c3936316f4e8bf452d08972f5732129027ec` (201 files), descriptor
`strong/resource-replanning-runtime-evidence-v1.json`; archive SHA256
`8791c1dcf3eccab72e792da83f0cdf95421091f451d6518cd6a275b0de296e5a`. Do not restart the ended pilot or repeat its upload.

Complete endpoint measurements admitted **cpu-upgrade: 8 vCPU / 32 GB / 50 GB**,
with **two-hour timeouts** and at most two concurrent calibration jobs. The estimated
budget floor was 6,356.62 s, including setup and margins; both dry runs passed.
This is a measured local budget for remote calibration, not a remote speed claim.
Admission: `strong/resource-replanning-hf-runtime-admission-v1.json`.
Both original jobs were authoritatively **RUNNING** at **2026-10-25T00:38:06.911945+00:00**:

- **2p:** `6add4e77046eb82b1ece123a` — eight runtime-only games.
- **6p:** `6add4e781e112550ce7e5a74` — 24 runtime-only games.

Original guards: `ai/runs/resource-replanning-hf-runtime-launches-v1/`.
Use `collect-resource-replanning-hf-runtime-v1.py 2 --inspect` (or `6`) for status;
when complete, omit `--inspect` to collect/revalidate exact archived local/HF
choices, world draws, resource continuations and terminals. No retries or duplicate
submissions. The unchanged source is still revision
`8d3697dec0845aa6ded857f3e00d91a8ff4406c0`; the separate batching experiment is not
included. Calibration outcomes remain excluded from strength.

`strong/collect-resource-hf-calibration-v1.py` is prepared for **both** verified
endpoints. It revalidates each existing job, aggregates all 32 games, and defaults
to audit only; `--archive` is a one-time complete archive. Three tests passed,
including ten incomplete/inconsistent-record cases and missing-endpoint refusal
before any network access/upload. The actual current partial calibration was also
rejected. Preflight uses synthetic HF-shaped envelopes around real local counts;
it is not actual HF parity evidence. Receipt:
`ai/runs/resource-hf-calibration-collector-preflight-v1.json`.

At the same checkpoint, reference coordinator **76600 / PID 443128** was confirmed
live with **24/28 verified**, all 28 submitted, no failures.
Exact checkpoint: `ai/runs/resource-hf-calibration-launch-checkpoint-v1.json`.
**Next:** continue these existing jobs; verify/archive both complete calibration
endpoints before preparing separate measured admission/orchestration for the
3,360-game resource development screen (still unlaunched). Collect and audit the
reference comparison only after all 28 shards finish. No new gradients, production
changes, selected candidate, or final seeds. No plateau conclusion.

**Previous — 25 October: action-count batching checked locally and on AMD8840U.**
A separate experimental wrapper sorts inference rows by legal-menu size, runs the
unchanged float64 model in batches of at most 64, and restores original row order.
All **2,553 canonical serving choices** matched locally, including every previously
recorded target move across 2–6 players and all four rule combinations. On each
host, **28,743 predictions / 224 continuations** across four saved stress requests
matched exactly; observation hashes, choices and continuation results also matched
between the local HX370 and the actual AMD8840U.

On the idle-at-start AMD8840U, the 2p original/open large-batch case reduced padded
actions **393,044→277,987** and summed inference time **10.402→8.315 s** (about 20%).
The other three cases had unchanged padding and essentially unchanged timing
(about 0.5–0.7% slower). Calls alternated baseline/candidate order. These are four
old selected four-world stress cases, not representative latency or fresh strength.
The canonical batch timing is order-biased and should not be used as a speed claim.
The wrapper is **not adopted** into live/pinned evaluations or serving; no model
weights changed. Any adoption still needs a new runtime identity and exact paired
full-game checks, including actual eight-world workloads.

Evidence is archived and remotely verified once at private HF revision
`7f7b3834c2160f1d9a5ece41ad1ea83e8af8f566` (44 files), descriptor
`strong/bucketed-inference-evidence-v1.json`. Archive SHA256:
`bf4a94b591eb7d6669d41f4ef075faff8014e8185b55df98902250d02ee112bd`.
The actual target run **PID 2976420** is complete and collected; do not restart it.
Source: `strong/bucketed_inference_v1.py`; paired/canonical harnesses:
`strong/probe-bucketed-resource-inference-v1.py` and
`strong/probe-bucketed-serving-inference-v1.py`.
Read-only collector: `strong/collect-bucketed-inference-v1.py` (archive already done).

At **2026-10-25T00:29:17.812512+00:00**, the unchanged resource pilot **75756 / PID 559327**
has **64/64 game files**, all four cells verified, zero caps,
and **11/16 replay files**, stage `replaying`.
The reference coordinator **76600 / PID 443128** remains live:
**28/28 submitted, 22 verified**, failures `[]`.
Snapshot: `ai/runs/bucketed-inference-checkpoint-v1.json`.

**Next:** complete/collect/archive the existing 16-replay resource pilot. Its full
6p resource cell measured 2,728.31 s wall / 20,435.01 s CPU and 7.99 GB sampled
summed RSS. After the complete archive, review the prepared launcher's admission
for **cpu-upgrade (8 vCPU, 32 GB), two-hour calibration jobs**, dry-run both endpoints,
then submit each once and verify exact local/HF behavior. This hardware choice is
provisional until the launcher's full evidence checks pass; no HF resource admission
or jobs exist at this checkpoint. The 3,360-game resource strength screen remains
unlaunched. Collect the reference comparison only after all 28 shards verify.
No new gradients, production changes, selected candidate or final seeds.

**Previous — 25 October: fixed-root component profile complete and archived.**
The corrected profiling harness completed the previously saved 2p/original/open
resource stress request: **128 continuations / 17,248 simulated neural decisions**,
exact recorded actions and continuation receipts, zero caps. All packaged source
hashes remain unchanged. This used four worlds and one inference/search worker
on the shared local HX370, not the current eight-world development setup or a
fresh AMD8840U latency sample. Native ONNX calls took **34.20 / 56.57 s (60.4%)**;
engine-pool calls took **19.38 s (34.3%)**, including IPC/waiting. Python prediction
work outside ONNX was about **2.00 s**. Three V8 profiles and Python statistics
are preserved. Idle Node intervals overlap inference and must not be added to wall
time. This supports investigating inference costs before a wholesale engine rewrite;
it is one selected, instrumented case, not a representative latency result.

The first harness failed by comparing integer world keys in memory with string
keys in JSON. Its raw profiles and failed source are preserved; its actual result
was not saved, so do not claim its behavior was verified. The v2 comparison
canonicalizes JSON keys and saves the result before asserting equality. Both
attempts, the diagnosis and successful audit are archived once at private HF
revision `4d16663067b7683a2a1e735560448d3b788291c3` (21 files), descriptor
`strong/resource-components-profile-evidence-v2.json`. Do not repeat the upload.
Collector `strong/collect-resource-components-profile-v2.py` defaults to read-only
validation and rejects another archive attempt.

At **2026-10-25T00:18:53.815513+00:00**, both existing processes were checked alive. Reference coordinator
**76600 / PID 443128**: **27/28 submitted, 20 verified**,
failures `[]`. Resource pilot **75756 / PID 559327**:
**20/24 six-player resource game files**,
cell still `evaluating`; **0/16 replay files**.
The three earlier cells remain complete. Exact snapshot:
`ai/runs/resource-components-profile-checkpoint-v2.json`.

**Next:** let those existing runs finish; preserve the full 64-game/16-replay
resource pilot and all 28 reference shards before their respective collectors.
The prepared HF resource calibration still has no admission or submission; the
3,360-game strength screen remains unlaunched. No new gradients, candidate selection,
production changes or final seeds. Auction search remains promising but regresses
in several cells; do not advance unchanged building/combined search or treat this
profiling result as evidence of a strength plateau.

**Previous — 25 October: resource HF source and preflight archived; both 2p pilot cells verified.**
At **23:53:14 UTC, 24 October** (25 October locally), both existing processes were
checked live. Resource **session 75756 / PID 559327** has verified all eight
2p/filter games, eight 2p/resource-filter games and **24 6p/filter games**, zero caps.
It is running **6p/resource-filter** (**6/24 game files complete**, cell unverified);
all 16 independent replays remain pending. Auction **session 76600 / PID 443128**
has **23/28 submitted, 16 verified**, no failures at this checkpoint.

The tested HF wrapper is now in an immutable, remotely verified source:
`strong/resource-replanning-job-source-v1.json`, dataset revision
`8d3697dec0845aa6ded857f3e00d91a8ff4406c0`. All 1,482 prior package files remain
unchanged; only the wrapper and builder were added. Its 378 valid / 13 rejected
contract checks and three intentional execution-boundary stops are archived once
at model revision `ed9f76066b7d858e7b5ad1603ffa54012f354a74` (30 files), descriptor
`strong/resource-job-source-preflight-evidence-v1.json`. Both uploads were verified;
do not repeat them. The ended archive session 4420 is reconciled by that descriptor
and the downloaded archive hash, not by an assumption about the expired handle.

The complete 2p resource cell used **41,632 continuations**, 450 resource searches,
**1203.34 s wall / 6352.42 s CPU**, sampled summed RSS 6.97 GB. Resource-only decision
median **9.81 s**, p95 **33.01 s**. These are parallel local HX370 engineering
measurements, not 8840U latency, HF hardware admission or playing-strength results.
Raw cost summary: `ai/runs/resource-replanning-runtime-source-prepared-v1/completed-2p-resource-cost.json`.
Exact checkpoint: `ai/runs/resource-replanning-runtime-source-prepared-v1/job-source-checkpoint.json`.

The new `strong/launch-resource-replanning-runtime-v1.py` prepares a separate HF
calibration admission only after the full pilot archive exists, then can submit
one 2p and one 6p resource job. **No admission file or submission exists yet.**
Five tests passed, including incomplete-pilot refusal, measured-budget bounds,
duplicate submission and an ambiguous submission that remains blocked from retry.
The success/timeout submission cases use a fake API; they are not actual HF jobs.
Receipt: `ai/runs/resource-hf-runtime-launcher-preflight-v1/receipt.json`.
The source bootstrap and both offered CPU hardware sizes were also checked.
Latest snapshot: `ai/runs/resource-replanning-runtime-source-prepared-v1/hf-launcher-preparation-checkpoint.json`.

`strong/collect-resource-replanning-hf-runtime-v1.py` is now prepared. It only
inspects/collects existing admitted calibration jobs, verifies their complete raw
reports and archive identity, and requires exact recorded local/HF behavior. Only
host paths and the explicitly named timing fields are excluded; all resource worlds,
continuations, actions and terminals must match. Five corruption/boundary tests
passed. A full saved 2p batch converted to synthetic HF paths/timings also passed:
8 games, 1,306 learner decisions, 450 resource decisions, 41,632 continuations.
This is a collector preflight, **not actual HF calibration or new game execution**.
Proof: `ai/runs/resource-hf-runtime-collector-preflight-v1/receipt.json`.
Current snapshot: `ai/runs/resource-replanning-runtime-source-prepared-v1/hf-collector-preparation-checkpoint.json`.

**Next:** continue the two existing processes. Require all 64 local games and
16 replays before running `collect-resource-replanning-runtime-v1.py`, then archive
once. Use that complete evidence to choose/review the calibration hardware and
run the prepared launcher's `prepare` command, followed by both dry runs before
submission. Use the new collector on those existing jobs after completion; require
both exact endpoint comparisons before any separate development admission. Neither
calibration nor the 3,360-game development screen has launched. The source descriptor's `runtime_admitted=false` describes preparation
and must not be edited into an admission. After all 28 auction shards verify, run
the prepared reference collector and archive the complete comparison. No gradients,
production changes, candidate selection or final seeds. This is not a plateau claim.

**Previous — 25 October: resource runtime pilot started; auction diagnostic continues.**
**23:16:43 UTC update:** both handles were checked live. Auction coordinator
**76600 / PID 443128** has **12/28 submitted, five verified, seven running**, no
failures. Resource pilot **75756 / PID 559327** has completed/verified 2p/filter;
**seven of eight 2p/resource-filter games have ended**, but that cell is not yet
fully verified. Keep the 6p cells and 16 replays pending, not complete.

`strong/collect-resource-replanning-runtime-v1.py` now requires the entire 64-game
pilot and all 16 replays, rechecks pairing/receipts/source identity and preserves
runtime/resource-search distributions. Its partial-pilot rejection check passed.
Run it without arguments only after pilot completion, inspect all cells, then use
`--archive` once. No archive has been attempted.

`strong/resource-replanning-development-job-v1.py` is a tested **unlaunched** job
wrapper, including a separate runtime-calibration mode. Its clean-package preflight
checked 378 valid partitions, rejected 13 invalid requests, and exercised three
execution boundaries with real pinned model hashes and injected stops before games.
No external uploads/jobs/games occurred in that preflight. Inputs/receipt:
`ai/runs/resource-development-wrapper-preflight-v1/`. It still needs a new pinned
source/launcher and measured runtime admission; do not call it a launched screen.
Exact current checkpoint:
`ai/runs/resource-replanning-runtime-source-prepared-v1/collection-preparation-checkpoint.json`.

The prior turn added and checked the complete-results audit. This turn prepared,
uploaded and verified a separate resource-policy runtime package, then started the
preregistered full paired endpoint pilot. No gradients or fresh strength games.

**Continue local session 75756 / PID 559327**, started **23:02:46 UTC, 24 October**
(25 October locally). At **23:04:53 UTC**, the eight-game 2p/filter cell had completed
and verified 1,371 decisions, zero caps; **2p/resource-filter is running**. The pilot
will continue to both 6p cells and then 16 predeclared independent replays: **64 games
total**, every seat and all four rule combinations, eight resource worlds, 2400-step
rollouts and unchanged 1600-step games. Pilot outcomes are excluded from strength.
It runs eight games at a time on the local HX370, not the AMD8840U target or HF.

Source: `strong/resource-replanning-runtime-source-v1.json`, private HF dataset
revision `6950d0baffdbb1e2a91bb09849c68b9c15db9fbf`, SHA
`5e3a402b03e26d93d6741d6879024c49bc5b7ca7db3a01b575c3c8d6461a684c`.
All 1,463 base files remain unchanged; 18 files were added. A clean-package check
and exact replay of an existing 159-decision game passed before launch.
Do not edit the pinned pilot, builder, protocol, plan or packaged runtime while live.
Output is **inside the clean layout**:
`ai/runs/resource-replanning-runtime-source-prepared-v1/layout/ai/runs/resource-replanning-runtime-v1/`.
Checkpoint: `ai/runs/resource-replanning-runtime-source-prepared-v1/turn-checkpoint.json`.

The first local package preparation stopped before games/upload because a current
reporting script differed from its historical packaged version. The failed files
are preserved in `ai/runs/resource-replanning-runtime-source-preparation-failed-v1/`.
The correction keeps the historical runtime intact and checks current reporting
dependencies on the host, separately from runtime overlays. The corrected source
upload completed once; do not repeat it.

**Also continue auction coordinator session 76600 / PID 443128.** At the same snapshot,
10/28 jobs were submitted, three verified, seven running, no failures. Its complete
audit/archiver remains ready but unrun. No duplicate/retried/canceled jobs were started.
After both complete, verify/archive each full result separately. The resource
3360-game development screen is still unlaunched and requires measured admission;
the runtime pilot is not that screen. No candidate selection, production changes or
final seeds. The strong-model goal remains active.

**Previous — 25 October: HF diagnostic continues; complete-results audit prepared.**
The same coordinator, **session 76600 / PID 443128**, is alive. At the explicit
**22:53:31 UTC, 24 October** snapshot, **10/28 jobs were submitted, three verified,
seven running, no failures**. The three verified batches contain 96 continuations;
do not read these faster batches as a partial ranking. Exact checkpoint:
`ai/runs/reference-opponent-coordinator-v2/collector-preparation-checkpoint.json`.
No duplicate launches, retries, cancellations, additional simulations or gradients
were initiated during this checkpoint.

`strong/collect-reference-opponent-diagnostic-v2.py` is ready for full completion.
It requires the coordinator's `comparison_complete` state and all 28 verified jobs,
then revalidates every shard and independently rebuilds credits from terminal
players, exact rational paired margins and the joint bootstrap using block counts.
Its preflight checked **896 control + 16 pilot + 96 collected terminal rows**,
rejected five corrupted inputs, and rejected a partial comparison without creating
an archive. The full seven-root aggregate audit is still pending. Receipt:
`ai/runs/reference-opponent-collector-v2-preflight/receipt.json`.

**Next:** continue session 76600. After completion, run the new collector without
arguments, inspect all seven roots, then run once with `--archive` to persist the
complete evidence. The final descriptor/archive do not exist yet; do not claim
completion or reuse an uncertain upload. No new strength result, candidate selection
or final seeds. The resource ablation remains unlaunched.

**Previous — 25 October: repaired opponent-model pilot passed; HF diagnostic running.**
The v2 worker scopes `analysis-public-balances-v1.cjs` to the reference opponent's
nested search through `reference-search-public-balances-v1.cjs`. Historical modules,
outer world sampling and mixture controls remain unchanged. JSONL errors now exit
immediately. Six worker tests passed, including arena parity and failure isolation.
All **896** mixture continuations matched again. All **16** reference pilot
continuations completed with no caps, including the previously failing 6p sealed
case; the 12 previously completed v1 rows reproduced exactly. Session **67264**
finished exit 0. The full pilot is archived once and verified at private HF revision
`59243d245597ebd4034d187bf9b07e3c8b3f952b` (74 files), descriptor
`strong/reference-opponent-pilot-evidence-v2.json`. Do not rerun its collector.

The fixed **896-continuation** comparison is now admitted as **28 CPU Basic jobs**,
16 worlds/two actions each, at most seven concurrent, three-hour timeouts. No new
candidate actions, roots or seeds were selected from the pilot. An infrastructure
canary completed and verified 32 continuations before expanding the job queue.
**Continue coordinator session 76600 / PID 443128**, started 22:43:31 UTC on 24 October
(25 October locally). At the explicit 22:44:48 UTC check, eight jobs had been submitted:
the canary was verified and the other seven were RUNNING. State and exact job handles:
`ai/runs/reference-opponent-coordinator-v2/{state,turn-checkpoint}.json`; guards:
`ai/runs/reference-opponent-launches-v2/`. The coordinator collects every shard and
only then writes `strong/reference-opponent-comparison-v2.json`. No automatic retries
or cancellations. Do not duplicate or restart a live coordinator or job.

**Next:** monitor the existing handle, verify the complete fixed comparison, then
assess the original chosen-versus-model action margins on worlds 8..63 against the
unchanged mixture. These are outcome-selected, conditional diagnostics, not fresh
strength games; known opponent identity is diagnostic only. Preserve all seven roots
and adverse cases. The separate resource ablation remains unlaunched. No new gradients,
candidate selection, production changes or final seeds; the strong-model goal is active.

**Previous — 25 October: opponent-model pilot found a nested sealed-history failure.**
The new isolated reference-opponent worker reproduced all **896** fixed-action
mixture controls exactly across the seven roots and 64 worlds. Three complete
reference pilots (2p/4p search, 3p heuristic), **12 continuations**, passed with zero
caps. The 6p Recharged/sealed pilot failed inside nested `createAnalysisScenario`:
an inferred earlier bid was assigned to the hypothetical state without a matching
history entry, so unconditional money reconstruction could not replay the next
nomination. All balances were already public; that reconstruction was unused.

Session **5175** is finished, exit 1. Its four failed workers printed exceptions
but kept stdin alive; they were explicitly terminated after recording the failure,
allowing the parent to exit. No HF jobs were launched, no strength comparison was
made, and no policy or frozen dependency changed. Do not rerun the v1 pilot.
The one-shot failure collector completed and verified 70 evidence files:
`strong/reference-opponent-pilot-failure-evidence-v1.json`, private HF revision
`e2605d3e6f5d3ef2b43eb6713504f08ae496c449`. Do not repeat its upload.

An isolated proposed sampler repair, `strong/analysis-public-balances-v1.cjs`, skips
balance replay only if every balance is already known. It preserves **2,553** normal
fixture worlds exactly and **24** unknown-money recoveries, and repairs the captured
failure without changing its public history or leaking hidden fields. It is **not
integrated or adopted**. All 1,463 historical runtime files and 32 frozen dependencies
remain unchanged. The draft HF job/launcher/success-collector files are unlaunched;
their required successful admission descriptor does not exist.

**Next:** build a versioned reference worker using the isolated sampler only for its
nested search, with immediate JSONL process exit on errors. Recheck arena/control
parity and run a fresh complete runtime pilot, including the 6p sealed failure, before
admitting the 64-world HF diagnostic. Keep the same seven roots, original action
pairs and public seeds. Preserve the failed v1 record; do not treat its three finished
pilots as a successful comparison. No new gradients, candidate selection or final
seeds. The separate resource ablation remains unlaunched. This is an engineering
failure in a new diagnostic, not evidence of a training plateau.

**Previous — 25 October: all seven one-action counterfactual pairs complete.**
`strong/auction-first-action-counterfactual-v1.py` ran the filtered model throughout
seven controls (every original decision/public root and terminal report matched),
and seven branches changing exactly the saved first differing action before returning
to the filtered model. All **1,886 learner decisions / 6,919 root moves** passed;
zero game/opponent-search caps. Session **82545** exited 0. Evidence is archived and
verified: `strong/auction-first-action-counterfactual-evidence-v1.json`, private HF
revision `f9dc1f9f1092e9a36809001486bac0daa8111866`.

Effects within these fixed deals: the 4p original/open opening change turns a win
into a loss; the 2p and 6p Recharged/sealed changes turn losses into wins. The other
four cases keep the same win result. Three of those also have identical complete
terminal player summaries. These are outcome-selected, known-deal counterfactuals,
not fresh strength results or hindsight training labels. Opponent reactions are
allowed to change after the intervention; all later learner actions use the same
filtered policy rather than replaying a different trajectory's moves.

**Next:** test opponent-model mismatch using sampled public worlds, not actual
future decks. On the same seven fixed roots and the same original candidate pair,
compare the current equal opponent mixture with continuations using the frozen
arena reference policy (search_geo16, or heuristic for the 3p case), including
policy-consistent inferred sealed bids. This is a diagnostic use of known arena
roles, not a deployable policy that knows opponents' identities. Preserve the
model, candidate pair, sampled-world seeds and full horizons; keep the existing
64-world results as the mixture reference. Build an isolated worker, verify control
parity/privacy and measure complete rollout runtime before admitting CPU HF jobs;
nested reference search may be costly. Do not fit a rule switch or confidence
threshold to these seven examples. The separate resource ablation remains unlaunched.
No policy changed, no HF jobs launched, no gradients or final seeds used. The archive
collector completed once and must not be rerun.

**Previous — 24 October: exact auction replays and holdout-world diagnostic complete.**
Fourteen replayed games (seven fixed adverse/improved pairs) match their saved
outcomes exactly: **7,083 root moves, 1,908 learner decisions**, all legal moves,
model proposals, search seeds and public-state/economy trace checks passed.
All 1,463 frozen runtime files are unchanged. Replays are complete, session **19372**
exited 0. Evidence: `strong/population-auction-regression-replays-evidence-v1.json`,
private HF revision `b51a1f40428adc6d83da9e4341165e7b8c8378bb`.

At all seven first-divergence positions, a fixed-action audit expanded from 8 to
64 sampled worlds: **2,304 terminal continuations, zero caps**, with every original
candidate's first eight outcomes and opponent roles/beliefs reproduced exactly.
It compared the originally chosen action against the original model action on
the remaining 56 worlds, without reselecting those actions. **Three of seven
advantages changed sign**, including two examples where the complete hybrid game
had improved. The 4p original/open regression's opening advantage remained +0.125;
the 5p Recharged/open example went +0.3125→−0.0893. These are conditional simulated
credit differences, not win-rate improvements or causes of the complete game result.
Session **71292** exited 0. Evidence: `strong/auction-world-generalization-evidence-v1.json`,
private HF revision `467a2250d6343e20a58eb365baa0798c88294fc5`.

**Next:** run fixed one-action counterfactuals for all seven saved first-divergence
roots. Baseline control must reproduce the original filtered-model game; change
only the first differing action in the paired branch, then use the same filtered
model for all later learner decisions against unchanged actual arena opponents.
Preserve the original deal/seat/rules and hidden engine state, but keep hidden bids
and deck out of policy requests. This isolates an action's effect within a known
deal; it is still diagnostic, not fresh strength. No threshold/rule routing should
be fitted to these seven outcome-selected examples. No policy change, new HF job,
training, candidate selection or final seed use occurred in these diagnostics.
Both archive uploads completed; do not rerun their one-shot collectors.

**Previous — 24 October, 21:27 UTC: all 8,400 hybrid-screen games verified and archived.**
The fixed coordinator finished successfully: **135/135 batches**, zero game or
rollout caps. Session **5513** exited 0; do not restart it or either recovery launcher.
The unchanged full comparator reproduced exactly and all 17,797 evidence files
were archived and verified at private HF revision
`91076fb5f4cffed75bf2ddd22f70f3442f78c00d`. The one-shot archive helper has completed;
do not rerun its upload. See [the complete review](HYBRID-SCREEN-2026-10-24.md) and
`strong/population-hybrid-development-review-v1.json`.

Auction search improves the search-opponent overall point estimate at every count:
2p **62.5→78.1%**, 3p **41.7→66.7%**, 4p **50.0→53.1%**, 5p **47.5→50.0%**,
6p **45.8→58.3%**. Four-player Recharged sealed improves **43.8→68.8%**.
However, 4p original/open falls **81.25→31.25%**, 5p Recharged/open **70→50%**,
and 3p heuristic **100→85.42%**. Only four independent deals per cell: this is a
development screen, not confirmation or qualification. All adverse cells are retained.

**Decision:** keep frozen-1 plus the strict loss filter as the research reference;
investigate auction search's regressions before admitting larger fresh confirmation.
Do not advance this building/combined implementation: building loses to the filtered
model against search at every count, and combined loses to auction at every count.
Do not retrofit rule routing from these outcomes or distill the search wholesale.
9,977/18,813 auction changes had a simulated mean-credit margin of at most 1/8;
selection noise, opponent-model mismatch and future-policy approximation are hypotheses
to diagnose, not established causes. Start with exact replays of paired adverse games
and improved controls using the saved decisions. The resource ablation remains
unlaunched and needs its own runtime/source admission. No new jobs in this review.

This does not establish a training plateau; there is a promising auction direction
and specific failures to address. No candidate selected or final seeds used. The
exact-policy final integration requirements below still apply.

**Previous — 24 October: 133 batches verified; hybrid final integration remains separate.**
At 20:56 UTC the coordinator had **133/135 batches and 8,208/8,400 games verified**.
Only six-player auction/search_geo and combined/search_geo remain. Their 20:57
read-only HF checks reported RUNNING at 82/96 and 81/96 games, respectively, with
no errors, caps or truncations observed. Continue coordinator PID **2812975** /
session **5513** through the existing recovery adapter; no new experiment yet.

Final-tooling source inspection found that `launch-final.py` calls `arena-job.py`
and `evaluate.py`, which use the older engine search. They do **not** invoke
`PopulationPolicy`, its endgame filter, phase arms or balanced opponent worlds.
The old `search_scope` means `all` versus `recharged-sealed`, not auction/building.
Existing final technical receipts cover model-only inference (`search_samples=0`).
If a filter or hybrid is eventually selected, it needs an exact final-arena adapter,
policy identity/receipt checks, a frozen runtime and the full selected-policy 8840U
proof before reserved seeds can be used. Do not relabel the existing model-only
proof as hybrid qualification or map the hybrid arm to the old search-scope field.
The 20,160-game strength protocol and thresholds remain unchanged. This was a
read-only audit, not an integration test or selection; no final seeds were used.

**Previous — 24 October, 20:31 UTC: final archive helper prepared; 128 batches verified.**
The coordinator has **128/135 batches and 7,776/8,400 games verified**, including
the five-player combined/search batch. All 128 receipt identities were rechecked;
their summaries contain zero rollout caps. The seven outstanding jobs were freshly
confirmed RUNNING at 20:30 UTC, with no errors, caps or truncations in their last
200 log lines. The complete strength comparison is still pending.
Continue the same coordinator PID **2812975** / session **5513**; no new experiment.

`strong/archive-population-hybrid-development-v1.py` is ready for the completed
comparison. Without arguments it only reports readiness. With `--execute` it
requires `comparison_complete`, all 135 verified batches, unchanged frozen
dependencies, exact reproduction of the full comparison, and the pinned recovery
proof before archiving all raw results/decisions and uploading a verified HF archive.
The actual incomplete run was rejected before any archive or upload was created;
syntax/readiness checks pass and all 32 frozen dependencies remain unchanged.
**The completed-data archive path has not run yet.** After the coordinator finishes,
run it once with `--execute`; inspect any existing output/upload before retrying.
This helper does not launch jobs, select a policy or use final seeds.

**Previous — 24 October, 19:45 UTC: all 135 batches submitted; 107 verified.**
The fixed comparison now has **6,544/8,400 verified games**. Both exact recovery
jobs completed and passed full collection. The storage replacement also passed
the mandatory parity gate: all 79 previously completed games, 9,258 decisions and
the 14 saved decisions from the interrupted game match, excluding timing only.
An independent read-only comparison repeated these checks and verified the
original/replacement artifact manifests. All 32 frozen dependencies are unchanged.

Proof is archived in private HF revision
`dcde2edaa1ead7128f3dc9a5c0b36c18044f3400`; descriptor:
`strong/population-hybrid-recovery-completion-evidence-v1.json`.
The collector is one-shot: do not rerun its upload after an existing outcome.
Continue the same coordinator PID **2812975** / session **5513** through the
storage-recovery adapter. All planned guards are present, so no further grid
submissions are needed. Remaining jobs and collection continue. Full comparison,
policy selection and final qualification remain outstanding; final seeds are unused.

**Previous execution checkpoint — 24 October, 19:03 UTC: 50/135 batches verified.**
The fixed hybrid comparison has 2,880 verified games out of 8,400, with zero
rollout caps in those batches. All 50 saved receipt identities and all 32 frozen
dependencies were rechecked. Of 82 submitted batches, HF reported 31 still
RUNNING and one further COMPLETED batch awaiting collection. No additional
terminal failures were found. These are execution counts, not partial strength
results; the complete comparison is still required.

The sole coordinator remains PID **2812975** / session **5513**, using the
storage-recovery adapter below. Both exact replacements remain outstanding;
the storage replacement's repeated-game parity check is still pending. Existing
jobs and planned submissions continue. Do not start another experiment or use
final qualification seeds. Persistent receipt/status checkpoint:
`strong/population-hybrid-50-batch-checkpoint-v1.json`.

**Previous: read-only monitor now records individual game errors before job termination.**
`strong/inspect-population-hybrid-runtime-v1.py` now retains explicit episode/error
events separately from authoritative HF job status. Four tests pass, including
the original 79-game storage-failure log. Live scan at 2026-10-24T17:58:37 UTC:
all 32 inspected jobs RUNNING; no game errors, caps or truncations observed in the
last 200 log lines per job. This bounded scan does not certify the entire run.
All 32 frozen experiment dependencies remain unchanged. No jobs launched by this
monitoring change. Evidence: `strong/population-hybrid-game-error-observer-evidence-v1.json`.
Continue the existing parity-gated coordinator PID 2812975 / session 5513 below.

**Previous: a second terminal failure recovered; use the parity-gated coordinator.**
Five-player auction/economic job `6adcdcf81e112550ce7e17d3` ended ERROR after
79/80 games with `OSError: [Errno 28] No space left on device` for episode 36.
The original partial archive is preserved at HF revision
`20afd14932631ee54be6bf27b5bc5ae312bf3eb8`. Its 9,258 completed-game decision
receipts and 14 saved decisions from the failed game pass consistency checks.
The full cell remains unusable; the specific storage resource is unknown.

Replacement `6adcee5f046eb82b1ecde67f` reruns all 80 games with identical source,
model, seeds, hardware and budgets. Five recovery tests passed. Other 70 existing
guards and all 32 frozen experiment dependencies are unchanged. Before accepting
the replacement, the coordinator requires exact repeated-game/decision parity
with all saved originals, ignoring only elapsed times and time-dependent receipt
hashes. That actual replacement parity check is **pending**.

Active coordinator: PID **2812975**, session **5513**, launched through
`strong/recover-population-hybrid-storage-v1.py coordinate --execute`.
At 2026-10-24T17:44:23 UTC: **72 submitted / 40 verified**, no failed jobs.
PID 2740649 / session 65141 stopped on this failure and is no longer active.
Do not start the original coordinator directly: this adapter adds the mandatory
parity gate. Do not rerun either one-shot replacement launcher or edit the active
adapter. Continue the fixed comparison; no new experiment or final qualification.
Evidence: `strong/population-hybrid-storage-failure-evidence-v1.json`,
`strong/population-hybrid-storage-recovery-evidence-v1.json`; admission:
`strong/population-hybrid-storage-recovery-admission-v1.json`.

**Previous: one confirmed no-start failure replaced exactly; fixed comparison resumed.**
HF job `6adce697046eb82b1ecde31d` (auction / 4p / legacy) ended ERROR with
exit code 6, no reported start time and no application logs. Its underlying cause
is unknown. Original status, logs, guard and stopped coordinator were archived;
the result archive was absent. The other 31 unverified handles were checked and
had no additional terminal failures. No partial outcomes were used.

The single replacement, `6adceba41e112550ce7e21fa`, uses exactly the same source,
model, seeds, hardware, timeout and search settings. Its canonical guard records
the original failure lineage; the other 69 original guards remain unchanged.
Four recovery tests passed. The unchanged coordinator resumed as PID **2740649**,
session **65141**. At 2026-10-24T17:32:42 UTC: **71 submitted / 39 verified**,
no failed jobs. This includes one further submission from the original fixed grid.

Evidence: `strong/population-hybrid-prestart-failure-evidence-v1.json` and
`strong/population-hybrid-prestart-recovery-evidence-v1.json`; admission:
`strong/population-hybrid-prestart-recovery-admission-v1.json`. The recovery helper
is one-shot and must not be rerun. Continue the resumed coordinator and existing
jobs. The 8,400-game comparison remains incomplete; source and protocol are frozen.
Do not start the prepared resource experiment yet. No final seeds or qualification.

**Previous: broader live check and conditional timeout partition verified; no recovery launched at that checkpoint.**
The 16:59 UTC snapshot inspected 30 running jobs, with zero caps in their completed
game logs; four newly launched jobs were separately confirmed running at 17:01.
Five-player combined/search_geo also shows runtime risk: 19/80 games after 10,654s,
alongside six-player 25/96. Their crude rate projections exceed 9h, but are neither
ETAs nor terminal failures. Coordinator PID 1447977 / session 53211 remains active:
2026-10-24T17:05:36 UTC, 66 submitted / 34 verified, no failed jobs.

`strong/hybrid_timeout_partition_v1.py` specifies a possible whole-deal split only
after a confirmed terminal timeout, stopped coordinator, preserved/reviewed failure
and artifact check. It has **no launch, collection or comparator implementation**.
Six tests verify exact coverage of all 8,400 original games and reject live/unknown
jobs, changed source/protocol, repeated replacement and incomplete review. Real
read-only checks reject both currently running 5p/6p jobs; no admission created.

Evidence: `strong/population-hybrid-timeout-partition-evidence-v1.json`, 46 archived
entries, private HF revision `44551e4bfff0f4e62430ff487cc580d8a4f778cd`. Continue existing
jobs/coordinator. If a real timeout occurs, preserve its evidence and inspect saved
artifacts before implementing any reviewed recovery; retain original guards and
require every replacement child in the complete comparison. This preparation
launched no recovery jobs/games and changed no running source. The existing
coordinator continues its original grid; no candidate or final qualification.

**Previous: live combined-search runtime risk observed; existing jobs continue.**
Read-only HF checks at 2026-10-24T16:47 UTC confirm combined6psearch RUNNING,
25/96 games completed after 9,978s, with zero caps in those completed games.
Its 20-frame CPU sample has a 40% median after the initial frame, about 4.8GB/32GB
RAM, eight allocated vCPUs. Combined6prush is RUNNING at 42/96; building6psearch
is COMPLETED at 96/96. The slow completed-game rate flags potential overrun of the
nine-hour job budget; it is not a reliable ETA, a stall, or a terminal failure.

Snapshot: `strong/population-hybrid-runtime-observation-v1.json`; observer:
`strong/inspect-population-hybrid-runtime-v1.py` (read-only, bounded metrics).
Do not infer why CPU use is lower from this short sample. No exposed job SSH or
supported installed-SDK timeout extension was found. No remote changes were made.
Continue/recheck existing handles and coordinator PID 1447977 / session 53211.
Retain any actual failure before deliberately planning a replacement with the
same games/policy; never restart from a projection or quiet logs. Future resource
runtime admission must not reuse the old endpoint estimate. This is execution
evidence, not evidence of a strength plateau. No new experiment, candidate or
qualification; all frozen dependencies/final seeds remain unchanged.

**Previous: resource ablation preregistered and result checker verified; no jobs launched.**
`strong/resource-replanning-development-protocol-v1.json` fixes filter versus
resource-filter on 3,360 fresh paired games: 27 count/opponent cells, Germany 2–6,
four original/Recharged × open/sealed rules, every seat, four independent deals,
eight balanced search worlds. This isolates resource replanning; combining it
with auction/building search needs later evidence. The protocol is not runtime
admitted and cannot launch anything itself. Finish the active 8,400-game comparison
first, review it, then package and run new resource-specific endpoint pilots before
choosing job hardware/timeout. Do not reuse the old search runtime admission.

`strong/resource_policy_verification_v1.py` checks actual atomic execution against
the selected hypothetical plan, all candidate rollout receipts, shared worlds,
cash/inventory consistency, terminal tie credits, means, choices and caps. Its
private adapter preserves the existing whole-game pairing/hash/winner checks.
Eleven tests pass: 652 existing resource-policy decisions / 11,900 rollouts, 80
unchanged full controls / 10,207 decisions, corrupt receipts/reports, cap rejection
and all legal shard partitions. No new resource strength evidence is claimed.

Evidence: `strong/resource-development-preflight-evidence-v1.json`, 243 archived
entries, private HF revision `915e442bbaf540a10d0593eeed42798157047200`. All local work
completed. No new games, HF jobs or gradients. Sole coordinator PID 1447977 / session
53211 remains live; snapshot 2026-10-24T16:34:50 UTC: 61 submitted / 29 verified,
no failed jobs. Combined6psearch was directly confirmed RUNNING. Source/model and
active screen remain unchanged; no candidate or final qualification.

**Previous: resource-search timing and exact parity verified on the actual 8840U.**
The four saved slow resource positions completed under three execution settings:
12 searches / 672 rollouts on each machine, zero caps, identical original decisions,
sampled worlds and terminal outcomes across local HX370 and target AMD 8840U.
With four ONNX threads and four engine workers, target times were 9.341s (2p
original/open), 2.519s (2p Recharged/sealed), 3.733s (6p original/open), and 2.277s
(6p Recharged/sealed). One-thread/one-worker times were 17.352/4.144/6.509/3.478s.
These are four-world stress positions, not representative latency or strength.

Passive timing finds both prediction (array packing + ONNX) and engine/IPC costs
material. More JS workers alone gives only a modest improvement; extra inference
threads help on this target. No runtime defaults, model or search behavior changed.
Do not infer that a Rust rewrite alone solves the latency. Prefer model-only for
instant feedback, with selective search considered for bot jobs/analysis only if
the fixed strength comparison supports it; whole-turn search also remains a
potential training teacher. Do not start another optimization or strength sweep
before the existing frozen comparison finishes.

Evidence: `strong/resource-replanning-8840u-evidence-v1.json`, 15 archive entries,
private HF revision `2f6051a13a666ffa5cd94914bc1f866b819791a4`. Target PID 2929509,
local run and archive process are completed. No HF jobs or gradients launched by
this benchmark. Sole screen coordinator PID 1447977 / session 53211 remains active:
2026-10-24T16:24:29 UTC, 56 submitted / 24 verified, no failed jobs. All screen
dependencies remain frozen; final qualification seeds are unused.

**Previous: stateless atomic resource replanning verified, with a material latency finding.**
The separate `strong/resource_replanning_policy_v1.py` returns one move and replans
from the next public request. It holds no pending purchase plan. This matches the
existing research worker's atomic contract without platform storage, but differs
from committing the macro evaluated by resource-turn search. The four-world probe
changed an opening from two planned coal to four actual buys; the other 22 turns
matched their initial plans. The known late-game omission still buys three coal.

All 1,798 outside-resource controls match; 23 complete resource turns / 112 atomic
decisions / 4,744 rollouts passed. Fresh processes, interleaved requests, metadata
changes, cap fallback and standalone JSONL responses match. A verifier-only JSON
integer-key/string-key failure was preserved, diagnosed and fixed; no policy change.
Four predeclared full-game integration smokes passed with 7,156 rollouts and zero
caps. Independent replay matches 540 learner and 1,454 opponent moves and finals.
These are engineering checks, not fresh strength estimates.

Full games reveal much slower early decisions than late fixtures: the maximum
local HX370 resource decision was 21.4s at only four worlds / one search worker.
Four exact slow public roots are saved under `ai/runs/resource-replanning-v1/replays/`
for profiling and actual8840U checks. All local processes completed. Evidence:
`strong/resource-replanning-evidence-v1.json`, 51 archive files, private HF revision
`ac7034af7546d5d3ef7ecbc7b26075bce6ec5c31`. No new HF jobs or gradients; frozen
screen dependencies unchanged. Coordinator PID 1447977 / session 53211 continues:
2026-10-24T16:03:44 UTC, 49 submitted / 17 verified, no failed jobs; combined6psearch
was directly confirmed RUNNING. Finish the fixed grid; profile actual expensive
requests before deciding live search versus a training teacher, then evaluate any
adopted atomic policy on fresh paired games. No final candidate or final seeds used.

**Previous: whole-resource-turn search verified in isolation.**
The new worker scores complete purchase sequences against the same sampled public
worlds and balanced neural/economic/legacy/rush opponents. It retains the exact
model turn, including purchases outside the generated bundle family. Future
building follows the model with the existing strict loss filter; no construction
route is forced. The caller must commit the returned whole turn: independently
replanning each purchase would be a different policy and is not evaluated here.

All 755 resource positions passed baseline checks (2,251 actual model decisions).
Twenty-three fixed engineering searches completed 1,232 rollouts, plus 464 control
rollouts, with no normal caps. Hidden-data, worker partition and sample-prefix
checks pass; a deliberate one-step cap falls back to the full model plan. The known
fuel omission now selects three coal costing 17 from public-world search, but that
outcome-selected example and the four-world probes are not strength evidence.

Evidence: `strong/resource-turn-search-evidence-v1.json`, 25 verified archived files,
private HF revision `ec76db0d6fe37a4fd94aa620e86ba9a06f35939c`. No jobs or gradients
launched for this work. All original 1,463 source files and running-screen hashes
remain unchanged. The existing coordinator continues: at 2026-10-24T15:38:03 UTC,
44 submitted / 12 verified, no failed jobs. Next: verify an arena/serving execution
contract for complete plans (or separately specify and test replanning), then use
fresh paired games after the current fixed comparison. Resource teacher labels
are another use. No final qualification or publication; final seeds unused.

**Previous: public resource-turn proposals verified and archived, not integrated.**
The isolated `strong/resource-turn-plans-v1.cjs` enumerates legal fuel bundles and
annotates them with affordable construction routes. All 7,185 bundles at 755
resource positions passed 28,177 real-engine purchases across 2–6 players and all
four rules. Forty-one construction cases passed, including recovery of the known
three-coal omission as a proposal. This does not select or score a move, account
for intervening opponents, prove an optimal route, or establish a strength gain.

Evidence: `strong/resource-turn-proposal-evidence-v1.json`, 58 files archived and
download-verified at private HF revision `6c366e1a9f6230099e0af40d22ad2be7cb2ce1b8`.
Initial fusion-plant guard failure and premature-copy startup failure are retained;
the corrected complete package passed. All 1,463 frozen source files and active
screen dependencies are unchanged. No new jobs or gradients for this prototype.

Next: keep the running five-arm comparison frozen. A separate resource-search
adapter must include the existing model's complete resource turn as a candidate,
then compare whole bundles against public sampled worlds and varied opponent
continuations. Use fresh paired games before adoption. Coordinator PID 1447977 /
session 53211 remains active: 2026-10-24T15:22:39.465618+00:00, 40 submitted / 8
verified, no failures. No candidate qualified; reserved final seeds unused.

**Previous: resource-planning failure reproduced and causally checked.**
The complete 33,600-game model-only grid now has a verified terminal-economy
analysis retaining every model/cell/rule. In two-player Recharged/open, frozen-1
has unused nominal output in 9/21 losses (parent: 4/19). In six-player
Recharged/sealed, 53/73 losses have fewer cities than the winner powers; categories
overlap and these are descriptive development counts.

Four selected full replays match exactly. In the two-player example, frozen-1
passes resources with 239 cash, 10 coal still available and fuel for 18 cities, then
builds 21. Buying three more coal for 17 changes that selected loss to a win:
21 powered / 61 cash versus 21 / 58, with the original full trace and 326-move prefix
verified. The selected six-player parent/current traces are identical, showing an
inherited city-growth weakness, not a new regression. These reused, outcome-selected
branches are not strength estimates or training labels.

Evidence: `strong/weak-cell-economy-evidence-v1.json` (57 files); all local analysis,
replay and intervention processes completed. The latest fine-tuning roots and
current hybrid scopes cover auctions/building; consider a separately frozen
resource-planning experiment after the unchanged full screen. Do not hard-code the
three-coal intervention or promote it from one example. No gradients or HF jobs
were launched for this diagnosis. Existing coordinator PID 1447977 / session 53211
continues: 2026-10-24T15:02:20.384283+00:00, 40 submitted/8 verified, no failures.
Final seeds remain unused; no candidate or AI publication.

**Previous: asynchronous sealed-bid serving gap reproduced and repaired in isolation.**
The frozen adapter rejects legal requests when a bidder acts before the first pending
seat or when earlier submissions are not a prefix of player order. The current BGS
source can dispatch such a bot. The research/current engines accept all 446 reproduced
cases. A separately versioned belief module now handles them, preserving all 2,553
canonical preparations exactly. Checks cover 640 pending-subset/actor combinations,
2,172 actual-model/filter decisions and 18 full searches / 840 rollouts, zero caps.
Canonical searches, hidden-data perturbation and worker partition controls match.
All 1,463 original source files and running-screen dependencies remain unchanged.

This is an isolated research repair, not a BGS change or strength result. For missing
submission history it assumes committed bidders acted in their public order; the real
order is unknown. It preserves true player/auction order. Evidence and the repair are
archived in `strong/live-sealed-order-evidence-v2.json` (69 files). Do not overwrite
frozen screen code. The sole coordinator remains PID 1447977 / session 53211; latest
snapshot 2026-10-24T14:41:49.409272+00:00: 33 submitted, 1 verified, no failed jobs.
Finish the complete fixed grid before selection; separately pin/test any later use
of the new adapter, including asynchronous-order strength and actual-target serving.
No HF jobs, gradients or final seeds were used for this repair; the existing
coordinator automatically filled a slot as the first shard completed.

**Previous: current engine 2.0.17 compatibility passed; hybrid grid continues.**
An isolated build of fetched master 537e41e matches the active research engine on
2,553 positions, 7,659 feature checks, 2,553 sampled public-information worlds,
32,770 action transitions, 2,553 default-bot steps and 80 complete Germany games
/ 40,464 transitions. All 1,463 frozen source files were independently rechecked.
The production checkout and live evaluation code remain unchanged. This covers
automatic standard-deck Germany with 2–6 players / all four rules, with documented metadata
exclusions; it does not certify alternate decks, other maps or platform transport.
Evidence: `strong/production-engine-compatibility-v2.json` (1,244 archived files).
At 14:16:22 UTC coordinator PID 1447977 / session 53211 is confirmed alive: 32 jobs
submitted, zero fully collected shards, no failures. Keep that same coordinator;
no new jobs or gradients this turn. Full strength comparison is still pending.

**Previous: both runtime pilots verified; 8,400-game hybrid screen running.**
The six-player pilot finished in 47.7 minutes: 24 games, 53,312 rollouts, zero caps,
all decision/terminal receipts independently verified. Together the endpoint
pilots cover 32 games / 74,008 rollouts. Neither enters strength estimates. A separate
12-game A260 callback/nonzero-offset compatibility check also passed.

The fixed source and plan are now published: 135 four-deal shards, five arms,
27 opponent/count cells, all seats/rules, 1,680 games per arm. Measured admission
uses cpu-upgrade / 8 game processes / 9h timeout and at most 32 live jobs. All 32 initial
jobs were checked through HF and are RUNNING. **Sole active coordinator:
PID 1447977 / session 53211**, state/log under
`ai/runs/population-hybrid-development-coordinator-v1`. It polls every 300 seconds,
fills slots and independently collects the whole grid. Do not launch duplicates,
edit frozen dependencies or retry failures automatically. Inspect the existing
handles; quiet output does not mean a stopped job. Evidence:
`strong/population-hybrid-development-launch-evidence-v1.json` (185 verified files).
Source/plan and exact continuation instructions are in the latest handoff.
No hybrid strength result, final selection or qualification is established yet.

**Previous: current population hybrid passes actual AMD8840U parity and timing.**
All 5,106 model/filter decisions and eight endpoint searches match the local
reference exactly; 384 rollouts, no caps. Four-thread/four-worker search takes
2.9–6.2s on the four existing Recharged/sealed auction/building positions; this
is a small engineering sample, not gameplay latency or strength evidence.
Model/filter median is about 5.4/5.7ms. Target PID2927472 completed and is fully
collected; do not restart it. The initial local receipt-key mismatch, corrected
package and raw results are archived in `strong/population-policy-8840u-evidence-v2.json`.
No new HF jobs this turn. Six-player runtime pilot `6adcad7b046eb82b1ecdc9cd`
remains RUNNING at 13:48 UTC, latest progress22/24 with zero reported caps.
Collect that same job, then freeze/inspect the prepared plan and launch its
single coordinator. The 8,400-game hybrid strength grid is still not launched.
See the latest handoff; final qualification and reserved seeds remain untouched.

**Previous: two-player hybrid runtime verified; fixed strength screen prepared.**
The two-player pilot completed: eight games, 20,696 full rollouts, zero caps,
498.465 seconds. Every saved decision and terminal result independently verifies.
The six-player job `6adcad7b046eb82b1ecdc9cd` is still RUNNING at 13:34:43 UTC;
13/24 games appear in the latest log. Inspect/collect that same handle with
`strong/collect-population-hybrid-runtime.py 6`; never restart it on quiet logs.
No new jobs this turn. Fourteen tests and clean-package initialization pass.
The new immutable source package preserves all 1,453 runtime base files.
The 8,400-game hybrid screen is not launched: collect/verify the six-player pilot,
then run `strong/build-population-hybrid-development-source.py freeze` to derive
the measured timeout, publish source and create the fixed plan. Review its dry
run, then use the single lock-protected coordinator (at most 32 live CPU jobs,
no automatic retries). See the latest handoff for commands and exact provenance.
All prepared code, tests, runtime receipts and the source archive are preserved
in `strong/population-hybrid-development-preparation-evidence-v1.json`.
No hybrid strength gain or final qualification has been claimed.

**Previous: all 33,600 development games are verified; two hybrid CPU pilots launched.**
Recovery PID 402796 completed and exited; do not restart it. All four trained
ensembles improve overall search results at 3p/4p to varying degrees. Frozen-1
also improves 5p/6p overall and becomes the single development base, not a final
candidate. Its search shares at 2–6p are 52.73 / 44.79 / 51.56 / 45.31 / 45.31%.
2p Recharged/open, 4p default and 6p Recharged/sealed remain unresolved; retain
all adverse cells. Full comparison and decision are under `strong/policy-iteration-development-*v2.json`.

New isolated model/filter/auction/building/combined arms pass four worker tests,
all 2,553 fixtures, 80 exact control games / 10,207 model decisions, and actual
trained search/partition/cap checks. The unchanged engine plus new source is
pinned. Two `cpu-upgrade` runtime pilots against search_geo are RUNNING:
2p `6adcad711e112550ce7dfe8d`, 6p `6adcad7b046eb82b1ecdc9cd`; timeout 6h.
Inspect those same HF handles. These are runtime pilots, not strength games.
The fixed 8,400-game initial hybrid screen is **not launched**. Collect and verify
both pilot archives, set measured runtime/resource admission, then proceed with
the fixed paired screen. See the latest handoff for paths and exact next actions.
The first two pilots failed before evaluation because the clean package lacked
`ai/runs`; v2 creates parent directories and passes a clean-package startup check.
Failure guards/logs are retained. Evidence: `strong/population-hybrid-runtime-launch-evidence-v2.json`
(repair and replacement handles) plus v1 (full controls/preflight).

**Previous: broader hybrid opponent continuations pass actual-model integration.**
The isolated worker adds legacy, rush and mixed-population opponents, with
shared sampled worlds and policy-consistent sealed bids. Five contract tests and
60 actual-model cases / 480 complete rollouts pass with zero caps. All five
models are retained. This is engineering validation, not fresh strength evidence;
weights are uncalibrated and no serving/search default changed. Source, both
failed/repaired test versions and raw outputs are archived in
`strong/population-hybrid-continuations-evidence-v1.json`. The probe is complete.
At 12:39:55 UTC only three six-player search shards remain: frozen arms are fully
collected, public-0 106/108, public-1 107/108. Keep recovery PID 402796 as sole
collector/comparator and finish the full grid before candidate selection or a
fresh hybrid experiment. See the latest handoff for exact provenance and limits.

**Previous: endgame counterfactuals complete; filter stays experimental.** All
56 single-decision branches finish, with 28 byte-identical original controls.
Always delaying the threshold build gains six and loses five selected outcomes.
A narrower strict fuel-output-loss certificate matches eight cases (four recovered
wins, four unchanged losses), with 26,772 exact root-move checks and the full
2,553-position serving fixture probe. It is not integrated into serving/evaluation,
and these outcome-selected examples are not a strength estimate. See
`strong/policy-iteration-endgame-diagnosis-evidence-v1.json` and the latest handoff.
At that earlier snapshot, 16 six-player search shards remained (416/432 shards
collected); the latest status is above. Keep the live recovery coordinator and complete the
full comparison before selection or a fresh hybrid study.

**Previous: four-player search gains are independently verified.** In the
new 25-cell complete subset (30,080 games, 16 deals/cell), frozen-1 rises from
30.86% to 51.56% overall against search and from 15.63% to 39.06% in Recharged
sealed. Candidate search is still off. All four models, adverse cells and rule
views remain; five-/six-player search are pending. Four-player legacy remains
below the 90% point floor for every model. No selection or qualification.
See `strong/policy-iteration-interim-complete-cells-evidence-v2.json`.

**Fuel-market/endgame failures are reproduced.** All 49 fixed diagnostic games
replay exactly with both observers; the enhanced observer records every root
move and verifies state continuity. One loss builds to 19 cities with capacity
16 but fuel for 10 because coal is already sold out. Plan realistic resource-
consuming opponent continuations and inspect resource policy/endgame timing
before scaling hybrid samples. Selected examples are not prevalence estimates
or causal interventions. Evidence: `strong/policy-iteration-terminal-economy-evidence-v1.json`.
All diagnostic processes are complete and archived. Keep the one live recovery
coordinator; finish the full comparison before further training or selection.

**New complete-cell evidence shows substantial three-player gains.** Against
search, frozen-0/frozen-1 rise from the parent's 20.31% win share to 40.10%/44.79%;
against a260 they rise from 34.38% to 48.44%/46.35%. This contradicts a blanket
plateau interpretation of the small validation metric. However, two-player search
remains inconclusive, and five-player legacy/default regresses from 94.06% to
83.75%/90.62% for those variants. All four ensembles, adverse rule views and all
19 cells complete in all five arms are retained. This is an interim diagnosis
(21,120 games, 16 independent deals/cell), not the full comparison or selection.
Four–six-player search cells remain pending in that snapshot. Evidence:
`strong/policy-iteration-interim-complete-cells-evidence-v1.json`.

Validation simulation gains are small: +0.192 / +0.386 pp for frozen ensembles,
+0.325 / +0.171 pp for public ensembles. All frozen seeds peaked at epoch 10;
public epochs are 35, 5, 5, 60. These deals selected the checkpoints. They do not
establish real-game gains. Finish the planned game comparison; do not automatically
extend training. See `strong/policy-iteration-training-results-v2.json`.

The independent verifier's JSON player-key mismatch was fixed with four regression
tests. Both actual trained integrations passed, without changing weights or
training jobs. Failure records and repair evidence are archived. The collector
completed. The original development coordinator PID 71261 stopped on ten HF
artifact-upload HTTP429 errors after all 432 candidate jobs were submitted.
The **only active development coordinator is recovery PID 402796 / session 78444**.
State: `ai/runs/policy-iteration-development-recovered-v1/state.json`. It owns
collection plus exactly ten reviewed replacements, at most two in flight.
All original failed handles/guards/logs are preserved; do not duplicate collection
or submit replacements manually. Frozen evaluation dependencies remain unchanged.
See `strong/policy-iteration-development-recovery-evidence-v1.json` and the
latest handoff section. No result is assumed for the failed uploads.

Trained packages/results are archived at
`strong/policy-iteration-trained-8840u-evidence-v2.json`. The target process is
complete. All twelve actual trained technical receipts are also archived in
`strong/policy-iteration-final-technical-evidence-v2.json`; the reserved final
gate remains untouched. Source or serving checks do not establish qualification.

The actual trained hybrid prototype now passes 40 searches / 2,160 complete
simulations, with zero caps, on four endpoint Recharged/sealed bid/building
fixtures. Inference checks span all 80 count/rule/phase cells per model. At eight
worlds per mode, trained request times on the local HX370 are 11–18s for two-player
cases and 30–35s for six-player cases. This is neither target8840U timing nor
fresh strength evidence. Source and raw outcomes are archived in
`strong/trained-hybrid-probe-evidence-v2.json`. The cost profile is now complete (below); retain the existing full-game comparison
as the strength checkpoint.
The prior synthetic cap failure and first frozen-source admission rejection are
preserved separately. No active pipeline dependency was changed for this probe.

Actual 8840U hybrid profiling is **COMPLETE**: the existing public-0 six-player
case takes 34.616–34.949s at one ORT thread, 19.484–19.541s at four (1.783x mean
speedup). All internal decisions and terminal outcomes match the local profile;
zero caps. This is one repeated fixture, not fresh strength or a latency
distribution. No default changed. Evidence and standalone package are archived
in `strong/trained-hybrid-8840u-evidence-v2.json`. The first attempt's unnecessary
HF-client dependency was removed from the profiler; its failure is preserved.
Target PID 2925814 / SSH session 73745 completed; do not restart it.

At the archived recovery snapshot, 357/432 candidate shards and 21,600/26,880
candidate games are verified. The first two replacements completed; the live
recovery owns the remaining eight and all collection. See
`strong/policy-iteration-development-recovery-active-evidence-v1.json`. No
partial win-rate ranking or selection is made. Finish the same full comparison.

The bounded packing experiment is complete: all checked moves and internal
search traces match, but packed16 saves only 6.94% elapsed time on one repeated
HX370 fixture (packed8: 2.07%). No default change or target benchmark. Source and
raw evidence are in `strong/hybrid-batch-packing-evidence-v1.json`. Keep it
experimental; prioritize the full strength comparison.

## Previous hybrid profile and development progress

The repeated trained six-player fixture takes 34.15–35.61s at one ORT thread
and 22.79–23.54s at four threads on the local HX370 (1.506x mean speedup).
Every internal neural choice and terminal outcome matches; zero caps. At one
thread ONNX inference is about 71% of total time. Only 24.3% of padded action
slots are legal actions. The completed packing experiment below found only modest local savings,
so further optimization is lower priority than the strength comparison.
No default changed; no target8840U hybrid benchmark or fresh strength claim.
Evidence: `strong/trained-hybrid-profile-evidence-v1.json`, remotely archived.
The profile process completed; do not relaunch into its existing output directory.

At the 2026-10-24T11:04:58.294716+00:00 snapshot, all four candidate grids are submitted: 108 shards per model, 432 unique jobs / 26,880 candidate games, plus the completed 6,720-game parent reference. All four launch evidence archives are remotely verified. All eight runtime probes passed. The only coordinator remains PID 71261 / session 77604, now collecting the development results; its 39 dependencies are unchanged. Do not duplicate submission or collection. No candidate is selected and final seeds remain unused.

## User steering, 24 October: diminishing returns and hybrid play

The user asks to be told candidly when further work has diminishing returns,
and asks whether hybrid search/AI is the right direction after the fresh4p
parent result. This is not a pause. Judge progress by fresh complete-game
strength and target latency, not numbers of generated labels or jobs.

The complete older3–6p terminal audit is now saved in
`strong/multiplayer-search-terminal-analysis-v1.json`, reproducible with
`strong/analyze-multiplayer-search-outcomes.py --output NEW_PATH`. All12
model/count cells, raw hashes/provenance and existing paired win summaries were
rechecked; no new games. For10102 at6p Recharged/open, search changes58.33% wins
to33.33% (paired−25pp, exploratory95% interval−35.42 to−14.58), with18 wins lost
and6 losses converted to wins. It ends with2.1667 fewer cities,1.8958 fewer
powered cities and10.0625 more cash on average. At5p Recharged/open the win
change is also−25pp and cities−2.35, but cash falls14.675. Thus neither sealed
belief correction alone nor a universal spending rule addresses this evidence.
Terminal states do not identify the causal phase. In a follow-up hybrid study,
retain5–6p open cases and distinguish auction-only/building-only/combined search
with realistic continuations before increasing budget or choosing phase gates.
This is a diagnostic recommendation, not a new launched experiment. All
intervals use8 independent older deals; they are not final-test evidence.

Recommendation: finish the already running policy-iteration round, then compare
its model-only agent with a bounded hybrid on fresh development deals. Keep
the current frozen model-only protocol and its single development coordinator unchanged.
The quoted30.86% overall /15.625% Recharged-sealed4p results have candidate
search OFF. Current training learns from search continuations; it does not
perform search when making a deployed move.

Hybrid is already supported by preliminary evidence, not a wholly new idea:
the earlier10102 paired search-transfer experiment against search_geo raised
4p share24.21875% to35.15625%, but lowered6p38.54167% to29.16667%.
Each had only8 independent deals. Auction-only3p raised20.83333% to43.75%
(paired gain22.91667pp, exploratory95% deal interval9.375–36.45833).
These use older development deals and cannot be compared directly to the
current30.86% reference. Reports: `strong/multiplayer-search-transfer-results-v1.json`
and `strong/phase-search-ablation-results-v1.json`.

The old hybrid adds the neural proposal to a heuristic shortlist and rolls out
heuristic/economic continuations. It is not a fully neural policy/value tree
search. Its10102 actual8840U probe measured60 searched positions: median1.113s,
p952.064s, max2.346s at48 samples. This supports job-based feasibility only
for that implementation, not latency promises for neural continuations.
Report: `strong/search-transfer-8840u-probe-v1.json`.

A follow-up should compare raw neural, independent search, and hybrid at
measured compute budgets, with all counts/rules retained. Prioritize auctions
and building; use policy-consistent hidden-bid beliefs (including passes),
public balances and plausible opponent-policy mixtures. Do not replay hidden
bids or hidden deck order. The learned value head is not yet calibrated for
truncated search; validate it before substituting it for complete outcomes.
More search alone is not an answer to inaccurate rollout/opponent models.
If completed training and a bounded hybrid comparison fail to produce useful
fresh gains, recommend changing approach or stopping this line instead of
automatically scaling another training round. No hybrid jobs were launched
and no active protocol, final threshold or reserved seed was changed here.

- **Labels and parent baseline COMPLETE:** all 948 new plus 60 pilot shards,
  17,280 roots; all 108 baseline batches / 6,720 games / 27 cells verified.
- **Training and independent collection COMPLETE:** all four candidate pins are
  in `strong/policy-iteration-development-pins-v2/`. No seed cherry-picking.
- **Trained 8840U benchmark COMPLETE:** reports and standalone packages are
  archived; the target process ended normally. Do not restart it.
- **Development recovery ACTIVE:** PID 402796 / session 78444. All four grids
  are submitted; exactly ten reviewed upload failures can be replaced once,
  two at a time. Collection and the 33,600-game comparison remain unchanged.
  No final test, selection or publication.
- **Final technical receipts COMPLETE:** all twelve records are prepared and
  archived. No candidate is selected, and no final game has run.
- **Next:** let the coordinator complete the game comparison, then make a candid
  stop/continue decision and pursue any justified bounded hybrid study.

---

## Historical pause snapshot — 10 October 2026

**Historical [paused handoff](HANDOFF-2026-10-10-PAUSED.md).**
The user explicitly paused research and prohibited new jobs. The Codex goal is
paused. No jobs or retries may be launched until the user resumes. Existing HF
jobs were left running and terminate on completion, failure or timeout.

At 18:38:44 UTC: 20 jobs running (6 label, 11 collection, 3 arena); two completed
cases awaiting independent verification. Labels: 13 pilot shards / 149,472
rollouts verified; 72 roots have both modes. Collection: 2,880 full games /
147,417 roots verified. The strict collection merger is now implemented and
preflight-checked on existing data, but no full 4–6p case has been merged.
The new strategic correction is implemented and untrained. No model is qualified,
no AI is deployed, and the reserved final seeds remain unused.

The handoff includes exact handles, timeouts, immutable pins, progress since the
beginning and the ordered recovery procedure. Its snapshot supersedes all older
active/pending/next instructions below. Those sections are preserved as history.

---

# Historical continuation notes — 10 October 2026

**No candidate has passed the full strength gate. Nothing is deployed. Reserved
final-test seeds remain unused.** The separate UI redesign was reverted.

Use `/home/eliheros/Documents/Codex/2026-09-26/je-x20-2/work/powergrid-ai`, branch
`ai/germany-baseline`. No UI work or publication is part of this AI continuation.

## Latest: first teacher labels verified; frozen-parent correction preflight passes

Previous goal turn: **progress** (balanced label jobs dispatched and five-player
search regression verified). This turn: **progress**. The production UI revert
remains complete and is separate from this work. The earlier AI work was committed
and pushed as `22700badf23ca0cbc9f1b30825828fd4ebec0c24`.

**Labels:** 12 of 20 pilot shards independently verified, 137,856 full paired
simulations, no caps. All 10 `neural_economic` cases and both 2p `neural` cases are
complete. The eight 3–6p `neural` jobs are authoritatively RUNNING on their original
handles; do not relaunch them. The three historical image-pull errors already have
completed, verified replacements. Raw revision for the original seven completed
shards: `73242585764795b390c3067a74666ce056cf5ef4`; the remaining five were collected
at `3d67c0f4735f16f0a6c7bd70c28ff85153ab3814`. Individual immutable pins and hashes:
`strong/strategic-teacher-training-results-v1.json` and each local
`runs/strategic-teacher-training-verified-v1/*/verified.json`.

Both continuation modes are available for only **48 two-player roots**, 24 train
and 24 validation. Equal-mixture choices selected on A gain 8.88 percentage points
on B over the parent on validation; reversing A/B gives 7.53 points. Choice
agreement is 66.7%. These are small, conditional simulation diagnostics, **not
whole-game win rates, confidence intervals or model qualification**. All roots
remain in the dataset, including weak/negative/uncertain labels. First partial
label evidence: revision `c4d264577f6e6db24fea4238a5d80031046e5c04`, prefix
`runs/strategic-teacher-training-first-partial-evidence-v1`.

The label launcher now accepts `--start N --end N+2` for the remaining 140 chunks,
but **requires all 20 independently verified pilot shards first**. It uses the
slowest observed same-count/source/mode root, 2x margin and 25% timeout headroom.
Invalid ranges and incomplete-pilot admission were explicitly rejected. Future
chunks use the smaller Python CPU image and run all 2,553 serving parity checks
before labeling. No continuation chunks have been launched yet; first-wave guards
remain unchanged.

**Collection:** 2,880 full unique games / 5,760 twin executions and 147,417 roots
verified. The new 3p/search collection has 192 games and 10,451 roots, source raw
revision `73242585764795b390c3067a74666ce056cf5ef4`. All 15 collection probes are
verified (240 games / 12,208 roots). The 6p/search probe took 3,031.438s; raw revision
`6c1a9c14abbadd1f8051c83dc4a68885f56bb65e`. The unsplit estimate exceeded admission,
so four original-deal pieces were launched at 10h each, all confirmed RUNNING:

- [0,4): `6aca8277fee2c9007018b4d9`
- [4,8): `6aca8278fee2c9007018b4dc`
- [8,12): `6aca8279fee2c9007018b4de`
- [12,16): `6aca827afee2c9007018b4e0`

All 12 collection pieces across 4–6p are RUNNING. Preserve the original whole-job
`stage: split_plan` guards; they intentionally have no job_id. Strict full-case
merge still needs implementation once pieces verify. The 6p guided evaluation
jobs (`6aca6ba9fee2c9007018a204`, `6aca6babfee2c9007018a206`,
`6aca6bad095c5780893147f0`) are also confirmed RUNNING; no new 6p strength result.

**Continuation runtime probes:** all 20 verified, 832 outer and 1,348,096 nested
rollouts, zero caps. The last 4p/neural_search case took 1,181.961s and used 378,112
nested rollouts. Completed probe/collection evidence: revision
`4d8352fba22b93a55aa1aa0a6483bbbcb2d7afaa`, prefix
`runs/strategic-runtime-completed-probes-evidence-v1`.

**Next learned correction is implemented, untrained.** Schema
`4.3-strategic-correction` adds one public eligibility bit and one shortlist bit,
preserving the entire 4.2 parent prefix and legal menu. It reuses the frozen
ordered-player embeddings and adds a 97,473-parameter head. It may select only the
teacher shortlist plus the parent proposal, and switches only above the fixed
0.025 predicted-advantage margin. Parent values and all other decisions stay
frozen. The complete trainable 10102 parent is pinned at revision
`b115a2d78aae095e51fb72a5535b3507abdf90c0`, path
`runs/discard-correction-v1/10102/best.pt`, SHA256
`66a10b831a54843063bbca89743a542ed1f89515a16452a40483eef369c59bd8`.
Do not initialize training from its inference-only derivative.

The design/loss is recorded before gradients in
`strong/strategic-correction-design-v1.json`. Targets average paired outcomes
across both continuation modes **within each sampled world before estimating
uncertainty**, then combine the independent A/B batches (96 samples). Weighted
MSE learns soft action advantages; noisy/negative evidence is retained, no winner
labels. All roots have equal total weight. Seeds 11101/11102, 120 epochs, validation
selection every fifth epoch, epoch0 parent baseline. No threshold tuning from the
small pilot metrics. The full-grid loader rejects partial coverage before downloads
or gradients; `train-strategic-correction.py` also requires HF/CUDA and frozen source,
design and data-manifest hashes. The loader/trainer are compiled but **have not yet
been executed on the complete dataset**. No gradient job or frozen training source
exists yet.

Preflight evidence: feature/menu/shortlist/hidden-state invariance on all 2,553
fixtures (1,096 eligible), two routing tests, four paired-target tests. A boolean
scatter initially failed ONNX export; an equivalent dynamic-index equality mask
fixed it. Failed local attempt retained at `runs/strategic-correction-preflight-v1`;
accepted output is `runs/strategic-correction-preflight-v2`. Zero correction matches
the actual frozen parent on all 2,553 positions, including choices/values, and
passes native/export parity and legal serving. Local **HX370**, not the 8840U:
median/p95 round-trip 3.916/8.217ms for the untrained prototype. Do not count this
as the requested final hardware benchmark. Prototype evidence/code/checkpoint:
revision `a4ff888a73e33f5b29918978f1beabac5dd437d0`, prefix
`runs/strategic-correction-preflight-evidence-v1`.

**Next:** finish the original eight label jobs; independently collect and inspect
the complete first-wave mixture, then admit the remaining 140 label chunks. Finish
4–6p collection and 6p arenas on their existing handles. Once all 160 labels verify,
freeze the complete manifest/source (include the known teacher source descriptor
and root gzip), run the HF training/export checks, independently verify outcomes
and perform fresh full-game screens. Source bootstrap must pass `DESIGN_SHA256`
and `DATA_MANIFEST_SHA256` to the trainer; do not attempt to put a source archive's
own future revision/hash inside that same archive. Reserved final seeds stay unused.

## Previous: balanced teacher labels running; five-player search exposes a regression

Previous goal turn: **progress** (2,560 full collection games verified and
continuation probes dispatched). This turn: **progress**:480 guided5p games and
another128 full collection games verified, a balanced1,920-root teacher dataset
frozen,20 HF label jobs dispatched, and4–5p collection split into disjoint deals
without altering the games. No new gradient training or qualified candidate yet.

**Five-player guided search is not a universal improvement.** All three jobs
COMPLETED and independently verified,160 games/model, eight paired development
deals, all seats and four rule combinations, no game/search caps. Parent/10101/
10102 search win shares35.0/34.375/35.0%; raw35.0/33.75/33.75%.10102 gains only
1.25 percentage points overall, paired95% deal interval[-3.75,6.875].
Its four rule shares are37.5/35/27.5/40% (original/open,original/sealed,
Recharged/open,Recharged/sealed). Original/sealed improves20 points[10,32.5],
but Recharged/open loses25 points[-42.5,-10]. The latter search interval
[12.5,40]% includes20% chance. These exploratory eight-deal results neither
qualify a model nor justify picking a per-rule switch from the evaluation data.
Keep both the sealed improvement and open regression visible in fresh acceptance
checks for the learned correction.

Raw5p revision `468eb0c35822897c190e3ff8b41d2413dc31911c`; verified directories
`ai/runs/multiplayer-search-transfer-verified-v1/{parent,10101,10102}-5p`.
Result file now verifies3–5p:1,152 guided games plus1,152 paired raw games;
6p remains pending on the three original live handles. Immutable5p evidence:
revision `d542f9713ab11d3db6cc5930113e3c745cdfb655`, prefix
`runs/multiplayer-search-transfer-5p-evidence-v1`.

**Collection now verified:**2,688 unique games /5,376 twin executions and136,966
public roots (all economic/self-play cases plus2p/search).2p/search raw revision
`d9e2b049e525f7778f10e23e0d34de52b8d96a91`. Fourteen runtime probes verified:
216 games /10,944 roots;6p/search probe remains live.3p/search full job remains
live.4p and5p search probes measured1,230.991s and2,053.539s; projected unsplit
jobs required15h/25h, beyond admission. They were **not** launched unsplit.

A new range runner preserves all original16 deals, full seat/rule grids,
serial model decisions, root selection, split assignments and horizons. Actual
nonzero-offset parity matched8 previously verified games and448 public roots
exactly (only worker-local terminal index and root file order index differ).
All base1,383 files unchanged. Slice source: dataset revision
`00e833da8dca00fdc26cf7e07b320a8276ad27f3`, archive
`strong-source-strategic-training-collection-slices-20261010-v1.tgz`, SHA256
`bb0498e19106fb233239af59ced62ffddbad056f71c6500ba15d46ec56e7a842`.
Each of4p/5p now has four jobs for[0,4),[4,8),[8,12),[12,16), admitted4h/7h.
Exact handles: `strong/strategic-training-collection-slices-status-v1.json`.
The original whole-job guards for4p/5p now have `stage: split_plan`, **no job_id**;
skip those when inspecting jobs. They reserve the slot against accidental whole-
shard duplication. Never remove these guards. Slice launch/evidence revision
`c523c30e320a357f38573b647e018a4e7dbd748a`, prefix
`runs/strategic-training-collection-slices-launch-evidence-v1`.
Use `manage-strategic-collection-slices.py collect N START END REV` for completed
pieces. A strict full-case merge still needs implementation after all pieces
verify; retain individual source pins and reject overlap/missing deals. The old
collection summarizer intentionally continues listing incomplete cases as pending.

**Continuation probes:**19 of20 independently verified,788 outer rollouts and
969,984 nested search rollouts,0 caps. Only4p/neural_search remains pending.
Two/three/five/six-player neural_search probes took322.062/380.700/669.286/
1,094.197s for two roots, versus3–14s for neural/economic continuations.
Nested search is overwhelmingly engine-bound. Raw pins:2p/3p neural_search
`f00229fad716d924d753e5d2512789973abcbea4`;5p at
`468eb0c35822897c190e3ff8b41d2413dc31911c`;6p at
`1c01d3d4b13e9df7a9fb043a542a98a42f620f87`.
Partial evidence: `9f665e252d84e196486ae5e822f52941716587db`, prefix
`runs/strategic-teacher-probe-partial-evidence-v1`. These two-sample probes do
not establish teacher reliability; the neural-search branches remain diagnostic.

**Balanced teacher pilot frozen:**1,920 fresh roots,1,440 train /480 validation;
640 each nominations,bids,building. Every2–6p ×economic/self-play source ×16 deals
×four rules ×three decision types appears once. Selection used fixed rootId
hashes and no outcomes. Whole count/source/deal units stay in one split. The
first preparation correctly rejected one identical public input crossing splits;
validation was fixed first and training used its next hash-ranked distinct input.
The final selection has no identical public-state overlap; runtime-probe roots
are excluded. Actual first/last chunk grids and eight model proposals passed
in the frozen source. No selection or loss was based on the held-out final seeds.

The first wave is20 HF jobs:five counts ×two source families ×two continuation
modes (neural self-play and neural focal player versus economic opponents).
Each job labels deals[0,2),24 roots, with48 worlds in each independent batch A/B,
full2400-step continuations and shortlist plus parent proposal. All individual
outcomes and paired advantages are retained. This is a counterfactual-label
pilot, **not gradient training**. Full design160 shards; the remaining 140 are
not admitted until first-wave results and runtime verify. Label jobs using actual
search opponents are not part of this initial bulk pilot due their measured cost;
independent strong-opponent full games remain required for acceptance.

Teacher source: dataset revision `837d94e14272163c33e5e55fa9c24b24686a28ae`,
archive `strong-source-strategic-teacher-training-20261010-v1.tgz`, SHA256
`a011f9ee4b8116b99220913a7db9d00849e9e593137cdb7e435e116fcafdd6c3`.
Protocol SHA256 `3c39786cc6c44a3838d3c4183c312c94a26563222b2720572010b76bbdd62a76`.
Root gzip SHA256 `f0fd62b4dd75c6b6c0936adeb1ffc75a2747cb2c62debe6b5d0aba60dbb4a091`;
local `ai/runs/strategic-teacher-training-roots-v1.jsonl.gz`, packaged at
`ai/strong/fixtures/strategic-teacher-training-roots-v1.jsonl.gz`. Recover it from
the pinned source if needed; do not rerun the exclusive selector/builder.
Five overlays in the source record are frozen; all1,391 prior files unchanged.
Launch evidence: revision `8e86b1336d1ef0a80bd8373f545700933afa193e`, prefix
`runs/strategic-teacher-training-launch-evidence-v1`.

**Three original jobs failed before program execution with ErrImagePull registry
response timeouts.** They were authoritatively ERROR with no result artifact,
then retried once using `python:3.11-slim-bookworm` and CPU libraries. All three
retries passed2,553-position serial/batched/reversed inference parity before
labeling. Exact parity artifacts pinned at model revision
`2ada43251d67a64a8b4f28e0fa9fbb3b1fc5f99b`; details and runtime versions in
`strong/strategic-teacher-training-retry-parity-v1.json`.
Replacement handles:3p/self-play/neural_economic `6aca7fb3fee2c9007018b207`,
4p/economic/neural_economic `6aca7fb5fee2c9007018b209`,
6p/economic/neural_economic `6aca7fb7fee2c9007018b20d`.
**All 20 effective label jobs were confirmed RUNNING** at the saved status time;
three original ERROR records remain as history, not three unhandled cases.
The exclusive `.retry-image-pull-1.json` guards retain each original handle.
Retry evidence revision `6a4fb8a59d7cc52f7dd34276752d9a4a7eb275cb`, prefix
`runs/strategic-teacher-training-retry-evidence-v1`.

**Next:** collect finished label shards using `collect-strategic-teacher-training.py
N SOURCE_MODE MODE START END IMMUTABLE_REV`; it checks the complete cells, all
samples/roles/credits/caps, exact public proposals and independent-batch advantage
accounting. No finished label shard has yet been independently collected. Verify
retry parity for any retry results, then size/launch remaining chunks using actual
first-wave runtime. Freeze a conservative uncertainty-aware correction loss and
train it on HF, with the parent fixed and fresh full-game evaluations required.
Also finish6p arenas,4p neural-search probe and6p collection probe; split6p work
if its measured admission requires it. Do not shorten horizons, reuse reserved
final seeds, or treat label fit as strength. Goal remains unachieved.

## Earlier: 2,560 fresh games verified; neural continuation probes running

Previous goal turn: **progress** (collector frozen and probes dispatched; verified
initial probes and launched full shards). This turn: **progress** (full public-root
verification, source-frozen continuation runtime, exact inference/control checks,
20 HF probe jobs dispatched). No new gradients or candidate qualification.

**Fresh collection:** all ten economic/frozen-self-play full shards for2–6p are
verified:2,560 unique games /5,120 exact twin executions and129,588 public auction/
building roots. Every public encoding, legal menu and serial model proposal was
reproduced; all actual-game/search caps are zero. Collection remains partial:
five search_geo shards are outstanding. Full2p/search and3p/search are live;
4–6p/search runtime probes are still live, so their full shards are not launched.
Twelve of15 probes are verified,180 probe games /8,903 roots, excluded from training.
The3p/search probe took444.839s; its full shard was admitted for6h and launched as
`6aca784afee2c9007018ac7c`. Exact other handles and timestamps are in
`strong/strategic-training-collection-status-v1.json` and exclusive launch guards.

Full economic and2–4p self-play raw pins: model revision
`5c97d76a82141bb05474decf05a8df8d08c03264`;5p self-play
`5b79e4b65d2bd73de1cae8e918d9949622ee99d0`;6p self-play
`4786b5cc52fc1ffd51fb7415aa41552bdb4035d6`.
Partial evidence: revision `abd58220f3c0ee9beef0922af52c2e8c944364f0`, prefix
`runs/strategic-training-collection-partial-evidence-v1`. It saves verified game
records, source/artifact pins, runtime admissions and launch guards. Large public
root files remain at the immutable raw revisions recorded in each verified shard.
`manage-strategic-collection.py summarize [--smoke]` aggregates only independently
verified shards and retains the missing cases. Do not recollect existing outputs.

**New continuation runtime:** `strategic-continuations.cjs` and
`strategic_teacher.py` keep the focal player on frozen10102 while opponents use
that same network, economic policy, or the unchanged search_geo16 reference.
The historical mixed economic/heuristic continuation is a separate control.
Same public worlds and random streams are paired across root moves and modes;
independent batches A/B use fresh seeds, never the true game seed. Candidate set
is the unchanged geography/economics shortlist plus the exact model proposal.
Every terminal outcome and paired advantage over that proposal is retained;
no hard winner labels or calibrated action-value claims are made. Outer and
nested search both retain2400-step caps; every inner cap is counted and prevents
admission. Existing workers and1,383 source files are unchanged.

Four meaningful engine checks passed: exact historical neural/mixed trajectories,
neural focal-player/opponent routing, split-worker equivalence, hidden-data
invariance and nested-budget/cap propagation. All2,553 serving decisions match
serial inference at batch sizes1/17/64 and in reverse order, including float64
inference and the4.2 feature contract.

Probe source: dataset revision `ca3be3ff81cc259135daa50e9bdf41590b6552ff`, archive
`strong-source-strategic-teacher-probe-20261010-v1.tgz`, SHA256
`c4a700ef7fb6c83c5e85060c52bc49b8eea94ff1c65c62b0bbcc39f0905b91fd`.
Protocol SHA256 `f19085fef326bfba66895648d2a33309b2be929615ed85ffa3b021be661a21dd`.
Eight overlays listed in the source record are frozen; do not edit them or rerun
the exclusive source builder. Roots:10 validation-only positions, one per count/
phase, selected by a fixed hash without looking at outcomes. **Not a balanced
rule-cell reliability study:** notably the selected auction roots are open.
Broader teacher-label experiments still need explicit sealed/open and variant
coverage. These two-sample probes establish runtime only, not label reliability.

All 20 jobs (five counts ×four continuation modes) were dispatched with exclusive
guards under `ai/runs/strategic-teacher-probe-launches-v1`; inspect
`strong/strategic-teacher-probe-status-v1.json` for exact handles. Four completed
cases have independently verified172 outer rollouts,0 caps:2p/neural7.732s,
2p/neural_economic5.015s,5p/mixed_control1.016s,6p/neural_economic3.251s.
No neural_search result is verified yet; do not extrapolate its cost from these.
Raw revision for those four is `5705e7011a44621b7d4a5e3dba6b82ca0cf55de3`.
Launch/partial evidence: revision `0a37a764963f8021d1c31f51f0abb600e0c073d4`, prefix
`runs/strategic-teacher-probe-launch-evidence-v1`.

Collect a completed probe with `ai/.venv/bin/python
ai/strong/collect-strategic-teacher-probe.py N MODE IMMUTABLE_REV`; this validates
root proposals, every rollout/sample/role/credit, paired advantages and all
nested-search counters independently. Then run `summarize-strategic-teacher-probe.py`.
Probes do not generate training labels or authorize gradients. Do not rerun launch
commands for existing guards, including SCHEDULING jobs. The six guided5–6p arena
jobs were also authoritatively confirmed RUNNING at the latest status timestamp.

**Next:** finish public-root and continuation-probe verification on the existing
handles. Use actual nested-search costs to size a rule/count/phase-balanced
paired teacher pilot, preserving individual uncertainty and train/validation
whole-deal separation. Then train the conservative correction on HF and require
fresh complete-game gains before expanding or selecting it. Earlier heuristic
continuation bias and original/sealed weaknesses remain unresolved. Reserved
final seeds remain unused; no candidate meets the full strength gate.

## Earlier: fresh strategic training collection frozen; HF probes dispatched

Previous goal turn: **progress** (all704 phase games and384 guided4p games
verified). This turn: **progress** (new training-data collector implemented,
privacy/twin checks passed, immutable source and evidence saved,15 HF probes
dispatched). No gradients or new candidate yet. Six guided5–6p jobs are still
RUNNING; the collection probes are SCHEDULING at the saved status timestamp.
These are existing live jobs, not a reason to restart or duplicate submissions.

The phase comparisons below support retaining **both auction and building
contexts**, with explicit player-count/rule coverage. The new collector records
every target-seat multi-choice nomination, bid or building decision on fresh
Germany deals; no outcome, final-round, win/loss or future-action selection.
It uses fixed10102 float64 inference, serially, and three opponent families:
economic, unchanged search_geo16, and the same frozen10102 policy as opponents
(snapshot0, frozen self-play with one designated learner observer). A260 is
excluded from collection and remains a neural development reference.

Full design:15 shards (2–6 players ×3 modes),16 independent deals/shard, all
seats and original/Recharged ×open/sealed. Total3,840 unique games and7,680
engine executions including twins. Whole deal indices0,4,8,12 are validation;
all seats, rules and repeated roots from a deal stay together. All full and
smoke prefixes are disjoint from evaluations and reserved final seeds. Labels
and teacher targets are a separate later stage. Terminal rows are retained
only to verify completion and coverage, not used to select roots or supervise
strategic action values.

**Checks passed:** all2,553 existing fixtures retain exact model inputs and
legal menus;1,096 strategic positions (779 auction,317 building) re-encode
identically from their sanitized public roots. Changing hidden decks/seeds,
sealed bids and queued plans does not change those roots. Opponent money is
retained as requested. Three contract tests reject incomplete grids, wrong
seeds/rules/roles, truncation, unexpected learner search and bad terminal credits.
An eight-game local diagnostic (16 twin executions) matched every observation,
submitted action and terminal row exactly;441 roots, no caps. It is engineering
evidence only and is excluded from training data. No local gradients.

Source dataset revision `4462dade57131375986bd1b17ee13ff292292e0a`, archive
`strong-source-strategic-training-collection-20261010-v1.tgz`, SHA256
`1846a4f168a8a38b67612a198f143958eb24df019cb35b9c55acde6ce25d08e0`.
Protocol SHA256 `0086deceb58a0dc21a8e07f7e74142315b237985aead8db5ce7ac1617369e45a`.
All1,378 existing base files are unchanged; five added capture/collection/test/
protocol files are frozen. Do not edit those overlays or rerun the exclusive
source builder. Source and preflight records:
`strong/strategic-training-collection-{source,preflight}-v1.json`.

**All15 HF probes are dispatched**, one deal/case,240 unique games /480 twin
executions planned. Exact handles are in
`strong/strategic-training-collection-status-v1.json` and exclusive guards in
`ai/runs/strategic-training-collection-launches-v1`. Launch/evidence snapshot:
model repo revision `307d2ae752a30a687457f81a2847460cd4b04dc2`, prefix
`runs/strategic-training-collection-launch-evidence-v1`, pin
`strong/strategic-training-collection-launch-evidence-v1.json`.
**No full collection shard is launched yet.**

Manager: `ai/.venv/bin/python ai/strong/manage-strategic-collection.py`:
`collect N MODE REV --smoke` independently checks every game, artifact hash,
public root, legal menu and serial model proposal; then `profile N MODE` and
`launch N MODE` admit that full shard. MODE is economic/search_geo/snapshot0.
Runtime admission is120s+2×matching probe seconds×16 deals,25% timeout headroom,
min4h/max12h; split work if too slow without lowering game/search horizons.
Full collection uses `collect N MODE REV` without `--smoke`. All output
directories and launch intents are exclusive; recover ambiguous outcomes from
the exact HF handles rather than resubmitting. No root labels or gradients are
created by any of these commands.

**Next:** collect/admit the fresh-data shards as their probes finish; also
collect the six existing5–6p guided arenas when complete. Inspect count/rule/
phase coverage and runtime before freezing paired-continuation labels. Retain
uncertainty rather than copying noisy winners; the planned learned correction
must earn gains in fresh full-game comparisons. No candidate has qualified.

## Earlier: all phase comparisons and guided four-player games verified

The previous goal turn was **progress** (128 verified two-player phase games).
This turn is **progress**: 576 additional phase games and 384 four-player guided
games independently verified, 960 new complete games total. All game/search caps
are zero. No new gradients, final seeds, candidate selection or deployment.

**The entire 704-game phase ablation is complete**, all six HF jobs COMPLETED.
`strong/phase-search-ablation-results-v1.json` has `all_cases_verified: true`.
The same raw/all-search baselines, public-search settings and reused development
deals are retained. Results below are win shares; 2p/search and3p/search each
have eight independent deals,3p/A260 has16:

| Case | Raw | Auction only | Building only | Both |
| --- | ---: | ---: | ---: | ---: |
| search_geo2p | 50.0000% | 68.7500% | 51.5625% | 65.6250% |
| search_geo3p | 20.8333% | 43.7500% | 38.5417% | 41.6667% |
| A2603p | 36.1979% | 41.1458% | 41.6667% | 49.4792% |

At3p/search, auction-only gains22.9167 points over raw, paired95% interval
[9.3750,36.4583]; building-only gains17.7083 points [6.25,30.2083]. Their
difference is uncertain: auction-minus-building5.2083 points [-11.4583,23.9583].
The four-arm interaction is -19.7917 points [-38.5417,-1.0417], meaning the two
gains are not additive on this scale; it does **not** prove either phase should
be disabled, since their direct comparisons against both include zero.
Auction-only rule shares37.5/37.5/37.5/62.5%; building-only45.8333/37.5/45.8333/25%.
Order is original/open,original/sealed,Recharged/open,Recharged/sealed.

At3p/A260, neither single-phase overall gain over raw is clear:
auction+4.9479 points [-3.3854,13.8021], building+5.4688 [-1.8229,12.2396].
Combined search has the higher point estimate. In original/sealed, combined
search improves on auction-only here: auction-only29.1667% versus combined47.9167%,
paired difference -18.75 points [-33.3333,-4.1667]. Building-only is68.75% on
Recharged/open versus52.0833% combined, but that difference remains uncertain
[−6.25,+37.5] points. Auction-only rule shares31.25/29.1667/52.0833/52.0833%;
building-only25/33.3333/68.75/39.5833%. All intervals are exploratory marginal
deal-bootstrap intervals, not multiplicity-adjusted or qualification evidence.

Final phase raw pins: building search_geo3p andA2603p at
`ea8d2d7df93fd510964035bb7ed6ea7d043a48f9`; auction search_geo3p at
`1b23f136b7e6a79fbf44267550fa08fc8c800107`; auctionA2603p at
`7599d61619387936824757d057d0b86609df05c0`. Two-player pins are preserved below.
Immutable complete evidence: model repo revision
`9ab4a39b49ac9ece8a3f26f9624fc1e2a68fc633`, prefix
`runs/phase-search-ablation-completed-evidence-v1`, pin
`strong/phase-search-ablation-completed-evidence-v1.json`. All six local verified
directories already exist; do not recollect or relaunch them.

**Guided4p also complete**,128 games/model, all three jobs COMPLETED; raw revision
`1b23f136b7e6a79fbf44267550fa08fc8c800107` for parent,10101 and10102.
Parent/10101/10102 search shares34.375/34.375/35.1563%, versus raw22.6563/24.2188/24.2188%.
The10102 paired gain is10.9375 points [-1.5625,19.5313]; its aggregate search
interval[27.3438,42.1875]% exceeds25% chance but rule cells remain weak.
Its four rule shares37.5/21.875/46.875/34.375%; original/sealed is below chance
in point estimate, with interval[12.5,31.25]%. Search-minus-raw in that cell
is−3.125 points [−21.875,18.75]. These eight deals do not qualify the agent.
10102 minus parent is only0.78125 points [0,2.34375].

`strong/multiplayer-search-transfer-results-v1.json` now verifies players[3,4],
672 guided games plus672 paired raw baselines, `all_counts_verified: false`.
Immutable4p evidence: revision `0f93f5edd7e30f19f32e70aa6f6e8ee9f8ebae42`, prefix
`runs/multiplayer-search-transfer-4p-evidence-v1`, pin
`strong/multiplayer-search-transfer-4p-evidence-v1.json`. The six full5–6p jobs
remain on their original live handles in the status file. Do not duplicate them.

**Next training direction:** the phase evidence does not support universally
replacing only auctions or only building. Retain both phase contexts and all
rule/count strata in fresh teacher data. Earlier global distillation regressed
and the continuation audit found policy-dependent rankings; do not convert
noisy search winners directly into hard labels. The next concrete preparation
is fresh public strategic-root collection (disjoint from these evaluations),
followed by paired continuation targets that preserve uncertainty and a small
frozen-parent correction experiment on HF Jobs. Record fresh full-game
development comparisons before accepting it. Complete the six live5–6p guided
reports alongside this work, keeping original/sealed weaknesses visible.
No final candidate is chosen; all reserved seeds and the full gate are unchanged.

## Earlier: two-player phase comparison verified; larger comparisons running

The previous goal turn was **progress and a verified wait**: preserved verified
probes and the production-engine audit, and checked all live jobs. This turn is
**progress**: independently collected 128 complete two-player phase games,
compared all four arms, and saved the raw and derived evidence. The UI revert
remains finished. Four phase jobs and nine guided 4–6p jobs are still running
at the status-file timestamps. Do not restart them.

**First phase result: auction search supplies the clearer two-player gain.**
These are the same eight development deals against the unchanged search_geo
reference, all seats and four rule combinations, 64 games per arm:

| Search phases | Win share | Paired gain over raw (95% deal interval) |
| --- | ---: | ---: |
| none (raw policy) | 50.0000% | — |
| auction only | 68.7500% | +18.7500 points [4.6875,31.2500] |
| building only | 51.5625% | +1.5625 points [-10.9375,12.5000] |
| both (previously verified) | 65.6250% | +15.6250 points |

Auction-only minus building-only is +17.1875 points [7.8125,26.5625].
Auction-only minus both is only +3.1250 points [-9.3750,15.6250], so this does
not establish that disabling building search improves the complete agent.
Auction-only rule shares: original/open81.25%, original/sealed75%,
Recharged/open50%, Recharged/sealed68.75%. Recharged/open is **12.5 points
below raw**, interval [-37.5,12.5]. Its original/sealed gain is25 points
[6.25,43.75]. Keep every rule result; no universal auction-label claim.

Both new arms passed exact source/model, all game rows, phase-routing and
zero-cap checks. Full raw revision `53a7b0802c5f7b680631f0c8724253c5a73e96bf`;
local directories `ai/runs/phase-search-ablation-verified-v1/{auction,building}-search_geo-2p`.
Immutable evidence revision `62f80c93e1bfea96c5defa07eb7c15fe18a35cfc`, prefix
`runs/phase-search-ablation-2p-evidence-v1`; pin
`strong/phase-search-ablation-2p-evidence-v1.json`. The results file
`strong/phase-search-ablation-results-v1.json` is explicitly partial:
128 new games, `all_cases_verified: false`. Do not recollect completed directories.

The local comparison now reports four-arm contrasts, keeping shared deals
together across all arms: auction with/without building, building with/without
auction, and the joint interaction. Overall interaction is -4.6875 points
[-23.4375,14.0625], inconclusive. This exploratory extension was added before
reading the full phase outputs; it changes no frozen jobs or game seeds.
Nine phase tests passed, including exact shared-arm covariance cancellation,
cluster uncertainty, tie credits and rejection of incomplete/mismatched data.
The four marginal effects also reproduce the separately collected pairwise
estimates and intervals exactly on these real results. This analysis does not
validate teacher targets or qualify the policy.

**All nine phase probes passed:** 96 complete games, 780,000 learner rollouts
and 405,328 opponent rollouts, no truncations. Search routing was checked for
each phase and game. The 32 all-search control games exactly reproduce the
previous game rows, including terminal money, not only winner credits.
`test_phase_search_collect.py` passes three tests against real probe artifacts,
including rejection of altered routing, model, seed, horizon and replay data.
Probe win rates are not strength evidence.

Immutable probe evidence: model repo `coyotte508/powergrid-ai-germany-v1`,
revision `c0ab287bff19e1f2d807e9163fc70716c814498e`, prefix
`runs/phase-search-ablation-probes-evidence-v1`.
Pins and summary: `strong/phase-search-ablation-probes-evidence-v1.json` and
`strong/phase-search-ablation-probes-results-v1.json`. Includes all collected
artifacts, replay controls, six runtime admissions and exact launch guards.

**All six full phase jobs were dispatched**, 704 games on existing development
deals. The two search_geo2p jobs are now complete; the four 3p jobs are running:

| Search arm | Case | HF job |
| --- | --- | --- |
| auction | search_geo 2p | `6aca6df4fee2c9007018a388` |
| auction | search_geo 3p | `6aca6df7fee2c9007018a38c` |
| auction | A260 3p | `6aca6dfafee2c9007018a393` |
| building | search_geo 2p | `6aca6dfd095c578089314950` |
| building | search_geo 3p | `6aca6e00095c578089314955` |
| building | A260 3p | `6aca6e04fee2c9007018a399` |

Every job passed matching control parity and same-arm/case runtime admission;
all use CPU-performance with a four-hour timeout. Collect complete artifacts
at immutable revisions with `manage-phase-search-ablation.py collect ARM CASE REV`
(without `--smoke`). Compare only cases whose two full arms are both verified.
The existing nine full guided 4–6p jobs also remain RUNNING. Their exact handles
are in `strong/multiplayer-search-transfer-status-v1.json`; 3p is already verified.
No new gradient job has been launched while these comparisons are pending.

**Production-engine compatibility passed within its tested scope.** An isolated
compile of release commit `aac09f231d4b024a7ea1c7e24cad0223a8c4a7ea`
(engine 2.0.14) was compared with the frozen research engine (2.0.10):
2,553 legal menus, 5,106 feature checks, 2,553 default-bot one-step transitions,
and 80 complete Germany games / 41,026 transitions across 2–6p and all four
rule combinations. No differences in the compared state or terminal outcomes.
Games use alternating heuristic/economic actors; this is not learned-policy
strength evidence. Explicit exclusions: new powering-choice snapshots, pending
announcement queues and Step 2/3 announcement log text.

Immutable compatibility evidence: model repo revision
`107ac032692cd7effd529bd03f7e6dc319602c55`, prefix
`runs/production-engine-compatibility-evidence-v1`, pin
`strong/production-engine-compatibility-v1.json`. Contains the checker, full
result, production source archive, all 40 compiled engine files, provenance,
research-source byte check and build environment. Dependency entry-file hashes
match; this does not claim a complete dependency-tree comparison. Pending
choice revisions, platform scheduling/transport and other maps were not tested.
No production source or frozen evaluation runtime was changed. Any eventual
qualified serving package still needs its exact engine/configuration checked.

**Next:** collect the remaining four 3p phase reports and nine guided 4–6p
reports from their saved live handles; report paired differences and every rule
cell; then choose a targeted teacher/student intervention. The two-player result
prioritizes auction investigation but does not settle Recharged/open or3p. Do not
spend reserved final seeds or infer phase benefit from runtime probes. No model
has qualified, and the value head remains uncalibrated for player-score analysis.

## Earlier: all raw counts verified; phase diagnosis probes dispatched

The previous goal turn was **progress** (verified three-player search gains and
the real final-harness smoke). This turn is **progress**: the entire 13,440-game
raw opponent suite is independently verified, the three full six-player guided
jobs are dispatched, and a frozen auction/building phase ablation has nine HF
probes in flight. No new gradients, candidate selection, reserved seeds or
production deployment. UI remains at the previously reverted version.

**All raw-policy 2–6p comparisons are complete**, 15 jobs and 13,440 games.
`strong/discard-opponents-results-v1.json` now has `all_shards_verified: true`.
Every raw game and search rollout passed the prescribed completion checks.
New six-player raw artifacts are pinned at
`b0444707a202113269df5c2a9a332d86be587c76`; local verified directories:
`ai/runs/discard-opponents-verified-v1/{parent,10101,10102}-6p`.
Immutable complete evidence: `3faadbc32dfdb6e1c1490f9ea6ade911bb68d9c4`,
`runs/discard-opponents-completed-evidence-v1`, pin
`strong/discard-opponents-completed-evidence-v1.json`. Earlier partial snapshots
are preserved historical evidence, superseded by this full comparison.

| 6p opponent | Parent | 10101 | 10102 |
| --- | ---: | ---: | ---: |
| legacy | 94.0104% | 94.0104% | 94.2708% |
| heuristic | 99.2188% | 99.2188% | 99.2188% |
| rush | 75.1302% | 75.3906% | 75.3906% |
| search_geo | 38.5417% | 38.0208% | 38.5417% |

Search has 192 games/model but only eight independent deals. Parent/10102
interval is [31.25,46.3672]%; their credits are identical. The10101 point
regression is 0.5208 percentage points. Parent/10102 rule shares are
50/18.75/58.3333/27.0833% for original/open, original/sealed,
Recharged/open, Recharged/sealed. Both sealed intervals include 1/6 chance:
[8.3333,29.1667]% and [14.5833,41.6667]%. The favorable aggregate is not a
qualification result. The earlier weak 3–4p and 5p sealed findings remain.

**All 12 full 3–6p search jobs are dispatched**, 1,728 new guided games planned.
Three 3p jobs/288 games are already independently verified; the other nine
4–6p jobs are live or scheduling in the saved status file. Newly launched 6p:
parent `6aca6ba9fee2c9007018a204`,10101 `6aca6babfee2c9007018a206`,
10102 `6aca6bad095c5780893147f0`, 192 games each, CPU-performance10h.
Their admission reverified the matching complete raw baseline and the measured
6p runtime probe. No duplicated or restarted jobs.

**New phase ablation is frozen**, using10102 and the exact same search settings,
models, opponents and existing development deals. It compares auction-only and
building-only search against the already pinned raw and all-search controls:
search_geo2p (64 games/arm),search_geo3p (96),A2603p (192),704 new full games.
This diagnoses phase contributions before choosing new teacher training; it
cannot qualify a model. Report all rule cells and regressions, not just winners.

Source `strong-source-phase-search-ablation-20261010-v1.tgz`, dataset revision
`a597aed2089a746b2884083b6fea3ab4e9d774af`, SHA256
`564543f80271af6bd26fc364e23e3fd107b7598742813119db7cd99fd71e607c`.
Protocol SHA256 `facc2c51a8ef7af5e61283764dcb117cb7531e516bbf67a4d2d8b60436884c32`.
All 1,378 base runtime files are byte-identical. Five added files attach a public
phase tag, filter only learner search requests, count routing per game, and
validate it. Local frozen-package checks cover 5,533 encodings on all2,553
fixtures with unchanged features/legal moves/game state, plus routing checks
preserving opponent and excluded-phase choices. Those are engineering checks;
complete-game replay parity still requires the HF controls.

Nine 4h HF probes, 96 games total, are dispatched:

| Arm | search_geo2p | search_geo3p | A2603p |
| --- | --- | --- | --- |
| all control | `6aca6b8cfee2c9007018a1df` | `6aca6b8e095c5780893147d6` | `6aca6b90fee2c9007018a1e1` |
| auction | `6aca6b92fee2c9007018a1e3` | `6aca6b93095c5780893147d9` | `6aca6b95095c5780893147dd` |
| building | `6aca6b97fee2c9007018a1e5` | `6aca6b99095c5780893147df` | `6aca6b9a095c5780893147e4` |

All-control probes replay one existing deal/case and must match every original
game row exactly (apart from new routing counters). Phase probes use separate
fresh runtime seeds. Do not use probe win rates as strength evidence. Full
phase jobs have NOT launched yet. Independent collection and same-case control
parity plus same-arm runtime admission are mandatory before full launch.
Full admission uses120s+2×probe duration×deals,25% timeout headroom,max12h.
If above the limit, split the work without weakening horizons.

Manager: `ai/.venv/bin/python ai/strong/manage-phase-search-ablation.py`:
`collect ARM CASE REV --smoke`, `profile ARM CASE`, then `launch ARM CASE`
when admitted. ARM is `all` (controls only), `auction` or `building`; CASE is
`search_geo-2p`, `search_geo-3p` or `a260-3p`. Full collection omits `--smoke`.
`compare --cases ...` requires both phase arms for every requested case and
explicitly marks incomplete case subsets. Launch guards are exclusive under
`ai/runs/phase-search-ablation-launches-v1`. Preserve them on observation errors.
Launch/preflight evidence pin: `strong/phase-search-ablation-launch-evidence-v1.json`.

**Next:** collect finished phase probes and full4–6p guided arenas from their
exact handles, verify outputs, admit full phase comparisons as justified, and
use complete paired/rule evidence to choose the next teacher/student change.
Current policy values remain uncalibrated for live player-score analysis.
The original final strength gate and reserved prefix are unchanged and unused.

## Earlier: complete three-player search comparison verified

All three full3p jobs have now **COMPLETED**,288 new complete games with288
paired raw baselines,zero game/search truncations. `strong/multiplayer-search-transfer-results-v1.json`
is explicitly partial (`verified_players: [3]`, `all_counts_verified: false`).
Parent and10101 raw outputs are pinned at
`2fdd41a0a1b646fcb2da7f77a563771ce32b4a59`;10102 at
`363e2b5aab88c0be17ee2ab36c0a61421d419fb8`. Local artifacts:
`ai/runs/multiplayer-search-transfer-verified-v1/{key}-3p`.

Parent raw16.67% → search40.625%,paired gain23.9583 points,
whole-deal95% interval[16.6667,31.25]. Both corrections raw20.8333% →
search41.6667%,gain20.8333 points,interval[15.625,26.0417]. Corrected
search interval[34.375,48.9583]% is just above1/3 overall, but all four
rule-cell intervals include chance. Corrected original/open45.8333%,
original/sealed45.8333%,Recharged/open33.3333%,Recharged/sealed41.6667%.
These are only8 independent deals; passing the40% aggregate point floor
is not qualification. Recharged/open remains a priority diagnostic gap.
Both correction seeds again have identical credits,not necessarily trajectories.

Immutable3p paired evidence: `be8688136e9bfd5744f1751808aa33c884d36aef`, prefix
`runs/multiplayer-search-transfer-3p-evidence-v1`, pin
`strong/multiplayer-search-transfer-3p-evidence-v1.json`. Do not recollect
these exclusive directories or relaunch these jobs. Six full4–5p guided jobs
remain live; the three6p raw jobs remain live. After collecting raw6p,
launch its three already-admitted guided jobs. Compare further counts only
when all three models/count are independently verified. The final-harness
real8-game development smoke is also verified,as detailed below.

## Earlier this turn: raw 2–5p verified; all search probes passed; full 3–5p launched

The preceding AI goal turn was **progress** (verified the first search-transfer
suite and launched multiplayer probes). This continuation is **progress**:
verified 9,408 raw-policy opponent games, all four 3–6p probes, and dispatched
nine full search comparisons. Final-evaluation compatibility and evidence checks
were repaired and tested, without playing any reserved games. No new gradients,
selection, promotion or deployment. The intervening UI revert remains complete.

**Raw-policy 5p results are complete**, 1,120 games per model (3,360 new games).
Parent raw artifact revision: `8372a23b6fa130a6549cd0783e1116ce293af4c0`.
Both correction artifacts: `bbaca62cad80b0a3a01f715f2e3cc01f8cf42898`.
Local verified directories: `ai/runs/discard-opponents-verified-v1/{key}-5p`.
All 2–5p results are in `strong/discard-opponents-results-v1.json`, with zero
actual-game/search truncations and `all_shards_verified: false` (6p pending).

| 5p opponent | Parent | 10101 | 10102 |
| --- | ---: | ---: | ---: |
| legacy | 92.8125% | 91.5625% | 92.1875% |
| heuristic | 97.8125% | 97.8125% | 97.8125% |
| rush | 75.625% | 75.625% | 75.625% |
| search_geo | 35% | 33.75% | 33.75% |

The 160 search games/model represent only eight independent deals. Corrected
aggregate interval [28.75,38.75]%; parent [31.25,38.75]%. The correction is
-1.25 points versus parent, paired interval [-3.125,0]. Corrected rule shares
(original/open, original/sealed, Recharged/open, Recharged/sealed):
45/15/52.5/22.5%. Original/sealed interval [7.5,20]% fails to establish advantage
over 20% chance; Recharged/sealed [10,35]% also does not establish it. Thus the
aggregate passing the 28% point floor is insufficient. Preserve the sealed
weakness and correction regression when choosing a candidate.
Immutable complete 2–5p evidence: `01e02f69e85a21cf20967b373fb1fe3acf477a96`,
`runs/discard-opponents-2p5p-completed-evidence-v1`. Pin:
`strong/discard-opponents-2p5p-evidence-v1.json`.

**All 3–6p search runtime probes are independently verified:** 72 complete games,
1,993,808 search rollouts, zero truncations. Probes are execution evidence only.
Profiles `strong/multiplayer-search-transfer-{3,4,5,6}p-runtime-v1.json` admit
4/5/7/10h jobs respectively, retaining the prescribed conservative margins.
Probe revisions: 3p `8372a23b6fa130a6549cd0783e1116ce293af4c0`,
4p `bbaca62cad80b0a3a01f715f2e3cc01f8cf42898`,
5p `739545765dae4b33853c3156f6237d6014e79059`,
6p `e4e5ccc4b649fd1df18dd6394d4aae3613a6aa9f`.
Evidence: `b546cd8337c0e659e0ca9fceda5da5f020269c6b`, prefix
`runs/multiplayer-search-transfer-runtime-evidence-v1`.

**Nine full search jobs are dispatched, 1,152 new paired games**:

| Count / games per model | Parent | 10101 | 10102 |
| --- | --- | --- | --- |
| 3p / 96 | `6aca6497fee2c90070189d0d` | `6aca649a095c5780893143dc` | `6aca649b095c5780893143de` |
| 4p / 128 | `6aca65b1095c57808931448b` | `6aca65b2fee2c90070189dea` | `6aca65b5095c57808931448d` |
| 5p / 160 | `6aca67e4095c57808931461f` | `6aca67e6095c578089314626` | `6aca67e8095c578089314628` |

All nine were RUNNING at the saved status check. Three full 6p jobs (576 games)
remain to launch: runtime is admitted, but their pinned raw-policy baselines
must finish and be independently collected first. Those existing raw6p handles
are parent `6aca55e9095c578089313ace`, 10101 `6aca55edfee2c900701891ef`,
10102 `6aca55ef095c578089313adb`, all confirmed RUNNING. Do not duplicate them.
Use status files and exclusive launch guards; do not relaunch on a log timeout.

**Final harness repaired, not qualification:** the launcher now accepts the
current4.2 models, requires frozen runtime/model hashes, preserves individual
submission intents, and locks concurrent ledger access. The arena wrapper
records actual source/model/runner identities. Verification rejects wrong exact
deals/episode pairings, wrong runtime or truncated searches. New
`merge-arena-reports.py` verifies disjoint contiguous shards and recomputes
statistics from raw games; it never averages confidence intervals/percentiles.
Nine isolated contract tests pass, using mock submissions and temporary metadata
around existing development rows. They do not execute final games or qualify a
model. Frozen source `strong/final-runtime-source-v1.json`:
`9e0f1e957512c8dfa9bdb5edd7caf1671c197de4`, archive
`strong-source-final-runtime-20261010-v1.tgz`, SHA256
`07c635937b08a6e37adfed6c94f6f4cc63a24e8e0572da78a1717b743b873571`.
Only the arena provenance wrapper changed;1,377 other files are unchanged.
A real8-game HF development smoke is **COMPLETED and independently verified**:
`6aca67f3fee2c90070189ff5`,
seed `final-runtime-smoke-development-v1-2p`. Record:
`strong/final-runtime-smoke-v1.json`. Raw revision:
`faf5b78910806a199599f42094a7aad902015e7e`. All8 games completed,
108,096 learner rollouts across445 decisions,0truncations,248.829s evaluation.
Source/model/runner hashes, all paired rules/seats and the strict shard merger
passed independent collection. Immutable evidence: `2fdd41a0a1b646fcb2da7f77a563771ce32b4a59`,
`runs/final-runtime-smoke-evidence-v1`. Local:
`ai/runs/final-runtime-smoke-verified-v1`. Do not rerun its exclusive collector.
This smoke measures plumbing only; its seed is not reserved. Source package is
already built/uploaded: do not rerun the exclusive builder.

**Next:** collect the exact live jobs on completion. Independently verify raw6p,
then launch its three already specified guided matchups with the existing
manager. Collect full search3–5p results and compare by count/rule against their
pinned raw baselines. Keep regressions visible; don’t select on aggregate wins.
The real harness smoke is verified and preserved; keep the reserved final prefix
unused until a complete candidate is justified. Future
phase ablations/teacher training should follow these results. The nine full
search jobs are work in flight, not qualified results.

## Earlier: search improves A260 results; 3–6p search probes launched

The preceding goal turn was **progress**: verified raw 2–4p, all two-player
search comparisons, and the actual 8840U benchmark. This turn is **progress**:
independently verified all three A260 arms, completed the 1,152-game search
comparison, analyzed paired terminal outcomes, and froze/launched the broader
3–6p search probes. No new gradients, final seeds, promotion or deployment.

**The entire first search-transfer experiment is now verified:** 1,152 guided
games paired with 1,152 pinned raw-policy baselines; all nine jobs COMPLETED,
zero actual-game or search truncations. Do not relaunch any of them.
`strong/search-transfer-results-v1.json` now has `all_cases_verified: true`.

| Case | Parent raw → search | 10101 raw → search | 10102 raw → search |
| --- | ---: | ---: | ---: |
| heuristic 2p | 63.28 → 89.06% | 71.09 → 92.97% | 71.09 → 92.97% |
| search_geo 2p | 23.44 → 62.50% | 50.00 → 65.63% | 50.00 → 65.63% |
| A260 3p | 37.24 → 48.44% | 36.20 → 49.48% | 36.20 → 49.48% |

All three new A260 collections are pinned at raw revision
`5f229b534da876c6455740631c2012e3152138b5`, local directories
`ai/runs/search-transfer-verified-v1/{parent,10101,10102}-a260-3p`.
Each is 192 games, 16 independent deals, all seats/four rules. The corrected
models' paired search gain is +13.28125 points, whole-deal 95% interval
[+4.1667,+22.4023]. Guided win-share interval [40.625,59.375]%; the parent
improves by +11.1979 points, interval [+2.6042,+20.3125]. These are exploratory
development comparisons on intentionally reused deals, not final qualification.

Corrected A260 rule-cell shares (original/open, original/sealed,
Recharged/open, Recharged/sealed): 39.5833/47.9167/52.0833/58.3333%.
Original/open interval [25,56.25]% includes chance. Recharged/open loses
4.1667 points versus raw, paired interval [-20.8333,+12.5]; keep that regression
visible. The two sealed cells gain 19.7917 and 29.1667 points with positive
paired intervals. Corrected-vs-parent guided aggregate gain is only1.0417
points, interval [-1.0417,+3.125]. Both training seeds still produce identical
win credits in this first transfer experiment, not necessarily identical states.

Full immutable evidence: `5d574befee21c335b49b2ffe53d6d89002b83152`, prefix
`runs/search-transfer-completed-evidence-v1` in
`coyotte508/powergrid-ai-germany-v1`. Pin file:
`strong/search-transfer-evidence-v1.json`. Earlier partial snapshots remain valid
historical evidence, superseded by this complete comparison.

**Paired terminal diagnostics are saved**, reproducibly generated by
`strong/analyze-search-transfer-outcomes.py` in
`strong/search-transfer-terminal-analysis-v1.json`, including every rule cell.
For corrected 2p versus search, 21 losses turn into wins while 11 wins turn into
losses. Remaining losses: 16/22 have fewer cities than the winner powers, 4/22
lack nominal capacity, and4 lose a powered-city tie on cash. For corrected 3p
versus A260, 51 losses turn into sole wins,26 sole wins become losses, and one
shared win becomes a sole win. Among97 remaining losses,88 have fewer cities
than the winner powers and41 have insufficient nominal capacity. Categories
overlap, the loss cohort changes, and unused nominal potential may mean fuel
shortage. These observations suggest building/auction phase ablations may be
useful; they do not prove causal move errors or justify hard labels by themselves.

**The broader 3–6p search experiment is frozen and its four probes are live.**
All three existing models will face unchanged search_geo with public search48,
geographic/model proposals and unchanged horizons. Eight development deals per
count, all seats and four rules: 1,728 new full games planned. Two-player games
and A260 are not duplicated. Raw-policy baselines remain the already frozen
`discard-opponents` jobs. Corresponding verified raw baseline plus same-count
verified runtime probe are required before each full launch. Raw 3p/4p baselines
are ready; the six raw5–6p jobs remain RUNNING at the saved status timestamp.

The new frozen wrapper verified672 existing raw games and rejected48 altered
contracts. All1,376 files of the preceding source archive are byte-identical;
only the new wrapper and protocol are added. Archive
`strong-source-multiplayer-search-transfer-20261010-v1.tgz`, dataset revision
`a96a04f0914a34f4a86bcac0948db0e4777fa83d`, SHA256
`98fd31d794e96f0e4598db484cb074e899fe3af465b4c911d7c2abea6f15bbe2`.
Protocol SHA256
`9f6606955ac2aa3ebd46168bce0d983cd4aaed5b9d1d4feda21890d07fff5dda`.
This package does not change the old completed/running experiments.

| Runtime probe | HF job | Games |
| --- | --- | ---: |
| 10102 / 3p | `6aca61e3fee2c90070189b3e` | 12 |
| 10102 / 4p | `6aca61e5fee2c90070189b41` | 16 |
| 10102 / 5p | `6aca61e6fee2c90070189b44` | 20 |
| 10102 / 6p | `6aca61e8095c578089314282` | 24 |

All four probes are CPU-performance,4h, separate smoke deals, confirmed RUNNING.
The72 games are runtime/legal admission only; do not treat their win rates as
strength evidence. No full job for this extension has launched yet.
Guards: `ai/runs/multiplayer-search-transfer-launches-v1`.
Launch/preflight evidence: `2d214efc19e49d296145608a339f8aee75eeb0ed`, prefix
`runs/multiplayer-search-transfer-launch-evidence-v1`.

Use `ai/.venv/bin/python ai/strong/manage-multiplayer-search-transfer.py`:
`collect 10102 N IMMUTABLE_REV --smoke` verifies completed probes into
`ai/runs/multiplayer-search-transfer-smoke-verified-v1/Np`; `profile N` computes
admission from twice linear observed runtime plus120s and25% timeout headroom.
If admitted, `launch KEY N` also rechecks the full raw baseline and creates an
exclusive guard before calling HF. Above12h requires partitioning, not weaker
horizons. Full result collection: `collect KEY N IMMUTABLE_REV`; comparison:
`compare --players N ...` requires all three models at each requested count and
marks incomplete-count subsets explicitly. No restarts on observation timeouts.

**Next:** collect the four probes and remaining raw5–6p results as they finish;
launch each admitted full search matchup. This closes the currently untested
search-guided3–6p gap against the independent search reference. The first
experiment's improved A260 and2p results do not establish general strength.
Use the full pattern of wins/regressions to choose training or phase-ablation
work, then test an eventual frozen candidate on fresh held-out deals and the
unchanged final gate. The current 8840U benchmark remains valid for these model
and search settings; a later changed configuration needs its own verification.

## Earlier: raw 2–4p evaluated; search transfer running; actual-device probe verified

The preceding AI goal turn was **progress**: independently verified three-player
results, completed search-routing/package checks and all three HF runtime probes,
and launched all nine full search-transfer jobs. The intervening UI revert is
complete. This continuation is **progress**: independently verified all 6,048 raw 2–4p games,
576 new search-guided 2p games and 8,013 requests on the actual 8840U, confirmed
every live HF handle, and saved immutable raw evidence. No new
training gradients, final seeds, model promotion or deployment.

**All 2p, 3p and 4p independent-opponent results are verified**, 6,048 games total;
zero actual-game/search truncations. The remaining six 5–6p jobs were confirmed
RUNNING at the timestamp in `strong/discard-opponents-status-v1.json`.
Do not relaunch. All 15 full jobs were already dispatched (13,440 games).

| Opponent (3p) | Parent | Seed 10101 | Seed 10102 |
| --- | ---: | ---: | ---: |
| legacy | 91.15% | 92.71% | 92.71% |
| heuristic | 85.42% | 85.42% | 85.42% |
| rush | 57.81% | 60.68% | 60.68% |
| search_geo | 16.67% | 20.83% | 20.83% |

Against search_geo, corrections have whole-deal 95% interval [15.625,27.0833]%:
below 1/3 chance and the40% point floor. Only eight independent deals
(96 games/model), so this is exploratory development evidence. Paired gain is
+4.1667 points, interval [0,8.3333]. Both seeds have identical outcome credits
on 2p and3p; their trajectories are not identical. Corrections' 3p rule-cell
shares are20.8333/25/29.1667/8.3333% (original open/sealed, Recharged open/sealed).
The Recharged sealed weakness remains especially large. Raw3p revisions:
parent `84c1d964400507eb4796fc7f2584b87c5b173370`;
both seeds `96a899ef266439f72f50f2dbcfe8d5060985a543`.
Combined 2p–4p immutable evidence:
`3a61f660c843e93eec01ab147418a825d7b92cce`, prefix
`runs/discard-opponents-2p4p-completed-evidence-v1` in the model repo.

| Opponent (4p) | Parent | Seed 10101 | Seed 10102 |
| --- | ---: | ---: | ---: |
| legacy | 90.23% | 89.84% | 90.63% |
| heuristic | 92.19% | 92.58% | 92.58% |
| rush | 63.28% | 64.84% | 64.84% |
| search_geo | 22.66% | 24.22% | 24.22% |

Four-player search performance remains below the 32.5% point floor and the
25% chance point. Both confidence intervals include chance; the paired gain
is +1.5625 points, with seed10101 interval [-1.5625,+4.6875]. The training
seeds differ in some individual outcomes/rule cells despite the equal aggregate.
Raw4p revisions: parent `a531d4e90204005fa4e9555df599aaab8ecb933b`;
both corrections `a974ede722560313372a5b3a02329784cbf11d1f`.
All three four-player jobs are COMPLETED and independently verified, each
896 games including128 against search_geo. Do not repeat them.

**Search-transfer experiment now implemented, frozen and running.**
`strong/search-transfer-protocol-v1.json` fixes public search48, six proposal
candidates, geographic proposals plus the model proposal, all existing strategic
phases, with the learned discard/resource/powering actions retained outside
search. All three models remain separate. Cases:2p heuristic (16deals),2p
search_geo (8deals),3p A260 (16deals), all seats/four rules:1,152 new games paired
with1,152 verified existing raw-policy games. These development deals were
intentionally reused and the target cases selected after raw weaknesses appeared;
this does not replace an independent held-out strength test. The newly observed
3p search_geo deficit is not in this already-frozen transfer protocol.

Frozen source archive `strong-source-search-transfer-20261010-v1.tgz`, dataset
revision `1ef629c51282936c0bd2be9e7b584ce985e91d03`, SHA256
`e35e93d6d410ccb34bfb59a2840a7e4ed3b67e950a429968adcdf383ec53ef55`.
All1,372 base files unchanged; four overlays. A preflight missing-helper error
was fixed before upload/launch and preserved in the packaging-repair report.
Protocol SHA256
`5c0d303a3ea15c69c29c841f022a3c7a80379d97f1e14cf7901ce371df3b5d1c`.
5,106 actual bridge-routing checks over2,553 positions passed with stubbed
search/transitions; this is compatibility evidence only. All1,152 baseline
contracts pass. Collector negative checks reject wrong models, seeds, opponents,
search configurations, incomplete games and caps.

All three real HF search probes are COMPLETED and independently verified:
28 complete games,371,328 rollouts,zero game/search caps. Timings:
heuristic2p247.08s/8games; search_geo2p298.33s/8games;
A2603p369.53s/12games. Full jobs use CPU-performance:4h for2p,5h forA260,
admitted from twice the measured linear runtime plus120s and25% timeout headroom.
No game/search horizons were reduced. Search runtime/preflight/launch evidence:
`fc0b2db80dc0fb1ef758e259c2efbc33bfaa8ce3`, prefix
`runs/search-transfer-runtime-completed-evidence-v1`. Local verified probes:
`ai/runs/search-transfer-smoke-verified-v1/{heuristic-2p,search_geo-2p,a260-3p}`.

All nine full search jobs were launched once. Six are now COMPLETED and
independently verified (576 new games); all three A260 jobs were still RUNNING
at the saved status timestamp:

| Model | heuristic2p | search_geo2p | A2603p |
| --- | --- | --- | --- |
| parent | `6aca5acdfee2c90070189545` | `6aca5bb6fee2c900701896a1` | `6aca5bba095c578089313ec7` |
| 10101 | `6aca5acefee2c90070189548` | `6aca5bb8095c578089313ec3` | `6aca5bbbfee2c900701896a4` |
| 10102 | `6aca5acf095c578089313d8b` | `6aca5bb9095c578089313ec5` | `6aca5bbc095c578089313ecb` |

**First complete-game search-transfer results are verified.**
All three heuristic2p arms are complete (384 new games). Parent improves from
63.28125% raw to89.0625% search; each correction improves from71.09375% to
92.96875%. Corrections' paired search gain is +21.875 points, whole-deal95%
interval [+13.2617,+32.03125], on16 independent deals. Rule-cell shares for
both corrections:90.625/87.5/100/93.75% (original open/sealed, Recharged
open/sealed). The100% cell is only32 games, not a perfect-performance claim.

All three search_geo2p arms are also complete (192 new games): parent62.5%,
both corrected models65.625%, versus their raw23.4375% and50%. Each correction's
search-minus-raw gain is +15.625 points, paired interval [+1.5625,+31.25].
Their aggregate win-share interval is [54.6875,75]%, but all four rule-cell
intervals include50% (one at the boundary). Rule-cell shares are62.5/68.75/
62.5/68.75%. Eight development deals do not establish final qualification.
Both seeds have identical win credits on this two-player transfer subset; this
does not establish equal behavior or strength in other populations.

The added learned discard correction still helps when search is enabled:
versus parent+search, each correction gains3.90625 points against heuristic,
paired interval [+0.78125,+7.8125]; against search_geo the gain is3.125 points,
interval [0,+7.8125]. Retain the parent control and both seeds.
All576 independently collected guided games have zero game/search caps.
The combined comparison verifies both 2p cases, explicitly partial relative
to the three-case protocol because A260 remains running. Raw revision for the
first five arms: `0fa5c86d2550499c1ad2100b1b6d4ae6be7f1fc1`; sixth arm
10102/search_geo: `7512fc2d33fb1d7653be0e8a3717d9fe0e594a20`.
Durable complete 2p evidence: `ebf6cdce5d571f1067082985a819d053ea16d753`, prefix
`runs/search-transfer-2p-completed-evidence-v1`. The earlier five-arm snapshot
remains immutable at its earlier revision.

Collect completed results at immutable revisions:
`collect-search-transfer.py KEY CASE REV ai/runs/search-transfer-verified-v1/KEY-CASE`.
Compare all three models in each completed case with
`compare-search-transfer.py DIRECTORY OUTPUT [--cases CASE ...]`. It rechecks
raw contracts, caps, hashes and paired whole-deal/rule contrasts. A partial
case collection must not be called the full1,152-game result.

**8840U diagnostic completed and independently verified.**
Research directory `/home/coyotte508/powergrid-ai-search-transfer-probe-v1`
on `ssh minipc`; source/models use the immutable search-transfer pins.
All 8,013 requests are legal, model/schema/order match, 174 discard responses
are preserved under the search configuration, and all 43,200 rollouts finish
without truncation. Each model served all 2,553 saved public positions raw,
then 118 search-configured requests: one median-round root in each of the
60 player-count/rule/strategic-action strata, plus all 58 discard roots.

| Model | Raw median / p95 | Strategic search median / p95 | Search maximum |
| --- | ---: | ---: | ---: |
| parent | 2.54 / 5.03 ms | 1.083 / 2.027 s | 2.291 s |
| 10101 | 3.13 / 5.47 ms | 1.098 / 2.017 s | 2.321 s |
| 10102 | 3.09 / 5.40 ms | 1.113 / 2.064 s | 2.346 s |

Raw timings exclude each worker's cold first request. Search timings count the
60 actual search decisions/model, excluding the cheap discard passthroughs.
Fixed sequential diagnostics are not significance tests, worst-case guarantees,
or evidence of game strength. No training or production routing. Full per-request
responses, timings and immutable fixtures were independently rechecked by
`strong/collect-search-transfer-8840u.py`. Device report:
`strong/search-transfer-8840u-probe-v1.json`. Durable evidence revision
`3ffca6810bfddd1be50f1c2a7acf7b9416eac478`, prefix
`runs/search-transfer-8840u-completed-evidence-v1`. This establishes plausible
bot-job latency for the current configurations, not qualification of a model.

**Next:** collect the remaining raw5–6p/search cases, then extend guided
evaluation to3–6p against the independent search reference. Current search
transfer covers only2p and3p A260; it cannot establish4–6p strength. Use the
full-game search-versus-raw changes to select the next training recipe.
Search wins do not automatically supply reliable hard labels: earlier teacher
continuations were policy-dependent. The complete Germany2–6p strength gate,
reserved held-out tests and benchmark of the eventual exact qualified policy
remain required. Other maps and score calibration are not demonstrated.

## Earlier: learned discard gains transfer to independent 2p opponents

The preceding goal turn was **progress**: verified the runtime probe and launched
three complete 2p opponent evaluations. This turn is **progress**: all 1,344 games
are independently verified, with every raw artifact, model/source pin,
seat/rule/deal, outcome credit, search diagnostic and aggregate checked. The
combined collector has now run successfully on the complete 2p subset. Both
runtime probes are verified and all remaining full shards are launched. Zero
actual-game/search truncations. No final seeds or model promotion.

| Opponent (2p) | Parent | Seed 10101 | Seed 10102 |
| --- | ---: | ---: | ---: |
| legacy | 92.97% | 95.31% | 95.31% |
| heuristic | 63.28% | 71.09% | 71.09% |
| rush | 53.91% | 71.09% | 71.09% |
| search_geo | 23.44% | 50.00% | 50.00% |

Both training seeds have identical per-game win credits on this subset (not a
claim that trajectories or final states are identical). Against search_geo,
the paired gain is +26.5625 percentage points, whole-deal bootstrap 95% interval
[+15.625,+39.0625]. Candidate win-share interval is [37.5%,60.9375%]: this does
not establish an advantage over chance. Only eight independent search deals
(64 games/model). The other opponents have 16 deals each (128 games/model).
Heuristic gain +7.8125 points, interval [+3.90625,+12.5]; rush gain +17.1875,
[+10.9375,+23.4375]; legacy gain +2.34375, [0,+6.25]. All are marginal,
exploratory development intervals. Search and heuristic remain below their
55% and77.5% 2p point floors; the earlier A260 gap also remains.

Search_geo rule-cell win shares (original/open, original/sealed,
Recharged/open, Recharged/sealed): parent 12.5/31.25/31.25/18.75%; both
corrections 56.25/50/62.5/31.25%. Do not hide the remaining Recharged sealed
weakness. Both seeds remain candidates for further development, not deployment.

Raw immutable revisions: parent `6798691ac954c9c95702fea5476920062b61631e`;
10101/10102 `c378cd1437fc6bd3fc340c94aca20142d5de5c73`. Local collections:
`ai/runs/discard-opponents-verified-v1/{parent,10101,10102}-2p`.
Summary `strong/discard-opponents-results-v1.json` explicitly records only 2p
and `all_shards_verified: false`. All three full 2p HF jobs are COMPLETED;
do not relaunch. Durable combined evidence is pinned in
`strong/discard-opponents-2p-evidence-v1.json`.

**Both runtime probes completed and independently verified.** The 6p probe
`6aca4fcf095c5780893136a4` completed before15:11:04 UTC. All96 games verify at
raw revision `029d32c11af9310383d942c748202b32719cf487`; search_geo took
1,418.27s (23.64min),448,816 rollouts,zero caps. Combined endpoints:128 games,
483,520 search rollouts,zero caps. Both probes are complete; do not relaunch.
Durable runtime/launch evidence is revision
`3e79eccc2e5219b9a543c32a0fadcd9ee0ad219e`, prefix
`runs/discard-opponents-runtime-completed-evidence-v1`. Earlier partial evidence
remains immutable at its old revision. Full2p evidence is revision
`029d32c11af9310383d942c748202b32719cf487`, prefix
`runs/discard-opponents-2p-completed-evidence-v1`.

**All12 remaining 3–6p shards launched**, 12,096 games, completing dispatch of
all13,440 prescribed games. The 6p linear projection is3.20h; doubling it and
adding120s setup gives6.44h. A9h HF timeout preserves25% extra execution
headroom. Counts3–5 conservatively use this endpoint estimate; their runtime
was not directly measured. These are scheduling budgets; actual-game1600 and
search2400 cutoffs, frozen source, opponents, models and seeds are unchanged.
2p jobs used4h. Jobs needing more than12h under this rule must be partitioned.
No strength criteria were relaxed.

Authoritative status at15:13:46 UTC:4 new jobs RUNNING,8 SCHEDULING. Every
new job is CPU-performance,9h; no duplicate launches. Exact handles:

| Shard | HF job | Last status |
| --- | --- | --- |
| 10101-3p | `6aca55eafee2c900701891e9` | SCHEDULING |
| 10101-4p | `6aca55ebfee2c900701891eb` | SCHEDULING |
| 10101-5p | `6aca55ecfee2c900701891ed` | SCHEDULING |
| 10101-6p | `6aca55edfee2c900701891ef` | SCHEDULING |
| 10102-3p | `6aca55ed095c578089313ad4` | SCHEDULING |
| 10102-4p | `6aca55ee095c578089313ad7` | SCHEDULING |
| 10102-5p | `6aca55ef095c578089313ad9` | SCHEDULING |
| 10102-6p | `6aca55ef095c578089313adb` | SCHEDULING |
| parent-3p | `6aca55e6fee2c900701891e0` | RUNNING |
| parent-4p | `6aca55e6095c578089313acc` | RUNNING |
| parent-5p | `6aca55e7fee2c900701891e4` | RUNNING |
| parent-6p | `6aca55e9095c578089313ace` | RUNNING |

Launch guards are in `ai/runs/discard-opponents-launches-v1`. Collect only
completed outputs at immutable model-repo revisions using
`collect-discard-opponents.py KEY N REV ai/runs/discard-opponents-verified-v1/KEY-Np`.
The comparison script can report a complete-count subset while clearly marking
the suite partial. Do not duplicate or restart queued/live jobs after an
observation timeout. No candidate is promoted and reserved final seeds are unused.

**Independent next work while these jobs run.** A development-only proposal is
saved in `strong/search-transfer-protocol-v1.json`, not implemented or launched.
It pins allthree current models and exact raw baseline artifacts for2p heuristic,
2p search_geo, and3p A260. Test fixed public search48 with geographic proposals
and the model proposal, all existing strategic phases. This would be1,152 new
complete games on intentionally reused paired development deals, keeping each
seed and every adverse rule cell separate. Before any launch, freeze its wrapper,
verify schema4.2 search/menu compatibility and retained discard behavior, and
measure HF search48 runtime. The nine pinned raw baseline files (1,152 games)
were independently rechecked; `strong/search-transfer-plan-check-v1.json`
explicitly marks compatibility, runtime, packaging and launch as still unproved.
Do not derive new hard labels from mixed-policy
winners without evidence: prior continuation audits showed policy dependence.
Historical search48 on the older b052 model achieved42.08% againstA260 over480
games but failed some rule-cell confidence requirements; that does not establish
performance for the current weights. The full2–6p strength gate and exact-config
AMD8840U benchmark remain unchanged. No new gradients occurred this turn.

## Earlier: 4,800 complete games verified; broader opponents profiled


The preceding AI goal turn was **progress**: independently verified all three
learned-discard complete-game screens and started two HF runtime probes. This
continuation is also **progress**: independently collected the 2p runtime probe,
prepared a combined raw-artifact verifier, launched the three full 2p opponent
shards on their measured runtime, and preserved all positive and negative results. No qualification, deployment or reserved final
seeds. The UI remains at the published version.

All three correction-screen jobs are **COMPLETED**, with all 4,800 games
independently verified and zero actual-game or search truncations. Raw model-repo
revision `d6bbd10b729231bc574ad1037065c25d7fb0b61e`; local collection
`ai/runs/discard-correction-screen-verified-v1`. Summary:
`strong/discard-correction-screen-results-v1.json`. Durable combined evidence:
`d278ad42e2213dd3b4a4fcb1991f40b4572046bb`, prefix
`runs/discard-correction-screen-completed-evidence-v1` in
`coyotte508/powergrid-ai-germany-v1`.

| Opponent / count | Parent | Seed 10101 | Seed 10102 |
| --- | ---: | ---: | ---: |
| economic 2p | 55.47% | 69.53% | 70.31% |
| economic 3p | 58.85% | 61.46% | 60.94% |
| economic 4p | 60.55% | 64.06% | 63.28% |
| economic 5p | 71.88% | 71.56% | 71.88% |
| economic 6p | 72.79% | 72.01% | 72.27% |
| capacity-economic 2p | 58.59% | 75.00% | 75.00% |
| A260 3p | 37.24% | 36.20% | 36.20% |

These are actual complete-game win shares on 16 independent deals per cell,
all seats and four rule combinations. Both seeds improve economic 2p (+14.06 /
+14.84 points, paired whole-deal 95% intervals [+7.03,+21.09] /
[+8.59,+21.09]) and capacity-economic 2p (+16.41 points each,
[+10.94,+21.88]). Economic 4p gains are smaller but both intervals are positive.
Economic 6p slips by 0.78 / 0.52 points. Both A260 results are below the 40%
point floor and 1.04 points below the parent; the paired interval includes zero.
Keep both seeds; no winner or strong-model claim. All rule-cell estimates and
contrasts are in the report. These are marginal exploratory intervals, not
simultaneous confidence or the reserved final evaluation.

`strong/discard-parent-loss-profile-v1.json` describes overlapping terminal-loss
conditions, not causal move labels. Against A260, 83 of 120 parent losses have
nominal capacity below the winner's powered cities; 27 have too few cities
despite enough nominal capacity; 10 lose a powered-city tie on cash. At 6p
against economic, the larger category is insufficient cities (63/104), compared
with capacity shortfall (26/104). Unused nominal capacity can mean missing fuel;
it is not evidence of a plant-activation bug.

**Broader opponent extension.** Predeclared 13,440 fresh development games:
parent and both learned seeds, counts 2–6, all four rule cells and every seat,
versus legacy/heuristic/rush (16 deals each) and unchanged search_geo (8 deals).
No candidate search. Independent search_geo remains 16 samples, 6 candidates,
geographic proposals and horizon 2400. Actual-game hard cap remains 1600;
either cap invalidates a result. No engine or opponent changes.
Protocol `strong/discard-opponents-protocol-v1.json`, SHA
`191ab3a37cd1317cff6e7edbb865f33a1644a1d8be8235493dcc4dba60668f2c`.
Frozen source dataset revision `e44812ae307ae3e8a2b62306511d55b61d34720f`,
archive `strong-source-discard-opponents-20261010-v1.tgz`, SHA
`b40efa0c88e8b8a148bf44f955a50b1aa20804cc7e9eb09bd0f4f15efe31a880`.
All 1,370 base files are unchanged. Fresh main seed prefix
`discard-opponents-games-v1-{players}p`; separate smoke prefix
`discard-opponents-smoke-v1-{players}p`. Same pinned model manifest as above.

HF CPU-performance 4h probes launched 14:46 UTC:
- 2p seed10102: `6aca4fce095c57808931369e`, COMPLETED and independently verified
  at raw revision `d26b848916e6c360cec6f332cd01d5b6a0e837c4`.
  All 32 games pass; search_geo takes 108.33s and 34,704 rollouts, zero caps.
  Simpler opponents take 1.66–1.77s each.
- 6p seed10102: `6aca4fcf095c5780893136a4`, last observed RUNNING at
  14:54:38 UTC. Re-inspect this exact handle, never relaunch on log timeout.

Independent collector `strong/collect-discard-opponents.py` downloads immutable
raw artifacts, checks hashes/contracts/outcomes and recomputes every summary.
`strong/compare-discard-opponents.py` revalidates saved artifacts and compares
all three policies, retaining complete counts and every rule cell. It can mark
a complete-count subset explicitly partial; it never treats missing shards as
losses or successes. Runtime report builder `strong/profile-discard-opponents.py`
uses independently verified 2p and 6p smoke collections in
`ai/runs/discard-opponents-smoke-verified-v1/{2,6}p`.

**Full 2p shards launched at 14:58 UTC**, 448 games each (1,344 total):
- parent: `6aca529e095c578089313879`
- 10101: `6aca529ffee2c90070188f0f`
- 10102: `6aca52a0095c57808931387c`

The verified same-count smoke projects 2,019.53 seconds including the doubled
runtime margin and setup, below the existing 3h admission limit. The profiler
now admits counts independently: `--players 2` admits only 2p. Other counts
require their own probe or both endpoints; no unmeasured 6p work was launched.
No frozen runner, evaluation seed, model, opponent, game count or cutoff changed.
Each launch intent preserves the runtime basis and profile hash. Current profile:
`strong/discard-opponents-runtime-profile-v1.json` (only 2p verified so far).

Last authoritative check at **15:00:58 UTC**: all three full 2p jobs and the
6p smoke are RUNNING; the 2p smoke is COMPLETED. Statuses live in
`strong/discard-opponents-status-v1.json`. Verified 2p probe, collectors, runtime
profile and launch records are also durable in HF revision
`505379fca4e2c6091f96cd59af43fafc76ef8ea2`, prefix
`runs/discard-opponents-runtime-evidence-v1` (explicitly partial, only 2p).
Local real-artifact admission tests pass, including rejection of altered search
caps, wrong model/count, missing games and treating a smoke as a full shard.
The combined full-shard comparison awaits actual completed outputs.

**Next:** re-inspect the exact 6p smoke and three full 2p handles. Collect completed
full shards into `ai/runs/discard-opponents-verified-v1/KEY-Np`, then compare with
`ai/.venv/bin/python ai/strong/compare-discard-opponents.py ai/runs/discard-opponents-verified-v1 ai/strong/discard-opponents-results-v1.json --players 2`.
This explicitly marks the broader suite partial. On 6p probe completion,
independently collect it and rebuild the profile with both endpoints. Use measured
runtime to admit or split the remaining 12 planned shards. The launcher's 3h
planning limit and 4h execution limit remain unchanged. If too slow, shard the
workload without weakening opponents or cutting prescribed games. Full launch
intents live in `ai/runs/discard-opponents-launches-v1`; inspect before any retry.
The A260 deficit remains unresolved. The unchanged full multiplayer gate and
exact-model benchmark on the actual AMD 8840U are still required.

## Earlier: learned corrections trained, exported and verified

**Actual complete-game intervention, all960 games verified.** The fixed parent
wins50.3125%, economic-guided discards73.75%, neural-guided discards73.125% in320
fresh2p games per arm (40 deals ×2 seats ×4 rule combinations). Economic minus
parent is+23.4375 percentage points, paired whole-deal95% interval
[+19.6875,+27.34375]. Neural minus economic is−0.625 points, interval
[−1.875,+0.625]: no demonstrated neural advantage. All four economic-minus-parent
rule-cell intervals are positive. Every arm has282 identical public roots and
zero game/search caps. This intervenes at only the **first eligible discard**
per game against unchanged economic opponents; it does not prove a learned
policy or general multiplayer gain. Economic search took39.16s versus767.55s
for neural on HF CPU,72,192 rollouts each. Choose the cheaper economic teacher.
See `strong/public-discard-intervention-results-v1.json`.
Raw model-repo revision `248af172b9ebd0c5732de95903b9d64e27a6223a`;
combined verified evidence `6c48f461d31ee25ca95798aec1a1522974831096`,
`runs/public-discard-intervention-completed-evidence-v1`.

**Fresh training data.** All5,120 collection games and uninstrumented twins are
verified (10,240 engine games):2–6p, every seat, original/Recharged, open/sealed,
four opponent families. Every eligible late discard is captured, including
repeated discards. Opponents: economic/rush/frozen parent at all counts, plus
capacity-economic at2p or heuristic at3–6p. No result-based filtering.
3,361 sanitized public roots:2,527 train,834 validation, separated by whole
(count,opponent family,deal), including all seats/rules/repeated roots together.
Root counts by players2–6:631/458/610/857/805. Every original model proposal,
legal menu, public-state hash and twin trajectory independently reproduced;
zero caps. See `strong/discard-training-collection-results-v1.json`.

**All teacher labels independently verified.** Economic continuations,64 public
scenarios per legal action,685,696 rollouts,zero truncations. Original private
seed/deck and future moves are excluded. Store all per-sample outcomes and ties;
retain all positions. Full five-plant features preserve the old prefixes/menu;
every parent logit was recomputed with zero discrepancy. Raw labels revision
`9b2d0a8ef63fb6da13df6961af153725c35e8c68`, prefixes
`runs/discard-training-labels-v1-Np`. All ten collection/label jobs are COMPLETED;
IDs/statuses live in their tracked status files. Do not relaunch them.
Combined durable evidence in `coyotte508/powergrid-ai-germany-v1`:
`8882fe1eda0cc0b6262e48b46daa555c4b7fb8d6`,
`runs/discard-training-completed-evidence-v1`. Reports:
`strong/discard-training-labels-results-v1.json`,
`strong/discard-training-evidence-v1.json`.

**Learned corrections trained and independently verified.** HF job
`6aca4a1b095c5780893132ed` is COMPLETED (verified14:26:15UTC10October), one L4,
fixed seeds10101/10102,120 epochs and1,200 optimizer updates each. Both selected
epoch10 under the predeclared validation rule; later epochs overfit. The376,001
parameter head takes3.37/3.12s to train, peak allocated GPU memory57.7/57.0MB.
More GPUs would not help this stage; collection and validation dominate.
No local gradients. Launch intent: `ai/runs/discard-correction-launch-v1/launch.json`.
Protocol `strong/discard-correction-protocol-v1.json`, SHA
`aa7bf7bc6a33ac5ea637fabf23d787a481b10496acd228b3fd2eab8504757cdb`.
Dataset source revision `70acf6d6c9eb743aedadc48e38b143ff511803f8`, archive
`strong-source-discard-correction-20261010-v1.tgz`, SHA
`59bf548ea4fa49f848609179a02cd8d692a76f713ff81df83312ff1c150d0bdf`.
Output prefix `runs/discard-correction-v1`.

The parent update79 FP32 checkpoint is frozen exactly. A small head learns
centered action win-credit means, preserving paired-scenario differences and
all ties. Roots receive equal total weight by count, then family, then deal.
Only public late multi-choice discards may use the head; require predicted gain
>0.025 over the parent proposal, otherwise retain parent. This applies to every
eligible discard, not only the first. Schema4.2 appends one public eligibility
bit to schema4.1:state1216/action100. No hidden info or phase-history memory.
Parent inputs are exact old1149/98 prefixes; value outputs stay the uncalibrated
parent estimates. No forced old-economic tie fallback. Both seeds run fully;
best checkpoint is lowest held-out label regret every5epochs, with epoch0
parent baseline and ties retaining the earlier epoch. These are simulated
conditional label metrics, never actual win rates. All gradients run on HF.

Preflight:2,553 menus/prefixes/public eligibility checks; strict zero-head
native64/ONNX parity over2,553 fixtures plus all3,361 labels; parent choices
unchanged everywhere and outside-scope logits identical. Frozen package repeats
all checks and independently re-verifies631 labels. See
`strong/discard-correction-preflight-v1.json`. Both trained exports pass the job and independent strict native/ONNX/serving
checks on all2,553 fixtures, plus all3,361 label inputs. All parent tensors and
2,544 outside-scope decisions remain identical (logit error0); eligible fixture
changes are5/9 and4/9. Largest native/export logit error4.75e-10.

Raw training revision `b115a2d78aae095e51fb72a5535b3507abdf90c0`, prefix
`runs/discard-correction-v1`. Independently verified local outputs:
`ai/runs/discard-correction-verified-v1-recheck`; tracked report
`strong/discard-correction-results-v1.json`. Durable combined evidence revision
`727848e6a675fe749211a2222ca0efd9826b3d23`,
`runs/discard-correction-completed-evidence-v1`. The first collector stopped on
one-ULP float32 weighted-statistic rounding across BLAS builds. Recheck allows
absolute1e-7 only for aggregate gain/regret fields, with exact counts and a
rejection regression; native/ONNX tolerances are unchanged. Failed artifacts and
an explanation are retained. This was no retraining or model repair.

Held-out **conditional simulated gains**, not actual game win gains:

| Seed | 2p | 3p | 4p | 5p | 6p |
| --- | --- | --- | --- | --- | --- |
| 10101 | .21860 | .02625 | .02426 | .00385 | −.00986 |
| 10102 | .22773 | .02625 | .02589 | .00073 | .00000 |

Do not hide the6p regression for10101 or choose a winner from this alone.
Selected export SHA256:10101
`bb0790074d2df1a4929c059b61424da72ddf4fc51cf9396a91a27c031934808d`;
10102 `57f8255e79b991ba466f91e953d0bca6868144bb543577fc0dad8ade387ebf68`.

**Complete-game diagnostic now launched.** Three arms(parent,10101,10102),
1,600 games each:16 fresh deals ×all seats ×4 rule cells versus economic at
2–6p, plus capacity-economic2p and A2603p. All eligible discards may use the
learned head; this tests repeated-discard deployment, unlike the original
first-discard intervention. No training or final seeds. Report paired whole-deal
bootstrap differences and every rule cell; keep the two seeds separate.
Protocol `strong/discard-correction-screen-protocol-v1.json`, SHA
`88d9439a15d20724ae5a155e36b17f2ba54017f971a2c65511ca7fee2023a070`.
Source dataset revision `63db2c7e4b870bf019436a6338c9385f3bad82a6`, archive
`strong-source-discard-correction-screen-20261010-v1.tgz`, SHA
`2ee290d6a7c5863fcfea9ebefa1b00515776be8174e22662870e86e547a04d4d`.
All1,366 base files stay unchanged. Frozen preflight:108 complete smoke games,
all models at2p/6p plus mixed-schema A2603p, zero game/search truncations.

| Arm | HF CPU-performance job |
| --- | --- |
| parent | `6aca4c50095c578089313476` |
| 10101 | `6aca4c51fee2c90070188a1c` |
| 10102 | `6aca4c51fee2c90070188a1e` |

All three jobs subsequently completed and all games were independently verified;
see the latest section above. Do not relaunch these completed jobs.

## Earlier: all 34,720 precision reruns verified; discard audit and intervention setup

The preceding AI goal turn was **progress**: it independently verified all nine
completed screens, exposed a gap in discard search coverage and collected fresh
public discard roots. This turn is also **progress**: verified the frozen audit
package, launched five HF CPU jobs for all 189 roots, independently collected the
all five audits (229,248 rollouts), and launched a fresh complete-game intervention test. No
external blocker.

**Completed comparisons.** All nine precision reruns are authoritatively COMPLETED;
all 34,720 raw games have been independently checked, including exact paired
seat/rule/deal coverage, original training provenance, all 2,553 strict numerical
and legal serving requests per screen, and zero game/search caps. All 19,040
available earlier FP32 terminal result records match their FP64 reruns exactly;
this is not full action-trace equivalence. Original failed FP32 checks remain
failures. Summary: `strong/inference64-results-v1.json`; raw game-record audit:
`strong/inference64-game-record-audit-v1.json`. Durable combined evidence is model
repo `coyotte508/powergrid-ai-germany-v1`, revision
`a9a33c938b0f2cfcef4aa0e442d1b14bcac4bc16`, prefix
`runs/inference64-completed-evidence-v1`. Raw population revision:
`1c1af00ae2c355c1f5c9382cff5dead96f0e4bd7`; raw five-plant revision:
`76307c9e7d820644573c00a3e2afee2eb5a8fbff`.

- Population comparison: all six overall heterogeneous-minus-homogeneous paired
  intervals include zero. Both retained-opponent arms beat control at 4p; control
  regresses against parent there. Highest 2p economic win share is 61.875%, below
  the 66.25% floor. One training seed; exploratory marginal intervals, no
  multiplicity adjustment. There is no clear recipe winner to promote.
- Five-plant feature ablation: full-minus-control economic point estimates are
  negative at every count for both training seeds. Clear overall regressions
  include 6p seed10031 (−8.333 percentage points), capacity-economic 2p seed10031
  (−8.438), and 5p seed10032 (−5.625). Both A260 deltas are negative but uncertain.
  This recipe has no demonstrated benefit from the added inputs; that does not
  show that the information itself is useless. Keep seed contrasts separate.

**Why investigate discards.** The existing search gate covers plant choice, bids
and building, but not `DiscardPowerPlant`. In the 2,553 serving fixtures there
are 58 discard positions and zero searched discards. PPO does update those
moves; do not say discards receive no learning. The old economic discard rule
also maximizes income without its endgame mode. See
`strong/discard-search-coverage-v1.json` and `audit-discard-coverage.cjs`.
Do not change the independent reference opponents to make a candidate look good.

**Fresh public roots.** HF collection job `6aca3874fee2c90070187ba0` is COMPLETED.
320 fresh games across 2–6p × all seats × original/Recharged × open/sealed yield
189 first eligible learner discards (30/21/36/49/53 by count). Eligibility is the
public condition max cities ≥ end threshold−3, never the eventual result or last
discard of a completed trajectory. Every game matched an uninstrumented twin
at every observation/action and terminal record: 640 engine runs, zero caps.
All 189 sanitized public roots independently reproduce the original parent
model's proposal. Keep the three absent rule/seat cells absent: coverage77/80,
no outcome-driven resampling. Raw data revision
`1a9027f0b9c76d86846c3987df0687dcd12f9dd5`, prefix
`runs/public-discard-collection-v1`; root SHA
`268ab59096b3600dd61c10c7622696cacf033ff6902853e0b596b2014df38e0a`.
Tracked report: `strong/public-discard-collection-results-v1.json`.
These are development data, not a strength result or accepted teacher labels.

**Completed HF audit.** All legal discards on every root, three continuation
policies (economic/heuristic/neural), two independent batches of64 public-belief
scenarios: 229,248 independently verified rollouts, zero caps. Identical scenarios within a batch across
moves and continuation policies. No actual private deck/seed or future moves.
Neural continuations use the fixed original update79 parent for every actor;
that is an explicit modelling assumption. Record all ties and sample results.
Any cap makes that target invalid, never a loss. Protocol:
`strong/public-discard-teacher-protocol-v1.json`, SHA
`3b42768997a9f85ca462961448143e385b84bef3878bb27dbc48b03ea2200e09`.

Frozen source dataset revision `52041c96794e0b3c76065ea5538c87b1a878d58f`,
archive `strong-source-public-discard-teacher-20261010-v1.tgz`, SHA
`9bfaa1bbfe95bc5a2c1392e56128315604fe401c9063ed35e7b05ee5410615ff`.
The collection base is preserved byte-for-byte except the five explicit audit
files; 1,338 base files unchanged. Frozen 2p/6p smokes reproduce every original
sample/action outcome exactly (84 rollouts, zero caps). Three continuation
regressions pass: economic/heuristic reference agreement, caps/legality/worker
offsets, hidden-deck/bid invariance. The independent collector rejects missing,
duplicate, miscomputed or silently capped evidence and reports valid caps as
invalid targets. Preflight: `strong/public-discard-teacher-preflight-v1.json`.

HF CPU-performance jobs (4h timeout, launched 13:24UTC):

| Players | Roots | Planned rollouts | Job |
| --- | --- | --- | --- |
| 2 | 30 | 46,080 | `6aca3c8b095c578089312a44` |
| 3 | 21 | 24,192 | `6aca3c8cfee2c90070187e70` |
| 4 | 36 | 41,472 | `6aca3c8d095c578089312a46` |
| 5 | 49 | 56,448 | `6aca3c8d095c578089312a48` |
| 6 | 53 | 61,056 | `6aca3c8efee2c90070187e72` |

All five audit jobs are authoritatively COMPLETED and independently collected.
Status is in `strong/public-discard-teacher-status-v1.json`; do not relaunch them.
Each wrote `runs/public-discard-teacher-v1-Np/{audit-check.json,rows.jsonl}`.
For reproduction pin the recorded model-repo revision and run
`collect-public-discard-teacher.py N REVISION ai/runs/public-discard-teacher-verified-v1/Np`.
It independently recomputes every target and both batch/policy comparisons.
Cross-batch gain selects on batch a and measures on b, then reverses: it is still
simulated continuation return, not actual strength. The resulting complete-game
intervention test is below; do not train from guidance or promote a policy until
its benefit is independently verified. Full engine/inference timings are saved
by count in the result manifest. No gradients ran locally.

The full verified audit is `strong/public-discard-teacher-results-v1.json`.
Durable model-repo evidence revision `29f803c518d18b3acfe93d54c82ccd69095d841e`,
prefix `runs/public-discard-teacher-completed-evidence-v1`, includes every raw
sample, count/rule summary, verifier, protocol and intervention preflight.
Neural selected-action agreement across independent batches is188/189 with the
specified tie rule; 28 positions consistently change the parent proposal.
Conditional simulated cross-batch mean gains by count:

| Players | Roots | Economic | Neural | Consistent neural changes |
| --- | --- | --- | --- | --- |
| 2 | 30 | .21120 | .22005 | 9 |
| 3 | 21 | .17411 | .13876 | 5 |
| 4 | 36 | .14692 | .12174 | 10 |
| 5 | 49 | .01244 | .00925 | 3 |
| 6 | 53 | .01312 | .01179 | 1 |

These are returns conditional on captured public roots and the assumed
continuation policy, not actual win-rate improvements or independent games.
The pattern supports prioritizing2p while retaining the full multiplayer scope.
For2p total measured HF timing is118.004s engine and67.926s policy (560,163 neural
decisions) over all46,080 rollouts; this differs from the initial one-root local
smoke and is the appropriate evidence for later hardware decisions.

**Fresh complete-game intervention launched.** The independently verified 2p audit
has 46,080 rollouts and zero caps. Neural batch choices agree29/30; both batches
change the parent proposal in9/30 positions. Economic choices agree27/30 and
change10/30. Mean cross-batch simulated gain is .2201 neural and .2112 economic;
these are conditional simulated returns, not arena win gains. The verified3p
and4p audits also suggest stable changes;5–6p gains are much smaller. Full count/rule summaries are in the
local `ai/runs/public-discard-teacher-verified-v1/Np` directories. All roots,
ties, disagreements and adverse strata remain in the evidence.

The next causal test uses40 fresh independent deals ×2seats ×4rule combinations
=320 complete games per arm: parent, economic-guided discard, neural-guided
discard (960 total). The only intervention is the first eligible learner discard
in each game, chosen with64 independent public-scenario rollouts. All other
moves remain the same frozen parent policy. Keep the parent proposal on ties.
Economic opponents are unchanged; there is no training or deployment.
This is an explicitly focused2p development experiment, not a narrowed strength
gate. Any gain must still survive every2–6p/rule cell and independent opponents,
then an appropriately trained/exported candidate and the reserved final tests.

Protocol `strong/public-discard-intervention-protocol-v1.json`, SHA
`e50f6b471b0af055eb80048a127b2aea06f01034d437cedba03f1ed4d12c6b76`.
Fresh game prefix `public-discard-intervention-games-v1-2p`; separate search RNG
prefix and separate smoke deals. Prescribed three contrasts, whole-deal paired
bootstrap with10,000 replicates/seed8543, overall and every rule cell. Marginal
exploratory intervals, not multiplicity adjusted.

Source dataset revision `7bc8f890992d3c44faa38a7241521f6d1736d9ea`, archive
`strong-source-public-discard-intervention-20261010-v1.tgz`, SHA
`ecc08c7b64634d83e2f1b023b3a890be1b2368c1434f985287b59950b160583c`.
All1,343 audit-base files unchanged; only the new protocol/harness overlaid.
Local three-arm smoke8games/arm: all pre-intervention public roots, legal menus
and parent proposals identical. Unchanged arm's8 terminal records match a
separate uninstrumented engine control. Frozen-source smoke repeats every
root/action/sample outcome and complete-game record exactly for all three arms.
No game/search caps. `strong/public-discard-intervention-preflight-v1.json`.

HF CPU-performance jobs launched13:34UTC (4h timeout):

- Parent: `6aca3ef4fee2c90070188056`.
- Economic continuation: `6aca3ef5fee2c9007018805e`.
- Neural continuation: `6aca3ef6fee2c90070188062`.

Inspect `strong/public-discard-intervention-status-v1.json` and those exact HF
handles before any follow-up. At the latest authoritative observation parent and
economic are COMPLETED; neural is RUNNING with29 recorded roots and no reported
error. The full intervention comparison has not yet been independently collected.
Artifacts are
`runs/public-discard-intervention-v1-ARM/{intervention-check.json,games.json,roots.jsonl}`.
After all three finish, pin a model-repo revision containing all three and run
`collect-public-discard-intervention.py REVISION ai/runs/public-discard-intervention-verified-v1`.
That collector independently rechecks hashes, complete paired games, all legal
public roots and original model proposals, every search sample/target, unchanged
pre-intervention roots across arms, and paired result intervals. A successful
job alone does not establish benefit; do not train/promote from uncollected results.

The collection/audit preflight evidence is also saved at model revision
`443a96ead2624a87e2ec53f169b7f905a1ed8116`, prefix
`runs/public-discard-preflight-evidence-v1`; manifest
`strong/public-discard-preflight-artifacts-v1.json`.

**Preserved inference evidence.** Eight unique derivatives at model revision
`f14d0db14edb494c8797af00a546ac56088cfa96`, prefix
`runs/inference64-cohort-v1`, pass all 2,553 strict export/serving requests each.
Stored weights and float32 inputs unchanged; float64 internal inference, same
rtol1e-4/atol1e-5. Max native64 logit error6.053e-10, zero fixture action changes.
Actual AMD8840U parent FP64 median/p95 full-request latency2.709/5.235ms; full
s10031 FP64 2.763/5.308ms. Four configs ×2,553 legal requests in an isolated
probe, no deployment. Evidence revision
`5b3e67be71ed911bcef458f6c9c0ed6a6c0c9091`, prefix
`runs/inference64-8840u-probe-v1`; report `strong/inference64-8840u-probe-v1.json`.
The eventual selected winner still needs the full independent strength gate,
reserved tests, a standalone package and a benchmark on that exact machine.

Everything below is historical context. Current handles and next actions are above.

## Previous continuation: numerical repair prepared; both old coordinators ended with errors

Authoritative HF inspections confirm **all training jobs completed**, sealed-menu
pair **COMPLETED**, and both old coordinators **ERROR**. Do not treat their old
RUNNING state snapshots below as current, or blindly restart either coordinator.
The failures are export parity failures, not lost training checkpoints.

- Five-plant control-s10032 screen completed and was independently verified at
  revision`c23b06ec36efd1dc59bde7e43a5bdf66045d0f9a`:4,000 games, zero caps, all2,553
  strict export and legal serving checks. Economic2–6p win shares are
  54.688/65.625/64.297/82.125/78.542%; corrected economic2p51.25%; A2603p39.792%.
  It still fails two-player and A260 floors. This is a masked-input control;
  it does not establish the effect of fifth-plant inputs. Full report:
  `strong/five-plant-control-s10032-screen-v1.json`.
- The other three five-plant screens stopped before arena games on
  `check-export.py`'s unchanged`rtol=1e-4, atol=1e-5`. Each first failure was one
  small logit differing by1.1444092e-5. Reports/logs remain at
  `runs/five-plant-screen-v1-{control-s10031,full-s10031,full-s10032}`,
  model snapshot`de70c5cbd57bcdf34a5b906b4dea92ffcb693a38`.
- Population control update19 also failed parity before its six arenas, at
  checkpoint revision`2c7a715f609b9d7f4d55d646191414f0245590de`. First failing logit
  differs by1.5258789e-5. Frozen coordinator logs are at
  `runs/population-coordinator-v1/control-u19/{prepare,parity-check}.log`, snapshot
  `f25045c917ea697164c3044bac4a3ea0ec72c5eb`. The all-arm update19 comparison has
  **not** been completed. No future evaluation should claim these original
  FP32 failures passed.

For full-s10031, a complete local audit of all2,553 fixtures found one failing
logit position and zero value/action mismatches. All four ONNX optimization
levels (all/extended/basic/disabled) had the same failure; changing optimization
does not fix it. `strong/audit-onnx-numerics.py` records all errors without
loosening the assertion or treating missing checks as passing.

An explicit **inference-only float64 derivative** now exists for the parent and
all four five-plant finals. Stored checkpoint parameter values stay unchanged;
original float32 feature inputs are cast to float64 *inside* the network.
The model loader only enables this with explicit checkpoint metadata. Training
rejects inference-only checkpoints; resume from their pinned original source.
No optimizer ran. Old default inference behavior remains unchanged.

Native SiLU exported to float64 hit an ONNX Runtime QuickGelu fusion with no CPU
double kernel. The versioned derivative`float64-exp-div-silu-v1` uses the
mathematically equivalent`x/(1+exp(-x))` expression, keeping supported operators.
The initial unsupported export and original parity failures are preserved.
This is a numerical derivative with a distinct model hash, not a claim that the
original FP32 export passed or that all complete-game decisions are identical.

**All five derivatives pass all2,553 strict PyTorch/ONNX checks and legal serving
requests**, with the same unchanged tolerance. Maximum logit errors are
4.18e-10–5.90e-10. Local serving timings are from the HX370, not AMD8840U.
Artifacts: model revision **`309ce38ad1609d8a8f296860d8488f9681add327`**,
`runs/five-plant-inference64-v1`; each key has`inference64.pt`, `inference64.onnx`,
`derivative.json`, `parity.json`, `serving.json`. Source model/export scripts and
complete hashes accompany them. Tracked provenance:
`strong/five-plant-inference64-{validation,artifacts}-v1.json`.

The five remote derivative checkpoint/model hashes were downloaded and verified.
Additionally, full-s10031's Exp/Div ONNX passes all2,553 unchanged strict checks
against a **native-SiLU float64 PyTorch reference** (maximum logit error5.894e-10,
all actions match). This checks the activation rewrite independently for that
model; the whole-cohort FP32-to-FP64 action-change audit is still pending.
Detailed failed exports, optimization-level audit, unsupported native64 export,
native-SiLU comparison and86-file original replay runtime check are persistent at
model revision **`13e956d360fc2a0f8545d9a9900873f281e5895f`**,
`runs/export-numerics-investigation-v1`. Tracked manifest:
`strong/export-numerics-investigation-v1.json`.

**Next actions:** check native64-versus-Exp/Div equivalence and record FP32-to-FP64
chosen-action changes; prepare the missing population finals in the same explicit
precision; freeze a new repair evaluation protocol/source and evaluate every
candidate and parent uniformly on the original prescribed development deals.
Use new run names and preserve original failed screens. Do not reuse FP32 game
outcomes as FP64 outcomes, move to a convenient earlier checkpoint, relax
tolerances, or claim the numerical repair qualifies a model. Actual8840U latency,
the complete independent strength gate and reserved final tests remain pending.

## Sealed-menu experiment complete: no robust gain, not promoted

Independent verification at model revision
**`de70c5cbd57bcdf34a5b906b4dea92ffcb693a38`** reproduces the remote comparison
exactly:15,040 complete games, zero caps, all3,760 paired open-game records
identical, both conditions'2,553 strict export and legal serving checks.
Comparison SHA`87961dcb4af1f7ddb43daf1ffed20f3c8ee42230ce7b4e5c64e889a222204342`.
All13 opponent/count cells and rule strata are retained in
`strong/sealed-menu-results-v1.json` and local`ai/runs/sealed-menu-comparison-v1`.

Expanded-minus-control economic2p is+1.875pp, paired whole-deal95% interval
[-0.3125,4.0625]; versus full-sealed economic2p it is+0.938pp[-2.5,4.0625].
A2603p changes only+0.208pp[-1.667,1.875]. Economic5p regresses1.375pp;
Recharged/sealed5p regresses3pp[-6,-0.5]. Against full-sealed economic3p,
Recharged/sealed regresses5.833pp[-10.833,-0.833]. These are marginal exploratory
intervals, not multiplicity-adjusted; no broad improvement is established.
Expanded two-player rates remain55–58.125%, and A26031.458%, below the gates.
**Do not promote the full menu as a strength improvement or retrain blindly on
this recipe.** The infrastructure may support future training, but current
unchanged weights do not benefit reliably from it.

## Earlier this turn: late discard failures isolated

All four H200 input-ablation trainers are **COMPLETED** (authoritatively inspected
at approximately12:17 UTC). The existing coordinator launched all four final
screens; do not duplicate them:

| Key | Final evaluation job |
| --- | --- |
| control-s10031 | `6aca2d08095c5780893122b9` |
| full-s10031 | `6aca2d0bfee2c9007018750f` |
| control-s10032 | `6aca2c0e095c5780893121dd` |
| full-s10032 | `6aca2c8b095c578089312280` |

The coordinator was live; its12:18 snapshot was model revision
`538b91d2fe39f5104c10768ccd2b6bc889c7ac04`. Evaluations were pending, not verified
model improvements. Use `runs/five-plant-coordinator-v1/state.json` and inspect
actual screen handles. Population control training and its coordinator remain
separate. Reserved final seeds remain unused.

### Conditional discard diagnosis: five selected losses can flip

Model: prescribed homogeneous update19, immutable model revision
`cc86f7a36392c829e44fd81d9dbf362cb74a0b1b`, ONNX SHA
`8606c6902806f7df82f7c687fa92746230b63c110d2654730b7913cbc68d3258`.
Selection was frozen before replay: first numeric development deal in each
rule/seat cell with a strict loss, rated capacity below the opponent's powered
count and at least50 final cash, plus the first strict win. There are69 eligible
losses in the320-game homogeneous2p report; only8 selected losses and8 selected
wins are traced. This is deliberately selected outcome sampling, not prevalence.

All16 original terminal records and entire public move traces replay exactly,
both without and with read-only auction instrumentation. Then enumerate all
**four engine-legal discards at the last learner discard** in each selected game,
and resume unchanged greedy neural/economic policies on the same actual deal.
All64 branches finish, every prefix before the intervention is identical, and
all16 original-choice branches exactly reproduce the complete original traces.
**Five of the eight selected losses have a winning alternative discard.** Every
branch, including unchanged losses and degraded winning controls, is retained.
For example, Recharged/open episode35 changes from a loss to a win by discarding
the one-city free plant13 instead of six-city plant31 at the last discard.

This establishes a causal effect *conditional on these selected roots, actual
deals and continuation policies*. Choosing the last discard uses hindsight;
it is not a deployable rule or a public-belief teacher. Do not train on these
outcomes, extrapolate a win-rate gain, or assume every low-capacity free plant
should be discarded. Fuel supply, money, timing and opponents still matter.
The original economic discard prior uses an income-minus-fuel-cost plan even
late in the game; investigate public endgame-aware discard guidance and its
interaction with the completed fifth-plant input ablation before further
training. New teachers/priors must be tested on fresh complete games and under
public-information scenarios, retaining existing independent strength gates.

An initial draft incorrectly enumerated all five held plants. The first branch
stopped at the exact-legal-set assertion: the newly purchased plant cannot be
discarded. No branch outcomes were analyzed then. Protocolv2 preserves all16
roots and enumerates the exact four legal choices; rejected draft and failure
log are retained. Do not describe this initial validation failure as a model
or game-engine failure.

Persistent artifacts: model repo `runs/two-player-discard-diagnostic-v1`, revision
**`ac6cf7294ae5d0d8aab5dadcb77f75b0c0fc2378`**. `evidence.tgz` contains all public
traces, auction ledgers,64 branch traces and intervention records, original
controls and rejected-draft evidence. Source scripts/protocols/selection and
hashes accompany it. Tracked files:
`strong/two-player-discard-diagnostic{,-artifacts}-v1.json`,
`strong/two-player-upgrade-selection-v1.json`,
`strong/two-player-discard-counterfactual-protocol-v2.json`,
`strong/replay-discard-counterfactuals.py`, and diagnostic preload scripts.
No optimizer steps, production change, or final seeds were used.

### Sealed-menu control independently collected; pair pending

Control result revision **`949d0f7f7699711953edc8278ffe6673eb4fff66`** is independently
verified: all13 cells /7,520 games, no caps, all2,553 strict export and legal
serving checks, exact source/model/protocol/fixture hashes. Local artifacts:
`ai/runs/sealed-menu-comparison-v1/control`. As an additional isolation check,
all1,760 paired open-game records match between old and full-sealed reference
opponents after excluding the intentionally different role names. Saved in
`reference-open-isolation.json`. Expanded-condition results and the required
3,760 cross-condition open-game matches are still pending at this observation;
the paired job remains live. Do not interpret control-only percentages as a
menu effect or compare them to different-seed population results.

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
