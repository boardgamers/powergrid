# Conservative auction search — runtime pilots, 25 October 2026

Updated 2026-10-25T11:40:21.460828+00:00. **Four original HF jobs submitted and directly observed RUNNING
at 11:38 UTC. Completion and runtime admission are pending.** The frozen
10,080-game strength comparison has not launched. No candidate is qualified,
no gradients were run in this step, and reserved final seeds remain unused.

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

## Resume directly

Working directory: `/home/eliheros/Documents/Codex/2026-09-26/je-x20-2/work/powergrid-ai`; branch `ai/germany-baseline`.

1. Run `ai/.venv/bin/python -B ai/strong/manage-conservative-auction-runtime-v1.py collect`.
   It only inspects the four original jobs, downloads their immutable evidence
   when complete, and independently audits all raw decisions and terminals.
   Preserve failure artifacts and original handles. Never restart due to a
   tool observation timeout. No coordinator is active for these four jobs.
2. Once all four are verified, archive the complete results and use actual
   wall/CPU/RSS measurements to choose development sharding/resources.
3. Execute the already frozen **10,080-game** development protocol across all
   counts/rules/opponent cells. Its protocol SHA is
   `ab4dbb7fdde1689d988671ca4abb4bd25ed52cd912dc0d4a94c6ca7f61c57e61`. Do not add more unchanged compatibility work
   unless these originals expose a concrete failure. The scientific question
   needs fresh whole-game outcomes, including adverse cells.
4. Select only on complete development evidence. The unchanged final strength
   gate, exact full-policy export/package checks and actual AMD 8840U benchmark
   still remain. Do not substitute model-only latency for complete hybrid latency.

Code: `strong/manage-conservative-auction-runtime-v1.py`,
`strong/public_policy_measured_job_v1.py`,
`strong/prepare-conservative-auction-runtime-v1.py`.
State/guards: `runs/conservative-auction-runtime-hf-v1/`.
Preflight: `runs/conservative-auction-runtime-prepared-v1/`.
Persistent descriptors: `strong/conservative-auction-runtime-source-v1.json` and
`strong/conservative-auction-runtime-launch-evidence-v1.json`.
The launcher admits only these four pilots; it cannot submit the full grid or
reserved final games. The engine and policy code remain unchanged.
