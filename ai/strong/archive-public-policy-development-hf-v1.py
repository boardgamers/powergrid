"""Preserve the original verified HF portability job and its submission evidence."""
import argparse
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import shutil

from policy_iteration_evidence_archive import upload_evidence
from public_policy_development_job_v1 import read, write, digest

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'ai/runs/public-policy-development-hf-evidence-v1'
DESCRIPTOR = ROOT/'ai/strong/public-policy-development-hf-evidence-v1.json'
spec = importlib.util.spec_from_file_location('development_hf_archive_manager', ROOT/'ai/strong/manage-public-policy-development-hf-v1.py')
manager = importlib.util.module_from_spec(spec); spec.loader.exec_module(manager)


def main():
    parser = argparse.ArgumentParser(__doc__); parser.add_argument('--archive', action='store_true', required=True)
    parser.parse_args()
    assert not any(p.exists() for p in (OUT, OUT.with_suffix('.tgz'), DESCRIPTOR))
    assert manager.RESULT.exists(), 'Collect and verify the original HF job first'
    result = manager.collect()
    assert result['verified'] and result['authoritative_status'] == 'COMPLETED'
    assert result['review']['exact_local_comparison'] and result['review']['games'] == 8
    assert result['review']['decisions'] == 1607
    tests = ROOT/'ai/runs/public-policy-development-hf-tests-v1.log'
    assert 'Ran 5 tests' in tests.read_text() and tests.read_text().rstrip().endswith('OK')
    study = read(ROOT/'ai/runs/surrogate-continuation-study-coordinator-v1/state.json')
    assert all(digest(ROOT/name) == sha for name, sha in study['code_hashes'].items())
    process = Path('/proc')/str(study['pid'])/'cmdline'
    live = process.exists() and b'coordinate-surrogate-continuation-study-v1.py' in process.read_bytes()
    assert live or study['stage'] in ('complete', 'complete_with_caps')
    assert read(ROOT/'ai/strong/experiments.json')['final_seed_prefix_used'] is False
    checkpoint = {'checked_at': datetime.now(timezone.utc).isoformat(),
                  'previous_goal_turn': 'progress: local development job execution verified, archived and pushed',
                  'current_goal_turn': 'progress: actual HF source, original job and uploaded raw evidence independently verified',
                  'study_owner_live': live, 'study_pinned_code_unchanged': True, 'study_state': study,
                  'new_hf_jobs': 1, 'new_strength_games': 0, 'gradient_updates': 0, 'reserved_final_seeds_used': False}
    paths = {p for p in manager.OUT.rglob('*') if p.is_file() and not p.name.startswith('.')}
    paths.update({manager.SOURCE, manager.RESULT, Path(__file__), tests,
                  ROOT/'ai/strong/manage-public-policy-development-hf-v1.py',
                  ROOT/'ai/strong/test_public_policy_development_hf_v1.py',
                  ROOT/'ai/strong/public-policy-development-job-evidence-v1.json',
                  ROOT/'ai/strong/policy_iteration_evidence_archive.py'})
    OUT.mkdir(); hashes = {}
    for path in sorted(paths):
        name = str(path.relative_to(ROOT)); dest = OUT/name; dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dest); hashes[name] = digest(path); assert digest(dest) == hashes[name]
    write(OUT/'checkpoint.json', checkpoint); hashes['checkpoint.json'] = digest(OUT/'checkpoint.json')
    write(OUT/'manifest.json', hashes)
    print(json.dumps({'stage': 'uploading', 'files': len(hashes)+1}), flush=True)
    evidence = upload_evidence(OUT)
    write(DESCRIPTOR, {'complete': True, 'original_job_id': result['job_id'], 'review': result['review'],
          'source': result['source'], 'raw_hf_job_evidence': result['evidence'], 'archive': evidence,
          'checkpoint': checkpoint, 'submission_tests': 5, 'result_sha256': digest(manager.RESULT),
          'qualification_eligible': False, 'reserved_final_seeds_used': False,
          'scope': 'Exact local/HF portability of filtered-policy development execution. Auction settings, strength, actual target latency and final execution admission remain unqualified.'})
    print(json.dumps(evidence), flush=True)


if __name__ == '__main__': main()
