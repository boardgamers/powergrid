# Resource sampling and public-state correctness

**28 October update — corrected full-game artifact v2 validated.**

The correction is now integrated into a separately pinned full-game artifact.
Its model turns reproduce 33 existing complete games. Across 334 resource turns
and 1,611 decisions, 12,888 full-state feature/menu checks passed in Steps 1–3,
rounds 1–12, all player counts and all four rules. Corrected atomic search is a
separate mode, so input correction can be distinguished from commitment.
Two predetermined search roots also match historical continuations (96 rollouts,
zero caps). No new strength games or candidate selection were performed.
Read [the v2 integration handoff](RESOURCE-TURN-CORRECTED-INTEGRATION-2026-10-28.md).
Earlier notices below that say full-game integration is pending are superseded;
stable within-turn sampling, fresh runtime admission and strategy evaluation
remain pending. The auction comparison keeps its frozen source.

## Findings

A fixed public sampling seed is feasible for a within-turn control. Across the
20 predetermined first resource-search turns (Germany, 2–6 players, economic
opponents, every original/Recharged and open/sealed combination, seat zero), the
probe reproduced all 51 recorded search seeds/menus and traversed 53 positions.
The seed changed after each of the 33 recorded purchases. Resampling changed the
deck in all 33 transitions, opponent roles in 32, and the continuation RNG prefix
in all 33. Holding the first decision's public seed fixed preserved all three
latent assumptions across each turn: 424 sampled-world checks, plus 53 checks
that structurally valid private-field changes did not affect sampling.

This is a mechanism check, not a causal strength result. There were no new model
inferences in the sampling probe, continuation rollouts, complete game
trajectories, HF jobs, gradients or final seeds. All cases are round 1 / step 1;
late-game and other-opponent coverage is still needed for a general control.

## A separate input bug exposed by the replay

Calling `E.move` on a public state after a purchase recomputes `cardsLeft` and
`nextCardWeak` from its deliberately omitted hidden deck. It therefore reports
an empty deck. This also occurs in the unchanged historical `ModelResourceTurn`,
which uses those incorrect values when encoding subsequent model decisions.
The probe observed that defect on all 33 purchases, and checked the correct
public transition against eight complete sampled states per purchase (264 checks).

`strong/resource-model-turn-v2.cjs` is a separately identified correction. It
wraps the historical model-turn primitive, preserves the two public deck facts
for Resources purchases, and re-encodes the resulting public state. It is limited
to the same Germany scope. It does not read the actual private deck or change
weights, rules, rollout settings or the running auction source.

Actual frozen-1 inference on the same 20 roots made 67 decisions / 47 purchases.
Every corrected observation and legal menu agreed with all eight complete sampled
states: **536 checks**. Initial decisions and complete model plans were unchanged
on these cases. Correct inputs alone do not demonstrate better strength. The
existing auction policy uses atomic resource decisions, not this model-turn path.

The earlier 66 recorded-game replays and eight-game CLI check remain valid as
behavioral replay evidence. They did not prove every intermediate public feature
was correct. Preserve the v1 artifact and results, but do not admit it unchanged
for a new whole-resource strategy study.

## Preserved evidence and failed probes

- `runs/resource-sampling-anchor-v1-validated/`: design, all sampled assumptions,
  recorded transitions, initial-seed comparisons, private-field controls and
  unchanged historical baseline metadata; all 20 turns passed.
- `runs/resource-model-turn-v2/`: fixed-model inference traces, per-step metadata
  and independent full-state feature/menu comparisons; all 20 turns passed.
- `strong/resource-sampling-anchor-results-v1.json` and
  `strong/resource-model-turn-results-v2.json`: tracked assessments with input,
  code, runtime and output hashes.
- `strong/resource-public-state-checks-evidence-v1.json`: verified private HF
  archive descriptor, referencing the already archived runtime, model and roots.

Two earlier local probe failures are preserved with their exact source and logs.
`runs/resource-sampling-anchor-v1/` used a malformed automation object in the
adversarial fixture and completed zero positions; its error exit also left the
reader waiting, so the owned Node process was terminated. The second attempt,
`runs/resource-sampling-anchor-v1-checked/`, completed one position then rejected
the next recorded seed. That mismatch exposed the empty-deck metadata problem.
The final probe preserves the public facts and validates them against eight
complete sampled worlds. No completed game or HF evaluation was repeated.

## Next research work

Integrate the corrected model-turn primitive into a new, separately pinned
full-game artifact, verify its public observations across later rounds, and add
an explicit stable-seed atomic control. Keep the original v1 artifact as the
historical reproduction control. The design must distinguish commitment,
sampling stability and this input correction; otherwise their effects are
confounded. A persistent seed also needs clear reset/recovery boundaries before
it can serve platform requests.

Finish the unchanged auction comparison before choosing the next strategy study.
Any resource comparison still needs fresh paired complete games, stronger
opponents, runtime admission and independent auditing. No candidate is selected
or qualified by these checks, and final seeds remain untouched.

The 45-file evidence archive was uploaded and downloaded successfully at private
HF revision `78d2e4eba6aac8be55bdf70cd358e1c022044c26`:
`archives/resource-public-state-checks-evidence-v1.tgz`, SHA-256
`ad5102c90806005fd201431e2575aeff5bcc6880ff91eb62781c313e2c529f23`.
The active auction owner was independently verified live at its 12:46 UTC
checkpoint, all pinned files unchanged, with 392 audited / 456 submitted selected
jobs. These counts are a snapshot; consult its state before acting.
