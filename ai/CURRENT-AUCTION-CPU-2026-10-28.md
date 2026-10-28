# Current-engine auction policies: AMD 8840U benchmark

**28 October, 23:19 UTC: completed and independently audited, 320/320 exact responses.**
Research remains active. This is engineering latency and cross-host response
validation, not playing-strength evidence or the final 2,553-position qualification.

The original target is `minipc`, **AMD Ryzen 7 8840U w/ Radeon 780M Graphics**,
PID **3461338**, isolated directory
`/home/coyotte508/powergrid-ai-current-auction-8840u-v1`.
It finished at **23:16:01 UTC** and its original process has exited. Collection
and a fresh-interpreter audit verified all 320 raw responses, legal menus,
policy identities, player order and complete reference pairing. All **2,960
uncapped continuations / 512,203 neural continuation decisions** match the
reference execution; search changed 24 of its 88 searched decisions. Only
elapsed-time fields are excluded from semantic comparison.

| Policy | Warm auction median | Other-stage median | First request including startup |
| --- | ---: | ---: | ---: |
| Filtered model | 5.35 ms | 5.63 ms | 0.685 s |
| Population auction search | 8.34 s | 6.49 ms | 9.853 s |

These canonical medians cover 39 warm auction and 60 other-stage requests per
policy. The additional 40 discount/menu and 20 simultaneous-wrapper cases per
policy are reported separately, with breakdowns for every player count. The
complete target replay took 550.95 seconds wall / 764.96 CPU-seconds. These are
fixed-position observations, not representative gameplay latency percentiles
or a controlled comparison of old and current engine speed.

The final report is `strong/current-auction-8840u-results-v1.json`, SHA-256
`5617f2005a812e82711c92a90db2a162baac4e6e5de1bf2d087b255f9e0216fe`.
Raw outputs and the successful independent audit are preserved in
`runs/current-auction-8840u-collected-v1/`. Do not rerun the benchmark or collector.

No previous Power Grid benchmark process was found on the target before this
launch. Its existing Python environment and offline HF import dependencies are
reused, without package installations or production routing.

## Scope and reference construction

Both unchanged confirmation policies use the current engine and repaired public
pending-player handling, runtime manifest SHA-256
`fc135130689140b6fd72a76e6e14c59a7fea59717b858d330bac0c7f6aad93df`.
Weights, feature revision, eight-world budget, minimum advantage, four search
workers, one inference thread and auction-only search scope are unchanged.

The benchmark contains **160 positions × two policies = 320 requests**:

- 100 canonical positions: every 2–6-player count, four rule combinations and
  five decision stages, selected previously without viewing outcomes.
- All 40 previously audited auction discount/menu cases.
- All 20 actual simultaneous-wrapper cases, including pending actors and
  opponents auto-passing after becoming unable to afford an auction.

All 160 population-search references reuse the existing successful current-engine
v2 execution. These contain 2,960 uncapped continuations and 512,203 neural
continuation decisions; they were **not rerun locally**. The 20 wrapper filter
references are also reused. Only 140 inexpensive current-engine filter calls
were newly executed to complete the reference set for the exact repaired
runtime. No new full games, training or HF jobs were needed.

Reference provenance is bound to `runs/current-engine-auction-v2/assessment.json`
and its archived original receipts. The assessment hash was checked against
`strong/current-engine-auction-evidence-v2.json`, not merely trusted from its
success flag. Request order and legal menus are preserved. Exact comparison
removes only `elapsedMs` fields, retaining moves, request revisions, policy
identities, player order and every sampled world, continuation and credit.

Six focused tests passed for complete case coverage, missing/duplicate cases,
reference hashes, hidden inputs/public money, player order/legal menus and
semantic equality that excludes elapsed time only. The preparation additionally
audited all 320 actual reference responses with the frozen runtime verifiers.

## Original package and execution

- Package: `runs/current-auction-8840u-prepared-v1/package.tgz`, 130,737,945 bytes.
- Package SHA-256: `9289cefa5aec94efaa693d0b6cadfe02ba44a2f5d3882277c05921b1fe183cd3`.
- Benchmark manifest: `3da298955ba7c682d5bec8ba85a4942430250abf14577515206f7e789681bc33`.
- Cases: `e79423fbce381e240ec22372e73e019afc0f5f1fa97fc758996c412d60be3fcc`.
- Exact reference hashes: `af1df3dab4b5dbcc62c5f61c8f58ec0f77959f85de64053ddde0460888f783de`.
- Original launch guard: `strong/current-auction-8840u-launch-v1.json`.
- Manager: `strong/benchmark-current-auction-8840u-v1.py`.
- Frozen packaged runner: `strong/current_auction_cpu_v1.py`.

Keep the prepared package, runner, manager, test log and original guard unchanged.
The launch manager writes an exclusive intent before contacting the target;
an ambiguous outcome must be reconciled without another launch. Target files,
partial receipts and failures must be preserved. Never restart on an observation
timeout or overwrite an existing output/collection directory.

Inspect the exact original process with:

```sh
ai/.venv/bin/python -u -B ai/strong/benchmark-current-auction-8840u-v1.py inspect
```

The following original collection command has already succeeded; it is recorded
for provenance and must not be repeated:

```sh
ai/.venv/bin/python -u -B ai/strong/benchmark-current-auction-8840u-v1.py collect
```

Collection uses a fresh interpreter and the pinned standalone package to audit
every raw target response and complete reference pairing. It preserves cold
startup separately and reports canonical, discount and wrapper timings. These
are descriptive fixed-position timings, not representative gameplay latency
percentiles. The canonical subset has 39 warm auction and 60 other-stage
requests per policy. No controlled speedup should be claimed against the old
engine merely by subtracting its earlier timings.

## Parallel research and remaining requirements

The original HF runtime collection owner PID 1655353 / session 81765 completed
at 23:19:23 UTC and has exited, with all 40 source/input pins unchanged. All four
original pilots / 64 games are now collected and audited, including final pop/6p
handle `6ae273363fb22a235dd4a660`. Its result is
`strong/current-auction-runtime-results-v1.json`, SHA-256
`fe1f794098e0755c61bb321371a133e0cf757e037c33ea462327f7d9f0afef68`.
Do not restart the collector. Full runtime cost review and grid admission remain
the next separate step; no confirmation grid has been admitted or submitted.
This target benchmark cannot submit HF work or admit the confirmation grid.

Review all four completed pilots' measured costs before separately
preparing the frozen 26,880-game fresh strength confirmation. The final gate,
selected-policy full serving coverage and standalone qualification package
remain outstanding. No candidate qualified and reserved final seeds remain unused.

## Verified recovery archive

The full original package, source helpers, six-test log, local-reference
provenance, target guard and first live snapshot are archived in private model
repository `coyotte508/powergrid-ai-germany-v1`, revision
`f491ed02f10cb71c00e7291d621bc7eb48387f22`, path
`archives/current-auction-cpu-launch-evidence-v1.tgz`, downloaded SHA-256
`1e90da09dd84698dbe6f3cf70ca0c5c5bf2424e49c06c972aab70083fe06fe47`.
The 19-file archive includes the exact 130 MB package, so recovery does not need
to regenerate any reference or simulation. Its descriptor is
`strong/current-auction-cpu-launch-evidence-v1.json`; this records launch and
reference readiness, not completed target verification.

The **completed target evidence** is separately archived and download-verified
at revision `632d31b0653a033da8f9a11a389d59311ad4c48f`,
`archives/current-auction-cpu-results-evidence-v1.tgz`, SHA-256
`957cf4130c573a79dcae9f3b178efdbe043bc0e07b8b28b4925cf69ca6f78788`.
Its 21 files contain all raw target receipts, the independent audit, timing
report and recovery metadata; the exact execution package is referenced through
the immutable launch archive above. Descriptor:
`strong/current-auction-cpu-results-evidence-v1.json`. Do not repeat collection
or either upload.
