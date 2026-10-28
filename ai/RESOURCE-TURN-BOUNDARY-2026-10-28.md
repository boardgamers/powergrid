# Resource search: reproduced phase-boundary failure and separate correction

28 October 2026. Research remains active; no qualified candidate or deployment.
The auction strength study is unchanged. This work is correctness evidence,
not a strength comparison and not a replacement for the failed runtime pilot.

## Confirmed failure

Original HF job `6ae20c133fb22a235dd4146f`
(`pg-resource-turn-runtime-v1-anchored-2p`) ended in **ERROR**. It completed
seven of eight games. Episode 7 failed after 137 recorded learner actions.
The original guard, logs, partial output and failure remain preserved; no retry
or replacement was submitted.

`newTurn` means the engine has committed the previous move because it can no
longer be undone. It is not a marker for the start of every game phase. When
the last auction buyer discards a plant and immediately becomes the first
resource buyer, the phase changes to Resources while `newTurn` stays false.
The v1 anchor incorrectly required `newTurn == (trailing purchases == 0)`.
Its independent auditor also incorrectly required true at the first request.

Replaying exactly the 137 recorded learner actions through the frozen original
arena reproduced every public request, legal menu and player ordering. The
next request is episode 7, revision 315, round 12, Step 3, Resources, player 1;
its public log ends with that player's `DiscardPowerPlant(25)` and its
`newTurn` is false. The unchanged frozen anchor produces the exact assertion
failure. Reconstruction stops there. It does not finish or replace the game.

This took 20.479 seconds locally. No learner inference ran. The deterministic
search opponent was necessarily rerun along the saved prefix; its search work
was not separately instrumented and must not be represented as zero rollouts.
No new complete game, HF job, gradient update or reserved final seed was used.

Reproduction: `runs/resource-turn-boundary-failure-v1/assessment.json`, SHA256
`6bc570ee6db898dc5f4b1bedd5f7ff777f8f0498a8dd338dc101a6b9030e2988`.
The reconstructed public request SHA256 is
`966cd4a7e99b90cc4fade18a322fed1adaf95f938ca1f08ed1da0b9fda926cdf`.

## Separate v2 mechanism

`strong/resource-turn-anchor-v2.cjs` still rewinds the current player's trailing
market purchases and verifies their forward replay. It derives the commitment
flag from the public log tail, preserving false after an own plant discard.
It checks the current flag against the public tail and checks the reconstructed
forward replay's flag as well. The receipt explicitly records
`boundaryCommitted`; the actual start of buying is determined from purchase
history, independently of the undo boundary.

`strong/resource_turn_anchor_verification_v2.py` retains the actual first
request's seed and commitment flag. It rejects starting its audit after a
purchase, verifies the chronological purchase suffix and checks later flags.
It does not call the producer's rewind helper.

Neither component authenticates arbitrary forged public history. Complete,
authentic engine history remains required. In particular, a stateless helper
cannot always detect an omitted purchase combined with forged balances when
both boundary flags are false. The chronological auditor detects omitted
entries against the actual first observation.

All old helpers, policies, source bundles, runtime artifacts, launch guards and
running jobs remain unchanged. The v2 helper/auditor have **not yet been wired
into a new pinned search policy or full-game artifact**.

## Validation

The successful checker selected all 334 turns from the existing 33-game model
replay corpus, all resource requests from the three terminal two-player pilots
(including the failed pilot's saved prefix), and the reconstructed failed entry.
It also checked every legal purchase path of depth two from that entry and one
deterministic buy-until-forced path. There was no selection based on wins.

- **625 turns / 3,082 checked positions**, including 24 local purchase edges.
- Coverage: 2–6 players, original/Recharged × open/sealed, Steps 1–3.
- 621 entries have committed=true; four have committed=false.
- Every prepared anchor matches the actual first observation and seed.
- **3,078 inputs** accepted by the original anchor retain exact input parity;
  the other four are the newly covered valid boundaries it wrongly rejected.
- **488 original anchored-search seed/sampling receipts** match, with only the
  explicit v2 receipt revision and additional boundary flag normalized.
- 3,082 duplicate requests match; 3,082 corrupted commitment flags are rejected.
- Two chronological log-omission controls and one late-audit-start control are
  rejected by the independent auditor.
- Successful check duration: **97.178 seconds**. No inference, search
  continuations, complete games or HF jobs ran in this checker.

The three other false-commit entries are whole-turn episode 3/revision 350,
and corrected-atomic episode 2/revisions 332 and 365; all follow own plant
discards. They were already present in preserved runtime games.

The first checking harness stopped after one valid position because its process
transport interpreted an expected negative-test response as an exception.
That attempt, source copies and log remain in `runs/resource-turn-boundary-v2`.
The separate successful output is `runs/resource-turn-boundary-v2-recovered-v1`.
No policy code changed for this harness repair; no complete game was rerun.

Successful assessment SHA256:
`5f47c21bb6284f138269dc3856ff7e6c967142fcdd78ee6af9138c99f988d9d4`.
Machine-readable report: `strong/resource-turn-boundary-results-v2.json`.

## Original immutable runtime evidence

Private model repository: `coyotte508/powergrid-ai-germany-v1`.

- Original job archive revision: `cc490998a1d3cf4a1d65994dd7669df2dc375c6b`.
- Path: `archives/pg-resource-turn-runtime-v1-anchored-2p.tgz`.
- Archive SHA256: `0dafef7c84d923ceabcb38f52c1874f7265289dc329b11fe60b2adb42a9e0415`.
- Manifest SHA256: `466fad853bd4a04ccf0f5756af430321a4568cc9b049830277b1e5fcefabf7b1`.
- All 37 payload files and the exact file set were independently verified
  against that manifest (38 files including the manifest).
- Failed episode's 137-row receipt SHA256:
  `a25de80c6585d70bfd7fa4cca963af1419655b56d92000c86321c9f1f859ffc1`.
- Failed job measured cost: 4,073.517 seconds wall, 11,555.03 CPU seconds,
  4,878,475,264 bytes sampled peak RSS; 19,484 samples at 0.2-second intervals.

The original source bundle remains pinned by
`strong/resource-turn-runtime-source-v1.json`, private dataset revision
`8fa152b14b9940db50fb41d899c1ea6322c70405`, archive SHA256
`5b9b405f3320249e63c8b3c618dacca6456d1e2feac46336bd659cff5192f49b`.

The diagnosis, exact new sources, receipts, preserved harness failure and
recovery metadata are archived by `strong/archive-resource-turn-boundary-v2.py`.
`strong/resource-turn-boundary-evidence-v2.json` records the verified immutable
revision and hashes. Inspect existing intent/outcome before any archive retry.

## Next actions and limits

1. Finish the original auction comparison before selecting another strength
   study. Its sole coordinator PID 1075760 was live, with all code pins intact,
   at 16:30 UTC: 553 audited / 617 submitted of 648 selected batches. This is a
   snapshot, not a substitute for checking the live process.
2. Collect the remaining original six-player runtime handles. They were directly
   confirmed RUNNING during this diagnosis. The original collector stops at the
   preserved two-player failure; use a separately reviewed collection-only path
   to retain later outcomes, never silently skip the failure or resubmit it.
3. If continuing the resource experiment, integrate this correction into a
   separately pinned policy/worker/auditor artifact, checking complete receipt
   and execution parity before any separately admitted runtime study. This
   mechanism check does not establish that full-game integration has passed.
4. The original six-job / 96-game success gate is **not passed**. Preserve its
   incomplete status. No partial pilot win results support policy selection.

No candidate qualified, no final seeds used, no deployment or game publication.
