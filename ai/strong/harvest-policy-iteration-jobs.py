"""Bounded collection of existing jobs; never submit, cancel or restart HF jobs."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import fcntl
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

from strategic_collection import ROOT, read, write, digest

STRONG = ROOT/'ai/strong'
RUNS = ROOT/'ai/runs'
COMMANDS = {
    'label-status': ['manage-policy-iteration-labels.py', 'status'],
    'label-collect': ['manage-policy-iteration-labels.py', 'collect'],
    'label-summarize': ['manage-policy-iteration-labels.py', 'summarize'],
    'parent-status': ['manage-policy-iteration-development.py', 'status'],
    'parent-collect': ['manage-policy-iteration-development-grid.py', 'collect', 'parent'],
}


def now():
    return datetime.now(timezone.utc).isoformat()


def save_state(directory, state):
    temporary = directory/'state.tmp.json'
    write(temporary, {**state, 'updated_at': now()})
    temporary.replace(directory/'state.json')


def parent_reports():
    plan = read(STRONG/'policy-iteration-development-plans-v2/parent.json')
    reports = []
    for row in plan['shards']:
        path = RUNS/'policy-iteration-development-verified-v2'/row['case']/'verified.json'
        if path.exists():
            record = read(path)
            assert record['verified'] and record['source'] == plan['source']
            assert record['model_pin_sha256'] == plan['model_pin_sha256']
            assert record['summary']['games'] == row['games']
            for file, sha in record['artifacts'].items():
                assert digest(path.parent/file) == sha
            reports.append(record)
    return reports


def pending_jobs(snapshot, kind):
    jobs = snapshot['jobs']
    if kind == 'parent':
        jobs = [j for j in jobs if j['case'].startswith('development-parent-')]
    assert len(jobs) == (948 if kind == 'label' else 108)
    assert len({j['job_id'] for j in jobs}) == len(jobs)
    bad = [{'job_id': j['job_id'], 'status': j['authoritative_status']} for j in jobs
           if j['authoritative_status'] not in ['COMPLETED', 'RUNNING', 'SCHEDULING']]
    assert not bad, 'Existing jobs require review; no automatic retries: '+str(bad)
    base = RUNS/('policy-iteration-labels-verified-v2' if kind == 'label' else 'policy-iteration-development-verified-v2')
    return [j for j in jobs if j['authoritative_status'] == 'COMPLETED'
            and not (base/(j['shard']['id'] if kind == 'label' else j['case'])/'verified.json').exists()]


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--run-name', default='policy-iteration-harvest-v2')
    parser.add_argument('--interval-seconds', type=int, default=300)
    parser.add_argument('--max-hours', type=float, default=12)
    parser.add_argument('--once', action='store_true')
    args = parser.parse_args()
    assert re.fullmatch(r'policy-iteration-harvest-[a-z0-9-]+', args.run_name)
    assert 60 <= args.interval_seconds <= 3600 and 0 < args.max_hours <= 12
    directory = RUNS/args.run_name
    deadline = time.monotonic()+args.max_hours*3600
    # One collector orchestrator at a time. Existing per-manager locks also apply.
    with (RUNS/'.policy-iteration-harvest.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        directory.mkdir(exist_ok=False)
        code_files = {row[0] for row in COMMANDS.values()} | {'policy_iteration_label_attempts.py'}
        code_hashes = {name: digest(STRONG/name) for name in code_files}
        for source_name in ['policy-iteration-labels-source-v2.json', 'policy-iteration-development-source-v2.json']:
            for file, sha in read(STRONG/source_name)['overlays'].items():
                assert digest(ROOT/file) == sha
        state = {'pid': os.getpid(), 'started_at': now(), 'stage': 'starting', 'cycle': 0,
                 'interval_seconds': args.interval_seconds, 'max_hours': args.max_hours,
                 'code_hashes': code_hashes, 'script_sha256': digest(Path(__file__)),
                 'remote_submissions_allowed': False, 'remote_cancellations_allowed': False,
                 'gradients': False, 'qualification_eligible': False}
        save_state(directory, state)

        def run(name, cycle):
            file, *arguments = COMMANDS[name]
            assert all(digest(STRONG/name) == sha for name, sha in code_hashes.items()), 'Collector code changed during run'
            state.update(stage='running', command=name)
            save_state(directory, state)
            with (cycle/(name+'.log')).open('w') as log:
                subprocess.run([sys.executable, str(STRONG/file), *arguments], cwd=ROOT,
                               stdout=log, stderr=subprocess.STDOUT, check=True)

        try:
            while time.monotonic() < deadline:
                state['cycle'] += 1
                cycle = directory/('cycle-%03d' % state['cycle'])
                cycle.mkdir()
                labels = read(STRONG/'policy-iteration-labels-results-v2.json')
                if not labels['complete']:
                    run('label-status', cycle)
                    snapshot = read(STRONG/'policy-iteration-labels-status-v2.json')
                    shutil.copy2(STRONG/'policy-iteration-labels-status-v2.json', cycle/'label-status.json')
                    if pending_jobs(snapshot, 'label'):
                        run('label-collect', cycle)
                    # Also reconcile a collector that finished before this process started.
                    run('label-summarize', cycle)
                    labels = read(STRONG/'policy-iteration-labels-results-v2.json')
                    state['label_status_checked_at'] = snapshot['checked_at']
                    state['label_status_counts'] = snapshot['status_counts']
                reports = parent_reports()
                if len(reports) < 108:
                    run('parent-status', cycle)
                    snapshot = read(STRONG/'policy-iteration-development-status-v2.json')
                    shutil.copy2(STRONG/'policy-iteration-development-status-v2.json', cycle/'parent-status.json')
                    if pending_jobs(snapshot, 'parent'):
                        run('parent-collect', cycle)
                    reports = parent_reports()
                    state['parent_status_checked_at'] = snapshot['checked_at']
                    state['parent_status_counts'] = dict(Counter(j['authoritative_status'] for j in snapshot['jobs']
                                                                 if j['case'].startswith('development-parent-')))
                state.update(label_shards_verified=labels['complete_shards'], labels_complete=labels['complete'],
                             label_root_mode_pairs=labels['verified_root_mode_pairs'],
                             rollouts_including_pilot=labels['rollouts'],
                             parent_shards_verified=len(reports), parent_reference_complete=len(reports)==108,
                             parent_games_verified=sum(r['summary']['games'] for r in reports), command=None)
                state['stage'] = ('complete' if state['labels_complete'] and state['parent_reference_complete']
                                  else 'single_cycle_complete' if args.once else 'waiting')
                write(cycle/'progress.json', {**state, 'updated_at': now()})
                save_state(directory, state)
                print({k: state[k] for k in ['cycle', 'stage', 'label_shards_verified', 'rollouts_including_pilot',
                                             'parent_shards_verified', 'parent_games_verified']}, flush=True)
                if state['stage'] != 'waiting':
                    return
                # This is a background process; the calling agent stays responsive.
                time.sleep(min(args.interval_seconds, max(0, deadline-time.monotonic())))
            state.update(stage='window_ended', command=None)
            save_state(directory, state)
        except BaseException as error:
            state.update(stage='stopped_with_error', error=type(error).__name__+': '+str(error))
            save_state(directory, state)
            raise


if __name__ == '__main__':
    main()
