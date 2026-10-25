"""Collect only the four already-submitted runtime pilots, then exit.

No training, submissions, restarts, development admission or deployment. The
broader development owner must be stopped with its STOP marker intact.
"""
from datetime import datetime, timezone
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import time

from huggingface_hub import HfApi

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'ai/runs/conservative-auction-runtime-finish-v1'
OWNER = ROOT / 'ai/runs/conservative-auction-development-coordinator-v1'
IDS = {
    'conservative-auction-runtime-v1-conservative_population-2p': '6addea031e112550ce7eaa88',
    'conservative-auction-runtime-v1-conservative_population-6p': '6addea031e112550ce7eaa8a',
    'conservative-auction-runtime-v1-conservative_dual-2p': '6addea04046eb82b1ece4faf',
    'conservative-auction-runtime-v1-conservative_dual-6p': '6addea04046eb82b1ece4fb1',
}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(state, **updates):
    state.update(updates, updated_at=datetime.now(timezone.utc).isoformat())
    tmp = OUT / 'state.tmp'
    tmp.write_text(json.dumps(state, indent=2) + '\n')
    tmp.replace(OUT / 'state.json')
    print(json.dumps({k: state[k] for k in ('updated_at', 'stage', 'verified_jobs', 'statuses') if k in state}), flush=True)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / '.owner.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        assert not (OUT / 'state.json').exists(), 'Inspect the original collector before starting another'
        stopped = json.loads((OWNER / 'state.json').read_text())

        def check():
            assert (OWNER / 'STOP').exists()
            assert stopped['stage'] == 'stopped_for_inspection'
            assert stopped['development_submitted'] == 0
            proc = Path('/proc') / str(stopped['pid']) / 'cmdline'
            assert not proc.exists() or b'coordinate-conservative-auction-development-v1.py' not in proc.read_bytes()
            assert all(digest(ROOT / name) == sha for name, sha in stopped['code_hashes'].items())
            assert not (ROOT / 'ai/strong/conservative-auction-development-source-v1.json').exists()

        check()
        spec = importlib.util.spec_from_file_location('original_runtime', Path(__file__).with_name('manage-conservative-auction-runtime-v1.py'))
        manager = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(manager)
        source = manager.source_checked()
        assert {row['name']: manager.read(manager.OUT / row['name'] / 'launch.json')['job_id'] for row in source['rows']} == IDS
        state = {'pid': os.getpid(), 'original_jobs': IDS, 'new_jobs': 0, 'goal_paused': True,
                 'development_owner_stopped': True, 'source_sha256': digest(manager.SOURCE)}
        save(state, stage='collecting_original_pilots')
        try:
            result = manager.collect()
            while not result['complete']:
                check()
                statuses = {name: HfApi().inspect_job(job_id=job_id).status.stage for name, job_id in IDS.items()}
                changed = statuses != state.get('statuses')
                if changed:
                    result = manager.collect()
                    save(state, stage='waiting_for_original_pilots', statuses=statuses, verified_jobs=result['verified_jobs'])
                if result['complete']:
                    break
                time.sleep(60)
            check()
            save(state, stage='complete', verified_jobs=4, completed_games=64,
                 result_sha256=digest(manager.RESULT), next_action='Archive results and finish paused handoff; do not start development jobs')
        except BaseException as error:
            save(state, stage='stopped_for_inspection', failure_type=type(error).__name__, failure=str(error),
                 next_action='Inspect original handles and evidence; no automatic restart or resubmission')
            raise


if __name__ == '__main__':
    main()
