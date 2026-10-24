"""Collect the two prescribed HF training jobs after their upstream admission.

This bounded process cannot submit/cancel/retry jobs or promote candidates. It
uses the existing independent collector, then archives exact pins and reports.
Training and development/final evaluation remain separate stages.
"""
import argparse
from datetime import datetime, timezone
import fcntl
import hashlib
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
from policy_iteration_job import admission, BOOTSTRAP
from policy_iteration_development import PROTOCOL, validate_pin
from policy_iteration_evidence_archive import upload_evidence

STRONG = ROOT/'ai/strong'
RUNS = ROOT/'ai/runs'
UPSTREAM = RUNS/'policy-iteration-training-coordinator-v2/state.json'
GUARDS = RUNS/'policy-iteration-training-launches-v2'
VERIFIED = RUNS/'policy-iteration-training-verified-v2'
PINS = STRONG/'policy-iteration-development-pins-v2'
HEADS = ['frozen', 'public']
WAIT_STAGES = {'starting', 'waiting_for_complete_labels', 'labels_admitted',
               'prepare-data', 'archive-data', 'build-source', 'admit-frozen',
               'admit-public', 'launch-frozen', 'launch-public'}


def now():
    return datetime.now(timezone.utc).isoformat()


def upstream_ready(state):
    """Never use an incomplete/ambiguous upstream handoff as admission."""
    assert state['execute'] and state['local_gradients'] is False
    assert state['qualification_eligible'] is False and state['reserved_final_seeds_used'] is False
    if state['stage'] in WAIT_STAGES:
        return False
    assert state['stage'] == 'both_jobs_submitted', 'Upstream stopped or needs review; no automatic recovery'
    assert state['labels_complete'] and state['label_shards_verified'] == 948
    jobs = state['jobs_submitted']
    assert set(jobs) == set(HEADS) and len(set(jobs.values())) == 2
    assert all(re.fullmatch('[a-f0-9]{24}', job) for job in jobs.values())
    assert set(state['launch_evidence']) == set(HEADS)
    for head in HEADS:
        evidence = state['launch_evidence'][head]
        assert evidence['head_type'] == head and evidence['job_id'] == jobs[head]
        assert evidence['remote_archive_verified'] and evidence['qualification_eligible'] is False
    return True


def guard_matches(guard, head, state, design, data_pin, source):
    assert guard['stage'] == 'launched' and guard['job_id'] == state['jobs_submitted'][head]
    assert guard['head_type'] == head and guard['seeds'] == design['seeds']
    assert guard['source'] == source and guard['data_pin'] == data_pin
    assert guard['flavor'] == 'l4x1' and guard['timeout_hours'] == 3
    assert guard['bootstrap_sha256'] == hashlib.sha256(BOOTSTRAP.encode()).hexdigest()
    assert guard['qualification_eligible'] is False


def check_live_upstream(state):
    command = Path('/proc', str(state['pid']), 'cmdline').read_bytes()
    assert b'coordinate-policy-iteration-training.py' in command
    assert b'policy-iteration-training-coordinator-v2' in command


def expected_code():
    state = read(UPSTREAM)
    assert digest(STRONG/'coordinate-policy-iteration-training.py') == state['script_sha256']
    expected = dict(state['source_hashes'])
    extra = [Path(__file__), STRONG/'coordinate-policy-iteration-training.py',
             STRONG/'collect-policy-iteration-training.py', STRONG/'policy_iteration_training_verification.py',
             STRONG/'policy_iteration_development.py', PROTOCOL, STRONG/'strategic_collection.py']
    expected.update({str(p.relative_to(ROOT)): digest(p) for p in extra})
    check_code(expected)
    return expected


def check_code(expected):
    assert all(digest(ROOT/path) == sha for path, sha in expected.items()), 'Verification code changed; review before continuing'


def read_guard(path):
    for attempt in range(3):
        try:
            return read(path)
        except json.JSONDecodeError:
            if attempt == 2:
                raise
            time.sleep(1)


def verify_outputs(head, guard, data_pin, source):
    out = VERIFIED/head
    record = read(out/'verified.json')
    assert record['verified'] and record['head_type'] == head and record['job_id'] == guard['job_id']
    assert record['source'] == source and record['data_pin'] == data_pin
    assert record['guard_sha256'] == digest(GUARDS/(head+'.json'))
    assert record['verifier_sha256'] == digest(STRONG/'policy_iteration_training_verification.py')
    assert record['gradients_during_verification'] is False and record['qualification_eligible'] is False
    for file, sha in record['artifacts'].items():
        assert digest(out/file) == sha
    protocol = read(PROTOCOL)
    pins = {}
    for penalty in [0, 1]:
        key = head+'-'+str(penalty)
        pin = read(PINS/(key+'.json'))
        validate_pin(pin, key, protocol)
        assert pin['training_verified_sha256'] == digest(out/'verified.json')
        assert pin['data_check_sha256'] == data_pin['files']['data-check.json']
        assert pin['revision'] == record['revision'] and pin['repo'] == record['repo']
        assert pin['qualification_eligible'] is False
        pins[key] = {'sha256': digest(PINS/(key+'.json')), 'pin': pin}
    return record, pins


def archive_head(head, guard, data_pin, source):
    record, pins = verify_outputs(head, guard, data_pin, source)
    out = RUNS/('policy-iteration-trained-'+head+'-evidence-v2')
    out.mkdir(exist_ok=False)
    shutil.copy2(GUARDS/(head+'.json'), out/'launch-guard.json')
    for file in ['training-check.json', 'verified.json', 'collection-intent.json']:
        shutil.copy2(VERIFIED/head/file, out/file)
    for seed in record['seeds']:
        for name in ['training.json', 'metrics.json']:
            target = out/str(seed)/name
            target.parent.mkdir(exist_ok=True)
            shutil.copy2(VERIFIED/head/str(seed)/name, target)
    for penalty in [0, 1]:
        ensemble = 'ensemble-'+str(penalty)
        for name in ['calibration.json', 'parity-scope.json', 'derivative/derivative.json']:
            target = out/ensemble/name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(VERIFIED/head/ensemble/name, target)
        key = head+'-'+str(penalty)
        shutil.copy2(PINS/(key+'.json'), out/(key+'-pin.json'))
    for name in ['harvest-policy-iteration-training.py', 'collect-policy-iteration-training.py',
                 'policy_iteration_training_verification.py', 'policy-iteration-training-source-v2.json',
                 'policy-iteration-training-data-evidence-v2.json', 'policy-iteration-training-design-v2.json',
                 'policy-iteration-development-protocol-v2.json', 'policy_iteration_evidence_archive.py']:
        shutil.copy2(STRONG/name, out/name)
    write(out/'manifest.json', {str(p.relative_to(out)): digest(p) for p in out.rglob('*') if p.is_file()})
    evidence = {**upload_evidence(out), 'head_type': head, 'job_id': guard['job_id'],
                'training_artifact_revision': record['revision'], 'training_artifact_prefix': record['prefix'],
                'verified_sha256': digest(VERIFIED/head/'verified.json'), 'candidate_pins': pins,
                'seeds': record['seeds'], 'local_gradients': False, 'qualification_eligible': False,
                'scope': 'Exact trained outputs verified;raw weights remain at their immutable HF pin. This is not whole-game strength or promotion.'}
    write(STRONG/(out.name+'.json'), evidence)
    return evidence


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--run-name', required=True)
    parser.add_argument('--execute', action='store_true', help='Collect and archive completed admitted jobs')
    parser.add_argument('--once', action='store_true')
    parser.add_argument('--interval-seconds', type=int, default=120)
    parser.add_argument('--max-wait-hours', type=float, default=12)
    args = parser.parse_args()
    assert re.fullmatch(r'policy-iteration-training-harvest-[a-z0-9-]+', args.run_name)
    assert 60 <= args.interval_seconds <= 600 and 0 < args.max_wait_hours <= 12
    deadline = time.monotonic()+args.max_wait_hours*3600
    with (RUNS/'.policy-iteration-training-harvest.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        assert not VERIFIED.exists() and not PINS.exists(), 'Inspect existing training verification;do not duplicate it'
        directory = RUNS/args.run_name
        directory.mkdir(exist_ok=False)
        expected = expected_code()
        state = {'pid': os.getpid(), 'started_at': now(), 'stage': 'starting', 'execute': args.execute,
                 'code_hashes': expected, 'interval_seconds': args.interval_seconds,
                 'max_wait_hours': args.max_wait_hours, 'commands_started': [], 'heads_verified': {},
                 'remote_submissions_allowed': False, 'remote_cancellations_allowed': False,
                 'automatic_retries': False, 'local_gradients': False,
                 'qualification_eligible': False, 'reserved_final_seeds_used': False}

        def save():
            temporary = directory/'state.tmp.json'
            write(temporary, {**state, 'updated_at': now()})
            temporary.replace(directory/'state.json')

        save()
        try:
            while time.monotonic() < deadline:
                check_code(expected)
                upstream = read(UPSTREAM)
                state['upstream_stage'] = upstream['stage']
                state['label_shards_verified'] = upstream.get('label_shards_verified')
                if not upstream_ready(upstream):
                    check_live_upstream(upstream)
                    state['stage'] = 'waiting_for_training_submission'
                else:
                    design, data_pin, source = admission()
                    state['training_jobs'] = upstream['jobs_submitted']
                    state['stage'] = 'waiting_for_training_completion'
                    statuses = {}
                    api = HfApi()
                    for head in HEADS:
                        if head in state['heads_verified']:
                            continue
                        guard = read_guard(GUARDS/(head+'.json'))
                        guard_matches(guard, head, upstream, design, data_pin, source)
                        job = api.inspect_job(job_id=guard['job_id'])
                        statuses[head] = job.status.stage
                        state['job_statuses'] = statuses
                        save()
                        assert job.status.stage in ['SCHEDULING', 'RUNNING', 'COMPLETED'], 'Training job needs review;no automatic retry'
                        if job.status.stage != 'COMPLETED' or not args.execute:
                            continue
                        command = 'collect-'+head
                        assert command not in state['commands_started']
                        state.update(stage=command)
                        state['commands_started'].append(command)
                        save()
                        with (directory/(command+'.log')).open('x') as log:
                            subprocess.run([sys.executable, '-u', str(STRONG/'collect-policy-iteration-training.py'),
                                            '--head-type', head], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=True)
                        check_code(expected)
                        state.update(stage='archive-'+head)
                        save()
                        state['heads_verified'][head] = archive_head(head, guard, data_pin, source)
                        save()
                        print({'head_type': head, 'verified_and_archived': True, 'qualification_eligible': False}, flush=True)
                    if set(state['heads_verified']) == set(HEADS):
                        state['stage'] = 'both_heads_verified_and_archived'
                        save()
                        print({'stage': state['stage'], 'candidate_pins': 4, 'evaluation_jobs_submitted': 0}, flush=True)
                        return
                    state['stage'] = 'waiting_for_training_completion'
                save()
                if args.once:
                    print({k: state[k] for k in ['stage', 'label_shards_verified', 'commands_started', 'heads_verified']}, flush=True)
                    return
                time.sleep(min(args.interval_seconds, max(0, deadline-time.monotonic())))
            state['stage'] = 'wait_window_ended'
            save()
        except BaseException as error:
            state.update(stage='stopped_with_error', error=type(error).__name__+': '+str(error))
            save()
            raise


if __name__ == '__main__':
    main()
