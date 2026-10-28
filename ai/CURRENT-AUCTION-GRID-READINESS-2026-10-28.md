# Current-engine confirmation: execution and analysis readiness

**23:43 UTC superseding update:** original coordinator PID 1981427 has stopped
and exited after 64 submissions. One job returned ERROR on a post-terminal
30-second child shutdown timeout. All 48 original game files passed a separate
diagnostic raw audit, but recovery is not admitted yet. See the current stop,
immutable failure evidence and required recovery review in
[the execution handoff](CURRENT-AUCTION-CONFIRMATION-2026-10-28.md). Do not restart
the original owner or repeat source preparation; no policy/source changes or
resubmissions have occurred. All 64 originals are now terminal: 63 COMPLETED,
one ERROR. Only seven have the coordinator's collection audit so far.

**23:27 UTC execution update:** all four original pilots / 64 games have passed
and their measured costs admitted the unchanged confirmation. Source preparation
re-audited all raw receipts. The sole coordinator **PID 1981427 / session 28315**
is live; all first 64 original HF jobs were confirmed RUNNING. The full allocation
is 944 jobs / 26,880 games, with a maximum of 64 active jobs. Read
[the execution handoff](CURRENT-AUCTION-CONFIRMATION-2026-10-28.md) for source,
cost review and recovery. The earlier collection-only owner has exited; do not
repeat the historical preparation/launch commands below or start a competing
collector. All policies, protocols and tested execution code remain unchanged.

**22:44 UTC collection update:** PID 1655353 / session 81765 now runs the
collection-only `strong/finish-current-auction-runtime-v1.py`. Both its actual
process and the remaining original HF handle were verified live. Read
`runs/current-auction-runtime-finish-v1/state.json` and its sibling first-run log
before acting. Do not invoke the bounded collector below while this owner is
alive. It exits after the four original audits and does not admit or submit the
confirmation. Complete measured-cost review remains the next prerequisite.

**22:39 UTC update:** the original filter/6p job also passed its audit, bringing
the completed total to 40/64 games. Its 24-game workflow took 1,549.85 seconds,
5,920.21 CPU-seconds and 2.678 GB sampled peak RSS. Its immutable raw archive is
revision `b25c58f05464206c16e86398604ecf59285c675e`, SHA-256
`2e238588df08feae3d4a6a4414d661844a2d8bb2d4d877ceda7c965f51673cd6`.
See `strong/current-auction-runtime-progress-v3.json`. The pop/6p original was
confirmed RUNNING at 22:39:45; its earlier log check reported 8/24 complete.
No grid source, coordinator or new jobs exist. The original 22:35 readiness
snapshot and its archived bytes below remain unchanged.

**28 October, 22:35 UTC. Research remains active; no candidate qualified.**

The two original two-player runtime pilots are complete and independently
audited. Their 16 games establish runtime and portability, not playing strength.
Both original six-player pilots were confirmed RUNNING by HF at 22:35 UTC.
No confirmation source, submission or coordinator exists yet. The frozen
26,880-game comparison must wait for all four original pilots and their complete
cost review. Do not restart or replace an original job automatically.

## Runtime checkpoint

`strong/current-auction-runtime-progress-v2.json` records all four handles,
source binding, audit receipt hashes, immutable archives and measured costs.
The previous one-job checkpoint remains unchanged.

| Completed pilot | Games | Workflow wall time | CPU time | Sampled peak process-tree RSS |
|---|---:|---:|---:|---:|
| Filter, 2 players | 8 | 78.31 s | 288.03 s | 2.298 GB |
| Population search, 2 players | 8 | 589.38 s | 2,493.16 s | 6.773 GB |

The search pilot completed 12,000 uncapped continuations and 1,123,276 neural
continuation decisions. These costs include measured startup and validation,
exclude HF bootstrap/upload, and do not measure AMD serving latency. Comparing
them with different historical deals does not establish a controlled speedup.

Original handles:

- Filter/2p: `6ae2733541e90535df77d71e`, completed and audited.
- Filter/6p: `6ae273363fb22a235dd4a65d`, running at the checkpoint.
- Population/2p: `6ae2733641e90535df77d722`, completed and audited.
- Population/6p: `6ae273363fb22a235dd4a660`, running at the checkpoint.

## Frozen comparison and tested tooling

`strong/current-auction-confirmation-protocol-v1.json` remains unchanged:
32 independent deals per count, every seat, four rule combinations, 2–6 players,
27 opponent/count cells, two fixed arms and 13,440 games per arm. The single
primary contrast is the equally count-weighted search-opponent credit difference.
Whole-deal paired bootstrap intervals preserve correlations across seats,
rules, arms and opponents. All secondary results and adverse cells are retained.
The reserved final protocol and seeds remain untouched.

Five test suites passed, **35 tests total**, using synthetic results and mocked
HF submissions. No new jobs, games, neural inference or gradient updates were
needed for these tests.

| Suite | Tests | What it covers |
|---|---:|---|
| Resource planning | 6 | Complete pairing, cost-only sizing, invalid/incomplete pilots, memory and finite-value checks |
| Source/job manager | 7 | Durable intents before submission, duplicate/ambiguous outcomes, original handles, locks and completion races |
| Statistical analysis | 13 | Complete 26,880-record synthetic grid, exact tie credits, identities, independent bootstrap calculation, chance-boundary rejection and final-gate separation |
| Comparison admission/archive audit | 5 | Completeness before analysis, original handles, pinned raw archives and rejection of changed evidence |
| Coordinator | 4 | Audit before submission, stop markers, and no launch after failure or completion |

The initial comparison-test harness omitted a `hashlib` import. Its two failing
tests, original source, log and diagnosis are preserved under
`runs/current-auction-comparison-test-failure-v1/`. The corrected five-test suite
passed. This was a test-harness error, not a policy or evaluation failure.

An initial metadata snapshot also assumed the wrong location for the source
hash. The archive preflight stopped on the missing snapshot before creating an
upload intent or making an HF request. The source binding was then checked via
the original launch guards and collection summary; original/final test logs and
this preflight failure are preserved in the evidence archive. Runtime receipts,
policies and jobs were unchanged.

The readiness descriptor binds the tested code, protocols and test logs. Mutable
documentation and runtime checkpoints are archived, but are not execution pins.
`strong/current-auction-grid-readiness-evidence-v1.json` records the verified
private HF archive at revision `7b466be6a632a349d63e6ba36247fb7f570369c2`,
`archives/current-auction-grid-readiness-evidence-v1.tgz`, downloaded SHA-256
`71e08cfafb9a96dc4bd753923d6279f4e8dccf80ddb0a90145b703a7250c76f9`.
It preserves 57 files, including the pre-upload document and all failure evidence.

## Next execution, in order

Use `ai/.venv/bin/python -u -B` from this worktree. Inspect existing intents and
original process handles before a retry. The current bounded collector is:

```sh
ai/.venv/bin/python -u -B ai/strong/manage-current-auction-runtime-v1.py collect
```

Only after all four original pilots pass, `prepare-current-auction-grid-v1.py
prepare` re-audits their raw artifacts and sizes the complete schedule from
measured cost, without reading pilot wins. It keeps the tested CPU hardware,
four concurrent games, four search workers and one inference thread. It uses
the slower endpoint per game for each arm, a 2× time allowance, 900 seconds of
setup allowance and whole-deal batches targeting three hours. The timeout has
additional headroom; sampled memory requires a 2× margin within the chosen
capacity. These are engineering allowances, not statistical runtime bounds.

Review the resulting allocation before running, in sequence:

```sh
ai/.venv/bin/python -u -B ai/strong/manage-current-auction-grid-v1.py prepare
ai/.venv/bin/python -u -B ai/strong/manage-current-auction-grid-v1.py upload
ai/.venv/bin/python -u -B ai/strong/coordinate-current-auction-grid-v1.py --start
```

The coordinator refuses to start before complete pilot admission and verified
source upload. It owns at most 64 active original jobs, collects and audits
before submitting more, stops on failure, and never automatically restarts,
retunes, trains or selects a policy. Do not run a competing collector while it
is alive. A completion between collection and submission defers the batch until
the next audit.

After the entire coordinator finishes, run
`compare-current-auction-confirmation-v1.py`. It independently verifies every
raw archive and receipt before comparing all 26,880 outcomes. It checks the
unchanged final-protocol strength requirements on these confirmation deals,
but cannot qualify a candidate: reserved final evaluation, complete selected
policy export/serving verification and actual-8840U packaging remain separate.

The earlier historical study supports carrying forward the cheaper population
search recipe. It does not establish current-engine strength, performance on
other maps, expert human strength or a general learning plateau.
