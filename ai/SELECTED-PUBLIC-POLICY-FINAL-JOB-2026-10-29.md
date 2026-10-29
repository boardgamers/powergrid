# Complete-policy final job transport

**29 October: 12 lifecycle tests and five real-artifact validation cases passed.**
This is execution infrastructure only. No candidate has been selected, no new
HF jobs or games were created by this work, and reserved final seeds remain
unused. The independent confirmation continues under its existing coordinator.

The older `launch-final.py` path uses the earlier arena/model configuration.
The newer `public_policy_final_runner_v1.py` already supports the complete
standalone policy, including exact auction search settings and opponent model
identity, but its portable HF wrapper previously admitted engineering jobs only.

The new `strong/public_policy_selected_final_job_v1.py` supplies the corresponding
final-purpose wrapper. It invokes the unchanged frozen final runner, first in
validation-only mode. Actual execution additionally requires an explicit flag,
immutable source revision/hash, a separately selected candidate with immutable
selection evidence, and the exact original launch authorization. The runner
independently checks the full policy identity, reserved shard, fingerprint and
freeze chronology. Existing output cannot be overwritten or automatically
retried. Failures retain original receipts; execution never implies qualification.

The tests cover default validation, immutable bytes/file sets, escaping paths,
missing selection/launch evidence, wrong purpose, changed candidate identity,
immutable source requirements, failed admission, exclusive execution, retained
failures and complete final-purpose receipt binding. All policy execution in
these unit tests is mocked.

Real validation used the exact current-engine conservative-population artifact
already pinned by the confirmation source. It accepted its unchanged full
configuration and rejected a wrong fingerprint, unknown reserved shard, altered
search-worker setting, and substitution of the filtered model for auction search.
All five cases ran without `--execute` or `--upload`; none created an execution
directory or made a policy inference call. Synthetic selection/launch documents
are contract fixtures only and must never authorize a real job.

The first harness passed three cases, then rejected its own attempted 16-world
fixture before reaching the intended identity test: the frozen verifier supports
eight worlds. The corrected harness changes search workers instead and reuses
the three successful original validations. The first log, script and partial
case remain preserved. Final report:
`strong/selected-public-policy-final-job-preflight-v2.json`.

## Archived evidence

All 52 metadata files, original/corrected harnesses, failed setup evidence,
validation controls and logs are privately archived and download-verified at
model revision `27738f3229ce8f7f93d0c3144a002334c37d143c`, path
`archives/selected-public-policy-final-job-evidence-v1.tgz`, SHA-256
`9aae3d316c8819afa30a790a331cdb1d7daabb1e4849003208a6f7701f482233`.
Descriptor: `strong/selected-public-policy-final-job-evidence-v1.json`.
The archive references the unchanged current-engine source rather than copying
its artifact again. Do not rerun the preflight or repeat the upload.

## Remaining integration

1. Complete and independently audit all 26,880 confirmation games, including all
   adverse cells and original failures. Select/freeze a candidate only if the
   unchanged requirements and review support it.
2. The [offline source builder](SELECTED-PUBLIC-POLICY-FINAL-SOURCE-2026-10-29.md)
   now preserves and validates every unchanged contract using synthetic controls.
   Build/admit the real immutable final HF source and launch manager that
   bind the selected complete-policy identity, selection archive and original
   launch intents. Preserve the unchanged final schedule of 320 shards / 20,160
   games; derive batch resources from complete measured evidence. The new job
   wrapper is not itself a launcher or selection authority.
3. Full export/serving and standalone-package checks on the actual AMD 8840U
   are complete for both unchanged policies: 2,553 positions each, all 5,106
   responses independently audited and bound to the native checkpoint. Bind
   the [archived technical proof](CURRENT-FULL-SERVING-2026-10-29.md) to the
   exact selected policy/settings; do not repeat the completed replay.
4. Execute the reserved strength plan only after admission; independently audit
   every original result and apply the unchanged final qualification gate.

The confirmation owner's current status and recovery instructions are in
[the recovery handoff](CURRENT-AUCTION-RECOVERY-2026-10-29.md). Do not modify its
54 pinned inputs or run a competing collector. This transport work does not
change its policies, source, budget or analysis.
