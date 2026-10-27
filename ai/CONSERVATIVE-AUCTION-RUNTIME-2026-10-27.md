# Corrected auction runtime pilots — 27 October 2026

The research goal is active following the human's “do ai research” request.
Four new HF CPU jobs are running the corrected frozen runtime. This is a full-game
runtime regression, not the strength comparison or final qualification.

## Current jobs

All four handles were directly inspected RUNNING at approximately
**2026-10-27T19:24:14.454287+00:00**. Each has a five-hour timeout from its original
submission at approximately 19:23 UTC. No local coordinator/collector is running.

| Arm | Players | Games | Original v2 HF job | Last checked stage |
| --- | --- | --- | --- | --- |
| conservative_population | 2 | 8 | `6ae0fa243fb22a235dd31616` | RUNNING |
| conservative_population | 6 | 24 | `6ae0fa2541e90535df7674df` | RUNNING |
| conservative_dual | 2 | 8 | `6ae0fa2541e90535df7674e1` | RUNNING |
| conservative_dual | 6 | 24 | `6ae0fa2541e90535df7674e3` | RUNNING |

There are **64 planned runtime games**, one paired deal per endpoint/arm with all
seats and the four original/Recharged × open/sealed combinations. These repeat
engineering seeds from v1 to exercise the failed case; they are excluded from
strength. The original v1 run remains incomplete (three passing jobs, one error).
All original v1 guards, archives and STOP markers are preserved.

## What passed before submission

- Newly identified artifact with the two forced-prior fixes; all weights, search
  settings, thresholds, menus, sampled-world rules and final protocol unchanged.
- Five dry job-contract validations; source includes **1,524 pinned files**.
- **72 saved public decisions / 1,992 continuations** match v1 exactly after
  accounting only for the new worker hash and elapsed time.
- Recovered request `5:21` matches the corrected recovery result exactly, with
  **96 independently audited continuations and zero caps**.
- Portable measured wrapper: **eight complete control games / 1,607 decisions**
  and terminals match the original control exactly. This repeats engineering games.
- Seven launch/measurement tests pass: prior intent, no persisted credential,
  original-handle reuse, refusal to retry ambiguity, source mismatch rejection,
  exclusive launch owner, validation-only rows and finite complete measurements.
- HF source uploaded and downloaded/hash-verified before submission.

`conservative-auction-development-protocol-v2.json` changes runtime identity and
records the recovery, while preserving all development seeds, 27 cells, 10,080
games, model weights, thresholds and the reserved final gate. No threshold fitting.
The v1 protocol is untouched.

## Pins and evidence

- Source dataset: `coyotte508/powergrid-ai-training-v1`.
- Source revision: `8f504f71b51c6ec5bc284c02b961d90923cdce88`.
- Source archive: `strong-source-conservative-auction-runtime-v2.tgz`.
- Archive SHA256: `528f8ff361de6775a340ced2b2e08713a350ece12a469ed40a36b4d152471678`.
- Source manifest SHA256: `fa06eceea6b755240ed954fe887619f0ea9073520ca0bef1ad1f7bc10f3965cb`.
- Runtime manifest SHA256: `a2047543f5f6a8065dd9b868dd4551531147185068c665900691c5b13c278619`.
- Source descriptor: `strong/conservative-auction-runtime-source-v2.json`.
- Live launch snapshot: `strong/conservative-auction-runtime-launch-state-v2.json`.
- Verified launch archive descriptor: `strong/conservative-auction-runtime-launch-evidence-v2.json`;
  created only after the upload/download verification, containing its immutable
  private model-repository archive revision and hashes.
- Root recovery: [27 October diagnosis](CONSERVATIVE-AUCTION-RECOVERY-2026-10-27.md).

Resources: `cpu-upgrade`, four concurrent games per job, unchanged policy workers,
5h timeout. Planning uses 900s setup plus twice the largest observed v1 wall time
(including its failed shard as an observed cost, not as a passing measurement).
This is below 75% of the timeout. Actual v2 measurements are pending.

## Continue from these handles

Work in the AI checkout on `ai/germany-baseline`; use `ai/.venv/bin/python -B`.
The source, preparer and manager are now pinned. Preserve them while these jobs
run. Do not resubmit/restart on an observation timeout or uncertain response.
Use a bounded collection:

```bash
ai/.venv/bin/python -B ai/strong/manage-conservative-auction-runtime-v2.py collect
```

The collector verifies original guards, source and artifact hashes, independent
legal decisions/terminal credits, execution binding, complete measurements and
archive provenance. It writes `strong/conservative-auction-runtime-results-v2.json`
only when all four jobs and 64 games pass. If a job fails, preserve its raw archive
and partial receipts and inspect the original handle; never silently replace it
or score only survivors. Continue inspecting other originals read-only if needed.

After all four pass, archive completion and prepare the **v2** development
admission/source/manager using measured complete-game resources. The old v1
coordinator PID 1061599 remains intentionally stopped; do not restart it.
The old collection-only PID 1146868 is also absent. Adapt the existing development
planning to the v2 protocol/source; do not overwrite v1 outputs. The 10,080-game
comparison is still unadmitted/unlaunched, with zero development submissions.

No new gradients, new strength games, final seeds, candidate qualification or
production changes. Previous goal turn: progress (verified failure recovery).
Current goal turn: progress (validated source and four actual HF submissions),
with all four jobs directly verified running. The full strength goal remains open.
