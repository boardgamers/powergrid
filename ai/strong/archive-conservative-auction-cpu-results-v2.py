"""Archive a completed, independently audited actual-8840U benchmark."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil

from huggingface_hub import HfApi
from policy_iteration_evidence_archive import upload_evidence
from public_policy_development_job_v1 import read, write, digest

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'ai/runs/conservative-auction-cpu-results-evidence-v2'
DESCRIPTOR = ROOT/'ai/strong/conservative-auction-cpu-results-evidence-v2.json'
COLLECTED = ROOT/'ai/runs/conservative-auction-8840u-collected-v2'
REVIEW = ROOT/'ai/strong/conservative-auction-8840u-cost-review-v2.json'


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--archive', action='store_true', required=True)
    parser.parse_args()
    assert not any(p.exists() for p in (OUT, OUT.with_suffix('.tgz'), OUT.with_suffix('.intent.json'), DESCRIPTOR)), 'Inspect previous archive intent/outcome before any retry'
    assessment = read(COLLECTED/'assessment.json')
    status = read(COLLECTED/'output/status.json')
    review = read(REVIEW)
    assert assessment['complete'] and assessment['exact_cross_host_responses'] == 300 and assessment['caps'] == 0
    assert status['stage'] == 'completed' and status['passed'] and status['completed_requests'] == 300
    assert '8840U' in status['processor'] and status['required_cpu'] == '8840U'
    assert digest(COLLECTED/'output/status.json') == assessment['target_status_sha256']
    assert all(digest(COLLECTED/'output'/name) == sha for name, sha in status['output_hashes'].items())
    assert review['requests'] == review['exact_cross_host_responses'] == 300
    assert not review['qualification_eligible'] and not review['reserved_final_seeds_used']
    assert all(digest(ROOT/name) == sha for name, sha in review['source_hashes'].items())
    references = {}
    for name in ('readiness', 'recovery-evidence', 'target-launch-evidence'):
        path = ROOT/f'ai/strong/conservative-auction-cpu-{name}-v2.json'
        references[str(path.relative_to(ROOT))] = read(path)['archive']
    target_launch = read(ROOT/'ai/strong/conservative-auction-cpu-target-launch-evidence-v2.json')
    assert assessment['local_status_sha256'] == target_launch['checkpoint']['local_reference_sha256']
    assert assessment['manifest_sha256'] == target_launch['checkpoint']['target_guard']['manifest_sha256']
    repo = 'coyotte508/powergrid-ai-germany-v1'
    api = HfApi()
    assert api.repo_info(repo).private
    assert 'archives/'+OUT.name+'.tgz' not in api.list_repo_files(repo), 'Inspect previous remote archive'
    paths = {p for p in COLLECTED.rglob('*') if p.is_file()}
    paths.update(ROOT/name for name in references)
    paths.update((Path(__file__), REVIEW,
        ROOT/'ai/strong/analyze_conservative_auction_cpu_v2.py',
        ROOT/'ai/strong/test_conservative_auction_cpu_analysis_v2.py',
        ROOT/'ai/runs/conservative-auction-cpu-analysis-tests-v2.log',
        ROOT/'ai/strong/conservative-auction-8840u-launch-v2.json',
        ROOT/'ai/RESUME.md', ROOT/'ai/CONSERVATIVE-AUCTION-CPU-2026-10-27.md'))
    checkpoint = {'created_at': datetime.now(timezone.utc).isoformat(),
        'actual_target_complete': True, 'processor': status['processor'],
        'independent_receipts_audited': 600, 'exact_cross_host_responses': 300, 'caps': 0,
        'assessment_sha256': digest(COLLECTED/'assessment.json'),
        'cost_review_sha256': digest(REVIEW), 'raw_target_status_sha256': digest(COLLECTED/'output/status.json'),
        'immutable_recovery_archives': references,
        'interpretation': review['interpretation'],
        'local_reference': 'Two-segment correctness reference, preserved in the target-launch archive. No local uninterrupted timing claim.',
        'new_hf_jobs_from_cpu_work': 0, 'new_strength_games': 0,
        'qualification_eligible': False, 'reserved_final_seeds_used': False}
    OUT.mkdir()
    hashes = {}
    for path in sorted(paths):
        assert not path.is_symlink()
        name = str(path.relative_to(ROOT)); target = OUT/name
        target.parent.mkdir(parents=True, exist_ok=True)
        before = digest(path); shutil.copyfile(path, target)
        assert digest(target) == digest(path) == before
        hashes[name] = before
    write(OUT/'checkpoint.json', checkpoint)
    hashes['checkpoint.json'] = digest(OUT/'checkpoint.json')
    write(OUT/'manifest.json', hashes)
    with OUT.with_suffix('.intent.json').open('x') as stream:
        json.dump({'manifest_sha256': digest(OUT/'manifest.json'), 'archive_path': 'archives/'+OUT.name+'.tgz'}, stream)
    evidence = upload_evidence(OUT)
    write(DESCRIPTOR, {'actual_target_complete': True, 'archive': evidence,
        'checkpoint': checkpoint, 'qualification_eligible': False, 'reserved_final_seeds_used': False})
    print(json.dumps(evidence), flush=True)


if __name__ == '__main__': main()
