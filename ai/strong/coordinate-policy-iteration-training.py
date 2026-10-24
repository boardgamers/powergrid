"""Wait for complete verified labels, then run the already prescribed HF pipeline.

No gradients run locally. No partial-data training, automatic retries, altered
designs or candidate promotion. A failure leaves every intermediate intact.
"""
import argparse
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

from huggingface_hub import HfApi
from strategic_collection import ROOT, read, write, digest
from policy_iteration_data import validate_manifest, PROTOCOL, SOURCE
from policy_iteration_evidence_archive import upload_evidence

STRONG = ROOT/'ai/strong'
RUNS = ROOT/'ai/runs'
MANIFEST = STRONG/'policy-iteration-labels-results-v2.json'
GUARDS = RUNS/'policy-iteration-training-launches-v2'
STAGES = [
    ('prepare-data', ['prepare-policy-iteration-training-data.py']),
    ('archive-data', ['archive-policy-iteration-training-data.py']),
    ('build-source', ['build-policy-iteration-training-source.py']),
    ('admit-frozen', ['launch-policy-iteration-training.py', '--head-type', 'frozen']),
    ('admit-public', ['launch-policy-iteration-training.py', '--head-type', 'public']),
]
OUTPUTS = [RUNS/'policy-iteration-training-data-v2',
           RUNS/'policy-iteration-training-source-complete-v2', GUARDS,
           STRONG/'policy-iteration-training-data-evidence-v2.json',
           STRONG/'policy-iteration-training-source-v2.json',
           RUNS/'strong-source-policy-iteration-training-20261024-v2.tgz']


def now():
    return datetime.now(timezone.utc).isoformat()


def save(directory, state):
    temporary = directory/'state.tmp.json'
    write(temporary, {**state, 'updated_at': now()})
    temporary.replace(directory/'state.json')


def source_hashes():
    check_path = STRONG/'policy-iteration-training-source-code-check-v2.json'
    check = read(check_path)
    assert check['passed'] and check['code_only'] and not check['gradients']
    assert len(check['overlays']) == 17 and check['unchanged_base_files'] == 1434
    expected = dict(check['overlays'])
    expected.update({str(p.relative_to(ROOT)): digest(p) for p in [
        check_path, PROTOCOL, SOURCE, STRONG/'strategic_correction_targets.py',
        STRONG/'policy_iteration_evidence_archive.py']})
    assert all(digest(ROOT/file) == sha for file, sha in expected.items())
    return expected


def check_sources(expected):
    assert all(digest(ROOT/file) == sha for file, sha in expected.items()), 'Inputs changed; review before proceeding'


def label_snapshot():
    # The collector writes this file after verification; tolerate a concurrent
    # write, but stop on a persistently incomplete/corrupt JSON representation.
    for attempt in range(3):
        try:
            return read(MANIFEST)
        except json.JSONDecodeError:
            if attempt == 2:
                raise
            time.sleep(1)


def archive_launch(head):
    guard = GUARDS/(head+'.json')
    row = read(guard)
    assert row['stage'] == 'launched' and row['head_type'] == head
    assert row['flavor'] == 'l4x1' and row['timeout_hours'] == 3
    out = RUNS/('policy-iteration-training-launch-'+head+'-evidence-v2')
    out.mkdir(exist_ok=False)
    for name in ['policy-iteration-training-design-v2.json', 'policy-iteration-training-data-evidence-v2.json',
                 'policy-iteration-training-source-v2.json', 'policy-iteration-training-source-check-v2.json',
                 'coordinate-policy-iteration-training.py', 'launch-policy-iteration-training.py',
                 'policy_iteration_evidence_archive.py']:
        shutil.copy2(STRONG/name, out/name)
    shutil.copy2(guard, out/'launch-guard.json')
    shutil.copy2(guard.with_suffix('.log'), out/'launch.log')
    write(out/'manifest.json', {str(p.relative_to(out)): digest(p) for p in out.rglob('*') if p.is_file()})
    result = {**upload_evidence(out), 'head_type': head, 'job_id': row['job_id'],
              'seeds': row['seeds'], 'qualification_eligible': False}
    write(STRONG/(out.name+'.json'), result)
    return result


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--run-name', required=True)
    parser.add_argument('--execute', action='store_true', help='Advance to the prescribed HF jobs once full gates pass')
    parser.add_argument('--once', action='store_true', help='One readiness observation; never wait')
    parser.add_argument('--interval-seconds', type=int, default=60)
    parser.add_argument('--max-wait-hours', type=float, default=12)
    args = parser.parse_args()
    assert re.fullmatch(r'policy-iteration-training-coordinator-[a-z0-9-]+', args.run_name)
    assert 30 <= args.interval_seconds <= 600 and 0 < args.max_wait_hours <= 12
    deadline = time.monotonic()+args.max_wait_hours*3600
    with (RUNS/'.policy-iteration-training-coordinator.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        assert not any(p.exists() for p in OUTPUTS), 'Inspect existing preparation/launch state; do not recreate it'
        expected = source_hashes()
        directory = RUNS/args.run_name
        directory.mkdir(exist_ok=False)
        state = {'pid': os.getpid(), 'started_at': now(), 'stage': 'starting', 'execute': args.execute,
                 'source_hashes': expected, 'script_sha256': digest(Path(__file__)),
                 'max_wait_hours': args.max_wait_hours, 'interval_seconds': args.interval_seconds,
                 'commands_started': [], 'jobs_submitted': {}, 'local_gradients': False,
                 'qualification_eligible': False, 'reserved_final_seeds_used': False}
        save(directory, state)

        def run(name, arguments):
            check_sources(expected)
            state.update(stage=name)
            state['commands_started'].append(name)
            save(directory, state)
            with (directory/(name+'.log')).open('w') as log:
                subprocess.run([sys.executable, '-u', str(STRONG/arguments[0]), *arguments[1:]],
                               cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=True)

        try:
            while True:
                check_sources(expected)
                manifest = label_snapshot()
                assert manifest['planned_shards'] == 948 and manifest['source'] == read(SOURCE)
                assert isinstance(manifest['complete'], bool)
                state.update(label_shards_verified=manifest['complete_shards'], labels_complete=manifest['complete'],
                             rollouts_including_pilot=manifest['rollouts'])
                if manifest['complete']:
                    validate_manifest(manifest, read(PROTOCOL), read(SOURCE))
                    state.update(stage='labels_admitted', label_manifest_sha256=digest(MANIFEST))
                    save(directory, state)
                    break
                assert manifest['pending'] and manifest['complete_shards'] < 948
                state['stage'] = 'waiting_for_complete_labels'
                save(directory, state)
                if args.once:
                    print({k: state[k] for k in ['stage', 'label_shards_verified', 'commands_started', 'jobs_submitted']}, flush=True)
                    return
                if time.monotonic() >= deadline:
                    state['stage'] = 'wait_window_ended'
                    save(directory, state)
                    return
                time.sleep(min(args.interval_seconds, max(0, deadline-time.monotonic())))
            if not args.execute:
                print({'stage': 'labels_admitted', 'executed': False}, flush=True)
                return
            assert not any(p.exists() for p in OUTPUTS), 'Another process prepared inputs; inspect instead of duplicating'
            for name, arguments in STAGES:
                run(name, arguments)
            for head in ['frozen', 'public']:
                run('launch-'+head, ['launch-policy-iteration-training.py', '--head-type', head, '--execute'])
                guard = read(GUARDS/(head+'.json'))
                assert guard['stage'] == 'launched'
                state['jobs_submitted'][head] = guard['job_id']
                save(directory, state)
                evidence = archive_launch(head)
                status = HfApi().inspect_job(job_id=guard['job_id']).status.stage
                state.setdefault('launch_evidence', {})[head] = evidence
                save(directory, state)
                assert status in ['SCHEDULING', 'RUNNING', 'COMPLETED'], 'New job requires inspection; no automatic retries'
            assert len(set(state['jobs_submitted'].values())) == 2
            state.update(stage='both_jobs_submitted')
            save(directory, state)
            print({'stage': state['stage'], 'jobs_submitted': state['jobs_submitted']}, flush=True)
        except BaseException as error:
            state.update(stage='stopped_with_error', error=type(error).__name__+': '+str(error))
            save(directory, state)
            raise


if __name__ == '__main__':
    main()
