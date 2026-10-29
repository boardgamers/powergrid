# Independent verification of returned final-job archives

`strong/selected_public_policy_final_collection_v1.py` now verifies one returned
job against its exact original launch, selected-policy source and immutable
archive. It is a read-only verifier, not a selector, launcher, downloader, batch
manager or qualification authority. No final games have been executed.

## What is checked

The caller must supply the original HF status explicitly as `hf_stage`;
only `COMPLETED` is accepted. ERROR, running or ambiguous executions remain
unaccepted, with no automatic recovery or retry. The original launch must bind
the same release, shard, job handle and worker allocation.

The verifier hashes the complete source/extracted trees and downloaded archive,
checks every archive member against the extracted manifest, and rejects missing,
duplicate, additional, noncanonical or symlink entries. It verifies the actual
complete-policy artifact and any learned opponent, the exact candidate/contract
bytes, wrapper/source provenance, worker allocation and policy descriptor.

It then calls the unchanged `audit_shard(..., reserved=True)` to independently
recheck every raw game and public decision, and `audit_execution_binding` to
recompute the saved execution contract. The independent result must exactly
match the saved audit, counters and game count. It rechecks source/evidence
hashes after auditing. Nothing is edited, regenerated or executed.

```python
review = verify_artifacts(
    extracted_directory, frozen_source_directory, admitted_release,
    original_launch_receipt, immutable_evidence_descriptor,
    downloaded_archive, frozen_bootstrap, hf_stage=original_job_status.stage,
)
```

The caller still must verify the substantive selection/admission evidence,
download from the stated immutable HF revision, bind the queried status to the
original handle, and enforce unique original handles across the full batch.
This function deliberately returns `qualified: false` and does not claim that
it independently verified selection or launch admission.

## Validation scope

**16 tests passed.** They use the actual source-control producer, wrapper
lifecycle and execution-binding validator. Subprocess execution, artifact
identity and the raw-game auditor are mocked for these synthetic transport tests.
They cover archive tampering, bad provenance, ambiguous launches, failed remote
jobs, candidate replacement, changed execution settings, independent-audit
disagreement, duplicate/symlink archive entries, source mutation during audit,
missing files and preservation of failed evidence.

A separate check used the **real frozen source package and actual policy
artifact**, with its existing synthetic candidate/dispatch controls. Mocked
subprocesses created a deliberately false completion summary with no games.
The real collection verifier passed the source/archive bindings, reached the
real independent raw auditor, and correctly rejected it with
`Missing/duplicate episodes`. This is negative integration evidence, not a
successful audit of real final games. No actual subprocess, inference, game,
HF job or reserved seed was executed by this preflight.

Evidence:

- `strong/selected-public-policy-final-collection-preflight-v1.json`
- `runs/selected-public-policy-final-collection-preflight-v1/`
- `runs/selected-public-policy-final-collection-tests-v1-stage-worker-binding.log`
- `runs/selected-public-policy-final-collection-preflight-v1-first.log`

The first 14 tests also passed. Code review then added explicit original-HF-stage
and executed-worker/descriptor checks, with two more tests. The earlier code,
test file and log are preserved. Synthetic fixture metadata is explicitly
labelled and must never be used as actual final-game evidence.

## Archive and remaining integration

All **38 evidence files** are privately archived and upload/download-verified
in `coyotte508/powergrid-ai-germany-v1`, revision
`0ff65717751ccee3eb3722c5350712c81a2201f6`, path
`archives/selected-public-policy-final-collection-evidence-v1.tgz`, SHA-256
`8cde6e023872690e1042a4cab4184eacc4ebfa5a71c7de368fb1e3ea0dab6e93`.
Descriptor: `strong/selected-public-policy-final-collection-evidence-v1.json`.
The archive references the existing real source package and synthetic dispatch
controls. The completed tests, rejection preflight and upload need no rerun.

After complete confirmation and reviewed selection, the real final manager must
still admit/publish the source, bind measured resource allocations, dispatch
original jobs, collect immutable archives and call this verifier. It must preserve
every failure and ambiguous submission, without replacement games. After all
320 shards / 20,160 actual held-out games are independently audited, call the
unchanged `assess_final_games` and combine its result with the separately verified
technical evidence for the exact selected complete policy. No strength criterion
has changed, and no candidate is currently selected or qualified.

The live confirmation owner and the explicit `--owner-state` needed for its later
complete comparison are in
[the network-resumption handoff](CURRENT-AUCTION-NETWORK-RESUME-2026-10-29.md).
