# Resource-policy evaluation against the frozen neural opponent

## Completed capability

The separate `strong/resource_turn_snapshot_arena_v1.py` adapter can run the
existing v3 resource policy against the **frozen A260 neural opponent** used by
the qualification protocol. The v3 artifact and all running HF studies are
unchanged. This closes the evaluator's missing neural-opponent route; it does
not select a resource strategy or establish a stronger model.

A260 is a three-player checkpoint. Its pinned SHA-256 is
`9b46db558669a0c3085412fe2544359eda55ed9f092dffb67bead6af3c409ecd`.
It has no feature metadata and uses the historical **3.0 encoder (738 state /
96 action features)**. The learner retains its own 4.3 encoder and frozen-1
weights. The adapter refuses a different opponent hash or player count rather
than silently using the learner's encoder for the older model. This matches
the existing qualification protocol's three-player A260 cell; it does not add
multi-player support to that old checkpoint.

Every focal decision still crosses the existing public JSON policy boundary.
The learner receives the public request only, never the arena's role labels,
the opponent's model or its encoded observations. Opponent inference uses the
same fixed model and encoder as the earlier arena. Returned atomic moves and
complete resource transactions are applied through the existing authoritative
JavaScript engine and validated resource exchange.

## Exact recorded-game validation

The control uses episodes 0–11 from the immutable prior filter-versus-A260
resource-replanning study: one paired deal, all three focal seats and all four
original/Recharged × open/sealed combinations. These are already recorded
development games, not new or reserved strength seeds.

Two routes each reproduced all 12 games exactly:

| Route | Public learner requests | Executed learner moves | Complete resource transactions | Opponent predictions independently rechecked |
| --- | ---: | ---: | ---: | ---: |
| Atomic filtered model | 1,555 | 1,555 | 0 | 3,213 |
| Whole-turn model control | 1,119 | 1,555 | 126 | 3,213 |

Both reproduce the original learner action sequence and terminal state in every
game. The atomic route also matches original decision diagnostics; the whole-turn
route matches the corresponding atomic model decisions inside each resource
transaction. No search rollouts, rollout caps or root-filter overrides occurred.

The unchanged v3 auditor verifies learner receipts, transactions, counters,
terminal scores and the complete paired schedule. A second audit independently
replays the entire engine trajectory. It checks each learner request, legal menu,
player ordering and response, reconstructs each opponent observation and reruns
the actual pinned opponent model. It compares the final state exactly. Thus the
two routes have **6,426 independently rechecked opponent predictions**, alongside
2,674 replayed learner requests. This total counts the audit predictions; the
original replay generation also performed opponent inference.

Six negative checks passed: wrong model, wrong player count, altered opponent
action index, altered encoded-input hash, substituted opponent model identity
and a forged actor role. The corrupted trace hashes were deliberately recomputed
so the engine/model audit, rather than only a file checksum, had to reject them.

The successful check took **98.598 seconds locally**. This is engineering timing,
not an AMD 8840U benchmark. It consists of **24 replays of 12 distinct existing
games**, zero fresh full-game trajectories, zero HF jobs, zero gradients and zero
new independent strength data. Search modes still need their own admitted
complete-game evaluation against the neural opponent if selected for study.

## Preserved failed attempt

The first local adapter attempt incorrectly assumed that the old 3.0 opponent
encoder emitted `playerOrder`. It does not. All 12 cases stopped at that adapter
boundary before any complete replay. The old engine and model were not faulty.

`runs/resource-turn-snapshot-adapter-v1/` retains its original plan, partial
receipts, failures and exact original source copies. Its sibling `.log` preserves
the exception. The correction hashes the fields actually emitted by the old
encoder, including `playerOrder` only when present. Learner ordering remains
mandatory and independently verified. The corrected attempt has a separate
directory, `runs/resource-turn-snapshot-adapter-v2/`; no failed evidence was
overwritten and no completed game was repeated for recovery.

## Evidence and recovery

- `strong/resource-turn-snapshot-adapter-results-v1.json` indexes the successful
  assessment, mode totals and six negative checks.
- Assessment SHA-256:
  `e7d054045984d1e24ecc7d9ff1fb075d990a08197bc9d57050a9b962b7377ed8`.
- `runs/resource-turn-snapshot-adapter-v2/plan.json` pins both new sources,
  all 12 original game inputs, the v3 artifact, A260 and the preserved failure.
- The v3 artifact descriptor remains
  `f41f16f64bf4e9b068e09e15116a6f02c5254ef60c01bd7650a0d7ad356a2e57`.
- `strong/resource-turn-snapshot-adapter-evidence-v1.json` indexes the verified
  private HF archive with both attempts, source copies, chronological opponent
  traces, learner receipts, independent audits and this handoff. Existing model,
  v3 source and original game archives are referenced through immutable records.

The checker is intentionally one-shot. Do not rerun completed inference or
audits. Inspect original intents/results before recovering any interruption.
The adapter remains separate research code around the pinned artifact; future
HF admission requires packaging and pinning it into a new source bundle.

## Other live work and next action

The [resource runtime pilots](RESOURCE-TURN-RUNTIME-2026-10-28.md) still use their
six original handles and unchanged source. The whole-turn two-player pilot was
independently collected: eight games, 11,352 uncapped continuations, 858.53 s
measured wall time, 3,079.67 CPU-s and 4.556 GB sampled process-tree peak RSS.
Those measurements exclude HF bootstrap/download/upload time and are not playing
strength evidence. Check the current collection state for the other originals;
do not submit replacements.

The unchanged auction owner PID 1075760 was directly verified live at the
15:25 UTC checkpoint, with **524 audited / 588 submitted / 648 selected jobs**.
Finish its complete 10,080-game comparison before choosing the next strategy
study. No partial win results were used here. This turn is progress: one runtime
pilot was independently collected and the neural-opponent route was implemented
and validated. Research stays active; no candidate is qualified, no reserved
final seed is used, and nothing is deployed.

The **278-file recovery archive** was uploaded and downloaded successfully at
private model revision `af4e53466b5a529d58a18a692f7ec87dc8544578`,
`archives/resource-turn-snapshot-adapter-evidence-v1.tgz`, SHA-256
`81301607405cf612e1e64dcf5ebe2490880d09975fa461fd137b341efd5df667`.
The descriptor and final archive reference are saved in Git.
