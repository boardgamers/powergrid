# Resource-search runtime pilots — 28 October 2026

## Current state

Six original HF jobs were submitted at approximately **14:52 UTC**, covering
**96 runtime-only games**. Direct inspection at **14:59 UTC** found all six
RUNNING. No pilot has yet been collected or independently audited. These are
fresh complete engineering trajectories, excluded from strength estimates,
candidate selection and final qualification. No new gradient training was run.

| Mode | Players | Games | Original HF job |
| --- | ---: | ---: | --- |
| Corrected atomic search | 2 | 8 | `6ae20c1241e90535df775236` |
| Corrected atomic search | 6 | 24 | `6ae20c123fb22a235dd4146d` |
| Anchored atomic search | 2 | 8 | `6ae20c133fb22a235dd4146f` |
| Anchored atomic search | 6 | 24 | `6ae20c1341e90535df775238` |
| Whole-turn search | 2 | 8 | `6ae20c133fb22a235dd41471` |
| Whole-turn search | 6 | 24 | `6ae20c1341e90535df77523a` |

These are the only admitted resource runtime handles. Every guard is `launched`;
there is no ambiguous submission. Do not launch replacements or repeat a pilot.
Inspect the actual jobs and original logs after a failure or timeout, preserve
partial evidence and review the cause before changing anything.

## What this establishes

The preceding [integration](RESOURCE-TURN-ANCHORED-POLICY-2026-10-28.md) tested
initial-search parity, complete focal resource turns, restart behaviour and an
independent sampling auditor. These pilots exercise those adapters and auditors
through fresh complete games, including later rounds and resource-turn boundaries.
They also measure full-game wall time, CPU time and sampled process-tree memory.
Success would admit further engineering/experimental planning, not prove that
resource search improves the frozen model.

The three modes separate corrected public inputs with a new sample seed after
each purchase, corrected inputs with a stable turn-start seed, and committing to
the initially selected complete resource bundle. All use the same v3 artifact,
frozen-1 model, eight sampled worlds, one search worker, one inference thread and
2,400-step continuation limit. Other phases retain the frozen filtered model.

Each cell plays one complete paired deal against `search_geo`: every focal seat
and original/Recharged × open/sealed. Seeds are
`resource-turn-runtime-v1-2p` and `resource-turn-runtime-v1-6p`, deal zero.
These seeds are not reserved final seeds. There are four concurrent games per
job, six `cpu-upgrade` jobs, and a **four-hour timeout per job**. No automatic
retry or background resource-study coordinator was created.

The timeout derives from prior measured HF resource-search pilots, not an
assumed device speed: 1,204.86 s at two players and 1,896.21 s at six players.
The planning bound is 900 s setup + four times the larger wall time = 8,484.86 s,
below 75% of four hours. The factor four allows for halving game concurrency
and changed-policy overhead. This is a planning estimate, not a guarantee.
Prior sampled peak process-tree RSS was 8.15 GB; shared pages may be counted
more than once. Final costs must come from the new jobs' measured receipts.

## Preflight completed

- All seven bundled specifications validated without executing simulations.
  The seventh is a local-only replay control; the launcher rejects submitting it.
- The wrapper exactly reproduced **eight previously recorded games and 1,360
  decisions**, including their terminal states. Independent full-game audit
  passed; zero search rollouts or caps. This is repeated validation evidence,
  not eight additional independent strength games.
- The local control measured 14.289 s wall, 71.11 CPU-s and 1.679 GB sampled
  peak process-tree RSS, including startup and audit. These are local wrapper
  measurements, not an AMD 8840U benchmark.
- Eight fake-API submission tests passed: duplicate submission prevention,
  preservation of unknown outcomes, existing intents, changed source, invalid
  handles, unadmitted cells, local-control exclusion and exact bootstrap/env.
  They submitted no HF jobs. Their receipt binds the actual launcher sources.
- The source bundle was uploaded, downloaded at its immutable revision and
  SHA-256 verified before launch. Node comes from the existing verified cache.

The completed checks should not be repeated absent a changed implementation or
a concrete unresolved concern. The pinned source and old artifacts stay intact.

## Source and recovery records

`strong/resource-turn-runtime-source-v1.json` binds the complete source:

- Private HF dataset: `coyotte508/powergrid-ai-training-v1`.
- Revision: `8fa152b14b9940db50fb41d899c1ea6322c70405`.
- Object: `strong-source-resource-turn-runtime-v1.tgz`.
- Archive SHA-256:
  `5b9b405f3320249e63c8b3c618dacca6456d1e2feac46336bd659cff5192f49b`.
- Source manifest SHA-256:
  `d695e83d822f54ef7412ebe23e535ea87226317e778f8041adacd008614cd364`;
  1,514 files plus the manifest.
- Artifact descriptor SHA-256:
  `f41f16f64bf4e9b068e09e15116a6f02c5254ef60c01bd7650a0d7ad356a2e57`.
- Protocol SHA-256:
  `f09275d1871fa59324a9cbd11fda6195f696bb18e7fda8c5237bf00b3afeb2c8`.

`runs/resource-turn-runtime-prepared-v1/` has the exact source, preflight records
and local control. `runs/resource-turn-runtime-tests-v1.json` records the eight
submission tests. `runs/resource-turn-runtime-hf-v1/` contains upload intent,
upload receipt, source preparation, six original launch guards and status files.
The status and collection files are observations, not proof that a job remains
live; query the exact original handles when resuming.

`strong/resource-turn-runtime-launch-evidence-v1.json` indexes a separate private
HF recovery archive containing these small records, launcher sources, control
receipts and this handoff. The full 1,514-file source is referenced through the
immutable dataset archive instead of uploaded twice. Check existing local and
remote archive intents/outcomes before retrying an interrupted upload.

## Collection and next decision

First verify that no resource collector is currently alive. The bounded
collection operation never submits a job:

```sh
ai/.venv/bin/python -u -B ai/strong/manage-resource-turn-runtime-v1.py collect
```

It checks the original handle's command, source, flavor and admitted environment;
fetches terminal logs; downloads and verifies the raw immutable evidence; and
independently re-audits each complete game with the pinned v3 auditor. Re-audits
use a separate directory and preserve the original sealed job evidence. Verified
jobs are cached. Failed or ambiguous jobs stop collection and remain preserved;
there is no replacement operation. If collection itself is interrupted, inspect
the original audit directory and process before attempting recovery.

Only six successful independent audits totalling 96 games can create
`strong/resource-turn-runtime-results-v1.json`. Until then the complete-game
runtime gate is unproven. No strength conclusion should be drawn from pilot wins.

The frozen auction study remains separate and unchanged. Its original active
owner is PID **1075760**, `coordinate-conservative-auction-attempts-v1.py`.
At 14:57 UTC it had **511 audited / 575 selected jobs submitted / 648 planned**;
the two preserved pre-evaluation infrastructure failures account for 577 total
HF attempts. Its process was checked directly. Do not run a competing auction
collector. Finish the full 10,080-game auction comparison before choosing the
next strategy study; do not select from partial win results.

Research remains active. No candidate has passed final qualification, no
reserved final seed has been used, and no game deployment is authorized here.
The last human-facing reminder was a verified wait with a live-process check;
the runtime preparation/launch and this recoverable snapshot are progress.

The **99-file launch/recovery archive** was uploaded and downloaded successfully
at private model revision `1de5edec1e444280c580de5a2d37ee5dd3d14661`,
`archives/resource-turn-runtime-launch-evidence-v1.tgz`, SHA-256
`b4d0193946bdb7185023b7152e47aceaa1c574c55ffe71ec8eded37dbe88cb33`.
Its descriptor and this final reference are saved with the launcher in Git.
