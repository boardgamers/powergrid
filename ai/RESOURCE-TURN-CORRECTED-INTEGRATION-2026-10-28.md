# Corrected public resource turns: full-game integration

## Completed work

The isolated v2 artifact integrates the public-deck metadata correction without
changing the historical runtime or frozen-1 model. Actual inference reproduces
all choices and terminal results of 33 previously recorded complete games:
economic opponents at 2–6 players with all rules at seat zero and one extra last
seat, plus legacy opponents at 2 and 6 players with all rules. These are
engineering replays, not fresh strength data. The unchanged filter replay was
not repeated.

The seven independent receipt audits cover 4,720 atomic learner actions,
including 334 complete resource turns. For every intermediate model decision
within those resource turns, its public features and legal menu were compared
against eight complete sampled states. All **12,888 checks / 1,611 decisions**
passed. Coverage includes Steps 1/2/3 (198/38/98 turns), rounds 1–12, 2–6 players,
and all four original/Recharged × open/sealed rules. This checks later-round
inputs as well as the initial 20 round-one cases.

Both corrected search modes reproduce the original plans and continuation
receipts at two predetermined roots: two-player original sealed and six-player
Recharged open. These four mode/root checks used **96 uncapped continuations**
and 18,768 continuation neural decisions, zero caps. They validate changed code
integration; they are not independent strength observations. No new HF job,
complete game trajectory, gradient or reserved final seed was used by this check.

## Artifact and explicit controls

Local artifact: `runs/resource-turn-full-artifact-v2/`, 1,497 manifest files.
Descriptor SHA-256:
`360e69c98382e2e837d6d6eedea5a9790778e19efef6542671d9bf5dd6e8676a`.
Manifest SHA-256:
`2895f9eb4232c4f1702e6bf0b1c976834ab5e7e987b2c00f97551f330f27db62`.
The unchanged runtime manifest is
`cebda6cb0ed6a1eff28cad8cd02cb17e37bb62f59595b2237b989337b40a9415`;
the frozen model remains
`55331f43379e8fe89025d93b1a7a48c88e0ea39b4ebd3a7ef8240d4b62753530`.

Five modes have explicit policy identities:

| Mode | Resources behavior |
|---|---|
| `filter` | Original filtered model, atomic actions |
| `model-turn` | Corrected complete model turn |
| `search-turn` | Corrected model baseline, execute the complete search-selected plan |
| `atomic-search` | Historical atomic replanning, preserving its original baseline-input defect |
| `atomic-search-corrected` | Corrected model baseline, but replan after every purchase |

Other phases keep the frozen filtered model. All search settings remain eight
worlds, one search worker, one inference thread and a 2,400-step continuation
horizon. Corrected atomic search still derives a new public seed after every
purchase; a stable-seed control is not implemented yet. Do not confuse the two.

The new Node worker uses the corrected model-turn primitive and the unchanged
candidate construction/continuation engine. The public service, private arena
and independent auditor bind the new policy identity and exact artifact. The
`resourceBaseline` identity field explicitly distinguishes historical, corrected
and ordinary atomic inputs. Run these modules from the pinned artifact layout;
the corrected worker expects its sibling `runtime/` directory.

## Evidence and recovery

`runs/resource-turn-full-integration-v2/` contains the design, per-game completion
receipts, raw public requests/responses, seven independent audits, all intermediate
input-check receipts, mode descriptions, four search checks and final assessment.
`strong/resource-turn-full-integration-results-v2.json` binds those files, the
original raw-game inputs and all source hashes. Validation finished successfully;
do not rerun completed checks without a new change or specific unresolved concern.

`strong/resource-turn-full-integration-evidence-v2.json` indexes the verified
private HF archive. It includes raw new evidence, adapter sources and artifact
manifests; the original runtime/model/game archives are referenced rather than
duplicated. The v1 artifact and its evidence remain unchanged.

To rebuild this exact package after restoring its pinned inputs, use a fresh
output directory with `strong/prepare-resource-turn-full-artifact-v2.py`.
The checker `strong/check-resource-turn-full-integration-v2.py` is a one-shot
validation tied to the saved output path; do not restart it over existing data.
Each completed replay was saved separately to permit evidence-preserving recovery
if needed. No recovery was required in this run.

## Remaining work

Prepare an explicit stable within-turn sampling policy with validated lifecycle
and reset boundaries. Keep commitment, input correctness and sampling stability
separate in any study design. A prospective search-policy complete-game runtime
pilot and measured resource admission still precede fresh paired strength games.
The current artifact supports its six engine-opponent CLI choices; it does not
yet support the neural snapshot opponent route required for broad qualification.
Finish the unchanged auction comparison before choosing the next strategy study.
No candidate is selected or qualified; final strength and serving gates remain.

The 242-file raw evidence archive was uploaded and downloaded successfully:
private HF revision `8258d9b79e3fbd5b153fe557a970eed933ca90de`,
`archives/resource-turn-full-integration-evidence-v2.tgz`, SHA-256
`e9e49af7b0a3a2b912787422a637557a4bb522b78ffc1455f3249101a95aaf71`.
The auction owner was verified live with all pins unchanged at its **13:43 UTC**
checkpoint: **457 audited / 522 selected jobs submitted / 524 total HF attempts**.
Direct inspection of the 65 then-uncached selected handles found 62 RUNNING,
3 COMPLETED and no failures. Counts are snapshots, not live status.
