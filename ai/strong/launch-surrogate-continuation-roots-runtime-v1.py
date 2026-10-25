"""Two bounded root-capture calibrations, preserving original HF job handles."""
import argparse
from datetime import datetime, timezone
import fcntl
import hashlib
import importlib.util
import json
import math

from huggingface_hub import HfApi, get_token
from strategic_collection import ROOT, read, write, digest

STRONG = ROOT/'ai/strong'
spec = importlib.util.spec_from_file_location('capture_bootstrap', STRONG/'launch-opponent-surrogate-runtime-v1.py')
old = importlib.util.module_from_spec(spec); spec.loader.exec_module(old)
BOOTSTRAP = old.BOOTSTRAP.replace('opponent-surrogate-source-manifest.json', 'surrogate-continuation-roots-source-manifest.json')
assert BOOTSTRAP.count('ai/strong/opponent-surrogate-collection-job-v1.py') == 1
BOOTSTRAP = BOOTSTRAP.replace('ai/strong/opponent-surrogate-collection-job-v1.py', 'ai/strong/surrogate-continuation-roots-job-v1.py')
SOURCE = STRONG/'surrogate-continuation-roots-source-v1.json'
PROTOCOL = STRONG/'surrogate-continuation-protocol-v1.json'
PREFLIGHT = ROOT/'ai/runs/surrogate-continuation-roots-preflight-v1/status.json'
LAYOUT = ROOT/'ai/runs/surrogate-continuation-roots-source-prepared-v1/layout-check.json'
PLAN = STRONG/'surrogate-continuation-roots-runtime-admission-v1.json'
GUARDS = ROOT/'ai/runs/surrogate-continuation-roots-runtime-launches-v1'


def prerequisites():
    source, protocol, proof, layout = map(read, (SOURCE, PROTOCOL, PREFLIGHT, LAYOUT))
    assert source['remote_archive_verified'] and source['unchanged_base_files'] == 1463
    assert digest(ROOT/'ai/runs'/source['archive']) == source['sha256']
    assert source['protocol_sha256'] == digest(PROTOCOL) and source['preflight_sha256'] == digest(PREFLIGHT)
    assert all(digest(ROOT/name) == sha for name, sha in source['new_files'].items())
    assert all(digest(ROOT/name) == sha for name, sha in proof['code_hashes'].items())
    assert proof['stage'] == 'complete' and proof['complete_games'] == 2 and proof['paired_executions'] == 4 and proof['caps'] == 0
    assert proof['resealed_duplicate_rejected'] and proof['runtime_unchanged']
    assert layout['source_sha256'] == source['sha256'] and layout['package_imports_correct'] and layout['exact_policy_requests'] == 20
    return source, protocol, proof


def prepare():
    source, protocol, proof = prerequisites()
    worst = max(case['seconds'] for case in proof['cases'].values())
    assert math.isfinite(worst) and worst > 0
    estimate = 900 + 4*3*worst
    assert estimate < 4*3600, 'Need a larger measured calibration allowance; never shorten games'
    plan = {'created_at': datetime.now(timezone.utc).isoformat(), 'source_descriptor_sha256': digest(SOURCE),
            'protocol_sha256': digest(PROTOCOL), 'preflight_sha256': digest(PREFLIGHT), 'layout_check_sha256': digest(LAYOUT),
            'launcher_sha256': digest(__file__), 'bootstrap_source_sha256': digest(old.__file__),
            'bootstrap_sha256': hashlib.sha256(BOOTSTRAP.encode()).hexdigest(), 'players': [2, 6],
            'jobs': 2, 'max_concurrent': 2, 'games': 32, 'paired_executions': 64,
            'flavor': 'cpu-upgrade', 'vcpus': 8, 'ram_gb': 32, 'workers': protocol['workers'], 'timeout_hours': 4,
            'local_worst_paired_case_seconds': worst, 'estimated_seconds': estimate,
            'scope': 'Bounded root-capture calibration only. Local endpoint timings are not HF guarantees. Preserve failures and collect measured wall/CPU/memory before full root collection.',
            'collection_admitted': False, 'continuation_jobs_admitted': False, 'automatic_retries': False,
            'gradients': False, 'qualification_eligible': False, 'reserved_final_seeds_used': False}
    with PLAN.open('x') as stream: json.dump(plan, stream, indent=2); stream.write('\n')
    print({k: plan[k] for k in ('jobs', 'games', 'paired_executions', 'flavor', 'timeout_hours', 'estimated_seconds')})


def launch(players, execute):
    assert type(players) is int and players in (2, 6)
    source, _, _ = prerequisites(); plan = read(PLAN)
    for key, path in [('source_descriptor_sha256', SOURCE), ('protocol_sha256', PROTOCOL), ('preflight_sha256', PREFLIGHT),
                      ('layout_check_sha256', LAYOUT), ('launcher_sha256', __file__), ('bootstrap_source_sha256', old.__file__)]:
        assert plan[key] == digest(path)
    assert plan['bootstrap_sha256'] == hashlib.sha256(BOOTSTRAP.encode()).hexdigest()
    assert plan['players'] == [2, 6] and plan['jobs'] == plan['max_concurrent'] == 2 and not plan['collection_admitted']
    case = f'surrogate-continuation-runtime-v1-{players}p-0-1'
    if not execute:
        print({'case': case, 'admitted': True, 'execute': False, 'plan_sha256': digest(PLAN)}); return
    token = get_token(); assert token; GUARDS.mkdir(exist_ok=True)
    with (GUARDS/'.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        guard = GUARDS/(case+'.json')
        if guard.exists():
            previous = read(guard); assert previous['stage'] == 'launched' and previous['plan_sha256'] == digest(PLAN)
            job = HfApi().inspect_job(job_id=previous['job_id'])
            print({'case': case, 'existing_job_id': previous['job_id'], 'authoritative_status': job.status.stage}); return
        active = 0
        for path in GUARDS.glob('*.json'):
            old_guard = read(path); assert old_guard['stage'] == 'launched' and old_guard['plan_sha256'] == digest(PLAN)
            stage = HfApi().inspect_job(job_id=old_guard['job_id']).status.stage
            assert stage in ('RUNNING', 'SCHEDULING', 'COMPLETED'), 'Inspect the original failed or uncertain job'
            active += stage != 'COMPLETED'
        assert active < plan['max_concurrent']
        record = {'case': case, 'stage': 'launch_intent', 'created_at': datetime.now(timezone.utc).isoformat(),
                  'players': players, 'plan_sha256': digest(PLAN), 'source': source, 'qualification_eligible': False}
        with guard.open('x') as stream: json.dump(record, stream, indent=2)
        try:
            env = {'SOURCE_ARCHIVE': source['archive'], 'SOURCE_REVISION': source['revision'], 'SOURCE_SHA256': source['sha256'],
                   'SOURCE_MANIFEST_SHA256': source['manifest_sha256'], 'SOURCE_MANIFEST_FILES': str(source['manifest_files']),
                   'PROTOCOL_SHA256': digest(PROTOCOL), 'PLAYERS': str(players), 'HF_HUB_DISABLE_PROGRESS_BARS': '1'}
            job = HfApi().run_job(image='python:3.11-slim-bookworm', command=['bash', '-lc', BOOTSTRAP],
                flavor=plan['flavor'], timeout=f"{plan['timeout_hours']}h", name=case, secrets={'HF_TOKEN': token}, env=env,
                labels={'project': 'powergrid-ai', 'stage': 'surrogate-continuation-runtime-v1', 'case': case})
            record.update(stage='launched', job_id=job.id)
        except BaseException as error:
            record.update(stage='launch_unknown', error=type(error).__name__+': '+str(error)); raise
        finally: write(guard, record)
    print({'case': case, 'job_id': record['job_id']}, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__); sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('prepare'); cmd = sub.add_parser('launch')
    cmd.add_argument('players', type=int, choices=[2, 6]); cmd.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    if args.command == 'prepare': prepare()
    else: launch(args.players, args.execute)
