# Power Grid AI — resumed 23 October 2026

The user explicitly requested “resume powergrid trainnig”. The existing goal is
active. HF Jobs are authorized for training and evaluation. No candidate has
passed the full strength gate, and no AI has been published to production.
This document supersedes the pause instruction in the
[10 October handoff](HANDOFF-2026-10-10-PAUSED.md), which retains the earlier history.

## Workspace and authoritative records

- Research checkout: `/home/eliheros/Documents/Codex/2026-09-26/je-x20-2/work/powergrid-ai`.
- Branch: `ai/germany-baseline`, remote `git@github.com:boardgamers/powergrid`.
- Interpreter: `ai/.venv/bin/python`. Use cached HF and SSH authentication;
  never print tokens or include them in documents, source archives or Git.
- Artifact repo: `coyotte508/powergrid-ai-germany-v1` (private).
- Source dataset: `coyotte508/powergrid-ai-training-v1`.
- Target: `ssh minipc`, AMD 8840U. The local HX370 is not the target benchmark.
- Latest explicit job snapshots:
  [teacher jobs](strong/strategic-teacher-training-status-v1.json) and
  [development arenas](strong/strategic-correction-screen-status-v1.json).
  Read its timestamps and inspect those exact handles; do not infer current
  state from this document. Local launch guards are under
  `ai/runs/strategic-teacher-training-launches-v1/` and
  `ai/runs/strategic-correction-screen-launches-v1/`. Refresh these safely with
  `ai/.venv/bin/python ai/strong/refresh-strategic-correction-jobs.py`;
  this only inspects existing jobs. The three historical image-pull failures
  retain explicit links to their completed replacement jobs. Do not retry them.
- Production/UI checkout remains separate. Do not merge or publish research
  there as part of resuming training. Do not comment on GitHub issues.

## Recovered evidence

No HF jobs were active at resume. All intended jobs left at the pause completed.
The three old image-pull errors already have completed replacement jobs and
must not be retried again. Recovered raw artifacts are pinned to model-repo
revision `7240a51338ba19cc47c437c955a61bb46f1ea70e`.

1. All 20 teacher pilot shards are independently verified: 240 roots with both
   continuation modes, 230,592 full counterfactual rollouts, no caps. The
   independent-batch validation diagnostic is +0.0743 mean paired advantage
   selecting on A/evaluating on B, and +0.0732 in reverse, with 65.8% agreement.
   These are conditional simulation diagnostics, not whole-game strength.
2. The full collection is verified and merged: 3,840 unique games, 7,680 twin
   executions and 200,775 public decision states. All 12 remaining 4–6p geographic
   search slices were checked, and original records and indices preserved.
   This collection contains more states than the fixed 1,920-root label design;
   do not silently change the selected roots or train/validation split.
3. All three 6p guided-search comparisons are verified: 192 games per model,
   eight paired deals with every seat and all four rule combinations. Every
   model lost 9.375 percentage points relative to its raw policy; the paired
   deal 95% interval is [-17.1875,-1.5625] points. Guided search remains unqualified.
   Preserve the earlier 5p Recharged/open regression as well.

Machine-readable results:

- `strong/strategic-teacher-training-results-v1.json`
- `strong/strategic-training-collection-combined-results-v1.json`
- `strong/multiplayer-search-transfer-results-v1.json`

## Verified checkpoint at 22:21 UTC, 23 October

- All 160 teacher shards are verified: **1,836,672 completed rollouts**, 1,920
  complete-mixture roots, 1,440 train and 480 validation. Each player count has
  384 positions; nomination, bid and building each have 640. No truncations.
- Complete manifest SHA256:
  `6135dba264e18bdc0d8002ca50719bb3340f94b05e22221812864295fe651e57`.
  It is frozen into the training source; do not edit it after submission.
- Parent reference: 25/27 complete opponent/count cells, 6,016/6,720 games.
  Five- and six-player search cells still run on their original handles.
- GPU job **`6adbddc9046eb82b1ecd7ac0`** was submitted at 22:20:56 UTC on L4,
  three-hour timeout, both seeds 11101/11102. Inspect its exact handle; do not
  resubmit. No new trained result has been verified yet.
- Source/data preflight passed: all 1,920 original parent proposals reproduced,
  3,196 negative action advantages retained, uncertainty weights 0.2733–1.0;
  all 2,553 serving fixtures and 160 zero-correction/parent games passed.
- This is progress, not qualification. The fresh parent versus A260 result is
  27.6% over 192 games/16 deals, 95% interval [21.88%,33.85%], below the 40% floor.
  Versus geographic search, parent win shares at 2/3/4 players are 49.22/25/23.05%;
  sealed-auction weaknesses remain. Preserve all adverse cells in comparisons.

## Work resumed

All 140 remaining teacher shards (deals 2–16) were submitted using the original
guarded launcher. Each of the seven 20-job batches covers 2–6 players, both root
sources and both continuation modes. Exact handles and timeouts are saved in
the status snapshot and launch guards. The first full snapshot had 67 running,
72 scheduling and one completed; this is historical, not a live count.

The first resumption checkpoint had 30/160 independently verified shards.
The live verified counts are in `strong/strategic-teacher-training-results-v1.json`.
The faster economic-opponent jobs finishing first does not make a partial dataset
ready for gradients; all 160 shards and 1,920 complete-mixture roots are required.

These are CPU simulation jobs, using 24 engine workers and single-thread FP64
ONNX inference. The lighter CPU image checks batching parity on all 2,553
serving fixtures before generating labels. Each shard retains 48 independent
worlds per A/B batch and the full 2,400-step continuation horizon. Runtime
admission uses all 20 verified pilots, twice the slowest matching root and 25%
timeout headroom. Timeouts are 4h or 5h; do not shorten games or samples to fit.

Frozen teacher source:

- Dataset revision: `837d94e14272163c33e5e55fa9c24b24686a28ae`
- Archive: `strong-source-strategic-teacher-training-20261010-v1.tgz`
- SHA256: `a011f9ee4b8116b99220913a7db9d00849e9e593137cdb7e435e116fcafdd6c3`
- Protocol SHA256: `3c39786cc6c44a3838d3c4183c312c94a26563222b2720572010b76bbdd62a76`
- Roots SHA256: `f0fd62b4dd75c6b6c0936adeb1ffc75a2747cb2c62debe6b5d0aba60dbb4a091`

Never edit those frozen overlays. Preserve errors and ambiguous launch intents.
Inspect exact existing handles before any retry; never treat a delayed tool
response or absence of artifacts as evidence that a job did not start.

## Next training stage

The design remains `strong/strategic-correction-design-v1.json`: freeze the
complete discard-correction 10102 parent and train a 97,473-parameter head on
paired advantages for nominations, bids and building. All other decisions and
the value head remain unchanged. The exact public shortlist plus the parent
proposal is used; the fixed margin is 0.025. Seeds 11101/11102 are fixed before
gradients. Keep negative and uncertain evidence and whole-deal data splits.

New source builder and launcher:

```bash
ai/.venv/bin/python ai/strong/build-strategic-correction-source.py
ai/.venv/bin/python ai/strong/launch-strategic-correction.py
```

The builder rejects incomplete manifests before upload. It preserves the
teacher engine, parent and base features byte-for-byte, overlays only explicit
correction/serving files, checks all 1,920 roots, and uploads an immutable source
archive. The launcher requires that full source/data check and an exclusive
launch guard before submitting one L4 GPU job for both seeds. Supply the cached
token through the environment only. The guarded job above is now submitted; do not rerun the launcher.

Code-only checks use `build-strategic-correction-source.py --code-only` and
never upload a training source or admit training. The zero correction passed
strict parent/ONNX checks on 2,553 positions. The arena whitelist now recognizes
feature revision 4.3 at all player counts. A separate 160-game plumbing check
passed across 2–6 players: every complete game record was identical between
zero correction and parent. Evidence is in
`strong/strategic-correction-source-code-preflight-v1.json`.

The public-information check now also mutates opponents' submitted sealed bids:
422 sealed-auction fixtures pass, with identical features and shortlists. Actual
trained exports must pass `strategic_correction_check.py`: all 2,553 serving
positions, unchanged parent values and out-of-scope actions, and native/ONNX
parity over all 1,920 labeled roots. The independent training collector additionally
checks parent tensors, optimizer steps, fixed validation selection, checkpoint
hashes and actual exported actions before writing evaluation model pins.

The trainable parent is pinned to model-repo revision
`b115a2d78aae095e51fb72a5535b3507abdf90c0`,
`runs/discard-correction-v1/10102/best.pt`, SHA256
`66a10b831a54843063bbca89743a542ed1f89515a16452a40483eef369c59bd8`.
Its serving ONNX SHA256 is
`57f8255e79b991ba466f91e953d0bca6868144bb543577fc0dad8ade387ebf68`.

## Frozen training source and collection

- Descriptor: `strong/strategic-correction-source-v1.json`.
- Dataset revision: `46d6986a28db0db26122b7188d833bcfb2ce8c8b`.
- Archive: `strong-source-strategic-correction-20261023-v1.tgz`.
- SHA256: `bea355639fa669217bd2636d8aa755976f4a291c0abb7daa9c4a00f35462cce5`.
- Full preflight: `strong/strategic-correction-source-preflight-v1.json`.
- Launch guard: `ai/runs/strategic-correction-launch-v1/launch.json`.
- Live snapshot: `strong/strategic-correction-job-status-v1.json`.
- Expected outputs: model repository prefix `runs/strategic-correction-v1`.
- Complete admission evidence: model-repo revision
  `67bb0d978b404ca49dfd034cb19c9dfc4ea8721d`, prefix
  `runs/strategic-correction-training-admission-v1` (178 files).

Do not edit training source overlays, design, or full label manifest while the
job runs. On completion, pin the model-repo revision and independently collect:

```bash
ai/.venv/bin/python ai/strong/collect-strategic-correction.py REVISION NEW_OUTPUT_DIRECTORY
```

The collector must pass for both seeds before either enters evaluation. A failed
job or check remains failed; inspect its original logs and uploaded status rather
than silently retrying or weakening tolerances. The source package intentionally
keeps the pre-gradient design/manifest flags unchanged as historical metadata.

## Fresh whole-game evaluation

The evaluation implementation and frozen source are ready. All **108 parent
reference shards** have been submitted, covering 6,720 games. Do not duplicate
those launches. The two runtime probes also completed and were independently
verified: 8 two-player games in 119.84s and 24 six-player games in 1,258.66s,
both against geographic search, without truncation. The conservative admission
calculation permits four-deal shards with a four-hour job timeout.

- Source descriptor: `strong/strategic-correction-screen-source-v1.json`.
- Dataset revision: `2c33a8878a742eabf54b94b7e2148a63223318e8`.
- Archive: `strong-source-strategic-correction-screen-20261023-v1.tgz`.
- SHA256: `162f93944f508853dcf446af74f2ba9a331e557d337a5b7193e2f764817562fb`.
- Protocol SHA256: `cd038070dcf7f875cecab0a9ecfa095447675cfd75bc3584c157fd1d4261787a`.
- Results: `strong/strategic-correction-screen-results-v1.json`.
- Exact model manifests: `strong/strategic-correction-screen-pins-v1/`.

Do not modify frozen evaluation overlays while these jobs run. The runtime
retains the original engine and features; seven explicit overlays support the
new correction and audited deal offsets. Preflight verified 40 plumbing games,
nonzero deal offsets and nine rejected corruptions. The arena outer cap remains
1,600 steps and search horizon 2,400; a cap invalidates the result, never turns it
into a scored ordinary game.

Collect a completed shard at an immutable model-repo revision:

```bash
ai/.venv/bin/python ai/strong/manage-strategic-correction-screen.py collect parent N OPPONENT START END REVISION
ai/.venv/bin/python ai/strong/manage-strategic-correction-screen.py compare
```

Only complete cells enter comparison, retaining all missing cells explicitly.
Both trained seeds remain separate contrasts with the parent. Training collection
uses `collect-strategic-correction.py REVISION NEW_OUTPUT_DIRECTORY`; only after
independent verification does it produce pins for 11101/11102. Each then needs
its own verified 2p and 6p search runtime probe before launching its 108 shards.
Neither seed has entered these arenas yet; their training job is now submitted.

Independent verification records and preflight logs are also archived in the
private model repository at revision `141ef2843681c3edb883ef79debe8462cf943c70`,
prefix `runs/strategic-correction-resume-evidence-v1` (258 files). This snapshot
contains partial results, not a completed training or strength claim. See
`strong/strategic-correction-resume-evidence-v1.json` for the manifest hash.

## Ordered continuation

1. Inspect submitted jobs and collect completed teacher shards at an immutable
   artifact revision with `collect-strategic-teacher-training.py N FAMILY MODE
   START END REVISION`. Existing verified folders should be retained, not
   overwritten. Reconcile any partial folder before retrying collection.
2. Run `summarize-strategic-teacher-training.py`. Require 160 verified shards,
   1,920 complete-mixture roots,1,440 train/480 validation, and no caps. Freeze
   the complete manifest; do not train from a convenient partial subset.
3. The frozen source is checked and the HF GPU job is submitted. Inspect and
   collect both seeds on completion; verify frozen parent tensors, epoch selection,
   strict exports, legal responses and source/data hashes independently.
4. Continue the fresh development protocol fixed in
   `strong/strategic-correction-screen-protocol-v1.json`: 20,160 games across
   parent and both seeds, 27 count/opponent cells, all four rules and every seat.
   Economic/search opponents, capacity behavior at 2p and frozen A260 at 3p are
   primary diagnostics; legacy/heuristic/rush are included. The parent reference
   is already running. Collect it and run each independently verified new seed
   with the frozen evaluator and matching deal partitions.
5. Report absolute strength and paired gains, including adverse cells. The
   reserved `final-protocol-multiplayer.json` remains unchanged and unused.
   No training-target result or small diagnostic substitutes for that gate.
   The final launcher now accepts 4.3 only with matching strategic encoder and
   evaluator bytes; eleven contract tests passed without real submissions. An
   archive audit found the development source still has the older arena wrapper
   (`strong/final-strategic-runtime-readiness-v1.json`). Before final qualification,
   derive a fresh source from the frozen development evaluator with only the
   provenance-aware arena-job.py overlay. Verify that wrapper with the exact
   selected candidate on development-only probes. Neither the older October 10
   source nor the current development archive is directly ready for final use.
   No candidate is selected and no reserved seeds have been used.
6. Benchmark the exact selected model/configuration on the actual 8840U and
   verify the extracted standalone serving package before any deployment.

Scope remains Germany, automatic setup, 2–6 players, original/Recharged and
open/sealed auctions. All players' money is allowed. Hidden deck order, random
seeds, submitted sealed bids and queued plans stay excluded. Other maps and
calibrated round-by-round value analysis remain future work.
