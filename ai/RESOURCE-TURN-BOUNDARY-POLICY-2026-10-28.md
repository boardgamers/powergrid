# Corrected resource-boundary policy integration

28 October 2026. Research remains active. No strength candidate is qualified,
no reserved final seeds are used, and nothing is deployed.

## What changed

The separately pinned **v4 research artifact** integrates the v2 public-history
anchor and chronological auditor from the
[boundary diagnosis](RESOURCE-TURN-BOUNDARY-2026-10-28.md). Undo commitment and
the start of buying are now distinct. A valid own plant discard followed by
Resources with `newTurn=false` no longer crashes the anchored search.

The six execution modes remain filter, model-turn, search-turn, atomic-search,
atomic-search-corrected and atomic-search-anchored. The anchored mode now uses
`resource_turn_anchored_search_v2.py`, `resource-turn-search-worker-v4.cjs` and
the explicitly versioned `turn-start-public-history-v2` sampling receipt.
The full policy, arena, auditor and builder have separate v4 filenames and
identities. Historical v1–v3 sources, artifacts, guards and jobs are unchanged.

All **1,493 common files** in the v3/v4 manifests are byte-identical; eight
versioned paths are replaced. The model, engine runtime, six mode names and
settings remain unchanged: eight sampled worlds, one search worker, one ONNX
thread and a 2,400-step horizon. No heuristic or weight change is hidden in this
boundary correction.

Artifact: `runs/resource-turn-full-artifact-v4` (1,501 manifest entries).

- Descriptor SHA256: `1bf7b9ecdf79f68ee781cc6153cc5079e6dfe16c5051a155026a7307c6782048`.
- Manifest SHA256: `ce05c01a314305f5f0b3f7b55f6a8e13355ee0edb9bf5cae2c9688efd55cf795`.
- Model SHA256: `55331f43379e8fe89025d93b1a7a48c88e0ea39b4ebd3a7ef8240d4b62753530`.
- Original runtime manifest SHA256:
  `cebda6cb0ed6a1eff28cad8cd02cb17e37bb62f59595b2237b989337b40a9415`.

## Actual inference and search checks

`strong/check-resource-turn-boundary-policy-v2.py` executes the full public
policy service, not just the rewind helper. Its selection was fixed before
execution: the existing 20 early roots, all four observed false-commit entries,
and every non-resource decision from the failed episode's saved prefix.

- **20/20 normal first searches** reproduce the complete historical plan and
  continuation receipts, excluding elapsed-time fields, across 2–6 players and
  all four rule combinations.
- **3/3 exceptional first searches** with an existing whole-turn or corrected
  atomic reference also match completely after normalizing the explicit
  sampling-receipt version. The fourth is the original missing failed request.
- **All four exceptional resource turns finish with a legal Pass**. Their
  complete atomic action counts are 4, 13, 4 and 10, including Pass. The
  independently tracked sampling seed remains tied to the actual entry after
  each purchase, including the 12-purchase sequence.
- **99/99 recorded non-resource decisions** reproduce the original model/filter
  decisions exactly, excluding elapsed time.
- Three replays of a real selected intermediate request match after other
  turns, a cold process restart and an intentionally invalid history request.
  The invalid request fails closed; the service then recovers.
- Twenty altered seed/current-seed/commitment/purchase-count/cost receipts are
  rejected by the independent auditor.
- **2,448 actual continuations / 114,561 continuation neural decisions / zero
  rollout caps**, including lifecycle replays. There are 51 primary resource
  policy requests (20 normal roots and 31 exceptional-turn actions), plus the
  99 non-resource requests and the lifecycle/error controls.
- Local duration: **176.330 seconds**. No new HF job, complete evaluation game,
  gradient update or reserved final seed was used.

Output: `runs/resource-turn-boundary-policy-v2`.
Assessment SHA256:
`35245e9387c2aa236cfcda6d8edb1560904ad8bc007f15dd87158dfef32d94d3`.
Summary: `strong/resource-turn-boundary-policy-results-v2.json`.

These searches are engineering evidence. The old atomic resource strategy's
negative development result is not overturned by a correctness fix. The v4
artifact has not yet completed a fresh full-game runtime study or any strength
comparison. Its full-game auditor retains the original paired-schedule gate.

## Newly collected original six-player runtime pilot

The separate collection-only path independently verified original whole-turn
job **`6ae20c1341e90535df77523a`**. This is the unchanged **v3** job launched
earlier, not a v4 replacement or a new submission.

- 24 complete paired runtime games, all seats and all four rule combinations.
- 2,285 policy requests / 2,937 atomic moves / 223 whole-resource turns.
- 16,200 continuations / 1,544,194 continuation neural decisions / zero caps.
- Measured workflow wall time **7,056.353 seconds**; **22,701.91 CPU seconds**.
- Sampled peak process-tree RSS **4,638,265,344 bytes**, with 33,643 samples at
  0.2-second intervals. Includes startup/validation, excludes HF bootstrap and
  archive upload. This is a job measurement, not per-move latency or AMD timing.
- Independent audit SHA256:
  `eba144fd975fc6f489ba00929854c0915af32a49b4821d956f38b902279cf3d3`.

Private model repository `coyotte508/powergrid-ai-germany-v1`:

- Raw revision: `3bb5ee93cdd98cdc39d4ef814e5db8ec4c53a37b`.
- Path: `archives/pg-resource-turn-runtime-v1-whole-6p.tgz`.
- Archive SHA256: `b57c61679acb2bc2d34d1414a9f1568f7e9f9c4f6a46bbe6ab7b1c01a1b8d495`.
- Manifest SHA256: `67c23c02210666e6f8a5df9d2bbf2fb559faf78fb56795c6467f945231f8f4a4`.
- 105 archived files including the manifest.

The original set now has **three verified successes / 40 games**, one preserved
two-player failure and two six-player originals observed RUNNING. The original
96-game success gate is still failed/incomplete. No pilot wins are used for
policy selection. The new successful receipt and audit are included in this
integration evidence archive; the large raw archive is referenced immutably.

## Recovery and next work

Exact sources, manifests, public requests, full search receipts, lifecycle logs,
the new runtime audit and source recovery descriptors are archived by
`strong/archive-resource-turn-boundary-policy-v2.py`. The immutable HF revision
and verified hashes are recorded in
`strong/resource-turn-boundary-policy-evidence-v2.json`. Inspect existing archive
intents/outcomes before any retry. The model and original runtime are recovered
through their existing immutable sources instead of being regenerated.

Continue bounded collection of the two remaining original handles with
`strong/collect-resource-runtime-outcomes-v2.py`; never replace a failed pilot
implicitly. Finish the unchanged auction comparison before selecting another
strength study. Its sole coordinator PID 1075760 was live at 16:54 UTC with
563 audited / 627 submitted of 648 selected batches. Recheck the live process
and state rather than treating this snapshot as current status.

Any v4 full-game runtime run needs a separately pinned source, measured budget
and explicit admission; the original v3 handles and their failure remain part
of the evidence. No new runtime jobs were admitted or launched by this work.
