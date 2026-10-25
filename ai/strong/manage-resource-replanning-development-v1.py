"""Collect fixed resource-screen jobs; reject partial or mismatched evidence."""
import argparse
import ast
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import re

from huggingface_hub import HfApi, hf_hub_download
from strategic_collection import ROOT, read, write, digest
from population_policy_verification import extract_verified, finite, integer
from resource_policy_verification_v1 import verify_evaluation

STRONG = ROOT / 'ai/strong'


def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, STRONG / filename)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


launcher = module('resource_screen_launcher', 'launch-resource-replanning-development-v1.py')
wrapper = module('resource_screen_wrapper', 'resource-replanning-development-job-v1.py')
COLLECTED = ROOT / 'ai/runs/resource-replanning-development-collected-v1'
FAILED = {'ERROR', 'CANCELED', 'CANCELLED', 'DELETED', 'FAILED', 'TIMEOUT'}
ACTIVE = {'RUNNING', 'SCHEDULING'}


def code_hashes():
    paths = [Path(__file__), Path(wrapper.__file__), STRONG / 'strategic_collection.py', STRONG / 'arena_statistics.py',
             STRONG / 'resource_policy_verification_v1.py', STRONG / 'population_policy_verification.py']
    return {**launcher.dependencies(), **{str(p.relative_to(ROOT)): digest(p) for p in paths}}


def identity(case):
    plan, source, row = launcher.admission(case)
    path = launcher.GUARDS / (case + '.json')
    guard = read(path)
    assert guard['case'] == case and guard['row'] == row and guard['stage'] == 'launched'
    assert re.fullmatch('[a-f0-9]{24}', guard['job_id'])
    assert guard['source'] == source and guard['admission'] == plan['admission']
    assert guard['plan_sha256'] == digest(launcher.PLAN)
    assert guard['protocol_sha256'] == digest(launcher.PROTOCOL)
    assert guard['bootstrap_sha256'] == plan['bootstrap_sha256']
    assert guard['qualification_eligible'] is guard['reserved_final_seeds_used'] is False
    return plan, source, row, path, guard


def inspect(case):
    _, _, _, path, guard = identity(case)
    job = HfApi().inspect_job(job_id=guard['job_id'])
    return {'case': case, 'job_id': guard['job_id'], 'authoritative_status': job.status.stage,
            'checked_at': datetime.now(timezone.utc).isoformat(), 'guard_sha256': digest(path)}


def verify_artifacts(artifacts, row, source, protocol, evidence):
    manifest = read(artifacts / 'manifest.json')
    assert {str(p.relative_to(artifacts)) for p in artifacts.rglob('*') if p.is_file()} == set(manifest) | {'manifest.json'}
    assert all(digest(artifacts / name) == sha for name, sha in manifest.items())
    assert digest(artifacts / 'manifest.json') == evidence['manifest_sha256']
    assert len(manifest) + 1 == evidence['archived_files']
    case, _, expected = wrapper.contract(protocol, row['arm'], row['players'], row['opponent'], row['start'], row['end'])
    expected['runtime'] = '/workspace'
    assert case == row['case']
    check = read(artifacts / 'resource-check.json')
    assert check['case'] == case and check['stage'] == 'complete' and check['runtime_pilot'] is False
    assert check['source_revision'] == source['revision'] and check['source_sha256'] == source['sha256']
    assert check['protocol_sha256'] == digest(launcher.PROTOCOL) and check['model_pin'] == protocol['model_pin']
    assert check['expected_config'] == expected
    assert check['job_runner_sha256'] == source['new_files']['ai/strong/resource-replanning-development-job-v1.py']
    assert check['sampler_sha256'] == source['base']['new_files']['ai/strong/resource-replanning-runtime-pilot-v1.py']
    for key in ('automatic_retries', 'gradients', 'qualification_eligible', 'reserved_final_seeds_used'):
        assert check[key] is False
    summary = verify_evaluation(artifacts / 'evaluation', {**expected, 'output': f'/workspace/ai/runs/{case}/evaluation'})
    assert summary == read(artifacts / 'summary.json')
    assert check['games'] == summary['games'] == row['games']
    measured = read(artifacts / 'runtime.json')
    assert measured == check['runtime']
    for key in ('seconds', 'cpu_seconds'):
        finite(measured[key])
        assert measured[key] > 0
    for key in ('sampled_peak_total_rss_bytes', 'memory_samples'):
        integer(measured[key], 1)
    assert measured['memory_sampling_period_seconds'] == .1
    finite(check['seconds'])
    assert check['seconds'] >= measured['seconds'] >= summary['wall_seconds']
    return {'summary': summary, 'runtime': measured}


def verified_receipt(case, full=False):
    path = COLLECTED / case / 'verified.json'
    if not path.exists():
        return None
    _, source, row, guard_path, guard = identity(case)
    checked = read(path)
    assert checked['verified'] is True and checked['authoritative_status'] == 'COMPLETED'
    assert checked['job_id'] == guard['job_id'] and checked['guard_sha256'] == digest(guard_path)
    assert checked['row'] == row and checked['source'] == source
    assert checked['plan_sha256'] == digest(launcher.PLAN) and checked['protocol_sha256'] == digest(launcher.PROTOCOL)
    assert checked['code_hashes'] == code_hashes()
    assert checked['qualification_eligible'] is checked['reserved_final_seeds_used'] is False
    assert checked['evidence']['remote_archive_verified'] is True
    assert checked['summary']['games'] == row['games'] and checked['summary']['all_receipts_verified']
    assert checked['summary']['counts']['rollout_caps'] == 0
    if full:
        result = verify_artifacts(path.parent / 'artifacts', row, source, read(launcher.PROTOCOL), checked['evidence'])
        assert all(checked[key] == value for key, value in result.items())
    return checked


def collect(case):
    hashes = code_hashes()
    _, source, row, _, _ = identity(case)
    status = inspect(case)
    folder = COLLECTED / case
    folder.mkdir(parents=True, exist_ok=True)
    write(folder / 'status.json', status)
    if status['authoritative_status'] != 'COMPLETED' and status['authoritative_status'] not in FAILED:
        return status
    logs = '\n'.join(str(line) for line in HfApi().fetch_job_logs(job_id=status['job_id'], follow=False))
    (folder / 'job.log').write_text(logs)
    if status['authoritative_status'] != 'COMPLETED':
        return {**status, 'failed': True}
    receipts = []
    for line in logs.splitlines():
        if not line.startswith('{'):
            continue
        try:
            value = ast.literal_eval(line)
        except (ValueError, SyntaxError):
            continue
        if isinstance(value, dict) and isinstance(value.get('status'), dict) and value['status'].get('case') == case and 'evidence' in value:
            receipts.append(value)
    assert len(receipts) == 1, 'Missing/ambiguous evidence; inspect the original job, never resubmit'
    receipt = receipts[0]
    evidence = receipt['evidence']
    assert evidence['repo'] == 'coyotte508/powergrid-ai-germany-v1'
    assert evidence['archive_path'] == f'archives/{case}.tgz' and re.fullmatch('[a-f0-9]{40}', evidence['revision'])
    assert evidence['remote_archive_verified'] is True and evidence['format'] == 'tar.gz'
    archive = Path(hf_hub_download(evidence['repo'], evidence['archive_path'], revision=evidence['revision']))
    assert digest(archive) == evidence['archive_sha256']
    artifacts = folder / 'artifacts'
    if not artifacts.exists():
        extract_verified(archive, artifacts)
    result = verify_artifacts(artifacts, row, source, read(launcher.PROTOCOL), evidence)
    assert receipt['status'] == read(artifacts / 'resource-check.json')
    assert hashes == code_hashes(), 'Collection code changed while verifying'
    checked = {**status, 'verified': True, 'row': row, 'source': source, 'evidence': evidence, **result,
               'code_hashes': hashes, 'plan_sha256': digest(launcher.PLAN), 'protocol_sha256': digest(launcher.PROTOCOL),
               'qualification_eligible': False, 'reserved_final_seeds_used': False}
    write(folder / 'verified.json', checked)
    return checked


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('operation', choices=['inspect', 'collect'])
    parser.add_argument('case')
    args = parser.parse_args()
    result = globals()[args.operation](args.case)
    print(json.dumps({k: v for k, v in result.items() if k in ('case', 'job_id', 'authoritative_status', 'verified', 'failed', 'summary', 'runtime')}, indent=2))
