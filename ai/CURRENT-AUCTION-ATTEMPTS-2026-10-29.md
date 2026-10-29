# Mixed-attempt confirmation checks — 29 October 2026

**20,596 / 26,880 games independently audited; 140 added this turn.**
The original retained batch has 40 verified jobs / 800 games. Latest
original states: 10 ERROR, 40 COMPLETED, 14 RUNNING. The bucket batch has
**50 submitted jobs / 1000 games**: 48 RUNNING, 2 SCHEDULING
at 2026-10-29T12:27:48.111967+00:00. 7 new fixed rows / 140 games were submitted
this turn. There are **208 untouched rows / 4804 games** left.
No failed jobs were restarted, no policies trained/changed, and no final seeds used.

All exact handles and launch hashes are in
`strong/current-auction-attempt-authentication-status-v3.json`. Earlier first-launch
records and all sources remain immutable. The shared 64-job limit includes the old
batch. Original collection session 61305 and bounded dispatch session 30545 completed.
No background coordinator started; check actual process ownership before continuing.

## What changed

`strong/current_auction_attempt_authentication_v3.py` connects the unchanged
canonical 944-row/26,880-game plan to the four actual recovery sources: the one
original-timeout recovery, 64 retained v2 first attempts, the completed first
bucket job, and 258 fixed bucket-pack rows. This preserves all 620 earlier audited
originals and their existing provenance. The ten failed v2 attempts remain explicit
missing coverage. No synthetic completion of an old coordinator is used.

The new checker binds each real HF handle, original command/configuration, selected
row, policy, legal/search audit, exact episode interval and archive to the original
plan. For bucket jobs, the global source-pack manifest and per-row bundle manifest
are distinct and checked separately. It also checks the actual sealed local archive
bytes and every member, the archived raw-review receipt and original execution
metadata. It does not repeat raw-game audits or run inference/simulations.

**23 new tests passed.** Actual integration checked one existing retained-v2 receipt
and the completed first-bucket receipt, including its versioned archive. The
complete-study entry refused current incomplete coverage before invoking recovery
review loaders or building authentication context. The new remaining-bucket backend
has not yet been exercised on a completed receipt; its synthetic metadata tests do
not substitute for that future check. No new strength statistics were computed.

Reports: `strong/current-auction-attempt-authentication-preflight-v3.json` and
`strong/current-auction-attempt-authentication-status-v3.json`. The preflight's
inventory is a historical snapshot; the status file records the newer inventory.
Evidence descriptor: `strong/current-auction-attempt-authentication-evidence-v3.json`.
The module remains a provenance adapter, not a complete comparison CLI. Complete
independent raw re-auditing and unchanged paired statistics are still required.

## Continue

Use the frozen manager and source from
[the bucket execution handoff](CURRENT-AUCTION-BUCKET-REMAINING-2026-10-29.md).
Do not repeat its preparation, source upload or first completed bucket audit.
`manage_current_auction_bucket_remaining_v3.py cycle --execute --launch-limit 64
--collect-limit 4` runs one bounded check/collection and fills available slots in the
fixed order. `--launch-limit 0` disables new submissions. The default without
`--execute` only validates. All commands use `ai/.venv/bin/python -u -B`,
`PYTHONPATH=ai/strong`, and `HF_HUB_DISABLE_PROGRESS_BARS=1`.

Collect v2 originals separately with the collection-only helper; both paths share
the original `.cycle` lock. Preserve STOP
`07a47d46a5cfb7e36b217f82b33632dd878b3b9deb56120cb8353db12e84ed53`.
Remote observation failure is unknown, not job death. Preserve any submission,
collection or promotion intent and inspect its exact outcome before acting.

Next: finish fixed untouched coverage, explicitly admit recovery for failed
transport attempts retaining their handles/logs, extend the routing for those exact
admitted recoveries, then complete raw re-auditing and the attempt-aware comparison
with unchanged strength requirements. The reserved final seed suite is still unused.
The finished 8840U export/serving replay is technical evidence, not qualification.
Goal ACTIVE; previous and current turns made progress. No candidate selected or qualified.

User communication preference: report new results and actionable blockers; do not
repeat the engine-language recap or other settled background in every update.
