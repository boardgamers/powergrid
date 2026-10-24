"""Resolve explicitly canceled/replaced jobs without rewriting original guards."""
from strategic_collection import ROOT, read, digest

ATTEMPTS = ROOT/'ai/runs/policy-iteration-labels-cpu-upgrade-v2'
FAILURE_RETRIES = ROOT/'ai/runs/policy-iteration-labels-upload-retries-v2'


def capacity_guard(path):
    original = read(path)
    attempt_path = ATTEMPTS/path.name
    if not attempt_path.exists():
        return original
    attempt = read(attempt_path)
    assert attempt['original_job_id'] == original['job_id']
    assert attempt['source'] == original['source'] and attempt['shard'] == original['shard']
    assert attempt['original_guard_sha256'] == digest(path)
    if attempt['stage'] == 'skipped':
        return original
    assert attempt['stage'] == 'launched', 'Reconcile the unfinished migration before collecting or launching again'
    assert attempt['cancellation']['stage'] in ['CANCELED', 'CANCELLED']
    assert attempt['cancellation']['job_id'] == original['job_id']
    assert attempt['job_id'] != original['job_id']
    return {**original, 'job_id': attempt['job_id'], 'original_job_id': original['job_id'],
            'attempt_guard': str(attempt_path.relative_to(ROOT)), 'attempt_guard_sha256': digest(attempt_path),
            'flavor': attempt['flavor'], 'timeout_hours': attempt['timeout_hours'],
            'created_at': attempt['replacement_created_at']}


def apply_failure_retry(previous, retry, retry_path):
    assert retry['stage'] == 'launched', 'Reconcile the unfinished failure retry before collecting'
    assert retry['previous_guard'] == previous
    assert retry['failure']['job_id'] == previous['job_id']
    assert retry['failure']['stage'] == 'ERROR' and retry['failure']['finished_at'] != 'None'
    assert retry['failure_reason'] == 'artifact_repository_file_limit'
    assert retry['remote_artifact_prefix_absent']
    assert retry['job_id'] != previous['job_id']
    return {**previous, 'job_id': retry['job_id'], 'failed_job_id': previous['job_id'],
            'failure_retry_guard': str(retry_path.relative_to(ROOT)),
            'failure_retry_guard_sha256': digest(retry_path), 'flavor': retry['flavor'],
            'timeout_hours': retry['timeout_hours'], 'created_at': retry['created_at']}


def effective_guard(path):
    previous = capacity_guard(path)
    retry_path = FAILURE_RETRIES/path.name
    if not retry_path.exists():
        return previous
    return apply_failure_retry(previous, read(retry_path), retry_path)
