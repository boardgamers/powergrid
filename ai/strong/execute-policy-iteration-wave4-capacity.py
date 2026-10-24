"""Coordinate one admitted hardware wave without racing the live collector."""
import argparse
from datetime import datetime, timezone
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

from strategic_collection import ROOT, read, write, digest
from policy_iteration_label_attempts import ATTEMPTS


def now():
    return datetime.now(timezone.utc).isoformat()


def identity(pid):
    proc = Path('/proc')/str(pid)
    command = (proc/'cmdline').read_bytes()
    assert b'harvest-policy-iteration-jobs.py' in command
    assert b'policy-iteration-harvest-recovered-v2' in command
    return (proc/'stat').read_text().rsplit(') ', 1)[1].split()[19]


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    admission_path = ROOT/'ai/strong/policy-iteration-cpu-upgrade-wave4-admission-v2.json'
    admission = read(admission_path)
    assert admission['admitted'] and admission['maximum_total_replacements'] == 420
    assert admission['current_migrations_started'] == 300 and len(admission['verified_full_shards']) >= 30
    assert digest(ROOT/admission['status_snapshot']) == admission['status_sha256']
    previous = [read(p) for p in ATTEMPTS.glob('*.json')]
    assert all(r['stage'] in ['launched', 'skipped'] for r in previous)
    assert sum(r['stage'] == 'launched' for r in previous) == 300
    if not args.execute:
        print({'admitted': True, 'maximum_new_migrations': 120, 'execute': False})
        return
    path = ROOT/'ai/runs/policy-iteration-wave4-capacity-operation-v2.json'
    assert not path.exists(), 'Inspect an existing operation and its exact handles before continuing'
    collector = read(ROOT/'ai/runs/policy-iteration-harvest-recovered-v2/state.json')
    assert collector['stage'] in ['running', 'waiting']
    pid = collector['pid']
    born = identity(pid)
    state = {'stage': 'prepared', 'started_at': now(), 'collector_pid': pid,
             'collector_start_ticks': born, 'admission_sha256': digest(admission_path),
             'admission_snapshot_sha256': admission['status_sha256'],
             'maximum_new_migrations': 120, 'maximum_total_migrations': 420,
             'collector_resumed': False, 'source_worker_changed': False, 'qualification_eligible': False}
    write(path, state)
    paused = False

    def run(name, script, *arguments):
        log = ROOT/'ai/runs'/('policy-iteration-wave4-'+name+'-v2.log')
        with log.open('x') as stream:
            subprocess.run([sys.executable, str(ROOT/'ai/strong'/script), *arguments],
                           cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT, check=True)

    try:
        os.kill(pid, signal.SIGSTOP)
        paused = True
        for _ in range(20):
            if '\nState:\tT' in (Path('/proc')/str(pid)/'status').read_text():
                break
            time.sleep(.05)
        assert '\nState:\tT' in (Path('/proc')/str(pid)/'status').read_text()
        state.update(stage='collector_temporarily_stopped', paused_at=now())
        write(path, state)
        print({'collector_temporarily_stopped': pid, 'remote_jobs_unaffected': True}, flush=True)
        run('launch', 'migrate-policy-iteration-labels-cpu.py', '--wave4', '--limit', '120', '--execute')
        for fill in range(3):
            attempts = [read(p) for p in ATTEMPTS.glob('*.json')]
            assert all(r['stage'] in ['launched', 'skipped'] for r in attempts)
            remaining = 420-sum(r['stage'] == 'launched' for r in attempts)
            assert 0 <= remaining <= 120
            if not remaining:
                break
            run('fill-status-'+str(fill), 'manage-policy-iteration-labels.py', 'status')
            run('fill-'+str(fill), 'migrate-policy-iteration-labels-cpu.py', '--wave4', '--limit', str(remaining), '--execute')
        attempts = [read(p) for p in ATTEMPTS.glob('*.json')]
        assert all(r['stage'] in ['launched', 'skipped'] for r in attempts)
        state.update(stage='migration_finished', total_migrations=sum(r['stage']=='launched' for r in attempts),
                     skipped_originals=sum(r['stage']=='skipped' for r in attempts))
        assert 300 < state['total_migrations'] <= 420
        write(path, state)
        run('final-status', 'manage-policy-iteration-labels.py', 'status')
        snapshot = read(ROOT/'ai/strong/policy-iteration-labels-status-v2.json')
        preserved = ROOT/'ai/runs/policy-iteration-wave4-final-status-v2.json'
        assert not preserved.exists()
        write(preserved, snapshot)
        state.update(stage='complete', finished_at=now(), status_checked_at=snapshot['checked_at'],
                     status_counts=snapshot['status_counts'], final_status_sha256=digest(preserved))
    except BaseException as error:
        state.update(stage='stopped_with_error', error=type(error).__name__+': '+str(error))
        raise
    finally:
        if paused:
            assert identity(pid) == born, 'Collector identity changed; do not signal another process'
            os.kill(pid, signal.SIGCONT)
            state.update(collector_resumed=True, resumed_at=now())
        write(path, state)
        print(state, flush=True)


if __name__ == '__main__':
    main()
