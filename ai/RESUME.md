# Power Grid AI — active continuation, 10 October 2026

Research resumed following the explicit goal continuation. **No candidate has
passed the complete strength gate. Nothing is deployed, and reserved final seeds
remain unused.** The UI work in the canonical checkout is separate.

The current research checkout is
`/home/eliheros/Documents/Codex/2026-09-26/je-x20-2/work/powergrid-ai`, branch
`ai/germany-baseline`. New continuation experiments intentionally use immutable
source-v36 as the control runtime, not the later engine/UI revisions. The saved
4 October handoff below remains historical context.

Current work: `strong/neural-continuation-protocol-v1.json` freezes a comparison
of learned-policy continuations against the completed heuristic teacher audit.
Job identifiers and source/model hashes are in
`strong/neural-continuation-status-2026-10-10.json`. Inspect those actual HF jobs
before launching anything else. The main new code is
`strong/continuation-rollouts.cjs` and `strong/audit-neural-continuations.py`.
There are no gradient-training jobs in this new cohort.

The prior goal turn handled an unrelated UI revert and made no AI progress.
This resumed turn revalidated that HF had no live jobs, checked all five old
result files against their immutable HF revision, implemented the neural
continuation path, and launched the new diagnostic cohort. Do not count the
repeated historical audit as a new strength result.

New checks: exact heuristic-control reproduction, worker partition/legality/cap
checks, hidden-deck/sealed-bid invariance, and a local 24-rollout inference smoke
check all passed. The two-player HF shard completed all 6,240 rollouts without truncation. Its
12 positions had disjoint A/B neural winner sets in 4 cases. Neural-selected
actions had a small positive confirmation gap under neural continuation but
negative gaps under each heuristic continuation; do not promote the teacher.
The 3–6p shards were confirmed RUNNING at the latest recorded observation.
In the first batches about 62% of wall time was engine/IPC work and about 35% model inference;
CPU-performance workers are used pending the full timing report. These tiny
runtime samples do not establish throughput for every player count.

Next actions:

1. Collect all five live jobs, pin their final artifact revision, verify hashes,
   exact cells, both A/B batches, model revision, and completion counts.
2. Compare A/B winner-set stability with matched 48-sample heuristic controls.
   Inspect root-proposal coverage and original/sealed bidding separately.
   Missing/capped continuations are missing evidence, never automatic losses.
3. Only if supported, build a policy-guided teacher candidate and test full games
   against frozen independent opponents on development deals. A reliable target
   is not by itself a stronger policy. Preserve strong baselines and all rule/count
   cells; this diagnostic is not evidence for final qualification or deployment.
4. Prepare the next HF training pilot from those results, with opponent mixtures,
   self-play and fixed independent screening. Keep the existing strength gates.

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
