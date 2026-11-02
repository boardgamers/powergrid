# Power Grid local run cleanup and recovery

The user requested cleanup of the historical `ai/runs` storage on 2 November
2026. The initial directory occupied 794,110,398,464 bytes, about 740 GiB.
Source code, the existing handoff, model weights, small recovery records and
all remote artifacts were preserved. No research job or collector was using
the checkout during the cleanup; no training, games or deployment ran.

Final sizes and integrity hashes are in [summary.json](summary.json).

## What was removed

The first two passes removed large expanded data files and archive copies
identified by existing download-verified receipts. A fresh HF metadata check
matched archive SHA-256 values for versioned repositories and Xet hashes plus
sizes for bucket objects. For versioned objects, the fresh check used the pinned
current repository revision and required the exact original archive hash;
original immutable revisions are retained in the records.

A third pass read the remaining large files and removed only those whose actual
SHA-256 matched a member of an already checked archive. Every unlink was limited
to a planned regular file under `ai/runs`, with unchanged inode, size and mtime.
Models with `.pt`, `.pth`, `.onnx` or `.safetensors` extensions were excluded.
Files under 1 MiB were kept, along with original receipts and STOP markers.

The final 1,350 large files not covered by those checks were compressed into
`retained-large-files.tar.zst` in this directory. The tar archive was compared
against every original file before removing the expanded copies. This bundle
is a **local backup**, not a claim that these additional files were uploaded
to HF. Preserve it when moving or deleting the research checkout.

## Restore a historical file

Metadata may still exist at an old run path while its bulk files have been
pruned. Do not infer a failed or incomplete experiment from the missing local
cache, and do not relaunch completed jobs to recreate files.

The tracked [recovery-records.tar.zst](recovery-records.tar.zst) contains the
plans, per-file deletion records, source archive descriptors, fresh remote checks
and the list of locally compressed files. Extract this small index into a
separate temporary directory to inspect it. It contains no model weights or
bulk game data.

For a file in `deleted.jsonl`, `second/deleted.jsonl` or
`duplicates/deleted.jsonl`, use its archive key in the corresponding `plan.json`.
Download the archive from the recorded HF repository/revision/path, or the
recorded HF bucket object, and verify its SHA-256. The `archive_member` field
identifies the source member; restore it to the recorded local `path` relative
to `ai/runs`. A null member means the local file was itself the compressed
archive. The original descriptor remains the authoritative recovery reference.

For a file listed in `retained-large-files.json`, use the local bundle instead.
From the repository root, after checking its SHA-256 against `summary.json`:

```sh
tar --extract --use-compress-program=zstd \
  --file=ai/run-cleanup-2026-11-02/retained-large-files.tar.zst \
  --directory=ai/runs --keep-old-files --no-same-owner \
  'the/relative/path/from/retained-large-files.json'
```

Restore only what the next experiment needs. Restoring the entire bundle expands
roughly 17.6 GB again. Remote-backed files and the local bundle may include
historical evaluation data; their original train/validation/final restrictions
still apply.

## Scripts and retained state

[cleanup.py](cleanup.py) records the first two passes; [duplicates.py](duplicates.py)
records the exact-byte duplicate pass. Their saved outcomes already exist;
do not blindly repeat an `apply` operation. The large local bundle and expanded
cleanup ledgers are excluded from Git; the compact recovery index and final
summary are tracked with the handoff.

Existing dirty policy-iteration status/results files and unrelated untracked
conservative-auction reports were not edited or staged. HF visibility was not
changed. On 2 November the model repository reported public visibility, which
differs from the handoff's explicitly dated 31 October private-access check.
