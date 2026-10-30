# Sealed bidding and target quality — 30 October 2026

The user authorized the next research step after the nomination-only iteration
failed to show convincing gameplay improvement. No objective or automation was
recreated. Keep the existing parent and all historical policies frozen.

## What the existing evidence shows

The new saved-game analysis covers **all 96 sealed parent games** from the recent
two/four/six-player screen, without selecting by outcome. It checks **1,468 sealed
decisions**, reconstructs each auction from subsequently revealed public bids,
and verifies its price and the learner's actual plant expenditure. Those later
disclosures are retrospective evidence only, never policy inputs.

- 1,066 bids, 402 voluntary passes, 449 auction wins.
- 328 wins cost less than the submitted bid; the median difference is 4.
- Only 7 wins leave less than 10 cash. This does not establish sufficient fuel
  or building reserves, but does not support a blanket overbidding fix.
- 60 lost bids and 22 voluntary passes occur with nominal generating capacity
  below owned cities. A capacity shortfall alone does not prove a bad decision.
- 616 decision menus omit some legal bid values under the existing coarse-menu
  rule. This is an observation, not proof that expanding the menu improves play.

Sealed auctions use the engine's second-price rule, including cyclic seat
priority from the nominator for ties and the possible +1 payment. The analyzer
checks this against every observed resolution. It does not confuse the submitted
maximum with the actual price paid. Three focused tests cover that distinction,
exact tie credit, shared sampled worlds, and rejection of corrupt/capped results.

The separate target diagnostic reuses all **5,770 nomination training positions**
and their original 64-world targets. Selecting an action using one 32-world half
and measuring it on the other yields a **+0.04359** average sampled terminal-credit
margin on the 1,444 validation positions, versus **+0.08292** when selecting and
measuring on the same half. Both directions are averaged, using the original
0.025 margin. There is repeatable simulated signal and substantial selection
optimism. These conditional margins are not full-game win-rate improvements, and
both halves share the same opponent assumptions.

The best existing model's frozen routing captures only **+0.002862** on those
validation targets. Removing the disagreement penalty or lowering the override
margin is not a consistent fix: for d1-all0, removing both makes its measured
validation advantage slightly negative; some other arms improve but remain small.
These alternative routes are diagnostics only. No thresholds, weights or policies
were changed, and the same validation targets already influenced checkpoint choice.
The first inference-only diagnostic attempt hit a float32/float64 input mismatch;
its log is retained, the input conversion was corrected, and the completed run
exactly reproduced all four previously recorded validation choice counts/margins.

Results: `strong/sealed-decision-diagnostic-v1.json` and
`strong/nomination-target-diagnostic-v1.json`. This evidence motivates examining
opponent assumptions and learning quality before spending on another large fit.

## Current finite mini-PC pilot

Started **30 October at 22:14:37 Paris**, supervisor **PID 704669**, host `minipc`.
It uses **10 saved training-only bid positions**, one per player count 2–6 and
Original/Recharged combination. Positions are chosen by a fixed SHA ordering
among later-round training roots, without looking at their outcomes. No recent
development games, confirmation positions or reserved final seeds become labels.

For each root, compare the unchanged economic shortlist plus parent fallback
under two continuation populations: existing `neural_population` and the exact
`search_geo` reference opponent. Root actions and sampled initial worlds are
paired. The latter uses arena-opponent identity only as a diagnostic intervention;
that identity must not be added to deployed policy inputs. Prior submitted bids
are inferred from public states, not read from hidden data.

**440 continuations total**, four worlds per root/action/population, four CPU
workers, one inference thread, nice level 10. This is a correctness/runtime pilot;
four worlds cannot admit labels or establish the best action. The local and
target-host preflights independently matched all ten saved legal menus, parent
choices, shortlists and prior-bid actors. The pinned current-engine runtime and
Node executable were verified. Existing files and models were not edited.

Estimated **45–120 minutes**, with a **three-hour hard timeout**. Suggested user
ping: **00:30 Paris, 31 October**. No automatic retries or follow-on jobs. There
are no new HF jobs or gradient updates in this step.

Remote directory: `/home/coyotte508/powergrid-ai-sealed-target-pilot-v1`.
Runtime: `/home/coyotte508/powergrid-ai-current-full-serving-8840u-v1/artifact`.
Protocol: `strong/sealed-target-pilot-protocol-v1.json`.
Original launch: `strong/sealed-target-pilot-launch-v1.json`.

From the repository, observe with:

```sh
PYTHONPATH=ai/strong ai/.venv/bin/python -u -B ai/strong/manage_sealed_target_pilot_v1.py status
```

When terminal, use the same command with `collect`. It downloads original raw
outputs and independently recomputes terminal credits, candidate/world coverage,
shared-world hashes and cap checks. On failure, retain partial evidence and
inspect the original logs; do not blindly relaunch or replace failed cases.

After successful collection, use the measured costs to predeclare a larger
assessment with separate action-selection and evaluation worlds before any new
bid-head training on HF. Keep both opponent populations and adverse results;
do not choose a policy from these four-world pilot scores. No candidate qualified,
no final seeds used, no game deployment.
