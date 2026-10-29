# Final evaluation storage: compressed originals and temporary audits

**29 October 2026 — storage lifecycle verified, no final games executed.**

The current storage measurements make retaining every expanded final job
impractical. At 04:04 UTC, 415 independently audited confirmation jobs contained
16,192 games. Extrapolating the remaining unchanged confirmation from observed
per-arm maxima leaves approximately **259 GB** available. The estimates include
the existing two- and six-player runtime pilots, and use decimal GB.

| Final storage option | Fast policy | Auction-search policy |
| --- | ---: | ---: |
| Keep all expanded evidence and compressed originals | 293 GB | 340 GB |
| Keep compressed originals, receipts and four temporary extractions, including a 50% margin | 33 GB | 41 GB |

These are capacity estimates, not hard upper bounds. They do not analyze partial
game outcomes or select a candidate. The unchanged final plan still contains
320 jobs / 20,160 held-out games. Existing confirmation evidence remains intact.
The observations and arithmetic are in
`strong/selected-public-policy-final-storage-review-v1.json`.

## Implemented lifecycle

`strong/selected_public_policy_final_streaming_v1.py` takes an already available
original compressed archive and uses the independent final-job verifier. It:

1. Checks the pinned archive and its actual expanded size, with a default
   16 GiB free-space reserve before extraction.
2. Extracts into a unique temporary directory and verifies every manifest member.
3. Performs the full source, launch, contract and raw-game audit.
4. Writes and fsyncs the complete audit receipt before deleting its own
   temporary extraction. The compressed original remains available.

Failures retain surviving scratch evidence and an inspection record. An existing
receipt prevents an accidental repeat or overwrite, including after a cleanup
failure. A separate independent audit must use a separate receipt and verify the
raw archive again. The helper has no HF submission, simulation or network API.
It does not establish selection/admission or qualify a policy.

## Validation completed

All **eight storage tests passed** in
`runs/selected-public-policy-final-streaming-tests-v1-first.log`. They cover
successful cleanup, preservation of unrelated files and original archives,
insufficient disk space, raw-audit failures, receipt-write failures,
cleanup failures, independent re-auditing, archive mutation and receipt location.
The transport fixtures are synthetic; they do not count as actual final games.

A separate storage preflight used an existing completed ordinary confirmation
archive: `pg-current-confirm-v1-pop-search_geo-3p-00`, original HF handle
`6ae2ab0f41e90535df781447`. The preflight-only adapter called the unchanged
confirmation raw verifier instead of the final verifier, because this archive
contains confirmation games. It reproduced the original independent audit for
**all 24 games**, then removed its temporary extraction. The original compressed
archive, original expanded evidence, source and all 471 coordinator pins remained
unchanged. No game or inference was rerun; no HF job or reserved seed was used.

The archive is **18,860,387 bytes** compressed and **275,269,709 bytes** expanded.
The storage preflight took **5.826 seconds** on this workstation. This one
observation is not a general throughput benchmark. Completed session: `73360`.
Report: `strong/selected-public-policy-final-streaming-preflight-v1.json`.
Do not repeat the completed tests or preflight.

Original raw evidence remains at private model repository
`coyotte508/powergrid-ai-germany-v1`, revision
`1dd204b7481129125c3e20c157b39c80adabf93c`, path
`archives/pg-current-confirm-v1-pop-search_geo-3p-00.tgz`, SHA-256
`8ccfe3131c336ed5d58f8b563596e60d5ed69851d7d4a04d758ff76e1347733d`.

## Recovery archive and next action

All **27 supporting files** were archived and download/hash verified in the same
private model repository, revision `05015dc6ca6531e211a5ac91d8ed4967f1091890`, path
`archives/selected-public-policy-final-streaming-evidence-v1.tgz`, SHA-256
`e6821caac157f19429848ce90717d27a036358666e97ff3a0a4df0c1f6d35921`.
The archive references the immutable original job archive and source bundle
instead of duplicating their large contents. Descriptor:
`strong/selected-public-policy-final-streaming-evidence-v1.json`.
Completed upload session: `69131`. Inspect the existing intent and descriptor
before any recovery; do not rerun the uploader.

At **04:20:12 UTC**, sole coordinator **PID 3788704 / session 32582** was verified
live with **471 unchanged pins**. The snapshot contained **441 audited jobs /
16,664 games**, 484 submitted originals, and **42 RUNNING / 1 COMPLETED** among
the 43 not yet audited originals. Three audited originals retain their HF ERROR
status; their complete terminal data passed the existing frozen recovery rule.
No replacement games were submitted. Their handles and recovery checks are
preserved in `strong/current-auction-network-resume-progress-v1.json`.

Preserve that owner. Finish all 944 original confirmation jobs and the unchanged
paired comparison before selection. Use the explicit resumed-owner comparator
command in `CURRENT-AUCTION-NETWORK-RESUME-2026-10-29.md`. Real final admission,
source publication, measured job allocation and batch/collection integration
remain required; integrate this storage lifecycle there. The separate held-out
strength gate and full qualification remain unpassed. **No candidate is selected
or qualified, and the reserved final seeds remain unused.**
