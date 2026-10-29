# Current-engine confirmation: original terminal-data recovery

Research is active. No candidate is qualified or deployed; reserved final seeds
remain unused. The complete 26,880-game confirmation protocol, 944 original job
slots, policies, current engine, search budget and statistical analysis remain
unchanged. This recovery does not generate replacement games.

<!-- RECOVERY-STATUS-BEGIN -->
**Later checkpoint, 00:35:27 UTC:** the same coordinator is live with all 54
pins unchanged. **108 jobs / 5,888 games** are audited; 172 originals submitted.
Fresh HF inspection found all 64 unverified originals RUNNING, with no new
terminal failure. Exact handles and guard hashes:
`strong/current-auction-confirmation-recovery-progress-v1.json`. The original
launch snapshot below remains historical recovery evidence.

**29 October, 00:18:52 UTC: recovery admitted; remaining confirmation is running.**
All **64 initial originals / 3,456 games** passed their complete data audits:
63 retain HF COMPLETED and one retains HF ERROR with its separate terminal-data
recovery. Initial collector PID 2299815 / session 43290 exited successfully.
Fresh inspection of those exact 64 HF handles matched the recorded statuses.

New sole coordinator **PID 2398668 / exec session 50170** started at
00:18:04 UTC. Its actual process and all 54 code/source/admission pins were
verified. The first 64 never-submitted rows were launched; HF independently
confirmed **64 RUNNING** at 00:18:52 UTC. There are now **128 total original
submissions**, with 816 still unsubmitted at that snapshot. No replacements,
reruns, new weights or final seeds. Do not restart either prior process.

Inspect `runs/current-auction-confirmation-recovery-v1/state.json`, its actual
`/proc` process and `runs/current-auction-confirmation-recovery-v1-first.log`.
Do not run a competing collector/launcher while the owner is alive. An observation
timeout is not a terminal status. The owner collects/audits before adding work,
maintains at most 64 active jobs and stops on any unadmitted failure. It must not
be automatically restarted. An explicit user pause uses its `STOP` marker.

Admission: `strong/current-auction-confirmation-recovery-admission-v1.json`.
Immutable first-64 collection:
`runs/current-auction-confirmation-recovery-initial-collection-v1.json`.
Launch/process/HF/guard snapshot:
`runs/current-auction-confirmation-recovery-launch-v1.json`.
<!-- RECOVERY-STATUS-END -->

## Why this recovery is valid

The original owner, PID 1981427 / session 28315, stopped and exited after
64 submissions. Its final status snapshot has 63 COMPLETED and one ERROR. The
ERROR is `pg-current-confirm-v1-filter-heuristic-3p-20`, original handle
`6ae2847a41e90535df77edf5`. All 48 terminal game files and their decision receipts
exist. A 30-second child shutdown timeout after episode 264 was written caused
the parent summary to omit that game. The original summary contains 47 games.
The reason for the slow shutdown is still unknown.

The new validator admits only this exact frozen arena's post-terminal shutdown
failure class. It requires the complete original game range, exact agreement
between every existing summary entry and game record, errors corresponding
exactly to the omitted terminals, the known command and timeout, empty affected
child stderr, no pre-terminal failure files, zero game/search caps, and matching
source, policy and execution provenance. Every original file is hash-checked.
The unchanged legal-action/decision auditor and execution-binding auditor must
then pass on all games. The rule is independent of wins or losses and applies
equally to any later original job with the same complete-data failure class.

Original HF ERROR, failed summary, wrapper status and archive stay intact. A
separate derived summary references all original terminal records; raw game and
decision files are never changed. Recovered verification is written to
`verified-terminal-recovery-v1.json`, never to the normal `verified.json`.
Missing, capped, altered or otherwise failed executions remain failures and
stop further submissions. No automatic retries or restarts are implemented.

## Evidence and tests

- The reusable validator passed on the actual failed archive: **48 games /
  6,486 decisions**, zero policy calls, game reruns or HF submissions.
  Report: `strong/current-auction-recovery-preflight-v1.json`.
- **26 tests** cover strict failure acceptance, incomplete/altered data,
  no resubmission of existing handles, collection before submission, explicit
  admission, STOP behavior, coordinator startup and complete-grid comparison.
- Review found a missing original-pilot module reference in the new manager
  before launch. It was fixed and the actual manager startup interface tested.
  First code and logs remain under
  `runs/current-auction-recovery-before-startup-fix-v1/` and the first test logs.
- All **35 original execution pins** remain unchanged. The new collection
  readiness freezes **52 input hashes** in
  `strong/current-auction-confirmation-recovery-readiness-v1.json`.
- Storage review projects approximately **409 GB** for the whole grid's raw
  files plus cached archives, using the larger measured endpoint per arm.
  Free space at review was **626 GB**; a 50% projection margin narrowly fits.
  This is a pilot extrapolation, not a hard upper bound. Monitor actual growth
  and preserve unarchived evidence. Report:
  `strong/current-auction-recovery-storage-review-v1.json`.

The immutable failed raw archive is in private model repo
`coyotte508/powergrid-ai-germany-v1`, revision
`c544b8a6006ee5be60b90e7362962a2c7f39bcd1`, path
`archives/pg-current-confirm-v1-filter-heuristic-3p-20.tgz`, SHA-256
`ea6c72626c478058b62e025bebc7dded141726554022a1d4ab7a51a60ecda903`.
The prior diagnostic-only evidence remains separately archived at revision
`500ad08c88eefdd638abdc95538ecb6fd9218e60`.

The source is unchanged: dataset `coyotte508/powergrid-ai-training-v1`, revision
`7db94147918597e1da1e8ee2f4bd12b96aa067b5`,
`strong-source-current-auction-grid-v1.tgz`, SHA-256
`bb2ef01bc09f176c62545971aa02b5e9dadc947fb14dd52ca191667ba456bfe0`.

## Durable recovery archive

The complete **334-file** metadata snapshot is privately archived and
upload/download-verified in `coyotte508/powergrid-ai-germany-v1`, revision
`5d8b4c90af3a7b0925add6a92f44afac5ee93389`, path
`archives/current-auction-confirmation-recovery-evidence-v1.tgz`, SHA-256
`37d17c844984bd8c6345cf1ea13744027308b2424fd96ac4649a66fa3ccaf128`.
Descriptor: `strong/current-auction-confirmation-recovery-evidence-v1.json`.
It preserves readiness, admission, tests, original and recovered failed reports,
all 128 launch guards and the exact live-process/HF snapshot. It references the
64 immutable original raw archives and unchanged source bundle; no games are
regenerated. Inspect existing archive intents/outcomes before any retry.

## Execution and remaining work

1. Completed collection and audit of all 64 original job archives, preserving
   the failed job's ERROR with its separate complete-data recovery. All handles,
   guard hashes and verified evidence are in the immutable initial snapshot.
2. Recorded explicit admission in
   `strong/current-auction-confirmation-recovery-admission-v1.json`, binding
   the complete initial collection, readiness, unchanged source and stopped
   original owner. Admission is required before any remaining submissions.
3. Started `strong/coordinate-current-auction-confirmation-recovery-v1.py --start`
   once, with the process and session above. Do not repeat this command. It uses the original launch manager and immutable HF source for only
   the never-submitted rows, with at most 64 active jobs. Preserve its original
   handle, log and state under `runs/current-auction-confirmation-recovery-v1/`.
   It audits collection before launching, never retries, and stops on any
   unadmitted failure. The old coordinator must not be restarted.
4. After all **944 jobs / 26,880 games** have verified complete data, use
   `strong/compare-current-auction-confirmation-recovered-v1.py`. It independently
   re-audits every immutable raw archive, explicitly reports every original
   ERROR/recovery, and uses the unchanged paired whole-deal analysis and
   requirements. Do not analyze partial wins or tune the frozen policies.
5. Confirmation is not final qualification. The separate held-out strength,
   export/serving and target-machine gates remain required.

Do not touch the three pre-existing policy-iteration status/result modifications,
the production game checkout, or reserved final seeds. Private HF evidence
archives and research-branch pushes are authorized. No UI deployment is part
of this work.
