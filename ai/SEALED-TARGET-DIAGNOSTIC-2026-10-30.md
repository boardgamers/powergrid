# Sealed bidding and target quality — 30 October 2026

**Update, 31 October:** the 6,160-continuation assessment below is now complete
and independently audited, zero caps, finishing at 03:52:37 Paris in 3h29m41s.
Its bid improvements transfer poorly to stronger search opponents. Current
findings and the next bounded HF learner experiment are in
[TARGET-GENERALIZATION-2026-10-31.md](TARGET-GENERALIZATION-2026-10-31.md).
The remaining launch/status text below is historical recovery information.

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

## Completed mini-PC runtime pilot

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

The original pilot completed **30 October at 22:53:20 Paris**, taking **38m43s**
(2,322.97 seconds). PID 704669 is no longer running. All **440 continuations /
20 components** were downloaded and independently audited, including exact
terminal tie credits, coverage, shared initial worlds, raw hashes and source pins.
**Zero outer or nested caps**. Report: `strong/sealed-target-pilot-complete-v1.json`;
measured costs: `strong/sealed-target-pilot-cost-v1.json`. Neural-population work
took 19.28 seconds in aggregate; reference-search work took 2,302.00 seconds.
Four-world values remain runtime/correctness evidence only, not admitted labels.

The original remote directory is
`/home/coyotte508/powergrid-ai-sealed-target-pilot-v1`; collected raw originals are
in `ai/runs/sealed-target-pilot-v1/collected`. Do not relaunch or recollect over
these files. Earlier estimated completion was 45–120 minutes; it finished sooner.

## Completed target-reliability assessment — 31 October

Started **31 October at 00:22:56 Paris**, supervisor **PID 961705**, host `minipc`.
This uses all ten original training roots and fixed candidate actions. The first
pilot's four sample indices (0–3) are excluded. For each root and each opponent
population, it runs **28 worlds at indices 4–31** and **28 at 32–59**:
**6,160 continuations**, two queues of four CPU workers, one inference thread per
queue, nice 10. Each half is balanced over the four neural-population modes.
The frozen sampler's world seed depends on the public root and sample index,
independently of the total sample count. Policies, engine and hidden-data rules
are unchanged; existing public-money assumptions still apply.

The analysis rule is fixed before these new outcomes: choose the highest mean
terminal-credit action only when its margin over the parent exceeds **1/40**;
favour the parent on ties, then the smallest legal index. Select on one half and
measure on the other, in both directions. Report selectors from the neural
population, reference search and their equal-weight mixture against **both**
evaluation populations. Keep every root and adverse result. Do not tune the
margin or choose a deployable policy using these ten roots. The two directions
share roots and are not independent observations. These are conditional sampled
terminal-credit margins, **not full-game win-rate gains**.

The two queues were balanced by measured runtime only, with projected loads of
4.51 and 4.52 hours before contention/variation. Estimated **5–8 hours** from
launch; suggested ping **09:00 Paris, 31 October**. Hard stop after **12 hours**
(12:22:56 Paris), or on the first failure/cap. No automatic retries or follow-on
jobs. Seven focused audit/selection tests passed; local and mini-PC preflights
independently matched all ten legal menus, parent choices, candidate sets and
prior-bid actors, verifying the complete frozen runtime and Node executable.
Preflights ran no simulated games.

Protocol: `strong/sealed-target-quality-protocol-v1.json`.
Original launch: `strong/sealed-target-quality-launch-v1.json`.
Remote directory: `/home/coyotte508/powergrid-ai-sealed-target-quality-v1`.
Runtime: `/home/coyotte508/powergrid-ai-current-full-serving-8840u-v1/artifact`.
From the repository:

```sh
PYTHONPATH=ai/strong ai/.venv/bin/python -u -B ai/strong/manage_sealed_target_quality_v1.py status
```

Once terminal, use `collect` instead of `status`. It downloads the original raw
outputs, independently recomputes credits and paired worlds, checks all 40
components and produces `strong/sealed-target-quality-complete-v1.json`. If the
run fails, preserve partial outputs and inspect the original logs; do not blindly
relaunch, retry collection over existing files, or replace failed roots. Remote
`lane-0.log`, `lane-1.log`, `execution.json`, and `state.json` record progress and
termination. Do not rerun `prepare` or `launch` for the existing run.

Completed pilot evidence and this run's recovery package are privately archived;
immutable revision, SHA and download verification are recorded in
`strong/sealed-target-quality-start-evidence-v1.json`. The prior diagnostic/source
references remain in `strong/sealed-target-diagnostic-evidence-v1.json`.

Next: audit this finite assessment and examine repeatability and transfer across
opponent assumptions, with explicit uncertainty from ten roots. Then define a
broader learning experiment if warranted. Any gradient training belongs on HF.
The nomination-only candidate iteration remains closed; its 35 deferred shards
stay unsubmitted. No new HF jobs, gradients, objective, automation, final-seed
use, candidate qualification or deployment in this step.
