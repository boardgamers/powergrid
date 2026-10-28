# Complete resource turns in a pinned full-game evaluator

The separate evaluator now routes resource purchases through complete plans and
uses the existing filtered model in other phases. Actual inference reproduces
the original choices and terminal results in **66 replay executions of 33 recorded
games**. A separate command-line run reproduces **eight recorded two-player games**
with every seat and rule combination, and passes the independent paired-game audit.
These are engineering replays, not fresh strength evidence or new training games.

The combined replay checks cover **10,800 atomic learner actions**, including
**425 complete resource turns**. The predetermined main selection covers 2–6
players, all four rules, seat zero and an additional nonzero seat against economic
opponents, plus all rules against legacy opponents at two and six players.
The CLI check overlaps that selection; do not count its games as independent data.

## Policy and execution controls

The local artifact contains an unchanged, verified resource-screen engine/runtime,
the frozen-1 ONNX model, and separate adapters. Its 1,495-file manifest is
`35fa75b5a808c12d903ebe4fb74568425d86f8b064595c39f3f3df58b8373607`;
the descriptor SHA256 is
`8e97c0165eee793dd3be7aefd1849281f36e88ac537c20b5906308f0a8fec723`.
There are four explicit execution controls:

- `filter`: the original filtered model, one atomic action at a time.
- `model-turn`: the same model's complete resource turn; filtered model elsewhere.
- `search-turn`: execute the complete bundle selected by the existing resource search;
  filtered model elsewhere.
- `atomic-search`: the previous resource policy that recomputes a plan after each
  purchase, with the same filtered model elsewhere. Its earlier poor strength
  result remains rejected; inclusion here is an execution control.

The full-game service receives public JSON in a separate process. Every response
binds its request/revision and policy, model and runtime identities. The private
arena validates legality, the complete purchase buffer and final Pass before
advancing opponents. Atomic action counts still determine the arena limit.
The independent auditor recomputes resource envelopes, search receipts, action
counts and terminal credits. Sealed bids and the hidden deck never enter the
public requests. Public money remains available.

Search settings are fixed at eight worlds, one search worker, one inference thread
and a 2,400-step horizon. On the first previously recorded search root in each of
the 20 count/rule combinations, both search controls exactly reproduce the old
evaluated plan and continuation outcomes. Committing each entire plan gives the
same resulting arena observation as applying its purchases individually through
Pass. Each control uses **544 uncapped continuations** across these checks
(**1,088 total**, zero caps). No new search-policy complete game was generated.

## Interrupted validation and recovery

The original checker finished all 66 replay executions and 14 receipt audits,
then recorded 17 of 20 search-root checks before it stopped. Its exact termination
cause is unknown; the host subsequently rebooted. Its process was verified absent,
and all completed outputs remain unchanged under
`runs/resource-turn-full-integration-v1/`.

`strong/finish-resource-turn-full-integration-v1.py` verifies those saved outputs
against the original archive and fixed artifact, then executes only the three
missing six-player roots. It does not repeat any completed continuation, game or
HF job. The completed assessment is under
`runs/resource-turn-full-integration-recovered-v1/`; the separate CLI evidence is
under `runs/resource-turn-full-cli-v1/`.

The tracked result and private archive descriptors are
`strong/resource-turn-full-integration-results-v1.json` and
`strong/resource-turn-full-integration-evidence-v1.json`. They retain source,
model, original-game archive, package and raw-receipt hashes. The archive includes
the adapters and manifests, referencing the already archived runtime/model rather
than duplicating those large inputs. Restore those pinned inputs before rebuilding.
For a justified fresh engineering reproduction, use new output directories:

```sh
ai/.venv/bin/python -B ai/strong/prepare-resource-turn-full-artifact-v1.py /absolute/new-artifact
ai/.venv/bin/python -B ai/strong/check-resource-turn-full-integration-v1.py \
  /absolute/new-artifact /absolute/new-check-output
```

The one-shot recovery helper is tied to the preserved interrupted evidence; never
run it again over its existing output. The normal checker above starts a new
reproduction, which is unnecessary unless code or evidence changes.

## Remaining research

No policy has been selected or qualified from this work. The current auction
comparison keeps its original code, source, policies, thresholds and seeds; only
its reviewed local coordinator was recovered after the host interruption.

A resource strategy study still needs a fixed design separating whole-turn
commitment from stable within-turn sampling, a full-game search-policy runtime
pilot and measured resource admission, then fresh paired strength games. The
current evaluator supports the six engine opponents listed in its CLI; the neural
snapshot-opponent route is not yet integrated here. Do not treat this artifact as
ready for the full final qualification protocol or as a production deployment.
Finish the complete auction comparison before choosing the next strategy study.
Final strength gates, serving fixtures and actual-target cost checks remain due
for any eventual selected policy. Reserved final seeds remain unused.
