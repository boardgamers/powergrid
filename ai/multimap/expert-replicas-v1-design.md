# Expert-v2 independent training replicas v1 — frozen design and launch

This is a qualification-ineligible research protocol, not a deployment.
`expert-replicas-protocol-v1.json` must be reviewed and committed with source and
real-service preflight evidence before any job submission. The separately
versioned `launch_expert_replicas_v1.py` enforces the source/preflight gate and
four-slot budget ledger; do not route this through `launch.py --workflow expert`
(which intentionally retains the old namespace). Keep the complete ignored group
directory for recovery. Uncertain API submissions consume their fixed slots and
must be inspected, never automatically retried.

## Fixed design

-   Exactly two additional runs, IDs 1 and 2. Independent optimizer/sampling seeds
    190731 and 827119; separate `pg-multimap-expert-replicas-v1-r{1,2}` roots, with
    disjoint warmup/train/update/selection/confirmation/smoke suffixes.
-   Same frozen bootstrap representation and fixed PPO0/1/2 population. Independence
    means training RNG and game roots, not a different pretrained representation.
-   Same 160 Germany expert warmup games / 24 epochs, then 32 x 80 balanced PPO
    games; teacher-v2, residual bound16, expert DAgger and all objectives unchanged.
    Germany is the only exact-reference map. No Italy/Benelux games anywhere.
-   **Each run selects its own checkpoint on its own fixed fresh selection roots**,
    using the original rule verbatim: eligible teacher fallback, warmup and
    updates8/16/24/32; Germany nonregression, other maps at most .05 regression,
    strict macro improvement and earliest tie. Do not force update24 or select
    between runs based on stress or final evaluation.
-   After selection, evaluate selected and teacher-v2 on two independent fresh
    deals per four-map cell, all seats (640 games per policy; 160 deal roots).
    Original `confirmation` transaction labels are retained but their roots and
    scope belong solely to this protocol. The two replicas also have independent
    evaluation roots: between-run differences include training, checkpoint-selection
    panel and evaluation-panel randomness, not pure training variance. Two runs
    are descriptive replication, not precise variance
    estimation. No shared held-out panel or stress-v1 reevaluation is implicit.
-   Report **both** runs, including fallback/incomplete/failure, chosen stage/update,
    full cell/map results and macro paired selected-minus-teacher credit. Summarize
    between-training spread without selecting a winner. Prior seed is historical
    context, not an extra same-panel observation. Everything qualification-ineligible.

## Isolation and reuse

All preexisting serving files remain untouched. Python functions are bound to private
copies of globals, preserving unchanged optimizer/selection/transaction function
bytecode. Original config validation executes against the original expert-v2
protocol before adding replica identity and source hashes. No global monkeypatch,
source execution, or relaxed old guard. The new JS bridge is a byte-for-byte copy
of `expert_game.cjs` **except its protocol import**, and this equality is enforced
at runtime and in tests. Its separate protocol loader changes only seed,
namespace and removal of transfer maps. Model, prior, teacher and exact-reference
helpers are imported unchanged; frozen core hashes are checked before planning.
Legacy and cross-replica tasks continue to fail closed.

`Replica(id).run(...)` is the local runner. `job_expert_replicas_v1.py` is the private
worker wrapper around the unchanged whitelist/compact-upload/reference recovery
worker. Set `EXPERT_REPLICA=1|2`, `EXPERT_WORKERS=6`, `EXPERT_SMOKE=0`, and a `RUN_ID`
ending in `-r1` or `-r2`, plus existing pinned source/repository environment. Resume
must retain that suffix and exact replica/config/source/runtime identity. Compact
artifact names and last.pt embedded-best transaction recovery are unchanged.

Real preflight verifies bit-exact model/optimizer/RNG recovery **after update 1**,
not every possible boundary. The inherited trainer constructs the selected model
again on a confirmation-only continuation; this consumes an additional, precisely
reproducible initialization-only Torch RNG advance. Dedicated synthetic boundary
tests check this narrow exception after selected/teacher confirmation commits:
model, optimizer, selected bytes and deterministic evaluation outcomes remain
unchanged, with no repeated optimization or committed evaluation. This is not
permission for unexplained training RNG drift. Replicas run in separate worker
processes; private function-global bindings do not isolate process-global RNGs.

## Bound and proposed operational sequence

1. The comparison choice is accepted: teacher-v2 baseline and independent
   evaluation roots. No algorithmic or hyperparameter tuning. The protocol
   declares 6,240 scheduled games per replica (2,720 training, 2,240 selection/
   control, 1,280 post-selection evaluation), 12,480 total. The primary analysis
   is selected-minus-teacher paired win credit: average all seats within each
   deal, then the two deals per map/count/rule cell, and weight all 80 cells
   equally. Report per-replica exploratory normal 95% intervals with clustered
   standard errors and descriptive between-replica spread; no pooled inference,
   winner selection, qualification or new significance-based progression gate.
2. Run offline suites and real-service smoke for **both** replica namespaces with
   existing cached reference and reusable venvs. Record all new source hashes,
   original serving hashes, runtime identity, routing/expert counters, complete
   four-map task coverage, zero initial-vs-teacher parity, full terminal outcomes,
   and interrupted/resumed exact transaction parity. Test both Python and JS
   foreign/old/reserved root rejection. Smoke observations do not count as study.
3. Verify total local study/cache storage below 8 GiB and at least 2 GiB free after
   worst-case additions. Reuse the retained ~451 MB reference artifact. Each run's
   compact artifact cap remains 128 MiB; trajectories live only in RAM. Check
   source package contents and bounded remote resume sizes before download.
4. Commit source + approved protocol + real-service preflight, then use the new
   versioned launcher/receipt gate (not a silent change to the old expert
   launcher). It requires clean source, exact identities and smoke counts, private
   repositories, immutable source package and artifact pins, no duplicate run/job,
   environment allowlist, source hash and a durable launch intent before submission.
   Storage admission preserves the older stricter decimal 8 GB ceiling while
   reserving another 1 GiB for bounded staging/recovery, above 2 GiB free headroom.
5. Two initial CPU-upgrade jobs, six workers, three hours each. At most **one**
   exact three-hour continuation per replica: maximum four job segments / twelve
   job-hours total. Continuations use an explicitly audited immutable snapshot,
   same source and same replica, never a new seed or retraining replacement.
   Stop and report incomplete at the cap; no open-ended retry. Runtime can exceed
   three hours including post-selection evaluation, so initial job timeout is not
   evidence of training failure. Current wrapper preserves transactions but does
   not itself enforce job scheduler segment counts; the launcher must do so.
6. Recover/audit all compact outcomes and both results, report every replica,
   leave update24 and serving frozen. No BGS deployment, release push, promotion,
   transfer claim, or reuse of final/reserved seeds.

## Validation currently completed

The full suites pass: **422 Python tests**, **54 Node tests**, and **366 engine
tests** (the existing ten-second Mocha timeout). Python coverage includes 34 expert
tests, 49 launcher/recovery tests, seven preflight-guard tests and 47 independent-
auditor tests. Python/JS validation exhaustively covers 7,360 production
and 292 smoke specifications without executing production games.

The real preflight **passed** for both replicas uninterrupted and with interruption
after update 1, using the retained exact reference and frozen models: **264 terminal
smoke games / 132 exact terminal-and-counter matches, zero failures**. Both replicas
preserved exact model/optimizer/RNG/history state at that interruption point,
repaired deliberately damaged uncommitted best bytes, and performed no collection
on a completed resume. Only two-player original/open smoke games execute; production
count/rule coverage is separately validated by exhaustive planning and the
unchanged mechanics tests. This is engineering validation, not strength evidence.

The independent `audit_expert_replicas_v1.py` preserves both IDs and withholds
strength statistics until full outcome/selection checks and separately verified
source/checkpoint/chronology evidence pass. Inherited uploaded files are not all
necessarily committed: external audit must reconstruct the original last.pt
boundary and verify committed outputs, allowing replay of uncommitted batches.
The private preflight archive is remotely hash-verified at model-repository
revision `15fe726e333c5a36257cf712ed98667678690038`: 105 files / 24,156,457 bytes.
`expert-replicas-preflight-v1.json` records its pins, all serving identities and
checks. After that source-freeze checkpoint, both initial replicas were submitted
on 2026-11-09 from Git `a75b787f38a833a8736ab6b84c7a2019f3773a55`. They were RUNNING
at post-launch verification, with completion/error notifications attached. Actual
submissions and immutable source pins are recorded separately in
`expert-replicas-launch-v1.json` and `runs.json`; no training outcome is claimed yet.
