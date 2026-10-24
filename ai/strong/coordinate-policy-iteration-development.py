"""Run the prescribed development grid only after exact trained verification.

Eight whole-deal runtime probes admit four immutable 108-shard grids. All four
ensembles and the parent enter the existing 33,600-game comparison. No final
seeds, altered opponents/horizons, retries, local gradients, or promotion.
"""
import argparse
from datetime import datetime, timezone
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

from strategic_collection import ROOT, read, write, digest
from policy_iteration_development import PROTOCOL, SOURCE, case_key, pin_hash
from policy_iteration_job import admission
from policy_iteration_evidence_archive import upload_evidence

STRONG, RUNS = ROOT/'ai/strong', ROOT/'ai/runs'
LABELS = RUNS/'policy-iteration-harvest-recovered-v2/state.json'
TRAINING = RUNS/'policy-iteration-training-harvest-v2/state.json'
KEYS = ['frozen-0', 'frozen-1', 'public-0', 'public-1']
COMPARISON = STRONG/'policy-iteration-development-comparison-v2.json'
LABEL_WAIT = {'starting', 'running', 'waiting'}
TRAINING_WAIT = {'starting', 'waiting_for_training_submission', 'waiting_for_training_completion',
                 'collect-frozen', 'collect-public', 'archive-frozen', 'archive-public'}


def module(name, file):
    spec = importlib.util.spec_from_file_location(name, STRONG/file)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


grid = module('coordinated_grid', 'manage-policy-iteration-development-grid.py')
trained = module('coordinated_training_collection', 'harvest-policy-iteration-training.py')


def now():
    return datetime.now(timezone.utc).isoformat()


def upstreams_ready(labels, training):
    assert labels['qualification_eligible'] is False and training['qualification_eligible'] is False
    assert training['remote_submissions_allowed'] is False and training['local_gradients'] is False
    assert labels['stage'] in LABEL_WAIT | {'complete'}, 'Label/reference collector needs review'
    assert training['stage'] in TRAINING_WAIT | {'both_heads_verified_and_archived'}, 'Training collector needs review'
    if labels['stage'] != 'complete' or training['stage'] != 'both_heads_verified_and_archived':
        return False
    assert labels['labels_complete'] and labels['label_shards_verified'] == 948
    assert labels['parent_reference_complete'] and labels['parent_shards_verified'] == 108
    assert labels['parent_games_verified'] == 6720
    assert set(training['heads_verified']) == {'frozen', 'public'}
    assert set(training['training_jobs']) == {'frozen', 'public'}
    assert len(set(training['training_jobs'].values())) == 2
    for head, evidence in training['heads_verified'].items():
        assert evidence['head_type'] == head and evidence['job_id'] == training['training_jobs'][head]
        assert evidence['remote_archive_verified'] and evidence['qualification_eligible'] is False
        assert set(evidence['candidate_pins']) == {head+'-0', head+'-1'}
    return True


def live_waiter(state, name, final):
    if state['stage'] != final:
        command = Path('/proc', str(state['pid']), 'cmdline').read_bytes()
        assert name.encode() in command, 'Inspect the missing upstream process;do not restart it here'


def expected_code():
    expected = dict(read(TRAINING)['code_hashes'])
    source = grid.manager.source_check()
    expected.update(source['overlays'])
    files = [Path(__file__), SOURCE, PROTOCOL, STRONG/'manage-policy-iteration-development.py',
             STRONG/'manage-policy-iteration-development-grid.py', STRONG/'compare-policy-iteration-development.py',
             STRONG/'policy-iteration-development-preflight-v2.json', STRONG/'arena_statistics.py',
             STRONG/'compare-population-screens.py', STRONG/'final-protocol-multiplayer.json']
    expected.update({str(p.relative_to(ROOT)): digest(p) for p in files})
    check_code(expected)
    return expected


def check_code(expected):
    assert all(digest(ROOT/file) == sha for file, sha in expected.items()), 'Prescribed code changed;review before proceeding'
    assert digest(STRONG/'final-protocol-multiplayer.json') == read(PROTOCOL)['final_protocol_sha256']


def admitted_pins(training):
    design, data_pin, source = admission()
    result = {}
    for head in ['frozen', 'public']:
        guard = read(trained.GUARDS/(head+'.json'))
        assert guard['job_id'] == training['training_jobs'][head]
        record, pins = trained.verify_outputs(head, guard, data_pin, source)
        evidence = training['heads_verified'][head]
        assert evidence['verified_sha256'] == digest(trained.VERIFIED/head/'verified.json')
        assert pins == evidence['candidate_pins']
        result.update({key: value['pin'] for key, value in pins.items()})
    assert set(result) == set(KEYS)
    assert design['seeds'] == read(PROTOCOL)['candidate_seeds']
    return result


def probe_rows():
    return [{'key': key, 'players': n, 'opponent': 'search_geo', 'start': 0, 'end': 1, 'mode': 'smoke',
             'case': case_key(key, n, 'search_geo', 0, 1, 'smoke')} for key in KEYS for n in [2, 6]]


def matching_probe(row, source, pins):
    guard = read(grid.manager.GUARDS/(row['case']+'.json'))
    assert guard['stage'] == 'launched'
    for key in ['key', 'players', 'opponent', 'start', 'end', 'mode', 'case']:
        assert guard[key] == row[key]
    assert guard['source'] == source and guard['model_pin'] == pins[row['key']]
    assert guard['model_pin_sha256'] == pin_hash(pins[row['key']])
    assert guard['protocol_sha256'] == digest(PROTOCOL) and guard['flavor'] == 'cpu-upgrade'
    assert guard['timeout_hours'] == 4 and guard['qualification_eligible'] is False
    return guard


def grid_progress(key):
    plan = grid.require_plan(key)
    reports = []
    for row in plan['shards']:
        directory = grid.manager.VERIFIED/row['case']
        if not (directory/'verified.json').exists():
            continue
        record = read(directory/'verified.json')
        guard = grid.matching_guard(grid.manager.GUARDS/(row['case']+'.json'), row, plan)
        assert record['verified'] and record['job_id'] == guard['job_id']
        assert record['source'] == plan['source'] and record['model_pin_sha256'] == plan['model_pin_sha256']
        for file, sha in record['artifacts'].items():
            assert digest(directory/file) == sha
        reports.append(record)
    return {'verified_shards': len(reports), 'verified_games': sum(r['summary']['games'] for r in reports)}


def archive(name, state, keys, *, complete=False):
    out = RUNS/name
    out.mkdir(exist_ok=False)
    write(out/'coordinator-state.json', state)
    for file in ['coordinate-policy-iteration-development.py', 'policy-iteration-development-protocol-v2.json',
                 'policy-iteration-development-source-v2.json', 'policy-iteration-development-preflight-v2.json',
                 'manage-policy-iteration-development.py', 'manage-policy-iteration-development-grid.py',
                 'compare-policy-iteration-development.py', 'policy_iteration_evidence_archive.py']:
        shutil.copy2(STRONG/file, out/file)
    for key in keys:
        if key != 'parent':
            shutil.copy2(trained.PINS/(key+'.json'), out/(key+'-pin.json'))
        cases = [case_key(key, n, 'search_geo', 0, 1, 'smoke') for n in [2, 6]]
        if grid.plan_path(key).exists():
            plan = grid.require_plan(key)
            shutil.copy2(grid.plan_path(key), out/(key+'-plan.json'))
            cases += [r['case'] for r in plan['shards']]
        for case in cases:
            guard = grid.manager.GUARDS/(case+'.json')
            target = out/'guards'/guard.name
            target.parent.mkdir(exist_ok=True)
            shutil.copy2(guard, target)
            verified = grid.manager.VERIFIED/case
            if (verified/'verified.json').exists():
                record = read(verified/'verified.json')
                for file, sha in record['artifacts'].items():
                    assert digest(verified/file) == sha
                shutil.copytree(verified, out/'verified'/case)
    if complete:
        shutil.copy2(COMPARISON, out/COMPARISON.name)
    write(out/'manifest.json', {str(p.relative_to(out)): digest(p) for p in out.rglob('*') if p.is_file()})
    evidence = {**upload_evidence(out), 'keys': keys, 'complete_development_comparison': complete,
                'qualification_eligible': False, 'reserved_final_seeds_used': False}
    write(STRONG/(name+'.json'), evidence)
    return evidence


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--run-name', required=True)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--once', action='store_true', help='Observe readiness once;never dispatch jobs')
    parser.add_argument('--interval-seconds', type=int, default=300)
    parser.add_argument('--max-hours', type=float, default=24)
    args = parser.parse_args()
    assert re.fullmatch(r'policy-iteration-development-coordinator-[a-z0-9-]+', args.run_name)
    assert 60 <= args.interval_seconds <= 600 and 0 < args.max_hours <= 24
    deadline = time.monotonic()+args.max_hours*3600
    with (RUNS/'.policy-iteration-development-coordinator.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        assert not COMPARISON.exists(), 'Preserve existing comparison'
        for key in KEYS:
            assert not grid.plan_path(key).exists()
            assert not list(grid.manager.GUARDS.glob('smoke-'+key+'-*.json'))
            assert not list(grid.manager.GUARDS.glob('development-'+key+'-*.json'))
        directory = RUNS/args.run_name
        directory.mkdir(exist_ok=False)
        expected = expected_code()
        state = {'pid': os.getpid(), 'started_at': now(), 'stage': 'starting', 'execute': args.execute,
                 'code_hashes': expected, 'interval_seconds': args.interval_seconds, 'max_hours': args.max_hours,
                 'commands_started': [], 'runtime_jobs': {}, 'grids_submitted': {}, 'grid_progress': {},
                 'remote_cancellations_allowed': False, 'automatic_retries': False, 'local_gradients': False,
                 'qualification_eligible': False, 'reserved_final_seeds_used': False}

        def save():
            path = directory/'state.tmp.json'
            write(path, {**state, 'updated_at': now()})
            path.replace(directory/'state.json')

        def run(name, script, *arguments):
            check_code(expected)
            assert name not in state['commands_started']
            state.update(stage=name)
            state['commands_started'].append(name)
            save()
            with (directory/(name+'.log')).open('x') as log:
                subprocess.run([sys.executable, '-u', str(STRONG/script), *arguments],
                               cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=True)

        def sleep():
            time.sleep(min(args.interval_seconds, max(0, deadline-time.monotonic())))

        save()
        try:
            while time.monotonic() < deadline:
                check_code(expected)
                labels, training = read(LABELS), read(TRAINING)
                ready = upstreams_ready(labels, training)
                state.update(stage='upstreams_ready' if ready else 'waiting_for_verified_training_and_parent',
                             upstream_label_stage=labels['stage'], upstream_training_stage=training['stage'],
                             label_shards_verified=labels.get('label_shards_verified'),
                             parent_shards_verified=labels.get('parent_shards_verified'))
                save()
                if args.once or not args.execute:
                    print({k: state[k] for k in ['stage', 'runtime_jobs', 'grids_submitted']}, flush=True)
                    return
                if ready:
                    break
                live_waiter(labels, 'policy-iteration-harvest-recovered-v2', 'complete')
                live_waiter(training, 'policy-iteration-training-harvest-v2', 'both_heads_verified_and_archived')
                sleep()
            else:
                state['stage'] = 'wait_window_ended'
                save()
                return
            # The original status/collection loop must have released its lock,
            # so it cannot observe new guards while they are still launch intents.
            with (RUNS/'.policy-iteration-harvest.lock').open('a') as prior:
                while True:
                    try:
                        fcntl.flock(prior, fcntl.LOCK_EX | fcntl.LOCK_NB)
                        break
                    except BlockingIOError:
                        if time.monotonic() >= deadline:
                            state['stage'] = 'wait_window_ended'
                            save()
                            return
                        state['stage'] = 'waiting_for_original_collector_lock'
                        save()
                        sleep()
                pins = admitted_pins(training)
                source = grid.manager.source_check()
                state['model_pins'] = pins
                state['source'] = source
                save()
                probes = probe_rows()
                for row in probes:
                    run('launch-'+row['case'], 'manage-policy-iteration-development.py', 'launch', row['key'],
                        str(row['players']), 'search_geo', '0', '1', '--mode', 'smoke', '--execute')
                    guard = matching_probe(row, source, pins)
                    state['runtime_jobs'][row['case']] = guard['job_id']
                    save()
                assert len(set(state['runtime_jobs'].values())) == 8
                state['runtime_launch_evidence'] = archive('policy-iteration-candidate-runtime-launch-evidence-v2', state, KEYS)
                save()
                cycle = 0
                while time.monotonic() < deadline:
                    cycle += 1
                    run(f'status-{cycle:03d}', 'manage-policy-iteration-development.py', 'status')
                    snapshot = read(STRONG/'policy-iteration-development-status-v2.json')
                    jobs = {row['case']: row for row in snapshot['jobs']}
                    assert len(jobs) == len(snapshot['jobs']) == len({j['job_id'] for j in jobs.values()})
                    for case, job in jobs.items():
                        assert job['authoritative_status'] in ['SCHEDULING', 'RUNNING', 'COMPLETED'], 'Existing job needs review;no retry'
                    for row in probes:
                        guard = matching_probe(row, source, pins)
                        assert jobs[row['case']]['job_id'] == guard['job_id']
                        if jobs[row['case']]['authoritative_status'] == 'COMPLETED' and not (grid.manager.VERIFIED/row['case']/'verified.json').exists():
                            run('collect-'+row['case'], 'manage-policy-iteration-development.py', 'collect', row['key'],
                                str(row['players']), 'search_geo', '0', '1', '--mode', 'smoke')
                    launched = False
                    for key in KEYS:
                        if key in state['grids_submitted']:
                            continue
                        if not all((grid.manager.VERIFIED/case_key(key, n, 'search_geo', 0, 1, 'smoke')/'verified.json').exists() for n in [2, 6]):
                            continue
                        run('plan-'+key, 'manage-policy-iteration-development-grid.py', 'plan', key)
                        run('launch-grid-'+key, 'manage-policy-iteration-development-grid.py', 'launch', key, '--limit', '108', '--execute')
                        plan = grid.require_plan(key)
                        handles = {row['case']: grid.matching_guard(grid.manager.GUARDS/(row['case']+'.json'), row, plan)['job_id'] for row in plan['shards']}
                        assert len(handles) == len(set(handles.values())) == 108
                        state['grids_submitted'][key] = handles
                        save()
                        state.setdefault('grid_launch_evidence', {})[key] = archive('policy-iteration-'+key+'-grid-launch-evidence-v2', state, [key])
                        save()
                        launched = True
                    if launched:
                        continue  # Refresh statuses to include the new guards before collection.
                    for key in state['grids_submitted']:
                        age = (datetime.now(timezone.utc)-datetime.fromisoformat(snapshot['checked_at'])).total_seconds()
                        if age >= 3000:
                            run(f'status-{cycle:03d}-before-'+key, 'manage-policy-iteration-development.py', 'status')
                            snapshot = read(STRONG/'policy-iteration-development-status-v2.json')
                        run(f'collect-grid-{cycle:03d}-'+key, 'manage-policy-iteration-development-grid.py', 'collect', key)
                        state['grid_progress'][key] = grid_progress(key)
                    save()
                    if set(state['grid_progress']) == set(KEYS) and all(v == {'verified_shards': 108, 'verified_games': 6720} for v in state['grid_progress'].values()):
                        run('compare-all-arms', 'compare-policy-iteration-development.py', '--output', str(COMPARISON))
                        comparison = read(COMPARISON)
                        assert comparison['full_comparison_complete'] and comparison['games'] == 33600
                        assert set(comparison['complete_arm_summaries']) == {'parent', *KEYS}
                        assert len(comparison['comparisons']) == 8 and comparison['qualification_eligible'] is False
                        assert comparison['reserved_final_seeds_used'] is False
                        state['comparison_sha256'] = digest(COMPARISON)
                        state['complete_evidence'] = archive('policy-iteration-development-complete-evidence-v2', state, ['parent', *KEYS], complete=True)
                        state['stage'] = 'development_comparison_complete'
                        save()
                        print({'stage': state['stage'], 'games': 33600, 'qualified': False}, flush=True)
                        return
                    state['stage'] = 'waiting_for_development_jobs'
                    save()
                    print({'cycle': cycle, 'grids_submitted': list(state['grids_submitted']), 'verified': state['grid_progress']}, flush=True)
                    sleep()
                state['stage'] = 'wait_window_ended'
                save()
        except BaseException as error:
            state.update(stage='stopped_with_error', error=type(error).__name__+': '+str(error))
            save()
            raise


if __name__ == '__main__':
    main()
