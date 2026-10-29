"""Archive source-builder validation; never publish it as an execution source."""
import json
from pathlib import Path

from huggingface_hub import HfApi
from policy_iteration_evidence_archive import upload_evidence
from public_policy_development_job_v1 import read, digest

ROOT = Path(__file__).resolve().parents[2]
NAME = 'selected-public-policy-final-source-evidence-v1'
OUT = ROOT/'ai/runs'/NAME
RESULT = ROOT/'ai/strong'/(NAME+'.json')


def save(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False); stream.write('\n')


def main():
    assert all(not p.exists() for p in (OUT, OUT.with_suffix('.tgz'), OUT.with_suffix('.intent.json'), RESULT)), 'Inspect existing archive intent/outcome'
    report_path = ROOT/'ai/strong/selected-public-policy-final-source-preflight-v1.json'
    report = read(report_path); validation = ROOT/'ai/runs/selected-public-policy-final-source-preflight-v1'
    assert report['passed'] and report['validated_jobs'] == 320 and report['games_executed'] == report['jobs_submitted'] == 0
    assert report['synthetic_candidate_and_allocation_only'] and not report['reserved_final_seeds_used']
    assert all(digest(ROOT/n) == sha for n, sha in report['input_hashes'].items())
    assert all(digest(ROOT/n) == sha for n, sha in report['validation_logs'].items())
    assert digest(validation/'validations.jsonl') == report['validation_receipts_sha256']
    assert digest(validation/'source/source-manifest.json') == report['source_manifest_sha256']
    assert all(digest(validation/'source'/n) == sha for n, sha in read(validation/'source/source-manifest.json').items())
    sources = {ROOT/n for n in report['input_hashes']}
    sources.update((Path(__file__).resolve(), report_path,
        ROOT/'ai/SELECTED-PUBLIC-POLICY-FINAL-SOURCE-2026-10-29.md',
        ROOT/'ai/strong/selected-public-policy-final-job-evidence-v1.json',
        ROOT/'ai/runs/selected-public-policy-final-source-preflight-v1-first.log',
        ROOT/'ai/strong/policy_iteration_evidence_archive.py', ROOT/'ai/strong/strategic_collection.py'))
    sources.update(p for p in validation.rglob('*') if p.is_file() and not p.is_relative_to(validation/'source/artifact'))
    source = read(ROOT/'ai/strong/current-auction-grid-source-v1.json')
    api = HfApi(); repo = 'coyotte508/powergrid-ai-germany-v1'
    assert api.model_info(repo).private and not api.file_exists(repo, 'archives/'+NAME+'.tgz')
    OUT.mkdir(); manifest = {}
    for p in sorted(sources):
        assert p.is_file() and not p.is_symlink()
        name = str(p.relative_to(ROOT)); before = digest(p)
        target = OUT/name; target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(p.read_bytes()); assert digest(target) == before == digest(p)
        manifest[name] = before
    save(OUT/'recovery.json', {
        'original_runtime_source': {k: source[k] for k in ('repo', 'revision', 'archive', 'sha256', 'source_manifest_sha256')},
        'runtime_manifest_sha256': report['identity']['runtimeManifestSha256'],
        'earlier_synthetic_control_evidence': read(ROOT/'ai/strong/selected-public-policy-final-job-evidence-v1.json')['archive'],
        'instruction': 'Restore the artifact directory from the referenced immutable confirmation source, then verify the complete source manifest. All archived candidate/contract/allocation controls are synthetic validation fixtures. Never upload this bundle as execution source or execute games. Preserve successful validations instead of rerunning them.',
        'candidate_selected': False, 'reserved_final_seeds_used': False})
    manifest['recovery.json'] = digest(OUT/'recovery.json'); save(OUT/'manifest.json', manifest)
    save(OUT.with_suffix('.intent.json'), {'stage': 'upload_intent', 'manifest_sha256': digest(OUT/'manifest.json')})
    archive = upload_evidence(OUT)
    save(RESULT, {'complete': True, 'validated_jobs': 320, 'tests': 7,
        'report_sha256': digest(report_path), 'identity': report['identity'],
        'candidate_selected': False, 'reserved_final_seeds_used': False, 'jobs_submitted': 0,
        'games_executed': 0, 'archive': archive})
    OUT.with_suffix('.intent.json').write_text(json.dumps({'stage': 'uploaded_download_verified',
        'archive': archive, 'descriptor_sha256': digest(RESULT)}, indent=2)+'\n')
    print(json.dumps(archive), flush=True)


if __name__ == '__main__':
    main()
