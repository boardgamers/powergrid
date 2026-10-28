# Research engine versus current game engine — 28 October 2026

The current repository engine is **2.0.19**, commit
`3adad0cc0d1d31352aa7a9059bd15efa79647269`, fetched from `origin/master`.
It was built separately under `ai/runs/current-engine-compatibility-v1`.
The active research branch, frozen artifacts, running jobs and the separate live
game checkout were not changed. Nothing was published or deployed.

## Measured result

All **3,443 public requests from 33 previously recorded games** had identical
legal-action menus under the frozen research engine and this current engine.
Recomputed frozen menus also match every recorded menu and policy candidate list.
All recorded first actions therefore remain legal at those same saved states.

| Coverage | Requests |
| --- | ---: |
| Two players | 1,065 |
| Three players | 510 |
| Four players | 511 |
| Five players | 495 |
| Six players | 862 |
| Auction | 1,261 |
| Resources | 334 |
| Building | 908 |
| Bureaucracy | 940 |

The corpus includes original/Recharged × open/sealed, Steps 1–3, economic
opponents at every player count, and legacy opponents at two and six players.
It covers seats zero and the last seat, **not every seat**. It was selected as
the complete existing 33-game integration corpus before examining compatibility,
without looking at partial results from the ongoing auction study.

Twenty deterministic setup comparisons (all player counts and rule combinations)
also match after omitting player clock timestamps. These are setup fixtures, not
new complete games or strength observations.

## Real rule difference outside those recorded positions

The current engine fixes Recharged nomination affordability: while the discount
is active, a player with one Elektro can nominate the cheapest market plant even
if its printed number is higher. The frozen research engine's nomination test
still requires the printed amount. The subsequent bid minimum was already
discounted; the discrepancy is the earlier nomination menu.

Ten targeted low-cash fixtures (2–6 players, open/sealed Recharged) reproduce this
difference: the old menu omits the discounted plant and the new menu includes it.
Twenty auto-pass checks also pass: with one Elektro the current engine retains
that affordable choice; with zero it applies the forced Pass. This explains why
updating affordability before auto-passing matters. **No such menu difference
occurred in the 3,443 recorded requests**, so its frequency or strength impact
cannot be estimated from this diagnostic.

Other current-source changes include editable powering choices, an alternate
plant deck, an optional end to the Recharged discount at Step 3, and automatic
auction passes in the live wrapper. Their existence is visible in the pinned
source snapshot; this diagnostic does not validate support for those options.

## Interpretation and next action

This is **saved-state menu parity**, not full transition, wrapper, replay or
serving parity. We did not replay complete games under the new engine, run model
inference, measure win rates, or claim the model understands new options.
Identical menus at historical states do not imply identical future trajectories.

The ongoing auction comparison remains valid for its explicitly frozen research
engine. Do not change that engine or discard those results mid-study. Before final
qualification/deployment, the chosen runtime needs an explicit current-engine
compatibility decision: verify transitions and serving against the intended engine,
handle the discounted-nomination difference, and define/reject unsupported option
combinations. Any migration must create a new pinned runtime and be evaluated
separately; this diagnostic does not authorize silently swapping the engine in
an existing candidate or reusing a final-strength claim across runtime changes.

## Reproduction and evidence

`strong/check-current-engine-compatibility-v1.py` prepares the isolated source and
runs `strong/check-current-engine-compatibility-v1.cjs`. Inputs are bound to the
successful previous integration assessment and its recorded-file hashes. The
prior intermediate assessment files have `passed:false` while later stages were
pending; the final successful assessment is the authoritative input.

TypeScript **4.3.5**, matching the repository lockfile, was downloaded from the
public npm registry and verified against the lockfile SHA-512 before use.
Forty-two source files were transpiled with ES2018/CommonJS/esModuleInterop.
This was **not a TypeScript typecheck**. Runtime dependencies came from the
unchanged, manifest-verified v4 research artifact. No dependency or build command
was run in the separate live game checkout.

The initial preparation accidentally compared the descriptor's assessment hash
with the enclosing results file. It stopped before creating the experiment
directory, downloading dependencies or running checks. Its source and log are
preserved under `ai/runs/current-engine-compatibility-v1-initial`. The corrected
preparation checks the actual final `assessment.json`; the diagnostic then ran
once successfully.

`strong/current-engine-compatibility-results-v1.json` contains the measurements,
coverage and design/build hashes. The experiment directory includes the exact
Git source archive, compiler archive, compiled engine, source/build manifests,
design, logs and assessment. Its temporary node_modules symlink is recovered
from the separately pinned research artifact and is excluded from the archive.
`strong/current-engine-compatibility-evidence-v1.json` indexes the immutable
private HF archive. Recorded requests already have their own immutable archive
and are referenced by hash instead of duplicated.

No HF job, new inference, full-game trajectory, gradient, final seed,
qualification or deployment was added by this diagnostic. The research goal
remains active. At 18:02 UTC the auction owner PID 1075760 was confirmed alive,
with all 648 selected batches submitted and 587 independently verified.
