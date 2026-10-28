"""One-shot archive of the public-history resource sampling anchor evidence."""
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil

from huggingface_hub import HfApi
from policy_iteration_evidence_archive import upload_evidence
from public_policy_development_job_v1 import read, digest

ROOT = Path(__file__).resolve().parents[2]
NAME = 'resource-turn-anchor-evidence-v1'
OUT = ROOT/'ai/runs'/NAME
RESULT = ROOT/'ai/strong'/(NAME + '.json')


def save(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')


def main():
    for path in (OUT, OUT.with_suffix('.tgz'), OUT.with_suffix('.intent.json'), RESULT):
        assert not path.exists(), 'Inspect prior archive intent/outcome before retrying'
    run = ROOT/'ai/runs/resource-turn-anchor-v1'
    report = ROOT/'ai/strong/resource-turn-anchor-results-v1.json'
    assessment = read(run/'assessment.json')
    assert assessment['passed'] and read(report)['assessment_sha256'] == digest(run/'assessment.json')
    assert assessment['turns'] == 354 and assessment['counts']['positions'] == 1664
    assert assessment['counts']['purchases'] == 1310 and assessment['counts']['latent_world_checks'] == 13312
    assert assessment['new_hf_jobs'] == assessment['rollouts'] == assessment['new_full_game_trajectories'] == 0
    for key in ('code_hashes', 'input_hashes'):
        assert all(digest(ROOT/name) == sha for name, sha in assessment[key].items())
    assert all(digest(run/name) == sha for name, sha in assessment['output_hashes'].items())
    sources = {Path(__file__).resolve(), report, run.with_suffix('.log')}
    sources.update(path for path in run.rglob('*') if path.is_file())
    sources.update(ROOT/name for name in assessment['code_hashes'])
    sources.update(ROOT/'ai/strong'/name for name in (
        'resource-turn-full-integration-evidence-v2.json', 'resource-turn-full-integration-results-v2.json',
        'resource-turn-full-integration-evidence-v1.json', 'resource-replanning-development-complete-evidence-v1.json',
        'resource-replanning-job-source-v1.json', 'resource-public-state-checks-evidence-v1.json',
        'resource-sampling-anchor-results-v1.json', 'policy_iteration_evidence_archive.py', 'strategic_collection.py'))
    sources.update(ROOT/'ai'/name for name in ('RESOURCE-TURN-ANCHOR-2026-10-28.md',
        'RESOURCE-TURN-CORRECTED-INTEGRATION-2026-10-28.md', 'RESUME.md'))
    assert HfApi().model_info('coyotte508/powergrid-ai-germany-v1').private
    OUT.mkdir(); hashes = {}
    for source in sorted(sources):
        assert source.is_file() and not source.is_symlink()
        name = str(source.relative_to(ROOT)); target = OUT/name
        target.parent.mkdir(parents=True, exist_ok=True)
        before = digest(source); shutil.copy2(source, target)
        assert digest(target) == before; hashes[name] = before
    note = OUT/'README.md'
    note.write_text('''# Stateless public-history resource sampling anchor

354 existing turns / 1,664 positions; exact first-decision seed reconstruction,
13,312 stable latent-world checks, public-only and malformed-input controls.
Raw new receipts and exact sources are included. Original games/runtime are
referenced through immutable descriptors. This archive contains no new search
policy, inference, continuations, full games, HF jobs, gradients or final seeds.
It establishes a mechanism, not a playing-strength gain or deployment readiness.
''')
    hashes[note.name] = digest(note); save(OUT/'manifest.json', hashes)
    intent = {'created_at': datetime.now(timezone.utc).isoformat(), 'stage': 'prepared_for_upload',
        'archive_path': 'archives/' + NAME + '.tgz', 'manifest_sha256': digest(OUT/'manifest.json')}
    save(OUT.with_suffix('.intent.json'), intent)
    print(json.dumps({'stage': 'uploading', 'files': len(hashes) + 1}), flush=True)
    archive = upload_evidence(OUT)
    save(RESULT, {'status': 'stateless_resource_anchor_mechanism_verified_not_strength_tested',
        'assessment_sha256': digest(run/'assessment.json'), 'turns': 354, 'positions': 1664,
        'latent_world_checks': 13312, 'new_hf_jobs': 0, 'new_inference': False, 'rollouts': 0,
        'new_full_game_trajectories': 0, 'qualification_eligible': False,
        'reserved_final_seeds_used': False, 'archive': archive})
    OUT.with_suffix('.intent.json').write_text(json.dumps({**intent, 'stage': 'uploaded_download_verified',
        'archive': archive, 'descriptor_sha256': digest(RESULT)}, indent=2) + '\n')
    print(json.dumps(archive), flush=True)


if __name__ == '__main__':
    main()
