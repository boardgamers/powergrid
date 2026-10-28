"""Persist the separate discount feature cache and its verified source references."""
from datetime import datetime, timezone
import json
from pathlib import Path

import numpy as np
from huggingface_hub import HfApi
from policy_iteration_evidence_archive import upload_evidence
from public_policy_development_job_v1 import digest, read

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / 'ai/runs/auction-discount-features-v1'
NAME = 'auction-discount-features-evidence-v1'
OUT = ROOT / 'ai/runs' / NAME
RESULT = ROOT / 'ai/strong' / (NAME + '.json')


def save(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')


def main():
    for p in (OUT, OUT.with_suffix('.tgz'), OUT.with_suffix('.intent.json'), RESULT):
        assert not p.exists(), 'Inspect previous archive intent/outcome before retrying'
    report_path = ROOT / 'ai/strong/auction-discount-features-results-v1.json'
    report, design = read(report_path), read(RUN / 'design.json')
    assert report == read(RUN / 'assessment.json')
    assert report['complete'] and report['parent_prefixes_and_full_input_hashes_exact'] == 17280
    assert report['split_counts'] == {'train': 12960, 'validation': 4320}
    assert report['counts']['discounted_nomination_excluded_by_shortlist'] == 397
    assert report['counts']['discounted_nomination_in_old_menu'] == 2496
    assert report['counts']['discounted_nomination_labelled'] == 2099
    assert report['training_ready'] is report['qualification_eligible'] is report['reserved_final_seeds_used'] is False
    assert all(report[k] == 0 for k in ['new_hf_jobs', 'new_inference', 'new_games', 'new_gradients'])
    assert digest(RUN / 'design.json') == report['design_sha256']
    for name, sha in report['artifacts'].items():
        assert digest(RUN / name) == sha
    for name, sha in design['code'].items():
        assert digest(ROOT / name) == sha
    parent = ROOT / 'ai/runs/policy-iteration-features-v2'
    assert digest(parent / 'features.npz') == design['parent_features_sha256']
    assert digest(parent / 'metadata.json') == design['parent_metadata_sha256']
    with np.load(RUN / 'features.npz', allow_pickle=False) as new, np.load(parent / 'features.npz', allow_pickle=False) as old:
        assert new['state'].shape == (17280, 1218) and new['actions'].shape == (17280, 7, 103)
        np.testing.assert_array_equal(new['state'][:, :1217], old['state'])
        np.testing.assert_array_equal(new['actions'][:, :, :101], old['actions'])
        for key in ['mask', 'legal_indices', 'proposal_index']:
            np.testing.assert_array_equal(new[key], old[key])
    sources = {Path(__file__).resolve(), report_path}
    sources.update(p for p in RUN.rglob('*') if p.is_file())
    sources.update(ROOT / name for name in design['code'])
    sources.update(ROOT / name for name in (
        'ai/strong/test-auction-discount-features-v1.cjs',
        'ai/strong/policy-iteration-feature-cache-evidence-v2.json',
        'ai/strong/current-engine-policy-evidence-v1.json',
        'ai/strong/current-engine-compatibility-evidence-v1.json',
        'ai/strong/resource-runtime-preflight-evidence-v2.json',
        'ai/strong/policy_iteration_evidence_archive.py', 'ai/strong/strategic_collection.py',
        'ai/runs/auction-discount-features-v1-first.log',
        'ai/AUCTION-DISCOUNT-FEATURES-2026-10-28.md', 'ai/RESUME.md',
        'ai/runs/conservative-auction-development-attempts-coordinator-v1/state.json'))
    api = HfApi()
    repo = 'coyotte508/powergrid-ai-germany-v1'
    assert api.model_info(repo).private and not api.file_exists(repo, 'archives/' + NAME + '.tgz')
    OUT.mkdir()
    manifest = {}
    for p in sorted(sources):
        assert p.is_file() and not p.is_symlink()
        name = str(p.relative_to(ROOT))
        target = OUT / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(p.read_bytes())
        manifest[name] = digest(target)
    save(OUT / 'manifest.json', manifest)
    intent = {'created_at': datetime.now(timezone.utc).isoformat(), 'stage': 'prepared_for_upload',
        'manifest_sha256': digest(OUT / 'manifest.json')}
    save(OUT.with_suffix('.intent.json'), intent)
    archive = upload_evidence(OUT)
    save(RESULT, {'status': 'append_only_discount_inputs_verified_with_teacher_coverage_gap',
        'report_sha256': digest(report_path), 'design_sha256': report['design_sha256'],
        'feature_cache_sha256': digest(RUN / 'features.npz'), 'positions': 17280,
        'discounted_nominations': 2496, 'missing_discounted_nomination_labels': 397,
        'training_ready': False, 'qualification_eligible': False, 'reserved_final_seeds_used': False,
        'new_hf_jobs': 0, 'new_inference': 0, 'new_games': 0, 'new_gradients': 0,
        'archive': archive})
    OUT.with_suffix('.intent.json').write_text(json.dumps({**intent, 'stage': 'uploaded_download_verified',
        'archive': archive, 'descriptor_sha256': digest(RESULT)}, indent=2) + '\n')
    print(json.dumps(archive), flush=True)


if __name__ == '__main__':
    main()
