"""Preserve the untrained discount extension, exact parity, and first failure."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from huggingface_hub import HfApi
import torch

from policy_iteration_evidence_archive import upload_evidence

ROOT = Path(__file__).resolve().parents[2]
NAME = 'auction-discount-warmstart-evidence-v1'
OUT = ROOT / 'ai/runs' / NAME
RESULT = ROOT / 'ai/strong' / (NAME + '.json')


def read(p): return json.loads(p.read_text())
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p, value):
    with p.open('x') as f:
        json.dump(value, f, indent=2, allow_nan=False)
        f.write('\n')


def main():
    for p in (OUT, OUT.with_suffix('.tgz'), OUT.with_suffix('.intent.json'), RESULT):
        assert not p.exists(), 'Inspect previous archive intent/outcome before retrying'
    torch.set_num_threads(1)
    run = ROOT / 'ai/runs/auction-discount-warmstart-v1'
    first = run.with_name(run.name + '-initial')
    report_path = ROOT / 'ai/strong/auction-discount-warmstart-results-v1.json'
    report, design = read(report_path), read(run / 'design.json')
    assert report == read(run / 'assessment.json') and report['passed']
    assert report['design_sha256'] == digest(run / 'design.json')
    assert report['native_exact_positions'] == report['export_choices_equal'] == 19843
    assert report['groups'] == {'cached_training_and_validation': 17280, 'serving': 2553, 'natural_discount': 10}
    assert report['max_export_parent_error'] == [0., 0.]
    assert report['training_admitted'] is report['qualification_eligible'] is report['reserved_final_seeds_used'] is False
    assert all(report[k] == 0 for k in ('new_gradient_updates', 'new_hf_jobs', 'new_games', 'new_rollouts'))
    sources = {Path(__file__).resolve(), report_path}
    for name, sha in report['artifacts'].items(): assert digest(run / name) == sha
    for name, sha in design['code'].items():
        assert digest(ROOT / name) == sha
        sources.add(ROOT / name)
    initial = design['preserved_initial_attempt']
    assert first == ROOT / initial['directory']
    assert digest(first / 'design.json') == initial['design_sha256']
    assert digest(first / 'numerical-first-failure.json') == initial['numerical_diagnosis_sha256']
    for name, sha in read(first / 'design.json')['code'].items():
        assert digest(first / 'source-files' / name) == sha
    failure = read(first / 'numerical-first-failure.json')
    assert failure['precision'] == 'float64' and failure['original_extension']['choice_changes'] == 0
    assert failure['copy_parent_prefix_control']['exact'] == [True, True]
    # This transitive dependency was not listed in the completed design. Bind it
    # separately and verify against the already frozen runtime; do not rewrite evidence.
    dependency = ROOT / 'ai/strong/model_v4.py'
    dependency_sha = '965469c5855ffbf8f6c152713bf48d07fd851cd94b363785820498df7fe027e0'
    frozen = ROOT / 'ai/runs/resource-turn-full-artifact-v4'
    assert digest(frozen / 'manifest.json') == design['artifact_manifest_sha256']
    assert digest(dependency) == digest(frozen / 'runtime/ai/strong/model_v4.py') == dependency_sha
    sources.add(dependency)
    trained = ROOT / 'ai/runs/policy-iteration-training-verified-v2/frozen'
    assert digest(trained / 'verified.json') == design['parent']['training_verified_sha256']
    assert digest(trained / 'ensemble-1/best.pt') == design['parent_training_checkpoint_sha256']
    old = torch.load(trained / 'ensemble-1/best.pt', map_location='cpu', weights_only=True)
    new = torch.load(run / 'warmstart.pt', map_location='cpu', weights_only=True)
    exported = torch.load(run / 'inference64.pt', map_location='cpu', weights_only=True)
    assert new['warm_start_parent_sha256'] == design['parent_training_checkpoint_sha256']
    assert new['new_gradient_updates'] == 0 and not new['qualification_eligible']
    assert (new['feature_revision'], new['state_dim'], new['action_dim']) == ('4.4-auction-discount', 1218, 103)
    assert all(torch.equal(new['state_dict'][k], v) for k, v in old['state_dict'].items())
    added = set(new['state_dict']) - set(old['state_dict'])
    assert added == set(new['initialized_new_tensors']) and len(added) == 8
    assert sum(new['state_dict'][k].numel() for k in added) == 1024
    assert all(torch.count_nonzero(new['state_dict'][k]) == 0 for k in added)
    assert exported['inference_only'] and exported['inference_precision'] == 'float64'
    assert new['state_dict'].keys() == exported['state_dict'].keys()
    assert all(torch.equal(v, exported['state_dict'][k]) for k, v in new['state_dict'].items())
    sources.add(trained / 'verified.json')
    for directory in (run, first): sources.update(p for p in directory.rglob('*') if p.is_file())
    for name in (
        'ai/runs/auction-discount-warmstart-v1-first.log',
        'ai/runs/auction-discount-warmstart-v1-second.log',
        'ai/AUCTION-DISCOUNT-WARMSTART-2026-10-28.md', 'ai/RESUME.md',
        'ai/strong/auction-discount-features-evidence-v1.json',
        'ai/strong/auction-training-history-evidence-v1.json',
        'ai/strong/policy-iteration-trained-frozen-evidence-v2.json',
        'ai/runs/resource-turn-full-artifact-v4/resource-full-descriptor.json',
        'ai/runs/resource-turn-full-artifact-v4/manifest.json',
        'ai/strong/resource-turn-boundary-policy-evidence-v2.json',
        'ai/strong/strategic-teacher-training-source-v1.json',
        'ai/strong/policy_iteration_evidence_archive.py', 'ai/strong/strategic_collection.py',
        'ai/strong/strategic_correction_check.py', 'ai/strong/feature_contract.py'):
        sources.add(ROOT / name)
    api = HfApi(); repo = 'coyotte508/powergrid-ai-germany-v1'
    assert api.model_info(repo).private and not api.file_exists(repo, 'archives/' + NAME + '.tgz')
    assert all(p.is_file() and not p.is_symlink() for p in sources)
    OUT.mkdir(); manifest = {}
    for p in sorted(sources):
        name = str(p.relative_to(ROOT)); target = OUT / name
        target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(p.read_bytes())
        manifest[name] = digest(target)
    save(OUT / 'manifest.json', manifest)
    intent = {'created_at': datetime.now(timezone.utc).isoformat(), 'stage': 'prepared_for_upload',
        'manifest_sha256': digest(OUT / 'manifest.json')}
    save(OUT.with_suffix('.intent.json'), intent)
    archive = upload_evidence(OUT)
    save(RESULT, {'status': 'untrained_discount_warm_start_exact_parity', 'report_sha256': digest(report_path),
        'design_sha256': report['design_sha256'], 'parent': design['parent'],
        'parent_training_checkpoint_sha256': design['parent_training_checkpoint_sha256'],
        'additional_code_pins': {'ai/strong/model_v4.py': dependency_sha},
        'artifacts': report['artifacts'], 'groups': report['groups'],
        'native_exact_positions': 19843, 'export_choices_equal': 19843, 'new_parameters': 1024,
        'stored_parent_tensors_unchanged': True, 'stored_new_tensors_zero': True,
        'initial_failure_preserved': True, 'new_hf_jobs': 0, 'new_gradient_updates': 0,
        'new_games': 0, 'new_rollouts': 0, 'archive_verification_inference': 0,
        'training_admitted': False, 'qualification_eligible': False, 'reserved_final_seeds_used': False,
        'archive': archive})
    OUT.with_suffix('.intent.json').write_text(json.dumps({**intent, 'stage': 'uploaded_download_verified',
        'archive': archive, 'descriptor_sha256': digest(RESULT)}, indent=2) + '\n')
    print(json.dumps(archive), flush=True)


if __name__ == '__main__': main()
