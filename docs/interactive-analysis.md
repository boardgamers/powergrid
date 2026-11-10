# Interactive analysis policy

The host-facing `dist/wrapper.js` export `createAnalysisScenario(data, { player, seed })` uses the interactive policy. The strong AI imports
`dist/src/analysis.js` directly; its default information-set sampler is unchanged.
Do not point AI callers at the wrapper's interactive export.

For hidden-money sources (`options.showMoney !== true`), interactive creation
initializes **every** seat to $999, including the requester. These are finite,
hypothetical balances: ordinary costs, affordability checks and income apply.
`analysisMoney: 'hypothetical'` identifies this state to secret stripping and the
viewer. Re-sampling an existing marked branch preserves its evolved balances;
creating a fresh branch from a live source starts a new $999 scenario. Public-money
sources retain their public balances.

Interactive creation does not reconstruct cash from history. It discards private
powering revision snapshots, all source sealed bids (including the requester's),
private logs and automation. Partially sealed auctions reopen every eligible seat
for manual input. Unknown cards still come from the public catalogue, not the
source deck or seed. The source object is not mutated.

`analysisMove` calls only the ordinary atomic rules engine, not the live wrapper's
premoves or affordability/preference auto-passes. Mandatory resolution, market
updates, income and phase transitions remain in effect. No bot/drop status may
choose moves for a seat. Existing one-turn buffer boundaries remain enforced.

## Host integration

No new host API or option is required for the confirmed ongoing-analysis route:
load the updated wrapper export for scenario creation, call its `analysisMove`
for each manually submitted turn, and continue selecting an active seat. Send the
branch's `analysisMoney` field through to the viewer. Never route these moves to
ordinary `move`/`moveAI`, or replace the evolving branch with the live source.
Existing persisted scenarios created before this change need a new branch to get
the new initial-cash policy.

The separate `createAnalysis` exact historical replay hook still retains the
existing finished-source policy (real, now-public historical balances and deck).
Its actors are manual too. Whether hidden-money _finished_ sources should instead
be forced through the hypothetical scenario policy remains a policy decision;
that routing has not been changed here. Ongoing hidden-money sources must use
`createAnalysisScenario`, never exact historical replay.

These changes have not been published. After integrating release master through
`0f0f3eb`, package versions remain engine 2.0.24 / viewer 2.3.26; release bumps are
pending successful publication authorization. The available account can log in,
but the BGS admin metadata request for Powergrid version 13 returns HTTP 403.
No upload or activation was attempted. Historical release receipts are not a
fresh verification of the currently deployed engine.

Post-integration checks: 423 engine tests, engine TypeScript build, 95 viewer unit
tests, viewer library packaging and bundle-size check, eight locale tests, and the
action-label browser smoke checks pass. A local-only hypothetical analysis fixture
also verifies all three seats display `Hypothetical: $999`; it is not evidence of
a deployed host analysis session.
