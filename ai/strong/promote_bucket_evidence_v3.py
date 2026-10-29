"""Serialized final promotion of verified bucket trees into versioned evidence.

The unchanged uploader is called once. An ambiguous Git commit leaves its
intent/archive for explicit reconciliation; never silently upload a second time.
This does not audit a game, change an HF job stage, or qualify a policy.
"""
from pathlib import Path

from checkpoint_bucket_transport_v3 import digest, read, require, save
from checkpoint_bucket_archives_v3 import checked_receipt, verify_archive
from current_auction_resource_job_v2 import tree
from policy_iteration_evidence_archive import upload_evidence

REPO = 'coyotte508/powergrid-ai-germany-v1'


def promote(folder, bucket_evidence, ledger, api):
    folder, ledger = Path(folder), Path(ledger)
    checked_receipt(bucket_evidence, folder.name)
    tree(folder, 'manifest.json', bucket_evidence['manifest_sha256'])
    require(api.model_info(REPO).private is True, 'Evidence repository must remain private')
    ledger.mkdir(parents=True, exist_ok=True)
    require(not (ledger/'intent.json').exists() and not (ledger/'receipt.json').exists(),
        'Inspect previous promotion intent/outcome; no automatic retry')
    require(not api.file_exists(REPO, 'archives/'+folder.name+'.tgz'), 'Inspect existing versioned archive')
    save(ledger/'intent.json', {'bucket_evidence': bucket_evidence,
        'manifest_sha256': digest(folder/'manifest.json'), 'automatic_retries': False})
    evidence = upload_evidence(folder, repo=REPO)
    require(evidence['manifest_sha256'] == bucket_evidence['manifest_sha256']
        and evidence['remote_archive_verified'] is True, 'Promoted bytes differ')
    # Gzip container bytes may differ from the bucket archive; member manifests
    # must match exactly. Both archive identities remain in the promotion receipt.
    verify_archive(folder.with_suffix('.tgz'), evidence['manifest_sha256'])
    result = {'bucket_evidence': bucket_evidence, 'versioned_evidence': evidence,
        'manifest_bytes_equal': True, 'qualified': False, 'job_stage_unchanged': True}
    save(ledger/'receipt.json', result)
    return result
