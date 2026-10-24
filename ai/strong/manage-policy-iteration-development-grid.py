"""Frozen full-grid plans and resumable submission/collection of exact HF shards."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import fcntl
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

from strategic_collection import ROOT, read, write, digest
from policy_iteration_development import PROTOCOL, case_key, contract, pin_hash

MANAGER = ROOT/'ai/strong/manage-policy-iteration-development.py'
SPEC = importlib.util.spec_from_file_location('development_manager', MANAGER)
manager = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(manager)
PLAN_DIR = ROOT/'ai/strong/policy-iteration-development-plans-v2'


def cells(protocol, key):
    assert key in protocol['models']
    result = []
    for start in range(0, 16, 4):
        for cell in protocol['screens']:
            n, opponent = cell['players'], cell['opponent']
            screen, _ = contract(protocol, n, opponent, start, start+4, 'development')
            result.append({'key': key, 'players': n, 'opponent': opponent, 'start': start, 'end': start+4,
                           'mode': 'development', 'case': case_key(key, n, opponent, start, start+4),
                           'games': screen['games']})
    assert len(result) == len({r['case'] for r in result}) == 108
    assert sum(r['games'] for r in result) == protocol['planned_games_per_model'] == 6720
    return result


def plan(key):
    protocol = read(PROTOCOL)
    source, pin = manager.source_check(), manager.get_pin(key)
    admission = manager.runtime_admission(key, pin, source)
    assert admission['admitted'], 'Runtime admission must pass before full-grid planning'
    return {'key': key, 'source': source, 'model_pin': pin, 'model_pin_sha256': pin_hash(pin),
            'protocol_sha256': digest(PROTOCOL), 'manager_sha256': digest(MANAGER),
            'bootstrap_sha256': hashlib.sha256(manager.BOOTSTRAP.encode()).hexdigest(),
            'runtime_admission': admission, 'flavor': 'cpu-upgrade', 'shards': cells(protocol, key),
            'games': 6720, 'independent_deals_per_cell': 16, 'qualification_eligible': False}


def plan_path(key):
    return PLAN_DIR/(key+'.json')


def require_plan(key):
    expected = plan(key)
    assert read(plan_path(key)) == expected
    return expected


def matching_guard(path, row, grid):
    record = read(path)
    assert record['stage'] == 'launched', 'Reconcile unknown submission before proceeding'
    for key in ['key', 'players', 'opponent', 'start', 'end', 'mode', 'case']:
        assert record[key] == row[key]
    for key in ['source', 'model_pin', 'model_pin_sha256', 'protocol_sha256', 'bootstrap_sha256', 'flavor', 'runtime_admission']:
        assert record[key] == grid[key]
    return record


def launch(key, limit, execute):
    grid = require_plan(key)
    assert 1 <= limit <= 108
    manager.GUARDS.mkdir(exist_ok=True)
    with (manager.GUARDS/'.grid-launch.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        pending = []
        for row in grid['shards']:
            path = manager.GUARDS/(row['case']+'.json')
            if path.exists():
                matching_guard(path, row, grid)
            else:
                pending.append(row)
        print({'key': key, 'already_submitted': 108-len(pending), 'remaining': len(pending),
               'selected': min(limit, len(pending)), 'execute': execute,
               'timeout_hours': grid['runtime_admission']['timeout_hours']}, flush=True)
        for row in pending[:limit]:
            manager.launch(argparse.Namespace(**row, execute=execute))


def collect(key):
    grid = require_plan(key)
    snapshot = read(ROOT/'ai/strong/policy-iteration-development-status-v2.json')
    age = (datetime.now(timezone.utc)-datetime.fromisoformat(snapshot['checked_at'])).total_seconds()
    assert 0 <= age <= 3600, 'Refresh exact job statuses before collecting the grid'
    jobs = {row['case']: row for row in snapshot['jobs']}
    todo = []
    for row in grid['shards']:
        path = manager.GUARDS/(row['case']+'.json')
        if not path.exists():
            continue
        guard = matching_guard(path, row, grid)
        job = jobs.get(row['case'])
        assert job and job['job_id'] == guard['job_id']
        if job['authoritative_status'] == 'COMPLETED' and not (manager.VERIFIED/row['case']/'verified.json').exists():
            todo.append(row)
    logdir = ROOT/'ai/runs/policy-iteration-development-grid-collection-v2'
    logdir.mkdir(exist_ok=True)
    with (logdir/'.collection.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        def one(row):
            command = [sys.executable, str(MANAGER), 'collect', row['key'], str(row['players']), row['opponent'],
                       str(row['start']), str(row['end']), '--mode', 'development']
            with (logdir/(row['case']+'.log')).open('w') as log:
                subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=True)
            report = read(manager.VERIFIED/row['case']/'verified.json')
            assert report['verified'] and report['summary']['games'] == row['games']
            return {'case': row['case'], 'games': row['games'], 'verified': True}
        print({'collecting': len(todo), 'key': key}, flush=True)
        errors = []
        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = {pool.submit(one, row): row for row in todo}
            for future in as_completed(futures):
                try:
                    print(future.result(), flush=True)
                except Exception as error:
                    errors.append({'case': futures[future]['case'], 'error': type(error).__name__+': '+str(error)})
        assert not errors, errors


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('command', choices=['plan', 'launch', 'collect'])
    parser.add_argument('key', choices=['parent', 'frozen-0', 'frozen-1', 'public-0', 'public-1'])
    parser.add_argument('--limit', type=int, default=108)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    if args.command == 'plan':
        value = plan(args.key)
        path = plan_path(args.key)
        if path.exists():
            assert read(path) == value
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open('x') as stream:
                json.dump(value, stream, indent=2)
                stream.write('\n')
        print({'key': args.key, 'shards': 108, 'games': value['games'],
               'plan_sha256': digest(path), 'timeout_hours': value['runtime_admission']['timeout_hours']})
    elif args.command == 'launch':
        launch(args.key, args.limit, args.execute)
    else:
        assert not args.execute
        collect(args.key)


if __name__ == '__main__':
    main()
