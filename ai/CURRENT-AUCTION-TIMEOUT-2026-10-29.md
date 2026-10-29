# Incomplete confirmation timeout — 29 October 2026

The research goal remains active, but the original 944-job confirmation cannot
qualify a candidate with missing game data. The launching coordinator stopped;
only collection of its original jobs is continuing. No replacement games,
new submissions, policy changes, partial strength comparison, or reserved final
evaluation are authorized by the collection path below.

## Original failure

- Job: `pg-current-confirm-v1-pop-search_geo-4p-05`.
- Original HF handle: `6ae2c32f3fb22a235dd50586`.
- Frozen allocation: `cpu-upgrade`, four game workers, four search workers,
  one inference thread, **3h timeout**; one deal / 16 games.
- Created: **03:53:19.475 UTC**. Coordinator stopped at **06:54:03.120499 UTC**.
- HF reports **ERROR**, message **Job timeout**. This is an actual terminal
  failure, not an observation timeout or a local network interruption.
- The preserved log reports **nine completion messages out of 16 expected
  games**. Those messages are not a substitute for raw, independently audited
  game records. The original log has no evidence archive receipt.
- A separate refetch returned identical log bytes, SHA-256
  `bb43205983d7349a0ee5dd0330e45a54ca05bd8a3c8d98fd04dedfcc438f638c`.
- The expected archive `archives/pg-current-confirm-v1-pop-search_geo-4p-05.tgz`
  was absent from private model repo `coyotte508/powergrid-ai-germany-v1` at
  immutable revision `857756d3925085c3914d1748893f437775f13559`.

The existing recovery rule only admits complete original terminal data after
a narrowly specified child-process shutdown error. This job does not meet that
rule. Its failed status, original handle, source, log, and missing evidence are
preserved; no successful receipt was created for it.

Evidence observations are in
`runs/current-auction-archive-receipt-inspection-v1/`. The original log remains
in its original job directory under `runs/current-auction-grid-hf-v1/`.

## Runtime diagnosis

The frozen planner used the slower per-game cost from its two- and six-player
runtime pilots: **164.8363 seconds/game** for the search policy. It doubled that
cost, added 900 seconds, and divided by 75% utilization to choose a whole-hour
timeout. For this four-player shard the projection was **6,174.76 seconds**,
giving a **three-hour** timeout.

This engineering allowance did not cover this deal's runtime tail. It was not a
statistical upper bound, and this failure does not justify dropping the hard
deal, treating missing games as successes, or comparing only surviving jobs.
The frozen policy, source, thresholds, seeds, workers and timeouts have not been
changed. Further resource design must account for this censored observation,
all completed cost evidence, and retention of partial raw data when a job dies.
No conclusion about partial win rates has been drawn.

Inspection of the immutable measured worker confirms that raw evidence uploads
occur in its finalization block, after execution exits. That wrapper contains no
periodic raw-data upload. A hard deadline can therefore prevent the upload even
when progress messages exist. This identifies a recovery-design requirement;
it does not prove that every possible copy of the failed job's data is lost.

## Stopped owner and original-only collection

Original coordinator **PID 3788704 / session 32582** exited with code 1 and its
process was confirmed absent. Preserve
`runs/current-auction-network-resume-v1/state.json` and its original log. Do not
restart it, overwrite its state, or reuse its launch command.

At the stop there were **621 original submitted handles**, **557 audited jobs**,
and **323 never-submitted rows**. All 471 frozen owner pins and all 621 launch
guards passed the collection admission check. The earlier stopped coordinators
and their evidence remain unchanged.

The new bounded helper is:

```sh
ai/.venv/bin/python -u -B ai/strong/collect_current_auction_originals_after_timeout_v1.py --limit 8
```

This is **collection only**. Before another invocation, inspect
`runs/current-auction-timeout-collection-v1/state.json`, its actual process and
the current tool session. Never run a competing collector. It holds both
coordinator locks plus the original operation lock, requires the stopped owner
and unchanged frozen inputs, and cannot submit jobs. Its context is immutable.

It uses the existing raw verifier for complete archives and the existing narrow
shutdown recovery verifier for eligible original ERROR archives. Missing,
ambiguous, changed or rejected evidence is saved separately as failure metadata.
Failure logs and original archive bytes remain intact. A failed original is not
silently retried or turned into success on later collection passes.

Collection reports stay under `runs/current-auction-timeout-collection-v1/`;
they always report `complete: false` and `qualified: false`. They never write the
original complete-grid result or enable selection. The original source bundle
and all immutable successful job archives are referenced, not regenerated.

**11 focused tests passed.** Positive unit archives and raw-verifier returns
were mocked. Tests cover continued collection after a failed original, missing
and ambiguous receipts, changed logs, invalid archives, rejected partial data,
preserved failure bindings, terminal limits, and rejection of a live owner.
The real admission then passed with all 471 pins and 621 original guards.

The first real collection cycle finished at **07:11:01 UTC**: **564 audited**,
**one explicit failed original**, **37 active originals**, **19 deferred terminal
originals**, **323 unsubmitted rows**, **zero new jobs/games**. Seven additional
real archives passed the unchanged raw verifier. The first collector PID was
1472607, session 42445, confirmed finished before the next pass.

The second bounded pass finished at **07:14:44 UTC**: **586 audited originals**,
**one explicit failure**, **34 active originals**, **zero deferred terminal
originals**, and **323 unsubmitted rows**. It audited another 22 original
archives. PID 1488769 / session 61145 finished successfully and the process was
confirmed absent. The first and second state snapshots are retained independently.

<!-- COLLECTION-LATEST-START -->
The third bounded pass finished at **07:27:00 UTC**: **598 audited originals**,
**one explicit failure**, **22 active originals**, **zero deferred terminal
originals**, and **323 unsubmitted rows**. It audited another 12 original
archives, bringing additional audits after the owner stopped to 41. PID 1596937
/ session 67648 finished successfully and the process was confirmed absent.
All three passes have finished; inspect the saved state before the next bounded
collection. Every immutable cycle report and log is retained.

These are dated collection observations; remote jobs may have completed since.
There were **zero new HF submissions, games, inference calls or retries** in this
recovery work. The failure diagnosis, collector, tests, frozen guard inventory,
original logs and references to the successful raw archives are preserved in
the verified archive described by `strong/current-auction-timeout-evidence-v1.json`.
The structured diagnosis is `strong/current-auction-incomplete-timeout-v1.json`.
<!-- COLLECTION-LATEST-END -->

## Resume order

1. Finish collection and preservation for the **621 already-submitted originals**,
   keeping every failure explicit. Do not submit the other 323 rows through the
   stopped coordinator.
2. Review runtime evidence and write a separate recovery/evaluation decision
   before any new study. The protocol requires diagnosis before such a decision;
   this collection helper admits no retry, replacement or new evaluation.
3. Require complete, unbiased confirmation and all original strength thresholds
   before selection. The current incomplete grid cannot satisfy that gate.
4. Preserve the existing full native/export/AMD 8840U technical proof. It remains
   technical evidence, not evidence that strength has passed. No selected or
   qualified candidate exists, and reserved final seeds remain unused.

The original complete confirmation result, independent comparison, actual
selected-final preparation/run directories, and final assessment result were
confirmed absent during this diagnosis. Existing preparation/manager/assessment
engineering checks do not change that scientific status.
