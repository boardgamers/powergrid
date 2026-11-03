# Multi-map Power Grid AI — v1 bootstrap

See `runs.json` for the active HF job, immutable source/data pins and evidence.
Completion/error watchers wake the owning session; no user ping is required.

The first job (`6ae8bd6cc78863f9c630be9c`) archived all 1,760 complete games,
then correctly refused to fit because 15 opening observations also appeared in
validation. The recovery excludes those **training** rows by public-feature
hash (61,425 retained), without changing any held-out row or examining labels
for selection. `bootstrap-data-v1.json` pins the reusable archives and generator
digest. The corrected run restores them with `--reuse-data`, rather than
regenerating deals or weakening the no-overlap guarantee.

Start here for the new research. The Germany reference and its historical
experiments remain frozen in `ai/strong/`; do not restart their coordinators.
The unrelated/deleted HF experiments are not inputs. No BGS deployment is made.

## Bootstrap result (completed)

The corrected HF job completed all 40 epochs and all 1,920 development games,
with **zero errors or capped games**. All saved artifacts and plan coverage were
independently checked; eight sampled games replayed exactly. See
`bootstrap-results-v1.json` for immutable pins, per-map/count results and caveats.

The standalone clone is **rejected for playing strength**: macro-cell win credit
was about 8.8%, versus 47.2% for its heuristic teacher. In-map action agreement
was 79.4% overall, but only 64.8% in auctions and 68.8% for resources. Completion
and imitation metrics are not strength. Preserve the graph representation as a
warm-start, diagnose phases, and improve from the stronger heuristic rather
than launching more fixed-data imitation epochs blindly.

## Scope and experiment

-   Current release engine **2.0.22**, merged from `origin/master` into
    `moon/ai-multimap` (based on `ai/germany-baseline`).
-   Train on **Germany, USA, France, UK & Ireland**. Validate on fresh deals of
    those maps. **Italy and Benelux** are transfer-only: their labels and metrics
    never drive gradients, hyperparameters or checkpoint selection.
-   2–6 players, Original/Recharged, open/sealed auctions, public money, automatic
    setup, standard deck. Other options/maps fail closed, rather than silently
    using the wrong rule representation.
-   `protocol.json` freezes split namespaces before results. 1,280 train games,
    320 validation games and 160 transfer games; up to 12 sampled decisions per
    phase per game. All seats in a deal stay in one split. Training observations
    matching held-out features are excluded deterministically, independent of
    labels; then feature-duplicate and deal-overlap audits must pass. Previous Germany/final games are never labels.
-   Initial HF fit: width 64, seed 508, 40 epochs, AdamW, policy cross-entropy plus
    0.1 terminal-credit value loss. Select by macro-cell in-map validation loss.
    This is a **behavior-cloning bootstrap**, not yet policy improvement or proof
    of strong play. The value is not a calibrated player win probability.
-   Development: two NEW deals per map/count/variant/auction cell, every seat,
    both model and teacher versus identical economic opponents: **1,920 full
    games / 960 paired seat comparisons**. Retain all errors/caps at zero credit
    and report each cell. Small deal counts mean no reliable strength
    qualification. Final seeds are reserved and not callable by this tooling.

## Representation and rules

`features.cjs` emits public tensors (273 global, 80 per player, 36 per city,
34 per action). There are **no city identities, map embeddings or teacher
scores in model input**. Every legal bid is retained; candidate padding is
masked. Cities have ownership, slots, build cost/availability, nuclear bans,
region/island holdings and explicit topology. Four graph relations represent
weighted links, unweighted links, same-region and same-island membership.
The shared graph layers are permutation-equivariant, with pooled city/player
context and a gathered city embedding for build actions.

Rules represented include refill by all three Steps, market prices and supply,
public money/fuel/plants/order, discount nomination costs, two-player plant
limits, Germany/Italy uranium cutoff, USA Recharged coal supply purchases,
Benelux market rule, UK island surcharge/access and regional nuclear restrictions.
Engine-generated legal actions remain authoritative. No hidden deck order,
random seed, submitted sealed bid, queued choice or private log enters tensors.

The bootstrap teacher reuses public economic calculations with versioned
corrections for plant limits and discount nomination. UK entry cities must be
completely empty: the teacher secures a second network early, before other
players make access permanently impossible. This was caught by a full-game
smoke test, not papered over by discarding capped games. The teacher is still a
heuristic, particularly for fuel foresight; imitation is only a starting point.

### Engine map inventory / next expansion

The engine has 24 maps. Six are admitted to this pilot; the others require
rule-feature/teacher tests before entering training:

| Maps                                              | Main additional audit                                                      |
| ------------------------------------------------- | -------------------------------------------------------------------------- |
| Brazil, Quebec                                    | Guaranteed/retained plants, market lifecycle                               |
| Spain & Portugal, Central Europe, Northern Europe | Regional nuclear restrictions, Wien discount, regional plant substitutions |
| India                                             | Resource-purchase limits, outages, step-dependent market access            |
| China, Russia, Middle East                        | Special auction/deck/market/Step lifecycle                                 |
| Baden-Württemberg                                 | Phase order, transregional cities/costs                                    |
| Europe, North America                             | Regional plant substitutions and market sizes                              |
| Korea                                             | Two resource markets and side commitment                                   |
| South Africa                                      | Coal storage, foreign single-occupancy cities                              |
| Australia                                         | Uranium mines, separate market, disconnected networks                      |
| Bremen                                            | Directed per-district entry costs and special deck                         |
| Manhattan                                         | Blocked single-occupancy spaces, recycle/depletion lifecycle               |
| Japan                                             | Starting cities, optional second network, custom slots, first-round limits |

The v1 schema must not be advertised as supporting those maps merely because
its graph shape could accept them.

## Running / recovery

```sh
pnpm install --frozen-lockfile
pnpm --filter powergrid-engine build
uv venv ai/.venv
uv pip install --python ai/.venv/bin/python \
  --extra-index-url https://download.pytorch.org/whl/cpu \
  -r ai/multimap/requirements-cpu.txt
node --test ai/multimap/test.cjs
PYTHONPATH=ai/multimap ai/.venv/bin/python -B -m unittest discover \
  -s ai/multimap -p 'test_*.py'
```

`launch.py` requires committed, clean source. It packages the compiled current
engine, its pinned production dependencies, source manifest and exact tested
Node binary. SHA-verified source is downloaded from an immutable dataset
revision inside a digest-pinned Python container. Credentials only enter Jobs
through its secret mechanism; never print or serialize full JobInfo objects.

```sh
PYTHONPATH=ai/multimap ai/.venv/bin/python -B ai/multimap/launch.py \
  --run-id multimap-bootstrap-20261102-v1 \
  --output ai/runs/multimap-bootstrap-20261102-v1
```

-   Source/data: private `coyotte508/powergrid-ai-training-v1`, under
    `multimap/<run-id>/`.
-   Checkpoints/results: private `coyotte508/powergrid-ai-multimap-v1`, under
    `runs/<run-id>/`. Germany's model repository is read-only for this work.
-   Data is archived before training. `last.pt` includes optimizer and generator
    state; `best.pt` is the selected checkpoint. Model artifacts are uploaded at
    epoch 0 and every five epochs, then every 80 development games. Data and
    evaluation are resumable from their validated files/plan; restore the run
    directory from pinned receipts before recovery. Do not reuse an existing run
    ID to overwrite source. CLI waiting uses `hf jobs wait <id>` in a detached
    shell with `notify: true`, so failure/completion wakes the owning session.
-   Artifacts have SHA-256 manifests and immutable revision receipts. A completed
    workflow is **not** a promoted or deployed policy. Inspect failures and full
    games before further training. Wall time is hard-bounded to 3 hours.

## Storage budget (user requirement)

The user permits roughly **10 GB or another reasonable bounded amount**, not
hundreds of GB of runaway accumulation. Keep useful reusable artifacts locally;
do not delete/redownload them just to satisfy an unnecessarily tiny working cap.
The launcher requires its working cache under `ai/runs/multimap-*`, currently
warns by refusing new launches above **8 GB** or with less than 2 GiB free, and
removes duplicate source staging after immutable HF upload. This leaves headroom
for dependencies/caches; the guard can be deliberately revised for justified work.
Older frozen bootstrap data workers retain their **512 MiB** collection guard.
The exact-reference cache has its own sufficient 512 MiB bound, and the recovered
451 MB artifact is retained for reuse. New PPO trajectories remain RAM-only.

All 1,760 games are already archived privately on HF (about 48 MB compressed).
The recovery reuses those pinned archives. Local expanded data and disposable
smoke weights were removed after verification (under 1 MB of run files at the
bootstrap cleanup). Retain only compact results after subsequent checks. The
Python environment is about 955 MB; HF's pinned data cache is about 46 MB plus
small checkpoint downloads. Preserve compact receipts/audits, not duplicate bulk data. Future large
iterations must stream/shard to HF buckets or remote storage; do not expand
hundreds of GB locally. If HF storage limits become an issue, discuss public
visibility or alternative storage with the user rather than changing visibility
silently. Never prune unrelated runs or shared caches wholesale.

## Phase diagnostic and residual PPO pilot

`phase-diagnostic-results-v1.json` pins the 384-game 8840U diagnostic. It used
four-player games on the four training maps only, 16 independent deals with
all four focal seats and six phase-substitution policies. Win credit: teacher
53.1%, full clone 1.6%, Auction-only clone 18.8%, Resources-only clone 3.1%,
Building-only clone 53.1%, Bureaucracy-only clone 43.8%. This small diagnostic
is not a qualification test. Tensor conversion + forward for the full clone
was 0.95 ms median / 1.44 ms p95 with four concurrent single-thread workers;
it excludes JS features, IPC and platform latency. Remote source/weights were
removed after private HF archival; the reusable Python environment remains.

The next experiment is frozen in `ppo-protocol-v1.json`:

-   Use the graph clone only as a feature warm-start. Zero the final action head,
    then add a bounded (`8*tanh(raw/8)`) learned residual to an explicit,
    versioned heuristic prior. This is a **new policy schema**, not a claim
    that bootstrap features secretly contained teacher scores.
-   Learn Auction and Building only. Keep resources, powering and forced moves
    under the deterministic geographic teacher. Keep every legal bid/action.
    Zero residual must match full teacher games exactly across all 120 cells.
-   Train on actual terminal win credit with PPO, gamma=1 Monte Carlo returns,
    a sigmoid value baseline and equal total loss weight per game. Clip ratio
    0.2, prior KL regularization 0.01, entropy coefficient 0.001, target KL 0.05,
    AdamW learning rate 1e-4, four optimization passes. No invented cap rewards.
-   16 updates × 80 fresh training games = **1,280 games**. Balance all four maps,
    player counts, variants and auction modes; rotate the focal seat. Rotate
    economic/geographic/rush opponents by game. No neural self-play yet.
-   Select on new **in-map** full games at updates 0/4/8/12/16 (320 games each).
    Verify initial teacher parity with another 320 games. Zero residual is
    eligible; earliest ties win. Reject candidates losing >0.1 win credit on
    any training map. Selection consumes no confirmation or transfer outcomes.
-   After selection, run 960 selected + 960 teacher games on fresh confirmation
    deals across six maps, all seats/counts/rules. Including selection/parity,
    this is **3,840 evaluation games**. Reserved final seeds remain untouched.
    Italy/Benelux remain excluded from optimizer updates and selection, but
    their earlier bootstrap results were already viewed: this is exploratory
    transfer evidence, not a new blind final test.

```sh
node --test ai/multimap/test.cjs ai/multimap/test_rl.cjs
PYTHONPATH=ai/multimap ai/.venv/bin/python -B -m unittest discover -s ai/multimap -p 'test_*.py'
# --smoke runs two tiny disposable updates; it does not change the HF protocol.
PYTHONPATH=ai/multimap ai/.venv/bin/python -B ai/multimap/ppo.py \
  --checkpoint /path/to/pinned/bootstrap/best.pt --output ai/runs/multimap-ppo-smoke --smoke
PYTHONPATH=ai/multimap ai/.venv/bin/python -B ai/multimap/launch.py \
  --workflow ppo --run-id multimap-ppo-20261102-v1 \
  --output ai/runs/multimap-ppo-20261102-v1
```

Trajectories exist only in the current RAM window (100,000-row cap), never on
disk. Save initial/best/latest checkpoints and compact outcomes; the HF worker
refuses artifacts exceeding 128 MiB. Upload an immutable snapshot every update.
`last.pt` is the recovery transaction: it includes the optimizer, RNG, selection
state and the exact committed best-artifact bytes, allowing recovery even if an
interruption replaced `best.pt` before committing `last.pt`. Tests interrupt with
a populated optimizer and an uncommitted best, then verify bit-exact weights.
To recover, use a **new run ID** and add `--resume-run <old-id> --resume-revision <immutable-model-commit>`; the worker verifies every restored
SHA and rejects algorithm/config/source mismatches. No bulk dataset restoration
is needed. Both workflows retain the three-hour HF limit and completion callback.

This remains a research pilot, with an unchanged-heuristic fallback, not a
production promotion. If it does improve, confirmation and stronger-opponent
screens still precede qualification. Germany frozen-1 must be compared using its
original runtime adapter, not raw weights with these features. Its verified
ONNX SHA is `55331f43379e8fe89025d93b1a7a48c88e0ea39b4ebd3a7ef8240d4b62753530`.

## PPO v1 result and frozen follow-up

`audit_ppo.py` independently verified all 32 saved artifacts (about 7.6 MB),
4,800 persisted outcomes, all plans/split namespaces and checkpoint selection,
plus 12 deterministic replays spanning all six maps and player counts. The
additional 320 initial teacher-parity games were asserted equal during the run
but are not separately persisted. See `ppo-results-v1.json` for full evidence.

Update **8** was selected. Fresh confirmation macro-cell win credit was
**55.16% vs 51.01%** for the geographic teacher against economic opponents,
a **+4.16 percentage-point** difference. A stratified paired deal-cluster
bootstrap gives an exploratory 95% interval of **+1.48 to +6.78 pp**. With only
two independent deals per configuration this interval can be optimistic;
it is not a qualification bound. There are 240 independent confirmation deals,
not 960 independent trials. No multiple-comparison adjustment was applied.

| Map          | Difference vs teacher, pp |
| ------------ | ------------------------: |
| Germany      |                     +5.54 |
| USA          |                     +6.17 |
| France       |                    +11.90 |
| UK & Ireland |                     -4.08 |
| Italy        |                     -3.50 |
| Benelux      |                     +8.92 |

Player counts matter too: differences for 2/3/4/5/6 players were respectively
**-5.21 / -4.17 / +9.11 / +7.50 / +13.54 pp**. Aggregate improvement must not hide
these regressions. Transfer-map improvement is inconclusive at this sample size.
This is promising pilot evidence, not human-level strength or a production bot.

Before changing the learning recipe or scaling training, the next fixed checks are:

1. **Two independent cold replications**, `--replica 1` and `--replica 2`.
   Only the Python RNG seed and whole-game namespaces change; original graph
   warm-start, zero residual initialization, 16x80 training budget, opponent
   mixture, optimizer and selection rules remain identical. Selection and
   confirmation deals are disjoint across replicas and from v1. Report each
   result, including failures or baseline fallback; do not present only the best
   seed. Each replica has 1,280 train and 3,840 evaluation games.
2. **Frozen PPO-8 opponent study**, specified by `opponent-study-v1.json`:
   11,520 games, 5,760 paired seat comparisons, 1,440 independent deal/opponent
   seeds. Selected policy and teacher each face economic/geographic/rush
   populations over six maps and all counts/rules. Four fresh deals per
   configuration/opponent. This is an evaluation-only robustness screen;
   it neither trains nor selects another checkpoint. Report every map/count/style.

```sh
PYTHONPATH=ai/multimap ai/.venv/bin/python -B ai/multimap/launch.py \
  --workflow ppo --replica 1 --run-id multimap-ppo-20261102-replica-1 \
  --output ai/runs/multimap-ppo-20261102-replica-1
# Repeat with replica 2 and its own run/output ID.
PYTHONPATH=ai/multimap ai/.venv/bin/python -B ai/multimap/launch.py \
  --workflow opponents --run-id multimap-ppo8-opponents-20261102-v1 \
  --output ai/runs/multimap-ppo8-opponents-20261102-v1
```

The study writes compact outcomes only, keeps failures at zero credit with an
explicit error flag, and fails its screen if any game fails. It uploads every
240 outcomes, has a 128 MiB artifact budget and supports immutable-revision
resume via the same `--resume-run/--resume-revision` flags. Plans and serving
code are bound; an interrupted final JSONL line is replayed rather than trusted.
Replicas additionally require the matching `--replica` on recovery. Strict
source guards remain: use the original archived source to recover older runs,
not a newer training implementation with its checks disabled.

A Germany neural-reference match is still pending. It must use the retained
**public-runtime filter arm**, not just the ONNX file: feature revision
4.3-strategic-correction, original bid-thinned candidate menu, built-in correction
heads, and the external strict endgame-loss filter. The archived current-engine
runtime also includes scope and simultaneous-sealed-pending-set fixes absent
from the unpatched checked-in originals. Its prior audit used engine 2.0.19;
a 2.0.22 compatibility screen is required. See
`ai/strong/current-auction-grid-source-v1.json`,
`ai/strong/current-engine-auction-prepared-v2.json` and
`ai/strong/public_policy_runtime_v1.py`. Keep this reference in a separate
Python environment (its ONNX/NumPy pins differ), send only public states, and
validate returned atomic moves against the authoritative full legal menu.
Reference indices are not multi-map action indices; all its phases must run
through its own policy, not our resource/powering teacher.

## Completed replication and opponent-study audits

All three follow-up jobs completed with no game failures. `audit_replicas.py`
verified all 32 artifacts per replica, exact source/engine/protocol identities,
4,800 persisted outcomes per run, selection/optimizer/embedded-best state, and
12 exact selected-policy replays per replica. All nine train/selection/confirmation
seed sets across the original and replicas are disjoint. See `replica-results-v1.json`.

| Run       | Selected update | Selected credit | Teacher credit | Difference, pp |
| --------- | --------------: | --------------: | -------------: | -------------: |
| Original  |               8 |          55.16% |         51.01% |          +4.16 |
| Replica 1 |              16 |          57.54% |         50.69% |          +6.85 |
| Replica 2 |              12 |          58.13% |         49.78% |          +8.35 |

These are **three different policies on different confirmation deals**, not one
pooled qualified model. Replica 1 still regresses descriptively on USA (-0.54 pp)
and two-player games (-1.56 pp); replica 2 is positive in every map/count group.
No best-confirmation-seed selection is performed. With only two independent
deals per cell, the ordinary within-cell bootstrap variance is half the unbiased
variance estimate. The reports retain the historical percentile intervals and
add unbiased stratified paired standard errors/approximate-normal intervals;
all remain exploratory, especially subgroup comparisons.

`audit_opponents.py` independently checked the frozen PPO0 study's full 11,520-game
plan, artifacts, source identities, metrics, and 18 exact replays. All-seat
geographic-teacher controls sum to one win credit per deal. The original checkpoint
scored **47.71% vs 44.80%**, a **+2.90 pp** macro-cell gain over the teacher across
three opponent styles. The paired-deal bootstrap interval is +1.72 to +4.12 pp;
the supplementary unbiased-SE normal interval is +1.54 to +4.27 pp. There are
1,440 independent deal/opponent seeds, not 11,520 independent trials.

Style gains are economic +2.37, geographic +2.15, rush +4.18 pp. Count-2/3/4/5/6
gains are **-1.65 / +0.46 / +1.56 / +6.53 / +7.61 pp**. Italy is slightly negative
(-0.73 pp); the other five map aggregates are positive. See `opponent-results-v1.json`
for all groups, paired uncertainty and caveats. Fixed heuristic populations do
not establish human strength or production readiness; final seeds remain reserved.

`candidate-pool-v1.json` freezes all three independently preselected checkpoints
and an **equal-logit ensemble of all three**, with no fitted weights or confirmation
winner selection. `candidates.py` checks all pins and serving identities before
loading. The common heuristic prior is preserved, all legal actions remain, and
auxiliary averaged values are not calibrated ensemble win probabilities. The
ensemble is a fresh evaluation candidate, not an already proven improvement.

## Exact Germany reference recovery and next screen

`reference_recover.py` restores the **complete, unchanged** archived FILTER artifact
and validates its pinned manifest/descriptor/model. Its old public loader hashes
17 unused fixtures/training files as well as the serving files; a runtime-only
subset fails closed. Compressed source (130.4 MB) now stays in bounded RAM, so the
451.3 MB complete artifact fits under the 512 MiB disk cap without a duplicate
archive. The compressed-source RAM cap remains 256 MiB. These historical fixture
bytes are verified only, never used for new training or evaluation. The separate
`ai/.venv-reference` preserves NumPy 2.5.3 / ONNX Runtime 1.30.0 without changing
training's NumPy 2.2.6 / Torch 2.10.0 pins.

`reference_game.cjs` keeps the authoritative engine-2.0.22 state in Node, projects
only public information, preserves JSON insertion order, and validates returned
atomic moves against the full current legal menu. A separate persistent Python
process runs the exact old policy in every reference phase. Synthetic fixtures
cover all 20 Germany count/rule cells, high-bid menu thinning, discount nominations,
discards, powering, noncanonical simultaneous sealed-pending sets and actual
strict-loss filter certificates. The old runtime still uses its own engine-2.0.19
feature/preparation code; compatibility is tested, not silently assumed.

`reference-preflight-v1.json` records 160 mechanical fixtures, **20 successful full
games covering every Germany count/rule cell**, 7,730 public reference decisions
with hidden-state projection checks, 80 repeated phase decisions and five exact
full-game replays. These validate the adapter, not playing strength. The common
regression suites pass 49 Python and 14 Node tests before the screen-specific
worker tests.

### Completed neural screen: substantial gap to the reference

The frozen **evaluation-only** screen completed **1,920 games**, 320 per policy,
on **80 independent Germany deals**, four per configuration. All nonfocal players
used the exact retained reference. Every focal policy received the same deals and
all seats. Immutable result revision:
`9362440850a7a523a0a7b90814bc3a7b8b224702`, run
`multimap-neural-screen-20261102-v1`.

[`neural-results-v1.json`](neural-results-v1.json) independently audits every
outcome, source/archive/model hash, credit vector and complete plan. All games
terminated, with **zero failures/caps**. All 80 reference-control deals reproduced
identical terminal vectors/counts across focal-seat rotations, summing to one win
credit per deal. **12 exact replays** cover all six policies, five player counts
and four rule combinations.

| Focal policy         | Macro credit | Difference vs reference, pp | Approximate 95% interval, pp |
| -------------------- | -----------: | --------------------------: | ---------------------------: |
| PPO 0                |      13.125% |                     −15.875 |           [−20.228, −11.522] |
| PPO 1                |      17.667% |                     −11.333 |            [−16.321, −6.345] |
| PPO 2                |      14.313% |                     −14.688 |            [−19.608, −9.767] |
| Equal-logit ensemble |      12.771% |                     −16.229 |           [−20.874, −11.584] |
| Geographic teacher   |      13.354% |                     −15.646 |           [−20.069, −11.222] |
| Reference control    |      29.000% |                           0 |                       [0, 0] |

The estimand equally weights the 20 fixed cells, averaging seats within each
deal first. Intervals use unbiased **stratified paired** variance and a normal
approximation, not the original summary's unstratified SE. Four clusters per cell
is small; comparisons are exploratory and not multiplicity-adjusted. The exact
29% control is mean(1/n) for n=2..6, not certainty about general playing strength.
**No candidate-versus-teacher interval excludes zero. No winner was selected.**
The ensemble did not solve the gap; heuristic-opponent gains did not establish
strength against this neural population. This is not training data, final
qualification, a human comparison, or evidence about other maps.

The HF job passed **13 Node tests with one archived-compatibility test skipped**
before artifact recovery, plus 24 Python tests. The earlier local 14-test Node
suite and reference preflight are separate evidence. Principal runtime versions
match; historical serve requirements did not fully pin transitive dependencies.
No action traces were saved, so attribution needs a new diagnostic rather than
post-hoc guesses from these terminal outcomes.

### Completed phase substitution and prior-reachability diagnostic

[`gap-protocol-v1.json`](gap-protocol-v1.json) freezes a diagnostic, **not another
blind PPO extension**: 20 Germany cells × two fresh deals × all seats × ten arms
= **1,600 games / 40 independent deals**. Arms are reference-all, teacher-all,
reference with one phase replaced by teacher (four), and teacher with one phase
replaced by reference (four). Nonfocal players always use the exact reference.
Auction includes upgrade/discard decisions as well as nominations and bids.

Every focal multi-action decision also obtains a legal counterfactual reference
move, including teacher-controlled decisions. Compact per-phase counters record
agreement, prior gaps/histograms and reachability; forced moves are excluded from
agreement denominators. No observations, action traces or training trajectories
are saved. Phase contrasts include downstream effects and need not add up;
state visitation differs by arm. All arms are reported, not selected.

**Verified v1 restriction:** logits are `prior + 8*tanh(raw/8)`. An expert action
more than 16 prior units behind a best-prior action cannot become greedy-best,
regardless of training. In particular, floor −20 actions cannot overcome a prior-0
action. Many bids above heuristic valuation hit this floor. Retaining every legal
bid structurally did **not** make every bid reachable by the greedy policy. The
diagnostic counts only gaps **strictly greater than 16 + epsilon**; an exact gap
of 16 is not called strictly unreachable because endpoint ties are possible.

`gap_study.py` reuses the frozen collector through private function-global
bindings, never by modifying old modules. The new bridge keeps authoritative
state in Node and maps exact reference atomic moves against the full legal menu.
Strict source/runtime/worker resume identity, six single-thread workers, zero-error
stop behavior, 128 MiB compact artifacts and 120-game HF snapshots remain.
Only identical snapshot uploads receive bounded retries, never games. A separate
20-game smoke namespace exercises all ten arms before the full run.

The completed run is independently audited in [`gap-results-v1.json`](gap-results-v1.json):
**1,600 terminal games, zero failures/caps/missing/duplicates, 10 exact replays**
covering every arm, all five player counts and all four rule combinations.

| Focal policy                           | Macro win credit |
| -------------------------------------- | ---------------: |
| Reference                              |         0.290000 |
| Teacher v1                             |         0.118333 |
| Reference except Auction → teacher     |         0.240000 |
| Reference except Resources → teacher   |         0.290000 |
| Reference except Building → teacher    |         0.204583 |
| Reference except Bureaucracy → teacher |         0.290000 |
| Teacher except Auction → reference     |         0.235833 |
| Teacher except Resources → reference   |         0.118333 |
| Teacher except Building → reference    |         0.240000 |
| Teacher except Bureaucracy → reference |         0.105833 |

Auction reference choices were strictly unreachable under v1 on **632/5,698
(11.09%)** reference-controlled decisions and **710/6,063 (11.71%)**
teacher-controlled decisions; exact floor−20 counts were 463 and 577. These are
correlated decision counts, not independent trials. The paired fixed-cell
intervals in the report are exploratory: only two deal clusters per cell,
multiple contrasts, repeated seats and policy-dependent visitation.

**Resource caveat:** all 160 focal credits match their respective baseline,
but this does not mean identical play. Reference swaps change 90/160 Resource
counter signatures despite identical terminal vectors/steps; teacher swaps change
84/160 signatures and **2/160 complete terminal vectors/step totals**. The latter
change nonfocal winners. No raw action traces or identical-fuel-purchase claim
is made. Auction and Building are learning targets, not promoted policies.

### Separately versioned mechanical teacher repairs

[`teacher-repairs-v2.json`](teacher-repairs-v2.json) describes unused-by-v1 helpers
`economics_v2.cjs` and `teacher_v2.cjs`, with three targeted repairs:

-   Finish-loss checks precede high-cash/late-round fallback and geographic/UK
    preferences. They use a conservative fuel-feasible ceiling across possible
    further builds, rather than vetoing a losing intermediate one-build position.
    Final power is computed automatically by the scoped engine. Opponents' future
    building/cash decisions and network reachability are not forecast.
-   Production plans retain exact per-plant fuel allocations, preventing a hybrid
    from consuming coal needed by another plant. Normal income/opportunity-cost
    scoring is retained; endgame planning maximizes feasible output.
-   Both direct/cached fuel purchase quotes include eligible USA Recharged supply
    coal at $8, after market stock, bounded by actual supply.

Tests cover legal edited fixtures, hidden-field isolation, 1,200 brute-force
production/continuation cases and 120 full scoped games. The retained reference
also makes the hybrid error on the synthetic regression case: it is not a perfect
oracle. These are correctness repairs, **not measured competitive improvements**.
No historical teacher/model/reference/engine code was edited, and the phase-gap
study deliberately used **v1**. The new learning recipe retains
Germany/USA/France/UK & Ireland training and Italy/Benelux whole-map holdouts;
no diagnostic or reserved final roots become training data.

### Expert-assisted multi-map PPO v2

[`expert-protocol-v2.json`](expert-protocol-v2.json) freezes the next learning
experiment, not another attribution screen. Its separately versioned files do
not modify any historical scorer, checkpoint, feature encoder or reference.

-   Learn Auction/Building with `prior + 16*tanh(raw/16)`, so all actions in the
    full legal menu can overcome the prior's maximum 20-unit gap. Add one masked
    `prior/20` channel to the action scorer. Keep the portable city graph, no city
    IDs/map-name embeddings, width64 and original bootstrap representation pin.
    Insert a zero-weight prior column and zero actor head: initial greedy policy
    is exactly teacher v2, checked against an independent direct-teacher control.
-   Use the mechanical v2 teacher only for fixed Resources/Bureaucracy/forced
    decisions and the new prior. This is not a claim that the repairs improve wins.
-   Warm up on **160 fresh Germany games**, reference focal A/B and reference
    opponents, with v2 fixed phases; **24 fixed supervised passes**. Reference
    labels are not available outside its Germany scope.
-   Then **32 × 80 = 2,560 fresh PPO games**, equally balanced across the four
    training maps and all player/rule cells. Germany alternates reference-population
    and mixed games; mixed per-seat opponents are all three frozen PPO replicas and
    the greedy current student, unchanged throughout collection. Only the focal
    student's training moves are sampled. Every Germany focal multi-action A/B
    choice receives a counterfactual legal reference label (DAgger); execute the
    student's actual choice, not the label.
-   True terminal win credit, equal game weights, phase-balanced expert CE,
    coefficient `.5*.97^(update-1)`, globally normalized weights (not minibatch
    label-subset normalization), and **no heuristic-prior KL penalty**. AdamW/PPO
    remain bounded; trajectories are RAM-only with a 100,000-row guard.
-   Select from initial, warmup, updates8/16/24/32 using **320 fixed in-map games**
    per checkpoint: Germany against reference, other maps against the frozen
    three-policy population, never self. Four-map macro credit, earliest ties;
    Germany cannot regress from the initial baseline, other maps at most .05.
    The zero-head baseline remains eligible. Another 320 direct-teacher games
    verify initial full terminal parity.
-   Only after selection, **960 selected + 960 teacher-v2 confirmation games**
    cover all six maps. Italy/Benelux are whole-map transfer-only. Evaluation never
    asks for expert labels; reference opponents still make their own public moves.
-   Atomic stage/update transactions save optimizer/RNG and the exact committed
    best-checkpoint bytes. Resume restores corrupt/uncommitted best files and rejects
    serving-source/runtime/worker drift. Whitelisted private snapshots cap at
    128 MiB and exclude requests, observations and trajectories. Reuse the complete
    unchanged 451 MB reference artifact and isolated reference environment.

The disjoint engineering smoke uses four in-map two-player original/open cells,
two warmup games/passes and two PPO updates. It is not strength evidence or a
model-selection experiment. HF delivery uses `launch.py --workflow expert`,
six collector workers and a three-hour CPU-job timeout; see `runs.json` for the
actual launch/completion state. No candidate is qualified or deployed.

[`expert-preflight-v2.json`](expert-preflight-v2.json) pins the final private
engineering evidence: **132 terminal games**, 66 exact terminal/counter replay
matches across uninterrupted versus interrupted/resumed execution, populated
Adam state, bit-identical weights/optimizer/RNG/history/best bytes, and recovery
from deliberate best-file corruption. All ten controller types were exercised;
276 expert labels and 3,419 reference requests occurred per execution. The smoke
selected the initial baseline, not a stronger learned model. Checks passed:
**366 engine tests, 152 Python tests, 44 Node tests**. The complete 451 MB reference
was reused unchanged; only about 12 MB of compact smoke evidence was archived.

#### Operational timeout and confirmation-only continuation

The initial v2 job reached its three-hour limit **after committing update32**.
[`expert-recovery-v2.json`](expert-recovery-v2.json) verifies the immutable
`8ca6e47686e06edc7a24c2e85cc2b31e5140f860` snapshot: 84 hashed files (~20 MB),
all 2,720 training games and 2,240 initial-control/selection games, zero failures
in those saved games, populated optimizer state and exact embedded-best bytes.
Its recorded serving-source/runtime/worker identity matches the unchanged code.
The predeclared selection rule chooses **update24**, checkpoint SHA256
`1377fc2112c3b9ff3c2a20078ed341305b2a9006a4f7a1df413eeb0b509e6fbd`.
That is a selection result, **not confirmation or qualification**.

No complete confirmation batch was committed. The `-r1` continuation uses the
**same original source archive, container image, six workers, frozen checkpoint
and evaluation seeds**; only its output run ID and immutable resume pointer
change. It skips all optimization and selection and runs the remaining
**960 selected + 960 teacher-v2 confirmation games**. Any in-memory partial
confirmation work lost to timeout is repeated with the same fixed tasks; it is
not turned into losses or used to alter the model. Inherited training/selection
files in the new prefix are copies, not additional independent games.
[`expert-resume-launch-v2.json`](expert-resume-launch-v2.json) records the launch.
The continuation subsequently completed; its results are audited below. No
training recipe was changed.

#### Expert-v2 result: substantial conditional gain, not qualification

The continuation completed on 2026-11-03. Its final private model-repository
revision is `39976d5e864638fe73d241061bc4dfd4b46ce0a4`, under
`runs/multimap-expert-ppo-20261102-v2-r1/`. The selected **update24** checkpoint
and SHA above remain unchanged. See [`expert-results-v2.json`](expert-results-v2.json)
for the complete independent audit and [`expert-audit-v2.json`](expert-audit-v2.json)
for the private evidence receipt.

Both confirmation arms completed **960 games**. Mean win credit (ties split,
equal map/player-count/rule-cell weights):

| Map                     | Selected update24 | Teacher v2 | Paired difference |
| ----------------------- | ----------------: | ---------: | ----------------: |
| Germany                 |            34.04% |     20.08% |         +13.96 pp |
| USA                     |            60.88% |     39.00% |         +21.88 pp |
| France                  |            64.25% |     32.92% |         +31.33 pp |
| UK & Ireland            |            71.46% |     28.88% |         +42.58 pp |
| Italy — transfer only   |            46.50% |     25.42% |         +21.08 pp |
| Benelux — transfer only |            61.19% |     41.13% |         +20.06 pp |
| **All six maps**        |        **56.39%** | **31.24%** |     **+25.15 pp** |

**The opponent standards differ:** Germany uses the exact retained reference;
other maps use the fixed mixed PPO0/1/2 population. These are not six measurements
against the Germany reference, nor a universal strength rating. The aggregate
paired difference has deal-cluster SE **2.41 pp**, approximate normal 95% interval
**[+20.42, +29.88] pp**. All five player-count aggregates and all four rule
aggregates are positive, but observed cell differences are **93 positive,
13 tied and 14 negative** out of 120.

For Germany, the paired improvement over teacher v2 is **+13.96 pp**,
approximate 95% **[+1.73, +26.19] pp**. Against the **analytical** all-reference
symmetry benchmark of 29% (`mean(1/n)` for 2–6 players), the selected policy is
**+5.04 pp**, interval **[−4.59, +14.68] pp**. No new all-reference control arm was
played here. **Superiority to the exact reference remains unproven.**

These intervals average all focal seats within each deal, then use unbiased
within-cell sample variance over **two independent deals per cell** and equal
fixed-cell weights. There are 240 confirmation deal clusters overall, 40 per map;
the 1,920 played games are not 1,920 independent samples. Intervals are exploratory,
unadjusted for multiple comparisons, conditional on one trained seed and these
populations. Teacher v2 differs from the earlier v1 teacher, so historical raw
scores cannot isolate the effect of any particular repair or learning ingredient.

Integrity checks passed for **all 6,880 scheduled saved outcomes**: 2,720 training,
2,240 selection/control and 1,920 confirmation, with no failures, caps, missing or
duplicate scheduled tasks. All 82 inherited unchanged artifacts match the
preconfirmation snapshot; the update32 model and populated optimizer are
bit-identical. Selection was independently reconstructed without confirmation.
All 44,262 expert labels were Germany training/warmup only; evaluation returned no
training labels, and Italy/Benelux never entered training or selection.

The audit rehashed 1,342 source-archive members (152 Git-tracked files), all 42
compiled engine modules and the complete reused 1,467-member reference artifact.
**12/12 exact confirmation replays** cover both arms, all six maps, every player
count and all four rules; terminal/controller/public/request fields match exactly.
Checks passed: **366 engine, 192 Python and 44 Node tests**, including 40 new
adversarial audit tests. RAM-only training trajectories/gradients were not retained,
so this is not an independent replay of every optimization step.

**Next decision:** freeze update24 rather than extend training immediately.
First preregister a fresh, larger-deal, four-training-map stress test against
frozen strong and heterogeneous populations, including multiple strong opponents
at the same table and reciprocal two-player matchups. Compare against a pinned,
predeclared old-PPO focal control; homogeneous self-play is a symmetry/control arm,
not evidence of strength. Frozen update24 opponents provide stronger opposition,
not independent algorithmic diversity. If that test supports robustness, run
independent training-seed replicas and report all of them, not only the best.
Do not iteratively tune on Italy/Benelux; these viewed transfer outcomes are now
consumed exploratory evidence. At that audit checkpoint, no next experiment had been launched. No model was
qualified, promoted or deployed.

### Frozen population stress v1

[`stress-protocol-v1.json`](stress-protocol-v1.json) preregisters **5,120 games**,
using only Germany, USA, France and UK & Ireland. Update24 stays frozen at the
SHA above. The sole focal comparator is pinned **PPO2**, chosen before stress
outcomes from the existing v1 evidence, not reselected on these results.

-   **Strong panel:** Germany nonfocal seats use the exact retained reference;
    other maps use frozen update24 in every nonfocal seat.
-   **Mixed panel:** a deterministic relative-seat schedule puts update24 in
    roughly half the opponent slots and rotates PPO0/1/2 and teacher v2 through
    the others, with reference included only on Germany. Actual strong-seat
    occupancy is reported; this is not uniform coverage of every lineup.
-   Each panel contains 80 map/count/rule cells, **four fresh deals per cell**, all
    focal seats, and both focal policies: **2,560 games / 320 deal clusters**.
    Panels have disjoint roots; paired focal policies share complete opponents,
    deal and seat. No Italy/Benelux, historical diagnostic/confirmation roots,
    expert labels, training, sampling or checkpoint selection is allowed.
-   The two panel primary comparisons are reported separately, with equal-cell
    paired deal-cluster estimates, normal 95% exploratory intervals and two-test
    Bonferroni normal 97.5% intervals. Mixed lineups vary with deal: sample variance
    includes between-lineup mean variation, so it is conservative in expectation
    for fixed-schedule uncertainty, **not an unbiased estimator of that variance**.
    Normal coverage remains approximate with four deals. All subgroup/occupancy
    comparisons are exploratory and unadjusted.
-   Strong non-Germany all-update24 focal games are **symmetry/replay controls**,
    not strength evidence or independent algorithm diversity. Their full terminal
    vectors/counters must agree across focal-seat rotations. Reciprocal two-player
    outcomes, map/count/rule breakdowns and actual opponent occupancy are saved.
-   Research progression to independent replicas requires both primary adjusted
    lower bounds above zero and no panel/map paired point estimate below −.05.
    This is a predeclared research heuristic, not qualification or a familywise
    guarantee for the many secondary comparisons. No outcome-dependent extension.

The new `stress_game.cjs`, `stress_rollout.py` and `stress_study.py` have their
own strict evaluation scope and reuse unchanged feature/policy/public-reference
helpers. No frozen v1/v2 serving file or namespace validator is modified.
`preflight_stress.py` runs **only engineering smoke roots** across both panels,
four maps, all five player counts and all four rules, testing interruption and
exact replays with real pinned policies/reference:

```sh
PYTHONPATH=ai/multimap ai/.venv/bin/python -B ai/multimap/preflight_stress.py \
  --output ai/runs/multimap-stress-preflight-v1
```

Each panel runs in its own bounded private CPU job (six workers, three-hour cap).
Every paired all-seat deal batch is written atomically locally; snapshots upload
**every 16 batches**. Immutable resumes preserve remotely checkpointed work. A
killed ephemeral job may lose up to 15 locally completed batches plus the current
batch; these may replay with identical tasks, counted once, never fabricated as
losses. Whitelisted outputs cap at 64 MiB per panel and contain no model copies or
raw states/actions/trajectories. The complete retained reference is reused locally;
remote jobs reconstruct its same manifest without loader omissions.

`launch_stress.py` gates production on hashed real-service preflight evidence and
packages one source archive for both panels. If interrupted, its explicit
`--continue-launch <receipt> --run-id <new-id> --resume-revision <immutable-sha>`
path reuses the original job command/source rather than repackaging. A separate
`--missing-panel` path handles an unsubmitted peer after partial launch; existing
intent files require inspection rather than blind submission retries. See
`runs.json` and the stress launch receipts for actual execution state.

[`stress-preflight-v1.json`](stress-preflight-v1.json) pins the completed private
preflight: **240 terminal games, zero failures, 120 exact terminal/counter replay
matches**, interrupted after two batches, with committed batches preserved and an
incomplete temporary write ignored. Completed resume performs no model load or
collection. Every controller was exercised, with **18,597 reference requests and
zero expert labels per execution**. Smoke roots were deliberately replayed for
engineering checks, never counted as independent strength evidence.

Checks passed: **237 Python, 54 Node and 366 engine tests**. Two existing engine
prefix-replay tests initially exceeded the default two-second timeout under host
load; all unchanged engine tests passed when run directly through Mocha with a
ten-second timeout. Both engine logs are archived. No engine or frozen policy code
was changed. The approximately 2.2 MB private evidence archive reuses the retained
reference; it contains compact outcomes, hashes, tests and logs, not raw gameplay
states or action trajectories.

Both private production panels were submitted on **2026-11-03**, using the same
source commit `e6e3b571eb07d1da66aec594e0ecb75b44d79e2c` and source archive:
[strong](https://huggingface.co/jobs/coyotte508/6ae9b2e2c78863f9c63189a6) and
[mixed](https://huggingface.co/jobs/coyotte508/6ae9b2e3c78863f9c63189a8).
[`stress-launch-v1.json`](stress-launch-v1.json) records the immutable source,
model, plan and preflight pins, verified job configuration and bounded budgets.
Completion/error watchers are attached to both. These are **ongoing frozen
research evaluations**, not completed results, qualification or deployment.
