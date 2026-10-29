# Final evaluation collection and dispatch

**29 October 2026 — runner implemented and tested; actual final admission blocked.**

`strong/manage_selected_public_policy_final_v1.py` connects the already-tested
source preparation, original-only dispatch and streaming raw auditor. It does
not select a policy, train, replace jobs or qualify a model. The incomplete
confirmation study still blocks actual use before network calls or creation of
the final-run directory.

## Admission and original-only operation

Admission first requires the completed original confirmation owner, then re-runs
the substantive selection/technical gate. It verifies the prepared candidate,
all 320 controls, measured allocations, admission and release, exact bootstrap,
source upload receipt and both immutable HF archive hashes. It freezes the
manager dependencies and complete source/evidence file hashes into a context.
The full 20,160-game schedule remains unchanged.

Each collection/dispatch operation takes one exclusive lock, respects `STOP`,
and checks the frozen context. It reads every original launch receipt, rejects
ambiguous submissions or duplicate handles, and inspects the original HF handles.
Completed jobs are downloaded and independently audited before new jobs may be
submitted. A second status pass catches jobs finishing during collection and
defers dispatch until their evidence can be collected. At most 64 original jobs
are active; only never-submitted rows can be dispatched.

Collection retains the original log and compressed archive. It uses the existing
streaming auditor, saves the full audit durably and removes only that successful
temporary extraction. Polling checks saved receipt bindings and original archive
presence/size; it does not repeatedly hash every compressed archive. Raw archive
hashing happens during initial collection and must happen again in the separate
final independent audit.

An original HF failure, missing/ambiguous archive receipt, changed source,
interrupted collection or uncertain submission stops work for inspection. A
failed job's available log/archive is preserved and is not treated as a win or
a completed game. The halt record stores the failure type, not arbitrary API
error text or credentials. Neither this helper nor its CLI automatically retries,
restarts or replaces a job. Preserve failures, original handles and partial data.

The runner performs a bounded cycle per invocation. It is not a new background
coordinator. After actual reviewed source publication, its commands are:

```bash
ai/.venv/bin/python -u -B ai/strong/manage_selected_public_policy_final_v1.py check
ai/.venv/bin/python -u -B ai/strong/manage_selected_public_policy_final_v1.py collect
ai/.venv/bin/python -u -B ai/strong/manage_selected_public_policy_final_v1.py advance --execute
```

`collect` cannot submit jobs. `advance --execute` first collects/audits original
results and then fills free slots with remaining original shards. Any halt must
be inspected and deliberately reconciled; there is no bypass/retry CLI. Do not
invoke advance now: confirmation, the comparison, selection and actual source
publication are still incomplete. The real final-run directory does not exist.

## Verification completed

All **16 focused manager tests passed**, covering:

- Admission bound to published preparation, complete controls and release;
  changed admission flags or source receipt rejected.
- The concurrency limit, original handle reuse, collection-only behavior and
  collection before dispatch, including completion during the collection cycle.
- Ambiguous submissions, duplicate handles, network failures, explicit stops,
  competing operations and changed frozen inputs.
- Real dispatch ledger and streaming collection integration with synthetic
  artifacts, archive retention, receipt mutation, duplicate evidence and HF failure.
- All 320 original shards accounted for as 20,160 games, while qualification
  remains false pending the separate independent audit and strength assessment.

Positive selection/identities, HF APIs and raw game-audit inputs are mocked.
The tests execute no model, engine simulation or actual HF job. An initial test
discovery also ran 40 existing fixture-class tests (55 total, all passed); imports
were then scoped to the manager suite and the full-completion test was added.
Both logs are retained. These are engineering checks, not strength evidence.

At **05:16:44 UTC**, the real admission entry point was checked against the live
study. It rejected after exactly one owner-state read, before any outcome read,
API construction, download or token lookup. Neither actual preparation nor final
run directories were created. Coordinator **PID 3788704 / session 32582** was
verified live with **471 unchanged pins**. Its 05:15:45 checkpoint recorded
**469 audited / 533 submitted** of 944 original confirmation jobs.

## Recovery and next actions

The 28-file engineering archive was privately uploaded, downloaded and hash
verified. It contains the recorder, code, test fixtures/logs, negative actual
preflight and original-owner snapshot, and references the existing preparation
and streaming proof archives.

- Report: `strong/selected-public-policy-final-manager-preflight-v1.json`.
- Descriptor: `strong/selected-public-policy-final-manager-evidence-v1.json`.
- Recorder: `runs/record-selected-public-policy-final-manager-v1.py`, original
  session **47444**, completed successfully. Do not rerun it or its archive upload.
- Model repository: `coyotte508/powergrid-ai-germany-v1`.
- Revision: `ec74b2b8f689f905d5c583f0465c3732e08e9e9c`.
- Archive: `archives/selected-public-policy-final-manager-evidence-v1.tgz`.
- SHA-256: `6f9052ed3a3bbf7508f2a49acfc8cb7d9f3d08692645725c1fb9773f1df9c0ce`.

Finish the unchanged confirmation and its complete independent comparison before
selecting anything. If selection passes, freeze/publish the real source using the
preparation handoff and verify actual manager admission before executing. After
all original final jobs finish, re-audit every original compressed archive in a
separate pass, assess the unchanged final strength requirements, and bind the
exact selected identity to the completed native/export/AMD evidence. That final
aggregation/qualification integration remains to finish. Do not substitute the
manager's collection count for a passed strength gate.

Previous goal turn: progress (`1bc3db7`, candidate/source preparation). This turn:
progress (runner implementation, tests and actual negative admission proof).
Research remains active; no candidate is qualified and final seeds remain unused.
