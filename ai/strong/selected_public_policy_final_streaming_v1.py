"""Audit one original compressed archive without retaining successful extractions.

The immutable archive remains untouched. Publish the full audit receipt durably
before deleting only this call's temporary copy. Failures retain scratch evidence
and never trigger a retry. This helper has no network or job execution interface.
"""
from datetime import datetime, timezone
from pathlib import Path
import shutil
import tarfile
import tempfile

from population_policy_verification import extract_verified
from public_policy_final_audit_v1 import digest, require
from public_policy_final_contract_v1 import object_hash
from public_policy_runtime_v1 import sha256
from selected_public_policy_final_collection_v1 import verify_artifacts
from selected_public_policy_final_dispatch_v1 import durable_write


def audit_archive(archive, source_root, release, launch, evidence, bootstrap, *,
                  hf_stage, scratch_root, receipt, purpose,
                  minimum_free_bytes=16 * 1024**3):
    require(purpose in ('initial_collection', 'independent_final_audit'), 'Unknown audit purpose')
    require(hf_stage == 'COMPLETED', 'Inspect original non-completed job; do not retry')
    require(type(minimum_free_bytes) is int and minimum_free_bytes >= 0, 'Invalid storage reserve')
    archive, source_root = Path(archive).resolve(), Path(source_root).resolve()
    scratch_root, receipt = Path(scratch_root).absolute(), Path(receipt).absolute()
    require(not receipt.exists() and not receipt.is_symlink(), 'Inspect existing audit receipt; never overwrite')
    require(not scratch_root.is_symlink() and not receipt.parent.is_symlink(), 'Symlink in audit output')
    require(not scratch_root.resolve().is_relative_to(source_root)
            and not receipt.resolve().is_relative_to(source_root), 'Cannot write inside frozen source')
    require(not receipt.resolve().is_relative_to(scratch_root.resolve()), 'Audit receipt must outlive scratch cleanup')
    expected_sha = sha256(evidence['archive_sha256'])
    scratch_root.mkdir(parents=True, exist_ok=True)
    receipt.parent.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix='original-final-audit-', dir=scratch_root))
    published = False
    intent = {'stage':'auditing_original_archive', 'started_at':datetime.now(timezone.utc).isoformat(),
              'purpose':purpose, 'original_archive':str(archive), 'archive_sha256':expected_sha,
              'launch_sha256':object_hash(launch), 'release_sha256':object_hash(release),
              'receipt':str(receipt), 'automatic_retries':False}
    try:
        durable_write(work/'intent.json', intent, exclusive=True)
        require(digest(archive) == expected_sha, 'Original archive hash changed')
        with tarfile.open(archive, 'r:gz') as bundle:
            members = bundle.getmembers()
            require(all(m.isfile() and m.size >= 0 for m in members), 'Invalid archive member')
            required_bytes = sum(m.size for m in members)
        require(shutil.disk_usage(work).free >= required_bytes + minimum_free_bytes,
                'Insufficient free space for original archive audit')
        extracted = work/'evidence'
        extraction = extract_verified(archive, extracted)
        require(extraction['archive_sha256'] == expected_sha
                and extraction['manifest_sha256'] == evidence['manifest_sha256']
                and extraction['files'] == evidence['archived_files'], 'Original extraction binding changed')
        review = verify_artifacts(extracted, source_root, release, launch, evidence,
                                  archive, bootstrap, hf_stage=hf_stage)
        require(digest(archive) == expected_sha, 'Original archive changed during audit')
        saved = {'version':1, 'purpose':purpose, 'created_at':datetime.now(timezone.utc).isoformat(),
                 'original_archive_sha256':expected_sha, 'evidence':evidence,
                 'release_sha256':object_hash(release), 'launch_sha256':object_hash(launch),
                 'review':review, 'review_sha256':object_hash(review),
                 'streaming_auditor_sha256':digest(__file__), 'qualified':False}
        # Even a disk/cleanup failure cannot lose the original archive. A saved
        # receipt is never overwritten or silently used to skip a fresh audit.
        durable_write(receipt, saved, exclusive=True)
        published = True
        shutil.rmtree(work)
        return {'receipt':str(receipt), 'receipt_sha256':digest(receipt),
                'review_sha256':saved['review_sha256'], 'temporary_extraction_removed':True,
                'archive_retained':True, 'qualified':False}
    except BaseException as error:
        if work.exists():
            failure = {**intent, 'stage':'stopped_for_inspection', 'failure_type':type(error).__name__,
                       'audit_receipt_published':published,
                       'next_action':'Inspect original archive, saved receipt and retained scratch. No automatic retry.'}
            try:
                durable_write(work/'failure.json', failure, exclusive=True)
            except OSError:
                pass  # Preserve the original failure and all surviving files.
        raise
