# Full serving replay on the actual AMD 8840U

**Completed and independently audited on 29 October 2026.** Both unchanged
confirmation policies passed all **2,553 original positions each: 5,106 requests**.
Every response has a legal move, the correct request/revision and player order,
and the frozen complete-policy identity. Every underlying model proposal also
matches the independently verified native checkpoint on the same input.

This completes the full current-policy serving/export integration on the target.
It does not select a candidate or qualify its strength. The 26,880-game
confirmation and the separate reserved strength gate remain required.

## Coverage and exact policies

The original positions cover Germany, 2–6 players, original/Recharged and
open/sealed auctions with public money. Coverage is **349 / 427 / 527 / 609 /
641 positions** for 2 / 3 / 4 / 5 / 6 players. All **80 count/rule/phase cells**
have warm timing observations for each policy. There are 840 auction, 755
resource, 491 building and 467 bureaucracy positions per policy. No original
position was dropped, replaced or regenerated.

The current engine's legal menus and public projection were independently checked
before replay. Money stays visible; private deck/sealed bids are removed. Exact
fixture hash: `f1c97bf909e38e5df372a89d169d80f5a6f24c00dccefacd60b10b767f1fcfa0`.
Runtime manifest: `fc135130689140b6fd72a76e6e14c59a7fea59717b858d330bac0c7f6aad93df`.
The standalone package was extracted on the actual Ryzen 7 8840U, using eight
worlds, four search workers, one inference thread and the unchanged population
and minimum advantage settings.

The filtered policy made 2,553 decisions with no search. The population policy
made **779 search decisions**, with **31,680 complete rollouts**, **4,043,599
neural decisions**, **138 search changes** and **zero truncations**. Each policy
recorded two root-filter overrides. Search is real simulation work; the replay
created no new full evaluation games, HF jobs, training updates or final seeds.

## Measured latency

These are end-to-end warm policy requests on this fixed fixture distribution.
They are descriptive timings, not representative gameplay or platform job
latency percentiles. The first request per policy is excluded from warm results.
Search rows include only requests with actual search receipts, excluding trivial
auctions that bypass search.

| Players | Fast policy median / p95 (ms) | Auction search median / p95 (s) | Warm searched requests |
| --- | ---: | ---: | ---: |
| 2 | 8.97 / 12.93 | 3.86 / 7.57 | 80 |
| 3 | 9.54 / 13.93 | 4.47 / 8.52 | 101 |
| 4 | 10.53 / 15.51 | 5.09 / 10.46 | 170 |
| 5 | 10.13 / 16.18 | 5.87 / 11.19 | 194 |
| 6 | 11.93 / 18.18 | 6.29 / 11.87 | 233 |

Across all positions, the fast policy median/p95 was **10.15 / 16.27 ms**.
Searched auctions were **5.34 / 11.20 seconds**, with a maximum of **13.81 s**
over 778 warm searched requests. Hybrid requests that did not search were
**10.49 / 17.19 ms** (median/p95, 1,774 requests).

Policy-process creation plus the first request took **0.671 s** for the filtered
policy and **6.617 s** for the hybrid. These cold timings exclude downloads,
installation, job queueing and the benchmark harness's initial validation.
The complete replay took **73.95 minutes** wall time and recorded
**6080.24 CPU seconds**. The earlier 160-position benchmark used a
different fixture mix; differences in these summaries are not a controlled
speedup or regression experiment.

## Original run, independent collection and checkpoint binding

Original target **PID 3462824** started at `2026-10-29T01:11:16.122496+00:00`
and finished successfully at `2026-10-29T02:25:13.385174+00:00`. Its actual process
was confirmed exited before collection. Remote directory:
`/home/coyotte508/powergrid-ai-current-full-serving-8840u-v1`.

Original collection **session 15475** completed successfully. Its fresh-interpreter
audit rechecked every response and search receipt, raw hashes and full identities.
The subsequent read-only binding **session 29225** also completed successfully:
all 5,106 target `modelProposal` values equal the native-checkpoint choices.
The independently audited filter/search may deliberately choose a different
final action. No new inference or simulations were required for collection or
binding. Six original serving tests and six export/binding tests remain separate
supporting checks; the full raw audits provide the coverage evidence.

Reports and raw proof:

- `strong/current-full-serving-8840u-results-v1.json`
- `strong/current-full-serving-export-binding-v1.json`
- `strong/current-full-serving-latency-summary-v1.json`
- `runs/current-full-serving-8840u-collected-v1/`
- `runs/current-full-serving-8840u-collect-v1-first.log`
- `runs/current-full-serving-export-binding-v1-first.log`

The original launch guard, exact package and readiness pins stay unchanged.
**Do not relaunch or recollect the completed replay.** This is not a full
cross-host response comparison; the earlier 320-request exact cross-host check
remains separate evidence. Values remain uncalibrated for player-analysis use.

## Immutable recovery archive

All **28 result files**, including every original target response, independent
audit, checkpoint-proposal binding and latency summary, are privately archived
and upload/download-verified at model revision
`e4f018ff2f983e5e4f1a6b7e92a7586051bf5842`, path
`archives/current-full-serving-results-evidence-v1.tgz`, SHA-256
`7848187c35f8844ffd20b8b7e1511ca0db8aec432e39ffc0e6baed1feb5e4256`.
Descriptor: `strong/current-full-serving-results-evidence-v1.json`.

It references the unchanged launch package/archive at revision
`46cecc8db0ece1b7013505b5555b0c1106cd7db9` and the full native-checkpoint export
proof at revision `47c1eb217410c3038e7609eae8f5a56154ebcecc`.
Restore those exact archives by hash; no fixtures or games need regeneration.
The successful original result archive was produced by
`strong/archive-current-full-serving-results-v1.py`; inspect its existing
intent/outcome before any retry. No upload or audit rerun is needed.

After complete confirmation, any candidate selection must bind the same exact
complete-policy identity/settings to reuse this technical evidence. Reserved
strength evaluation is still unused, no candidate is qualified, and no
production routing has changed.
