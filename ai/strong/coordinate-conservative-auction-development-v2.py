"""Own original pilot collection and the bounded frozen development grid.

Start once. An interrupted/failed owner preserves state and job handles; it does
not retry itself. No model selection, training, final games or deployment here.
"""
import argparse
from datetime import datetime, timezone
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import time

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'ai/runs/conservative-auction-development-coordinator-v2'
MODULES = ('coordinate-conservative-auction-development-v2.py',
    'prepare-conservative-auction-development-v2.py', 'manage-conservative-auction-development-v2.py',
    'manage-conservative-auction-runtime-v2.py', 'prepare-conservative-auction-runtime-v2.py',
    'manage-public-policy-development-hf-v1.py', 'public_policy_development_job_v1.py',
    'public_policy_final_audit_v1.py', 'public_policy_final_contract_v1.py',
    'public_policy_arena_v1.py', 'public_policy_runtime_v1.py', 'opponent_auction_verification_v1.py',
    'opponent_auction_policy_v1.py', 'population_policy_verification.py',
    'conservative-auction-development-protocol-v2.json',
    'test_conservative_auction_development_plan_v2.py', 'test_conservative_auction_development_manager_v2.py',
    'test_conservative_auction_development_coordinator_v2.py',
    'opponent_surrogate_policy_v1.py', 'surrogate-opponent-continuations-v1.cjs',
    'surrogate_opponent_continuations_v1.py', 'surrogate_continuation_study_v1.py')


def digest(path):
    with Path(path).open('rb') as stream: return hashlib.file_digest(stream, 'sha256').hexdigest()


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(filename))
    value = importlib.util.module_from_spec(spec); spec.loader.exec_module(value); return value


def now(): return datetime.now(timezone.utc).isoformat()


def write_state(state, **values):
    state.update(values, updated_at=now())
    tmp = OUT/'state.tmp'; tmp.write_text(json.dumps(state, indent=2, allow_nan=False)+'\n')
    tmp.replace(OUT/'state.json')
    print(json.dumps({k: state[k] for k in ('updated_at', 'stage', 'pilots_verified', 'development_verified',
                        'development_expected', 'development_submitted') if k in state}), flush=True)


def check_pins(state):
    assert all(digest(ROOT/name) == sha for name, sha in state['code_hashes'].items()), 'Code changed; inspect original owner'
    if (OUT/'STOP').exists(): raise KeyboardInterrupt('Explicit local stop marker')


def stop(signum, frame):
    raise KeyboardInterrupt(f'Owner interrupted by signal {signum}; preserve original submissions')


def development_tick(manager, state):
    # Audit finished originals before spending another batch's compute. An
    # invalid receipt or failed original stops here without new submissions.
    check_pins(state)
    collected = manager.collect()
    write_state(state, stage='audited_original_development_jobs', development_verified=collected['verified_jobs'])
    if collected['complete']: return True
    check_pins(state)
    launched = manager.launch(execute=True, limit=64)
    submitted = len(list(manager.OUT.glob('*/launch.json')))
    write_state(state, stage='waiting_for_original_development_jobs', development_submitted=submitted,
                active_at_submission=launched['active_jobs'])
    return False


def main():
    parser = argparse.ArgumentParser(__doc__); parser.add_argument('--start', action='store_true', required=True)
    parser.parse_args(); OUT.mkdir(parents=True, exist_ok=True)
    with (OUT/'.owner.lock').open('a') as owner:
        fcntl.flock(owner, fcntl.LOCK_EX | fcntl.LOCK_NB)
        assert not (OUT/'state.json').exists(), 'Inspect original owner; no automatic restarts'
        signal.signal(signal.SIGTERM, stop); signal.signal(signal.SIGINT, stop)
        pins = {str((ROOT/'ai/strong'/name).relative_to(ROOT)): digest(ROOT/'ai/strong'/name) for name in MODULES}
        state = {'pid': os.getpid(), 'started_at': now(), 'stage': 'starting', 'code_hashes': pins,
            'pilots_verified': 0, 'development_verified': 0, 'development_submitted': 0,
            'new_gradients': 0, 'qualified': False, 'reserved_final_seeds_used': False,
            'max_active_development_jobs': 64, 'automatic_restarts': False}
        write_state(state)
        try:
            for name in ('plan', 'manager'):
                log = ROOT/f'ai/runs/conservative-auction-development-{name}-tests-v2.log'
                assert 'Ran 5 tests' in log.read_text() and log.read_text().rstrip().endswith('OK')
            log = ROOT/'ai/runs/conservative-auction-development-coordinator-tests-v2.log'
            assert 'Ran 3 tests' in log.read_text() and log.read_text().rstrip().endswith('OK')
            manager = load('coordinated_development', 'manage-conservative-auction-development-v2.py')
            pilot = manager.pilots
            source = pilot.source_checked()
            state['original_pilots'] = [pilot.read(pilot.OUT/r['name']/'launch.json')['job_id'] for r in source['rows']]
            assert len(set(state['original_pilots'])) == 4
            while True:
                check_pins(state); result = pilot.collect()
                write_state(state, stage='waiting_for_original_pilots', pilots_verified=result['verified_jobs'])
                if result['complete']: break
                time.sleep(45)
            check_pins(state); write_state(state, stage='preparing_development_source')
            assert not manager.LOCAL.exists() and not manager.OUT.exists(), 'Inspect prior source preparation instead of replacing it'
            manager.planning.prepare()
            check_pins(state); manager.prepare()
            check_pins(state); write_state(state, stage='uploading_development_source'); manager.upload()
            source = manager.source_checked()
            write_state(state, stage='development_admitted', development_expected=len(source['rows']),
                        development_source_sha256=digest(manager.SOURCE))
            while True:
                if development_tick(manager, state): break
                time.sleep(45)
            check_pins(state)
            write_state(state, stage='complete', result_sha256=digest(manager.RESULT),
                        completed_games=10080, next_action='Archive and compare complete fresh outcomes; no automatic selection or qualification')
        except BaseException as error:
            write_state(state, stage='stopped_for_inspection', failure_type=type(error).__name__,
                        failure=str(error), next_action='Inspect original evidence and handles; do not restart or resubmit blindly')
            raise


if __name__ == '__main__': main()
