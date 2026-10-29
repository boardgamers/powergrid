# Canonical confirmation coverage across original and recovery attempts

The actual frozen schedule has **944 disjoint shards / 26,880 unique games**.
The new coverage component verified the complete metadata partition without
opening game outcomes:

| Disposition | Shards | Games |
| --- | ---: | ---: |
| Preserved audited originals | 620 | 19,764 |
| Same-seed recovery of the failed original | 1 | 16 |
| Fixed rows never submitted | 323 | 7,100 |

Original HF status accounting remains **617 COMPLETED and four ERROR**: three
ERROR jobs had independently verified complete raw data; the fourth is the
preserved incomplete timeout. Coverage never turns that timeout into a successful
original or counts its unavailable game messages as results.

First recovery remains the exact admitted handle **`6ae3083f3fb22a235dd56000`**,
attempt `pg-current-recover-v2-pop-search-4p-05`. HF reported RUNNING at
**09:09:12 UTC**, with the admitted 86,400-second timeout and unchanged command,
source environment and hardware. This work submitted zero jobs and ran no games
or inference. The original first-recovery controls and worker remain immutable.

## Implemented and exercised

`strong/current_auction_recovery_coverage_v2.py` constructs the canonical partition
from the exact original source descriptor, final terminal collection and recorded
resource decision. It binds the current first-recovery handle and immutable
published supervisor. It checks disjoint original dispositions, all fixed recovery
rows, unique original handles, unchanged row hashes, confirmation-only seeds and
nonoverlapping `(arm, group, episode)` keys.

Its assignment gate requires every missing canonical shard before invoking a
review loader. It rejects missing, duplicate or extra assignments, changed game
rows, original/reused handles, replacement of the first recovery, running or
unverified attempts, wrong loaded identities, substituted episodes and capped
receipts. A positive metadata result still has `statistics_admitted: false` and
requires independent raw re-auditing.

**Twelve focused tests passed**, using a small synthetic partition and mocked
review loading. The real metadata preflight also passed. Both an empty recovery
assignment list and a reference to only the actual first recovery were rejected
before any review loader call. No partial win rates were computed. These checks
do not assert that the recovery job or remaining grid has completed.

An initial ten-test version was reviewed and strengthened to pin the actual first
recovery handle before recording this result. Its code, tests and initial
preflight are preserved under
`runs/current-auction-recovery-coverage-preflight-v2-before-handle-pin/`.
The final proof uses the twelve-test log
`runs/current-auction-recovery-coverage-tests-v2-handle-pin.log`; do not rerun it
or the successful real preflight without a relevant change.

## Evidence and next steps

- Final report: `strong/current-auction-recovery-coverage-preflight-v2.json`.
- Complete canonical metadata: `runs/current-auction-recovery-coverage-preflight-v2/plan.json`.
- Private recovery archive descriptor: `strong/current-auction-recovery-coverage-evidence-v2.json`.
- Original execution/recovery instructions: [first recovery handoff](CURRENT-AUCTION-FIRST-RECOVERY-2026-10-29.md).

The coverage component does not replace the old comparator or its selection gate.
Those original paths require the original coordinator to report completion; do
not fabricate that status. The future integrated path must authenticate recovery
launch/admission/receipt references, independently re-audit all original and
recovery raw games, then run the unchanged paired analysis and strength gates.
The loader contract in this component explicitly requires that authentication;
a list of metadata flags alone is not evidence of completed games.

Next, check only the existing recovery handle and collect it after terminal
status. Its actual 16-game audit and live-child retention evidence must pass
before admitting the fixed remaining 323 rows. Then use this canonical partition
to reconcile all 944 shards before comparison. No candidate selected/qualified,
reserved final seeds used, new training or deployment.

Previous goal turn: **progress** (actual first-recovery submission). This turn:
**progress** (coverage implementation, tests and actual metadata/rejection proof),
with a verified wait on the same running recovery. Goal remains active.
