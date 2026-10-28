# Current-engine transition replay — 28 October 2026

The fixed 33-game historical corpus replays through the frozen research engine
and pinned current engine 2.0.19 with **16,330 matching economic transitions and
33 identical terminal economies/outcomes**. This extends the earlier
[menu checks](CURRENT-ENGINE-COMPATIBILITY-2026-10-28.md) beyond legal choices to
their consequences. It does not migrate a running study or qualify a policy.

The current-engine source is commit
`3adad0cc0d1d31352aa7a9059bd15efa79647269`, from the existing isolated build.
The checker verified that build and the frozen v4 runtime manifests before
execution. It did not rebuild or modify either engine or the live checkout.

## Coverage and method

Every learner action comes from the already recorded games. Deterministic
original economic/legacy opponents regenerate the intervening actions; those
exact actions are applied to the current engine as well. No neural inference,
continuation search, fresh strength trajectories, HF jobs or gradients ran.

- All **3,443 learner requests** and their ordered candidate lists matched the
  historical requests, apart from explicitly excluded execution timestamps.
- **4,720 learner actions + 11,610 opponent actions** were applied to both engines.
- Economic state, private deck state, phase, round, step and turn order matched
  after every action. All resulting ordinary moves, including engine-derived
  discount annotations, remained part of the comparison.
- Legal menus and hidden bid logs matched throughout. No new discounted
  nomination arose naturally in this fixed corpus.
- All 33 final states reproduced their recorded outcome, money, city counts,
  powered cities, plant capacities and plant holdings.

| Coverage | Transitions |
| --- | ---: |
| Two players | 2,842 |
| Three players | 1,932 |
| Four players | 2,595 |
| Five players | 3,094 |
| Six players | 5,867 |
| Original, sealed | 5,943 |
| Recharged, sealed | 2,973 |
| Original, open | 4,048 |
| Recharged, open | 3,366 |

All four gameplay phases and Steps 1–3 are covered. Transitions include every
seat, although learner decisions are at seat zero plus the previously selected
last-seat original-sealed economic cases; this is not a balanced new evaluation.

## Explicit exclusions and observed differences

Player clocks, `poweringChoices` snapshots and `pendingMessages` are excluded
from the economic comparison. Menus and logs are compared separately, rather
than silently ignored. Historical public-request matching removes move
`time`/`serverTime` fields and player clocks because replay execution timestamps
differ. The old and current engines receive the same stamped moves.

All **15 semantic log differences** are exactly one extra
`Starting Step 3.` event appended by the current engine. Bid logs and all other
semantic log deltas match. Log presentation strings are not semantic comparisons.
The evidence archive independently checks this classification.

Two initial checker failures are preserved. First, the legacy bot's timestamped
move was wrongly compared as a complete object against a name/data-only menu
after five completed games. Second, after eight completed games, the checker
rejected `usedPlantDiscount`, an annotation added by the old engine to the
executed move. Neither was an engine rejection. The corrected harness compares
menu membership by name/data and passes only name/data/timestamps to the current
engine, requiring it to derive the same resulting annotations independently.
The economic comparison was not weakened. Successful replay counts refer to
33 unique historical games, not the sum of repeated prefixes.

## Remaining work

The [targeted nomination check](CURRENT-ENGINE-POLICY-2026-10-28.md) established
that the filtered-model interface can accept the newly affordable discounted
plant, but did not establish its strategic quality. This replay does not exercise
that edge, alternate decks, the optional Step 3 discount rule, edited powering
or bid choices, wrapper auto-pass, or new model decisions on current-engine
trajectories. The internal search runtime still uses the frozen historical engine.

Finish the complete unchanged auction study before choosing another strength
study. Before qualification/deployment, explicitly select and pin the intended
engine, validate its serving/wrapper behavior and unsupported options, and
evaluate any migration separately. These replay checks are engineering evidence,
not added win-rate samples or final qualification. Final seeds remain unused.

`strong/current-engine-transitions-results-v1.json` records the complete report
and hashes. `strong/current-engine-transitions-evidence-v1.json` indexes the
verified private HF archive, including both failed checker versions and their
diagnoses, successful design/results, log deltas, and references to the existing
immutable engine and recorded-game archives.
