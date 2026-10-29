# Raw-game retention for resource recovery

The external retention component is implemented and tested. It preserves
completed game/decision pairs while an unchanged evaluator runs. **Actual
recovery-job source preparation and dispatch are not admitted yet.**

## What is implemented

`strong/current_auction_recovery_checkpoints_v2.py` wraps a caller-admitted child
process in its own process session and checks for completed records every 30
seconds by default. It has no job submission API or command-line launch entry.
The production caller must still verify the exact frozen source, command,
attempt identity and effective resources before using it.

Each game must be within the original shard and have its original policy,
seed, seat and rule pairing. The game record's decision-log hash must match the
copied bytes and line count. Streaming copies detect concurrent changes;
unfinished writes are deferred. Previously retained files must remain unchanged,
with a full hash recheck when the child exits. This is evidence retention, not
the independent audit of move legality, search receipts or complete coverage.

Snapshots contain only newly completed pairs and their immutable context/hash
manifest. The uploader must return a verified receipt at a unique attempt and
checkpoint path. A durable upload intent precedes the operation. Failed or
ambiguous uploads preserve evidence and stop the child without retrying or
restarting it. Existing output directories cannot be silently reused. A capped
terminal is also retained; the component does not discard adverse evidence.

Every checkpoint explicitly says `raw_audited: false`, `execution_complete:
false`, and `qualified: false`. A child exit, including a successful exit, is
not a qualification or independent-completeness claim. The final raw archive
and existing full audit remain mandatory.

## Completed tests and actual saved-data proof

**13 focused tests passed.** They cover partial game writes, unfinished decision
logs, concurrent replacement, changed policies/episodes, symlinks, mutation after
retention, capped terminals, ambiguous and unverified uploads, immutable context,
and duplicate prevention. Two tests use real short-lived synthetic child
processes: one is hard-killed after a checkpoint; the other is stopped after an
unknown upload response. Neither generates a game or runs policy inference.
Transport is mocked in those unit tests.

The separate real-transport preflight used episode 100 from the already-audited
four-player/search shard `pg-current-confirm-v1-pop-search_geo-4p-06`, original
HF handle `6ae2c3f741e90535df782f3b`. It copied the existing 2,668-byte game record
and **18,735,012-byte decision log**. Both match the original raw archive's
manifest exactly. Nothing was replayed or regenerated.

The real private-HF upload/download hash verification completed in **5.28
seconds** for this pair. This is one engineering sample, not a production
throughput or overhead guarantee. A repeated full-recheck scan uploaded nothing.
Original files remained unchanged.

The checkpoint archive is immutable model revision
`22dc795707f34405d51d2e1a2e9906a5ffcd05ff`, path
`archives/pg-retention-v2-preflight-existing-4p-checkpoint-0001.tgz`, SHA-256
`722d96082f58c3cf78675b23d1fd777bb94db80cae5e20402ca1818acf417c2d`.
The detailed receipt is `strong/current-auction-recovery-retention-preflight-v2.json`.

## Next work

Follow the unchanged [resource recovery decision](CURRENT-AUCTION-RESOURCE-RECOVERY-2026-10-29.md).
Build the production supervisor entry around the byte-identical original measured
worker, with the 24-hour external allowance and fixed worker settings. Bind the
new supervisor/control package, original source and decision to an immutable
attempt manifest. The first prepared package must authorize only the exact failed
16-game shard. Require real control verification before any HF submission.

Suppress the original worker's direct final upload and archive its unchanged raw
output inside a unique recovery envelope, preserving its original manifest and
case identity. Add independent envelope/attempt/raw-audit collection and explicit
canonical-coverage reconciliation. The old collectors/comparator must not accept
new attempts implicitly. Only a successfully audited first recovery, including
retention evidence, may admit the fixed 323 remaining rows.

The final original collection remains **620 audited shards / 19,764 games**, one
failed original and no active jobs. There were no new HF jobs, games, inference
calls, policy changes, selected candidate or reserved final seeds in this work.
Research remains active and strength qualification remains unproven.

Engineering evidence archive descriptor:
`strong/current-auction-recovery-retention-evidence-v2.json`. It preserves the
component, tests, original test log, real preflight metadata and source/decision
bindings. It references the actual checkpoint archive without duplicating its
raw game bytes. Do not repeat the successful preflight or upload.
