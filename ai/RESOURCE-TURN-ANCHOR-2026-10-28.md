# Stateless sampling anchor for resource purchases

## Result and scope

The current buyer's public purchase suffix can reconstruct the exact
first-decision sampling seed without keeping a cache between bot calls. The new
research helper `strong/resource-turn-anchor-v1.cjs` is separate from every
historical or currently running policy. It does not choose or execute a move.

The validation passed on **354 recorded turns / 1,664 positions**, comprising
all 334 resource turns from the 33 already selected corrected-model games and
the 20 previously selected historical atomic-search turns. Selection was fixed
by those existing datasets, not wins or plan changes. At every position the
reconstructed observation, legal menu and sampling seed exactly match the actual
first decision. All **13,312 sampled latent-world checks** preserve the deck,
opponent roles and rollout RNG prefix within the turn. The ordinary state-based
seed changes after all **1,310 purchases** in this set; the anchor does not.

Coverage includes 2–6 players, original/Recharged and open/sealed rules, Steps
1–3 and rounds 1–12. There are 105/55/55/53/86 turns at 2/3/4/5/6 players,
and 218/38/98 turns in Steps 1/2/3. The validation also checks 1,664 duplicate
requests, 1,664 reverse-ordered requests, 1,664 private-field/request-ID
contamination controls, 3,158 invalid requests and 354 untracked-spending cases.
All 51 historical search seeds present in the 20 atomic-search turns reproduce.
Validation took 91.921 seconds locally; this is total checker runtime, not a
serving or target-CPU latency benchmark.

This is mechanism evidence, **not stronger play**. No model inference, future
continuation, new complete-game trajectory, HF job or gradient was run for this
check. Sampling a possible hidden deck is not simulating a future game. No final
seed was used and no candidate is qualified.

## Reconstruction contract

The helper requires a standard Germany Resources state with public balances,
2–6 non-dropped players, one current buyer, feature revision 4.3 and the complete
canonical public log. It first strips hidden information using the pinned public
state implementation. Starting at the end of the log, it reverses only that
buyer's contiguous `BuyResource` moves:

- Recover each price from the current market position and the public price rack.
- Restore cash, held fuel, market inventory and tracked spending.
- Restore the turn boundary and legal menu. Germany retains `chosenResource`
  across turns, so its preceding value is recovered from the earlier public log.
- Replay the removed purchases using the authoritative engine, preserving the
  unchanged public deck metadata, and compare the current observation and menu.

The returned prepared input is compatible with the existing `public_seed`
function. Additional `resourceTurnAnchor` metadata records the revision, buyer,
round, step, number and cost of reversed purchases, and public-log boundary.
The helper has no per-game or per-turn mutable state. A fresh instance is used
for every validation request, including repeats and reverse-order requests.

Unsupported map/phase, hidden balances, missing boundary, inconsistent new-turn
metadata, impossible inventory, market-side and supply purchases fail explicitly.
There is no silent fallback to a fresh seed. The helper does **not authenticate
arbitrarily forged or selectively rewritten history**: the platform must provide
the authentic complete log. Testing an observable missing-tail error is not proof
that every form of log truncation can be detected. A truncated-log deployment
would need a different contract and validation.

The historical baseline's empty-public-deck input defect remains isolated in its
old artifacts. This new replay preserves `cardsLeft` and `nextCardWeak` after
purchases, following the separately verified v2 correction. Neither the frozen
auction study nor any v1/v2 full-resource policy was edited.

## Saved evidence

- `strong/resource-turn-anchor-v1.cjs`: stateless reconstruction helper.
- `strong/check-resource-turn-anchor-v1.cjs` and `.py`: one-shot checks.
- `runs/resource-turn-anchor-v1/`: fixed design, exact checker source copies,
  position-level seeds and sampled-world receipts, stderr and assessment.
- `strong/resource-turn-anchor-results-v1.json`: assessment and source/input hashes.
- `strong/resource-turn-anchor-evidence-v1.json`: verified private HF archive
  descriptor, created by the existing verified evidence-archive helper.

Original game and source data are referenced through their immutable archive
descriptors, not rerun. The immediate parent evidence is
`strong/resource-turn-full-integration-evidence-v2.json`; historical atomic-search
inputs come from the original full-resource and resource-replanning archives.
Inspect existing output/intent files before recovery. Do not rerun completed
checks without changed code or a specific unresolved concern.

## Next action

Integrate this helper into a separately pinned stable-sampling search mode and
independent receipt auditor, preserving the corrected atomic and whole-turn
controls. Match first-decision searches exactly before evaluating differences
later in the turn. Check process restart/lifecycle behavior in that full policy,
then admit a fresh full-game runtime pilot with measured compute costs.

Finish the unchanged auction comparison before selecting the next strength study.
Its sole owner PID 1075760 was confirmed live with all code pins matching at the
14:06 UTC snapshot: 477 audited / 538 selected jobs submitted, out of 648 planned
jobs / 10,080 games. Two earlier infrastructure failures remain preserved among
540 total attempts. These are execution counts, not partial strength results.
No new owner, competing collector or development study was started here.

The preceding status-only turn was a verified wait (the actual owner process was
checked live). This turn is progress: the previously missing stateless anchor is
implemented and its mechanism is validated. Research remains active; final
qualification, broad opponent coverage, selected-policy export and target-device
verification remain outstanding.

The 27-file evidence archive was uploaded and downloaded successfully at private
HF revision `433586055f1733c20b8aa8e470b8f63aad2b8882`,
`archives/resource-turn-anchor-evidence-v1.tgz`, SHA-256
`63bdb20c491d20282db3b15f11348bcf066afbc643582d12beea2bdf33f55f3f`.
The archive descriptor and this final reference are saved in Git.
