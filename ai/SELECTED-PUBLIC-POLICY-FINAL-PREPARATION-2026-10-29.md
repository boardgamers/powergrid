# Preparing a selected policy for the reserved evaluation

**29 October 2026 — workflow implemented and tested; no actual candidate selected.**

`strong/prepare_selected_public_policy_final_v1.py` connects the completed-results
selection gate to candidate freezing, immutable selection evidence and final
source publication. It contains no job-submission API or game execution. Actual
preparation remains blocked by incomplete confirmation. The final batch manager,
collection integration and complete independent strength assessment remain work
to finish; passing these engineering tests is not playing-strength evidence.

## Preconditions and allocation

The first operation is the existing selection verifier. It requires all original
944 jobs / 26,880 games, independent comparison, the unchanged strength checks,
a substantive review of every adverse cell and the full native/export/8840U
proof. Only a selected policy with that same complete identity may proceed.
Conflicting or changed evidence hashes are rejected.

The resource plan uses all 672 completed selected-arm cost records, binds each
to its original handle and game count, and retains the complete runtime pilots
as a cost floor. It keeps the measured four game workers, four search workers
and one inference thread on `cpu-upgrade`. It takes the slowest observed cost
per game for each player count, doubles it, adds 900 seconds, and uses a timeout
with 25% headroom. More than 24 hours or insufficient doubled memory headroom
blocks admission. These are planning allowances, not guaranteed upper bounds.

All **320 original final shards / 20,160 games** retain their reserved schedule,
opponents, deals, seats and rule coverage. No game is created by planning.

## Preparation and publication

Preparation archives the actual review, full comparison (including immutable
original-job archive references), source descriptor, technical results and
recovery descriptors. It freezes the candidate bytes only after that private
selection archive has been uploaded and downloaded/hash-verified. The existing
source builder copies the complete policy and constructs all final controls.

Publication re-runs the selection/readiness check, verifies the bundled full
policy identity, candidate/selection archive binding, every job control, every
worker allocation and the complete source manifest. Release format is checked
before upload. The source tarball is created exclusively, uploaded to the private
training dataset and verified at the returned immutable revision before writing
an admission/release descriptor. This publishes a research source archive only;
it does not publish game changes or submit evaluation jobs.

Preparation and source upload have separate durable intents. Existing or partial
preparations, archives and uncertain upload outcomes must be inspected; repeated
invocations cannot silently overwrite or upload again. A successful upload whose
download verification fails retains its original receipt without issuing a
release. There is no automatic recovery/retry operation in this helper.

After the original owner has completed, run the existing independent comparison
with the **resumed owner**, not the comparator's stopped default:

```bash
ai/.venv/bin/python -u -B ai/strong/compare-current-auction-confirmation-parallel-v1.py \
  --owner-state ai/runs/current-auction-network-resume-v1/state.json
```

Inspect existing comparison intents/results first; do not repeat a completed
audit. Only if the complete results warrant selection, write the substantive
review required by `current_auction_final_selection_v1.py`, then use:

```bash
ai/.venv/bin/python -u -B ai/strong/prepare_selected_public_policy_final_v1.py check \
  --review ai/strong/current-auction-final-selection-review-v1.json
ai/.venv/bin/python -u -B ai/strong/prepare_selected_public_policy_final_v1.py prepare \
  --review ai/strong/current-auction-final-selection-review-v1.json
ai/.venv/bin/python -u -B ai/strong/prepare_selected_public_policy_final_v1.py publish
```

These are future operations: that review and the actual preparation directory
do not exist as part of this engineering work. A failing strength comparison
must not be bypassed to use the reserved seeds.

## Completed verification and recovery

All **16 tests passed**, covering resource coverage/provenance, measured
concurrency and memory/timeout limits, full controls and schedule, immutable
archive bindings, changed inputs, private storage, failed verification and
uncertain upload outcomes. Positive selection and artifact identities are
synthetic and HF traffic is mocked into temporary local storage. The tests use
real control generation, manifests, tar verification and release validation;
they execute no model, simulation or HF job.

An additional check against the **actual live study** called the real preparation
entry point. It failed with `Wait for all original confirmation jobs before
selection` after exactly one owner-state read, before reading outcomes or
calling the preparation API. No actual preparation directory was created.
All **471 frozen coordinator pins** remained unchanged. At the recorded check
(05:05:29 UTC), PID **3788704** was verified live; its 05:04:35 checkpoint recorded
**464 audited / 526 submitted** originals. Preserve that owner and its handles.

- Tests: `runs/selected-public-policy-final-preparation-tests-v1-final.log`
  (16 passed). The initial 14-test log is also preserved.
- Actual negative preflight: `strong/selected-public-policy-final-preparation-preflight-v1.json`.
- Recorder: `strong/record-selected-public-policy-final-preparation-v1.py`;
  original session **5896** completed successfully. Do not rerun it.
- Recovery: `strong/selected-public-policy-final-preparation-evidence-v1.json`.
- Private model repository: `coyotte508/powergrid-ai-germany-v1`.
- Immutable revision: `85448366142104dc8aaf3c531c37d9721850d1b2`.
- Archive: `archives/selected-public-policy-final-preparation-evidence-v1.tgz`.
- SHA-256: `8543c90058a22714bb9a8abcd51c83cf3a3b73e33fabd5cb806b2b43cd5c430d`.

The 26-file engineering archive was upload/download verified and references
the existing selection, timeout and actual technical-evidence archives. Restore
the exact archives by hash; no benchmark or simulation replay is needed.

The intervening engine explanation was informational (no progress toward the
goal); this turn revalidated the live original process and completed preparation
workflow engineering (progress). Research remains active. No candidate is
qualified, no reserved seed has been used, and no production routing changed.
