# Integrated resource search with stable turn-start sampling

## Completed integration

The separately pinned v3 full-game artifact adds `atomic-search-anchored` to the
five existing resource controls. It still replans after every purchase. Its
random sampling seed is reconstructed from the actual turn-start public state,
rather than changing with each purchase. It does not commit to the first bundle
or promise that later choices will remain identical.

`strong/resource_turn_anchored_search_v1.py` inherits the frozen search setup and
corrected model baseline. Its chooser retains the original candidate valuation,
terminal-credit arithmetic, opponent mixture, tie-breaking and cap handling.
Only seed selection and explicit sampling receipts differ. The Node v3 worker
adds `anchor-prepare`, using the separately validated public-history helper.
Neither the historical runtime nor any v1/v2 adapter was edited.

The full-policy identity distinguishes `turn-start-public-history-v1` from
`current-public-state-v1`, and binds the complete artifact descriptor. All modes
still use the same frozen-1 model, eight sampled worlds, one search worker,
one inference thread and a 2,400-step continuation limit. Non-resource phases
use the frozen filtered model.

## Independent audit

`strong/resource_turn_anchor_verification_v1.py` does **not** call the history
reconstruction helper. It retains the actual first chronological public
request, computes its seed with the original public preparer, and checks all
later receipts against that reference. It independently checks the number/cost
of intervening purchases and public-log boundary. The existing candidate,
receipt and terminal-credit auditor verifies the unchanged search arithmetic.

The v3 full-game auditor uses this tracker for the new mode. Its existing
terminal, paired-schedule, policy identity and resource legality checks remain.
The new complete-game audit path has not yet been exercised on fresh complete
anchored-policy games; that is part of the forthcoming runtime pilot.

## Validation results

The fixed integration check starts from the same 20 previously selected economic
opponent resource roots: every 2–6 player count and original/Recharged ×
open/sealed rule. These are round-one development fixtures, not fresh strength
seeds. Broader later-round mechanism coverage is in the preceding anchor handoff.

- All **20 initial searches** reproduce the exact historical plans and raw
  continuation receipts, after removing elapsed time and the newly explicit
  sampling metadata/revision. This verifies that the experimental control does
  not change the first decision's sampling conditions.
- The new policy completes all **20 focal buying turns**, with **56 atomic
  requests**, legal purchases and final Passes. Their seeds are independently
  checked throughout. These are controlled resource-turn executions, not new
  complete games.
- Six intermediate-purchase replays match exactly: two representative states
  checked after other turns, after cold process restart, and after a malformed
  history request. Both malformed histories are rejected; subsequent valid
  requests recover without changing their responses. Expected rejection traces
  remain in the raw stderr logs.
- All **80 corrupted sampling receipts** are rejected, covering wrong search
  seed, current-state seed, purchase count and purchase cost.
- Actual search validation totals **1,368 uncapped continuations**, including
  144 in the six lifecycle replays; **262,150 continuation neural decisions**,
  zero rollout caps. Baseline model evaluations are additional and are not
  included in that continuation-decision count.

Total checker time was **368.415 seconds locally**. This is not a target-machine
latency benchmark. All six mode descriptions and identities passed inspection.
The already verified unchanged full-model games were not rerun.

No new HF job, gradient, complete-game trajectory or reserved final seed was used.
The search continuations above are new engineering work needed to verify the
changed policy. They do not establish improved win rate or qualify a candidate.

## Artifact and recovery

Local artifact: `runs/resource-turn-full-artifact-v3/`, 1,501 manifest files.
Descriptor SHA-256:
`f41f16f64bf4e9b068e09e15116a6f02c5254ef60c01bd7650a0d7ad356a2e57`.
The exact artifact manifest hash and all input/source/output hashes are recorded
in `strong/resource-turn-anchored-policy-results-v1.json`.

`runs/resource-turn-anchored-policy-v1/` contains the predetermined design, six
descriptions, chronological raw requests/responses, independent seed expectations,
lifecycle inputs/results, exact checker sources, stderr and final assessment.
Validation completed; no recovery or repeated full check was needed.

`strong/resource-turn-anchored-policy-evidence-v1.json` indexes the verified
private HF archive. It includes adapters, package manifests and raw new evidence;
the unchanged model/runtime and original game archives are referenced through
immutable descriptors. Use `strong/prepare-resource-turn-full-artifact-v3.py`
with a fresh path only when rebuilding from these pinned inputs. Inspect any
existing run/archive intent before retrying; do not repeat successful checks.

The previous stateless-anchor turn and this integration turn are both progress.
The active auction owner remained live; at the 14:24 UTC checkpoint it had
500 audited / 564 selected jobs submitted of the unchanged 648-job plan.
Those are execution counts only. No competing collector, replacement job or
change to the frozen auction source was introduced here.

## Next action

Prepare a prospective **runtime-only full-game pilot** for the corrected atomic,
anchored atomic and whole-turn controls, measuring actual wall/CPU costs and
checking complete-game audit/turn boundaries before admitting a larger study.
It must retain failures and caps and must not be interpreted as strength evidence.
Use a new explicit source/protocol/attempt record; no implicit resubmissions.

Finish and independently analyze the existing auction comparison before choosing
the next strategy experiment. A later paired strength comparison must separate
public-input correctness, sampling stability and whole-turn commitment. Neural
snapshot opponent integration, final held-out qualification, selected-policy
export/serving checks and AMD 8840U validation remain outstanding. Research stays
active; no candidate is qualified or deployed.

The 69-file evidence archive was uploaded and downloaded successfully at private
HF revision `c85f032c9db180ebebf57d1f6540194655dbea2d`,
`archives/resource-turn-anchored-policy-evidence-v1.tgz`, SHA-256
`d10abf3654648f27ee1349b50ca6947e83def49711da71d822040d6a1ac9db9e`.
The archive descriptor and this final reference are saved in Git.
