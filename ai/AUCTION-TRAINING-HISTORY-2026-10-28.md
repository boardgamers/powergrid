# Natural auction-discount states recovered — 28 October 2026

The newly affordable nomination is not confined to synthetic cash fixtures.
Replaying existing training-game histories recovered **ten natural public
positions**: **six from training deals and four from a separate validation
deal**. The current engine offers the discounted plant for one Elektro; the
historical engine offered only Pass. All ten were economic-opponent turns,
not learner turns. These are unlabelled regression/teacher-input candidates,
not evidence that buying would have improved the game outcome.

## Scope and results

The first fixed recovery used original deals 0 and 1 from the parent-versus-
economic collection at 2–6 players, all seats and all four rules. It replayed
160 saved prefixes / 87,187 actions and recovered four validation-only cases.
The follow-up used the eleven remaining predefined training deals, excluding
all validation deals and the already checked training deal 1. It replayed
880 more prefixes / 464,461 actions and recovered six training cases.

Combined: **1,040 historical prefixes / 551,648 recorded actions**, covering
960 training-game prefixes and 80 validation-game prefixes. Every original
public endpoint reconstructed exactly after the declared clock exclusions;
the economic state of both engines agreed after every recorded action.
No model, opponent policy, search or fresh trajectory was generated.

| Split | Players | Auction | Cases |
|---|---:|---|---:|
| Training | 5 | Sealed | 2 |
| Training | 6 | Open | 3 |
| Training | 6 | Sealed | 1 |
| Validation | 6 | Open | 3 |
| Validation | 6 | Sealed | 1 |

All recovered positions occur in Step 3 under the recorded option settings,
with `plantDiscountActive` still true. Cash ranges from 27 to 42; plant numbers
range from 28 to 44. For example, a player with 36 Elektro could not nominate
plant 37 under the historical menu, but the current minimum opening bid is 1.
No stored money, plant, history or discount flag was edited to produce these
states. The fixed histories still execute their original Pass actions.

No corresponding gap occurred on learner turns or at 2–4 players in these
prefixes. This is a bounded historical sample, not an estimate of prevalence
under different policies or a proof that the gap cannot occur elsewhere.
The same engine change can strengthen opponents, so it is not automatically
a win-rate gain for our model.

## Reconstruction and information boundary

Both preparations verify the original collection archive and its installed
files, raw root-file hashes and independent collection receipts. The old
runtime is `policy-iteration-collection-collector-v2`; the new engine is the
separate build of commit `3adad0cc0d1d31352aa7a9059bd15efa79647269`.

For each selected game, use its last saved strategic root outside an unresolved
sealed auction. An unresolved auction intentionally hides pending bid moves,
so its public log alone cannot reconstruct its endpoint. Replay the recorded
public move history from the original setup seed without asking any policy
for another choice. Accept a recovered position only if the entire prefix
subsequently reproduces the saved public endpoint and both engines preserve
the same economics for every action.

Public endpoint comparison excludes player clock fields and move timestamps.
Cross-engine economic comparison separately excludes logs, available-move
menus, powering-choice UI metadata and pending messages. Current and old
actor menus are checked explicitly before every replayed action; the only
permitted difference is the newly affordable discounted nomination. No
general current-engine migration or compatibility with other options is
claimed from this test.

Recovered requests use the current engine's public view. They have no future
draw pile, unrevealed bid log, private post-Step-3 deck, automation plans or
real game seed. Sealed bid values are cleared. Original seeds remain in
provenance metadata for reproduction, never in the policy's public request.
The training/validation assignment remains the original whole-deal split;
the four validation cases must not be moved into training.

## Next use

These ten cases are useful for current-engine, legal-menu, encoder and teacher
regressions. They have **no labels**: the historical Pass is not a target for
the newly available choice. Public-belief continuation evaluation would be
required to label both legal alternatives, with training and validation kept
separate and without revealing the replayed true deck/bids to the teacher.

Do not build a broad strength claim or train a complete policy from these six
training cases. The much wider issue remains the missing discount inputs and
the 397 discounted nominations excluded from the previous labelled options,
described in `AUCTION-DISCOUNT-FEATURES-2026-10-28.md`. Finish the unchanged
auction comparison before choosing the next strength experiment; any engine
migration must account for changes to opponent choices too.

## Recovery files

- `ai/strong/recover-auction-training-history-v1.py` and its `.cjs` worker:
  initial fixed training/validation recovery.
- `ai/strong/recover-auction-training-history-v2.py`: remaining predefined
  training deals, using the same replay worker.
- `ai/runs/auction-training-history-v1/` and `...-v2/`: immutable designs,
  source provenance, saved prefixes, replay logs and unlabelled recovered
  requests. Both executions completed successfully on their first attempt.
- `ai/strong/auction-training-history-results-v1.json` and `...-v2.json`:
  reports, input/output hashes and per-prefix checks.
- `ai/strong/auction-training-history-evidence-v1.json`: verified private HF
  recovery archive descriptor. Inspect its existing intent/outcome before
  any upload retry. Original raw collection archives are referenced rather
  than regenerated.

This turn and the previous feature-cache turn are progress. No HF jobs,
gradients, policy decisions, new strength games or deployment were added.
Research remains active; no candidate qualified and final seeds remain unused.
