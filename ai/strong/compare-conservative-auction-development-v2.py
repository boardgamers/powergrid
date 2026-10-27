"""Audit and compare the complete frozen development grid, never partial wins.

Read-only with respect to the coordinator, original jobs and their artifacts.
Writes one separately owned analysis intent/result; never submits or collects.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import importlib.util
import json
import os
from pathlib import Path
import re
import tarfile

from huggingface_hub import hf_hub_download
import conservative_auction_analysis_v2 as statistics
from public_policy_development_job_v1 import read, digest
from public_policy_final_audit_v1 import artifact_identity
from public_policy_final_contract_v1 import object_hash

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT/'ai/strong/conservative-auction-development-comparison-v2.json'
OWNER = ROOT/'ai/runs/conservative-auction-development-coordinator-v2/state.json'


def require(ok, message):
    statistics.require(ok, message)


def write_new(path, value):
    with Path(path).open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False); stream.write('\n')


def manager_module():
    path = Path(__file__).with_name('manage-conservative-auction-development-v2.py')
    spec = importlib.util.spec_from_file_location('readonly_development_manager', path)
    manager = importlib.util.module_from_spec(spec); spec.loader.exec_module(manager)
    return manager


def completion_index(source, report):
    """Cheap completeness admission before loading individual game outcomes."""
    names = [r['name'] for r in source['rows']]
    require(len(set(names)) == len(names), 'Duplicate source job')
    require(report['complete'] is True and report['qualified'] is False
            and report['reserved_final_seeds_used'] is False, 'Incomplete or wrong-purpose comparison')
    require(report['verified_jobs'] == report['expected_jobs'] == len(report['jobs']) == len(names),
            'All original jobs required')
    jobs = {}; handles = set()
    for job in report['jobs']:
        name = job['name']; handle = job['job_id']
        require(name in names and name not in jobs, 'Missing, duplicate or unexpected original job')
        require(re.fullmatch('[a-f0-9]{24}', handle) and handle not in handles, 'Duplicate/invalid original handle')
        require(job['verified'] is True and job['stage'] == 'COMPLETED', 'Unverified original job')
        require(job['review']['audit']['all_receipts_verified'] is True
                and job['review']['audit']['reserved_final_seeds_used'] is False, 'Missing original receipt audit')
        require(job['review']['audit']['counts']['rollout_caps'] == 0, 'Capped original job')
        jobs[name] = job; handles.add(handle)
    require(sum(j['review']['games'] for j in jobs.values()) == 10080, 'All 10080 games required')
    for row in source['rows']:
        job = jobs[row['name']]
        require(statistics.same(job['row'], row) and job['review']['games'] == row['shard']['games'],
                'Original job differs from source plan')
    return jobs


def immutable_archive(evidence, name):
    require(evidence['repo'] == 'coyotte508/powergrid-ai-germany-v1'
            and evidence['archive_path'] == 'archives/'+name+'.tgz'
            and evidence['remote_archive_verified'] is True
            and re.fullmatch('[a-f0-9]{40}', evidence['revision']), 'Unpinned original job archive')
    archive = Path(hf_hub_download(evidence['repo'], evidence['archive_path'], revision=evidence['revision']))
    require(digest(archive) == evidence['archive_sha256'], 'Original archive changed')
    with tarfile.open(archive, 'r:gz') as bundle:
        members = [m for m in bundle.getmembers() if m.name == 'manifest.json']
        require(len(members) == 1 and members[0].isfile(), 'Missing/duplicate archive manifest')
        import hashlib
        require(hashlib.sha256(bundle.extractfile(members[0]).read()).hexdigest() == evidence['manifest_sha256'],
                'Archive manifest differs from audited files')


def compare(output):
    output = Path(output).resolve(); intent = output.with_suffix('.intent.json')
    require(not output.exists() and not intent.exists(), 'Inspect existing analysis outcome/intent before retry')
    owner = read(OWNER)
    require(owner['stage'] == 'complete' and owner['completed_games'] == 10080,
            'Wait for complete original execution; do not compete with the coordinator')
    require(all(digest(ROOT/name) == sha for name, sha in owner['code_hashes'].items()), 'Execution code changed')
    manager = manager_module()
    require(manager.RESULT.exists(), 'Complete original result missing')
    source = manager.source_checked(); report = read(manager.RESULT)
    require(report['source_sha256'] == digest(manager.SOURCE)
            and owner['result_sha256'] == digest(manager.RESULT), 'Wrong source/result binding')
    jobs = completion_index(source, report)
    p = statistics.protocol()
    expected = manager.planning.schedule(p, source['sizing']['deals_per_job'])
    expected = {r['shard']['name']: r for r in expected}
    require(set(expected) == set(jobs), 'Wrong frozen schedule')
    artifact = manager.LOCAL/'source/artifact'
    identities = {arm: artifact_identity(artifact, f'policies/{arm}.json') for arm in statistics.ARMS}
    statistics.validate_identities(identities, p)
    for row in source['rows']:
        planned = expected[row['name']]
        require(statistics.same(row['shard'], planned['shard']) and row['arm'] == planned['arm']
                and statistics.same(row['identity'], identities[row['arm']]), 'Changed planned policy or shard')
    pins = {**owner['code_hashes'], str(Path(__file__).relative_to(ROOT)): digest(__file__),
            str(Path(statistics.__file__).relative_to(ROOT)): digest(statistics.__file__),
            str(manager.SOURCE.relative_to(ROOT)): digest(manager.SOURCE),
            str(manager.RESULT.relative_to(ROOT)): digest(manager.RESULT),
            str(OWNER.relative_to(ROOT)): digest(OWNER)}
    write_new(intent, {'started_at': datetime.now(timezone.utc).isoformat(), 'input_hashes': pins,
                      'jobs': len(jobs), 'games': 10080, 'purpose': 'complete development comparison only'})
    reports = {arm: {} for arm in statistics.ARMS}
    counts = {arm: Counter() for arm in statistics.ARMS}
    timings = {arm: [] for arm in statistics.ARMS}; provenance = {}
    for row in sorted(source['rows'], key=lambda r: r['name']):
        name, arm = row['name'], row['arm']; folder = manager.OUT/name
        job = jobs[name]; guard = read(folder/'launch.json')
        require(statistics.same(read(folder/'verified.json'), job), 'Collection summary changed')
        require(job['source_sha256'] == digest(manager.SOURCE)
                and job['guard_sha256'] == digest(folder/'launch.json'), 'Changed collection source/guard')
        require(guard['stage'] == 'launched' and guard['job_id'] == job['job_id']
                and statistics.same(guard['row'], row) and guard['source_fingerprint'] == object_hash(source),
                'Original launch binding mismatch')
        immutable_archive(job['evidence'], name)
        # This is a pure, independent raw re-audit, not the state-mutating collect operation.
        review = manager.verify_artifacts(folder/'artifacts', source, row, job['evidence'])
        require(statistics.same(review, job['review']), 'Saved review differs from independent audit')
        evaluation = folder/'artifacts/job/evaluation'
        records = read(evaluation/'evaluation.json')['results']
        reports[arm].setdefault(row['shard']['group'], []).extend(records)
        counts[arm].update(review['audit']['counts'])
        timings[arm].append({'name': name, 'job_id': job['job_id'], 'games': review['games'], **review['measurement']})
        provenance[name] = {'job_id': job['job_id'], 'evidence': job['evidence'],
            'verified_sha256': digest(folder/'verified.json'), 'launch_sha256': digest(folder/'launch.json'),
            'raw_input_hashes': review['audit']['input_hashes']}
        print(json.dumps({'audited': len(provenance), 'expected': len(jobs), 'name': name}), flush=True)
    result = statistics.analyze(reports, identities)
    costs = {arm: {'counts': dict(counts[arm]), 'per_job': timings[arm],
        'summed_job_wall_seconds': sum(m['seconds'] for m in timings[arm]),
        'cpu_seconds': sum(m['cpu_seconds'] for m in timings[arm]),
        'max_sampled_job_rss_bytes': max(m['sampled_peak_total_rss_bytes'] for m in timings[arm]),
        'scope': 'Concurrent HF batches including startup/validation; sum of job durations is neither elapsed experiment time nor AMD8840U serving latency.'}
        for arm in statistics.ARMS}
    require(all(digest(ROOT/name) == sha for name, sha in pins.items()), 'Input/code changed during analysis')
    # Detect mutations to receipts while the long full-grid audit was in progress.
    for name, evidence in provenance.items():
        folder = manager.OUT/name
        require(digest(folder/'verified.json') == evidence['verified_sha256']
                and digest(folder/'launch.json') == evidence['launch_sha256'], 'Original receipts changed during analysis')
        for path, sha in read(folder/'artifacts/manifest.json').items():
            require(digest(folder/'artifacts'/path) == sha, 'Raw artifact changed during analysis')
        require(digest(folder/'artifacts/manifest.json') == evidence['evidence']['manifest_sha256'],
                'Artifact manifest changed during analysis')
    result.update(created_at=datetime.now(timezone.utc).isoformat(), costs=costs,
                  input_hashes=pins, identities=identities, provenance=provenance,
                  protocol_sha256=statistics.PROTOCOL_SHA, raw_receipts_reaudited=True)
    temporary = output.with_suffix('.writing.json'); write_new(temporary, result)
    os.link(temporary, output); temporary.unlink()  # Atomic, exclusive publication of complete JSON.
    return {'complete': True, 'games': 10080, 'jobs': len(jobs), 'comparison_sha256': digest(output)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__); parser.add_argument('--output', type=Path, default=OUTPUT)
    print(json.dumps(compare(parser.parse_args().output)))
