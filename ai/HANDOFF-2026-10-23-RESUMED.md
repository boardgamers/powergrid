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
  This now covers all 948 effective shard handles, including explicitly recorded
  hardware replacements. Original guards remain in
  `ai/runs/policy-iteration-labels-launches-v2/`; use
  `ai/.venv/bin/python ai/strong/manage-policy-iteration-labels.py status`.
  Older teacher, collection, inference-profile and development jobs are complete;
  their failed/replaced historical handles must not be retried.
- Production/UI checkout remains separate. Do not merge or publish research
  there as part of resuming training. Do not comment on GitHub issues.

## 25 October, 06:22 UTC — original HF L4 calibration submitted

The original training coordinator **PID 2825298 / session 39111** completed
`prepare_data`, `archive_data`, `package_source` and `launch_calibration`, and is
now waiting for its **original L4x1 job `6adda008046eb82b1ece300b`**. Direct HF
inspection reports **SCHEDULING**. The calibration was submitted at **06:22:00
UTC**; no gradient updates have yet been observed. Preserve this handle; do not
relaunch after a slow startup or an observation timeout. No full training job yet.

The train/validation archive is privately uploaded and verified:

- Rows: **313,783 training / 52,543 validation**; **366,326 export/parity positions**.
- Games: **1,920 training / 320 validation**; all 320 test games excluded.
- Unpacked bytes: **2,726,265,837**.
- Data HF revision: `ef52777ba41420d7dcd8cc455b610fcde8e873b5`.
- Data archive SHA256: `0cfb251639483c1369d6c7380f0721e02971dcd293c5f3e0ccaad27a59818f2e`.
- Data descriptor: `strong/opponent-surrogate-training-data-v1.json`, SHA256
  `c2b678fd4823fd8bc00a29ca8bf4d7d900dea51544b3c15a26b872cdada6c005`.
- Source HF dataset revision: `5700a0327486e7fd67a165cd0a9fbde6bb350828`.
- Source archive SHA256: `381c8e4cc4586c274d8e91b36ec7a962efcf5218a4b3ebe5de4d20c125542fbe`.
- Source descriptor: `strong/opponent-surrogate-training-source-v1.json`, SHA256
  `823c3cc6ce4e2de4ccda100ee96fb8162565a36911c1231114ffef51db6d4bdd`.
- The **15-file** actual source package passed its isolated source check and remote
  hash verification; this is separate from the earlier code-only package.
- Guard: `ai/runs/opponent-surrogate-training-launches-v1/calibration.json`, SHA256
  `480923a2740ae0648e11f5973b3ffb1c0b73b93da7edc07e2a14f46122031b8a`.

Submission checkpoint:
`ai/runs/opponent-surrogate-training-calibration-submission-checkpoint-v1.json`,
SHA256 `dfbe8a61112415b0929dcf45b3bd4d698da6a93f38335a34440886b4f5d83c9b`.
All 30 coordinator-pinned files remain unchanged. Do not manually run its collection
or training stages concurrently. It still owns calibration inspection/collection,
measured full-training admission and submission, independent full collection, and
validation selection. Any failure or unknown action stops for inspection rather
than replacing a job or changing the fixed dataset/design.

Next: observe the original calibration, let its owner collect actual throughput,
RSS/VRAM and complete exact-export parity, then train all four fixed seeds for the
full specified schedule. The newly implemented full-study coordinator/archive
remain unstarted pending actual learned selection and separate inference timing.
No model-quality improvement, selected candidate, production change or final-seed
use is claimed. This turn advanced data packaging and one HF calibration submission.

## 25 October, 06:20 UTC — full-study coordinator and archive tooling

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

## 25 October, 06:10 UTC — collection complete and training preparation running

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

## 25 October, 06:07 UTC — all collection jobs complete; full-study management ready

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

## 25 October, 05:59 UTC — source packaging and selected-opponent calibration tooling

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

## 25 October, 05:42 UTC — complete continuation cost evidence and job runner

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

## 25 October, 05:28 UTC — complete fresh-root evidence and training coordinator

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

## 25 October, 05:17 UTC — paired fidelity analysis verified

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

## 25 October, 05:09 UTC — cost evidence helper and hybrid recommendation

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

## 25 October, 04:56 UTC — resource search rejected; reference-cost calibration running

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

## 25 October, 04:39 UTC — paired continuation runner verified; full fresh-root jobs running

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

## 25 October, 04:22 UTC — full root-collection controls verified; resource archive watcher live

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

## 25 October, 04:07 UTC — fresh-root capture verified; HF calibration launched

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

## 25 October, 03:48 UTC — surrogate continuation integration verified

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

## 25 October, 03:26 UTC — frozen selection and held-out evaluation pipeline implemented

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

## 25 October, 03:12 UTC — full opponent collection started; training-result audit implemented

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

## 25 October, 02:56 UTC — HF training packaging/launch path implemented

Previous turn was progress (`bccc417`). This turn added:

- `strong/opponent_surrogate_hf_v1.py`: fixed 14-file Python runtime manifest,
  immutable archive/data recovery, isolated import check and calibration/full entry.
  No JS engine or private raw test records are required in this training package.
- `strong/package-opponent-surrogate-training-v1.py`: complete-corpus admission,
  train/validation-only data archive and source packaging. The data archive wraps
  the existing strict bundle in a `data/` directory, so its outer archive manifest
  does not change the training loader's exact file contract.
- `strong/benchmark-opponent-surrogate-training-v1.py`: HF/CUDA-only calibration,
  16 warmup + 128 measured gradient updates, both complete split evaluation timings,
  float64 export/parity time, CPU RSS and GPU allocation. Its outputs/checkpoint are
  explicitly runtime-only and cannot be adopted as the full trained model.
- `strong/launch-opponent-surrogate-training-v1.py`: dry-run/submit the original
  calibration and full handles, collect/verify calibration, recompute the four-seed
  80-epoch runtime estimate and admit full training only with measured reserves.
  No automatic replacements; ambiguous submissions preserve their original guards.
- `strong/test_opponent_surrogate_hf_v1.py`: **seven passing tests**, including
  isolated imports, source corruption, premature packaging/full-training rejection,
  measured resource boundaries, original handle reuse and local-gradient refusal.

All seven original training pipeline files retain their `bccc417` hashes, so the
nine earlier core/forward/export checks remain applicable. New preflight:
`ai/runs/opponent-surrogate-hf-preflight-v1.json`, SHA256
`49fcb2fda0f4d948c22e13fbb942a14f623b742e0156a6825ddb8f9870ad8828`.
Persistent code-only tree/check:
`ai/runs/opponent-surrogate-training-code-v1{,-check.json}`. No source/data upload,
GPU execution, new HF job or gradient occurred. Actual missing-data/source checks
refused before network calls or output creation. The dataset still must finish.

Current HF hardware was queried through `list_jobs_hardware`: L4×1 is 8 vCPU,
30 GB RAM, 24 GB VRAM and 400 GB ephemeral storage. It is validated again at launch.
The bounded GPU calibration timeout is 2h. Full-run time is measured update count
plus per-epoch validation, initial/final train evaluation and export cost for all
four seeds, with 15 min setup + 2x measured cost + 25% timeout reserve. CPU RSS gets
2x + 4 GB, GPU allocation 30% reserve. Oversized results refuse admission rather
than reducing epochs/data. Calibration gradient checkpoints are not candidates.

At **02:55:11 UTC**, original 6p job `6add610d1e112550ce7e64e1` was directly
RUNNING, **21/24 games complete**, no logged errors. The collector also checked the
same handle at 02:53:13 and returned RUNNING without starting any replay/replacement.
Live metrics after the initial zero sample measured **48%,60%,60%,55% CPU** and
roughly 3.9 GB RAM. Hardware/metric records:
`ai/runs/opponent-surrogate-hardware-snapshot-v1.json`,
`ai/runs/opponent-surrogate-runtime-live-metrics-v1.json`.
Resource coordinator **11670 / PID 1291091** remains live, **54 submitted /
34 verified**, no failures; all pinned code is unchanged. Snapshot:
`ai/runs/opponent-surrogate-hf-preparation-checkpoint-v1.json`.

Next: finish original 6p endpoint; collect/audit/archive joint calibration; admit,
dry-run and execute full fresh collection. After complete collection, prepare
`ai/runs/opponent-surrogate-training-data-v1`; run the packaging `archive-data`
command and `source ai/runs/opponent-surrogate-training-source-v1` (without
`--code-only`). Use the training launcher `calibration` dry-run then `--execute`,
`collect-calibration` on that original handle, and `full` dry-run/execute only after
verification. Full trained-result collector/independent export/behaviour review
remain to implement. Validation-only policy selection, held-out behaviour,
fresh paired continuations, full strength gates and actual 8840U hybrid proof remain.

## 25 October, 02:41 UTC — surrogate training pipeline implemented

Previous goal turn was progress: collection orchestration committed/pushed in
`0571cd7`. This turn implemented the next training stage while the original HF
calibration/resource jobs continued. No new HF jobs or gradients were started.

New files:

- `strong/model_opponent_surrogate_v1.py`: 433,217-parameter state/action scorer,
  initialized at the public economic prior. The state retains ordered player money,
  holdings and geography; shortlist membership is public feature 100.
- `strong/opponent_surrogate_training_v1.py`: compact six-candidate tensors,
  integrity/whole-deal coverage checks, equal count/rule/phase weights and behaviour
  metrics. Teacher sampled values are diagnostic labels, never network inputs.
- `strong/prepare-opponent-surrogate-training-v1.py`: requires the complete verified
  2,560-game corpus and prepares only the 1,920 train / 320 validation games. Test
  records remain excluded. Reports natural exact-input overlap without filtering
  decisions by outcome.
- `strong/opponent-surrogate-training-design-v1.json`: four fixed seeds
  14101–14104, 80 epochs, batch 2,048, AdamW/cosine LR, validation macro-NLL selection.
  Equal total gradient weight for each of the 60 count/rule/phase groups. Forced
  shortlists are retained/reported but excluded from gradients. No test selection.
- `strong/train-opponent-surrogate-v1.py`: gradients require HF/CUDA; optional GPU
  resident data under a measured memory allowance. Saves best/latest/optimizer and
  all per-group histories, exports each selected seed and verifies its predictions.
- `strong/export-opponent-surrogate-v1.py`: unchanged float32 stored weights with
  explicit float64 arithmetic, supported SiLU expression and standalone ONNX.
  Every supplied record must match the corresponding float64 checkpoint's action;
  raw scores must meet the 1e-10 absolute/relative tolerance.
- `strong/test_opponent_surrogate_training_v1.py`: **nine passing tests**, no
  gradient steps. Real 382-row calibration tensors preserve inputs/targets; corrupt
  membership/targets and test inclusion are rejected; weighting/masking/permutation
  checks pass. Random unoptimized weights export with **382/382 exact choices**
  and max logit error below 1e-10. Random fixture files were temporary and not uploaded.

Preflight `ai/runs/opponent-surrogate-training-preflight-v1.json`, SHA256
`edafe0ebf89591c90f980644fbb03b91277f331c722efca454ff5e182fc6c6f1`, pins all seven
new files and the test log. Actual preparation from the incomplete corpus refused
before creating the output. Frozen collection source and all running resource
coordinator code hashes remain unchanged. No source package or HF training launcher
has been admitted, no real GPU training has been exercised, and no trained surrogate
exists. Do not present the random-weight export check as model strength or 8840U proof.

At **02:40:08 UTC**, original 6p runtime job `6add610d1e112550ce7e64e1` was directly
RUNNING, **17/24 games complete**, no logged errors. Resource coordinator
**11670 / PID 1291091** was live, **54 submitted / 31 verified**, no failures.
Snapshot: `ai/runs/opponent-surrogate-training-preparation-checkpoint-v1.json`.

Next: collect the original 6p endpoint when complete; audit/archive joint calibration;
prepare/dry-run/execute the existing full collection coordinator once. After all
fresh data verify, prepare tensors and immutable data/source, implement/admit the
HF GPU launcher and exercise actual training there. A surrogate's imitation metrics
do not establish playing strength: freeze validation-selected inference, test it,
then compare fresh paired continuations against actual search before modifying
the hybrid mixture. Keep all final qualification and actual-target hybrid gates.

## 25 October, 02:26 UTC — full surrogate collection orchestration ready

Implemented `strong/launch-opponent-surrogate-collection-v1.py`,
`strong/manage-opponent-surrogate-collection-v1.py` and
`strong/coordinate-opponent-surrogate-collection-v1.py`. Seven tests in
`strong/test_opponent_surrogate_orchestration_v1.py` pass. The initial test run had
a syntax error in a multiline mock context; corrected before the successful run.
Proof: `ai/runs/opponent-surrogate-orchestration-preflight-v1.json`, SHA256
`6bb9302f8a034b105dba73066dd9bea490dd8b456a6580d0f43734f3afd2aa10`.

Tests cover all 2,560 unique games/640 twins, whole-deal train/validation/test
boundaries at every supported batch size, synthetic resource admission limits,
actual missing-calibration refusal, and existing/failed/uncertain job handles.
The real 382-row 2p runtime archive also passed the collection verifier through
an explicitly synthetic envelope; this fixture is not actual collection data and
cannot enter the real training index. Full-corpus teacher searches will not be
rerun a second time locally: frozen HF workers re-encode all rows and replay
first/last strategic calls per game; complete endpoint calibration independently
repeats those calls locally. Every raw input/target/terminal remains host-verified.

No full collection plan or jobs exist yet; no new gradients. At **02:25:37 UTC**,
original 6p endpoint `6add610d1e112550ce7e64e1` was RUNNING, **15/24 complete**,
no logged errors. Resource coordinator **11670 / PID 1291091** was live with
**54 submitted / 29 verified**, no failures. Frozen source and resource coordinator
dependencies still match their pins. Checkpoint:
`ai/runs/opponent-surrogate-orchestration-checkpoint-v1.json`.

Resume with the original 6p collector, then joint calibration audit/archive. Only
then prepare the full collection plan (`launch-opponent-surrogate-collection-v1.py
prepare --max-in-flight 32`), dry-run every shard and the coordinator, and execute
the coordinator once. Its admission uses measured complete endpoints to select
4/2/1 whole deals, 2x time/RSS margins, 4x raw storage and 25% timeout reserve;
it refuses insufficient capacity instead of truncating games or teacher search.
All failed/uncertain original handles remain failures; no automatic replacements.
The complete index requires every fixed game and preserves the 1,920/320/320
train/validation/test split. HF-only training and held-out continuation validation
are still to implement after data collection.

The current recommendation remains selective auction search with better opponent
simulation and conservative action overrides. Old baseline figures 30.9%/15.6%
are superseded by frozen-1's 51.56%/39.06% on the larger 16-deal 4p evaluation.
The distinct four-deal hybrid screen has promising sealed-auction gains and large
open-auction regressions; do not combine those samples or route rules after seeing
results. No general plateau is established. Unchanged building/combined search
should not advance; fresh resource-screen results remain pending. No qualification,
production publication or reserved-final seed use.

## Previous checkpoint: resource-screen launcher prepared; measured HF CPU use

**Latest — 25 October, 02:08 UTC: first surrogate HF endpoint verified; complete audit tools prepared.**

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

## Previous checkpoint: complete resource pilot archived; HF calibration launched

**Latest — 25 October: full resource pilot archived; two HF calibration jobs running.**
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

## Previous checkpoint: exact batching experiment complete on local and target CPUs

**Latest — 25 October: action-count batching checked locally and on AMD8840U.**
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

## Previous checkpoint: component profile archived; existing runs continue

**Latest — 25 October: fixed-root component profile complete and archived.**
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

## Previous checkpoint: HF calibration launcher prepared; six-player resource cell running

At **2026-10-24T23:42:32 UTC**, the existing resource pilot **75756 / PID 559327**
has verified three complete cells: both 2p arms and the 24-game 6p/filter baseline.
That baseline verified 2,798 learner decisions, zero caps; wall 955.840 s, CPU
7,532.72 s, sampled summed RSS 4,032,208,896 bytes. The pilot is now running
**6p/resource-filter**. All 16 independent replays remain pending. The existing
reference coordinator **76600 / PID 443128** has **18 submitted, eleven verified,
seven running**, no failures. Both processes were checked live. Exact snapshot:
`ai/runs/resource-replanning-runtime-source-prepared-v1/hf-launcher-preparation-checkpoint.json`.

Prepared `strong/launch-resource-replanning-runtime-v1.py` without changing any live
source. It first requires the complete archived local pilot (64 games, 16 replays,
all pairs, zero caps), verified source/preflight hashes and unchanged runtime files.
`prepare --flavor cpu-upgrade|cpu-xl --timeout-hours N` writes a separate immutable
calibration admission. It requires twice measured summed RSS, 15 minutes setup plus
twice max(local wall, CPU/vCPU), and four times raw evidence storage. These are
calibration margins, not measured HF performance or guarantees. The hardware API
confirmed CPU Upgrade 8 vCPU/32 GB/50 GB and CPU XL 16 vCPU/124 GB/1000 GB.
Choose from the complete measurements, not the current partial resource results.

Then `launch 2` and `launch 6` are dry runs; add `--execute` only after inspecting
those plans. Each submits the existing tested wrapper's runtime-only mode against
search_geo, one whole deal/all seats/all rules, eight worlds, eight game workers and
one search worker. Both fixed endpoints total 32 calibration games, excluded from
strength. The bootstrap verifies all 1,484 packaged source hashes. A lock and
exclusive per-case guards prevent duplicates; ambiguous or failed submissions stop
for reconciliation rather than being retried. No launcher for the development grid
is included in this step.

Five tests passed in `strong/test_resource_runtime_launcher_v1.py`. They exercise
incomplete-pilot refusal before network access, invalid endpoints, CPU/wall/memory/
storage headroom, duplicate submission, and an injected timeout after submission.
The ambiguous guard remains `launch_unknown` and a second attempt never calls the
fake API. Shell syntax also passed. No remote job was created by the tests; actual
complete-pilot admission/submission are still pending. Preflight receipt and later
read-only hardware catalog check are in
`ai/runs/resource-hf-runtime-launcher-preflight-v1/`.
**The admission file and launch directory do not exist yet.**

**Collector addition, 2026-10-24T23:53:14.144101+00:00:** both existing process commands were checked live.
The 6p resource cell has **6/24 game files** complete, still unverified; all 16
replays remain pending. Reference diagnostic: **23/28 submitted, 16 verified**,
no failures. Snapshot:
`ai/runs/resource-replanning-runtime-source-prepared-v1/hf-collector-preparation-checkpoint.json`.

Prepared `strong/collect-resource-replanning-hf-runtime-v1.py`. It calls the launcher's
read-only admission review, requires the original per-endpoint guard, reads actual HF
status, and collects only complete jobs as verified outcomes. Any failure preserves
the logs for review; it cannot submit/cancel/retry. It verifies the immutable remote
archive, manifest, wrapper/source/model/protocol identities, full resource receipts,
terminal scoring and measured CPU/RSS/wall times. It then compares the HF evaluation
with the archived local endpoint: every learner proposal/action, sampled world,
resource continuation, game count/statistic and terminal must match exactly. Only
host paths, two named decision timing fields, and report/game durations are excluded.
Raw receipt hashes are checked separately; new or unexpected fields are not ignored.

Five tests in `strong/test_resource_hf_runtime_collection_v1.py` passed: altered
moves/model proposals, sampled worlds, resource costs, rollout terminals, seeds,
terminal results, added fields and corrupt raw hashes are rejected, and no HF call
occurs before the full local pilot is archived. A separate full-data preflight
independently verified both reports after converting the saved 2p batch to synthetic
HF paths and doubled timings. All **8 games / 1,306 learner decisions / 450 resource
decisions / 41,632 continuations** matched. This reuses existing records, executes no
engine games and is not evidence that actual HF calibration has run. Harness/receipt:
`ai/runs/resource-hf-runtime-collector-preflight-v1/`. No resource HF jobs exist yet.

After actual calibration jobs are submitted, use
`ai/.venv/bin/python ai/strong/collect-resource-replanning-hf-runtime-v1.py 2`
and the same command with `6`; `--inspect` reads status only. Require both complete
verified endpoint records and cost review before preparing any development launch.

Next: let both live runs finish. Audit/archive the complete resource pilot first,
then use this launcher for explicit runtime calibration and verify parity with the
local games before admitting the 3,360-game development screen. The 28-shard
reference comparison and complete archive remain pending independently. No new
resource HF jobs, gradients, candidate selection or final seeds were introduced.

## Previous checkpoint: verified resource job source; complete two-player runtime pair

The source/preflight work is complete and durable. New source descriptor
`strong/resource-replanning-job-source-v1.json` pins dataset revision
`8d3697dec0845aa6ded857f3e00d91a8ff4406c0`, archive
`strong-source-resource-replanning-jobs-v1.tgz`, SHA
`e26f742778fa48796e7226f24dcea2591597d4a12f01dced2d8283711a295152`.
All 1,482 files from the local-pilot package remain identical; the tested HF wrapper
and its builder add two files (1,484 manifest entries, 1,485 archive files including
the manifest). No generated run outputs are packaged. Its false admission flags
record this preparation stage; a separate measured admission is still required.

`strong/collect-resource-job-preflight-v1.py` archived the clean-package tests,
intentional stopped-before-evaluation records, source manifest and upload receipts.
Descriptor `strong/resource-job-source-preflight-evidence-v1.json` pins model repo
revision `ed9f76066b7d858e7b5ad1603ffa54012f354a74`, archive SHA
`d2dc0dd44777e02456c145c4833ce84ee0523e15ec818cc22a78435577f3d350`, **30 files**.
The 378 valid contracts, 13 rejected contracts and three execution-boundary checks
are preflight evidence, not games or failed HF jobs. Session 4420's terminal output
was unavailable after compaction; both immutable remote archives and all local
evidence-manifest files were checked against their completed descriptors. Do not
repeat the source or evidence upload. No new resource HF jobs or strength games.

At **2026-10-24T23:37:38 UTC**, resource **session 75756 / PID 559327** and reference
**session 76600 / PID 443128** were checked alive with matching process commands.
The resource pilot has completed and verified **2p/filter and 2p/resource-filter**
(eight games each, zero caps). It is in 6p/filter, with **18/24 game files** at this
snapshot; the 6p resource cell and 16 replays remain pending. The reference coordinator
has **17/28 submitted, ten verified, seven running**, no failed jobs. Full snapshot:
`ai/runs/resource-replanning-runtime-source-prepared-v1/job-source-checkpoint.json`.

Completed 2p resource runtime: 1,306 learner decisions, 450 resource searches,
41,632 continuations / 2,701,343 simulated neural decisions, 99 search changes,
zero caps. Cell wall 1203.341 s, CPU 6352.42 s, sampled summed RSS 6,971,523,072 bytes.
Resource-only elapsed median 9.809 s, p95 33.008 s, max 81.521 s; bundle median nine,
p95 29.55, max 44. This measures parallel HX370 execution, not AMD8840U serving
latency or HF performance. Pilot outcomes are excluded from strength. Cost evidence:
`ai/runs/resource-replanning-runtime-source-prepared-v1/completed-2p-resource-cost.json`.

Next: leave both existing processes running. Complete and archive the full local
64-game / 16-replay resource pilot before choosing HF calibration hardware/timeout
and implementing its explicit launcher. The tested source is ready for that step;
the 3,360-game development screen remains unlaunched. Continue the complete
28-shard auction diagnostic and prepared audit separately. No final seeds or
candidate selection. The unchanged-building/combined search results remain adverse;
auction search remains promising but unqualified, pending regression diagnosis.

## Previous checkpoint: collectors and HF wrapper prepared; both runs remain live

The previous goal turn made substantive progress by pinning the resource runtime
source and starting the full pilot. This turn added the complete resource evidence
collector, exercised the future HF execution wrapper, and checked actual live HF
progress/metrics. Neither live runtime was modified or restarted.

At **2026-10-24T23:16:43 UTC** (25 October locally), local **session 75756 / PID 559327**
remained in `2p-resource-filter`: the baseline eight-game cell was complete/verified,
and seven of eight resource games had ended. This is partial progress, not a verified
resource cell or strength result. The 6p cells and all 16 replays remain pending.
Auction **session 76600 / PID 443128** had **12 submitted, five verified, seven running**,
no failures. Exact snapshot:
`ai/runs/resource-replanning-runtime-source-prepared-v1/collection-preparation-checkpoint.json`.

Read-only HF inspection at **23:11:43 UTC** confirmed continued neural-decision
progress in the jobs queried. Its full evidence is
`ai/runs/reference-opponent-live-runtime-v2/20261024T231143Z.json`.
A three-frame sample of root 1/worlds 16..31 showed a median CPU utilization of
68.5% after the first frame, about 1.93 GB maximum RAM on CPU Basic. This is only a
brief observation, not a sustained-utilization estimate or reason to restart jobs.
The coordinator subsequently collected the completed root 3 and root 4 first shards
and admitted their next fixed shards normally. No timeout, cancellation or retry.

New `strong/collect-resource-replanning-runtime-v1.py` requires `stage=complete`,
all 64 endpoint games and 16 predeclared replays before any audit/archive. It
revalidates the frozen package, complete-game decision receipts, terminal scoring,
paired arms and replay identities; it reports resource search latency/bundle/simulation
distributions and raw evidence size alongside CPU/RSS measurements. It does not
produce a pilot win-rate comparison. Its partial-pilot refusal passed before any
evidence directory/upload, receipt
`ai/runs/resource-replanning-runtime-source-prepared-v1/collector-preflight.json`.
Collector SHA `a2487777cacbbbeebaba0e6909f3041c32f3b774a2b1fb2fa2291fa187ded21f`.
After full completion, run without arguments, inspect, then run once with `--archive`.
The descriptor `strong/resource-replanning-runtime-evidence-v1.json` does not yet exist.

New `strong/resource-replanning-development-job-v1.py` is **not launched or included
in an uploaded job source yet**. It uses the unchanged atomic evaluator and resource
verifier, eight worlds, eight game workers, one search worker, and the same horizons.
Normal jobs use only the fixed resource development seeds/partitions. Its explicit
`--runtime-pilot` mode is restricted to one full 2p or 6p resource-filter/search_geo
deal using the separate runtime seeds, allowing later HF calibration and exact
comparison with the local pilot. No automatic launcher or admission was added.

Clean-package wrapper preflight completed **378 valid job contracts, 13 rejected
invalid contracts and three execution-boundary checks**: 6p runtime, nonzero-offset
2p resource/economic-capacity development, and 3p filter/a260 development. Real model
and independent-opponent file hashes were checked. An injected `ReachedEvaluation`
exception stopped each command before any game, with failure records/manifests
preserved and uploads stubbed out. These three intentional preflight failures are
not failed HF jobs. All 1,481 packaged files remained unchanged. Evidence/harness:
`ai/runs/resource-development-wrapper-preflight-v1/`, receipt `receipt.json`.
Wrapper SHA `c711da9db3b8c20ee75c7469e76f3b27026771e2336351246f09aaf4874ff08c`.

Next: continue both existing processes. Complete/verify/archive the local resource
pilot, then package the tested wrapper and use explicit measured HF runtime
calibration to set the resource development admission. The fresh 3,360-game screen
is still unlaunched. Auction comparison/archive also remains pending all 28 shards.
No gradients, candidate selection, production edits or final seeds this turn.

## Previous checkpoint: pinned resource pilot running, 25 October

This turn advanced the separate resource-planning work while the seven-root auction
diagnostic continued. The complete 8,400-game comparison already satisfied the
resource protocol's prerequisite. Its source/model/arms/seeds/horizons and 3,360-game
future development design remain unchanged; no development or final games started.

New runtime plan: `strong/resource-replanning-runtime-plan-v1.json`, SHA
`60bfb71d31464e360a6c5d38468cb99cd7a8786bfd38c9089c264ec2ae6b17fb`.
It fixes four sequential cells: 2p filter, 2p resource-filter, 6p filter,
6p resource-filter. Each has one complete deal, every seat and four rule combinations
against the unchanged search_geo opponent: **64 games total**, eight concurrent game
workers and one search worker per game, eight resource worlds, 2400 rollout/1600 game
horizons. Seeds are `resource-replanning-runtime-v1-{players}p`, disjoint from the
future development and reserved final seeds. The last seat's four rules in every
cell are fixed in advance for **16 exact replays**, including model proposals and
legal atomic choices. Runtime results are not strength estimates.

New scripts: `strong/build-resource-replanning-runtime-source-v1.py` and
`strong/resource-replanning-runtime-pilot-v1.py`. The first preparation stopped before
archive/upload/games: `collect-population-screen.py` in the current research plan had
a different hash from its older frozen-source counterpart. These are reporting
tools, not playing-policy changes. The failed preparation, original script copies,
plan and failure receipt are preserved at
`ai/runs/resource-replanning-runtime-source-preparation-failed-v1/`.
The explicit correction checks current reporting dependencies on the host, keeps
all historical source files intact, and verifies the full package manifest plus
resource overlays inside the runtime. No engine or frozen policy file was replaced.

The corrected clean package has **1,463 unchanged base files + 18 added files**.
Clean-layout initialization verified all four commands and the actual float64 model,
without starting games. A new replay preflight reproduced one existing 2p/filter
search-opponent game exactly: **159 learner decisions**, all legal choices/model
proposals/public observations and terminal state matched. This is an existing game,
not an extra runtime deal or strength result.

Source upload session **70559** completed exit 0, uploaded once and downloaded for
hash verification. Descriptor `strong/resource-replanning-runtime-source-v1.json`:
private dataset `coyotte508/powergrid-ai-training-v1`, revision
`6950d0baffdbb1e2a91bb09849c68b9c15db9fbf`, archive
`strong-source-resource-replanning-runtime-v1.tgz`, SHA
`5e3a402b03e26d93d6741d6879024c49bc5b7ca7db3a01b575c3c8d6461a684c`,
109,606,680 bytes. Manifest SHA
`35f85462b63798fccc4134feceba73485e0c8fb102479ef133f23883047eb630`.
Preparation and upload receipts: `ai/runs/resource-replanning-runtime-source-prepared-v1/`.
Do not rerun the builder or uploader, and do not alter pinned source files while live.

**Active local pilot: session 75756, PID 559327**, started
`2026-10-24T23:02:46.683303+00:00`, AMD Ryzen AI 9 HX 370. Output lives inside the
clean package, at
`ai/runs/resource-replanning-runtime-source-prepared-v1/layout/ai/runs/resource-replanning-runtime-v1/`.
Its `status.json` records the current cell, evaluator PID and complete-cell summaries.
It does not automatically retry failures. At the explicit **23:04:53 UTC** snapshot,
the 2p/filter cell completed all eight games and verified **1,371 decisions**, no
game/rollout/nested caps. Measured wall time 28.18 seconds, CPU 247.09 seconds and
sampled summed RSS 3,307,708,416 bytes. These are parallel local engineering timings,
not 8840U timings or HF hardware predictions. The **2p/resource-filter** cell is
running; the 6p cells and 16 replays are still pending. No runtime admission yet.

The auction diagnostic is also still live: **session 76600 / PID 443128**, 10 submitted,
three verified, seven running, no failures at the same snapshot. Both processes were
checked live. Full exact snapshot:
`ai/runs/resource-replanning-runtime-source-prepared-v1/turn-checkpoint.json`.

Next: continue both existing handles. For the resource pilot, require all 64 games,
four complete receipt summaries, 16 exact replays, no caps and unchanged manifest;
then archive the full evidence including the initial packaging failure and replay
preflight. Only after those checks should measured runtime determine hardware,
concurrency and timeout for the separate 3,360-game development screen. For auctions,
use the already prepared complete-result collector after all 28 shards finish.
Do not turn fast partial results into policy selection or strength claims. No
gradients, production changes, qualified model or final seeds were used this turn.

## Previous checkpoint: complete-results audit prepared; existing jobs continue

At **2026-10-24T22:53:31 UTC** (25 October locally), coordinator **session 76600 /
PID 443128** remained alive with **10/28 submitted, three verified, seven running,
zero failed jobs**. This is a timestamped observation; inspect the existing handle
again before acting. The exact snapshot, including immutable evidence receipts for
the three completed shards, is
`ai/runs/reference-opponent-coordinator-v2/collector-preparation-checkpoint.json`.
No additional experiment, duplicate launch, automatic retry, cancellation or local
simulation was started. The existing coordinator alone continues its admitted queue.

The new `strong/collect-reference-opponent-diagnostic-v2.py` requires all 28 verified
shards and `comparison_complete` before producing any aggregate review. It reruns
the original complete verification and independently derives credits from terminal
player scores; it uses rational arithmetic for paired margins and bootstrap block
multiplicities to audit the saved intervals. It preserves original worlds 0..7 as
secondary and worlds 8..63 as primary, all seven original action pairs and adverse
roots. No new candidate selection or outcome-dependent routing is introduced.

Preflight rechecked 896 control, 16 pilot and 96 collected continuation rows. Five
corruptions (wrong credit, duplicate/missing world-action, nested cap, wrong offset)
were rejected. A partial comparison was rejected before writing evidence. Receipt:
`ai/runs/reference-opponent-collector-v2-preflight/receipt.json`; script SHA
`fc58f9046b5dad387a9ec06fe6471e603bf3c50de2edf83d9123e778330bac37`.
The initial one-off import harness omitted the `ai/strong` module path; adding it
fixed that harness, with no change to the live code or jobs. No full aggregate
audit or archive upload has occurred yet.

Continue the existing coordinator. Once complete, run:

```sh
ai/.venv/bin/python ai/strong/collect-reference-opponent-diagnostic-v2.py
```

Inspect the complete seven-root comparison, then archive once with the same command
plus `--archive`. The intended descriptor is
`strong/reference-opponent-complete-evidence-v2.json`; it does not yet exist.
The collector preserves all 28 guards, job logs, verified raw artifacts, controls,
protocol, sources, comparison and audit in one verified private HF archive. Check
any pre-existing archive/output/descriptor before attempting an upload again.

The strong-model goal remains active. No conclusion about tapering gains follows
from these running diagnostics. Keep auction search under investigation, the current
filtered model as reference, and the resource ablation unlaunched until its own
runtime admission. No gradients, final seeds, qualified candidate or publication.

## Previous checkpoint: complete repaired pilot and active HF diagnostic, 25 October

The prior turn was substantive progress: it isolated a nested sealed-history failure
and verified a sampler component. This turn integrated that component into a new
diagnostic worker, completed its full pilot, archived it, and launched the admitted
fixed public-world comparison. This changes research evidence, not production or
the selected model.

`strong/reference-opponent-continuations-v2.cjs` differs from v1 only in its isolated
nested-search import and immediate nonzero exit on JSONL failures. The new
`reference-search-public-balances-v1.cjs` loads the frozen search in a private module
with the repaired sampler; it does not change `require.cache`, historical module
exports, outer world sampling, or the original source files. Six tests pass: all 80
control cells, 32 exact comparisons with the actual frozen arena implementation,
seven-root hidden-input and world sharing checks, partition identity, the captured
failure with the original search still failing unchanged, and immediate process exit
on invalid input with stdin left open.

The v2 protocol is `ai/runs/reference-opponent-diagnostic-v2/protocol.json`, SHA
`88c1f9e78c41bfa6c8b11fec87d4692a221dfee65181f473047da2a4da9a9d77`.
All seven original candidate pairs and public seeds are preserved. **896** full
mixture controls matched their saved credits, roles, beliefs and sampled worlds.
All **16** reference pilot continuations finished with zero outer/nested caps.
All terminal rows of the three previously complete v1 pilot cases matched exactly;
the four previously failing 6p sealed continuations are now complete. Seven corrupt
receipt variants were rejected. Session **67264** finished exit 0.

Local HX370 runtime for four continuations each: 4p search 230.42 seconds, 3p heuristic
0.91 seconds, 2p search 31.49 seconds, 6p search 233.11 seconds. The maximum observed
CPU time was 458.39 seconds and summed process RSS about 1.46 GB. These are runtime
admission measurements, not AMD8840U timings or strength results. The complete pilot
and clean-package check are archived and verified at private HF revision
`59243d245597ebd4034d187bf9b07e3c8b3f952b`, archive SHA
`ef94026a3131a088293e014514ecd7688ed50263a9257a2898e2488386d74b76`, 74 files,
descriptor `strong/reference-opponent-pilot-evidence-v2.json`. The one-shot collector
has completed; do not rerun it. All 1,463 historical runtime files and 32 frozen
development-screen dependencies remain unchanged.

The admission fixes 28 `cpu-basic` jobs (2 vCPU / 16 GB each), four worker processes,
16 worlds × two actions per job, a three-hour timeout, and at most seven concurrent
jobs. CPU timing, completeness and memory determined admission; pilot scores did not.
The first infrastructure canary was root 2 / worlds 0..15:
`6add3494046eb82b1ece0468`. It completed and independently verified 32 continuations,
3,524 neural decisions and 11,918 outer moves, zero caps, and exact pilot-prefix rows.
Its evidence is private HF revision `e74bbfe45bb9179604104175abf1373c348c8da9`, SHA
`8f23c9f8b9c2fc4eaf0f2c7f54b59612cd7dc940f1b686d7c9797fb712a97875`.
Only after verification did the coordinator expand to seven concurrent jobs.

**Active coordinator:** session **76600**, PID **443128**, started
`2026-10-24T22:43:31.799020+00:00` (25 October locally).
`ai/runs/reference-opponent-coordinator-v2/state.json` records pinned code and progress;
`turn-checkpoint.json` contains the explicit HF status snapshot at 22:44:48 UTC.
At that check eight jobs had been submitted, one verified, and seven were RUNNING:
root 0 `6add34c4046eb82b1ece048b`, root 1 `6add34c5046eb82b1ece048d`, root 3
`6add34c6046eb82b1ece048f`, root 4 `6add34c7046eb82b1ece0491`, root 5
`6add34c9046eb82b1ece0493`, root 6 `6add34cb046eb82b1ece049b` (all worlds 0..15),
and root 2 / worlds 16..31 `6add34cd046eb82b1ece049d`.
Guards are in `ai/runs/reference-opponent-launches-v2/`; verified shard evidence is in
`ai/runs/reference-opponent-collected-v2/`. These are a timestamped checkpoint, not a
claim that the status can never change. Read the current handles before acting.

The coordinator checks source identity, collects immutable HF archives and validates
every terminal row before allowing comparison. It stops for review on any failed or
uncertain submission; it does not retry or cancel remote jobs. Its 12-hour observation
window is distinct from remote job failure. Do not duplicate a live coordinator or
existing job. On full completion it writes `strong/reference-opponent-comparison-v2.json`:
all seven roots, both original fixed actions, all 64 worlds, with the original primary
worlds 8..63 and paired four-world block bootstrap. Every adverse result is retained.

Next: monitor the existing coordinator, revalidate the complete comparison and assess
whether known stronger-opponent continuation changes the fixed action ranking.
These remain outcome-selected conditional diagnostics; no conclusion about fresh
game strength or calibrated win probability follows directly. No new gradients,
candidate selection, production/UI edits, deployment or reserved final seeds occurred.
The separate resource ablation remains unlaunched and the full strong-model goal active.

## Previous checkpoint: opponent-model pilot failure isolated, 25 October

The opponent-model diagnostic now has an isolated worker and a frozen pilot
protocol at `ai/runs/reference-opponent-diagnostic-v1/protocol.json`, SHA
`121dd85f2d9bd9e8cb10d170c74857ccb783d02ea90eb92bb1878382163de9f5`.
It keeps the same seven outcome-selected public roots, the original model/search
action pair, public sampled-world seeds, frozen-1 model, focal loss filter and full
2,400-move horizons. The treatment replaces the outer opponent mixture and inferred
prior sealed bids with the known arena reference policy. This is diagnostic knowledge,
not a deployment assumption about an opponent's identity.

`strong/reference-opponent-continuations-v1.cjs` loads the historical runtime without
editing it. Four tests passed: 80 rule/count/phase control cells, 32 exact comparisons
with the frozen arena's actual `applyBot`, public-only world/bid construction, and
partition identity. The full **896** mixture continuations (seven roots × two fixed
actions × 64 worlds) matched every saved credit, role, inferred bid and shared world.
Terminal scores are independently recomputed from powered cities, money and cities.

Three full reference pilot cases completed: 4p search took 218.29 seconds for four
continuations, 3p heuristic 0.94 seconds, and 2p search 30.65 seconds. These are local
HX370 runtime observations, not AMD8840U timings or strength estimates. They include
65,248 nested candidate evaluations in the two search cases, with zero caps. The
6p Recharged/sealed case failed during initialization; no result was imputed.

The failure was reproduced on sample 0 / original model action index 10. Earlier
actor 1 had an inferred bid of 15 on plant 8, but its assignment to `player.bid` did
not append a hidden-history move. After the simulated auction, the public history
contains bids by actors 2, 3 and 5, followed by actor 1 nominating plant 5. Replaying
that incomplete hypothetical history cannot finish the first auction. Nested search's
sampler unconditionally attempted that replay to recover balances, although every
balance was already known. This finding concerns the new nested diagnostic; it does
not invalidate the completed population-mixture screen or establish a live game bug.

Pilot session **5175** exited 1. The worker error handler set `process.exitCode` but
left readline alive; after all four exceptions were observed and recorded, the four
failed workers were explicitly terminated so the parent could observe EOF and exit.
All those processes are gone. The v1 pilot is failed and must not be restarted.

`strong/analysis-public-balances-v1.cjs` is a proposed isolated repair: load the
historical sampler in a separate module and skip only the unused reconstruction when
all money is public. Unknown money still requires the original replay. Tests passed:
**2,553** ordinary sampled worlds identical, **24** hidden-money recovery cases
identical, and the captured failure repaired with unchanged public history and hidden
input invariance. This component is **not integrated into the worker or adopted**.
The first test-source guard caught a compiler-expression spelling mismatch before
simulation; the corrected exact-source guard and all three tests pass. Both logs are
preserved. All 1,463 historical runtime files and 32 frozen screen dependencies remain
unchanged. Seven intentionally corrupted result checks were also rejected.

The failure and repair evidence were archived once and verified:
`strong/reference-opponent-pilot-failure-evidence-v1.json`, private HF revision
`e2605d3e6f5d3ef2b43eb6713504f08ae496c449`, archive SHA
`5e58a38c12c7667419ac4371521de3ee87c2ecc79ce2546dfe18b810b252a3ea`, 70 files.
The collector has completed; do not repeat it. Draft success collector/job/launcher
code was prepared, but its required successful admission descriptor is absent and
**no HF jobs were submitted**. No gradients, new strength games, candidate selection,
deployment or reserved final seeds occurred.

Next: version a new reference worker with the isolated sampler scoped to nested
reference search, and make JSONL failures close immediately. Verify its normal arena
behavior and controls again; run a fresh complete pilot, including all four 6p failed
continuations, before admitting the larger fixed 64-world comparison. Preserve the
same action pair and sampled worlds. Do not score the partial v1 set, fit switches to
these seven positions, or silently change the historical engine. The resource ablation
remains independent and unlaunched. The goal remains active; this is not a plateau.

## Previous checkpoint: seven one-action counterfactual pairs complete, 25 October

The preceding replay/holdout-world turn was substantive progress. This turn completed
the next fixed causal diagnostic, preserving all seven positions rather than choosing
only examples that supported a hypothesis. No deployed or research policy was changed.

`strong/auction-first-action-counterfactual-v1.py` prepared seven filtered-model
controls and seven single-action branches from the previously verified first-divergence
roots. Every control used live filtered-model inference and exactly matched all saved
control decisions, public roots and complete terminal reports. Each branch matched
the original public prefix, injected its one saved auction-search action, and then
returned to filtered-model inference for every subsequent learner decision. Opponents
continued their unchanged frozen arena policies and could respond to the intervention.
The full engine state was recreated from the original seed/rules/seat; the policy
only received public observations, with hidden deck and sealed bids removed.

All **14 games / seven controls / seven intervention branches** completed, covering
**1,886 learner decisions and 6,919 root moves**. The chained economy traces match
executed moves, and all game/opponent-search cap counts are zero. The seven controls
match the original evaluations exactly; each intervention branch has precisely one
override and uses the same filtered policy without search everywhere else.
Session **82545** exited 0. Output directory:
`ai/runs/auction-first-action-counterfactual-v1/`.

| Selected case | Filter control | One changed action | Interpretation on this deal |
|---|---:|---:|---|
| 4p original/open regression | 1 | 0 | Opening nomination alone is sufficient for this loss under model continuation. |
| 5p Recharged/open regression | 1 | 1 | Complete terminal player summaries unchanged. |
| 3p heuristic regression | 1 | 1 | Complete terminal player summaries unchanged. |
| 4p Recharged/sealed improvement | 0 | 0 | Different terminal state, same loss. |
| 4p original/sealed improvement | 0 | 0 | Complete terminal player summaries unchanged. |
| 2p Recharged/sealed improvement | 0 | 1 | First change alone recovers this win under model continuation. |
| 6p Recharged/sealed improvement | 0 | 1 | First change alone recovers this win under model continuation. |

The 4p original/open opening still had a +0.125 mean advantage in the earlier
56-world mixture diagnostic, despite losing this known-deal intervention. Conversely,
the 2p sealed opening had a slightly negative heldout mixture mean but wins this
known-deal intervention. This does not by itself prove an incorrectly estimated
expected value: a single actual deck can differ from its sampled expectation, and
these examples were selected by prior outcomes. It does establish that later search
is not necessary for those particular changes in outcome. In the other cases, the
full search-policy outcome cannot be attributed to its first change alone.

Evidence was checked again from saved receipts and uploaded with pinned download
verification; 107 archived files, including source, protocol, full controls/branches,
public requests and economy traces:

- Descriptor: `strong/auction-first-action-counterfactual-evidence-v1.json`.
- Protocol SHA: `c163db683f2e5b29036880e818df72c6176e08e4bc09f2f5d7be16243bf5ba45`.
- HF revision: `f9dc1f9f1092e9a36809001486bac0daa8111866`.
- Archive: `archives/auction-first-action-counterfactual-evidence-v1.tgz`.
- SHA256: `4c3f304209521bc4fc17f223441f7246b0fdf3dbb19330db97a2ac524fb02d80`.

The one-shot archive succeeded; do not rerun it. No new HF jobs, gradients, fresh
strength games, final candidate or reserved seeds were used. Do not turn these
outcome-selected known-deal labels into a training target or a strength claim.
All 1,463 frozen runtime files and current Python dependencies remain unchanged.

**Next:** a controlled opponent-model diagnostic on the same seven public roots and
the same original two candidate actions. Preserve the existing 64 sampled-world
seeds and model/engine/horizons. Compare the equal neural/economic/legacy/rush mixture
with the frozen actual arena opponent policy (search_geo16 for six pairs, heuristic
for the 3p pair), including policy-consistent inferred prior sealed bids. Never use
actual hidden bids/deck, and never treat this diagnostic knowledge of arena roles
as a deployable ability to know a live opponent's strategy. The original expanded
mixture results remain immutable controls. Use a separate worker rather than editing
the 32 frozen dependencies. Verify pure control parity, candidate/shared-world
identity, public-only beliefs, full terminal scoring and cap rejection; measure a
small complete rollout pilot before CPU HF job admission because reference search
inside continuations can be expensive. Do not shorten horizons or silently fall back.
This tests whether assumed opponent behavior contributes to candidate ranking;
it does not yet establish a stronger search policy or eliminate sampling uncertainty.

The separately preregistered resource ablation remains unlaunched and still needs
its own source and runtime admission. A read-only review this turn confirmed those
requirements; nothing was changed or submitted. Final gate and adapter requirements
remain unchanged, and larger confirmation still needs an improved, frozen policy.

## Previous checkpoint: exact auction replays and fixed-action holdout worlds

The previous goal turn completed the full screen and changed the next research
action; it was substantive progress. This turn added exact replay evidence and
a completed conditional simulation audit. No policy, training or strength gate
was changed, and no HF jobs were launched.

`strong/replay-population-auction-regressions-v1.py` selected the lowest eligible
episode in each of seven stated categories, retaining every eligible episode ID.
Three adverse pairs: 4p original/open versus search, 5p Recharged/open versus search,
3p heuristic overall. Four improved controls: 4p Recharged/sealed, 4p original/sealed,
2p Recharged/sealed and 6p Recharged/sealed versus search. Both filter and auction
trajectories were replayed for each pair through the immutable 1,463-file source.

All **14 games, 7,083 root moves and 1,908 learner decisions** reproduce exactly.
Checks cover terminal players/outcomes, opponent search counts, legal moves, original
model proposals, original public search seeds, full chained economy traces, and the
public-root correspondence for each learner decision. Every player's money/cities/
plants match the trace; policy inputs exclude the hidden deck and sealed bids.
`analyze-population-auction-replays-v1.py` proves that the first differing learner
action in each pair has the same public state, legal menu and model proposal.
All later trajectory differences remain confounded; the whole-game result is not
the causal effect of that first action.

Replay output: `ai/runs/population-auction-regression-replays-v1/`.
Session **19372** exited 0. The separate collector repeated hash, trace-chain,
public-root and move checks and archived 99 files with pinned download verification:

- Descriptor: `strong/population-auction-regression-replays-evidence-v1.json`.
- HF revision: `b51a1f40428adc6d83da9e4341165e7b8c8378bb`.
- Archive: `archives/population-auction-regression-replays-evidence-v1.tgz`.
- SHA256: `77f1eaa00e253828b8645539827f7ce65d1beeb3858b542ad608d63775579635`.

The descriptive spending evidence does not support a universal overbidding fix.
In the selected 4p original/open regression, auction search spent 211 on plants
versus 230 for filter, and both powered 18 cities. In the selected 5p regression,
search ended at 15 cities / 17 capacity versus filter's 16 cities / 14 capacity;
the games ended in different rounds. These are examples, not general causal claims.

`strong/probe-auction-world-generalization-v1.py` then froze all seven first-divergence
positions, candidates, original selected actions and original model baselines before
generating additional worlds. It used the same model/source/public seed/opponent
mixture, 64 worlds, four JS workers and unchanged 2,400-step horizon. Every candidate's
original eight outcomes and their roles/prior-bid beliefs matched exactly. The
original selected action was compared to its original baseline on worlds 8–63;
it was not reselected using those outcomes. All **2,304 continuations** completed
with **zero caps**. This was local CPU inference, not gradient training.

| Selected example | Original 8-world margin | New 56-world margin | Conditional 95% block interval |
|---|---:|---:|---:|
| 4p original/open regression | +0.1250 | +0.1250 | [+0.0179, +0.2321] |
| 5p Recharged/open regression | +0.3125 | −0.0893 | [−0.2500, +0.0714] |
| 3p heuristic regression | +0.1250 | +0.0357 | [−0.0536, +0.1429] |
| 4p Recharged/sealed improvement | +0.2500 | −0.1250 | [−0.2500, 0.0000] |
| 4p original/sealed improvement | +0.1250 | +0.1607 | [+0.0893, +0.2500] |
| 2p Recharged/sealed improvement | +0.2500 | −0.0179 | [−0.1429, +0.1250] |
| 6p Recharged/sealed improvement | +0.1250 | +0.1250 | [−0.0179, +0.2500] |

These margins are simulated terminal-credit differences conditional on selected
public states and the existing continuation model. Intervals resample 14 balanced
four-world blocks (10,000 draws, seed 12343); they are exploratory, not multiplicity
adjusted, not calibrated win probabilities and not fresh game-strength evidence.
Three signs reversed, including two improved whole-game examples. Thus eight-world
values can be unstable, but this does not explain every policy loss or justify an
uncertainty threshold fitted to these seven examples. More samples alone have not
been established as a strength improvement.

World-audit output: `ai/runs/auction-world-generalization-v1/`.
Session **71292** exited 0. The diagnostic checks were repeated from saved outcomes;
twenty evidence files were uploaded with pinned-download verification:

- Protocol SHA: `ffd05be775f21dbb9961608bb1e536b238e4953ec1459606fd09a866c4053119`.
- Descriptor: `strong/auction-world-generalization-evidence-v1.json`.
- HF revision: `467a2250d6343e20a58eb365baa0798c88294fc5`.
- Archive: `archives/auction-world-generalization-evidence-v1.tgz`.
- SHA256: `d6ac9ff112f5be7dcc41927a919bc15806bff4e2702434bfae9e8389f6b3e1dc`.

Both one-shot uploads completed; do not rerun them. Preparation initially rejected
a nonexistent dependency path before creating its output directory; correcting the
path to `ai/strong/feature_contract.py` allowed preparation. No policy/runtime change
or failed simulation was involved.

**Next concrete diagnostic:** all seven first-action counterfactual pairs. Recreate
the original full engine state from the fixed deal and saved prefix, verify the
same public root, then compare (a) the filtered model throughout, requiring exact
reproduction of its saved reference, and (b) only the first search-selected action
followed by the filtered model for all subsequent decisions. Keep actual frozen
arena opponent policies, rules, seat and game seed identical. Do not expose actual
hidden deck/bids to the policy or use this known-deal intervention for strength
claims. This distinguishes a first-move effect from later search decisions;
opponent-model mismatch and repeated replanning remain hypotheses to investigate.
Only then decide whether a separately frozen confidence/continuation improvement
is ready for fresh development. Resource replanning remains separately unlaunched.
No candidate selected, no final seeds or final qualification; the final-adapter
requirements and original strength gate remain unchanged.

## Previous checkpoint: hybrid screen complete; auction promising, regressions prevent promotion

At **2026-10-24 21:27:05 UTC**, the coordinator reached `comparison_complete`,
**135/135 verified batches and 8,400 games**, and session **5513** exited 0.
Both final six-player search-opponent jobs were independently confirmed COMPLETED.
There are zero game/rollout caps in all accepted results. Do not restart the completed
coordinator or either historical recovery launcher.

The archive helper completed once, reproduced the unchanged full comparison, verified
all 32 frozen dependencies and preserved the replacement parity proof. All 17,797 files
are uploaded with pinned-download/SHA verification:

- Descriptor: `strong/population-hybrid-development-complete-evidence-v1.json`.
- HF revision: `91076fb5f4cffed75bf2ddd22f70f3442f78c00d`.
- Archive: `archives/population-hybrid-development-complete-evidence-v1.tgz`.
- Archive SHA256: `d9f140ced5394b154eaddced865723ca70e064a5e311d5ff098319d0f6f0b1fc`.
- Comparison SHA256: `6acbd8e57990f4cb9dc775b46b3859db18ccab3cb653dc50552c92f60a86bcbb`.

Do not rerun the one-shot upload. [The full review](HYBRID-SCREEN-2026-10-24.md)
and `strong/population-hybrid-development-review-v1.json` contain all 27 cell totals,
all search-opponent rule strata, every adverse auction view, runtime aggregates and
the paired terminal records for the three principal regression cases. The review
checks receipt/report/decision hashes against the completed comparison. It generates
no games, gradients, policy changes or jobs.

Auction search versus the filtered model, overall against search_geo, 2–6 players:
**62.5→78.125%, 41.667→66.667%, 50→53.125%, 47.5→50%, 45.833→58.333%**.
Recharged sealed improves at every count; four-player is **43.75→68.75%**.
But important failures remain: 4p original/open **81.25→31.25%** (8 worse paired
outcomes, no better, 16 games), 5p Recharged/open **70→50%** (6 worse, 2 better,
20 games), and 3p heuristic **100→85.417%** (7 worse, no better, 48 games).
Each cell contains only four independent deals. The marginal whole-deal intervals
are coarse and exploratory, not multiplicity-adjusted or a qualification claim.

Building-search overall point estimates are below the filtered model against search
at all five counts. Combined search is below auction-only at all five counts.
Neither implementation advances. The strict endgame filter has no negative cell/rule
point estimate in this screen and is retained with frozen-1 as the research reference;
this is not a guarantee of universal benefit or a final candidate selection.

**Next:** exact replay diagnosis of auction regressions plus improved controls from
the saved immutable outcomes/decisions, before larger fresh confirmation. Selection
noise, opponent-policy mismatch and approximating future searches with model-only
continuations are plausible hypotheses; none is established by terminal summaries.
9,977 of 18,813 auction changes have simulated mean-credit advantage ≤1/8, a useful
diagnostic lead rather than a causal explanation. Do not retrofit rule-specific routing
to favorable outcomes, indiscriminately distill search actions or launch another large
unchanged grid. Freeze any resulting policy and its confirmation protocol on fresh
seeds after resolving the regressions. The separate resource ablation is still unlaunched
and still requires source packaging and resource-specific full-game runtime admission.

All 8,400 games and roughly 7.03 million candidate rollouts are complete. HF search
decision timings reflect eight concurrent games and are not 8840U serving latency.
This is evidence of a promising direction and identifiable failures, not a general
training plateau. No new jobs were launched by this review. No candidate selected,
no final qualification, no final seeds used; the exact-policy final integration gap
in the previous checkpoint remains relevant.

## Previous checkpoint: 133 batches verified; final qualification needs the exact selected policy

At **2026-10-24 20:56 UTC**, the coordinator accepted **133/135 batches and
8,208/8,400 games**. All model-only, filtered and building-search batches are
verified. Four- and five-player auction/search_geo also passed collection, with
64 and 80 games respectively. Only auction/6p/search_geo and combined/6p/search_geo
remain; direct HF inspection at 20:57 UTC confirmed both RUNNING, at 82/96 and
81/96 games, with no errors, caps or truncations observed in their last 200 lines.
Continue the same coordinator PID 2812975 / session 5513. No partial strength
comparison or selection has been performed.

Read-only inspection of the final runner identified a concrete integration gap:
`launch-final.py` → `arena-job.py` → `evaluate.py` uses the older engine search.
It does not call `PopulationPolicy` or encode the strict endgame filter, phase
arms, shared sampled worlds and balanced opponent policy mixture of this screen.
`search_scope.py` accepts `all` and `recharged-sealed`: these are rule scopes, not
auction/building phase arms. `verify-final.py` checks that older search contract;
it does not independently bind a population-hybrid arm or its world mixture.
The current `evaluate-population-policy.py` deliberately rejects reserved seed
names and marks all reports ineligible for qualification.

The existing twelve converted technical receipts, archived by
`policy-iteration-final-technical-evidence-v2.json`, cover the four trained models
with **zero search samples**. They cannot serve as the full selected-policy
benchmark for a filtered or hybrid candidate. If development and fresh confirmation
eventually select one of those policies, implement a separate exact-policy final
arena/receipt adapter, freeze its source and complete its required 8840U/package
parity checks before spending final seeds. Validate integration on non-reserved
seeds first. Preserve the existing final protocol's counts, opponents, thresholds,
pairing and cap rejection; never obtain a pass by reducing its scope or silently
substituting the old engine search. This is an integration requirement, not a
reason to launch qualification now or change the running comparison.

Audit scope: source and existing receipt inspection only; no new games, runtime
integration test, candidate selection, upload or final launch. Inspected code
hashes are recorded under `population_hybrid_final_integration_audit_v1` in
`strong/experiments.json`. All 32 running-experiment dependencies and the final
protocol hash remain unchanged. The registry still has no final run, its final
seed-use flag is false, and `ai/strong/candidate.json` is absent.

## Previous checkpoint: full-comparison archive helper prepared; remaining jobs continue

At **2026-10-24 20:31 UTC**, the coordinator has 128/135 batches verified (7,776
games). All 128 saved receipt identities were rechecked; their summaries have
zero rollout caps. Newly collected combined/5p/search_geo is job
`6adcba08046eb82b1ecdce06`, with 80 games archived at HF revision
`a631ae34d4671fbab27499f0a426dcd35afcf5a4`; receipt SHA
`5a579c85cb864b633bbd2b366c90266318ddaf7b504a313b83e0e4f9ad151101`.
The seven outstanding jobs were confirmed RUNNING at 20:30 UTC, with no errors,
caps or truncated games observed in their last 200 log lines. The same
storage-recovery coordinator PID 2812975 / session 5513 remains live.

Prepared `strong/archive-population-hybrid-development-v1.py` outside the frozen
experiment dependencies. Default invocation only reports readiness. `--execute`
first requires `comparison_complete`, all 135 batches/8,400 games, the exact source,
plan, code and per-batch provenance, and no previous archive outcome. It acquires
the coordinator lock, reruns the unchanged comparator against all saved decisions
and checks that every contrast reproduces. It then verifies the pinned recovery
archive against both canonical replacement guards/receipts and the parity proof.
The archive includes all raw per-game records and decision receipts, guards,
collection receipts, frozen verification code, full comparison and recovery proof.
Upload uses the existing pinned-download/SHA verification helper.

Syntax and default readiness passed. An actual `--execute` attempt while the
comparison was incomplete correctly failed before creating an archive, changing
the coordinator state/lock, downloading evidence or launching anything. All 32
frozen dependencies are unchanged. **The completed-data path is not yet exercised;
do not claim a full archive or comparison exists.** Once the existing coordinator
finishes successfully, execute this helper once and inspect its resulting descriptor
before reviewing the complete strength comparison. Unknown upload outcomes require
inspection, not an automatic rerun. No new experiment, policy selection or final
qualification was started.

## Previous checkpoint: both recoveries complete, exact parity proven, all batches submitted

At **2026-10-24 19:45 UTC**, the unchanged coordinator has submitted every one of
the 135 fixed batches and verified **107 batches / 6,544 games**. The complete
8,400-game comparison remains unfinished. No partial strength comparison or
candidate selection was performed. Final qualification seeds remain unused.

Both exact replacements are now authoritatively COMPLETED and fully collected:

- Four-player auction/legacy: `6adceba41e112550ce7e21fa`, 64 games.
- Five-player auction/economic: `6adcee5f046eb82b1ecde67f`, 80 games.

The storage-recovery coordinator's mandatory parity gate passed. Its receipt is
`ai/runs/population-hybrid-storage-recovery-v1/repeated-games-verified.json`.
All 79 saved original games, **9,258 decisions**, and the **14-decision prefix**
from the originally failed episode 36 are identical, excluding elapsed times and
the decision-file hash affected by those times. The failed episode now completes.
The original failure evidence remains preserved; the storage resource that caused
the original error is still unidentified.

`strong/collect-population-hybrid-recovery-completion-v1.py` independently repeated
the saved-record/decision comparisons without invoking or rewriting the active
coordinator's parity check. It verified original and replacement artifact manifests,
fresh HF terminal statuses, both collection receipts and all 32 frozen dependency
hashes. It archived 13 evidence files, uploaded the archive, and downloaded the
pinned revision to verify its SHA. This collector launches no jobs and performs no
strength selection. Its one-shot archive must not be blindly rerun.

Evidence: `strong/population-hybrid-recovery-completion-evidence-v1.json`;
private HF revision `dcde2edaa1ead7128f3dc9a5c0b36c18044f3400`, archive
`archives/population-hybrid-recovery-completion-evidence-v1.tgz`, SHA
`b1ff5e5387e7d61c3dbcd34969a3f1e5a815498cb480aa0f93882c91a85cf349`.
The subsequent collection review checked all 15 newly accepted batch receipts,
confirmed the full 135-case guard set, and inspected the final 11 submissions:
six RUNNING and five already COMPLETED at 19:45:52 UTC. Local snapshot:
`ai/runs/population-hybrid-live-runtime-v1/20261024T194552649430Z-collection-review.json`.

Continue PID **2812975** / session **5513** through the existing storage-recovery
adapter. No further planned grid submissions remain; await/collect existing jobs.
Do not bypass the adapter, duplicate a job, select from partial results, or start
the prepared resource experiment before reviewing the completed fixed comparison.

## Previous execution checkpoint: 50 verified batches, comparison still running

At **2026-10-24 19:03 UTC**, the fixed hybrid screen has 50/135 verified batches,
containing **2,880/8,400 games**, with zero rollout caps in those verified batches.
All 50 saved receipt identities, source/guard bindings and 32 frozen dependency
hashes were rechecked. This checkpoint does not repeat every full decision/artifact
check; those checks were performed at collection and remain pinned in each receipt.

The coordinator snapshot at 19:01:25 UTC records 82 submitted / 50 verified.
Fresh authoritative HF inspection of the remaining 32 submitted handles found
31 RUNNING and one COMPLETED, with no additional terminal failures. The original
two failures below remain preserved. Both replacements are outstanding; actual
storage-replacement parity is still pending. The checkpoint is saved in
`strong/population-hybrid-50-batch-checkpoint-v1.json`, including receipt hashes,
private HF archive revisions and timestamped job statuses.

The live process was checked directly: PID **2812975**, session **5513**, running
`ai/strong/recover-population-hybrid-storage-v1.py coordinate --execute`.
Continue this adapter; do not start the original coordinator or duplicate jobs.
The coordinator continues its original fixed submission plan. No experiment,
model, policy, evaluation budget or running source changed for this checkpoint.
No partial win-rate comparison, candidate selection or final qualification was
performed. Finish the full screen before deciding whether to retain search or
launch the separately prepared resource-search experiment.

## Previous checkpoint: individual game-error visibility verified

Previous goal turn was a verified wait on the live coordinator and jobs. This turn
adds a read-only monitoring correction: the runtime observer previously parsed
completed-game progress but skipped an individual `episode/error` log event until
HF reported the whole job as failed. It now returns `observed_game_errors`
separately, validates the episode against the exact shard, and explicitly retains
the last-200-lines observation limit. An error event never changes authoritative
job status or automatically cancels/replaces a running job.

Four tests pass, including the actual preserved storage-failure log: 79 completed
games plus the missing episode 36 error. Tests cover early error visibility,
irrelevant log messages, bad episode ranges and error shapes. This observer is
outside the frozen execution dependency set; all 32 frozen hashes were rechecked.
No policy, source package, evaluation budget, active coordinator or job changed.

The new live scan is
`ai/runs/population-hybrid-live-runtime-v1/20261024T175837114375Z-game-errors.json`:
all 32 inspected jobs RUNNING, no observed game errors, caps, truncations or
observation errors in the bounded log windows. This is execution health evidence,
not verified full-game outcomes, model strength, or proof of error-free full logs.
Evidence: `strong/population-hybrid-game-error-observer-evidence-v1.json`.

Continue PID 2812975 / session 5513 through the storage-recovery coordinator
adapter below. Latest coordinator snapshot at 17:54:36 UTC remained 72 submitted /
40 verified. Both replacements are running; actual repeated-game parity remains
pending. No new jobs, gradients, independent experiment or final qualification.

## Previous checkpoint: storage failure preserved, exact batch replacement, parity gate

Previous goal turn: progress (the no-start failure recovery below). This turn:
progress from discovering and recovering a separate terminal storage failure.
The fixed hybrid comparison remains incomplete and final seeds remain unused.

A read-only scan of all 32 unverified handles at 17:37 UTC found 30 running,
one completed and one ERROR: `6adcdcf81e112550ce7e17d3`, case
`population-hybrid-development-v1-auction-5p-economic-0-4`. The coordinator
PID 2740649 / session 65141 stopped at 17:37:51, 71 submitted / 40 verified.
The session exited 1 and the process is absent. Do not resume that direct entry.

### Original failure and recovery decision

The job ran for 3,822 seconds and saved 79/80 completed games, with zero reported
caps in those games. Episode 36 failed with
`OSError: [Errno 28] No space left on device`. The logs do not localize the storage
resource or prove its underlying cause. The saved compressed archive is 552,097
bytes, so the archive size alone does not explain the failure. No playing-strength
outcomes were selected from this partial batch.

The failed job itself uploaded its evidence to private HF revision
`20afd14932631ee54be6bf27b5bc5ae312bf3eb8`, archive SHA
`88ae0fd0177e006e869ff7b4bc0044c8127392b54c9c95f90b486942cd29ae66`.
All 163 archived entries were verified and retained in
`ai/runs/population-hybrid-auction5p-failure-v1/artifacts`.
Original guard, logs/status, stopped coordinator and all 71 guard hashes are also
preserved there. The review validates 79 completed records / 9,258 decision
receipts and all 14 saved decisions from episode 36. This is partial consistency
evidence, **not** full-cell verification or an accepted strength result.

### Exact replacement and mandatory repetition check

`strong/recover-population-hybrid-storage-v1.py` reuses the original guarded
one-shot launch implementation, with a separate failure-specific admission.
The dry run revalidated the terminal job, stopped coordinator, original pinned
partial archive and hashes. Replacement job **6adcee5f046eb82b1ecde67f** reruns
the same 80 games; only job ID and launch time differ from the original launch.
Model, source, seeds, hardware, nine-hour timeout, workers and search budgets are
unchanged. There is no automatic retry of this replacement.

Original guard SHA: `0c4b3e7c187e081f71a5b8ac950024f88be8ea9d9d613ce3414a8270781f9e45`.
Replacement guard SHA: `96f153f299c0db83769a23121b38e05692ddcc74846744db2a5c078032ca9644`.
The other 70 existing guards and all 32 frozen plan dependencies were checked
unchanged. The first no-start replacement from the previous checkpoint continues.

The new execution adapter imports the unchanged coordinator and adds a strict
check to both fresh collection and reuse of a saved verified receipt for this
one case. All 79 repeated terminal results and their full decision receipts, plus
the failed game's saved prefix, must match. Only timing fields and receipt digests
that include timing may differ. Any mismatch stops the coordinator before final
comparison. Actual replacement parity is pending; successful unit tests are not
represented as a successful remote repetition.

Five tests pass: the actual saved partial records; rejection of changed/capped or
complete reports; rejection of live/wrong jobs or missing evidence; parity that
rejects changed moves and simulated outcomes; and failure propagation through
both coordinator collection paths. They launch no jobs and change no policy.

### Current execution and next action

- Sole active coordinator: **PID 2812975 / session 5513**, via
  `ai/.venv/bin/python -u ai/strong/recover-population-hybrid-storage-v1.py coordinate --execute`.
- Log: `ai/runs/population-hybrid-storage-recovery-v1/coordinator.log`.
- State remains `ai/runs/population-hybrid-development-coordinator-v1/state.json`.
- Snapshot 2026-10-24T17:44:23 UTC: waiting, **72 submitted / 40 verified**, no failures.
- Failure evidence: `strong/population-hybrid-storage-failure-evidence-v1.json`,
  private HF revision `67f14a02db09fb49d00e3794185f8dad3545d772` (178 entries).
- Admission: `strong/population-hybrid-storage-recovery-admission-v1.json`.
- Launch/resumption evidence: `strong/population-hybrid-storage-recovery-evidence-v1.json`.
- On successful replacement collection, inspect
  `ai/runs/population-hybrid-storage-recovery-v1/repeated-games-verified.json`.

Continue the existing fixed screen. Do not start a direct original coordinator,
modify the active adapter or frozen sources, rerun a replacement launcher, use
partial outcomes, or start the prepared resource experiment. The 5p/6p combined
search jobs were separately confirmed RUNNING at 17:35 UTC, at 24/80 and 31/96
completed games; runtime risk remains an observation, not a terminal failure.
No training gradients, independent new experiment, candidate or qualification.

## Previous checkpoint: terminal no-start failure preserved and exact replacement resumed

The original coordinator PID 1447977 / session 53211 exited with a real failure
at 2026-10-24T17:20:59 UTC (70 submitted / 38 verified). It is absent and must not
be treated as live. HF reports job `6adce697046eb82b1ecde31d`, case
`population-hybrid-development-v1-auction-4p-legacy-0-4`, ERROR with exit code 6,
`started_at=null`, and `No logs available`. The underlying cause is unknown.
This differs from the still-running 5p/6p combined-search runtime warnings below.

Original failure records are retained in
`ai/runs/population-hybrid-prestart-failure-v1` and the private HF evidence archive
pinned by `strong/population-hybrid-prestart-failure-evidence-v1.json`
(revision `e3286f02e53834628245b972fda16b20e1d0621c`). All 32 previously unverified
jobs were inspected; this was the only terminal failure. The failed case had no
saved result archive at the checked HF revision. No partial result was selected.

`strong/recover-population-hybrid-prestart-v1.py` admitted and launched exactly
one replacement after fresh terminal-status/artifact checks, archived evidence
hash checks, a stopped coordinator and exclusive locks. It preserved every launch
field except job ID and creation time, then added original-failure provenance to
the replacement canonical guard. Its four tests reject live/unknown/completed or
started jobs, changed guards, repeated replacements, live coordinators and existing
artifacts. No frozen screen dependency, source, model or protocol was edited.

- Replacement job: `6adceba41e112550ce7e21fa`, same original games and settings.
- Original guard SHA: `5c2a3980ec6e1e6fc7a1e21ca198277cf5c81b8ef6dd2c48bbdd942604752d6b`.
- Replacement guard SHA: `b3e47d804a2b8e7378915d2f0a502c33be43ca1d4982a2a4455268bff9193598`.
- Other 69 original guards verified unchanged before and after resumption.
- Resumed unchanged coordinator: PID **2740649**, session **65141**.
- 2026-10-24T17:32:42 UTC: waiting, **71 submitted / 39 verified**, no failures.
- Coordinator log: `ai/runs/population-hybrid-prestart-recovery-v1/coordinator.log`.
- Admission/evidence: `strong/population-hybrid-prestart-recovery-admission-v1.json`
  and `strong/population-hybrid-prestart-recovery-evidence-v1.json`.

The recovery helper does not itself resume the coordinator; that was done once
after verifying the installed guard. The saved `resumption-check.json` records
this later action, so the earlier launch state intentionally says not resumed.
Do not rerun the helper or launch another coordinator. The existing coordinator
continues the original 135 logical shards / 8,400 games, with no automatic retries.
The conditional timeout partition below remains unlaunched and is not this recovery.

Current recommendation remains selective model-plus-search, judged by the full
fixed comparison before adopting any search scope. The completed model-only
development comparison gives frozen-1 51.5625% against search_geo in 4p overall
(256 games / 16 deals), 39.0625% Recharged sealed (64 games / 16 deals), versus
parent 30.8594% / 15.625%. These are development results, not final qualification
or a measured hybrid improvement. No new independent experiment or gradients,
no candidate publication, and no final seeds used. Finish this screen before the
prepared resource experiment or further optimization sweeps.

## Previous checkpoint: broader runtime risk and conditional partition spec

Previous goal turn: verified wait; two shards completed and the existing coordinator
advanced. This turn: progress from a broader live execution scan and tested timeout
partition specification. All local checks/archive work completed. This preparation
launched no recovery jobs/games or gradients. The existing coordinator continued
its original grid; no running guards, source, model, plan or coordinator modified.

Coordinator PID 1447977 / session 53211 remains active. At
2026-10-24T17:05:36.253591+00:00 it reports 66 submitted / 34 verified, no failed jobs.
Both slow search jobs were directly confirmed RUNNING again, with the coordinator
present, and explicitly rejected by the new recovery-spec gate.

### Broader execution observation

`ai/runs/population-hybrid-live-runtime-v1/20261024T165902795776Z-live-grid.json`
contains 30 jobs from the coordinator's prior live snapshot. All 30 were RUNNING;
no observation errors or caps in completed-game logs. Four newer jobs absent from
that snapshot were separately confirmed RUNNING in
`20261024T170134979081Z-observation.json`. These are staggered observations, not a
single simultaneous all-job census or independent result collection.

The 30-job scan found two completed-rate warnings after 30 minutes of execution:

- Five-player combined/search_geo, `6adcba08046eb82b1ecdce06`: 19/80 games after
  10,654s; crude extrapolation 12.46h against the 9h configured budget.
- Six-player combined/search_geo, `6adcba011e112550ce7e0464`: 25/96 after 10,655s;
  crude extrapolation 11.37h. The earlier short CPU observation is below.

These remain risk flags from ordered, concurrent, censored games—not ETAs, proof
of timeout or reasons to replace an active job. No playing-strength outcomes were
compared or selected. Continue the same handles and sole coordinator.

### Prepared partition, deliberately not an executable recovery system

`strong/hybrid_timeout_partition_v1.py` uses the frozen job's existing one-deal
range support to specify splitting a failed four-deal shard into four one-deal
jobs. It retains the source/model/bootstrap, hardware, nine-hour per-job budget,
eight game workers, one search worker, eight sampled worlds, horizons, absolute
episodes and every seat/rule. Original failed guard and lineage must be preserved.

The specification requires a confirmed terminal ERROR identified as timeout,
unchanged canonical guard, stopped/absent original coordinator, preserved/reviewed
failure and no recoverable artifacts. A live/unknown/finished job, low-CPU warning,
unrelated error, repeated replacement or missing review is rejected. A real future
launcher must still verify the actual failure files/hashes and fresh remote state;
the pure unit-test review declarations are not evidence of a real failure.

`test_hybrid_timeout_partition_v1.py`: six tests pass. Applying the hypothetical
partition to all 135 original rows preserves all 8,400 episodes exactly with no
duplicates, omissions or scope changes (540 potential one-deal rows). This is a
coverage test, not a plan to launch 540 jobs. The positive failure test is explicitly
synthetic. Actual read-only checks of the 5p/6p jobs reject them as RUNNING; no real
failure admission exists.

No submission, guard replacement, collection or comparator integration is
implemented. If an actual timeout occurs, first retain/review its logs/status and
look for recoverable complete artifacts. Only then implement and verify the
necessary launcher/collector/comparator using explicit original/child provenance,
complete all children, and retain every other unchanged logical shard. Never label
the original ERROR job as COMPLETED or count a partial child as its full shard.
Do not restart the original coordinator against changed guards/code.

### Persistent evidence

- Descriptor: `strong/population-hybrid-timeout-partition-evidence-v1.json`.
- Local tests and live rejections: `ai/runs/population-hybrid-timeout-partition-v1/`.
- Private HF revision: `44551e4bfff0f4e62430ff487cc580d8a4f778cd`, 46 archive entries,
  including source, tests, exact frozen dependencies, original 5p/6p guards and both
  broader execution snapshots.
- Archive: `archives/population-hybrid-timeout-partition-evidence-v1.tgz`, downloaded
  and SHA-verified:
  `c34aff3b882df8502f0592e6b3273d3bb496abac1e5a709b4679492d74d426bd`.

No candidate, AI publication or final qualification. Final protocol/seeds and all
32 active-screen dependencies are unchanged. Resource-specific experiments remain
unlaunched pending the complete fixed comparison.

## Previous checkpoint: live runtime risk, no remote mutation

Previous goal turn: progress (resource preflight pushed as 104b635). This turn:
progress, from live evidence that changes runtime expectations. The sole
coordinator remains PID 1447977 / session 53211, confirmed via its actual process.
At 2026-10-24T16:45:02 UTC it reports 62 submitted / 30 verified, no failed jobs.
No additional experiment, job retry, cancellation or changed search budget.

`strong/inspect-population-hybrid-runtime-v1.py` verifies the original plan/guard,
inspects the existing job ID, reads a finite tail of progress logs, and optionally
takes at most 30 metrics frames under a 40s alarm. It never collects results or
mutates jobs. All output is whitelisted execution metadata; no environment/secrets.
`strong/population-hybrid-runtime-observation-v1.json` preserves the actual raw
progress and 20-frame metrics observation, source hash, SDK version and limitations.

At 2026-10-24T16:47 UTC:

| Existing shard | Authoritative status | Games completed | Completed-game median / max |
| --- | --- | ---: | ---: |
| combined6psearch_geo, `6adcba011e112550ce7e0464` | RUNNING | 25/96 | 2,317 / 4,765s |
| combined6prush, `6adcba00046eb82b1ecdce00` | RUNNING | 42/96 | 1,366 / 3,057s |
| building6psearch_geo, `6adcba26046eb82b1ecdce1e` | COMPLETED | 96/96 | 666 / 1,166s |

All observed completed-game progress rows report zero rollout/game caps. This does
not certify the remaining games or bypass the coordinator's independent collection.
Combined6psearch had run for 9,978s on cpu-upgrade; 20 raw metrics frames show eight
allocated vCPUs, median reported CPU40% after the initial frame, peak RAM4.814GB of
32GB, no GPU. An earlier five-frame observation had roughly48–61% CPU. These short
samples cannot identify the cause, represent its entire runtime, or prove hardware
throttling. No per-process/SSH access was exposed for this job.

The simple completed-rate extrapolation is 38,316s (10.64h), above the fixed 9h
timeout; this is a **risk indicator only**. Games are ordered, concurrent and
censored by completion, so neither that estimate nor the current median is an
ETA or proof of a future timeout. The old endpoint pilot underestimated some
observed game costs. Do not shorten games/search, score incomplete games, cancel,
retry, or change the frozen plan because of this projection. Continue the same
handles and sole coordinator. If a real terminal failure occurs, retain it and
reconcile the stopped coordinator before deliberately designing a documented
replacement with identical source, seeds, all seats/rules and no partial promotion.

The installed HF API has no live timeout-extension method; inspected
[official configuration docs](https://huggingface.co/docs/hub/jobs-configuration)
describe setting timeout at launch. No unsupported endpoint was attempted. This
is not a universal claim about every HF interface. No automatic recovery or extra
jobs were started. Building-only completion is runtime evidence, not a policy
strength conclusion. This is also not evidence that training has plateaued.

All 32 frozen screen dependencies and final protocol remain unchanged. Current
runtime measurements reinforce requiring new resource-specific admission after
the fixed comparison completes. No qualified candidate or final seeds used.

## Previous checkpoint: resource comparison preparation verified, unlaunched

Previous goal turn: progress (actual 8840U benchmark archived/pushed as a6f1919).
This turn: progress. Preregistered a fresh resource ablation and implemented its
independent decision/report checker. No new games, HF jobs or gradients; all local
checks and archive upload completed. The active screen stays unchanged.

Coordinator PID 1447977 / session 53211 remains confirmed live. Snapshot
2026-10-24T16:34:50.655557+00:00: 61 submitted / 29 verified, no failed jobs. Direct
HF inspection confirmed `6adcba011e112550ce7e0464` RUNNING, using the actual case
`population-hybrid-development-v1-combined-6p-search_geo-0-4` (not `search`).
No duplicate coordinator, manual collection, retries or cancellations.

### Prepared experiment, not launch admission

`strong/resource-replanning-development-protocol-v1.json`, SHA256
`e5e7c8d891a41c9c48ca0ee75d17fcd14b7ceeac827f600e3af6d177ff81e0d8`, fixes:

- `filter` versus `resource-filter`, exact frozen-1 model and original canonical
  runtime. Outside Resources behavior is identical. No hidden async-repair swap.
- Germany 2–6; 27 count/opponent cells inherited from the full screen; every seat
  and all four original/Recharged × open/sealed combinations; four fresh deals.
  Total 1,680 games per arm, 3,360 games. No per-rule/count routing or partial grid.
- Eight balanced opponent worlds, 2,400 continuation cap, 1,600 real-game cap.
  Whole hypothetical bundles are valued, but only the first action is executed;
  every actual resource request replans. Any cap invalidates the result.
- Fresh strength seed template `resource-replanning-development-v1-{players}p`;
  separate runtime-only `resource-replanning-runtime-v1-{players}p`. Neither used.
- Paired whole-deal bootstrap, 10,000 replicates, seed 12317. Primary descriptive
  summary averages the five search_geo player counts equally; preserve all cell,
  rule and opponent contrasts. Four-deal intervals are coarse, never qualification.

`strong/resource_development_v1.py` creates/validates the protocol and enumerates
1/2/4-deal partitions (216/108/54 potential shards), all preserving 3,360 games.
It cannot launch jobs. No source package, job wrapper, measured admission, launch
plan or coordinator for this experiment has been created. First finish/review the
current complete comparison. Then pin/package the separate runtime and use full
paired 2p/6p search_geo endpoint pilots with eight worlds to measure hardware and
runtime, independently check/replay results, and choose shard size/timeout. Existing
auction/building pilots do not establish resource-policy admission. No automatic
promotion; favorable screening still requires a larger fresh confirmation.

### Independent checker and tested limits

`strong/resource_policy_verification_v1.py` recomputes resource receipt consistency:
bundle counts, exact model baseline, selected first action, common sampled worlds,
balanced roles, common initial cash/holdings/market, continuation counts, terminal
tie credits, sample means, tie-breaking and cap fallback. A private import binds
this checker into the unchanged existing whole-game verifier; frozen files and the
running coordinator's Python module are never modified.

All 11 tests in `test_resource_policy_verification_v1.py` and
`test_resource_development_v1.py` pass:

- 112 existing phase decisions plus 540 decisions from the four existing full
  smokes; 11,900 rollout receipts. A genuine single-Pass-bundle search is accepted.
  The draft's initial two-bundle minimum was corrected from that real receipt
  before preregistration; no policy behavior changed.
- 80 existing paired base-policy control games / 10,207 decisions: private report
  adapter outputs exactly match the old verifier. An existing eight-world resource
  plan passes; the genuine deliberate one-step cap is rejected for strength.
- 24 corrupt decision mutations, a coherent but wrong selected plan, four corrupt
  reports, 20 weakened protocol changes and two stale source/evidence pins rejected.
  All 1/2/4-deal partitions retain every intended deal, seat and rule.
- Eight existing auction/building receipts wrapped as resource-combined/filter
  check envelope composition only; they are not new resource-combined games.

Receipt consistency alone cannot prove legality or reproduce inference. Earlier
engine replay covers the four smokes; a new full paired resource-specific report
does not exist yet and must be exercised by the future pilots. These tests and
preregistration do not establish new playing strength, speed or live integration.

### Evidence and next action

- Collector: `strong/collect-resource-development-preflight-v1.py`.
- Descriptor: `strong/resource-development-preflight-evidence-v1.json`.
- Exact tested inputs, source and logs: 243 archive entries; private HF revision
  `915e442bbaf540a10d0593eeed42798157047200`.
- Archive: `archives/resource-development-preflight-evidence-v1.tgz`, downloaded
  and hash-verified:
  `4c271e65c06a41227d3fe47f99ee72cc6a5745cd4752a8e7d8bb18c2065bc333`.
- Local assessments/logs: `ai/runs/resource-development-preflight-v1/`.

Continue the current fixed screen. Do not start extra optimization/strength sweeps
or resource pilots while it remains incomplete. Final protocol/hash/seeds unchanged;
no candidate selected, qualified or published.

## Previous checkpoint: actual 8840U resource stress profiling complete

Previous goal turn: progress (atomic policy and full-game engineering evidence
archived/pushed as a79cfa9). This turn: progress. The four saved slow resource roots
were profiled locally and on the actual target without changing the policy, model
or active comparison. Both runs and the evidence collector/archive are completed.
No gradients, new HF jobs, new strength games or final qualification seeds used.

The sole fixed-grid coordinator remains PID 1447977 / session 53211. Snapshot
2026-10-24T16:24:29.083368+00:00: 56 submitted / 24 verified, no failures; process
confirmed present. Do not start another coordinator, collect behind it, or retry
quiet jobs. Finish all arms/cells before selecting or launching another sweep.

### Fixed package and checks

`strong/benchmark-resource-replanning-8840u-v1.py` prepares and guards the one-shot
local/remote run, collects cross-machine equality, and archives evidence.
`strong/profile-resource-replanning-runtime-v1.py` wraps prediction, EnginePool and
root Node calls in passive timers, restoring them after each search. The package
contains 1,238 unchanged runtime files from the independently verified atomic
runtime, exact frozen-1 ONNX, four saved public roots, and the timing runner.

- Package: `ai/runs/resource-replanning-8840u-prepared-v1/package.tgz`, SHA256
  `73356e16b33ac9f98da3ccf829354d9d559ebabd784548dcc0c39e5b2ebbcc6c`.
- Package manifest SHA256:
  `cdebd3353d4bcc4aacd8cde5dce260428830bc5ff5e6314646f28d1b9abc8e39`.
- Model SHA256:
  `55331f43379e8fe89025d93b1a7a48c88e0ea39b4ebd3a7ef8240d4b62753530`.
- Local output: `ai/runs/resource-replanning-profile-local-v1/`.
- Collected target: `ai/runs/resource-replanning-8840u-collected-v1/`.
- Guard: `strong/resource-replanning-8840u-launch-v1.json`.
- Remote: `minipc:/home/coyotte508/powergrid-ai-resource-replanning-8840u-v1`;
  PID 2929509 terminal, status passed, command no longer present.

Each machine completed 12 searches and 672 rollouts with zero caps: the four
slowest resource decisions from the earlier four integration games, under settings
(ORT threads, JS workers) = (1,1), (1,4), (4,4). Samples remain four worlds and
continuation cap 2,400. Every complete result matches its original recorded
decision and all settings/machines after JSON-key normalization and exclusion of
elapsedMs only. Local and remote receipt/output hashes pass. No behavior/default
changes, no inference approximation and no new rollout seeds.

Target reported AMD Ryzen 7 8840U, Python 3.12.3, NumPy 2.5.3, ONNX Runtime 1.30.0,
Node 24.19.0. Total target run 77.785s, finished 2026-10-24T16:24:03.335496+00:00.
HX370 local run 91.070s; neither elapsed total is a strength or typical-latency claim.

### Target measurements and interpretation

| Fixed slow resource root | 1 thread / 1 worker | 1 thread / 4 workers | 4 threads / 4 workers |
| --- | ---: | ---: | ---: |
| 2p original/open | 17.352s | 15.175s | 9.341s |
| 2p Recharged/sealed | 4.144s | 3.630s | 2.519s |
| 6p original/open | 6.509s | 5.812s | 3.733s |
| 6p Recharged/sealed | 3.478s | 3.280s | 2.277s |

This is a single run per setting on four selected slow roots, not a representative
latency distribution. Settings run in fixed order; timing noise/thermal effects
are not isolated. Do not claim these speedups universally or compare the two CPUs
as a hardware ranking.

At 1/1, prediction takes 10.465/2.265/4.031/2.011s and engine-pool calls
6.614/1.825/2.403/1.430s respectively. At 4/4, prediction takes
4.679/1.168/2.030/1.217s and engine-pool calls 4.381/1.294/1.626/1.021s.
Prediction includes array packing and ONNX; engine calls include JS, IPC and JSON.
These are serial wall-duration attributions, not CPU utilization or pure inference
kernel timings. Root preparation and remaining Python are small in these cases.

More JS workers alone modestly helps; the ONNX thread increase matters on the
8840U. Both major paths remain costly. A Rust rewrite cannot remove prediction
time by itself. Do not change defaults or start another optimization sweep while
the fixed 8,400-game strength screen is incomplete. The provisional product
direction remains a fast model for instant feedback, selective deeper search for
bot jobs or analysis if fresh paired evidence supports it, and search-generated
teaching labels to improve the fast model. The resource wrapper's full-game
strength still requires a separate frozen comparison after the active screen.

### Durable evidence

- Descriptor: `strong/resource-replanning-8840u-evidence-v1.json`.
- Private HF model repo revision: `2f6051a13a666ffa5cd94914bc1f866b819791a4`.
- Archive: `archives/resource-replanning-8840u-evidence-v1.tgz`, 15 entries,
  downloaded and SHA-verified:
  `cc1b97196b2737c820f516d75466ce059aace56b6ff304e2c6403f20baa641a5`.
- Raw target results SHA256:
  `2ca3baa4b2c42a456e4ebeb0b47a24b311540ac0703bbda8ecd0a7809ca127bb`.
- Raw local results SHA256:
  `646851b6508232cd08f50133192a80f70119d5b4f09233911cfc800f5e78ef22`.

No candidate is qualified/published. Keep the final protocol and reserved seeds
unchanged. Existing research serving still needs the separately verified async
sealed-order repair pinned into any later adopted runtime; this benchmark did not
silently apply it or alter the frozen screen source.

## Previous checkpoint: atomic resource replanning verified; early-game cost exposed

Previous goal turn: progress (complete-turn search archived/pushed as 96c2f50).
This turn: progress. Implemented the actual one-action-per-request policy, checked
complete resource turns and four full games, independently replayed their atomic
moves, and archived the evidence. All local probes, games and collector are terminal.
No HF jobs or gradients launched; no strength or final qualification claimed.

The sole fixed-grid coordinator remains PID 1447977 / session 53211. At
2026-10-24T16:03:44.550787+00:00 it reports 49 submitted / 17 verified, no failures.
Direct inspection confirms combined6psearch job `6adcba011e112550ce7e0464` RUNNING.
All frozen dependencies remain unchanged. Do not start another coordinator or
retry/cancel current handles based on quiet logs.

### Actual atomic policy and checks

`strong/resource_replanning_policy_v1.py` wraps the unchanged population policy.
For resource-filter, other phases use model + strict loss filter; resource-combined
can compose it with auction/building search. The default resource-filter variant
was exercised in the checks below. At each resource request it evaluates complete
bundles, returns only the selected first move, and discards any notion of a pending
plan. The next request is evaluated afresh. Thus no platform-side plan storage or
cross-request memory is required. This is explicitly a **different policy** from
the committed macro teacher. The hypothetical search rollouts still assume the
complete bundle followed by model continuations, not recursive future replanning.

The module also provides a research JSONL worker with request ID/revision echo,
one atomic move, errors without a move, and optional diagnostics. The platform's
authoritative revision/legal-action checks remain necessary. This is not live BGS
integration or a qualified serving package; the frozen canonical sealed-order
restriction outside resources still needs the separately tested repair before
deployment. `strong/evaluate-resource-replanning-v1.py` reuses the unchanged arena
runner via an explicit process-local policy factory, without editing frozen files.

The isolated runtime in `ai/runs/resource-replanning-v1/runtime` preserves all 1,467
inherited files (1,463 original frozen files plus the earlier four proposal/search
files), then adds three separately pinned files. `preparation.json` and
`selection.json` were saved before testing. Both copies and checks are complete.

`strong/probe-resource-replanning-v1.py` passed:

- 1,798 exact outside-resource model/filter controls.
- 23 complete existing resource turns, 112 atomic choices, 111 actual searches and
  4,744 rollouts, zero normal caps. Engine stepping checks prices, legal actions,
  market depletion, holdings, completion and bounded progress.
- Fresh-process and interleaved-request identity, request-metadata invariance,
  standalone JSONL equivalence from `/tmp`, and deliberate-cap model-action fallback.
- The known omission executes three coal buys for 17 then Pass. One opening differs
  from its initial hypothetical plan: early 2p Recharged/sealed proposes two coal
  but actually buys four after replanning. The other 22 quantities/sequences match.
  Neither that change nor the known repair establishes a general strength gain.

The first run completed all turn checks but failed its standalone assertion by
comparing integer-keyed live dictionaries with JSON string-keyed dictionaries.
Reproduction proves identical moves and data after JSON roundtrip. The policy and
runtime stayed unchanged; only comparator key normalization and the output folder
changed. Preserve `checks/`, `failed-probe-v1.py`, `standalone-reproduction.json`,
`serialization-diagnosis.json` and `probe.log`. The complete corrected rerun is in
`checks-v2/` with `probe-v2.log`; both attempts' actual decisions match exactly.

### Full-game integration and latency finding

`strong/probe-resource-replanning-games-v1.py` completed four predeclared games:
2p and 6p, original/open and Recharged/sealed, learner seat 0, economic opponents,
four sampled worlds / one search worker, two game processes locally. These are
engineering seeds, not strength samples. Results: 540 learner decisions, 167
resource searches, 7,156 rollouts, zero game/rollout caps. Do not report their win
rate as strength evidence. Raw decisions, configs and terminal reports are under
`ai/runs/resource-replanning-v1/games/`; all four passed.

`strong/replay-resource-replanning-games-v1.cjs` independently reconstructs each
game from setup and seeded economic opponents, checks every saved action against
its true engine index, and reproduces all terminal fields and policy counts:
540 learner moves + 1,454 opponent moves. It saves the slowest **public** request
from each game, with its original decision, under `replays/*-slow-root.json`.

The full games expose a cost hidden by the mostly-late fixture sample:

| Case | Searches | Local median | Local maximum |
| --- | ---: | ---: | ---: |
| 2p original/open | 47 | 6.529s | 21.412s |
| 2p Recharged/sealed | 48 | 1.953s | 4.881s |
| 6p original/open | 43 | 5.034s | 10.131s |
| 6p Recharged/sealed | 29 | 2.926s | 6.436s |

These HX370 timings were taken while two game processes ran; they are neither an
8840U benchmark nor a representative game distribution. The earlier 112-choice
fixture median was only 609.5ms, maximum 2.771s. Do not use that easier subset as a
general latency claim. Profile the saved expensive roots and test the actual target
before deciding whether to optimize live search or use it primarily as a teacher.

### Evidence and continuation

- Descriptor: `strong/resource-replanning-evidence-v1.json`.
- Private HF revision: `ac7034af7546d5d3ef7ecbc7b26075bce6ec5c31`.
- Archive: `archives/resource-replanning-evidence-v1.tgz`, 51 files, downloaded and
  SHA-verified: `04f8becf8445912dd5b9b1ebbc54569f5babc58b78a45bd5aa117fc708aa47cc`.
- Collector: `strong/collect-resource-replanning-v1.py`; completed log at
  `ai/runs/resource-replanning-collection-v1.log`. Do not rerun over the archive.
- Completed sessions: initial probe 38233 (failed comparator only), reproduction
  72034, corrected probe 1570, games 37641, collector 39784.

Next: continue the unchanged five-arm grid. The saved slow roots support measured
profiling / actual8840U serving experiments. A later resource study must evaluate
the **actual atomic replanning policy** on fresh paired games across counts/rules
and independent opponents, separately from committed-macro teacher experiments.
Do not infer strength from these four smokes or change the running grid. Any final
runtime also needs the separately pinned asynchronous sealed-order repair and
full final serving checks. No candidate, publication or reserved final seeds used.

## Previous checkpoint: whole-resource-turn search integration verified in isolation

Previous goal turn: progress (proposal evidence archived and research pushed as
f890710). This turn: progress. Added complete resource-turn valuation, ran actual
model integration and independent engine controls, and archived verified evidence.
No new HF jobs, gradients, fresh strength games or final seeds used for this work.
Existing coordinator PID 1447977 / session 53211 remains active; its 15:38:03 UTC
snapshot is 44 submitted / 12 verified, no failed jobs. The combined six-player
search opponent handle `6adcba011e112550ce7e0464` was directly confirmed RUNNING
this turn. Do not start a duplicate coordinator or change its frozen sources.

### New resource search and execution contract

- `strong/resource-turn-search-v1.cjs` adds an exact model-turn state machine,
  retaining the model's actual purchase order through its final Pass. If that
  stockpile is absent from the one/two-cycle candidate family, it is appended.
  Zero purchases is also always present. No candidate is pruned on construction
  route assumptions. Every root macro is executed through the actual engine.
- `strong/resource_turn_search_v1.py` evaluates every complete bundle in shared
  public sampled deck worlds. Each opponent spans neural/economic/legacy/rush
  roles evenly. The focal future policy is the model with the existing strict
  endgame-loss filter. No nested search and no forced building route. Exact
  terminal win credits determine the choice; ties prefer the original model turn.
- Search receipts include the common pre-action world hash, every root purchase,
  prices, post-purchase money/stock/market, roles, continuation action counts and
  terminal powered cities/cash/city counts. Any capped rollout invalidates the
  search and returns the model's **whole** turn. The cap counts continuation moves;
  root macro actions are recorded separately and do not consume that horizon.
- **The returned complete plan must be committed.** Calling this anew after each
  purchase and executing only `firstMove` is a different policy. No complete-game
  arena adapter or stateless platform persistence contract exists yet. Do not
  present it as production-ready or silently equate these execution modes. It
  could instead be used as a teacher on fresh roots and distilled into the model.

### Checks completed

The isolated package is `ai/runs/resource-turn-search-v1/runtime`; all 1,463 frozen
source files were copied unchanged, with separately pinned new modules only.
Preparation completed before any tests started. All processes are terminal:
contract session 41490, actual-model probe 13624, evidence collector 73434.

`strong/test-resource-turn-search-v1.cjs` checks 755 resource positions across all
20 count/rule cells, 2,840 arbitrary baseline steps, 755 hidden-data preparations,
329 partial baselines outside the generated menu, 236 independent root macro
replays, 186 continuation response comparisons and 100 invalid requests. All pass.

`strong/probe-resource-turn-search-v1.py` verifies all 755 actual model baselines
(2,251 decisions), including exact first-action parity with the unchanged model
adapter. Before search, `selection.json` fixed 20 late positions using public
round/city count, two opening Recharged-sealed endpoint fixtures, and the separate
known outcome-selected fuel omission. The 23 searches complete 1,232 rollouts.
Partition, hidden-data and sample-prefix controls add 464 complete rollouts, all
exact with zero normal caps. The intentional one-step test has 116 capped rollouts
and correctly preserves the full model baseline. No selected probes are strength
games; no claims generalize from these samples to a win-rate improvement.

Four of the 23 positions change plan. In the known omission, search selects three
coal costing 17 rather than Pass. The baseline scores [0,0,0,0] and that bundle
[1,1,1,1] over the four sampled opponent/deck worlds. These are simulated credits
under an uncalibrated equal opponent mixture, not estimated true win probability.
Local HX370 timings over the 23 engineering positions: median 765.9 ms, maximum
2,794.9 ms. These are mostly late positions with four worlds, not representative
gameplay latency and not an AMD8840U benchmark.

### Preserved evidence and next action

- Descriptor: `strong/resource-turn-search-evidence-v1.json`.
- Collector: `strong/collect-resource-turn-search-v1.py`; completed output in
  `ai/runs/resource-turn-search-collection-v1.log`. Do not rerun over its archive.
- Private HF revision: `ec76db0d6fe37a4fd94aa620e86ba9a06f35939c`.
- Archive: `archives/resource-turn-search-evidence-v1.tgz`, 25 files, downloaded
  and SHA-verified: `5eeac23003cbc8ef510dea3282257c7718334b0d7e67ba27e737809951fbae7d`.
- The collector rechecks all source hashes and raw artifacts, every saved bundle's
  budget, terminal score ordering, win credits, means, tie selection and controls.

Next: preserve and complete the current five-arm comparison. Before adopting
resource search, implement and verify complete-plan execution in the arena and
resolve its serving contract, or define a separate per-purchase replanning policy
and evaluate that actual policy. Freeze fresh paired games before observing
outcomes; test all counts/rules/opponent cells and latency. The known omission
remains a diagnostic example, not an unbiased training label. Resource-turn
teacher generation on fresh roots is also viable. No final candidate or production
AI publication; reserved final seeds remain untouched.

## Previous checkpoint: resource-turn proposals verified, not integrated

Progress: the isolated public fuel/construction proposal generator and its evidence
collection completed. All local tests and the archive upload are terminal; do not
restart the collector. No new HF jobs, gradients or fresh strength games were
launched for this prototype. Existing coordinator PID 1447977 / session 53211 is
alive: at 2026-10-24T15:22:39.465618+00:00, 40 submitted, 8 verified, no failed jobs.
All running-screen dependency hashes remain unchanged.

### Proposal mechanics and limitations

- `strong/resource-turn-plans-v1.cjs` accepts public, money-visible, standard
  Germany resource turns with 2–6 players. It enumerates each plant subset and
  hybrid allocation's requirements for one or two identical fuel cycles, subtracts
  existing holdings, and checks exact market prices, affordability and shared
  storage. The zero-purchase candidate is always retained. This is not every
  stockpile or every combination of different allocations across two rounds.
- A bounded native-engine construction beam (width 8, branch width 6) finds legal
  routes at different city counts. These annotate each fuel bundle's remaining
  budget and possible powered cities. They assume the current board with no
  intervening opponent actions or deck draws. They are neither optimal routes nor
  proofs that an absent route is impossible; no fuel candidates are pruned by them.
- `selectedMove` remains null. No neural score, opponent valuation, serving
  integration or changed policy is claimed.

### Verification and preserved failures

`strong/test-resource-turn-plans-v1.cjs` checks an isolated copy of all 1,463 frozen
source files plus only the new module. The corrected runtime is in
`ai/runs/resource-turn-proposals-v2/`; its complete checks passed:

- 755 public resource positions covering 20 player-count/rule cells; 7,185 legal
  bundles and 28,177 real-engine purchase transitions. Every position retains zero
  purchases and passes hidden-data invariance.
- 41 construction cases, 184 conditional paths and 336 executed joint witnesses.
  Independent exhaustive inventory checks cover 1,870 states and 422 minimum-fuel
  price targets. Four unsupported requests are rejected.
- The known omission is reconstructed through all 326 recorded moves, checking
  every public transition. A three-coal bundle costs 17, supports output 24 and
  includes a route to 21 cities costing 161, leaving 61 cash. This recovers a
  candidate; it does not imply the generator chooses it or predicts the win.
- The separate Python collector independently rechecks 336 saved bundles and
  1,342 joint budget annotations, verifies source/checker hashes and the unchanged
  running-screen dependencies, then archives and download-verifies all evidence.

Initial v1 rejected valid fusion plant 50/type 6 after 23 fixtures. Its module and
failure are retained in `ai/runs/resource-turn-proposals-v1/`. An initial v2 test was
started before its copy finished and failed on a missing engine module; that log
is retained too. The subsequent completed package passed the full suite. Do not
overwrite these failures or describe the first attempt as passing.

Local HX370 engineering medians: 0.387 ms fuel enumeration (755 samples), 6.478 ms
construction (41 samples); maxima 2.412 and 204.707 ms respectively. These measure
proposal generation only, not search latency or actual AMD8840U performance.

### Evidence and continuation

- Descriptor: `strong/resource-turn-proposal-evidence-v1.json`.
- Collector: `strong/collect-resource-turn-plans-v1.py`; completed output in
  `ai/runs/resource-turn-proposal-collection-v1.log`. Do not rerun it over its archive.
- Private model repo revision: `6c366e1a9f6230099e0af40d22ad2be7cb2ce1b8`.
- Archive: `archives/resource-turn-proposal-evidence-v1.tgz`, 58 files.
- SHA256: `d6265bd708c5d659f6c9bb57c5f1f69f5f87965afe204549df4d2ccdeded6c36`.
- Proposal module SHA256:
  `1540f21cfe0edd19b5cf2a370442228301ac52c7272735677c64c60a0a882d5a`.

Continue the existing fixed five-arm grid without modifying its source or launching
a second coordinator. A separate resource-search adapter should preserve the exact
existing model's full resource turn as an additional candidate, then score complete
bundles using public sampled worlds and varied realistic opponent continuations.
Fuel denial, future refill, player order and opponents' building must enter those
continuations. Select fresh evaluation roots before seeing outcomes; retain all
adverse cells and compare on fresh paired games before adopting it. Do not train
on the selected hindsight example as though it were an unbiased teacher label.

User asks whether hybrid AI/search is worthwhile: yes, as an empirically tested
direction. The quoted four-player 30.9% overall / 15.6% Recharged-sealed numbers
are the parent. Frozen-1 model-only development results are 51.6% / 39.1% against
search, with only 16 independent deals per cell. Hybrid strength remains pending;
actual8840U endpoint search measurements exist but do not prove strength. No final
candidate, publication or reserved final seeds used.

## Previous checkpoint: resource-planning weak-cell diagnosis verified

Previous goal turn: progress (isolated asynchronous sealed-bid repair). This turn:
progress. Reused the completed model-only grid to investigate remaining weaknesses,
then verified four full replays and one controlled resource-purchase intervention.
All local diagnostic processes finished. No new HF jobs, gradients, candidate
promotion or final seeds were used for this work. The separate existing coordinator
PID 1447977 / session 53211 continues at 2026-10-24T15:02:20.384283+00:00: 40 submitted,
8 verified, no failures. It may continue filling its already authorized slots.

### Complete descriptive analysis

`strong/analyze-complete-policy-economy-v1.py` re-verifies the immutable 33,600-game
model comparison, retaining all five models, 27 opponent/count cells and all four
rules. New terminal summaries and paired whole-deal intervals are in
`ai/runs/complete-policy-economy-v1/assessment.json`. The collector independently
recomputes absolute counts from all pinned raw reports and checks rank outcomes.

Two remaining weak cells for frozen-1 illustrate different problems:

- 2p Recharged/open: 11/32 win credit. Of 21 losses, 9 have unused nominal output,
   8 insufficient cities, 5 insufficient plant capacity and 6 powered ties lost on cash.
   Parent has unused output in 4/19 losses. Mean unused output increases 0.531 cities,
   marginal paired 95% interval [0.188,0.906]. The win-share difference is −6.25pp with
   interval [−18.75,+6.25]pp, so a true win-rate regression is not established.
- 6p Recharged/sealed: 23/96 win credit. Of 73 losses, 53 have fewer cities than the
   winner powers, 22 insufficient plant capacity, 7 unused output and 10 cash tie losses.
   Relative to parent, mean cities rise 0.615 while nominal capacity falls 0.531 and cash
   falls 7.57. This is not simply “always build more”; budget/capacity timing matters.
   The win-share difference is −3.125pp, interval [−11.46,+5.21]pp, also inconclusive.

Categories overlap. These are reused development results with only 16 independent
deals per cell. Marginal intervals are exploratory and not multiplicity-adjusted.
No causal phase attribution follows from these terminal counts alone.

### Fixed four-game replay and controlled resource branch

The full analysis freezes two hash-ranked cohorts before replay: one current-model
2p Recharged/open loss with unused potential (9 eligible cases), and one 6p
Recharged/sealed loss with insufficient cities but enough nominal capacity to match
the winner (38 eligible cases). The corresponding parent is retained for each.
`strong/replay-weak-cell-economy-v1.py` executes all four, with the existing public
economy observer and unchanged frozen model/engine/opponent policies.

All four replays match every recorded terminal field, policy counters and opponent
search statistics. The enhanced analysis checks every root move and continuous
before/after state: 1,983 moves total. Selected cases are diagnostic examples, not
frequency estimates. The six-player parent/current **entire public traces match**;
the learner finishes 11 cities / 18 plant capacity / 9 cash while opponents power 14.
This is an inherited weak trajectory, not evidence that the new correction caused it.

In the two-player frozen-1 case (episode 35, seat 0), the final resource Pass is root 326,
round 12. Public state has 15 cities, 239 cash, 10 coal left in the market, two coal plants
requiring six coal in total but only three held, a hybrid already covered by oil,
and a free plant. Nominal capacity is 24, fuel-supported capacity 18. It then builds
six more cities and ends with 21 cities / 18 powered / 78 cash; the opponent powers 21.

The separate frozen protocol `strong/weak-cell-resource-counterfactual-v1.json`
compares the original action with **three legal coal purchases then the same Pass**.
All future model/opponent policies, real future deck and seeded randomness are kept.
`strong/replay-resource-bundle-v1.py` and an independent collector verify:

- Original full public trace is byte-identical to its reference.
- Both branches share all 326 preceding root moves and the exact decision state.
- All subsequent root-state transitions are continuous; no truncations.
- The inserted purchases are legal and independently price-checked: 5+6+6=17.
   An independent plant-subset fuel calculation confirms 18→24 available output.
- The changed branch wins: learner 21 powered / 61 cash / 21 cities, opponent
   21 powered / 58 cash / 21 cities. Original branch loses 18/78 versus 21/60.
   The opponent reacts to the changed market, explaining its changed cash.

This establishes a conditional causal effect **on that selected trajectory only**.
It is not a deployment policy, teacher label, calibrated value or fresh strength
estimate. It does not justify blindly buying all fuel or infer a general win-rate gain.
Arena counters count policy proposals; the executed trace includes three inserted
purchases, so its trace length is the arena step count plus three.

### Preserved evidence and next action

- Descriptor: `strong/weak-cell-economy-evidence-v1.json`.
- Private model repo revision: `f9a067364f6d3ae8a4dce3a4cce76d84ccb95209`.
- Archive: `archives/weak-cell-economy-evidence-v1.tgz`; 57 files, downloaded and hash-verified.
- SHA256: `6635a373e4e173b78e7a5087f1c8f030739d9a8d1e78c26c6bf13f5e0141918e`.
- Complete descriptive report/selection: `ai/runs/complete-policy-economy-v1/`.
- Four replay traces: `ai/runs/weak-cell-economy-replays-v1/`.
- Verified phase/economy summary: `ai/runs/weak-cell-economy-analysis-v1.json`.
- Controlled branches: `ai/runs/weak-cell-resource-counterfactual-v1/`.

The latest fine-tuning roots are explicitly auction/building only
(`strong/strategic-training-collection-protocol-v1.json`, `strategic_collection.phase`).
The active population policy also searches only auction/building; BuyResource/Pass
uses the existing model. This does not mean the historical parent never trained on
resources. The causal result makes joint fuel/city planning a justified future
experiment, rather than automatically extending the same auction/build training.

**Next:** keep the current five-arm grid/source/protocol frozen and finish all cells.
If further development is needed, design a separately pinned resource-turn study
with public fuel bundles and feasible city targets, preserving ordinary cases,
all counts/rules, affordable storage/legal moves and resource denial effects. Select
fresh roots before outcomes; do not reuse this hindsight branch as a label. Compare
against the unchanged model/hybrid on paired fresh deals, retaining adverse cases.
Asynchronous-order repair and actual 8840U/standalone serving requirements also
remain as recorded below. No final candidate or strength qualification yet.


## Previous checkpoint: asynchronous sealed-order research repair verified

Previous goal turn: progress (current-engine compatibility audit). This turn:
progress. A real serving boundary problem was reproduced and repaired in a separate
runtime while the frozen 8,400-game strength grid continues unchanged. At
2026-10-24T14:41:49.409272+00:00 the same coordinator PID 1447977 / session 53211 reports
33 submitted, 1 verified, no failures. The existing coordinator filled one
new slot automatically. This separate repair launched no HF jobs or gradients. Final seeds remain untouched; no candidate is qualified.

### Diagnosis and platform relevance

`strong/audit-live-sealed-order-v1.cjs` checks the frozen research runtime and the
previously pinned engine 2.0.17 build. All 2,553 canonical fixture preparations pass.
From its 161 sealed-auction roots, **446 legal requests** reproduce two failures:
223 requests from a non-first pending bidder, and 223 requests after a different
pending bidder legally submitted first. Both engines accept the actions with
matching transitions. The frozen adapter rejects them before inference, including
its model/filter arms. There are examples in every Germany 2–6p original/Recharged
cell. The cases are constructed legal transitions, not a prevalence estimate.

Read-only BGS source inspection at `ebd02b74b0ecba1806f2ec15e990f8b2430d0fe9`
shows `apps/game-server/app/services/bots.ts` selecting the first bot by seat index
among all current seats, not requiring it to be first in the engine's pending list.
Thus a bot may be called while an earlier human is still pending. The exact clean
source and SHA are archived. This does not assert which commit is deployed or test
platform transport. Production/BGS files were not changed.

### Isolated repair and evidence

`strong/sealed-policy-beliefs-order-v2.cjs` is an experimental replacement for the
belief module, copied **only** to
`ai/runs/live-sealed-order-repair-v2/runtime/ai/strong/sealed-policy-beliefs.cjs`.
All 1,463 source archive files were verified; only that module differs in this copy.
The live/frozen source and all current plan dependency hashes are unchanged.

The repair determines submitted bidders as eligible minus pending. It permits any
pending focal bidder, validates the pending set/order and never reorders the real
player order or auctioning seat. Public state lacks the actual submission history,
so previous policy prompts assume committed bidders acted in their public player
order, then leave the actual pending bidders. **That is an explicit uncalibrated
belief approximation**, not recovered history. Canonical behavior is exactly retained.

`strong/test-live-sealed-order-v2.cjs` passed:

- 2,553 identical preparations and original prior prompts.
- All 446 known failure requests, plus all 640 pending-subset/actor combinations
   across ten full-seat fixtures, Germany 2–6 players, original/Recharged.
- 1,967 legal inferred-bid prompts and 1,086 hidden-data invariance checks.
- 80 fixed-bid submission-order resolutions with identical strategic outcome;
   40 malformed/out-of-turn/hidden-money requests rejected.

`strong/probe-live-sealed-order-v2.py` uses the actual frozen-1 model
`55331f43379e8fe89025d93b1a7a48c88e0ea39b4ebd3a7ef8240d4b62753530`:

- 2,172 model/filter decisions across 1,086 constructed requests, all legal.
- 12 noncanonical search requests across all ten cells plus two pending-only cases.
- Two canonical old/new search pairs; identical choices, worlds, credit outcomes
   and statistics, excluding elapsed time.
- One hidden-data search pair and one 1-worker/4-worker partition pair, identical.
- Total 18 full searches / 840 rollouts, zero caps, 88.1s on the local HX370.
   These are reused-fixture integration checks, not strength or 8840U latency estimates.

The independent collector rechecks every persisted decision, exact legal action,
committed actor list, all paired controls, immutable source and frozen dependencies.
It then archives 69 files, including scripts, complete constructed requests, raw
results, logs, original failures and BGS source provenance:

- Descriptor: `strong/live-sealed-order-evidence-v2.json`.
- Private model repo: `coyotte508/powergrid-ai-germany-v1`.
- Revision: `ae31a5c7b0aec86ca4e96d72dd4c7282973970ac`.
- Archive: `archives/live-sealed-order-evidence-v2.tgz`.
- SHA256: `bf91b6fafe78a616139dfdd6018b48d2c17fce48b21aa79c4ad55ac42993d125`.
- Local audit: `ai/runs/live-sealed-order-audit-v1/`.
- Local repair/checks/trained results: `ai/runs/live-sealed-order-repair-v2/`.
- All local audit/probe/collection processes finished. No additional observer or
   coordinator was started. The existing screen coordinator is the only active one.

### Continue without changing the active experiment

1. Keep coordinator 1447977 / session 53211 as the sole collector/launcher. Inspect
   its existing state/guards/handles. Do not restart quiet jobs, edit frozen inputs,
   collect behind it, or retry/cancel automatically.
2. Complete the whole fixed canonical grid and compare all five arms/opponent
   cells. Do not choose from partial results or claim strength from this repair.
3. If the hybrid merits fresh larger confirmation, pin a new runtime that explicitly
   adopts this repaired module. Preserve exact canonical controls and add a separately
   frozen asynchronous-submission-order comparison before claiming platform readiness.
   The current grid cannot establish strength for previously unsupported orderings.
4. The prior 8840U result remains evidence for the old canonical runtime. Any eventual
   selected runtime still needs exact standalone target checks and platform integration;
   the production engine/BGS driver and final candidate were not changed here.
5. Continue the unchanged qualification gate only after development selection;
   final reserved seeds are still unused. This work neither proves nor rejects a
   training plateau; the independent-game hybrid strength results remain pending.

## Previous checkpoint: current engine compatibility audited; hybrid grid continues

Previous goal turn: progress (runtime admission and launch of the fixed screen).
This turn: progress. A current-engine compatibility audit removes an unresolved
deployment concern while the unchanged hybrid screen runs. At 14:16:22 UTC the
sole coordinator PID 1447977 / session 53211 is confirmed alive, with 32 submitted
jobs, zero fully collected shards and no failed jobs. Representative HF handles
were independently confirmed RUNNING and producing completed games. No jobs,
gradients, source changes or candidate promotions were added this turn.

The earlier audit covered engine 2.0.14. A read-only fetch now identifies current
master `537e41e3184208c580afbd25077faf3264fc1678`, engine **2.0.17**. Its intervening
changes include alternate-deck/fuel-storage logic and colour selection. The
engine was compiled in an isolated diagnostic directory; the production checkout
remains clean, and every frozen evaluation dependency retains its hash. This is
the current repository engine, not a check of which version a live BGS game uses.

`strong/check-production-engine-compat-v2.cjs` compares this build with the exact
frozen source used by the active hybrid screen. It passed:

- 2,553 legal-menu checks and 7,659 feature checks, including the current 4.3
  feature revision and presentation-metadata invariance.
- 2,553 deterministic hidden-information scenarios reconstructed from public
  positions, identical across both engines.
- All **32,770** distinct legal/neural-candidate root action transitions in those
  scenarios, with identical resulting strategic states.
- 2,553 seeded default-bot transitions, zero differences.
- **80 complete games / 40,464 transitions**, covering Germany with 2–6 players, original/
  Recharged, open/sealed and four deals per cell, all states/outcomes identical.
  The whole-game trace policy is the existing mixed heuristic/economic policy;
  these games are compatibility checks, excluded from strength comparisons.

Independent collection rechecked **all 1,463 source-archive files** against the
runtime used by the checker. Lodash 4.17.21, seedrandom 3.0.5 and delaunator 4.0.1
versions and resolved entry hashes also match the current production checkout.
The audit uses the pinned complete dependency modules from the research source.
Only the earlier explicitly documented presentation/revision metadata exclusions
remain: root.poweringChoices, root.pendingMessages, and Starting Step 2/3 event text.
No exclusion was added to make this new audit pass.

Limits: automatic Germany setup with the standard deck, ordinary current-player
decisions. Alternate decks, other maps, manual colour/region drafting, pending
choice revisions and platform transport remain outside this certification.
This is compatibility evidence, not stronger play or production routing.

Evidence descriptor: `strong/production-engine-compatibility-v2.json`. All
**1,244 files** (source snapshot, compiled current engine, dependencies, checker,
raw results and hash receipts) are archived at model-repo revision
`6a36212303c706341e725bdba07d0fd7cd967984`, archive
`archives/production-engine-compatibility-evidence-v2.tgz`, SHA256
`474245b9e67df52803a1368aaeba13c81715b348922758033ca2c00244396a0b`.
Local evidence is under `ai/runs/production-engine-compatibility-v2/` and
`ai/runs/production-engine-compatibility-evidence-v2/`; its checker and upload
processes are terminal. Do not repeat the audit unless relevant source changes.

Next: keep the existing coordinator as sole collector/launcher, inspect its
specific handles and wait for the full prescribed comparison. Do not edit frozen
dependencies, choose from partial results, rerun quiet live jobs, or use final
seeds. The immediately following checkpoint records the execution plan.

## Previous checkpoint: both runtime pilots verified; full hybrid screen running

Previous goal turn: progress (actual 8840U parity/timing and archived evidence).
This turn: progress. The six-player runtime pilot completed and independently
verified. The measured execution plan is frozen and the **8,400-game initial
hybrid screen is now launched**. Its first 32 HF jobs are authoritatively RUNNING
at the recorded launch snapshot. No fresh strength comparison is complete, no
candidate is qualified, and reserved final seeds remain unused.

### Completed runtime admission

The original two v2 endpoint handles are both COMPLETED; do not relaunch them:

| Players | HF job | Games | Full rollouts | Wall time | Caps |
| --- | --- | ---: | ---: | ---: | ---: |
| 2 | `6adcad711e112550ce7dfe8d` | 8 | 20,696 | 498.465s | 0 |
| 6 | `6adcad7b046eb82b1ecdc9cd` | 24 | 53,312 | 2,862.506s | 0 |

The six-player verification checks 2,904 learner decisions, 1,301 searches,
434 search changes, two root filter overrides and 6,372,955 neural continuation
decisions. It recomputes receipt choices, means, terminal credits, pairing and
all counts; it does not replay every internal simulation. These runtime games
remain excluded from strength estimates. The six-player raw archive is at model
revision `4aeb3747d691b6eae7d4b08c9248be8f0016a663`,
`archives/population-hybrid-runtime-v2-6p.tgz`, SHA256
`8e01166682b0a3ec6d9c118f71198d34b56638316a6a0647fd8644160d11a325`.
Both local `verified.json` receipts are under
`ai/runs/population-hybrid-runtime-collected-v2/`. The bounded observer PID1423275
/ session78637 completed collection successfully and exited; do not restart it.

The new evaluator's snapshot-model opponent path also passed 12 separate local
compatibility games (3p, all seats/rules, nonzero deal offset1, 1,643 learner
decisions). Exact pinned A260 loading and callbacks work. Results are under
`ai/runs/population-policy-a260-compatibility-v1/`, excluded from strength results.
They are engineering-only inference; no local gradients or extra HF jobs.

### Frozen source, plan and sole active coordinator

- Source descriptor: `strong/population-hybrid-development-source-v1.json`.
- Dataset revision `cdec1d3079eb9a54b776f6237ec5f93cc1de84d8`.
- Archive `strong-source-population-hybrid-development-20261024-v1.tgz`, SHA256
  `ffcb3b0026555746f2fd4c17658be4d84a65463ee1accee796773efeafbe0d23`.
- Plan: `strong/population-hybrid-development-plan-v1.json`, SHA256
  `bd2d80bac1384f6d71a9cc4ee1f71db21ce6d9c8fd95e9a12543cdeceb83859f`.
- **135 shards, 8,400 games**: five arms ×27 cells ×four independent fresh deals,
  all seats and all four rules. Each arm has 1,680 games.
- Admission: cpu-upgrade, eight game processes, one simulation worker per game,
  eight worlds, four deals per shard, **9-hour timeout**, at most **32 live jobs**.
  Calculation: 120s setup +2×4×2,862.506s =23,020.051s projected, then 25%
  timeout headroom. Endpoint pilots are not a hard bound on every later game;
  preserve failures, never truncate/scored-cap or automatically retry.
- The **sole coordinator is PID1447977 / exec session53211**. It is confirmed
  alive through `/proc` with the expected command. State:
  `ai/runs/population-hybrid-development-coordinator-v1/state.json`; log:
  `ai/runs/population-hybrid-development-coordinator-v1.log`.
- Its launch used `--execute --interval-seconds 300 --max-hours 48`. The local
  lock and unique guards prevent duplicates. All 32 initial handles were checked
  through HF, all RUNNING; snapshot:
  `ai/runs/population-hybrid-development-launch-snapshot-v1.json`.

**Do not start a second coordinator or submit shards manually.** Inspect the
existing process/session and its exact HF handles. The coordinator fills freed
slots, collects immutable result archives, independently verifies every receipt
and compares only after all 135 planned shards verify. It stops new submissions
on failed/uncertain jobs without cancelling live jobs or creating replacements.
An observation timeout or quiet log is not a terminal job. A 48h coordinator
window ending also does not cancel remote jobs. Source/plan/dependency hashes
are frozen: do not edit their overlays while this screen runs.

After completion, read the full five-arm paired comparison, retaining all adverse
counts, rules and opponents. Four independent deals is a coarse first screen;
require separately frozen fresh confirmation before final model selection.
There is no automatic promotion or extra training from partial results.

### Persistent evidence

Descriptor `strong/population-hybrid-development-launch-evidence-v1.json` points
to model-repo revision `bd602457ca45e684980842fc25a8dbec7c42852c`, archive
`archives/population-hybrid-development-launch-evidence-v1.tgz`, SHA256
`ba93bf4bd6defcfdc4b94d2095906bb9dc9235d5dbe0d6b709ab32490f620893`.
All **185 files** are remotely verified: both runtime pilots and receipts,
execution/source pins, admission, initial 32 guards/HF status snapshot,
compatibility check and supporting code. The complete source archive is also
pinned in the dataset above. This is an initial-launch snapshot, not evidence
that all 135 jobs have already been submitted or completed.

## Previous checkpoint: current population hybrid verified on the actual 8840U

Previous goal turn: progress (independent runtime verification and prepared grid).
This turn: progress. The exact current frozen-1 population policy now passes
the actual AMD8840U benchmark. No gradients or new HF jobs were started. The
six-player HF runtime pilot `6adcad7b046eb82b1ecdc9cd` remains RUNNING at the
13:48 UTC snapshot; its last inspected progress log has 22/24 complete games,
zero reported caps. Continue that same handle; do not restart it. The fixed
8,400-game hybrid strength screen still awaits its complete verified result.

### New actual-target evidence

`strong/benchmark-population-policy-8840u.py` provides explicit prepare, local,
launch, inspect, collect and archive stages. It copies the exact frozen runtime
into an isolated package, with **1,234 unchanged runtime files**, the actual
frozen-1 ONNX and existing fixtures. Local and target runs execute from `/tmp`,
without checkout dependencies. The target runner imports no HF training client
and performs inference only.

The local reference completed in 81.46s, the target in 89.10s. On the actual
8840U, all 2,553 model and 2,553 filter decisions match the local reference;
all eight search results match in actions, sampled worlds, terminal-credit
outcomes, search statistics and certificates. Both one-thread/one-worker and
four-thread/four-worker settings are semantically identical. All 384 normal
rollouts complete, with no caps. This does not prove replay identity of every
internal simulated move, nor any playing-strength gain.

| Existing Recharged/sealed fixture | 1 thread /1 worker | 4 threads /4 workers |
| --- | ---: | ---: |
| 2p building | 8.883s | 4.873s |
| 2p bid | 4.850s | 2.922s |
| 6p bid | 11.503s | 6.168s |
| 6p building | 12.261s | 6.206s |

Those are four fixed endpoint positions, not a representative gameplay latency
distribution or all-count search benchmark. Across the full 2,553 existing
fixtures, model median/p95 is 5.36/7.82ms and filter median/p95 is 5.74/8.23ms;
these are warm decision timings and exclude initial model loading. The actual
target environment is Python3.12.3, NumPy2.5.3, ORT1.30.0, Node24.19.0.

The first local harness failed after all 5,106 model/filter checks: it passed an
in-memory search object to a verifier for JSON receipts, where integer world
keys become strings. V2 serializes the receipt before independent verification.
The failed package, runner, raw local results and diagnosis are preserved;
no policy/engine/model change or target run occurred in V1. The frozen source
for the live HF pilot and prepared development screen remains unchanged.

Target PID **2927472** completed successfully in
`/home/coyotte508/powergrid-ai-population-policy-8840u-v2`. Do not relaunch it.
Its guard is `strong/population-policy-8840u-launch-v2.json`; collection and
independent parity are complete under `ai/runs/population-policy-8840u-collected-v2/`.
Local V2 reference and prepared package are in the corresponding `ai/runs/`
directories. The private evidence archive has **24 files**, including both
package versions, failures and raw local/target results:

- Descriptor `strong/population-policy-8840u-evidence-v2.json`.
- Model-repo revision `d703d37d3668600353b927d46d37d8f253be9b66`.
- Archive `archives/population-policy-8840u-evidence-v2.tgz`.
- SHA256 `5f01eda4a4f65c0a3ed4ade1f92db1b888788644e2864fd0c3350bbbc467db55`.

Next action is unchanged: independently collect the existing six-player HF
pilot, then freeze the prepared development source/plan, inspect measured
timeout admission and launch the single guarded 8,400-game coordinator. Keep
all phases/counts/rules and adverse outcomes. This target benchmark does not
admit a strength claim, final selection or production routing; final seeds
remain unused. The immediately following checkpoint retains exact commands.

## Previous checkpoint: independent runtime verification and hybrid grid prepared

Previous goal turn: progress (complete model comparison and two runtime pilots).
This turn: progress. The two-player pilot completed and independently verifies;
the same six-player handle remains RUNNING at 13:34:43 UTC on 24 October.
No new HF jobs or gradients were started this turn. The fixed 8,400-game strength
screen has **not launched**; source preparation is complete, but final runtime
admission and source/plan publication wait for the six-player pilot. No candidate
is qualified, and final seeds remain unused.

### Completed two-player runtime pilot

- Job `6adcad711e112550ce7dfe8d`, COMPLETED, eight games / one runtime deal.
- 1,446 learner decisions, 530 searched decisions, 20,696 full rollouts, zero
  caps; 1,786,457 neural continuation decisions. Wall time 498.465 seconds.
- Independent verification: `ai/runs/population-hybrid-runtime-collected-v2/population-hybrid-runtime-v2-2p/verified.json`.
  Every saved decision, terminal credit, pairing and aggregate is checked.
  Search means and selected actions are recomputed from raw terminal credits.
  This is not independent replay of every simulated trajectory or strength evidence.
- Raw archive revision `065379fd84a562717e26864f7e0220f132187064`,
  `archives/population-hybrid-runtime-v2-2p.tgz`, SHA256
  `38224cf1cec76d6ff717c056c7825558deaf3be0dd549f8783f61da322a6d2f3`.
- The first collection is retained as `verified-initial.json`. The current
  receipt was independently repeated after closing test receipt streams and
  pinning collector/verifier hashes; the policy and running source never changed.

### Continue the existing six-player pilot

Job **`6adcad7b046eb82b1ecdc9cd`** is still the only active pilot. The latest log
snapshot has 13/24 games complete, no reported caps. Do not restart or duplicate
it. Collect with `ai/.venv/bin/python ai/strong/collect-population-hybrid-runtime.py 6`.
The collector is read-only and returns immediately for a running job. When it
completes, it downloads the immutable archive, verifies all file hashes and
independently verifies every game/decision before writing `verified.json`.

The retained short live metrics sample is
`ai/runs/population-hybrid-runtime-metrics-v1.json`: cpu-upgrade has 8 vCPU /32 GB,
initial CPU 0 followed by 99/100%, about 5.7 GB RAM, no GPU. This is not a time
average. It supports retaining eight game processes and scaling independent CPU
jobs; no evidence supports adding GPUs for this evaluator.

### Prepared next execution, not yet launched

`build-population-hybrid-development-source.py prepare` completed successfully.
All **1,453 base files are unchanged**; new files supply verification, the shard
wrapper, guarded manager/coordinator, comparison and tests. The exact source
archive is `ai/runs/strong-source-population-hybrid-development-20261024-v1.tgz`,
SHA256 `ffcb3b0026555746f2fd4c17658be4d84a65463ee1accee796773efeafbe0d23`.
Preparation manifest and logs are in
`ai/runs/population-hybrid-development-source-prepared-v1/`.

Six independent-verifier tests and eight execution/analysis tests pass. They
cover real controls/receipts, corruption rejection, balanced 8,400-game coverage,
nonzero deal offsets, retained adverse comparisons, duplicate/ambiguous submission
guards and the 32-job concurrency bound. A clean extracted-package check reaches
the real evaluation subprocess with the actual frozen-1 model, then deliberately
stops before playing; its expected failure receipt is retained. No extra games
or jobs are produced by these tests.

After the existing six-player pilot completes and verifies:

1. Run `ai/.venv/bin/python ai/strong/build-population-hybrid-development-source.py freeze`.
   It rechecks both runtime receipts, all prepared hashes and the unchanged final
   protocol. Timeout admission uses 120 seconds setup plus twice the slower
   endpoint's complete runtime times deals per shard, with 25% timeout headroom.
   It partitions into four, two or one whole deals to remain within 12 hours.
   It never shortens games or search. Inspect the resulting source/plan and
   measured timeout before launching; `freeze` itself submits no jobs.
2. Review the dry run of `coordinate-population-hybrid-development.py`. Only one
   coordinator may run: it holds a filesystem lock, retains unique launch guards,
   checks all pinned dependencies and validates saved receipt identities on resume.
   The fixed maximum is 32 live jobs; no automatic retries or cancellations.
3. Launch the fixed grid with `--execute` only after that concrete admission.
   The five arms, all 27 cells and all four fresh deals remain unchanged. The
   coordinator stops new submissions on failed/uncertain jobs, retaining every
   handle. All complete results are independently verified before a full paired
   comparison. Four deals is coarse development evidence, not final selection.

Evidence is remotely verified at private model-repo revision
`4f045dfaf5c03efe7a5d5058938e342af313bbe3`, archive
`archives/population-hybrid-development-preparation-evidence-v1.tgz`, SHA256
`f4e68ba9e00d0db29aa8da7766b8fdf926889f96e91e2e176bf9618f36e91568`.
All 54 files include the exact prepared source archive, verifier/tests, initial
and repeated two-player receipts/raw results, metrics and six-player progress.
Descriptor: `strong/population-hybrid-development-preparation-evidence-v1.json`.

The user's quoted 30.9% /15.6% rates refer to the old four-player baseline.
The completed new model-only comparison is 51.56% overall /39.06% Recharged
sealed for frozen-1 against search. Those are meaningful development gains,
not qualification and not new hybrid gains. The hybrid strength experiment
must establish whether selective search improves them across all counts/rules.

## Previous checkpoint: full comparison complete; hybrid runtime pilots running

Previous goal turn: progress (population worker integration and archived evidence).
This turn: progress. The sole recovery coordinator completed all remaining jobs,
verified every result, produced the complete comparison and archived it. PID
402796 / session 78444 is terminal and no longer exists; do not restart it.
All 550 effective development/smoke job handles are COMPLETED. No GPU training
is running. Two **new CPU-only hybrid runtime pilots** are the active jobs below.

### Complete model-only comparison

`strong/policy-iteration-development-comparison-v2.json` covers all five models,
27 opponent/count cells, all four rules and every seat: **33,600 games**, 6,720
per model, 16 independent deals per cell. Source/model/artifact pins and raw game
records are verified. The eight prespecified paired contrasts retain all adverse
cells. Intervals resample whole deals and are exploratory marginal intervals.

| Players | Parent vs search | frozen-0 | frozen-1 | public-0 | public-1 |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2 | 48.83% | 53.52% | 52.73% | 45.31% | 51.95% |
| 3 | 20.31% | 40.10% | 44.79% | 39.58% | 29.69% |
| 4 | 30.86% | 48.24% | 51.56% | 38.28% | 39.84% |
| 5 | 34.38% | 47.19% | 45.31% | 41.56% | 36.72% |
| 6 | 37.63% | 47.79% | 45.31% | 38.67% | 44.01% |

Frozen-1's paired search gains over parent are +24.48 / +20.70 / +10.94 / +7.68
percentage points at 3/4/5/6 players; their exploratory intervals exclude zero.
Two-player overall change is inconclusive (+3.91 pp, interval −0.78 to +8.59).
The gains do not establish universal strength or qualification:

- 2p Recharged/open search is only 34.38% (parent 40.62%).
- 4p legacy/default is 86.72%, below the unchanged 90% point floor.
- 5p legacy is 90.62% but drops 3.44 pp from parent; interval −5.31 to −1.56.
- 6p Recharged/sealed search is 23.96%, with lower interval 14.58%, below 1/6.

`strong/policy-iteration-development-decision-v2.json` retains every negative
paired frozen-1 view and chooses **frozen-1 only as the next development base**:
large 3p/4p gains and smaller legacy regressions than frozen-0. No per-rule model
routing, final candidate selection or promotion. Whole-game gains contradict a
blanket plateau claim; additional epochs are not automatically justified.

Complete evidence: HF revision `23cf5dfe1d7adc0d6ec62fe56a99f252634708a3`,
`archives/policy-iteration-development-complete-evidence-v2.tgz`,
SHA256 `e59b6c786504335f9d3ba7e9af38b9ab847f903eb694f1b30a4695b76568343d`
(5520 files, remotely verified). Comparison SHA256
`b85e900c30b70d523d8e2beb4e8ecf9f3bdb1a03c14924b0041ec45b3c422cb2`.

### New isolated policy and admission checks

`population_hybrid_policy.py` plus `population-hybrid-policy.cjs` implement five
arms: model only, strict-loss filter, filter+auction search, filter+building
search, and filter+combined search. The filter also applies to future focal
neural decisions during rollouts. Neural opponents retain their own unfiltered
policy. Certified losing root Builds are excluded; equal simulated scores keep
the filtered model proposal. Any incomplete rollout falls back safely and still
invalidates a strength cell. No existing serving/evaluation code was modified.

`public-arena-bridge.cjs` is the frozen arena with one observation-only addition:
public sanitized game requests for the external policy. The original bridge is
preserved. `evaluate-population-policy.py` checks every root model proposal
against the original arena's encoded observation and stores per-decision receipts.

Four worker tests pass: all **2,553 fixtures**, 24 certified legal Build choices,
future filter behavior, all 80 count/rule/phase cells with exact filter-off
compatibility, cap retention, and root rejection. Whole-game adapter controls
replay the first existing legacy development deal for every count/rule/seat:
**80 games / 10,207 learner decisions**, identical terminal states, move counts
and opponent statistics. These are reused controls, not fresh strength results.

The actual frozen-1 selector probe checks all 2,553 model/filter positions (two
proposals changed), eight normal-budget searches / 384 complete rollouts with
zero caps, phase routing, shared public-world prefixes, worker partition equality,
and a deliberate one-step cap fallback. All checks pass. These are engineering
checks on the local HX370, not representative latency or target8840U evidence.

Preflight: `ai/runs/population-policy-preflight-v1/` (session 42038 complete).
Controls: `ai/runs/population-policy-arena-controls-v1/` plus `.log`
(session 43997 complete). Selector probe: `ai/runs/population-policy-trained-probe-v1/`
plus `.log` (session 15858 complete). Do not rerun those processes.

### Fresh experiment and active runtime jobs

`strong/population-hybrid-development-protocol-v1.json` fixes five arms and all
27 count/opponent cells on four fresh paired deals: **8,400 planned games**.
It is an initial screen with coarse uncertainty, not final selection. A larger
separately frozen fresh confirmation is required before final qualification.
The 8-world population spans neural/economic/default/rush twice per opponent,
with policy-consistent prior sealed bids. Equal population weights remain
uncalibrated. Keep all adverse cells; do not pick from partial screens.

**The strength grid is NOT launched.** First measure the most expensive combined
arm against the unchanged search_geo reference on one distinct runtime deal per
endpoint, all seats/rules. Both guards were created once and both handles were
confirmed RUNNING at 2026-10-24T13:07:33 UTC (replacement handles):

- 2p: `6adcad711e112550ce7dfe8d` (8 games).
- 6p: `6adcad7b046eb82b1ecdc9cd` (24 games).

Both use `cpu-upgrade`, eight game processes, one simulation worker per game,
eight worlds, full 2400-step continuation horizon, 1600-step outer game cap and
6-hour job timeout. Jobs terminate automatically. No gradients/GPU jobs were
started. Runtime outcomes must be excluded from strength comparisons.

Launcher: `strong/launch-population-hybrid-runtime.py`; worker:
`strong/population-hybrid-runtime-job.py`. Guards/logs:
`ai/runs/population-hybrid-runtime-launches-v2/`; last status:
`ai/runs/population-hybrid-runtime-status-v2.json`. Source:
`strong/population-hybrid-source-v2.json` pins dataset revision
`9a49df8a3baa5e5b6b62cae8208ef301b8540ba7`, archive
`strong-source-population-hybrid-20261024-v2.tgz`, SHA256
`cd5c08165dfecce5753bcab1c9c0bf10ef45797bf3e5e082914fd6634f91a778`.
All 1,439 base source files remain byte-identical; only new research overlays
were added. Do not edit the pinned overlays while jobs are running.

On completion the worker prints an immutable evidence receipt and uploads one
archive to private model repo `coyotte508/powergrid-ai-germany-v1` at
`archives/population-hybrid-runtime-v2-2p.tgz` or `...-6p.tgz`, including failures.
Read the same authoritative HF handles; do not relaunch for quiet logs/timeouts.
`HfApi.fetch_job_logs(..., tail=...)` returns strings in this environment.
A collector/runtime-admission driver has **not yet been written**. Next: verify
complete archives and every game/decision receipt, measure throughput, then set
strength-job batching/concurrency/timeouts without shortening games/search.
Do not launch the full grid before both runtime pilots pass and resource use is
reviewed. No final seeds or candidate.json exist; the full goal stays active.

The original v1 pilots `6adcab91046eb82b1ecdc943` and
`6adcab9b1e112550ce7dfd96` are **ERROR**, not live. Both failed before game
evaluation because the extracted package had no `ai/runs` directory. Their
complete logs and guards are preserved in `ai/runs/population-hybrid-runtime-failures-v1/`
and the v1 launch evidence. The v2 repair creates parent directories and versions
the output receipt path; model, engine, samples, horizons and deals are unchanged.
A clean-package admission now reaches the evaluation subprocess using the actual
trained model and writes a failure receipt on an intentional preflight stop.
The first layout-test harness accidentally intercepted `platform.processor()`;
its failed tree/log are preserved, and the corrected harness intercepts only the
evaluation command. These tests launched no games or remote jobs.

Repaired source staging: `ai/runs/population-hybrid-source-v2-layoutfix/`;
failed layout staging: `...source-v2/`. Build logs use the same suffixes.
Sessions 57092 (failed local layout harness), 33372 (successful source v2) and
68902 (repair evidence) are terminal. There were four new remote submissions
this turn: two startup failures, then exactly two guarded replacements.
No automatic retry or strength-grid launch is scheduled.

Repair/launch evidence: `strong/population-hybrid-runtime-launch-evidence-v2.json`,
HF revision `466e862d976299ebfc04bae0ef60a68de6aa0edf`, archive `archives/population-hybrid-runtime-launch-evidence-v2.tgz`,
SHA256 `77efdfd619a2d254791fc4cbcf3010940c11bb6a2e477c010577fe8391a4bfac` (34 files,
remotely verified). This references the full v1 preflight/control evidence below.

All new source, raw controls/probes, admissions, full comparison reference and
launch guards/status are archived in
`strong/population-hybrid-runtime-launch-evidence-v1.json`: HF revision
`76d09db43973089c4904685bee44af76061f19af`, `archives/population-hybrid-runtime-launch-evidence-v1.tgz`,
SHA256 `52db6807e0c6f7ee4f205b0620f75511e10d3214626b0d9206be48a5392d82d7` (209 files,
remotely verified). Source-building session 74192 and evidence session 24181 are
complete. This checkpoint belongs to `ai/germany-baseline`; production remains unchanged.

## Previous checkpoint: trained population continuations verified

Previous goal turn: progress (endgame counterfactuals and isolated loss filter).
This turn: progress through a broader experimental continuation worker. No new
HF jobs, gradients, fresh strength games, candidate selection or final-test games.
Production and historical evaluation/serving behavior remain unchanged.

`strong/population-hybrid-continuations.cjs` adds three isolated modes:
`neural_legacy`, `neural_rush`, and `neural_population`. The focal player uses the
actual trained model. Population mode assigns each opponent neural, economic,
legacy/default and rush policies once per four sampled worlds, with per-seat
seeded offsets. Assignments, future-world seeds and inferred prior sealed bids
are shared across candidate actions and remain stable across worker partitions
and budget prefixes. This is an uncalibrated experimental mixture, not a chosen
optimal weighting or a calibrated sealed-bid distribution. Legacy continuations
use the actual default bot; its legal bids are validated against the complete
legal menu rather than the pruned neural menu.

Five meaningful tests pass in the pinned frozen evaluation runtime: exact
historical-mode compatibility for both feature revisions, 40 positions spanning
2–6 players/all rules/auction/building, input immutability and private-future
invariance, role routing, action-order/worker-partition invariance, and 96 complete
heuristic-driven endpoint continuations. The first test run failed because the
test changed public open-auction bids while demanding invariant observations.
Only that test was corrected to perturb sealed bids; both versions and logs are
retained. The worker implementation did not change between those runs.

`strong/probe-trained-population-continuations.py` then exercised the parent and
all four actual trained ensembles on the four existing endpoint Recharged/sealed
bid/building fixtures: **60 cases / 480 terminal rollouts, zero caps**. All neural
actors use actual batched model inference. It checks exact model/source hashes,
serial/batch root decisions, legal menus, public seeds, role assignments, shared
worlds/beliefs and decision accounting. Results are plumbing evidence on reused
fixtures, not a fresh win-rate study or representative latency distribution.
The host is the local HX370, not the target AMD8840U.

Outputs: `ai/runs/population-hybrid-preflight-v1/` (preserved failed test),
`population-hybrid-preflight-v2/` (five passing tests), and
`trained-population-continuations-probe-v1/` plus its `.log` (completed).
No probe is still running. No filter or new mode has been wired into the Python
hybrid selector, serving or the existing development evaluation.

All new source, both test versions/logs, admissions, raw results and fixture/model
references are archived in `strong/population-hybrid-continuations-evidence-v1.json`.
HF revision `cdd474cc52caab02bceb9a955351bf967dcddee8`, archive
`archives/population-hybrid-continuations-evidence-v1.tgz`,
SHA256 `5daf12ad4017df29a0d5c1e1ec317b8568a8fcdd7cdd7957280be6e4b170d92d`
(25 files; remote content hash verified).

### Comparison and next decision

At 2026-10-24T12:39:55.583176+00:00, recovery PID 402796 / session 78444 remains live.
Frozen-0 and frozen-1 are complete (108/108 shards, 6,720 games each);
public-0 has 106/108 and public-1 107/108. All 41 pinned dependencies still match.
Only three six-player search shards remain; keep the same coordinator as sole
collector/comparator. Do not choose an arm from this partial grid. Its next
artifact is `strong/policy-iteration-development-comparison-v2.json`.

The recommendation remains a bounded hybrid experiment after that comparison:
compare model-only, a cheap strict-loss filter, auction search, building search,
and combined search on fresh development deals. Include 2–6 players and all four
rules, retain default/rush/economic/search opposition and adverse cells, and
measure the actual target CPU for the exact policy. Opponent-mixture and sealed-
bid calibration matter more than merely increasing rollout counts. The earlier
hybrid helped 3p/4p but harmed 6p, so broader modes are an experiment, not evidence
of improvement. The current model-only 4p search gains are already substantial
(30.86→51.56% overall, 15.63→39.06% Recharged/sealed for frozen-1); two-player
weaknesses and legacy regressions still need attention. Do not automatically add
training epochs. No candidate is qualified; reserved final seeds remain unused.

## Previous checkpoint: endgame counterfactuals and a strict loss filter

Previous goal turn: progress (four-player gains plus complete fuel-market replays).
This turn: progress through single-decision counterfactuals and an isolated
experimental endgame filter. No new HF jobs, gradient updates, candidate selection,
serving changes or final-test games. The fixed development coordinator stays live.

### Counterfactual diagnosis

From the existing 49 outcome-selected five-player legacy trajectories, take
**every** game where the learner first crosses the endgame city threshold,
without further filtering by winner or current lead: 28 cases across the parent
and all four trained ensembles. For each, replay the original action and replace
only that threshold-crossing Build with a legal Pass. Later decisions still use
the same original policy. All 28 original controls reproduce **byte-identical
full traces** and exact terminal outputs. All 28 changed branches match every
preceding move and the intervention state; every subsequent public-state
transition is continuous. All 56 branches finish with zero caps.

The universal delay changes six selected losses into wins, but also changes five
wins into losses; 17 are unchanged. This rejects "always delay the ending" as a
general fix. These are conditional counterfactuals on reused, outcome-selected
deals with the actual future deck/RNG, not a fresh strength sample, training
labels, a deployment expectation or a representative frequency estimate.

| Model | Delay gains | Delay losses | Unchanged |
| --- | ---: | ---: | ---: |
| Parent | 2 | 3 | 5 |
| frozen-0 | 2 | 0 | 4 |
| frozen-1 | 1 | 1 | 2 |
| public-0 | 0 | 0 | 5 |
| public-1 | 1 | 1 | 1 |

Source: `strong/policy-iteration-endgame-counterfactual-protocol-v1.json`,
`strong/intervene-endgame-build.cjs`, `strong/replay-policy-iteration-endgame-branches.py`.
Output/log: `ai/runs/policy-iteration-endgame-branches-v1/` and `.log`.
Session 51335 completed. The arena's `policyMoves` counts proposals before the
intervention; use the full trace for executed-action counts in changed branches.

### Experimental certificate: strict fuel-supported output loss only

`strong/endgame-loss-filter.cjs` is **not wired into serving, training, existing
evaluation or hybrid search**. It proposes Pass only for a legal first
threshold-crossing Build when the player's maximum output with all current fuel
and plants (even with enough cities) is strictly lower than an opponent's already
fuel-supported current cities. It reads no deck, hidden bid or future action.

The reasoning is specific to standard Germany: reaching the city threshold ends
the game after Building, before fuel is consumed. During the remaining Building
phase the player's fuel-supported ceiling cannot rise, while the opponent's
already fueled cities cannot fall. Thus the strict output gap cannot be fixed
by buying more cities that turn. Equal outputs are deliberately **not** certified
because money and later construction can affect ties. Already-triggered endings,
unsupported maps/options, dropped players, illegal actions and unavailable Pass
are rejected. Do not broaden these conditions without new reasoning and tests.

The 49 original game ledgers were independently replayed as recorded moves through
the frozen engine: **26,772 root moves have matching before/after states**. All certificate
calls leave full states unchanged; perturbing private deck/RNG fields does not
change them. Eight of the 28 threshold cases meet the strict certificate; every
original is a loss. Their already-computed Pass branches recover four wins and
leave four losses unchanged. This is diagnostic consistency, not a new win rate.
No model or production behavior has changed.

Three meaningful unit tests pass, covering all 2–6 player counts/seats, strict
versus tied output, later possible powering, already-ended scope, legality,
read-only behavior and private-future invariance. The actual frozen serving
fixture probe covers **2,553 positions / 22,597 supplied legal choices** across
2–6 players. It finds 24 certified Build choices in 3p/5p fixtures; all replacement
Pass moves are legal and inputs remain unchanged. Positive real-game causal
examples are five-player only; fresh all-count strength evaluation is still needed.

Scripts: `strong/test-endgame-loss-filter.cjs`, `strong/audit-endgame-loss-filter.cjs`,
`strong/probe-endgame-filter-serving.cjs`. Results: `ai/runs/endgame-loss-filter-audit-v1.json`,
`endgame-loss-filter-serving-v1.json`, corresponding logs and
`endgame-loss-filter-tests-v1.log`. Sessions 6300 and 59475 completed.

All raw counterfactual traces, controls, intervention receipts, protocol, source,
checks and linked prior replay evidence are archived in
`strong/policy-iteration-endgame-diagnosis-evidence-v1.json`:
HF revision `7517a821fbb292d89315da3e243d1eccdaeb5698`, archive `archives/policy-iteration-endgame-diagnosis-evidence-v1.tgz`,
SHA256 `59395b348c215f1109c814f08c4a6da72473dbe2f3c9a7b8b4e6fc4b44f4a3ff` (132 files, remotely verified).

### Remaining comparison and next action

At 2026-10-24T12:27:37.801047+00:00, recovery PID 402796 / session 78444 is live,
stage `waiting_for_development_jobs`; all 41 dependency hashes match. Each candidate has 104/108
shards and 6,336/6,720 games verified (416 shards / 25,344 candidate games total).
The only remaining jobs are the 16 six-player search shards. A direct HF check
this turn confirmed handles `6adc8f091e112550ce7def98` and
`6adc90cf046eb82b1ecdc0a9` RUNNING; do not restart them because observation is slow.
All five-player cells are now collected, but no extra partial ranking or selection
was performed. Let the same coordinator finish the complete 33,600-game comparison.

After that, determine the bounded hybrid experiment from all model/count/rule
results. The experimental certificate can be tested as a separate cheap arm;
fuel-consuming opponent mixtures and earlier provisioning still matter, since
avoiding a certain terminal loss does not fix an already bad position. Final
qualification still requires the unchanged full gate and exact serving/8840U
receipts for any modified policy. The original goal remains incomplete and active.

## Previous checkpoint: four-player gains verified; fuel-market failures reproduced

Previous goal turn: verified wait on the live recovery coordinator. This turn:
progress through additional complete-cell verification and exact diagnostic replays.
No new HF jobs, training updates, model selection or final-test games were started.

Six previously missing cells are now complete in all five arms. The new fixed
cutoff is 2026-10-24T12:10:34.702104+00:00: **25/27 cells, 30,080 games, 6,016 per arm**.
This includes all four-player search games (16 independent deals, all seats,
all four rules). Five- and six-player search are still incomplete in this snapshot.
All previous cells, all four candidates, adverse results and eight paired
contrasts remain in the full report. No incomplete-grid ranking or aggregate
win rate is used. This is a new completed group, not a rerun of the same sample.

| Model | 4p search overall | Original open | Original sealed | Recharged open | Recharged sealed | 4p legacy/default |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Parent | 30.86% | 45.31% | 25.00% | 37.50% | 15.63% | 88.28% |
| frozen-0 | 48.24% | 57.81% | 29.69% | 67.19% | 38.28% | 89.06% |
| frozen-1 | 51.56% | 67.19% | 34.38% | 65.63% | 39.06% | 86.72% |
| public-0 | 38.28% | 56.25% | 25.00% | 45.31% | 26.56% | 82.03% |
| public-1 | 39.84% | 51.56% | 34.38% | 54.69% | 18.75% | 89.06% |

Frozen-1's paired four-player search gain is +20.70 pp, exploratory 95% whole-deal
interval +14.06 to +26.96. Its Recharged/sealed gain is +23.44 pp, interval +14.06
to +32.81. These are **model-only** gains: candidate search remains off. Original
sealed improvements are less certain (paired interval includes zero), and none
of these models reaches the fixed 90% legacy point floor in this four-player
sample. Two-player Recharged/open and five-player legacy problems remain.
Do not select a model or claim qualification from the stronger search result.

Evidence: `strong/policy-iteration-interim-complete-cells-evidence-v2.json`.
Report/log: `ai/runs/policy-iteration-interim-complete-cells-v2.json` / `.log`;
independent verification session 34994 completed. All 500 included raw batches,
verification records, effective guards, plans and comparison source are archived:
HF revision `25143658a84e2ff15027f7d014fde385f96118ef`, archive `archives/policy-iteration-interim-complete-cells-evidence-v2.tgz`,
SHA256 `ca8fdcc0128ee18b1631389a06b1e0825ccc8a4622965313c59ba7c1b72678fc` (1515 files, remotely verified).
Archive preparation initially missed the plans directory and stopped before any
upload; the empty staging directory was repaired and the single upload verified.

### Concrete regression diagnosis: fuel competition and endgame timing

The prior fixed 19-cell snapshot was analyzed without adding or reselecting
win-rate observations. All models, cells and rule views are retained. Terminal
metrics show frozen-1 gaining 0.83 powered cities / 1.22 nominal capacity against
three-player search while ending with 51.82 less cash. Capacity-below-winner
losses fall from 116 to 44. Against five-player legacy, frozen-0 instead ends
with 0.96 fewer powered cities, 0.66 less nominal capacity and 20.93 less cash;
it loses 39 parent wins and gains six. Frozen-1 loses 15 and gains four.
The two-player Recharged/open fuel-supported shortfall also grows. Terminal
metrics alone do not locate a causal decision.

We hash-selected at most one lost and one gained outcome per model/rule from
five-player legacy: **27 diagnostic pairs, 49 unique games**. Every terminal
field exactly reproduces the original evaluation. The first observer records
learner moves only and its old `p.resources` field is absent in this engine;
no fuel claim relies on that field. A new read-only observer records actual
coal/oil/garbage/uranium holdings, market availability, public spending totals,
and the frozen engine's fuel-supported capacity, including legacy root moves.
All 49 games were repeated: every terminal output matches again, every root move
is present, and every consecutive public-state transition is continuous.

Concrete example: frozen-1 episode 128 (5p original/sealed) ends with 19 cities,
plant capacity 16, but only 10 powered. At its last resource pass it has 159 cash,
one uranium, zero coal, and **zero coal remaining in the market**. Plant 31 needs
three coal and therefore cannot be fueled that turn even ignoring price. The bot
then buys five more cities. Other selected losses similarly lack enough coal
in the entire remaining market. This is not evidence for a blanket "buy more
resources now" rule: some fuel is already unobtainable. Earlier plant choice,
resource reserves, purchase order and endgame-triggering expansion need to be
modeled together. Other examples have different causes; the selected-case counts
are diagnostic, not representative failure frequencies or causal interventions.

Implication for the bounded hybrid study: test realistic fuel-consuming opponent
continuations, including stockpiling/rushing behavior, before increasing sample
counts. Neural/economic-only continuations can miss this pressure. Check the
resource-buying policy and endgame timing as well as auction/building search;
there is no justification yet for a universal spend-more or spend-less rule.
Finish the fixed full comparison first; do not blindly add training epochs.

Scripts: `analyze-policy-iteration-terminal-outcomes.py`,
`replay-policy-iteration-legacy-diagnosis.py`,
`analyze-policy-iteration-legacy-replays.py`, `trace-public-economy.cjs`,
`replay-policy-iteration-economy.py`, `analyze-policy-iteration-economy.py`
(all under `ai/strong`). Results: `ai/runs/policy-iteration-terminal-diagnosis-v1.json`,
`policy-iteration-legacy-replays-v1/`, `policy-iteration-legacy-replay-analysis-v1.json`,
`policy-iteration-economy-replays-v1/`, `policy-iteration-economy-analysis-v1.json`.
Sessions 84471, 58947, 50688 and 9768 completed; do not restart into these paths.
Evidence: `strong/policy-iteration-terminal-economy-evidence-v1.json`, HF revision
`d7fbe5fda02f46104a99fd320b6a4908eae2c8b9`, archive `archives/policy-iteration-terminal-economy-evidence-v1.tgz`,
SHA256 `745bc719322a18fc121547cf9f98553c23d24f32697786e9493fbd176ca2255f` (120 files, verified remotely).
Raw traces from both observers, all analyses and source are preserved.

### Active work

At 2026-10-24T12:10:33.444273+00:00, the sole recovery coordinator PID 402796
(session 78444) is live, stage `waiting_for_development_jobs`. All 41 dependency hashes match.
Verified collection: `{"frozen-0": {"verified_games": 6256, "verified_shards": 103}, "frozen-1": {"verified_games": 6336, "verified_shards": 104}, "public-0": {"verified_games": 6256, "verified_shards": 103}, "public-1": {"verified_games": 6096, "verified_shards": 101}}`.
All ten reviewed replacements were submitted; the original failed handles remain
preserved. The coordinator owns all remaining collection and the required
33,600-game full comparison. Do not duplicate it. No candidate, final-test run,
production change or publication has been made. Full objective remains active.

## Previous checkpoint: substantial complete-cell strength gains, with regressions retained

The small simulation-validation gains did **not** imply uniformly small whole-game
improvement. A read-only interim diagnostic now includes every opponent/count
cell whose four shards were already verified in **all five arms** at a fixed
cutoff (2026-10-24T11:38:32.300371+00:00). It includes 19 of 27 cells, 21,120 games in total,
4,224 per arm. Each included cell has all 16 independent deals, every seat and
all four rule combinations. No incomplete cell contributes a result. Missing
cells are listed explicitly. Nothing was selected using their outcomes.

| Model | 2p vs search | 3p vs search | 3p vs older neural a260 | 5p vs legacy/default |
| --- | ---: | ---: | ---: | ---: |
| Parent | 48.83% | 20.31% | 34.38% | 94.06% |
| frozen-0 | 53.52% | 40.10% | 48.44% | 83.75% |
| frozen-1 | 52.73% | 44.79% | 46.35% | 90.62% |
| public-0 | 45.31% | 39.58% | 38.54% | 85.94% |
| public-1 | 51.95% | 29.69% | 35.42% | 93.12% |

These are development win shares, not qualification results. All arms, all 19
ready cells and all adverse rule views are retained in the report and archive.
Against three-player search, paired gains over the parent are +19.79 pp for
frozen-0 (exploratory 95% deal interval +8.85 to +31.25) and +24.48 pp for frozen-1
(+15.63 to +33.85). Against a260 they gain +14.06 and +11.98 pp respectively.
Two-player search improvements are not established: all paired intervals include
zero. Recharged/open remains particularly weak there: parent 40.63%, frozen-0
37.50%, frozen-1 34.38%. Keep this rule/count failure visible in the later hybrid
study; an overall two-player gain does not fix it. The larger public-state model
is also not uniformly stronger.

The five-player default-bot regression is material: frozen-0 changes -10.31 pp
(interval -14.69 to -6.25), frozen-1 -3.44 pp (-5.31 to -1.56), and public-0
-8.13 pp (-13.44 to -3.13). Public-1 changes -0.94 pp, with an interval including
zero. Do not suppress these losses or equate an improved search-opponent result
with broad qualification. The confidence intervals are exploratory, marginal
and based on 16 deals; repeated interim views are not independent confirmatory
tests. Four-, five- and six-player search cells remain unavailable in this snapshot.

This evidence changes the progress assessment: there is meaningful real-game
improvement to pursue, rather than evidence of a blanket training plateau.
It does not justify simply adding epochs; validation still peaked early, and
larger-player robustness and the untouched final gate remain unresolved.
Finish the prescribed full comparison before model selection, another gradient
round or the bounded hybrid strength study. No candidate has been selected.

- Script: `strong/inspect-policy-iteration-complete-cells.py --output NEW_PATH`.
- Report/log: `ai/runs/policy-iteration-interim-complete-cells-v1.json` and `.log`.
  Session 3317 completed. The initial console formatter used a wrong display key;
  the report itself completed successfully and was not changed or rerun.
- Evidence: `strong/policy-iteration-interim-complete-cells-evidence-v1.json`.
- HF revision `4433355d1c38ae63bbc6592afdcd4c743bf87000`, archive
  `archives/policy-iteration-interim-complete-cells-evidence-v1.tgz`, SHA256
  `61b8618dd1cd9b661dddae701cfdab3907bc232e81b823ab38b5db1a43a9b01e`. All 1155 files verified remotely,
  including all 380 included batches' raw evaluation rows, verification records,
  effective launch guards, plans, analysis source and complete diagnostic.

### Bounded batch-packing experiment: correct, only modest local gains

New experimental batch packing sorts observations by legal-menu length, evaluates
small groups, then restores their original order. Serial, ordinary batched,
packed and reversed-input choices agree on all 2,553 serving roots plus 240
prior-bid observations for public-0, and on all 80 count/rule/phase cells for each
of the other four models. All five models and both feature formats are covered.
Six full-search repetitions in order plain64, packed16, packed8, packed8,
packed16, plain64 preserve every internal decision and terminal outcome; 576
complete simulations and zero caps. No engine, model, protocol or default changed.

On the local HX370 at four ORT threads, mean request times are 21.704s ordinary,
20.197s packed16 and 21.254s packed8. That is 6.94% and 2.07% less elapsed time,
with overlapping timing ranges. Legal action-slot utilization rises from 24.3%
to 54.4% / 73.6%, but ONNX calls rise from 702 to 1,881 / 3,622. These are
one-fixture engineering observations, not representative speedup estimates.
Packing remains experimental and was not measured on the 8840U. There is no
reason to prioritize another optimization round over the strength comparison.

- Source: `strong/hybrid_packed_inference.py`, `strong/probe-hybrid-batch-packing.py`.
- Completed session 10364; results `ai/runs/hybrid-batch-packing-v1`.
- Evidence: `strong/hybrid-batch-packing-evidence-v1.json`.
- HF revision `aa1d62fcdeaa99b67bc22894b84a556be738d21e`, archive
  `archives/hybrid-batch-packing-evidence-v1.tgz`, SHA256
  `c72c31d9b9ea1851e90a434d01e80c4075995f647eeb11a89a5777b5c1f35248`. Raw outcomes, traces, source and environment saved.

At 2026-10-24T11:47:09.829964+00:00, recovery PID 402796 / session 78444 remains live,
stage `waiting_for_development_jobs`, with 10/10 reviewed replacements submitted.
Its 41 dependency hashes match. Completed collection progress:
`{"frozen-0": {"verified_games": 5952, "verified_shards": 99}, "frozen-1": {"verified_games": 5760, "verified_shards": 97}, "public-0": {"verified_games": 6016, "verified_shards": 100}, "public-1": {"verified_games": 5824, "verified_shards": 97}}`. The coordinator alone owns the
remaining replacements, collection and full comparison. Do not start another.

## Previous checkpoint: actual 8840U hybrid speed and restored collection

The trained hybrid cost profile now passes on the actual **AMD Ryzen 7 8840U**.
It uses only public-0 and the same existing six-player Recharged/sealed building
fixture (2029), eight worlds per continuation mode and four engine workers.
Thread order is 1, 4, 4, 1; each request starts new search workers with a loaded
model. No default or search budget was changed.

| ORT threads | Two request times | Mean ONNX time | Mean engine / IPC / JSON time |
| --- | --- | ---: | ---: |
| 1 | 34.616s, 34.949s | 24.735s | 8.016s |
| 4 | 19.484s, 19.541s | 9.398s | 8.061s |

Mean whole-request speedup is **1.783x**. All four internal policy-choice
transcripts and all terminal outcomes match each other **and the local HX370
profile**; 28,074 policy rows per request, zero caps. This supports feasibility
for background bot jobs. It is one repeated fixture, not a representative latency
distribution, a fresh strength result or a justified default for every model/count.
Python 3.12.3, ORT 1.30.0, NumPy 2.5.3, Node v24.19.0 were recorded on target.

The first target attempt failed before simulations because the profiling script
imported an HF training client through generic file helpers. Its terminal PID,
logs, source and guard are retained. The repaired profiler uses standard-library
file helpers and an explicit CPU admission check. Model, frozen engine, search
and inference files are unchanged. No package was installed on the target.

- Completed target: PID 2925814, SSH session 73745; no process to restart.
- Remote: `/home/coyotte508/powergrid-ai-trained-hybrid-8840u-v2`.
- Guard: `strong/trained-hybrid-8840u-launch-v2.json` (`completed`).
- Prepared/results: `ai/runs/trained-hybrid-8840u-prepared-v2` and
  `ai/runs/trained-hybrid-8840u-results-v2`.
- Evidence: `strong/trained-hybrid-8840u-evidence-v2.json`.
- HF revision `2351a59ac0fb49d17686079559e10bf81ed54361`, archive
  `archives/trained-hybrid-8840u-evidence-v2.tgz`, SHA256
  `894fa571b9e861b9ca08629e601857d0244e45706d08fc5d8fdde1a900ff9a01`. All 19 files verified remotely,
  including the standalone package, raw results, source and first failure.

At 2026-10-24T11:23:17.373063+00:00, the development recovery is live as
**PID 402796 / session 78444**, stage `waiting_for_development_jobs`. The two first
replacement jobs are authoritatively COMPLETED. Eight reviewed replacements
remain to be submitted by this same coordinator, at most two at a time. Its
41 frozen dependency hashes match. There are **357 / 432 candidate shards and
21,600 / 26,880 candidate games independently verified**, plus all 6,720 parent
games. No partial win-rate ranking or model choice is made.

Recovery progress and actual first replacement handles are durably archived:
`strong/policy-iteration-development-recovery-active-evidence-v1.json`, HF revision
`14128918fbd0620d618f325462187d6f212645e2`, archive `archives/policy-iteration-development-recovery-active-evidence-v1.tgz`,
SHA256 `7ff1d37c4bdbf11a14c7d392110b294fae2f20fb8fd7e59fa435c6c7a168c746`. Original failed handles remain failures,
with the replacements linked explicitly. Do not rerun or duplicate its tasks.

Next: complete the unchanged whole-game comparison before selecting a candidate,
starting another gradient round or launching the bounded hybrid strength study.
The untouched final strength gate still has to pass; no candidate is qualified.
For future large grids, improve artifact-upload queuing/backoff before submitting
another synchronized burst; the observed upload failures are not evidence for a
model or simulator change. No active job's source was modified.

## Previous checkpoint: reviewed artifact-upload failures and bounded recovery

The original development coordinator (PID 71261 / session 77604) stopped at
11:05:39 UTC on ten ERROR jobs; the PID was absent and its 39 dependencies
were unchanged. Do not restart the original launcher. All 432 candidate shards
were submitted and their launch archives remain valid.

All ten errors are on frozen-1 jobs, with HF artifact commit HTTP 429:
`maximum queue size reached`. Their exact original handles, sanitized full logs,
guards, terminal statuses and the stopped coordinator are preserved. All ten
remote result prefixes were absent at the inspected repository revision. Because
upload runs in a finally block, upload errors alone do not prove that their games
completed correctly; no result or strength credit is assumed for these batches.

A separately admitted recovery replaces only these ten terminal jobs, once each,
with **at most two replacements in flight**. It uses the unchanged source,
bootstrap, models, hardware, seeds, rules, horizons and per-case timeout. Original
guards are preserved in the failure evidence; canonical guards now name each
replacement and reference its original job. Completed and running jobs are not
rerun. Five recovery-control tests and the real ten-case admission passed.

- Current coordinator: **PID 402796 / session 78444**.
- Script: `strong/recover-policy-iteration-development.py`.
- State: `ai/runs/policy-iteration-development-recovered-v1/state.json`.
- Log: `ai/runs/policy-iteration-development-recovered-v1.log`.
- Admission: `strong/policy-iteration-development-recovery-admission-v1.json`.
- Evidence: `strong/policy-iteration-development-recovery-evidence-v1.json`.
- HF revision `7c5b6d96037bf3cc31b543f80d8015e7e49588d3`, archive
  `archives/policy-iteration-development-recovery-evidence-v1.tgz`, SHA256
  `97f75f02a1a3c6fe9f03effd101283787eb3cb93bb34e775cdb63e5f04791a07`. All 30 files verified remotely.

At 2026-10-24T11:16:30.126359+00:00, the stage is `collect-001-public-0` and
2/10 replacements are submitted. The first two are
`6adc92d91e112550ce7df2e6` (2p economic-capacity deals 12–16) and
`6adc92db046eb82b1ecdc147` (3p a260 deals 8–12). Current completed
collection progress by model: `{"frozen-0": {"verified_games": 5616, "verified_shards": 93}, "frozen-1": {"verified_games": 4912, "verified_shards": 82}}`.
The independent initial frozen-0 collection completed 90 shards / 5,504 games;
the recovery collector has since advanced it. Do not start a second collector
or submit any of the remaining eight replacements manually.

The recovery owns collection of all four grids and the same complete 33,600-game
comparison. Its fixed list cannot silently grow; any new failure stops for review.
It cannot cancel jobs, retry replacements, alter the final gate, select a model,
or publish. It has a 12-hour observation window. Final seeds remain unused.

The first target timing attempt described at this checkpoint subsequently failed
before simulations on the missing HF training-client dependency. Its PID 2925654
and SSH session 13220 ended. Preserve `trained-hybrid-8840u-launch-v1.json` and
`ai/runs/trained-hybrid-8840u-failed-v1`; the separate v2 attempt above completed.

## Previous checkpoint: trained hybrid cost profile and development grids

The bounded local cost investigation is complete. It repeats the existing
six-player Recharged/sealed building fixture (2029) with the verified public-0
ensemble, eight worlds per continuation mode and four engine workers. ORT
thread order is 1, 4, 4, 1. No fresh game seed, HF job or gradient run is involved.

| ORT threads | Two request times | Mean ONNX time | Mean engine / IPC / JSON time |
| --- | --- | ---: | ---: |
| 1 | 34.15s, 35.61s | 24.89s | 8.13s |
| 4 | 22.79s, 23.54s | 11.48s | 9.26s |

Mean whole-request speedup is **1.506x**. Every internal policy-choice transcript
matches across the four profiled runs. Root decisions and terminal outcomes also
match the earlier probe; no rollout is capped. There are 28,074 policy rows per request including
the root proposal. Only 24.3% of padded action slots are legal actions, suggesting
batch packing as another possible optimization, not an established speedup.

This is one repeated fixture on the local **HX370**, not a latency distribution,
a target 8840U result or evidence of stronger play. Model loading is separately
recorded. ONNX time is included in total policy time; do not double-count it.
The pool timer combines simulator work, IPC and JSON; it does not isolate those
three costs. At one thread, inference accounts for about 71% of request time.
No runtime default, active pipeline dependency or production code was changed.

- Reproduce: `ai/.venv/bin/python ai/strong/profile-trained-hybrid-search.py NEW_OUTPUT`.
- Local results: `ai/runs/trained-hybrid-profile-v1/profile.json` and fixture/log.
  Process 322789 / session 76412 completed normally.
- Evidence: `strong/trained-hybrid-profile-evidence-v1.json`.
- HF revision `7d3a6046f6ca7a0fed2531835ff1e5df82796c56`, archive
  `archives/trained-hybrid-profile-evidence-v1.tgz`, SHA256
  `73926eae41527487cd820110ce8f18a8ab8ca7ec4102344666178d1d2f3625e1`. All 13 files remotely verified.

At the 2026-10-24T11:04:58.294716+00:00 snapshot, all four candidate grids are submitted: 108 shards per model, 432 unique jobs / 26,880 candidate games, plus the completed 6,720-game parent reference. All four launch evidence archives are remotely verified. All eight runtime probes passed. The only coordinator remains PID 71261 / session 77604, now collecting the development results; its 39 dependencies are unchanged. Do not duplicate submission or collection. No candidate is selected and final seeds remain unused.

Next: finish the fixed full-game comparison and report whether its small
validation gains translate. Do not automatically add training epochs. If a
bounded hybrid study is justified, retain all player counts and rule combinations,
including the earlier five/six-player open-auction regressions; compare auction-only,
building-only and combined search against model-only and independent search.
Use realistic opponent mixtures and hidden-bid beliefs. Profile and benchmark
any proposed inference optimization on the actual 8840U before setting a budget.
More simulations alone do not correct inaccurate continuation policies.

## Previous checkpoint: actual trained hybrid continuations and local cost

The trained hybrid prototype now passes integration checks on the parent and
all four actual trained ensembles. This is separate from the unchanged model-only
development pipeline and does not launch any HF job or gradient run.

- Batched inference agrees with serial inference on 80 count/rule/phase cells
  per model, covering all 2–6-player counts and four rule combinations.
- Full continuations cover four existing Recharged/sealed positions: bidding
  with earlier sealed submissions and building, at two and six players.
- Each model/position uses one and eight worlds per continuation mode, with
  both neural and neural/economic continuations: **40 searches, 2,160 terminal
  simulations, zero caps**. Legal actions and original model proposals are checked.
- Shared sample prefixes match exactly when the budget increases. All adverse
  outcomes remain recorded; no model or search budget was selected by win credit.

Eight-world request times on the **local HX370**, with four engine workers and
one inference thread, were:

| Model | 2p building | 2p bid | 6p bid | 6p building |
| --- | ---: | ---: | ---: | ---: |
| parent | 10.01s | 7.45s | 19.57s | 20.57s |
| frozen-0 | 16.13s | 10.62s | 30.01s | 31.04s |
| frozen-1 | 16.76s | 10.91s | 31.41s | 34.00s |
| public-0 | 17.61s | 12.11s | 33.01s | 34.82s |
| public-1 | 18.22s | 12.01s | 33.87s | 34.30s |

Each timing is one fixture run with a loaded model and newly started search
workers; this is not a latency distribution, a target 8840U measurement or fresh
whole-game strength. Model-only millisecond latency does not transfer to full
neural simulation search. This cost is plausible for background jobs, but not
instant analysis at this budget. Profile policy and engine costs before increasing
the budget or choosing hardware. The still-uncalibrated value head is not used
to replace terminal outcomes.

The first admission attempt rejected the current checkout's older
`features-v4.cjs` difference before creating probe outputs or running searches.
The completed probe reconstructs the exact trained engine and JavaScript
helpers, then adds only the isolated hybrid adapter. Used Python inference/pool
files match the frozen source. Every copied file and experimental-code hash is
checked again after execution. Existing research files were not reverted.

- Reproduce: `ai/.venv/bin/python ai/strong/probe-trained-hybrid-search.py NEW_OUTPUT`.
- Results/runtime: `ai/runs/trained-hybrid-probe-v2/`; log:
  `ai/runs/trained-hybrid-probe-v2.log`. Completed session 52006, elapsed 508.67 s.
- Evidence: `strong/trained-hybrid-probe-evidence-v2.json`.
- HF revision `ab777c678e025b0936a6e371dc8ead6b7b1ef082`; archive
  `archives/trained-hybrid-probe-evidence-v2.tgz`; SHA256
  `bfa856381debe49caf2a737ec611f1dae4545d72f5355f80c1631c8673d54caa`.
  All 16 archived files are verified, including per-search outcomes, fixtures,
  source, versions and the failed first admission log/source.

At the owned 10:51:13 UTC snapshot, all four two-player runtime probes are complete
and independently verified; the four six-player probes remain RUNNING. The only
coordinator remains PID 71261 / session 77604, with all 39 dependency hashes unchanged.
No candidate grid has been submitted yet. It owns the pending probe collection,
full candidate grids and comparison. No new hybrid jobs, final tests, candidate
selection or publication have occurred.

## Previous checkpoint: trained models verified and measured on the 8840U

Both original HF training jobs completed. All eight seeds (four per architecture)
and all four prescribed ensembles passed independent verification. The parent
weights are unchanged; each seed completed 120 epochs / 6,120 optimizer updates
on HF GPUs. No new local gradients or replacement training jobs were used.
The collector completed normally at 10:23:39 UTC. The four model pins are in
`strong/policy-iteration-development-pins-v2/`. No candidate is selected or
qualified, and the reserved final-test seeds remain unused.

### Learning outcome and diminishing returns

The learned corrections recover only small gains on validation simulations:

| Ensemble | Train simulated gain | Validation simulated gain | Changed validation moves | Adverse changes |
| --- | ---: | ---: | ---: | ---: |
| frozen-0 | 0.528 pp | 0.192 pp | 441 / 4,320 | 110 |
| frozen-1 | 0.452 pp | 0.386 pp | 264 / 4,320 | 53 |
| public-0 | 2.671 pp | 0.325 pp | 571 / 4,320 | 163 |
| public-1 | 0.453 pp | 0.171 pp | 67 / 4,320 | 12 |

All frozen-representation seeds selected epoch 10. Public-representation seeds
12101–12104 selected epochs 35, 5, 5 and 60 respectively. Later training generally
degrades validation performance; the public-0 training/validation gap is large.
These same validation deals selected the epochs, so these are conditional
training diagnostics, not independent evidence of real-game improvements.
No model was dropped or selected from these small differences. Finish the
prescribed full-game comparison before drawing a strength conclusion. Do not
launch another gradient round automatically; this supports examining the
planned bounded hybrid approach if the small gains fail to transfer.

Results: `strong/policy-iteration-training-results-v2.json`. Complete per-seed
histories, calibration, parity and immutable model pins are archived in:

- Frozen: `strong/policy-iteration-trained-frozen-evidence-v2.json`, HF revision
  `62ea88095773de4e3eaa07d8b42911d9528c49fd`.
- Public: `strong/policy-iteration-trained-public-evidence-v2.json`, HF revision
  `aa3c1a83e19254638f3a21ce98cb0d18caeed366`.

### Actual trained CPU benchmark

All 10,212 requests (2,553 per ensemble, all 2–6-player/rule/phase fixtures)
returned legal moves identical to the frozen runtime, with zero observed value
difference. Packages also passed standalone checks from `/`.

| Ensemble | Median warm ms | 95th percentile ms | Cold first request ms |
| --- | ---: | ---: | ---: |
| frozen-0 | 4.484 | 7.089 | 214.022 |
| frozen-1 | 4.346 | 6.952 | 224.209 |
| public-0 | 5.543 | 8.031 | 255.209 |
| public-1 | 5.904 | 8.767 | 251.921 |

Target: `coyotte508-4X4-BOX-8840U`, AMD Ryzen 7 8840U. These sequential timings
include the standalone JSONL worker but no search. They establish model-only
CPU feasibility, not browser performance, hybrid-search latency or strength.

- Report: `strong/policy-iteration-trained-8840u-results-v2.json`.
- Evidence: `strong/policy-iteration-trained-8840u-evidence-v2.json`.
- HF revision `d86e395ddd8cb82d7947f47f8d4a767106fd5049`, archive
  `archives/policy-iteration-trained-8840u-evidence-v2.tgz`, SHA256
  `a3548810bfa3f7dcd2986dc8730180bbea5970b9351415ef0d804499bc3aba6c`.
  All 38 archived files, including deployable standalone packages and raw target
  responses, were verified after download.
- Local preparation/results: `ai/runs/policy-iteration-trained-8840u-prepared-v2`
  and `ai/runs/policy-iteration-trained-8840u-results-v2`.
- Remote directory: `/home/coyotte508/powergrid-ai-policy-iteration-trained-v2`.
  Target run completed; do not relaunch into that directory.

### Verification repair and current process ownership

After an unrelated collector termination was recovered, the first independent
verification failed because live `by_player_count` keys are integers while JSON
keys are strings. The verifier now normalizes only this documented field. Counts,
model identities, legal decisions, weights and numerical tolerances remain fully
checked. Four regression tests and both actual trained integrations pass. All
32 frozen-head artifacts are identical to the failed attempt. Training inputs,
weights, source archives and remote job IDs were not changed.

The failed collector, waiting development coordinator and failed output directory
were preserved before restarting the local pipeline. Their paths are recorded
in `ai/runs/policy-iteration-training-verifier-json-repair-v2.json`. The earlier
signal interruption is separately preserved. Repair evidence:
`strong/policy-iteration-training-verifier-json-repair-evidence-v2.json`, HF
revision `ec8788213f5965969c3bb95af6a19f4c73980b93`, archive
`archives/policy-iteration-training-verifier-json-repair-evidence-v2.tgz`, SHA256
`02b900406b522c7205b778066dd0e9ebf7fb91f61be61ff1740fb8dd211f48b1`.

The trained collector **PID 71229 / session 25772 is complete**. The only live
coordinator is **development PID 71261 / session 77604**, with canonical state
`ai/runs/policy-iteration-development-coordinator-v2/state.json`. It owns eight
CPU runtime jobs (all directly confirmed RUNNING after launch), then four full
candidate grids and the prescribed comparison. Do not duplicate those operations
or edit its 39 frozen dependencies. Its inputs include the repaired verifier.
Runtime launch evidence: `strong/policy-iteration-candidate-runtime-launch-evidence-v2.json`,
HF revision `0ffaf9eba7b3ba6892c9821b86a4082fe4371d14`.

All twelve trained technical receipts have now been prepared and archived in
`ai/runs/policy-iteration-final-evidence-v2/`. Exact source/engine compatibility,
model identities and full trained target coverage passed the converter. Evidence:
`strong/policy-iteration-final-technical-evidence-v2.json`, HF revision
`23487b7a1715262259fc2bf11a689cf393643939`, archive
`archives/policy-iteration-final-technical-evidence-archive-v2.tgz`, SHA256
`8236b137294dde8628b92816cba54ecdf2251d4ce9f9d382924d7899c56154b3`.
These are technical receipts only. No candidate was selected, no final games were
run and no AI was published. Fresh full-game comparisons and any justified later
hybrid evaluation remain the strength checkpoints.

## Previous checkpoint: full labels and baseline verified; two GPU jobs submitted

**Local collector recovery, 10:13 UTC:** polling session65326 returned exit143,
and `/proc/2850424` was absent. Its last state was waiting for training completion,
with no commands started, no verified outputs/pins, and no lock holder. The sender
of the termination signal is unknown. All28 frozen dependencies matched. The
original directory was preserved as
`ai/runs/policy-iteration-training-harvest-interrupted-v2/`, and the unchanged
collector was started with the original canonical run name: **PID35876,
execsession68668**. Both existing HF jobs were kept; no remote restart, new
training job, protocol change or duplicate collection occurred. The live
state path remains `ai/runs/policy-iteration-training-harvest-v2/state.json`.
The original frozen-head job completed, and its owned verification began at
10:15:48UTC. The public-head job was still RUNNING at its last direct inspection.

Recovery evidence: `strong/policy-iteration-training-harvest-recovery-evidence-v2.json`,
HF revision `6203af10ce532bdca0e4ec7409b2676f19449313`, archive
`archives/policy-iteration-training-harvest-recovery-evidence-v2.tgz`, SHA256
`e9a46acb27610bc8e9ba8ce959138f93bebeffff09a7f0e02fddde94f6fea938`.
Seven files include the original state, interruption checks, resumed state and
unchanged collector/development code. The remote archive was verified.

All **948 new label shards plus 60 pilot shards** are independently verified:
17,280 roots, both continuation modes, and 33,351,552 completed simulations.
The full data bundle has 12,960 training / 4,320 validation roots, split by deal;
27,744 negative action advantages were retained. The complete source package
passed data recovery, four model tests, four synthetic export/parity checks and
three training-contract tests. These checks did not run local gradients.

The prescribed training coordinator submitted exactly two HF jobs at 10:06 UTC:

| Head | HF job | Seeds | Hardware / timeout |
| --- | --- | --- | --- |
| Frozen representation | `6adc8338046eb82b1ecdbb92` | 12101–12104 |L4x1 / 3 hours|
| Full public representation | `6adc833d1e112550ce7deb4c` | 12101–12104 |L4x1 / 3 hours|

Both were scheduling at the harvester's10:07:17 UTC snapshot. This is submission,
not a completed gradient run or verified trained candidate. Each job trains four
seeds; the frozen design exports both prescribed ensemble uncertainty penalties.
Do not launch replacements or manually collect their outputs while the existing
trained-output harvester owns them.

- Data evidence: `strong/policy-iteration-training-data-evidence-v2.json`, HF
  revision `eaba4f51ba9b65a52d35bff3d1478e3fbd77742a`.
- Full source: `strong/policy-iteration-training-source-v2.json`, dataset revision
  `776fc237a19be9789fe160d4406e68cd31adf080`, archive
  `strong-source-policy-iteration-training-20261024-v2.tgz`, SHA256
  `21a162cb75167e3781bcd8e8f2810b4b93f37712775af300abb910fdcccfd958`.
- Launch evidence: `strong/policy-iteration-training-launch-frozen-evidence-v2.json`
  and `strong/policy-iteration-training-launch-public-evidence-v2.json`.
  Their verified archive revisions are respectively
  `7fd7925f7be052ab5f5fd2681779c60923651107` and
  `c1befdde62f0cbbfeec95977477f50373b5fc31d`.

The original collector completed normally at 10:04:46 UTC: **108/108 parent
batches, 6,720 games, all 27 cells**. The training coordinator also completed its
prescribed launch sequence. Do not restart either completed process. The two
remaining active processes are trained-output harvester PID 2850424  / session65326
and development coordinator PID 2950746  / session63641. Verify actual process
identities and their state files before acting. Frozen dependencies remain
unchanged. Trained AMD8840U measurement, full development comparisons and the
reserved final gate remain pending; no model is selected or qualified.

### Complete parent baseline

The newly complete six-player search cell has 384 games over 16 independent deals:

| Rules | Win share | Exploratory 95% whole-deal interval |
| --- | ---: | ---: |
| Overall |37.6302%|32.8125–42.5781%|
| Original/open |51.5625%|42.7083–60.4167%|
| Original/sealed |14.5833%|7.2917–21.8750%|
| Recharged/open |57.2917%|45.8333–66.6667%|
| Recharged/sealed |27.0833%|16.6667–38.5417%|

Both sealed-rule intervals include the 16.6667% chance baseline. Six-player
aggregate performance is clearly better than chance in this development sample,
but sealed play and the previously identified 2–4p deficits prevent qualification.
This is the unchanged model-only parent, not new training improvement.

- Diagnostic: `strong/policy-iteration-parent-reference-complete-v2.json`.
- Evidence: `strong/policy-iteration-parent-reference-complete-evidence-v2.json`.
- HF revision `2dc527b0ecb4818484d936a8afdc5b441f29739a`; archive
  `archives/policy-iteration-parent-reference-complete-evidence-v2.tgz`;
  SHA256 `47a85217a2f8338a51a22a6815882b333f833f13ee81cb8a7b9d7cbc8c682e14`.
  All 1,117 archived files and the remote archive were verified.

### Full teacher-label diagnostic

The existing read-only audit now covers all 17,280 planned roots. It selects a
move with simulation batch A and measures that move on B, then reverses the roles,
with continuation modes averaged within each world. At the fixed 0.025 margin,
mean selection gain is 0.058641 and separate-batch simulated gain 0.051495.
There are 12,284 changed directions; 1,740 are adverse on the other batch (14.16%).
Train/validation means are 0.051442/0.051655; player-count means range 0.046140
through 0.058344. Both open and sealed aggregates remain positive. These are
conditional simulated credits on selected positions, not independent real-game
win-rate improvements, significance tests, or evidence of model generalization.
The design and margin were not adjusted from this audit.

- Reproduce to a fresh directory with
  `ai/.venv/bin/python ai/strong/inspect-policy-iteration-label-quality.py --output NEW_PATH`.
- Evidence: `strong/policy-iteration-label-quality-full-evidence-v2.json`.
- HF revision `dc6511fa5bd64158ce9608779e7a50e6d4222de2`; archive
  `archives/policy-iteration-label-quality-full-v2.tgz`; SHA256
  `6a2b4b604b03cffe90408c5bcc563f65405700f6c2bf8855ee5aa5f6d42e12fe`.
  Nine archived files include per-root records, complete provenance and audit code.
  The reused audit's generic scope text describes partial snapshots; its
  `full_cohort:true` and complete coverage establish that this run is the full
  planned cohort. It is still not a representative sample of all game positions.

The signal supports completing the already prescribed learning/evaluation round.
It does not justify another training round automatically. Fresh full-game gains,
sealed-auction performance, 5–6p regressions and actual 8840U cost remain the
stop/continue criteria for this approach and any later bounded hybrid study.

## Previous checkpoint: all label jobs complete; five-player baseline verified

The preceding turn was a verified wait on the final live label job and the four
local pipeline processes. This turn confirms the last label job completed and
adds a new verified five-player baseline diagnostic. **No new gradients yet.**

All948 effective label jobs are now complete: the owned09:29 status had916
complete;09:43 direct checks completed28 of the remaining32;09:46 checks completed
three more; final job `6adc48851e112550ce7dd47a` completed at09:47:33UTC, confirmed
by HF at09:48:51. Local verification has reached916/948. The existing collector
will verify the remaining32 on its next pass; do not duplicate that work or start
partial-data training. All four pipeline process identities remain live.

The parent reference now has105/108 verified batches and6,432 games. Five-player
search coverage is complete:320 games,16 independent deals, all seats/four rules.
The model-only parent wins34.375% overall, exploratory95% whole-deal interval
30.0–38.4375%, above20% chance. Rule splits are:

| Rules | Win share | Exploratory95% interval |
| --- | ---: | ---: |
| Original/open |51.25%|40.0–62.5%|
| Original/sealed |15.0%|7.5–23.75%|
| Recharged/open |46.25%|35.0–56.25%|
| Recharged/sealed |25.0%|18.75–31.25%|

Both sealed-rule intervals include chance. This is not evidence of improvement
from the pending new training, nor qualification; other2–4p deficits remain.
It reinforces treating sealed auctions separately at every player count, rather
than assuming the weakness only concerns4p Recharged. Only6p search remains
incomplete (96/384 verified games); do not summarize that partial cell.

- Diagnostic: `strong/policy-iteration-parent-reference-progress-105-v2.json`.
- Evidence: `strong/policy-iteration-parent-reference-105-evidence-v2.json`.
- Immutable HF revision `85372928a30a944c1b90ef208e7bb5031d8a282b`;
  archive `archives/policy-iteration-parent-reference-105-evidence-v2.tgz`.
- Archive SHA256 `edb87cf5f388e0855633116480e58f6f20c026032237a3a2125a255f79ba61d4`;
 1,090 files, remote download/hash verified. Includes raw105 batches, provenance,
  runtime admission, diagnostic and code. No existing artifact was overwritten.
- Six-player parent jobs remaining at the owned09:47 snapshot:
  `6adc39361e112550ce7dcd1f`, `6adc38fe1e112550ce7dccd3`,
  `6adc391a1e112550ce7dccff`. Latest inspected statuses remainRUNNING; quiet
  evaluator logs do not imply failure. The collector owns their verification.

## Previous checkpoint: actual ONNX hybrid inference plumbing

The preceding turn added the isolated hybrid continuation adapter. This turn
adds `strong/hybrid_search.py`: a persistent local JSONL driver using batched
ONNX decisions, public-only seeds shared between4.2/4.3, the existing six-option
shortlist plus the model proposal, and neural/economic full continuations.
Auction-only, building-only and combined scopes are supported for later
comparisons. Equal-weight mean simulated credits rank moves; exact ties retain
the model proposal. The current default is8 worlds per continuation mode.
These are prototype defaults, not a selected or strength-validated configuration.

Every rollout is accounted for. Any cap makes the entire search unusable,
keeps the original proposal and reports the cap; partial means are not used.
The frozen teacher/training/development paths were not modified. No HF job or
new gradient was started by this work.

Reproduce the local integration check in a **new** output directory:
`ai/.venv/bin/python ai/strong/preflight-hybrid-search.py NEW_OUTPUT`.
Completed session25931 produced `ai/runs/hybrid-search-preflight-v2/`;
`strong/hybrid-search-preflight-v2.json` persists the results, CLI check and logs.

- Existing trained, unqualified parent plus all four **untrained** architecture
  exports:80 positions/model spanning every2–6p/rule/phase cell. Fixed64 batching,
  single-row batching and serial inference choose identical legal moves.
- Parent2p/6p Recharged/sealed searches exactly reproduce actual neural rollout
  outputs from the frozen old worker. The new4.3 public architecture completes
  economic-opponent continuations at both counts, and its6p mixed search completes.
- The untrained public-0 model caps **6/12** simulations in2p mixed search (the
  all-neural mode). That search remains explicitly **unusable**. The first
  preflight stopped on its too-strong expectation that untrained self-play would
  always end; its failed log/report are retained. The second check distinguishes
  correct fallback behavior from uncapped complete continuations. No production
  gate, rollout horizon or strength threshold was relaxed.
- A complete hidden-field-mutated search has identical seed/actions/outcomes,
  including the same caps. A deliberate one-step cap test verifies fallback;
  three phase-gating and seven budget rejection controls pass. JSONL serving
  from `/` produces a legal resource move without invoking search.
- These tiny one-world integration cases are not fresh strength evaluations,
  search-budget evidence or target8840U timings. Actual newly trained ensembles,
  their self-play behavior, realistic opponent mixtures, target latency and
  whole-game hybrid ablations remain pending. Do not use these fixtures as a
  model selection result.

At09:26UTC, all four existing pipeline processes are live. The collector has
verified822/948 data batches and103/108 parent batches (6,256 games). Training
still waits for complete data; no new trained outputs or final-test use.

## Previous checkpoint: hybrid continuation format adapter

The preceding turn was a verified wait on live HF jobs and collector session
82318. This turn adds an isolated experimental adapter for future hybrid play,
without changing any frozen teacher, training or development dependency.
`strong/hybrid-continuations.cjs` supports both4.2 and4.3 feature formats. The
existing neural teacher only accepts4.2; new ensembles use1217-state/101-action
4.3 features, so they cannot simply be substituted into that teacher.

The adapter reuses the unchanged public scenario and policy-belief machinery,
encodes every rollout observation and earlier sealed bidder with the requested
format, and checks identical action ordering. Root preparation strips private
information. It does not introduce a new search policy or start any remote job.

- Reproduce: `node --test ai/strong/test-hybrid-continuations.cjs`.
- All6 tests pass; report/log and exact dependency hashes:
  `strong/hybrid-continuations-controls-v1.json`.
-25 positions cover all2–6p auction/rule combinations plus saved building
  positions. Short controls preserve every transition and truncation record.
-32 complete paired rollouts at2p/6p across all four rules retain identical
  terminal outcomes (64 engine executions). Neural-role choices here are fixed
  legal controls, not actual trained inference or strength evidence.
- Earlier bidder encoding, hidden-field mutation invariance, worker partitioning,
  legal passes and invalid/missing bids are checked. The first pass fixture used
  an opening auction where passing was illegal; the test now reaches a genuine
  later auction and verifies a valid inferred pass before the rejection checks.
- A version-aware batched ONNX driver, actual trained rollout integration,
 8840U timing and fresh hybrid comparisons remain pending. The current training
  and model-only development protocol remain unchanged.

All four live local process identities and dependency hashes were rechecked.
Collector cycle27 is verifying outputs from the latest HF snapshot822COMPLETED /
126RUNNING; its preceding verified total is753/948. The seven remaining parent
jobs were inspected directly at09:08UTC and were allRUNNING. No new gradients,
trained outputs, final-seed use or model qualification yet. Live state supersedes
these counts; do not start competing collectors or preparation.

## Previous checkpoint: older multiplayer hybrid regression audit

The preceding turn was a verified wait on the three oldest remaining HF label
jobs and collector session82318. The current turn adds a read-only terminal
audit of all12 completed hybrid model/count cells at3–6p, reusing the existing
paired statistics. It revalidates every saved raw hash, source/model protocol,
pairing and earlier win summary. No simulations, gradients, final seeds or
additional jobs were launched.

- Script: `strong/analyze-multiplayer-search-outcomes.py --output NEW_PATH`.
- Result: `strong/multiplayer-search-terminal-analysis-v1.json`.
- For10102, the6p overall−9.375pp hybrid regression (exploratory95% interval
  −17.1875 to−1.5625) is entirely in the aggregate open-auction cells; both
  sealed cells have unchanged win share, although individual games change.
- Recharged/open6p:28/48 raw wins versus16/48 hybrid wins;18 wins lost,6 gained.
  Mean terminal cities14.375→12.2083, powered14.0208→12.125,
  cash21.1042→31.1667. Paired city change−2.1667 [−2.8542,−1.375],
  cash+10.0625 [3.7708,16.9589]. Capacity change−0.75 includes zero.
- Recharged/open5p also loses25pp (52.5→27.5%) with2.35 fewer terminal cities,
  but14.675 less cash. This does not support a universal cash-spending rule.
- These are8 reused independent development deals/cell, marginal bootstrap
  intervals and overlapping failure categories. End states cannot attribute
  the failure causally to auctions versus building. No new model-strength claim.

Follow-up implication: a bounded hybrid comparison should retain5–6p open
cases and distinguish auction-only, building-only and combined search with
realistic continuations. Increasing sample count or only correcting sealed
beliefs is not enough to address the observed failure pattern. The existing
training/development protocols remain frozen. All four processes are live with
unchanged dependencies; collector cycle24 is active, with656/948 labels and
100/108 parent batches at its preceding completed snapshot.

## Previous checkpoint: final evidence conversion and hybrid decision point

The preceding turn was a verified wait and a review of historical hybrid
evidence. The user wants candid advice when strength gains taper off; they have
not paused work. Finish the current round and judge fresh complete-game results,
not label throughput. A bounded hybrid comparison is a sensible follow-up, but
the older6p regression must not be hidden. See the user-steering section in
`RESUME.md` for the exact earlier results and8840U timings. No hybrid jobs have
been launched and the active model-only evaluation stays unchanged.

Added `strong/prepare-policy-iteration-final-evidence.py` with `check` and
`prepare` stages. After all four trained ensembles have been independently
verified, benchmarked on the8840U and archived, it creates12 per-model parity,
CPU and standalone-package receipts in
`ai/runs/policy-iteration-final-evidence-v2`. These match the unchanged final
verifier's input schema. It checks pinned training/target/package identities,
every archived input receipt, all2553 fixtures/counts,17280 cached parity cases,
and every packaged engine/inference file against the actual frozen final
archive. The inactive-value claim traces to the admitted immutable native
parity checker, which asserts zeros on every serving/cache batch.

Three tests passed: reject mixed models/incomplete coverage/wrong CPU/search;
exercise the real final verifier with converted unit-test receipts (it still
rejects missing games); and reject pending training before filesystem/network
side effects. A real `prepare` invocation also rejected the current pending
training before creating the output directory. Full integration remains pending
actual trained outputs. No candidate JSON, selection, jobs, gradients, final
seeds or publication are produced by this converter.

All four existing process identities and all their frozen dependencies were
rechecked unchanged. The latest completed collection snapshot is643/948 labels,
20,150,016 continuations including the pilot,100/108 parent batches and6,016
parent games; collector cycle23 is active. Training is still waiting on the
remaining labels. Live state files supersede these counts.

## Previous checkpoint: four-player baseline and final-wrapper compatibility

Previous turn was a verified wait. This turn produced new diagnostic and runtime
compatibility evidence. The four pipeline processes are still active and their
hashed dependencies are unchanged. Latest completed collection snapshot:
**614/948 labels**, **19,099,392 continuations**, **100/108 parent batches** and
**6,016 parent games**. No new gradients or trained outputs yet. No final seeds,
selection or production publication.

The four-player search baseline now covers all16 paired deals /256 games. Its
fractional win rate is **30.859375%**, with exploratory95% deal-bootstrap interval
**25.0–36.71875%**. This does not establish an advantage over25% chance. The32.5%
final point floor is orientation only; the actual reserved80-deal test is unused.
Rule results (64 games each):

| Rules | Win rate | Exploratory95% interval |
| --- | ---: | ---: |
| Original/open |45.3125%|34.375–56.25%|
| Original/sealed |25.0%|12.5–39.0625%|
| Recharged/open |37.5%|25.0–50.0%|
| Recharged/sealed |15.625%|6.25–25.0%|

All adverse cells are retained. Only5p/6p search cells remain incomplete; no
strength summaries are drawn from those partial cells. The parent remains
unqualified. The new heads must demonstrate improvement in actual whole games,
including sealed auctions; promising conditional labels do not prove that.

- Diagnostic: `strong/policy-iteration-parent-reference-progress-100-v2.json`.
- Complete100-batch evidence: `strong/policy-iteration-parent-reference-100-evidence-v2.json`.
- HF revision: `06066a778ed94b5b3ad3de51d843b25126e9d598`; archive:
  `archives/policy-iteration-parent-reference-100-evidence-v2.tgz`.

The existing final runtime was audited against the current development archive.
All1,165 engine files and the ONNX evaluator/inference/encoder/search code match.
The five differences among1,397 common files are the provenance wrapper plus
checkpoint-training, export, packaging and collection helpers; they do not
replace the actual ONNX evaluation path. The existing final source is therefore
reused, without creating another source variant.

`strong/check-policy-iteration-final-runtime.py` then exercised the actual final
wrapper with all four **synthetic/untrained** ensemble architectures,2p and6p,
all four rules, offset4, and a separate plumbing seed namespace. All128 games
completed and their exact model/runtime provenance was checked. Only artifact
upload was captured locally. This validates wrapper compatibility, not strength
or actual trained models. The existing final launcher still requires a selected
candidate; the final ledger remains unspent. One initial local path-lookup typo
failed before any test tree or game was created; its log is preserved.

- Report: `strong/policy-iteration-final-runtime-preflight-v2.json`.
- Evidence: `strong/policy-iteration-final-runtime-compatibility-evidence-v2.json`.
- HF revision: `194535560839cdc05f8edadcaba83ac32537f6eb`; archive:
  `archives/policy-iteration-final-runtime-compatibility-evidence-v2.tgz`.
- Local test session7799 and diagnostic session11860 completed. Neither is a
  fifth coordinator. The four long-lived processes below remain authoritative.
- Final qualification still needs an eligible trained candidate, actual trained
  parity/AMD/package evidence and all reserved games. Existing aggregate
  benchmark reports need verified per-candidate adapters for `verify-final.py`;
  do not label the runtime compatibility check as the entire final gate.

## Earlier checkpoint: trained target benchmark tooling prepared

The four existing local pipeline processes remain active and unchanged. The
latest completed collection cycle verified **595/948** new label batches and
**18,656,064** continuations including the pilot; parent evaluation has
**97/108 batches /5,824 games**. Read their live state files for newer counts.
The training coordinator still waits for the complete dataset. No new gradients,
trained candidates, final-test use or publication yet.

`ai/strong/benchmark-policy-iteration-trained-8840u.py` now supplies explicit
`check`, `prepare`, `run`, `collect`, and `archive` stages for **actual trained**
exports. It is not a fifth background process. Do not run it until both trained
heads are independently verified and archived. It revalidates the exact training
guards, data/source identities, all four candidate pins and verification artifacts;
synthetic or incomplete handoffs fail before creating packages or contacting the
8840U. Existing ambiguous target-launch records cannot be retried automatically.

After admission, it packages byte-identical frozen development runtime plus each
trained ONNX export, verifies standalone serving from an unrelated working
directory, and runs the existing2553-fixture harness per model on `minipc`.
Collection checks all10,212 target responses, legal moves, exact reference moves,
values and hashes before archiving packages and raw timing evidence as one HF
tar. It reports every candidate and does not select or promote a model. The old
synthetic architecture benchmark remains separate and cannot substitute for this.

Three admission/duplicate-launch tests passed. A real preparation attempt while
training is pending was rejected before any output tree or remote launch. All
four live processes' dependencies remain unchanged. **Actual trained packaging
and target execution are still untested until those outputs exist.**

- Controls: `strong/policy-iteration-trained-8840u-controls-v2.json`.
- Preparation evidence: `strong/policy-iteration-trained-8840u-preparation-evidence-v2.json`.
- HF revision: `dcb1faaa982ec01735e54f53b6c1c578e721b469`; archive: `archives/policy-iteration-trained-8840u-preparation-evidence-v2.tgz`.
- Future outputs: `ai/runs/policy-iteration-trained-8840u-prepared-v2` and
  `ai/runs/policy-iteration-trained-8840u-results-v2`.
- Future target guard: `ai/strong/policy-iteration-trained-8840u-launch-v2.json`;
  target directory: `/home/coyotte508/powergrid-ai-policy-iteration-trained-v2`.
  None exists yet. Inspect recorded actual processes before any later recovery.

## Earlier checkpoint: collection and full-data training handoff are active

Previous goal turn: **verified wait** (the live collector completed another
verification cycle). This turn made **progress**: the bounded development
coordinator is tested and active, and collection reached552 verified label
shards. The goal remains active. There are still no new model gradients,
final-test use, qualification or production changes.

### Development coordinator ACTIVE — fourth local process

PID **2950746**, exec session **63641**, started
`2026-10-24T06:45:25.855641+00:00`. Command:

```sh
ai/.venv/bin/python -u ai/strong/coordinate-policy-iteration-development.py \
  --run-name policy-iteration-development-coordinator-v2 --execute \
  --interval-seconds 300 --max-hours 24
```

State: `ai/runs/policy-iteration-development-coordinator-v2/state.json`; log:
`ai/runs/policy-iteration-development-coordinator-v2.log`. It currently waits for
**both** upstreams: all948 labels plus108 parent reference batches verified, and
all four exact trained ensemble pins independently verified and archived. It
checks actual upstream process identities while waiting. No candidate runtime
probe or development job has been submitted yet;commands started are empty.

It freezes39 code dependencies. Once the prerequisites pass, it obtains the
original collector's lock before changing development guards, preventing that
collector from reading a partly written launch intent. Do not run competing
development launch/status/collection commands or edit hashed dependencies while
this coordinator is active. Existing parent jobs and all three older local
processes remain untouched.

Its only planned submissions are **8 complete-deal runtime probes** (each of
four ensembles at2p and6p;128 probe games) and, only after same-candidate/source/
hardware runtime admission, **4 ×108 full development shards**. The existing
manager's conservative projection and at-most12h job bound remain unchanged;
a failed admission stops instead of shortening games/search or weakening opponents.
Every ensemble gets the complete27-cell/6,720-game grid. All five arms including
the parent then enter the already frozen **33,600-game,8-contrast comparison**.
All rule/count/opponent cells, adverse results and all four prespecified seed
ensembles are retained;there is no automatic best-model selection.

The coordinator archives the probe guards, each full grid's guards/runtime
proof, and finally the full verified comparison as compact HF archives. It
terminates at `development_comparison_complete` or its24h window. Errors and
ambiguous handles stop with intermediates preserved;**no retries,cancellations,
local gradients,final evaluation or candidate promotion**. Actual trained AMD
benchmark/standalone export and the untouched final gate still remain. On a
future explicit pause, stop this coordinator too so it cannot submit later.

Three contract test suites passed:both complete upstream handoffs are required,
all four archived candidate identities are required,and probes cover the exact
2p/6p endpoints with a separate runtime seed namespace. A real-data one-shot
check started no commands; a second coordinator was lock-rejected before output
creation. **Full trained/runtime/grid integration is pending real trained data.**
Controls: `strong/policy-iteration-development-coordinator-controls-v2.json`.
Evidence: `strong/policy-iteration-development-coordinator-evidence-v2.json`,
revision`a2269d800d44d62dbc868e41decdece52bc0a322`, archive
`archives/policy-iteration-development-coordinator-evidence-v2.tgz`, SHA
`55c22d8507e2439ea977055e9b5dcaa85a12739490eca6d4b8de061ae3f846aa`.
Archive55965 finished successfully and downloaded bytes were verified.

Latest completed label cycle9: **552/948 shards /17,783,232 continuations**.
Snapshot06:42:31UTC:552 completed,396 running,**none queued**. All948 effective
jobs have started;no additional hardware migration is needed. Parent remains
96 verified batches/5,760 games. The earlier label-quality audit remains frozen
at475 shards. Training submissions are still0;none of this infrastructure is
model-strength evidence. Verify the four actual local PIDs/sessions before any
recovery action;do not recreate them just because logs are quiet.

### Trained-output harvester ACTIVE — third local process

PID **2850424**, exec session **65326**, started
`2026-10-24T06:29:16.427844+00:00`. Command:

```sh
ai/.venv/bin/python -u ai/strong/harvest-policy-iteration-training.py \
  --run-name policy-iteration-training-harvest-v2 --execute \
  --interval-seconds 120 --max-wait-hours 12
```

State: `ai/runs/policy-iteration-training-harvest-v2/state.json`; log:
`ai/runs/policy-iteration-training-harvest-v2.log`. It currently waits for the
existing training coordinator's **both_jobs_submitted** handoff. No collection
command, training model or candidate pin exists yet. Its28 code dependencies are
hashed, including the existing training collector/verifier, source-admission
code and development pin contract. Do not edit those while it is active.

Once both exact prescribed jobs have archived launch evidence, it polls their
actual HF handles. Each completed job goes through
`collect-policy-iteration-training.py`, which independently checks all four
seed checkpoints, frozen parent tensors, epoch selection, exact exports and
2,553 serving/17,280 cached positions. Only verified results produce the two
ensemble pins for that representation. The harvester then stores one compact
HF evidence archive per representation. Raw trained weights stay at their
immutable HF pins rather than being duplicated in the archive.

It **cannot submit, cancel or retry jobs**, launch development/final evaluations,
run gradients locally or promote a candidate. Errors, unknown handles, changed
code and expired waits stop the local harvester with intermediates preserved.
It terminates after both heads are verified and archived, or its12h wait window.
Do not manually run competing training collection while it is active. Verify
actual PID/command or session before deciding it stopped;never restart from a
quiet log. On an explicit pause, reconcile and stop local pipeline processes;
existing remote jobs require a separate cancellation decision.

Validation:3 contract test suites passed;incomplete/failed upstream handoffs,
wrong/duplicate jobs, mismatched source/data/recipe and changed verification code
are rejected. A real-data one-shot check at493 shards started no collection;
a duplicate harvester was rejected by its lock before creating an output tree.
**Full trained-artifact integration remains pending the actual HF outputs.**
Controls: `strong/policy-iteration-training-harvest-controls-v2.json`.
Evidence: `strong/policy-iteration-training-harvest-evidence-v2.json`, revision
`ef815eab00f394cfc70aef1767d2137dc7ae9b2b`, archive
`archives/policy-iteration-training-harvest-evidence-v2.tgz`, SHA
`9ac0a7a95ea51e1b415931eb4c93cc7cd1e84532da5e7f9752cce1c4dd6de70d`.
Archive operation25526 finished and downloaded bytes were verified.

Latest completed collection cycle7: **509/948 new label shards verified**,
**16,819,584 continuations including pilot**. Snapshot06:26:44UTC had509 completed,
430 running and9 queued;96 parent batches/5,760 reference games are verified.
The earlier475-shard audit remains a separate frozen cohort. Both original
processes(PID2476443 collector,PID2536611 training coordinator) are still alive;
this third process does not replace them. Training submissions are still0.

### Broader cross-batch label audit — completed, still no strength claim

This turn made **progress**: a read-only diagnostic froze the manifest at
**475/948 new shards /16,072,704 continuations including pilot**. It independently
reduced every fully paired position available in that snapshot: **4,520 roots**
(4,160 new +360 pilot), across all player counts and train/validation splits.
Another7,615 roots have only one continuation mode verified and are excluded,
without imputation. Data collection and the existing training coordinator remain
active; neither was duplicated or interrupted. No extra HF compute jobs were
submitted for this diagnostic, and no training inputs were prepared from it.

At the already fixed0.025 margin, A-select/B-evaluate and B-select/A-evaluate
produce a mean conditional fractional-win-score gain of **0.04983387875** over
all9,040 directions, versus0.05688068461 on the selection batches. There are
3,100 changed directions, including **448 negative evaluation outcomes (14.45%)**.
The4,160 new roots yield0.050796; the1,098 validation roots yield0.052953.
Every player-count group is positive descriptively. These are **conditional
simulated action-label results, not a trained model's whole-game win rate**.
The partial cohort is selected by runtime/scheduling and cannot represent the
full planned population. Directions share roots/deals; no independent-games
confidence interval or new acceptance threshold is claimed.

Controls confirm that selection noise can evaluate negatively, zero/margin ties
keep the parent, consistent gain survives, and incomplete modes are rejected.
The360 reused pilot roots reproduce the original assessment's gain, change and
negative counts at both fixed margins exactly (within1e-15 for floating means).
The worker, training design and final gate are unchanged. The next action remains
complete labels -> two prescribed HF training jobs -> whole-game evaluation;
this audit supports that experiment, not a shortcut to qualification.

New read-only helper: `strong/inspect-policy-iteration-label-quality.py`.
Run39065 and archive51360 finished successfully; do not restart those outputs.
Evidence: `strong/policy-iteration-label-quality-progress-evidence-v2.json`,
revision`b9e6773c6fbc17dd537638572ad667c389d8a342`, archive
`archives/policy-iteration-label-quality-progress-v2.tgz`, SHA
`acc844716cb04f33a5ed972a233760fcd3f15fcbd16f6ffbf03b7a213e4ba342`.
The one-file archive includes the exact475-shard manifest, per-root diagnostics,
coverage, provenance, assessment code, and pilot-replication check. Downloaded
archive bytes were verified. The earlier418-shard capacity checkpoint remains
intact. Both live process identities below were confirmed again after this work.

### Fourth hardware wave complete; collector resumed

This turn made **progress**. The fourth measured capacity expansion admitted
120 additional queued-job migrations, raising the cap from300 to **420**.
All300 previous migrations had started. The admission revalidated **50 full
alternative-hardware batches /2,375,232 continuations**, covering2–6 players,
both continuation modes, all three behavior policies and both opponents.
Observed wall times including setup/upload:1,412.845–7,961.616 seconds, all within
the existing conservative per-shard bounds. The exact source,192 worlds per root,
fixed inference batches, runtime multiplier1.4454652311275429,12h timeout and25%
headroom remain unchanged. No additional capacity beyond420 is admitted here.

The first pass moved114 jobs and safely skipped six originals that had already
started. Six fresh queued originals filled the remaining slots. **420 launched
migration records +9 skipped original records**, plus the two separate confirmed
upload-failure retries; all948 effective handles are distinct. Every canceled
original was confirmed never started. No live HF job was canceled or restarted.

To avoid racing guard reads, the local harvester was temporarily stopped with
SIGSTOP from05:55:22UTC to06:00:17UTC while its existing child collection and all
remote jobs continued. It was resumed withSIGCONT and its actual process checked
running again. **The goal and the training coordinator were never paused.**
Operation24746 finished; do not relaunch it. Exact durable record:
`ai/runs/policy-iteration-wave4-capacity-operation-v2.json`. All fourth-wave launch
and fill attempts are resolved. Both existing long-lived process handles below
remain the ones to use.

Snapshot `2026-10-24T06:00:14.411662+00:00`: **450 COMPLETED /432 RUNNING /
66 SCHEDULING**. The archived independently verified label snapshot is
**418/948 new shards**,15,081 root-mode pairs, **14,545,152 continuations** including
pilot. The collector is already harvesting further completions. Its next fresh
snapshot showed119 of the120 new replacements running and one scheduling.

Evidence descriptor: `strong/policy-iteration-wave4-checkpoint-v2.json`, revision
`93e02587f638fe24edbbccbdbcd53d92e49e157d`, archive
`archives/policy-iteration-wave4-checkpoint-v2.tgz`, SHA
`9fd92e6447eadc9ba26f05c61bed5e9af549c19fb5d209a26c333d1837efb13d`.
It contains all948 original guards,429 migration attempts,two failure-retry
guards,418 verified label records, exact admission/final status snapshots and
operation evidence. Raw artifacts retain their original immutable pins. The
admission status snapshot is preserved separately this time, rather than only
its hash. Source/model weights and all final-test thresholds remain unchanged.

### A training coordinator is also ACTIVE — no competing preparation or launch

PID **2536611**, exec session **93205**, started
`2026-10-24T05:38:39.856827+00:00`. Its actual process was checked alive. State:
`ai/runs/policy-iteration-training-coordinator-v2/state.json`; log:
`ai/runs/policy-iteration-training-coordinator-v2.log`.
It is currently **waiting for complete labels**, with no preparation commands or
GPU jobs submitted. `coordinate-policy-iteration-training.py --execute` checks
readiness every60 seconds, bounded12h. Do not start another coordinator or manually
prepare/archive/build/launch the same training inputs while it is active.

Once all948 new shards plus60 pilot cases pass the strict coverage/identity/cap
checks, it invokes the existing data reducer, immutable data uploader, full source
builder and both launch dry runs. The complete packaged preflight must pass on
real complete inputs. Only then may it launch exactly two prescribedL4x1 jobs:
frozen/public representations, four fixed seeds each,3h timeouts. No local
training or changed hyperparameters. Each launch guard is archived immediately as
one HF file. Any failure/unknown result stops the pipeline with intermediates
preserved; no automatic retries or candidate promotion.

The partial real grid and a forged-complete grid were both rejected before any
preparation commands or submissions; a competing coordinator also failed before
creating outputs. All17 preflight-checked source overlays still match. Controls:
`strong/policy-iteration-training-coordinator-controls-v2.json`. Evidence:
`strong/policy-iteration-training-coordinator-evidence-v2.json`, revision
`e0f7d4b11b85dcb605129a13d7ff94d40cd714c6`, archive
`archives/policy-iteration-training-coordinator-evidence-v2.tgz`, SHA
`bb0a6f0593cee5bdf064a45abeae4674b85b5bfe58cfb221c000123463457a27`.

On a future explicit pause/no-new-jobs request, stop this local coordinator after
confirming its PID/command, so it cannot submit later. Do not interpret a stale
state file as a live process, or rerun blindly after a failure. If preparation
outputs or training guards exist, inspect/recover those exact stages first.

### A label/reference collector is ACTIVE — do not duplicate it

`harvest-policy-iteration-jobs.py` runs existing status/collection/summarization
commands every300 seconds, for at most12 hours. It cannot submit, cancel or
restart HF jobs. It stops on failed jobs, duplicate handles, changed collector
code or verification errors. It preserves status snapshots and command logs per
cycle. It stops successfully when both labels and the parent reference are fully
verified; that does not itself train or qualify a model.

Current process: **PID2476443**, exec session **82318**, started
`2026-10-24T05:28:50.781195+00:00`. State and logs:
`ai/runs/policy-iteration-harvest-recovered-v2/state.json` and
`ai/runs/policy-iteration-harvest-recovered-v2.log`.
Confirm its actual PID/command or poll session82318 before deciding it stopped.
Do not infer liveness from the state file alone. Do not run competing manual
collectors or modify its dependency files while it is active.

The earlier collector PID2404541/session19853 **ended with error as intended**
after observing two actual HF job failures. Its state/log remain preserved under
`ai/runs/policy-iteration-harvest-v2`; do not restart that directory. Its first
cycle verified **333/948 new shards**,12,112 root-mode pairs and **11,679,168
continuations including pilot**. The recovered collector then verified **395/948 new shards**,14,291 root-mode
pairs and **13,790,400 continuations**. Latest fresh effective-job snapshot at
`2026-10-24T05:40:04.630602+00:00`: **395 COMPLETED /328 RUNNING /225 SCHEDULING**,
no ERROR handles. It finished verifying all395 completions and is waiting between collection
cycles. Read current process state/results for later progress.

Latest label evidence: `strong/policy-iteration-labels-395-progress-evidence-v2.json`,
revision `bb85f3dacc9ed3119f41ca2fa493b630651d597e`, archive
`archives/policy-iteration-labels-395-progress-evidence-v2.tgz`, SHA
`8e406ed7c29713be2908f8bb74e701b93cc67c482ebd547ab95d4913c4b22120`.

### Fresh parent reference: search exposes large baseline weaknesses

**96 batches /5,760 fresh games independently verify**, with24 complete cells.
The latest partial diagnostic is `strong/policy-iteration-parent-reference-progress-96-v2.json`;
the latest full raw checkpoint below contains all96 batches /5,760 games.
All 128 two-player search_geo games across16 paired deals are now complete: parent win rate
**48.83%**,95% whole-deal bootstrap interval **38.28–59.77%**. This does not exclude
50% chance and is below the55% final point floor. Original/open62.5%,
original/sealed45.31%,Recharged/open40.63%,Recharged/sealed46.88%; all four marginal
intervals include chance. These are exploratory developmental results, not a
final-test pass/failure. The prior A260,2p heuristic and4p legacy deficits remain.

The complete3p search cell is considerably worse: **20.31% wins in192 games**,
95% whole-deal interval **14.58–26.56%**, entirely below one-third chance.
Original/open22.92%,original/sealed16.67%,Recharged/open22.92%,
Recharged/sealed18.75%. This additional deficit remains in the report; no cells
or rule combinations were dropped. The new training experiment still needs the
full fresh-game comparison to establish whether its corrections actually help.

Diagnostic: `strong/policy-iteration-parent-reference-progress-96-v2.json`.
Evidence: `strong/policy-iteration-parent-reference-96-evidence-v2.json`, revision
`44793a4ae5464d1c190e2484ebe6bdd42080efe1`, archive
`archives/policy-iteration-parent-reference-96-evidence-v2.tgz`, SHA
`88fc8eb6b4ccc065c216135d93788109766c4c6a27a15186d6b3b4d4f65eb03b`.
This compact archive includes all96 independently verified raw reference batches.
The previous92-batch partial-upload incident remains documented in the recovery
archive. Only4–6p search cells remain incomplete; use existing submitted handles.

### HF file limit fixed; two confirmed upload failures recovered

A checkpoint upload hit the model repository's **20,000-file HEAD limit**.
Thirteen duplicate evidence folders were packed into content-verified archives,
then each archive addition and duplicate-folder removal was committed atomically.
**8,158 file entries freed**;11,886 files remained at the retry admission snapshot.
All previous pinned Git revisions remain accessible and were retrieval-checked.
No raw job-output folders, model weights or source archives were removed.
The AMD benchmark folder used a different manifest format and was safely left
untouched; its attempted compaction stopped before any remote mutation.

Old checkpoint descriptors still resolve at their original pinned revisions.
`strong/*-compacted.json` records compact archive locations and checksums. Future
label/reference progress uploads now use one `.tgz` file via
`policy_iteration_evidence_archive.py`, instead of duplicating hundreds of files.
`model_info(...,files_metadata=True)` truncated its listing at10,000 entries;
use paginated `list_repo_tree` for true repository file counts.

Exactly two label jobs failed at their upload step and left no remote artifacts:

| Shard | Failed job | Exact retry |
| --- | --- | --- |
| 2p-11101-snapshot0-neural-0504 | 6adc221c1e112550ce7dc2c5 | 6adc41e8046eb82b1ecda91d |
| 5p-parent-economic-neural-0095 | 6adc1f98046eb82b1ecd9b84 | 6adc41e91e112550ce7dd171 |

Both failures were authoritatively ERROR with finished timestamps. Their logs
show the file-limit rejection; no simulation assertion preceded it. After
compaction, the two retries use the identical frozen source, world seeds,
root/action sets, output prefixes and fixed inference batches on proven CPU
Upgrade hardware,12h timeout and the existing conservative runtime multiplier.
**No live job was canceled or restarted.** These are two failure recoveries in
addition to the300 bounded queued-job migrations; the migration cap is unchanged.

Retry records/logs: `ai/runs/policy-iteration-labels-upload-retries-v2`.
`policy_iteration_label_attempts.py` resolves them after ordinary capacity
migration guards. All948 effective handles remain distinct; original guards are
unchanged. Ten negative controls reject live/ambiguous/same-ID/altered-source or
already-published retry cases. `retry-policy-iteration-upload-errors.py` is scoped
to these exact two failed jobs and now refuses resubmission. No missing launches.

Combined recovery archive descriptor:
`strong/policy-iteration-storage-recovery-evidence-v2.json`.
Revision `016d3bacfa6f7f679a259d20aae530c94204d93f`, archive
`archives/policy-iteration-storage-recovery-evidence-v2.tgz`, SHA
`b80eec1d50723be0faece3e2eb407ff763ea394881e3b7ac5525cf0ec36f4f47`. It saves all13
compaction proofs, retry guards/logs, collector controls/state and updated code.

Next: let the active collector harvest existing jobs and the existing coordinator
advance the prescribed full-data training pipeline. Do not duplicate either
process. Inspect their actual state if progress stops; training launches do not
need to wait for the collector's12h deadline if labels complete sooner. Parent full comparison still
requires108 verified shards; four trained candidate arms and the untouched final
strength gate remain. No final thresholds were weakened.

## Previous checkpoint: 312 verified label shards; fresh baseline weaknesses measured

This turn made **progress**: 312 label shards and 90 parent-reference batches now
verify, a bounded third CPU capacity wave completed, and the fresh baseline
results expose concrete remaining weaknesses. **No new gradients, trained
candidate, qualified model, final-test use or production change.** The goal
remains active.

### Labels and CPU capacity

**312/948 new shards verified**, 11,388 root-mode pairs and **10,986,048
continuations** including the reused pilot. The authoritative snapshot at
`2026-10-24T05:10:51.941074+00:00` is **320 COMPLETED /341 RUNNING /287 SCHEDULING**.
Eight completed jobs still need independent collection. Collector48591 (to312)
and all previous collectors finished. No local label collector is active.
Use `manage-policy-iteration-labels.py status`, then `collect`, then `summarize`.
All948 new shards plus60 pilot shards are still required before gradients.

The third CPU Upgrade wave is **complete: 300 total replacements**, within its
recorded cap. Its admission used15 verified full shards /640,512 continuations,
covering2–6 players, both continuation modes, all three behavior policies and both
opponents. Observed wall times including setup/upload were2,799–4,725 seconds.
All120 previous additional replacements had started, while430 original jobs were
waiting for requested hardware. The exact cross-hardware controls and original
conservative bounds remain unchanged: multiplier1.4454652311275429,12h timeouts,
25% headroom, identical frozen workers/worlds/actions/output prefixes.

The main wave launched117 replacements and safely skipped three originals that
had already started. A refreshed snapshot admitted the final three slots.
**303 attempt records =300 launched +3 skipped; no unresolved submissions.**
Every replaced original was confirmed canceled and never started; every original
guard is preserved. Skipped originals remain their effective handles. Both
launchers48109/63227 finished. Do not expand beyond300 from this admission.
New decision: `strong/policy-iteration-cpu-upgrade-wave3-admission-v2.json`.

### Parent reference grid

Both original runtime probes remain **COMPLETED/verified**:2p job
`6adc2d29046eb82b1ecda152` (8 games,146.19s),6p job
`6adc2d2a1e112550ce7dc710` (24 games,2,786.69s). These32 games establish runtime only.
All108 parent reference jobs are already submitted with9h timeouts on CPU Upgrade.
Plan: `strong/policy-iteration-development-plans-v2/parent.json`, SHA
`080893449fde758e1820bf2fe5557dcaf4772343e2395d2adbf788bad840658b`.
Do not resubmit probes or grid jobs.

At `2026-10-24T05:10:32.063653+00:00`, parent-reference jobs were
**92 COMPLETED /16 RUNNING**, plus the two completed runtime probes.
**90 batches /5,504 fresh games independently verify**. Collectors64829/31476
finished; two additional completed batches await collection. Every remaining
batch is against search_geo. The full arm requires108 batches /6,720 games.

The diagnostic `strong/policy-iteration-parent-reference-progress-90-v2.json`
revalidates all raw hashes, guards and games. It summarizes only the22 cells with
all16 independent deals; all five search cells remain incomplete in this snapshot.
All seats and four edition/auction combinations remain paired. Whole-deal
bootstrap intervals are exploratory, not simultaneous guarantees. The following
fresh parent point estimates fall below the unchanged final-protocol floors:

| Cell | Parent win rate | 95% deal-bootstrap interval | Final floor, orientation only |
| --- | --- | --- | --- |
| 2p heuristic | 73.44% | 64.06–83.59% | 77.5% |
| 4p legacy | 88.28% | 83.59–92.97% | 90% |
| 3p independent A260 | 34.38% | 26.04–42.71% | 40% |

The A260 interval includes random-seat chance (one third). Fourteen rule-specific
intervals across the complete cells do not exclude chance; all remain in the
report. This is developmental diagnosis, **not a final-test failure or pass**.
No thresholds changed and final reserved deals remain unused. All four future
trained candidates still require their own runtime probes and full matching grids.

New evidence descriptor: `strong/policy-iteration-wave3-checkpoint-v2.json`.
Private model-repo revision **981a5dbf0fc8368ef503bdc8778771ee891ff25c**, prefix
`runs/policy-iteration-wave3-checkpoint-v2`, manifest SHA
`8d8b59e547a719ffd1daaf94888dda9917fad7e3bc9180e69e710233b3230915`.
It archives all948 original label guards,303 migration attempts,312 verified label
records with immutable raw pins, all110 reference/probe handles,90 raw verified
reference batches, both partial diagnostics and the capacity decision/code.
Older launch and AMD evidence remain available below. No local HF launcher or
collector from this checkpoint remains active; HF jobs continue remotely.

Next collection commands:

```sh
ai/.venv/bin/python ai/strong/manage-policy-iteration-labels.py status
ai/.venv/bin/python ai/strong/manage-policy-iteration-labels.py collect
ai/.venv/bin/python ai/strong/manage-policy-iteration-labels.py summarize
ai/.venv/bin/python ai/strong/manage-policy-iteration-development.py status
ai/.venv/bin/python ai/strong/manage-policy-iteration-development-grid.py collect parent
```

### AMD8840U architecture benchmark

This used the four already archived **synthetic, untrained** configurations,
not newly trained candidates. The current frozen development source supplied
all engine/worker/encoder/inference files byte-for-byte. Four standalone archives
passed local package smoke checks and then all2,553 public fixtures each on
`ssh minipc`, from an unrelated working directory. No target software installation
or production routing was changed. The target load was low before the probe.

Independent local collection verified **all10,212 moves exactly match the frozen
runtime**, with maximum value difference **0**. Every move was legal; request,
revision, schema and player-value ordering were checked. Actual CPU: AMD Ryzen7
8840U. Timings are sequential engineering measurements, not statistical rankings.

| Untrained configuration | Warm median | Warm p95 | First request |
| --- | --- | --- | --- |
| frozen-0 | 4.39ms | 6.98ms | 217.62ms |
| frozen-1 | 4.49ms | 7.18ms | 221.52ms |
| public-0 | 5.95ms | 8.71ms | 247.86ms |
| public-1 | 5.94ms | 8.97ms | 253.70ms |

The richer architecture's measured cost looks practical on this CPU. **The actual
trained candidate still needs its own exact package benchmark.** This says
nothing about strength or browser performance. Report:
`strong/policy-iteration-8840u-results-v2.json`; scripts:
`prepare-policy-iteration-8840u.py`, `launch-policy-iteration-8840u.py`,
`collect-policy-iteration-8840u.py`, `archive-policy-iteration-8840u.py`.

Local preparation `ai/runs/policy-iteration-8840u-prepared-v2`; recovered raw results
`ai/runs/policy-iteration-8840u-results-v2`. Remote directory
`/home/coyotte508/powergrid-ai-policy-iteration-architecture-v2` completed;
launcher86400 and collector67581 finished. Its recorded PID no longer exists.
**No target benchmark remains active.** Do not restart the completed benchmark.

Benchmark evidence: revision **d4af1c8d92a0ff1f42835c0e48a382113337836f**, prefix
`runs/policy-iteration-8840u-evidence-v2`, manifest SHA
`19215960a4d5bad56da7baf7a2fa310ebfe28ee6d6d0da78d1596ab412a7bc76`. Exact standalone packages, raw responses,
timings, local checks and preparation/collection code are preserved there.

### Next work

1. Refresh/collect labels and parent reference completions, then summarize labels.
   All local launchers/collectors from this turn are finished; HF jobs remain live.
2. Once all948 new labels and60 reused pilot shards verify, prepare/archive the
   full compact data bundle, build the admitted HF training source, and launch the
   two four-seedL4 training jobs. No incomplete-data shortcut.
3. Independently verify both trained ensembles per representation, launch their
   endpoint probes and matching108-shard grids, and compare all33,600 fresh games.
4. Diagnose every adverse result, benchmark the exact selected trained package
   on AMD8840U, and satisfy the unchanged final gate. Parent preservation,
   synthetic timing and raw label volume do not establish strong play.

## Previous checkpoint: second CPU wave and complete evaluation tooling

This turn made **progress**. The first two CPU Upgrade full shards independently
verified, allowing a bounded second hardware wave. The training-output collector,
full development-grid launcher and all-arm comparison code are now implemented
and their contract tests pass. **No new gradients or strength-qualified model.**
The old parent and old rejected candidates remain unqualified; no production
change or final-test use occurred.

### Verified labels and capacity

Final snapshot at `2026-10-24T04:34:16.621265+00:00`: **219 COMPLETED /243 RUNNING /
486 SCHEDULING** across948 unique effective job handles. All219 completed shards
independently verified: **8,254 root-mode pairs /7,988,544 continuations**, including
the reused pilot. The complete manifest is still false; all948 new shard
identities plus60 reused pilot shards are required before gradients.

The second migration launcher **session78951 finished successfully**:120 new
replacements,180 total. All180 originals were confirmed canceled without starting.
At the snapshot the CPU Upgrade tier had **175 RUNNING /5 COMPLETED**. All five
completed upgrade shards verify, totaling96,000 continuations across4p/5p/6p.
No pending cancellation or unknown submission intent remains.

Collectors89101 (to195),46865 (to207) and46432 (to219) all finished successfully;
**no local collector or submission launcher is active**. Their logs are
`ai/runs/policy-iteration-labels-collect-195-v2.log`, `...collect-207-v2.log` and
`...collect-219-v2.log`. Use `manage-policy-iteration-labels.py status` to resolve
effective replacement handles; do not reuse historical canceled originals.

The6p runtime probe remains **RUNNING**; the last persisted development snapshot
is `2026-10-24T04:33:07.944210+00:00`, with2p COMPLETED/verified and6p RUNNING. No complete
parent-grid plan or full parent/candidate development job has been admitted.

Immutable checkpoint: private model repo revision **969786e971f9f1b84f71eb378a66467d9c03aa2d**,
prefix `runs/policy-iteration-wave2-checkpoint-v2`, manifest SHA
`cebd7f3828aef896747a3137d210ad0da6718cf76ca06eeadeb2d6512b88029b`. It includes all948 original guards,180 replacement
attempts,219 verified label records, the two development guards, verified2p raw
probe output, the full-shard capacity decision, new collector/grid/comparison
code and contract logs. Descriptor: `strong/policy-iteration-wave2-checkpoint-v2.json`.
Local archive/upload session45934 finished; manifest was downloaded by revision
and hash-checked. This supersedes earlier159/136-shard evidence snapshots.

`policy-iteration-cpu-upgrade-wave2-admission-v2.json` records the first two full
CPU Upgrade shards: `6p-11101-economic-neural-0018` and
`6p-11102-snapshot0-neural-0018`, **34,176 continuations** in total. Full job times,
including setup/upload, were **2,799.335s and2,896.730s**. Both passed the unchanged
independent raw verifier. Original jobs had never started and were confirmed
canceled. The earlier2p/6p × both-mode hardware controls remain exact.

This small full-shard runtime sample supports one bounded expansion; it does not
prove every shard runs this quickly. The existing conservative per-shard
estimate, hardware multiplier1.4454652311275429,12h timeout and25% headroom remain.
The maximum bound is31,136s. New capacity is limited to **180 total replacements**
(60 first wave plus at most120 second wave). No further expansion is admitted by
this decision. The worker source, inference batches, root selections, worlds,
policy choices and artifact prefixes are unchanged.

Launcher: `migrate-policy-iteration-labels-cpu.py --wave2 --limit 120 --execute`.
It persists exclusive cancellation/replacement intents, checks original status
again, waits for confirmed cancellation, and rejects an original that starts
during cancellation. A partial/unknown intent must be reconciled, never blindly
retried. Its final session state is in the snapshot above.

### Training collection now implemented

`collect-policy-iteration-training.py --head-type frozen|public` requires the
complete dataset and admitted training source before touching outputs. After a
COMPLETED HF job, it pins one immutable artifact revision, verifies the archived
worker source and recovers the exact data bundle. Its independent verifier:

- checks all120 epochs/6,120 updates per seed and the earliest minimum validation
  regret checkpoint, retaining all four prescribed seeds;
- checks exact parent tensors and source/design/data identities in best/latest
  checkpoints, plus optimizer step counts;
- rebuilds both ensembles from the exact four individual checkpoints and checks
  every stored tensor and float64 export provenance;
- reruns2,553 real serving fixtures and17,280 cached positions, including exact
  native/ONNX choices, legality, parent fallback/value preservation;
- recomputes exported ensemble calibration and creates both development pins
  only after verification.

These checks ran on synthetic contract fixtures only: **no actual new trained
output exists yet**, so full training-collector integration remains pending the
HF training jobs. The collector refuses the current incomplete label grid before
creating output/pin directories. `policy-iteration-collection-grid-controls-v2.json`
records five passing contract tests and this negative admission check. No local
gradients were run.

### Complete fresh-game execution and comparison tooling

The frozen development source/protocol remain unchanged. New local orchestration:

- `manage-policy-iteration-development-grid.py plan parent` builds an immutable
  108-shard plan only after the exact2p and6p endpoint probes verify.
- `... launch parent` is a dry run; add `--execute` to submit. `--limit` can bound
  submissions. Each existing guard must match the plan before it is skipped;
  unknown submissions halt the run. Every arm has16 deals in all27 cells,
  **6,720 games**. The same commands accept each prescribed candidate key once
  its training/export pin and both runtime probes exist.
- After `manage-policy-iteration-development.py status`, use the grid manager's
  `collect KEY` to independently collect completed shards with four local workers.
- `compare-policy-iteration-development.py --arm parent --output NEW_PATH` can
  summarize a complete parent arm. Omit `--arm` only when all five arms complete:
  **33,600 games**, absolute cell/rule results, four candidate-minus-parent
  contrasts, two representation contrasts and two disagreement-penalty contrasts.
  Whole deals are resampling units; every adverse rule/count/opponent cell remains.
  Marginal intervals are exploratory. Incomplete arms fail before report creation.

The grid/statistics tests verify exact16-deal coverage and preserve a deliberately
negative rule slice even when the overall difference is zero. Real full-grid
aggregation has not run yet. All frozen source additions still match their hashes.

### Next actions

1. Refresh label status and collect new completions; summarize after collection.
   The previous migration and collectors have all finished; do not repeat their submissions.
2. Inspect/collect existing6p probe **6adc2d2a1e112550ce7dc710**; never relaunch it
   merely because evaluator logs are quiet.2p **6adc2d29046eb82b1ecda152** is already
   complete/verified. Once both verify, prepare, review and launch the108 parent
   shards using the new grid manager. Runtime admission may require execution
   repartitioning; preserve every deal and full search/game horizon.
3. Once all labels verify, prepare/archive the compact training bundle, build the
   full-data source, and launch the two four-seedL4 jobs. Independently collect
   them with the new collector, then execute all four prescribed development arms.
4. Diagnose every adverse result, benchmark the exact selected package on AMD8840U,
   and pass the unchanged reserved final gate. No threshold relaxation or parent
   compatibility shortcut.

## Previous checkpoint: fresh development runner verified and HF probes running

This goal turn made **progress**. Verified labels reached **159 new shards /
6,448,512 continuations including the reused pilot**. The next complete-game
comparison is fixed and its actual packaged runner passed160 plumbing games.
No new gradients or trained candidate; old candidates remain unqualified. No
production change, final-test use or AI publication.

At `2026-10-24T04:06:03.975032+00:00`, the948 effective label handles were
**159 COMPLETED /129 RUNNING /660 SCHEDULING**, with all60 CPU Upgrade replacements
still RUNNING. Their first full shards have not yet verified, so the migration
has not expanded. **Local collector session57232 finished successfully**, verifying23 newly
completed shards; log `ai/runs/policy-iteration-labels-collect-159-v2.log`.
Earlier collectors65807 (to130) and46472 (to136) are also finished. No local
collector or submission launcher is active. The manifest now includes all159.
Their immutable progress archive is model-repo revision
`e781647d9739303cd876a9cb95672979d5eb14a8`, prefix
`runs/policy-iteration-labels-159-progress-evidence-v2`, manifest SHA
`8a1723722d5827bbd2097c8845651dddbe819de61d90f0ef4186fb7abff91445`.

### Fresh full-game evaluation

`strong/policy-iteration-development-protocol-v2.json` fixes five arms: parent,
`frozen-0`, `frozen-1`, `public-0`, `public-1`. Each has27 opponent/count cells,
16 independent deals per cell, all seats and all four edition/auction rules:
**6,720 games per arm /33,600 total**. The independent baselines and their
settings remain the earlier fixed legacy, heuristic, economic, rush and
search_geo opponents, plus3p A260 and2p economic_capacity_v1. All adverse cells
must remain visible. Comparison/aggregation across all arms still needs its
manager entry point; the actual execution and independent collector are ready.

Fresh development namespace: `policy-iteration-development-v2-{players}p`.
Runtime probes use `policy-iteration-runtime-v2-{players}p`; local synthetic
checks use `policy-iteration-plumbing-v2-{players}p`, with nonzero deal offset4.
Neither training deals nor reserved final deals are used. Four ensembles are
prespecified; individual seeds cannot be selected instead.

The new wrapper admits real candidates only with independently verified training,
all four prescribed seeds, exact architecture/design/data hashes and complete
native/export checks. Synthetic weights are explicitly local plumbing only and
cannot be uploaded as development or smoke candidates. The parent is pinned
exactly to the existing10102 derivative.

Accepted source:

- Dataset revision `a393d0fa83d9fee8a27a876a217fe97dfea03ff8`.
- Archive `strong-source-policy-iteration-development-20261024-v2.tgz`.
- SHA `c020987f3a05a2c0116dfd52498139f6bb7480e1721ca058caf9771f94d970ce`.
- All1,434 base files unchanged; five added files. Do not edit those frozen additions.
- Accepted scratch: `ai/runs/policy-iteration-development-source-v3`.

The first scratch `...source-v2` is preserved. Its historical population verifier
assumed deal offset0 and rejected a correctly generated offset4 game batch.
The new wrapper independently checks the actual offset and exact deal/seat/rule
identities without modifying the frozen base checker. All8 terminal records of
that first batch exactly match the accepted rerun. This was an integration
check failure, not a game-engine or label-data change.

The accepted preflight ran the actual wrapper, serving interface and evaluator
for all five model routes at2p/6p, all rules: **160 full games**, plus2,553 serving
fixtures per route/count. Twelve corrupted-report cases are rejected, including
missing/duplicated games, wrong model/deal/offset, altered credit, truncations,
wrong opponent/workers and seed-namespace mixing. Bootstrap syntax and refusal
to launch a full screen without runtime probes or an unverified candidate were
also checked. Gradient behavior and model strength are not established by this.

### HF runtime probes and exact next actions

Both are CPU Upgrade jobs with4h timeouts, using the original pinned parent:

- **2p: `6adc2d29046eb82b1ecda152` COMPLETED and independently verified**.
  Eight full games,146.1888seconds,369 search decisions /30,496 search evaluations,
  zero game or search caps. Raw revision `832e7af1d7404838b2f4075392a02046a3df1c89`,
  prefix `runs/policy-iteration-development-v2-smoke-parent-2p-search_geo-0-1`.
- **6p: `6adc2d2a1e112550ce7dc710` RUNNING** at04:13:39UTC. Do not restart it.

`strong/policy-iteration-development-runtime-probes-v2.json` retains the complete
verified2p record. These probes measure runtime, not strength. Both endpoint
probes must independently verify before the parent reference grid is admitted.
The launcher projects four whole deals using2x the slower endpoint plus120s and
25% timeout headroom, on the same hardware;12h maximum. If admission fails,
partition execution with verified parity while preserving every deal and horizon.
No full parent-development batch or trained-candidate job has launched yet.

1. Refresh exact label handles, collect further completions and run the label
   manager `summarize`. No local collector is currently active. Do not expand CPU Upgrade migration
   before its actual full shards verify.
2. Inspect/collect the existing6p probe with
   `ai/.venv/bin/python ai/strong/manage-policy-iteration-development.py collect parent 6 search_geo 0 1 --mode smoke`.
   The2p probe is complete. Never resubmit either merely because it is quiet.
3. After both probes verify, the same manager can dry-run and launch parent
   reference shards: `launch parent N OPPONENT START END`, adding `--execute`
   only for submission. Use all27 protocol cells and all16 deals, in four-deal
   pieces. Each launch has an exclusive guard. Freeze/review a bulk launch plan
   before submitting the108 parent shards; no such bulk launcher exists yet.
4. Label completion still precedes the compact training bundle and HF gradients.
   Use the existing full-data source builder and two-representation trainer;
   then independently collect/check all four trained ensembles and create their
   development pins. The new training-output collector is still to be implemented.
5. Complete the actual fresh development comparisons, diagnose every adverse
   result, benchmark the exact candidate on AMD8840U and satisfy the unchanged
   final protocol. Parent compatibility alone is insufficient.

Preparation evidence is archived privately at model-repo revision
**8d124c173a41660b29f40f24b73d528f4676e45d**, prefix
`runs/policy-iteration-development-preparation-evidence-v2`, manifest SHA
`daf39c4f637dd9ab8a414770b4f35fac04f059e1048bf00b5ee3a7a6eb716f4f`.
It includes both probe guards, raw passed/failed plumbing cases, the exact
synthetic fixtures, source/controls, and136 verified label records. Its probe
status was captured at04:02:30UTC, when both jobs were running; the newer runtime
probe report and live HF status supersede that historical snapshot.

## Previous checkpoint: full fleet submitted; second CPU tier verified

This continuation made **progress**: all 948 original label jobs were submitted
and archived, more outputs were independently verified, the same workload was
validated on another CPU tier, and the HF training package passed isolated code
checks. **No new gradients, qualified model, production changes, or reserved
final-test use.** The goal remains active.

### Label jobs and hardware capacity

The remaining-wave launcher (old session62283) finished successfully. **All 948
original guards are `launched`, with unique handles and exact planned shard IDs**.
There is no active original submission launcher. Complete launch evidence is
model-repo revision `4a0cedfcb7cd7ac6e4b0ec0b72b57109fb82ee7a`, prefix
`runs/policy-iteration-labels-complete-launch-evidence-v2`.

All 60 first-wave shards plus 59 subsequent shards are independently verified:
**119/948 new shards; 5,281 root-mode pairs; 5,113,344 continuations including the
705,408 reused pilot continuations**. No caps were accepted. This remains partial
training data, not strength evidence. The local26-shard and33-shard collectors both finished successfully;
no collector remains active at this checkpoint.
The119-shard checkpoint is archived at model-repo revision
`a6c91fba94065f5e07bde6f51727d0be02b94831`, prefix
`runs/policy-iteration-labels-119-progress-evidence-v2`, manifest SHA
`9d40b2e4706383490053b98eef9d2839e719851e6b9c81bc5a6b952939f55d55`.

At `2026-10-24T03:31:46.448219+00:00`, the original fleet had 86 COMPLETED,
69 RUNNING and 793 SCHEDULING. Queued jobs explicitly reported “Waiting for
requested hardware to become available”. This establishes hardware waiting,
not an account quota or a guarantee about queue timeouts. The newer effective
fleet snapshot in `strong/policy-iteration-labels-status-v2.json` takes priority.

CPU Upgrade profiling job **6adc24af046eb82b1ecd9f1f** COMPLETED and was independently
verified. It used the exact frozen inference-profile source and the same 3,072
serial/concurrent continuations, plus 2,553 microbenchmark positions. Every
recorded terminal result and policy-choice transcript matches the original
CPU Performance workload. Concurrent runtime was **1.08479x** overall, worst
case **1.15637x**. The observed cgroup quota was 8 CPUs / 32GB, despite host
CPU/affinity reporting64. Do not infer usable cores from affinity alone.

A bounded first batch of up to60 queued shards was moved to CPU Upgrade.
`migrate-policy-iteration-labels-cpu.py` rechecks each original handle immediately
before cancellation and requires an authoritative canceled terminal state before
submitting its replacement. Originals that are no longer queued are skipped.
Original guards are never overwritten. Exact attempts are in
`ai/runs/policy-iteration-labels-cpu-upgrade-v2/`; the manager resolves those
explicit attempts for status and collection. The data, engine, source, action
choices and artifact prefixes remain unchanged. Timeout is12h; admission applies
1.25x the worst observed hardware slowdown to the already-conservative shard
bound and retains25% headroom. First hardware wave is capped at60 pending actual
full-shard verification; do not expand it blindly or relaunch ambiguous attempts.

The migration launcher (session66785) is finished: **60 replacements submitted,
60 original cancellations confirmed, zero original jobs had started**. At
`2026-10-24T03:39:57.560773+00:00`, all60 replacements were RUNNING. The whole
effective fleet had **119 COMPLETED / 129 RUNNING / 700 SCHEDULING**, no failed
handles. The latest33 completed shards were independently verified by the now
finished session37663, log `ai/runs/policy-iteration-labels-collect-119-v2.log`.
No collector is active. Do not resubmit the original948 or the completed
60-replacement wave. The first full CPU Upgrade shards are not verified yet.

Hardware profile raw revision: `aac063cb7d805345d3b6f9780800aea2066688aa`, prefix
`runs/policy-iteration-cpu-upgrade-profile-v2`. The complete capacity checkpoint
is model-repo revision **1d6850b531d5586a4bd75cce3dad11f6d9f7dd44**, prefix
`runs/policy-iteration-capacity-checkpoint-v2`, manifest SHA
`0b86051f4c4b3f1e7f40f6e128318ab42a3528426e3b67c2810205f45d736c4a`.
It preserves all60 attempt guards,86 verified-shard pins, effective fleet status,
raw hardware comparison, source-package code/checks, and failed/successful test
logs. It is preparation/throughput evidence, not model qualification.

Local verifier profiling rechecked existing2p/4p/6p shards unchanged. Serial
wall times were17.92/41.29/55.99seconds; loading/scanning the full root set took
8–9seconds each. Four collector workers remain unchanged. Verification has not
been shown to be the bottleneck; no speculative indexing/cache rewrite was made.

All 948 new shards plus all60 reused pilot shards must verify before gradients.
No full compact training bundle exists yet. All historical failed/replaced job
identities remain preserved; never retry a handle just because logs are quiet.

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
and strict member assembly; the gradient loop has **not** run. A pinned full-data HF training source and data bundle remain pending. The
source builder, data recovery, admission and two-representation launcher are now
implemented and code-checked; they reject the current incomplete label grid. The source builder includes the explicit
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

### Training job package and ordered continuation

`build-policy-iteration-training-source.py --code-only` passed in the isolated
scratch tree `ai/runs/policy-iteration-training-source-code-v3`, preserving all
1,434 frozen base files and adding17 explicit files. It ran four model tests,
all four synthetic native/ONNX configurations on2,553 fixtures +17,280 cached
positions each, then three training-contract tests. The earlier failed scratch
`...source-code-v2` is preserved: one test consumed synthetic export fixtures
before they were created. The order is fixed both locally and in the HF
bootstrap. These are code/inference checks; the gradient loop remains unexecuted.

The package recovers the complete compact data from immutable HF pins and
revalidates it before training. The two jobs will each train all four prescribed
seeds, on `l4x1`, with a3h timeout. The richer model and control remain separate;
all four ensemble candidates require evaluation. The package refuses partial
labels, a code-only source check or drifted source/data/design hashes. Its shell
bootstrap and embedded Python syntax were checked; original/skipped/canceled
attempt resolution and rejection of unresolved/live originals were exercised.
All frozen label overlays and the final protocol hash remain unchanged.

1. Inspect effective fleet status with `manage-policy-iteration-labels.py status`;
   collect only COMPLETED jobs and `summarize`. Read exact guards/logs first;
   do not start another collector while locked.
2. Independently verify completed CPU Upgrade shards before considering a larger
   migration. Preserve the cancellation evidence, original handles and immutable
   raw-data pins. Do not cancel running jobs to fill the alternative pool.
3. Once all948 new shards verify: run `prepare-policy-iteration-training-data.py`,
   then `archive-policy-iteration-training-data.py`. Never synthesize a complete
   manifest or use partial data for this fixed experiment.
4. Run `build-policy-iteration-training-source.py` without `--code-only`; it
   validates the real bundle and entire isolated package before uploading a
   source archive. Then dry-run and execute `launch-policy-iteration-training.py
   --head-type frozen` and `--head-type public` (add `--execute` only for launch).
   Guards prevent duplicate submissions; reconcile any unknown outcome.
5. Independently collect/check every trained ensemble and run fresh whole-game
   development evaluation. Actual8840U measurement and the untouched final
   gate remain required. Conditional training targets do not establish strength.

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
