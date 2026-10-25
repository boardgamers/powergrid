"""Audit saved original pilot evidence and archive the paused handoff. No execution/submission."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import shutil

from huggingface_hub import HfApi, get_token, hf_hub_download
from policy_iteration_evidence_archive import upload_evidence
from public_policy_final_audit_v1 import audit_terminal, audit_public_decision, verify_auction
from public_policy_final_contract_v1 import audit_execution_binding

ROOT = Path(__file__).resolve().parents[2]
STRONG = ROOT/'ai/strong'
RUNS = ROOT/'ai/runs'
OUT = RUNS/'paused-handoff-evidence-2026-10-25'
DESCRIPTOR = STRONG/'paused-handoff-archive-2026-10-25.json'
INTENT = RUNS/'paused-handoff-archive-2026-10-25-intent.json'
IDS = ['6addea031e112550ce7eaa88', '6addea031e112550ce7eaa8a',
       '6addea04046eb82b1ece4faf', '6addea04046eb82b1ece4fb1']
spec = importlib.util.spec_from_file_location('original_runtime', STRONG/'manage-conservative-auction-runtime-v1.py')
manager = importlib.util.module_from_spec(spec)
spec.loader.exec_module(manager)
read, digest = manager.read, manager.digest


def absent(pid, script):
    path = Path('/proc')/str(pid)/'cmdline'
    return not path.exists() or script.encode() not in path.read_bytes()


def paused():
    owner = read(RUNS/'conservative-auction-development-coordinator-v1/state.json')
    finisher = read(RUNS/'conservative-auction-runtime-finish-v1/state.json')
    assert absent(owner['pid'], 'coordinate-conservative-auction-development-v1.py')
    assert absent(finisher['pid'], 'finish-conservative-auction-runtime-v1.py')
    assert (RUNS/'conservative-auction-development-coordinator-v1/STOP').exists()
    assert owner['development_submitted'] == 0 and owner['stage'] == 'stopped_for_inspection'
    assert all(digest(ROOT/name) == sha for name, sha in owner['code_hashes'].items())
    assert not (STRONG/'conservative-auction-development-source-v1.json').exists()
    return owner, finisher


def archive_integrity(folder, evidence):
    assert evidence['repo'] == 'coyotte508/powergrid-ai-germany-v1' and evidence['remote_archive_verified']
    downloaded = hf_hub_download(evidence['repo'], evidence['archive_path'], revision=evidence['revision'])
    assert digest(downloaded) == evidence['archive_sha256']
    assert digest(folder/'manifest.json') == evidence['manifest_sha256']
    manifest = read(folder/'manifest.json')
    assert set(manifest)|{'manifest.json'} == {str(p.relative_to(folder)) for p in folder.rglob('*') if p.is_file()}
    assert all(digest(folder/name) == sha for name, sha in manifest.items())


def partial_audit(folder, row, source):
    """Validate existing successful receipts without treating an incomplete shard as passed."""
    target = folder/'job/evaluation'
    report = read(target/'evaluation.json')
    expected, identity = row['shard'], row['identity']
    assert not report['passed'] and not report['all_complete']
    assert report['expected_games'] == 24 and report['completed_games'] == 23
    assert not report['qualification_eligible'] and not report['reserved_final_seeds_used']
    assert {r['episode'] for r in report['results']} == set(range(24)) - {5}
    config = report['config']
    assert config['identity'] == identity
    for key in ('players', 'start', 'deals', 'seed', 'opponent', 'opponent_sha256'):
        assert config[key] == expected[key]
    binding = audit_execution_binding(target, identity, source['runner_sha256'])
    assert binding == report['execution_binding']
    totals = Counter()
    for record in report['results']:
        episode = record['episode']
        terminal = audit_terminal(record, expected)
        assert read(target/f'game-{episode}.json') == record
        assert record['public_runtime_identity'] == identity
        receipt = target/f'decisions-{episode}.jsonl'
        assert digest(receipt) == record['decision_receipt_sha256']
        counts, moves, elapsed, previous_round = Counter(), Counter(), 0., 0
        for ordinal, line in enumerate(receipt.read_text().splitlines(), 1):
            decision = json.loads(line)
            audit_public_decision(decision, identity, episode, terminal['seat'], ordinal)
            assert previous_round <= decision['round'] <= terminal['final']['round']
            previous_round = decision['round']
            counts.update(verify_auction(decision, {**config, 'sealed': terminal['sealed']}, terminal['seat']))
            moves[decision['move']['name']] += 1
            elapsed += decision['elapsedMs']
        for key in ('decisions', 'root_filter_overrides', 'rollouts', 'rollout_caps', 'neural_decisions', 'search_changes'):
            assert record[key] == counts[key]
        assert terminal['policyMoves'] == dict(moves) and elapsed <= record['seconds']*1000+1
        totals.update(counts)
    failure = read(target/'failure-5.json')
    assert failure['episode'] == 5 and 'AssertionError' in failure['error']
    assert digest(target/'decisions-5.jsonl') == failure['receipt_sha256']
    assert report['errors'] == [{'episode': 5, 'error': failure['error']}]
    return {'complete_shard_audit_passed': False, 'completed_receipts_audited': 23,
            'terminal_credits_recomputed': 23, 'completed_receipt_counts': dict(totals),
            'failed_episode': failure, 'failed_episode_complete_audit': False,
            'validation_error': report['validation_error'], 'execution_binding_verified': True,
            'qualification_eligible': False, 'runtime_only': True}


def audit():
    paused()
    assert not manager.RESULT.exists(), 'Inspect the existing final report; do not overwrite it'
    source = manager.source_checked()
    jobs, verified_counts, ids = [], Counter(), []
    for row in source['rows']:
        directory = manager.OUT/row['name']
        guard = read(directory/'launch.json')
        assert guard['source'] == source and guard['row'] == row
        job_id = guard['job_id']; ids.append(job_id)
        stage = HfApi().inspect_job(job_id=job_id).status.stage
        assert stage in ('COMPLETED', 'ERROR', 'CANCELED', 'TIMEOUT', 'FAILED'), 'Original is not terminal'
        folder = directory/'artifacts'
        if stage == 'COMPLETED':
            saved = read(directory/'verified.json')
            evidence = saved['evidence']
            archive_integrity(folder, evidence)
            review = manager.verify_artifacts(folder, source, row, evidence)
            assert review == saved['review'] and saved['job_id'] == job_id
            verified_counts.update(review['audit']['counts'])
            details = {'verified': True, 'games': review['games'], 'counts': review['audit']['counts']}
        else:
            receipts = []
            for line in (directory/'job.log').read_text().splitlines():
                try: value = json.loads(line)
                except json.JSONDecodeError: continue
                if set(value) == {'case', 'status', 'evidence'} and value['case'] == row['name']:
                    receipts.append(value)
            assert len(receipts) == 1
            evidence = receipts[0]['evidence']; archive_integrity(folder, evidence)
            measurement = read(folder/'measurement.json')
            assert measurement['provenance'] == read(folder/'job/job-status.json')['provenance']
            assert measurement['case'] == row['name'] and measurement['scope'] == 'runtime'
            assert measurement['experiment_protocol_sha256'] == source['protocol_sha256']
            assert measurement['measured_entry_sha256'] == source['measured_entry_sha256']
            details = {'verified': False, 'games': 0, 'partial_evidence_audit': partial_audit(folder, row, source)}
        assert evidence['archive_path'] == 'archives/'+row['name']+'.tgz'
        measurement = read(folder/'measurement.json')
        jobs.append({'name': row['name'], 'job_id': job_id, 'stage': stage,
            'planned_games': row['shard']['games'], **details, 'measurement': measurement['measurement'],
            'evidence': evidence, 'guard_sha256': digest(directory/'launch.json'),
            'measurement_sha256': digest(folder/'measurement.json')})
        print(json.dumps({'job_id': job_id, 'stage': stage, 'verified': details['verified']}), flush=True)
    assert ids == IDS
    assert [j['stage'] for j in jobs] == ['COMPLETED', 'COMPLETED', 'COMPLETED', 'ERROR']
    report = {'checked_at': datetime.now(timezone.utc).isoformat(), 'terminal': True,
        'complete': False, 'status': 'incomplete_failed_original_pilot', 'planned_games': 64,
        'verified_jobs': 3, 'failed_jobs': 1, 'fully_audited_games': 40,
        'partial_job_completed_receipts_audited': 23, 'failed_games': 1,
        'verified_complete_job_counts': dict(verified_counts), 'jobs': jobs,
        'measured_total_wall_seconds': sum(j['measurement']['seconds'] for j in jobs),
        'measured_total_cpu_seconds': sum(j['measurement']['cpu_seconds'] for j in jobs),
        'source_descriptor': str(manager.SOURCE.relative_to(ROOT)), 'source_sha256': digest(manager.SOURCE),
        'source': {k: source[k] for k in ('revision', 'archive', 'sha256', 'source_manifest_sha256')},
        'source_repo': manager.REPO, 'runtime_only': True, 'goal_status': 'paused',
        'new_hf_jobs_submitted': 0, 'development_jobs_submitted': 0, 'gradient_updates': 0,
        'grid_admitted': False, 'qualification_eligible': False, 'reserved_final_seeds_used': False,
        'failure_interpretation': 'Original dual/6p failed at episode 5, public request 5:21, AssertionError; stack/location not preserved. Cause unconfirmed. No replacement or policy change.',
        'measurement_interpretation': 'HF batch wall/CPU/process-tree memory costs, including startup/validation. Failed-job measurement is not a successful 24-game calibration. No strength or target-machine latency claim.'}
    manager.write_new(manager.RESULT, report)
    return report


def archive():
    paused()
    assert not any(p.exists() for p in (OUT, OUT.with_suffix('.tgz'), DESCRIPTOR, INTENT)), 'Reconcile prior archive intent/outcome before retrying'
    report = read(manager.RESULT)
    assert report['terminal'] and not report['complete'] and report['verified_jobs'] == 3
    repo = 'coyotte508/powergrid-ai-germany-v1'
    archive_path = 'archives/'+OUT.name+'.tgz'
    assert HfApi().model_info(repo).private is True
    assert not HfApi().get_paths_info(repo, [archive_path]), 'Remote archive already exists; inspect original outcome'
    paths = {ROOT/'ai'/name for name in ('HANDOFF-2026-10-25-PAUSED.md', 'RESUME.md',
        'HANDOFF-2026-10-23-RESUMED.md', 'CONSERVATIVE-AUCTION-RUNTIME-2026-10-25.md')}
    paths.update(STRONG/name for name in ('paused-handoff-state-2026-10-25.json', 'experiments.json',
        'conservative-auction-runtime-results-v1.json', 'conservative-auction-runtime-source-v1.json',
        'conservative-auction-runtime-launch-evidence-v1.json', 'conservative-auction-development-readiness-v1.json',
        'conservative-auction-development-protocol-v1.json', 'final-protocol-multiplayer.json',
        'finalize-paused-handoff-2026-10-25.py', 'policy_iteration_evidence_archive.py',
        'finish-conservative-auction-runtime-v1.py', 'manage-conservative-auction-runtime-v1.py'))
    for name in ('conservative-auction-runtime-finish-v1', 'conservative-auction-development-coordinator-v1'):
        paths.add(RUNS/name/'state.json'); paths.add(RUNS/(name+'.log'))
    paths.add(RUNS/'conservative-auction-development-coordinator-v1/STOP')
    for job in report['jobs']:
        directory = manager.OUT/job['name']
        for name in ('launch.json', 'verified.json', 'failure.json', 'status.json', 'job.log'):
            if (directory/name).exists(): paths.add(directory/name)
    paths.add(RUNS/'paused-handoff-final-audit-2026-10-25.log')
    token = get_token()
    assert token and all(token.encode() not in path.read_bytes() for path in paths), 'Never archive credentials'
    intent = {'created_at': datetime.now(timezone.utc).isoformat(), 'repo': repo, 'archive_path': archive_path,
              'report_sha256': digest(manager.RESULT), 'files': {str(p.relative_to(ROOT)): digest(p) for p in sorted(paths)}}
    manager.write_new(INTENT, intent)
    OUT.mkdir()
    for path in sorted(paths):
        assert path.is_file() and not path.is_symlink()
        target = OUT/path.relative_to(ROOT); target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target); assert digest(path) == digest(target)
    manager.write_new(OUT/'archive-intent.json', intent)
    manager.write_new(OUT/'manifest.json', {str(p.relative_to(OUT)): digest(p) for p in sorted(OUT.rglob('*')) if p.is_file()})
    result = {**upload_evidence(OUT), 'handoff_finalized': True, 'run_complete': False,
              'original_jobs_terminal': 4, 'verified_jobs': 3, 'fully_audited_games': 40,
              'partial_job_completed_receipts_audited': 23, 'goal_status': 'paused',
              'report_sha256': digest(manager.RESULT), 'qualification_eligible': False,
              'reserved_final_seeds_used': False, 'new_hf_jobs_submitted': 0,
              'raw_archives_referenced': [j['evidence'] for j in report['jobs']], 'source': report['source']}
    manager.write_new(DESCRIPTOR, result)
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('operation', choices=['audit', 'archive'])
    args = parser.parse_args()
    if args.operation == 'audit': audit()
    else: archive()
