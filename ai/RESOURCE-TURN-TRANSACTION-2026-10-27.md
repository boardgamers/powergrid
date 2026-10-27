# Resource-turn transaction prototype — 27 October 2026

The isolated transaction boundary passes **755 saved resource positions / 2,251
recorded baseline actions**, spanning 2–6 players and all four Germany rule
combinations, plus **23 recorded whole-turn search plans**. It rejects **10,387**
stale or malformed controls and preserves all **755** hidden-information controls.
There were no new model predictions, sampled continuations, full games or HF jobs.
This is an execution component, not a playing-strength result or a qualified policy.

**28 October follow-up:** a separate public response and arena path now replays
120 recorded games exactly; see [the arena execution notes](RESOURCE-TURN-ARENA-2026-10-28.md).
The primitive below is unchanged. The earlier statements about missing arena
support describe its original checkpoint; actual policy-producer integration
and fresh strength testing are still pending.

## Why this component exists

The rejected resource-search screen evaluated complete purchase bundles but
executed their first move and searched again. The subsequent consistency audit
found changed bundles in 41.03% of comparable adjacent decisions and deviations
from the first bundle in 47.56% of turns containing search. Those observations
do not prove that commitment would improve outcomes: some examples also show
that completing an earlier bundle can consume useful building money.

The game wrapper already accepts a complete turn buffer, including resource
purchases followed by Pass (`engine/wrapper.ts`). An experimental full-turn
policy can therefore return its evaluated sequence together, without storing a
partial plan between separate jobs. The existing atomic research transport and
arena do not yet implement that interface; this prototype does not modify them.

## Implemented boundary

`strong/resource-turn-transaction-v1.cjs` loads an explicitly supplied, previously
verified runtime and validates one complete resource turn on a private copy of
its public state. Its caller must verify the runtime manifest before loading it.
The checked envelope binds the acting player and public root, the exact ordered
purchase sequence, cost, inventory, market and final turn boundary. Each purchase
must be legal and tentative; exactly one final Pass must commit the turn.

Verification recomputes the complete envelope. Stale money/round/actor state,
changed costs or actions, incomplete buffers, extra actions after Pass and
unknown fields are rejected. The caller's state and proposed actions remain
unchanged even on rejection. Secret deck contents and prior sealed bids do not
affect the result. The root binding is deliberately strict, including the public
JSON state; it is not a tolerance policy for changing live clock metadata.

No policy weights, search thresholds, candidate bundles, live coordinator files,
active auction source artifacts or production code were changed. The currently
running conservative-auction comparison remains the priority.

## Verification and recovery

`strong/test-resource-turn-transaction-v1.cjs` checks the new boundary against the
previously pinned resource-search runtime, all 755 saved model baselines and all
23 saved searched plans. Every selected plan's cost and post-purchase inventory
also match its original continuation receipts. It verifies the input and runtime
hashes before replaying. This is saved-position engine replay, not new full games.

Results and raw envelopes are under `runs/resource-turn-transaction-v1/` and in
the private evidence archive indexed by
`strong/resource-turn-transaction-evidence-v1.json`. The descriptor references
the existing immutable runtime, fixture and search archives needed to reconstruct
the inputs. The test output directory must be new; do not overwrite earlier
evidence or repeat an archive upload without checking its intent and outcome.

Reproduction after restoring the pinned input archives:

```sh
node ai/strong/test-resource-turn-transaction-v1.cjs /absolute/path/to/new-output
```

The isolated check is complete. A future strength experiment still needs an arena
and public transport adapter that execute the same whole turn, a frozen paired
design, runtime admission, fresh full games and the actual target CPU benchmark.
It should distinguish commitment from stable within-turn sampling and retain the
filtered-model control. Do not adopt the rejected resource policy, use its chosen
actions as improved teacher labels, select rule-specific routing after viewing
results or interpret this component as evidence of improved win rate. No such
new experiment has been admitted or launched here. Final evaluation seeds remain
unused, and no candidate is qualified or deployed.
