# Corrected resource runtime pilots complete — 28 October 2026

The two separately admitted v4 anchored-resource pilots are complete. At
20:24 UTC, independent collection verified **32/32 games**, every scheduled
seat/rule pair, 4,174 atomic decisions and **118,392 uncapped continuations**.
Both raw job archives were downloaded by immutable revision and checked against
their hashes. No new inference, games, HF jobs or gradient updates ran during
collection. The original failed experiment remains failed and preserved.

## Scope and measured costs

| Players | Games | Workflow seconds | CPU seconds | Sampled peak RSS, GB | Continuations | Neural decisions |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 2 | 8 | 4,031.86 | 13,015.63 | 4.975 | 62,808 | 4,930,345 |
| 6 | 24 | 6,585.55 | 24,337.54 | 5.108 | 55,584 | 3,938,166 |

The six-player workflow took 1.83 hours, below the admitted six-hour limit.
These workflow measurements include startup and validation, but not HF
bootstrap/download/upload. Peak RSS is sampled across the process tree every
0.2 seconds and can count shared pages more than once. These are concurrent
HF batch costs, not serving latency on the AMD 8840U.

Both jobs use the unchanged `cpu-upgrade` admission: four concurrent games,
eight sampled worlds, one search worker and one inference thread. The 32 games
cover all seats and original/Recharged × open/sealed rules against `search_geo`
on fresh runtime-only seeds. The two jobs made 8,868,511 continuation neural
decisions in total; two root-filter overrides were recorded in the six-player
job. Zero continuation limits were hit.

The audit counter `resource_turns` is zero because this mode submits atomic
resource actions; it is not a count of how often the game entered Resources.
All 4,174 recorded policy requests are accounted for as atomic moves.

Different deals, trajectories and competing host load prevent interpreting the
lower six-player wall time than the original pilot as a controlled speedup.
These engineering games are excluded from strength selection and final tests.
No win-rate estimate is used here, and the corrected policy is not qualified.

## Immutable evidence and recovery

The original admitted handles are unchanged:

- Two players: `6ae23f6e41e90535df779e68`, private model revision
  `b3039278a9bcb6734c7cf8b9d4f06ccf1b15c6de`, object
  `archives/pg-resource-turn-runtime-v2-anchored-2p.tgz`, SHA-256
  `47ad2a12a575e2faae11053d2830b92462c4eebc63af0910da01e8dc86b1fdf5`.
- Six players: `6ae23f6e3fb22a235dd467c4`, private model revision
  `1167fd540a08c9bc31a4efca140c7a53145999e5`, object
  `archives/pg-resource-turn-runtime-v2-anchored-6p.tgz`, SHA-256
  `38e49cb0596538e3556ddd3fecf5e07b5c8b9c2a8abcf5eb060de34bea868187`.

Both archives are in `coyotte508/powergrid-ai-germany-v1`. The source remains
private dataset `coyotte508/powergrid-ai-training-v1`, revision
`e8eef00401823710ca646574edc3372363160940`, object
`strong-source-resource-turn-runtime-v2.tgz`, SHA-256
`ce73a76efa7552035064e55b781fd58f4a5872247420b70ae99f4bfb31b9e727`.
The [admission record](RESOURCE-RUNTIME-ADMISSION-2026-10-28.md) retains the
original failure, measured budget and exact launch provenance.

Final results are `strong/resource-turn-runtime-results-v2.json` and
`strong/resource-turn-runtime-terminal-v2.json`. Per-job independent receipts,
raw evidence and final state are under `runs/resource-turn-runtime-collected-v2/`.
The sixth collection log records successful terminal collection; that process
exited successfully. There is no remaining resource pilot or resource collector.

`strong/resource-runtime-complete-evidence-v2.json` binds a separate verified
recovery archive containing the final reports, independent receipts, launch
guards and helper sources. It references the two existing raw job archives and
the source bundle instead of duplicating or regenerating their games. Inspect
the archive intent and outcome before any retry. Do not relaunch completed jobs.

## Next decision

Finish the unchanged 10,080-game conservative-auction comparison before choosing
another strength experiment. Resource search still needs a separately justified
full-game comparison if selected; these pilots only establish runnable, audited
execution of the corrected policy. No candidate qualified, final seeds remain
unused, and the broader research goal remains active.

This turn is progress: the final resource pilot was collected and independently
audited. The preceding turn was a verified wait on the exact live HF handles.
