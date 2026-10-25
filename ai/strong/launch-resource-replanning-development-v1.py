"""Measured, immutable admission and one-time submission for the resource screen."""
import argparse
from datetime import datetime, timezone
import fcntl
import hashlib
import importlib.util
import json
import math
from pathlib import Path

from huggingface_hub import HfApi, get_token, hf_hub_download
from strategic_collection import ROOT, read, write, digest
from resource_development_v1 import PROTOCOL, case_rows, verify_pins

STRONG = ROOT / 'ai/strong'
spec = importlib.util.spec_from_file_location('resource_runtime_launch', STRONG / 'launch-resource-replanning-runtime-v1.py')
runtime = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runtime)
SOURCE = runtime.SOURCE
CALIBRATION = STRONG / 'resource-hf-calibration-evidence-v1.json'
CALIBRATION_FILES = ROOT / 'ai/runs/resource-hf-calibration-evidence-v1'
PLAN = STRONG / 'resource-replanning-development-plan-v1.json'
GUARDS = ROOT / 'ai/runs/resource-replanning-development-launches-v1'
OLD_COMMAND = 'python -u ai/strong/resource-replanning-development-job-v1.py resource-filter "$PLAYERS" search_geo 0 1 --runtime-pilot'
NEW_COMMAND = 'python -u ai/strong/resource-replanning-development-job-v1.py "$ARM" "$PLAYERS" "$OPPONENT" "$START" "$END"'
assert runtime.BOOTSTRAP.count(OLD_COMMAND) == 1
BOOTSTRAP = runtime.BOOTSTRAP.replace(OLD_COMMAND, NEW_COMMAND)


def prerequisites():
    assert CALIBRATION.exists(), 'Both complete HF endpoints must be verified and archived first'
    pilot, source, _ = runtime.prerequisites()
    calibration = read(CALIBRATION)
    assert calibration['complete'] and calibration['jobs'] == 2 and calibration['games'] == 32
    assert calibration['caps'] == 0 and calibration['exact_local_hf_parity']
    assert calibration['remote_archive_verified'] and calibration['development_admitted'] is False
    assert calibration['source'] == source and calibration['admission'] == read(runtime.ADMISSION)
    assert calibration['admission_sha256'] == digest(runtime.ADMISSION)
    assert calibration['local_pilot_descriptor_sha256'] == digest(runtime.PILOT)
    assert calibration['collector_sha256'] == digest(STRONG / 'collect-resource-hf-calibration-v1.py')
    assert all(digest(ROOT / name) == sha for name, sha in calibration['endpoint_code_hashes'].items())
    assert digest(CALIBRATION_FILES.with_suffix('.tgz')) == calibration['archive_sha256']
    assert digest(CALIBRATION_FILES / 'manifest.json') == calibration['manifest_sha256']
    assert all(digest(CALIBRATION_FILES / name) == sha for name, sha in read(CALIBRATION_FILES / 'manifest.json').items())
    assert set(calibration['cells']) == {'2', '6'}
    measurements = {}
    for n in (2, 6):
        cell = calibration['cells'][str(n)]
        assert cell['summary']['games'] == cell['parity']['games'] == 4 * n
        assert cell['parity']['exact'] and cell['summary']['counts']['rollout_caps'] == 0
        folder = CALIBRATION_FILES / f'ai/runs/resource-replanning-hf-runtime-collected-v1/{cell["case"]}/artifacts/evaluation'
        assert folder.is_dir()
        measurements[str(n)] = {'runtime': cell['runtime'],
                                'raw_evaluation_bytes': sum(p.stat().st_size for p in folder.rglob('*') if p.is_file())}
    return source, calibration, measurements


def measured_admission(measurements, hardware, max_in_flight):
    assert type(max_in_flight) is int and 1 <= max_in_flight <= 32
    assert set(measurements) == {'2', '6'}
    flavor = hardware['flavor']
    assert flavor in runtime.HARDWARE
    expected = runtime.HARDWARE[flavor]
    assert all(hardware[key] == value for key, value in expected.items())
    for cell in measurements.values():
        for value in [cell['raw_evaluation_bytes'], *[cell['runtime'][key] for key in ('seconds', 'cpu_seconds', 'sampled_peak_total_rss_bytes')]]:
            assert type(value) in (int, float) and math.isfinite(value) and value > 0
    peak = max(cell['runtime']['sampled_peak_total_rss_bytes'] for cell in measurements.values())
    assert 2 * peak <= expected['ram_gb'] * 10**9, 'Measured memory headroom is insufficient'
    worst = max(max(cell['runtime']['seconds'], cell['runtime']['cpu_seconds'] / expected['vcpus']) for cell in measurements.values())
    raw = max(cell['raw_evaluation_bytes'] for cell in measurements.values())
    for deals in (4, 2, 1):
        projected = 900 + 2 * deals * worst
        hours = math.ceil(projected / (.75 * 3600))
        if hours <= 12 and 4 * deals * raw <= expected['disk_gb'] * 10**9:
            break
    else:
        raise AssertionError('Measured runtime/storage needs a new execution plan; do not shorten games or search')
    return {'admitted': True, 'flavor': flavor, **expected, 'workers': 8, 'search_workers': 1,
            'samples': 8, 'deals_per_shard': deals, 'timeout_hours': hours, 'max_in_flight': max_in_flight,
            'projected_seconds': projected, 'measurements': measurements,
            'calculation': '15 min setup + twice the slower complete HF endpoint deal times 4/2/1 whole deals; reserve 25% timeout headroom. Require 2x sampled RSS and 4x raw evaluation storage. Keep measured hardware and eight game workers.',
            'limitation': 'Endpoint measurements do not bound every new count/opponent/deal. All caps, errors and timeouts remain failures for review; no automatic retries, selective exclusions, shortened horizons or partial promotion.'}


def dependencies():
    paths = [Path(__file__), Path(runtime.__file__), STRONG / 'resource_development_v1.py',
             STRONG / 'collect-resource-hf-calibration-v1.py', STRONG / 'resource_policy_verification_v1.py',
             STRONG / 'population_policy_verification.py']
    return {str(p.relative_to(ROOT)): digest(p) for p in paths}


def validate_plan(plan, protocol):
    verify_pins(protocol)
    assert plan['planned_games'] == protocol['planned_games_total'] == 3360
    expected = case_rows(protocol, plan['admission']['deals_per_shard'])
    assert sorted(plan['shards'], key=lambda row: row['case']) == sorted(expected, key=lambda row: row['case'])
    assert sum(row['games'] for row in plan['shards']) == 3360
    assert len({row['case'] for row in plan['shards']}) == len(plan['shards'])
    for key in ('automatic_retries', 'gradients', 'qualification_eligible', 'reserved_final_seeds_used'):
        assert plan[key] is False


def prepare(max_in_flight):
    source, calibration, measurements = prerequisites()
    protocol = read(PROTOCOL)
    admission = measured_admission(measurements, calibration['admission']['hardware'], max_in_flight)
    shards = case_rows(protocol, admission['deals_per_shard'])
    shards.sort(key=lambda row: (row['arm'] != 'resource-filter', -row['players'], row['opponent'], row['start']))
    plan = {'created_at': datetime.now(timezone.utc).isoformat(), 'protocol_sha256': digest(PROTOCOL),
            'source': source, 'source_descriptor_sha256': digest(SOURCE),
            'calibration_descriptor_sha256': digest(CALIBRATION), 'admission': admission,
            'shards': shards, 'planned_games': 3360, 'dependency_hashes': dependencies(),
            'bootstrap_sha256': hashlib.sha256(BOOTSTRAP.encode()).hexdigest(),
            'automatic_retries': False, 'gradients': False, 'qualification_eligible': False,
            'reserved_final_seeds_used': False}
    validate_plan(plan, protocol)
    with PLAN.open('x') as stream:
        json.dump(plan, stream, indent=2)
        stream.write('\n')
    print({'plan': str(PLAN), 'shards': len(shards), 'games': 3360, 'admission': admission, 'jobs_launched': 0})


def admission(case):
    source, calibration, measurements = prerequisites()
    assert PLAN.exists(), 'Prepare and review the full measured plan before submitting'
    plan = read(PLAN)
    validate_plan(plan, read(PROTOCOL))
    assert plan['source'] == source and plan['source_descriptor_sha256'] == digest(SOURCE)
    assert plan['calibration_descriptor_sha256'] == digest(CALIBRATION)
    assert plan['protocol_sha256'] == digest(PROTOCOL) and plan['dependency_hashes'] == dependencies()
    assert plan['bootstrap_sha256'] == hashlib.sha256(BOOTSTRAP.encode()).hexdigest()
    assert plan['admission'] == measured_admission(measurements, calibration['admission']['hardware'], plan['admission']['max_in_flight'])
    rows = [row for row in plan['shards'] if row['case'] == case]
    assert len(rows) == 1, 'Case is outside the complete fixed experiment'
    return plan, source, rows[0]


def launch(case, execute):
    plan, source, row = admission(case)
    if not execute:
        print({'case': case, 'admitted': True, 'execute': False, 'row': row, 'admission': plan['admission']})
        return
    token = get_token()
    assert token
    assert digest(hf_hub_download(source['repo'], source['archive'], repo_type='dataset', revision=source['revision'])) == source['sha256']
    GUARDS.mkdir(exist_ok=True)
    with (GUARDS / '.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        api, active = HfApi(), 0
        for path in GUARDS.glob('*.json'):
            previous = read(path)
            assert previous['stage'] == 'launched', 'Reconcile unresolved submission; never retry automatically'
            assert previous['plan_sha256'] == digest(PLAN) and previous['row'] in plan['shards']
            assert previous['case'] == previous['row']['case'] and previous['source'] == source
            assert previous['admission'] == plan['admission']
            stage = api.inspect_job(job_id=previous['job_id']).status.stage
            assert stage not in ('ERROR', 'CANCELED', 'CANCELLED', 'DELETED', 'FAILED', 'TIMEOUT'), 'Review failed jobs before proceeding'
            active += stage != 'COMPLETED'
        assert active < plan['admission']['max_in_flight'], 'Existing development jobs occupy all admitted slots'
        record = {'case': case, 'row': row, 'stage': 'launch_intent', 'created_at': datetime.now(timezone.utc).isoformat(),
                  'plan_sha256': digest(PLAN), 'source': source, 'admission': plan['admission'],
                  'protocol_sha256': digest(PROTOCOL), 'bootstrap_sha256': plan['bootstrap_sha256'],
                  'qualification_eligible': False, 'reserved_final_seeds_used': False}
        guard = GUARDS / (case + '.json')
        with guard.open('x') as stream:
            json.dump(record, stream, indent=2)
        try:
            env = {'SOURCE_ARCHIVE': source['archive'], 'SOURCE_REVISION': source['revision'],
                   'SOURCE_SHA256': source['sha256'], 'SOURCE_MANIFEST_SHA256': source['manifest_sha256'],
                   'PROTOCOL_SHA256': digest(PROTOCOL), 'HF_HUB_DISABLE_PROGRESS_BARS': '1'}
            env.update({key.upper(): str(row[key]) for key in ('arm', 'players', 'opponent', 'start', 'end')})
            job = api.run_job(image='python:3.11-slim-bookworm', command=['bash', '-lc', BOOTSTRAP],
                flavor=plan['admission']['flavor'], timeout=f"{plan['admission']['timeout_hours']}h", name=case,
                secrets={'HF_TOKEN': token}, env=env,
                labels={'project': 'powergrid-ai', 'stage': 'resource-development-v1', 'case': case})
            record.update(stage='launched', job_id=job.id)
        except BaseException as error:
            record.update(stage='launch_unknown', error=type(error).__name__ + ': ' + str(error))
            raise
        finally:
            write(guard, record)
    print({'case': case, 'job_id': record['job_id']}, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    prepare_parser = commands.add_parser('prepare')
    prepare_parser.add_argument('--max-in-flight', type=int, required=True)
    launch_parser = commands.add_parser('launch')
    launch_parser.add_argument('case')
    launch_parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    if args.command == 'prepare':
        prepare(args.max_in_flight)
    else:
        launch(args.case, args.execute)
