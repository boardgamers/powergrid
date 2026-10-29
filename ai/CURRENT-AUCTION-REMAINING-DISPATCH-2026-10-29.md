# Remaining fixed confirmation executions

**29 October 2026: the remaining worker is admitted and published; the first
64 original, never-submitted rows have now been submitted once.** These are
1,280 five-player games in the recorded fixed order, with no policy, opponent,
seed, search-budget or rule changes. The initial 10:06 UTC snapshot verified all
64 actual HF configurations and reported SCHEDULING. A subsequent bounded
observation at **10:08:59 UTC confirmed all 64 RUNNING**, with zero new jobs or
completed raw reviews. Use the current handles for
later observations; scheduling and observation timeouts never justify replacement.

The broad goal is active. The previous Rust explanation was informational and
made no research progress. This turn made progress through completed independent
collection controls, actual preparation, source publication and real dispatch.
No candidate is selected/qualified; reserved final seeds remain unused.

## Coverage and prerequisites

The complete confirmation requires **944 canonical shards / 26,880 games**.
Previously audited usable coverage remains **621 shards / 19,780 games**:
620 original shards plus the exact 16-game recovery. The original timeout
`6ae2c32f3fb22a235dd50586` remains failed. Its separate successful recovery
`6ae3083f3fb22a235dd56000` passed the unchanged full raw audit and all 14 checkpoint
archives; it must not be rerun or recollected.

The frozen remaining set contains **323 shards / 7,100 games**: 16/256 at two
players, 16/384 at three, 131/2,620 at five, and 160/3,840 at six. Following the
initial 64 submissions, **259 shards / 5,820 games remain unsubmitted**. Pending
or completed-but-unaudited games do not add to verified coverage. No incomplete
or survivor-only strength comparison is admitted.

The prior worker preflight checked all 323 actual source/spec/policy/contract
bindings and original validation-only commands at all four remaining counts.
The real first-recovery audit SHA is
`b83b2dfa755d3bc0ea6500461a6ca8166724c6ce2b6071dab282798378a91940`.
This exact result is bundled and required before remaining game execution.

## Implementation and validation

- `strong/current_auction_remaining_collection_v2.py`: exact attempt/row/command
  identity; immutable final and checkpoint references; every retained game and
  decision file must match the final raw bytes; at least one successful upload
  must occur while the original child stays live. Then the unchanged complete
  original raw auditor runs. Twelve focused tests passed, including the actual
  16/20/24-game row sizes and missing/changed/duplicated evidence failures.
- `strong/manage_current_auction_remaining_v2.py`: fixed-order bounded dispatch,
  fsynced atomic launch intents and handles, exclusive operation locks, exact
  remote image/source/command/environment/resource verification, independent
  collection, failure preservation and no automatic retries. Eighteen tests
  passed. The first test run had one missing synthetic source-file fixture; its
  failed log is retained, the fixture was corrected, and all 18 passed on the
  second run. All HF operations in unit tests were mocked.
- The previously completed ten worker tests and actual-source preflight remain
  valid. No completed preflight, first recovery, game or inference was repeated
  to obtain preparation evidence. Four real admitted configurations were checked
  locally without executing their original evaluator.

The only external allowance change remains **24h / cpu-upgrade**, with four game
workers, four search workers, one inference thread, 30-second checkpoint scans
and at most 64 active jobs. The original dependency/source bootstrap prefix is
unchanged. The reviewed remaining bootstrap SHA is
`ca1805ff3b62faba2ab02d94c7830988eaa2b79947ded5ed792e80546ee4d008`.
Existing original/first-worker files and all 471 owner pins / 621 launch guards
are preserved. The old original coordinator remains stopped; no new background
coordinator was created by this dispatch.

## Durable source and recovery evidence

The **39-file preparation evidence** was uploaded, downloaded and verified in
private model repo `coyotte508/powergrid-ai-germany-v1`, revision
`a4d8d65e7cf7d708720081fc16893bdd91084b55`, path
`archives/current-auction-remaining-preparation-evidence-v2.tgz`, SHA
`a1e30b7ce7412045732e7c4feb65016050fa9244995aee7c59422a2ebe465d86`.
Descriptor: `strong/current-auction-remaining-preparation-evidence-v2.json`.

The separate execution source is in private dataset
`coyotte508/powergrid-ai-training-v1`, revision
`80f50a076657bf840ee0997c908c90a3ec036a22`, file
`strong-source-current-auction-remaining-retained-v2.tgz`, SHA
`ef98506245e988d874bb8d5bfd6a6f5d40e42c7f6df07b3a7f8a84cd0a346ab7`,
manifest SHA `ff6a644c3f57caaa32b6a79b521f2fd27d78f9a7c9a770000929fa0a89ad0200`.
Its descriptor is `strong/current-auction-remaining-source-v2.json`.
It references the original immutable evaluator bundle; it does not replace it.

The launch recovery archive descriptor is
`strong/current-auction-remaining-launch-evidence-v2.json`. It preserves actual
preparation/admission metadata, source upload receipts, dispatch guard/intent
files, sanitized HF observations and the initial submitted-handle register.
Inspect existing archive intents/outcomes before any archive retry.

## Continue the existing execution

Local preparation: `ai/runs/current-auction-remaining-prepared-v2`.
Execution: `ai/runs/current-auction-remaining-hf-v2`, with per-attempt `jobs/`,
sanitized `checks/`, independent `review.json` files and cycle snapshots.
The tracked initial register is `strong/current-auction-remaining-dispatch-v2.json`.
Never rerun prepare/upload or dispatch an existing intent under a new name.

From this worktree, a bounded collection/observation cycle with **no new jobs**:

```bash
PYTHONPATH=ai/strong ai/.venv/bin/python -u -B ai/strong/manage_current_auction_remaining_v2.py cycle --execute --launch-limit 0 --collect-limit 4
```

Once current observations and collection are healthy, use `--launch-limit 64`
to fill only available slots with the next frozen rows. The global cycle lock
prevents competing dispatch. An unresolved submission response has a durable
intent and must be resolved against HF; it cannot be automatically resubmitted.
An audit/terminal failure writes `STOP.json`, retains logs/evidence, and requires
inspection. A transient observation failure is not a terminal job failure.

Current local free storage was 353 GiB before collection. The completed first
16-game recovery used 270 MiB for final evidence and 268 MiB for checkpoint trees;
do not assume later player counts have the same size. Keep collection bounded,
measure disk use, and preserve immutable remote archives before considering
removal of reconstructible local caches. No existing evidence was deleted.

After all remaining rows verify, authenticate explicit attempt receipts and use
the existing coverage component to reconcile all 944 canonical shards / 26,880
unique games. Full raw re-auditing and the unchanged paired analysis/selection
gates remain necessary. Do not make the stopped original owner's state appear
complete. Exact selected-policy binding, untouched reserved strength evaluation
and the final qualification gate remain outstanding. Existing AMD8840U/export
evidence applies only if the exact complete policy is selected.
