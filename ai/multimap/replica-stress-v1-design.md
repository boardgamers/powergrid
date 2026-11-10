# Frozen replica population stress study v1

**Final status:** both original panels completed; joint external integrity and all
48 fixed saved-outcome replays passed. Nine requested job-hours were used, without
recovery, selection, promotion or deployment. See the
[final report](replica-stress-results-v1.md), [full results](replica-stress-results-v1.json)
and [verified private archive](replica-stress-audit-v1.json). The frozen scientific
design below is unchanged; execution updates distinguish historical checkpoints
from the final state.

## Authorization and purpose

This is a **new evaluation-only study**, separately authorized after completion of
expert-replicas-v1, with a maximum of **12 aggregate requested remote job-hours**.
It does not extend that completed study's exhausted authorization. Both audited
replica checkpoints remain fixed. No learning, checkpoint reselection, winner
selection, promotion, BGS publication or deployment is authorized here.

The question is whether both independently trained policies' gains persist under
stronger and mixed opponent populations, using more independent deal roots and
common comparisons against the frozen PPO2 policy. Teacher-v2 confirmation gains
do not answer that question. Both panels and both replicas must remain in the
report, including any incomplete or failed panel and all adverse subgroups.

Implementation is versioned separately from stress-v1 and expert-replicas-v1.
All old serving modules, protocols, launchers, source guards and auditors remain
unchanged. The common base at design time is Git
`6a7cdc6b46d497065a0f73aaf9ca465ce0d2a874`.

## Fixed policies and scope

The model repository is private `coyotte508/powergrid-ai-multimap-v1`.

| Role                            | Immutable revision                         | Selected update | SHA-256                                                            |
| ------------------------------- | ------------------------------------------ | --------------: | ------------------------------------------------------------------ |
| Focal replica1                  | `ebb354b5c2206376fb65ee7d8e19e2809bb72a70` |              24 | `7918c5ceec29ee181721eaaa3a38f63fd94cf0248c34d192e0b3f65960c729e5` |
| Focal replica2                  | `9a116e30b14eb32b48603475f5036d510177f1b9` |              32 | `89d03f5b23fd6d088e175d32ff9c90ff88bd947f7e8b17d508b1b2f641a037fa` |
| Focal control PPO2              | `af87f0b46382e4f06d420f339fd1a65a4ba9ef45` |              12 | `3d2ffeb02feb17462385ff2a4d2ccd930e58bb445bf97df386b7eef5fce9dc91` |
| Opponent-only original expert24 | `39976d5e864638fe73d241061bc4dfd4b46ce0a4` |              24 | `1377fc2112c3b9ff3c2a20078ed341305b2a9006a4f7a1df413eeb0b509e6fbd` |

Replica paths are
`runs/multimap-expert-replicas-20261109-v1-continuation-r{1,2}/expert/best.pt`.
Original expert24 is at
`runs/multimap-expert-ppo-20261102-v2-r1/expert/best.pt`.
PPO2 is at `runs/multimap-ppo-20261102-replica-2/ppo/best.pt`.
The complete unchanged PPO0/1/2 pool is pinned by `candidate-pool-v1.json`, SHA
`a4f5d80966d9dd5b7af712459dffea255590eeb158b3a8e73cb66b0045d29a4b`.

An offline check of all six retained checkpoints identified a provenance detail:
PPO0 predates replica-aware training helpers. Its complete saved configuration
has historical `ppo.py` and `rollout.py` hashes, not the current trainer hashes.
All 11 historical source hashes are independently pinned to original Git
`a3b492b650dec51c34b6f9322d87088b1e863f0e`; only those two nonserving differences
are permitted. Current serving/runtime configuration remains separate from the
historical saved checkpoint configuration, and both are checked in full. No
weights, inference source or old loader guards are changed to accommodate this.

All three expert-family models use the unchanged v2 Auction/Building inputs,
normalized prior, bound16 residual and fixed-v2 other phases. PPO0/1/2 retain
their v1 inputs/prior/fixed phases. The historical exact Germany reference stays
Germany-only, controlling all of its own phases. It is never queried for labels.
Replica checkpoints are never nonfocal opponents; original expert24 is never a
focal arm. Neither replica is disguised as the original expert model.

Maps: **Germany, USA, France, UK & Ireland**. Each has players 2–6,
Original/Recharged, open/sealed (`fastBid=false/true`): 80 cells. Italy/Benelux,
unsupported setup options and all reserved final roots are excluded.

## Common fresh panels and counts

Namespace: `pg-multimap-replica-stress-20261109-v1`.
Default run group: `multimap-replica-stress-20261109-v1`.
The seed is `namespace[:smoke]:panel:cell:deal`.

There are **eight fresh deals per cell**, with every focal seat and all three
focal policies (`replica1`, `replica2`, `ppo2`). Roots and opponent assignments
match across all three arms within a panel. Panel names remain part of the seed,
so strong and mixed panels have **disjoint**, not shared, roots.

-   640 independent roots per panel; 1,280 across both panels.
-   2,560 games per focal arm per panel.
-   7,680 games per panel; **15,360 games total**.
-   One shared PPO2 observation set serves both paired contrasts. It is played and
    counted once, not duplicated as independent evidence.

The namespace is disjoint from all training, selection, confirmation, previous
stress, diagnostic and reserved-final namespaces. These are frozen-policy
comparisons, not independent new training replicas.

### Strong population

All nonfocal seats use the historical exact reference on Germany, and original
expert24 on the other three maps. Original expert24 is stronger available
opposition, not independent algorithmic diversity. Unlike the old study's
expert24 focal arm, replica-versus-expert24 games are heterogeneous: **the old
homogeneous self-play neutrality assertion must not be imposed**.

### Mixed population

Cell ordinal preserves the original 80-cell order:

```text
ci = mapIndex*20 + (players-2)*4 + variantIndex*2 + int(fastBid)
ordinal = (seat-focalSeat+players)%players - 1
i = ci + deal + ordinal
```

Even `i` routes original expert24. Odd `i` routes
`weakPool[(i//2)%len(weakPool)]`, where the pool is
`[ppo0, ppo1, ppo2, teacherV2]`, appending `reference` only on Germany.

Use the **actual deal index 0–7, not `deal % 4`**. This is the eight-deal extension
of the old assignment formula, not a claim that the old four-lineup distribution
is repeated unchanged. All three focal arms have identical lineups and all-seat
rotations for each root. It is not uniform sampling of all possible populations.

## Predeclared analysis

Four primary comparisons: replica1 minus PPO2 and replica2 minus PPO2, separately
for strong and mixed. For each comparison, first take paired credit differences
for the same root/seat, average all seats within each deal, then the eight deals
within each cell, then weight all 80 cells equally. Credit is shared for ties;
this is not a pooled game win rate.

```text
SE = sqrt(sum_c(sample_variance_ddof1(deal_differences_c)/8))/80
```

Report exploratory normal 95% intervals (`z=1.96`) and four-primary Bonferroni
98.75% individual intervals (`z=2.4977054744123737`). The shared control induces
dependence between contrasts; Bonferroni does not require their independence.
Normal coverage remains approximate. In mixed panels, deterministic lineup
changes contribute between-lineup mean variation, making this variance estimate
conservative in expectation, not unbiased for the fixed-schedule mean.

Retain per-map, player-count, rule, map/count, full-cell and strong-opponent-
occupancy subgroups, with unadjusted exploratory intervals and all adverse cells.
Explicit watchpoints include Germany 2-player Recharged/sealed, USA 3-player
Original/sealed and Recharged/sealed, and replica2's prior USA 2-player marginal.
These use a different comparator from the earlier teacher confirmation.

For occupancy subgroups, each included cell's point estimate is its mean over
its `K` selected deals. Variance uses all eight scheduled root positions with
fixed `8/K` weights on selected observations and analytical zero contributions
for nonmembership. These zeros are not played outcomes or fabricated losses.
Report `selectedDeals` and `selectedDealsByCell` explicitly; the full scheduled
root count is not the number of observations in that subgroup. The variance is
conservative in expectation under the fixed schedule, but sparse membership,
especially `K=1`, can yield very poor normal coverage. No occupancy comparison is
part of the four-primary multiplicity family or a randomized causal contrast.

Germany's balanced neutral credit `mean(1/n)=0.29` is analytical context, not a
newly played reference-control arm or an automatic qualification criterion.
There is no pooled recipe/population inference, direct replica superiority or
winner claim, precise training-variance estimate, automatic research progression
rule, or new readiness/qualification gate. Do not extend the sample based on
significance. Incomplete data are reported operationally, not turned into a
success-only strength conclusion.

## Execution and hard budget

Six workers per private `cpu-upgrade` job; one inference thread; 4,000-step
fail-closed cap per game. Requested maxima are reserved before submission:

| Slot                             |         Requested cap |
| -------------------------------- | --------------------: |
| Initial strong                   |               6 hours |
| Initial mixed                    |               3 hours |
| One shared recovery, if eligible |               3 hours |
| **Total maximum / maximum jobs** | **12 hours / 3 jobs** |

Unknown/ambiguous submissions consume their reservation. There is no blind
retry. A locked, durable ledger records intents before submission and reconciles
actual job identities/configuration without persisting credentials. Source and an
owner marker are reserved atomically in one remote conditional commit against an
observed immutable dataset HEAD; absence checks use that same revision. This
prevents independent worktrees/hosts from both winning an initial launch race.
The original and current owner markers are verified before every paid submission.
Both configured exposure and active SDK-reported HTTP/SSH endpoints are rejected.

Recovery is considered only after **both initial jobs are terminal**. An
unfinished original must have actual `ERROR / Job timeout` status and a verified
immutable incomplete snapshot. After both originals terminate, their authoritative
manifests are resolved together at immutable model-repository HEAD. Caller-supplied
revisions must match those current manifests; older incomplete snapshots cannot
hide newer completion or failure or change recovery priority. Payload audits and
resume use the authoritative revision, and both manifests are rechecked immediately
before the recovery reservation. A complete snapshot after a terminal job error
needs audit/reconciliation, not another job. If both panels need recovery,
**strong has fixed priority**; the other remains visibly incomplete. There is
only one shared recovery slot, never one per panel. Recovery reuses the exact
original source/bootstrap/tasks/checkpoints; no repackaging or replacement seed.
Missing initial-peer submission after a partial launch uses explicit original-
source ledger recovery. Uncertainty about whether an API submission succeeded
must be reconciled before any further submission.

The old 2,560-game jobs took 1.6864 hours strong and 0.7623 hours mixed. A threefold
extrapolation is approximately **7.346 job-hours**, not a runtime guarantee; new
policies and the extended mixed schedule can change durations. Local preflight,
audit and deterministic replays do not consume remote job-hours. If the cap is
exhausted, preserve incomplete results and stop.

## Storage, publication and recovery

No models, raw states/actions, reference requests, labels, rows or trajectories
are saved in study output. Each panel commits at most 640 atomic whole-three-arm,
all-seat deal batches, plus compact plan/summary/metadata. The panel artifact cap
is 64 MiB and the manifest cap 64 KiB; test the actual maximum manifest size.

Every completed batch commits locally; publication occurs every 16 batches.
Remote-committed batches must never repeat. A killed ephemeral job may replay
unpublished work with identical tasks, counted once. Any game error aborts;
there are no fabricated losses or silent retries. Resume requires a contiguous
committed prefix, exact source/runtime/model/task identity, and valid complete
three-arm/all-seat batches; malformed uncommitted temporary files are ignored.

Worker output, reference cache, reference venv, resume cache and model cache are
five nonnested paths. Set the dedicated HF model cache before transitive imports.
Metadata-budget all six model files before transferring any; validate immutable
revision, size, SHA, complete saved configuration, update, tensor shapes and
finite values. Explicit verified retained checkpoint copies are supported for
preflight; the original expert's exact revision must not be assumed cached.
Legitimate HF snapshot-to-blob links contained within its cache are accepted;
restored study snapshots and ledgers must not contain symlinks.

Keep the reference artifact and existing Python environments. Retain the local
8,000,000,000-byte ceiling, 2 GiB free-space minimum and additional 1 GiB staging
allowance. Source archive metadata/hash/member/Git verification uses compressed
size below 128 MiB and expanded size below 256 MiB; do not relax old shared guards.

## Validation and independently gated reporting

The 13 versioned serving/launch/preflight source files and their tests are pinned
by the study identity. Auditors, documentation and generated receipts are excluded
to avoid identity cycles. Validate all 15,360 production and 198 smoke specs
against independent Python/Node planners. Test three distinct expert-family model
routes, swapped checkpoint/config rejection, missing arms, duplicated control,
atomic resume, statistical covariance/weights/multiplicity, strict budgets,
source/archive/storage limits, actual cache symlink shapes and uncertain launches.

Real-runtime smoke uses one deal (index 0), all focal seats and all three arms in
each panel for these fixed scopes:

| Map          | Players | Rules     | Bidding |
| ------------ | ------: | --------- | ------- |
| Germany      |       2 | Recharged | Sealed  |
| Germany      |       6 | Recharged | Sealed  |
| USA          |       3 | Recharged | Sealed  |
| USA          |       5 | Original  | Sealed  |
| France       |       4 | Recharged | Open    |
| France       |       2 | Original  | Sealed  |
| UK & Ireland |       5 | Recharged | Sealed  |
| UK & Ireland |       6 | Original  | Open    |

There are 99 games / 8 batches per panel, 198 per execution. Compare uninterrupted
execution with interruption after the **first committed batch**, followed by exact
resume: **396 terminal executions / 198 exact matches**. Check all non-timing
terminal/controller/public counters, preserve committed bytes, ignore a malformed
uncommitted temporary file, and prove completed resume neither loads models nor
collects. All ten controllers must be exercised, with zero expert labels.
Source/runtime/full model/reference identities must match before and after.
Archive and remotely verify bounded evidence; commit/push the frozen source before
paid launch. Smoke makes no strength inference.

Final reporting additionally requires an independent standard-library outcome/
statistical audit, actual external source/runtime/model/job/budget/inheritance
integrity evidence, and **48 fixed deterministic production replays**. For each
row below, replay all three focal arms in both panels:

| Map          | Players | Rules     | fastBid | Deal | Focal seat |
| ------------ | ------: | --------- | ------- | ---: | ---------: |
| Germany      |       2 | Recharged | true    |    0 |          0 |
| Germany      |       6 | Recharged | true    |    7 |          5 |
| USA          |       3 | Recharged | true    |    2 |          1 |
| USA          |       5 | Original  | true    |    5 |          4 |
| France       |       4 | Recharged | false   |    4 |          2 |
| France       |       2 | Original  | true    |    1 |          1 |
| UK & Ireland |       5 | Recharged | true    |    6 |          3 |
| UK & Ireland |       6 | Original  | false   |    3 |          0 |

Only `featureMs`, `inferenceMs`, `referenceMs`, and `seconds` may differ in replay
outcomes. Replays add zero independent strength observations. JSON completeness
alone is integrity-pending; expected projections or success booleans are not
substitutes for actual external evidence. Preserve failed/incomplete panels and
failed-closed diagnostic attempts. No optimization trajectory replay is claimed.

## Readiness communication

Current status: **promising, reproducible research; not a production-integrated
bot**. Explicitly reassess readiness after this study. Do not equate audited
results with human strength or readiness for release.

“Approaching controlled human-playtest readiness” requires both credible stress
performance (including adverse cells and uncertainty) and a validated bounded
serving path. The production engine still uses its existing heuristic. These
PyTorch graph checkpoints are not drop-in replacements for the legacy Germany
ONNX service. A pinned native service or export with action/output parity, full
platform revision/player/dedup/legality handling, timeout/error/unsupported-option
fallback, and actual-host decision/turn latency, concurrency and memory checks
remain necessary. Research checkpoint recovery is not platform persistence or
restart testing.

Release readiness is a later decision requiring supervised human feedback,
explicit supported scope and qualification/acceptance criteria, monitored rollout,
identifiable policy versions and tested rollback. No numerical human-strength
criterion is established here. Serving integration, human playtesting and release
are not authorized by this evaluation-only study; do not silently expand scope.

## Current execution state

Isolated implementation is complete and pre-launch validation is in progress.
Independent review found and verified fixes for stale recovery snapshots,
cross-worktree initial-launch races, and dropped SDK exposure fields. The
worker/launcher passed 74 offline tests, the independent auditor 34, the core 35
Python / 6 Node tests, and the preflight harness 17. The complete Node suite passed
60 tests and engine suite 366; the combined Python suite passed all 637 tests.
The real-runtime preflight passed **396 terminal executions / 198 exact replay
matches, zero failures**, in 499.48 seconds. All ten controllers were exercised;
no expert labels were collected. All six cold model sets' tensors and inference
flags, all 13 serving/test files, and legacy/reference/runtime identities remained
unchanged. First-batch preservation, ignored/replaced incomplete temporary files,
and no-work completed resume passed. This adds no independent strength evidence.

The remotely verified private archive contains **58 files / 5,804,466 bytes** at
model revision `1d859ae85fb8a9ac1dbe4dd68d1df9efdd741e14`, prefix
`diagnostics/replica-stress-v1-preflight`. The actual launcher independently
rechecked all 198 matches from the downloaded archive; the generated gate receipt
is [`replica-stress-preflight-v1.json`](replica-stress-preflight-v1.json).
The source freeze `7bab96167ee32d691b2ccc450c50162283b0a473` was pushed and remotely
verified before submission. Strong initial job `6af24e8a9737d9a9e08ddd53` was submitted.
The first launcher stopped after its returned ID and durable receipt, before any
mixed submission: live response fields use `timeout: 21600`, `expose: {ports: []}`
and `ssh: {enabled: false}`. The actual six-hour timeout, disabled access and all
other expected job fields were independently observed. No job was retried.

The new non-serving reconciliation decoder passed **110 tests** (74 original
worker/launcher and 36 new), independent focused review and 16 additional read-only
test executions, plus actual read-only admission of strong with the unchanged job
validator. Private bindings of the original inventory/submit/continuation functions
preserve every owner/budget/source/preflight guard. The driver may only submit the
missing mixed initial peer or the already-authorized conditional recovery; there
is no initial-launch mode. Both actual timeout aliases are strictly typed and must
agree, disabled exposure shapes are narrowly allowlisted, and active endpoint
evidence is retained. The proof is
[`replica-stress-reconciliation-v1.json`](replica-stress-reconciliation-v1.json).
The original 13 runtime files and source/bootstrap remain unchanged. The immutable
first launch/admission record is
[`replica-stress-launch-v1.json`](replica-stress-launch-v1.json).

After reconciliation commit `4dceb9c16a9690d3e22fcedb9fed64043d66e505` was pushed,
the missing mixed initial was submitted once through the original ledger:
`6af2549c9737d9a9e08df3e7`, with actual timeout **10,800 seconds** and disabled
HTTP/SSH access. At initial-pair verification both originals were running and
actual inventory, configuration, source and owner checks passed. Strong's original receipt is byte-identical.
[`replica-stress-peer-v1.json`](replica-stress-peer-v1.json) records the completed
initial pair. **Nine requested hours are committed; the single shared three-hour
recovery was unsubmitted and remained conditional at that checkpoint.** Both
completion watchers were attached; no production strength inference had been
released. The completed training replicas and their evidence remain unchanged.

Mixed completed at `2026-11-10T01:24:15.429Z` under its verified 10,800-second
limit. Its authenticated final own upload is
`0fa0ff123e9d5a135aa8e490475dbb03e885309a`, containing **647 files / 29,766,403 bytes**.
Remote metadata/member hashes, independent full JSON validation, and the exact
43-upload production log chain passed. The panel contains **7,680 saved games /
640 independent roots / 2,560 games per arm**, with zero expert labels. It remained
**integrity-pending**: no one-panel strength estimates were released, no production
replays had run, and strong was still pending at that checkpoint. See
[`replica-stress-mixed-completion-v1.json`](replica-stress-mixed-completion-v1.json).

Strong subsequently completed at `2026-11-10T03:47:29.178Z` under its verified
21,600-second limit. Its final own upload is
`a0ff9f45bcc008eea22bb5a74fc65d9ae1a9ea36`, with **647 files / 29,839,370 bytes**.
Remote metadata/raw hashes, independent full JSON checks, and the 43-upload
production log chain passed. Both originals completed, yielding **15,360 saved
games / 1,280 independent roots**, without recovery. The study consumed nine
requested hours across two initial jobs; the conditional three-hour recovery is
unused and will not be repurposed. Both panels remained integrity-pending at this
operational checkpoint, pending joint external verification and all 48 fixed
replays. The combined operational record is
[`replica-stress-completion-v1.json`](replica-stress-completion-v1.json).

### External integrity tooling (separate from the frozen worker)

`audit_replica_stress_integrity_v1.py` provides explicitly gated bounded payload
fetching, joint verification without games, the 48 literal production replays,
and joint receipt finalization. The original paid-job ledger is fixed at
`ai/runs/multimap-replica-stress-20261109-v1`; an alternate or copied ledger cannot
replace its unknown-attempt accounting. All source/runtime/model/job/recovery
checks remain required. The posthoc control-plane decoder is executed from
privately authenticated bytes, not a preloaded module namespace.

Verification issues only a live, closure-owned authority. Public session fields
are checked detached views, and public model descriptors do not expose live
policies. Actual model fingerprints cover tensors, all submodule modes and grad
flags, roles, class, width and residual bound. Constructed/copied sessions or saved
verification JSON cannot authorize replays or final receipts.

Each replay panel consumes one exclusive, fsynced intent in the fixed protected
`ai/runs/multimap-replica-stress-20261109-v1-integrity-attempts-v1` directory before
collection. It binds both snapshots, source, tasks, models, common budget evidence
and output. Success/failure evidence is retained there independently of the chosen
report directory. A failed, interrupted or unknown attempt cannot be retried by
changing directories or processes. Even a successful partial replay cannot be
resumed in a fresh process; this conservative restriction must not be bypassed by
removing its evidence. Both 24-game comparisons must succeed before either
external attestation is written. No integrity-tool test or offline compatibility
probe is itself production replay evidence or an independent strength observation.

The final implementation passed **790 full-suite Python tests** and independent
focused review. The last review's remaining test-only retained-file dependency was
removed; all **117 final component tests then passed in an isolated public-source
copy with no private artifacts or network**. The full suite ran the final auditor
with the immediately preceding test revision; the final test-only change and its
portable rerun are recorded explicitly in
[`replica-stress-integrity-tool-v1.json`](replica-stress-integrity-tool-v1.json).
Offline retained-byte compatibility checks verified all 1,404 source-manifest
files and all six real cached checkpoints, including complete saved config,
tensors, class, width and bound. No remote production attestation or actual fixed
production replay was performed during this development validation.

### Final external audit, statistical review and preservation

Subsequent actual joint verification passed all source/runtime/reference,
six-decoded-checkpoint, owner, job-budget and chronology checks. The separate final
process re-verified inputs and completed **24 strong + 24 mixed exact saved-outcome
comparisons** before issuing either attestation. Only the four preregistered timing
fields were excluded. Full model fingerprints were unchanged, with zero labels
or new independent strength observations. All four exclusive durable replay
intent/result files are retained; no retry or replacement occurred.

Independent standard-library review recalculated all four primaries and all
114 subgroup sets per panel from the 15,360 saved games, checked the literal
lineups, and independently compared the 48 existing replays. It found no numerical
or replay mismatch. Supplementary rational-credit analysis resolved two tiny
negative floating-point cell means to exact zero without changing any original
statistic; actual negative cell counts are strong 7/8 and mixed 3/2 for
replica1/replica2. All adverse data, occupancy sparsity and watchpoints remain.

The four replica-minus-PPO2 means are strong **+0.153177 / +0.149583** and mixed
**+0.192995 / +0.186849**. Every primary Bonferroni 98.75% normal interval is positive,
but coverage remains approximate and conditional on the fixed checkpoints and
schedules. This does not imply every subgroup improves, establish historical
Germany-reference superiority or human strength, select a replica, or estimate
training variance. See the [full report](replica-stress-results-v1.md) and
[untrimmed result record](replica-stress-results-v1.json).

The bounded final archive contains **85 files / 11,933,091 bytes**, with exact
remote inventory and downloaded content hashes verified at private model revision
`df4c22f914a5131c7d7bee1a39703e1c8dbf3132`; the
[publication receipt](replica-stress-audit-v1.json) binds all members. It preserves
both genuine attestations/replays, full statistics, independent review, source,
validation and adverse operational evidence. The archive publisher was separately
reviewed: frozen secret-scanned upload bytes, pre-upload proof-chain binding,
optimized-Python rejection, one CAS commit and retained intent/receipt were checked.
Original snapshots keep their own immutable revisions; the canonical paid ledger
was not moved or copied, and all retained reference/training artifacts remain.

Strength evidence now supports considering a bounded serving prototype. The
integrated bot is **not controlled-playtest ready or release ready**: export/action
parity, platform state/legality/deduplication, fallback and target-host performance
still need validation, followed by supervised human testing and monitored
rollout/rollback. No new progression/qualification gate or serving/release
authorization is introduced by these results.
