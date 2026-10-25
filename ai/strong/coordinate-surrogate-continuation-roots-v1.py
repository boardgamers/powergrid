"""Drive the fixed fresh-root plan using original handles and an immutable code set."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import fcntl
import importlib.util
import os
from pathlib import Path
import time

from strategic_collection import ROOT, read, write, digest

spec = importlib.util.spec_from_file_location('root_collection_manager', Path(__file__).with_name('manage-surrogate-continuation-roots-v1.py'))
manager = importlib.util.module_from_spec(spec); spec.loader.exec_module(manager)
launcher = manager.launcher
OUT = ROOT/'ai/runs/surrogate-continuation-roots-coordinator-v1'


def dependencies():
    return {**manager.code_hashes(), str(Path(__file__).relative_to(ROOT)): digest(__file__)}


def cycle(plan, state, save):
    cases = [row['case'] for row in plan['shards']]
    guards = {path.stem: read(path) for path in launcher.GUARDS.glob('*.json')}
    assert set(guards) <= set(cases)
    assert all(g['stage'] == 'launched' and g['plan_sha256'] == digest(launcher.PLAN) for g in guards.values())
    assert len({g['job_id'] for g in guards.values()}) == len(guards)
    verified = {case for case in cases if manager.verified_receipt(case) is not None}; assert verified <= set(guards)
    with ThreadPoolExecutor(max_workers=4) as pool:
        statuses = list(pool.map(manager.inspect, [case for case in guards if case not in verified]))
    write(OUT/'latest-status.json', {'checked_at': datetime.now(timezone.utc).isoformat(), 'jobs': statuses})
    ready = [row['case'] for row in statuses if row['authoritative_status'] == 'COMPLETED']
    with ThreadPoolExecutor(max_workers=2) as pool: collected = list(pool.map(manager.collect, ready))
    failures = [row for row in statuses if row['authoritative_status'] not in manager.ACTIVE | {'COMPLETED'}]
    state.update(stage='collecting', jobs_submitted=len(guards), jobs_verified=len(verified)+sum(r.get('verified', False) for r in collected), failed_jobs=failures); save()
    assert not failures, 'Inspect original failures/unknown states; never replace automatically'
    if state['jobs_verified'] == len(cases):
        state['stage'] = 'freezing_roots'; save(); result = manager.index()
        assert result['complete'] and result['games'] == 160 and set(result['cases']) == set(cases)
        state.update(stage='collection_complete', index_sha256=digest(manager.INDEX), root_manifest_sha256=result['root_manifest_sha256']); save(); return True
    active = sum(row['authoritative_status'] in manager.ACTIVE for row in statuses)
    limit = plan['admission']['max_in_flight']; assert active <= limit
    for case in [case for case in cases if case not in guards][:limit-active]:
        state.update(stage='launching', launching_case=case); save(); launcher.launch(case, True)
    state.update(stage='waiting_for_jobs', jobs_submitted=len(list(launcher.GUARDS.glob('*.json')))); save()
    print({key: state[key] for key in ('stage', 'jobs_submitted', 'jobs_verified')}, flush=True); return False


def main(execute, interval, max_hours):
    assert interval >= 60 and max_hours > 0
    plan = read(launcher.PLAN); launcher.admission(plan['shards'][0]['case'])
    if not execute:
        print({'jobs': len(plan['shards']), 'games': 160, 'maximum_roots': 480, 'admission': plan['admission'], 'execute': False}); return
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT/'coordinator.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        state = {'pid': os.getpid(), 'started_at': datetime.now(timezone.utc).isoformat(),
                 'plan_sha256': digest(launcher.PLAN), 'code_hashes': dependencies(), 'stage': 'starting',
                 'automatic_job_retries': False, 'remote_cancellations_allowed': False, 'gradients': False,
                 'qualification_eligible': False, 'reserved_final_seeds_used': False}
        if (OUT/'state.json').exists():
            old = read(OUT/'state.json'); assert old['plan_sha256'] == state['plan_sha256'] and old['code_hashes'] == state['code_hashes']

        def save():
            state['updated_at'] = datetime.now(timezone.utc).isoformat()
            temporary = OUT/'state.tmp.json'; write(temporary, state); temporary.replace(OUT/'state.json')

        deadline = time.monotonic()+max_hours*3600
        try:
            while time.monotonic() < deadline:
                assert digest(launcher.PLAN) == state['plan_sha256'] and dependencies() == state['code_hashes']
                if cycle(plan, state, save): return
                time.sleep(min(interval, max(0, deadline-time.monotonic())))
            state['stage'] = 'observation_window_ended'; save()
        except BaseException as error:
            state.update(stage='stopped_with_error', error=type(error).__name__+': '+str(error)); save(); raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__); parser.add_argument('--execute', action='store_true')
    parser.add_argument('--interval-seconds', type=int, default=180); parser.add_argument('--max-hours', type=float, default=48)
    args = parser.parse_args(); main(args.execute, args.interval_seconds, args.max_hours)
