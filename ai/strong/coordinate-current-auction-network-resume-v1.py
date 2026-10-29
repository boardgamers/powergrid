"""Deliberately resume the unchanged confirmation after an inspected DNS failure.

Preserve the stopped owner. Reuse its frozen collection/launch implementation,
which collects originals before submitting never-submitted rows. No job retries,
automatic restarts, changed policies, partial selection or reserved games.
"""
import argparse
from contextlib import ExitStack
import fcntl
import importlib.util
import os
from pathlib import Path
import signal
import time

from public_policy_development_job_v1 import digest, read

ROOT = Path(__file__).resolve().parents[2]
REVIEW = ROOT / 'ai/strong/current-auction-network-resume-review-v1.json'
OUT = ROOT / 'ai/runs/current-auction-network-resume-v1'
OLD_OUT = ROOT / 'ai/runs/current-auction-confirmation-recovery-v1'


def original_owner():
    path = Path(__file__).with_name('coordinate-current-auction-confirmation-recovery-v1.py')
    spec = importlib.util.spec_from_file_location('frozen_confirmation_owner', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def checked_review(manager):
    review = read(REVIEW)
    assert review['ready_for_deliberate_resume'] and review['original_jobs_only']
    assert not review['automatic_restarts'] and not review['reserved_final_seeds_used']
    assert all(digest(ROOT / n) == sha for n, sha in review['input_hashes'].items())
    old = read(OLD_OUT / 'state.json')
    assert old['stage'] == 'stopped_for_inspection'
    assert old['failure_type'] == 'ConnectError'
    assert old['failure'] == '[Errno -2] Name or service not known'
    assert not Path(f"/proc/{old['pid']}").exists(), 'Prior owner must have exited'
    assert not (OLD_OUT / 'STOP').exists(), 'Respect any explicit pause'
    assert all(digest(ROOT / n) == sha for n, sha in old['code_hashes'].items())
    guards = {str(p.relative_to(ROOT)): digest(p) for p in manager.OUT.glob('*/launch.json')}
    assert guards == review['original_guard_hashes'], 'Reconcile changed/unknown submissions'
    assert all(read(ROOT / n)['stage'] == 'launched' for n in guards), 'Ambiguous submission'
    handles = [read(ROOT / n)['job_id'] for n in guards]
    assert len(handles) == len(set(handles)) == review['submitted_jobs']
    assert set(handles) == set(review['original_handles'])
    initial = read(ROOT / review['initial_collection'])
    assert initial['verified_jobs'] == len(initial['jobs']) == review['audited_jobs']
    assert {j['job_id'] for j in initial['jobs']} <= set(handles)
    assert all(manager.recovery.complete_data(j) for j in initial['jobs'])
    manager.admitted()
    source = manager.source_checked()
    assert source['games'] == 26880 and len(source['rows']) == 944
    assert source['max_active_jobs'] == 64
    return review, old


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--start-reviewed', action='store_true', required=True)
    parser.parse_args()
    owner = original_owner()
    manager = owner.manager_module()
    with ExitStack() as stack:
        # Keep the original owner's lock as well: no competing original owner.
        old_lock = stack.enter_context((OLD_OUT / '.owner.lock').open('a'))
        fcntl.flock(old_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        review, old = checked_review(manager)
        OUT.mkdir(parents=True, exist_ok=True)
        new_lock = stack.enter_context((OUT / '.owner.lock').open('a'))
        fcntl.flock(new_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        assert not (OUT / 'state.json').exists() and not (OUT / 'STOP').exists(), 'Inspect existing owner; never automatically restart'
        owner.OUT = OUT
        signal.signal(signal.SIGTERM, owner.stop)
        signal.signal(signal.SIGINT, owner.stop)
        pins = {**old['code_hashes'], **review['input_hashes'],
                **review['original_guard_hashes'],
                str(REVIEW.relative_to(ROOT)): digest(REVIEW),
                str(Path(__file__).resolve().relative_to(ROOT)): digest(__file__)}
        state = {'pid': os.getpid(), 'started_at': owner.now(),
                 'stage': 'starting_reviewed_network_resumption', 'code_hashes': pins,
                 'source_sha256': old['source_sha256'], 'expected_jobs': 944,
                 'verified_jobs': review['audited_jobs'], 'submitted_jobs': review['submitted_jobs'],
                 'max_active_jobs': 64, 'automatic_restarts': False,
                 'recovery_rule': old['recovery_rule'], 'previous_owner_pid': old['pid'],
                 'new_gradients': 0, 'qualified': False, 'reserved_final_seeds_used': False}
        owner.write_state(state)
        try:
            while True:
                if (OLD_OUT / 'STOP').exists():
                    raise KeyboardInterrupt('Explicit stop marker on previous owner')
                if owner.tick(manager, state):
                    break
                time.sleep(45)
            owner.check_pins(state)
            owner.write_state(state, stage='complete', result_sha256=digest(manager.RESULT),
                              completed_games=26880,
                              next_action='Independently audit the complete grid before selection. No automatic final qualification.')
        except BaseException as error:
            owner.write_state(state, stage='stopped_for_inspection',
                              failure_type=type(error).__name__, failure=str(error),
                              next_action='Inspect original handles/state; no automatic retry or restart.')
            raise


if __name__ == '__main__':
    main()
