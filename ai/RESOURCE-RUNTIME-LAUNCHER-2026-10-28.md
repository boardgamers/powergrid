# Corrected resource runtime launcher — 28 October 2026

The corrected v4 runtime package now has a separate one-attempt launcher:
`strong/launch-resource-turn-runtime-v2.py`. Its 26 offline tests pass. No actual
runtime admission, selected timeout, execution-source upload or new job exists.
The positive test cases are synthetic and never submit to HF.

This is runtime preparation, not a new strength result. The full auction study
continues unchanged; finish its complete comparison before choosing another
strength study. No gradients, new full games, final seeds, qualification or
deployment were introduced by this work.

## What is ready

- The exact source package from [the preflight](RESOURCE-RUNTIME-PREFLIGHT-2026-10-28.md):
  source manifest `7678b22c535648280394cb7374c926bfcb2ea88da5c2d8b35100cda64a3c299a`.
  Its recorded control already reproduced eight games / 1,360 decisions; no
  additional replay or simulation was performed for the launcher.
- Exactly two proposed HF jobs: `pg-resource-turn-runtime-v2-anchored-2p`
  (eight games) and `pg-resource-turn-runtime-v2-anchored-6p` (24 games). Both
  use the separately corrected v4 policy, fresh runtime seeds, all seats and
  all four rule combinations, four concurrent games, and `search_geo`.
- Immutable source upload, verified Node cache and separate admission transport.
  The bootstrap decodes the exact admission bytes outside the frozen source,
  verifies their SHA-256 and passes the file/hash to the already pinned wrapper.
- Durable exclusive upload/submission intents. A repeated completed launch
  returns its original handle. An ambiguous submission, invalid returned handle
  or unfinished prior intent stops for inspection; none is automatically retried.

## What must happen before using it

The launcher does **not** create its own admission. Its `prepare` operation
currently fails before creating a directory/archive because the original terminal
outcome report and real admission do not exist.

1. Finish collecting the **six exact original resource handles** using the
   collection-only `strong/collect-resource-runtime-outcomes-v2.py`. Inspect any
   actual running collector first. Preserve original failures and their raw
   evidence; never replace a failed handle or pretend the 96-game gate passed.
2. Once all originals are terminal, verify
   `strong/resource-turn-runtime-outcomes-v2.json`, original source/guards,
   raw archive manifests, successful independent-audit receipts and failed
   partial evidence. The new launcher repeats these checks and refuses missing
   evidence. Immediately before submission it also inspects the six original HF
   handles and checks their actual stages, bootstrap and source environment.
3. Review the measured wall/CPU/memory costs and set a separate budget in
   `strong/resource-turn-runtime-admission-v2.json`. Bind its source/protocol,
   two exact job-spec hashes and terminal original-outcomes hash. The format
   permits 2–12 hours per job on `cpu-upgrade`, at most two concurrent jobs;
   **these bounds are not a selected or approved timeout**. Its `budget_review`
   must repeat the outcomes hash, state `max_total_job_hours = 2 * timeout / 3600`,
   and give a dated reason based on measured costs. Scope remains runtime-only,
   retries false, qualification false and final seeds unused.
4. Prepare the execution source, upload/download-verify it once, and then use
   the launch operation with `--execute` only after reviewing the concrete
   admission. Default launch is dry. Do not rerun preparation, overwrite intents
   or infer authorization from a test fixture.
5. The subsequent [v4 collection implementation](RESOURCE-RUNTIME-COLLECTION-2026-10-28.md)
   is now ready at `strong/collect-resource-turn-runtime-v2.py`, with 21 offline
   tests. Use it only after the two corrected pilots actually exist. The original
   v1 collector is only for the six original jobs and must not be pointed at the
   corrected pilots.

The two proposed jobs validate corrected runtime behavior; they cannot select
the strongest policy. Fresh full-game v4 runtime and strength validation remain
pending. The main auction study must reach its complete comparison independently.

## Verification and recovery

`strong/test_resource_runtime_launcher_v2.py` passed **26 tests** with zero
network calls, HF submissions, inference or new game trajectories. Tests cover
exact source/admission and job-set binding; budget accounting; live, duplicate,
invented or unpreserved original outcomes; fresh remote-stage disagreement;
one-attempt behavior; local-control exclusion; exact public environment; shell
syntax; and actual decoding/hash rejection of the separate admission bytes.

The actual `prepare` operation was checked against the existing real v4 package:
it rejected the absent terminal evidence/admission and created no execution
source or launch directory. Test sources and the successful receipt are retained
under `ai/runs/resource-turn-runtime-launcher-tests-v2`, with the log next to it.
No existing source, original guard or frozen policy was modified.

At the bounded HF collection at **17:28 UTC**, the original resource set remained
three verified successes / 40 games, one preserved failed pilot, and two running
six-player originals. At **17:33 UTC**, the auction coordinator PID 1075760 was
confirmed alive; its latest state recorded 574 audited / 638 submitted of 648
selected batches. Do not launch a competing coordinator or use partial wins to
choose a policy. These are timestamped observations, not promises of later status.

The immutable evidence archive is indexed by
`strong/resource-runtime-launcher-evidence-v2.json`. It includes the launcher,
tests, copied test sources/result/log, relevant source descriptors, current
original-outcome snapshot, auction-owner snapshot and this handoff. The complete
prepared package is already independently archived at private model revision
`0c5597ce154a87da3a46a4e01ef209c7be43e237`, path
`archives/resource-runtime-preflight-evidence-v2.tgz`, SHA-256
`ae60f8e37c35f07d884bde1d5670489a4e458eeb01f27c5d12a6941dd31b2d55`.
Do not repack or rerun the package to recover it.
