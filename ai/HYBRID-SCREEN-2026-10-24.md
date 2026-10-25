# Power Grid hybrid screen — 24 October 2026

All **135 batches / 8,400 games** completed and passed verification. The unchanged
comparator reproduced exactly; all raw results, decision receipts and recovery
proofs are archived in the private HF repository. No final candidate was selected.

**Decision:** continue investigating auction search, keep the filtered model as
the research reference, and do not advance this building-search or combined-search
implementation. Auction search has meaningful regressions that must be explained
before larger confirmation. No new jobs were submitted by this review.

Each arm has 1,680 games over Germany 2–6 players, all four rule combinations,
all seats and 27 count/opponent cells. Each cell has only **four independent deals**.
The table percentages include fractional credit for ties. They are exploratory.

## Against the independent search opponent

| Players | Model | Filter | Auction | Building | Combined |
|---|---:|---:|---:|---:|---:|
| 2 | 62.5% | 62.5% | 78.1% | 53.1% | 65.6% |
| 3 | 41.7% | 41.7% | 66.7% | 37.5% | 35.4% |
| 4 | 50.0% | 50.0% | 53.1% | 45.3% | 33.6% |
| 5 | 47.5% | 47.5% | 50.0% | 35.0% | 35.0% |
| 6 | 45.8% | 45.8% | 58.3% | 45.3% | 43.7% |

## Search opponent, each rule combination

| Players / rules | Model | Filter | Auction | Building | Combined |
|---|---:|---:|---:|---:|---:|
| 2 / original/open | 62.5% | 62.5% | 75.0% | 75.0% | 87.5% |
| 2 / original/sealed | 87.5% | 87.5% | 87.5% | 75.0% | 50.0% |
| 2 / recharged/open | 75.0% | 75.0% | 62.5% | 25.0% | 62.5% |
| 2 / recharged/sealed | 25.0% | 25.0% | 87.5% | 37.5% | 62.5% |
| 3 / original/open | 50.0% | 50.0% | 58.3% | 66.7% | 41.7% |
| 3 / original/sealed | 33.3% | 33.3% | 83.3% | 25.0% | 41.7% |
| 3 / recharged/open | 58.3% | 58.3% | 66.7% | 58.3% | 25.0% |
| 3 / recharged/sealed | 25.0% | 25.0% | 58.3% | 0.0% | 33.3% |
| 4 / original/open | 81.2% | 81.2% | 31.2% | 68.8% | 31.2% |
| 4 / original/sealed | 25.0% | 25.0% | 62.5% | 25.0% | 18.8% |
| 4 / recharged/open | 50.0% | 50.0% | 50.0% | 62.5% | 40.6% |
| 4 / recharged/sealed | 43.8% | 43.8% | 68.8% | 25.0% | 43.8% |
| 5 / original/open | 50.0% | 50.0% | 50.0% | 30.0% | 25.0% |
| 5 / original/sealed | 30.0% | 30.0% | 40.0% | 20.0% | 45.0% |
| 5 / recharged/open | 70.0% | 70.0% | 50.0% | 55.0% | 40.0% |
| 5 / recharged/sealed | 40.0% | 40.0% | 60.0% | 35.0% | 30.0% |
| 6 / original/open | 62.5% | 62.5% | 66.7% | 68.7% | 58.3% |
| 6 / original/sealed | 37.5% | 37.5% | 45.8% | 12.5% | 20.8% |
| 6 / recharged/open | 50.0% | 50.0% | 58.3% | 62.5% | 62.5% |
| 6 / recharged/sealed | 33.3% | 33.3% | 62.5% | 37.5% | 33.3% |

Auction search improves Recharged sealed point estimates at every count.
However, four-player original/open falls from **81.25% to 31.25%**
(8 worse paired outcomes, no better outcomes, 16 games / four deals).
Five-player Recharged/open falls from **70% to 50%** (6 worse, 2 better,
20 games / four deals). Three-player heuristic falls from **100% to 85.42%**
(7 worse, no better, 48 games / four deals). These cannot be hidden by the
overall auction gains or used to invent a retrospectively optimized rule switch.

The strict loss filter changes no search-opponent win totals in this screen.
It improves several other cells and has no negative point estimate here;
this is not a guarantee of universal improvement.

## Every count/opponent cell

| Cell | Model | Filter | Auction | Building | Combined |
|---|---:|---:|---:|---:|---:|
| economic/2p | 65.6% | 65.6% | 84.4% | 68.8% | 87.5% |
| economic_capacity_v1/2p | 62.5% | 62.5% | 93.8% | 65.6% | 81.2% |
| heuristic/2p | 87.5% | 87.5% | 78.1% | 78.1% | 62.5% |
| legacy/2p | 96.9% | 96.9% | 100.0% | 93.8% | 100.0% |
| rush/2p | 68.8% | 71.9% | 100.0% | 68.8% | 84.4% |
| search_geo/2p | 62.5% | 62.5% | 78.1% | 53.1% | 65.6% |
| a260/3p | 22.9% | 22.9% | 39.6% | 27.1% | 39.6% |
| economic/3p | 75.0% | 75.0% | 83.3% | 70.8% | 83.3% |
| heuristic/3p | 100.0% | 100.0% | 85.4% | 91.7% | 81.2% |
| legacy/3p | 93.8% | 100.0% | 100.0% | 95.8% | 97.9% |
| rush/3p | 70.8% | 72.9% | 87.5% | 72.9% | 79.2% |
| search_geo/3p | 41.7% | 41.7% | 66.7% | 37.5% | 35.4% |
| economic/4p | 70.3% | 70.3% | 76.6% | 53.1% | 70.3% |
| heuristic/4p | 96.9% | 96.9% | 96.9% | 92.2% | 93.8% |
| legacy/4p | 85.9% | 87.5% | 98.4% | 95.3% | 96.9% |
| rush/4p | 62.5% | 62.5% | 79.7% | 64.1% | 68.8% |
| search_geo/4p | 50.0% | 50.0% | 53.1% | 45.3% | 33.6% |
| economic/5p | 67.5% | 70.0% | 90.6% | 83.8% | 85.0% |
| heuristic/5p | 97.5% | 97.5% | 96.2% | 100.0% | 90.0% |
| legacy/5p | 86.2% | 88.8% | 91.3% | 87.5% | 92.5% |
| rush/5p | 81.2% | 82.5% | 88.8% | 88.8% | 85.0% |
| search_geo/5p | 47.5% | 47.5% | 50.0% | 35.0% | 35.0% |
| economic/6p | 78.1% | 79.2% | 91.7% | 71.9% | 87.5% |
| heuristic/6p | 99.0% | 99.0% | 97.9% | 99.0% | 97.9% |
| legacy/6p | 93.8% | 96.9% | 95.8% | 94.8% | 89.6% |
| rush/6p | 71.9% | 72.9% | 92.7% | 88.5% | 87.5% |
| search_geo/6p | 45.8% | 45.8% | 58.3% | 45.3% | 43.7% |

## Execution and next steps

All game and rollout cap counts are zero. Timing below is from shared HF
cpu-upgrade jobs with eight concurrent games, **not AMD 8840U latency**.

| Arm | Search decisions | Search changes | Rollouts | Search median / p95 |
|---|---:|---:|---:|---:|
| model | 0 | 0 | 0 | — |
| filter | 0 | 0 | 0 | — |
| auction | 51,922 | 18,813 | 2,099,704 | 18.9s / 64.5s |
| building | 33,462 | 9,007 | 1,432,904 | 8.9s / 40.6s |
| combined | 84,759 | 27,856 | 3,499,072 | 24.7s / 87.7s |

Of 18,813 auction changes, 9,977 have a simulated mean-credit advantage of at most 1/8 over the model action. That motivates checking
selection noise; it does not establish the cause of any loss. Opponent
mixture mismatch and approximating future search with model-only play also
remain hypotheses, not measured explanations.

1. Replay paired auction regressions and suitable improved controls from immutable saved data; inspect bidding, candidate margins and simulated opponent behavior.
2. Distinguish finite-world selection noise, opponent-model mismatch and future-policy approximation with separately specified diagnostics; none is established by terminal summaries.
3. Only after addressing regressions, freeze the policy and run larger fresh all-count/all-rule confirmation. Do not retrofit routing to the favorable cells.
4. Keep the separate resource-replanning ablation unlaunched until its source and full-game runtime admission are complete.
5. Before final qualification, implement the exact selected-policy final adapter and repeat full target-hardware evidence; existing model-only receipts are insufficient.

**Progress assessment:** this is not evidence of a general plateau.
Auction search offers a promising direction, but running more unchanged
building/combined search or indiscriminately distilling its actions is not justified.

## Persistent evidence

- [Full comparison](strong/population-hybrid-development-comparison-v1.json).
- [Machine-readable review, all adverse auction cells and paired terminals](strong/population-hybrid-development-review-v1.json).
- [Archive descriptor](strong/population-hybrid-development-complete-evidence-v1.json).
- Private HF revision: `91076fb5f4cffed75bf2ddd22f70f3442f78c00d`.
- Archive SHA256: `d9f140ced5394b154eaddced865723ca70e064a5e311d5ff098319d0f6f0b1fc`.
- Comparison SHA256: `6acbd8e57990f4cb9dc775b46b3859db18ccab3cb653dc50552c92f60a86bcbb`.
- Final qualification protocol and reserved seeds remain unchanged and unused.


## 25 October: completed opponent-assumption diagnostic

All 28 original HF jobs completed and verified: **896 reference-opponent
continuations plus 896 fixed-mixture controls**, no outer or nested caps. Seven
previously selected public positions each compare only the two already fixed
model/search actions. The first eight worlds are diagnostic repeats; the primary
comparison uses the remaining 56 worlds. No action is reselected from these results.

Numbers below are **selected action minus model action terminal-credit estimates**,
in percentage points, conditional on each sampled position and continuation setup.
They are not full-game win rates or calibrated probabilities.

| Root / selected position | Existing mixture | Reference opponents | Change, with paired 95% interval |
|---|---:|---:|---:|
| 0 — 4p original/open regression | +12.5 | +1.8 | −10.7 [−32.1, +12.5] |
| 1 — 5p Recharged/open regression | −8.9 | +8.9 | +17.9 [0.0, +35.7] |
| 2 — 3p heuristic regression | +3.6 | 0.0 | −3.6 [−14.3, +5.4] |
| 3 — 4p Recharged/sealed improvement | −12.5 | +11.6 | +24.1 [+8.9, +41.1] |
| 4 — 4p original/sealed improvement | +16.1 | −5.4 | −21.4 [−30.4, −12.5] |
| 5 — 2p Recharged/sealed improvement | −1.8 | +14.3 | +16.1 [−5.4, +37.5] |
| 6 — 6p Recharged/sealed improvement | +12.5 | +7.1 | −5.4 [−30.4, +19.6] |

The intervention changes the sign at four roots (1, 3, 4, 5). Its paired interval
excludes zero at roots 3 and 4, in opposite directions. This supports treating
opponent-model mismatch as a real concern at these inspected positions. Increasing
the existing mixture's sample count alone does not address that concern.

Interpretation remains conditional: these roots were selected using earlier game
outcomes; the known arena opponent identity is unavailable in deployment; and
prior sealed-bid inference and future opponent policy changed together where prior
inference exists (roots 4 and 6). Root 3 has no prior-bid evaluations, so its
intervention does concern future opponent play. Reference search opponents retain
their own historical internal rollout assumptions. None of the seven reference
selected-minus-model intervals has a strictly positive lower bound. These results
therefore do not certify the selected actions as training targets or establish a
stronger deployable policy.

**Decision:** continue auction research with a fresh-position experiment that tests
stronger opponent coverage and cautious action overrides; preserve all adverse
count/rule results and model-only controls. Keep deployment opponent identity out
of the input contract. Do not indiscriminately distill these outcome-selected roots.
The isolated 3,360-game resource screen is now running under its own frozen plan;
its results are not available yet. No general plateau conclusion is justified.

The independent audit recomputed terminal credits from final players, used rational
paired margins and bootstrap block multiplicities, and checked all 64 world/action
pairs per root. Runtime totals: **85,247.13 CPU seconds**, maximum job wall time
**3,483.18 s**, maximum sampled summed process RSS **1.47 GB** on CPU Basic. Those
nested-search costs are diagnostic execution, not 8840U serving latency.

- [Complete comparison](strong/reference-opponent-comparison-v2.json).
- [Independent full audit and archive descriptor](strong/reference-opponent-complete-evidence-v2.json).
- Private HF revision: `baa0e390312c92e9bde3a2979e1e310a1a9330e4`.
- Archive SHA256: `131837afcf38a3dde522fa0810551d744cf309670ec1d475fcf8359d9293f1c6` (301 files).

## 25 October: recommendation after the next completed experiments

**Continue with selective auction search, keeping the fast model as the default.**
Do not adopt unchanged building or resource search, and do not extend the completed
opponent-imitation training run simply to spend more compute.

The user's original four-player baseline, **30.9% overall / 15.6% Recharged sealed**,
is superseded by frozen-1's **51.5625% / 39.0625%** in the larger development
evaluation (256 / 64 games, 16 independent deals). Those are different seeds and
sample sizes from this exploratory hybrid screen. Within this screen, auction
search improves four-player Recharged sealed **43.75% → 68.75%**, but original/open
regresses **81.25% → 31.25%**. Its four-deal cells justify investigation, not a
claim of a reliably stronger hybrid or a hand-picked switch by game variant.

The separate resource-search screen is now complete and rejected: its primary
equal-player-count comparison against search is **−9.1875 percentage points**,
95% whole-deal interval **[−16.36484, −1.55182]**. See
[the complete resource review](RESOURCE-SEARCH-SCREEN-2026-10-25.md).

The learned opponent surrogate has completed four-seed HF training, validation
selection and held-out evaluation. Across 320 unseen games / 52,360 decisions,
macro exact teacher agreement improves only **60.0598% → 60.5742%**, despite a
large NLL reduction. All seeds' best epochs are 9–10; later training overfits.
This does not establish stronger playing decisions. The frozen continuation study
must test whether the surrogate better predicts the consequences of candidate
actions; a later full-game experiment must separately establish strength.
The study compares it with full-search reference opponents and the existing
population, without a prior-only arm. Do not attribute a possible improvement
specifically to learned residuals without that additional comparison.

For serving, retain instant model decisions and investigate an optional auction
search budget. Actual 8840U **model-only** latency is median 4.3–5.9 ms; full hybrid
latency is still unknown. Distillation should use verified search improvements
after fresh full-game confirmation, not all search overrides indiscriminately.

No general plateau is established. The useful next question is whether improved
opponent coverage and cautious overrides preserve auction gains while avoiding
the regressions. Training longer on this same imitation configuration, adding
unchanged resource/building search, or increasing samples under an inaccurate
opponent model are not justified by the evidence so far.

- [Completed training and held-out evidence](strong/opponent-surrogate-trained-evaluation-evidence-v1.json).
- [Current operational handoff](RESUME.md), including the original timing job and next steps.

## 25 October: standalone auction prototype verified on engineering fixtures

The shared JSON worker and development arena now support `opponent-auction-v1`.
It retains the filtered focal model outside auctions, keeps the model action in
the auction shortlist, and can evaluate the unchanged population and learned-
opponent continuation paths. Each included population receives equal weight.
The caller explicitly supplies a rational minimum advantage. An override must
strictly exceed that pooled margin and must have a nonnegative margin within
every included population. Exact terminal tie credits determine the calculation;
any capped continuation keeps the model. This is an empirical screening rule,
not calibrated confidence or a guarantee of stronger play.

The engineering artifact uses both populations, eight worlds each, and a strict
**1/8** minimum pooled advantage. **This is not a selected strength recipe.**
The ongoing 480-root study remains unchanged; none of its partial outcomes was
used to tune this implementation. Here the mixture combines separate population
scenarios; it does not assign surrogate and heuristic roles together inside each
learned-opponent scenario. Prior sealed bids remain modelled rather than observed.

Standalone checks completed on the 24 existing 2p/6p runtime fixtures, all rules
and plant/bid/building phases:

- **16 auction searches / 1,328 continuations / zero unexpected caps**; three
  prototype overrides. Eight building decisions retain the original filtered model.
- **512 exact archived continuation matches**, covering every original fixed
  action pair within the now-expanded candidate menus. Initial sampled worlds,
  inferred bids, policy decision counts and terminals match; only array position
  `env` changes with the larger candidate menu.
- The saved-receipt checker reuses the independently audited fixed-pair verifier
  for every model/alternative pair and separately reconstructs pooled means,
  per-population margins, eligible candidates and the selected action.
- A repeated auction request matches the direct class exactly after excluding
  elapsed time. Changed request metadata/unused opponent metadata do not change it.
- Ten saved model/filter checks cover all five player counts. Seven chooser
  contract tests and eleven public transport/arena contract tests pass.
- An intentional one-step horizon cap falls back to the model; a corrupted
  opponent pin is rejected. Repeat/cap checks are additional to the 1,328
  continuations in the 24-fixture count.

Artifact pins include the focal model, opponent ensemble, execution settings and
runtime. The new loader checks every member and module; the research arena applies
the actual returned legal move. Existing population descriptors remain supported.
**1,487 of 1,488** study-source files are unchanged in the new standalone package;
the public arena bridge receives its previously verified public-move interface,
with new policy/transport files added. The original study source itself is untouched.

Eight two-player engineering games (all seats and all four rules, economic
opponents) are now running through that artifact. Original **PID 8564**, guard
`ai/runs/opponent-auction-engineering-games-v1-launch.json`, outputs
`ai/runs/opponent-auction-engineering-games-v1`, log with the same base name plus
`.log`. Preserve the original process and inspect it on observation timeout;
do not launch a replacement. These games are pending verification and their
outcomes are not strength evidence.

Evidence: `strong/opponent-auction-runtime-preflight-v1.json`; private HF revision
**0f655c2563bec8d489db7dac10d65879897684c9**, archive SHA256
**47976cecd0dd9fe2983e127ea224b76d24111cd17789cd1b8c6611ed6bd42153**,
**1,574 files**, downloaded and hash-verified. Runtime manifest SHA256
**dfc07dd4ec2f15266863394bc1a12fd4eb8882db02e27b360faf9357f300069a**;
prototype policy SHA256
**a76aa90ec10e5e62b45036b6e3b3f2e9f4aa24b93cba6762f147ad34421d878d**.
Original preflight session **71567** and archive **69890** completed normally.
No additional HF jobs, gradients, strength selection, production changes or
reserved final seeds. Complete the full fidelity comparison before freezing the
playing recipe and running fresh strength games. The exact final adapter and
actual whole-policy 8840U benchmark remain outstanding.


## 25 October, 09:26 UTC: original standalone prototype games verified

The **eight original standalone prototype games** completed and were independently
audited: **1,411 public decisions**, **269 auction searches**, **22,048 continuations**,
**29 search overrides**, zero game/rollout caps. The continuation receipts include
2,096,329 focal neural decisions and 318,728 surrogate decisions. This covers one
two-player deal, all seats and four rule combinations, against economic opponents.
It is engineering evidence, not a strength estimate or a selected playing recipe.

The audit recomputes terminal tie credits, every saved model/alternative pair and
the exact population-consensus override rule. Every standalone response matches
its saved decision and the independent arena's legal menu, request/revision and
player ordering. Hidden deck/RNG and submitted sealed bids are absent from public
requests. All **1,494** frozen runtime files retain their hashes. Whole-game direct
policy parity is not claimed; the earlier separate fixture parity remains intact.
These local timings are not an AMD 8840U benchmark.

- Descriptor: `strong/opponent-auction-engineering-evidence-v1.json`.
- Verification: `ai/runs/opponent-auction-engineering-verification-v1.json`;
  collector `strong/collect-opponent-auction-engineering-v1.py`.
- Private HF **7efa9f9f43d3d4ac4497e855ac1fc157386cbdec**, archive SHA256
  **7b2d0de5845e0cf111f885f5f9ddedd6849eb9ebc6e9120b1e5714f352e12f0e**,
  **39 files**, downloaded/hash-verified. Raw full-game receipts, original guard,
  logs and audit code retained; the earlier runtime archive pins the package.
- Original PID **8564** completed and is absent. Verification session **9822** and
  archive **1898** completed successfully. Do not rerun this unchanged experiment.

The main-study owner **PID 3502343 / session 23779** remains live and all its pinned
code is unchanged. At **09:25:53 UTC**, it reports **319 submitted /
302 verified**, zero caps, no reported failures, stage `submitting`. It alone owns
submission/collection of the 480 roots. Preserve its original handles; no manual
parallel collection or restart on a polling timeout. Checkpoint:
`ai/runs/opponent-auction-engineering-completion-checkpoint-v1.json`.

The final integration review confirms a remaining requirement: the old launcher
and verifier bind legacy search settings and cannot qualify this new public
backend, opponent ensemble and override rule. A separate exact-policy adapter
must bind the full artifact identity and settings to every game/CPU receipt while
preserving all thresholds and paired deals in the unchanged final protocol. The
current development arena deliberately rejects reserved seeds; do not weaken that
boundary or translate the new policy into old `search_scope` fields.

**Next:** complete/archive the entire original fidelity study before choosing a
recipe; then freeze the auction policy, run fresh full-game confirmation across
2–6 players/all rules, complete exact-policy final integration and benchmark the
complete policy on the actual 8840U. No new HF jobs, gradients, strength games,
production changes, selected candidate or reserved final seeds in this collection.
Both the previous and current goal turns made concrete progress. There is no
established general plateau; unchanged rejected building/resource search remains
unjustified.


## 25 October, 09:41 UTC: exact-policy final-game audit verified

The read-only final-game audit now binds every response to the **complete public
policy identity**, including opponent ensemble, population modes and override
margin. It checks raw legal moves, request/revision/player identity, hidden-state
exclusions, terminal tie credits, continuation receipts and counters. It enumerates
the unchanged **320 shards / 20,160 games / 26 opponent-count groups** and retains
the original overall/rule confidence bounds and minimum rates. A strength pass
explicitly does **not** qualify a model without export, serving and package proof.

**13 synthetic contract tests passed**, including missing/duplicate shards,
changed settings/protocol, bad rule subsets concealed by good overall averages,
the 90% default-bot floor, absent search, private inputs and wrong legal moves.
The new checker also passed **88 existing engineering games / 11,618 public
decisions / 22,048 continuations / zero caps**. Every raw input hash matches the
two prior immutable archives. This reuses existing evidence and adds no games,
inference, training, jobs, final seeds, selected policy or strength estimate.

- Code: `strong/public_policy_final_audit_v1.py`; checker/archiver
  `strong/check-public-policy-final-audit-v1.py`.
- Descriptor: `strong/public-policy-final-audit-evidence-v1.json`; outputs
  `ai/runs/public-policy-final-audit-preflight-v1`.
- Private HF **0132792a782735f596a3c6c23db356f94d58125c**, archive SHA256
  **d7b0fdb607d52ea734348493fa3428be42c35481ebde75e9d4b702852070abaa**,
  **23 files**, downloaded/hash-verified. Raw receipts remain in the two pinned
  original archives; new code, audit outputs, source/input hashes and test log saved.
- Original tests **86371**, verification **1547**, archive **2133** completed.
  Do not rerun unchanged work. Final protocol and live study code are unchanged.

**Integration is not complete:** a selected-policy final launcher/source admission,
actual final-wrapper engineering execution, and binding complete-policy
export/8840U/package evidence are still needed. The opponent-backend receipt audit
currently admits eight worlds; a different selected budget requires corresponding
verified audit support, not forcing the policy to fit this engineering setting.
No final candidate is selected or qualified.

The original study owner **PID 3502343 / session 23779** is directly confirmed live.
At **09:40:58 UTC** it reports **360 submitted / 336 verified**, zero caps and
no failures, stage `submitting`. Preserve its handles and sole submission/collection
ownership. No partial-results interpretation or retrospective recipe selection.
Checkpoint: `ai/runs/public-policy-final-audit-completion-checkpoint-v1.json`.
Previous and current goal turns both made concrete progress. Next, complete and
archive the entire fidelity study, use those findings to freeze an auction recipe,
then run fresh full-game confirmation and the unchanged final strength gate with
the exact serving policy. No general strength plateau has been established.


## 25 October, 09:44 UTC: final-game audit ordering correction

The final-game audit now sorts by canonical episode before computing bootstrap
intervals. A regression test against the **archived first implementation** failed
when shard/receipt order changed; the corrected implementation passes with identical
results. This fixes collection-order sensitivity without changing the protocol,
thresholds, games, current prototype or live study. The first archive is retained;
use **v2 evidence** with the current audit code.

**14 contract tests passed.** The corrected audit again passed the immutable
**88 engineering games / 11,618 public decisions / 22,048 continuations**, zero
caps, with every input hash matching the original archives. This is verification
of evaluation infrastructure, not additional strength evidence. No new games,
model inference, training, HF jobs, candidate selection or final seeds.

- Current descriptor: `strong/public-policy-final-audit-evidence-v2.json`;
  outputs `ai/runs/public-policy-final-audit-preflight-v2`.
- Private HF **4b294a863f6189c78b8e33ebe49f80935658d1fa**, archive SHA256
  **38d48d421c306cb7d40876ed29bb88c77bed586721a8968cf83045356b75d903**, **25 files**, downloaded/hash-verified.
- Original v2 tests **70723**, archived-code regression check **19029**,
  verification **21208** and archive **47701** completed. First-run originals
  and archive remain preserved. Do not rerun unchanged work.
- The read-only audit preserves **320 shards / 20,160 games / 26 groups**.
  Final execution admission/wrapper and complete-policy export/8840U/package
  evidence binding remain incomplete; eight-world opponent receipt auditing
  is an engineering capability, not a forced recipe choice.

The original full-study coordinator **PID 3502343 / session 23779** is directly
confirmed live, pinned code unchanged. Its **09:42:50 UTC** snapshot is
**370 submitted / 336 verified**, zero caps and no reported failures;
stage `waiting_for_original_jobs`. It remains the only submission/collection owner.
Checkpoint `ai/runs/public-policy-final-audit-completion-checkpoint-v2.json`.
Previous and current goal turns both made concrete progress. Complete/archive the
whole fidelity study before choosing the auction recipe, then fresh full-game
confirmation and exact-policy final/target validation. No qualified candidate or
general plateau established.
