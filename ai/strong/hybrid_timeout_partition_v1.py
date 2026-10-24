"""Failure-gated specification for replaying a timed-out shard in whole deals.

No submission, cancellation, collection or guard replacement is implemented here.
The original runtime already accepts one-deal ranges; only their scheduling changes.
A future launcher/collector must retain original attempt lineage and combine every
child, rather than pretending that the original failed job completed.
"""
import argparse
import copy
import importlib.util
from pathlib import Path

from huggingface_hub import HfApi
from strategic_collection import ROOT, read, digest
from population_hybrid_development import case_key, contract, expected_config

PLAN = ROOT / 'ai/strong/population-hybrid-development-plan-v1.json'
PROTOCOL = ROOT / 'ai/strong/population-hybrid-development-protocol-v1.json'


def partition(row, protocol):
    """Preserve the exact episode set while reducing only each job's deal count."""
    contract(protocol, *(row[k] for k in ['arm', 'players', 'opponent', 'start', 'end']))
    assert row['end'] - row['start'] > 1, 'A one-deal failure needs a different reviewed recovery strategy'
    assert row['case'] == case_key(*(row[k] for k in ['arm', 'players', 'opponent', 'start', 'end']))
    n = row['players']
    assert row['games'] == (row['end'] - row['start']) * 4 * n
    children = []
    for start in range(row['start'], row['end']):
        child = {**copy.deepcopy(row), 'start': start, 'end': start + 1, 'games': 4 * n}
        child['case'] = case_key(*(child[k] for k in ['arm', 'players', 'opponent', 'start', 'end']))
        config = expected_config(protocol, *(child[k] for k in ['arm', 'players', 'opponent', 'start', 'end']))
        children.append({'row': child, 'expected_config': config,
                         'episodes': list(range(start * 4 * n, (start + 1) * 4 * n))})
    expected = list(range(row['start'] * 4 * n, row['end'] * 4 * n))
    observed = [episode for child in children for episode in child['episodes']]
    assert observed == expected and len(set(observed)) == len(expected) == row['games']
    return children


def require_reviewed_failure(original, canonical, current, *, coordinator,
                             coordinator_present, artifacts, failure_review):
    """Reject live/unknown jobs and keep failure review distinct from a risk flag."""
    assert current['job_id'] == original['job_id']
    assert current['authoritative_status'] == 'ERROR', 'Only a confirmed terminal error can be reviewed for replacement'
    message = (current.get('message') or '').lower()
    assert 'timeout' in message or 'timed out' in message, 'Terminal error is not identified as a timeout'
    assert original == canonical and original['stage'] == 'launched'
    assert 'replaces_job_id' not in original and 'recovery_admission_sha256' not in original
    assert original['qualification_eligible'] is original['reserved_final_seeds_used'] is False
    assert not coordinator_present, 'Original coordinator is still present'
    assert coordinator['stage'] == 'stopped_with_error'
    assert not artifacts, 'Review/recover existing artifacts before replacing their producer'
    assert failure_review is not None, 'No saved failure review supplied'
    assert failure_review['reviewed'] is True
    assert failure_review['original_job_id'] == original['job_id']
    assert failure_review['original_guard_sha256'] == current['guard_sha256']
    assert failure_review['terminal_status'] == 'ERROR' and failure_review['reason'] == 'timeout'
    assert failure_review['failure_logs_preserved'] is True
    assert failure_review['remote_artifact_check']['completed'] is True
    assert failure_review['remote_artifact_check']['files'] == []
    assert failure_review['selection_from_partial_results'] is False


def specification(plan, protocol, original, canonical, current, **review):
    require_reviewed_failure(original, canonical, current, **review)
    assert plan == read(PLAN) and protocol == read(PROTOCOL)
    assert original['plan_sha256'] == digest(PLAN) and original['protocol_sha256'] == digest(PROTOCOL)
    assert all(digest(ROOT / path) == sha for path, sha in plan['dependency_hashes'].items())
    row = original['row']
    assert row in plan['shards'] and original['source'] == plan['source']
    assert original['plan_sha256'] == current['plan_sha256']
    assert original['protocol_sha256'] == plan['protocol_sha256']
    children = partition(row, protocol)
    return {'status': 'reviewed_partition_specification_not_launched',
            'original_case': row['case'], 'original_job_id': original['job_id'],
            'original_guard_sha256': current['guard_sha256'],
            'plan_sha256': original['plan_sha256'], 'protocol_sha256': original['protocol_sha256'],
            'source': copy.deepcopy(original['source']),
            'bootstrap_sha256': original['bootstrap_sha256'],
            'flavor': original['flavor'], 'timeout_hours': original['timeout_hours'],
            'model_pin': copy.deepcopy(protocol['model_pin']),
            'children': children, 'games': row['games'],
            'preserve_original_guard_and_failure': True,
            'require_all_children_before_comparison': True,
            'automatic_retry': False, 'launch_implemented': False,
            'qualification_eligible': False, 'reserved_final_seeds_used': False}


def check_live(case):
    """Read-only inspection; even a terminal result does not create admission."""
    path = ROOT / 'ai/strong/manage-population-hybrid-development.py'
    spec = importlib.util.spec_from_file_location('original_hybrid_manager_readonly', path)
    manager = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(manager)
    plan, source, row = manager.admission(case)
    original = read(manager.GUARDS / (case + '.json'))
    assert original['source'] == source and original['row'] == row
    assert original['plan_sha256'] == digest(PLAN) and original['protocol_sha256'] == digest(PROTOCOL)
    job = HfApi().inspect_job(job_id=original['job_id'])
    state = read(ROOT / 'ai/runs/population-hybrid-development-coordinator-v1/state.json')
    present = Path('/proc', str(state['pid']), 'cmdline').exists()
    current = {'job_id': job.id, 'authoritative_status': job.status.stage,
               'message': job.status.message, 'plan_sha256': digest(PLAN),
               'guard_sha256': digest(manager.GUARDS / (case + '.json'))}
    try:
        specification(plan, read(PROTOCOL), original, original, current,
                      coordinator=state, coordinator_present=present, artifacts=[], failure_review=None)
    except AssertionError as error:
        rejection = str(error)
    else:
        raise AssertionError('Live check without a failure review must not admit recovery')
    return {'case': case, 'job_id': original['job_id'], 'authoritative_status': job.status.stage,
            'coordinator_present': present, 'coordinator_stage': state['stage'],
            'terminal_failure_review_required': True,
            'potential_children': [c['row'] for c in partition(row, read(PROTOCOL))],
            'original_games': row['games'], 'admitted': False, 'admission_rejection': rejection,
            'new_jobs': 0, 'remote_mutations': False}


if __name__ == '__main__':
    import json
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('case')
    args = parser.parse_args()
    print(json.dumps(check_live(args.case), indent=2))
