"""Snapshot tested development tooling and the original live coordinator."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil

from huggingface_hub import HfApi
from policy_iteration_evidence_archive import upload_evidence
from public_policy_development_job_v1 import read, write, digest

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'ai/runs/conservative-auction-development-readiness-v1'
DESCRIPTOR = ROOT/'ai/strong/conservative-auction-development-readiness-v1.json'
OWNER = ROOT/'ai/runs/conservative-auction-development-coordinator-v1/state.json'
PILOTS = ROOT/'ai/runs/conservative-auction-runtime-hf-v1'


def main():
    parser = argparse.ArgumentParser(__doc__); parser.add_argument('--archive', action='store_true', required=True)
    parser.parse_args(); assert not any(p.exists() for p in (OUT, OUT.with_suffix('.tgz'), DESCRIPTOR))
    owner = read(OWNER); process = Path('/proc')/str(owner['pid'])/'cmdline'
    assert process.exists() and b'coordinate-conservative-auction-development-v1.py' in process.read_bytes()
    assert all(digest(ROOT/name) == sha for name, sha in owner['code_hashes'].items())
    source_path = ROOT/'ai/strong/conservative-auction-runtime-source-v1.json'; source = read(source_path)
    api = HfApi(); statuses = []; completed = []; paths = {ROOT/name for name in owner['code_hashes']}
    for row in source['rows']:
        folder = PILOTS/row['name']; guard = read(folder/'launch.json')
        statuses.append({'name': row['name'], 'job_id': guard['job_id'],
                         'stage': api.inspect_job(job_id=guard['job_id']).status.stage})
        paths.add(folder/'launch.json')
        if (folder/'verified.json').exists():
            result = read(folder/'verified.json'); paths.add(folder/'verified.json')
            assert result['verified'] and result['review']['audit']['counts']['rollout_caps'] == 0
            completed.append({'name': row['name'], 'job_id': guard['job_id'], 'games': result['review']['games'],
                'measurement': result['review']['measurement'], 'counts': result['review']['audit']['counts'],
                'evidence': result['evidence']})
    for name in ('plan', 'manager'):
        path = ROOT/f'ai/runs/conservative-auction-development-{name}-tests-v1.log'
        assert 'Ran 5 tests' in path.read_text() and path.read_text().rstrip().endswith('OK'); paths.add(path)
    paths.update((Path(__file__), source_path, ROOT/'ai/strong/conservative-auction-runtime-launch-evidence-v1.json'))
    checkpoint = {'created_at': datetime.now(timezone.utc).isoformat(), 'original_owner': owner,
        'owner_verified_live': True, 'original_job_statuses': statuses, 'verified_pilots': completed,
        'schedule_games': 10080, 'schedule_batch_sizes_checked': [1, 2, 4, 8], 'tests_passed': 10,
        'actual_development_source_prepared': (ROOT/'ai/runs/conservative-auction-development-prepared-v1/prepared.json').exists(),
        'actual_development_source_uploaded': (ROOT/'ai/strong/conservative-auction-development-source-v1.json').exists(),
        'previous_goal_turn': 'progress: verified and launched four original runtime pilots',
        'current_goal_turn': 'progress: two pilot receipts audited; development scheduling/submission tooling tested; original owner started',
        'qualified': False, 'reserved_final_seeds_used': False}
    OUT.mkdir(); hashes = {}
    for path in sorted(paths):
        name = str(path.relative_to(ROOT)); dest = OUT/name; dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, dest); hashes[name] = digest(path); assert digest(dest) == hashes[name]
    write(OUT/'checkpoint.json', checkpoint); hashes['checkpoint.json'] = digest(OUT/'checkpoint.json')
    write(OUT/'manifest.json', hashes)
    print(json.dumps({'stage': 'uploading', 'files': len(hashes)+1}), flush=True)
    evidence = upload_evidence(OUT)
    write(DESCRIPTOR, {'readiness_evidence_complete': True, 'archive': evidence, 'checkpoint': checkpoint,
        'full_development_execution_verified': False, 'qualification_eligible': False, 'reserved_final_seeds_used': False})
    print(json.dumps(evidence), flush=True)


if __name__ == '__main__': main()
