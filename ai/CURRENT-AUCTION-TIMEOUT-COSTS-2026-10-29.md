# Confirmation timeout: resource diagnosis

The original three-hour allowance is too small for part of the four-player
hybrid/search matchup. This is a resource finding, not a model-strength result.
Do not resume the stopped coordinator or treat its incomplete results as a
qualified confirmation.

## Evidence as of 07:32:38 UTC, 29 October

The fourth collection pass finished successfully: **603 audited original jobs /
19,424 games**, **one explicit failed original**, **17 active originals**, and
**323 unsubmitted rows**. It added five successful original audits. Its PID
1649138 / session 41391 exited; no new games or HF jobs were launched. All 17
active handles were inspected by the collector, rather than inferred from an
old lock or state file. They were five-player hybrid/economic jobs.

The resource review binds every collected measurement to its original archive
manifest, immutable source, policy identity, launch guard and verified receipt.
It only examines timing, CPU accounting, sampled memory, coverage and provenance.
It does not examine wins, player values or partial strength aggregates.

| Four-player hybrid opponent | Audited / planned jobs | Median measured time | Maximum measured time | Largest share of deadline |
| --- | ---: | ---: | ---: | ---: |
| Economic | 32 / 32 | 50.6 min | 131.9 min | 73.3% |
| Heuristic | 32 / 32 | 46.2 min | 97.4 min | 54.1% |
| Legacy | 32 / 32 | 59.9 min | 147.0 min | 81.7% |
| Rush | 32 / 32 | 54.7 min | 73.7 min | 40.9% |
| Geographic search | 31 / 32, plus one timeout | 95.8 min | 177.8 min | 98.8% |

The 31-job search summary is conditional on completion. The missing job is
explicitly excluded from numerical cost summaries, not treated as a short or
successful game. Its terminal HF timeout is retained as evidence that the
allocation was insufficient. No uncensored upper runtime bound is estimated.

The slowest completed search shard was
`pg-current-confirm-v1-pop-search_geo-4p-06`, handle
`6ae2c3f741e90535df782f3b`: **10,666.08 measured seconds** for 16 games, leaving
only 133.92 seconds of the three-hour allowance before accounting for operations
outside the measurement. Two more completed shards reached 97.9% and 96.9% of
their deadlines. The adjacent failed shard remains
`pg-current-confirm-v1-pop-search_geo-4p-05`, handle
`6ae2c32f3fb22a235dd50586`, with no usable raw archive at the inspected revision.

At the unchanged concurrency, the slowest completed shard's amortized wall cost
was **666.63 seconds/game**, **4.04 times** the 164.84 seconds/game used by the
pilot-based planner. This is job wall time divided by games, not serial game
latency. The initial two- and six-player pilot allowance did not cover this
four-player/opponent tail.

Across the 603 audited originals, measured job times sum to **359.78 hours** and
accounted CPU time to **1,272.61 CPU-hours**. These are totals across parallel
jobs, not elapsed research time or an HF billing estimate. The largest sampled
process RSS was **6.53 GiB**. Sampling does not bound total container memory;
the observed hard failure was a timeout, not evidence of an out-of-memory event.

## Coverage and limits

Only **41 of 54 arm/player-count/opponent groups** have complete cost coverage.
The search/4p group has its recorded failure, and economic/5p is still incomplete.
Eleven hybrid groups have no completed confirmation jobs yet, including all
six-player groups and most five-player opponents. Their pilot observations are
not confirmation coverage. Do not extrapolate a safe maximum from the survivors.

The measured wrapper excludes at least archive upload and platform queueing.
Its runtime-to-deadline fraction understates full job occupancy. CPU/wall is
accounted concurrency, not a hardware utilization percentage. Resource observations
also cannot establish playing strength or justify changing an evaluated policy.

## Consequence for recovery

1. Finish collecting all **621 original handles** and preserve every failure.
   Use only the bounded collector in the [timeout handoff](CURRENT-AUCTION-TIMEOUT-2026-10-29.md).
2. Do not restart the previous three-hour allocation. A separately recorded
   recovery decision must account for the timeout and near-deadline successes,
   incomplete opponent/count coverage, and upload/shutdown overhead.
3. Prefer a resource-only recovery that keeps the frozen policy, workers, every
   planned deal/seat/rule combination and all strength thresholds intact. Preserve
   original attempts and distinguish any later recovery executions. Do not swap
   out difficult seeds, keep only survivors, or rerun until a favorable result.
4. Any future worker design must preserve completed raw games before a hard
   deadline. The current wrapper uploads only during finalization; increasing a
   timeout alone does not fix that evidence-retention weakness.

This report admits no change or new job. It does not yet choose a new deadline,
alter source or policies, use reserved seeds, or select/qualify a candidate.
The research goal remains active. The next recovery decision should use the
complete original resource evidence once the 17 remaining jobs terminate.

## Reproducible records

- Analysis: `strong/review_current_auction_timeout_costs_v1.py`.
- Structured observations: `strong/current-auction-timeout-cost-review-v1.json`.
- Fixed collection cycle:
  `runs/current-auction-timeout-collection-v1/cycles/2026-10-29T07-32-38.441309+00-00.json`.
- Collection log: `runs/current-auction-timeout-collection-v1-fourth.log`.
- Verified private evidence descriptor:
  `strong/current-auction-timeout-cost-evidence-v1.json`.

The archive keeps original measurement files, their manifests and verification
receipts, original guards, collection state/log and this analysis. Complete raw
game archives remain referenced by their immutable existing revisions and hashes;
no games or audits were regenerated for this resource review.
