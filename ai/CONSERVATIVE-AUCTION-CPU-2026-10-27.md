# Conservative auction CPU benchmark and execution handoff — 27 October 2026

## Current state

**Checkpoint: 27 October, 20:31 UTC. Research is active.** The original actual
AMD Ryzen 7 **8840U** benchmark is live on `minipc`, remote PID **3200567**, with
**210/300 requests** complete. Target directory:
`/home/coyotte508/powergrid-ai-conservative-auction-8840u-v2`.

The complete local correctness reference passed **300 requests, zero caps**.
It preserves the original 273 receipts byte for byte and adds only the 27 missing
requests. Recovery PID 2050537 has exited. Target performance and independent
cross-host parity remain pending until the unchanged full target run completes.
Do not treat a partial timing sample as the final report.

The sole HF coordinator, **PID 1919833 / session 94582**, remains live. Both
original 2p pilots are audited (16 games); both 6p jobs were directly verified
RUNNING. **Zero development submissions** at this checkpoint. All 24 code pins
match. No competing collector/submitter may run while this owner is live.

Research remains active; no new playing-strength result, qualified candidate,
deployment or reserved final seeds. The last goal turn was a verified wait on
these exact live handles. This turn consolidates conflicting incremental notes;
source policies, gates, jobs and benchmark settings remain unchanged.

## Next operations

Use `ai/.venv/bin/python -B`. Inspect the existing target; never launch it again:

```sh
ai/.venv/bin/python -B ai/strong/recover-conservative-auction-cpu-v2.py inspect-target
```

Only after successful completion and process exit:

```sh
ai/.venv/bin/python -B ai/strong/recover-conservative-auction-cpu-v2.py collect-target
ai/.venv/bin/python -B ai/strong/analyze_conservative_auction_cpu_v2.py
```

The recovery wrapper binds collection to the completed local reference. Do not
invoke the old manager directly: its default local path is the interrupted run.
Collection refuses an existing destination and independently audits **600 raw
receipts**, requiring all **300 semantic responses** to match exactly across
hosts (including choices, worlds and terminal credits, excluding timing).
Inspect any failure/partial collection before considering recovery; no blind retry.

Expected outputs:

- `runs/conservative-auction-8840u-collected-v2/assessment.json` and raw `output/`.
- `strong/conservative-auction-8840u-cost-review-v2.json`.

The timing review retains every count/rule/stage point, separates three cold
starts, and reports warm medians/ranges per stage and count. This is one saved
position per cell, not a representative gameplay latency distribution. Do not
present its descriptive percentiles as deployment latency guarantees. The split
local reference is only for correctness, not uninterrupted local timing.

After successful collection, archive the complete raw target evidence, assessment
and review using the verified evidence helper; inspect prior upload intents and
outcomes first. Update this handoff and `RESUME.md`, then commit/push only related
files on `ai/germany-baseline`. Never stage the three pre-existing modified
`policy-iteration-{development-status,labels-results,labels-status}-v2.json` files.

## Exact benchmark

The unchanged package uses three frozen policies (filter, population auction
search and dual-population auction search), four search workers, one inference
thread and the original eight-world budgets/thresholds. It covers **100 saved
public positions**: 2–6 players × four rules × five stages (choose, bid, resources,
building, bureaucracy), making 300 requests per host. Selection uses the first
non-forced menu per cell without inspecting outcomes. No new full strength games
or reserved seeds are generated.

The historical fixture pool contained private simulator state. Initial preparation
correctly rejected it before producing a package or running a policy. Preparation
then applied the exact frozen public-state projection used by the arena; all 100
legal menus remained identical. Private decks, seeds and submitted sealed bids are
excluded, while permitted public money remains. Preserve the initial rejection at
`runs/conservative-auction-cpu-initial-rejection-v2.json`.

Immutable identities:

| Item | SHA-256 |
|---|---|
| Package | `d179c066ff69243bb81d3c7ae0d9bf9999350db0bb879a9317974d2d50db7f78` |
| Benchmark manifest | `c6e1698208bdda2ab19d8d4e1f1e23e145bd16f882fcc535428729f056856bb3` |
| Cases | `407da2d87c758d7d55ef57900ee74a18ed956a49d2fe0d1fd400fb2b39afacba` |
| Runtime manifest | `a2047543f5f6a8065dd9b868dd4551531147185068c665900691c5b13c278619` |
| Recovered local status | `2bb3b20bc4a3eabed57a5c5507ddaa33bdce99b6eb901c7e7a661ba72365a072` |

Preparation lives at `runs/conservative-auction-8840u-prepared-v2/`. The target
launch guard is `strong/conservative-auction-8840u-launch-v2.json`. Keep its
manager, runner, recovery helper and package unchanged. The target uses its
existing venv and isolated HF import dependencies in offline mode; no target
environment modification was needed.

Tests already passed: six CPU preparation/admission tests, three suffix-recovery
tests, five complete-target analysis tests and fourteen development analysis tests.
The complete end-to-end cross-host result remains a separate requirement.

## Preserved interruptions and recovery

Original local PID **1904528**, session **24932**, exited with code **143** after
273/300 requests. Its process and workers were absent, stderr files were empty,
and no STOP marker existed. The signal source is unknown. Its original status
SHA is `21d45c7e81ac14bea9c7505bc0273cafe844a95a2ab8fdff11932fbf6db7729f`, and
receipt SHA is `47e67e187499b03adc77f19ad5485f17a5cb5fca7aaaf1bc4254d9f78a39d1e4`.
Both remain unchanged under `runs/conservative-auction-8840u-local-v2/`.

After inspection, detached recovery PID **2050537** re-audited all 273 receipts
and executed only the missing 27 in
`runs/conservative-auction-8840u-local-recovered-v2/`. It completed successfully.
The first recovery request's extra cold start is explicitly recorded. The local
processor is **HX 370**, not the target 8840U. Do not rerun either local process.
Guard: `strong/conservative-auction-cpu-local-recovery-launch-v2.json`.

Original HF coordinator **1685160** received SIGTERM at 19:54:38 UTC while waiting;
its state records `KeyboardInterrupt`, not an HF-job failure. Its absence, all
22 unchanged pins, no STOP marker and zero development work were checked before
starting one recovery owner. Original state SHA:
`d5f5ebcae52ffd0b2f4b35c3279fb8440cad91da96a670b492e6b46c6a79ce51`.
Source of termination is unknown; preserve its state/log.

Current owner **1919833** started at 20:02:37 UTC via
`strong/recover-conservative-auction-development-v2.py --start`. State and admission
record are under `runs/conservative-auction-development-coordinator-recovery-v2/`;
log is `runs/conservative-auction-development-coordinator-recovery-v2.log`.
The wrapper holds the original lock, preserves the tested coordinator and all
admission gates, and cannot retry failed jobs or restart itself. Old v1 owners
and their STOP marker remain unchanged. Verify actual command lines, not merely
saved state; Linux command-line arguments are NUL-separated.

Original HF handles:

| Policy | Players | Job | Checkpoint |
|---|---:|---|---|
| population | 2 | `6ae0fa243fb22a235dd31616` | completed/audited |
| population | 6 | `6ae0fa2541e90535df7674df` | running |
| dual | 2 | `6ae0fa2541e90535df7674e1` | completed/audited |
| dual | 6 | `6ae0fa2541e90535df7674e3` | running |

Only the live owner may collect these pilots and admit the frozen **10,080-game**
comparison after all 64 runtime games pass. It runs at most 64 jobs concurrently,
audits completed batches before new launches and stops on failures. After the
entire development grid passes, use the explicit current owner path:

```sh
ai/.venv/bin/python -B ai/strong/compare-conservative-auction-development-v2.py \
  --owner-state ai/runs/conservative-auction-development-coordinator-recovery-v2/state.json
```

## Durable recovery evidence

Private model repo: `coyotte508/powergrid-ai-germany-v1`. These descriptors bind
immutable revisions and verified archive/manifest hashes:

| Descriptor under `strong/` | Immutable HF revision | Contents |
|---|---|---|
| `conservative-auction-cpu-readiness-v2.json` | `8fbf712bd834843da52fd999a771048f0bbb3a73` | Benchmark additions, public projection, tests, coordinator recovery |
| `conservative-auction-cpu-recovery-evidence-v2.json` | `36de35d36dac3cb3d3113ed87bc16141fb3fa785` | Original 273 receipts/interruption and suffix-recovery admission |
| `conservative-auction-cpu-target-launch-evidence-v2.json` | `21c927539d882bb47026b16b5e7e7d9dea4bdf94` | Complete local reference, original target guard and live launch snapshot |

Restore the unchanged artifact from dataset `coyotte508/powergrid-ai-training-v1`,
source revision `8f504f71b51c6ec5bc284c02b961d90923cdce88`, then overlay the archived
benchmark additions and verify every manifest entry. No games need rerunning to
recover evidence. Earlier incremental notices remain in Git commit `1c0a712` and
these archives; this document replaces their obsolete procedural instructions.
