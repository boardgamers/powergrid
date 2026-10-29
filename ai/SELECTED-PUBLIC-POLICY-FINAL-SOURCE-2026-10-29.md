# Portable source for the complete-policy final evaluation

The offline builder in `strong/selected_public_policy_final_source_v1.py`
packages the separately selected policy for the unchanged **320 shards / 20,160
held-out games**. It preserves the entire standalone artifact, candidate bytes,
full search identity, paired deal/seat/rule schedule and frozen learned opponent.
It generates the inputs expected by the existing final job wrapper and runner.

This is packaging infrastructure. It cannot select a candidate, submit jobs,
execute games or grant launch admission. The current confirmation and 8840U
owners are unchanged; no reserved seeds have been used.

## Validation

<!-- VALIDATION-STATUS-BEGIN -->
**Seven unit tests and all 320 real-artifact contract validations passed.**
The original validation, PID 3082651 / session 36178, exited successfully.
It used the actual frozen hybrid artifact and the clearly labelled synthetic
candidate from the previous transport preflight. No policy calls, game moves,
HF submissions or execution output directories were created. Preserve the
successful original logs and receipts; no rerun is needed.
<!-- VALIDATION-STATUS-END -->

The tests cover all original shards, exact candidate-byte hashes, complete search
settings, freeze chronology, missing selection evidence, complete integer worker
allocations, path traversal, symlinks and preservation of existing partial output.
All 320 source contracts are checked by the copied job wrapper and the actual
frozen final runner, in separate validation-only subprocesses. Neither
`--execute` nor `--upload` is passed. Their expected execution output directory
must remain absent.

The synthetic controls and their four-game-worker allocations are **test fixtures
only**, not a real candidate selection or measured resource plan. Their selection
archive reference is deliberately fake. Never publish this validation bundle as
an HF execution source or execute its contracts.

Evidence:

- `strong/selected-public-policy-final-source-preflight-v1.json`
- `runs/selected-public-policy-final-source-preflight-v1/validations.jsonl`
- `runs/selected-public-policy-final-source-preflight-v1/validation-logs/`
- `runs/selected-public-policy-final-source-tests-v1-first.log`
- `runs/selected-public-policy-final-source-preflight-v1-first.log`

## Actual integration after selection

1. Finish all 26,880 confirmation games and the independent complete comparison.
   Review every regression and the unchanged confirmation requirements before
   selecting and freezing a candidate. Preserve failures and do not tune using
   partial or reserved results.
2. Finish the original 8840U replay, collect/audit it and bind saved proposals to
   the independently verified checkpoint. Bind all technical evidence to the
   same selected complete-policy identity.
3. Derive the real per-shard game-worker allocation and HF resources/timeouts
   from complete measured execution costs. Game concurrency is separate from
   the already-frozen policy search workers and inference threads.
4. Call `build(artifact, descriptor, candidate_path, workers, output)` with the
   real frozen candidate and a complete worker mapping keyed by the unchanged
   schedule's shard names. The builder writes exclusively, preserves failures
   and emits a full file manifest. It does not validate the substantive contents
   of selection/technical archives: that remains an explicit launch prerequisite.
5. Validate and independently admit the real source, then publish its immutable
   archive. The separate original-only launch manager still needs integration:
   bind source/selection/technical evidence and every original launch intent;
   reconcile ambiguous submissions rather than retry them. Only then execute
   the reserved plan and apply the unchanged final strength gate.

Do not use the old model-only `launch-final.py` for this complete hybrid. The
portable wrapper is documented in
[the final-job handoff](SELECTED-PUBLIC-POLICY-FINAL-JOB-2026-10-29.md).

## Immutable recovery archive

The 986-file proof is privately archived and download-verified at model
revision `acb27a6a3ad95960bc713ea8a9ea12a83338f2a4`, path
`archives/selected-public-policy-final-source-evidence-v1.tgz`,
SHA-256 `9252d1158c4aaa3c136b5b563c917ecd3f2d9e1dea9fb1b9ddd82553ff61d3ff`.
Descriptor: `strong/selected-public-policy-final-source-evidence-v1.json`.
The archive preserves all synthetic controls and validation logs, referencing
the unchanged immutable confirmation source for the artifact bytes. It is an
evidence archive, never an admitted final execution source.
