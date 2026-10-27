"""Preserve CPU preparation and reviewed owner recovery without new jobs."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil

from huggingface_hub import HfApi
from policy_iteration_evidence_archive import upload_evidence
from public_policy_development_job_v1 import read, write, digest

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'ai/runs/conservative-auction-cpu-readiness-v2'
DESCRIPTOR = ROOT/'ai/strong/conservative-auction-cpu-readiness-v2.json'


def live(state, needle):
    path = Path('/proc')/str(state['pid'])/'cmdline'
    return path.exists() and needle.encode() in path.read_bytes()


def main():
    parser = argparse.ArgumentParser(__doc__); parser.add_argument('--archive', required=True, action='store_true'); parser.parse_args()
    assert not any(p.exists() for p in (OUT, OUT.with_suffix('.tgz'), OUT.with_suffix('.intent.json'), DESCRIPTOR))
    repo = 'coyotte508/powergrid-ai-germany-v1'; api = HfApi()
    assert api.repo_info(repo).private and 'archives/'+OUT.name+'.tgz' not in api.list_repo_files(repo)
    recovery = ROOT/'ai/runs/conservative-auction-development-coordinator-recovery-v2'
    owner = read(recovery/'state.json'); assert live(owner, 'recover-conservative-auction-development-v2.py')
    assert all(digest(ROOT/name) == sha for name, sha in owner['code_hashes'].items())
    local = read(ROOT/'ai/runs/conservative-auction-8840u-local-v2/status.json')
    local_live = live(local, 'conservative-auction-8840u-prepared-v2/package/benchmark.py')
    assert local_live or local['stage'] == 'completed'
    prep = ROOT/'ai/runs/conservative-auction-8840u-prepared-v2'; p = read(prep/'prepared.json')
    assert p['package_sha256'] == digest(prep/'package.tgz')
    assert p['runner_sha256'] == digest(ROOT/'ai/strong/conservative_auction_cpu_v2.py')
    assert p['manager_sha256'] == digest(ROOT/'ai/strong/benchmark-conservative-auction-8840u-v2.py')
    test_names = {'conservative-auction-cpu-tests-v2.log': 6, 'conservative-auction-owner-recovery-tests-v2.log': 3,
                  'conservative-auction-analysis-owner-path-tests-v2.log': 14}
    paths = {ROOT/'ai/runs'/name for name in test_names}
    for name, count in test_names.items():
        value = (ROOT/'ai/runs'/name).read_text()
        assert f'Ran {count} tests' in value and value.rstrip().endswith('OK')
    names = ('conservative_auction_cpu_v2.py', 'benchmark-conservative-auction-8840u-v2.py',
        'test_conservative_auction_cpu_v2.py', 'recover-conservative-auction-development-v2.py',
        'test_conservative_auction_owner_recovery_v2.py', 'compare-conservative-auction-development-v2.py',
        'archive-conservative-auction-cpu-readiness-v2.py', 'conservative-auction-runtime-source-v2.json',
        'conservative-auction-analysis-readiness-v2.json')
    paths.update(ROOT/'ai/strong'/name for name in names)
    paths.update((prep/'prepared.json', prep/'local-intent.json', prep/'package/cases.json',
        prep/'package/benchmark.py', prep/'package/benchmark-manifest.json', recovery/'predecessor.json',
        ROOT/'ai/runs/conservative-auction-development-coordinator-v2/state.json',
        ROOT/'ai/runs/conservative-auction-development-coordinator-v2.log',
        ROOT/'ai/runs/conservative-auction-runtime-manual-collect-after-interrupt-v2.log',
        ROOT/'ai/runs/conservative-auction-cpu-initial-rejection-v2.json'))
    paths.update(ROOT/'ai'/name for name in ('RESUME.md', 'CONSERVATIVE-AUCTION-CPU-2026-10-27.md',
        'CONSERVATIVE-AUCTION-DEVELOPMENT-2026-10-27.md', 'CONSERVATIVE-AUCTION-ANALYSIS-2026-10-27.md'))
    checkpoint = {'created_at': datetime.now(timezone.utc).isoformat(), 'owner': owner, 'owner_verified_live': True,
        'original_pilot_statuses': [{'job_id': j, 'stage': api.inspect_job(job_id=j).status.stage} for j in owner['original_pilots']],
        'local_reference': local, 'local_reference_verified_live': local_live, 'prepared': p,
        'target_launch_exists': (ROOT/'ai/strong/conservative-auction-8840u-launch-v2.json').exists(),
        'tests': test_names, 'raw_fixture_projection_legal_menus_unchanged': 100,
        'runtime_recovery': 'Restore artifact/ from the immutable runtime source archive in the saved benchmark manifest, then add archived benchmark.py and cases.json; verify every benchmark-manifest file hash before execution. Do not rerun originals to recover evidence.',
        'previous_goal_turn': 'progress: independent complete-grid analysis tested, archived and pushed',
        'current_goal_turn': 'progress: exact public projected CPU coverage prepared and local reference running; terminated waiter inspected and single recovery owner started',
        'new_hf_jobs_from_this_work': 0, 'new_strength_games': 0, 'qualified': False, 'reserved_final_seeds_used': False}
    OUT.mkdir(); hashes = {}
    for path in sorted(paths):
        name = str(path.relative_to(ROOT)); target = OUT/name; target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target); hashes[name] = digest(path); assert digest(target) == hashes[name]
    write(OUT/'checkpoint.json', checkpoint); hashes['checkpoint.json'] = digest(OUT/'checkpoint.json')
    write(OUT/'manifest.json', hashes)
    with OUT.with_suffix('.intent.json').open('x') as stream:
        json.dump({'manifest_sha256': digest(OUT/'manifest.json'), 'archive_path': 'archives/'+OUT.name+'.tgz'}, stream)
    evidence = upload_evidence(OUT)
    write(DESCRIPTOR, {'readiness_verified': True, 'archive': evidence, 'checkpoint': checkpoint,
        'target_benchmark_complete': False, 'qualification_eligible': False, 'reserved_final_seeds_used': False})
    print(json.dumps(evidence), flush=True)


if __name__ == '__main__': main()
