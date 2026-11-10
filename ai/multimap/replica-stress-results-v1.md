# Fixed-replica population stress study: final results

**Status: both panels complete and integrity-verified; 48/48 fixed saved-outcome
replay comparisons passed. No model selected, promoted, qualified or deployed.**

The two previously trained replicas improve substantially over the frozen PPO2
comparator under **both tested opponent schedules**. This is credible
fixed-checkpoint research evidence, not a human-strength claim or a release gate.

## Design and completion

-   Germany, USA, France, and UK & Ireland; 2–6 players; Original/Recharged;
    open/sealed auctions. Italy, Benelux and reserved final roots were not used.
-   **80 cells × eight independent deal roots per panel**, with all focal seats.
    Each root/seat is shared by replica1, replica2 and PPO2; the PPO2 games are
    counted once, then reused in both paired comparisons.
-   **15,360 saved games / 1,280 independent roots**, split into 7,680 games and
    640 roots per panel; 2,560 games per arm per panel. Seats and arms sharing a
    root are not independent observations.
-   Strong: all nonfocal opponents are the pinned historical reference on Germany,
    and the frozen original expert24 on the other three maps.
-   Mixed: the preregistered deterministic schedule alternates expert24 with a
    weaker pool of PPO0/PPO1/PPO2/teacherV2, plus reference on Germany. It uses the
    actual deal indices 0–7, not a repeated four-deal schedule. Neither replica
    is an opponent, and this is not uniform sampling of all possible populations.
-   Both original jobs completed. **Nine requested job-hours across two jobs**;
    the conditional three-hour recovery was neither needed nor submitted and was
    not repurposed. No unknown submissions, fitting, labels or new selection.

## Four preregistered primary comparisons

The metric is **fractional win credit**, averaged equally over the 80 cells—not
an unweighted pooled game win rate. Within a cell, paired focal-seat differences
are averaged within each root, then over its eight roots. The standard error is
`sqrt(sum_c(sample_variance_ddof1(root_differences_c) / 8)) / 80`.

| Panel  | Fixed replica versus PPO2 | Difference, percentage points | Four-primary adjusted interval |
| ------ | ------------------------- | ----------------------------: | -----------------------------: |
| Strong | Replica1                  |                    **+15.32** |           **[+12.23, +18.41]** |
| Strong | Replica2                  |                    **+14.96** |           **[+11.67, +18.25]** |
| Mixed  | Replica1                  |                    **+19.30** |           **[+16.03, +22.57]** |
| Mixed  | Replica2                  |                    **+18.68** |           **[+15.47, +21.90]** |

These are Bonferroni **98.75% normal intervals**, using
`z = 2.4977054744123737` for the family of four primaries. Coverage is approximate
and conditional on the frozen policies and schedules. Shared PPO2 makes the
contrasts dependent; Bonferroni does not require independence. No direct
replica-superiority test, winner selection, pooled training-recipe inference or
precise training-variance estimate follows from this table.

Each of the four map-wide and five player-count-wide marginal contrasts is
positive in both panels for both replicas, including its exploratory unadjusted
95% interval. This does **not** imply improvement in every map/count combination
or full cell.

## Adverse results and watchpoints retained

All 114 subgroup sets per panel, raw-arm estimates, cell/deal means, occupancy
results, reciprocal two-player outcomes and watchpoints are preserved in the
[full result record](replica-stress-results-v1.json), not just favorable excerpts.
Subgroup intervals below are **exploratory, unadjusted 95% normal intervals**.

-   Negative exact cell means: **strong 7/80 for replica1 and 8/80 for replica2;
    mixed 3/80 and 2/80**. Rational tie-credit recalculation resolves two additional
    saved negative floating-point values (about `−7e−18` and `−1.4e−17`) to exact
    zero. The original floating summaries remain unchanged, and the supplementary
    exact-sign evidence is retained.
-   **Strong USA / 3 players**, across rules: replica1 **−3.65 pp
    [−14.55, +7.26]**, replica2 **−2.08 pp [−13.94, +9.77]**.
-   **Strong USA / 3 / Original / sealed**: replica1 **−25.00 pp
    [−45.47, −4.53]**; replica2 **−4.17 pp [−32.96, +24.62]**. The replica1
    interval excludes zero only on this exploratory, non-multiplicity-adjusted
    basis; it is not a confirmatory subgroup claim.
-   **Mixed Germany / 2 / Recharged / sealed**: replica1 **−18.75 pp
    [−50.49, +12.99]**, replica2 **−12.50 pp [−52.86, +27.86]**.
-   Other adverse examples remain visible: strong replica2 USA / 4 / Original /
    open **−18.75 pp [−46.14, +8.64]**, and mixed replica2 France / 2 /
    Recharged / sealed **−18.75 pp [−50.49, +12.99]**.

| Fixed watchpoint                 | Strong R1 / R2, pp | Mixed R1 / R2, pp |
| -------------------------------- | -----------------: | ----------------: |
| Germany / 2 / Recharged / sealed |    +31.25 / +37.50 |   −18.75 / −12.50 |
| USA / 3 / Original / sealed      |     −25.00 / −4.17 |   +16.67 / +12.50 |
| USA / 3 / Recharged / sealed     |      +4.17 / +4.17 |    +8.33 / +29.17 |
| USA / 2, all rules               |    +28.13 / +17.19 |   +16.41 / +28.13 |

The mixed occupancy analysis has **five cell-memberships with only one selected
root**. Occupancy four contains just **five selected roots across four cells**;
its replica2 interval barely excluding zero is not robust assurance. The
calculation uses selected-root equal-cell means, with all eight scheduled
positions and fixed `8/K` weights for variance. Nonmembership zeros are analytical
contributions, not fabricated losses. Different cell mixes and deterministic
membership prevent causal occupancy comparisons. Mixed ddof=1 also includes
lineup mean variation and is conservative in expectation, not unbiased.

## Historical Germany reference: still not established superiority

Against the all-reference strong Germany lineup, raw equal-cell credits are:

-   Replica1: **31.69%**, exploratory 95% interval **[27.80%, 35.57%]**.
-   Replica2: **30.85%**, exploratory 95% interval **[26.84%, 34.87%]**.

Both intervals include the analytical balanced `mean(1/n) = 29%`. That value is
context, **not a newly played focal reference control or a qualification
threshold**. The mixed Germany lineup is not an all-reference comparison.
No homogeneous-expert neutrality claim applies to these replica focals.

## Integrity, independent review and preservation

The completed external audit authenticated both immutable snapshots, packaged
source/runtime/reference provenance, all six decoded checkpoint tensors and full
saved configurations, actual job settings/ownership/budget/chronology, and the
original canonical paid-job ledger. PPO0's historical saved configuration was
checked separately from its current serving configuration; no checks were relaxed.
The pinned reference model/filter/source and principal current environment are
verified, without claiming every historical transitive dependency was reproduced.
Historical Git push wall-clock time is not independently exposed; authenticated
HF publication and actual job timestamps are distinguished from recorded Git
sequence evidence.

All **48 fixed replays matched every saved non-timing field**. Only `featureMs`,
`inferenceMs`, `referenceMs` and `seconds` were excluded. Model tensors, buffers,
modes, gradient flags, class, width and residual bounds remained unchanged.
Replays produced zero labels and zero new independent strength observations.
Both genuine attestations were issued only after both replay sets passed. The
exclusive durable attempt records remain retained; there were no replay retries.

An independent standard-library review recalculated all four primaries and all
114 subgroup sets from the saved raw games, checked literal opponent assignments,
and independently compared the 48 existing replay outcomes. It found no numerical
or replay mismatch. Auditor engineering validation comprised **790 full-suite
Python tests** plus **117 final portable component tests** after a documented
last test-only fix; the exact test revisions and limits remain recorded.

The [publication receipt](replica-stress-audit-v1.json) pins the bounded private
archive in the existing research repository. It includes full statistics,
genuine proofs/replays, independent review scripts/findings, source, validation
logs and adverse operational evidence. Original outcome snapshots retain their
own immutable job-upload revisions; they are not replaced by the audit archive.
The reference cache, both environments, prior studies and canonical paid ledger
remain intact.

## Readiness assessment

**The strength evidence is now credible enough to justify considering a serving
prototype. The integrated bot is not yet controlled-playtest ready or release
ready.** The production bot has not been replaced by either checkpoint, and these
PyTorch policies are not drop-in legacy Germany ONNX replacements.

The remaining steps are serving/export and action-output parity, platform
state/legality/deduplication checks, timeout/error fallback, and target-host
latency, concurrency, memory and persistence validation. Then supervised human
playtesting is needed, followed by scope/acceptance criteria, monitored rollout
and tested rollback before any release decision. Automated gains alone cannot
establish human strength or robustness outside the tested schedules.

This study introduces no automatic progression gate and authorizes no serving
integration, checkpoint selection, promotion, deployment or BGS publication.
