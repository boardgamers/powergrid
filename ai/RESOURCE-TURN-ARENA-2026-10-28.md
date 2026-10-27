# Complete resource turns in a separate research arena

The new execution path replays **120 existing games / 15,838 recorded learner
actions** exactly, grouping **1,167 resource turns / 5,253 actions** into complete
purchase buffers. The original and new arenas agree on every compared logical
observation, atomic step count, move count and terminal result. This enables a
future controlled commitment experiment; it does not show that committing a
purchase plan improves play.

The live 10,080-game auction comparison is unchanged. Its coordinator remains
the only submitter/collector. No new HF jobs, model predictions, sampled games,
training, final seeds or game deployments were used for these checks.

## Execution boundary

`strong/resource-turn-exchange-v1.cjs` turns an already chosen complete action
sequence into a public response. The response binds the request ID/revision,
acting player, permitted public state, policy/model/runtime identities, exact
ordered purchases, inventory, cost, market and final Pass. It has no selection
logic and does not load a model or rank candidate plans.

The arena independently checks that response against its current private state,
validates every move, and applies the sequence to a private clone. It replaces
the live state only after validation succeeds. Purchases remain tentative; exactly
one final Pass commits the turn. Hidden state is preserved in the arena and never
included in the policy response. Malformed or stale responses are rejected without
leaving partial purchases behind.

`strong/resource-turn-arena-bridge-v1.cjs` is a separate, explicitly enabled
extension of the existing arena. Enable `publicMoves` and `publicResourceTurns`,
provide the expected policy identity on reset, and return
`{publicResourceTurn: response}` in the learner's step. The bridge issues request
metadata from its episode and atomic-step counter. It advances opponents only
after the final Pass and charges the original number of atomic moves against the
arena cap. Other phases retain the existing atomic move interface.

Both components require a caller-verified runtime. They are currently exercised
with the immutable resource-screen runtime, not a new standalone inference
artifact. The supported resource scope remains Germany, 2–6 active players,
original/Recharged, open/sealed, with permitted public money. This is not a live
platform adapter: production clock tolerance, saved-turn buffer semantics and
policy packaging still need explicit integration.

## What was verified

The replay selection is fixed without regard to outcome: deal zero, all seats
and all four rules against economic opponents (**80 games**), plus seat zero in
all player-count/rule combinations against legacy opponents (**20**) and from
the previously rejected resource-search arm against economic opponents (**20**).
The tests group the moves actually recorded in those games; they do not replace
them with an earlier proposed plan or claim that the rejected strategy improved.

The checker uses the original frozen arena in one subprocess, the new JSON arena
in another, and the new direct adapter. It verifies all **1,484** runtime files
and **135** archived input files before replay. Only JSON omission of undefined
optional properties, added request metadata/legal menus, and the existing
legacy-bot wall-clock bookkeeping are excluded from cross-instance logical
observation comparison. Terminal results and atomic counters must match exactly.

The checks also reject **1,320** malformed/stale controls, preserve **1,167**
hidden-data controls, and reject **200** responses bound to another instance's
clock state. Root binding remains strict; the test supplies each independent
arena's own exact root rather than weakening that contract. Two initial harness
failures are preserved: optional-undefined wire normalization, then the
cross-instance clock mismatch. Neither was a live HF job failure.

`strong/audit-resource-turn-arena-v1.py` separately checks archived-input hashes,
predetermined coverage, response identities, action order, and purchase
conservation. All **4,086** recorded purchases appear exactly once in the grouped
responses. It does not rerun the engine or make another strength estimate.

## Recovery and next work

Successful raw evidence is under `runs/resource-turn-arena-v1/`; the two preserved
attempts have `-attempt1` and `-attempt2` suffixes. The tracked assessment and
private HF archive are indexed by `strong/resource-turn-arena-results-v1.json`
and `strong/resource-turn-arena-evidence-v1.json`. The archive references the
immutable original resource-screen source and complete raw-game archive, rather
than duplicating those large inputs. Restore them at the paths recorded in the
assessment before reproducing into a new output directory:

```sh
node ai/strong/test-resource-turn-arena-v1.cjs /absolute/path/to/new-output
ai/.venv/bin/python -B ai/strong/audit-resource-turn-arena-v1.py /absolute/path/to/new-output
```

Next complete the unchanged auction comparison. If the resource experiment is
pursued, connect the actual chosen-plan producer to this response interface,
add a separately pinned evaluator/receipt audit, and freeze a paired design that
distinguishes commitment from stable within-turn sampling. Preserve the filtered
model control and measure fresh complete games before interpreting any gain.
Target-CPU checks and final qualification still apply to whichever policy is
eventually selected. No resource-search policy has been adopted or qualified.
