# Confirmation resumption after the inspected network failure

Research remains active. No policy is selected, qualified or deployed; reserved
final seeds remain unused. This continues the unchanged **944-job / 26,880-game**
confirmation study. It changes ownership after an inspected local network failure,
not the simulation source, policies, search budgets, statistics or job schedule.

## Original failure and collection

Previous coordinator **PID 2398668 / session 50170** exited at
`2026-10-29T02:36:24.845995+00:00` on a DNS `ConnectError` during a read-only
HF identity/status lookup. Its state and full log remain untouched. All 54
execution/admission pins match. All **403 original launch records** have complete
handles; none is an ambiguous submission intent. No existing job was restarted
or replaced, and this DNS error is not relabelled as a remote job failure.

With the owner confirmed absent and no competing collector, original-only
collection **session 11423** exited successfully. It independently audited
another **33 original jobs / 720 games**: **372 jobs / 15,232 games** were then
verified. The earlier single HF ERROR retains its separately admitted terminal-data
recovery; no new terminal job failure was found. There were 31 uncollected originals
and 541 never-submitted rows. Exact receipts, immutable archive references and
fresh original-handle statuses are bound by
`strong/current-auction-network-resume-review-v1.json`.

## Resumption and current owner

The new owner is **PID 3788704 / session 32582**, started at
`2026-10-29T03:12:33.664606+00:00`. At 03:13:05 UTC its actual `/proc` command
was verified live with all **471 pins unchanged**. It was collecting additional
original completions; startup counts were 372 audited / 403 submitted.
At **03:14:57 UTC**, a fresh actual-process/pin/HF inspection found **378 audited
jobs / 15,344 games**, **442 originals submitted**, and all **64 uncollected
originals RUNNING**. The 39 added submissions are never-submitted rows from the
unchanged plan. There are 502 rows still unsubmitted at that checkpoint.
Later observations belong in `strong/current-auction-network-resume-progress-v1.json`.

State: `runs/current-auction-network-resume-v1/state.json`.
Log: `runs/current-auction-network-resume-v1-first.log`.
Code: `strong/coordinate-current-auction-network-resume-v1.py`.
It holds both the old owner's lock and its own, respects either owner's STOP
marker, and uses the exact frozen collection/launch implementation. Every cycle
collects and audits before considering never-submitted rows, with at most 64 active
original jobs. Existing launch handles are never submitted again. Any failure
stops and preserves state; no automatic retry or restart is provided.

**Do not run a competing collector or launcher while this owner is live.**
An observation timeout is not a stopped process. Inspect this exact PID/session
and the original handles before acting. Do not restart either previous owner.
The old progress file `strong/current-auction-confirmation-recovery-progress-v1.json`
is now frozen as evidence; write new observations to the new progress file above.
Do not modify any of the 471 pinned inputs while the owner runs.

## Validation and durable recovery

Ten tests passed with all remote operations mocked. They cover a still-live
prior owner, changed execution pins, unknown submissions, ambiguous launch
intents, STOP markers, non-network failures, missing deliberate review, existing
resumption state, and collection failure before any submission. The first test
harness incorrectly resolved the frozen owner relative to its temporary fixture
directory; both failed log and original test file are preserved. Correcting that
fixture path changed no production code or frozen execution input.

The review rechecked the original source/admission, all existing cached receipt
and manifest bindings, every original launch handle, and fresh statuses for the
31 uncollected originals. Preparation/archive session **60893** completed without
submitting jobs, generating games or calling policies.

All **419 evidence files** are privately archived and upload/download-verified:

- Repository: `coyotte508/powergrid-ai-germany-v1`.
- Revision: `dacc0d05572417eaad2d781211a19ef6a336c509`.
- Path: `archives/current-auction-network-resume-evidence-v1.tgz`.
- SHA-256: `73f154f8623d39938a7c63a7b3d22fcfafcc4aa42466f130b68a46567d6c3ae0`.
- Descriptor: `strong/current-auction-network-resume-evidence-v1.json`.

The archive contains the stopped state/log, exact launch receipts, original-only
collection snapshot, review, code and test evidence. It references the existing
immutable game/source archives; no raw game needs regeneration. Preparation and
upload have completed: inspect their intent/outcome rather than repeating them.

## Remaining strength decision

Let the unchanged original study finish. Only after all 944 original rows are
collected should the independent complete comparison run using
`strong/compare-current-auction-confirmation-parallel-v1.py` and its frozen
readiness. Do not analyze partial win rates or tune policies on incomplete results.
Preserve every failure and adverse cell. Selection still requires the original
confirmation criteria, then a separately admitted held-out strength evaluation.

Both policies already passed the full actual-8840U serving/export proof; see
[the completed benchmark](CURRENT-FULL-SERVING-2026-10-29.md). Bind that proof to
the exact selected identity/settings if selection later succeeds. Do not repeat
the completed 5,106-request replay or change the qualification gate.
