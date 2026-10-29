"""Archive audit-only evidence, referencing immutable original jobs and sources."""
from datetime import datetime, timezone
import json
from pathlib import Path

from huggingface_hub import HfApi
from policy_iteration_evidence_archive import upload_evidence
from public_policy_development_job_v1 import read, digest
from public_policy_final_contract_v1 import object_hash

ROOT = Path(__file__).resolve().parents[2]
NAME = 'current-auction-parallel-audit-evidence-v1'
OUT = ROOT/'ai/runs'/NAME
RESULT = ROOT/'ai/strong'/(NAME+'.json')


def save(path, value):
    with path.open('x') as f:
        json.dump(value, f, indent=2, allow_nan=False); f.write('\n')


def main():
    assert all(not p.exists() for p in (OUT, OUT.with_suffix('.tgz'),
        OUT.with_suffix('.intent.json'), RESULT)), 'Inspect previous archive outcome'
    ready_path = ROOT/'ai/strong/current-auction-parallel-comparison-readiness-v1.json'
    profile_path = ROOT/'ai/strong/current-auction-audit-parallel-profile-v1.json'
    ready, profile = read(ready_path), read(profile_path)
    assert ready['passed'] and ready['tests'] == 14 and ready['workers'] == 4
    assert ready['profile_sha256'] == digest(profile_path)
    assert profile['passed'] and profile['all_reviews_exact'] and profile['original_error_preserved']
    assert profile['games_per_pass'] == 248 and len(profile['cases']) == 6 and len(profile['passes']) == 4
    for report in (ready, profile):
        assert report['new_games'] == report['new_policy_calls'] == report['new_hf_jobs'] == 0
        assert not report['qualified'] and not report['reserved_final_seeds_used']
        assert all(digest(ROOT/n) == h for n, h in report['input_hashes'].items())
    sources = {ROOT/n for n in ready['input_hashes']}
    sources.update((Path(__file__).resolve(), ready_path, profile_path,
        ROOT/'ai/CURRENT-AUCTION-PARALLEL-AUDIT-2026-10-29.md',
        ROOT/'ai/strong/policy_iteration_evidence_archive.py',
        ROOT/'ai/strong/strategic_collection.py'))
    run = ROOT/'ai/runs/current-auction-audit-parallel-profile-v1'
    sources.update(p for p in run.rglob('*') if p.is_file())
    for name in ('current-auction-audit-parallel-profile-v1-first.log',
                 'current-auction-audit-parallel-profile-v1-process-check-fixed.log',
                 'current-auction-audit-parallel-profile-v1-before-process-check-fix.py'):
        sources.add(ROOT/'ai/runs'/name)
    references = []; recovery_links = []
    for case in profile['cases']:
        parent = 'current-auction-grid-hf-v1' if case['kind'] == 'confirmation' else 'current-auction-runtime-hf-v1'
        folder = ROOT/'ai/runs'/parent/case['name']
        receipt = folder/'verified.json'
        if not receipt.exists(): receipt = folder/'verified-terminal-recovery-v1.json'
        saved = read(receipt)
        assert digest(receipt) == case['verified_sha256'] and digest(folder/'launch.json') == case['guard_sha256']
        assert saved['job_id'] == case['job_id'] and saved['evidence']['remote_archive_verified']
        for p in profile['passes']:
            proof = next(v for v in p['per_job'] if v['name'] == case['name'])
            assert proof['review_sha256'] == object_hash(saved['review'])
            assert proof['original_hf_stage'] == saved['stage'] and p['games'] == 248
        references.append({**case, 'original_hf_stage': saved['stage'],
            'games': saved['review']['games'], 'raw_archive': saved['evidence'],
            'receipt': str(receipt.relative_to(ROOT))})
        if saved['stage'] == 'ERROR':
            recovered = folder/'terminal-recovery-v1'
            sources.update((recovered/'intent.json', recovered/'review.json',
                            recovered/'evaluation/evaluation.json'))
            for target in (recovered/'evaluation').iterdir():
                if target.name == 'evaluation.json': continue
                original = folder/'artifacts/job/evaluation'/target.name
                assert target.is_file() and digest(target) == digest(original)
                recovery_links.append({'original': str(original.relative_to(ROOT)),
                    'target': str(target.relative_to(ROOT)), 'sha256': digest(original)})
    repo = 'coyotte508/powergrid-ai-germany-v1'; api = HfApi()
    assert api.model_info(repo).private and not api.file_exists(repo, 'archives/'+NAME+'.tgz')
    OUT.mkdir(); manifest = {}
    for path in sorted(sources):
        assert path.is_file() and not path.is_symlink()
        name = str(path.relative_to(ROOT)); before = digest(path); target = OUT/name
        target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(path.read_bytes())
        assert digest(target) == before == digest(path); manifest[name] = before
    save(OUT/'raw-references.json', {'originals': references,
        'recovered_evaluation_links': recovery_links,
        'source_descriptors': ['ai/strong/current-auction-grid-source-v1.json',
                               'ai/strong/current-auction-runtime-source-v1.json'],
        'instructions': 'Restore originals from these immutable revisions/hashes and verify manifests. Preserve the original ERROR and archived separate derived terminal recovery. Copy or hardlink recovered_evaluation_links from the unchanged raw originals, checking hashes; never modify those raw links. Do not rerun simulations or benchmark passes. Restore source bundles using the archived descriptors; they are unchanged.'})
    manifest['raw-references.json'] = digest(OUT/'raw-references.json')
    save(OUT/'manifest.json', manifest)
    intent = {'created_at': datetime.now(timezone.utc).isoformat(),
        'stage': 'prepared_for_upload', 'manifest_sha256': digest(OUT/'manifest.json')}
    save(OUT.with_suffix('.intent.json'), intent)
    archive = upload_evidence(OUT)
    save(RESULT, {'passed': True, 'tests': 14, 'original_artifacts': 6, 'games_per_pass': 248,
        'passes': 4, 'all_reviews_exact': True, 'original_error_preserved': True,
        'readiness_sha256': digest(ready_path), 'profile_sha256': digest(profile_path),
        'median_wall_speedup': profile['median_wall_speedup'], 'new_games': 0,
        'new_policy_calls': 0, 'new_hf_jobs': 0, 'live_coordinator_changed': False,
        'qualified': False, 'reserved_final_seeds_used': False, 'archive': archive})
    OUT.with_suffix('.intent.json').write_text(json.dumps({**intent,
        'stage': 'uploaded_download_verified', 'archive': archive,
        'descriptor_sha256': digest(RESULT)}, indent=2)+'\n')
    print(json.dumps(archive), flush=True)


if __name__ == '__main__': main()
