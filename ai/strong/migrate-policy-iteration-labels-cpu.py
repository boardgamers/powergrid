"""Move a bounded batch of queued jobs after exact alternative-hardware controls."""
import argparse
from collections import defaultdict
from datetime import datetime, timezone
import fcntl
import hashlib
import importlib.util
import json
import math
import os
import re
import subprocess
import time

from huggingface_hub import HfApi, get_token
from strategic_collection import ROOT, read, write, digest
from policy_iteration_label_attempts import ATTEMPTS, effective_guard

GUARDS = ROOT/'ai/runs/policy-iteration-labels-launches-v2'
PROFILE = ROOT/'ai/strong/policy-iteration-cpu-upgrade-profile-results-v2.json'


def snapshot(api, job_id):
    job = api.inspect_job(job_id=job_id)
    return {'job_id': job_id, 'stage': job.status.stage, 'message': job.status.message,
            'started_at': str(job.started_at), 'finished_at': str(job.finished_at),
            'checked_at': datetime.now(timezone.utc).isoformat()}


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--limit', type=int, default=60)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    assert 1 <= args.limit <= 60, 'First hardware wave is deliberately limited'
    profile = read(PROFILE)
    assert profile['verified'] and profile['rollouts'] == 3072
    assert profile['full_trajectories_and_choice_transcripts_match_reference']
    assert profile['microbenchmark_positions'] == 2553 and profile['all_microbenchmark_raw_outputs_identical']
    assert profile['worst_case_upgrade_slowdown'] < 1.5
    source = read(ROOT/'ai/strong/policy-iteration-labels-source-v2.json')
    protocol = read(ROOT/'ai/strong/policy-iteration-labels-protocol-v2.json')
    assert profile['source'] == protocol['inference_profile']['source']
    assert source['protocol_sha256'] == digest(ROOT/'ai/strong/policy-iteration-labels-protocol-v2.json')
    assert all(digest(ROOT/file) == sha for file, sha in source['overlays'].items())
    status = read(ROOT/'ai/strong/policy-iteration-labels-status-v2.json')
    spec = importlib.util.spec_from_file_location('label_manager', ROOT/'ai/strong/manage-policy-iteration-labels.py')
    manager = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(manager)
    groups = defaultdict(list)
    for job in status['jobs']:
        shard = job['shard']
        if job['authoritative_status'] == 'SCHEDULING' and not (ATTEMPTS/(shard['id']+'.json')).exists():
            assert job['source'] == source
            groups[tuple(shard[k] for k in ['players', 'behavior', 'opponent', 'mode'])].append(job)
    candidates = []
    while groups and len(candidates) < args.limit:
        for key in sorted(groups):
            if len(candidates) == args.limit:
                break
            candidates.append(groups[key].pop(0))
        groups = {key: rows for key, rows in groups.items() if rows}
    multiplier = max(1., profile['worst_case_upgrade_slowdown'])*1.25
    for job in candidates:
        assert math.ceil(job['shard']['admission']['conservative_seconds']*multiplier) <= .75*12*3600
    print({'planned': len(candidates), 'flavor': 'cpu-upgrade', 'timeout_hours': 12,
           'admission_multiplier': multiplier, 'executed': args.execute}, flush=True)
    if not args.execute:
        return
    env = os.environ.copy()
    env['HF_TOKEN'] = get_token() or env.get('HF_TOKEN') or ''
    assert env['HF_TOKEN']
    api = HfApi()
    ATTEMPTS.mkdir(exist_ok=True)
    with (ATTEMPTS/'.migration.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        # Stop on any unresolved earlier submission rather than guessing.
        previous = [read(path) for path in ATTEMPTS.glob('*.json')]
        assert all(r['stage'] in ['launched', 'skipped'] for r in previous)
        assert sum(r['stage'] == 'launched' for r in previous) + len(candidates) <= 60
        for job in candidates:
            shard = job['shard']
            original_path = GUARDS/(shard['id']+'.json')
            original = read(original_path)
            assert effective_guard(original_path) == original
            assert original['job_id'] == job['job_id'] and original['shard'] == shard and original['source'] == source
            before = snapshot(api, original['job_id'])
            record = {'stage': 'cancel_intent', 'original_job_id': original['job_id'], 'source': source,
                      'shard': shard, 'original_guard_sha256': digest(original_path), 'before': before,
                      'profile_sha256': digest(PROFILE), 'flavor': 'cpu-upgrade', 'timeout_hours': 12,
                      'conservative_seconds': math.ceil(shard['admission']['conservative_seconds']*multiplier),
                      'bootstrap_sha256': hashlib.sha256(manager.BOOTSTRAP.encode()).hexdigest(),
                      'qualification_eligible': False}
            path = ATTEMPTS/original_path.name
            with path.open('x') as stream:
                json.dump(record, stream, indent=2)
            if before['stage'] != 'SCHEDULING':
                record.update(stage='skipped', reason='Original job is no longer queued')
                write(path, record)
                print({'shard': shard['id'], 'skipped': before['stage']}, flush=True)
                continue
            api.cancel_job(job_id=original['job_id'])
            for _ in range(20):
                after = snapshot(api, original['job_id'])
                if after['stage'] in ['CANCELED', 'CANCELLED', 'COMPLETED', 'ERROR', 'TIMEOUT']:
                    break
                time.sleep(1)
            record['cancellation'] = after
            write(path, record)
            if after['stage'] == 'COMPLETED':
                record.update(stage='skipped', reason='Original completed during cancellation')
                write(path, record)
                continue
            assert after['stage'] in ['CANCELED', 'CANCELLED'], 'No replacement until cancellation is confirmed'
            record.update(stage='replacement_intent', replacement_created_at=datetime.now(timezone.utc).isoformat())
            write(path, record)
            command = ['hf', 'jobs', 'run', '--detach', '--flavor', 'cpu-upgrade', '--timeout', '12h',
                       '--secrets', 'HF_TOKEN', '--label', 'project=powergrid-ai',
                       '--label', 'stage=policy-labels-cpu-upgrade-v2', '--label', 'shard='+shard['id']]
            for key, value in {'SOURCE_ARCHIVE': source['archive'], 'SOURCE_REVISION': source['revision'],
                               'SOURCE_SHA256': source['sha256'], 'LABEL_SHARD': shard['id'],
                               'HF_HUB_DISABLE_PROGRESS_BARS': '1'}.items():
                command += ['--env', key+'='+value]
            command += ['--', 'python:3.11-slim-bookworm', 'bash', '-lc', manager.BOOTSTRAP]
            try:
                result = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True, check=True)
                path.with_suffix('.log').write_text(result.stdout+result.stderr)
                ids = set(re.findall(r'\b[a-f0-9]{24}\b', result.stdout))
                assert len(ids) == 1, 'Ambiguous launch: inspect HF before retrying'
                record.update(stage='launched', job_id=ids.pop())
            except BaseException as error:
                record.update(stage='launch_unknown', error=type(error).__name__+': '+str(error))
                raise
            finally:
                write(path, record)
            print({'shard': shard['id'], 'original_canceled': original['job_id'], 'new_job_id': record['job_id']}, flush=True)


if __name__ == '__main__':
    main()
