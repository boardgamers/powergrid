"""Archive the completed storage tests and original-archive engineering probe.

No test reruns, game execution, inference, job submission or original collection.
The original compressed job evidence is referenced at its immutable HF revision.
"""
import json
from pathlib import Path
import shutil

from huggingface_hub import HfApi
from policy_iteration_evidence_archive import upload_evidence
from public_policy_final_audit_v1 import digest, read
from selected_public_policy_final_dispatch_v1 import durable_write

ROOT = Path(__file__).resolve().parents[2]
STRONG = ROOT / 'ai/strong'
RUNS = ROOT / 'ai/runs'
NAME = 'selected-public-policy-final-streaming-evidence-v1'
OUT = RUNS / NAME
DESCRIPTOR = STRONG / (NAME + '.json')


def main():
    assert all(not p.exists() for p in (OUT, OUT.with_suffix('.tgz'), OUT.with_suffix('.intent.json'), DESCRIPTOR)), 'Inspect existing archive intent/outcome before any retry'
    report_path = STRONG / 'selected-public-policy-final-streaming-preflight-v1.json'
    report = read(report_path)
    assert report['passed'] and report['unit_tests'] == 8 and report['original_games_reaudited'] == 24
    assert report['raw_audit_equal_to_original'] and report['original_archive_and_extraction_unchanged']
    assert report['temporary_extraction_removed'] and report['final_verifier_replaced_only_in_engineering_preflight']
    assert all(report[k] == 0 for k in ('new_games', 'policy_inference_calls', 'hf_jobs_submitted', 'actual_final_games'))
    assert not report['qualified'] and not report['reserved_final_seeds_used']
    assert all(digest(ROOT / n) == sha for n, sha in report['input_hashes'].items())
    receipt = Path(report['receipt']['receipt'])
    assert digest(receipt) == report['receipt']['receipt_sha256']
    sources = {ROOT / n for n in report['input_hashes']}
    sources.update({Path(__file__).resolve(), report_path, receipt,
        STRONG / 'policy_iteration_evidence_archive.py',
        STRONG / 'selected-public-policy-final-collection-evidence-v1.json',
        STRONG / 'current-auction-recovery-storage-review-v1.json',
        RUNS / 'selected-public-policy-final-streaming-preflight-v1/ENGINEERING-SCOPE.json',
        RUNS / 'selected-public-policy-final-streaming-preflight-v1/intent.json',
        RUNS / 'selected-public-policy-final-streaming-preflight-v1-first.log'})
    api = HfApi(); repo = 'coyotte508/powergrid-ai-germany-v1'
    assert api.model_info(repo).private and not api.file_exists(repo, 'archives/' + NAME + '.tgz')
    OUT.mkdir(); manifest = {}
    for path in sorted(sources):
        assert path.is_file() and not path.is_symlink()
        name = str(path.relative_to(ROOT)); target = OUT / name
        target.parent.mkdir(parents=True, exist_ok=True)
        with path.open('rb') as src, target.open('xb') as dst:
            shutil.copyfileobj(src, dst)
        assert digest(target) == digest(path); manifest[name] = digest(path)
    durable_write(OUT / 'STORAGE-ENGINEERING-SCOPE.json', {
        'scope': 'Storage planning and verification lifecycle only. The raw re-audit used an existing ordinary confirmation archive via a preflight-only adapter. No final games or strength qualification.',
        'original_job_archive': report['evidence'],
        'source_bundle': {k: read(STRONG / 'current-auction-grid-source-v1.json')[k]
                          for k in ('repo', 'revision', 'archive', 'sha256', 'source_manifest_sha256')},
        'final_collection_verifier_archive': read(STRONG / 'selected-public-policy-final-collection-evidence-v1.json')['archive'],
        'actual_final_games': 0, 'candidate_selected': False, 'qualified': False,
        'reserved_final_seeds_used': False}, exclusive=True)
    manifest['STORAGE-ENGINEERING-SCOPE.json'] = digest(OUT / 'STORAGE-ENGINEERING-SCOPE.json')
    durable_write(OUT / 'manifest.json', manifest, exclusive=True)
    durable_write(OUT.with_suffix('.intent.json'), {'stage': 'upload_intent', 'report_sha256': digest(report_path)}, exclusive=True)
    archive = upload_evidence(OUT)
    durable_write(DESCRIPTOR, {'complete': True, 'report_sha256': digest(report_path), 'archive': archive,
        'tests': 8, 'existing_games_reaudited': 24, 'new_games': 0, 'actual_final_games': 0,
        'candidate_selected': False, 'qualified': False, 'reserved_final_seeds_used': False}, exclusive=True)
    durable_write(OUT.with_suffix('.intent.json'), {'stage': 'uploaded_download_verified',
        'archive': archive, 'descriptor_sha256': digest(DESCRIPTOR)})
    print(json.dumps({'complete': True, 'tests': 8, 'archive': archive}), flush=True)


if __name__ == '__main__':
    main()
