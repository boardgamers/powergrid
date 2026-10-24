"""Archive completed exact recoveries; never launch jobs or select a policy."""
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import shutil

from huggingface_hub import HfApi
from strategic_collection import ROOT, read, write, digest
from policy_iteration_evidence_archive import upload_evidence


def main():
    source = ROOT / 'ai/strong/manage-population-hybrid-development.py'
    spec = importlib.util.spec_from_file_location('recovery_completion_manager', source)
    manager = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(manager)
    cases = ['population-hybrid-development-v1-auction-4p-legacy-0-4',
             'population-hybrid-development-v1-auction-5p-economic-0-4']
    receipts = [manager.verified_receipt(case) for case in cases]
    assert all(v is not None for v in receipts)
    guards = [read(manager.GUARDS / (case + '.json')) for case in cases]
    api = HfApi()
    statuses = []
    for case, receipt, guard, games in zip(cases, receipts, guards, [64, 80]):
        job = api.inspect_job(job_id=guard['job_id'])
        assert job.status.stage == 'COMPLETED'
        assert guard['replaces_job_id'] and receipt['job_id'] == guard['job_id']
        assert receipt['summary']['games'] == games
        assert receipt['summary']['all_receipts_verified'] is True
        assert receipt['summary']['counts']['rollout_caps'] == 0
        statuses.append({'case': case, 'job_id': job.id, 'status': job.status.stage,
                         'original_job_id': guard['replaces_job_id']})

    parity_path = ROOT / 'ai/runs/population-hybrid-storage-recovery-v1/repeated-games-verified.json'
    parity = read(parity_path)
    assert parity['verified'] is True
    assert parity['original_job_id'] == guards[1]['replaces_job_id']
    assert parity['replacement_job_id'] == guards[1]['job_id']
    assert parity['replacement_verified_sha256'] == digest(manager.COLLECTED / cases[1] / 'verified.json')
    assert (parity['repeated_games'], parity['repeated_decisions'], parity['failed_prefix_decisions']) == (79, 9258, 14)

    # Independently repeat the actual saved-game comparisons without rewriting
    # the active coordinator's parity receipt or invoking its wrapped collector.
    failure = ROOT / 'ai/runs/population-hybrid-auction5p-failure-v1'
    previous = failure / 'artifacts'
    replacement = manager.COLLECTED / cases[1] / 'artifacts'
    original_receipt = read(failure / 'original-failed-job-receipt.json')
    for directory, evidence in [(previous, original_receipt['evidence']),
                                (replacement, receipts[1]['evidence'])]:
        manifest = read(directory / 'manifest.json')
        assert digest(directory / 'manifest.json') == evidence['manifest_sha256']
        assert {str(p.relative_to(directory)) for p in directory.rglob('*') if p.is_file()} == set(manifest) | {'manifest.json'}
        assert all(digest(directory / name) == sha for name, sha in manifest.items())
    old = previous / 'evaluation'
    new = replacement / 'evaluation'
    old_report, new_report = read(old / 'evaluation.json'), read(new / 'evaluation.json')
    assert len(old_report['results']) == 79 and new_report['completed_games'] == 80
    assert new_report['all_complete'] is True and new_report['errors'] == []
    assert {r['episode'] for r in old_report['results']} == set(range(80)) - {36}
    assert {r['episode'] for r in new_report['results']} == set(range(80))
    decisions = 0
    for record in old_report['results']:
        episode = record['episode']
        current = read(new / f'game-{episode}.json')
        ignore = {'seconds', 'decision_receipt_sha256'}
        assert {k: v for k, v in record.items() if k not in ignore} == {k: v for k, v in current.items() if k not in ignore}
        earlier = [json.loads(line) for line in (old / f'decisions-{episode}.jsonl').read_text().splitlines()]
        later = [json.loads(line) for line in (new / f'decisions-{episode}.jsonl').read_text().splitlines()]
        assert len(earlier) == len(later)
        for a, b in zip(earlier, later):
            assert {k: v for k, v in a.items() if k != 'elapsedMs'} == {k: v for k, v in b.items() if k != 'elapsedMs'}
        decisions += len(earlier)
    prefix = [json.loads(line) for line in (old / 'decisions-36.jsonl').read_text().splitlines()]
    later = [json.loads(line) for line in (new / 'decisions-36.jsonl').read_text().splitlines()]
    assert len(prefix) == 14 and len(later) >= 14 and decisions == 9258
    for a, b in zip(prefix, later):
        assert {k: v for k, v in a.items() if k != 'elapsedMs'} == {k: v for k, v in b.items() if k != 'elapsedMs'}

    plan = read(manager.PLAN)
    assert all(digest(ROOT / name) == sha for name, sha in plan['dependency_hashes'].items())
    snapshot = read(ROOT / 'ai/runs/population-hybrid-development-coordinator-v1/state.json')
    review = {'checked_at': datetime.now(timezone.utc).isoformat(),
              'status': 'both_exact_recoveries_complete_and_storage_parity_verified',
              'jobs': statuses, 'verified_games': 144,
              'storage_repeated_games': 79, 'storage_repeated_decisions': decisions,
              'storage_failed_prefix_decisions': 14,
              'frozen_dependencies_checked': len(plan['dependency_hashes']),
              'plan_sha256': digest(manager.PLAN),
              'full_collection_receipts': [v['evidence'] for v in receipts],
              'coordinator_snapshot': {k: snapshot[k] for k in ['pid', 'stage', 'jobs_submitted', 'jobs_verified', 'updated_at']},
              'scope': 'Recovery completion and exact replay parity only; full hybrid comparison remains required.',
              'new_jobs': 0, 'gradients': False, 'qualification_eligible': False,
              'reserved_final_seeds_used': False}
    directory = ROOT / 'ai/runs/population-hybrid-recovery-completion-evidence-v1'
    descriptor = ROOT / 'ai/strong/population-hybrid-recovery-completion-evidence-v1.json'
    assert not directory.exists() and not descriptor.exists(), 'Inspect any prior archive outcome before retrying'
    directory.mkdir()
    write(directory / 'review.json', review)
    write(directory / 'coordinator-state.json', snapshot)
    shutil.copy2(Path(__file__), directory / Path(__file__).name)
    shutil.copy2(parity_path, directory / 'repeated-games-verified.json')
    for index, case in enumerate(cases):
        shutil.copy2(manager.GUARDS / (case + '.json'), directory / f'guard-{index}.json')
        shutil.copy2(manager.COLLECTED / case / 'verified.json', directory / f'verified-{index}.json')
    for name in ['population-hybrid-prestart-failure-evidence-v1.json',
                 'population-hybrid-prestart-recovery-evidence-v1.json',
                 'population-hybrid-storage-failure-evidence-v1.json',
                 'population-hybrid-storage-recovery-evidence-v1.json']:
        shutil.copy2(ROOT / 'ai/strong' / name, directory / name)
    write(directory / 'manifest.json', {p.name: digest(p) for p in sorted(directory.iterdir())})
    evidence = upload_evidence(directory)
    result = {**review, 'collector_sha256': digest(Path(__file__)), **evidence}
    write(descriptor, result)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
