# Corrected v4 runtime package — prepared, not launched

**28 October, 18:31 UTC — corrected v4 runtime pilots launched.**

The six originals are terminal: five audited successes / 88 games and one
preserved failure; their 96-game success gate failed. After reviewing measured
costs (maximum 3.44 h workflow and 6.066 GB sampled peak RSS), the separate
admission launched exactly two corrected v4 jobs / 32 runtime-only games,
with six-hour limits and no automatic retries. See the
[admission and recovery record](RESOURCE-RUNTIME-ADMISSION-2026-10-28.md)
for exact handles, source hashes and the v4 collection command. The preparation
notes below retain their historical state; no candidate is qualified and final
seeds remain unused. Complete the separate auction comparison before selecting
another strength study.

28 October 2026. Research remains active. No new HF jobs, complete evaluation
trajectories, gradients or reserved final seeds were used by this preparation.

The v4 boundary-corrected policy is now packaged with the full-game runner,
independent auditor, exact job specifications and measured wrapper. This is
preflight evidence, not a passed fresh runtime study or a playing-strength gain.

## Planned scope and execution boundary

Two proposed HF jobs contain **32 runtime-only games**: anchored atomic search,
eight games at two players and 24 at six players, one complete paired deal per
count, every seat and original/Recharged × open/sealed. The opponent remains
`search_geo`; seed prefixes are `resource-turn-runtime-v2-{players}p`, separate
from original runtime handles and reserved qualification seeds. Four games run
concurrently within each job; the frozen policy uses eight worlds, one search
worker, one ONNX thread and a 2,400-step horizon.

There is also an eight-game **local-only recorded control** using the frozen
filtered model and its existing reference games. It is excluded from the two
HF jobs. Its upload path is explicitly rejected.

There is **no actual HF admission, source upload for execution, launch manager,
job handle or selected timeout** for this v2 study yet. The protocol records
the three completed original calibrations, but leaves the timeout unset.
The remaining original atomic six-player jobs were directly observed RUNNING;
their latest log reports were 15/24 and 16/24 games. Those counts are progress
only, not audited outcomes, runtime extrapolations or strength evidence.

Experimental `--execute` requires a separate admission document and its SHA256.
That document must bind the exact source/protocol/two job specifications, retain
the original terminal-outcomes evidence and record the reviewed flavor,
concurrency and timeout. The future launcher must independently verify those
original outcomes and create that admission; a self-asserted JSON document is
not evidence that the original jobs have finished. The wrapper checks its
binding and format, not HF's live state. No user approval is being requested.

Synthetic admission fixtures in `runs/resource-runtime-admission-checks-v2`
are labelled **dry-test data only** and deliberately use a dummy original
outcome hash. Never use them to execute or submit jobs. Their example timeout
is not a selected runtime budget.

## Verification

`strong/prepare-resource-turn-runtime-v2.py verify` ran the exact bundled entry:

- All three job specifications passed dry validation.
- Both experimental specifications rejected execution without an admission,
  before creating an output directory or starting a game.
- The local control replayed **eight recorded games**, reproducing **all 1,360
  decisions and all terminal results** exactly.
- The full v4 game runner and independent full-game auditor passed that replay,
  with paired scheduling, zero search rollouts and zero caps.
- Measured local replay: **19.051 s wall / 84.67 CPU-s / 1,678,475,264 bytes**
  sampled peak process-tree RSS, 93 samples at 0.2-second intervals. This is
  local wrapper verification, not a forecast for expensive anchored search.

`strong/check-resource-runtime-admission-v2.py` passed **12 further checks**:
validation-only acceptance of a correctly shaped synthetic document; rejection
of a different source, live-original flag, invalid evidence hash, missing
preservation claim, development scope, retries, changed job set, excessive
timeout/concurrency, changed admission bytes and uploading the local control.
These checks run no inference or simulation and make no HF calls.

The initial preparation stopped before creating the package or protocol because
a version-name substitution incorrectly changed the paths of three historical
calibration receipts. Its exact sources and log are preserved under
`runs/resource-turn-runtime-prepared-v2-initial`. Correcting those read paths
did not rerun any completed game; the recorded-control replay ran once, after
the corrected package was prepared.

## Exact recovery artifacts

- Package: `runs/resource-turn-runtime-prepared-v2/source` (1,510 manifest entries).
- Protocol: `strong/resource-turn-runtime-protocol-v2.json`.
- Protocol SHA256: `72f43b24137d18d578b694dd74aba1b0ea5e96864e62ab76cd80a313c15dff95`.
- Source manifest SHA256: `7678b22c535648280394cb7374c926bfcb2ea88da5c2d8b35100cda64a3c299a`.
- Bundled entry SHA256: `28fc4f09a1ade8c7e4d8b49612eee06561d7cceb256798b77f4baad9e9afe474`.
- Prepared descriptor SHA256: `2a4399fb656d4e4a765ad5826a8b8f51f0e874dda99206209e394b90e9dc6bf8`.
- Replay verification SHA256: `8516a6f00f965aaa756af16db010c308d0cc03d504eb1fc102daab01613414f4`.
- Admission-check assessment SHA256:
  `519ee34bcd398604b7edb7542e7c6be5aa150580b2c105647ac91b888193364e`.

The v4 artifact, model and runtime pins remain those in
[the policy integration handoff](RESOURCE-TURN-BOUNDARY-POLICY-2026-10-28.md).
`strong/archive-resource-runtime-preflight-v2.py` archives the complete exact
prepared source, replay receipts, test fixtures, initial failed preparation,
current helpers and recovery metadata to the existing private HF model repo.
The immutable revision and download-verified hashes are recorded in
`strong/resource-runtime-preflight-evidence-v2.json`. An evidence archive is
not an HF execution admission or a launch receipt.

## Next actions

Keep collecting the remaining original handles with the existing collection-only
tool. Preserve failures and timeouts as outcomes. After all originals are
terminal, use their measured costs to decide whether the corrected 32-game
runtime study is worth admitting and, if so, set its bounded runtime budget and
build a separately tested single-attempt launcher. Do not blindly repeat this
preparation, verification or any original job.

The unchanged auction comparison remains the strength study in progress; finish
its complete comparison before selecting another strength study. No candidate
is qualified, no final seeds are used, and nothing is deployed.
