"""Archive the complete local parity reference and exact live target launch."""
import argparse
import contextlib
from datetime import datetime, timezone
import importlib.util
import io
import json
from pathlib import Path
import shutil

from huggingface_hub import HfApi
from policy_iteration_evidence_archive import upload_evidence
from public_policy_development_job_v1 import read, write, digest

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'ai/runs/conservative-auction-cpu-target-launch-evidence-v2'
DESCRIPTOR = ROOT/'ai/strong/conservative-auction-cpu-target-launch-evidence-v2.json'


def main():
    parser = argparse.ArgumentParser(__doc__); parser.add_argument('--archive', action='store_true', required=True); parser.parse_args()
    assert not any(p.exists() for p in (OUT, OUT.with_suffix('.tgz'), OUT.with_suffix('.intent.json'), DESCRIPTOR))
    repo = 'coyotte508/powergrid-ai-germany-v1'; api = HfApi()
    assert api.repo_info(repo).private and 'archives/'+OUT.name+'.tgz' not in api.list_repo_files(repo)
    helper = ROOT/'ai/strong/recover-conservative-auction-cpu-v2.py'
    spec = importlib.util.spec_from_file_location('original_cpu_recovery', helper)
    recovery = importlib.util.module_from_spec(spec); spec.loader.exec_module(recovery)
    with contextlib.redirect_stdout(io.StringIO()): observed = recovery.target('inspect')
    assert observed['command_matches'] or (observed['status']['stage'] == 'completed' and observed['status']['passed'])
    assert '8840U' in observed['status']['processor']
    reference = recovery.OUT; status = read(reference/'status.json')
    assert status['passed'] and status['completed_requests'] == 300 and status['new_requests'] == 27
    assert status['counts'].get('rollout_caps', 0) == 0
    assert all(digest(reference/name) == sha for name, sha in status['output_hashes'].items())
    assert not (Path('/proc')/str(status['pid'])/'cmdline').exists()
    guard = ROOT/'ai/strong/conservative-auction-8840u-launch-v2.json'
    assert read(guard)['local_status_sha256'] == digest(reference/'status.json')
    paths = {p for p in reference.iterdir() if p.is_file()}
    paths.update((Path(__file__), helper, guard, recovery.GUARD,
        ROOT/'ai/strong/test_conservative_auction_cpu_recovery_v2.py',
        ROOT/'ai/strong/conservative-auction-cpu-recovery-evidence-v2.json',
        ROOT/'ai/strong/conservative-auction-cpu-readiness-v2.json',
        ROOT/'ai/strong/analyze_conservative_auction_cpu_v2.py',
        ROOT/'ai/strong/test_conservative_auction_cpu_analysis_v2.py',
        ROOT/'ai/runs/conservative-auction-cpu-recovery-tests-v2.log',
        ROOT/'ai/runs/conservative-auction-cpu-analysis-tests-v2.log',
        recovery.PREP/'prepared.json', recovery.PREP/'local-recovery.log',
        ROOT/'ai/RESUME.md', ROOT/'ai/CONSERVATIVE-AUCTION-CPU-2026-10-27.md'))
    owner = read(ROOT/'ai/runs/conservative-auction-development-coordinator-recovery-v2/state.json')
    assert all(digest(ROOT/name) == sha for name, sha in owner['code_hashes'].items())
    checkpoint = {'created_at': datetime.now(timezone.utc).isoformat(), 'target': observed,
        'local_reference': status, 'local_reference_sha256': digest(reference/'status.json'),
        'target_guard': read(guard), 'owner_snapshot': owner,
        'source_recovery': 'Use immutable artifact source and benchmark additions from conservative-auction-cpu-readiness-v2; complete local reference is contained here.',
        'new_hf_jobs': 0, 'new_strength_games': 0, 'qualified': False, 'reserved_final_seeds_used': False}
    OUT.mkdir(); hashes = {}
    for path in sorted(paths):
        name = str(path.relative_to(ROOT)); target = OUT/name; target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target); hashes[name] = digest(path); assert digest(target) == hashes[name]
    write(OUT/'checkpoint.json', checkpoint); hashes['checkpoint.json'] = digest(OUT/'checkpoint.json')
    write(OUT/'manifest.json', hashes)
    with OUT.with_suffix('.intent.json').open('x') as stream: json.dump({'manifest_sha256': digest(OUT/'manifest.json'), 'archive_path': 'archives/'+OUT.name+'.tgz'}, stream)
    evidence = upload_evidence(OUT)
    write(DESCRIPTOR, {'local_reference_complete': True, 'target_launch_verified': True,
        'archive': evidence, 'checkpoint': checkpoint, 'full_cross_host_parity_verified': False,
        'qualification_eligible': False, 'reserved_final_seeds_used': False})
    print(json.dumps(evidence), flush=True)


if __name__ == '__main__': main()
