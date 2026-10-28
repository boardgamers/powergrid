# Corrected v4 runtime collection — 28 October 2026

The separately prepared v4 resource runtime package now has its collection path:
`strong/collect-resource-turn-runtime-v2.py`. This closes the collector follow-up
in [the launcher handoff](RESOURCE-RUNTIME-LAUNCHER-2026-10-28.md). **No actual
admission, execution-source upload or corrected-pilot job exists yet.**

The collector uses the launcher's pinned source/admission checks and requires
both original launch records with distinct HF handles. It observes those exact
handles and verifies the remote bootstrap, source and admission environment.
There is no submission, restart, retry, cancellation or simulation operation.

For a completed pilot, it verifies the immutable archive hash, exact manifest,
all raw file hashes and wrapper provenance, including the separate admission
file. It then runs the pinned **v4 independent auditor** on the recorded receipts
with the complete paired schedule required. A successful saved audit is reused;
changed source, admission, raw evidence or audit output is rejected. An
interrupted audit directory requires inspection before any further audit.

Failures remain explicit. Raw partial results are preserved and are never
counted as independently audited successes. Missing/ambiguous archive receipts
remain unverified; unknown remote stages remain unresolved. Interrupted log
downloads do not leave a partial file masquerading as a complete terminal log.
An early failed process may legitimately have zero CPU/RSS samples; that evidence
is retained, while successful jobs require positive measurements.

Only **two successfully audited jobs / 32 games** can create
`strong/resource-turn-runtime-results-v2.json`. A terminal set containing a
preserved failure instead produces `strong/resource-turn-runtime-terminal-v2.json`
without passing the success gate. Terminal jobs with unresolved evidence remain
in the collection state until reviewed; they cannot create a successful result.
All reports remain runtime-only, with no qualification or strength-selection use.

## Verification

- **21 offline tests passed**, using synthetic archives and a fake HF API.
  These test real archive extraction/hash checking and orchestration, not actual
  corrected full-game performance. The semantic auditor itself was already
  checked by the previous pinned v4 integration and recorded-game preflight.
- Tests cover both successful jobs, a failed job followed by the other job,
  cached-audit reuse, changed admissions/audits, corrupted archives, absent or
  duplicate receipts, remote-stage/environment disagreement, interrupted logs
  and audits, duplicate handles, wrong game counts, and early zero-sample failure.
- The audit-driver test checks that the subprocess imports the v4 auditor and
  keeps full pairing enabled. It does not execute inference or a new game.
- The actual collector command was invoked once against the current checkout.
  It rejected the absent original terminal report before creating a collection
  directory or contacting HF. The rejection log and receipt are retained with
  the tests.
- The initial 20 tests passed. Code review then identified the zero-sample
  failure case; those initial sources/log/result were preserved under
  `ai/runs/resource-turn-runtime-collector-tests-v2-initial`. The final 21-test
  run includes the fix and additional case. No failed test run is hidden.

Final test sources/result/log are under
`ai/runs/resource-turn-runtime-collector-tests-v2` and the adjacent `.log`.
`strong/resource-runtime-collector-evidence-v2.json` indexes the verified private
HF evidence archive. The prepared v4 source package remains the separate immutable
preflight archive; it was neither changed nor repacked here.

## Current runs and next action

The previous goal turn made progress: it implemented, tested, archived and pushed
the one-attempt launcher. This turn completes its collection counterpart.
Neither turn adds a strength result.

The bounded original-HF collection at **17:38 UTC** still found three verified
resource successes / 40 games, one preserved failed job and two running six-player
originals. At **17:43 UTC**, the sole auction coordinator PID 1075760 was confirmed
alive; its latest state recorded 579 audited / 644 submitted of 648 selected
batches. No competing coordinator was started or frozen policy changed.

Continue collecting the six originals with
`strong/collect-resource-runtime-outcomes-v2.py` after checking for a live local
collector. Wait for their terminal measured costs, preserve all outcomes, and
review a concrete budget before creating the separate corrected-runtime
admission. The two proposed v4 pilots remain runtime-only. Once they actually
exist, use the new v4 collector; never point the original v1 collector at them.

Finish the complete unchanged auction comparison before choosing another
strength study. No new HF jobs, inference, full game trajectories, gradients or
final seeds were used for this collector work. No candidate qualified or deployed;
the research goal remains active.
