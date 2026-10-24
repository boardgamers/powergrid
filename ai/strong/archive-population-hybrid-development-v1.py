"""Archive the complete fixed comparison; never launch jobs or select a policy.

Without --execute, only report readiness. An incomplete comparison is rejected
before creating an archive directory, downloading evidence, or reproducing scores.
"""
import argparse
from datetime import datetime, timezone
import fcntl
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from huggingface_hub import hf_hub_download
from policy_iteration_evidence_archive import upload_evidence
from population_hybrid_development import PLAN, PROTOCOL, SOURCE, validate_plan
from population_policy_verification import extract_verified
from strategic_collection import ROOT, read, write, digest

STRONG = ROOT / 'ai/strong'
COORDINATOR = ROOT / 'ai/runs/population-hybrid-development-coordinator-v1'
COMPARISON = STRONG / 'population-hybrid-development-comparison-v1.json'
OUTPUT = ROOT / 'ai/runs/population-hybrid-development-complete-evidence-v1'
DESCRIPTOR = STRONG / (OUTPUT.name + '.json')
RECOVERY = STRONG / 'population-hybrid-recovery-completion-evidence-v1.json'
PARITY = ROOT / 'ai/runs/population-hybrid-storage-recovery-v1/repeated-games-verified.json'


def require_complete():
    state = read(COORDINATOR / 'state.json')
    assert state['stage'] == 'comparison_complete', 'Fixed comparison is not complete'
    plan, protocol, source = read(PLAN), read(PROTOCOL), read(SOURCE)
    validate_plan(plan, protocol)
    assert state['jobs_submitted'] == state['jobs_verified'] == len(plan['shards']) == 135
    assert state['failed_jobs'] == []
    assert state['plan_sha256'] == digest(PLAN)
    assert state['code_hashes'] == plan['dependency_hashes']
    assert all(digest(ROOT / name) == sha for name, sha in plan['dependency_hashes'].items())
    assert plan['source'] == source and plan['protocol_sha256'] == digest(PROTOCOL)
    comparison = read(COMPARISON)
    assert state['comparison_sha256'] == digest(COMPARISON)
    assert comparison['complete'] is True and comparison['games'] == 8400
    assert comparison['plan_sha256'] == digest(PLAN) and comparison['protocol_sha256'] == digest(PROTOCOL)
    assert comparison['source'] == source and comparison['independent_deals_per_cell'] == 4
    assert comparison['candidate_selected'] is False
    assert comparison['qualification_eligible'] is comparison['reserved_final_seeds_used'] is False
    assert set(comparison['provenance']) == {row['case'] for row in plan['shards']}
    return state, plan, comparison


def archive():
    state, plan, comparison = require_complete()
    assert not OUTPUT.exists() and not OUTPUT.with_suffix('.tgz').exists() and not DESCRIPTOR.exists(), \
        'Inspect any previous archive/upload outcome before retrying'
    spec = importlib.util.spec_from_file_location('hybrid_archive_manager', STRONG / 'manage-population-hybrid-development.py')
    manager = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(manager)
    assert {p.stem for p in manager.GUARDS.glob('*.json')} == set(comparison['provenance'])
    receipts = {}
    for row in plan['shards']:
        case = row['case']
        receipt = manager.verified_receipt(case)
        assert receipt is not None and receipt['summary']['counts']['rollout_caps'] == 0
        assert comparison['provenance'][case] == {
            'job_id': receipt['job_id'],
            'verified_sha256': digest(manager.COLLECTED / case / 'verified.json'),
            'evidence': receipt['evidence']}
        receipts[case] = receipt
    assert len({r['job_id'] for r in receipts.values()}) == 135
    assert sum(r['summary']['games'] for r in receipts.values()) == 8400

    with tempfile.TemporaryDirectory(prefix='powergrid-hybrid-archive-') as temporary:
        temporary = Path(temporary)
        # The frozen comparator repeats every artifact/decision check and every
        # paired contrast. It reads completed data; it generates no new games.
        reproduced = temporary / 'comparison.json'
        subprocess.run([sys.executable, str(STRONG / 'compare-population-hybrid-development.py'),
                        '--output', str(reproduced)], cwd=ROOT, check=True)
        assert read(reproduced) == comparison, 'Full comparison did not reproduce'

        recovery = read(RECOVERY)
        assert recovery['remote_archive_verified'] and recovery['plan_sha256'] == digest(PLAN)
        pinned = Path(hf_hub_download(recovery['repo'], recovery['archive_path'], revision=recovery['revision']))
        checked = extract_verified(pinned, temporary / 'recovery')
        assert checked['archive_sha256'] == recovery['archive_sha256']
        assert checked['manifest_sha256'] == recovery['manifest_sha256']
        assert checked['files'] == recovery['archived_files']
        assert read(temporary / 'recovery/repeated-games-verified.json') == read(PARITY)
        recovered = {job['case'] for job in recovery['jobs']}
        assert recovered == {case for case in receipts if 'replaces_job_id' in read(manager.GUARDS / (case + '.json'))}
        for index, job in enumerate(recovery['jobs']):
            case = job['case']
            assert read(temporary / 'recovery' / f'guard-{index}.json') == read(manager.GUARDS / (case + '.json'))
            assert read(temporary / 'recovery' / f'verified-{index}.json') == receipts[case]

        # Do not snapshot a changed coordinator or frozen input after rechecking.
        assert require_complete() == (state, plan, comparison)
        OUTPUT.mkdir()
        def copy(path, target):
            assert path.is_file() and not path.is_symlink()
            destination = OUTPUT / target
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, destination)
            assert digest(destination) == digest(path)
        files = {ROOT / name for name in plan['dependency_hashes']}
        files.update([PLAN, COMPARISON, Path(__file__).resolve(), RECOVERY])
        for path in sorted(files):
            copy(path, path.relative_to(ROOT))
        write(OUTPUT / 'coordinator-state.json', state)
        shutil.copytree(temporary / 'recovery', OUTPUT / 'recovery-completion')
        for case, receipt in receipts.items():
            copy(manager.GUARDS / (case + '.json'), Path('guards') / (case + '.json'))
            base = manager.COLLECTED / case
            copy(base / 'verified.json', Path('collected') / case / 'verified.json')
            artifacts = base / 'artifacts'
            manifest = read(artifacts / 'manifest.json')
            assert digest(artifacts / 'manifest.json') == receipt['evidence']['manifest_sha256']
            assert {str(p.relative_to(artifacts)) for p in artifacts.rglob('*') if p.is_file()} == set(manifest) | {'manifest.json'}
            for name in [*manifest, 'manifest.json']:
                assert not Path(name).is_absolute() and '..' not in Path(name).parts
                if name != 'manifest.json':
                    assert digest(artifacts / name) == manifest[name]
                copy(artifacts / name, Path('collected') / case / 'artifacts' / name)

    review = {'checked_at': datetime.now(timezone.utc).isoformat(),
              'complete_development_comparison': True, 'comparison_reproduced': True,
              'comparison_sha256': digest(COMPARISON), 'plan_sha256': digest(PLAN),
              'collector_sha256': digest(Path(__file__)), 'batches': 135, 'games': 8400,
              'frozen_dependencies_checked': len(plan['dependency_hashes']),
              'storage_recovery_parity_preserved': True,
              'scope': comparison['scope'], 'new_jobs': 0, 'gradients': False,
              'candidate_selected': False, 'qualification_eligible': False,
              'reserved_final_seeds_used': False}
    write(OUTPUT / 'review.json', review)
    write(OUTPUT / 'manifest.json', {str(p.relative_to(OUTPUT)): digest(p)
                                    for p in sorted(OUTPUT.rglob('*')) if p.is_file()})
    result = {**review, **upload_evidence(OUTPUT)}
    write(DESCRIPTOR, result)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    if args.execute:
        # Reject incomplete/live work without touching the coordinator lock.
        require_complete()
        with (COORDINATOR / 'coordinator.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            archive()
    else:
        state = read(COORDINATOR / 'state.json')
        print(json.dumps({'execute': False, 'coordinator_stage': state['stage'],
                          'verified_batches': state['jobs_verified'],
                          'required_batches': 135, 'comparison_exists': COMPARISON.exists()}, indent=2))
