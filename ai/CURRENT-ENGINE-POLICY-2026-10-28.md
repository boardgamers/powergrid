# Current-engine discounted nominations: public model check

The unchanged frozen-1 filtered model successfully handled **30 current-engine
public requests**: ten recorded controls and twenty isolated counterfactual
cash changes. All replies were legal, matched the request identity/revision and
retained the pinned model/policy identity. All **ten controls reproduce their
complete recorded decisions exactly**, excluding elapsed time.

This follows the [current-engine menu diagnostic](CURRENT-ENGINE-COMPATIBILITY-2026-10-28.md).
It tests the actual pinned v4 JSON policy service in `filter` mode, with current
engine 2.0.19 menus. It does not change the model, encoder, service, continuation
engine, running studies or deployed game.

## Fixed fixtures and outcomes

At each player count 2–6 and each open/sealed Recharged rule, the fixture is the
first round-after-one nomination with an active discount in recorded economic
episodes 1 and 3. The original control is followed by the same public position
with only the acting player's money changed to one, then to zero. Menus are
recomputed with the separately built current engine. Requests use public cash,
hide the future deck and sealed bids, and carry unique diagnostic request IDs.

| Fixture | Requests | Legal replies | Nominate | Pass |
| --- | ---: | ---: | ---: | ---: |
| Original recorded control | 10 | 10 | 5 | 5 |
| One Elektro, discounted plant available | 10 | 10 | 0 | 10 |
| Zero Elektro, only Pass legal | 10 | 10 | 0 | 10 |

The one-Elektro fixtures include the discounted nomination in the current menu
and omit it from the frozen engine's recomputed menu. The response indexes match
the current menus, including Pass at index 1 in those fixtures rather than index
0 in the old one-action menu. Thus the observed success is not just a silent
fallback to the historical menu. The archive checker verifies every response
index and proposal index against the exact input legal list.

The cash interventions are explicitly **counterfactual**, not naturally sampled
game positions, and do not rewrite historical logs to fabricate trajectories.
Passing in all ten does not prove an error, good strategy, or understanding of
the discount. There was no search, opponent continuation or outcome comparison.
The 30 policy requests took 1.08 seconds including service startup on this local
host; this is not an AMD 8840U latency benchmark.

## Remaining boundary

The public filtered-model interface accepts these newly legal choices without
a schema change. The internal continuation engine still has the old nomination
affordability behavior. This is not whole-game compatibility, a strength result,
support for alternate decks or new option combinations, or final qualification.
Before deploying a selected candidate, explicitly validate the intended current
engine and any separately pinned migration. Keep the existing auction study
unchanged and finish its full comparison before selecting another strength study.

## Evidence

`strong/check-current-engine-policy-v1.py` and its `.cjs` fixture builder produced
`ai/runs/current-engine-policy-v1/`: fixed design, public inputs, descriptor,
30 raw responses, assessment and logs. Preparation verifies the archived current
engine build, frozen artifact manifest and ten recorded source-file hashes.
The check completed once; no failed attempt or repeat inference is hidden.

`strong/current-engine-policy-results-v1.json` binds the design, input and response
hashes. `strong/current-engine-policy-evidence-v1.json` indexes the verified private
HF archive, including independent index checks and references to the existing
engine/source archives. No new HF job, complete game trajectory, gradient,
continuation rollout or final seed was used. Thirty actual policy decisions were
executed; do not describe this turn as zero inference. No candidate qualified or
deployed; the research goal remains active.
