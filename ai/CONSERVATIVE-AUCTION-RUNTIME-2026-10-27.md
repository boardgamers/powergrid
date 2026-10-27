# Corrected runtime complete; development comparison launched — 27 October 2026

**Checkpoint: 22:37 UTC. Research is active.** All four original corrected-runtime
pilots completed and passed independent raw auditing: **64 games / 8,416 decisions /
135,608 uncapped continuations**. The previously failing episode 5 completed in its
original corrected job. These repeated engineering seeds are runtime evidence;
they are excluded from strength estimates.

The sole coordinator is **PID 1919833**, original session **94582**. Its process
and all 24 pins were directly verified. It admitted and uploaded the unchanged
**10,080-game / 648-job** development comparison and submitted its first **64**
original jobs. The direct snapshot at `2026-10-27T22:35:37.906227+00:00` found **44
COMPLETED / 20 RUNNING**, with no failed jobs. Completed remote jobs
still require the owner's local audit. Do not run another collector or submitter.

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
- Original per-job guards: `runs/conservative-auction-development-hf-v2/*/launch.json`.
- Recovery owner state: `runs/conservative-auction-development-coordinator-recovery-v2/state.json`.

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

After **all 648 jobs / 10,080 games** complete and pass auditing, run the existing
independent comparison with the explicit recovery owner path:

```sh
ai/.venv/bin/python -B ai/strong/compare-conservative-auction-development-v2.py \
  --owner-state ai/runs/conservative-auction-development-coordinator-recovery-v2/state.json
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
