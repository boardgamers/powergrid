# Power Grid AI — paused handoff, 25 October 2026

**The user requested: finish the current run, then hand off. The research goal
is PAUSED. Do not start another training or evaluation experiment.** This document
supersedes active instructions in older handoffs. It does not authorize resuming
the 10,080-game development grid or using final qualification seeds.

<!-- CURRENT-RUN-START -->
The current run is being finished: the four original conservative-auction
runtime pilots, 64 games in total. Both two-player pilots are complete and
independently verified; both six-player pilots are running. No new HF jobs were
submitted during this handoff. The broad coordinator was stopped at
**12:13:24 UTC**, before any development submissions. Its STOP marker is intact.

A collection-only finisher, **PID 1146868 / execution session 24085**, watches
the four original handles and exits after auditing their results. It cannot
submit jobs, train, restart a failed job or proceed to the next experiment.
Its state is `runs/conservative-auction-runtime-finish-v1/state.json`; its log is
`runs/conservative-auction-runtime-finish-v1.log`. Inspect the actual process
before touching it. Do not start a competing collector.

The completion-only heartbeat **`finish-power-grid-handoff`** checks every
15 minutes. Once the originals are terminal, it will verify/archive the results,
replace this pending section, push the final handoff and pause itself. While the
finisher is live it must not run a competing collector. This follow-up is limited
to completing the existing run; it cannot authorize another experiment. The
original handoff checkpoint was pushed as **d8d931b**.
<!-- CURRENT-RUN-END -->

No AI is qualified or deployed. The final strength gate is unchanged, and its
reserved seeds have never been used. The production game/UI is separate.

## What we have achieved

The research progressed from a weak imitation baseline to a substantially
stronger learned policy, with careful evaluation across **Germany, 2–6 players,
original/Recharged and open/sealed auctions**. Strength on other maps is not
established. The JavaScript engine remains authoritative; no Rust engine rewrite
was completed. All gradient training ran on HF Jobs.

- Early human-data work audited 4,007 BGS records; only 32 supported, exactly
  replayable games supplied the corrected Germany/3p baseline. That initial
  model failed against the existing bot. Human data helped replay validation
  and bootstrapping; it did not establish strong play.
- Better observations and stronger opponents followed: economic, rush,
  geographic-search and frozen neural baselines. The model sees every player's
  **money**, cities, plants, fuel, order, players left to act, replenishment and
  territory/building capacity. Hidden future decks and submitted sealed bids
  are excluded. Generic geography features do not imply other-map strength.
- Search imitation, league/self-play work, discard corrections and later
  policy-iteration correction heads produced useful improvements. The latest
  completed policy-iteration cohort has eight trained seeds and four ensembles.
- A large five-arm development comparison completed **33,600 games**, 6,720 per
  arm, with 16 independent paired deals per cell. The current research reference
  is **frozen-1**. Against geographic search, its four-player win share improved
  from **30.859% to 51.563%**; Recharged sealed improved from **15.625% to 39.063%**.
  Those figures are paired development evidence, not a final qualification.

| Players | Parent vs search | frozen-1 vs search |
|---|---:|---:|
| 2 | 48.828% | 52.734% |
| 3 | 20.313% | 44.792% |
| 4 | 30.859% | 51.563% |
| 5 | 34.375% | 45.313% |
| 6 | 37.630% | 45.313% |

The four-player overall estimate includes 256 games; its Recharged-sealed cell
includes 64 games. All seats and four rules share the same 16 independent deals.
Weak cells remain: two-player Recharged/open vs search **34.375%**, four-player
vs legacy **86.719%** (below the 90% target), and six-player Recharged/sealed vs
search **23.958%**, below the parent's **27.083%**. Do not average these away.
Source: `strong/policy-iteration-development-comparison-v2.json`.

## Which approaches to continue, and which to stop

**Selective auction search is still a reasonable next experiment; no hybrid is
yet validated for deployment.** The current paused pilots measure its cost.

The completed broad hybrid screen comprised **8,400 games / 135 original jobs**,
five arms and four paired deals per cell. Auction search helped several sealed
auction cells, but four-player original/open vs search fell **81.25% → 31.25%**,
and five-player Recharged/open fell **70% → 50%**. Building search regressed at
every player count; combining it with auction search also underperformed
auction search. Do not scale those unchanged implementations or retrofit a
rule-specific switch to the favorable results. See
[HYBRID-SCREEN-2026-10-24.md](HYBRID-SCREEN-2026-10-24.md).

The separate resource-search screen completed **3,360 games / 54 jobs**. Its
equally weighted search-opponent result was **−9.1875 percentage points**,
exploratory paired whole-deal 95% interval **[−16.3648, −1.5518]**. Every count
regressed. Replanning inconsistency was observed, but is not an established
cause of the losses. Do not continue that recipe unchanged. See
[RESOURCE-SEARCH-SCREEN-2026-10-25.md](RESOURCE-SEARCH-SCREEN-2026-10-25.md).

We also trained a four-member learned opponent ensemble from **418,686 teacher
rows**, with 2,560 collection games plus 640 twin replays. It trained successfully
on HF and exported exactly. Validation best was around epochs 9–10; later
epochs overfit. Held-out agreement improved only about 0.51 percentage points
over its economic prior. Better training loss was not sufficient evidence.

The completed continuation-fidelity study included **480 positions / 480 jobs /
23,040 continuations**. Absolute action-margin error was **16.79 pp** for the
existing population and **17.33 pp** for the learned opponent; difference
**+0.541 pp**, exploratory whole-deal 95% interval **[−1.234, +2.316] pp**.
It did not establish better fidelity. Keep the existing population; test the
learned model only as additional coverage in a separate arm. Do not extend its
unchanged training recipe. See
[SURROGATE-FIDELITY-2026-10-25.md](SURROGATE-FIDELITY-2026-10-25.md).

These negative results justify stopping particular approaches. They do not
establish a general AI plateau. The next useful question is whether a conservative
auction override preserves gains without the earlier regressions, rather than
whether more epochs or a larger GPU can improve the same failed recipe.

## Current model and serving feasibility

- Model repo: `coyotte508/powergrid-ai-germany-v1` (private).
- Frozen-1 revision: `6b6009756d7b5968bc5b6425efc84a94aab2a1d6`.
- Export: `runs/policy-iteration-training-v2-frozen/ensemble-1/derivative/inference64.onnx`.
- SHA256: `55331f43379e8fe89025d93b1a7a48c88e0ea39b4ebd3a7ef8240d4b62753530`.
- Feature schema 4.3: 1,217 state features / 101 action features, four correction
  heads. The hybrid research control additionally applies the strict loss filter;
  an ONNX file alone is not the complete hybrid policy.
- **Actual AMD 8840U model-only** validation covered 10,212 exact requests:
  median 4.3–5.9 ms, p95 7.0–8.8 ms, cold start 214–255 ms across tested models.
- Learned-opponent component benchmark on that machine passed 24 roots / 384
  continuations, with exact HF parity apart from elapsed time. Median batch
  2.134s, maximum 7.340s; eight workers, one inference thread. This is not
  complete-hybrid latency.

The standalone public-state runner, legal-action checks, provenance receipts and
full-game auditing exist and have engineering parity evidence. They distinguish
engineering tests from new strength evidence. The exact selected hybrid still
needs final execution integration and a complete-policy 8840U benchmark.
Browser deployment has not been established. The value head remains uncalibrated;
it is not ready to present reliable round-by-round winning probabilities.

## Original current-run handles and evidence

| Arm | Players | Games | Original HF job |
|---|---:|---:|---|
| Conservative population | 2 | 8 | `6addea031e112550ce7eaa88` |
| Conservative population | 6 | 24 | `6addea031e112550ce7eaa8a` |
| Conservative dual population | 2 | 8 | `6addea04046eb82b1ece4faf` |
| Conservative dual population | 6 | 24 | `6addea04046eb82b1ece4fb1` |

These are **runtime-only** deals: `conservative-auction-runtime-v1-{players}p`,
all seats/four rules vs search_geo. Never mix them into the strength comparison.
Each original job uses cpu-upgrade, four simultaneous games, four search workers,
one inference thread, five-hour timeout. Jobs terminate on completion, failure
or timeout; the finisher never replaces a failed handle.

Authoritative source descriptor: `strong/conservative-auction-runtime-source-v1.json`.
Source dataset `coyotte508/powergrid-ai-training-v1`, revision
`6edcec8f03e3bf0c84f08ed2c02e458e887d1ca5`, archive
`strong-source-conservative-auction-runtime-v1.tgz`, SHA256
`99227f1fc4bd8976e168db88f2c330eeff9947d320526d83dffaeff59b492328`.
Source manifest: `187812b75ce569ea8302cd405d0dfc7b2b79d2eb5837970dbefc8c0db1e39521`.
All 1,522 previous source files were preserved; this source has 1,540 files.

Per-job launch guards, raw artifacts and verification reports are under
`runs/conservative-auction-runtime-hf-v1/<case>/`. The complete aggregate is
`strong/conservative-auction-runtime-results-v1.json` once all four pass.
Every original raw evidence archive is identified by immutable revision and
SHA256 in those reports. The original source/preflight archive descriptor is
`strong/conservative-auction-runtime-launch-evidence-v1.json`; the pre-pause
tooling snapshot is `strong/conservative-auction-development-readiness-v1.json`.

## Resume only after the user asks

The prepared next design is **10,080 fresh development games**, three arms ×
27 opponent/count cells × eight paired whole deals, all seats and four rules:
filtered model, conservative population auction search, conservative dual
population auction search. It has **not run**.

Protocol: `strong/conservative-auction-development-protocol-v1.json`, SHA256
`ab4dbb7fdde1689d988671ca4abb4bd25ed52cd912dc0d4a94c6ca7f61c57e61`.
Eight matched sampled worlds per included population; override only for pooled
terminal-credit advantage strictly above **1/8**, with nonnegative advantage in
each population. Ties favor the baseline. This threshold is a heuristic,
**not calibrated confidence**. Opponent identity from the evaluation arena is
not fed to the policy. Future focal play is approximated by the filtered model.

The planner and manager are implemented and have ten schedule/submission tests,
but actual development-source preparation and HF execution remain unverified.
`prepare-conservative-auction-development-v1.py` derives batching/resources from
all four completed pilots, using cost only: doubled measured time, 900s setup,
three-hour batch target and memory headroom. `manage-conservative-auction-development-v1.py`
preserves exclusive submission guards, limits active jobs to 64, and audits all
raw receipts. Do not change frozen policies during a comparison.

**Do not restart the old coordinator.** PID 1061599 / session 42688 was stopped
on purpose, with zero development jobs submitted. Keep its STOP marker and
history in `runs/conservative-auction-development-coordinator-v1/`. Its startup
refuses existing state. On an explicit future resume, first inspect the finished
pilot evidence and all original guards; then create a separately identified
owner or drive the existing prepare/upload/launch/collect stages deliberately.
Do not delete guards/state to make an old launcher run again.

If the finisher is interrupted, inspect its PID and original job statuses before
collecting. The original runtime manager's `collect` operation only collects;
the `launch`, `prepare` and `upload` operations are not needed to finish this run.
Preserve failures/partial outputs. No retry just because an observation times out.

After a resumed development comparison, report every opponent/count/rule cell,
paired whole-deal intervals and costs. Never promote from an aggregate while
hiding regressions. The original final gate remains **20,160 games / 320 shards /
26 groups**, including independent-search and legacy requirements and actual
complete-policy serving/export checks. Protocol `strong/final-protocol-multiplayer.json`,
SHA256 `7f0336c8784faf8f18e046b95b88e0ab1be7c2de1c0ec4d3eec96f0a415286ce`.
No final candidate has been chosen. Reserved final seeds are unused.

## Locations and recovery

- Checkout: `/home/eliheros/Documents/Codex/2026-09-26/je-x20-2/work/powergrid-ai`.
- Git: `git@github.com:boardgamers/powergrid`, branch **ai/germany-baseline**.
  Last research implementation before this handoff: **c2dcf86**.
- Interpreter: `ai/.venv/bin/python -B`; use cached HF/SSH authentication.
- Actual target: `ssh minipc`, AMD 8840U. The local HX370 is a different machine.
- Production checkout: `/home/eliheros/code/powergrid`. Do not publish or merge
  research into it while saving/resuming this handoff. Do not comment on GitHub.
- `ai/runs/` is ignored. Git holds source, descriptors and reports; private HF
  holds large immutable archives. Recover by exact descriptor revision/SHA256,
  verify manifests, and restore original source, guards and evidence. Do not
  silently regenerate missing evidence or substitute a current repo HEAD.
- Three historical modified files are deliberately not included in this handoff
  commit: `strong/policy-iteration-development-status-v2.json`,
  `strong/policy-iteration-labels-results-v2.json`, and
  `strong/policy-iteration-labels-status-v2.json`. Preserve their local changes.

The older [10 October handoff](HANDOFF-2026-10-10-PAUSED.md) covers the beginning;
the [23–25 October research log](HANDOFF-2026-10-23-RESUMED.md) retains the detailed
execution history. Its historical “active”, “next” and “running” statements do
not override this pause. Exact experiment descriptors are indexed in
`strong/experiments.json`. No credentials belong in any handoff or archive.
