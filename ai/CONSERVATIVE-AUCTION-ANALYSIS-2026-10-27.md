# Conservative auction comparison — analysis readiness, 27 October 2026

**Update:** execution now has a [reviewed recovery owner](CONSERVATIVE-AUCTION-CPU-2026-10-27.md)
after the original waiter received SIGTERM. Use the explicit recovery owner path
below after it completes. Statistical logic/protocol is unchanged; all 14 tests pass.

The research goal remains active. The previous turn was a **verified wait**:
the original coordinator process and four HF pilot handles were directly checked.
This turn made **progress** by implementing and testing the independent complete-grid
analysis. No new strength result, training, simulations, candidate selection or
reserved seed use comes from these tests.

## Current execution snapshot

At **19:48 UTC**, original owner PID **1685160** was independently verified alive,
with all **22 execution pins unchanged**. Its state showed one verified pilot and
zero development submissions. Direct HF inspection confirmed:

| Original corrected-runtime job | Status |
| --- | --- |
| `6ae0fa243fb22a235dd31616` — population, 2p | COMPLETED, independently audited |
| `6ae0fa2541e90535df7674df` — population, 6p | RUNNING |
| `6ae0fa2541e90535df7674e1` — dual, 2p | RUNNING |
| `6ae0fa2541e90535df7674e3` — dual, 6p | RUNNING |

This is a timestamped snapshot, not a current-state guarantee. Recheck the actual
owner process and original handles. The sole coordinator retains collection and
submission ownership. Preserve the old v1 STOP marker and all original failures.
See [the execution handoff](CONSERVATIVE-AUCTION-DEVELOPMENT-2026-10-27.md).

## Implemented analysis

- `strong/conservative_auction_analysis_v2.py` implements the frozen protocol
  `51b845f4a57c3131475e24267fbbb08eb624c391aa6a8e6a4f5d5c6b8ac718ee`.
- It requires all **10,080 games**, three exact policies, 27 opponent/count cells,
  eight paired deals, every seat and all four rules. It rejects runtime seeds,
  duplicate/missing games, mixed model/settings, caps and invalid terminal scores.
- Credits are recomputed from `(powered, money, cities)` terminal scores. Ties use
  exact rational credit; strict wins and tied wins are also reported separately.
- Primary comparisons are population-minus-filter and dual-minus-filter,
  **equally weighted across the five search-opponent player counts**. Dual-minus-
  population remains secondary. Larger player counts cannot dominate by supplying
  more seat rotations.
- The predeclared bootstrap uses **10,000 replicates, seed 15125**, resampling
  eight whole deals within each player count. The same indices keep all policies,
  opponents, seats and rules paired. Intervals are exploratory and unadjusted;
  eight deals per count is limited evidence, not final qualification.
- Every contrast retains all **135 overall/rule views** (27 × five), with explicit
  negative, zero and positive directions. No retrospective rule routing or
  automatic candidate selection is implemented.

## Independent evidence reader

`strong/compare-conservative-auction-development-v2.py` waits for the owner's
complete state and the complete original result. It never calls a launch/collect
operation. It validates the exact frozen schedule, source, identities, original
handles and launch guards, download-verifies every immutable raw archive, then
independently re-audits all raw game/decision receipts. It checks input hashes again
after the full audit, aggregates override/cap counts and measured job costs, and
writes a separate comparison atomically without overwriting an existing outcome.

Do not invoke it until all originals finish. Once the execution owner is complete:

```sh
ai/.venv/bin/python -B ai/strong/compare-conservative-auction-development-v2.py \
  --owner-state ai/runs/conservative-auction-development-coordinator-recovery-v2/state.json
```

The expected output is `strong/conservative-auction-development-comparison-v2.json`.
An exclusive `.intent.json` records inputs before the long audit. If interrupted,
inspect the intent, original input hashes and any `.writing.json`/final output
before deciding how to recover. No automatic restart or deletion of evidence.
The script does not qualify or deploy anything, even for a positive development result.

Summed job wall durations are compute consumption, not end-to-end experiment
elapsed time or serving latency. CPU seconds and sampled per-job RSS are retained;
complete-policy latency on the actual 8840U is still a separate requirement.

## Verification and recovery

**14 tests pass**, recorded in `runs/conservative-auction-analysis-tests-v2.log`.
Synthetic terminal records exist only in memory/temporary test directories.
Tests check complete coverage, terminal ties and tie-breakers, wrong credits,
missing/duplicate/capped evidence, equal-count weighting, adverse cells, shared
whole-deal uncertainty, asynchronous ordering, original-job admission, refusal
to analyze a live partial run, existing intents and archive/manifest tampering.

The archive reader also passed against the actual first completed pilot:
revision `05345057533b5fd407f8466c4dea0f720e22511c`, archive SHA-256
`daf7312d68a97860ca5ce3df037ae76f30067d65bfd523aebb0fc7ed666997aa`.
This checks recovery plumbing only; pilot results remain excluded from strength.
Full-grid end-to-end analysis cannot be verified until the real grid completes.

The tested code, log, protocol, current owner snapshot and recovery references
are archived using the existing verified evidence helper. The resulting private
HF descriptor is `strong/conservative-auction-analysis-readiness-v2.json`.
No coordinator pins, policies, model weights or source jobs were changed.

Next: let the sole owner finish pilot admission and the frozen development grid;
inspect any original failure without replacement submissions. If complete,
run the independent comparison, review every adverse cell and measured cost,
then decide the next research step. The unchanged final gate and reserved seeds
remain separate and unused. No general learning plateau has been established.
