"""Archive tested final-collection code and explicitly synthetic rejection proof.

No game execution, inference, job submission, collection or repeated tests.
"""
import json
from pathlib import Path
import shutil

from huggingface_hub import HfApi
from policy_iteration_evidence_archive import upload_evidence
from public_policy_final_audit_v1 import digest, read

ROOT = Path(__file__).resolve().parents[2]
STRONG = ROOT / 'ai/strong'
RUNS = ROOT / 'ai/runs'
NAME = 'selected-public-policy-final-collection-evidence-v1'
OUT = RUNS / NAME
DESCRIPTOR = STRONG / (NAME + '.json')


def save(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False); stream.write('\n')


def main():
    assert all(not p.exists() for p in (OUT, OUT.with_suffix('.tgz'), OUT.with_suffix('.intent.json'), DESCRIPTOR)), 'Inspect existing archive outcome before any retry'
    report_path = STRONG / 'selected-public-policy-final-collection-preflight-v1.json'
    report = read(report_path)
    assert report['passed'] and report['unit_tests'] == 16
    assert report['synthetic_missing_game_summary_rejected'] == 'Missing/duplicate episodes'
    assert all(report[k] == 0 for k in ('games_executed', 'policy_inference_calls', 'hf_jobs_submitted', 'actual_subprocesses'))
    assert report['qualified'] is False and report['reserved_final_seeds_used'] is False
    assert all(digest(ROOT/n) == sha for n,sha in {**report['input_hashes'], **report['synthetic_fixture_hashes']}.items())
    sources = {ROOT/n for n in {**report['input_hashes'], **report['synthetic_fixture_hashes']}}
    sources.update({Path(__file__).resolve(), report_path,
        STRONG / 'selected-public-policy-final-dispatch-evidence-v1.json',
        STRONG / 'policy_iteration_evidence_archive.py',
        RUNS / 'selected-public-policy-final-collection-preflight-v1-first.log',
        RUNS / 'selected_public_policy_final_collection_v1-before-stage-worker-binding.py',
        RUNS / 'test_selected_public_policy_final_collection_v1-before-stage-worker-binding.py'})
    api = HfApi(); repo = 'coyotte508/powergrid-ai-germany-v1'
    assert api.model_info(repo).private and not api.file_exists(repo, 'archives/' + NAME + '.tgz')
    OUT.mkdir(); manifest = {}
    for p in sorted(sources):
        assert p.is_file() and not p.is_symlink()
        name = str(p.relative_to(ROOT)); target = OUT / name
        target.parent.mkdir(parents=True, exist_ok=True)
        with p.open('rb') as src, target.open('xb') as dst: shutil.copyfileobj(src, dst)
        assert digest(target) == digest(p); manifest[name] = digest(p)
    save(OUT / 'SYNTHETIC-TEST-SCOPE.json', {
        'scope': 'Unit tests and negative collection integration only. Claimed final completion/launch metadata inside the fixture is deliberately synthetic and must be rejected for missing actual games.',
        'actual_final_games': 0, 'actual_policy_inference_calls': 0, 'candidate_selected': False,
        'qualified': False, 'reserved_final_seeds_used': False,
        'source_package_recovery': read(STRONG / 'selected-public-policy-final-source-evidence-v1.json')['archive'],
        'dispatch_fixture_recovery': read(STRONG / 'selected-public-policy-final-dispatch-evidence-v1.json')['archive']})
    manifest['SYNTHETIC-TEST-SCOPE.json'] = digest(OUT / 'SYNTHETIC-TEST-SCOPE.json')
    save(OUT / 'manifest.json', manifest)
    save(OUT.with_suffix('.intent.json'), {'stage': 'upload_intent', 'report_sha256': digest(report_path)})
    archive = upload_evidence(OUT)
    save(DESCRIPTOR, {'complete': True, 'report_sha256': digest(report_path), 'archive': archive,
        'tests': 16, 'synthetic_missing_games_rejected': True, 'actual_games': 0,
        'candidate_selected': False, 'qualified': False, 'reserved_final_seeds_used': False})
    OUT.with_suffix('.intent.json').write_text(json.dumps({'stage': 'uploaded_download_verified',
        'archive': archive, 'descriptor_sha256': digest(DESCRIPTOR)}, indent=2) + '\n')
    print(json.dumps({'complete': True, 'tests': 16, 'archive': archive}), flush=True)


if __name__ == '__main__': main()
