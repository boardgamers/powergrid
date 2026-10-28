"""Collect the four original current-engine runtime pilots and exit.

No submissions, retries, source preparation, training or policy selection.
The confirmation grid still requires a separate complete-cost review.
"""
from datetime import datetime, timezone
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import signal
import time

from huggingface_hub import HfApi
from public_policy_development_job_v1 import digest, read

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'ai/runs/current-auction-runtime-finish-v1'
IDS = {
    'pg-current-auction-runtime-v1-filter-2p': '6ae2733541e90535df77d71e',
    'pg-current-auction-runtime-v1-filter-6p': '6ae273363fb22a235dd4a65d',
    'pg-current-auction-runtime-v1-pop-2p': '6ae2733641e90535df77d722',
    'pg-current-auction-runtime-v1-pop-6p': '6ae273363fb22a235dd4a660',
}


def now(): return datetime.now(timezone.utc).isoformat()


def save(state, **updates):
    state.update(updates, updated_at=now())
    temporary = OUT / 'state.tmp'
    temporary.write_text(json.dumps(state, indent=2, allow_nan=False) + '\n')
    temporary.replace(OUT / 'state.json')
    print(json.dumps({k: state[k] for k in ('updated_at', 'stage', 'verified_jobs', 'live_statuses')
                      if k in state}), flush=True)


def stop(signum, frame):
    raise KeyboardInterrupt(f'Collector interrupted by signal {signum}')


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / '.owner.lock').open('a') as owner:
        fcntl.flock(owner, fcntl.LOCK_EX | fcntl.LOCK_NB)
        assert not (OUT / 'state.json').exists() and not (OUT / 'STOP').exists(), 'Inspect original collector before restarting'
        ready_path = ROOT / 'ai/strong/current-auction-grid-readiness-v1.json'
        ready = read(ready_path); assert ready['passed']
        pins = {**ready['input_hashes'], str(ready_path.relative_to(ROOT)): digest(ready_path),
                str(Path(__file__).resolve().relative_to(ROOT)): digest(__file__)}
        spec = importlib.util.spec_from_file_location('original_current_runtime',
                    Path(__file__).with_name('manage-current-auction-runtime-v1.py'))
        manager = importlib.util.module_from_spec(spec); spec.loader.exec_module(manager)
        source = manager.source_checked()
        assert {r['name']: read(manager.OUT / r['name'] / 'launch.json')['job_id'] for r in source['rows']} == IDS
        pins[str(manager.SOURCE.relative_to(ROOT))] = digest(manager.SOURCE)
        for name in IDS:
            path = manager.OUT / name / 'launch.json'; pins[str(path.relative_to(ROOT))] = digest(path)
        state = {'pid': os.getpid(), 'started_at': now(), 'original_jobs': IDS, 'code_and_input_hashes': pins,
                 'new_jobs': 0, 'automatic_restarts': False, 'grid_admitted': False,
                 'goal_status': 'active', 'qualified': False, 'reserved_final_seeds_used': False}

        def check():
            assert all(digest(ROOT / name) == sha for name, sha in pins.items()), 'Inputs changed'
            if (OUT / 'STOP').exists(): raise KeyboardInterrupt('Explicit stop marker')
            assert not (ROOT / 'ai/strong/current-auction-grid-source-v1.json').exists(), 'Grid admission requires finished collector'
            assert not (ROOT / 'ai/runs/current-auction-grid-coordinator-v1/state.json').exists()

        signal.signal(signal.SIGTERM, stop); signal.signal(signal.SIGINT, stop)
        save(state, stage='checking_original_pilots')
        try:
            check()
            result = manager.collect()
            while not result['complete']:
                check()
                pending = {name: handle for name, handle in IDS.items()
                           if not (manager.OUT / name / 'verified.json').exists()}
                statuses = {name: HfApi().inspect_job(job_id=handle).status.stage for name, handle in pending.items()}
                # A terminal original triggers the tested collector. Failures and
                # missing/ambiguous receipts stop it; nothing is resubmitted.
                if any(stage not in ('SCHEDULING', 'RUNNING') for stage in statuses.values()):
                    result = manager.collect()
                save(state, stage='waiting_for_original_pilots', live_statuses=statuses,
                     verified_jobs=result['verified_jobs'])
                if result['complete']: break
                time.sleep(60)
            check()
            save(state, stage='complete', verified_jobs=4, completed_games=64,
                 result_sha256=digest(manager.RESULT),
                 next_action='Review all four complete runtime costs before separately preparing the fixed confirmation grid.')
        except BaseException as error:
            save(state, stage='stopped_for_inspection', failure_type=type(error).__name__, failure=str(error),
                 next_action='Inspect original handles and preserved evidence. No automatic restart or resubmission.')
            raise


if __name__ == '__main__': main()
