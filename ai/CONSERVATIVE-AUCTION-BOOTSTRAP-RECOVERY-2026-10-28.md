# Conservative auction comparison: reviewed infrastructure recovery

## Status and interpretation

Research remains active. This recovery continues the same 648-job, 10,080-game
Germany development comparison across 2–6 players and all four rule combinations.
It changes only transport of the original Node v24.14.0 release. Frozen models,
policy settings, engine/source, seeds, matchups and analysis arithmetic are unchanged.
It provides no new strength conclusion and does not qualify a candidate.

The last goal turn was a verified wait/status check (55 running handles directly
observed). This turn made progress: reviewed two pre-evaluation failures, verified
an immutable cache, tested separate-attempt collection and analysis, launched
exactly two reviewed replacements and admitted a new sole owner. No training or
reserved final games were started.

## Failed originals and explicit attempts

| Study row | Preserved failed original | Explicit attempt 1 |
|---|---|---|
| `pg-conservative-dev-v2-pop-heuristic-5p-02` | `6ae1dca83fb22a235dd3e7c7` | `6ae1e7b941e90535df77318d` |
| `pg-conservative-dev-v2-pop-legacy-6p-00` | `6ae1dcb03fb22a235dd3e7eb` | `6ae1e7b941e90535df77318f` |

The first failed with HTTP 502; the second received only 6,717,440 of 31,039,304
Node-archive bytes. Both exact remote commands, source environment, ERROR status,
full logs and absent output archives were reviewed. Both failed at the Node
`urlretrieve` before source extraction/evaluation. Original guard/log hashes are
bound in `strong/conservative-auction-bootstrap-recovery-v1.json`.

Original directories under `runs/conservative-auction-development-hf-v2/` remain
unchanged. Replacement guards/results use
`runs/conservative-auction-development-attempts-v1/<name>/attempt-1/`.
These are the only reviewed retries. Unknown or failed launches require inspection;
there is no automatic retry. Successful final accounting would contain 648 selected
jobs plus these two failed originals: 650 total HF attempts, not 650 game shards.

## Same release, verified cache

The original Node archive was downloaded from the official release URL and matched
its official SHASUMS256 file. Its binary reports `v24.14.0`. The uploaded archive
was downloaded at its immutable HF revision and checked again.

- Private dataset: `coyotte508/powergrid-ai-training-v1`.
- Revision: `a25e8feaa51bc9506c2469a1c7e5ad5c2d8bf346`.
- File: `bootstrap/node-v24.14.0-linux-x64.tar.xz`.
- Archive SHA-256: `41cd79bb7877c81605a9e68ec4c91547774f46a40c67a17e34d7179ef11729df`.
- Binary SHA-256: `e237a2839d0cbdc9a9a2adda1a184afc0f5b20306ffbe923af5686550472d8a8`.
- Actual cached-bootstrap SHA-256: `95e46cbeb9ee6da9090ef74567ca776577ba1593690adc3a63975cb3ac115e91`.

The source descriptor keeps its historical bootstrap hash. Each new launch guard
records the actual cached-bootstrap hash and review/cache descriptor hashes.
Historical jobs did not record a Node binary checksum; do not claim their binary
bytes were retrospectively verified. The same official release is preserved.

## Owner and independent comparison

New sole owner: PID **1075760**, session **83119**, started
**2026-10-28T12:18:29 UTC**. Its state and immutable admission record are in
`runs/conservative-auction-development-attempts-coordinator-v1/`; its log is the
sibling `.log`. At admission: 424 selected guards, 360 cached raw audits, 426 total
HF attempts. Check actual PID/state before acting; these are snapshots.

The stopped v3 owner PID 678525 and all earlier states/logs/STOP markers are
preserved. The new owner holds execution locks against old owners and direct
collectors, checks pinned code, audits completed selected attempts before each
batch, and submits only rows without a guard. Maximum concurrency stays 64.
No automatic restart or retry is implemented.

The new complete report will be
`strong/conservative-auction-development-results-with-attempts-v1.json`.
Only after the owner is complete, run:

```sh
ai/.venv/bin/python -u -B ai/strong/compare-conservative-auction-attempts-v1.py
```

This requires all 648 successful selected jobs and all 10,080 games. It checks
separate attempt routing and both original failures, independently re-audits all
immutable raw archives/receipts, then uses the unchanged paired whole-deal
statistics. It writes `strong/conservative-auction-development-comparison-with-attempts-v1.json`.
Inspect any existing analysis intent/outcome before running; do not run on partial
results. The old comparison remains unchanged for historical provenance.

## Validation and persistence

Twenty admission/provenance tests passed. They cover exactly bounded bootstrap
substitution, rejected wrong caches and post-evaluation failures, preserved
original guards, no resubmission after an unknown launch, no automatic retry,
64-job concurrency, failed-collection stop, actual setup receipt binding, routing,
and unchanged analysis arithmetic/completeness. These are synthetic control tests,
not game evidence. The bootstrap shell syntax also passed.

The receipt `runs/conservative-auction-attempts-tests-v1.json` binds the exact
manager, owner, analysis, review and test files. The archive descriptor is
`strong/conservative-auction-bootstrap-recovery-evidence-v1.json`; it references
the original immutable source and cached job archives rather than replaying games.

No candidate is qualified. Final seeds remain unused. Finish the fixed development
comparison, assess all adverse cells and measured 8840U cost, then perform the
unchanged final strength and serving gates before any deployment.

Archive verified after upload: revision
`bc85f2942018bf422aff8572e63acadfe29ff901`,
`archives/conservative-auction-bootstrap-recovery-evidence-v1.tgz`, SHA-256
`89318d3a602645329de9f24feed03c89d9de412a45fcb01df5dfdf9627f872e0`.
It contains 1,209 files, including exact admission guards, cached audit receipts
and manifest references, reviewed failure logs, cache provenance and recovery
code. At the later **12:21:34 UTC** owner checkpoint: **370 audited / 434 selected
jobs submitted / 436 total HF attempts**, 64 active at submission. Treat these as
snapshots; consult the live owner before any action.
