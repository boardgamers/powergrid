"""Check temporary audit storage on an existing ordinary confirmation archive.

This is a storage-only engineering preflight, not final collection. The adapter
uses the unchanged confirmation raw verifier because there are no final games.
It does not simulate, infer, submit jobs, collect for the live owner or select a
candidate. It writes only its own new preflight directory and report.
"""
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import tarfile
import time
from unittest.mock import patch

from huggingface_hub import HfApi, try_to_load_from_cache
from public_policy_final_audit_v1 import digest, read
from public_policy_final_contract_v1 import object_hash
from selected_public_policy_final_dispatch_v1 import durable_write
import selected_public_policy_final_streaming_v1 as streaming

ROOT = Path(__file__).resolve().parents[2]
STRONG = ROOT / 'ai/strong'
RUNS = ROOT / 'ai/runs'
OUT = RUNS / 'selected-public-policy-final-streaming-preflight-v1'
REPORT = STRONG / 'selected-public-policy-final-streaming-preflight-v1.json'
ORIGINAL = RUNS / 'current-auction-grid-hf-v1/pg-current-confirm-v1-pop-search_geo-3p-00'
SOURCE = STRONG / 'current-auction-grid-source-v1.json'
SOURCE_ROOT = RUNS / 'current-auction-grid-prepared-v1/source'


def main():
    assert not OUT.exists() and not REPORT.exists(), 'Inspect original preflight outcome; do not rerun'
    original = read(ORIGINAL / 'verified.json')
    launch = read(ORIGINAL / 'launch.json')
    source = read(SOURCE)
    assert original['verified'] and original['stage'] == 'COMPLETED'
    assert original['source_sha256'] == digest(SOURCE)
    assert original['guard_sha256'] == digest(ORIGINAL / 'launch.json')
    assert original['job_id'] == launch['job_id'] and launch['row'] == original['row']
    assert launch['source_fingerprint'] == object_hash(source)
    evidence = original['evidence']
    cached = try_to_load_from_cache(evidence['repo'], evidence['archive_path'], revision=evidence['revision'])
    assert isinstance(cached, str), 'Inspect missing cached original; do not regenerate it'
    archive = Path(cached).resolve()
    assert digest(archive) == evidence['archive_sha256']
    assert HfApi().inspect_job(job_id=launch['job_id']).status.stage == 'COMPLETED'
    unit_log = RUNS / 'selected-public-policy-final-streaming-tests-v1-first.log'
    assert 'Ran 8 tests' in unit_log.read_text() and unit_log.read_text().rstrip().endswith('OK')
    inputs = [Path(__file__).resolve(), SOURCE, SOURCE_ROOT / 'source-manifest.json', unit_log,
              ORIGINAL / 'verified.json', ORIGINAL / 'launch.json', ORIGINAL / 'artifacts/manifest.json']
    inputs += [STRONG / name for name in (
        'selected_public_policy_final_streaming_v1.py', 'test_selected_public_policy_final_streaming_v1.py',
        'selected_public_policy_final_collection_v1.py', 'selected_public_policy_final_dispatch_v1.py',
        'manage-current-auction-grid-v1.py', 'public_policy_final_audit_v1.py',
        'public_policy_final_contract_v1.py', 'population_policy_verification.py',
        'selected-public-policy-final-storage-review-v1.json')]
    pins = {str(p.relative_to(ROOT)): digest(p) for p in inputs}
    owner = read(RUNS / 'current-auction-network-resume-v1/state.json')
    assert all(digest(ROOT / n) == sha for n, sha in owner['code_hashes'].items())
    spec = importlib.util.spec_from_file_location('original_grid_storage_preflight', STRONG / 'manage-current-auction-grid-v1.py')
    manager = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(manager)
    OUT.mkdir()
    scope = {'scope': 'Storage-only re-audit of an already verified ordinary confirmation archive. The final verifier is replaced only in this isolated preflight by the unchanged confirmation verifier. This is not final evidence or a final launch admission.',
             'job_id': launch['job_id'], 'evidence': evidence, 'input_hashes': pins,
             'new_games': 0, 'policy_inference_calls': 0, 'hf_jobs_submitted': 0,
             'candidate_selected': False, 'qualified': False, 'reserved_final_seeds_used': False}
    durable_write(OUT / 'ENGINEERING-SCOPE.json', scope, exclusive=True)
    durable_write(OUT / 'intent.json', {'stage': 'single_original_archive_storage_probe',
                  'started_at': datetime.now(timezone.utc).isoformat(), 'automatic_retries': False}, exclusive=True)
    bridge = {'scope': 'engineering-storage-preflight-only', 'source_sha256': digest(SOURCE)}
    bootstrap = 'NO_EXECUTION_STORAGE_PREFLIGHT'
    adapter_calls = []

    def original_verifier(folder, source_root, release, passed_launch, passed_evidence, passed_archive, passed_bootstrap, *, hf_stage):
        assert source_root == SOURCE_ROOT.resolve() and release == bridge
        assert passed_launch == launch and passed_evidence == evidence and passed_archive == archive
        assert passed_bootstrap == bootstrap and hf_stage == 'COMPLETED'
        review = manager.verify_artifacts(folder, source, original['row'], evidence)
        assert review == original['review'], 'Fresh raw audit differs from original independent review'
        adapter_calls.append(True)
        return review

    with tarfile.open(archive, 'r:gz') as bundle:
        expanded_bytes = sum(m.size for m in bundle.getmembers())
    started = time.perf_counter()
    with patch.object(streaming, 'verify_artifacts', side_effect=original_verifier):
        result = streaming.audit_archive(archive, SOURCE_ROOT, bridge, launch, evidence, bootstrap,
                    hf_stage='COMPLETED', scratch_root=OUT / 'scratch', receipt=OUT / 'receipts/engineering-audit.json',
                    purpose='independent_final_audit')
    elapsed = time.perf_counter() - started
    assert adapter_calls == [True] and result['temporary_extraction_removed'] and result['archive_retained']
    assert not list((OUT / 'scratch').iterdir())
    assert digest(archive) == evidence['archive_sha256']
    original_pins = read(ORIGINAL / 'artifacts/manifest.json')
    assert all(digest(ORIGINAL / 'artifacts' / n) == sha for n, sha in original_pins.items())
    assert all(digest(ROOT / n) == sha for n, sha in pins.items())
    assert all(digest(ROOT / n) == sha for n, sha in owner['code_hashes'].items())
    report = {**scope, 'passed': True, 'completed_at': datetime.now(timezone.utc).isoformat(),
              'unit_tests': 8, 'original_games_reaudited': original['review']['games'],
              'raw_audit_equal_to_original': True, 'original_archive_and_extraction_unchanged': True,
              'temporary_extraction_removed': True, 'archive_bytes': archive.stat().st_size,
              'temporary_expanded_bytes': expanded_bytes, 'audit_seconds': elapsed,
              'unchanged_owner_pins': len(owner['code_hashes']), 'receipt': result,
              'actual_final_games': 0, 'final_verifier_replaced_only_in_engineering_preflight': True}
    durable_write(REPORT, report, exclusive=True)
    print(json.dumps({k: report[k] for k in ('passed', 'unit_tests', 'original_games_reaudited',
          'raw_audit_equal_to_original', 'archive_bytes', 'temporary_expanded_bytes', 'audit_seconds',
          'unchanged_owner_pins', 'actual_final_games')}), flush=True)


if __name__ == '__main__':
    main()
