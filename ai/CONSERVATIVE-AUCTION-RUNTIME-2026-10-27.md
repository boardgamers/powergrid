# Corrected runtime complete; development comparison launched — 27 October 2026

**Current execution — 28 October, 12:18 UTC: reviewed bootstrap recovery is running.**

The two Node-download failures occurred before evaluation and remain preserved.
Exactly two explicit replacement attempts were submitted with the same frozen
source, policies, seeds and Node v24.14.0 release. The Node archive now comes
from a checksum-verified immutable HF dataset revision. No completed game was
repeated, and no policy was selected from partial outcomes.

The sole owner is **PID 1075760 / session 83119**,
`strong/coordinate-conservative-auction-attempts-v1.py`. At admission it owned
**424 selected study jobs / 426 total HF attempts**, including **360 audited**
selected jobs and the two failed originals. The full plan remains **648 selected
jobs / 10,080 games**. This snapshot is not live status: inspect the process and
`runs/conservative-auction-development-attempts-coordinator-v1/state.json` before
acting. It collects first, submits only unsubmitted rows, caps active jobs at 64,
and stops on failures; it never creates another retry. Do not run another owner
or collector. Old v3 is stopped and must not be restarted.

A later owner checkpoint at **12:21:34 UTC** reached **370 audited / 434 selected
jobs submitted / 436 total HF attempts**, with 64 active at submission. The
verified HF recovery archive is indexed by
`strong/conservative-auction-bootstrap-recovery-evidence-v1.json`.

Read [the bootstrap recovery handoff](CONSERVATIVE-AUCTION-BOOTSTRAP-RECOVERY-2026-10-28.md)
for both failed/replacement pairs, verified cache provenance and the final
comparison command. Use the new attempts-aware collector/result/analysis;
the old collector will correctly stop on the preserved failed originals.
No new gradients, qualification, final seeds or deployment. Historical owner
references below are superseded by this notice.

**Current execution — 28 October, 11:34 UTC.** V3 audited all **360 original jobs**
then submitted 64 unsubmitted rows (**424 / 648 submitted**). It stopped at 11:32
on `pg-conservative-dev-v2-pop-heuristic-5p-02`, HF `6ae1dca83fb22a235dd3e7c7`:
HTTP 502 downloading Node v24.14.0, before source extraction or evaluation.
PID 678525 is absent. The failed original and logs remain preserved; the other
63 outstanding originals were directly observed RUNNING. No replacements or
automatic retries have occurred. Research remains active, with reviewed
infrastructure recovery and completion of the unchanged grid still required.

The recovery archive descriptor is
`strong/conservative-auction-development-owner-recovery-evidence-v3.json`.
Its snapshot includes all 424 original guards and the 360 cached audits with
immutable raw-archive references. Do not restart the stopped owner or treat this
infrastructure failure as a measured policy outcome. Later complete comparison
must use the eventual completed owner, not this stopped v3 checkpoint.

**Recovery admission — 28 October, 11:19 UTC (historical).** The prior host rebooted; PID 1919833
is absent and its original state/log remain preserved. Its last state recorded
360 submitted jobs and 296 verified. All 64 outstanding original handles were
directly observed COMPLETED, with no uncertain launch and all 24 code pins intact.
The exact termination time/cause is unknown.

The sole reviewed recovery owner is **PID 678525 / session 49555**, running
`strong/recover-conservative-auction-development-v3.py`. It retains every original
guard and the existing source, audits the completed originals first, then uses the
unchanged coordinator loop to submit only remaining planned rows. Its state and
360-handle admission record are under
`runs/conservative-auction-development-coordinator-recovery-v3/`. Four recovery
admission tests pass. No replacement jobs, failed-job retries, policy changes,
partial-result selection or final seeds are involved. Research remains active.

**Historical checkpoint: 27 October, 23:44 UTC.** All four original corrected-runtime
pilots completed and passed independent raw auditing: **64 games / 8,416 decisions /
135,608 uncapped continuations**. The previously failing episode 5 completed in its
original corrected job. These repeated engineering seeds are runtime evidence;
they are excluded from strength estimates.

The coordinator at that checkpoint was **PID 1919833**, original session **94582**. Its process
and all 24 pins were directly verified before and after the new recovery snapshot.
The unchanged **10,080-game / 648-job** development comparison has **310 original
handles** in the snapshot ending `2026-10-27T23:44:56.066451+00:00`. It captures
**249 cached audits / 3,564 games**; direct inspection of the remaining 61
originals found **two COMPLETED / 59 RUNNING**, with no failures or observation
errors. No launch was unknown or in progress during this capture. Completed remote
jobs still require the owner's local audit. Do not run another collector or submitter.

The owner state still reported 246 audited jobs while the snapshot captured 249
completed audit files. That counter is updated after collection batches, so this
is an interval snapshot, not a claim that all counters update simultaneously.
No partial outcomes have been used to compare or select policies.

## Completed original runtime pilots

All four jobs below are **COMPLETED and independently audited**. Wall time includes
startup and validation within the measured job, not HF provisioning. Peak RSS is
sampled across the process tree every 0.2 seconds; it is not an exact allocator peak.

| Arm | Players | Games | Original job | Wall seconds | CPU seconds | Peak RSS GiB |
|---|---:|---:|---|---:|---:|---:|
| conservative_population | 2 | 8 | `6ae0fa243fb22a235dd31616` | 1191.169 | 2776.58 | 6.091 |
| conservative_population | 6 | 24 | `6ae0fa2541e90535df7674df` | 5704.235 | 21761.38 | 6.426 |
| conservative_dual | 2 | 8 | `6ae0fa2541e90535df7674e1` | 3322.012 | 7167.61 | 5.840 |
| conservative_dual | 6 | 24 | `6ae0fa2541e90535df7674e3` | 11238.000 | 41080.39 | 6.569 |

Measured sums: **21455.416 batch-wall seconds (5.960 job-hours)** and
**72785.96 CPU seconds (20.218 CPU-hours)**; largest sampled RSS
**6.569 GiB**. No gradient updates or final seeds were involved.

`strong/conservative-auction-runtime-results-v2.json` is the complete collector
result. `strong/conservative-auction-runtime-independent-audit-v2.json` records a
separate read-only re-audit of every raw file, receipt, execution binding, terminal
credit and measurement. The four immutable raw archive revisions and hashes are
inside both reports; no game was rerun to obtain this final audit.

The earlier regression check compared all three originally successful v1 jobs to
v2: **40 games / 5,522 decisions** preserve public inputs, legal menus, choices,
sampled outcomes and terminals. Only pinned runtime identities and timings differ.
The original v1 dual-6p failure remains failed and preserved; it is not silently
relabelled by this corrected run. Its original owners and STOP marker stay stopped.

Paired timing observations from those three repeated jobs and bounded live HF
telemetry are retained under `runs/conservative-auction-live-metrics-v2/`. They
show slower timing across multiple decision types; they do not identify its cause.
Admission uses the four complete current measurements, not partial or older costs.

## Frozen development comparison now running

Three arms have **3,360 games each**: filtered model, conservative population
auction search and conservative dual-population auction search. The unchanged
protocol has 27 opponent/count cells, eight paired deals per cell, every seat,
and all original/Recharged × open/sealed combinations across 2–6 players.
Eight worlds per population, strict advantage greater than 1/8, nonnegative
included-population margins and model preference on ties remain unchanged.
Permitted public balances are available; hidden decks/bids and opponent identity
are excluded from policy inputs. No resource-turn prototype was added to this run.

Measured resource admission selected **one complete paired deal per job**:
**648 jobs / 10,080 games**, at most **64 concurrently**, on `cpu-upgrade`.
Each job runs four games concurrently with four search workers and one inference
thread. Timeouts are 2–5 hours for population search and 4–9 hours for dual search
and the conservatively sized control. The sizing formula uses a 900-second setup
allowance, twice observed per-game wall cost and 75% timeout utilization. This is
an engineering allowance, not a statistical upper bound on unseen runtimes.

Development source dataset: `coyotte508/powergrid-ai-training-v1`.

- Revision: `0f9c129af46fe181a71b1f131243517fff4cc16b`.
- Archive: `strong-source-conservative-auction-development-v2.tgz`.
- Archive SHA256: `d1345d552192c46efe38c3eb7df22c4e4663f2993f2a09fc597bb7ef4d83808e`.
- Source manifest SHA256: `b0c68341ca3cb7d0aa65831cf1bb4ec748fdf5712278e2c23a7ccff6b275e09e`.
- Source files: **2821**; the original runtime files are unchanged.
- Descriptor: `strong/conservative-auction-development-source-v2.json`.
- First 64 exact handles and direct statuses: `strong/conservative-auction-development-launch-state-v2.json`.
- Later 310-handle recovery snapshot: `strong/conservative-auction-development-progress-state-v2.json`.
- Original per-job guards: `runs/conservative-auction-development-hf-v2/*/launch.json`.
- Current recovery owner state: `runs/conservative-auction-development-coordinator-recovery-v3/state.json`.
- Preserved previous owner state: `runs/conservative-auction-development-coordinator-recovery-v2/state.json`.

The runtime source remains dataset revision
`8f504f71b51c6ec5bc284c02b961d90923cdce88`, archive
`strong-source-conservative-auction-runtime-v2.tgz`, SHA256
`528f8ff361de6775a340ced2b2e08713a350ece12a469ed40a36b4d152471678`.
The runtime manifest remains
`a2047543f5f6a8065dd9b868dd4551531147185068c665900691c5b13c278619`.

## Continue without duplicate work

Work in the AI checkout on `ai/germany-baseline`, using `ai/.venv/bin/python -B`.
Leave the live owner, frozen source, policies, thresholds and seeds unchanged.
Inspect the actual process and original handles. Observation timeouts are not
stopped jobs. The owner audits each completed batch before launching the next and
stops on failures; never restart or replace a failed original automatically.
Do not invoke either manager's collect or launch operation beside the live owner.

The later snapshot and its archive descriptor
`strong/conservative-auction-development-progress-evidence-v2.json` preserve
original launch guards, completed cached audits, their local artifact manifests,
exact immutable raw-archive references and before/after owner states. They add
recovery coverage beyond the first 64-handle launch archive. The snapshotter only
reads study files and inspects exact existing handles; it cannot collect or submit.
It does not replace the original raw audits with a new strength analysis.

Snapshot copies are nested under
`runs/conservative-auction-development-progress-snapshot-v2/`, retaining their
repository-relative paths. Do not restore them over a live owner. If recovery
becomes necessary, first verify the actual original process and every relevant
handle. Restore missing raw job artifacts from each captured `evidence` reference,
verifying the immutable revision/archive SHA and manifest, before relying on cached
`verified.json` files: the metadata snapshot does not duplicate those large raw
archives. Preserve existing original guards and failed/uncertain evidence. Never
infer permission to relaunch from a missing local artifact or observation timeout.

After **all 648 jobs / 10,080 games** complete and pass auditing, run the existing
independent comparison with the explicit recovery owner path:

```sh
ai/.venv/bin/python -B ai/strong/compare-conservative-auction-development-v2.py \
  --owner-state ai/runs/conservative-auction-development-coordinator-recovery-v3/state.json
```

Retain all adverse cells and the predefined whole-deal bootstrap. Do not select a
policy from partial outcomes. The unchanged final strength protocol and all 2,553
serving fixtures remain required; reserved final seeds are unused. The separate
actual-8840U result passed 300 exact responses, with auction medians of 5.89 ms,
8.47 s and 17.52 s for the three arms; the extra search cost still needs a measured
strength benefit. No candidate is qualified, deployed or published.

Final runtime/admission/first-batch recovery evidence is indexed by
`strong/conservative-auction-development-launch-evidence-v2.json`, referencing
four immutable raw pilot archives and both immutable source bundles. Historical
launch notices remain in Git and the prior launch archive. Do not rerun completed
pilots, CPU benchmarks, archive uploads or unchanged checks.
