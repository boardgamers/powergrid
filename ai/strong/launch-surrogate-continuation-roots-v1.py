"""Admit the fixed fresh-root collection from completed HF endpoint measurements."""
import argparse
from datetime import datetime, timezone
import fcntl
import hashlib
import importlib.util
import json
import math
from pathlib import Path

from huggingface_hub import HfApi, get_token
from strategic_collection import ROOT, read, write, digest
from surrogate_continuation_roots_v1 import contract

STRONG = ROOT/'ai/strong'
spec = importlib.util.spec_from_file_location('root_runtime_launch', STRONG/'launch-surrogate-continuation-roots-runtime-v1.py')
runtime = importlib.util.module_from_spec(spec); spec.loader.exec_module(runtime)
SOURCE, PROTOCOL = runtime.SOURCE, runtime.PROTOCOL
CALIBRATION = STRONG/'surrogate-continuation-roots-calibration-evidence-v1.json'
PLAN = STRONG/'surrogate-continuation-roots-plan-v1.json'
GUARDS = ROOT/'ai/runs/surrogate-continuation-roots-launches-v1'
OLD = 'python -u ai/strong/surrogate-continuation-roots-job-v1.py "$PLAYERS" 0 1 --mode runtime'
NEW = 'python -u ai/strong/surrogate-continuation-roots-job-v1.py "$PLAYERS" "$START" "$END" --mode root'
assert runtime.BOOTSTRAP.count(OLD) == 1
BOOTSTRAP = runtime.BOOTSTRAP.replace(OLD, NEW)


def measured_admission(cells):
    assert set(cells) == {'2', '6'}
    for n, cell in cells.items():
        assert cell['complete'] and cell['games'] == cell['twin_games'] == int(n)*4 and cell['caps'] == 0
        assert 0 < cell['selected_roots'] <= 3*cell['games']
        for value in [cell['raw_evidence_bytes'], *[cell['runtime'][key] for key in ('seconds', 'cpu_seconds', 'sampled_peak_total_rss_bytes')]]:
            assert type(value) in (int, float) and math.isfinite(value) and value > 0
    peak = max(cell['runtime']['sampled_peak_total_rss_bytes'] for cell in cells.values())
    assert 2*peak <= 32*10**9, 'Need a new memory calibration; do not reduce sample coverage'
    worst = max(max(cell['runtime']['seconds'], cell['runtime']['cpu_seconds']/8) for cell in cells.values())
    raw = max(cell['raw_evidence_bytes'] for cell in cells.values())
    for deals in (2, 1):
        estimate = 900+2*deals*worst; hours = math.ceil(estimate/(.75*3600))
        if hours <= 12 and 4*deals*raw <= 50*10**9: break
    else: raise AssertionError('Need a new runtime/storage plan; never shorten games or the fixed study')
    return {'flavor': 'cpu-upgrade', 'vcpus': 8, 'ram_gb': 32, 'disk_gb': 50, 'workers': 8,
            'deals_per_shard': deals, 'timeout_hours': hours, 'max_in_flight': 10,
            'estimated_seconds': estimate, 'measurements': cells,
            'calculation': '15 min setup plus twice measured worst HF endpoint time per whole deal; 25% timeout reserve, 2x peak summed RSS, 4x raw evidence storage. Runtime pairs every game while the main collection is single execution; retain that conservative margin.',
            'limitation': 'Endpoint timings are not hard bounds. Preserve failures and caps; never auto-retry or discard difficult games.'}


def cases(protocol, deals):
    assert deals in (1, 2) and protocol['deals_per_count'] == 2
    rows = []
    for n in protocol['player_counts']:
        for start in range(0, 2, deals):
            end = start+deals
            games = [contract(n, deal, seat, rule, 'root') for deal in range(start, end) for seat in range(n) for rule in range(4)]
            rows.append({'case': f'surrogate-continuation-root-v1-{n}p-{start}-{end}', 'players': n,
                         'start': start, 'end': end, 'games': len(games), 'maximum_roots': 3*len(games)})
    rows.sort(key=lambda row: (-row['players'], row['start']))
    assert sum(row['games'] for row in rows) == protocol['root_collection_games'] == 160
    return rows


def dependencies():
    files = [Path(__file__), Path(runtime.__file__), STRONG/'collect-surrogate-continuation-roots-calibration-v1.py',
             STRONG/'collect-surrogate-continuation-roots-runtime-v1.py', STRONG/'surrogate_continuation_roots_v1.py',
             STRONG/'surrogate_continuation_root_verification_v1.py', STRONG/'population_policy_verification.py',
             STRONG/'strategic_collection.py', STRONG/'population_hybrid_policy.py']
    return {str(path.relative_to(ROOT)): digest(path) for path in files}


def prerequisites():
    assert CALIBRATION.exists(), 'Complete and archive both original HF calibrations before collection admission'
    source, protocol, _ = runtime.prerequisites(); calibration = read(CALIBRATION)
    assert calibration['complete'] and calibration['remote_archive_verified'] and calibration['caps'] == 0
    assert calibration['jobs'] == 2 and calibration['games'] == calibration['twin_games'] == 32
    assert calibration['source'] == source and calibration['protocol_sha256'] == digest(PROTOCOL)
    assert calibration['admission'] == read(runtime.PLAN) and calibration['admission_sha256'] == digest(runtime.PLAN)
    assert all(digest(ROOT/name) == sha for name, sha in calibration['code_hashes'].items())
    folder = ROOT/'ai/runs/surrogate-continuation-roots-calibration-evidence-v1'
    assert digest(folder.with_suffix('.tgz')) == calibration['archive_sha256']
    assert digest(folder/'manifest.json') == calibration['manifest_sha256']
    assert all(digest(folder/name) == sha for name, sha in read(folder/'manifest.json').items())
    return source, protocol, calibration


def prepare():
    source, protocol, calibration = prerequisites()
    resource = measured_admission({n: cell['review'] for n, cell in calibration['cells'].items()})
    plan = {'created_at': datetime.now(timezone.utc).isoformat(), 'source': source,
            'source_descriptor_sha256': digest(SOURCE), 'protocol_sha256': digest(PROTOCOL),
            'calibration_sha256': digest(CALIBRATION), 'admission': resource, 'shards': cases(protocol, resource['deals_per_shard']),
            'games': 160, 'maximum_roots': 480, 'dependency_hashes': dependencies(),
            'bootstrap_sha256': hashlib.sha256(BOOTSTRAP.encode()).hexdigest(), 'automatic_retries': False,
            'gradients': False, 'qualification_eligible': False, 'reserved_final_seeds_used': False}
    with PLAN.open('x') as stream: json.dump(plan, stream, indent=2); stream.write('\n')
    print({'shards': len(plan['shards']), 'games': plan['games'], 'maximum_roots': 480, 'admission': resource})


def admission(case):
    source, protocol, calibration = prerequisites(); plan = read(PLAN)
    assert plan['source'] == source and plan['source_descriptor_sha256'] == digest(SOURCE)
    assert plan['protocol_sha256'] == digest(PROTOCOL) and plan['calibration_sha256'] == digest(CALIBRATION)
    assert plan['admission'] == measured_admission({n: cell['review'] for n, cell in calibration['cells'].items()})
    assert plan['shards'] == cases(protocol, plan['admission']['deals_per_shard'])
    assert plan['games'] == 160 and plan['maximum_roots'] == 480 and plan['dependency_hashes'] == dependencies()
    assert plan['bootstrap_sha256'] == hashlib.sha256(BOOTSTRAP.encode()).hexdigest()
    assert all(plan[key] is False for key in ('automatic_retries', 'gradients', 'qualification_eligible', 'reserved_final_seeds_used'))
    matches = [row for row in plan['shards'] if row['case'] == case]; assert len(matches) == 1
    return plan, source, matches[0]


def launch(case, execute):
    plan, source, row = admission(case)
    if not execute: print({'case': case, 'admitted': True, 'execute': False, 'row': row}); return
    token = get_token(); assert token; GUARDS.mkdir(exist_ok=True)
    with (GUARDS/'.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB); guard = GUARDS/(case+'.json')
        if guard.exists():
            previous = read(guard); assert previous['stage'] == 'launched' and previous['plan_sha256'] == digest(PLAN)
            stage = HfApi().inspect_job(job_id=previous['job_id']).status.stage
            print({'case': case, 'existing_job_id': previous['job_id'], 'authoritative_status': stage}); return
        active = 0
        for path in GUARDS.glob('*.json'):
            previous = read(path); assert previous['stage'] == 'launched' and previous['plan_sha256'] == digest(PLAN)
            stage = HfApi().inspect_job(job_id=previous['job_id']).status.stage
            assert stage in ('RUNNING', 'SCHEDULING', 'COMPLETED'), 'Inspect original failed/uncertain jobs before further submissions'
            active += stage != 'COMPLETED'
        assert active < plan['admission']['max_in_flight']
        record = {'case': case, 'stage': 'launch_intent', 'created_at': datetime.now(timezone.utc).isoformat(),
                  'plan_sha256': digest(PLAN), 'row': row, 'source': source, 'qualification_eligible': False}
        with guard.open('x') as stream: json.dump(record, stream, indent=2)
        try:
            env = {'SOURCE_ARCHIVE': source['archive'], 'SOURCE_REVISION': source['revision'], 'SOURCE_SHA256': source['sha256'],
                   'SOURCE_MANIFEST_SHA256': source['manifest_sha256'], 'SOURCE_MANIFEST_FILES': str(source['manifest_files']),
                   'PROTOCOL_SHA256': digest(PROTOCOL), 'PLAYERS': str(row['players']), 'START': str(row['start']),
                   'END': str(row['end']), 'HF_HUB_DISABLE_PROGRESS_BARS': '1'}
            job = HfApi().run_job(image='python:3.11-slim-bookworm', command=['bash', '-lc', BOOTSTRAP],
                flavor=plan['admission']['flavor'], timeout=f"{plan['admission']['timeout_hours']}h", name=case,
                env=env, secrets={'HF_TOKEN': token}, labels={'project': 'powergrid-ai', 'stage': 'surrogate-continuation-roots-v1', 'case': case})
            record.update(stage='launched', job_id=job.id)
        except BaseException as error:
            record.update(stage='launch_unknown', error=type(error).__name__+': '+str(error)); raise
        finally: write(guard, record)
    print({'case': case, 'job_id': record['job_id']}, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__); sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('prepare'); cmd = sub.add_parser('launch'); cmd.add_argument('case'); cmd.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    if args.command == 'prepare': prepare()
    else: launch(args.case, args.execute)
