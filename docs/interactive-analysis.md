# Interactive analysis policy

The host-facing `dist/wrapper.js` export `createAnalysisScenario(data, { player, seed })` uses the interactive policy. The strong AI imports
`dist/src/analysis.js` directly; its default information-set sampler is unchanged.
Do not point AI callers at the wrapper's interactive export.

For hidden-money sources (`options.showMoney !== true`), interactive creation
preserves the authenticated requester's own known balance and initializes opponents
to $999. The host supplies the source-game seat as `player`; spectators receive
$999 for every seat. An already redacted own balance also falls back to $999.
These are finite sandbox balances: ordinary costs, affordability checks and income apply.
`analysisMoney: 'hypothetical'` identifies the sandbox to secret stripping and the
viewer. `analysisKnownMoney` identifies seats initialized from known cash, which
show the normal Money label even as play proceeds. Changing such a balance with
the editor removes that known-cash label; the manually assumed amount is hypothetical.
Re-sampling an existing marked branch preserves its balances. Old analyses that
already replaced the creator's money with $999 cannot recover it; create a fresh
analysis from the live source instead. Public-money sources retain all public balances.
Sharing an analysis also shares the creator's retained balance. This policy does
not change the host's initial displayed seat or manual control of all seats.

Interactive creation does not reconstruct cash from history. It discards private
powering revision snapshots, all source sealed bids (including the requester's),
private logs and automation. Partially sealed auctions reopen every eligible seat
for manual input. Unknown cards still come from the public catalogue, not the
source deck or seed. The source object is not mutated.

`analysisMove` calls only the ordinary atomic rules engine, not the live wrapper's
premoves or affordability/preference auto-passes. Mandatory resolution, market
updates, income and phase transitions remain in effect. No bot/drop status may
choose moves for a seat. Existing one-turn buffer boundaries remain enforced.

## Editing sandbox money

In an editable analysis, select an active seat and use a player's money editor to
set any seat's balance to an integer from $0 to $9,999. Finish or undo tentative
moves first. A balance cannot be reduced below an outstanding auction bid.
Read-only views, live games and ended analyses do not allow edits.

The viewer sends a standalone `SetAnalysisMoney` command with
`data: { player: targetSeat, money: amount }` to `analysisMove`. The server-selected
acting seat remains separate from the target seat. Ordinary live move handlers
reject this command, even inside a buffered turn. Edits are cloned, committed
immediately and saved as analysis history positions without advancing the turn;
legal actions are recalculated and normal spending/income still apply. Stale
powering revision checkpoints are cleared so reopening an old choice cannot
restore the old balance. The upper bound limits materialized legal-bid arrays.

Use the host's saved analysis positions to navigate or branch around edits.
Structured money-edit events also support log reconstruction, but a sampled
scenario's initial hypothetical cash and deck cannot generally be recovered
from its original live-game move log alone.

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
