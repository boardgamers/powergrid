# Power Grid opponent-model fidelity — 25 October 2026

**Decision: do not replace the existing opponent mixture. Test conservative auction search in fresh full games, with learned-opponent coverage as a separate experimental arm.**

All 480 original positions / 23,040 continuations completed and passed independent terminal-credit auditing. Zero outer or nested caps. Coverage: Germany, 2–6 players, all four rules, plant choice/bidding/building; 160 originating games but only two independent deals per count.

| Pre-specified metric | Existing mixture | Learned opponent |
|---|---:|---:|
| Absolute action-margin error | 16.79 pp | 17.33 pp |
| Absolute per-action credit error | 20.92 pp | 21.48 pp |
| Three-way preference agreement, including ties | 48.22% | 53.14% |

The primary learned-minus-mixture error difference is **+0.541 pp**, exploratory 95% whole-deal interval **[−1.234, +2.316] pp**. Lower is better. This does not establish improved continuation fidelity. All 60 groups are retained: 23 improve, 29 worsen, eight tie. Higher preference agreement is secondary and includes ties.

| Players | Mixture margin error | Learned margin error | Difference |
|---|---:|---:|---:|
| 2 | 17.45 pp | 19.01 pp | +1.56 pp |
| 3 | 17.45 pp | 16.67 pp | -0.78 pp |
| 4 | 16.86 pp | 18.10 pp | +1.24 pp |
| 5 | 18.23 pp | 18.18 pp | -0.05 pp |
| 6 | 13.98 pp | 14.71 pp | +0.74 pp |

Descriptively, bidding error improves by 0.99 pp; plant-choice error worsens by 2.30 pp and building by 0.31 pp. These summaries do not authorize phase/rule-specific routing. Among the 43 roots with prior sealed bids (eight represented groups), error worsens by 2.64 pp; those conditional subsets are not a matched causal comparison.

The teacher is a particular search policy, not optimal or human play. There is no economic-prior-only arm, so learned residual benefit is not isolated. Fixed two-action diagnostic outcomes are not training labels. The two-deal uncertainty estimates are exploratory and cannot certify a deployment policy.

Reference continuations used 54,396,368 physical nested evaluations / 160.67 CPU hours. The learned model used 1.90 CPU hours and the existing mixture 1.53. Median time per 16 continuations was 314.88s / 4.93s / 4.99s respectively on shared HF hardware. Those are neither whole-policy nor 8840U latencies.

## Next experiment, frozen before new game outcomes

Compare the filtered frozen-1 model, conservative auction search with the existing population, and the same conservative search with both populations. Keep the existing eight-world, strict 1/8-margin recipe and require nonnegative advantage in each included population. No learned-only replacement, threshold fitting or retrospective rule routing.

The fixed development design has **10,080 games: three arms × 27 count/opponent cells × eight full paired deals** (3,360 games/arm). All counts, seats and four rules are included. First run 64 separate HF runtime-pilot games across the two search arms and 2p/6p against search. These are excluded from strength; the full grid is not admitted or launched yet.

The primary endpoint is the paired mean win-credit improvement against search, equally weighting 2–6 players. Report both conservative contrasts, dual-minus-population, every opponent/rule/count regression and paired whole-deal intervals. No automatic promotion; the original final gate and unused reserved seeds remain mandatory.

Do not extend unchanged surrogate training: its validation best was near epoch 9, later epochs overfit, and this completed fidelity study supplies no overall improvement. This is a reason to change this particular approach, not evidence of a general Power Grid AI plateau.

## Evidence

- Complete immutable study: HF `afe515a3d64dda6f7828c0654ad4fdfab0f481d2`, archive SHA256 `66dab2b8db7d583beabefef81e1c4163d1b82f65039cb58acbd287edb0fc247c`.
- All group and root metrics: `strong/surrogate-continuation-study-comparison-v1.json`.
- Machine-readable review: `strong/surrogate-continuation-study-review-v1.json`.
- Frozen next design: `strong/conservative-auction-development-protocol-v1.json`.
- Actual HF portability smoke passed eight games / 1,607 exact public decisions; this is engineering evidence only.
