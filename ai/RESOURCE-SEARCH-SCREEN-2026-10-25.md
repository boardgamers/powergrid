# Power Grid resource-search screen — 25 October 2026

All **54 original jobs / 3,360 games** completed with zero game or rollout caps.
The full comparison was independently reproduced; every terminal credit was
recomputed from final powered cities, money and city count, including exact tie
shares. The paired aggregate and bootstrap were independently reconstructed.

**Decision: do not adopt or scale this resource-search implementation unchanged.**
The filtered neural policy remains the research control. This negative result
narrows the search approach; it does not establish a general learning plateau.

The primary search-opponent difference, equally weighted across 2–6 players, is
**−9.1875 percentage points**, with a paired whole-deal bootstrap 95% interval
**[−16.3648, −1.5518] points**. Every count has a worse point estimate. Each cell
contains only **four independent deals**, keeping all rules and seats together;
these are exploratory intervals, not strength qualification. Different studies
use different deal sets, so compare the paired arms within this screen.

## Against independent search opponents

| Players | Filtered model | Resource search | Difference |
|---|---:|---:|---:|
| 2 | 50.00% | 43.75% | -6.25 pp |
| 3 | 58.33% | 41.67% | -16.67 pp |
| 4 | 47.66% | 39.84% | -7.81 pp |
| 5 | 48.75% | 45.00% | -3.75 pp |
| 6 | 47.92% | 36.46% | -11.46 pp |

## Search opponents by rules

| Players / rules | Filtered model | Resource search |
|---|---:|---:|
| 2 / original/open | 50.00% | 50.00% |
| 2 / original/sealed | 37.50% | 25.00% |
| 2 / recharged/open | 75.00% | 62.50% |
| 2 / recharged/sealed | 37.50% | 37.50% |
| 3 / original/open | 66.67% | 50.00% |
| 3 / original/sealed | 50.00% | 41.67% |
| 3 / recharged/open | 75.00% | 50.00% |
| 3 / recharged/sealed | 41.67% | 25.00% |
| 4 / original/open | 62.50% | 43.75% |
| 4 / original/sealed | 46.88% | 40.62% |
| 4 / recharged/open | 68.75% | 56.25% |
| 4 / recharged/sealed | 12.50% | 18.75% |
| 5 / original/open | 60.00% | 60.00% |
| 5 / original/sealed | 15.00% | 20.00% |
| 5 / recharged/open | 80.00% | 70.00% |
| 5 / recharged/sealed | 40.00% | 30.00% |
| 6 / original/open | 75.00% | 62.50% |
| 6 / original/sealed | 29.17% | 33.33% |
| 6 / recharged/open | 54.17% | 37.50% |
| 6 / recharged/sealed | 33.33% | 12.50% |

## Every opponent/count cell

The economic-opponent secondary aggregate is **+6.25 pp**, interval
**[−0.42, +12.29] pp**. Two-player economic, capacity-economic and rush improvements
coexist with regressions elsewhere. These do not justify choosing a retrospective
count/rule switch or promoting the policy despite its primary result.

| Opponent / players | Filtered model | Resource search | Difference |
|---|---:|---:|---:|
| a260/3p | 47.92% | 47.92% | +0.00 pp |
| economic/2p | 65.62% | 93.75% | +28.12 pp |
| economic/3p | 75.00% | 70.83% | -4.17 pp |
| economic/4p | 67.19% | 64.06% | -3.12 pp |
| economic/5p | 72.50% | 78.75% | +6.25 pp |
| economic/6p | 71.88% | 76.04% | +4.17 pp |
| economic_capacity_v1/2p | 62.50% | 100.00% | +37.50 pp |
| heuristic/2p | 78.12% | 84.38% | +6.25 pp |
| heuristic/3p | 87.50% | 85.42% | -2.08 pp |
| heuristic/4p | 90.62% | 85.94% | -4.69 pp |
| heuristic/5p | 100.00% | 97.50% | -2.50 pp |
| heuristic/6p | 98.96% | 96.88% | -2.08 pp |
| legacy/2p | 100.00% | 93.75% | -6.25 pp |
| legacy/3p | 83.33% | 93.75% | +10.42 pp |
| legacy/4p | 95.31% | 92.19% | -3.12 pp |
| legacy/5p | 91.25% | 97.50% | +6.25 pp |
| legacy/6p | 94.79% | 92.71% | -2.08 pp |
| rush/2p | 62.50% | 84.38% | +21.88 pp |
| rush/3p | 81.25% | 75.00% | -6.25 pp |
| rush/4p | 65.62% | 60.94% | -4.69 pp |
| rush/5p | 81.25% | 86.25% | +5.00 pp |
| rush/6p | 75.52% | 77.08% | +1.56 pp |
| search_geo/2p | 50.00% | 43.75% | -6.25 pp |
| search_geo/3p | 58.33% | 41.67% | -16.67 pp |
| search_geo/4p | 47.66% | 39.84% | -7.81 pp |
| search_geo/5p | 48.75% | 45.00% | -3.75 pp |
| search_geo/6p | 47.92% | 36.46% | -11.46 pp |

## Cost and interpretation

The resource arm made **69,624 search decisions**, changed the baseline choice
**17,637 times**, and ran **5,151,608 continuations** with zero rollout caps. It
used eight sampled worlds and fixed candidate fuel bundles, replanning after each
atomic purchase. The retained decision receipts support later diagnosis; this
screen alone does not identify which search assumption caused the regressions.

Search median / p95 latency was **13.13 / 54.51 seconds** in shared HF CPU-upgrade
jobs with eight concurrent games. These are **not AMD 8840U serving timings**.
There is no justification for spending more compute on the identical implementation
or treating its selected actions as improved training labels.

Continue the separately specified fresh-position opponent-model experiment and
cautious auction-search work. Any redesigned resource search needs a concrete
hypothesis, frozen configuration and fresh paired full games. The final strength
protocol and reserved seeds remain unchanged and unused.

## Persistent evidence

- [Full comparison](strong/resource-replanning-development-comparison-v1.json).
- [All adverse results and decision](strong/resource-replanning-development-review-v1.json).
- [Independent full audit/archive](strong/resource-replanning-development-complete-evidence-v1.json).
- Private HF revision: `637202d691efc8121f95b7ff3954d4f20bfa54dd`.
- Archive SHA256: `e6e93cf4bf858f9afada6576654aaf021c2d455e50471319488de2d1c3831cc3` (7,290 files).
- Original archive watcher PID 2444260 / session 56315 completed normally; do not restart or repeat the upload.

## 25 October: complete within-turn consistency diagnosis

The atomic policy values a complete fuel bundle but executes only its first
purchase, then searches again. This was an explicit research policy, not a new
serving bug. The new audit measures how often its simulated buying sequence
differs from its actual execution. It reads **all 1,680 resource-filter games**,
their paired control terminals and **69,624 search decisions** from the immutable
screen. No new strength games, inference, gradients or HF jobs were needed.

| Description | Count | Relevant denominator |
|---|---:|---:|
| Changed remaining bundle after an atomic purchase | 21,870 (41.03%) | 53,301 adjacent plan-bearing requests |
| Actual purchases differ from the first selected bundle | 7,763 (47.56%) | 16,323 turns containing search |
| Same, restricted to initially nonempty bundles | 7,763 (52.50%) | 14,786 initially nonempty turns |
| Immediate Pass despite a nonempty previous remainder | 5,157 | 53,301 adjacent plan-bearing requests |
| Changed bundles with tied new estimated credits | 4,006 (18.32%) | 21,870 changed bundles |
| Changed bundles with new estimated advantage at most 1/8 | 13,099 (59.89%) | 21,870 changed bundles |

Every previous remainder was still available in the new candidate menu. All
53,301 pairs changed the public sampling seed. Thus disappearance of the old
candidate does not explain these changes; changed sampling is a plausible
contributor, but this audit does not isolate its causal effect. Thirteen other
pairs changed only action order, without changing the count vector.

Actual turns comprise **8,560 exact**, **2,977 fewer resources**, **3,374 more**
and **1,412 mixed changes** relative to the first selected bundle. The denominator
includes 870 final forced passes without another search; the independent audit
confirms no unfulfilled immediate remainder at those forced passes. Turns that
never invoke resource search are outside this analysis.

Against search opponents, changed-first-bundle turns are 260/401 at 2p,
317/542 at 3p, 375/681 at 4p, 380/740 at 5p and 372/830 at 6p. All 108
count/opponent/rule cells and all game-level counts are retained. Across the full
opponent mix, changed-turn rates are **56.40% in better paired outcomes** and
**56.32% in worse paired outcomes** (200 games each), versus 44.58% in equal
outcomes (1,280 games). These are descriptive, outcome-conditioned associations;
repeated decisions are not independent strength observations.

Three examples were chosen by minimum SHA256 of their identity, without ranking
by outcome or search advantage. Their original games replayed exactly:
**417 legal learner moves**, **115 purchases with no intervening opponent move**,
and identical final scores/credits. Every recorded candidate purchase in those
games was legal in the frozen engine. All **1,484** runtime files match the source
manifest. The within-turn alternatives were compared only for legal inventories,
cash and fuel-supported output; no alternative future outcome was generated.

The examples warn against assuming commitment is always better. In one case,
buying all four originally planned coal would leave $19 and fuel capacity for
three cities; the executed one-coal purchase leaves $28 and fuel for two cities.
The player currently owns two cities in both cases. Its paired resource-search
game ultimately improves over the control, but that does not attribute the gain
to this specific decision. A different early Pass drops a reserve purchase while
leaving enough fuel for every existing city. Blindly completing old plans could
also be harmful.

**Decision remains unchanged:** reject this resource policy. A future controlled
experiment should compare execution-consistent full-turn planning with atomic
replanning, separately testing stable sampling and any override rule. It must
include the frozen filtered-model control and fresh full games across counts and
rules; these receipts cannot establish that commitment fixes the regression.
The current priority remains the unchanged auction/opponent-fidelity study.

Evidence:

- Design: `strong/resource-plan-consistency-design-v1.json` explicitly records
  the one preliminary inspected game and the exploratory status.
- Analyzer, independent conservation/aggregation auditor and exact engine
  replayer: `strong/resource_plan_consistency_v1.py`,
  `strong/audit-resource-plan-consistency-v1.py`,
  `strong/replay-resource-plan-consistency-v1.cjs`. Six focused contract tests pass.
- Raw derived rows and assessments: `ai/runs/resource-plan-consistency-v1`.
  All 1,734 input report/receipt hashes match the prior complete archive.
- Descriptor: `strong/resource-plan-consistency-evidence-v1.json`.
- Private HF revision **963eadd772292c9f8d8099f9648a11f66b8703bb**;
  archive **3a1be7a7150decf8811c5a6de431ef9ea2e8b4c4bcd4d3cc38d8bec7d23ebb1e**,
  **81 files**, downloaded and hash-verified. The other original raw receipts
  remain in the separately pinned complete-screen archive, not duplicated here.
- Original analyzer session **19277**, replay **65623**, independent audit,
  and archive **65655** completed successfully. Do not rerun unchanged work.
