# Bucket-backed remaining confirmation — 29 October 2026

**43 original fixed-row jobs / 860 games submitted; 43 RUNNING at 2026-10-29T12:08:17.904974+00:00.**
Each exact handle, source and effective 24h/cpu-upgrade configuration was checked
at launch and again in a bounded pass with zero further submissions. Together
with 21 older active jobs this respects the **64-job maximum**.
No background coordinator was started. Current manager check session 18458 is
complete; original collection session 44450 completed. Check actual processes
before another collection/dispatch cycle.

Read `strong/current-auction-bucket-remaining-launch-v3.json` for all 43 exact
handles and immutable launch-guard hashes. First handle is `6ae336803fb22a235dd5959f`;
last is `6ae3369841e90535df78b25d`. Do not resubmit them, change frozen source,
repeat preparation/uploads, or restart the old v2 dispatcher.

## Completed first proof and current coverage

Original bucket job `6ae32f6741e90535df78a8a6` is COMPLETED and independently audited:
all **16 games / 11 checkpoints**, with ten uploads while the evaluator child
remained live. Each checkpoint used one application upload call. Complete raw
legal/search receipts, policy/source identities and checkpoint/final bytes passed.
Result `strong/current-auction-first-bucket-results-v3.json` SHA-256:
`c596072e97c8ffda2969697c8e783fd41541a3807f7925325bfb9586a8c3fa5a`. See the updated
[first-job handoff](CURRENT-AUCTION-FIRST-BUCKET-2026-10-29.md).

Its unchanged evaluator took 802.10 s wall / 3,743.39 CPU s, sampled peak total
RSS 6,206,517,248 bytes. These are runtime measurements, not strength estimates.
The 203-file independently collected proof is upload/download-verified in private
model revision `2769e975d02b497c1f7b5f408aab5b2986c35f34`, path
`archives/pg-current-bucket-v3-pop-economic-capacity-v1-2p-00-collected.tgz`, SHA-256
`878d62b02b7b32bade7f13ab8662f1ce30abff86ae6c1a1696bd74da68fd9419`.
Do not repeat this successful collection/promotion.

The original 64-job v2 batch has **33 completed/audited jobs / 660 games**.
Its latest collection at 2026-10-29T12:07:01.600953+00:00 had no unknown observations or
deferred terminals. Ten upload-failed attempts and their original logs/partial
archives remain preserved. Original STOP hash remains
`07a47d46a5cfb7e36b217f82b33632dd878b3b9deb56120cb8353db12e84ed53`. This turn added **56 audited games**;
total confirmation coverage is **20,456 / 26,880**.
The 860 newly submitted games are not yet counted. **215 rows / 4,944 games**
remain never submitted. The ten failures require a separate, explicit recovery
decision retaining their original handles and evidence; they were not restarted.

## Prepared scope and unchanged execution

The new decision covers the **258 untouched original rows / 5,804 games** after
excluding the original 64 and the completed first bucket job. It preserves the
original fixed order. The current 43 happen to be five-player rows; remaining
coverage also includes 2/3/6 players. No outcomes were used to choose these rows.
All original deals, seats, variants, auction rules, evaluator code, frozen policy
weights, legal rules and search budgets are unchanged. There are no new gradients
or reserved final seeds. Scope remains Germany across 2–6 players and four rules.

`strong/current_auction_bucket_pack_v3.py` stores shared code/descriptor once,
selects exactly the requested prepared row and reconstructs the exact flat bundle
expected by the already-audited worker. Worker/collector files are unchanged.
Each individual bundle and global archive have checked manifests. **25 new tests**
passed (synthetic pack/submission failures, no real games or HF calls); actual
preparation validated **all 258 original specs/policies/contracts** and ran the
prepared non-executing CLI at 2/3/5/6 players. The actual first-job raw audit is
separate evidence. No test result substitutes for final strength qualification.

Private dataset source `coyotte508/powergrid-ai-training-v1`, revision
`bbbb69d2a0307373e518809e5fa3868738600429`, file `strong-source-current-auction-bucket-remaining-v3.tgz`, SHA-256
`c616dfa88ed654d016e75428680c88c43586bae0a4cb604476f9cd0c382d2fd7`, manifest
`ef6c5ea376282d653c3b9290b484d17be901a83c265dc361536aee5a4a26c001`. Descriptor:
`strong/current-auction-bucket-remaining-source-v3.json`. The shared compressed
source is 236,615 bytes. Preparation evidence (28 files) is privately verified at
model revision `a19068feaa95bd1b7303790fffac33f736ed8cbd`, path
`archives/current-auction-bucket-remaining-preparation-evidence-v3.tgz`, SHA-256
`f11e5e8fa8a8ce6feb73601d17966dc680a076dbdfa82a60c203e2f4806d362d`.

## Safe continuation

Frozen manager: `strong/manage_current_auction_bucket_remaining_v3.py`.
Use `ai/.venv/bin/python -u -B`, with `PYTHONPATH=ai/strong` and
`HF_HUB_DISABLE_PROGRESS_BARS=1`.

- `cycle` defaults to validation only. `cycle --execute --launch-limit 0
  --collect-limit 4` checks exact handles and collects up to four terminals,
  without new jobs. It returns after this bounded pass.
- `cycle --execute --launch-limit 64 --collect-limit 4` additionally fills only
  available slots in the immutable row order, counting original v2 live handles.
  Unresolved submission intent or unknown remote observation prevents dispatch.
- Terminal failures or collection errors preserve evidence and stop new dispatch;
  an observation timeout is not job death. Inspect the exact handle and existing
  intent/outcome; never automatically restart a job.
- Collection independently checks the original envelope, every checkpoint and
  full raw legal/search receipts. It saves the raw audit before one serialized
  model-repository archive containing the envelope, all checkpoint trees and
  review. Ambiguous promotion requires inspection, not blind reupload.
- The v2 originals still use the separate collection-only helper
  `collect_current_auction_retained_after_transport_failure_v2.py --limit 8`.
  Both managers share the original `.cycle` lock; never run competing collectors.
  Preserve both original STOP and failures. Old v2 `state.json` is stale;
  use the original failure-inspection collection state and current observations.

Recovery paths: `runs/current-auction-bucket-remaining-prepared-v3/`,
`runs/current-auction-bucket-remaining-hf-v3/jobs/`, `state.json`, `cycles/`.
Metadata archive descriptor:
`strong/current-auction-bucket-remaining-launch-evidence-v3.json`.

Continue complete collection and fixed untouched dispatch, then explicitly recover
transport failures and integrate full attempt-aware coverage/comparison. All
canonical games must be present before unchanged paired statistics/selection;
then the separate reserved final strength gate remains required. The frozen-policy
8840U serving/export benchmark is complete but is not strength qualification.
No candidate selected or qualified, no final seeds used, no deployment.
Previous goal turn: informational recap/no progress. This turn: completed raw
proof, two more original audits, verified preparation and 43 actual submissions.
Goal ACTIVE.
