# Conservative auction search — runtime pilots, 25 October 2026

Updated 2026-10-25T12:06:40.457367+00:00. **Both two-player pilots are complete and independently
verified; both original six-player pilots are RUNNING.** Six-player completion
and resource admission remain pending. No candidate is qualified; final seeds
are unused. Pilot outcomes do not count as strength evidence.

**One live coordinator now owns collection and the authorized next comparison:**
PID **1061599**, original execution session **42688**, started 12:02 UTC.
It waits for all four original pilots, admits resources from complete audited
measurements, prepares/uploads the unchanged policies with development controls,
then submits/collects the frozen 10,080 games with at most 64 jobs active.
Do not start another owner or call the mutating collectors while it is live.
Seventeen code files are pinned and unchanged. Any failure or changed source stops
for inspection; original handles and partial artifacts are retained. The owner
cannot train, select, qualify or deploy a model.

Completed costs for eight two-player games per arm, four simultaneous games:

| Arm | Wall seconds | CPU seconds | Sampled peak RSS | Simulations |
|---|---:|---:|---:|---:|
| Population | 519.906 | 2291.83 | 6,600,781,824 bytes | 9,576 |
| Dual population | 835.857 | 3965.48 | 6,810,087,424 bytes | 17,872 |

All **2,777 public decisions / 27,448 continuations** passed raw auditing with
zero caps. These are HF batch costs, not AMD 8840U per-move latency or strength.
The original raw archives are pinned in `strong/conservative-auction-development-readiness-v1.json`.
The six-player observation at 11:56 UTC found population **6/24** and dual **2/24**
games complete; both original handles were directly confirmed RUNNING again in
the readiness archive. Do not extrapolate strength or resource admission from
these partial six-player runs.

## Scientific decision

The quoted 30.86% overall / 15.625% Recharged-sealed four-player results are
superseded by frozen-1's **51.56% / 39.06%** in the 16-deal development comparison
(256 overall games; 64 Recharged sealed). These are development results, not
final qualification. See [the hybrid screen](HYBRID-SCREEN-2026-10-24.md) and
[the completed fidelity review](SURROGATE-FIDELITY-2026-10-25.md).

Continue **selective auction search**. Earlier broad auction search produced
promising gains and serious rule-specific regressions. Building/combined and
resource search should not be scaled unchanged. Learned-opponent continuation
fidelity did not improve the primary metric, so it is tested only as additional
coverage, not a replacement for the existing population.

The frozen three-arm development protocol compares filtered model, conservative
population search and conservative dual-population search. Search uses eight
paired sampled worlds per included population and overrides only for pooled
terminal-credit advantage strictly above 1/8, with no negative margin in any
included population. This is a heuristic screening rule, **not calibrated
confidence**. Future focal play still uses the filtered policy approximation.
Sealed bids and future deck order are hidden; public player money is available.

## Original jobs — preserve these handles

| Pilot | Original HF job |
|---|---|
| conservative_population-2p | `6addea031e112550ce7eaa88` |
| conservative_population-6p | `6addea031e112550ce7eaa8a` |
| conservative_dual-2p | `6addea04046eb82b1ece4faf` |
| conservative_dual-6p | `6addea04046eb82b1ece4fb1` |

Each two-player pilot has eight games; each six-player pilot has 24. All four
rule combinations and seats are included, versus search_geo. Total **64 pilot
games**, excluded from strength estimates. Separate seed prefix:
`conservative-auction-runtime-v1-{players}p`.

Each job uses **cpu-upgrade, four simultaneous games, four search workers,
one inference thread, five-hour timeout**. The timeout allows 900s setup plus
four times the previous measured six-player combined-search runtime (2862.51s),
within 75% of the limit. This is a conservative initial allowance, not a measured
bound for the new recipe. Actual wall time, CPU time and sampled process-tree RSS
are captured. The complete-policy latency on AMD 8840U is still unmeasured.

## Checks completed

- All 1,522 previous source files remain byte-identical; the new bundle has 1,540 files.
- Five actual descriptor/admission checks and 72 public requests across all
  three arms passed. **1,992 auction continuations** exactly match archived
  component simulations; zero caps. Original verification session **58888 completed**.
- The measurement wrapper repeated the existing eight-game engineering fixture:
  **1,607 exact public decisions and complete terminals**, zero caps. Local wall
  16.15s, CPU 69.82s, sampled process-tree RSS 1,796,087,808 bytes. This validates
  the measurement wrapper, not new playing strength. Session **68514 completed**.
- Seven ownership/admission/measurement tests passed. No retry after an ambiguous
  submission; existing handles are reused; tokens are not written into guards.
- Source archive uploaded/downloaded/hash-verified: dataset revision
  `6edcec8f03e3bf0c84f08ed2c02e458e887d1ca5`, archive `strong-source-conservative-auction-runtime-v1.tgz`,
  SHA256 `99227f1fc4bd8976e168db88f2c330eeff9947d320526d83dffaeff59b492328`. Source manifest
  `187812b75ce569ea8302cd405d0dfc7b2b79d2eb5837970dbefc8c0db1e39521`. Sessions **45390 / 41522 completed**.
- Original four submissions **5390 completed**; read-only collection **76244
  completed** with all four RUNNING, none verified yet.
- Launch/preflight evidence: HF model repo revision `ad73f20efddc935106b38ee949db5b81a4b77898`,
  archive SHA256 `d9136d74c7df1fef611665ec00334f3b1e980e254cbc4748b6cb0fb2c526b1ec`,
  **76 files**, downloaded/hash-verified. Archive session **84034 completed**.

## Development tooling and resume

Working directory: `/home/eliheros/Documents/Codex/2026-09-26/je-x20-2/work/powergrid-ai`; branch `ai/germany-baseline`.

- Owner `strong/coordinate-conservative-auction-development-v1.py`; state
  `runs/conservative-auction-development-coordinator-v1/state.json`; log
  `runs/conservative-auction-development-coordinator-v1.log`. Verify its PID via
  `/proc/1061599/cmdline` and compare all state `code_hashes` before acting.
  Do not restart because an observation times out. Original session **42688** is
  still running, with output redirected to that log.
- `strong/prepare-conservative-auction-development-v1.py` validates complete
  original runtime receipts and preserves every existing source file. It chooses
  whole-deal batch sizes using cost only: a doubled measured per-game envelope,
  900s setup, target three hours, at most 75% timeout utilization, and a doubled
  sampled-memory allowance inside 80% of 32 GiB. If these resources do not fit,
  it stops for a new hardware admission rather than silently changing the policy.
- `strong/manage-conservative-auction-development-v1.py` packs/uploads that
  admitted source, submits only frozen development rows, caps active jobs at 64,
  and independently audits uploaded raw receipts. Launch/collect ownership and
  uncertain-submission behavior preserve original handles. Source preparation,
  actual new-source HF execution and complete results are still **pending**.
- **Ten tests pass**: five schedule/resource-admission checks and five actual
  submission-primitive checks. All batch sizes 1/2/4/8 have exactly the same
  10,080 deal/seat/rule cases. Four deals per job would mean 162 shards, but that
  is only a preview; no batch size is admitted until all pilots complete.
- Source wrappers and engine remain unchanged. **Do not add repeated engineering
  games** unless the original execution exposes a concrete failure. Next evidence
  needed is the full fresh comparison, including adverse counts/rules.
- At owner completion, archive/review all 10,080 games. No automatic candidate
  selection occurs. The unchanged final strength gate, complete-policy export,
  standalone package checks and actual AMD 8840U benchmark remain necessary.

Readiness/archive proof: `strong/conservative-auction-development-readiness-v1.json`.
Private HF revision **66a9f8b9e36a96498aa96ec4a0654acf947b6023**, archive SHA256
**69eaa46b1ebfe80ec00134fcafaedcc51515904b1ac4bd07829502fd68aa7197**, **30 files**, downloaded/hash-verified.
Original archive execution **18289 completed**. It records the coordinator, code,
passing tests, original live job statuses and both complete two-player raw archives.

The previous and current goal turns both made concrete progress. No new gradients,
reserved seeds or strength claim in this turn; the runtime pilots and next grid
serve the existing strong-AI objective. The same surrogate-training recipe remains
unpromising, but no general AI plateau has been established.
