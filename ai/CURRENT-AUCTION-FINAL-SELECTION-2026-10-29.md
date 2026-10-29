# Candidate-selection prerequisites for the current auction study

**29 October 2026 — engineering checks completed; no candidate selected.**

`strong/current_auction_final_selection_v1.py` connects the complete confirmation
comparison, an explicit adverse-cell review and the existing full export/AMD
8840U proof. It is read-only and cannot freeze a candidate, upload source, submit
jobs or qualify playing strength. It addresses the unchanged conservative
population auction policy in this study, not a new count/rule-specific policy.

## Required evidence

The public entry point is `verify(review_path)`. Its first read is the original
coordinator state. It rejects an unfinished study before opening comparison data
or a selection review. Once the study has completed, it checks:

- All 944 original jobs / 26,880 games, the frozen source, owner result binding,
  original handles and receipts, retained failure statuses, and the complete
  independent comparison audit. All pinned comparison inputs must remain intact.
- Both full policy identities and the unchanged uncertainty settings. The gate
  recomputes the existing confirmation requirements from the complete comparison:
  positive primary paired lower bound, absolute floors and every required
  count/rule lower bound above chance. A saved `passed` flag is insufficient.
- Every negative overall or rule-specific paired cell. The review must preserve
  each cell, rule and measured difference, provide an assessment, bind the exact
  comparison and policy, and postdate the completed comparison. It must explain
  the selection rationale and remaining limitations. Presence checks cannot judge
  the quality of that reasoning; the reviewer still must assess the regressions.
- The complete 2,553-position native/export proof and 5,106-request target proof,
  exact checkpoint/model/runtime/report bindings, legal moves, uncapped actual
  search, the AMD 8840U target and all 80 count/rule/phase timing cells. Saved raw
  target and native/export hashes and frozen inputs must still match.

The output `ready_for_candidate_freeze` means only that these prerequisites pass.
It also explicitly reports `candidate_created: false`,
`final_launch_admitted: false` and `qualified: false`.

## Validation and its limits

**13 tests passed** in `runs/current-auction-final-selection-tests-v1-first.log`.
Positive confirmation results in these tests are explicitly synthetic. Negative
tests cover partial coverage, a false saved pass, a primary bound at zero,
chance-level bounds, inadequate absolute performance, changed search settings,
omitted regressions, stale or mismatched reviews, incomplete target coverage,
wrong checkpoint/report bindings, absent search and changed evidence files.
No games, model calls or HF requests run in the unit tests.

The separate preflight exercised the actual live state: `verify` rejected the
unfinished confirmation after **exactly one read**, before opening any game
outcomes. It also accepted the existing full technical reports against the
actual complete policy identities and checked their original raw file hashes.
This did not rerun inference, search or games. A successful complete end-to-end
selection check remains untested until the original study and its review finish.

At **04:31:58 UTC**, original coordinator **PID 3788704 / session 32582** was
verified live with **471 unchanged pins**. The owner checkpoint recorded
**449 audited jobs / 510 submitted originals**. This is an owner-state snapshot,
not a new full remote HF inventory. The snapshot is preserved in
`runs/current-auction-final-selection-preflight-v1/owner-state-observed.json`.
Do not run a competing collector, restart originals or inspect partial strength.

Report: `strong/current-auction-final-selection-preflight-v1.json`.
Completed preflight/archive session: `40187`. All **21 supporting files** were
privately archived and upload/download verified in
`coyotte508/powergrid-ai-germany-v1`, revision
`cfedb1fd0fdf7a2124f1bcb085fd11491b7c4ac6`, path
`archives/current-auction-final-selection-evidence-v1.tgz`, SHA-256
`439f1b156a355ab1f8d5225885258458b03546072209ee1f4e5195b5fca983bc`.
Descriptor: `strong/current-auction-final-selection-evidence-v1.json`.
Inspect these existing outcomes before recovery; do not repeat completed checks.

## Next action

Finish the original study and run the unchanged parallel comparison with the
explicit resumed owner, as documented in
`CURRENT-AUCTION-NETWORK-RESUME-2026-10-29.md`. If its prespecified requirements
fail, keep the final seeds unused and diagnose the complete results. Do not
weaken this gate or change the frozen recipe to pass the same confirmation.

If the requirements pass, assess every adverse cell and write the actual review
using the schema enforced by `reviewed_selection`. Run `verify` on that review,
archive the reviewed evidence and freeze the exact candidate bytes. Actual
source publication, measured allocation and final batch/collection integration
remain required before execution. Use the storage lifecycle documented in
`SELECTED-PUBLIC-POLICY-FINAL-STORAGE-2026-10-29.md`. All 20,160 reserved final
games and the full independent qualification remain outstanding.
