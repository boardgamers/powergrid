# Conservative auction comparison — execution readiness, 27 October 2026

The research goal is active. A **single new coordinator** owns collection of the
four corrected-runtime pilots and subsequent execution of the already frozen
10,080-game development comparison. No model selection, gradients, reserved
final games, qualification or deployment is automatic.

## Current owner

- PID **1685160**, exec session **76424**, started **2026-10-27T19:31:44.057702+00:00**.
- Process command was independently checked under `/proc/1685160/cmdline`;
  **22 code pins** match the saved owner state.
- Script: `strong/coordinate-conservative-auction-development-v2.py`.
- State: `runs/conservative-auction-development-coordinator-v2/state.json`.
- Log: `runs/conservative-auction-development-coordinator-v2.log`.
- Snapshot stage: `waiting_for_original_pilots`, **0/4 pilots audited**,
  **0 development submissions** at `2026-10-27T19:35:42.173876+00:00`.

Do not run a competing collector or submitter while this process is alive.
A state file alone does not establish liveness: check the process command and
original HF handles. The original v1 coordinator PID 1061599 and collector PID
1146868 remain stopped; their STOP marker and evidence are unchanged.

The only pilot handles are:

- population / 2p: `6ae0fa243fb22a235dd31616`
- population / 6p: `6ae0fa2541e90535df7674df`
- dual / 2p: `6ae0fa2541e90535df7674e1`
- dual / 6p: `6ae0fa2541e90535df7674e3`

They were re-inspected RUNNING this turn. See [pilot source and provenance](CONSERVATIVE-AUCTION-RUNTIME-2026-10-27.md).
Original v1 failures are not replaced or relabelled by this run.

## Tested before starting

**13 tests pass**, with logs under `runs/conservative-auction-development-*-tests-v2.log`:

- Five schedule/resource tests: every allowed batch length covers exactly the
  same 10,080 games; reject incomplete/capped/duplicated/wrong-source evidence;
  outcomes cannot influence resource allocation; slow measurements shrink
  batches; inadequate memory or missing pilots blocks preparation.
- Five submission tests: exact development scope, intent recorded before API,
  secrets excluded from saved guards, original-handle reuse, source-change and
  ambiguity rejection, exclusive submitter and rejection of non-development seeds.
- Three coordinator tests: failed audit prevents any new submission; complete
  comparison launches nothing further; pending batches audit first and then use
  the bounded launcher.

The v2 schedule changes job names and runtime identity only. It retains all
**27 cells, three arms, eight independent paired deals per cell, every seat and
four rule combinations**, the v1 development seeds and all original thresholds.
The three arms each have **3,360 games**. A one-deal preview gives 648 jobs; actual
batch length, count and timeouts depend on all four completed runtime measurements.
No synthetic test measurements are saved or used as admission evidence.

## Execution boundary

1. The owner collects and independently audits the exact four original v2 jobs.
   It cannot prepare the development source until all four and all 64 games pass.
2. It chooses whole-deal batches/timeouts from complete measured wall/CPU/memory
   costs only, validates every policy/contract, preserves every base source byte,
   and uploads/download-verifies a separate development source.
3. It runs at most **64 development HF jobs concurrently**. Existing completed
   jobs are collected and audited **before** launching the next batch. Failed or
   ambiguous originals stop the owner for inspection; no automatic retry/restart.
4. It requires every planned job/game and stops at completion. Review/selection
   and final qualification are separate steps.

The current source/protocol and all 22 pinned modules must stay unchanged while
the owner runs. An explicit user pause should stop this owner and preserve its
state/handles; never restart the old v1 owner. If this owner exits, inspect the
actual process, saved failure and original handles before taking any action.
Observation timeouts do not mean HF jobs stopped or authorize replacements.

Future development outputs use `conservative-auction-development-*-v2` paths and
`pg-conservative-dev-v2-*` names. The unchanged seed template remains
`conservative-auction-development-v1-{players}p`. The development source has not
been prepared/uploaded and no development jobs have been submitted at this
readiness snapshot. The broad comparison is **not yet runtime-admitted**.

The readiness archive descriptor is `strong/conservative-auction-development-readiness-v2.json`,
created after the evidence upload/download hash check. It records the immutable
private HF archive, original owner, direct pilot statuses, code pins and tests.

While waiting, independent analysis tooling can be prepared without changing
these pins: require complete paired coverage before reading outcomes, use the
predeclared whole-deal bootstrap (10,000 replicates, seed 15125), retain every
adverse count/rule/opponent cell, and do not turn development results into final
qualification. The original final protocol and all reserved seeds remain unused.

Previous goal turn: progress (validated, archived and launched corrected runtime
pilots). Current goal turn: progress (tested and started the gated sole owner),
plus a verified wait on the four original pilot handles. No new playing-strength
result or general plateau conclusion is established.
