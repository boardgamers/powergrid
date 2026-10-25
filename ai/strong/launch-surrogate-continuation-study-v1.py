"""Admit the complete paired study using actual selected-opponent HF timings."""
import argparse
from datetime import datetime, timezone
import fcntl
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re

from huggingface_hub import HfApi, get_token
from strategic_collection import ROOT, read, write, digest
import surrogate_continuation_job_v1 as job
from surrogate_continuation_roots_v1 import object_hash

STRONG = ROOT/'ai/strong'
spec = importlib.util.spec_from_file_location('study_selected_cost', STRONG/'manage-surrogate-continuation-selected-cost-v1.py')
calibration = importlib.util.module_from_spec(spec); spec.loader.exec_module(calibration)
builder = calibration.builder
OLD_COMMAND = 'python -u ai/strong/surrogate_continuation_selected_cost_v1.py'
assert calibration.BOOTSTRAP.count(OLD_COMMAND) == 1
BOOTSTRAP = calibration.BOOTSTRAP.replace(OLD_COMMAND, 'python -u ai/strong/surrogate_continuation_job_v1.py "$ROOT_ID"')
PLAN = STRONG/'surrogate-continuation-study-admission-v1.json'
GUARDS = ROOT/'ai/runs/surrogate-continuation-study-launches-v1'
PROOF = ROOT/'ai/runs/surrogate-continuation-study-management-preflight-v1.json'


def dependencies():
    return {**calibration.dependencies(), str(Path(__file__).relative_to(ROOT)): digest(__file__)}


def allowance(reference, learned):
    assert reference['complete'] and reference['remote_archive_verified'] and reference['caps'] == 0
    assert reference['jobs'] == 24 and reference['continuations'] == 768
    assert learned['complete'] and learned['scope'] == 'selected_runtime_calibration'
    assert learned['roots'] == 24 and learned['continuations'] == 384 and learned['caps'] == 0
    a, b = reference['measurements'], learned['measurements']
    assert set(a) == set(b) == {f'{n}p-{r}-{p}' for n in (2, 6) for r in range(4) for p in ('plant', 'bid', 'building')}
    costs = {}; peaks = []
    for key in sorted(a):
        assert set(a[key]['modes']) == {'neural_population', 'reference_opponent_v1'}
        measurements = [*a[key]['modes'].values(), b[key]]
        for m in measurements:
            assert m['rows'] == 16 and m['memory_sampling_period_seconds'] == .2
            assert all(type(m[k]) in (int, float) and math.isfinite(m[k]) and m[k] > 0
                       for k in ('seconds', 'cpu_seconds', 'sampled_peak_total_rss_bytes', 'memory_samples'))
        costs[key] = sum(m['seconds'] for m in measurements)
        peaks.extend(m['sampled_peak_total_rss_bytes'] for m in measurements)
    estimate = 900 + 2*max(costs.values()); memory = 2*max(peaks)+4e9
    hours = math.ceil(estimate/(.75*3600)); assert hours <= 12 and memory < 32e9
    return {'flavor': 'cpu-upgrade', 'vcpus': 8, 'ram_gb': 32, 'disk_gb': 50, 'workers': 8,
            'timeout_hours': hours, 'max_concurrent': 32, 'estimated_seconds_per_job': estimate,
            'historical_combined_seconds': costs, 'memory_allowance_bytes': memory,
            'historical_peak_rss_bytes': max(peaks),
            'calculation': '15 min setup plus twice the largest measured sum of the three modes on the same timing root; 25% timeout reserve. Twice maximum observed RSS plus 4 GB. All player counts receive this global allowance.',
            'limitation': 'Fresh positions may be slower than calibration. Retain failures and caps, never reduce samples, substitute roots or rerun after an observation timeout. This admits diagnostic fidelity jobs, not full-game strength or 8840U serving latency.'}


def cases(manifest):
    roots = job.manifest_roots(manifest); assert len(roots) == 480
    rows = [{'root_id': root['root_id'], 'case': job.job_name(root), 'root_sha256': object_hash(root),
             'public_root_sha256': root['public_root_sha256'], 'continuations': 48}
            for root in manifest['roots']]
    assert len({row['case'] for row in rows}) == len(rows) == 480
    assert sum(row['continuations'] for row in rows) == 23040
    return rows


def prerequisites():
    assert calibration.RESULT.exists(), 'Complete and independently collect the actual selected-surrogate timing job first'
    timing = calibration.collect()  # An existing result is reaudited locally, never resubmitted.
    assert timing['verified'] and timing['authoritative_status'] == 'COMPLETED'
    source = timing['source']; frozen, manifest, roots, policy = job.validate_inputs(builder.FROZEN)
    assert source['study_inputs_sha256'] == digest(builder.FROZEN/'frozen.json')
    assert source['root_manifest_sha256'] == frozen['root_manifest_sha256']
    assert source['surrogate_policy_sha256'] == job.policy_digest(policy)
    proof = read(PROOF)
    assert proof['complete'] and proof['launcher_code_hashes'] == dependencies() and proof['tests'] >= 8
    assert all(digest(ROOT/name) == sha for name, sha in proof['collector_code_hashes'].items())
    assert proof['test_code_sha256'] == digest(STRONG/'test_surrogate_continuation_study_management_v1.py')
    assert proof['new_hf_jobs'] == 0 and proof['fresh_scientific_continuations'] == 0
    return source, timing, frozen, manifest


def prepare():
    source, timing, frozen, manifest = prerequisites()
    plan = {'created_at': datetime.now(timezone.utc).isoformat(), 'source': source,
            'source_descriptor_sha256': digest(builder.SOURCE), 'selected_cost_result_sha256': digest(calibration.RESULT),
            'reference_cost_evidence_sha256': digest(builder.COST), 'preflight_sha256': digest(PROOF),
            'study_inputs_sha256': digest(builder.FROZEN/'frozen.json'), 'protocol_sha256': digest(job.PROTOCOL),
            'admission': allowance(read(builder.COST), timing['review']), 'cases': cases(manifest),
            'dependency_hashes': dependencies(), 'bootstrap_sha256': hashlib.sha256(BOOTSTRAP.encode()).hexdigest(),
            'jobs': 480, 'continuations': 23040, 'samples': 8, 'actions_per_root': 2, 'modes': list(job.MODES),
            'full_fidelity_study_admitted': True, 'automatic_retries': False, 'gradients': False,
            'full_game_strength_claim': False, 'qualification_eligible': False, 'reserved_final_seeds_used': False}
    assert frozen['continuations'] == plan['continuations']
    with PLAN.open('x') as stream: json.dump(plan, stream, indent=2); stream.write('\n')
    return plan


def admission():
    source, timing, frozen, manifest = prerequisites(); plan = read(PLAN)
    assert plan['source'] == source and plan['source_descriptor_sha256'] == digest(builder.SOURCE)
    assert plan['selected_cost_result_sha256'] == digest(calibration.RESULT)
    assert plan['reference_cost_evidence_sha256'] == digest(builder.COST) and plan['preflight_sha256'] == digest(PROOF)
    assert plan['study_inputs_sha256'] == digest(builder.FROZEN/'frozen.json') and plan['protocol_sha256'] == digest(job.PROTOCOL)
    assert plan['admission'] == allowance(read(builder.COST), timing['review']) and plan['cases'] == cases(manifest)
    assert plan['dependency_hashes'] == dependencies() and plan['bootstrap_sha256'] == hashlib.sha256(BOOTSTRAP.encode()).hexdigest()
    assert plan['jobs'] == len(plan['cases']) == 480 and plan['continuations'] == frozen['continuations'] == 23040
    assert plan['samples'] == 8 and plan['actions_per_root'] == 2 and plan['modes'] == list(job.MODES)
    assert plan['full_fidelity_study_admitted'] is True
    assert all(plan[k] is False for k in ('automatic_retries', 'gradients', 'full_game_strength_claim', 'qualification_eligible', 'reserved_final_seeds_used'))
    return plan, source, manifest


def original(row, source):
    path = GUARDS/(row['case']+'.json'); guard = read(path)
    assert guard['stage'] == 'launched', 'Reconcile the original uncertain submission; never replace it'
    assert guard['row'] == row and guard['source'] == source and guard['plan_sha256'] == digest(PLAN)
    assert guard['case'] == row['case'] and re.fullmatch('[a-f0-9]{24}', guard['job_id'])
    return guard, path


def launch_ready(execute=False):
    plan, source, _ = admission()
    if not execute: return {'jobs': plan['jobs'], 'continuations': plan['continuations'], 'execute': False}
    GUARDS.mkdir(parents=True, exist_ok=True); api = HfApi()
    with (GUARDS/'.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        rows = {row['case']: row for row in plan['cases']}; present = {p.stem for p in GUARDS.glob('*.json')}
        assert present <= set(rows); active = 0; ids = set()
        for case in sorted(present):
            guard, _ = original(rows[case], source); assert guard['job_id'] not in ids; ids.add(guard['job_id'])
            stage = api.inspect_job(job_id=guard['job_id']).status.stage
            assert stage in ('RUNNING', 'SCHEDULING', 'COMPLETED'), 'Inspect the original failed job before submitting more work'
            active += stage != 'COMPLETED'
        assert active <= plan['admission']['max_concurrent']
        available = [row for row in plan['cases'] if row['case'] not in present][:plan['admission']['max_concurrent']-active]
        if not available: return {'submitted': 0, 'active': active, 'original_jobs': len(present)}
        token = get_token(); assert token; submitted = []
        for row in available:
            path = GUARDS/(row['case']+'.json')
            guard = {'case': row['case'], 'row': row, 'stage': 'launch_intent', 'source': source,
                     'created_at': datetime.now(timezone.utc).isoformat(), 'plan_sha256': digest(PLAN), 'qualification_eligible': False}
            with path.open('x') as stream: json.dump(guard, stream, indent=2)
            try:
                env = {'SOURCE_ARCHIVE': source['archive'], 'SOURCE_REVISION': source['revision'], 'SOURCE_SHA256': source['sha256'],
                       'SOURCE_MANIFEST_SHA256': source['manifest_sha256'], 'SOURCE_MANIFEST_FILES': str(source['manifest_files']),
                       'STUDY_INPUTS_SHA256': source['study_inputs_sha256'], 'SURROGATE_POLICY_SHA256': source['surrogate_policy_sha256'],
                       'PROTOCOL_SHA256': digest(job.PROTOCOL), 'ROOT_ID': row['root_id'], 'HF_HUB_DISABLE_PROGRESS_BARS': '1'}
                remote = api.run_job(image='python:3.11-slim-bookworm', command=['bash', '-lc', BOOTSTRAP],
                    flavor=plan['admission']['flavor'], timeout=f"{plan['admission']['timeout_hours']}h", name=row['case'],
                    env=env, secrets={'HF_TOKEN': token}, labels={'project': 'powergrid-ai', 'stage': 'surrogate-continuation-study-v1', 'case': row['case']})
                guard.update(stage='launched', job_id=remote.id); submitted.append(remote.id)
            except BaseException as error:
                guard.update(stage='launch_unknown', failure_type=type(error).__name__); raise
            finally: write(path, guard)
            print({'case': row['case'], 'job_id': remote.id}, flush=True)
        return {'submitted': len(submitted), 'active': active+len(submitted), 'original_jobs': len(present)+len(submitted)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__); parser.add_argument('operation', choices=['prepare', 'launch-ready'])
    parser.add_argument('--execute', action='store_true'); args = parser.parse_args()
    assert args.operation == 'launch-ready' or not args.execute
    result = prepare() if args.operation == 'prepare' else launch_ready(args.execute)
    print({k: result[k] for k in ('jobs', 'continuations', 'execute', 'submitted', 'active', 'original_jobs') if k in result})
