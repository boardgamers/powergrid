# Parallel independent audit for the complete confirmation

The independent raw-data audit took **2.09 times less wall time** with four
isolated processes on six fixed saved job archives. Every full review matched
the original, including the recovered job's original HF ERROR status. This
changes audit scheduling only: no new games, policy calls or HF jobs were used
by this experiment. The running confirmation coordinator remains untouched.

## Measurement and limits

The fixed workload contains four confirmation archives (2, 3, 4 and 5 players)
and two search-policy runtime archives (2 and 6 players), **248 games per pass**.
Pass order was serial, parallel, parallel, serial. These are repeated audits of
the same records, not 992 newly played games.

| Pass | Workers | Wall time | Process-tree CPU time |
| --- | ---: | ---: | ---: |
| 0 | 1 | 26.864 s | 26.50 s |
| 1 | 4 | 12.156 s | 37.92 s |
| 2 | 4 | 12.136 s | 38.82 s |
| 3 | 1 | 24.022 s | 24.00 s |

Median wall time fell from **25.443 s to 12.146 s**. Median CPU time increased
from 25.25 s to 38.37 s. Parallel timings include process startup, imports and
shutdown. This was the local Ryzen AI 9 HX 370, not the target AMD 8840U.
The sample is small, local files were cached, and the live collector competed
for CPU and I/O. It does not establish an engine, inference, HF throughput,
download/extraction or whole-comparison speedup, or any playing-strength gain.

Report: `strong/current-auction-audit-parallel-profile-v1.json`.
Original intent and all four pass reports are under
`runs/current-auction-audit-parallel-profile-v1/`. The first process-identity
check failed before creating that run directory because it did not normalize
NUL-separated command-line bytes. The original script and failure log are
preserved; the corrected benchmark completed once. Do not rerun it on restore.

## Complete-grid integration

`strong/current_auction_parallel_audit_v1.py` runs the same frozen verifier on
each original archive, including the complete terminal-data recovery checks.
It verifies the source, job handle, launch guard and original receipt before
and after auditing. Workers do not collect, extract, write receipts, call HF,
run policies or generate games.

`strong/compare-current-auction-confirmation-parallel-v1.py` requires all
**944 jobs / 26,880 games** and the completed owner state before creating its
analysis intent. It uses four isolated processes for the independent raw
audits, then matches every complete review hash, decision count, job identity
and original HF status. Missing, extra, duplicate or altered proofs fail.
The original immutable archive verification, post-analysis raw-file checks,
paired whole-deal statistics and qualification requirements remain unchanged.
All adverse results and original ERROR statuses remain visible.

**14 tests passed**, covering complete-grid admission, immutable archives,
recovered failures, worker-result binding and failure propagation. Four real
confirmation reviews from each benchmark pass also matched the comparator's
proof checks. Readiness binds 79 input hashes:
`strong/current-auction-parallel-comparison-readiness-v1.json`.
The original serial comparator is unchanged and remains the reference.

After the sole coordinator has completed, inspect the owner process, state,
full result and any existing comparison intent/output before running once:

```sh
ai/.venv/bin/python -u -B ai/strong/compare-current-auction-confirmation-parallel-v1.py
```

Expected output: `strong/current-auction-confirmation-comparison-parallel-v1.json`.
The complete comparison has **not** run yet. Do not run a competing collector,
modify the live coordinator's 54 pins, analyze partial wins or tune frozen
policies. No automatic retries or substitution of incomplete results.

## Recovery and remaining work

The private archive descriptor is
`strong/current-auction-parallel-audit-evidence-v1.json`. It preserves code,
tests, readiness, measurements, pass records and first-attempt failure evidence,
and references the six immutable raw archives and both source bundles rather
than duplicating or regenerating games. Inspect archive intents/outcomes before
retrying an upload.

Research remains active. No candidate is selected or qualified, and reserved
final seeds are unused. The complete confirmation, independent comparison,
selection, held-out strength test and full selected-policy export/serving and
actual AMD 8840U package checks remain necessary.
