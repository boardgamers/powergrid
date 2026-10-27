"""Archive the immutable interrupted prefix and one-shot recovery provenance."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil

from huggingface_hub import HfApi
from policy_iteration_evidence_archive import upload_evidence
from public_policy_development_job_v1 import read, write, digest

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'ai/runs/conservative-auction-cpu-recovery-evidence-v2'
DESCRIPTOR = ROOT/'ai/strong/conservative-auction-cpu-recovery-evidence-v2.json'


def main():
    parser = argparse.ArgumentParser(__doc__); parser.add_argument('--archive', required=True, action='store_true'); parser.parse_args()
    assert not any(p.exists() for p in (OUT, OUT.with_suffix('.tgz'), OUT.with_suffix('.intent.json'), DESCRIPTOR))
    repo = 'coyotte508/powergrid-ai-germany-v1'; api = HfApi()
    assert api.repo_info(repo).private and 'archives/'+OUT.name+'.tgz' not in api.list_repo_files(repo)
    guard_path = ROOT/'ai/strong/conservative-auction-cpu-local-recovery-launch-v2.json'; guard = read(guard_path)
    helper = ROOT/'ai/strong/recover-conservative-auction-cpu-v2.py'; assert guard['runner_sha256'] == digest(helper)
    old = ROOT/'ai/runs/conservative-auction-8840u-local-v2'
    assert digest(old/'status.json') == guard['original_status_sha256']
    assert digest(old/'receipts.jsonl') == guard['original_receipts_sha256']
    recovery = ROOT/'ai/runs/conservative-auction-8840u-local-recovered-v2'; state = read(recovery/'status.json')
    command = Path('/proc')/str(guard['pid'])/'cmdline'
    args = command.read_bytes().split(b'\0') if command.exists() else []
    live = any(p.endswith(b'/recover-conservative-auction-cpu-v2.py') for p in args) and b'run' in args
    assert live or (state['stage'] == 'completed' and state['passed'])
    owner = read(ROOT/'ai/runs/conservative-auction-development-coordinator-recovery-v2/state.json')
    assert all(digest(ROOT/name) == sha for name, sha in owner['code_hashes'].items())
    paths = {p for p in old.iterdir() if p.is_file()}
    paths.update((Path(__file__), helper, guard_path, recovery/'original-interruption.json',
        ROOT/'ai/strong/test_conservative_auction_cpu_recovery_v2.py',
        ROOT/'ai/strong/analyze_conservative_auction_cpu_v2.py',
        ROOT/'ai/strong/test_conservative_auction_cpu_analysis_v2.py',
        ROOT/'ai/strong/conservative-auction-cpu-readiness-v2.json',
        ROOT/'ai/RESUME.md', ROOT/'ai/CONSERVATIVE-AUCTION-CPU-2026-10-27.md'))
    for name, count in (('conservative-auction-cpu-recovery-tests-v2.log', 3), ('conservative-auction-cpu-analysis-tests-v2.log', 5)):
        p = ROOT/'ai/runs'/name; value = p.read_text(); assert f'Ran {count} tests' in value and value.rstrip().endswith('OK'); paths.add(p)
    checkpoint = {'created_at': datetime.now(timezone.utc).isoformat(), 'original_local_exit_code': 143,
        'original_prefix_reaudited': 273, 'suffix_requests_planned': 27, 'recovery': state,
        'recovery_verified_live': live, 'owner_snapshot': owner,
        'original_pilot_statuses': [{'job_id': j, 'stage': api.inspect_job(job_id=j).status.stage} for j in owner['original_pilots']],
        'scope': 'Interrupted local correctness reference and inspected suffix-only recovery. Not complete target performance or new playing strength.',
        'previous_goal_turn': 'progress: descriptive complete-target timing review tested and pushed',
        'current_goal_turn': 'progress: terminal local interruption inspected; 273 responses preserved/re-audited and only 27 missing fixed requests resumed; both 2p HF pilots completed',
        'new_hf_jobs': 0, 'new_strength_games': 0, 'qualified': False, 'reserved_final_seeds_used': False}
    OUT.mkdir(); hashes = {}
    for path in sorted(paths):
        name = str(path.relative_to(ROOT)); target = OUT/name; target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target); hashes[name] = digest(path); assert digest(target) == hashes[name]
    write(OUT/'checkpoint.json', checkpoint); hashes['checkpoint.json'] = digest(OUT/'checkpoint.json')
    write(OUT/'manifest.json', hashes)
    with OUT.with_suffix('.intent.json').open('x') as stream: json.dump({'manifest_sha256': digest(OUT/'manifest.json'), 'archive_path': 'archives/'+OUT.name+'.tgz'}, stream)
    evidence = upload_evidence(OUT)
    write(DESCRIPTOR, {'interrupted_prefix_preserved': True, 'archive': evidence, 'checkpoint': checkpoint,
        'target_benchmark_complete': False, 'qualification_eligible': False, 'reserved_final_seeds_used': False})
    print(json.dumps(evidence), flush=True)


if __name__ == '__main__': main()
