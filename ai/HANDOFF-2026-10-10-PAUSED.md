# Power Grid AI — paused handoff, 10 October 2026

**Research is PAUSED at the user's explicit request. Do not start jobs, retries,
training, evaluations or further development until the user resumes.** Existing
HF jobs were left running. They terminate on completion, failure or timeout;
this handoff does not schedule any continuation. The Codex goal is paused, not
complete. No AI candidate has passed the full strength gate or been deployed.

This document supersedes active/pending instructions in older notes. The status
snapshot is **2026-10-10 18:38:44 UTC / 20:38:44 Paris**; jobs may finish after it.
The machine-readable snapshot is
[paused-handoff-state-2026-10-10.json](strong/paused-handoff-state-2026-10-10.json).
Historical evidence remains in [RESUME.md](RESUME.md) and the complete
[experiment ledger](strong/experiments.json). Do not interpret old “next” sections
as authorization to resume.

## Locations and recovery

- Working checkout: `/home/eliheros/Documents/Codex/2026-09-26/je-x20-2/work/powergrid-ai`.
- Git remote: `git@github.com:boardgamers/powergrid`; branch `ai/germany-baseline`.
  Last implementation commit before this handoff: `ab8758c593f8406c8d5aec9778f15d9f27dd41ee`.
- Python: `ai/.venv/bin/python`; `python3` is also available, bare `python` is not.
- Checkpoints, exports and reports:
  [coyotte508/powergrid-ai-germany-v1](https://huggingface.co/coyotte508/powergrid-ai-germany-v1).
- Immutable source/data bundles:
  [coyotte508/powergrid-ai-training-v1](https://huggingface.co/datasets/coyotte508/powergrid-ai-training-v1).
- Latest model-repo revision observed at pause:
  `b9ac766f397ce5ca5a0943bc8f2fbb0c4f6a543f`. This is a raw artifact snapshot,
  not an assertion that all results in it have been verified.
- `ai/runs/` is ignored and contains large local artifacts. A fresh clone needs
  the exact HF revisions recorded in manifests; do not assume those files exist.
- Actual target device: `ssh minipc`, user `coyotte508`, AMD 8840U. Most recent
  search probe directory: `/home/coyotte508/powergrid-ai-search-transfer-probe-v1`.
  The local laptop is an HX370 and is not interchangeable with that benchmark.
- Production/UI checkout: `/home/eliheros/code/powergrid`, clean at `aac09f2`,
  viewer 2.3.6. The later experimental UI redesign was reverted. Do not merge
  or publish research merely to save this handoff.

Use cached HF/SSH authentication. No tokens or private historical game records
belong in Git, this handoff, logs or a serving package.

## What has changed since the beginning

1. **A working baseline and an honest failure.** We audited 4,007 BGS records.
   Only 32 supported, exactly replayable human games remained for the corrected
   Germany/3p baseline, providing 11,366 decisions. With 600 synthetic games,
   imitation and short self-play training worked technically, but the corrected
   baseline scored 0% against the existing bot in its 480-game comparison.
   Human data was useful for bootstrapping and replay checks, not sufficient
   evidence for a strong policy.
2. **Better observations and real opponents.** We fixed a broken training
   heuristic (NaN fuel prices and incorrect stock pricing); the repaired heuristic
   itself beat the default bot 85.1% over 960 games. We added economic, rush,
   geographic-search and frozen neural opponents, making default-bot wins a
   sanity check rather than the strength target. Public features include
   replenishment, money, plants/fuel, cities, turn order, players left to act,
   and territory/building capacity. Opponents are represented individually.
3. **Actual training, then wider training.** Three-player leagues, imitation
   from search and PPO produced useful reference policies. The system expanded
   to Germany at 2–6 players, original/Recharged and open/sealed auctions. The
   ordered multiplayer architecture has 983,682 parameters. Initial multiplayer
   teacher data contained 1,200 games and 142,804 decisions. Two later major
   training runs each completed 80 updates and 19,200 full games. More training,
   harder opponents or closer imitation did not reliably improve every matchup.
4. **Controlled diagnosis instead of assuming later is better.** We investigated
   population training, fifth-plant context at two players, bidding menus,
   teacher reliability, export precision and individual decision phases. Some
   changes helped certain cases and regressed others. We retained unsuccessful
   runs and earlier checkpoints. The JavaScript engine remains authoritative;
   no Rust rewrite was completed. Profiling, shared calculations, batching and
   asynchronous workers improved throughput without changing game rules.
5. **A useful learned discard correction.** Two trained correction seeds improved
   several independent matchups. Against the stronger search opponent at two
   players, win share rose from 23.44% for the parent to 50% for both seeds on
   eight paired development deals (+26.56 points, paired 95% interval
   +15.63 to +39.06). That is a real development improvement, not proof of
   overall strength: sealed weaknesses and failures at other counts remain.
6. **Search helps, but can also hurt.** The latest raw-policy opponent suite
   covers 13,440 completed games across 2–6 players. Guided search improved
   three-player play against frozen A260 from 36.20% to 49.48% in its paired
   development comparison. At five players, however, the Recharged/open rule
   cell fell from 52.5% to 27.5% against geographic search. An aggregate gain
   cannot hide that regression. No universal search configuration is qualified.
7. **Deployment feasibility is demonstrated.** Export and legal-serving checks
   cover 2,553 positions across all counts. On the actual 8840U, the current
   10102 raw policy took median/p95 3.09/5.40 ms per warm request. Guided search
   took 1.11/2.06 s on the measured searched subset. These are research probes;
   platform integration and the final exact-model/configuration benchmark remain.
8. **The current next approach is prepared, not trained.** We are collecting
   paired counterfactual targets for auction nominations, bids and building.
   A small correction head learns estimated advantages over the frozen parent,
   preserving existing behavior elsewhere. Its untrained export works, but
   there has been no gradient job for this new strategic correction.

Current validated learning scope is **Germany, automatic setup, 2–6 players,
original/Recharged, open/sealed**. Generic geography and UK/Ireland feature checks
do not establish trained strength on other maps. All players' money is allowed
to be visible; hidden deck order, seeds, submitted sealed bids and queued plans
are excluded. Sealed auctions use their actual rules. The value head remains
uncalibrated and is not ready for a reliable round-by-round analysis graph.

Separately, published game/UI work includes geographic backgrounds across maps,
faded unselected regions, adaptive board sizing, clearer activation/discard
states, automatic free-plant powering, and mobile resource buying with step
refill previews. The most recent broader controls/card redesign was reverted;
the released viewer 2.3.6 resource UI remains. This is separate from AI deployment.

## State at pause

| Work | Verified state | Still outstanding |
| --- | --- | --- |
| Latest independent raw-policy suite | 13,440 complete games, 2–6p | Full qualification not passed |
| Guided transfer vs geographic search | 1,152 guided + 1,152 paired raw games, 3–5p | Three 6p jobs running |
| Fresh strategic collection | 2,880 unique games / 5,760 twin executions; 147,417 roots | 4–6p search pieces incomplete |
| Collection runtime probes | All 15 verified; 240 games / 12,208 roots | None |
| Continuation runtime probes | All 20 verified; 832 outer + 1,348,096 nested rollouts | No strength inference from these probes |
| Teacher labels | 13/20 pilot shards verified; 149,472 full rollouts, no caps | One completed unverified + six running |
| Full label plan | 1,920 roots, 160 shards | Remaining 140 shards never launched |
| New strategic correction | Code and zero-head export preflight pass | Complete dataset, frozen training source, HF gradients and fresh games |

There were **20 running jobs** at the snapshot: six label jobs, eleven collection
pieces and three six-player arenas. Two additional jobs had completed but were
not independently collected. The three historical label image-pull errors have
completed, verified replacements; they are not outstanding failures to retry.

## Current label design and provenance

The 1,920 selected public roots contain 1,440 train / 480 validation, 640 each
nomination/bid/build, balanced over count, source, deal and four rules. Splits
keep whole count/source/deal units together; validation deals are 0, 4, 8, 12.
Hash selection used no outcomes, excludes the ten runtime-probe roots, and rejects
identical public inputs across train/validation. A detected duplicate was replaced
by the next hash-ranked distinct training input without changing grid coverage.

Each root uses the frozen 10102 parent, a six-proposal geographic/economic
shortlist plus its exact proposal, 48 worlds in each independent A/B batch,
and full 2,400-step continuations. Both continuation modes share sampled worlds:
all-neural, and neural focal player with economic opponents. Outcomes and paired
advantages are retained, including negatives; these are not hard winner labels.
Search-opponent continuations were too expensive for this bulk label plan;
independent full-game acceptance against strong opponents is still required.

- Local root gzip: `ai/runs/strategic-teacher-training-roots-v1.jsonl.gz`;
  packaged under `ai/strong/fixtures/` in the frozen HF source, not tracked as a
  local Git fixture. SHA256
  `f0fd62b4dd75c6b6c0936adeb1ffc75a2747cb2c62debe6b5d0aba60dbb4a091`.
- Dataset revision: `837d94e14272163c33e5e55fa9c24b24686a28ae`.
- Archive: `strong-source-strategic-teacher-training-20261010-v1.tgz`.
- Archive SHA256: `a011f9ee4b8116b99220913a7db9d00849e9e593137cdb7e435e116fcafdd6c3`.
- Protocol SHA256: `3c39786cc6c44a3838d3c4183c312c94a26563222b2720572010b76bbdd62a76`.
- First seven verified raw shards: revision `73242585764795b390c3067a74666ce056cf5ef4`.
- Next five: `3d67c0f4735f16f0a6c7bd70c28ff85153ab3814`.
- Latest 3p/economic/neural: `44ea71ff87cef3d3772caaa5fcfa514f580d00d0`.
- First partial evidence archive: `c4d264577f6e6db24fea4238a5d80031046e5c04`,
  `runs/strategic-teacher-training-first-partial-evidence-v1`.

[Label results](strong/strategic-teacher-training-results-v1.json) contain exact
per-shard hashes. There are only 72 roots with both modes verified (36 train /
36 validation). Validation A-selected/B-evaluated advantage is +8.16 percentage
points, reverse +7.26, choice agreement 61.11%. These are small conditional
simulation diagnostics, **not whole-game win rates, confidence intervals or
evidence that the untrained correction is strong**.

Preserve frozen source overlays and exclusive launch guards. The remaining-chunk
launcher rejects admission until all 20 pilot results verify, then derives a
timeout from the slowest matching root with 2x margin and 25% headroom. Future
chunks use the Python CPU image and all 2,553 batch-parity checks first. No future
chunks have been launched. Do not infer permission from a script being ready.

## New strategic correction: implemented, untrained

See [the fixed design](strong/strategic-correction-design-v1.json).
Schema `4.3-strategic-correction` has 1,217 state and 101 action features; the
complete 4.2 prefix and legal menu are unchanged. The head adds 97,473 parameters
and reuses frozen ordered-player/action embeddings. It may change multi-choice
nomination/bid/build decisions only within the teacher shortlist plus parent
proposal, and only above a fixed 0.025 predicted advantage. Parent values and all
other decisions remain unchanged.

Trainable parent, model repo revision `b115a2d78aae095e51fb72a5535b3507abdf90c0`:
`runs/discard-correction-v1/10102/best.pt`, SHA256
`66a10b831a54843063bbca89743a542ed1f89515a16452a40483eef369c59bd8`.
**Use the full checkpoint, not the inference-only derivative.** Its serving
derivative is `runs/discard-correction-v1/10102/derivative/inference64.onnx`, SHA256
`57f8255e79b991ba466f91e953d0bca6868144bb543577fc0dad8ade387ebf68`.

Targets average paired outcomes across modes within each world before estimating
variance, preserving covariance, then combine 96 independent A/B samples.
Weighted MSE learns relative action advantages; uncertainty weights are clipped
to [0.25, 1], normalized within each root, with equal total weight per root.
Seeds 11101/11102; 120 epochs; batch 256; LR 0.0003; weight decay 0.001;
gradient clip 1; validation every five epochs plus epoch-zero parent baseline.
Choose lowest validation simulated regret, breaking ties toward earlier epochs.
No threshold tuning or qualification from these simulation targets.

The loader requires all 160 verified shards and full 1,920-root coverage before
gradients. Training additionally requires HF/CUDA and frozen design/data/source
pins. It has been compiled, **not executed on a full dataset**. No frozen gradient
training source exists. A future source must include teacher source descriptor
and root gzip; the bootstrap must supply `DESIGN_SHA256`, `DATA_MANIFEST_SHA256`,
`SOURCE_REVISION`, `SOURCE_SHA256`. Do not put a future archive's own hash inside it.

Preflight: 2,553 fixtures, 1,096 eligible, hidden-information invariance, two
routing and four paired-target tests. Zero correction preserves all parent
choices/values and legal serving. Successful output:
`ai/runs/strategic-correction-preflight-v2`; failed first ONNX attempt is retained.
Evidence revision `a4ff888a73e33f5b29918978f1beabac5dd437d0`, prefix
`runs/strategic-correction-preflight-evidence-v1`. The untrained ONNX SHA256 is
`bf08d13ad2feebbe923684d0e2c8bc5a658fe4f2aaf9b26fd67bcf7ce64100d1`.
Local HX370 median/p95 3.916/8.217 ms is not the target-device benchmark.

## Collection and saved merger work

Full collection plans 3,840 unique games / 7,680 identical twin executions,
covering every seat, four rules, 16 deals, counts 2–6 and economic/search/self-play
sources. All economic/self-play cases and 2p/3p search are verified. Remaining
4p/5p/6p search work was split into original deal ranges [0,4), [4,8), [8,12),
[12,16), preserving rules, horizons and observations. Whole-job guards with
`stage: split_plan` intentionally have no job ID; do not remove them.

Slice dataset revision `00e833da8dca00fdc26cf7e07b320a8276ad27f3`, archive
`strong-source-strategic-training-collection-slices-20261010-v1.tgz`, SHA256
`bb0498e19106fb233239af59ced62ffddbad056f71c6500ba15d46ec56e7a842`.
Protocol SHA256 `0086deceb58a0dc21a8e07f7e74142315b237985aead8db5ce7ac1617369e45a`.
Keep `strategic_collection_slices.py` and `check-strategic-collection-slices.py`
frozen against that source. Nonzero-offset parity already passed.

New code saved with this handoff:

- `merge-strategic-collection-slices.py`: requires all disjoint pieces, verifies
  provenance/hashes/full game grid, preserves every game/root/proposal, normalizes
  only global root order while retaining original indices, and rereads output.
- `check-strategic-collection-merge.py`: completed before pause; reconstructed
  128 already verified games / 7,283 roots, rejects missing/overlapping ranges and
  overwrites. This generated no new games. Result:
  [strategic-collection-merge-preflight-v1.json](strong/strategic-collection-merge-preflight-v1.json).
- `summarize-strategic-collection-combined.py`: records whole-job and split-source
  provenance separately and rejects duplicate coverage. Current
  [combined results](strong/strategic-training-collection-combined-results-v1.json)
  remain 2,880 games / 147,417 roots. **No actual 4–6p full-case merge has run.**

## Strength and release constraints

The latest model is still below the requested universal strength standard.
10102 guided versus geographic search: 3p 20.83% raw → 41.67% guided;
4p 24.22% → 35.16%; 5p 33.75% → 35%. These use eight paired development deals
per count; neither aggregates nor per-rule uncertainty establish qualification.
At 5p the overall gain interval is [-3.75, +6.875] percentage points, while
Recharged/open regresses 25 points (paired 95% interval [-42.5, -10]). Preserve
this diagnostic; do not create a per-rule switch selected from those same tests.

Key evidence revisions in the model repo:

| Evidence | Revision |
| --- | --- |
| Complete 13,440-game raw opponent suite | `3faadbc32dfdb6e1c1490f9ea6ade911bb68d9c4` |
| Guided 5p regression | `d542f9713ab11d3db6cc5930113e3c745cdfb655` |
| Decision-phase search comparisons | `9ab4a39b49ac9ece8a3f26f9624fc1e2a68fc633` |
| Actual 8840U search/serving probe | `3ffca6810bfddd1be50f1c2a7acf7b9416eac478` |
| Production engine compatibility audit | `107ac032692cd7effd529bd03f7e6dc319602c55` |

The 8840U probe covers 2,553 raw positions per model and a 118-position subset
per searched configuration, not all positions searched. Across three models,
180 actual searched decisions produced 43,200 full rollouts without caps.
Production engine 2.0.14 vs research 2.0.10 agreed on 2,553 legal menus, 5,106
feature encodings, 2,553 default-bot transitions, and 80 games / 41,026 transitions.
This excludes pending powering choices, messages/step announcements and platform
wrapper scheduling; it is not a full production integration certification.

The [reserved final protocol](strong/final-protocol-multiplayer.json) is unused:
prefix `strong-multiplayer-final-reserved-v1`, 20,160 games, 320 shards, 26
opponent/count cells. Every count/rule needs its stated win floor and a deal-based
confidence interval strictly above 1/N; all actions legal, no game/search caps,
strict native/export/serving parity, actual 8840U exact-configuration measurement
and standalone package. Do not lower thresholds, consume final seeds while
selecting candidates, or rerun a failed final on the same seeds as fresh proof.

## Resume only after explicit user instruction

1. Read this handoff and inspect the existing handles below before any launch.
   Record authoritative terminal status and immutable artifact revisions. Preserve
   guards; never duplicate a live job or infer failure merely from a local timeout.
2. Independently collect completed existing jobs first. At pause the two new
   completed-but-unverified cases were 3p/snapshot0/neural [0,2) and the
   4p/search [0,4) collection piece. The pause revision is a candidate raw pin;
   collectors must actually verify its artifacts before any result claim.
3. Finish all 20 teacher pilot verifications and inspect the balanced mixture
   and measured runtime. Only then consider the remaining 140 chunks through the
   guarded launcher. Do not restart the three already replaced image-pull errors.
4. Collect all four search collection pieces per count, then run the strict
   merger and combined summarizer. Finish the three existing 6p guided arenas,
   then compare all counts/rules without suppressing regressions.
5. Once all 160 label shards verify, freeze the complete data manifest and job
   source; run the two planned gradient seeds on HF. Export and independently
   check them; require fresh complete-game acceptance against the parent and
   strong independent opponents before choosing a final candidate.
6. Only a convincingly strong, fixed candidate proceeds to the untouched final
   gate and actual-device/package checks. Multi-map training, browser integration
   and calibrated analysis are future work, not current deliverables.

Commands below are reference only, **not permission to run while paused**.
From the research repo root, after explicit resume and artifact inspection:

```sh
ai/.venv/bin/python ai/strong/collect-strategic-teacher-training.py 3 snapshot0 neural 0 2 b9ac766f397ce5ca5a0943bc8f2fbb0c4f6a543f
ai/.venv/bin/python ai/strong/manage-strategic-collection-slices.py collect 4 0 4 b9ac766f397ce5ca5a0943bc8f2fbb0c4f6a543f
```

After all four pieces of a given count verify, the merge CLI takes that count
(4, 5 or 6). Guided arenas use
`manage-multiplayer-search-transfer.py collect KEY N IMMUTABLE_REV` for
`KEY=parent,10101,10102`; run `compare --players 3 4 5 6` only when all three 6p
results verify. Summary scripts are not substitutes for the collectors.

## Exact job snapshot

The tables below are generated from the saved pause snapshot. COMPLETED does not
mean independently verified unless noted; statuses are not live. Configured
timeouts are maximum execution allowances, not predicted time remaining.

### strategic-teacher-training

| Case | HF job ID | Snapshot status | Timeout | Verification note |
| --- | --- | --- | --- | --- |
| 2p-economic-neural-0-2 | `6aca7e08095c5780893154bd` | COMPLETED | 4 h | Independently verified |
| 2p-economic-neural_economic-0-2 | `6aca7e0afee2c9007018b07f` | COMPLETED | 4 h | Independently verified |
| 2p-snapshot0-neural-0-2 | `6aca7e0bfee2c9007018b081` | COMPLETED | 4 h | Independently verified |
| 2p-snapshot0-neural_economic-0-2 | `6aca7e0cfee2c9007018b083` | COMPLETED | 4 h | Independently verified |
| 3p-economic-neural-0-2 | `6aca7e0d095c5780893154c3` | COMPLETED | 4 h | Independently verified |
| 3p-economic-neural_economic-0-2 | `6aca7e0efee2c9007018b085` | COMPLETED | 4 h | Independently verified |
| 3p-snapshot0-neural-0-2 | `6aca7e0ffee2c9007018b087` | COMPLETED | 4 h | Awaiting independent collection |
| 3p-snapshot0-neural_economic-0-2 | `6aca7e10095c5780893154c5` | ERROR | 4 h | Historical image-pull error; replacement below verified |
| 3p-snapshot0-neural_economic-0-2.retry-image-pull-1 | `6aca7fb3fee2c9007018b207` | COMPLETED | 4 h | Independently verified |
| 4p-economic-neural-0-2 | `6aca7e11095c5780893154c7` | RUNNING | 4 h | Pending |
| 4p-economic-neural_economic-0-2 | `6aca7e12095c5780893154c9` | ERROR | 4 h | Historical image-pull error; replacement below verified |
| 4p-economic-neural_economic-0-2.retry-image-pull-1 | `6aca7fb5fee2c9007018b209` | COMPLETED | 4 h | Independently verified |
| 4p-snapshot0-neural-0-2 | `6aca7e13fee2c9007018b089` | RUNNING | 4 h | Pending |
| 4p-snapshot0-neural_economic-0-2 | `6aca7e14fee2c9007018b08c` | COMPLETED | 4 h | Independently verified |
| 5p-economic-neural-0-2 | `6aca7e15fee2c9007018b090` | RUNNING | 4 h | Pending |
| 5p-economic-neural_economic-0-2 | `6aca7e16095c5780893154ce` | COMPLETED | 4 h | Independently verified |
| 5p-snapshot0-neural-0-2 | `6aca7e17fee2c9007018b092` | RUNNING | 4 h | Pending |
| 5p-snapshot0-neural_economic-0-2 | `6aca7e18095c5780893154d1` | COMPLETED | 4 h | Independently verified |
| 6p-economic-neural-0-2 | `6aca7e19fee2c9007018b094` | RUNNING | 4 h | Pending |
| 6p-economic-neural_economic-0-2 | `6aca7e1afee2c9007018b096` | ERROR | 4 h | Historical image-pull error; replacement below verified |
| 6p-economic-neural_economic-0-2.retry-image-pull-1 | `6aca7fb7fee2c9007018b20d` | COMPLETED | 4 h | Independently verified |
| 6p-snapshot0-neural-0-2 | `6aca7e1afee2c9007018b098` | RUNNING | 4 h | Pending |
| 6p-snapshot0-neural_economic-0-2 | `6aca7e1b095c5780893154d4` | COMPLETED | 4 h | Independently verified |

### strategic-training-collection-slices

| Case | HF job ID | Snapshot status | Timeout | Verification note |
| --- | --- | --- | --- | --- |
| 4p-search_geo-0-4 | `6aca7ca3fee2c9007018af5c` | COMPLETED | 4 h | Awaiting independent collection |
| 4p-search_geo-12-16 | `6aca7ca5fee2c9007018af62` | RUNNING | 4 h | Pending |
| 4p-search_geo-4-8 | `6aca7ca4fee2c9007018af5e` | RUNNING | 4 h | Pending |
| 4p-search_geo-8-12 | `6aca7ca4fee2c9007018af60` | RUNNING | 4 h | Pending |
| 5p-search_geo-0-4 | `6aca7ec5fee2c9007018b131` | RUNNING | 7 h | Pending |
| 5p-search_geo-12-16 | `6aca7ec7fee2c9007018b137` | RUNNING | 7 h | Pending |
| 5p-search_geo-4-8 | `6aca7ec6fee2c9007018b133` | RUNNING | 7 h | Pending |
| 5p-search_geo-8-12 | `6aca7ec7095c578089315550` | RUNNING | 7 h | Pending |
| 6p-search_geo-0-4 | `6aca8277fee2c9007018b4d9` | RUNNING | 10 h | Pending |
| 6p-search_geo-12-16 | `6aca827afee2c9007018b4e0` | RUNNING | 10 h | Pending |
| 6p-search_geo-4-8 | `6aca8278fee2c9007018b4dc` | RUNNING | 10 h | Pending |
| 6p-search_geo-8-12 | `6aca8279fee2c9007018b4de` | RUNNING | 10 h | Pending |

### multiplayer-search-transfer

| Case | HF job ID | Snapshot status | Timeout | Verification note |
| --- | --- | --- | --- | --- |
| 10101-6p | `6aca6babfee2c9007018a206` | RUNNING | 10 h | Pending |
| 10102-6p | `6aca6bad095c5780893147f0` | RUNNING | 10 h | Pending |
| parent-6p | `6aca6ba9fee2c9007018a204` | RUNNING | 10 h | Pending |
