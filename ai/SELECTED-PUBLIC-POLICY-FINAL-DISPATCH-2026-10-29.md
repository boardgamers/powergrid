# Final-job transport and durable submission records

`strong/selected_public_policy_final_dispatch_v1.py` supplies the submission
layer for a separately admitted final release. It binds the unchanged 320-shard
plan, full policy identity, candidate fingerprint, immutable source, resource
allocation, bootstrap and admission hash before any API call.

Twelve tests pass, including API timeouts, invalid handles, interruption between
remote creation and local receipt persistence, incomplete writes, corrupt
receipts and competing owners. A durable intent is flushed to disk before
submission. Known handles are reused. Any unresolved intent blocks all further
submissions in that ledger, including other shards. A changed release cannot
reuse its reserved namespace. Credentials and API exception messages are not
written into the ledger.

The final bootstrap keeps the exact exercised dependency setup, cached Node
binary and source archive/hash checks. Only its final command changes to the
complete-policy final wrapper. Shell syntax and setup-byte checks pass. The
first expanded test caught an added blank line before that command; it was
removed without changing the setup pin. The failed log and pre-fix code remain
preserved. Ten earlier dispatch tests passed before the bootstrap extension;
the corrected full suite passes all twelve.

This is transport evidence, **not final launch admission**. Unit API calls are
mocked. The real-source metadata check uses the earlier clearly synthetic
candidate/source/admission controls. No job, policy inference, reserved game or
production release is created. The bootstrap has not been remotely executed
with a real selected candidate.

## Remaining integration

The caller must independently verify complete confirmation, reviewed candidate
selection, full selected-policy technical evidence, and measured job sizing. It
must publish/download-verify the real immutable source and admission, enforce
the batch concurrency limit, inspect original handles and audit completed jobs
before replenishing the batch. The transport module has no CLI, token lookup,
batch scheduler, collector, selection logic or automatic retry loop. Its
`admission_sha256` is a binding to evidence already verified by its caller;
it does not establish that the evidence substantively passes.

Use the [source builder](SELECTED-PUBLIC-POLICY-FINAL-SOURCE-2026-10-29.md) and
the unchanged complete-policy final wrapper after those prerequisites pass.
Do not use the old model-only final launcher. Do not change either original
running owner or consume reserved seeds while confirmation remains unfinished.

Evidence: `strong/selected-public-policy-final-dispatch-preflight-v1.json`;
archive descriptor: `strong/selected-public-policy-final-dispatch-evidence-v1.json`.
Preserve completed tests and inspect archive intents before retrying an upload.

The 25-file recovery archive is private and download-verified at model revision
`2f7d97248c2d212d062d177430a9ccbf191ac6d1`, path
`archives/selected-public-policy-final-dispatch-evidence-v1.tgz`,
SHA-256 `bb7c23ddee7f140f24485b2bea754abe15d4578eb2aabf4335ac8cff3219daea`.
It includes the failed and corrected bootstrap checks, tests, source and generated
bootstrap, and references the earlier synthetic source-validation archive.
