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

The next frozen **evaluation-only** screen compares `ppo0`, `ppo1`, `ppo2`, their
equal-logit ensemble, the geographic teacher, and the retained reference itself
against a population of that exact reference. All six focal policies get the same
fresh Germany deals and all seats: **1,920 games, 320 per policy, 80 independent
deals**, four per configuration. The homogeneous reference control must sum to one
win credit per deal. This is not a training dataset, a checkpoint selection loop,
or final qualification. All maps outside Germany remain out of this comparator's
scope; the multi-map model scope is unchanged.
