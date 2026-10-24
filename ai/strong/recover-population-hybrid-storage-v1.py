"""Reviewed exact replacement of the single preserved storage-error batch.

Uses the original launch implementation and frozen experiment. The coordinator
adapter additionally requires deterministic parity with every saved original
game and the failed game's saved decision prefix before accepting the replacement.
No automatic retries, altered games, partial scoring, or gradient computation.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path

from huggingface_hub import HfApi, hf_hub_download
from strategic_collection import ROOT, read, write, digest
from population_hybrid_development import PROTOCOL, expected_config
from population_policy_verification import verify_decision


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


core = module('storage_recovery_core', Path(__file__).with_name('recover-population-hybrid-prestart-v1.py'))
FAILED = ROOT / 'ai/runs/population-hybrid-auction5p-failure-v1'
RUN = ROOT / 'ai/runs/population-hybrid-storage-recovery-v1'
ADMISSION = ROOT / 'ai/strong/population-hybrid-storage-recovery-admission-v1.json'
CASE = 'population-hybrid-development-v1-auction-5p-economic-0-4'
ERROR = {'episode': 36, 'error': 'OSError: [Errno 28] No space left on device'}


def partial_contract(report, guard):
    assert guard['case'] == CASE and guard['stage'] == 'launched'
    assert 'replaces_job_id' not in guard
    row = guard['row']
    expected = expected_config(read(PROTOCOL), *(row[k] for k in ['arm', 'players', 'opponent', 'start', 'end']))
    assert all(report['config'][k] == value for k, value in expected.items())
    assert report['all_complete'] is False and report['errors'] == [ERROR]
    assert report['expected_games'] == row['games'] == 80
    assert report['completed_games'] == len(report['results']) == 79
    assert {r['episode'] for r in report['results']} == set(range(80)) - {36}
    assert report['game_caps'] == report['rollout_caps'] == 0
    assert report['qualification_eligible'] is report['reserved_final_seeds_used'] is False


def review_partial():
    guard = read(FAILED / 'original-guard.json')
    artifacts = FAILED / 'artifacts'
    manifest = read(artifacts / 'manifest.json')
    assert {str(p.relative_to(artifacts)) for p in artifacts.rglob('*') if p.is_file()} == set(manifest) | {'manifest.json'}
    assert all(digest(artifacts / name) == sha for name, sha in manifest.items())
    receipt = read(FAILED / 'original-failed-job-receipt.json')
    evidence = receipt['evidence']
    assert evidence['repo'] == 'coyotte508/powergrid-ai-germany-v1'
    assert evidence['archive_path'] == 'archives/' + CASE + '.tgz'
    assert evidence['manifest_sha256'] == digest(artifacts / 'manifest.json')
    assert evidence['archived_files'] == len(manifest) + 1
    status = read(artifacts / 'development-check.json')
    assert {k: v for k, v in receipt.items() if k != 'evidence'} == status
    assert status['stage'] == 'failed' and status['case'] == CASE
    assert status['source_revision'] == guard['source']['revision']
    assert status['source_sha256'] == guard['source']['sha256']
    assert status['protocol_sha256'] == guard['protocol_sha256'] == digest(PROTOCOL)
    assert status['model_pin'] == read(PROTOCOL)['model_pin']
    directory = artifacts / 'evaluation'
    report = read(directory / 'evaluation.json')
    partial_contract(report, guard)
    decisions = 0
    for record in report['results']:
        episode = record['episode']
        assert read(directory / f'game-{episode}.json') == record
        terminal = record['terminal']
        seat = episode // 4 % 5
        assert terminal['episode'] == episode and terminal['seat'] == seat
        assert terminal['playerCount'] == 5 and terminal['truncated'] is False
        assert terminal['gameSeed'] == report['config']['seed'] + '-' + str(episode // 20)
        assert terminal['variant'] == ('recharged' if episode % 2 else 'original')
        assert terminal['sealed'] is (episode % 4 < 2)
        assert terminal['roles'] == ['learner' if i == seat else 'economic' for i in range(5)]
        assert 1 <= terminal['steps'] <= 1600 and terminal['searchStats'] == {}
        path = directory / f'decisions-{episode}.jsonl'
        assert digest(path) == record['decision_receipt_sha256']
        rows = [json.loads(line) for line in path.read_text().splitlines()]
        assert len(rows) == record['decisions']
        counts, moves = Counter(), Counter()
        for index, row in enumerate(rows, 1):
            assert row['decision'] == index
            counts.update(verify_decision(row, {**report['config'], 'sealed': terminal['sealed']}, seat))
            moves[row['move']['name']] += 1
        for key in ['decisions', 'root_filter_overrides', 'rollouts', 'rollout_caps', 'neural_decisions', 'search_changes']:
            assert counts[key] == record[key]
        assert terminal['policyMoves'] == dict(moves)
        decisions += len(rows)
    prefix = [json.loads(line) for line in (directory / 'decisions-36.jsonl').read_text().splitlines()]
    assert not (directory / 'game-36.json').exists() and len(prefix) == 14
    for index, row in enumerate(prefix, 1):
        assert row['decision'] == index
        verify_decision(row, {**report['config'], 'sealed': True}, 4)
    return {'completed_records': 79, 'completed_decisions_checked': decisions,
            'failed_episode': 36, 'saved_failed_prefix_decisions': len(prefix),
            'full_cell_verified': False, 'storage_resource_cause_not_localized': True,
            'partial_archive_bytes': 552097, 'source_unchanged': True,
            'qualification_eligible': False, 'reserved_final_seeds_used': False}


def replacement_allowed(original, canonical, status, remote, reviewed, *, present, stage):
    assert original['case'] == CASE and original['stage'] == 'launched'
    assert canonical == original and 'replaces_job_id' not in original
    assert original['qualification_eligible'] is original['reserved_final_seeds_used'] is False
    assert status['job_id'] == original['job_id'] and status['stage'] == 'ERROR'
    assert status['started_at'] is not None and status['finished_at'] is not None
    assert not present and stage == 'stopped_with_error'
    assert remote['repo'] == 'coyotte508/powergrid-ai-germany-v1'
    assert remote['path'] == 'archives/' + CASE + '.tgz' and remote['exists'] is True
    assert reviewed['completed_records'] == 79 and reviewed['failed_episode'] == 36
    assert reviewed['saved_failed_prefix_decisions'] == 14 and reviewed['full_cell_verified'] is False


def admit():
    admission = read(ADMISSION)
    assert admission['maximum_replacements'] == 1 and admission['maximum_replacement_retries'] == 0
    assert admission['qualification_eligible'] is admission['reserved_final_seeds_used'] is False
    assert admission['recovery_adapter_sha256'] == digest(Path(__file__))
    assert admission['recovery_core_sha256'] == digest(Path(core.__file__))
    for name, sha in admission['failure_file_hashes'].items():
        assert digest(FAILED / name) == sha
    assert digest(ROOT / 'ai/strong/population-hybrid-storage-failure-evidence-v1.json') == admission['failure_evidence_descriptor_sha256']
    assert admission['failure_evidence']['remote_archive_verified'] is True
    original = read(FAILED / 'original-guard.json')
    assert original['case'] == admission['case'] and original['job_id'] == admission['original_job_id']
    assert original['source'] == admission['source'] and original['plan_sha256'] == admission['plan_sha256']
    plan, source, row = core.manager.admission(CASE)
    assert source == original['source'] and row == original['row']
    assert digest(core.manager.GUARDS / (CASE + '.json')) == admission['original_guard_sha256']
    assert not (core.manager.COLLECTED / CASE / 'verified.json').exists()
    state = read(core.COORDINATOR / 'state.json')
    assert digest(core.COORDINATOR / 'state.json') == admission['original_coordinator_sha256']
    reviewed = review_partial()
    assert reviewed == admission['partial_review']
    api = HfApi()
    job = api.inspect_job(job_id=original['job_id'])
    status = {'job_id': job.id, 'stage': job.status.stage, 'message': job.status.message,
              'started_at': str(job.started_at) if job.started_at else None,
              'finished_at': str(job.finished_at) if job.finished_at else None,
              'checked_at': datetime.now(timezone.utc).isoformat()}
    evidence = read(FAILED / 'original-failed-job-receipt.json')['evidence']
    remote = {'repo': evidence['repo'], 'revision': evidence['revision'], 'path': evidence['archive_path']}
    remote['exists'] = api.file_exists(remote['repo'], remote['path'], revision=remote['revision'])
    archive = hf_hub_download(remote['repo'], remote['path'], revision=remote['revision'])
    assert digest(archive) == evidence['archive_sha256']
    replacement_allowed(original, read(core.manager.GUARDS / (CASE + '.json')), status, remote,
                        reviewed, present=Path('/proc', str(state['pid'])).exists(), stage=state['stage'])
    before = read(FAILED / 'original-guard-hashes.json')
    assert {p.stem: digest(p) for p in core.manager.GUARDS.glob('*.json')} == before
    return admission, original, status, remote, before


def same_record(original, replacement):
    ignored = {'seconds', 'decision_receipt_sha256'}
    assert {k: v for k, v in original.items() if k not in ignored} == {
        k: v for k, v in replacement.items() if k not in ignored}, 'Repeated game changed'


def same_decision(original, replacement):
    assert {k: v for k, v in original.items() if k != 'elapsedMs'} == {
        k: v for k, v in replacement.items() if k != 'elapsedMs'}, 'Repeated decision changed'


def verify_repeated_games(verified):
    assert verified['case'] == CASE and verified['verified'] is True
    guard = read(core.manager.GUARDS / (CASE + '.json'))
    assert verified['job_id'] == guard['job_id']
    assert guard['replaces_job_id'] == read(FAILED / 'original-guard.json')['job_id']
    assert guard['recovery_admission_sha256'] == digest(ADMISSION)
    review = review_partial()
    old = FAILED / 'artifacts/evaluation'
    new = core.manager.COLLECTED / CASE / 'artifacts/evaluation'
    report = read(new / 'evaluation.json')
    assert report['all_complete'] is True and report['completed_games'] == 80 and report['errors'] == []
    assert {r['episode'] for r in report['results']} == set(range(80))
    checked_decisions = 0
    for record in read(old / 'evaluation.json')['results']:
        episode = record['episode']
        same_record(record, read(new / f'game-{episode}.json'))
        previous = [json.loads(line) for line in (old / f'decisions-{episode}.jsonl').read_text().splitlines()]
        current = [json.loads(line) for line in (new / f'decisions-{episode}.jsonl').read_text().splitlines()]
        assert len(previous) == len(current)
        for a, b in zip(previous, current):
            same_decision(a, b)
        checked_decisions += len(previous)
    prefix = [json.loads(line) for line in (old / 'decisions-36.jsonl').read_text().splitlines()]
    current = [json.loads(line) for line in (new / 'decisions-36.jsonl').read_text().splitlines()]
    assert len(current) >= len(prefix) == 14
    for a, b in zip(prefix, current):
        same_decision(a, b)
    result = {'verified': True, 'original_job_id': guard['replaces_job_id'], 'replacement_job_id': guard['job_id'],
              'repeated_games': 79, 'repeated_decisions': checked_decisions, 'failed_prefix_decisions': 14,
              'partial_review': review, 'replacement_verified_sha256': digest(core.manager.COLLECTED / CASE / 'verified.json'),
              'qualification_eligible': False, 'reserved_final_seeds_used': False}
    write(RUN / 'repeated-games-verified.json', result)
    return result


def coordinate():
    admission = read(ADMISSION)
    assert digest(Path(__file__)) == admission['recovery_adapter_sha256']
    assert digest(Path(core.__file__)) == admission['recovery_core_sha256']
    coordinator = module('storage_recovery_coordinator', ROOT / 'ai/strong/coordinate-population-hybrid-development.py')
    collect = coordinator.manager.collect
    receipt = coordinator.manager.verified_receipt
    def guarded_collect(case):
        result = collect(case)
        if case == CASE and result.get('verified'):
            verify_repeated_games(result)
        return result
    def guarded_receipt(case):
        result = receipt(case)
        if case == CASE and result is not None:
            verify_repeated_games(result)
        return result
    coordinator.manager.collect = guarded_collect
    coordinator.manager.verified_receipt = guarded_receipt
    coordinator.main(execute=True, interval=300, max_hours=48)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('operation', choices=['review', 'launch', 'coordinate', 'parity'])
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    if args.operation == 'review':
        print(json.dumps(review_partial(), indent=2))
    elif args.operation == 'launch':
        core.FAILED, core.RUN, core.ADMISSION, core.admit = FAILED, RUN, ADMISSION, admit
        core.main(args.execute)
    elif args.operation == 'coordinate':
        assert args.execute
        coordinate()
    else:
        print(json.dumps(verify_repeated_games(core.manager.verified_receipt(CASE)), indent=2))
