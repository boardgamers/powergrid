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

## Latest checkpoint: automatic collection, search weakness and storage recovery

Previous goal turn: **progress** (312 verified shards,90 reference batches and
bounded CPU expansion saved). This turn also made **progress**: more verified
labels, the complete2p search reference, a bounded collector, and recovery from
an actual HF repository file-count limit. The goal remains active; no new
model gradients, final-test use, model qualification or production changes.

### A local collector is ACTIVE — do not start another one

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
continuations including pilot**. Latest fresh effective-job snapshot at
`2026-10-24T05:29:17.154498+00:00`: **364 COMPLETED /332 RUNNING /252 SCHEDULING**,
no unresolved ERROR handles. The recovered collector is verifying those new
completions. Read its current state/results for later progress.

333-shard evidence: `strong/policy-iteration-labels-333-progress-evidence-v2.json`,
private HF revision `03231c902048a5c91fe12424142758d43453bba2`, archive
`archives/policy-iteration-labels-333-progress-evidence-v2.tgz`, SHA
`ee244e73671c5877db79c01fe87e9ff7132e2fb3607a65cbfa308e1e126097f4`.

### Fresh parent reference: two-player search is not convincingly beaten

**92 batches /5,568 fresh games independently verify**, with23 complete cells.
All 128 two-player search_geo games across16 paired deals are now complete: parent win rate
**48.83%**,95% whole-deal bootstrap interval **38.28–59.77%**. This does not exclude
50% chance and is below the55% final point floor. Original/open62.5%,
original/sealed45.31%,Recharged/open40.63%,Recharged/sealed46.88%; all four marginal
intervals include chance. These are exploratory developmental results, not a
final-test pass/failure. The prior A260,2p heuristic and4p legacy deficits remain.

Diagnostic: `strong/policy-iteration-parent-reference-progress-92-v2.json`.
Evidence: `strong/policy-iteration-parent-reference-92-evidence-v2.json`, revision
`3df972b391728184ff7d3921cae465c0616336a1`, archive
`archives/policy-iteration-parent-reference-92-evidence-v2.tgz`, SHA
`266be50f184746b8ce44545e74bd28f909e5d28039b0e893d166c6c28d48de39`.
It contains all972 files of the full local92-batch checkpoint. Its initial
folder upload was partial; the complete compact archive is verified.
Parent3–6p search cells remain incomplete; collect only existing submitted handles.

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

Next: let the active collector harvest existing jobs. Once all948 new labels and
60 reused pilot shards verify, build/archive the full compact training bundle and
admitted frozen source, then launch the two four-seedL4 jobs. Do not wait for the
collector's12h deadline if labels complete sooner. Parent full comparison still
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
