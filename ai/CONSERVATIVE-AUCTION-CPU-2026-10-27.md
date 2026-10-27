# Conservative auction CPU benchmark and owner recovery — 27 October 2026

**Current — actual 8840U run launched:** the recovered local reference completed
all **300 requests**, preserving the original 273 byte for byte and executing
only the missing 27. It passed independent per-request validation with zero caps.
Local final status SHA-256 is
`2bb3b20bc4a3eabed57a5c5507ddaa33bdce99b6eb901c7e7a661ba72365a072`.
Recovery PID 2050537 has exited; do not rerun it.

The unchanged package is now running on **AMD Ryzen 7 8840U w/ Radeon 780M
Graphics**, remote PID **3200567**, directory
`/home/coyotte508/powergrid-ai-conservative-auction-8840u-v2` on `minipc`.
The exact remote command was independently verified alive at **113/300 requests**.
Guard: `strong/conservative-auction-8840u-launch-v2.json`. Re-inspect that original
PID through `recover-conservative-auction-cpu-v2.py inspect-target`; do not launch
again. After terminal success and process exit, use `collect-target`, then
`analyze_conservative_auction_cpu_v2.py`. Full local/target parity and target costs
remain pending; partial timings are not reported as completed results.

The complete local reference, target guard and launch snapshot are indexed by
`strong/conservative-auction-cpu-target-launch-evidence-v2.json`. The source
package and all policy settings remain unchanged. No HF submissions, gradients,
new strength games, qualification or reserved seeds were used for this work.

**Latest local recovery:** exec session 24932 ended with code **143** after
**273/300 requests**. PID 1904528 and its package workers were absent; all stderr
files were empty, no STOP marker existed, and all 273 complete receipts were intact.
The original state and receipt file remain unchanged. The termination source is
unknown. This was not recorded as a successful full local run.

After inspection, `strong/recover-conservative-auction-cpu-v2.py` independently
re-audited the prefix and started only the **27 missing requests** in a separate
directory. Three tests reject changed/duplicated/out-of-order prefixes, a live
original, STOP markers and unexpected failure/count states. Recovery **PID 2050537**
is detached and tracked by `strong/conservative-auction-cpu-local-recovery-launch-v2.json`.
State: `runs/conservative-auction-8840u-local-recovered-v2/status.json`.
Log: `runs/conservative-auction-8840u-prepared-v2/local-recovery.log`.
At the last live check it had **278/300 total requests**, including five new suffix
requests. Verify `/proc/2050537/cmdline` as NUL-separated arguments, not a string
containing spaces. Preserve the guard; never launch another local recovery.

This produces a two-segment **correctness reference only**. The new process's
startup cost is recorded separately and must not be presented as an uninterrupted
local latency benchmark. The original immutable package, frozen policies and full
300-request target benchmark remain unchanged. After recovered reference success,
use these commands instead of the old manager's target operations:

```sh
ai/.venv/bin/python -B ai/strong/recover-conservative-auction-cpu-v2.py launch-target
ai/.venv/bin/python -B ai/strong/recover-conservative-auction-cpu-v2.py inspect-target
ai/.venv/bin/python -B ai/strong/recover-conservative-auction-cpu-v2.py collect-target
```

Both original **two-player HF pilots are now completed and audited (16 games)**;
the two six-player handles remain RUNNING. Recovery coordinator PID 1919833 is
live with all 24 pins unchanged. Zero development jobs or replacements have been
submitted. Do not compete with it. The local interruption/recovery evidence is
indexed by `strong/conservative-auction-cpu-recovery-evidence-v2.json`.

**Timing review addition:** `strong/analyze_conservative_auction_cpu_v2.py` now
requires the complete independently audited 8840U result before producing a
report. Five tests verify complete coverage, finite positive timings, separation
of all three cold starts, deterministic receipt order and refusal of incomplete
cross-host evidence. It preserves all 300 individual count/rule/stage points and
separates auction-stage costs from other stages, including per-count views.
One saved position per cell cannot estimate a deployment latency percentile;
the review reports descriptive fixture medians/ranges without making that claim.
After successful target collection, run:

```sh
ai/.venv/bin/python -B ai/strong/analyze_conservative_auction_cpu_v2.py
```

No target timings were produced while preparing this reader. The original CPU
runner/package and the recovery coordinator's 24 pins remain unchanged.

Research remains active. Previous turn: **progress**, independent analysis tested
and archived. This turn: **progress**, complete-policy CPU fixture coverage prepared,
local reference replay started, and interrupted execution ownership safely recovered.
No new HF jobs, gradients, full evaluation games or final seeds were launched by
this work. No new playing-strength result or qualified candidate exists.

## Execution ownership changed

Original development coordinator **PID 1685160 / session 76424** received
**SIGTERM at 19:54:38 UTC** while sleeping between pilot checks. Its saved failure
is `KeyboardInterrupt`, not an assertion or failed HF job. It was independently
confirmed absent. All 22 code pins matched, there was no v2 STOP marker, and no
development preparation, upload or submission existed. The research goal was
confirmed active. The source of the signal is unknown; do not infer a pilot failure.

The original state/log remain intact. State SHA-256:
`d5f5ebcae52ffd0b2f4b35c3279fb8440cad91da96a670b492e6b46c6a79ce51`.
A bounded collection-only check of the original handles completed at 19:59 UTC:
one audited pilot, three still running, zero replacement submissions.

After that inspection, one successor started at **20:02:37 UTC**:

- **PID 1919833 / session 94582**.
- Entry: `strong/recover-conservative-auction-development-v2.py --start`.
- State: `runs/conservative-auction-development-coordinator-recovery-v2/state.json`.
- Log: `runs/conservative-auction-development-coordinator-recovery-v2.log`.
- Admission record: `runs/conservative-auction-development-coordinator-recovery-v2/predecessor.json`.
- Snapshot at 20:03 UTC: live, **24 code pins unchanged**, one audited pilot,
  zero development submissions. Recheck the actual process on resumption.

This is a reviewed one-shot recovery, not an automatic retry loop. Three new tests
reject a live owner, STOP marker, changed predecessor state, existing development
work, failed/missing/extra handles and other failure types. The wrapper holds the
original owner lock, retains the unchanged tested coordinator, and uses a new
state directory. It collects the same four HF pilots and preserves all original
admission gates. It cannot restart itself or replace jobs. Do not run a competitor.

Original HF handles remain:
`6ae0fa243fb22a235dd31616`, `6ae0fa2541e90535df7674df`,
`6ae0fa2541e90535df7674e1`, `6ae0fa2541e90535df7674e3`.
The first was completed/audited; the others were directly confirmed running.
The old v1 owner/STOP marker remain unchanged.

The analysis CLI now accepts an explicit owner-state path. Its statistical
implementation/protocol is unchanged; all **14 analysis tests still pass**. After
the recovered owner completes the full grid, use:

```sh
ai/.venv/bin/python -B ai/strong/compare-conservative-auction-development-v2.py \
  --owner-state ai/runs/conservative-auction-development-coordinator-recovery-v2/state.json
```

## Actual 8840U benchmark preparation

SSH verified `minipc` as **AMD Ryzen 7 8840U w/ Radeon 780M Graphics**, with no
other Python/Node research worker running at the time of inspection. The new
target directory did not exist. No target benchmark has launched at this snapshot.

The package uses the **exact corrected runtime and three frozen descriptors**,
four search workers and one inference thread, with unchanged eight-world search
budgets and thresholds. No serving simplification or new model is substituted.

It selects the first non-forced saved menu in each of **100 cells**:
five player counts × four rules × five stages (plant choice, bid, resources,
building, bureaucracy). Three policies make **300 requests per host**. Selection
does not inspect outcomes. These fixed examples are engineering coverage, not a
representative distribution of gameplay latency or new strength games.

The historical 2,553-position model-only fixture pool has SHA-256
`f1c97bf909e38e5df372a89d169d80f5a6f24c00dccefacd60b10b767f1fcfa0`.
It contains private simulator state. The initial public-API benchmark preparation
correctly rejected it before producing a package or running any policy. That
rejection is preserved in `runs/conservative-auction-cpu-initial-rejection-v2.json`.
The preparation now applies the exact frozen `sealed-policy-beliefs.cjs.publicState`
conversion used by the public arena. **All 100 legal menus match after projection**;
private deck, seed and sealed bids are absent, and permitted public money remains.
No old fixtures, policies or execution source were modified.

Six tests pass for deterministic complete fixture selection, private-input
rejection, source tampering, incomplete local reference and duplicate target
launch guards. Local replay is the first end-to-end test of the new harness.

## Current local reference and next steps

- Entry: `strong/benchmark-conservative-auction-8840u-v2.py`.
- Runner: `strong/conservative_auction_cpu_v2.py`.
- Preparation: `runs/conservative-auction-8840u-prepared-v2/`.
- Local reference: `runs/conservative-auction-8840u-local-v2/`.
- **PID 1904528 / exec session 24932**, started 20:00:36 UTC.
- At 20:03 UTC: process command verified live, **155/300 requests completed**.
- Local processor is **HX 370**, not the user's 8840U. Do not report its timings
  as target performance. Do not score/interpret partial benchmark results.

Package SHA-256:
`d179c066ff69243bb81d3c7ae0d9bf9999350db0bb879a9317974d2d50db7f78`.
Benchmark manifest SHA-256:
`c6e1698208bdda2ab19d8d4e1f1e23e145bd16f882fcc535428729f056856bb3`.
Runtime manifest remains
`a2047543f5f6a8065dd9b868dd4551531147185068c665900691c5b13c278619`.
Keep the prepared runner/manager unchanged while the run is live.

Once the original local run completes, inspect its process/status and full log.
If it fails, preserve the failure; do not overwrite/retry blindly. If all 300
requests pass, execute `benchmark-conservative-auction-8840u-v2.py launch` once.
It refuses an existing target guard, verifies the local reference and transfers
to `/home/coyotte508/powergrid-ai-conservative-auction-8840u-v2`. It uses the
existing target venv and separate HF import dependencies with Hub offline mode;
no environment changes or HF job submissions are needed.

Observe that original target with `inspect`; after terminal success use `collect`.
Collection independently audits all 600 local/target decision receipts and requires
exact cross-host choices, sampled worlds and terminal credits, excluding timing.
It reports cold process-plus-request cost separately from warm round trips.
All receipts are retained for per-count/rule inspection. A final chosen policy
still requires the unchanged strength gate and its complete qualification package.

The readiness archive references the existing immutable HF runtime source and
stores the benchmark additions, tests, owner recovery evidence and snapshot.
Descriptor: `strong/conservative-auction-cpu-readiness-v2.json`. The full source
artifact is already recoverable from the runtime source revision
`8f504f71b51c6ec5bc284c02b961d90923cdce88`; no rerunning games is needed.
