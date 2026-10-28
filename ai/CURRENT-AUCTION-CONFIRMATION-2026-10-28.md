# Current-engine auction strength confirmation

**28 October, 23:43 UTC: all 64 submitted originals are terminal; coordinator stopped after a shutdown timeout, with complete game data audited separately.**
Research remains active. No candidate is qualified or deployed, and reserved
final seeds remain unused.

## Current stop and diagnostic evidence

The original coordinator stopped at **23:29:44 UTC** and exited; session 28315
returned exit code 1. It submitted exactly 64 originals and audited seven before
detecting a terminal error. No further jobs, retries or replacements were
submitted. A fresh HF check at **23:38:41 UTC** found **57 COMPLETED, one ERROR
and six RUNNING**. Completed HF status is not an independent game audit.
The final 23:43:00 UTC inventory now shows **63 COMPLETED and one ERROR**, with
no additional failures or active jobs. All original handles match the launch
snapshot. Only seven jobs have the coordinator's complete collection audit so
far; the remaining completed originals must still be collected and audited.

The ERROR is `pg-current-confirm-v1-filter-heuristic-3p-20`, original handle
`6ae2847a41e90535df77edf5`. Episode 264 wrote its full terminal game record and
160 decision receipts before `PublicPolicyProcess.close()` exceeded its
30-second child-process shutdown wait. Python's finally-block exception then
prevented this completed record from reaching the parent summary: the summary
contains 47 games, while all 48 original terminal files exist. The reason the
child process shut down slowly is not established.

The immutable failed archive was downloaded and verified. A separately labelled
**diagnostic-only** reconstruction takes all 48 original game files, changes no
game/decision bytes, and retains the original ERROR and failed report. The
unchanged frozen auditor verified all **48 games / 6,486 decisions**, full legal
menus, exact identities, all seat/rule pairs, zero caps and execution bindings.
No policy calls, games or HF jobs were needed. This diagnosis is **not yet
admitted into the confirmation result**; no complete result or strength claim
exists. Report: `strong/current-auction-shutdown-diagnostic-v1.json`.

Original failure archive: model revision
`c544b8a6006ee5be60b90e7362962a2c7f39bcd1`,
`archives/pg-current-confirm-v1-filter-heuristic-3p-20.tgz`, SHA-256
`ea6c72626c478058b62e025bebc7dded141726554022a1d4ab7a51a60ecda903`.
Logs, original state, later HF snapshot, the diagnostic script and its successful
audit are under `runs/current-auction-grid-first-stop-v1/`. Original raw files
remain unchanged. Do not rerun this diagnosis or the failed batch.

Next: implement and test a narrowly admitted recovery path that retains all
original failure evidence and independently audits complete terminal data.
It must reject missing, partial, capped, mismatched or non-shutdown failures,
preserve all 26,880 planned games, and leave frozen policies, source and seeds
unchanged. Record a separate recovery decision before any resumed submission.
The research goal remains active; neither the original owner nor any replacement
owner is currently running.

## Original execution owner

The original coordinator was **PID 1981427 / session 28315**, executing
`strong/coordinate-current-auction-grid-v1.py --start`. Its actual `/proc`
command line was verified after launch; it has now exited as described above. State is
`runs/current-auction-grid-coordinator-v1/state.json`; the original log is
`runs/current-auction-grid-coordinator-v1-first.log`. Its 35 code/source pins
must remain unchanged. A fresh HF inventory at 23:27:37 UTC matched all **64
original handles**, all RUNNING, with zero verified confirmation games yet.
`runs/current-auction-grid-launch-snapshot-v1.json` preserves this checkpoint,
every handle and launch-guard hash. Read current state and original guards before
acting; the snapshot is not a later status guarantee.

The original owner was limited to the 944 planned originals, with at most 64 active at
once. It audits completed batches before adding work, stops on failures or
ambiguous submissions, and cannot retry, restart, train, retune or select a
policy. A completed-but-not-yet-collected race defers submissions. An observation
timeout is not evidence that the process or HF job stopped.

Do not restart this owner or submit more work before the recovery review. The
unchanged manager stops on the known failed job. For an explicitly requested pause, its `STOP` marker
is `runs/current-auction-grid-coordinator-v1/STOP`; preserve all original handles
and partial evidence. Before any later recovery, verify the actual process,
inspect the original logs and HF handles, and reconcile every existing intent.

## Completed runtime evidence and cost review

All **four original pilots / 64 games / 8,713 decisions** passed independent
raw auditing, including **48,560 uncapped continuations / 6,046,875 neural
continuation decisions**. The original collection-only PID 1655353 completed
at 23:19:23 UTC and exited. Do not restart it. Source preparation independently
re-audited all four raw artifact sets before admitting this comparison.

| Policy / players | Original HF job | Games | Workflow wall time | CPU time | Sampled peak RSS |
| --- | --- | ---: | ---: | ---: | ---: |
| Filter / 2 | `6ae2733541e90535df77d71e` | 8 | 78.31 s | 288.03 s | 2.298 GB |
| Filter / 6 | `6ae273363fb22a235dd4a65d` | 24 | 1,549.85 s | 5,920.21 s | 2.678 GB |
| Population / 2 | `6ae2733641e90535df77d722` | 8 | 589.38 s | 2,493.16 s | 6.773 GB |
| Population / 6 | `6ae273363fb22a235dd4a660` | 24 | 3,956.07 s | 18,877.60 s | 7.333 GB |

These workflows include measured startup/validation and exclude HF bootstrap
and upload. They are runtime-only games, not strength evidence, a controlled
speedup or AMD serving-latency estimates. Pilot wins are not used for sizing.

The complete original result is `strong/current-auction-runtime-results-v1.json`,
SHA-256 `fe1f794098e0755c61bb321371a133e0cf757e037c33ea462327f7d9f0afef68`.
The measured-cost review is `strong/current-auction-runtime-cost-review-v1.json`,
SHA-256 `3c2d9388f6e5c98e2f2015ac3e0a3a8c43ffe43c8d776064b80fa05ef1bd6bf8`.
Both retain all four immutable raw archive revisions and hashes. The final
pop/6p archive is revision `5d02515d32c76769bde354e22aeb029c3dd1ca89`,
`archives/pg-current-auction-runtime-v1-pop-6p.tgz`, SHA-256
`fb362484401ca029e11e53588416174701ef5794f4bde9ce5329deb379816d78`.

## Frozen scope and measured allocation

The comparison has **26,880 games**, equally divided between the unchanged
filtered `frozen-1` model and conservative population auction search. It covers
Germany, 2–6 players, original/Recharged and open/sealed auctions, public money,
all seats and 27 opponent/count cells. There are **32 fresh independent deals per
player count**, repeated across both policies, seats, rules and opponents.

All use `cpu-upgrade`, four game workers, four search workers and one inference
thread. Memory planning requires twice the measured peak to fit inside 80% of
32 GiB. Per-arm timing uses the slower endpoint per game, doubles it for unseen
deals/counts/opponents, adds 900 seconds setup allowance, and packs whole deals
to a three-hour target. Timeouts add further headroom. These are engineering
allowances, not statistical bounds.

| Players | Filter: deals/job, timeout | Search: deals/job, timeout |
| --- | --- | --- |
| 2 | 8, 4 h | 2, 3 h |
| 3 | 4, 3 h | 2, 4 h |
| 4 | 4, 4 h | 1, 3 h |
| 5 | 2, 3 h | 1, 3 h |
| 6 | 2, 3 h | 1, 4 h |

This yields **272 filter + 672 search = 944 jobs**. No HF jobs were active at
the 23:23:59 preflight. Weights, features, candidate menus, search budgets,
opponent populations and the minimum-advantage rule remain unchanged.
The fresh seed namespace is `current-auction-confirmation-v1-{players}p`,
offsets 0–31. Reserved final seeds are separate and unused.

Source admission and all 35 previously passed execution/analysis tests were
checked before submission. The exact 130,442,976-byte source archive was uploaded
and download-verified in dataset repository `coyotte508/powergrid-ai-training-v1`,
revision `7db94147918597e1da1e8ee2f4bd12b96aa067b5`,
`strong-source-current-auction-grid-v1.tgz`, SHA-256
`bb2ef01bc09f176c62545971aa02b5e9dadc947fb14dd52ca191667ba456bfe0`.
Its descriptor is `strong/current-auction-grid-source-v1.json`, SHA-256
`a4384b10eb8a4381423731bc0c315673f9214d91c1fb336aa81ef4a7102d1c5a`.
Never rebuild or overwrite this source or original upload intents.

## Interpretation and next action

Wait for all original jobs and audits. Do not inspect partial win rates to
change this study. The single prespecified primary result is population minus
filter mean win credit against geographic search, with equal player-count
weighting and paired whole-deal bootstrap intervals. All secondary and adverse
cells must be retained, including the historical four-player open-auction concern.

After the owner is complete and all 26,880 games are present, run the existing
`strong/compare-current-auction-confirmation-v1.py` once. It independently audits
every immutable job archive and raw receipt before analysis. A positive primary
interval alone is insufficient: the unchanged strength floors, count/rule
requirements and regressions also require review. Do not tune on these deals.

The actual current-engine 8840U benchmark already passed 320 exact responses;
see `CURRENT-AUCTION-CPU-2026-10-28.md`. Full selected-policy serving/export
coverage, standalone package proof and reserved final evaluation remain required
before any qualification or deployment.

## Immutable recovery archive

The 128-file launch/recovery archive was uploaded and download-verified in
private model repository `coyotte508/powergrid-ai-germany-v1`, revision
`51bcd4362ec78690bf91cc54fe9aa0aecd8a7277`,
`archives/current-auction-confirmation-launch-evidence-v1.tgz`, SHA-256
`a1f29e996bea95745a1d492bf50a470daacc4d27018982c89b457d2f62d60bc1`.
It contains the first 64 exact launch guards, live-owner snapshot, complete
runtime cost review, all four pilot receipts, tested source/analysis pins and
the source admission/upload records. The four immutable raw pilot archives and
the immutable full execution source are referenced, not regenerated.

Descriptor: `strong/current-auction-confirmation-launch-evidence-v1.json`.
This is a launch checkpoint, not a completed confirmation or evidence of its
playing strength. Preserve it and inspect subsequent original handles in
`runs/current-auction-grid-hf-v1/` rather than replaying archived launch commands.

The later shutdown diagnosis is separately archived and download-verified at
model revision `500ad08c88eefdd638abdc95538ecb6fd9218e60`,
`archives/current-auction-shutdown-diagnostic-evidence-v1.tgz`, SHA-256
`4594697ab72ae31605c6cc349574b582b943955f60ec98acc0efcd7b3ae3d2be`.
Its 27 files include the original failed summary, omitted game/decision files,
diagnostic script, derived report, full raw audit and stopped-owner evidence.
The complete 48-game original archive remains referenced by its immutable
revision. Descriptor: `strong/current-auction-shutdown-diagnostic-evidence-v1.json`.
This archive does not authorize recovery or change the original ERROR.
