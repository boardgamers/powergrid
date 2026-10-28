# Auction discount inputs and training coverage — 28 October 2026

The saved training roots retain the public discount flag. A separate schema
`4.4-auction-discount` now appends it to the state and appends the opening bid
and discount amount to each nomination action. This is input preparation, not
a trained or selected policy. The running auction study and its frozen sources
are unchanged. Finish that complete comparison before selecting another
strength experiment.

## What was checked

`prepare-auction-discount-features-v1.py` completed on all **17,280** existing
training/validation roots in 61.85 seconds, without inference, new games,
gradients, HF jobs or inspecting teacher outcomes. Every original public-root
hash, full parent-input hash, cached feature prefix and target-column mapping
matched. The split remains **12,960 training / 4,320 validation** roots, with
the original whole-deal assignment and `policy-iteration-training-v2-` seeds.
No development evaluation or reserved final seeds became training data.

The feature revision changes state/action dimensions from **1217/101** to
**1218/103**. State index 1217 is the public `plantDiscountActive` bit. Action
indices 101 and 102 contain nomination opening bid / 50 and discount / 50;
both are zero for other actions. Existing plant identity, zero immediate
nomination debit, priors, teacher index, shortlist bits and legal menu remain
intact. The opening bid is neither an immediate purchase nor a final auction
price. The extension rejects a missing flag or an incompatible parent schema.

Every saved nomination price matched `minimumPlantBid` in the separately built
current engine at `3adad0cc0d1d31352aa7a9059bd15efa79647269`.
This does not establish compatibility of old continuation targets with that
engine. The parent encoder was loaded from the immutable v4 resource runtime;
the new file is not registered in any running service or source bundle.

The targeted test passed 40 encodings across 2–6 players and open/sealed
Recharged, including one-Elektro and zero-money menus. The ten previously
aliased discount-on/off pairs now differ in the appended inputs, while their
entire old prefixes remain identical. Five additional contract checks cover
non-nomination actions, rejected invalid inputs and the original-rule price.
Those paired flag/cash interventions are synthetic, not evidence of natural
reachability or better moves.

## The remaining data gap

All 17,280 roots retain a Boolean discount flag; it is active in 4,739 roots.
Of the **5,760 nomination roots**, **2,496** have a legal discounted nomination.

| Split | Discounted nomination available | Included in labelled options | Excluded from labelled options |
|---|---:|---:|---:|
| Training | 1,866 | 1,554 | 312 |
| Validation | 630 | 545 | 85 |
| Total | 2,496 | 2,099 | 397 |

Thus **15.9%** of those discounted nominations have no saved teacher target.
The old option set is the economic/geographic shortlist plus the parent move.
The shortlist can omit legal nominations; its economic prior uses the printed
plant number. The correction head cannot choose a move outside that set unless
the parent already proposes it. This is a coverage limitation, not evidence
that the omitted plant was the best move or caused the measured weakness.

The current engine adds/removes **zero nomination options in this selected
training corpus**. This does not cover the known low-cash edge: the old menu
could contain only Pass where the current engine also permits the one-Elektro
plant. A corpus of strategic multi-option roots cannot demonstrate coverage
of those old forced-pass positions. Fresh current-engine collection or a
separately verified reconstruction is needed to cover them naturally.

## Next experiment requirements

After the unchanged auction comparison, decide whether a discount-aware
nomination experiment is the best next investment. Preserve the best model as
the reference and separate input changes from proposal/teacher changes. Check
all legal nomination options rather than inheriting an unexplained shortlist
exclusion; verify the resulting budget and actual option-count bounds before
labelling. Use current-engine public states, fixed training/validation deals
and independent evaluation deals. Do not invent targets for missing choices.

The saved targets were generated with old continuation policies and engine.
The recovered inputs do **not** by themselves admit reusing those targets for
a migrated engine. No new model architecture, warm-start/export parity,
training schedule or strength study has been admitted by this preparation.
The result deliberately records `training_ready: false`.

## Recovery

- Feature module: `ai/strong/features-v4_4.cjs`.
- Preparation and worker: `prepare-auction-discount-features-v1.py` and
  `auction-discount-feature-cache-v1.cjs` under `ai/strong`.
- Targeted test: `ai/strong/test-auction-discount-features-v1.cjs`.
- Completed output: `ai/runs/auction-discount-features-v1/`; do not overwrite.
- Report: `ai/strong/auction-discount-features-results-v1.json`.
- Raw selected roots remain at private HF model repo
  `coyotte508/powergrid-ai-germany-v1`, revision
  `96d59920f004d85016c063eb466a1a66611ec593`, under
  `runs/policy-iteration-selected-v2`. Their SHA-256 values and parent cache,
  runtime and engine references are bound in the preparation design.
- `auction-discount-features-evidence-v1.json` records the verified recovery
  archive once uploaded; inspect its intent/outcome before retrying an upload.

This goal turn is progress: it supplies reproducible candidate inputs and
identifies missing teacher coverage. The preceding recap turn was a verified
wait, with the coordinator process and both runtime handles checked live.
Research remains active. No candidate is qualified or deployed; reserved final
seeds remain unused.
