"""Archive the original completed target replay and checkpoint-proposal binding.

Requires successful original collection and independent audits. No simulation,
inference, job creation, collection or rerun is performed by this helper.
"""
import json
from pathlib import Path

from huggingface_hub import HfApi
from policy_iteration_evidence_archive import upload_evidence
from public_policy_final_audit_v1 import digest, read

ROOT = Path(__file__).resolve().parents[2]
STRONG = ROOT/'ai/strong'
COLLECTED = ROOT/'ai/runs/current-full-serving-8840u-collected-v1'
NAME = 'current-full-serving-results-evidence-v1'
OUT = ROOT/'ai/runs'/NAME
RESULT = STRONG/(NAME+'.json')


def save(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False); stream.write('\n')


def main():
    assert all(not p.exists() for p in (OUT, OUT.with_suffix('.tgz'), OUT.with_suffix('.intent.json'), RESULT)), 'Inspect existing archive intent/outcome before retry'
    result_path = STRONG/'current-full-serving-8840u-results-v1.json'; result = read(result_path)
    binding_path = STRONG/'current-full-serving-export-binding-v1.json'; binding = read(binding_path)
    status_path = COLLECTED/'output/status.json'; status = read(status_path)
    assert result['complete'] and result['requests'] == binding['requests'] == status['completed_requests'] == 5106
    assert result['positions_per_policy'] == 2553 and result['all_moves_legal']
    assert binding['complete'] and binding['all_target_model_proposals_match_native_checkpoint']
    assert binding['technical_report_sha256'] == digest(result_path)
    assert binding['target_receipts_sha256'] == digest(COLLECTED/'output/receipts.jsonl')
    assert binding['auditor_sha256'] == digest(STRONG/'audit_current_engine_export_v1.py')
    assert result['status_sha256'] == digest(status_path) and result == read(COLLECTED/'audit.json')
    assert status['stage'] == 'completed' and status['passed'] and '8840U' in status['processor']
    assert all(digest(COLLECTED/'output'/n) == sha for n, sha in status['output_hashes'].items())
    for arm in ('filter', 'conservative_population'):
        assert result['counts'][arm].get('rollout_caps', 0) == 0
    ready = read(STRONG/'current-full-serving-readiness-v1.json')
    assert all(digest(ROOT/n) == sha for n, sha in ready['input_hashes'].items())
    export_path = STRONG/'current-engine-export-parity-v1.json'
    export_audit = STRONG/'current-engine-export-audit-v1.json'
    assert binding['export_report_sha256'] == digest(export_path)
    assert binding['export_audit_sha256'] == digest(export_audit)
    assert not result['candidate_selected'] and not result['qualified'] and not result['reserved_final_seeds_used']
    sources = {Path(__file__).resolve(), result_path, binding_path, export_path, export_audit,
        STRONG/'current-full-serving-readiness-v1.json', STRONG/'current-full-serving-8840u-launch-v1.json',
        STRONG/'current-full-serving-launch-evidence-v1.json', STRONG/'current-engine-export-evidence-v1.json',
        STRONG/'current_auction_full_serving_v1.py', STRONG/'benchmark-current-full-serving-8840u-v1.py',
        STRONG/'audit_current_engine_export_v1.py', STRONG/'current_engine_export_parity_v1.py',
        STRONG/'policy_iteration_evidence_archive.py', STRONG/'strategic_collection.py',
        ROOT/'ai/runs/current-full-serving-8840u-collect-v1-first.log',
        ROOT/'ai/runs/current-full-serving-export-binding-v1-first.log'}
    sources.update(p for p in COLLECTED.rglob('*') if p.is_file())
    for p in sources:
        assert p.is_file() and not p.is_symlink()
    api = HfApi(); repo = 'coyotte508/powergrid-ai-germany-v1'
    assert api.model_info(repo).private and not api.file_exists(repo, 'archives/'+NAME+'.tgz')
    OUT.mkdir(); manifest = {}
    for p in sorted(sources):
        name = str(p.relative_to(ROOT)); before = digest(p); target = OUT/name
        target.parent.mkdir(parents=True, exist_ok=True)
        with p.open('rb') as source, target.open('xb') as dest:
            import shutil
            shutil.copyfileobj(source, dest)
        assert digest(target) == before == digest(p); manifest[name] = before
    save(OUT/'recovery.json', {
        'original_package_and_public_cases': read(STRONG/'current-full-serving-launch-evidence-v1.json')['archive'],
        'native_checkpoint_and_raw_parity_proof': read(STRONG/'current-engine-export-evidence-v1.json')['archive'],
        'original_target_pid': 3462824,
        'instruction': 'Restore the referenced exact standalone package and current-engine native/ONNX proof by immutable revisions and hashes. This archive preserves all 5106 original target responses, independent collection audit and native-proposal binding. Never rerun the completed replay or parity inference. Technical evidence alone neither selects nor qualifies a candidate; full confirmation and held-out strength remain required.'})
    manifest['recovery.json'] = digest(OUT/'recovery.json'); save(OUT/'manifest.json', manifest)
    save(OUT.with_suffix('.intent.json'), {'stage': 'upload_intent', 'manifest_sha256': digest(OUT/'manifest.json')})
    archive = upload_evidence(OUT)
    save(RESULT, {'complete': True, 'requests': 5106, 'positions_per_policy': 2553,
        'processor': result['processor'], 'identities': result['identities'],
        'technical_report_sha256': digest(result_path), 'checkpoint_binding_sha256': digest(binding_path),
        'archive': archive, 'candidate_selected': False, 'qualified': False, 'reserved_final_seeds_used': False})
    OUT.with_suffix('.intent.json').write_text(json.dumps({'stage': 'uploaded_download_verified', 'archive': archive,
        'descriptor_sha256': digest(RESULT)}, indent=2)+'\n')
    print(json.dumps({'complete': True, 'requests': 5106, 'archive': archive}), flush=True)


if __name__ == '__main__': main()
