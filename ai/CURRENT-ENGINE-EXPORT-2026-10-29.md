# Current-engine checkpoint and ONNX parity

All **2,553 original serving positions** passed a fresh native-checkpoint/ONNX
comparison using the current frozen policy's public preparation path. A separate
process then regenerated every input tensor and re-audited all saved output
arrays, without running either network again.

- Every legal-action argmax matched exactly, including near ties.
- Every value output was finite, nonnegative and normalized; inactive player
  slots were exactly zero in both implementations.
- Largest absolute logit difference: **4.746425474877469e-10**.
- Largest absolute value difference: **1.0236589353951331e-11**.
- Coverage: 349 / 427 / 527 / 609 / 641 positions for 2 / 3 / 4 / 5 / 6 players.
- The successful comparison took 25.73 seconds locally, with one inference
  thread. This is validation workload timing, not a serving latency benchmark.

The exact model is shared by both unchanged confirmation policies. This proves
base-network export parity on the current engine; filter/search overrides and
their playing strength are separate checks. No candidate was selected, no
weights or execution settings changed, and no final seeds were used.

## Identity and source provenance

ONNX SHA-256:
`55331f43379e8fe89025d93b1a7a48c88e0ea39b4ebd3a7ef8240d4b62753530`.
Native inference checkpoint SHA-256:
`3c17d4228e7446f8859aa01e79020ed91f454312925d29c153a76f49f94118da`.
Runtime manifest SHA-256:
`fc135130689140b6fd72a76e6e14c59a7fea59717b858d330bac0c7f6aad93df`.

The original trained checkpoint and model pin are bound to the immutable earlier
technical-evidence archive, model revision
`23487b7a1715262259fc2bf11a689cf393643939`. The actual checkpoint/model files and
archived parity receipt were hash-checked before the new run.

The deployment artifact intentionally omits PyTorch model definitions. The first
harness setup rejected an import from outside that artifact before loading the
checkpoint or making any forward pass. Its script and failure log are preserved.
The corrected setup verifies the six native definition files directly against
the original immutable training source, dataset revision
`776fc237a19be9789fe160d4406e68cd31adf080`, archive
`strong-source-policy-iteration-training-20261024-v2.tgz`, SHA-256
`21a162cb75167e3781bcd8e8f2810b4b93f37712775af300abb910fdcccfd958`.
Their imports must come from the separate native verification directory.
Engine preparation and ONNX runtime modules must come from the unchanged
deployment artifact. Neither source is silently substituted for the other.

There were 2,553 native and 2,553 ONNX forward passes, no training, re-export,
search rollouts, full evaluation games or HF job submissions in this work.
All original public fixtures were retained in their original order. The separate
live 8840U replay and HF coordinator continue their authorized work unchanged.

## Evidence and tests

- Report: `strong/current-engine-export-parity-v1.json`.
- Original tensors' hashes, native/ONNX output arrays and legal proposals:
  `runs/current-engine-export-parity-v1/receipts.jsonl`.
- Independent audit: `strong/current-engine-export-audit-v1.json`.
- Native source definitions and immutable source metadata:
  `runs/current-engine-export-native-source-v1/`.
- Four numerical tests reject argmax disagreements despite close logits,
  non-finite/negative/unnormalized values, nonzero inactive slots and bad shapes.
- Two target-binding tests accept a legal filter/search override while rejecting
  altered underlying model proposals, identities, settings or request metadata.

The 37-file archive is uploaded and download-verified at private model revision
`47c1eb217410c3038e7609eae8f5a56154ebcecc`, path
`archives/current-engine-export-evidence-v1.tgz`, SHA-256
`d06fa97590f60d0f547cd3682beec58a9e196d01c5c2331116f148d476a83b29`.
The private evidence descriptor is
`strong/current-engine-export-evidence-v1.json`. Its archive preserves raw
outputs, the independent audit, checkpoint, native source files, code, tests and
the failed first setup. It references the already archived complete serving
package for the exact current engine and public fixtures; no regeneration or
inference rerun is required on restore. Inspect existing intents/outcomes before
retrying an upload.

## Full target binding completed

The original full target replay completed and was independently collected and
audited. The subsequent `bind_serving` operation passed on **all 5,106 saved
target responses**: each `modelProposal` equals the native-checkpoint argmax on
the same request. Legal filter/search overrides remain separately audited.
No new inference, search or game execution was needed. Do not repeat the binding.

Report: `strong/current-full-serving-export-binding-v1.json`. Full target
results, measured timings and recovery references are in
[the completed serving handoff](CURRENT-FULL-SERVING-2026-10-29.md).
The raw response/audit/binding archive is verified at model revision
`e4f018ff2f983e5e4f1a6b7e92a7586051bf5842`; descriptor
`strong/current-full-serving-results-evidence-v1.json`.

The full confirmation and reserved strength qualification remain unfinished.
Later selection must bind the same complete policy identity/settings before
reusing this technical evidence. Values remain uncalibrated estimates; these
checks do not establish their suitability for player analysis.
