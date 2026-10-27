# Actual model and search producing complete resource turns

The actual frozen model and existing resource-search algorithm now produce the
complete response consumed by the separate resource-turn arena. Checks pass on
**755 saved model positions / 2,251 decisions** and **23 saved search cases /
1,232 ordinary continuations**. Chosen bundles, continuation outcomes and the
previously verified transaction envelopes match exactly. This is execution
integration, not a stronger strategy, fresh strength result or deployment.

The separate 10,080-game auction comparison continues unchanged. No HF jobs,
gradient updates, new complete games or reserved final seeds were used here.
These checks do run real local model inference and repeat the explicitly named
engineering continuations; they are not mock-policy tests.

## Producer and transport

`strong/resource_turn_public_policy_v1.py` verifies the supplied runtime manifest,
every listed file, the ONNX hash, feature revision and imported module origins.
It fixes the mode, sample budget, worker/thread counts and continuation horizon.
Those settings, model/runtime identities and adapter source hashes determine the
policy identity. The supporting `resource-turn-exchange-worker-v1.cjs` creates
the checked response using the existing transaction/exchange boundary.

In `model` mode, the producer evaluates each purchase on its copied public state
until Pass, returning that exact sequence together. In `search` mode it calls the
unchanged `ResourceTurnSearch.choose()` and returns every action in its selected
evaluated bundle. It does not return only `firstMove`, cache a partial plan, fit
new thresholds or alter future-deck/opponent sampling. Search truncation retains
the backend's complete model-baseline fallback.

The JSON result contains `response` for the arena and separate `diagnostics`,
including the original baseline trace and, in search mode, the complete search
receipts. Feed the response to the arena as `{publicResourceTurn: response}`.
The producer supports only the **Resources phase** in the existing automatic
Germany research scope with public money. Other phases still need the existing
filtered-model path in a separately pinned full-game evaluator. This component
does not itself implement a production platform job or a full-game runner.

## Evidence and limits

The check runs the real producer as a subprocess from `/tmp`, using the frozen
resource-screen runtime manifest
`cebda6cb0ed6a1eff28cad8cd02cb17e37bb62f59595b2237b989337b40a9415`
and frozen-1 float64 ONNX
`55331f43379e8fe89025d93b1a7a48c88e0ea39b4ebd3a7ef8240d4b62753530`.
It compares complete responses with the earlier independent engine envelopes and
recomputes terminal credits using the separate original search verifier.

The ordinary search checks use **four worlds**, one search worker, one inference
thread and horizon 2,400, matching the saved engineering cases. They cover all
2–6 player/rule combinations plus the pre-existing early/omission probes. These
positions include outcome-selected diagnostics, so they cannot support a win-rate
claim or choose a policy. They do not replace fresh paired eight-world experiments.

All ordinary continuations finish without caps. An additional hidden-data control
repeats 116 continuations and leaves the result unchanged. A deliberate horizon-one
control caps all 116 continuations and returns the complete recorded model turn.
Four malformed requests are rejected, and the service then recovers to the exact
saved result. The initial checker failure is preserved: the historical verifier
expected integer sample keys, whereas JSON keys are strings. The checker now
normalizes that representation on a private copy; producer/search output is unchanged.

Evidence is under `runs/resource-turn-public-policy-v1/`; the failed first checker
attempt is under `runs/resource-turn-public-policy-v1-attempt1/`. The tracked
assessment and verified private HF archive are indexed by
`strong/resource-turn-public-policy-results-v1.json` and
`strong/resource-turn-public-policy-evidence-v1.json`. They pin the earlier fixture,
search, transaction and runtime archives needed for recovery. The upstream arena
already passed 120 recorded-game replays; that completed check was not rerun here.

After restoring those inputs, reproduction into a new output directory is:

```sh
ai/.venv/bin/python -B ai/strong/check-resource-turn-public-policy-v1.py /absolute/path/to/new-output
```

Finish the current auction comparison before selecting the next strategy. A
resource commitment study still needs a frozen full-game evaluator and artifact,
runtime admission, a paired control distinguishing commitment from stable
within-turn sampling, and fresh full games. The rejected atomic resource-search
strategy remains rejected. Target-8840U cost and final strength qualification
remain requirements for any eventual selected policy.
