# Resource recovery decision after all original jobs terminated

**Research is active. This records the recovery design; execution is not yet
admitted. Do not restart an old coordinator or submit from this document alone.**

## Original execution is fully accounted for

The final original-only collection finished at **07:45:19 UTC on 29 October**.
All **621 submitted originals** are terminal:

- **617 HF COMPLETED** jobs passed their original raw audit.
- **Three HF ERROR** jobs retained complete original game data and passed the
  already-reviewed, narrow post-terminal shutdown recovery. Their original
  ERROR status remains recorded.
- **One HF ERROR / Job timeout** has no usable raw archive at the inspected
  revision and remains failed: `6ae2c32f3fb22a235dd50586`,
  `pg-current-confirm-v1-pop-search_geo-4p-05`.

This gives **620 audited jobs / 19,764 unique planned games**. There are no
active or deferred originals. The final collector PID 1753619 / session 58206
exited successfully; the preceding fifth pass, PID 1726102 / session 70627,
also exited. Preserve all six immutable collection cycles and original logs.
The stopped launching coordinator PID 3788704 must remain stopped.

The original 944-shard / 26,880-game confirmation is still incomplete. Its
remaining coverage is **324 fixed shards / 7,116 games**: the failed 16-game
shard plus **323 never-submitted shards / 7,100 games**. All belong to the
hybrid arm. Do not analyze only survivors or mark the existing study complete.

The final cost review binds every measurement to its original raw manifest and
verified receipt. Measured completed-job times total **375.79 wall-hours** and
**1,336.62 accounted CPU-hours**, summed across parallel jobs. These omit the
unmeasured failed job and some platform/upload overhead and are not billed or
elapsed research time. Final five-player/economic coverage is 29 of 32 shards;
the other three were never launched. Only **41 of 54 groups** have complete
cost coverage. Eleven hybrid groups have no completed confirmation jobs.

## Recorded resource-only decision

The [cost diagnosis](CURRENT-AUCTION-TIMEOUT-COSTS-2026-10-29.md) establishes a
real deadline problem: completed four-player/search costs reached 4.04 times
the pilot input, with three jobs consuming 96.9–98.8% of their deadline. The
failed shard is censored; no safe upper runtime bound follows from survivors.

The next implementation should preserve the exact existing immutable source
bundle, game engine, policies, model weights, features, candidate menus, search
budget, opponent mixture, seeds, seats, rules, workers and strength thresholds.
Use the same `cpu-upgrade` hardware, four game workers, four search workers and
one inference thread. **Change only the external execution allowance and
evidence retention**, with separately recorded attempt identities:

1. Use a **24-hour hard deadline** for recovery and remaining original shards.
   This deliberately leaves substantial headroom beyond the observed tail and
   preserves the work performed by the policy. It is an engineering allowance,
   not a statistical runtime guarantee. Do not alter the frozen original rows
   or source to hide this change; record effective resources in a new attempt
   manifest and verify them against the actual HF submission.
2. Add an external supervisor that archives completed raw game records and their
   decision receipts during execution, under a unique recovery-attempt prefix.
   The original evaluator and policy source remain byte-identical. Only publish
   stable snapshots with hashes; never treat a log message or partial snapshot
   as a complete audited game set. Test interrupted writes and a hard-killed
   child before admission. Final uploads must not overwrite original evidence.
3. Preserve and reuse all 620 audited original shards. Execute the failed
   **same 16 games**, with the same source and seeds, exactly once as a clearly
   identified recovery attempt. The nine old completion messages provide no
   raw results to reuse. Keep the original failed handle and diagnostics;
   do not replace seeds or choose between competing successful attempts.
4. Collect and independently audit that recovery attempt before admitting any
   of the remaining 323 unsubmitted rows. Verify periodic evidence retention as
   well as the full original game and policy identity. Its win rate is not an
   admission criterion and must not be used to tune settings.
5. After that technical gate, run the fixed remaining rows, each once, with the
   same recovery controls and at most the existing **64 concurrent jobs**.
   Stop on any failed or ambiguous attempt. No automatic retries or replacements.
6. Independently reconcile all 944 canonical shards / 26,880 unique games across
   preserved originals and the separately identified recovery executions before
   comparison or selection. Retain failures and all attempt provenance. The
   original strength requirements and separate held-out final gate remain intact.

This is a resource recovery of the same planned confirmation, not permission to
change a policy after seeing partial results. No partial strength statistics
were inspected to make this decision. Reserved final seeds remain unused.

## Admission work still required

Implement and test the supervisor, immutable attempt/provenance controls,
single-recovery dispatch and independent collection/coverage checks. The old
collector and comparator cannot silently combine new attempts: any extension
must explicitly bind this decision and reject duplicate, missing, changed or
outcome-selected evidence. Archive and review the actual prepared controls before
the first new job. A source/policy mismatch or failed retention test blocks
dispatch without changing thresholds or weakening the existing audits.

This turn launched **zero jobs**, generated **zero new games**, changed no
frozen inputs and selected/qualified no candidate. The next action is the
recovery implementation and its real admission checks; no original job remains
to wait for. The research goal has not passed its strength gate.

## Recovery records

- Decision: `strong/current-auction-resource-recovery-decision-v2.json`.
- Final original cycle:
  `runs/current-auction-timeout-collection-v1/cycles/2026-10-29T07-45-19.458530+00-00.json`.
- Final measured resource data: `runs/current-auction-timeout-final-cost-review-v1.json`.
- Verified private archive descriptor:
  `strong/current-auction-original-terminal-evidence-v1.json`.

The archive retains final collection state, logs, decision, cost measurements,
their manifests and all attempt guards/receipts. Existing immutable archives
hold the raw games; restore by revision/hash without regenerating them.
