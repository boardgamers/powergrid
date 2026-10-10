# Power Grid AI — active continuation, 10 October 2026

**No candidate has passed the full strength gate. Nothing is deployed. Reserved
final-test seeds remain unused.** The separate UI redesign was reverted.

Use `/home/eliheros/Documents/Codex/2026-09-26/je-x20-2/work/powergrid-ai`, branch
`ai/germany-baseline`. No UI work or publication is part of this AI continuation.

## Latest: all phase comparisons and guided four-player games verified

The previous goal turn was **progress** (128 verified two-player phase games).
This turn is **progress**: 576 additional phase games and 384 four-player guided
games independently verified, 960 new complete games total. All game/search caps
are zero. No new gradients, final seeds, candidate selection or deployment.

**The entire 704-game phase ablation is complete**, all six HF jobs COMPLETED.
`strong/phase-search-ablation-results-v1.json` has `all_cases_verified: true`.
The same raw/all-search baselines, public-search settings and reused development
deals are retained. Results below are win shares; 2p/search and3p/search each
have eight independent deals,3p/A260 has16:

| Case | Raw | Auction only | Building only | Both |
| --- | ---: | ---: | ---: | ---: |
| search_geo2p | 50.0000% | 68.7500% | 51.5625% | 65.6250% |
| search_geo3p | 20.8333% | 43.7500% | 38.5417% | 41.6667% |
| A2603p | 36.1979% | 41.1458% | 41.6667% | 49.4792% |

At3p/search, auction-only gains22.9167 points over raw, paired95% interval
[9.3750,36.4583]; building-only gains17.7083 points [6.25,30.2083]. Their
difference is uncertain: auction-minus-building5.2083 points [-11.4583,23.9583].
The four-arm interaction is -19.7917 points [-38.5417,-1.0417], meaning the two
gains are not additive on this scale; it does **not** prove either phase should
be disabled, since their direct comparisons against both include zero.
Auction-only rule shares37.5/37.5/37.5/62.5%; building-only45.8333/37.5/45.8333/25%.
Order is original/open,original/sealed,Recharged/open,Recharged/sealed.

At3p/A260, neither single-phase overall gain over raw is clear:
auction+4.9479 points [-3.3854,13.8021], building+5.4688 [-1.8229,12.2396].
Combined search has the higher point estimate. In original/sealed, combined
search improves on auction-only here: auction-only29.1667% versus combined47.9167%,
paired difference -18.75 points [-33.3333,-4.1667]. Building-only is68.75% on
Recharged/open versus52.0833% combined, but that difference remains uncertain
[−6.25,+37.5] points. Auction-only rule shares31.25/29.1667/52.0833/52.0833%;
building-only25/33.3333/68.75/39.5833%. All intervals are exploratory marginal
deal-bootstrap intervals, not multiplicity-adjusted or qualification evidence.

Final phase raw pins: building search_geo3p andA2603p at
`ea8d2d7df93fd510964035bb7ed6ea7d043a48f9`; auction search_geo3p at
`1b23f136b7e6a79fbf44267550fa08fc8c800107`; auctionA2603p at
`7599d61619387936824757d057d0b86609df05c0`. Two-player pins are preserved below.
Immutable complete evidence: model repo revision
`9ab4a39b49ac9ece8a3f26f9624fc1e2a68fc633`, prefix
`runs/phase-search-ablation-completed-evidence-v1`, pin
`strong/phase-search-ablation-completed-evidence-v1.json`. All six local verified
directories already exist; do not recollect or relaunch them.

**Guided4p also complete**,128 games/model, all three jobs COMPLETED; raw revision
`1b23f136b7e6a79fbf44267550fa08fc8c800107` for parent,10101 and10102.
Parent/10101/10102 search shares34.375/34.375/35.1563%, versus raw22.6563/24.2188/24.2188%.
The10102 paired gain is10.9375 points [-1.5625,19.5313]; its aggregate search
interval[27.3438,42.1875]% exceeds25% chance but rule cells remain weak.
Its four rule shares37.5/21.875/46.875/34.375%; original/sealed is below chance
in point estimate, with interval[12.5,31.25]%. Search-minus-raw in that cell
is−3.125 points [−21.875,18.75]. These eight deals do not qualify the agent.
10102 minus parent is only0.78125 points [0,2.34375].

`strong/multiplayer-search-transfer-results-v1.json` now verifies players[3,4],
672 guided games plus672 paired raw baselines, `all_counts_verified: false`.
Immutable4p evidence: revision `0f93f5edd7e30f19f32e70aa6f6e8ee9f8ebae42`, prefix
`runs/multiplayer-search-transfer-4p-evidence-v1`, pin
`strong/multiplayer-search-transfer-4p-evidence-v1.json`. The six full5–6p jobs
remain on their original live handles in the status file. Do not duplicate them.

**Next training direction:** the phase evidence does not support universally
replacing only auctions or only building. Retain both phase contexts and all
rule/count strata in fresh teacher data. Earlier global distillation regressed
and the continuation audit found policy-dependent rankings; do not convert
noisy search winners directly into hard labels. The next concrete preparation
is fresh public strategic-root collection (disjoint from these evaluations),
followed by paired continuation targets that preserve uncertainty and a small
frozen-parent correction experiment on HF Jobs. Record fresh full-game
development comparisons before accepting it. Complete the six live5–6p guided
reports alongside this work, keeping original/sealed weaknesses visible.
No final candidate is chosen; all reserved seeds and the full gate are unchanged.

## Earlier: two-player phase comparison verified; larger comparisons running

The previous goal turn was **progress and a verified wait**: preserved verified
probes and the production-engine audit, and checked all live jobs. This turn is
**progress**: independently collected 128 complete two-player phase games,
compared all four arms, and saved the raw and derived evidence. The UI revert
remains finished. Four phase jobs and nine guided 4–6p jobs are still running
at the status-file timestamps. Do not restart them.

**First phase result: auction search supplies the clearer two-player gain.**
These are the same eight development deals against the unchanged search_geo
reference, all seats and four rule combinations, 64 games per arm:

| Search phases | Win share | Paired gain over raw (95% deal interval) |
| --- | ---: | ---: |
| none (raw policy) | 50.0000% | — |
| auction only | 68.7500% | +18.7500 points [4.6875,31.2500] |
| building only | 51.5625% | +1.5625 points [-10.9375,12.5000] |
| both (previously verified) | 65.6250% | +15.6250 points |

Auction-only minus building-only is +17.1875 points [7.8125,26.5625].
Auction-only minus both is only +3.1250 points [-9.3750,15.6250], so this does
not establish that disabling building search improves the complete agent.
Auction-only rule shares: original/open81.25%, original/sealed75%,
Recharged/open50%, Recharged/sealed68.75%. Recharged/open is **12.5 points
below raw**, interval [-37.5,12.5]. Its original/sealed gain is25 points
[6.25,43.75]. Keep every rule result; no universal auction-label claim.

Both new arms passed exact source/model, all game rows, phase-routing and
zero-cap checks. Full raw revision `53a7b0802c5f7b680631f0c8724253c5a73e96bf`;
local directories `ai/runs/phase-search-ablation-verified-v1/{auction,building}-search_geo-2p`.
Immutable evidence revision `62f80c93e1bfea96c5defa07eb7c15fe18a35cfc`, prefix
`runs/phase-search-ablation-2p-evidence-v1`; pin
`strong/phase-search-ablation-2p-evidence-v1.json`. The results file
`strong/phase-search-ablation-results-v1.json` is explicitly partial:
128 new games, `all_cases_verified: false`. Do not recollect completed directories.

The local comparison now reports four-arm contrasts, keeping shared deals
together across all arms: auction with/without building, building with/without
auction, and the joint interaction. Overall interaction is -4.6875 points
[-23.4375,14.0625], inconclusive. This exploratory extension was added before
reading the full phase outputs; it changes no frozen jobs or game seeds.
Nine phase tests passed, including exact shared-arm covariance cancellation,
cluster uncertainty, tie credits and rejection of incomplete/mismatched data.
The four marginal effects also reproduce the separately collected pairwise
estimates and intervals exactly on these real results. This analysis does not
validate teacher targets or qualify the policy.

**All nine phase probes passed:** 96 complete games, 780,000 learner rollouts
and 405,328 opponent rollouts, no truncations. Search routing was checked for
each phase and game. The 32 all-search control games exactly reproduce the
previous game rows, including terminal money, not only winner credits.
`test_phase_search_collect.py` passes three tests against real probe artifacts,
including rejection of altered routing, model, seed, horizon and replay data.
Probe win rates are not strength evidence.

Immutable probe evidence: model repo `coyotte508/powergrid-ai-germany-v1`,
revision `c0ab287bff19e1f2d807e9163fc70716c814498e`, prefix
`runs/phase-search-ablation-probes-evidence-v1`.
Pins and summary: `strong/phase-search-ablation-probes-evidence-v1.json` and
`strong/phase-search-ablation-probes-results-v1.json`. Includes all collected
artifacts, replay controls, six runtime admissions and exact launch guards.

**All six full phase jobs were dispatched**, 704 games on existing development
deals. The two search_geo2p jobs are now complete; the four 3p jobs are running:

| Search arm | Case | HF job |
| --- | --- | --- |
| auction | search_geo 2p | `6aca6df4fee2c9007018a388` |
| auction | search_geo 3p | `6aca6df7fee2c9007018a38c` |
| auction | A260 3p | `6aca6dfafee2c9007018a393` |
| building | search_geo 2p | `6aca6dfd095c578089314950` |
| building | search_geo 3p | `6aca6e00095c578089314955` |
| building | A260 3p | `6aca6e04fee2c9007018a399` |

Every job passed matching control parity and same-arm/case runtime admission;
all use CPU-performance with a four-hour timeout. Collect complete artifacts
at immutable revisions with `manage-phase-search-ablation.py collect ARM CASE REV`
(without `--smoke`). Compare only cases whose two full arms are both verified.
The existing nine full guided 4–6p jobs also remain RUNNING. Their exact handles
are in `strong/multiplayer-search-transfer-status-v1.json`; 3p is already verified.
No new gradient job has been launched while these comparisons are pending.

**Production-engine compatibility passed within its tested scope.** An isolated
compile of release commit `aac09f231d4b024a7ea1c7e24cad0223a8c4a7ea`
(engine 2.0.14) was compared with the frozen research engine (2.0.10):
2,553 legal menus, 5,106 feature checks, 2,553 default-bot one-step transitions,
and 80 complete Germany games / 41,026 transitions across 2–6p and all four
rule combinations. No differences in the compared state or terminal outcomes.
Games use alternating heuristic/economic actors; this is not learned-policy
strength evidence. Explicit exclusions: new powering-choice snapshots, pending
announcement queues and Step 2/3 announcement log text.

Immutable compatibility evidence: model repo revision
`107ac032692cd7effd529bd03f7e6dc319602c55`, prefix
`runs/production-engine-compatibility-evidence-v1`, pin
`strong/production-engine-compatibility-v1.json`. Contains the checker, full
result, production source archive, all 40 compiled engine files, provenance,
research-source byte check and build environment. Dependency entry-file hashes
match; this does not claim a complete dependency-tree comparison. Pending
choice revisions, platform scheduling/transport and other maps were not tested.
No production source or frozen evaluation runtime was changed. Any eventual
qualified serving package still needs its exact engine/configuration checked.

**Next:** collect the remaining four 3p phase reports and nine guided 4–6p
reports from their saved live handles; report paired differences and every rule
cell; then choose a targeted teacher/student intervention. The two-player result
prioritizes auction investigation but does not settle Recharged/open or3p. Do not
spend reserved final seeds or infer phase benefit from runtime probes. No model
has qualified, and the value head remains uncalibrated for player-score analysis.

## Earlier: all raw counts verified; phase diagnosis probes dispatched

The previous goal turn was **progress** (verified three-player search gains and
the real final-harness smoke). This turn is **progress**: the entire 13,440-game
raw opponent suite is independently verified, the three full six-player guided
jobs are dispatched, and a frozen auction/building phase ablation has nine HF
probes in flight. No new gradients, candidate selection, reserved seeds or
production deployment. UI remains at the previously reverted version.

**All raw-policy 2–6p comparisons are complete**, 15 jobs and 13,440 games.
`strong/discard-opponents-results-v1.json` now has `all_shards_verified: true`.
Every raw game and search rollout passed the prescribed completion checks.
New six-player raw artifacts are pinned at
`b0444707a202113269df5c2a9a332d86be587c76`; local verified directories:
`ai/runs/discard-opponents-verified-v1/{parent,10101,10102}-6p`.
Immutable complete evidence: `3faadbc32dfdb6e1c1490f9ea6ade911bb68d9c4`,
`runs/discard-opponents-completed-evidence-v1`, pin
`strong/discard-opponents-completed-evidence-v1.json`. Earlier partial snapshots
are preserved historical evidence, superseded by this full comparison.

| 6p opponent | Parent | 10101 | 10102 |
| --- | ---: | ---: | ---: |
| legacy | 94.0104% | 94.0104% | 94.2708% |
| heuristic | 99.2188% | 99.2188% | 99.2188% |
| rush | 75.1302% | 75.3906% | 75.3906% |
| search_geo | 38.5417% | 38.0208% | 38.5417% |

Search has 192 games/model but only eight independent deals. Parent/10102
interval is [31.25,46.3672]%; their credits are identical. The10101 point
regression is 0.5208 percentage points. Parent/10102 rule shares are
50/18.75/58.3333/27.0833% for original/open, original/sealed,
Recharged/open, Recharged/sealed. Both sealed intervals include 1/6 chance:
[8.3333,29.1667]% and [14.5833,41.6667]%. The favorable aggregate is not a
qualification result. The earlier weak 3–4p and 5p sealed findings remain.

**All 12 full 3–6p search jobs are dispatched**, 1,728 new guided games planned.
Three 3p jobs/288 games are already independently verified; the other nine
4–6p jobs are live or scheduling in the saved status file. Newly launched 6p:
parent `6aca6ba9fee2c9007018a204`,10101 `6aca6babfee2c9007018a206`,
10102 `6aca6bad095c5780893147f0`, 192 games each, CPU-performance10h.
Their admission reverified the matching complete raw baseline and the measured
6p runtime probe. No duplicated or restarted jobs.

**New phase ablation is frozen**, using10102 and the exact same search settings,
models, opponents and existing development deals. It compares auction-only and
building-only search against the already pinned raw and all-search controls:
search_geo2p (64 games/arm),search_geo3p (96),A2603p (192),704 new full games.
This diagnoses phase contributions before choosing new teacher training; it
cannot qualify a model. Report all rule cells and regressions, not just winners.

Source `strong-source-phase-search-ablation-20261010-v1.tgz`, dataset revision
`a597aed2089a746b2884083b6fea3ab4e9d774af`, SHA256
`564543f80271af6bd26fc364e23e3fd107b7598742813119db7cd99fd71e607c`.
Protocol SHA256 `facc2c51a8ef7af5e61283764dcb117cb7531e516bbf67a4d2d8b60436884c32`.
All 1,378 base runtime files are byte-identical. Five added files attach a public
phase tag, filter only learner search requests, count routing per game, and
validate it. Local frozen-package checks cover 5,533 encodings on all2,553
fixtures with unchanged features/legal moves/game state, plus routing checks
preserving opponent and excluded-phase choices. Those are engineering checks;
complete-game replay parity still requires the HF controls.

Nine 4h HF probes, 96 games total, are dispatched:

| Arm | search_geo2p | search_geo3p | A2603p |
| --- | --- | --- | --- |
| all control | `6aca6b8cfee2c9007018a1df` | `6aca6b8e095c5780893147d6` | `6aca6b90fee2c9007018a1e1` |
| auction | `6aca6b92fee2c9007018a1e3` | `6aca6b93095c5780893147d9` | `6aca6b95095c5780893147dd` |
| building | `6aca6b97fee2c9007018a1e5` | `6aca6b99095c5780893147df` | `6aca6b9a095c5780893147e4` |

All-control probes replay one existing deal/case and must match every original
game row exactly (apart from new routing counters). Phase probes use separate
fresh runtime seeds. Do not use probe win rates as strength evidence. Full
phase jobs have NOT launched yet. Independent collection and same-case control
parity plus same-arm runtime admission are mandatory before full launch.
Full admission uses120s+2×probe duration×deals,25% timeout headroom,max12h.
If above the limit, split the work without weakening horizons.

Manager: `ai/.venv/bin/python ai/strong/manage-phase-search-ablation.py`:
`collect ARM CASE REV --smoke`, `profile ARM CASE`, then `launch ARM CASE`
when admitted. ARM is `all` (controls only), `auction` or `building`; CASE is
`search_geo-2p`, `search_geo-3p` or `a260-3p`. Full collection omits `--smoke`.
`compare --cases ...` requires both phase arms for every requested case and
explicitly marks incomplete case subsets. Launch guards are exclusive under
`ai/runs/phase-search-ablation-launches-v1`. Preserve them on observation errors.
Launch/preflight evidence pin: `strong/phase-search-ablation-launch-evidence-v1.json`.

**Next:** collect finished phase probes and full4–6p guided arenas from their
exact handles, verify outputs, admit full phase comparisons as justified, and
use complete paired/rule evidence to choose the next teacher/student change.
Current policy values remain uncalibrated for live player-score analysis.
The original final strength gate and reserved prefix are unchanged and unused.

## Earlier: complete three-player search comparison verified

All three full3p jobs have now **COMPLETED**,288 new complete games with288
paired raw baselines,zero game/search truncations. `strong/multiplayer-search-transfer-results-v1.json`
is explicitly partial (`verified_players: [3]`, `all_counts_verified: false`).
Parent and10101 raw outputs are pinned at
`2fdd41a0a1b646fcb2da7f77a563771ce32b4a59`;10102 at
`363e2b5aab88c0be17ee2ab36c0a61421d419fb8`. Local artifacts:
`ai/runs/multiplayer-search-transfer-verified-v1/{key}-3p`.

Parent raw16.67% → search40.625%,paired gain23.9583 points,
whole-deal95% interval[16.6667,31.25]. Both corrections raw20.8333% →
search41.6667%,gain20.8333 points,interval[15.625,26.0417]. Corrected
search interval[34.375,48.9583]% is just above1/3 overall, but all four
rule-cell intervals include chance. Corrected original/open45.8333%,
original/sealed45.8333%,Recharged/open33.3333%,Recharged/sealed41.6667%.
These are only8 independent deals; passing the40% aggregate point floor
is not qualification. Recharged/open remains a priority diagnostic gap.
Both correction seeds again have identical credits,not necessarily trajectories.

Immutable3p paired evidence: `be8688136e9bfd5744f1751808aa33c884d36aef`, prefix
`runs/multiplayer-search-transfer-3p-evidence-v1`, pin
`strong/multiplayer-search-transfer-3p-evidence-v1.json`. Do not recollect
these exclusive directories or relaunch these jobs. Six full4–5p guided jobs
remain live; the three6p raw jobs remain live. After collecting raw6p,
launch its three already-admitted guided jobs. Compare further counts only
when all three models/count are independently verified. The final-harness
real8-game development smoke is also verified,as detailed below.

## Earlier this turn: raw 2–5p verified; all search probes passed; full 3–5p launched

The preceding AI goal turn was **progress** (verified the first search-transfer
suite and launched multiplayer probes). This continuation is **progress**:
verified 9,408 raw-policy opponent games, all four 3–6p probes, and dispatched
nine full search comparisons. Final-evaluation compatibility and evidence checks
were repaired and tested, without playing any reserved games. No new gradients,
selection, promotion or deployment. The intervening UI revert remains complete.

**Raw-policy 5p results are complete**, 1,120 games per model (3,360 new games).
Parent raw artifact revision: `8372a23b6fa130a6549cd0783e1116ce293af4c0`.
Both correction artifacts: `bbaca62cad80b0a3a01f715f2e3cc01f8cf42898`.
Local verified directories: `ai/runs/discard-opponents-verified-v1/{key}-5p`.
All 2–5p results are in `strong/discard-opponents-results-v1.json`, with zero
actual-game/search truncations and `all_shards_verified: false` (6p pending).

| 5p opponent | Parent | 10101 | 10102 |
| --- | ---: | ---: | ---: |
| legacy | 92.8125% | 91.5625% | 92.1875% |
| heuristic | 97.8125% | 97.8125% | 97.8125% |
| rush | 75.625% | 75.625% | 75.625% |
| search_geo | 35% | 33.75% | 33.75% |

The 160 search games/model represent only eight independent deals. Corrected
aggregate interval [28.75,38.75]%; parent [31.25,38.75]%. The correction is
-1.25 points versus parent, paired interval [-3.125,0]. Corrected rule shares
(original/open, original/sealed, Recharged/open, Recharged/sealed):
45/15/52.5/22.5%. Original/sealed interval [7.5,20]% fails to establish advantage
over 20% chance; Recharged/sealed [10,35]% also does not establish it. Thus the
aggregate passing the 28% point floor is insufficient. Preserve the sealed
weakness and correction regression when choosing a candidate.
Immutable complete 2–5p evidence: `01e02f69e85a21cf20967b373fb1fe3acf477a96`,
`runs/discard-opponents-2p5p-completed-evidence-v1`. Pin:
`strong/discard-opponents-2p5p-evidence-v1.json`.

**All 3–6p search runtime probes are independently verified:** 72 complete games,
1,993,808 search rollouts, zero truncations. Probes are execution evidence only.
Profiles `strong/multiplayer-search-transfer-{3,4,5,6}p-runtime-v1.json` admit
4/5/7/10h jobs respectively, retaining the prescribed conservative margins.
Probe revisions: 3p `8372a23b6fa130a6549cd0783e1116ce293af4c0`,
4p `bbaca62cad80b0a3a01f715f2e3cc01f8cf42898`,
5p `739545765dae4b33853c3156f6237d6014e79059`,
6p `e4e5ccc4b649fd1df18dd6394d4aae3613a6aa9f`.
Evidence: `b546cd8337c0e659e0ca9fceda5da5f020269c6b`, prefix
`runs/multiplayer-search-transfer-runtime-evidence-v1`.

**Nine full search jobs are dispatched, 1,152 new paired games**:

| Count / games per model | Parent | 10101 | 10102 |
| --- | --- | --- | --- |
| 3p / 96 | `6aca6497fee2c90070189d0d` | `6aca649a095c5780893143dc` | `6aca649b095c5780893143de` |
| 4p / 128 | `6aca65b1095c57808931448b` | `6aca65b2fee2c90070189dea` | `6aca65b5095c57808931448d` |
| 5p / 160 | `6aca67e4095c57808931461f` | `6aca67e6095c578089314626` | `6aca67e8095c578089314628` |

All nine were RUNNING at the saved status check. Three full 6p jobs (576 games)
remain to launch: runtime is admitted, but their pinned raw-policy baselines
must finish and be independently collected first. Those existing raw6p handles
are parent `6aca55e9095c578089313ace`, 10101 `6aca55edfee2c900701891ef`,
10102 `6aca55ef095c578089313adb`, all confirmed RUNNING. Do not duplicate them.
Use status files and exclusive launch guards; do not relaunch on a log timeout.

**Final harness repaired, not qualification:** the launcher now accepts the
current4.2 models, requires frozen runtime/model hashes, preserves individual
submission intents, and locks concurrent ledger access. The arena wrapper
records actual source/model/runner identities. Verification rejects wrong exact
deals/episode pairings, wrong runtime or truncated searches. New
`merge-arena-reports.py` verifies disjoint contiguous shards and recomputes
statistics from raw games; it never averages confidence intervals/percentiles.
Nine isolated contract tests pass, using mock submissions and temporary metadata
around existing development rows. They do not execute final games or qualify a
model. Frozen source `strong/final-runtime-source-v1.json`:
`9e0f1e957512c8dfa9bdb5edd7caf1671c197de4`, archive
`strong-source-final-runtime-20261010-v1.tgz`, SHA256
`07c635937b08a6e37adfed6c94f6f4cc63a24e8e0572da78a1717b743b873571`.
Only the arena provenance wrapper changed;1,377 other files are unchanged.
A real8-game HF development smoke is **COMPLETED and independently verified**:
`6aca67f3fee2c90070189ff5`,
seed `final-runtime-smoke-development-v1-2p`. Record:
`strong/final-runtime-smoke-v1.json`. Raw revision:
`faf5b78910806a199599f42094a7aad902015e7e`. All8 games completed,
108,096 learner rollouts across445 decisions,0truncations,248.829s evaluation.
Source/model/runner hashes, all paired rules/seats and the strict shard merger
passed independent collection. Immutable evidence: `2fdd41a0a1b646fcb2da7f77a563771ce32b4a59`,
`runs/final-runtime-smoke-evidence-v1`. Local:
`ai/runs/final-runtime-smoke-verified-v1`. Do not rerun its exclusive collector.
This smoke measures plumbing only; its seed is not reserved. Source package is
already built/uploaded: do not rerun the exclusive builder.

**Next:** collect the exact live jobs on completion. Independently verify raw6p,
then launch its three already specified guided matchups with the existing
manager. Collect full search3–5p results and compare by count/rule against their
pinned raw baselines. Keep regressions visible; don’t select on aggregate wins.
The real harness smoke is verified and preserved; keep the reserved final prefix
unused until a complete candidate is justified. Future
phase ablations/teacher training should follow these results. The nine full
search jobs are work in flight, not qualified results.

## Earlier: search improves A260 results; 3–6p search probes launched

The preceding goal turn was **progress**: verified raw 2–4p, all two-player
search comparisons, and the actual 8840U benchmark. This turn is **progress**:
independently verified all three A260 arms, completed the 1,152-game search
comparison, analyzed paired terminal outcomes, and froze/launched the broader
3–6p search probes. No new gradients, final seeds, promotion or deployment.

**The entire first search-transfer experiment is now verified:** 1,152 guided
games paired with 1,152 pinned raw-policy baselines; all nine jobs COMPLETED,
zero actual-game or search truncations. Do not relaunch any of them.
`strong/search-transfer-results-v1.json` now has `all_cases_verified: true`.

| Case | Parent raw → search | 10101 raw → search | 10102 raw → search |
| --- | ---: | ---: | ---: |
| heuristic 2p | 63.28 → 89.06% | 71.09 → 92.97% | 71.09 → 92.97% |
| search_geo 2p | 23.44 → 62.50% | 50.00 → 65.63% | 50.00 → 65.63% |
| A260 3p | 37.24 → 48.44% | 36.20 → 49.48% | 36.20 → 49.48% |

All three new A260 collections are pinned at raw revision
`5f229b534da876c6455740631c2012e3152138b5`, local directories
`ai/runs/search-transfer-verified-v1/{parent,10101,10102}-a260-3p`.
Each is 192 games, 16 independent deals, all seats/four rules. The corrected
models' paired search gain is +13.28125 points, whole-deal 95% interval
[+4.1667,+22.4023]. Guided win-share interval [40.625,59.375]%; the parent
improves by +11.1979 points, interval [+2.6042,+20.3125]. These are exploratory
development comparisons on intentionally reused deals, not final qualification.

Corrected A260 rule-cell shares (original/open, original/sealed,
Recharged/open, Recharged/sealed): 39.5833/47.9167/52.0833/58.3333%.
Original/open interval [25,56.25]% includes chance. Recharged/open loses
4.1667 points versus raw, paired interval [-20.8333,+12.5]; keep that regression
visible. The two sealed cells gain 19.7917 and 29.1667 points with positive
paired intervals. Corrected-vs-parent guided aggregate gain is only1.0417
points, interval [-1.0417,+3.125]. Both training seeds still produce identical
win credits in this first transfer experiment, not necessarily identical states.

Full immutable evidence: `5d574befee21c335b49b2ffe53d6d89002b83152`, prefix
`runs/search-transfer-completed-evidence-v1` in
`coyotte508/powergrid-ai-germany-v1`. Pin file:
`strong/search-transfer-evidence-v1.json`. Earlier partial snapshots remain valid
historical evidence, superseded by this complete comparison.

**Paired terminal diagnostics are saved**, reproducibly generated by
`strong/analyze-search-transfer-outcomes.py` in
`strong/search-transfer-terminal-analysis-v1.json`, including every rule cell.
For corrected 2p versus search, 21 losses turn into wins while 11 wins turn into
losses. Remaining losses: 16/22 have fewer cities than the winner powers, 4/22
lack nominal capacity, and4 lose a powered-city tie on cash. For corrected 3p
versus A260, 51 losses turn into sole wins,26 sole wins become losses, and one
shared win becomes a sole win. Among97 remaining losses,88 have fewer cities
than the winner powers and41 have insufficient nominal capacity. Categories
overlap, the loss cohort changes, and unused nominal potential may mean fuel
shortage. These observations suggest building/auction phase ablations may be
useful; they do not prove causal move errors or justify hard labels by themselves.

**The broader 3–6p search experiment is frozen and its four probes are live.**
All three existing models will face unchanged search_geo with public search48,
geographic/model proposals and unchanged horizons. Eight development deals per
count, all seats and four rules: 1,728 new full games planned. Two-player games
and A260 are not duplicated. Raw-policy baselines remain the already frozen
`discard-opponents` jobs. Corresponding verified raw baseline plus same-count
verified runtime probe are required before each full launch. Raw 3p/4p baselines
are ready; the six raw5–6p jobs remain RUNNING at the saved status timestamp.

The new frozen wrapper verified672 existing raw games and rejected48 altered
contracts. All1,376 files of the preceding source archive are byte-identical;
only the new wrapper and protocol are added. Archive
`strong-source-multiplayer-search-transfer-20261010-v1.tgz`, dataset revision
`a96a04f0914a34f4a86bcac0948db0e4777fa83d`, SHA256
`98fd31d794e96f0e4598db484cb074e899fe3af465b4c911d7c2abea6f15bbe2`.
Protocol SHA256
`9f6606955ac2aa3ebd46168bce0d983cd4aaed5b9d1d4feda21890d07fff5dda`.
This package does not change the old completed/running experiments.

| Runtime probe | HF job | Games |
| --- | --- | ---: |
| 10102 / 3p | `6aca61e3fee2c90070189b3e` | 12 |
| 10102 / 4p | `6aca61e5fee2c90070189b41` | 16 |
| 10102 / 5p | `6aca61e6fee2c90070189b44` | 20 |
| 10102 / 6p | `6aca61e8095c578089314282` | 24 |

All four probes are CPU-performance,4h, separate smoke deals, confirmed RUNNING.
The72 games are runtime/legal admission only; do not treat their win rates as
strength evidence. No full job for this extension has launched yet.
Guards: `ai/runs/multiplayer-search-transfer-launches-v1`.
Launch/preflight evidence: `2d214efc19e49d296145608a339f8aee75eeb0ed`, prefix
`runs/multiplayer-search-transfer-launch-evidence-v1`.

Use `ai/.venv/bin/python ai/strong/manage-multiplayer-search-transfer.py`:
`collect 10102 N IMMUTABLE_REV --smoke` verifies completed probes into
`ai/runs/multiplayer-search-transfer-smoke-verified-v1/Np`; `profile N` computes
admission from twice linear observed runtime plus120s and25% timeout headroom.
If admitted, `launch KEY N` also rechecks the full raw baseline and creates an
exclusive guard before calling HF. Above12h requires partitioning, not weaker
horizons. Full result collection: `collect KEY N IMMUTABLE_REV`; comparison:
`compare --players N ...` requires all three models at each requested count and
marks incomplete-count subsets explicitly. No restarts on observation timeouts.

**Next:** collect the four probes and remaining raw5–6p results as they finish;
launch each admitted full search matchup. This closes the currently untested
search-guided3–6p gap against the independent search reference. The first
experiment's improved A260 and2p results do not establish general strength.
Use the full pattern of wins/regressions to choose training or phase-ablation
work, then test an eventual frozen candidate on fresh held-out deals and the
unchanged final gate. The current 8840U benchmark remains valid for these model
and search settings; a later changed configuration needs its own verification.

## Earlier: raw 2–4p evaluated; search transfer running; actual-device probe verified

The preceding AI goal turn was **progress**: independently verified three-player
results, completed search-routing/package checks and all three HF runtime probes,
and launched all nine full search-transfer jobs. The intervening UI revert is
complete. This continuation is **progress**: independently verified all 6,048 raw 2–4p games,
576 new search-guided 2p games and 8,013 requests on the actual 8840U, confirmed
every live HF handle, and saved immutable raw evidence. No new
training gradients, final seeds, model promotion or deployment.

**All 2p, 3p and 4p independent-opponent results are verified**, 6,048 games total;
zero actual-game/search truncations. The remaining six 5–6p jobs were confirmed
RUNNING at the timestamp in `strong/discard-opponents-status-v1.json`.
Do not relaunch. All 15 full jobs were already dispatched (13,440 games).

| Opponent (3p) | Parent | Seed 10101 | Seed 10102 |
| --- | ---: | ---: | ---: |
| legacy | 91.15% | 92.71% | 92.71% |
| heuristic | 85.42% | 85.42% | 85.42% |
| rush | 57.81% | 60.68% | 60.68% |
| search_geo | 16.67% | 20.83% | 20.83% |

Against search_geo, corrections have whole-deal 95% interval [15.625,27.0833]%:
below 1/3 chance and the40% point floor. Only eight independent deals
(96 games/model), so this is exploratory development evidence. Paired gain is
+4.1667 points, interval [0,8.3333]. Both seeds have identical outcome credits
on 2p and3p; their trajectories are not identical. Corrections' 3p rule-cell
shares are20.8333/25/29.1667/8.3333% (original open/sealed, Recharged open/sealed).
The Recharged sealed weakness remains especially large. Raw3p revisions:
parent `84c1d964400507eb4796fc7f2584b87c5b173370`;
both seeds `96a899ef266439f72f50f2dbcfe8d5060985a543`.
Combined 2p–4p immutable evidence:
`3a61f660c843e93eec01ab147418a825d7b92cce`, prefix
`runs/discard-opponents-2p4p-completed-evidence-v1` in the model repo.

| Opponent (4p) | Parent | Seed 10101 | Seed 10102 |
| --- | ---: | ---: | ---: |
| legacy | 90.23% | 89.84% | 90.63% |
| heuristic | 92.19% | 92.58% | 92.58% |
| rush | 63.28% | 64.84% | 64.84% |
| search_geo | 22.66% | 24.22% | 24.22% |

Four-player search performance remains below the 32.5% point floor and the
25% chance point. Both confidence intervals include chance; the paired gain
is +1.5625 points, with seed10101 interval [-1.5625,+4.6875]. The training
seeds differ in some individual outcomes/rule cells despite the equal aggregate.
Raw4p revisions: parent `a531d4e90204005fa4e9555df599aaab8ecb933b`;
both corrections `a974ede722560313372a5b3a02329784cbf11d1f`.
All three four-player jobs are COMPLETED and independently verified, each
896 games including128 against search_geo. Do not repeat them.

**Search-transfer experiment now implemented, frozen and running.**
`strong/search-transfer-protocol-v1.json` fixes public search48, six proposal
candidates, geographic proposals plus the model proposal, all existing strategic
phases, with the learned discard/resource/powering actions retained outside
search. All three models remain separate. Cases:2p heuristic (16deals),2p
search_geo (8deals),3p A260 (16deals), all seats/four rules:1,152 new games paired
with1,152 verified existing raw-policy games. These development deals were
intentionally reused and the target cases selected after raw weaknesses appeared;
this does not replace an independent held-out strength test. The newly observed
3p search_geo deficit is not in this already-frozen transfer protocol.

Frozen source archive `strong-source-search-transfer-20261010-v1.tgz`, dataset
revision `1ef629c51282936c0bd2be9e7b584ce985e91d03`, SHA256
`e35e93d6d410ccb34bfb59a2840a7e4ed3b67e950a429968adcdf383ec53ef55`.
All1,372 base files unchanged; four overlays. A preflight missing-helper error
was fixed before upload/launch and preserved in the packaging-repair report.
Protocol SHA256
`5c0d303a3ea15c69c29c841f022a3c7a80379d97f1e14cf7901ce371df3b5d1c`.
5,106 actual bridge-routing checks over2,553 positions passed with stubbed
search/transitions; this is compatibility evidence only. All1,152 baseline
contracts pass. Collector negative checks reject wrong models, seeds, opponents,
search configurations, incomplete games and caps.

All three real HF search probes are COMPLETED and independently verified:
28 complete games,371,328 rollouts,zero game/search caps. Timings:
heuristic2p247.08s/8games; search_geo2p298.33s/8games;
A2603p369.53s/12games. Full jobs use CPU-performance:4h for2p,5h forA260,
admitted from twice the measured linear runtime plus120s and25% timeout headroom.
No game/search horizons were reduced. Search runtime/preflight/launch evidence:
`fc0b2db80dc0fb1ef758e259c2efbc33bfaa8ce3`, prefix
`runs/search-transfer-runtime-completed-evidence-v1`. Local verified probes:
`ai/runs/search-transfer-smoke-verified-v1/{heuristic-2p,search_geo-2p,a260-3p}`.

All nine full search jobs were launched once. Six are now COMPLETED and
independently verified (576 new games); all three A260 jobs were still RUNNING
at the saved status timestamp:

| Model | heuristic2p | search_geo2p | A2603p |
| --- | --- | --- | --- |
| parent | `6aca5acdfee2c90070189545` | `6aca5bb6fee2c900701896a1` | `6aca5bba095c578089313ec7` |
| 10101 | `6aca5acefee2c90070189548` | `6aca5bb8095c578089313ec3` | `6aca5bbbfee2c900701896a4` |
| 10102 | `6aca5acf095c578089313d8b` | `6aca5bb9095c578089313ec5` | `6aca5bbc095c578089313ecb` |

**First complete-game search-transfer results are verified.**
All three heuristic2p arms are complete (384 new games). Parent improves from
63.28125% raw to89.0625% search; each correction improves from71.09375% to
92.96875%. Corrections' paired search gain is +21.875 points, whole-deal95%
interval [+13.2617,+32.03125], on16 independent deals. Rule-cell shares for
both corrections:90.625/87.5/100/93.75% (original open/sealed, Recharged
open/sealed). The100% cell is only32 games, not a perfect-performance claim.

All three search_geo2p arms are also complete (192 new games): parent62.5%,
both corrected models65.625%, versus their raw23.4375% and50%. Each correction's
search-minus-raw gain is +15.625 points, paired interval [+1.5625,+31.25].
Their aggregate win-share interval is [54.6875,75]%, but all four rule-cell
intervals include50% (one at the boundary). Rule-cell shares are62.5/68.75/
62.5/68.75%. Eight development deals do not establish final qualification.
Both seeds have identical win credits on this two-player transfer subset; this
does not establish equal behavior or strength in other populations.

The added learned discard correction still helps when search is enabled:
versus parent+search, each correction gains3.90625 points against heuristic,
paired interval [+0.78125,+7.8125]; against search_geo the gain is3.125 points,
interval [0,+7.8125]. Retain the parent control and both seeds.
All576 independently collected guided games have zero game/search caps.
The combined comparison verifies both 2p cases, explicitly partial relative
to the three-case protocol because A260 remains running. Raw revision for the
first five arms: `0fa5c86d2550499c1ad2100b1b6d4ae6be7f1fc1`; sixth arm
10102/search_geo: `7512fc2d33fb1d7653be0e8a3717d9fe0e594a20`.
Durable complete 2p evidence: `ebf6cdce5d571f1067082985a819d053ea16d753`, prefix
`runs/search-transfer-2p-completed-evidence-v1`. The earlier five-arm snapshot
remains immutable at its earlier revision.

Collect completed results at immutable revisions:
`collect-search-transfer.py KEY CASE REV ai/runs/search-transfer-verified-v1/KEY-CASE`.
Compare all three models in each completed case with
`compare-search-transfer.py DIRECTORY OUTPUT [--cases CASE ...]`. It rechecks
raw contracts, caps, hashes and paired whole-deal/rule contrasts. A partial
case collection must not be called the full1,152-game result.

**8840U diagnostic completed and independently verified.**
Research directory `/home/coyotte508/powergrid-ai-search-transfer-probe-v1`
on `ssh minipc`; source/models use the immutable search-transfer pins.
All 8,013 requests are legal, model/schema/order match, 174 discard responses
are preserved under the search configuration, and all 43,200 rollouts finish
without truncation. Each model served all 2,553 saved public positions raw,
then 118 search-configured requests: one median-round root in each of the
60 player-count/rule/strategic-action strata, plus all 58 discard roots.

| Model | Raw median / p95 | Strategic search median / p95 | Search maximum |
| --- | ---: | ---: | ---: |
| parent | 2.54 / 5.03 ms | 1.083 / 2.027 s | 2.291 s |
| 10101 | 3.13 / 5.47 ms | 1.098 / 2.017 s | 2.321 s |
| 10102 | 3.09 / 5.40 ms | 1.113 / 2.064 s | 2.346 s |

Raw timings exclude each worker's cold first request. Search timings count the
60 actual search decisions/model, excluding the cheap discard passthroughs.
Fixed sequential diagnostics are not significance tests, worst-case guarantees,
or evidence of game strength. No training or production routing. Full per-request
responses, timings and immutable fixtures were independently rechecked by
`strong/collect-search-transfer-8840u.py`. Device report:
`strong/search-transfer-8840u-probe-v1.json`. Durable evidence revision
`3ffca6810bfddd1be50f1c2a7acf7b9416eac478`, prefix
`runs/search-transfer-8840u-completed-evidence-v1`. This establishes plausible
bot-job latency for the current configurations, not qualification of a model.

**Next:** collect the remaining raw5–6p/search cases, then extend guided
evaluation to3–6p against the independent search reference. Current search
transfer covers only2p and3p A260; it cannot establish4–6p strength. Use the
full-game search-versus-raw changes to select the next training recipe.
Search wins do not automatically supply reliable hard labels: earlier teacher
continuations were policy-dependent. The complete Germany2–6p strength gate,
reserved held-out tests and benchmark of the eventual exact qualified policy
remain required. Other maps and score calibration are not demonstrated.

## Earlier: learned discard gains transfer to independent 2p opponents

The preceding goal turn was **progress**: verified the runtime probe and launched
three complete 2p opponent evaluations. This turn is **progress**: all 1,344 games
are independently verified, with every raw artifact, model/source pin,
seat/rule/deal, outcome credit, search diagnostic and aggregate checked. The
combined collector has now run successfully on the complete 2p subset. Both
runtime probes are verified and all remaining full shards are launched. Zero
actual-game/search truncations. No final seeds or model promotion.

| Opponent (2p) | Parent | Seed 10101 | Seed 10102 |
| --- | ---: | ---: | ---: |
| legacy | 92.97% | 95.31% | 95.31% |
| heuristic | 63.28% | 71.09% | 71.09% |
| rush | 53.91% | 71.09% | 71.09% |
| search_geo | 23.44% | 50.00% | 50.00% |

Both training seeds have identical per-game win credits on this subset (not a
claim that trajectories or final states are identical). Against search_geo,
the paired gain is +26.5625 percentage points, whole-deal bootstrap 95% interval
[+15.625,+39.0625]. Candidate win-share interval is [37.5%,60.9375%]: this does
not establish an advantage over chance. Only eight independent search deals
(64 games/model). The other opponents have 16 deals each (128 games/model).
Heuristic gain +7.8125 points, interval [+3.90625,+12.5]; rush gain +17.1875,
[+10.9375,+23.4375]; legacy gain +2.34375, [0,+6.25]. All are marginal,
exploratory development intervals. Search and heuristic remain below their
55% and77.5% 2p point floors; the earlier A260 gap also remains.

Search_geo rule-cell win shares (original/open, original/sealed,
Recharged/open, Recharged/sealed): parent 12.5/31.25/31.25/18.75%; both
corrections 56.25/50/62.5/31.25%. Do not hide the remaining Recharged sealed
weakness. Both seeds remain candidates for further development, not deployment.

Raw immutable revisions: parent `6798691ac954c9c95702fea5476920062b61631e`;
10101/10102 `c378cd1437fc6bd3fc340c94aca20142d5de5c73`. Local collections:
`ai/runs/discard-opponents-verified-v1/{parent,10101,10102}-2p`.
Summary `strong/discard-opponents-results-v1.json` explicitly records only 2p
and `all_shards_verified: false`. All three full 2p HF jobs are COMPLETED;
do not relaunch. Durable combined evidence is pinned in
`strong/discard-opponents-2p-evidence-v1.json`.

**Both runtime probes completed and independently verified.** The 6p probe
`6aca4fcf095c5780893136a4` completed before15:11:04 UTC. All96 games verify at
raw revision `029d32c11af9310383d942c748202b32719cf487`; search_geo took
1,418.27s (23.64min),448,816 rollouts,zero caps. Combined endpoints:128 games,
483,520 search rollouts,zero caps. Both probes are complete; do not relaunch.
Durable runtime/launch evidence is revision
`3e79eccc2e5219b9a543c32a0fadcd9ee0ad219e`, prefix
`runs/discard-opponents-runtime-completed-evidence-v1`. Earlier partial evidence
remains immutable at its old revision. Full2p evidence is revision
`029d32c11af9310383d942c748202b32719cf487`, prefix
`runs/discard-opponents-2p-completed-evidence-v1`.

**All12 remaining 3–6p shards launched**, 12,096 games, completing dispatch of
all13,440 prescribed games. The 6p linear projection is3.20h; doubling it and
adding120s setup gives6.44h. A9h HF timeout preserves25% extra execution
headroom. Counts3–5 conservatively use this endpoint estimate; their runtime
was not directly measured. These are scheduling budgets; actual-game1600 and
search2400 cutoffs, frozen source, opponents, models and seeds are unchanged.
2p jobs used4h. Jobs needing more than12h under this rule must be partitioned.
No strength criteria were relaxed.

Authoritative status at15:13:46 UTC:4 new jobs RUNNING,8 SCHEDULING. Every
new job is CPU-performance,9h; no duplicate launches. Exact handles:

| Shard | HF job | Last status |
| --- | --- | --- |
| 10101-3p | `6aca55eafee2c900701891e9` | SCHEDULING |
| 10101-4p | `6aca55ebfee2c900701891eb` | SCHEDULING |
| 10101-5p | `6aca55ecfee2c900701891ed` | SCHEDULING |
| 10101-6p | `6aca55edfee2c900701891ef` | SCHEDULING |
| 10102-3p | `6aca55ed095c578089313ad4` | SCHEDULING |
| 10102-4p | `6aca55ee095c578089313ad7` | SCHEDULING |
| 10102-5p | `6aca55ef095c578089313ad9` | SCHEDULING |
| 10102-6p | `6aca55ef095c578089313adb` | SCHEDULING |
| parent-3p | `6aca55e6fee2c900701891e0` | RUNNING |
| parent-4p | `6aca55e6095c578089313acc` | RUNNING |
| parent-5p | `6aca55e7fee2c900701891e4` | RUNNING |
| parent-6p | `6aca55e9095c578089313ace` | RUNNING |

Launch guards are in `ai/runs/discard-opponents-launches-v1`. Collect only
completed outputs at immutable model-repo revisions using
`collect-discard-opponents.py KEY N REV ai/runs/discard-opponents-verified-v1/KEY-Np`.
The comparison script can report a complete-count subset while clearly marking
the suite partial. Do not duplicate or restart queued/live jobs after an
observation timeout. No candidate is promoted and reserved final seeds are unused.

**Independent next work while these jobs run.** A development-only proposal is
saved in `strong/search-transfer-protocol-v1.json`, not implemented or launched.
It pins allthree current models and exact raw baseline artifacts for2p heuristic,
2p search_geo, and3p A260. Test fixed public search48 with geographic proposals
and the model proposal, all existing strategic phases. This would be1,152 new
complete games on intentionally reused paired development deals, keeping each
seed and every adverse rule cell separate. Before any launch, freeze its wrapper,
verify schema4.2 search/menu compatibility and retained discard behavior, and
measure HF search48 runtime. The nine pinned raw baseline files (1,152 games)
were independently rechecked; `strong/search-transfer-plan-check-v1.json`
explicitly marks compatibility, runtime, packaging and launch as still unproved.
Do not derive new hard labels from mixed-policy
winners without evidence: prior continuation audits showed policy dependence.
Historical search48 on the older b052 model achieved42.08% againstA260 over480
games but failed some rule-cell confidence requirements; that does not establish
performance for the current weights. The full2–6p strength gate and exact-config
AMD8840U benchmark remain unchanged. No new gradients occurred this turn.

## Earlier: 4,800 complete games verified; broader opponents profiled


The preceding AI goal turn was **progress**: independently verified all three
learned-discard complete-game screens and started two HF runtime probes. This
continuation is also **progress**: independently collected the 2p runtime probe,
prepared a combined raw-artifact verifier, launched the three full 2p opponent
shards on their measured runtime, and preserved all positive and negative results. No qualification, deployment or reserved final
seeds. The UI remains at the published version.

All three correction-screen jobs are **COMPLETED**, with all 4,800 games
independently verified and zero actual-game or search truncations. Raw model-repo
revision `d6bbd10b729231bc574ad1037065c25d7fb0b61e`; local collection
`ai/runs/discard-correction-screen-verified-v1`. Summary:
`strong/discard-correction-screen-results-v1.json`. Durable combined evidence:
`d278ad42e2213dd3b4a4fcb1991f40b4572046bb`, prefix
`runs/discard-correction-screen-completed-evidence-v1` in
`coyotte508/powergrid-ai-germany-v1`.

| Opponent / count | Parent | Seed 10101 | Seed 10102 |
| --- | ---: | ---: | ---: |
| economic 2p | 55.47% | 69.53% | 70.31% |
| economic 3p | 58.85% | 61.46% | 60.94% |
| economic 4p | 60.55% | 64.06% | 63.28% |
| economic 5p | 71.88% | 71.56% | 71.88% |
| economic 6p | 72.79% | 72.01% | 72.27% |
| capacity-economic 2p | 58.59% | 75.00% | 75.00% |
| A260 3p | 37.24% | 36.20% | 36.20% |

These are actual complete-game win shares on 16 independent deals per cell,
all seats and four rule combinations. Both seeds improve economic 2p (+14.06 /
+14.84 points, paired whole-deal 95% intervals [+7.03,+21.09] /
[+8.59,+21.09]) and capacity-economic 2p (+16.41 points each,
[+10.94,+21.88]). Economic 4p gains are smaller but both intervals are positive.
Economic 6p slips by 0.78 / 0.52 points. Both A260 results are below the 40%
point floor and 1.04 points below the parent; the paired interval includes zero.
Keep both seeds; no winner or strong-model claim. All rule-cell estimates and
contrasts are in the report. These are marginal exploratory intervals, not
simultaneous confidence or the reserved final evaluation.

`strong/discard-parent-loss-profile-v1.json` describes overlapping terminal-loss
conditions, not causal move labels. Against A260, 83 of 120 parent losses have
nominal capacity below the winner's powered cities; 27 have too few cities
despite enough nominal capacity; 10 lose a powered-city tie on cash. At 6p
against economic, the larger category is insufficient cities (63/104), compared
with capacity shortfall (26/104). Unused nominal capacity can mean missing fuel;
it is not evidence of a plant-activation bug.

**Broader opponent extension.** Predeclared 13,440 fresh development games:
parent and both learned seeds, counts 2–6, all four rule cells and every seat,
versus legacy/heuristic/rush (16 deals each) and unchanged search_geo (8 deals).
No candidate search. Independent search_geo remains 16 samples, 6 candidates,
geographic proposals and horizon 2400. Actual-game hard cap remains 1600;
either cap invalidates a result. No engine or opponent changes.
Protocol `strong/discard-opponents-protocol-v1.json`, SHA
`191ab3a37cd1317cff6e7edbb865f33a1644a1d8be8235493dcc4dba60668f2c`.
Frozen source dataset revision `e44812ae307ae3e8a2b62306511d55b61d34720f`,
archive `strong-source-discard-opponents-20261010-v1.tgz`, SHA
`b40efa0c88e8b8a148bf44f955a50b1aa20804cc7e9eb09bd0f4f15efe31a880`.
All 1,370 base files are unchanged. Fresh main seed prefix
`discard-opponents-games-v1-{players}p`; separate smoke prefix
`discard-opponents-smoke-v1-{players}p`. Same pinned model manifest as above.

HF CPU-performance 4h probes launched 14:46 UTC:
- 2p seed10102: `6aca4fce095c57808931369e`, COMPLETED and independently verified
  at raw revision `d26b848916e6c360cec6f332cd01d5b6a0e837c4`.
  All 32 games pass; search_geo takes 108.33s and 34,704 rollouts, zero caps.
  Simpler opponents take 1.66–1.77s each.
- 6p seed10102: `6aca4fcf095c5780893136a4`, last observed RUNNING at
  14:54:38 UTC. Re-inspect this exact handle, never relaunch on log timeout.

Independent collector `strong/collect-discard-opponents.py` downloads immutable
raw artifacts, checks hashes/contracts/outcomes and recomputes every summary.
`strong/compare-discard-opponents.py` revalidates saved artifacts and compares
all three policies, retaining complete counts and every rule cell. It can mark
a complete-count subset explicitly partial; it never treats missing shards as
losses or successes. Runtime report builder `strong/profile-discard-opponents.py`
uses independently verified 2p and 6p smoke collections in
`ai/runs/discard-opponents-smoke-verified-v1/{2,6}p`.

**Full 2p shards launched at 14:58 UTC**, 448 games each (1,344 total):
- parent: `6aca529e095c578089313879`
- 10101: `6aca529ffee2c90070188f0f`
- 10102: `6aca52a0095c57808931387c`

The verified same-count smoke projects 2,019.53 seconds including the doubled
runtime margin and setup, below the existing 3h admission limit. The profiler
now admits counts independently: `--players 2` admits only 2p. Other counts
require their own probe or both endpoints; no unmeasured 6p work was launched.
No frozen runner, evaluation seed, model, opponent, game count or cutoff changed.
Each launch intent preserves the runtime basis and profile hash. Current profile:
`strong/discard-opponents-runtime-profile-v1.json` (only 2p verified so far).

Last authoritative check at **15:00:58 UTC**: all three full 2p jobs and the
6p smoke are RUNNING; the 2p smoke is COMPLETED. Statuses live in
`strong/discard-opponents-status-v1.json`. Verified 2p probe, collectors, runtime
profile and launch records are also durable in HF revision
`505379fca4e2c6091f96cd59af43fafc76ef8ea2`, prefix
`runs/discard-opponents-runtime-evidence-v1` (explicitly partial, only 2p).
Local real-artifact admission tests pass, including rejection of altered search
caps, wrong model/count, missing games and treating a smoke as a full shard.
The combined full-shard comparison awaits actual completed outputs.

**Next:** re-inspect the exact 6p smoke and three full 2p handles. Collect completed
full shards into `ai/runs/discard-opponents-verified-v1/KEY-Np`, then compare with
`ai/.venv/bin/python ai/strong/compare-discard-opponents.py ai/runs/discard-opponents-verified-v1 ai/strong/discard-opponents-results-v1.json --players 2`.
This explicitly marks the broader suite partial. On 6p probe completion,
independently collect it and rebuild the profile with both endpoints. Use measured
runtime to admit or split the remaining 12 planned shards. The launcher's 3h
planning limit and 4h execution limit remain unchanged. If too slow, shard the
workload without weakening opponents or cutting prescribed games. Full launch
intents live in `ai/runs/discard-opponents-launches-v1`; inspect before any retry.
The A260 deficit remains unresolved. The unchanged full multiplayer gate and
exact-model benchmark on the actual AMD 8840U are still required.

## Earlier: learned corrections trained, exported and verified

**Actual complete-game intervention, all960 games verified.** The fixed parent
wins50.3125%, economic-guided discards73.75%, neural-guided discards73.125% in320
fresh2p games per arm (40 deals ×2 seats ×4 rule combinations). Economic minus
parent is+23.4375 percentage points, paired whole-deal95% interval
[+19.6875,+27.34375]. Neural minus economic is−0.625 points, interval
[−1.875,+0.625]: no demonstrated neural advantage. All four economic-minus-parent
rule-cell intervals are positive. Every arm has282 identical public roots and
zero game/search caps. This intervenes at only the **first eligible discard**
per game against unchanged economic opponents; it does not prove a learned
policy or general multiplayer gain. Economic search took39.16s versus767.55s
for neural on HF CPU,72,192 rollouts each. Choose the cheaper economic teacher.
See `strong/public-discard-intervention-results-v1.json`.
Raw model-repo revision `248af172b9ebd0c5732de95903b9d64e27a6223a`;
combined verified evidence `6c48f461d31ee25ca95798aec1a1522974831096`,
`runs/public-discard-intervention-completed-evidence-v1`.

**Fresh training data.** All5,120 collection games and uninstrumented twins are
verified (10,240 engine games):2–6p, every seat, original/Recharged, open/sealed,
four opponent families. Every eligible late discard is captured, including
repeated discards. Opponents: economic/rush/frozen parent at all counts, plus
capacity-economic at2p or heuristic at3–6p. No result-based filtering.
3,361 sanitized public roots:2,527 train,834 validation, separated by whole
(count,opponent family,deal), including all seats/rules/repeated roots together.
Root counts by players2–6:631/458/610/857/805. Every original model proposal,
legal menu, public-state hash and twin trajectory independently reproduced;
zero caps. See `strong/discard-training-collection-results-v1.json`.

**All teacher labels independently verified.** Economic continuations,64 public
scenarios per legal action,685,696 rollouts,zero truncations. Original private
seed/deck and future moves are excluded. Store all per-sample outcomes and ties;
retain all positions. Full five-plant features preserve the old prefixes/menu;
every parent logit was recomputed with zero discrepancy. Raw labels revision
`9b2d0a8ef63fb6da13df6961af153725c35e8c68`, prefixes
`runs/discard-training-labels-v1-Np`. All ten collection/label jobs are COMPLETED;
IDs/statuses live in their tracked status files. Do not relaunch them.
Combined durable evidence in `coyotte508/powergrid-ai-germany-v1`:
`8882fe1eda0cc0b6262e48b46daa555c4b7fb8d6`,
`runs/discard-training-completed-evidence-v1`. Reports:
`strong/discard-training-labels-results-v1.json`,
`strong/discard-training-evidence-v1.json`.

**Learned corrections trained and independently verified.** HF job
`6aca4a1b095c5780893132ed` is COMPLETED (verified14:26:15UTC10October), one L4,
fixed seeds10101/10102,120 epochs and1,200 optimizer updates each. Both selected
epoch10 under the predeclared validation rule; later epochs overfit. The376,001
parameter head takes3.37/3.12s to train, peak allocated GPU memory57.7/57.0MB.
More GPUs would not help this stage; collection and validation dominate.
No local gradients. Launch intent: `ai/runs/discard-correction-launch-v1/launch.json`.
Protocol `strong/discard-correction-protocol-v1.json`, SHA
`aa7bf7bc6a33ac5ea637fabf23d787a481b10496acd228b3fd2eab8504757cdb`.
Dataset source revision `70acf6d6c9eb743aedadc48e38b143ff511803f8`, archive
`strong-source-discard-correction-20261010-v1.tgz`, SHA
`59bf548ea4fa49f848609179a02cd8d692a76f713ff81df83312ff1c150d0bdf`.
Output prefix `runs/discard-correction-v1`.

The parent update79 FP32 checkpoint is frozen exactly. A small head learns
centered action win-credit means, preserving paired-scenario differences and
all ties. Roots receive equal total weight by count, then family, then deal.
Only public late multi-choice discards may use the head; require predicted gain
>0.025 over the parent proposal, otherwise retain parent. This applies to every
eligible discard, not only the first. Schema4.2 appends one public eligibility
bit to schema4.1:state1216/action100. No hidden info or phase-history memory.
Parent inputs are exact old1149/98 prefixes; value outputs stay the uncalibrated
parent estimates. No forced old-economic tie fallback. Both seeds run fully;
best checkpoint is lowest held-out label regret every5epochs, with epoch0
parent baseline and ties retaining the earlier epoch. These are simulated
conditional label metrics, never actual win rates. All gradients run on HF.

Preflight:2,553 menus/prefixes/public eligibility checks; strict zero-head
native64/ONNX parity over2,553 fixtures plus all3,361 labels; parent choices
unchanged everywhere and outside-scope logits identical. Frozen package repeats
all checks and independently re-verifies631 labels. See
`strong/discard-correction-preflight-v1.json`. Both trained exports pass the job and independent strict native/ONNX/serving
checks on all2,553 fixtures, plus all3,361 label inputs. All parent tensors and
2,544 outside-scope decisions remain identical (logit error0); eligible fixture
changes are5/9 and4/9. Largest native/export logit error4.75e-10.

Raw training revision `b115a2d78aae095e51fb72a5535b3507abdf90c0`, prefix
`runs/discard-correction-v1`. Independently verified local outputs:
`ai/runs/discard-correction-verified-v1-recheck`; tracked report
`strong/discard-correction-results-v1.json`. Durable combined evidence revision
`727848e6a675fe749211a2222ca0efd9826b3d23`,
`runs/discard-correction-completed-evidence-v1`. The first collector stopped on
one-ULP float32 weighted-statistic rounding across BLAS builds. Recheck allows
absolute1e-7 only for aggregate gain/regret fields, with exact counts and a
rejection regression; native/ONNX tolerances are unchanged. Failed artifacts and
an explanation are retained. This was no retraining or model repair.

Held-out **conditional simulated gains**, not actual game win gains:

| Seed | 2p | 3p | 4p | 5p | 6p |
| --- | --- | --- | --- | --- | --- |
| 10101 | .21860 | .02625 | .02426 | .00385 | −.00986 |
| 10102 | .22773 | .02625 | .02589 | .00073 | .00000 |

Do not hide the6p regression for10101 or choose a winner from this alone.
Selected export SHA256:10101
`bb0790074d2df1a4929c059b61424da72ddf4fc51cf9396a91a27c031934808d`;
10102 `57f8255e79b991ba466f91e953d0bca6868144bb543577fc0dad8ade387ebf68`.

**Complete-game diagnostic now launched.** Three arms(parent,10101,10102),
1,600 games each:16 fresh deals ×all seats ×4 rule cells versus economic at
2–6p, plus capacity-economic2p and A2603p. All eligible discards may use the
learned head; this tests repeated-discard deployment, unlike the original
first-discard intervention. No training or final seeds. Report paired whole-deal
bootstrap differences and every rule cell; keep the two seeds separate.
Protocol `strong/discard-correction-screen-protocol-v1.json`, SHA
`88d9439a15d20724ae5a155e36b17f2ba54017f971a2c65511ca7fee2023a070`.
Source dataset revision `63db2c7e4b870bf019436a6338c9385f3bad82a6`, archive
`strong-source-discard-correction-screen-20261010-v1.tgz`, SHA
`2ee290d6a7c5863fcfea9ebefa1b00515776be8174e22662870e86e547a04d4d`.
All1,366 base files stay unchanged. Frozen preflight:108 complete smoke games,
all models at2p/6p plus mixed-schema A2603p, zero game/search truncations.

| Arm | HF CPU-performance job |
| --- | --- |
| parent | `6aca4c50095c578089313476` |
| 10101 | `6aca4c51fee2c90070188a1c` |
| 10102 | `6aca4c51fee2c90070188a1e` |

All three jobs subsequently completed and all games were independently verified;
see the latest section above. Do not relaunch these completed jobs.

## Earlier: all 34,720 precision reruns verified; discard audit and intervention setup

The preceding AI goal turn was **progress**: it independently verified all nine
completed screens, exposed a gap in discard search coverage and collected fresh
public discard roots. This turn is also **progress**: verified the frozen audit
package, launched five HF CPU jobs for all 189 roots, independently collected the
all five audits (229,248 rollouts), and launched a fresh complete-game intervention test. No
external blocker.

**Completed comparisons.** All nine precision reruns are authoritatively COMPLETED;
all 34,720 raw games have been independently checked, including exact paired
seat/rule/deal coverage, original training provenance, all 2,553 strict numerical
and legal serving requests per screen, and zero game/search caps. All 19,040
available earlier FP32 terminal result records match their FP64 reruns exactly;
this is not full action-trace equivalence. Original failed FP32 checks remain
failures. Summary: `strong/inference64-results-v1.json`; raw game-record audit:
`strong/inference64-game-record-audit-v1.json`. Durable combined evidence is model
repo `coyotte508/powergrid-ai-germany-v1`, revision
`a9a33c938b0f2cfcef4aa0e442d1b14bcac4bc16`, prefix
`runs/inference64-completed-evidence-v1`. Raw population revision:
`1c1af00ae2c355c1f5c9382cff5dead96f0e4bd7`; raw five-plant revision:
`76307c9e7d820644573c00a3e2afee2eb5a8fbff`.

- Population comparison: all six overall heterogeneous-minus-homogeneous paired
  intervals include zero. Both retained-opponent arms beat control at 4p; control
  regresses against parent there. Highest 2p economic win share is 61.875%, below
  the 66.25% floor. One training seed; exploratory marginal intervals, no
  multiplicity adjustment. There is no clear recipe winner to promote.
- Five-plant feature ablation: full-minus-control economic point estimates are
  negative at every count for both training seeds. Clear overall regressions
  include 6p seed10031 (−8.333 percentage points), capacity-economic 2p seed10031
  (−8.438), and 5p seed10032 (−5.625). Both A260 deltas are negative but uncertain.
  This recipe has no demonstrated benefit from the added inputs; that does not
  show that the information itself is useless. Keep seed contrasts separate.

**Why investigate discards.** The existing search gate covers plant choice, bids
and building, but not `DiscardPowerPlant`. In the 2,553 serving fixtures there
are 58 discard positions and zero searched discards. PPO does update those
moves; do not say discards receive no learning. The old economic discard rule
also maximizes income without its endgame mode. See
`strong/discard-search-coverage-v1.json` and `audit-discard-coverage.cjs`.
Do not change the independent reference opponents to make a candidate look good.

**Fresh public roots.** HF collection job `6aca3874fee2c90070187ba0` is COMPLETED.
320 fresh games across 2–6p × all seats × original/Recharged × open/sealed yield
189 first eligible learner discards (30/21/36/49/53 by count). Eligibility is the
public condition max cities ≥ end threshold−3, never the eventual result or last
discard of a completed trajectory. Every game matched an uninstrumented twin
at every observation/action and terminal record: 640 engine runs, zero caps.
All 189 sanitized public roots independently reproduce the original parent
model's proposal. Keep the three absent rule/seat cells absent: coverage77/80,
no outcome-driven resampling. Raw data revision
`1a9027f0b9c76d86846c3987df0687dcd12f9dd5`, prefix
`runs/public-discard-collection-v1`; root SHA
`268ab59096b3600dd61c10c7622696cacf033ff6902853e0b596b2014df38e0a`.
Tracked report: `strong/public-discard-collection-results-v1.json`.
These are development data, not a strength result or accepted teacher labels.

**Completed HF audit.** All legal discards on every root, three continuation
policies (economic/heuristic/neural), two independent batches of64 public-belief
scenarios: 229,248 independently verified rollouts, zero caps. Identical scenarios within a batch across
moves and continuation policies. No actual private deck/seed or future moves.
Neural continuations use the fixed original update79 parent for every actor;
that is an explicit modelling assumption. Record all ties and sample results.
Any cap makes that target invalid, never a loss. Protocol:
`strong/public-discard-teacher-protocol-v1.json`, SHA
`3b42768997a9f85ca462961448143e385b84bef3878bb27dbc48b03ea2200e09`.

Frozen source dataset revision `52041c96794e0b3c76065ea5538c87b1a878d58f`,
archive `strong-source-public-discard-teacher-20261010-v1.tgz`, SHA
`9bfaa1bbfe95bc5a2c1392e56128315604fe401c9063ed35e7b05ee5410615ff`.
The collection base is preserved byte-for-byte except the five explicit audit
files; 1,338 base files unchanged. Frozen 2p/6p smokes reproduce every original
sample/action outcome exactly (84 rollouts, zero caps). Three continuation
regressions pass: economic/heuristic reference agreement, caps/legality/worker
offsets, hidden-deck/bid invariance. The independent collector rejects missing,
duplicate, miscomputed or silently capped evidence and reports valid caps as
invalid targets. Preflight: `strong/public-discard-teacher-preflight-v1.json`.

HF CPU-performance jobs (4h timeout, launched 13:24UTC):

| Players | Roots | Planned rollouts | Job |
| --- | --- | --- | --- |
| 2 | 30 | 46,080 | `6aca3c8b095c578089312a44` |
| 3 | 21 | 24,192 | `6aca3c8cfee2c90070187e70` |
| 4 | 36 | 41,472 | `6aca3c8d095c578089312a46` |
| 5 | 49 | 56,448 | `6aca3c8d095c578089312a48` |
| 6 | 53 | 61,056 | `6aca3c8efee2c90070187e72` |

All five audit jobs are authoritatively COMPLETED and independently collected.
Status is in `strong/public-discard-teacher-status-v1.json`; do not relaunch them.
Each wrote `runs/public-discard-teacher-v1-Np/{audit-check.json,rows.jsonl}`.
For reproduction pin the recorded model-repo revision and run
`collect-public-discard-teacher.py N REVISION ai/runs/public-discard-teacher-verified-v1/Np`.
It independently recomputes every target and both batch/policy comparisons.
Cross-batch gain selects on batch a and measures on b, then reverses: it is still
simulated continuation return, not actual strength. The resulting complete-game
intervention test is below; do not train from guidance or promote a policy until
its benefit is independently verified. Full engine/inference timings are saved
by count in the result manifest. No gradients ran locally.

The full verified audit is `strong/public-discard-teacher-results-v1.json`.
Durable model-repo evidence revision `29f803c518d18b3acfe93d54c82ccd69095d841e`,
prefix `runs/public-discard-teacher-completed-evidence-v1`, includes every raw
sample, count/rule summary, verifier, protocol and intervention preflight.
Neural selected-action agreement across independent batches is188/189 with the
specified tie rule; 28 positions consistently change the parent proposal.
Conditional simulated cross-batch mean gains by count:

| Players | Roots | Economic | Neural | Consistent neural changes |
| --- | --- | --- | --- | --- |
| 2 | 30 | .21120 | .22005 | 9 |
| 3 | 21 | .17411 | .13876 | 5 |
| 4 | 36 | .14692 | .12174 | 10 |
| 5 | 49 | .01244 | .00925 | 3 |
| 6 | 53 | .01312 | .01179 | 1 |

These are returns conditional on captured public roots and the assumed
continuation policy, not actual win-rate improvements or independent games.
The pattern supports prioritizing2p while retaining the full multiplayer scope.
For2p total measured HF timing is118.004s engine and67.926s policy (560,163 neural
decisions) over all46,080 rollouts; this differs from the initial one-root local
smoke and is the appropriate evidence for later hardware decisions.

**Fresh complete-game intervention launched.** The independently verified 2p audit
has 46,080 rollouts and zero caps. Neural batch choices agree29/30; both batches
change the parent proposal in9/30 positions. Economic choices agree27/30 and
change10/30. Mean cross-batch simulated gain is .2201 neural and .2112 economic;
these are conditional simulated returns, not arena win gains. The verified3p
and4p audits also suggest stable changes;5–6p gains are much smaller. Full count/rule summaries are in the
local `ai/runs/public-discard-teacher-verified-v1/Np` directories. All roots,
ties, disagreements and adverse strata remain in the evidence.

The next causal test uses40 fresh independent deals ×2seats ×4rule combinations
=320 complete games per arm: parent, economic-guided discard, neural-guided
discard (960 total). The only intervention is the first eligible learner discard
in each game, chosen with64 independent public-scenario rollouts. All other
moves remain the same frozen parent policy. Keep the parent proposal on ties.
Economic opponents are unchanged; there is no training or deployment.
This is an explicitly focused2p development experiment, not a narrowed strength
gate. Any gain must still survive every2–6p/rule cell and independent opponents,
then an appropriately trained/exported candidate and the reserved final tests.

Protocol `strong/public-discard-intervention-protocol-v1.json`, SHA
`e50f6b471b0af055eb80048a127b2aea06f01034d437cedba03f1ed4d12c6b76`.
Fresh game prefix `public-discard-intervention-games-v1-2p`; separate search RNG
prefix and separate smoke deals. Prescribed three contrasts, whole-deal paired
bootstrap with10,000 replicates/seed8543, overall and every rule cell. Marginal
exploratory intervals, not multiplicity adjusted.

Source dataset revision `7bc8f890992d3c44faa38a7241521f6d1736d9ea`, archive
`strong-source-public-discard-intervention-20261010-v1.tgz`, SHA
`ecc08c7b64634d83e2f1b023b3a890be1b2368c1434f985287b59950b160583c`.
All1,343 audit-base files unchanged; only the new protocol/harness overlaid.
Local three-arm smoke8games/arm: all pre-intervention public roots, legal menus
and parent proposals identical. Unchanged arm's8 terminal records match a
separate uninstrumented engine control. Frozen-source smoke repeats every
root/action/sample outcome and complete-game record exactly for all three arms.
No game/search caps. `strong/public-discard-intervention-preflight-v1.json`.

HF CPU-performance jobs launched13:34UTC (4h timeout):

- Parent: `6aca3ef4fee2c90070188056`.
- Economic continuation: `6aca3ef5fee2c9007018805e`.
- Neural continuation: `6aca3ef6fee2c90070188062`.

Inspect `strong/public-discard-intervention-status-v1.json` and those exact HF
handles before any follow-up. At the latest authoritative observation parent and
economic are COMPLETED; neural is RUNNING with29 recorded roots and no reported
error. The full intervention comparison has not yet been independently collected.
Artifacts are
`runs/public-discard-intervention-v1-ARM/{intervention-check.json,games.json,roots.jsonl}`.
After all three finish, pin a model-repo revision containing all three and run
`collect-public-discard-intervention.py REVISION ai/runs/public-discard-intervention-verified-v1`.
That collector independently rechecks hashes, complete paired games, all legal
public roots and original model proposals, every search sample/target, unchanged
pre-intervention roots across arms, and paired result intervals. A successful
job alone does not establish benefit; do not train/promote from uncollected results.

The collection/audit preflight evidence is also saved at model revision
`443a96ead2624a87e2ec53f169b7f905a1ed8116`, prefix
`runs/public-discard-preflight-evidence-v1`; manifest
`strong/public-discard-preflight-artifacts-v1.json`.

**Preserved inference evidence.** Eight unique derivatives at model revision
`f14d0db14edb494c8797af00a546ac56088cfa96`, prefix
`runs/inference64-cohort-v1`, pass all 2,553 strict export/serving requests each.
Stored weights and float32 inputs unchanged; float64 internal inference, same
rtol1e-4/atol1e-5. Max native64 logit error6.053e-10, zero fixture action changes.
Actual AMD8840U parent FP64 median/p95 full-request latency2.709/5.235ms; full
s10031 FP64 2.763/5.308ms. Four configs ×2,553 legal requests in an isolated
probe, no deployment. Evidence revision
`5b3e67be71ed911bcef458f6c9c0ed6a6c0c9091`, prefix
`runs/inference64-8840u-probe-v1`; report `strong/inference64-8840u-probe-v1.json`.
The eventual selected winner still needs the full independent strength gate,
reserved tests, a standalone package and a benchmark on that exact machine.

Everything below is historical context. Current handles and next actions are above.

## Previous continuation: numerical repair prepared; both old coordinators ended with errors

Authoritative HF inspections confirm **all training jobs completed**, sealed-menu
pair **COMPLETED**, and both old coordinators **ERROR**. Do not treat their old
RUNNING state snapshots below as current, or blindly restart either coordinator.
The failures are export parity failures, not lost training checkpoints.

- Five-plant control-s10032 screen completed and was independently verified at
  revision`c23b06ec36efd1dc59bde7e43a5bdf66045d0f9a`:4,000 games, zero caps, all2,553
  strict export and legal serving checks. Economic2–6p win shares are
  54.688/65.625/64.297/82.125/78.542%; corrected economic2p51.25%; A2603p39.792%.
  It still fails two-player and A260 floors. This is a masked-input control;
  it does not establish the effect of fifth-plant inputs. Full report:
  `strong/five-plant-control-s10032-screen-v1.json`.
- The other three five-plant screens stopped before arena games on
  `check-export.py`'s unchanged`rtol=1e-4, atol=1e-5`. Each first failure was one
  small logit differing by1.1444092e-5. Reports/logs remain at
  `runs/five-plant-screen-v1-{control-s10031,full-s10031,full-s10032}`,
  model snapshot`de70c5cbd57bcdf34a5b906b4dea92ffcb693a38`.
- Population control update19 also failed parity before its six arenas, at
  checkpoint revision`2c7a715f609b9d7f4d55d646191414f0245590de`. First failing logit
  differs by1.5258789e-5. Frozen coordinator logs are at
  `runs/population-coordinator-v1/control-u19/{prepare,parity-check}.log`, snapshot
  `f25045c917ea697164c3044bac4a3ea0ec72c5eb`. The all-arm update19 comparison has
  **not** been completed. No future evaluation should claim these original
  FP32 failures passed.

For full-s10031, a complete local audit of all2,553 fixtures found one failing
logit position and zero value/action mismatches. All four ONNX optimization
levels (all/extended/basic/disabled) had the same failure; changing optimization
does not fix it. `strong/audit-onnx-numerics.py` records all errors without
loosening the assertion or treating missing checks as passing.

An explicit **inference-only float64 derivative** now exists for the parent and
all four five-plant finals. Stored checkpoint parameter values stay unchanged;
original float32 feature inputs are cast to float64 *inside* the network.
The model loader only enables this with explicit checkpoint metadata. Training
rejects inference-only checkpoints; resume from their pinned original source.
No optimizer ran. Old default inference behavior remains unchanged.

Native SiLU exported to float64 hit an ONNX Runtime QuickGelu fusion with no CPU
double kernel. The versioned derivative`float64-exp-div-silu-v1` uses the
mathematically equivalent`x/(1+exp(-x))` expression, keeping supported operators.
The initial unsupported export and original parity failures are preserved.
This is a numerical derivative with a distinct model hash, not a claim that the
original FP32 export passed or that all complete-game decisions are identical.

**All five derivatives pass all2,553 strict PyTorch/ONNX checks and legal serving
requests**, with the same unchanged tolerance. Maximum logit errors are
4.18e-10–5.90e-10. Local serving timings are from the HX370, not AMD8840U.
Artifacts: model revision **`309ce38ad1609d8a8f296860d8488f9681add327`**,
`runs/five-plant-inference64-v1`; each key has`inference64.pt`, `inference64.onnx`,
`derivative.json`, `parity.json`, `serving.json`. Source model/export scripts and
complete hashes accompany them. Tracked provenance:
`strong/five-plant-inference64-{validation,artifacts}-v1.json`.

The five remote derivative checkpoint/model hashes were downloaded and verified.
Additionally, full-s10031's Exp/Div ONNX passes all2,553 unchanged strict checks
against a **native-SiLU float64 PyTorch reference** (maximum logit error5.894e-10,
all actions match). This checks the activation rewrite independently for that
model; the whole-cohort FP32-to-FP64 action-change audit is still pending.
Detailed failed exports, optimization-level audit, unsupported native64 export,
native-SiLU comparison and86-file original replay runtime check are persistent at
model revision **`13e956d360fc2a0f8545d9a9900873f281e5895f`**,
`runs/export-numerics-investigation-v1`. Tracked manifest:
`strong/export-numerics-investigation-v1.json`.

**Next actions:** check native64-versus-Exp/Div equivalence and record FP32-to-FP64
chosen-action changes; prepare the missing population finals in the same explicit
precision; freeze a new repair evaluation protocol/source and evaluate every
candidate and parent uniformly on the original prescribed development deals.
Use new run names and preserve original failed screens. Do not reuse FP32 game
outcomes as FP64 outcomes, move to a convenient earlier checkpoint, relax
tolerances, or claim the numerical repair qualifies a model. Actual8840U latency,
the complete independent strength gate and reserved final tests remain pending.

## Sealed-menu experiment complete: no robust gain, not promoted

Independent verification at model revision
**`de70c5cbd57bcdf34a5b906b4dea92ffcb693a38`** reproduces the remote comparison
exactly:15,040 complete games, zero caps, all3,760 paired open-game records
identical, both conditions'2,553 strict export and legal serving checks.
Comparison SHA`87961dcb4af1f7ddb43daf1ffed20f3c8ee42230ce7b4e5c64e889a222204342`.
All13 opponent/count cells and rule strata are retained in
`strong/sealed-menu-results-v1.json` and local`ai/runs/sealed-menu-comparison-v1`.

Expanded-minus-control economic2p is+1.875pp, paired whole-deal95% interval
[-0.3125,4.0625]; versus full-sealed economic2p it is+0.938pp[-2.5,4.0625].
A2603p changes only+0.208pp[-1.667,1.875]. Economic5p regresses1.375pp;
Recharged/sealed5p regresses3pp[-6,-0.5]. Against full-sealed economic3p,
Recharged/sealed regresses5.833pp[-10.833,-0.833]. These are marginal exploratory
intervals, not multiplicity-adjusted; no broad improvement is established.
Expanded two-player rates remain55–58.125%, and A26031.458%, below the gates.
**Do not promote the full menu as a strength improvement or retrain blindly on
this recipe.** The infrastructure may support future training, but current
unchanged weights do not benefit reliably from it.

## Earlier this turn: late discard failures isolated

All four H200 input-ablation trainers are **COMPLETED** (authoritatively inspected
at approximately12:17 UTC). The existing coordinator launched all four final
screens; do not duplicate them:

| Key | Final evaluation job |
| --- | --- |
| control-s10031 | `6aca2d08095c5780893122b9` |
| full-s10031 | `6aca2d0bfee2c9007018750f` |
| control-s10032 | `6aca2c0e095c5780893121dd` |
| full-s10032 | `6aca2c8b095c578089312280` |

The coordinator was live; its12:18 snapshot was model revision
`538b91d2fe39f5104c10768ccd2b6bc889c7ac04`. Evaluations were pending, not verified
model improvements. Use `runs/five-plant-coordinator-v1/state.json` and inspect
actual screen handles. Population control training and its coordinator remain
separate. Reserved final seeds remain unused.

### Conditional discard diagnosis: five selected losses can flip

Model: prescribed homogeneous update19, immutable model revision
`cc86f7a36392c829e44fd81d9dbf362cb74a0b1b`, ONNX SHA
`8606c6902806f7df82f7c687fa92746230b63c110d2654730b7913cbc68d3258`.
Selection was frozen before replay: first numeric development deal in each
rule/seat cell with a strict loss, rated capacity below the opponent's powered
count and at least50 final cash, plus the first strict win. There are69 eligible
losses in the320-game homogeneous2p report; only8 selected losses and8 selected
wins are traced. This is deliberately selected outcome sampling, not prevalence.

All16 original terminal records and entire public move traces replay exactly,
both without and with read-only auction instrumentation. Then enumerate all
**four engine-legal discards at the last learner discard** in each selected game,
and resume unchanged greedy neural/economic policies on the same actual deal.
All64 branches finish, every prefix before the intervention is identical, and
all16 original-choice branches exactly reproduce the complete original traces.
**Five of the eight selected losses have a winning alternative discard.** Every
branch, including unchanged losses and degraded winning controls, is retained.
For example, Recharged/open episode35 changes from a loss to a win by discarding
the one-city free plant13 instead of six-city plant31 at the last discard.

This establishes a causal effect *conditional on these selected roots, actual
deals and continuation policies*. Choosing the last discard uses hindsight;
it is not a deployable rule or a public-belief teacher. Do not train on these
outcomes, extrapolate a win-rate gain, or assume every low-capacity free plant
should be discarded. Fuel supply, money, timing and opponents still matter.
The original economic discard prior uses an income-minus-fuel-cost plan even
late in the game; investigate public endgame-aware discard guidance and its
interaction with the completed fifth-plant input ablation before further
training. New teachers/priors must be tested on fresh complete games and under
public-information scenarios, retaining existing independent strength gates.

An initial draft incorrectly enumerated all five held plants. The first branch
stopped at the exact-legal-set assertion: the newly purchased plant cannot be
discarded. No branch outcomes were analyzed then. Protocolv2 preserves all16
roots and enumerates the exact four legal choices; rejected draft and failure
log are retained. Do not describe this initial validation failure as a model
or game-engine failure.

Persistent artifacts: model repo `runs/two-player-discard-diagnostic-v1`, revision
**`ac6cf7294ae5d0d8aab5dadcb77f75b0c0fc2378`**. `evidence.tgz` contains all public
traces, auction ledgers,64 branch traces and intervention records, original
controls and rejected-draft evidence. Source scripts/protocols/selection and
hashes accompany it. Tracked files:
`strong/two-player-discard-diagnostic{,-artifacts}-v1.json`,
`strong/two-player-upgrade-selection-v1.json`,
`strong/two-player-discard-counterfactual-protocol-v2.json`,
`strong/replay-discard-counterfactuals.py`, and diagnostic preload scripts.
No optimizer steps, production change, or final seeds were used.

### Sealed-menu control independently collected; pair pending

Control result revision **`949d0f7f7699711953edc8278ffe6673eb4fff66`** is independently
verified: all13 cells /7,520 games, no caps, all2,553 strict export and legal
serving checks, exact source/model/protocol/fixture hashes. Local artifacts:
`ai/runs/sealed-menu-comparison-v1/control`. As an additional isolation check,
all1,760 paired open-game records match between old and full-sealed reference
opponents after excluding the intentionally different role names. Saved in
`reference-open-isolation.json`. Expanded-condition results and the required
3,760 cross-condition open-game matches are still pending at this observation;
the paired job remains live. Do not interpret control-only percentages as a
menu effect or compare them to different-seed population results.

## New result: homogeneous final checkpoint, primary pair available

Independent collection from coordinator snapshot
**`0935d49415181c52eb30e8d3da4ab2fa62e96f53`** verifies homogeneous update19:
all training/checkpoint hashes and provenance, 2,553 strict parity requests,
six complete arena cells, **3,680 games with zero truncations**. Checkpoint
revision **`cc86f7a36392c829e44fd81d9dbf362cb74a0b1b`**; raw result revision
**`af1a3e2cda076beee87483d0a38178e045dceffe`**. Local artifacts are under
`ai/runs/population-homogeneous-u19-v1`; tracked full count/rule results and all
paired contrasts are `strong/population-homogeneous-u19-screen-v1.json`.

| Final homogeneous win share | Econ 2p | 3p | 4p | 5p | 6p | A260 3p |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| % | 61.875 | 61.25 | 60.156 | 75.75 | 74.896 | 41.667 |

Two-player rule cells are original/open65%, original/sealed60%,
Recharged/open67.5%, Recharged/sealed55%. The two-player economic floor66.25%
still fails. Against the same parent/deals, overall gains of4.53pp in2p
([-2.34,11.41]) and5.10pp againstA260 ([-1.88,12.29]) are inconclusive.

The predeclared primary **heterogeneous-minus-homogeneous update19** pair is now
available: economic2–6p differences are -6.56,+2.60,+3.59,0,-0.73pp; A2603p
is+2.81pp. **All six overall95% whole-deal intervals include zero.** In2p the
interval is[-14.06,+0.94]pp, and A260[-3.23,+8.96]pp. This is one training-seed
pilot with exploratory marginal intervals; do not claim a clear superior
population recipe, pool player counts, or select update9 in place of prescribed
update19. All rule strata and regressions are retained in the report.

Population control update19 and the full three-arm comparison remain pending;
the existing population coordinator owns their evaluation. The four H200 runs
are a separate paired input ablation with heterogeneous opponents fixed in both
conditions, not evidence that heterogeneous training has won this comparison.

## Latest: frozen-weight sealed-bid experiment running

HF job **`6aca28c7fee2c90070187151`** was launched successfully at 12:00 UTC,
10 October. Inspected RUNNING at 12:03 UTC; subsequent logs reached the control
economic 5p cell. **Do not rerun `launch-sealed-menu-pair.py`**: persistent launch
intent is `ai/runs/sealed-menu-pair-launch-v1.json`, mirrored by
`strong/sealed-menu-status-v1.json`. An observation timeout is not a failed job.

This is an inference experiment, with **no optimizer updates**. It holds original
H200 u79 tensors and ONNX graph fixed, and adds revision `4.0-sealed-all-bids` to
allow every engine-legal sealed bid. The menu-relative best-heuristic flag retains
its definition but is recomputed on the larger menu. Open menus and other model
revisions stay unchanged. Neural actions now dispatch through the acting model's
menu; search with the new revision is explicitly rejected because its proposal
indices have not been adapted. The experiment does not change either running
training cohort, older opponent identities, final gates, or published UI.

Validation, saved at model revision **`42593c73c1f2d778c9eea8ec0c71bb8e408d6228`**,
prefix `runs/sealed-menu-initial-v1`:

- All 2,553 original encoder outputs and actor menus match their pre-edit
  references exactly; hidden deck/seed/sealed bids/queued plans do not affect the
  new encoding. All added 3,002 bids apply successfully on independent engine
  copies. Of these fixtures, 42 sealed menus expand. This is fixture coverage,
  not a prevalence estimate or evidence of better play.
- Separate engine-legal fixtures preserve all requests, leaving the original
  pruned fixture file untouched. New fixture SHA256 is
  `0a43c0234b810253d07ef7281ee3e83c8fe7a4fa27e8aa05bd6589c024661883`.
- 176 complete integration games, every count/rule/seat against a frozen neural
  opponent plus new heuristic modes: no caps; 155 formerly omitted bids actually
  played; all 40 paired open-game result records exactly identical. Records
  include terminal player summaries and action counts, not entire trajectories
  or the complete terminal engine state.
- All 2,553 strict single-request export checks and engine-legal serving checks
  pass. Saved initial files' hashes were reverified in this continuation. No
  batch16 parity or current-model AMD8840U latency claim is made.

Frozen protocol: `strong/sealed-menu-protocol-v1.json`. Each condition plays
**7,520 fresh development games**, 40 deals/count × every seat × four rule cells:
economic 2–6p, capacity-aware economic 2p, A260 3p, plus separately named
full-sealed-menu economic 2–6p and capacity-aware 2p references. The latter are
additional references, not assumed stronger or replacements for existing gates.
Both conditions run sequentially on one CPU-performance host (24 workers, four
hour limit) to avoid CPU-host differences in the required 3,760 paired open-game
record identity check. Seed prefix `sealed-menu-development-v1-{players}p`;
20,000 whole-deal bootstrap samples, seed10041. Report every count/rule/reference
contrast and regression; intervals are exploratory and not multiplicity-adjusted.

Source archive `strong-source-sealed-menu-20261010-v1.tgz`, dataset revision
**`e571f96d453a4b148a3185b99cb047655b6a4f75`**, SHA256
`e9de0cc444c843d5b298d5070298902f613a19aa1fab7d568093fa939871b993`.
All source/model/fixture pins are in `strong/sealed-menu-{source,initial}-v1.json`.
The expanded PT/ONNX carry a distinct revision tag and an explicit untrained
transfer record. They are not a newly trained or qualified model.

When complete, pin a model-repo revision and independently run
`collect-sealed-menu-screen.py {control|expanded} REV OUTPUT`, then
`compare-sealed-menu-screens.py CONTROL EXPANDED --output REPORT`. Compare the
reproduced report to `runs/sealed-menu-pair-v1/comparison.json`; screen evidence
lives at `runs/sealed-menu-screen-v1-{control,expanded}`. The pair wrapper uploads
failure evidence too. Any open-game mismatch invalidates an isolated-menu effect
claim and must be diagnosed before interpretation. Reserved final seeds unused.

At 12:03 UTC the four H200 ablation trainers, population control trainer and both
coordinators were all authoritatively RUNNING. Population homogeneous training
was COMPLETED, with its six update19 screens still being collected by the old
coordinator. Do not manually duplicate those screens. H200 logs subsequently
showed completed updates14–15 and ongoing updates15–16; final update19 evaluation
is still owned by `6aca236f095c578089311e41`.

## Latest: parent reference complete, automatic final evaluations, bid-menu audit

The parent screen **COMPLETED**, HF job `6aca2110095c578089311b47`. Independent
collection at model revision **`616b253875d3219667a3041ae192a2d46f2fbb92`** verified
all artifact/source/protocol hashes, all 2,553 strict export and legal serving
checks, and all 4,000 game outcomes with zero truncations. Exact 40 deals, every
seat and all four rules in each of seven cells; final reserved seeds unused.
`strong/five-plant-parent-screen-v1.json` contains all count/rule cells and
20,000-bootstrap whole-deal intervals. Raw local data is
`ai/runs/five-plant-comparison-v1/parent`.

| Parent on fresh ablation deals | Econ 2p | 3p | 4p | 5p | 6p | Corrected econ 2p | A260 3p |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Win share (%) | 54.06 | 62.81 | 56.56 | 75.75 | 73.70 | 50.63 | 38.96 |

The original/open 2p subgroup against economic is 38.75%. These are different
fresh deals from prior screens, not a change in the frozen parent. Compare each
new model against these same paired deals; never compare unpaired percentages
across seed sets as a training effect. This is an unqualified reference, not a
new candidate or evidence the two-player gap has closed.

### Evaluation ownership: do not manually duplicate any new ablation screen

New CPU-basic coordinator **`6aca236f095c578089311e41`** is RUNNING (confirmed
11:38–11:39 UTC). It has collected the existing parent without starting any new
parent games. It owns **all four final update19 ablation evaluations**. It waits
for each named trainer to be authoritatively COMPLETED, validates the final
wrapper/checkpoint/metrics, pins an immutable model revision, and launches one
CPU-performance screen per final model. Intermediate checkpoints/internal best
are never selected. It independently collects the seven cells and compares
both training seeds after all five reference/candidate screens are verified.

- State: model repo `runs/five-plant-coordinator-v1/state.json` (pin a repo revision).
- Config/source/status: `strong/five-plant-coordinator-{config,source,status}-v1.json`.
- Source archive: `strong-source-five-plant-coordinator-20261010-v1.tgz`.
- Dataset revision: **`f9097a2f61eeeef636b13f9f92a9320149c1ff64`**.
- Source SHA: `aad13711f2ebfdeb27b9f5ed089a28ef23a7dc56a6793b83530534f64d7fdba1`.
- Persistent launch intent: `ai/runs/five-plant-coordinator-launch-v1.json`.
- Four local screen intents are reserved as `coordinator_owned` under
  `ai/runs/five-plant-screen-launches-v1`; do not delete or bypass these guards.

It persists intents before submission, never retries an ambiguous POST, keeps
observing the same handle after a read timeout, and only treats explicit HF
terminal stages as terminal. Failures do not abandon live peers. State-only
recovery rehydrates exact pinned artifacts before comparison. Ten focused
failure/recovery tests pass; the five screen-validation tests and existing
80-game mixed-revision integration test also pass (16 tests total). Its startup
tests passed on HF, then parent collection succeeded. Final learner collection
is still pending and must not be inferred from parent success.

The old population coordinator `6aca0d29095c578089310fca` separately retains
ownership of homogeneous/control update19 and all-arm comparisons. Do not mix
their states or manually duplicate either coordinator's work.

### Confirmed action-menu limitation; diagnostic only, not a strength result

`ai/core.cjs::candidates` prunes bids when more than 48 are legal: first 8,
multiples of 10, and maximum. The exact current runtime was checked against the
immutable training source. Audited all 2,553 serving fixtures: 564 bid positions,
142 pruned (100 open,42 sealed), all non-bid legal moves preserved. In 14 sealed
positions, all bids preferred by the economic heuristic were omitted. Both
original and capacity-aware heuristic preferences had the same omission counts.
This is a stratified fixture corpus, **not a prevalence estimate**.

A separate read-only encoding/inference audit evaluated all legal bids on those
142 positions using frozen original u79 weights. State and all existing action
features except the menu-relative best-heuristic flag (index 75) remained exact;
the temporary candidate override was restored exactly and no game state changed.
The model changed 13 sealed choices, 12 to bids absent from its original menu
(4 of these were in 2p). All 100 pruned open-auction choices stayed unchanged.
PyTorch/ONNX strict single-request logits/values and chosen actions agreed on
both original and expanded sets of 142 positions. Example changes 40→48 or 8→9 are model
preferences, **not proof of better play**. No games or gradients ran for this
audit, and no production encoder/baseline/training job was changed.

Raw coverage, per-position choices, encoded pairs and runnable audit scripts are
persistent in model repo `runs/bid-candidate-audit-v1`, revision
**`4b8c97343d4be022d003002e5781bdfdca527041`**. Tracked summary/provenance:
`strong/bid-candidate-audit-v1.json`. It supports a future separately frozen
full-legal sealed-bid experiment with unchanged weights, paired outcomes, all
existing baselines plus appropriate unpruned opposition. Do not alter the
running two-seed input ablation or call this a demonstrated strength gain.

**Fixture caveat for that future experiment:** existing fixture `legal` lists
are `c.candidates`, a pruned subset of engine legality. An expanded-menu encoder
needs a separate fixture manifest built from exact engine `allLegal` lists and
identical requests, plus a versioned per-actor action-menu/encoder contract.
Do not weaken current checks, mutate existing fixtures, apply a global override
in actual games, or silently change retained opponents. The diagnostic override
in `encode-full-bid-audit.cjs` is for isolated read-only inference only.

## Previous: final population result and two-seed input ablation (11:29 UTC)

The original **heterogeneous update19** trainer has COMPLETED. Its prescribed
final development screen is independently verified: 3,680 complete games, all
40 deals × every seat × four rules, no caps, all 2,553 strict export checks.
Checkpoint revision **`3a71c9d1d7300a2d2169e059e8d9242167e73625`**; result revision
**`7055d120f9e503694fd58575d0e91e118e18dfa3`**. Local raw data:
`ai/runs/population-heterogeneous-u19-v1/heterogeneous-u19`. Source/metrics/export
hashes are in its `checkpoint.json`, with independent evidence in the parent
`verified.json`. `strong/population-heterogeneous-u19-screen-v1.json` preserves
all absolute cells and paired comparisons against both original parent and u9,
including every rule subgroup.

| Final heterogeneous | Econ 2p | 3p | 4p | 5p | 6p | A260 3p |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Win share (%) | 55.31 | 63.85 | 63.75 | 75.75 | 74.17 | 44.48 |

Against parent: A260 +7.92 pp [2.50,13.33], economic4p +3.67 pp [0.16,7.19],
but economic2p -2.03 pp [-8.44,4.38]. These are marginal exploratory paired-deal
intervals, one training seed, not multiplicity-adjusted. Original/sealed economic2p
is **48.75%**, and overall two-player performance misses the unchanged 66.25%
floor. Do not promote this model or select u9 instead based on these outcomes.
All-arm primary comparison is still pending; the original coordinator owns it.
At 11:22 UTC the other two original trainers and coordinator were confirmed
RUNNING. At 11:27 the coordinator snapshot (`528bf019eee9f0aa9d16ae59e72f65327d381d38`)
still had only heterogeneous-u19 collected; all u9 arms are complete. Inspect
actual job states before any recovery. Never duplicate coordinator-owned screens.

### Four independent H200 training jobs, final checkpoints only

`strong/five-plant-ablation-protocol-v1.json` is immutable and authoritative.
Both conditions start from **identical weights transferred from original H200u79**,
not an unfinished population winner. Same 985,346-parameter architecture, full
encoder work, optimizer, retained opponent mixture, seeds and schedules; the
control masks only the appended 66 state and 2 action inputs. Existing feature
prefixes, priors and teacher labels are unchanged. Two seeds (10031,10032),
20 updates × 240 complete games, 48/count/update: **4,800 games/run**, 19,200 total.
Four independent H200 learners (not four GPUs on one learner); measured full-update
speedup over optimized CPU is 1.39×. All gradients remain on HF Jobs.

| Run key | HF job |
| --- | --- |
| control-s10031 | `6aca1efa095c578089311a40` |
| full-s10031 | `6aca1efa095c578089311a42` |
| control-s10032 | `6aca1efb095c578089311a44` |
| full-s10032 | `6aca1efcfee2c90070186af2` |

All four confirmed RUNNING at 11:27 UTC, update2 in progress or just completed,
with no caps in the observed completed batches. Full final validation is pending.
`strong/five-plant-ablation-status-v1.json` records launch intents and observations;
`ai/runs/five-plant-ablation-launches-v1` holds local no-duplicate launch guards.
Do not rerun launchers. Training source is `strong-source-five-plant-ablation-20261010-v1.tgz`,
dataset revision **`8349b1348a9d6d7fd9efe4382d77619d75fcc14d`**, SHA
`aeaf45968ec6054009a546ff22a01cb4ae32487c3be3b43025530284aabfc104`.
Initial weights and audit files: model revision
**`22fe3c03faaae01225cab24e9ecedda654df835b`**, `runs/five-plant-ablation-initial-v1`.
Exact hashes are in `strong/five-plant-ablation-initial-v1.json`.

**Inherited numerical limitation:** original u79 and its full-input transfer both
fail strict ONNX batch16 tolerance on the same one logit; all actions agree.
All 2,553 strict single-request checks pass for original/full/control. PyTorch
transfer is exact at both batch1 and16; training uses PyTorch. No tolerance was
weakened. Preserve `initial-numerical-audit.json`; do not claim all batched export
checks passed. The earlier u9 diagnostic transfer passed both batch sizes, a
different checkpoint. New final candidates must pass strict single-request export
and legal serving checks. Initializers are not deployment candidates.

### New development evaluation and next steps

`strong/five_plant_screen.py` validates all final artifact hashes, initialization,
frozen opponents, all 20 balanced batches, game/search caps, snapshot admission,
finite weights and zero/nonzero extra projections. It then runs strict parity and
legal serving on all 2,553 fixtures before seven independent evaluation cells.
Each final candidate and original parent gets **4,000 games**: economic2–6,
capacity-aware economic2p, frozenA2603p, on the same40 fresh development deals per
count (`five-plant-ablation-screen-v1-{players}p`), all seats/rules. No search added
to candidate. Only final latest update19 is compared; update9 is recovery-only.
Original economic remains a separate baseline; corrected economic is evaluation-only.

The parent's evaluation is RUNNING as CPU-performance job
**`6aca2110095c578089311b47`**, run `five-plant-screen-v1-parent`. At 11:29 UTC
all 2,553 strict export and legal serving checks had passed; economic2p/3p/4p
game cells completed, remaining cells running. No aggregate result collected yet.
The original homogeneous/control trainers were at updates16/14 and coordinator
RUNNING (see `strong/population-and-screen-observed-20261010-v3.json`). Check actual
status; `strong/five-plant-screen-status-v1.json` is only the last observation.
Immutable evaluator source `strong-source-five-plant-screen-20261010-v1.tgz`,
dataset revision **`79480a2c32e9ecdffce00440e1150cb857c18d1e`**, SHA
`2540dd5ccaee671baf47467c9e184dd7dda602de98cf07b898fff15f7ccc96b0`.
Five evidence-rejection tests pass (wrong encoder/model/opponent, missing paired
seat/rule/deal, actual/search caps, repeated deals). All six old final population
cell verifications reproduce unchanged after optional encoder-tag support.

The new coordinator described above now owns every final screen. Do not manually
launch `launch-five-plant-screen.py` while it is live, and never bypass recorded
intents after observation timeouts. Only reconcile recovery against authoritative
job state and persisted remote intent/job IDs. Its collector pins each completed result revision and runs
`collect-five-plant-screen.py KEY REV ai/runs/five-plant-comparison-v1/KEY`.
The collector verifies source/protocol provenance, retraces all training artifact
hashes and rechecks all raw outcomes. Preserve all seven cells and rule subgroups.
Once parent plus four finals are collected, run `compare-five-plant-screens.py
ai/runs/five-plant-comparison-v1 --output PATH`. It reports full-minus-control
separately for both training seeds and against parent, using 20,000 whole-deal
bootstrap draws with seed10031. Reused 40 deals do **not** become 80 independent
deals across training seeds. Assess consistent two-player gains and regressions
in both seeds, references and every other count; do not select a convenient cell.

Final reserved seeds remain unused. Default-bot, heuristic, rush, independent
search, retained neural opposition, serving package, engine compatibility and
actual AMD8840U delivery remain required for eventual qualification. This ablation
is a development experiment, not a replacement for the full strength gate.

## Earlier completed evidence (11:06 UTC)

All **three update9 arms** are now collected and independently reverified:
11,040 candidate games plus 3,680 previously pinned parent outcomes, exact
40-deal/seat/rule coverage in each cell, zero caps. `strong/collect-population-comparison.py`
rechecks checkpoint bytes/provenance, all balanced training batches, complete
export reports, raw game reports and all six contrasts; it exactly reproduces
the coordinator's 20,000-bootstrap whole-deal comparisons. Source snapshot:
**`4669fed94f8882e55eac3e3ff7bfb186c92ad36c`**. Local artifacts are
`ai/runs/population-comparison-u9-v1`; full verified results including every
rule/count cell are in `strong/population-comparison-u9-v1.json`.

| Update9 arm | Econ 2p | 3p | 4p | 5p | 6p | A260 3p |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Parent (u79) | 57.34 | 60.00 | 60.08 | 76.25 | 73.13 | 36.56 |
| Control | 53.44 | 58.96 | 53.91 | 73.19 | 70.00 | 38.13 |
| Homogeneous | 60.00 | 63.54 | 58.67 | 76.31 | 77.08 | 39.38 |
| Heterogeneous | 58.44 | 60.42 | 64.06 | 76.06 | 73.18 | 45.52 |

Heterogeneous minus control: economic4p +10.16 pp [5.16,15.31]; A2603p +7.40 pp
[1.56,13.33]. Heterogeneous minus homogeneous: economic4p +5.39 pp [1.09,9.84],
but economic6p -3.91 pp [-7.24,-0.63]. Its A260 advantage over homogeneous is
+6.15 pp [0,12.29]. These are **intermediate, marginal exploratory intervals,
one training seed and many contrasts**; no universally best recipe is established.
None clears the economic2p floor. Keep primary update19 comparisons unchanged.

The additional opponent **`economic_capacity_v1`** is implemented and wired into
the arena bridge/CLI. It uses the schema4.1 pure auction valuation helper, with
four plant slots in two-player portfolios; every existing opponent identity and
all training mixtures remain unchanged. A 16-game / 9,535-decision equivalence
test confirms identical choices and RNG consumption at 3–6 players. A focused
rule/information test also passes. This is a separately named reference, not a
replacement for old economic/search opponents or a presumed stronger teacher.

`strong/capacity-reference-protocol-v1.json` froze 40 new development deals,
all seats × four rule combinations, 320 games/cell before outcomes. All five
cells completed with no caps (1,600 total), independently verified by
`strong/collect-capacity-reference.py`. Results:

- Capacity-aware bot vs original economic: **52.50%**, whole-deal interval
  [48.59,56.56]; not clearly stronger. 321 candidate-turn deterministic choices
  differed. Its original/sealed subgroup was 48.13%; all subgroups are retained.
- Parent vs original/corrected economic: **57.81 / 59.38%**.
- Heterogeneous u9 vs original/corrected economic: **52.66 / 51.56%**.
- Against corrected economic, heterogeneous minus parent is **-7.81 pp**,
  paired whole-deal marginal interval [-15.00,-0.63]. Against original economic
  it is -5.16 pp [-12.81,2.66]. Do not hide this fresh two-player regression
  behind the A260 gain or the earlier screening seed results.

These results reinforce the need for a controlled two-player repair. They do
not establish that correcting the heuristic alone improves its strength or that
schema4.1 learning is better (no strength test of a trained schema4.1 candidate
has been conducted). Preserve both old and corrected reference opponents in
future relevant evaluations. No new teacher labels or training jobs this turn.

Persistent source: `strong-source-capacity-reference-20261010-v1.tgz`, dataset
revision **`7c1514ddf4a8f94cd0baebe0e733275b62678cdb`**, SHA
`c4cf7694a5cd86a7decb9f581c7ca824a1be7741c121a652063ce0289a18af7f`.
Raw reports/protocol/source/summary: model repo `runs/capacity-reference-v1`,
revision **`76e207f4ee444dd4e4f4ee13177eb460d2071125`**. See tracked
`capacity-reference-{protocol,source,artifacts,results}-v1.json`; local raw data
`ai/runs/capacity-reference-v1`. Local inference only, no gradients.

At **11:06 UTC**, all three trainers and coordinator were confirmed RUNNING:
heterogeneous update19 (233/240 complete), homogeneous update13 (226/240),
control update11 (220/240). State snapshot at model revision
`76e207f4ee444dd4e4f4ee13177eb460d2071125`; all u9 arms collected and comparison
ready, no u19 checkpoint recorded yet. Exact job IDs/progress are in
`strong/population-observed-status-20261010-v2.json`. Inspect live state before
collecting later results; coordinator owns all u19 screens. Do not duplicate,
restart, or alter the running cohort. No primary comparison yet.

## Validated five-plant implementation for the next controlled training run

The five-plant HF gradient smoke is **COMPLETED and independently verified**.
Job `6aca192dfee2c900701863fd`, H200, run `five-plant-gradient-smoke-v1`;
terminal status confirmed at 10:57 UTC. One update / 80 complete games (16 per
count), heterogeneous retained opponents, schema4.1 learner/snapshots with
schema4.0 frozen opponents. Both new projections changed from zero (norms
0.02661736 / 0.003502778), all parameters finite, all frozen roles present,
zero actual-game caps and **81,872 search rollouts / zero caps**. Update took
76.85 s. The trained ONNX passed all 2,553 strict export checks and all actions
matched its checkpoint. **This is correctness evidence, not playing strength or
candidate selection.** No local gradients ran. Do not launch this smoke again.

Immutable model-repo result revision:
**`4669fed94f8882e55eac3e3ff7bfb186c92ad36c`**.
`strong/collect-five-plant-smoke.py REV OUTPUT` independently verified every
artifact hash, source/protocol/init provenance, actual checkpoint dimensions,
new parameter norms, balanced metrics, frozen opponent pins, snapshot admission
and export report. See `strong/five-plant-smoke-results-v1.json` and local raw
files `ai/runs/five-plant-smoke-collected-v1`. Trained PT SHA
`f7c4771038a0470b30680f7c8325f62969f2e4e0a22c0724bc5f39cef77f28cc`;
ONNX SHA `574ad0af7e3c9df95bb9c28c6bb99ed1ac6a2f9e1eee5d069461db45d1eb42a2`.
Retain this smoke as integration evidence. The later fixed-parent two-seed
ablation above supersedes the earlier plan to wait for population recipe
selection; the original population experiment and strength gates are unchanged.

Schema **4.1-five-plants** is implemented as `features-v4_1.cjs` and
`model_v4_1.py`; the architecture is `multiplayer_ordered_plants`. State/action
sizes are **1215/100**: unchanged old 1149/98 prefixes plus six fifth-plant slots
and two capacity-aware economic action cues. Extra cues are learned inputs;
old residual prior and teacher index remain unchanged. Pure `economics-v4_1.cjs`
uses the four-plant limit for two-player purchase valuations. Old encoders,
network code, economic/search opponents and running experiments remain unchanged.
Trainer, model loader, evaluator and package builder support the new revision;
old/new neural opponents keep their own encoders. The explicit CPU transfer adds
1,664 zero-initialized parameters, preserving old weights and matrix shapes.
Contiguous legacy input slices are necessary for exact CPU transfer numerics.

Verified local evidence is in `strong/five-plant-validation-v1.json`:

- All 2,553 fixtures preserve every old feature exactly; fifth plants are explicit
  in the 8 relevant discard states; 8 positions have changed added auction cues.
  Deck order, sealed bids, seed and injected queued plans do not affect inputs.
- Parent and transferred PyTorch outputs match **exactly** on all 2,553 positions
  at batch sizes 1 and 16 (5,106 comparisons); strict ONNX tolerances and all
  decisions match. Six model-contract unit tests pass.
- Eighty complete mixed-revision games cover every count/rule/learner seat with
  zero truncations. Ten existing information/population Node tests pass.
- All 2,553 real serving requests return legal moves. The extracted package works
  from `/`, passes all 1,205 file hashes and 80 count/phase/rule cases. Local
  latency is a contended HX370 diagnostic, **not an AMD8840U qualification**.

Diagnostic transfer parent is heterogeneous update9, pinned by the prior audit;
this is not selection of the next full-training parent. Initial artifact revision
**`bbbbd1ac091651f8854386a476cb42617d9c095a`**, under
`runs/five-plant-transfer-v1` in the model repo. Initial PT SHA
`5bd9cef9b6a419c39f2d461d549393c5f046bb8b084ddd7d92221090a279d227`;
ONNX SHA `ded16c0977cea50049df0cea58d238b96655d32eddb1766ab849ad284055b11b`.
See `strong/five-plant-transfer-artifacts-v1.json` for further validation revision
and exact package/report hashes. Local outputs are `ai/runs/five-plant-transfer-v1`
and `ai/runs/five-plant-fixtures-v1.jsonl`.

Immutable source: `strong-source-five-plants-20261010-v1.tgz`, dataset revision
**`9691971d63d556b542647137291d19cfce750808`**, SHA
`877a58929a6eb2141f46cc96ba5ebb7b20f7078bbc51aad5d652b8f6cacf9055`.
`strong/five-plant-source-v1.json` lists all overlays and unchanged base provenance;
`strong/five-plant-smoke-protocol-v1.json` freezes exact job settings.
Use the actual update19 population comparison to choose the next parent/recipe;
require controlled strength evaluation of this feature change. Preserve all
existing baseline identities/gates and retain the separately named capacity-aware
reference when evaluating two-player strength. No new expert hard labels.

At 10:54 UTC, all three population trainers and coordinator were confirmed
RUNNING. Heterogeneous was on update17, homogeneous update11, control completed
update9. Coordinator owns every scheduled screen and had launched control-u9.
Its state was pinned at `bdbd57a81517231658d791f0c984d7cbb95d123e`, copied to
`ai/runs/population-coordinator-observed-state-v1.json` (wrapper with `revision`
and `state`). Inspect live jobs and refreshed state before collecting results;
never manually duplicate its screens. Reserved final seeds remain untouched.

## Diagnostic rationale for the new two-player plant context

Two-player terminal audit (`strong/two-player-terminal-audit-v1.json`): the first
population screen has 187 wins and 133 strict losses. Among losses, 29 are
tiebreaks; 63 have both cities and rated capacity below the winner's powered
total; 28 have enough cities but insufficient capacity; 10 have insufficient
cities despite sufficient capacity; 3 have both but lower actual powered count.
These are terminal constraints, not proof of earlier causal mistakes.

Sixteen preselected wins/losses (one each per rule/seat cell, first numeric deal)
replayed exactly with the frozen v32 arena engine and the pinned heterogeneous
update9 model. The public move traces remained byte-identical after adding the
plant diagnostics. See `strong/two-player-replay-selection-v1.json`,
`strong/two-player-plant-audit-v1.json` and
`strong/two-player-plant-audit-source-v1.json`. Full traces, reports and diagnostic
source are persistent in HF model repo under `runs/two-player-plant-audit-v1`,
revision **`f06dc7d6e26646ec92f9afeef6ba69df54f02b59`**.

Confirmed issues:

- `economics.cjs::plantValue` assumes replacement at three held plants. Germany
  two-player games allow four. Changing only the portfolio limit changes 151
  of 172 observed valuation queries (both players; queries are not independent
  games), by -14 to +10. The direction is not uniformly beneficial: these are
  heuristic values, not true action values. A corrected helper still needs
  strategic evaluation.
- Schema4 has four explicit plant slots per player. All 192 observed discard
  states held five plants and had `chosenPowerPlant` cleared. Aggregate capacity
  and the fifth plant's own discard action row retain partial information, but
  other candidate scores and the state-only value head lack a fifth plant slot.
  Do not call the fifth plant completely invisible. This is a confirmed input
  limitation; its strength impact still needs a controlled experiment.

Schema4.0 and the current cohort are immutable. The append-only implementation
and its validation are described above. The diagnostic helper in
`audit-two-player-plants.cjs` remains a read-only preload hook, not a production
module. The separate `economics-v4_1.cjs` is the new pure helper. Corrected
heuristic values still need playing-strength evaluation; input correctness and
exact transfer do not establish strategy improvement.

## First population checkpoint — verified intermediate result

The heterogeneous arm's update 9 passed full 2,553-position export parity and
provenance validation for its ten complete, balanced training batches. All six
screen jobs completed and their raw outcomes were independently reverified.
Checkpoint revision: `3f56f692fc5204140257538099e1ec50a2b4fb09`.
Result revision: `116032eed805e92e1c30a7d1f1192c2704e8f8f6`.
Exact hashes and details: `strong/population-heterogeneous-u9-checkpoint-v1.json`
and `strong/population-heterogeneous-u9-screen-v1.json`. Local raw reports:
`ai/runs/population-observed/heterogeneous-u9`; also retained by the coordinator
in HF. No game/search truncations or missing pairs in the 3,680 outcomes.

Economic win shares at 2–6 players: **58.44 / 60.42 / 64.06 / 76.06 / 73.18%**.
Against frozen A260 at 3 players: **45.52%**, versus the starting policy's 36.56%.
The paired whole-deal improvement is +8.96 percentage points, marginal exploratory
95% interval [+2.91, +15.00]. All four A260 rule subgroups improved in point
estimate; only Recharged/open's subgroup interval excludes zero. Report the
uncertainty and all regressions: 5p economic fell by 0.19 points, and three of
the four 2p rule subgroups fell in point estimate. The aggregate 2p gain is only
+1.09 points, interval [-5.31, +7.50], still below the 66.25% economic target.

This is the prescribed intermediate checkpoint from **one arm**, not evidence
yet for the advantage of heterogeneous tables over homogeneous/control training.
The primary update19 comparison and other arms remain pending. The A260 point
estimate clearing its target does not qualify this model. Keep the experiment
unchanged until the prescribed comparisons are available; prioritize the
remaining two-player weakness when choosing the next training change.

## Full training throughput — separate from candidate selection

Two three-update HF probes use the verified faster economics runtime, identical
H200 update79 initialization, retained heterogeneous opponents, seed 10021,
240 complete games/update, all player counts, four Torch threads and batch 512.
The actual trainer is unchanged. Gradients run on HF only. These runs do not
alter the three-arm population experiment and are not candidate selection.

- CPU-performance: `6aca0ec4fee2c90070185e12`, run
  `multiplayer-throughput-v1-cpu-performance`.
- H200: `6aca0ec5fee2c90070185e14`, run `multiplayer-throughput-v1-h200`.

Inspect exact live statuses in HF; `strong/full-throughput-status-v1.json` is
only a last observation. Source and frozen settings are in
`strong/full-throughput-source-v1.json` and
`strong/full-throughput-protocol-v1.json`. Source dataset revision:
`13aaf16eb754b17fd6a4efb4c84b14d248c2b82e`.
Each run uploads `metrics.json`, checkpoints and `throughput.json` under its run
prefix. Require actual completion, exact source/protocol/checkpoint provenance,
updates 0–2, 720 complete games, balanced counts, and zero search/game caps before
using its timing. Recompute aggregates from metrics. Benchmark checkpoints must
not be presented as qualified candidates.

**Both probes completed and were independently verified.** Artifact revision:
`1e826b625d324245d2b64a9f2979c70b2e637b3b`. Full results and hashes are in
`strong/full-throughput-results-v1.json`; raw files are in
`ai/runs/full-throughput-collected-v1`. The collector
`strong/collect-full-throughput.py REV OUTPUT` verified exact provenance,
720 complete games/platform, updates 0–2, balanced counts, no search/game caps,
and recomputed stored aggregates from the raw metrics. It also pinned and
rechecked the first three original-runtime updates.

Observed update times (seconds): optimized CPU 225.18 / 218.06 / 236.33;
optimized H200 160.30 / 162.79 / 161.96. Medians: original CPU 308.34,
optimized CPU **225.18**, optimized H200 **161.96**. The observed ratios are
1.37× for original/optimized CPU and **1.39×** for optimized CPU/H200.
Median optimizer portions: CPU 60.28 s, H200 8.45 s; rollout portions:
CPU 161.83 s, H200 153.50 s. H200's sampled whole-process GPU utilization was
2.35%; rollout work dominates total update time. This supports the optimized
H200 runtime for a future cohort, not adding multiple GPUs to one small learner.
Keep the existing three-arm strength experiment unchanged. Workload counts,
processor differences, and timing limitations are retained in the report.

Compare all three update times, rollout/optimization components and actual
search/sample workloads. Also retain first three original heterogeneous updates
as an observational reference. Their median is 308.34 s/update; their full
metrics are now pinned by the verified heterogeneous update9 checkpoint above.
The collector uses that exact revision/hash. GPU and CPU hosts differ, and async scheduling/CUDA
numerics can change trajectories. These are platform throughput measurements,
not a pure GPU causal estimate. Isolated kernel timings alone were insufficient
to justify a scale-up. The wrapper rejects incomplete/truncated/count-imbalanced
batches or missing search diagnostics; those four rejection checks passed using
mutations of the actual 720-game reference.

## Automatic checkpoint evaluation — inspect before any manual launch

Coordinator job: `6aca0d29095c578089310fca` (CPU-basic, 12-hour timeout),
verified RUNNING with all startup tests passed at 10:03 UTC on October 10.
Inspect its actual status and `strong/population-coordinator-status-v1.json`.
It owns **all six scheduled candidate screens** (three arms × updates 9 and 19).
Do not launch duplicate screens while it is active. It does not train, change
the population experiment, use final-test seeds, or promote any model.

Remote state and reports live in model repo `coyotte508/powergrid-ai-germany-v1`,
under `runs/population-coordinator-v1/`. Pin the current repository revision
before reading `state.json`, candidate folders, or `comparison-u9/u19.json`.
Child screen job IDs are recorded there. A waiting checkpoint has no strength
result yet. On any failure, inspect its exact validation/launch/collection log;
never restart a job solely because observation timed out. An unresolved launch
intent means its POST may have succeeded and requires reconciliation first.

Frozen coordinator source: `strong-source-population-coordinator-20261010-v1.tgz`,
training dataset revision `68ac8b3a6dbc9706f69206df84ac4e98c25b551e`.
Exact hashes are in `strong/population-coordinator-source-v1.json`. It packages
the original population runtime, all 2,553 raw export fixtures, and all six
verified parent reports. Eleven failure/recovery tests passed locally and again on HF at startup. Packaged parent reports were independently
rechecked: 3,680 complete paired games and matching artifact hashes.

The coordinator waits for matching metrics/latest checkpoint updates, recovers
missed update 9 from immutable history, requires full strict export parity,
then runs the prescribed six cells. It records launch intent before POST and
never automatically retries an ambiguous launch. Failed trainers or screens do
not cause it to abandon already-running peer screens. After all three arms for
an update are collected, it produces the paired comparisons. Terminal failures
give a nonzero exit; they are evidence to inspect, not successful qualification.

## Current training — inspect exact jobs before taking action

`strong/population-status-v1.json` has exact job IDs, latest observed progress,
and first complete update records. The three runs are
`multiplayer-population-v1-{control,homogeneous,heterogeneous}`. All remain on
their original immutable runtime. No restarts or source/hardware changes were
made to this cohort. All observed complete batches contain 240 games, 48 per
player count, and zero game or search truncations. Training outcomes are not
independent strength evidence. A polling timeout is not job termination.

`strong/population-training-protocol-v1.json` freezes: H200 update79 parent,
three retained neural opponents, 20 PPO updates × 240 complete games, 2–6
players, original/Recharged and open/sealed, seed 10021, initial-policy anchor,
periodic snapshots every 5 updates. Population arms have identical opponent
marginals, assigning either one family per table or independently per opposing
seat. Two-player assignments match. The third arm retains the prior mixture.
This is a single-seed pilot. Source/revision/hash are in
`strong/population-source-v1.json`; gradients run only on HF Jobs.

## Completed evidence and runtime work

- Parent benchmark: all 3,680 games verified at artifact revision
  `29f232e329f05ce6a93ea92006a271d9ea292147`, 40 complete paired deals/count,
  zero truncations. Economic win shares at 2–6 players:
  57.34 / 60.00 / 60.08 / 76.25 / 73.13%; A260 at 3 players: 36.56%.
  The two priority weaknesses remain. Full report and hashes:
  `strong/population-parent-screen-v1.json`; raw reports:
  `ai/runs/population-parent-screen-v1`. Parent export parity passed all 2,553
  positions. Collector rejects wrong hashes/deals/opponents and missing or
  truncated matches.
- Neural-continuation audit: all five jobs completed, 30,048 continuations,
  zero truncated, pinned revision `577ecd7d834c64741db9cda715bd1db3c3dddbd9`.
  Across 60 reused positions, 11 had disjoint A/B winner sets and 27 tied every
  action in discovery. Selection depends on continuation policy. No teacher
  promotion or new hard labels. See `strong/neural-continuation-summary-v1.json`
  and `strong/neural-continuation-status-2026-10-10.json`.
- Compute probe: both HF Jobs completed; manifests and exact paired batch hashes
  verified. `strong/compute-protocol-v1.json`, `strong/compute-results-v1.json`
  and `strong/compute-source-v1.json` preserve everything. Artifact revision:
  `f6a3a7e98ee55501190c1acc4371eb85494557df`. At 4 Torch threads, optimizer batch
  512 took 254.88 ms on CPU versus 28.70 ms on H200 (8.88×). Eight-row inference
  changed only 1.58 → 1.51 ms. These isolated timings exclude concurrent engine
  work and search stragglers; no end-to-end training speed claim. Benchmark
  gradient targets were synthetic timing inputs; no weights were saved.
- Simulation profile: fuel cost calculation was the largest sampled hotspot
  (~28% self time). `strong/economics.cjs` now caches costs only within a production
  planning call and hoists repeated price/holding reads. **Only future runtimes
  use this change.** Equality checks passed for 5,760 production plans, all
  20,705 decisions and terminal states in 40 complete games, every outcome in
  1,252 search continuations on 60 positions, and all state/action features in
  2,553 serving positions. Ten existing Node tests passed. Three alternating
  timing pairs gave median 9.62 → 5.98 seconds (1.61×) on this local search probe.
  See `strong/economics-optimization-v1.json` for exact scope and provenance.
  The first four-pair attempt ended with SIGTERM; its partial timings were
  excluded. The recorded three-pair run finished successfully.
- Faster future source is saved independently in HF; see
  `strong/economics-fast-source-v1.json`. Do not overwrite the active cohort's
  source reference with it. `strong/verify-economics-optimization.cjs` compares
  the two extracted runtimes. Encoded public compute fixtures are inside the
  immutable compute source; original serving fixtures remain locally in
  `ai/runs/multiplayer-serving-fixtures.jsonl` (SHA in the reports).

## Next actions

1. Inspect the three training jobs and verify further completed batches. The
   original control performs more search rollouts than the population arms;
   raw update times are not a clean hardware comparison. Keep all prescribed
   checkpoints and regressions, including runs slower than the others.
2. Let the coordinator preserve immutable model-repository revisions at updates
   9 and 19 before later uploads replace `latest`. Its underlying tools are
   `strong/prepare-population-screen.py ARM UPDATE REV OUTPUT` to validate
   training provenance and full 2,553-position checkpoint/export parity, then
   launch its `screen-plan.json`. Internal `best` is not the scheduled candidate.
   If needed, recover update 9 from immutable repository history rather than
   substituting a later checkpoint.
3. Once each six-cell screen is complete, pin its artifact revision and run
   `strong/collect-population-screen.py OUTPUT REV`. Fresh development prefix:
   `multiplayer-population-screen-v1-{players}p`, offsets 0–39, every seat and all
   four rule combinations. Then `strong/compare-population-screens.py` compares
   all three arms and the parent at each scheduled update. It resamples whole
   deals, reports every rule/count cell, and does not pool away weaknesses.
   Sanity checks passed: identical actual reports give zero difference; missing
   pairs fail; 400 correlated synthetic rows retain only 4 independent deals.
4. If strength screens justify further training, consider the verified faster
   economics runtime and H200, with a full training-throughput check and a second
   training seed. Current source and hardware stay fixed. Only then proceed to
   stronger independent search/mixed tables and the unchanged final strength
   protocol, followed by export/legality/latency/package checks on the 8840U.
5. Training still freezes source-v36; independent screens use source-v32.
   Verify newer production-engine compatibility before any deployment. Public
   money is allowed; hidden deck, sealed bid values, RNG seed and queued plans
   stay excluded. Do not present value-head output as calibrated analysis.

The historical October 4 handoff follows; its paused status and old job snapshots
are historical, not the current state.

---

# Power Grid AI — saved research handoff, 4 October 2026

**Start here when resuming. Research is paused at the user's request. No model
has passed the complete strength gate; nothing is routed into production bot
moves. Reserved final-test seeds remain unused.** This document supersedes the
outdated “running / pending / active” statements in the earlier READMEs and
`strong/multiplayer-progress.json`. Those files remain useful historical notes.

This handoff was reconstructed from the checked-in experiment ledger, local
artifacts and read-only Hugging Face queries. The last five diagnostic jobs are
now COMPLETED. `hf jobs ps --format json` returned `[]` on 4 October. No training
or evaluation jobs were launched for this handoff.

## Objective and information contract

Build a **really strong** Power Grid bot, not just one that beats the default
engine bot. Train on HF Jobs; serve platform requests on the AMD 8840U. Browser
ONNX inference is a possible later use, not a completed integration. Later
analysis of players' decisions/win probabilities requires separately validated
and calibrated values; the current value head is not ready for that claim.

The user explicitly allows all players' money to be visible to the bot. Include
opponents' cities, plants, fuel, turn order and players still to act; resource
replenishment by step, available stock and prices; region/island presence and
remaining building slots. Building more cities can improve income but worsen
turn order, so optimize terminal winning, not an unconditional city reward.
Never expose actual hidden deck order, RNG seed, submitted sealed bids or queued
plans. Search samples public-consistent worlds rather than reading these secrets.

Validated training scope is **Germany, automatic setup, 2–6 players, original
and Recharged rules, open and sealed auctions**. Early policies were Germany/3p
only. Generic topology/territory export and UK/Ireland feature tests exist, but
there is no demonstrated trained strength on other maps. Do not advertise
multi-map support based on feature encoding alone.

## Where everything lives

| Material                                             | Location                                                                                                                         |
| ---------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| Canonical source                                     | [boardgamers/powergrid](https://github.com/boardgamers/powergrid), `ai/` and `ai/strong/`                                        |
| Complete experiment ledger                           | [strong/experiments.json](strong/experiments.json): source/model revisions, job IDs, reports, counterexamples and decisions      |
| Strong-policy background                             | [strong/README.md](strong/README.md), historical and partly stale                                                                |
| Baseline background                                  | [README.md](README.md)                                                                                                           |
| Private checkpoints, ONNX, reports, serving archives | [coyotte508/powergrid-ai-germany-v1](https://huggingface.co/coyotte508/powergrid-ai-germany-v1) (name predates multiplayer work) |
| Private immutable source bundles and data            | [coyotte508/powergrid-ai-training-v1](https://huggingface.co/datasets/coyotte508/powergrid-ai-training-v1)                       |
| Multiplayer final gate                               | [strong/final-protocol-multiplayer.json](strong/final-protocol-multiplayer.json)                                                 |
| Earlier 3p gate                                      | [strong/final-protocol.json](strong/final-protocol.json)                                                                         |
| Latest admission comparison protocol                 | [strong/league-admission-protocol-v1.json](strong/league-admission-protocol-v1.json)                                             |
| Collected diagnostic summary                         | [strong/handoff/teacher-reliability-v2-summary.json](strong/handoff/teacher-reliability-v2-summary.json)                         |
| Sanitized resume manifest                            | [strong/handoff/status-2026-10-04.json](strong/handoff/status-2026-10-04.json)                                                   |

Local canonical checkout: `/home/eliheros/code/powergrid`. Source before this
handoff was `face347f258a057c2ed3fb4e4606fce2003ab4c1`; AI research was integrated
by `1e73e53`. Old research checkout:
`/home/eliheros/Documents/Codex/2026-09-26/je-x20-2/work/powergrid-ai`, HEAD
`4bc256a8b126c0da977b9a728df9356e201ed815`. Its ignored `ai/runs/` contains large
local artifacts; do not assume those are present in a fresh clone. The previously
untracked `summarize-search-budgets.py` has been rescued into canonical source.

The research-only 8840U installation is `~/powergrid-ai-strong` on SSH alias
`minipc` (fallback `minipc-wg`). SSH configuration was updated previously. No
production routing was installed. Recheck host/runtime state when resuming.
The authenticated HF CLI is `/home/eliheros/.local/bin/hf`; its Python is
`/home/eliheros/.hf-cli/venv/bin/python`. Use cached authentication; never put
tokens or raw historical game data in Git.

## What was implemented and learned

1. **Baseline and historical-data audit.** Of 4,007 BGS records, 3,978 were ended;
   66 candidate Germany/3p games yielded 33 exact replays (7 sealed), then 32
   usable games / 11,366 decisions after excluding a colour-draft game. Failed,
   interrupted and incompatible replays were excluded explicitly. A 600-game
   synthetic + human baseline ran BC and PPO. It beat a weak heuristic but scored
   0% against the default bot: not useful evidence of strength.
2. **Corrected opponent and observations.** A heuristic read nonexistent
   `BuyResource.data.price`, producing NaN and suppressing fuel buying; stock-based
   resource pricing was also wrong. The corrected heuristic scored 85.1% against
   the default bot over 960 games. Default-bot wins are only a sanity check.
3. **Schema 3 strong policies.** 738 state / 96 action features; economic prior
   plus learned residual action scores, complete-episode PPO, frozen opponents,
   public-information search, CPU arenas and ONNX serving. Preserve frozen
   revision `3.0`; `3.1-uranium39` fixes persistent replenishment after plant 39
   has been purchased (even if later discarded). Unknown feature revisions fail.
4. **3p training/search/distillation.** A/B leagues completed 300 updates;
   high-exploration C/D were stopped after regression. Search-teacher datasets
   progressed from 512 games / 25,268 strategic positions to corrected v3's
   2,048 complete games / 247,104 decisions. More distillation did not reliably
   improve independent play. Corrected A260 refinement update 40 and A299 were
   useful references, but sealed-auction weaknesses remained.
5. **3p specialist.** Corrected A40 for three rule combinations and corrected-input
   B160 + 48-sample search for Recharged/sealed: 76.7% versus economic, 94.6%
   versus legacy, 46.7% versus frozen A260, each 480 development matches. SHA:
   `b4cae14eb6e1aff72b16e5056983b2a57ad42984f4a27cf99dd70bb63e86be32`.
   This is a research candidate, not a qualified universal bot. See ledger
   `specialist_candidate`, `specialists_remaining_results` and the other screens.
6. **Schema 4 multiplayer.** Revision `4.0-multiplayer`: 1,149 state / 98 action
   features, six ordered player slots (74 features each), inactive value slots
   masked to zero. `multiplayer_ordered` has 983,682 parameters and supersedes the
   earlier pooled prototype. Tested encoding and legal responses at every count;
   2,553 fixtures cover 2–6p. Initial teacher: 1,200 games / 142,804 positions /
   4,746,464 search rollouts with no truncations. Subsequent distillation, PPO,
   asynchronous environment workers, stronger-opponent replay and league
   admission comparisons are all recorded in the ledger.
7. **Later PPO.** H200 refinement and geographic-opponent asynchronous training
   each completed 80 updates / 19,200 games. These improved some development
   matchups, especially 5–6p, but did not qualify. A stronger teacher replay
   experiment did not translate prediction agreement into better independent
   play. Do not simply extend the same recipe or assume harder labels help.

## Latest completed strength screens

All numbers below are percentage win credit, including fractional ties, on
**reused development screening deals**, not untouched final tests. Each row has
3,680 completed matches: economic at 2/3/4/5/6 players (320/480/640/800/960 games)
plus frozen A260 at 3p (480). Full rule-level breakdowns and deal-cluster intervals
are in each corresponding ledger entry. Aggregate rates cannot override a weak
rule cell. Search is off for these candidates.

| Candidate                           | Econ 2p |    3p |    4p |    5p |    6p | Frozen A260 3p |
| ----------------------------------- | ------: | ----: | ----: | ----: | ----: | -------------: |
| H200 update 79                      |   63.44 | 60.83 | 59.69 | 77.69 | 73.28 |          33.54 |
| Geographic league update 79         |   52.34 | 59.90 | 54.53 | 71.44 | 65.99 |          33.33 |
| Admission “best” update 19          |   52.81 | 56.67 | 57.66 | 79.19 | 74.58 |          39.58 |
| Admission periodic-anchor update 19 |   60.31 | 57.40 | 61.72 | 74.94 | 70.16 |          36.04 |

None passes the 66.25% economic/2p and 40% A260/3p floors together. Geographic
update 79 also fails the strict export tolerance on one logit (although all
2,553 selected actions agree). Its training had four capped search rollouts;
the screening games/rollouts above were untruncated. Other three exports pass
their recorded parity checks. “Internal best” was not a reliable universal
external-strength selector; admission comparison had one training seed.

Pinned checkpoints in the private model repo:

| Candidate               | HF revision                                | File                                                               | SHA256                                                             |
| ----------------------- | ------------------------------------------ | ------------------------------------------------------------------ | ------------------------------------------------------------------ |
| H200 u79                | `0aeacd5b8e36ece36ba06a77ddfd7b86110d4f3a` | `runs/multiplayer-refine-hard-v1/latest.onnx`                      | `2f1dd42625ea86404155e63124e55d95d07016027a0ceda4e08164357b554927` |
| Geographic u79          | `035345f5f05bbbb55af5e0f4884d07f9087b1e32` | `runs/multiplayer-refine-geoleague-async-v1/latest.onnx`           | `35deffdacefdc3d3638417b1590432b84a86f3fb302958e273f5eeea9ad7ce34` |
| Admission best u19      | `efdb82f2712b8c6648100d7ad99b6941102f7001` | `runs/multiplayer-league-admission-v1-best/latest.onnx`            | `691a91ae58d5946a396fe595ffba2f866b5bfba6533ec504da9e6a134c07750e` |
| Periodic-anchor u19     | `efdb82f2712b8c6648100d7ad99b6941102f7001` | `runs/multiplayer-league-admission-v1-periodic-anchor/latest.onnx` | `08ad0042e548e9b871e9f4178626d405637fb55f3f42b0d580b2bd6979ac7f67` |
| Frozen 3p A260 opponent | `b38515c29e57826de05b55b645c29591e4a886bf` | `runs/strong-league-v2-a/best.onnx`                                | `9b46db558669a0c3085412fe2544359eda55ed9f092dffb67bead6af3c409ecd` |

Earlier H200 update 29 (revision
`fbdf2bf24c968bff99ab2d7d9ff9a7d97047db2b`, same hard-refinement model path,
SHA `d3d2ee88a0940f079a4b38879c8154dbab55951abc7b295a7db17bdf22e52c5f`)
remains a useful retained comparison; do not replace it just because later
updates exist. Its raw policy transferred gains over the distillation warm start
against independent `search_geo`, but 2–4p rates missed floors, with sealed-rule
weaknesses at 5–6p. Single-deal auction counterfactuals did not support the simple
explanation “pass or buy a cheaper plant”; no tested round-4 nomination won the
second investigated losing deal. Those are local diagnoses, not causal proof
about the whole policy.

## Diagnostics completed after the pause

Jobs `teacher-reliability-v2-{2..6}p`, CPU-performance, submitted 1 October:

| Players | Completed job                                                                               |
| ------- | ------------------------------------------------------------------------------------------- |
| 2       | [6abe1df0fbc85ba682360bd8](https://huggingface.co/jobs/coyotte508/6abe1df0fbc85ba682360bd8) |
| 3       | [6abe1df1404719ba3761721e](https://huggingface.co/jobs/coyotte508/6abe1df1404719ba3761721e) |
| 4       | [6abe1df2fbc85ba682360bda](https://huggingface.co/jobs/coyotte508/6abe1df2fbc85ba682360bda) |
| 5       | [6abe1df2fbc85ba682360bdc](https://huggingface.co/jobs/coyotte508/6abe1df2fbc85ba682360bdc) |
| 6       | [6abe1df3fbc85ba682360be0](https://huggingface.co/jobs/coyotte508/6abe1df3fbc85ba682360be0) |

Immutable source: dataset revision `d07e072058ee877112d609280980fc806ee8ce28`,
`strong-source-v36.tgz`, SHA256
`6c4170317a74a5148c2a576ad93d1170441e0d8e791a7e6c23197c51dad69109`.
Fixtures: 60 reused development positions, 2–6p × four rules × nomination/bid/build.
Fixture SHA `855b34ad7f07665dfcb012a673147f0780820a9e7560fda268a9a39478c60ff4`.

Downloaded model-repo revision `daef30ae69d6a96f21e46abd8a30909689682364`,
`runs/teacher-reliability-v1/` and `runs/teacher-reliability-v2/`. The summary
script verified every shard hash, all 360 searches / **721,152 rollouts**, zero
truncations, 2,400-step horizon, exact nested 48-sample prefixes and shared public
scenarios across continuation policies. It compares independent batches A/B and
budgets 48/96/192/384 under mixed/economic/heuristic continuations.

At 384 mixed samples, selected action agreed on 47/60 positions (v1: 39/60 at
48). Same unique winner rose from 19/60 to 29/60; disjoint winning sets fell from
16/60 to 10/60, but the intermediate budgets were not monotonic. Fourteen positions
had opposite economic/heuristic preferences in confirmation batch B for actions
selected in batch A. **Descriptive only:** this small reused fixture set establishes
neither playing strength nor which continuation policy is realistic. Larger
budgets alone do not resolve the teacher-policy mismatch. No gradients were run.

Reproduce this local audit without submitting jobs (from repo root):

```sh
hf download coyotte508/powergrid-ai-germany-v1 \
  --revision daef30ae69d6a96f21e46abd8a30909689682364 \
  --include 'runs/teacher-reliability-v1/*' 'runs/teacher-reliability-v2/*' \
  --local-dir ai/runs/resume-snapshot
python3 ai/strong/summarize-search-budgets.py \
  ai/runs/resume-snapshot/runs/teacher-reliability-v2 \
  ai/runs/resume-snapshot/runs/teacher-reliability-v1/results.jsonl \
  --output ai/runs/resume-snapshot/summary.json
```

## Runtime, implementation and resumption order

The JavaScript engine is still authoritative. No Rust rewrite was completed.
Profiling found repeated economics/territory calculations to be a bigger cost;
hoisting them out of action loops sped feature generation 2.2× with identical
outputs over 1,786 positions. Batching and asynchronous environment workers were
added. A tested cache regressed runtime and was removed. Low GPU utilization by
itself is not a reason to allocate more GPUs to CPU-bound simulation.

Actual 8840U measurements: schema-3 raw full-worker p95 around 3.5–3.8 ms;
multiplayer prototype p95 4.69 ms over 2,553 legal requests. Optional search is
much slower: roughly 0.7 s at 16 samples on a small fixture subset, 2–3 s at 48.
The specialist's 33 searched decisions had p95 2.36 s, max 2.57 s, no capped
rollouts. These measurements belong to their exact archived candidates/configs;
they are not latency guarantees for all later policies or browsers.

When the user explicitly resumes:

1. Read this file and relevant ledger entries; inspect HF jobs before launching
   anything, to avoid duplicates. Fetch exact HF revisions and verify hashes.
   Use immutable source bundles to reproduce old experiments; current engine
   code includes later UI/game fixes and is not automatically equivalent.
2. Start from the saved teacher-reliability summary. Design an explicit comparison
   of continuation quality/opponent coverage, especially sealed auctions, and
   evaluate uncertain targets before another large hard-label distillation run.
   More samples helped repeatability but did not make all labels reliable.
3. Retain H200 u29/u49/u79, specialist and frozen opponents as comparisons. Use
   paired development deals, every player count and rule cell, diverse opponents,
   and report all actual-game/search truncations. Search horizon must explicitly
   be 2,400 for the newer multiplayer runtime; older 1,200-step results remain
   separate. `six_player_search_horizon_investigation` documents the rare cap.
4. Re-run meaningful information-boundary, encoder and export checks when code
   changes. Key entry points: `test.cjs`, `test-v4.cjs`, `test-search-samples.cjs`,
   `test-search-horizon.cjs`, Python tests, `check-export.py`,
   `benchmark-serving.py`, `package-serving.py`, `verify-package.py`. Check each
   script's CLI and candidate feature contract before use. Standalone archives
   expose `serve.py`, which verifies the frozen model hash and configuration.
5. Freeze a candidate only after development evidence warrants it. The multiplayer
   gate requires each count/rule interval lower bound above 1/N, complete paired
   deals, no illegal moves, explicit rollout counters, strict ONNX parity, all
   2,553 legal serving requests and actual 8840U measurements. Minimum economic
   rates for 2–6p are 66.25/55/49.375/46/43.75%; default bot is 90% at every count;
   other opponent thresholds are in the protocol. Do not lower gates after results.
6. Only then use reserved prefix `strong-multiplayer-final-reserved-v1` under a
   frozen multiplayer evaluator. The existing `launch-final.py` / `verify-final.py`
   were built for the earlier 3p protocol: inspect/adapt their count support before
   invoking, rather than assuming the new protocol JSON is sufficient. Failed
   qualification stays failed; a new candidate requires new final seeds.
7. After qualification, integrate bot requests, then separately investigate
   browser ONNX and calibrated per-round analysis. Expand maps with per-map
   training/evaluation; UK/Ireland geography is particularly important.

Historical BGS data remains useful for legal-action replay, realistic positions,
imitation warm starts and diagnostics. It is small, selected and not evidence
that its players are expert. Keep whole games separated across splits and never
substitute training fit for independent playing-strength tests.
