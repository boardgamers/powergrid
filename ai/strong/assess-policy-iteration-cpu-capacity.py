"""Admit one bounded expansion after real CPU Upgrade shards independently verify."""
from datetime import datetime, timezone
import importlib.util
import math
from pathlib import Path

from strategic_collection import ROOT, read, write, digest
from policy_iteration_label_attempts import ATTEMPTS

OUTPUT = ROOT/'ai/strong/policy-iteration-cpu-upgrade-wave2-admission-v2.json'
PROFILE = ROOT/'ai/strong/policy-iteration-cpu-upgrade-profile-results-v2.json'


def assess():
    profile = read(PROFILE)
    assert profile['verified'] and profile['rollouts'] == 3072
    assert profile['full_trajectories_and_choice_transcripts_match_reference']
    assert profile['all_microbenchmark_raw_outputs_identical'] and profile['worst_case_upgrade_slowdown'] < 1.5
    source = read(ROOT/'ai/strong/policy-iteration-labels-source-v2.json')
    status_path = ROOT/'ai/strong/policy-iteration-labels-status-v2.json'
    status = read(status_path)
    age = (datetime.now(timezone.utc)-datetime.fromisoformat(status['checked_at'])).total_seconds()
    assert 0 <= age < 3600
    attempts = {read(path)['job_id']: (path, read(path)) for path in ATTEMPTS.glob('*.json') if read(path)['stage'] == 'launched'}
    assert len(attempts) == 60, 'This admission is for the first expansion only'
    spec = importlib.util.spec_from_file_location('capacity_label_manager', ROOT/'ai/strong/manage-policy-iteration-labels.py')
    manager = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(manager)
    completed = []
    for job in status['jobs']:
        if job['job_id'] not in attempts or job['authoritative_status'] != 'COMPLETED':
            continue
        path, attempt = attempts[job['job_id']]
        assert attempt['source'] == source == job['source'] and attempt['shard'] == job['shard']
        assert attempt['before']['stage'] == 'SCHEDULING'
        assert attempt['cancellation']['stage'] in ['CANCELED', 'CANCELLED']
        assert attempt['cancellation']['started_at'] == 'None'
        directory = manager.VERIFIED/job['shard']['id']
        verified = manager.verify_local(directory, source, job['shard'])
        assert verified['verified']
        seconds = (datetime.fromisoformat(job['finished_at'])-datetime.fromisoformat(job['started_at'])).total_seconds()
        assert 0 < seconds <= attempt['conservative_seconds'] <= .75*12*3600
        completed.append({'job_id': job['job_id'], 'shard': job['shard']['id'],
                          'players': job['shard']['players'], 'behavior': job['shard']['behavior'],
                          'opponent': job['shard']['opponent'], 'mode': job['shard']['mode'],
                          'seconds_including_setup_and_upload': seconds, 'admission_seconds': attempt['conservative_seconds'],
                          'roots': verified['summary']['roots'], 'rollouts': verified['summary']['rollouts'],
                          'revision': verified['revision'], 'prefix': verified['prefix'],
                          'attempt_sha256': digest(path), 'verified_sha256': digest(directory/'verified.json')})
    assert len(completed) >= 2 and len({row['behavior'] for row in completed}) >= 2
    assert any(row['players'] == 6 for row in completed)
    multiplier = max(1., profile['worst_case_upgrade_slowdown'])*1.25
    protocol = read(ROOT/'ai/strong/policy-iteration-labels-protocol-v2.json')
    largest = max(math.ceil(s['admission']['conservative_seconds']*multiplier) for s in protocol['shards'])
    assert largest <= .75*12*3600
    return {'admitted': True, 'source': source, 'profile_sha256': digest(PROFILE),
            'status_checked_at': status['checked_at'], 'status_sha256': digest(status_path),
            'verified_full_shards': completed, 'rollouts': sum(r['rollouts'] for r in completed),
            'maximum_total_replacements': 180, 'maximum_new_replacements': 120,
            'timeout_hours': 12, 'admission_multiplier': multiplier,
            'largest_admission_seconds': largest, 'frozen_worker_unchanged': True,
            'scope': 'One additional bounded wave after two complete verified shards and the prior exact 2p/6p both-mode hardware controls. Small runtime sample is not evidence that all shards have this speed; retain original conservative bounds with hardware margin. Only canceled, never-started originals may be replaced.',
            'qualification_eligible': False}


if __name__ == '__main__':
    report = assess()
    assert not OUTPUT.exists(), 'Preserve the first capacity decision'
    write(OUTPUT, report)
    print({k: report[k] for k in ['admitted', 'rollouts', 'maximum_total_replacements', 'maximum_new_replacements', 'largest_admission_seconds']})
