"""Archive paired feature-alias evidence; no policy inference or new trajectories."""
from datetime import datetime, timezone
import json
from pathlib import Path

from huggingface_hub import HfApi
from policy_iteration_evidence_archive import upload_evidence
from public_policy_development_job_v1 import digest, read

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / 'ai/runs/auction-discount-encoding-v1'
NAME = 'auction-discount-encoding-evidence-v1'
OUT = ROOT / 'ai/runs' / NAME
RESULT = ROOT / 'ai/strong' / (NAME + '.json')


def save(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')


def main():
    for p in (OUT, OUT.with_suffix('.tgz'), OUT.with_suffix('.intent.json'), RESULT):
        assert not p.exists(), 'Inspect previous archive intent/outcome before retrying'
    report_path = ROOT / 'ai/strong/auction-discount-encoding-results-v1.json'
    report = read(report_path)
    design = read(RUN / 'design.json')
    pairs = read(RUN / 'pairs.json')
    assert report['completed'] and report['fixtures'] == report['aliased_complete_encodings'] == len(pairs) == 10
    assert report['encoder_calls'] == 20
    assert report['new_inference'] == report['new_search_rollouts'] == report['new_hf_jobs'] == 0
    assert report['qualification_eligible'] is report['reserved_final_seeds_used'] is False
    assert report['design_sha256'] == digest(RUN / 'design.json')
    assert report['pairs_sha256'] == digest(RUN / 'pairs.json')
    assert design['checker_sha256'] == digest(ROOT / 'ai/strong/check-auction-discount-encoding-v1.cjs')
    assert design['source_fixture_sha256'] == digest(ROOT / 'ai/runs/current-engine-policy-v1/inputs.json')
    assert {(r['players'], r['sealed']) for r in pairs} == {(n, sealed) for n in range(2, 7) for sealed in (False, True)}
    for row in pairs:
        assert row['same_legal_menu'] and row['opening_bid_discounted'] == 1
        assert row['opening_bid_ordinary'] == row['plant'] > 1
        assert row['encoding_with_discount'] == row['encoding_without_discount']
        assert row['nomination_prior_with_discount'] == row['nomination_prior_without_discount']
    sources = {Path(__file__).resolve(), report_path}
    sources.update(p for p in RUN.rglob('*') if p.is_file())
    sources.update(ROOT / name for name in (
        'ai/strong/check-auction-discount-encoding-v1.cjs',
        'ai/strong/current-engine-policy-evidence-v1.json',
        'ai/strong/current-engine-compatibility-evidence-v1.json',
        'ai/strong/resource-runtime-preflight-evidence-v2.json',
        'ai/strong/policy_iteration_evidence_archive.py', 'ai/strong/strategic_collection.py',
        'ai/runs/auction-discount-encoding-v1.log',
        'ai/AUCTION-DISCOUNT-ENCODING-2026-10-28.md', 'ai/RESUME.md',
        'ai/runs/conservative-auction-development-attempts-coordinator-v1/state.json'))
    api = HfApi()
    repo = 'coyotte508/powergrid-ai-germany-v1'
    assert api.model_info(repo).private and not api.file_exists(repo, 'archives/' + NAME + '.tgz')
    OUT.mkdir()
    hashes = {}
    for p in sorted(sources):
        assert p.is_file() and not p.is_symlink()
        name = str(p.relative_to(ROOT))
        target = OUT / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(p.read_bytes())
        hashes[name] = digest(target)
    save(OUT / 'manifest.json', hashes)
    intent = {'created_at': datetime.now(timezone.utc).isoformat(), 'stage': 'prepared_for_upload',
              'manifest_sha256': digest(OUT / 'manifest.json')}
    save(OUT.with_suffix('.intent.json'), intent)
    archive = upload_evidence(OUT)
    save(RESULT, {'status': 'discount_flag_aliased_in_all_ten_fixed_encoder_pairs',
                 'report_sha256': digest(report_path), 'design_sha256': report['design_sha256'],
                 'pairs_sha256': report['pairs_sha256'], 'fixtures': 10, 'encoder_calls': 20,
                 'aliased_complete_encodings': 10, 'opening_bid_changed': 10,
                 'new_inference': 0, 'new_search_rollouts': 0, 'new_hf_jobs': 0,
                 'new_full_game_trajectories': 0, 'new_gradients': 0,
                 'qualification_eligible': False, 'reserved_final_seeds_used': False, 'archive': archive})
    OUT.with_suffix('.intent.json').write_text(json.dumps({**intent, 'stage': 'uploaded_download_verified',
        'archive': archive, 'descriptor_sha256': digest(RESULT)}, indent=2) + '\n')
    print(json.dumps(archive), flush=True)


if __name__ == '__main__':
    main()
