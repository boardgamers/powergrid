"""Resume fixed resource-screen work without duplicate submissions or retries."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import fcntl
import importlib.util
import os
from pathlib import Path
import time

from strategic_collection import ROOT, read, write, digest

spec = importlib.util.spec_from_file_location('resource_comparison', Path(__file__).with_name('compare-resource-replanning-development-v1.py'))
comparison = importlib.util.module_from_spec(spec)
spec.loader.exec_module(comparison)
manager, launcher = comparison.manager, comparison.manager.launcher
OUT = ROOT / 'ai/runs/resource-replanning-development-coordinator-v1'


def dependencies():
    return {**manager.code_hashes(), **{str(p.relative_to(ROOT)): digest(p) for p in
            [Path(__file__), Path(comparison.__file__), Path(comparison.pairs.__file__),
             ROOT / 'ai/strong/policy_iteration_development.py']}}


def cycle(plan, state, save):
    cases = [row['case'] for row in plan['shards']]
    guards = {path.stem: read(path) for path in launcher.GUARDS.glob('*.json')}
    assert set(guards) <= set(cases)
    assert all(g['stage'] == 'launched' and g['plan_sha256'] == digest(launcher.PLAN) for g in guards.values()), 'Reconcile uncertain submissions before continuing'
    assert len({g['job_id'] for g in guards.values()}) == len(guards)
    verified = {case for case in cases if manager.verified_receipt(case) is not None}
    assert verified <= set(guards)
    pending = [case for case in guards if case not in verified]
    with ThreadPoolExecutor(max_workers=4) as pool:
        statuses = list(pool.map(manager.inspect, pending))
    write(OUT / 'latest-status.json', {'checked_at': datetime.now(timezone.utc).isoformat(), 'jobs': statuses})
    ready = [row['case'] for row in statuses if row['authoritative_status'] == 'COMPLETED' or row['authoritative_status'] in manager.FAILED]
    with ThreadPoolExecutor(max_workers=4) as pool:
        collected = list(pool.map(manager.collect, ready))
    failed = [row for row in statuses if row['authoritative_status'] not in manager.ACTIVE | {'COMPLETED'}]
    state.update(stage='collecting', jobs_submitted=len(guards),
                 jobs_verified=len(verified) + sum(r.get('verified', False) for r in collected), failed_jobs=failed)
    save()
    assert not failed and not any(r.get('failed') for r in collected), 'Review failed/unknown jobs; no replacements or partial comparison'
    if state['jobs_verified'] == len(cases):
        state['stage'] = 'comparing'
        save()
        if not comparison.OUTPUT.exists():
            comparison.compare(comparison.OUTPUT)
        result = read(comparison.OUTPUT)
        assert result['complete'] and result['games'] == 3360 and result['plan_sha256'] == digest(launcher.PLAN)
        assert result['protocol_sha256'] == digest(launcher.PROTOCOL)
        assert set(result['provenance']) == set(cases)
        assert all(digest(ROOT / name) == sha for name, sha in result['code_hashes'].items())
        assert all(digest(manager.COLLECTED / case / 'verified.json') == r['verified_sha256'] for case, r in result['provenance'].items())
        state.update(stage='comparison_complete', comparison_sha256=digest(comparison.OUTPUT))
        save()
        return True
    active = sum(row['authoritative_status'] in manager.ACTIVE for row in statuses)
    limit = plan['admission']['max_in_flight']
    assert active <= limit
    # Submission itself rechecks all prior remote statuses and admission under a lock.
    for case in [case for case in cases if case not in guards][:limit - active]:
        state.update(stage='launching', launching_case=case)
        save()
        launcher.launch(case, True)
    state.update(stage='waiting_for_jobs', jobs_submitted=len(list(launcher.GUARDS.glob('*.json'))))
    save()
    print({k: state[k] for k in ('stage', 'jobs_submitted', 'jobs_verified')}, flush=True)
    return False


def main(execute, interval, max_hours):
    assert interval >= 60 and max_hours > 0
    plan = read(launcher.PLAN)
    launcher.admission(plan['shards'][0]['case'])
    if not execute:
        print({'shards': len(plan['shards']), 'games': 3360, 'admission': plan['admission'], 'execute': False})
        return
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / 'coordinator.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        state = {'pid': os.getpid(), 'started_at': datetime.now(timezone.utc).isoformat(),
                 'plan_sha256': digest(launcher.PLAN), 'code_hashes': dependencies(), 'stage': 'starting',
                 'automatic_job_retries': False, 'remote_cancellations_allowed': False,
                 'qualification_eligible': False, 'reserved_final_seeds_used': False}
        if (OUT / 'state.json').exists():
            previous = read(OUT / 'state.json')
            assert previous['plan_sha256'] == state['plan_sha256'] and previous['code_hashes'] == state['code_hashes'], 'Investigate changed orchestration before resuming'
        def save():
            state['updated_at'] = datetime.now(timezone.utc).isoformat()
            temp = OUT / 'state.tmp.json'
            write(temp, state)
            temp.replace(OUT / 'state.json')
        deadline = time.monotonic() + max_hours * 3600
        try:
            while time.monotonic() < deadline:
                assert digest(launcher.PLAN) == state['plan_sha256'] and dependencies() == state['code_hashes']
                if cycle(plan, state, save):
                    return
                time.sleep(min(interval, max(0, deadline - time.monotonic())))
            state['stage'] = 'observation_window_ended'
            save()
        except BaseException as error:
            state.update(stage='stopped_with_error', error=type(error).__name__ + ': ' + str(error))
            save()
            raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--interval-seconds', type=int, default=180)
    parser.add_argument('--max-hours', type=float, default=48)
    args = parser.parse_args()
    main(args.execute, args.interval_seconds, args.max_hours)
