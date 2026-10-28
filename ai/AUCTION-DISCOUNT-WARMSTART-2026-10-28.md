# Discount inputs: prediction-preserving warm start — 28 October 2026

A separate, untrained schema-4.4 extension of the trained `frozen-1` model now
accepts the public discount inputs. On **19,843 checked inputs**, its native
float32 and float64 outputs exactly equal the original model's outputs. Its
ONNX outputs and chosen moves also exactly equal the original ONNX outputs.
This prepares a controlled input experiment; it is not a new strength result
or permission to reuse incompatible teacher targets.

## Architecture

Each of the four existing frozen-context correction heads gains two separate
linear projections: the new discount bit to 128 state channels, and the two
nomination-price features to 64 action channels. All eight new tensors start
at zero (**1,024 additional parameters** total). Every existing stored tensor
and matrix shape is unchanged. Existing shortlist membership, parent fallback,
eligibility, ensemble disagreement penalty and correction margin are retained.

The extension reconstructs the original contiguous state/action prefixes
before evaluating the parent and its embeddings. New features enter only the
additional projections. A separate diagnostic copy with fixed nonzero weights
confirmed that both new paths can affect head scores. No optimizer or gradient
operation was used; the saved prototype still has all new weights equal to zero.
That connectivity diagnostic is not training or evidence of a good move.

`model_auction_discount_v1.py` provides an explicit loader for the prototype.
It is **not registered in existing runtime factories or services**. Its
architecture is `policy_iteration_auction_discount_v1`, feature revision
`4.4-auction-discount`, state/action dimensions 1218/103. The original parent
metadata is nested as provenance rather than presented as training of the new
feature revision.

## Checks and preserved failure

The final check covers:

- 17,280 saved training/validation inputs, using their actual recovered
  discount features and unchanged target-option columns;
- all 2,553 serving fixtures, with full legal menus across 2–6 players and
  different decision phases;
- the ten naturally recovered low-cash nomination cases, keeping their six
  training / four validation assignments intact.

Both native precisions returned exactly equal outputs. The exported prototype
returned exactly equal outputs to the original ONNX model (maximum difference
0 for logits and values), and every chosen move stayed legal. Native-versus-
ONNX numerical differences remain the original small differences: maximum
4.7464e-10 for logits and 1.4215e-11 for values, within the existing tolerance.
The successful comparison performs 119,058 policy-position forward evaluations
and 256 diagnostic head-position evaluations; export tracing and the preserved
failed attempt/diagnostics are additional work. No new games or rollouts ran.

The initial native float64 check failed despite unchanged choices: widened
feature rows changed memory strides, giving a maximum 2.6645e-15 logit
difference and 5.5511e-16 value difference on the first 64 positions. A control
that restored the original contiguous prefixes removed both differences
exactly. The repair adopts that layout explicitly; the exact native-output
requirement was **not relaxed**. The initial implementation, checkpoints,
export, log, design and diagnostic results remain in
`ai/runs/auction-discount-warmstart-v1-initial/` and the recovery archive.
The corrected second execution passed the complete check in 58.54 seconds
after model/export setup; that is check throughput, not serving latency.

## Next decision

Finish the unchanged auction comparison before selecting another strength
experiment. This prototype is one available warm start, not a selected or
qualified candidate. In particular, it retains the old shortlist: it does not
repair the 397 missing discounted-nomination teacher options. A subsequent
experiment must separately design candidate coverage, current-engine/public-
belief teachers, targets, whole-deal splits and held-out evaluation.

Do not train on the four recovered validation cases or on development/final
evaluation seeds. Do not claim the existing 8840U timings validate this new
architecture; a selected trained artifact still needs its own export, serving,
strength and target-hardware checks. No HF job, gradient update, deployment or
change to a running policy was made here.

## Recovery

- Checker: `ai/strong/check-auction-discount-warmstart-v1.py` and
  `auction-discount-warmstart-inputs-v1.cjs`.
- Prototype: `ai/strong/model_auction_discount_v1.py`.
- Successful artifacts: `ai/runs/auction-discount-warmstart-v1/` contains
  `warmstart.pt`, `inference64.pt`, `inference64.onnx`, design and assessment.
- Report: `ai/strong/auction-discount-warmstart-results-v1.json`.
- Archive descriptor: `ai/strong/auction-discount-warmstart-evidence-v1.json`.
  Inspect the existing archive intent/outcome before retrying an upload.
- Parent training checkpoint SHA-256:
  `6de3a433103a5cce4b88f54dd68ae8b4b4371d4e317ad9d8de1c5e3d4ea182fa`;
  original ONNX SHA-256:
  `55331f43379e8fe89025d93b1a7a48c88e0ea39b4ebd3a7ef8240d4b62753530`.
  Their immutable HF references and the input-cache/fixture hashes are bound
  in the design. The archive also records the `model_v4.py` dependency, checked
  equal to the previously frozen runtime copy.

This turn is progress; the preceding turn was a verified wait on the live
coordinator and remaining HF handles. Research remains active. No candidate
qualified and reserved final seeds remain unused.
