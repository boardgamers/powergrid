# Final evaluation timeout compatibility

**29 October 2026 — local validation fixed; no final allocation admitted.**

The fixed final plan has four independent deals per shard, including all seats
and all four rules. That is 32, 48, 64, 80 or 96 games per job for 2–6 players.
Applying the existing runtime allowance to the complete original pilots exposed
a mismatch: six-player auction-search shards require **13 hours**, while the
new final transport validator only accepted up to 12 hours.

The validator now accepts whole-hour values from **1h through 24h**. This is a
local validation bound, not a claim about HF's maximum. HF documents custom
timeouts including a day-long example in its
[job configuration documentation](https://huggingface.co/docs/hub/en/jobs-configuration).
The frozen confirmation planner already permits up to 24 hours. No running
job, frozen policy, source, schedule, search budget or worker count was changed.

## Measured basis

The unchanged pilot-derived allowance is:

`ceil((900 + 2 × slowest observed seconds/game × shard games) / (0.75 × 3600))`

This uses the slower complete two- or six-player pilot per arm, doubles runtime,
adds 900 seconds for setup and targets 75% of the timeout. It is a planning
allowance, not a statistical upper bound. No confirmation win results were read.

| Players | Fixed games/shard | Fast policy timeout | Auction-search timeout |
| --- | ---: | ---: | ---: |
| 2 | 32 | 2h | 5h |
| 3 | 48 | 3h | 7h |
| 4 | 64 | 4h | 9h |
| 5 | 80 | 5h | 11h |
| 6 | 96 | 5h | 13h |

Hardware and concurrency are the existing `cpu-upgrade`, four game workers,
four search workers and one inference thread. Twice the measured peak is
14,665,015,296 bytes, below the existing 80%-of-32-GiB envelope of
27,487,790,694 bytes. Actual final allocation must still be reviewed against
the complete confirmation's measured costs before admission; these projections
do not authorize a launch or promise a runtime.

## Verification and recovery

All **38 relevant tests passed**: 14 dispatch/bootstrap, 16 returned-job
collection and eight temporary-storage tests. The new dispatch cases verify
that 13h/24h are passed unchanged to a mocked API and that invalid or over-day
values never submit. These dependent suites were rerun because their shared
release validator changed; no inference or game tests were repeated.

The preserved old validator rejected the projected synthetic release with
`Invalid timeout`. The updated validator accepts all **320 original shards /
20,160 games** in the same synthetic release. No actual candidate, admission,
HF job or reserved game was created. The preflight completed in session `84033`.
Report: `strong/selected-public-policy-final-timeout-v2.json`.

The prior transport and tests are preserved under
`runs/selected-public-policy-final-timeout-v2/`. Earlier dispatch/collection/
storage archives still prove their original versions; their old dependency
hashes should not be mistaken for the updated validator. The new evidence
archive includes the preserved sources, current code, test logs and projections.

All **27 supporting files** were privately archived and download/hash verified
in `coyotte508/powergrid-ai-germany-v1`, revision
`866d1827df8e0a5965c75aa9973643d317b9ae4d`, path
`archives/selected-public-policy-final-timeout-evidence-v2.tgz`, SHA-256
`2cf242b040995fe794fc09ee7ca8cb0fef0fa3c8e55cfca20808dd8f7756cac1`.
Descriptor: `strong/selected-public-policy-final-timeout-evidence-v2.json`.
Do not repeat the completed tests/preflight/upload; inspect outcomes first.

At **04:45:25 UTC**, coordinator **PID 3788704 / session 32582** was verified
live with all **471 pins unchanged**. Its checkpoint contained **461 audited /
525 submitted original jobs**. Preserve that owner. The complete comparison,
adverse-cell review, actual candidate/source/allocation admission and all final
games remain outstanding. No candidate is qualified; final seeds remain unused.
