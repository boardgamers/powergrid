# Power Grid AI handoff for training across maps

Updated 31 October 2026. The user wants the next model to pursue generalized
training across Power Grid maps. The existing learned bot is Germany-only,
including its observation and action representation. Preserve it as a reference
while designing the broader model. No generalized model or new training run has
been created for this handoff.

## Access and starting point

Access was checked directly on 31 October 2026:

| Material | Location | Access |
| --- | --- | --- |
| Engine, AI code, handoffs, result summaries and archive descriptors | [boardgamers/powergrid, branch ai/germany-baseline](https://github.com/boardgamers/powergrid/tree/ai/germany-baseline/ai) | Public; anonymous GitHub access verified |
| Model weights, feature/target datasets and evidence archives | [coyotte508/powergrid-ai-germany-v1](https://huggingface.co/coyotte508/powergrid-ai-germany-v1) | Private; authenticated metadata confirms this, anonymous API returns 401 |
| Training source bundles and supporting data | [coyotte508/powergrid-ai-training-v1](https://huggingface.co/datasets/coyotte508/powergrid-ai-training-v1) | Private; authenticated metadata confirms this, anonymous API returns 401 |

The public Git branch does not contain every large dataset, weight or raw run.
An external model can read the handoffs and code without credentials, but needs
authorized HF access to reproduce existing inference/training. Use a secure
credential mechanism in its execution environment; never paste tokens into the
handoff, chat, Git, commands recorded in public logs, or model prompts. Read access
to the private repositories is sufficient for downloading; submitting Jobs or
writing artifacts requires the corresponding additional access. Repository
visibility has not been changed.

Existing source and evidence descriptors pin immutable HF revisions and SHA-256
hashes. Some original outputs also live in HF buckets or ignored local run
directories; use the verified evidence archives where available. This is a
research repository with several datasets, not one public packaged training set.

Local checkout:
`/home/eliheros/Documents/Codex/2026-09-26/je-x20-2/work/powergrid-ai`,
branch `ai/germany-baseline`. Research code/results immediately before this
handoff are at commit `14e31215e8cde26081b504f8fc438a9f70d65079`.

Read these first:

1. This handoff for the new direction, access and recovery entry points.
2. [TARGET-GENERALIZATION-2026-10-31.md](TARGET-GENERALIZATION-2026-10-31.md)
   for the completed latest experiments and their limitations. Its title refers
   to learner/target generalization, not an implemented multi-map model.
3. [CURRENT-FULL-SERVING-2026-10-29.md](CURRENT-FULL-SERVING-2026-10-29.md)
   for the actual mini-PC integration and measured latency.
4. [HANDOFF-2026-10-25-PAUSED.md](HANDOFF-2026-10-25-PAUSED.md) for historical
   model development, baseline results and negative hybrid experiments.
5. [RESUME.md](RESUME.md) for chronological operational history. Older paused,
   running and next-action notices are historical, not instructions to restart.

## What exists and what remains unproven

The retained model is `frozen-1`, feature revision `4.3-strategic-correction`,
with 1,217 state features, 101 action features and four correction heads.
Research covers automatic Germany games, 2–6 players, Original/Recharged,
open/sealed auctions and public money. The exact current-runtime scope is in
[current_engine_scope_v1.py](strong/current_engine_scope_v1.py); it also excludes
options such as randomized maps, manual region/color drafts and alternate decks.
Scope extensions need representation and rule checks, not just a wider router.

In the earlier 33,600-game development comparison, the frozen model's four-player
win-credit rate against geographic search was 51.563%, versus 30.859% for its
predecessor. Four-player Recharged sealed improved from 15.625% to 39.063%.
Those are development results from 16 independent deal seeds repeated across
seats/configurations. They are not human-level strength measurements or a final
current-engine qualification. Source:
[policy-iteration-development-comparison-v2.json](strong/policy-iteration-development-comparison-v2.json).

Current-engine serving on the actual AMD Ryzen 7 8840U passed 2,553 positions
per policy, 5,106 total requests, with legal actions and checkpoint bindings.
The fast filtered policy's warm median/p95 was 10.15/16.27 ms. Searched auction
requests were 5.34/11.20 seconds. These are fixture-distribution end-to-end policy
timings, excluding platform queueing/downloads, not production latency guarantees.
The model file alone is not the complete policy: public projection, legal moves,
features, filters and search settings are part of its identity.

No model has passed the reserved final strength qualification or been deployed
from this research. Value outputs are not calibrated player win probabilities.
The older current-engine confirmation has an unresolved evidence issue; see
the operations section below. Do not present its partial evidence as complete.

## Why Germany is a real implementation restriction

- [core.cjs](core.cjs) imports the Germany maps and builds a fixed `CITIES` list.
  Its action features include a city identity one-hot vector.
- [features-v4.cjs](strong/features-v4.cjs) rejects other maps and encodes city
  ownership by that fixed list. Revisions 4.1 through 4.3 build on it.
- [current_engine_scope_v1.py](strong/current_engine_scope_v1.py) explicitly
  rejects other maps before inference in the current confirmation runtime.
- [spatial.cjs](strong/spatial.cjs) already has reusable region/island ownership,
  empty slots, occupancy and connection features. [economics.cjs](strong/economics.cjs)
  supplies useful public economy features, but map-specific assumptions and
  hard-coded capacities still need review.

Do not remove the Germany guards and feed other maps into the existing weights.
Generic economics and serving infrastructure can carry over, but the fixed city
features and newly introduced rules require a new representation and training.

## Latest completed experiments

All jobs in the latest iteration are finished; no follow-on jobs were launched.

- A 960-game nomination-correction screen found no consistent improvement over
  the retained parent. All four candidates were below it in Recharged sealed
  at four and six players. This was a small four-deal-per-count screen; the
  remaining 35 shards / 2,240 games were deliberately deferred.
- All 16 neural fits reduced training error while increasing final-epoch
  validation error. Selected earlier checkpoints also failed to establish a
  full-game improvement. More epochs on that same batch are not justified.
- The sealed-bid diagnostic audited 6,160 continuations across ten training roots,
  with disjoint sampled worlds for selecting and evaluating bids and zero caps.
  Reference-search-selected actions gained only about 0.18 percentage points of
  conditional sampled terminal credit against reference continuations. This is
  not a whole-game win-rate improvement, and ten roots cannot establish strength.
- HF job `6ae5bddf0e0338d1bb7d1fe6` completed four regularized tree fits using the
  existing 5,770 nomination targets. Training/checking took 11.52 worker seconds,
  excluding setup/queue. All saved models and predictions passed independent CPU
  auditing. The best fixed ensemble's mean sampled validation advantage was
  +0.002775, offering no compelling improvement over the earlier neural recipe.

Keep the parent. The fixed-target learner experiment is closed. The next useful
hypothesis is fresh, varied data plus an explicit test of data/target quality,
now combined with the user's priority of support across maps. This is evidence
that particular recipes stalled, not that further AI improvement is impossible.

## Proposed next work

The user accepted prioritizing generalization across maps. The following is an
implementation proposal for the successor to assess, not completed work:

1. Inventory supported engine maps and their rule differences. Establish a
   compact compatibility matrix for legal actions, auction resolution, resource
   markets/refills, region/island access, Step transitions, plant limits and
   victory conditions. Use the engine's real rules rather than inferring them
   from a map name or importing Germany assumptions.
2. Introduce a new schema with variable city/edge/player sets and explicit masks.
   Encode connection costs, ownership/occupancy, building availability, region
   and island membership, access restrictions and relevant global rule features.
   Use a graph/set architecture or another permutation-aware representation;
   choose by correctness and measured cost rather than architecture fashion.
   Candidate build actions should reference the relevant city representation,
   not a Germany city one-hot vector. Preserve public-money/player-order/fuel
   information and refill information for all Steps.
3. Start with a small set of structurally different maps and audit complete
   games before scaling. Include a map with island/region-specific constraints
   once those rules are represented. Keep the old Germany model as a baseline;
   transferable components can be reused but the changed schema is not a
   drop-in checkpoint replacement.
4. Generate fresh training-only games against a mixture of frozen prior models,
   heuristic/search opponents and self-play opponents where each is supported.
   Do not run the Germany neural opponent on other maps. Separate whole deals
   and duplicate states between training/validation, and hold out entire maps
   when measuring transfer to unseen geography. Balance player counts and rule
   variants explicitly rather than assuming pooled averages cover them.
5. Train on HF Jobs in bounded iterations. Compare actual full-game strength
   per map/count/rule combination against suitable opponents on fresh deals.
   Refresh training trajectories after accepted improvements. Test search as a
   teacher or runtime addition only when it gives repeatable improvements;
   previous search changes often regressed other configurations.

Start with a small correctness/cost pilot, give the user an estimated duration
and Paris time to return, then scale only with evidence. Two or three iterations
without fresh-game improvement should trigger a review of direction, not an
automatic increase in epochs or GPU count. Preserve existing final evaluation
seeds and never turn prior development/confirmation/final games into training
labels. Define new multi-map evaluation splits before looking at outcomes.

The user wants a genuinely strong bot and an honest assessment of diminishing
returns. All opponents' money is visible in the intended public-money setting;
private deck order and submitted sealed bids must stay hidden. Opponents' city
counts/order, plants, fuel, region/island presence and remaining building slots
matter. Future analysis features and browser inference are separate ambitions;
neither calibrated values nor browser deployment is established.

## Recovering weights and data

Use authenticated `huggingface_hub` downloads pinned to the descriptor revision;
verify file/archive SHA-256 before using the contents. Do not trust mutable
`main` as an experiment identity or re-run completed jobs to recover artifacts.

The retained ONNX model is in private model repo
`coyotte508/powergrid-ai-germany-v1`, revision
`6b6009756d7b5968bc5b6425efc84a94aab2a1d6`, at
`runs/policy-iteration-training-v2-frozen/ensemble-1/derivative/inference64.onnx`.
Its SHA-256 is
`55331f43379e8fe89025d93b1a7a48c88e0ea39b4ebd3a7ef8240d4b62753530`.
The sibling `inference64.pt` hash is
`3c17d4228e7446f8859aa01e79020ed91f454312925d29c153a76f49f94118da`.
Full checkpoint/evidence pins:
[policy-iteration-training-results-v2.json](strong/policy-iteration-training-results-v2.json).

Important recovery entry points:

| Artifact | Checked descriptor |
| --- | --- |
| Earlier 17,280-root feature/target dataset, split 12,960 train / 4,320 validation, stored in the private model repo | [policy-iteration-training-data-evidence-v2.json](strong/policy-iteration-training-data-evidence-v2.json) |
| Current-engine source/runtime package used by recent experiments | [current-auction-grid-source-v1.json](strong/current-auction-grid-source-v1.json) |
| Full mini-PC serving package and verification | [current-full-serving-launch-evidence-v1.json](strong/current-full-serving-launch-evidence-v1.json), [current-full-serving-results-evidence-v1.json](strong/current-full-serving-results-evidence-v1.json) |
| Latest tree-probe source bundle and its existing nomination inputs | [target-learner-probe-source-v1.json](strong/target-learner-probe-source-v1.json) |
| Completed sealed assessment, learning curves and recovery evidence | [target-generalization-evidence-v1.json](strong/target-generalization-evidence-v1.json) |
| Four fitted tree models, final logs, receipts, independent audit and decision | [target-learner-probe-complete-evidence-v1.json](strong/target-learner-probe-complete-evidence-v1.json) |

The last two completion archives are at private model revisions
`f6889280c100f0c387432203a2002986318ec9e7` and
`088ff49fd541d33c80fdc45c5584469a7bd00c3b`, respectively. The tree source bundle
is at private dataset revision `6eff6eef6eef1942b0742fc596bfd5d8dca10480`.
These are different datasets/archives; preserve each original split and schema.
None is an already generalized multi-map training dataset.

## Operational state and boundaries

Use `ai/.venv/bin/python -u -B` and `PYTHONPATH=ai/strong` where required. Existing
serving packages pin their own Node/dependencies; read the relevant descriptors
before installing or substituting runtimes. Training belongs on HF Jobs. CPU
diagnostics/evaluations may use the user's AMD 8840U mini-PC. Give duration and
ping-time estimates when launching, especially for mini-PC work without a UI.

The old current-engine confirmation finisher was intentionally stopped. Original
HF job `6ae381225ddcdc083026324a` completed but had no available log/final receipt.
An original bucket archive retaining 24 games was discovered and hash-checked,
but not semantically audited/admitted to the comparison. Preserve the STOP marker
in `ai/runs/current-auction-failed-bucket-hf-v3/STOP.json` and read
[current-auction-log-availability-recovery-v1.json](strong/current-auction-log-availability-recovery-v1.json)
before any recovery. Do not fabricate a receipt, count this as a completed
qualification, restart old coordinators, or blindly resubmit original jobs.

The older October 25 runtime-only handoff is historical. Do not resume its stopped
development coordinator or old heartbeat. No objective or monitoring automation
has been recreated during the latest research. No jobs or visibility changes
were made for this handoff. Do not launch anything merely by reading it; follow
the successor session's user instructions for execution.

Keep UI/release work separate and do not touch `/home/eliheros/code/powergrid` or
publish game changes during this research. Do not comment on GitHub. Existing
modified files in this checkout belong to earlier work and were not staged here:

- `ai/strong/policy-iteration-development-status-v2.json`
- `ai/strong/policy-iteration-labels-results-v2.json`
- `ai/strong/policy-iteration-labels-status-v2.json`

Three pre-existing untracked conservative-auction development files ending in
`with-attempts-v1.intent.json`, `with-attempts-v1.json` and
`results-with-attempts-v1.json` also remain untouched. Review explicit paths when
committing; do not use a blanket `git add`.
