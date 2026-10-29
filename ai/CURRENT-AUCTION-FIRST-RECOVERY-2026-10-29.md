# First exact-shard resource recovery

**09:18 UTC update — real live checkpoints verified.** The same HF job was
RUNNING before and after independently downloading the first ten immutable
checkpoint archives. All **11 distinct completed game/decision pairs** passed
archive/manifest hashes, frozen context, original policy/deal/seat/rule binding,
decision-log hash and complete line-count checks. Verified bytes: **187,721,150**.
Episodes: 80–89 and 92. No game outcomes were aggregated, no games/inference/jobs
were generated, and these 11 retained pairs are not counted as independently
audited confirmation games. The complete 16-game audit and final envelope's
child-liveness/transport evidence remain required before any remaining launch.

The receipt references and measured observation are in
`strong/current-auction-first-recovery-live-retention-v2.json`; the exact read-only
checker is `strong/check_current_auction_live_retention_v2.py`. Original private
checkpoint archives already retain the raw bytes. Downloads are cached under
`runs/current-auction-resource-recovery-hf-v2/checkpoints/` for final collection.
Do not repeat this successful fixed-snapshot check; the final collector must
verify all checkpoints against the completed original output instead.

The first recovery was submitted on **29 October at 08:47 UTC** as HF job
**`6ae3083f3fb22a235dd56000`**, attempt
`pg-current-recover-v2-pop-search-4p-05`. Its actual HF configuration was checked
at 08:48 UTC: **86,400-second timeout**, `cpu-upgrade`, the original Python image,
exact reviewed bootstrap and source environment. HF reported **RUNNING at
08:50:35 UTC**. Use the check command below for current status; no result is
implied by submission.

This executes only the same **16 games** from failed original
`pg-current-confirm-v1-pop-search_geo-4p-05`, handle
`6ae2c32f3fb22a235dd50586`. That original remains an explicit three-hour timeout.
It does not replace seeds, weights, search settings, rules or strength thresholds.
The original 620 audited shards / 19,764 games remain valid; the 323 other fixed
rows remain unlaunched. No reserved final seeds, selected candidate or deployment.

## Actual preparation and controls

The new supervisor wraps the byte-identical measured evaluator. Original source
revision `7db94147918597e1da1e8ee2f4bd12b96aa067b5`, archive
`strong-source-current-auction-grid-v1.tgz`, SHA-256
`bb2ef01bc09f176c62545971aa02b5e9dadc947fb14dd52ca191667ba456bfe0`,
and original descriptor SHA-256
`a4384b10eb8a4381423731bc0c315673f9214d91c1fb336aa81ef4a7102d1c5a`
stay unchanged. Four game workers, four search workers and one inference thread
remain unchanged. The checkpoint poll period is 30 seconds, with uploads only
when new complete game/decision pairs exist.

The worker validates original source, job, policy identity, immutable bundle,
prepared admission and output isolation before executing. It requires private
verified checkpoint uploads and an upload completed while the original child
was live. Failed or ambiguous uploads stop the attempt without retries. Its final
envelope contains the original raw output and checkpoint receipts; failures are
preserved and cannot silently qualify as success.

The independent collector binds the exact command and source, all 16 episodes,
every unique checkpoint's original bytes, verified archive receipts, transport
observations and final output. It then invokes the existing full raw-game and
search-receipt auditor. Synthetic positive tests mock that auditor and remote
transport; they are engineering evidence, not proof that this new job passed.
The actual recovery must still pass the real auditor after termination.

Validation completed:

- 14 worker tests and validation against the **actual frozen source**. The
  original development runner validated the exact failed shard without running
  games. Execution without prepared admission was rejected.
- 11 independent-envelope collection tests: changed command, incomplete or
  duplicate retention, checkpoint/final disagreement, failed child, ambiguous
  uploads, missing in-flight retention and original audit failure all reject.
- 10 launcher tests: exact allocation, no duplicate submission, ambiguous API
  response, competing lock, actual HF configuration mismatches and secret-free
  status projection. HF requests were mocked in tests.
- Earlier retention tests and the real private upload/download of an existing
  game remain recorded separately. They were not repeated.

The manager has only one admitted attempt. It cannot launch the remaining grid.
An exclusive launch intent is durable before the API call; an unknown outcome
must be reconciled, never retried. The submitted handle was saved before checking
the remote allocation. Actual HF responses are reduced to public binding checks;
no credentials or full environment responses are saved.

## Immutable preparation and published supervisor

Preparation evidence, 29 files, was upload/download verified in private model
repo `coyotte508/powergrid-ai-germany-v1`:

- Revision: `55423a8cb56683a99ba004c7842107dbba36ddac`
- Archive: `archives/current-auction-resource-preparation-evidence-v2.tgz`
- SHA-256: `4e7e6a98d4bd9c6237005ed825320c9f012c731f138355c3f8f9a46a20b81332`
- Descriptor: `strong/current-auction-resource-preparation-evidence-v2.json`

The separately published supervisor bundle is in private dataset
`coyotte508/powergrid-ai-training-v1`:

- Revision: `778bae6ba409236528ff2e059de38a9e42423241`
- Archive: `strong-source-current-auction-resource-supervisor-v2.tgz`
- SHA-256: `97d4722af31a5146845419f0302ba91403b39f50d3f18e36e73a6eb75b3aa170`
- Manifest: `632d61da5f80863171f7c3fecb91b6d143e63aeea4a47400e5f283977fcee064`
- Admission: `4d73833e2e93f21d295bc602b7d327ff3aea5bce6817d8c92827ccada5c91951`
- Descriptor: `strong/current-auction-resource-supervisor-source-v2.json`

The original dependency/source setup prefix has SHA-256
`acaa414b8e917cbfd5642b28c45802c7673f18e1f08c1a6a33d02396bd435f68`.
The reviewed full recovery bootstrap has SHA-256
`604c628ebd57b1d09c6d377e0e501c9c87e4aa0fae10195f116aafe00b13b426`.

Local preparation and run metadata:
`runs/current-auction-resource-recovery-prepared-v2/` and
`runs/current-auction-resource-recovery-hf-v2/`.
All 471 original owner pins and 621 original launch guards were verified unchanged.
Old coordinators/collectors stay stopped; there is no new local launching loop.

## Resume order

Use the existing handle; do not run prepare, upload or launch again:

```sh
ai/.venv/bin/python -u -B ai/strong/manage_current_auction_resource_recovery_v2.py check
```

While pending/scheduling/starting/running, leave the exact job alone. `check`
supports status observation without interpreting a scheduling stage as failure.
The frozen collector accepts PENDING/RUNNING as waiting, rejects other unknown
stages without submission, and should be used after actual terminal status:

```sh
ai/.venv/bin/python -u -B ai/strong/manage_current_auction_resource_recovery_v2.py collect
```

Successful independent collection writes
`strong/current-auction-resource-recovery-results-v2.json` with 16 verified games
and references to every immutable checkpoint. HF failure or missing evidence
remains a failure; no replacement is launched automatically. Read the saved
terminal log and archived partial evidence before deciding any next action.

Only after that technical recovery gate passes can the same external controls
be extended to the fixed 323 never-submitted rows. No win-rate criterion admits
recovery. Reconcile all 944 canonical shards / 26,880 unique games before comparing
the confirmation arms or choosing a candidate. Keep the unchanged reserved final
strength gate separate and unused until justified selection.

Previous goal turn: **no progress** (informational Rust recap). This turn:
**progress** (verified actual preparation, source publication and one exact-shard
submission). Research remains active and unqualified.
