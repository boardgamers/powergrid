"""Freeze tested confirmation plumbing and archive it, without admitting jobs."""
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil

from huggingface_hub import HfApi
from public_policy_development_job_v1 import digest, read
from policy_iteration_evidence_archive import upload_evidence

ROOT = Path(__file__).resolve().parents[2]
NAME = 'current-auction-grid-readiness-evidence-v1'
OUT = ROOT / 'ai/runs' / NAME
READY = ROOT / 'ai/strong/current-auction-grid-readiness-v1.json'
RESULT = ROOT / 'ai/strong' / (NAME + '.json')
CODE = (
    'prepare-current-auction-grid-v1.py', 'manage-current-auction-grid-v1.py',
    'coordinate-current-auction-grid-v1.py', 'compare-current-auction-confirmation-v1.py',
    'current_auction_confirmation_analysis_v1.py',
    'test_current_auction_grid_plan_v1.py', 'test_current_auction_grid_manager_v1.py',
    'test_current_auction_grid_coordinator_v1.py', 'test_current_auction_comparison_v1.py',
    'test_current_auction_confirmation_analysis_v1.py',
    'manage-current-auction-runtime-v1.py', 'prepare-current-auction-confirmation-v1.py',
    'manage-conservative-auction-runtime-v2.py', 'prepare-conservative-auction-runtime-v2.py',
    'manage-public-policy-development-hf-v1.py', 'conservative_auction_bootstrap_recovery_v1.py',
    'public_policy_development_job_v1.py', 'public_policy_final_audit_v1.py', 'public_policy_final_contract_v1.py',
    'public_policy_arena_v1.py', 'public_policy_runtime_v1.py', 'population_policy_verification.py',
    'opponent_auction_verification_v1.py', 'opponent_auction_policy_v1.py',
    'current-auction-confirmation-protocol-v1.json', 'final-protocol-multiplayer.json')
TESTS = (
    ('current-auction-grid-plan-tests-v1-final.log', 6),
    ('current-auction-grid-manager-tests-v1-final.log', 7),
    ('current-auction-confirmation-analysis-tests-v1-first.log', 13),
    ('current-auction-comparison-tests-v1-corrected.log', 5),
    ('current-auction-grid-coordinator-tests-v1.log', 4))


def save(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False); stream.write('\n')


def main():
    for path in (OUT, OUT.with_suffix('.tgz'), OUT.with_suffix('.intent.json'), READY, RESULT):
        assert not path.exists(), 'Inspect prior readiness/archive outcome before retry'
    for filename, count in TESTS:
        text = (ROOT / 'ai/runs' / filename).read_text()
        assert f'Ran {count} tests' in text and text.rstrip().endswith('OK')
    progress = ROOT / 'ai/strong/current-auction-runtime-progress-v2.json'; snapshot = read(progress)
    assert snapshot['verified_jobs'] == 2 and snapshot['verified_games'] == 16
    assert snapshot['grid_admitted'] is False
    document = ROOT / 'ai/CURRENT-AUCTION-GRID-READINESS-2026-10-28.md'; assert document.is_file()
    for kind in ('plan', 'manager'):
        # Preserve first logs above and bind conventional admission log names to
        # the final tested code. No source/admission bundle exists at this point.
        assert not (ROOT / 'ai/runs/current-auction-grid-prepared-v1').exists()
        old = ROOT / f'ai/runs/current-auction-grid-{kind}-tests-v1.log'
        final = ROOT / f'ai/runs/current-auction-grid-{kind}-tests-v1-final.log'
        if old.exists():
            backup = old.with_name(old.stem + '-before-readiness.log')
            if backup.exists():
                # Inspected initial preflight failure normalized logs only;
                # preserve both originals and require the already-copied bytes.
                failure = ROOT / 'ai/runs/current-auction-readiness-archive-preflight-failure-v1'
                assert (failure / 'diagnosis.txt').is_file()
                assert digest(old) == digest(final)
            else:
                shutil.copyfile(old, backup)
        shutil.copyfile(final, old)
    paths = [ROOT / 'ai/strong' / name for name in CODE]
    paths += [ROOT / 'ai/runs' / name for name, _ in TESTS]
    paths += [ROOT / f'ai/runs/current-auction-grid-{kind}-tests-v1.log' for kind in ('plan','manager')]
    inputs = {str(p.relative_to(ROOT)): digest(p) for p in paths}
    protocol = read(ROOT / 'ai/strong/current-auction-confirmation-protocol-v1.json')
    assert protocol['planned_games_total'] == 26880 and protocol['independent_deals_per_count'] == 32
    ready = {'passed': True, 'created_at': datetime.now(timezone.utc).isoformat(),
        'scope': 'Tested schedule, resource admission, source manager, owner and full comparison. Not runtime admission or playing-strength evidence.',
        'tests': 35, 'test_suites': {name: count for name, count in TESTS}, 'input_hashes': inputs,
        'planned_confirmation_games': 26880, 'independent_deals_per_count': 32,
        'original_pilots_verified_at_snapshot': 2, 'original_pilot_games_verified_at_snapshot': 16,
        'pilot_snapshot_sha256': digest(progress), 'initial_test_harness_failure_preserved': True,
        'source_prepared': False, 'grid_admitted': False, 'owner_started': False,
        'new_hf_jobs': 0, 'new_games': 0, 'new_inference': 0, 'new_gradients': 0,
        'qualification_eligible': False, 'reserved_final_seeds_used': False}
    save(READY, ready)
    sources = set(paths) | {Path(__file__).resolve(), READY, progress, document, ROOT / 'ai/RESUME.md'}
    sources.update(ROOT / p for p in ('ai/strong/current-engine-auction-evidence-v2.json',
        'ai/strong/current-auction-runtime-source-v1.json', 'ai/strong/current-auction-runtime-launch-evidence-v1.json',
        'ai/strong/policy_iteration_evidence_archive.py', 'ai/strong/strategic_collection.py',
        'ai/runs/current-auction-runtime-collection-v1-third.log', 'ai/runs/current-auction-runtime-collection-v1-fourth.log',
        'ai/runs/current-auction-runtime-collection-v1-fifth.log',
        'ai/runs/current-auction-grid-plan-tests-v1-before-readiness.log',
        'ai/runs/current-auction-grid-manager-tests-v1-before-readiness.log'))
    failure = ROOT / 'ai/runs/current-auction-comparison-test-failure-v1'
    sources.update(p for p in failure.rglob('*') if p.is_file())
    preflight_failure = ROOT / 'ai/runs/current-auction-readiness-archive-preflight-failure-v1'
    sources.update(p for p in preflight_failure.rglob('*') if p.is_file())
    for row in snapshot['verified']:
        sources.add(ROOT / 'ai/runs/current-auction-runtime-hf-v1' / row['name'] / 'verified.json')
    api = HfApi(); repo = 'coyotte508/powergrid-ai-germany-v1'
    assert api.model_info(repo).private and not api.file_exists(repo, 'archives/' + NAME + '.tgz')
    OUT.mkdir(); hashes = {}
    for p in sorted(sources):
        assert p.is_file() and not p.is_symlink()
        name = str(p.relative_to(ROOT)); target = OUT / name; target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(p.read_bytes()); hashes[name] = digest(target)
    save(OUT / 'manifest.json', hashes)
    intent = {'created_at': ready['created_at'], 'stage': 'prepared_for_upload', 'manifest_sha256': digest(OUT / 'manifest.json')}
    save(OUT.with_suffix('.intent.json'), intent)
    archive = upload_evidence(OUT)
    save(RESULT, {'passed': True, 'readiness_sha256': digest(READY), 'tests': 35,
        'pilot_snapshot_sha256': digest(progress), 'pilots_verified': 2, 'pilot_games_verified': 16,
        'grid_admitted': False, 'owner_started': False, 'new_hf_jobs': 0,
        'qualification_eligible': False, 'reserved_final_seeds_used': False, 'archive': archive})
    OUT.with_suffix('.intent.json').write_text(json.dumps({**intent, 'stage': 'uploaded_download_verified',
        'archive': archive, 'descriptor_sha256': digest(RESULT)}, indent=2) + '\n')
    print(json.dumps(archive), flush=True)


if __name__ == '__main__': main()
