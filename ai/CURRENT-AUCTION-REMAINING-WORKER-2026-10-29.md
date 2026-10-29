# Remaining fixed-shard worker validation

**Update, 29 October 10:09 UTC:** the separate real preparation/admission and
publication are complete; the first 64 fixed remaining jobs are confirmed live.
See [the dispatch handoff](CURRENT-AUCTION-REMAINING-DISPATCH-2026-10-29.md).
The original validation evidence below is historical and remains unchanged.

The [first recovery](CURRENT-AUCTION-FIRST-RECOVERY-2026-10-29.md) completed and
passed its actual full 16-game audit, including all 14 checkpoint archives and
live-child transport evidence. Its exact result SHA-256 is
`b83b2dfa755d3bc0ea6500461a6ca8166724c6ce2b6071dab282798378a91940`.
The original failed handle remains preserved. Combined usable confirmation
coverage is **19,780 / 26,880 games**, not a complete strength comparison.

The remaining fixed grid consists of:

| Players | Shards | Games |
| --- | ---: | ---: |
| 2 | 16 | 256 |
| 3 | 16 | 384 |
| 5 | 131 | 2,620 |
| 6 | 160 | 3,840 |
| Total | 323 | 7,100 |

All remaining rows use the frozen hybrid arm. Four-player coverage is already
in the preserved originals and the now-audited recovery. No source row, seed,
policy, model, search setting or strength threshold was changed.

## New component and actual validation

`strong/current_auction_remaining_resource_job_v2.py` admits only decision rows
marked `never_submitted`. It rejects the failed original, its recovery and all
already-submitted originals. Each new attempt name replaces the original
`pg-current-confirm-v1-` prefix with `pg-current-retained-v2-` and normalizes
underscores to hyphens; all 323 names were checked unique.

The worker uses the unchanged original measured evaluator, original raw folder
name, four game workers, four search workers, one inference thread and tested
30-second retention core. Final envelopes preserve original raw bytes and unique
checkpoint receipts; failures/unknown uploads stop without retries. It does not
contain an HF job submission API.

Actual execution requires both the exact completed first-recovery result and a
separately reviewed remaining-grid admission. The first-result gate checks the
known job/failed handle, original policy, uncapped full raw audit, immutable
checkpoint coverage, successful HF controls, exact first supervisor and frozen
collector/manager hashes. The future admission must bind actual bundle bytes,
first-result hash, original source/decision, resources and private preparation
evidence. Default CLI operation validates only.

**Ten tests passed**, using actual tracked remaining-row metadata and synthetic
first-result positives. The actual source preflight checked **all 323 job specs,
candidate policies and contracts** against the full original manifest. It then
ran the new worker's validation-only CLI and the original development runner's
validation-only CLI for one actual shard at each remaining player count: eight
commands total, no output/game creation. Before the first recovery collection,
all four real execution checks correctly rejected its then-missing audit.

After the real first recovery finished and was independently collected, the same
new metadata gate **passed against the actual result**, without replaying games,
inference or the completed raw audit. This proves the first-result prerequisite;
it does not admit a remaining worker for execution yet.

Evidence:

- `strong/current-auction-remaining-worker-preflight-v2.json`
- `strong/current-auction-remaining-worker-first-gate-v2.json`
- `strong/current-auction-resource-recovery-results-v2.json`
- `runs/current-auction-remaining-worker-tests-v2-first.log`
- `runs/current-auction-remaining-worker-preflight-v2/` (unadmitted preview bundle and eight logs)
- `strong/current-auction-remaining-worker-evidence-v2.json` (private engineering/audit metadata archive)

Do not repeat successful tests, source validation, first collection or the real
first-result check. The actual first recovery is terminal; there is no live job
to wait on. The old original coordinators remain stopped.

## Next required work

1. Implement/test independent collection for the new worker's variable 16/20/24
   game envelopes. Preserve the same original full raw verifier, exact context,
   checkpoint/final equality, live-child retention and original source binding.
2. Prepare and privately archive actual remaining controls, including the real
   first audit. Publish a new immutable supervisor source; the current preview
   has no first-result/admission files and is not executable.
3. Add durable once-only launch/collection control for the fixed rows in recorded
   order, at most 64 active jobs, `cpu-upgrade` and 24-hour limits. Verify actual
   HF settings; preserve ambiguous submissions and stop on failures without
   automatic retries. Do not alter any first-recovery or original launch record.
4. Connect authenticated original/recovery receipts and full raw re-auditing to
   the [canonical coverage component](CURRENT-AUCTION-RECOVERY-COVERAGE-2026-10-29.md),
   then the unchanged complete paired comparison and strength/selection gates.
   Never fabricate completion of the stopped original owner.

This turn generated/submitted no new games/jobs. Source publication and remaining
execution are still unadmitted. Previous goal turn: progress (real live retention).
This turn: progress (actual recovery completion/audit and remaining-worker
implementation with real source validation). Goal active; no qualified candidate,
reserved final seeds or deployment.
