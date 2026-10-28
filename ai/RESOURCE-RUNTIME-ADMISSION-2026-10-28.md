# Resource runtime: terminal originals and corrected v4 pilots

All six original resource pilots are terminal. Five jobs / **88 games** passed
independent audit with zero rollout caps. The original anchored two-player job
failed on the reproduced turn-boundary defect. Its partial evidence is preserved;
the original 96-game success gate **failed**. This does not qualify any policy.

## Original measured outcomes

These workflow times include startup and validation, but exclude HF bootstrap,
download and upload. Peak RSS is sampled across the process tree and can count
shared pages more than once. Failed-job measurements are partial costs.

| Mode | Players | Audited games | Wall seconds | CPU seconds | Peak RSS, GB |
| --- | ---: | ---: | ---: | ---: | ---: |
| Corrected atomic | 2 | 8 | 2,814.58 | 8,462.71 | 4.398 |
| Corrected atomic | 6 | 24 | 12,244.20 | 37,674.11 | 6.066 |
| Anchored atomic, failed | 2 | 0 | 4,073.52 | 11,555.03 | 4.878 |
| Anchored atomic | 6 | 24 | 12,396.80 | 37,481.68 | 5.007 |
| Whole-turn | 2 | 8 | 858.53 | 3,079.67 | 4.556 |
| Whole-turn | 6 | 24 | 7,056.35 | 22,701.91 | 4.638 |

`strong/resource-turn-runtime-outcomes-v2.json` records the exact six original
handles, immutable raw archives, successful independent audits, failed partial
evidence and final measurements. The final bounded collector completed at
18:28 UTC. It ran no policy inference or new games.

The failed job reported seven completed games before the eighth failed. These
are not counted as audited successes. The original failure and source remain
unchanged; the [boundary fix](RESOURCE-TURN-BOUNDARY-POLICY-2026-10-28.md) is in
a separate v4 artifact.

## Separate corrected-runtime admission

The reviewed admission is `strong/resource-turn-runtime-admission-v2.json`,
SHA-256 `43cc87530989cd83b064a8ea889ea6424522b7a51629501eb2924e54fc7bd8d9`.
It binds the terminal original-outcomes report and the unchanged prepared v4
source/protocol. The same launcher and collector test sources remain pinned;
their 26 and 21 passing offline checks were verified, not rerun.

The maximum original workflow was 12,396.80 seconds (3.44 h). The new budget is
**six hours per job, at most two jobs / twelve aggregate job-hours**. This exceeds
1.5 times that observed maximum plus 3,000 seconds for bootstrap, upload and
trajectory variation. This is a bounded estimate, not a guaranteed completion
time. Keep `cpu-upgrade`, four concurrent games per job, eight sampled worlds,
one search worker and one inference thread. No GPU scaling is justified by
these measurements.

Exactly two corrected-runtime jobs were submitted at approximately 18:31 UTC:

| Job | Games | Original v2 handle |
| --- | ---: | --- |
| `pg-resource-turn-runtime-v2-anchored-2p` | 8 | `6ae23f6e41e90535df779e68` |
| `pg-resource-turn-runtime-v2-anchored-6p` | 24 | `6ae23f6e3fb22a235dd467c4` |

Both cover every seat and all original/Recharged × open/sealed combinations
against `search_geo`, with fresh runtime seeds `resource-turn-runtime-v2-2p`
and `resource-turn-runtime-v2-6p`, deal zero. They use v4 anchored atomic search;
other phases retain the same frozen filtered model. These are 32 engineering
games, excluded from win-rate selection, strength comparisons and final tests.
They do not replace or relabel any original failed run. No gradients changed.

The launcher freshly inspected all six original HF handles and their source
provenance immediately before submission. Both new durable guards are
`launched`, with no ambiguous outcome. Do not resubmit or automatically retry.
The six-hour timeout expires approximately 00:31 UTC on 29 October; authoritative
HF status determines completion, not the local clock.

## Source and recovery

The verified execution source is in private dataset
`coyotte508/powergrid-ai-training-v1`, revision
`e8eef00401823710ca646574edc3372363160940`, object
`strong-source-resource-turn-runtime-v2.tgz`, SHA-256
`ce73a76efa7552035064e55b781fd58f4a5872247420b70ae99f4bfb31b9e727`.
Source manifest: `7678b22c535648280394cb7374c926bfcb2ea88da5c2d8b35100cda64a3c299a`.
The full source is referenced, not duplicated in the evidence snapshot.

`strong/resource-runtime-terminal-evidence-v1.json` indexes the separate recovery
archive: all original independent receipts, final original-outcomes report,
reviewed admission, new source/launch guards, recovery helpers and these notes.
Inspect prior local and remote archive intents/outcomes before any retry.

Before collection, check that no collector is alive. Use only the v4 collector
for the two new handles:

```sh
ai/.venv/bin/python -u -B ai/strong/collect-resource-turn-runtime-v2.py
```

It cannot submit jobs. It validates exact source/admission/launch bindings and
immutable raw archives, independently audits all game decisions and pairing,
reuses completed audits and preserves failures. Inspect interrupted audit
directories rather than rerunning blindly. State is under
`runs/resource-turn-runtime-collected-v2/state.json`. Two verified successes /
32 games create `strong/resource-turn-runtime-results-v2.json`; preserved
terminal failure instead creates `strong/resource-turn-runtime-terminal-v2.json`.

The auction coordinator remains the sole owner of the separate 10,080-game
strength comparison. Complete that comparison before selecting another strength
study. No candidate qualified, reserved final seeds remain unused, and no game
deployment is authorized by this runtime work.

The 39-file recovery archive was uploaded and download-verified at private model
revision `0103931e42d6a549b0cbc11d1ec4f18d6c21f892`, object
`archives/resource-runtime-terminal-evidence-v1.tgz`, SHA-256
`d4c5f6c8cb6c61f1ab65ccb84bdadc9e683e0c1c4a78a63b4262964e9d3fa2f5`.
Both corrected handles were directly observed RUNNING in the first v4 collection;
there is no background resource collector. Inspect current handles on resumption.
