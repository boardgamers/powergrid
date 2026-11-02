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

Do not accumulate local training archives. The launcher requires its working
cache under `ai/runs/multimap-*`, refuses to start above **1 GiB** or with less
than 2 GiB free, removes the expanded staging tree immediately after packaging,
and removes the source archive after its immutable HF upload is receipted.
Local data workers stop above **512 MiB** of multi-map run files. This leaves
room for temporary source packaging; dependencies/venvs are separate.

All 1,760 games are already archived privately on HF (about 48 MB compressed).
The recovery reuses those pinned archives. Local expanded data and disposable
smoke weights were removed after verification: run directories are under 1 MB;
the Python environment is about 955 MB and HF's downloaded-data cache about
46 MB. Preserve compact receipts/audits, not duplicate bulk data. Future large
iterations must stream/shard to HF buckets or remote storage; do not expand
hundreds of GB locally. If HF storage limits become an issue, discuss public
visibility or alternative storage with the user rather than changing visibility
silently. Never prune unrelated runs or shared caches wholesale.

## Next after the first run

Audit checkpoints, per-cell results, terminal failures and transfer behavior.
Benchmark the selected model on `ssh minipc-wg` (AMD 8840U). Add an explicit
Germany frozen-1 comparison using its original public-runtime adapter, not its
raw weights with v1 features. Its ONNX SHA was independently verified as
`55331f43379e8fe89025d93b1a7a48c88e0ea39b4ebd3a7ef8240d4b62753530`.

Then improve policies using fresh on-policy trajectories and controlled
opponent mixtures, or public-world search labels where target-quality tests
justify them. Do not just repeat epochs on fixed weak targets. Refresh data
and compare fresh paired games before expanding compute or admitting more maps.
