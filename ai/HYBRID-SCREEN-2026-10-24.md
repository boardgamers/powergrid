# Power Grid hybrid screen — 24 October 2026

All **135 batches / 8,400 games** completed and passed verification. The unchanged
comparator reproduced exactly; all raw results, decision receipts and recovery
proofs are archived in the private HF repository. No final candidate was selected.

**Decision:** continue investigating auction search, keep the filtered model as
the research reference, and do not advance this building-search or combined-search
implementation. Auction search has meaningful regressions that must be explained
before larger confirmation. No new jobs were submitted by this review.

Each arm has 1,680 games over Germany 2–6 players, all four rule combinations,
all seats and 27 count/opponent cells. Each cell has only **four independent deals**.
The table percentages include fractional credit for ties. They are exploratory.

## Against the independent search opponent

| Players | Model | Filter | Auction | Building | Combined |
|---|---:|---:|---:|---:|---:|
| 2 | 62.5% | 62.5% | 78.1% | 53.1% | 65.6% |
| 3 | 41.7% | 41.7% | 66.7% | 37.5% | 35.4% |
| 4 | 50.0% | 50.0% | 53.1% | 45.3% | 33.6% |
| 5 | 47.5% | 47.5% | 50.0% | 35.0% | 35.0% |
| 6 | 45.8% | 45.8% | 58.3% | 45.3% | 43.7% |

## Search opponent, each rule combination

| Players / rules | Model | Filter | Auction | Building | Combined |
|---|---:|---:|---:|---:|---:|
| 2 / original/open | 62.5% | 62.5% | 75.0% | 75.0% | 87.5% |
| 2 / original/sealed | 87.5% | 87.5% | 87.5% | 75.0% | 50.0% |
| 2 / recharged/open | 75.0% | 75.0% | 62.5% | 25.0% | 62.5% |
| 2 / recharged/sealed | 25.0% | 25.0% | 87.5% | 37.5% | 62.5% |
| 3 / original/open | 50.0% | 50.0% | 58.3% | 66.7% | 41.7% |
| 3 / original/sealed | 33.3% | 33.3% | 83.3% | 25.0% | 41.7% |
| 3 / recharged/open | 58.3% | 58.3% | 66.7% | 58.3% | 25.0% |
| 3 / recharged/sealed | 25.0% | 25.0% | 58.3% | 0.0% | 33.3% |
| 4 / original/open | 81.2% | 81.2% | 31.2% | 68.8% | 31.2% |
| 4 / original/sealed | 25.0% | 25.0% | 62.5% | 25.0% | 18.8% |
| 4 / recharged/open | 50.0% | 50.0% | 50.0% | 62.5% | 40.6% |
| 4 / recharged/sealed | 43.8% | 43.8% | 68.8% | 25.0% | 43.8% |
| 5 / original/open | 50.0% | 50.0% | 50.0% | 30.0% | 25.0% |
| 5 / original/sealed | 30.0% | 30.0% | 40.0% | 20.0% | 45.0% |
| 5 / recharged/open | 70.0% | 70.0% | 50.0% | 55.0% | 40.0% |
| 5 / recharged/sealed | 40.0% | 40.0% | 60.0% | 35.0% | 30.0% |
| 6 / original/open | 62.5% | 62.5% | 66.7% | 68.7% | 58.3% |
| 6 / original/sealed | 37.5% | 37.5% | 45.8% | 12.5% | 20.8% |
| 6 / recharged/open | 50.0% | 50.0% | 58.3% | 62.5% | 62.5% |
| 6 / recharged/sealed | 33.3% | 33.3% | 62.5% | 37.5% | 33.3% |

Auction search improves Recharged sealed point estimates at every count.
However, four-player original/open falls from **81.25% to 31.25%**
(8 worse paired outcomes, no better outcomes, 16 games / four deals).
Five-player Recharged/open falls from **70% to 50%** (6 worse, 2 better,
20 games / four deals). Three-player heuristic falls from **100% to 85.42%**
(7 worse, no better, 48 games / four deals). These cannot be hidden by the
overall auction gains or used to invent a retrospectively optimized rule switch.

The strict loss filter changes no search-opponent win totals in this screen.
It improves several other cells and has no negative point estimate here;
this is not a guarantee of universal improvement.

## Every count/opponent cell

| Cell | Model | Filter | Auction | Building | Combined |
|---|---:|---:|---:|---:|---:|
| economic/2p | 65.6% | 65.6% | 84.4% | 68.8% | 87.5% |
| economic_capacity_v1/2p | 62.5% | 62.5% | 93.8% | 65.6% | 81.2% |
| heuristic/2p | 87.5% | 87.5% | 78.1% | 78.1% | 62.5% |
| legacy/2p | 96.9% | 96.9% | 100.0% | 93.8% | 100.0% |
| rush/2p | 68.8% | 71.9% | 100.0% | 68.8% | 84.4% |
| search_geo/2p | 62.5% | 62.5% | 78.1% | 53.1% | 65.6% |
| a260/3p | 22.9% | 22.9% | 39.6% | 27.1% | 39.6% |
| economic/3p | 75.0% | 75.0% | 83.3% | 70.8% | 83.3% |
| heuristic/3p | 100.0% | 100.0% | 85.4% | 91.7% | 81.2% |
| legacy/3p | 93.8% | 100.0% | 100.0% | 95.8% | 97.9% |
| rush/3p | 70.8% | 72.9% | 87.5% | 72.9% | 79.2% |
| search_geo/3p | 41.7% | 41.7% | 66.7% | 37.5% | 35.4% |
| economic/4p | 70.3% | 70.3% | 76.6% | 53.1% | 70.3% |
| heuristic/4p | 96.9% | 96.9% | 96.9% | 92.2% | 93.8% |
| legacy/4p | 85.9% | 87.5% | 98.4% | 95.3% | 96.9% |
| rush/4p | 62.5% | 62.5% | 79.7% | 64.1% | 68.8% |
| search_geo/4p | 50.0% | 50.0% | 53.1% | 45.3% | 33.6% |
| economic/5p | 67.5% | 70.0% | 90.6% | 83.8% | 85.0% |
| heuristic/5p | 97.5% | 97.5% | 96.2% | 100.0% | 90.0% |
| legacy/5p | 86.2% | 88.8% | 91.3% | 87.5% | 92.5% |
| rush/5p | 81.2% | 82.5% | 88.8% | 88.8% | 85.0% |
| search_geo/5p | 47.5% | 47.5% | 50.0% | 35.0% | 35.0% |
| economic/6p | 78.1% | 79.2% | 91.7% | 71.9% | 87.5% |
| heuristic/6p | 99.0% | 99.0% | 97.9% | 99.0% | 97.9% |
| legacy/6p | 93.8% | 96.9% | 95.8% | 94.8% | 89.6% |
| rush/6p | 71.9% | 72.9% | 92.7% | 88.5% | 87.5% |
| search_geo/6p | 45.8% | 45.8% | 58.3% | 45.3% | 43.7% |

## Execution and next steps

All game and rollout cap counts are zero. Timing below is from shared HF
cpu-upgrade jobs with eight concurrent games, **not AMD 8840U latency**.

| Arm | Search decisions | Search changes | Rollouts | Search median / p95 |
|---|---:|---:|---:|---:|
| model | 0 | 0 | 0 | — |
| filter | 0 | 0 | 0 | — |
| auction | 51,922 | 18,813 | 2,099,704 | 18.9s / 64.5s |
| building | 33,462 | 9,007 | 1,432,904 | 8.9s / 40.6s |
| combined | 84,759 | 27,856 | 3,499,072 | 24.7s / 87.7s |

Of 18,813 auction changes, 9,977 have a simulated mean-credit advantage of at most 1/8 over the model action. That motivates checking
selection noise; it does not establish the cause of any loss. Opponent
mixture mismatch and approximating future search with model-only play also
remain hypotheses, not measured explanations.

1. Replay paired auction regressions and suitable improved controls from immutable saved data; inspect bidding, candidate margins and simulated opponent behavior.
2. Distinguish finite-world selection noise, opponent-model mismatch and future-policy approximation with separately specified diagnostics; none is established by terminal summaries.
3. Only after addressing regressions, freeze the policy and run larger fresh all-count/all-rule confirmation. Do not retrofit routing to the favorable cells.
4. Keep the separate resource-replanning ablation unlaunched until its source and full-game runtime admission are complete.
5. Before final qualification, implement the exact selected-policy final adapter and repeat full target-hardware evidence; existing model-only receipts are insufficient.

**Progress assessment:** this is not evidence of a general plateau.
Auction search offers a promising direction, but running more unchanged
building/combined search or indiscriminately distilling its actions is not justified.

## Persistent evidence

- [Full comparison](strong/population-hybrid-development-comparison-v1.json).
- [Machine-readable review, all adverse auction cells and paired terminals](strong/population-hybrid-development-review-v1.json).
- [Archive descriptor](strong/population-hybrid-development-complete-evidence-v1.json).
- Private HF revision: `91076fb5f4cffed75bf2ddd22f70f3442f78c00d`.
- Archive SHA256: `d9f140ced5394b154eaddced865723ca70e064a5e311d5ff098319d0f6f0b1fc`.
- Comparison SHA256: `6acbd8e57990f4cb9dc775b46b3859db18ccab3cb653dc50552c92f60a86bcbb`.
- Final qualification protocol and reserved seeds remain unchanged and unused.
