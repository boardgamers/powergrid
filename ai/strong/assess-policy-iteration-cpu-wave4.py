"""Review broad full-shard evidence and current scheduling before a fourth bounded CPU wave."""
from collections import Counter
from datetime import datetime, timezone
import importlib.util
import math

from strategic_collection import ROOT, read, write, digest
from policy_iteration_label_attempts import ATTEMPTS

OUTPUT = ROOT/'ai/strong/policy-iteration-cpu-upgrade-wave4-admission-v2.json'
PROFILE = ROOT/'ai/strong/policy-iteration-cpu-upgrade-profile-results-v2.json'


def main():
    assert not OUTPUT.exists(), 'Preserve the original capacity decision'
    profile = read(PROFILE)
    assert profile['verified'] and profile['rollouts'] == 3072
    assert profile['full_trajectories_and_choice_transcripts_match_reference']
    assert profile['all_microbenchmark_raw_outputs_identical'] and profile['worst_case_upgrade_slowdown'] < 1.5
    status_path = ROOT/'ai/strong/policy-iteration-labels-status-v2.json'
    status = read(status_path)
    assert 0 <= (datetime.now(timezone.utc)-datetime.fromisoformat(status['checked_at'])).total_seconds() < 300
    status_copy = ROOT/'ai/runs/policy-iteration-wave4-admission-status-v2.json'
    assert not status_copy.exists(), 'Preserve the exact capacity-admission snapshot'
    write(status_copy, status)
    source = read(ROOT/'ai/strong/policy-iteration-labels-source-v2.json')
    attempts = {read(path)['job_id']: (path, read(path)) for path in ATTEMPTS.glob('*.json') if read(path)['stage'] == 'launched'}
    assert len(attempts) == 300
    spec = importlib.util.spec_from_file_location('wave4_manager', ROOT/'ai/strong/manage-policy-iteration-labels.py')
    manager = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(manager)
    completed, live = [], []
    for job in status['jobs']:
        if job['job_id'] not in attempts:
            continue
        path, attempt = attempts[job['job_id']]
        assert attempt['source'] == source == job['source'] and attempt['shard'] == job['shard']
        assert attempt['cancellation']['stage'] in ['CANCELED', 'CANCELLED'] and attempt['cancellation']['started_at'] == 'None'
        assert job['authoritative_status'] in ['RUNNING', 'COMPLETED'], 'Do not expand with an unresolved hardware/job failure'
        live.append(job)
        directory = manager.VERIFIED/job['shard']['id']
        if job['authoritative_status'] != 'COMPLETED' or not (directory/'verified.json').exists():
            continue
        verified = manager.verify_local(directory, source, job['shard'])
        seconds = (datetime.fromisoformat(job['finished_at'])-datetime.fromisoformat(job['started_at'])).total_seconds()
        assert 0 < seconds <= attempt['conservative_seconds'] <= .75*12*3600
        completed.append({'job_id':job['job_id'],'shard':job['shard']['id'],
                          **{k:job['shard'][k] for k in ['players','behavior','opponent','mode']},
                          'seconds_including_setup_and_upload':seconds,'admission_seconds':attempt['conservative_seconds'],
                          'roots':verified['summary']['roots'],'rollouts':verified['summary']['rollouts'],
                          'revision':verified['revision'],'prefix':verified['prefix'],
                          'attempt_sha256':digest(path),'verified_sha256':digest(directory/'verified.json')})
    assert len(live) == 300 and len(completed) >= 30
    assert all(j['started_at'] != 'None' for j in live)
    assert {r['players'] for r in completed} == {2,3,4,5,6}
    assert {r['mode'] for r in completed} == {'neural','neural_economic'}
    assert {r['behavior'] for r in completed} == {'parent','11101','11102'}
    assert {r['opponent'] for r in completed} == {'economic','snapshot0'}
    third = [j for j in live if attempts[j['job_id']][1].get('capacity_wave') == 3]
    assert len(third) == 120 and all(j['started_at'] != 'None' for j in third)
    queued = [j for j in status['jobs'] if j['authoritative_status'] == 'SCHEDULING' and j['job_id'] not in attempts]
    assert len(queued) >= 120 and all(j['message'] == 'Waiting for requested hardware to become available' for j in queued)
    multiplier = max(1.,profile['worst_case_upgrade_slowdown'])*1.25
    protocol = read(ROOT/'ai/strong/policy-iteration-labels-protocol-v2.json')
    maximum = max(math.ceil(s['admission']['conservative_seconds']*multiplier) for s in protocol['shards'])
    assert maximum <= .75*12*3600
    report = {'admitted':True,'source':source,'profile_sha256':digest(PROFILE),
              'status_checked_at':status['checked_at'],'status_sha256':digest(status_copy),
              'status_snapshot':str(status_copy.relative_to(ROOT)), 'current_migrations_started':300,
              'current_replacement_status_counts':dict(Counter(j['authoritative_status'] for j in live)),
              'third_wave_all120_started':True,'queued_originals':len(queued),
              'verified_full_shards':completed,'rollouts':sum(r['rollouts'] for r in completed),
              'measured_wall_seconds_range':[min(r['seconds_including_setup_and_upload'] for r in completed),max(r['seconds_including_setup_and_upload'] for r in completed)],
              'maximum_total_replacements':420,'maximum_new_replacements':120,
              'timeout_hours':12,'admission_multiplier':multiplier,'largest_admission_seconds':maximum,
              'frozen_worker_unchanged':True,'qualification_eligible':False,
              'scope':'One further bounded wave: verified full shards now span2-6p,both continuation modes,all behavior policies and both opponents;all300 current migrations and all120 third-wave jobs started. No assumption that every shard has measured runtimes or that unlimited hardware is available. Original conservative bounds remain. Only confirmed canceled,never-started originals may be replaced.'}
    write(OUTPUT,report)
    print({k:report[k] for k in ['admitted','queued_originals','rollouts','measured_wall_seconds_range','maximum_total_replacements']})


if __name__ == '__main__':
    main()
