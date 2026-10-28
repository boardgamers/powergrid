# Conservative auction search: completed comparison — 28 October 2026

Conservative population search is a promising next confirmation candidate: its
paired gain over the same filtered model is **+20.19 percentage points** against
`search_geo`, equally weighted across 2–6 players (exploratory 95% interval
**[+14.81, +25.74]**). Dual search gains **+21.78 points [+17.27, +26.36]**;
its additional **+1.59 points [-2.90, +6.17]** over population search is uncertain,
while its measured 8840U auction latency is about twice as high.

The research decision is to carry the cheaper population-search recipe into a
separate confirmation after current-engine runtime admission. Keep its exact
eight-world budget, thresholds, opponent population and auction-only scope.
Do not route between policies retrospectively by player count or auction rules.
No final candidate is selected or qualified, and reserved final seeds are unused.

## Completion and scope

- Full independent comparison completed at `2026-10-28T21:24:47.273138+00:00`.
- **10,080 games / 648 independently re-audited job archives**, 3,360 games per
  arm, 27 opponent/count cells per arm, eight paired deals per cell, every seat
  and all four rule combinations. Zero capped continuations.
- The final collector PID 1075760 completed at 20:38:58 UTC; comparator PID
  602651 / session 48296 exited with code 0. Neither should be restarted.
- There were **650 total HF attempts**: 648 selected successful executions and
  two preserved pre-evaluation bootstrap failures with explicitly reviewed
  replacements. No failed evaluation game is silently dropped.
- Germany, original/Recharged and open/sealed auctions, 2–6 players. Opponents:
  economic, geographic search, legacy, heuristic and rush at every count;
  A260 additionally at three players and economic-capacity at two players.
- All arms use the same strict-loss-filtered `frozen-1` outside auctions.
  Search uses public money and a public-belief simulator; no future deck,
  private sealed bids or opponent identity is exposed to the policy.

Credits below count a tied win fractionally. Strict wins and tied-win rates
are retained separately in the machine-readable report. Every interval resamples
eight whole deals within each player count, preserving policy/seat/rule pairing
and sharing indices across opponents. There are 10,000 replicates, seed 15125.
These are exploratory marginal intervals without multiplicity adjustment;
10,080 games do not mean 10,080 independent deals. This is not the final gate.

## Paired primary comparison

| Contrast | Equal-count search gain (percentage points) | Paired 95% interval |
|---|---:|---:|
| Population search minus Model + filter | 20.19 | [14.81, 25.74] |
| Dual search minus Model + filter | 21.78 | [17.27, 26.36] |
| Dual search minus Population search | 1.59 | [-2.90, 6.17] |

| Players | Model + filter | Population search | Dual search |
|---|---:|---:|---:|
| 2 | 63.28% | 82.81% | 73.44% |
| 3 | 39.58% | 67.71% | 79.17% |
| 4 | 44.53% | 57.03% | 64.06% |
| 5 | 40.00% | 62.81% | 60.62% |
| 6 | 43.49% | 61.46% | 62.50% |
| Equal-count average | 46.18% | 66.36% | 67.96% |

These are paired rates from this study. Do not subtract absolute rates from
earlier studies with different deals and claim a model-training improvement.

## Search opponent: all count/rule views

| Players | Rules | Model + filter | Population search | Dual search |
|---|---|---:|---:|---:|
| 2 | original/sealed | 68.75% | 75.00% | 75.00% |
| 2 | recharged/sealed | 56.25% | 87.50% | 68.75% |
| 2 | original/open | 81.25% | 87.50% | 75.00% |
| 2 | recharged/open | 46.88% | 81.25% | 75.00% |
| 3 | original/sealed | 41.67% | 62.50% | 83.33% |
| 3 | recharged/sealed | 20.83% | 54.17% | 83.33% |
| 3 | original/open | 50.00% | 75.00% | 70.83% |
| 3 | recharged/open | 45.83% | 79.17% | 79.17% |
| 4 | original/sealed | 34.38% | 62.50% | 62.50% |
| 4 | recharged/sealed | 31.25% | 46.88% | 43.75% |
| 4 | original/open | 53.12% | 46.88% | 81.25% |
| 4 | recharged/open | 59.38% | 71.88% | 68.75% |
| 5 | original/sealed | 35.00% | 56.25% | 50.00% |
| 5 | recharged/sealed | 15.00% | 50.00% | 35.00% |
| 5 | original/open | 52.50% | 67.50% | 75.00% |
| 5 | recharged/open | 57.50% | 77.50% | 82.50% |
| 6 | original/sealed | 39.58% | 41.67% | 52.08% |
| 6 | recharged/sealed | 28.12% | 50.00% | 37.50% |
| 6 | original/open | 56.25% | 81.25% | 81.25% |
| 6 | recharged/open | 50.00% | 72.92% | 79.17% |

The population-search four-player original/open rate fell from **53.12% to
46.88%**: paired difference **-6.25 points [-18.75, +9.38]**. The old large
open-auction failure is not reproduced at the same magnitude, but this negative
cell must remain in confirmation. Three-player Recharged/sealed population
search has a lower interval endpoint equal to chance (33.33%), so even an
informal application of the final per-rule bound would not yet pass.

Dual search is not uniformly stronger: it loses 9.38 points to population search
overall at two players, and has larger legacy regressions at three/six players.
Its extra cost is not justified by a demonstrated overall advantage here.

## All opponent/count cells

| Opponent / players | Model + filter | Population search | Dual search |
|---|---:|---:|---:|
| economic/2p | 78.12% | 96.88% | 98.44% |
| search_geo/2p | 63.28% | 82.81% | 73.44% |
| legacy/2p | 96.88% | 98.44% | 100.00% |
| heuristic/2p | 92.19% | 93.75% | 96.88% |
| rush/2p | 81.25% | 96.88% | 100.00% |
| economic/3p | 80.21% | 90.62% | 92.71% |
| search_geo/3p | 39.58% | 67.71% | 79.17% |
| legacy/3p | 96.88% | 96.88% | 91.67% |
| heuristic/3p | 86.46% | 90.62% | 96.88% |
| rush/3p | 64.58% | 90.62% | 93.75% |
| economic/4p | 74.61% | 89.84% | 89.84% |
| search_geo/4p | 44.53% | 57.03% | 64.06% |
| legacy/4p | 91.41% | 96.88% | 95.31% |
| heuristic/4p | 92.19% | 96.88% | 96.88% |
| rush/4p | 62.50% | 91.41% | 92.97% |
| economic/5p | 83.12% | 96.25% | 98.12% |
| search_geo/5p | 40.00% | 62.81% | 60.62% |
| legacy/5p | 90.00% | 95.62% | 91.25% |
| heuristic/5p | 100.00% | 99.38% | 98.75% |
| rush/5p | 86.88% | 95.62% | 99.38% |
| economic/6p | 75.00% | 93.75% | 97.40% |
| search_geo/6p | 43.49% | 61.46% | 62.50% |
| legacy/6p | 95.05% | 96.35% | 92.19% |
| heuristic/6p | 98.96% | 99.48% | 100.00% |
| rush/6p | 78.65% | 92.71% | 96.35% |
| a260/3p | 41.67% | 58.33% | 66.67% |
| economic_capacity_v1/2p | 75.00% | 93.75% | 98.44% |

Population search has legacy overall rates above 95% at every player count in
this development sample. This does not prove the final default-bot floor on
new deals, nor robustness to other maps or arbitrary human strategies.

## Every adverse primary-comparison view

The 135 overall/rule views per contrast are overlapping views, not independent
hypotheses. Population-minus-filter has **11 negative / 15 zero / 109 positive**
views; dual-minus-filter has **13 / 14 / 108**. All negative views follow.
No adverse view is removed for having a wide interval or a small sample.

| Search arm | Cell | Rules | Difference (points) | Paired 95% interval |
|---|---|---|---:|---:|
| Population search | heuristic/2p | original/sealed | -6.25 | [-18.75, 0.00] |
| Population search | legacy/3p | original/sealed | -4.17 | [-12.50, 0.00] |
| Population search | legacy/3p | original/open | -4.17 | [-12.50, 0.00] |
| Population search | heuristic/3p | recharged/sealed | -8.33 | [-20.83, 0.00] |
| Population search | search_geo/4p | original/open | -6.25 | [-18.75, 9.38] |
| Population search | legacy/4p | recharged/sealed | -3.12 | [-9.38, 0.00] |
| Population search | heuristic/4p | original/open | -3.12 | [-12.50, 6.25] |
| Population search | heuristic/4p | recharged/open | -3.12 | [-9.38, 0.00] |
| Population search | heuristic/5p | overall | -0.62 | [-1.88, 0.00] |
| Population search | heuristic/5p | recharged/sealed | -2.50 | [-7.50, 0.00] |
| Population search | legacy/6p | original/sealed | -2.08 | [-8.33, 4.17] |
| Dual search | search_geo/2p | original/open | -6.25 | [-25.00, 12.50] |
| Dual search | legacy/3p | overall | -5.21 | [-12.50, 1.04] |
| Dual search | legacy/3p | original/sealed | -4.17 | [-12.50, 0.00] |
| Dual search | legacy/3p | original/open | -8.33 | [-25.00, 0.00] |
| Dual search | legacy/3p | recharged/open | -8.33 | [-20.83, 0.00] |
| Dual search | legacy/5p | recharged/open | -2.50 | [-20.00, 15.00] |
| Dual search | heuristic/5p | overall | -1.25 | [-3.12, 0.00] |
| Dual search | heuristic/5p | recharged/sealed | -2.50 | [-7.50, 0.00] |
| Dual search | heuristic/5p | original/open | -2.50 | [-7.50, 0.00] |
| Dual search | legacy/6p | overall | -2.86 | [-6.25, 1.04] |
| Dual search | legacy/6p | original/sealed | -2.08 | [-6.25, 0.00] |
| Dual search | legacy/6p | recharged/sealed | -10.42 | [-20.83, 0.00] |
| Dual search | legacy/6p | recharged/open | -3.12 | [-11.46, 6.25] |

The full summary also retains every secondary dual-minus-population view
(36 negative / 34 zero / 65 positive), all strict-win contrasts and deal means.

## Measured cost

| Arm | Summed HF workflow hours | CPU hours | Max sampled job RSS (GB) | Search changes / decisions |
|---|---:|---:|---:|---:|
| Model + filter | 16.77 | 51.33 | 2.658 | 0 / 0 |
| Population search | 215.75 | 668.83 | 7.187 | 18,160 / 107,468 |
| Dual search | 377.15 | 1425.07 | 7.193 | 13,562 / 108,454 |

Population search ran **4,346,144** continuations; dual search ran **8,770,560**.
All finished uncapped. Their continuation neural-decision counts were
535,712,378 and 859,632,037 respectively; dual also recorded 426,173,656 surrogate
decisions. The summed workflow duration includes startup/validation and is
neither experiment elapsed time nor billed cost. Process-tree RSS can count
shared pages more than once. Per-job measurements remain in the full archive.

The separate [actual 8840U benchmark](CONSERVATIVE-AUCTION-CPU-2026-10-27.md)
measured warm auction medians of **5.89 ms / 8.47 s / 17.52 s** for filter,
population and dual. These are 39 saved warm auction positions per policy,
not representative latency percentiles. Instant analysis still favors the fast
model; auction search is feasible as a slower platform job. The selected final
policy will require its own full serving/target benchmark.

## Next research step

1. Preserve this complete comparison and the exact frozen policies. Do not tune
   thresholds or add rule/count routing using these eight evaluation deals.
2. Admit the same population-search and filtered-model policies on the pinned
   intended current engine. Check full public-state/search transitions, new
   cheap-nomination menus, information boundaries and export/runtime identity.
   Existing fixed-action replays and model-only menu checks do not establish
   full search compatibility; any failure must be resolved before new games.
3. Predeclare a fresh, larger whole-deal confirmation covering 2–6 players, all
   rules and the independent opponents, with the same model as paired control.
   Report every adverse cell and absolute strength; keep all final seeds unused.
   This document selects the next research direction, not a job launch protocol.
4. Keep discount-feature warm-start work and corrected resource runtime evidence
   available, but do not conflate their compatibility/runtime successes with
   strength or modify the confirmed recipe during evaluation. New training data
   must stay disjoint from these development and future final deals.

This result argues against stopping research for lack of progress: the targeted
conservative auction approach improves development strength substantially.
It does not establish a general learning plateau or make a broader Rust/GPU
rewrite the immediate next priority. Final qualification, current-engine
admission, full export/serving coverage and standalone deployment packaging
remain incomplete. No game changes are deployed.

## Recovery and provenance

- Full result: `strong/conservative-auction-development-comparison-with-attempts-v1.json`
  (SHA-256 `2d2e469a073e3cd71a919da6a137042cfb5fd2ea14d6fb0491997d06eee77e37`). Its `.intent.json` and complete audit log are preserved.
- Compact statistics: `strong/conservative-auction-development-summary-v2.json`.
  It retains every computed statistic, adverse cell, uncertainty description
  and identity; only per-job timing/execution/raw provenance tables move to
  the archived full result. The compact view is not a new analysis.
- Recovery descriptor: `strong/conservative-auction-comparison-evidence-v2.json`.
  The verified private-HF snapshot contains the full collected report, full
  comparison, source/code pins, all 648 launch/audit receipts, both failed
  bootstrap logs/guards, owner records, interpretation and recovery helper.
  It references the 648 immutable raw job archives instead of duplicating them.
- Frozen protocol SHA-256:
  `51b845f4a57c3131475e24267fbbb08eb624c391aa6a8e6a4f5d5c6b8ac718ee`.
- Source bundle: private dataset `coyotte508/powergrid-ai-training-v1`, revision
  `0f9c129af46fe181a71b1f131243517fff4cc16b`,
  `strong-source-conservative-auction-development-v2.tgz`, SHA-256
  `d1345d552192c46efe38c3eb7df22c4e4663f2993f2a09fc597bb7ef4d83808e`.
- Original failed handles: `6ae1dca83fb22a235dd3e7c7` (HTTP 502) and
  `6ae1dcb03fb22a235dd3e7eb` (short Node download). Reviewed replacements:
  `6ae1e7b941e90535df77318d` and `6ae1e7b941e90535df77318f`.
  Failed attempts did not start evaluation; exact original/selected identities
  are retained. Historical jobs did not record the Node binary checksum.
- Former coordinators and their STOP markers remain untouched. The complete
  source/result and final owner hashes are bound in the comparison input pins.

The preceding goal turn was a verified wait on the live comparator. This turn
completes the full independent analysis and records a new research decision.
Analysis and archiving submit no HF jobs, generate no games or inference, and
perform no gradient updates. Research remains active; no candidate qualified.
