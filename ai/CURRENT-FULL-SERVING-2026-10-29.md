# Full serving replay on the actual AMD 8840U

Research is active. This work checks both policies already frozen for the
confirmation study; it does not select one, qualify playing strength, change
the running HF study, or consume reserved final seeds.

## Fixture compatibility completed

All **2,553 original multiplayer fixtures** are compatible with the current
engine. The independently recomputed legal menus match their saved menus in
every case. Public projection preserves the permitted player balances, strips
private deck/sealed-bid information, leaves inputs unchanged, and produces finite
features and the expected player ordering. No original position was replaced,
dropped or regenerated. Counts are 349 / 427 / 527 / 609 / 641 for 2 / 3 / 4 / 5 /
6 players, including all four rule combinations. There are 840 auction, 755
resource, 491 building and 467 bureaucracy positions.

The compatibility audit made no policy calls or game moves. Report:
`strong/current-engine-serving-fixture-audit-v1.json`; raw per-position hashes
and checks: `runs/current-engine-serving-fixture-audit-v1/cases.jsonl`.
Original fixture hash:
`f1c97bf909e38e5df372a89d169d80f5a6f24c00dccefacd60b10b767f1fcfa0`.

## Full target replay

Both the filtered policy and conservative population auction search will receive
every original fixture in its original order: **5,106 requests**. The prepared
public requests are checked against every compatibility receipt before packing.
The standalone artifact is exactly the one used in confirmation, manifest hash
`fc135130689140b6fd72a76e6e14c59a7fea59717b858d330bac0c7f6aad93df`.
The eight-world search budget, four workers, one inference thread, opponent
population and minimum advantage remain unchanged.

The target runner checks every response's legal move, request/revision, player
order and complete policy identity. It independently audits search choices and
every continuation receipt, rejecting caps. Search simulations do occur and
are counted; no new full evaluation games or HF jobs are submitted by this
benchmark. Raw responses and partial output survive failures. There are no
automatic retries or restarts.

Six unit tests passed without policy execution. They cover full fixture counts,
missing/duplicate positions, public-data boundaries, acting player, actual target
CPU requirement, failed-run rejection, and all 5,106 receipt bindings, including
wrong policy, stale request, duplicate index and missing output. Readiness binds
65 input hashes in `strong/current-full-serving-readiness-v1.json`.

<!-- TARGET-STATUS-BEGIN -->
**Original target PID 3462824 was confirmed live on the AMD Ryzen 7 8840U.**
Started at 2026-10-29T01:11:16.122496+00:00; first inspected checkpoint has
1,050 / 5,106 completed requests, still in the filtered-policy pass.
The pre-launch process census found no existing benchmark. No packages were
installed; the existing target environment and offline dependencies are reused.
The package is 142,593,866 bytes, SHA-256
`a255e5f5bf21df18f667d2d0791c6ec8039087479e30178053d6df805f73cbde`.
Full serving verification remains unfinished. Preserve this original process,
remote directory and launch guard; do not launch another copy.
Later live inspection found **2,718 / 5,106** complete: the filtered-policy
pass finished all 2,553 positions and population search is underway. Snapshot:
`strong/current-full-serving-8840u-progress-v1.json`. Independent collection and
full re-audit remain pending.
<!-- TARGET-STATUS-END -->

Manager: `strong/benchmark-current-full-serving-8840u-v1.py`.
Prepared package and recovery metadata:
`runs/current-full-serving-8840u-prepared-v1/`.
Original launch guard: `strong/current-full-serving-8840u-launch-v1.json`.
Remote directory: `/home/coyotte508/powergrid-ai-current-full-serving-8840u-v1`.

Read-only inspection of the original target:

```sh
ai/.venv/bin/python -u -B ai/strong/benchmark-current-full-serving-8840u-v1.py inspect
```

Only after the original process has exited with all 5,106 requests complete,
collect once with the same manager's `collect` operation. It preserves the raw
outputs and uses a fresh interpreter to re-audit every response and search
receipt from the extracted package. Expected final result:
`strong/current-full-serving-8840u-results-v1.json`. A failed or incomplete run
must be inspected, not replaced automatically. An observation timeout does not
mean the original has stopped.

The 81-file recovery archive is uploaded and download-verified at private model
revision `46cecc8db0ece1b7013505b5555b0c1106cd7db9`, path
`archives/current-full-serving-launch-evidence-v1.tgz`, SHA-256
`bf9c7deeee96f1d534ff405348481127b5a48dcaef324c9eb6dad36a6d8566bb`.
The private recovery archive descriptor is
`strong/current-full-serving-launch-evidence-v1.json`. It contains the exact
standalone package and preparation/launch metadata, so restoration requires no
new games or regenerated fixtures. Inspect archive intents/outcomes before retry.

## What remains unproven

This measures fixed-position latency, not representative gameplay latency
percentiles. Cold startup is separate; warm results are grouped by policy,
player count, rule and phase. It is not a new model-checkpoint export parity
test or a full cross-host response comparison. The earlier 320-request exact
cross-host benchmark remains separate evidence.

After complete strength confirmation, selection must bind the same exact
identity/settings to reuse applicable technical evidence. Complete checkpoint
parity and the separate reserved strength gate remain required. No candidate is
qualified by this benchmark, and no production routing is changed.
