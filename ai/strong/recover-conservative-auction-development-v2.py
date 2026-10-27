"""Reviewed one-shot recovery after the original waiting owner received SIGTERM.

Preserve the original owner state; reuse its tested coordinator unchanged under
a new owner directory. No replacement jobs and no recovery of ambiguous launches.
"""
import fcntl
import importlib.util
import json
from pathlib import Path

from huggingface_hub import HfApi
from public_policy_development_job_v1 import read, digest

ROOT = Path(__file__).resolve().parents[2]
OLD = ROOT/'ai/runs/conservative-auction-development-coordinator-v2'
OUT = ROOT/'ai/runs/conservative-auction-development-coordinator-recovery-v2'
STOPPED_SHA = 'd5f5ebcae52ffd0b2f4b35c3279fb8440cad91da96a670b492e6b46c6a79ce51'
HANDLES = ['6ae0fa243fb22a235dd31616', '6ae0fa2541e90535df7674df',
           '6ae0fa2541e90535df7674e1', '6ae0fa2541e90535df7674e3']


def admit(state, state_sha, process_live, stop_present, development_exists, statuses):
    assert state_sha == STOPPED_SHA, 'Inspect changed original owner state'
    assert state['pid'] == 1685160 and state['stage'] == 'stopped_for_inspection'
    assert state['failure_type'] == 'KeyboardInterrupt' and state['failure'] == 'Owner interrupted by signal 15; preserve original submissions'
    assert state['original_pilots'] == HANDLES and state['development_submitted'] == 0
    assert not process_live and not stop_present and not development_exists, 'Do not recover a live/stopped-by-marker/partially-submitted owner'
    assert set(statuses) == set(HANDLES) and all(s in ('RUNNING', 'COMPLETED') for s in statuses.values()), 'Inspect failed or ambiguous original pilots'


def main():
    assert not OUT.exists(), 'Inspect original recovery owner; never restart automatically'
    with (OLD/'.owner.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        state = read(OLD/'state.json'); proc = Path('/proc')/str(state['pid'])/'cmdline'
        live = proc.exists() and b'coordinate-conservative-auction-development-v2.py' in proc.read_bytes()
        statuses = {j: HfApi().inspect_job(job_id=j).status.stage for j in HANDLES}
        development_exists = any((ROOT/p).exists() for p in (
            'ai/runs/conservative-auction-development-prepared-v2', 'ai/runs/conservative-auction-development-hf-v2',
            'ai/strong/conservative-auction-development-source-v2.json'))
        admit(state, digest(OLD/'state.json'), live, (OLD/'STOP').exists(), development_exists, statuses)
        assert all(digest(ROOT/name) == sha for name, sha in state['code_hashes'].items())
        tests = (ROOT/'ai/runs/conservative-auction-owner-recovery-tests-v2.log').read_text()
        assert 'Ran 3 tests' in tests and tests.rstrip().endswith('OK')
        path = Path(__file__).with_name('coordinate-conservative-auction-development-v2.py')
        spec = importlib.util.spec_from_file_location('original_tested_coordinator', path)
        coordinator = importlib.util.module_from_spec(spec); spec.loader.exec_module(coordinator)
        coordinator.OUT = OUT
        coordinator.MODULES += (Path(__file__).name, 'test_conservative_auction_owner_recovery_v2.py')
        OUT.mkdir()
        with (OUT/'predecessor.json').open('x') as stream:
            json.dump({'original_owner_state': state, 'original_state_sha256': STOPPED_SHA,
                'original_statuses_at_recovery': statuses, 'original_owner_absent': True,
                'reviewed_reason': 'SIGTERM while waiting; no STOP marker, no execution/audit failure, no development preparation/submission.',
                'authorization': 'Active human-resumed research goal; reuse original jobs and all existing admission gates.',
                'replacement_jobs': 0}, stream, indent=2)
        coordinator.main()  # Existing --start argument, same guards and no automatic retries.


if __name__ == '__main__': main()
