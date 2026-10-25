"""Bounded fresh-root reference-cost calibration; preserve every original handle."""
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
from surrogate_continuation_runtime_v1 import validate_inputs, INPUTS, PROTOCOL

STRONG = ROOT/'ai/strong'
spec = importlib.util.spec_from_file_location('continuation_bootstrap', STRONG/'launch-opponent-surrogate-runtime-v1.py')
old = importlib.util.module_from_spec(spec); spec.loader.exec_module(old)
BOOTSTRAP = old.BOOTSTRAP.replace('opponent-surrogate-source-manifest.json', 'surrogate-continuation-runtime-source-manifest.json')
OLD_COMMAND = 'python -u ai/strong/opponent-surrogate-collection-job-v1.py "$PLAYERS" 0 1 --mode runtime'
assert BOOTSTRAP.count(OLD_COMMAND) == 1
BOOTSTRAP = BOOTSTRAP.replace(OLD_COMMAND, 'python -u ai/strong/surrogate_continuation_runtime_v1.py "$ROOT_KEY"')
SOURCE = STRONG/'surrogate-continuation-cost-source-v1.json'
PREP = ROOT/'ai/runs/surrogate-continuation-cost-source-prepared-v1'
PREFLIGHT = ROOT/'ai/runs/surrogate-continuation-cost-preflight-v1.json'
REFERENCE = STRONG/'reference-opponent-complete-evidence-v2.json'
PLAN = STRONG/'surrogate-continuation-cost-admission-v1.json'
GUARDS = ROOT/'ai/runs/surrogate-continuation-cost-launches-v1'


def prerequisites():
    source, proof = read(SOURCE), read(PREFLIGHT)
    assert source['remote_archive_verified'] and source['unchanged_base_files'] == 1463 and source['roots'] == 24
    assert digest(ROOT/'ai/runs'/source['archive']) == source['sha256']
    assert source['layout_sha256'] == digest(PREP/'layout-check.json')
    assert source['protocol_sha256'] == digest(PROTOCOL) and source['calibration_only'] is True
    for name, sha in source['new_files'].items():
        assert digest(PREP/'layout'/name) == sha
        if name != str(INPUTS.relative_to(ROOT)): assert digest(ROOT/name) == sha
    inputs = read(PREP/'layout'/INPUTS.relative_to(ROOT)); validate_inputs(inputs)
    assert digest(PREP/'layout'/INPUTS.relative_to(ROOT)) == source['inputs_sha256']
    assert proof['complete'] and proof['source_sha256'] == source['sha256']
    assert proof['layout_public_roots_checked'] == 24 and proof['complete_continuations'] == 32 and proof['caps'] == 0
    assert proof['tests'] >= 6 and proof['source_unchanged']
    assert all(digest(ROOT/name) == sha for name, sha in proof['code_hashes'].items())
    return source, inputs, proof


def resources(reference):
    assert reference['complete'] and reference['remote_archive_verified'] and reference['caps'] == 0
    worst, peak = reference['max_shard_wall_seconds'], reference['max_sampled_process_rss_bytes']
    assert all(type(v) in (int, float) and math.isfinite(v) and v > 0 for v in (worst, peak))
    assert 8*peak < 32e9
    estimate = 900+4*worst; hours = math.ceil(estimate/(.75*3600)); assert hours <= 12
    return {'flavor': 'cpu-upgrade', 'vcpus': 8, 'ram_gb': 32, 'disk_gb': 50, 'workers': 8,
            'timeout_hours': hours, 'max_concurrent': 24, 'estimated_seconds': estimate,
            'historical_worst_seconds': worst, 'historical_peak_rss_bytes': peak,
            'calculation': '15 min setup plus four times the longest prior exact-reference 16-world shard, with 25% timeout reserve. Eight times prior peak RSS allows more workers and reserve. Each new job has only eight worlds per mode but fresh positions can be harder.',
            'limitation': 'A bounded calibration allowance, not a runtime guarantee or admission of the full scientific study. Preserve failures and caps, never substitute easier roots or smaller searches.'}


def dependencies():
    return {str(p.relative_to(ROOT)): digest(p) for p in [Path(__file__), Path(old.__file__),
        STRONG/'surrogate_continuation_runtime_v1.py', STRONG/'build-surrogate-continuation-runtime-source-v1.py',
        STRONG/'surrogate_continuation_study_v1.py', STRONG/'strategic_collection.py']}


def prepare():
    source, inputs, _ = prerequisites()
    plan = {'created_at': datetime.now(timezone.utc).isoformat(), 'source': source,
            'source_descriptor_sha256': digest(SOURCE), 'preflight_sha256': digest(PREFLIGHT),
            'protocol_sha256': digest(PROTOCOL), 'inputs_sha256': source['inputs_sha256'],
            'reference_evidence_sha256': digest(REFERENCE), 'admission': resources(read(REFERENCE)),
            'cases': [{'case': 'surrogate-continuation-cost-v1-'+key, 'key': key,
                       'root_sha256': root['public_root_sha256'], 'continuations': 32} for key, root in inputs['roots'].items()],
            'jobs': 24, 'continuations': 768, 'dependency_hashes': dependencies(),
            'bootstrap_sha256': hashlib.sha256(BOOTSTRAP.encode()).hexdigest(),
            'full_study_admitted': False, 'automatic_retries': False, 'gradients': False,
            'qualification_eligible': False, 'reserved_final_seeds_used': False}
    with PLAN.open('x') as stream: json.dump(plan, stream, indent=2); stream.write('\n')
    print({k: plan[k] for k in ('jobs', 'continuations', 'full_study_admitted')})


def admission(key):
    source, inputs, _ = prerequisites(); plan = read(PLAN)
    assert plan['source'] == source and plan['source_descriptor_sha256'] == digest(SOURCE)
    assert plan['preflight_sha256'] == digest(PREFLIGHT) and plan['protocol_sha256'] == digest(PROTOCOL)
    assert plan['inputs_sha256'] == source['inputs_sha256'] and plan['reference_evidence_sha256'] == digest(REFERENCE)
    assert plan['admission'] == resources(read(REFERENCE)) and plan['dependency_hashes'] == dependencies()
    assert plan['bootstrap_sha256'] == hashlib.sha256(BOOTSTRAP.encode()).hexdigest()
    assert plan['jobs'] == len(plan['cases']) == 24 and plan['continuations'] == 768
    assert plan['cases'] == [{'case': 'surrogate-continuation-cost-v1-'+k, 'key': k,
                            'root_sha256': root['public_root_sha256'], 'continuations': 32} for k, root in inputs['roots'].items()]
    assert all(plan[k] is False for k in ('full_study_admitted', 'automatic_retries', 'gradients', 'qualification_eligible', 'reserved_final_seeds_used'))
    matches = [r for r in plan['cases'] if r['key'] == key]; assert len(matches) == 1
    return plan, source, matches[0]


def launch(key, execute):
    plan, source, row = admission(key)
    if not execute: print({'case': row['case'], 'admitted': True, 'execute': False}); return
    token = get_token(); assert token; GUARDS.mkdir(exist_ok=True)
    with (GUARDS/'.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB); path = GUARDS/(row['case']+'.json')
        if path.exists():
            guard = read(path); assert guard['stage'] == 'launched' and guard['plan_sha256'] == digest(PLAN)
            print({'case': row['case'], 'existing_job_id': guard['job_id'], 'authoritative_status': HfApi().inspect_job(job_id=guard['job_id']).status.stage}); return
        active = 0
        for path0 in GUARDS.glob('*.json'):
            g = read(path0); assert g['stage'] == 'launched' and g['plan_sha256'] == digest(PLAN)
            stage = HfApi().inspect_job(job_id=g['job_id']).status.stage
            assert stage in ('RUNNING', 'SCHEDULING', 'COMPLETED'), 'Inspect an original failure or unknown status before further submission'
            active += stage != 'COMPLETED'
        assert active < plan['admission']['max_concurrent']
        guard = {'case': row['case'], 'key': key, 'row': row, 'stage': 'launch_intent',
                 'plan_sha256': digest(PLAN), 'source': source, 'qualification_eligible': False}
        with path.open('x') as stream: json.dump(guard, stream, indent=2)
        try:
            env = {'SOURCE_ARCHIVE': source['archive'], 'SOURCE_REVISION': source['revision'], 'SOURCE_SHA256': source['sha256'],
                   'SOURCE_MANIFEST_SHA256': source['manifest_sha256'], 'SOURCE_MANIFEST_FILES': str(source['manifest_files']),
                   'INPUTS_SHA256': source['inputs_sha256'], 'PROTOCOL_SHA256': digest(PROTOCOL),
                   'ROOT_KEY': key, 'HF_HUB_DISABLE_PROGRESS_BARS': '1'}
            job = HfApi().run_job(image='python:3.11-slim-bookworm', command=['bash', '-lc', BOOTSTRAP],
                flavor=plan['admission']['flavor'], timeout=f"{plan['admission']['timeout_hours']}h", name=row['case'],
                env=env, secrets={'HF_TOKEN': token}, labels={'project': 'powergrid-ai', 'stage': 'surrogate-continuation-cost-v1', 'case': row['case']})
            guard.update(stage='launched', job_id=job.id)
        except BaseException as error:
            guard.update(stage='launch_unknown', error=type(error).__name__+': '+str(error)); raise
        finally: write(path, guard)
    print({'case': row['case'], 'job_id': guard['job_id']}, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__); sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('prepare'); p = sub.add_parser('launch'); p.add_argument('key'); p.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    if args.command == 'prepare': prepare()
    else: launch(args.key, args.execute)
