"""Own an already admitted and uploaded confirmation grid; never admit pilots.

No automatic restart, retry, training, tuning, selection or reserved final games.
An interrupted owner leaves all original handles and state for explicit review.
"""
import argparse
from datetime import datetime, timezone
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import signal
import time

from public_policy_development_job_v1 import digest, read

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'ai/runs/current-auction-grid-coordinator-v1'
READINESS = ROOT / 'ai/strong/current-auction-grid-readiness-v1.json'


def manager_module():
    path = Path(__file__).with_name('manage-current-auction-grid-v1.py')
    spec = importlib.util.spec_from_file_location('admitted_confirmation_manager', path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module


def now(): return datetime.now(timezone.utc).isoformat()


def write_state(state, **values):
    state.update(values, updated_at=now())
    tmp = OUT / 'state.tmp'; tmp.write_text(json.dumps(state, indent=2, allow_nan=False) + '\n')
    tmp.replace(OUT / 'state.json')
    print(json.dumps({k: state[k] for k in ('updated_at', 'stage', 'verified_jobs', 'expected_jobs',
        'submitted_jobs', 'active_at_submission') if k in state}), flush=True)


def check_pins(state):
    assert all(digest(ROOT / name) == sha for name, sha in state['code_hashes'].items()), 'Execution code changed'
    if (OUT / 'STOP').exists(): raise KeyboardInterrupt('Explicit stop marker')


def stop(signum, frame):
    raise KeyboardInterrupt(f'Owner interrupted by signal {signum}; preserve original submissions')


def tick(manager, state):
    check_pins(state)
    collected = manager.collect()
    write_state(state, stage='originals_audited', verified_jobs=collected['verified_jobs'])
    if collected['complete']: return True
    check_pins(state)
    launched = manager.launch(execute=True, limit=64)
    write_state(state, stage='waiting_for_original_confirmation_jobs',
        submitted_jobs=len(list(manager.OUT.glob('*/launch.json'))), active_at_submission=launched['active_jobs'],
        awaiting_collection=launched.get('awaiting_collection', []))
    return False


def main():
    parser = argparse.ArgumentParser(__doc__); parser.add_argument('--start', action='store_true', required=True)
    parser.parse_args()
    readiness = read(READINESS)
    assert readiness['passed'] and all(digest(ROOT / n) == s for n, s in readiness['input_hashes'].items())
    manager = manager_module()
    # No owner/state is created until the complete-pilot source admission and
    # remote source verification have already happened outside this process.
    source = manager.source_checked()
    assert source['games'] == 26880 and source['max_active_jobs'] == 64
    assert read(manager.pilots.RESULT)['complete'] and read(manager.pilots.RESULT)['verified_jobs'] == 4
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / '.owner.lock').open('a') as owner:
        fcntl.flock(owner, fcntl.LOCK_EX | fcntl.LOCK_NB)
        assert not (OUT / 'state.json').exists() and not (OUT / 'STOP').exists(), 'Inspect original owner before any recovery'
        signal.signal(signal.SIGTERM, stop); signal.signal(signal.SIGINT, stop)
        pins = {**readiness['input_hashes'], str(READINESS.relative_to(ROOT)): digest(READINESS),
            str(manager.SOURCE.relative_to(ROOT)): digest(manager.SOURCE)}
        state = {'pid': os.getpid(), 'started_at': now(), 'stage': 'starting_admitted_grid',
            'code_hashes': pins, 'source_sha256': digest(manager.SOURCE), 'expected_jobs': len(source['rows']),
            'verified_jobs': 0, 'submitted_jobs': 0, 'max_active_jobs': 64, 'automatic_restarts': False,
            'new_gradients': 0, 'qualified': False, 'reserved_final_seeds_used': False}
        write_state(state)
        try:
            while True:
                if tick(manager, state): break
                time.sleep(45)
            check_pins(state)
            write_state(state, stage='complete', result_sha256=digest(manager.RESULT), completed_games=26880,
                next_action='Independently re-audit and compare all raw outcomes. No automatic policy selection or final qualification.')
        except BaseException as error:
            write_state(state, stage='stopped_for_inspection', failure_type=type(error).__name__, failure=str(error),
                next_action='Inspect original state, artifacts and handles. No automatic retry or restart.')
            raise


if __name__ == '__main__': main()
