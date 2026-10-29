"""Validate every packaged final contract against the real frozen artifact.

Reuses an explicitly synthetic candidate from the earlier transport preflight.
Never execute, upload, select, submit jobs, or instantiate reserved games.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys

import selected_public_policy_final_source_v1 as builder

ROOT = builder.ROOT
OUT = ROOT/'ai/runs/selected-public-policy-final-source-preflight-v1'
RESULT = ROOT/'ai/strong/selected-public-policy-final-source-preflight-v1.json'
BASE = ROOT/'ai/runs/current-auction-grid-prepared-v1/source/artifact'
CANDIDATE = ROOT/'ai/runs/selected-public-policy-final-job-preflight-v1/valid_hybrid/source/synthetic-candidate.json'


def validate(row, manifest_sha):
    source = OUT/'source'
    command = [sys.executable, '-u', '-B', str(source/builder.ENTRY), '--source', str(source),
        '--manifest-sha256', manifest_sha, '--job', row['job'],
        '--output', str(OUT/'must-not-exist'/row['name'])]
    assert '--execute' not in command and '--upload' not in command
    log = OUT/'validation-logs'/(row['name']+'.log')
    with log.open('x') as stream:
        completed = subprocess.run(command, cwd='/tmp', stdout=stream, stderr=subprocess.STDOUT)
    result = {'name': row['name'], 'returncode': completed.returncode, 'passed': False,
        'log_sha256': builder.digest(log), 'game_count_in_contract': row['shard']['games']}
    assert not (OUT/'must-not-exist').exists(), 'Validation instantiated execution outputs'
    if completed.returncode == 0:
        messages = [json.loads(line) for line in log.read_text().splitlines()]
        assert len(messages) == 2 and all(m['execute'] is False for m in messages)
        runner, wrapper = messages
        assert runner['valid_contract'] and wrapper['valid_job']
        assert runner['binding']['purpose'] == 'final' and runner['binding']['shard'] == row['shard']
        assert wrapper['provenance']['shard'] == row['shard']
        assert wrapper['provenance']['source_revision'] is None
        assert runner['binding']['contract_sha256'] == wrapper['provenance']['contract_sha256'] == builder.digest(source/row['contract'])
        result.update(passed=True, contract_sha256=builder.digest(source/row['contract']),
                      job_spec_sha256=builder.digest(source/row['job']))
    return result


def main():
    assert not OUT.exists() and not RESULT.exists(), 'Inspect original validation; never overwrite'
    tests = ROOT/'ai/runs/selected-public-policy-final-source-tests-v1-first.log'
    assert 'Ran 7 tests' in tests.read_text() and tests.read_text().rstrip().endswith('OK')
    candidate = builder.read(CANDIDATE)
    assert candidate['selection_evidence'] == {
        'repo': 'coyotte508/powergrid-ai-germany-v1', 'revision': '1'*40,
        'archive_path': 'archives/synthetic-final-job-contract-fixture.tgz', 'archive_sha256': '2'*64}
    previous = ROOT/'ai/strong/selected-public-policy-final-job-preflight-v2.json'
    proof = builder.read(previous)
    assert proof['passed'] and not proof['candidate_selected'] and not proof['reserved_final_seeds_used']
    prior = next(c for c in proof['real_artifact_validation_cases'] if c['case'] == 'valid_hybrid')
    assert builder.digest(CANDIDATE.parent/'source-manifest.json') == prior['source_manifest_sha256']
    assert builder.digest(CANDIDATE) == builder.read(CANDIDATE.parent/'source-manifest.json')['synthetic-candidate.json']
    paths = [Path(__file__), Path(builder.__file__), ROOT/'ai/strong'/builder.ENTRY,
        ROOT/'ai/strong/test_selected_public_policy_final_source_v1.py', tests, CANDIDATE, previous,
        ROOT/'ai/strong/final-protocol-multiplayer.json',
        ROOT/'ai/strong/current-auction-grid-source-v1.json']
    pins = {str(p.relative_to(ROOT)): builder.digest(p) for p in paths}
    workers = {s['name']: 4 for s in builder.schedule()}
    prepared = builder.build(BASE, 'policies/conservative_population.json', CANDIDATE, workers, OUT)
    builder.save(OUT/'synthetic-validation-only.json', {
        'created_at': datetime.now(timezone.utc).isoformat(), 'input_hashes': pins,
        'warning': 'Synthetic candidate and launch contracts. Never publish this bundle as an HF execution source or execute its games.',
        'candidate_selected': False, 'reserved_final_seeds_used': False,
        'workers': 'Four game workers are contract fixtures, not a measured final allocation.'})
    (OUT/'validation-logs').mkdir()
    results = []
    with (OUT/'validations.jsonl').open('x') as receipts, ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(validate, row, prepared['source_manifest_sha256']) for row in prepared['rows']]
        for future in as_completed(futures):
            result = future.result(); results.append(result)
            receipts.write(json.dumps(result, separators=(',', ':'))+'\n'); receipts.flush()
            if len(results) % 40 == 0:
                print(json.dumps({'validated': len(results), 'expected': 320, 'failures': sum(not r['passed'] for r in results)}), flush=True)
    assert len(results) == 320 and all(r['passed'] for r in results)
    assert {r['name'] for r in results} == set(workers)
    assert all(builder.digest(ROOT/p) == sha for p, sha in pins.items())
    manifest = builder.read(OUT/'source/source-manifest.json')
    assert builder.source_files(OUT/'source') == {**manifest, 'source-manifest.json': prepared['source_manifest_sha256']}
    assert not (OUT/'must-not-exist').exists()
    report = {'passed': True, 'created_at': datetime.now(timezone.utc).isoformat(), 'unit_tests': 7,
        'validated_jobs': 320, 'games_in_unchanged_contracts': 20160,
        'identity': prepared['identity'], 'protocol_sha256': builder.PROTOCOL_SHA,
        'prepared_sha256': builder.digest(OUT/'prepared.json'),
        'source_manifest_sha256': prepared['source_manifest_sha256'],
        'plan_sha256': prepared['plan_sha256'], 'input_hashes': pins,
        'validation_receipts_sha256': builder.digest(OUT/'validations.jsonl'),
        'validation_logs': {str(p.relative_to(ROOT)): builder.digest(p) for p in sorted((OUT/'validation-logs').glob('*.log'))},
        'all_original_frozen_source_bytes_unchanged': True,
        'synthetic_candidate_and_allocation_only': True, 'candidate_selected': False,
        'jobs_submitted': 0, 'games_executed': 0, 'policy_inference_calls': 0,
        'reserved_final_seeds_used': False, 'launch_admitted': False, 'qualified': False,
        'remaining': ['complete confirmation and selection', 'complete selected-policy technical evidence',
            'measured final resource allocation', 'immutable real source publication and original-only launch manager',
            'complete held-out strength evaluation and audit']}
    builder.save(RESULT, report)
    print(json.dumps({k: report[k] for k in ('passed', 'validated_jobs', 'games_executed', 'jobs_submitted')}), flush=True)


if __name__ == '__main__':
    main()
