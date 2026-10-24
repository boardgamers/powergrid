"""Recover ten reviewed upload failures and collect the unchanged development grid.

One replacement per admitted terminal job, at most two replacements in flight.
Never replace running jobs, alter experiments, retry a replacement, or select a
candidate. The original coordinator, guards and logs remain preserved evidence.
"""
import argparse
from contextlib import ExitStack
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from huggingface_hub import HfApi
from huggingface_hub.errors import EntryNotFoundError
from strategic_collection import ROOT, read, write, digest
from policy_iteration_development import prefix

STRONG, RUNS = ROOT/'ai/strong', ROOT/'ai/runs'
ADMISSION = STRONG/'policy-iteration-development-recovery-admission-v1.json'
FAILED = RUNS/'policy-iteration-development-failures-v1'
ORIGINAL = RUNS/'policy-iteration-development-coordinator-v2/state.json'
SPEC = importlib.util.spec_from_file_location('development_coordinator', STRONG/'coordinate-policy-iteration-development.py')
coordinator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(coordinator)
grid, manager = coordinator.grid, coordinator.grid.manager


def replacement_allowed(original, current_status, canonical, remote_files):
    assert current_status == 'ERROR', 'Only a confirmed terminal failed job may be replaced'
    assert canonical == original, 'Never replace a replacement or changed guard'
    assert not remote_files, 'Inspect existing artifacts before replacing their producer'
    assert original['stage'] == 'launched' and original['mode'] == 'development'
    assert original['qualification_eligible'] is False


def admit():
    prior = read(ORIGINAL)
    assert prior['stage'] == 'stopped_with_error'
    assert not Path('/proc', str(prior['pid']), 'cmdline').exists(), 'Original coordinator is still present'
    coordinator.check_code(prior['code_hashes'])
    admission = read(ADMISSION)
    assert admission['original_coordinator_sha256'] == digest(ORIGINAL)
    assert admission['maximum_replacements'] == 10 and admission['maximum_in_flight'] == 2
    assert len(admission['cases']) == len({r['job_id'] for r in admission['cases']}) == 10
    assert admission['qualification_eligible'] is False and admission['reserved_final_seeds_used'] is False
    for name, sha in admission['evidence_files'].items():
        assert digest(FAILED/name) == sha
    for row in admission['cases']:
        original = read(FAILED/(row['case']+'-guard.json'))
        assert digest(FAILED/(row['case']+'-guard.json')) == row['original_guard_sha256']
        assert original['job_id'] == row['job_id']
        plan = grid.require_plan(original['key'])
        planned = next(r for r in plan['shards'] if r['case'] == row['case'])
        assert grid.matching_guard(manager.GUARDS/(row['case']+'.json'), planned, plan) == original
        assert not (manager.VERIFIED/row['case']).exists(), 'Preserve any collection already in progress'
        log = (FAILED/(row['case']+'.log')).read_text()
        assert '429 Too Many Requests' in log and 'maximum queue size reached' in log
        assert 'line 230, in run' in log and 'HfApi().upload_folder' in log
    assert set(prior['grids_submitted']) == set(coordinator.KEYS)
    assert all(len(jobs) == 108 for jobs in prior['grids_submitted'].values())
    assert all(record['remote_archive_verified'] for record in prior['grid_launch_evidence'].values())
    return admission, prior


def remote_files(api, original):
    path = prefix(original['key'], original['players'], original['opponent'],
                  original['start'], original['end'], original['mode'])
    revision = api.model_info(original['model_pin']['repo']).sha
    try:
        files = [r.path for r in api.list_repo_tree(original['model_pin']['repo'],
            path_in_repo=path, revision=revision, recursive=True)]
    except EntryNotFoundError:
        files = []
    return revision, files


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--run-name', default='policy-iteration-development-recovered-v1')
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--interval-seconds', type=int, default=300)
    parser.add_argument('--max-hours', type=float, default=12)
    args = parser.parse_args()
    assert args.run_name.startswith('policy-iteration-development-recovered-') and '/' not in args.run_name
    assert 60 <= args.interval_seconds <= 600 and 0 < args.max_hours <= 24
    with ExitStack() as locks:
        for file in [RUNS/'.policy-iteration-development-coordinator.lock',
                     RUNS/'.policy-iteration-harvest.lock', manager.GUARDS/'.grid-launch.lock']:
            handle = locks.enter_context(file.open('a'))
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        admission, prior = admit()
        original_ids = {r['case']: r['job_id'] for r in read(FAILED/'policy-iteration-development-status-v2.json')['jobs']}
        assert len(original_ids) == 550
        assert not coordinator.COMPARISON.exists()
        if not args.execute:
            print({'admitted_replacements': 10, 'maximum_in_flight': 2, 'execute': False})
            return
        directory = RUNS/args.run_name
        directory.mkdir(exist_ok=False)
        attempts = directory/'replacement-guards'
        attempts.mkdir()
        expected = {**prior['code_hashes'], str(Path(__file__).relative_to(ROOT)): digest(Path(__file__)),
                    str(ADMISSION.relative_to(ROOT)): digest(ADMISSION)}
        state = {'pid': os.getpid(), 'started_at': coordinator.now(), 'stage': 'starting',
            'code_hashes': expected, 'original_coordinator_sha256': digest(ORIGINAL),
            'admission_sha256': digest(ADMISSION), 'commands_started': [], 'replacements': {},
            'grid_progress': {}, 'maximum_replacements': 10, 'maximum_in_flight': 2,
            'automatic_retries': False, 'remote_cancellations_allowed': False,
            'local_gradients': False, 'qualification_eligible': False, 'reserved_final_seeds_used': False,
            'original_grid_launch_evidence': prior['grid_launch_evidence']}

        def save():
            temporary = directory/'state.tmp.json'
            write(temporary, {**state, 'updated_at': coordinator.now()})
            temporary.replace(directory/'state.json')

        def run(name, script, *arguments):
            coordinator.check_code(expected)
            assert name not in state['commands_started']
            state['commands_started'].append(name)
            state['stage'] = name
            save()
            with (directory/(name+'.log')).open('x') as log:
                subprocess.run([sys.executable, '-u', str(STRONG/script), *arguments],
                    cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=True)

        def replace(row):
            original = read(FAILED/(row['case']+'-guard.json'))
            canonical = manager.GUARDS/(row['case']+'.json')
            api = HfApi()
            job = api.inspect_job(job_id=original['job_id'])
            revision, files = remote_files(api, original)
            replacement_allowed(original, job.status.stage, read(canonical), files)
            state['stage'] = 'replace-'+row['case']
            save()
            actual_guards = manager.GUARDS
            try:
                manager.GUARDS = attempts
                manager.launch(argparse.Namespace(**{k: original[k] for k in
                    ['key', 'players', 'opponent', 'start', 'end', 'mode']}, execute=True))
            finally:
                manager.GUARDS = actual_guards
            new = read(attempts/(row['case']+'.json'))
            assert new['job_id'] != original['job_id']
            for key in original:
                if key not in ['created_at', 'job_id']:
                    assert original[key] == new[key], key
            new.update(replaces_job_id=original['job_id'], original_guard_sha256=row['original_guard_sha256'],
                recovery_admission_sha256=digest(ADMISSION), missing_artifacts_revision=revision)
            assert read(canonical) == original
            write(directory/(row['case']+'-installed-guard.json'), new)
            temporary = canonical.with_suffix('.tmp')
            with temporary.open('x') as stream:
                json.dump(new, stream, indent=2)
                stream.write('\n')
            temporary.replace(canonical)
            state['replacements'][row['case']] = {'original_job_id': original['job_id'],
                'job_id': new['job_id'], 'guard_sha256': digest(canonical)}
            save()

        save()
        deadline = time.monotonic()+args.max_hours*3600
        try:
            cycle = 0
            while time.monotonic() < deadline:
                cycle += 1
                run(f'status-{cycle:03d}', 'manage-policy-iteration-development.py', 'status')
                snapshot = read(STRONG/'policy-iteration-development-status-v2.json')
                jobs = {r['case']: r for r in snapshot['jobs']}
                assert len(jobs) == 550 and len({r['job_id'] for r in jobs.values()}) == 550
                pending = {r['case']: r for r in admission['cases'] if r['case'] not in state['replacements']}
                for case, job in jobs.items():
                    expected_id = state['replacements'].get(case, {}).get('job_id', original_ids[case])
                    assert job['job_id'] == expected_id
                    if case in state['replacements']:
                        assert digest(manager.GUARDS/(case+'.json')) == state['replacements'][case]['guard_sha256']
                    if case in pending:
                        assert job['job_id'] == pending[case]['job_id'] and job['authoritative_status'] == 'ERROR'
                    else:
                        assert job['authoritative_status'] in ['SCHEDULING', 'RUNNING', 'COMPLETED'], (case, job['authoritative_status'])
                in_flight = sum(jobs[case]['authoritative_status'] != 'COMPLETED' for case in state['replacements'])
                selected = list(pending.values())[:2-in_flight]
                for row in selected:
                    replace(row)
                if selected:
                    run(f'status-{cycle:03d}-after-replacements', 'manage-policy-iteration-development.py', 'status')
                for key in coordinator.KEYS:
                    run(f'collect-{cycle:03d}-'+key, 'manage-policy-iteration-development-grid.py', 'collect', key)
                    state['grid_progress'][key] = coordinator.grid_progress(key)
                    save()
                print({'cycle': cycle, 'replacements': len(state['replacements']), 'progress': state['grid_progress']}, flush=True)
                if all(v == {'verified_shards': 108, 'verified_games': 6720} for v in state['grid_progress'].values()):
                    assert len(state['replacements']) == 10
                    run('compare-all-arms', 'compare-policy-iteration-development.py', '--output', str(coordinator.COMPARISON))
                    comparison = read(coordinator.COMPARISON)
                    assert comparison['full_comparison_complete'] and comparison['games'] == 33600
                    assert set(comparison['complete_arm_summaries']) == {'parent', *coordinator.KEYS}
                    assert len(comparison['comparisons']) == 8 and comparison['qualification_eligible'] is False
                    assert comparison['reserved_final_seeds_used'] is False
                    state['comparison_sha256'] = digest(coordinator.COMPARISON)
                    state['complete_evidence'] = coordinator.archive('policy-iteration-development-complete-evidence-v2',
                        state, ['parent', *coordinator.KEYS], complete=True)
                    state['stage'] = 'development_comparison_complete'
                    save()
                    return
                state['stage'] = 'waiting_for_development_jobs'
                save()
                time.sleep(min(args.interval_seconds, max(0, deadline-time.monotonic())))
            state['stage'] = 'wait_window_ended'
            save()
        except BaseException as error:
            state.update(stage='stopped_with_error', error=type(error).__name__+': '+str(error))
            save()
            raise


if __name__ == '__main__':
    main()
