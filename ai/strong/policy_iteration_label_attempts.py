"""Resolve explicitly canceled/replaced jobs without rewriting original guards."""
from strategic_collection import ROOT, read, digest

ATTEMPTS = ROOT/'ai/runs/policy-iteration-labels-cpu-upgrade-v2'


def effective_guard(path):
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
