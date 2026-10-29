"""Compare a complete canonical study across explicit execution attempts.

No job API, uploads, simulations, inference, selection or owner-state rewrites.
Four isolated processes reuse the frozen full raw verifiers. Cached archives are
required locally; a missing artifact is an error, never an implicit download.
"""
import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
import multiprocessing
import os
from pathlib import Path
import re
import resource
import tarfile
import time

from huggingface_hub import hf_hub_download
import current_auction_attempt_authentication_v3 as auth
import current_auction_confirmation_analysis_v1 as statistics
import current_auction_parallel_audit_v1 as originals
from public_policy_final_audit_v1 import artifact_identity

ROOT = auth.ROOT
read, digest, require, object_hash = auth.read, auth.digest, auth.require, auth.object_hash
OUTPUT = ROOT/'ai/strong/current-auction-attempt-comparison-v3.json'
READINESS = ROOT/'ai/strong/current-auction-parallel-comparison-readiness-v1.json'
CONTEXT = None


def write_new(path, value):
    with Path(path).open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')


def complete_reference_index(plan, found):
    """Reject incomplete coverage before loading recovery reviews or raw data."""
    slots = {s['name']: s for s in plan['slots'] if s['kind'] != 'preserved_original'}
    refs = found['available']
    require(found['complete'] is True and found['missing'] == []
            and found['required'] == len(slots) == len(refs), 'Incomplete recovery coverage; do not read outcomes')
    indexed = {}
    handles = {s['original']['job_id'] for s in plan['slots'] if s['original']}
    attempts = set()
    for ref in refs:
        name = ref['name']
        require(name in slots and name not in indexed, 'Duplicate/foreign recovery assignment')
        slot = slots[name]
        require(ref['original_row_sha256'] == slot['original_row_sha256'], 'Changed recovery row')
        require(ref['stage'] == 'COMPLETED' and ref['verified'] is True, 'Unverified recovery assignment')
        require(re.fullmatch('[a-f0-9]{24}', ref['job_id']) and ref['job_id'] not in handles,
                'Duplicate/original recovery handle')
        require(re.fullmatch('[a-z0-9_-]+', ref['attempt_id']) and ref['attempt_id'] not in attempts,
                'Duplicate/invalid recovery attempt')
        require(re.fullmatch('[a-f0-9]{64}', ref['review_sha256']), 'Unpinned recovery review')
        expected_failure = auth.previous.first.worker.FAILED_HANDLE if slot['kind'] == 'failed_original_recovery' else None
        require(ref['original_failed_handle'] == expected_failure, 'Original failure history changed')
        if slot['kind'] == 'failed_original_recovery':
            require(all(ref[k] == v for k, v in plan['first_recovery'].items()), 'First recovery substituted')
        indexed[name] = ref
        handles.add(ref['job_id']); attempts.add(ref['attempt_id'])
    require(set(indexed) == set(slots), 'Missing recovery assignment')
    return indexed


def cached_archive(evidence, name):
    """Verify the original immutable archive from cache, without network I/O."""
    require(evidence['repo'] == 'coyotte508/powergrid-ai-germany-v1'
            and evidence['archive_path'] == 'archives/'+name+'.tgz'
            and evidence['remote_archive_verified'] is True
            and re.fullmatch('[a-f0-9]{40}', evidence['revision']), 'Unpinned archive')
    path = Path(hf_hub_download(evidence['repo'], evidence['archive_path'],
                               revision=evidence['revision'], local_files_only=True))
    require(digest(path) == evidence['archive_sha256'], 'Cached archive bytes changed')
    with tarfile.open(path, 'r:gz') as archive:
        manifests = [m for m in archive.getmembers() if m.name == 'manifest.json']
        require(len(manifests) == 1 and manifests[0].isfile(), 'Missing/ambiguous archived manifest')
        require(hashlib.sha256(archive.extractfile(manifests[0]).read()).hexdigest()
                == evidence['manifest_sha256'], 'Archived manifest changed')


def tree_pin(path, expected=None):
    path = Path(path)
    sha = digest(path/'manifest.json') if expected is None else expected
    auth.first.worker.base.tree(path, 'manifest.json', sha)
    return {'directory': str(path.relative_to(ROOT)), 'manifest_sha256': sha}


def attempt_context():
    # Preparation checks are shared within each isolated process, not repeated
    # for every shard. Individual launch/receipt/raw bindings are still checked.
    global CONTEXT
    if CONTEXT is None:
        CONTEXT = auth.context()
    return CONTEXT


def audit_case(case):
    started = time.perf_counter(); before = resource.getrusage(resource.RUSAGE_SELF)
    require(digest(ROOT/case['receipt_file']) == case['receipt_sha256'], 'Receipt changed before independent audit')
    if case['backend'] == 'original':
        result = originals.audit_original(case['original_case'])
        manager = originals.manager('confirmation')
        folder = manager.OUT/case['name']; saved = read(ROOT/case['receipt_file'])
        cached_archive(saved['evidence'], case['name'])
        raw = saved['review']; stage = saved['stage']
        trees = [tree_pin(folder/'artifacts', saved['evidence']['manifest_sha256'])]
        require(result['review_sha256'] == object_hash(raw), 'Original independent review differs')
        evaluation = manager.evaluation_directory(folder, saved)
    else:
        context = attempt_context()
        require(object_hash(context['routes']) == case['routing_sha256'], 'Attempt routing changed')
        reference = case['reference']; saved = auth.authenticate(reference, context)
        paths = auth.locations(case['name'], case['backend']); folder = paths['folder']
        is_bucket = case['backend'] in ('bucket_first_v3', 'bucket_remaining_v3')
        root = folder/(reference['attempt_id']+'-collected') if is_bucket else folder
        envelope = root/('envelope' if is_bucket else 'artifacts')
        trees = []
        checkpoints = {object_hash(item['evidence']): item['evidence'] for item in saved['checkpoint_archives']}
        seen = set()
        def reader(evidence):
            key = object_hash(evidence)
            require(key in checkpoints and key not in seen, 'Unknown/repeated checkpoint')
            seen.add(key)
            name = evidence['path'].split('/')[1] if is_bucket else Path(evidence['archive_path']).stem
            if not is_bucket:
                cached_archive(evidence, name)
            directory = root/'checkpoints'/name
            trees.append(tree_pin(directory, evidence['manifest_sha256']))
            return directory
        if not is_bucket:
            cached_archive(saved['envelope_evidence'], reference['attempt_id']+'-final')
        args = (envelope, saved['envelope_evidence'], paths['bundle'], saved['bundle_manifest_sha256'], auth.first.ORIGINAL)
        audited = (paths['collector'].audit_envelope(*args, case['name'], reader)
                   if case['backend'] == 'retained_v2' else paths['collector'].audit_envelope(*args, reader))
        require(seen == set(checkpoints), 'Not every checkpoint independently checked')
        for key, value in audited.items():
            expected = True if key == 'versioned_archive_pending' else saved[key]
            require(value == expected, 'Independent envelope review differs: '+key)
        raw = audited['review']; stage = saved['terminal']['stage']
        trees.append(tree_pin(envelope, saved['envelope_evidence']['manifest_sha256']))
        if is_bucket:
            trees.append(tree_pin(root, saved['versioned_collection_archive']['manifest_sha256']))
        evaluation = envelope/'raw/job/evaluation'
    require(digest(ROOT/case['receipt_file']) == case['receipt_sha256'], 'Receipt changed during independent audit')
    require(object_hash(raw) == case['raw_review_sha256'], 'Full independent raw review differs')
    after = resource.getrusage(resource.RUSAGE_SELF)
    return {'name': case['name'], 'backend': case['backend'], 'job_id': case['job_id'],
            'original_hf_stage': stage, 'games': raw['games'], 'review_sha256': object_hash(raw),
            'counts': raw['audit']['counts'], 'receipt_sha256': case['receipt_sha256'],
            'raw_trees': trees, 'evaluation_file': str((evaluation/'evaluation.json').relative_to(ROOT)),
            'evaluation_sha256': digest(evaluation/'evaluation.json'),
            'seconds': time.perf_counter()-started,
            'cpu_seconds': after.ru_utime+after.ru_stime-before.ru_utime-before.ru_stime,
            'process_lifetime_peak_rss_bytes': after.ru_maxrss*1024}


def parallel_audit(cases):
    pool = ProcessPoolExecutor(max_workers=4, mp_context=multiprocessing.get_context('spawn'))
    try:
        results = list(pool.map(audit_case, cases, chunksize=1))
    except BaseException:
        pool.shutdown(wait=True, cancel_futures=True)
        raise
    else:
        pool.shutdown(wait=True)
    return results


def match_audits(cases, results):
    wanted = {c['name']: c for c in cases}
    require(len(wanted) == len(cases) == len(results), 'Every canonical audit required')
    indexed = {}
    for result in results:
        name = result['name']
        require(name in wanted and name not in indexed, 'Duplicate/foreign independent audit')
        case = wanted[name]
        for field in ('backend', 'job_id', 'games', 'receipt_sha256'):
            require(result[field] == case[field], 'Changed audit identity/coverage: '+field)
        require(result['review_sha256'] == case['raw_review_sha256']
                and result['counts'] == case['counts'] and result['original_hf_stage'] == case['stage'],
                'Changed full audit/status/counts')
        indexed[name] = result
    return indexed


def make_cases(plan, routes, refs):
    manager = originals.manager('confirmation'); cases = []; saved = {}
    for slot in plan['slots']:
        name = slot['name']
        if slot['kind'] == 'preserved_original':
            folder = manager.OUT/name; receipt = manager.verified_path(folder); job = read(receipt)
            require(all(job[k] == v for k, v in slot['original'].items())
                    and object_hash(job['row']) == slot['original_row_sha256'], 'Preserved original snapshot changed')
            original_case = {'kind': 'confirmation', 'name': name, 'job_id': job['job_id'],
                'source_sha256': digest(manager.SOURCE), 'verified_sha256': digest(receipt),
                'guard_sha256': job['guard_sha256']}
            backend = 'original'; stage = job['stage']; extra = {'original_case': original_case}
        else:
            ref = refs[name]; backend = routes[name]; receipt = auth.locations(name, backend)['review']
            require(digest(receipt) == ref['review_sha256'], 'Recovery review changed')
            job = read(receipt); stage = job['terminal']['stage']
            extra = {'reference': ref, 'routing_sha256': object_hash(routes)}
        raw = job['review']; saved[name] = job
        require(raw['games'] == len(slot['episodes']), 'Canonical game coverage differs')
        cases.append({'name': name, 'backend': backend, 'job_id': job['job_id'], 'stage': stage,
            'games': raw['games'], 'receipt_file': str(receipt.relative_to(ROOT)), 'receipt_sha256': digest(receipt),
            'raw_review_sha256': object_hash(raw), 'counts': raw['audit']['counts'], **extra})
    return cases, saved


def check_inputs(plan):
    manager = originals.manager('confirmation'); source = manager.source_checked()
    readiness = read(READINESS)
    require(readiness['passed'] and readiness['ready_for_complete_grid_audit']
            and all(digest(ROOT/p) == sha for p, sha in readiness['input_hashes'].items()), 'Frozen verifier readiness changed')
    p = statistics.protocol(); final = ROOT/'ai/strong/final-protocol-multiplayer.json'
    require(digest(final) == p['final_protocol_sha256'], 'Final requirements changed')
    schedule = {r['shard']['name']: r for r in manager.planning.schedule(p, source['sizing'])}
    require(set(schedule) == {s['name'] for s in plan['slots']}, 'Canonical schedule changed')
    identities = {arm: artifact_identity(manager.LOCAL/'source/artifact', 'policies/'+arm+'.json') for arm in statistics.ARMS}
    statistics.validate_identities(identities, p)
    for row in source['rows']:
        expected = schedule[row['name']]
        require(row['shard'] == expected['shard'] and row['arm'] == expected['arm']
                and row['identity'] == identities[row['arm']], 'Frozen row/policy differs')
    auth_ready_path = ROOT/'ai/strong/current-auction-attempt-authentication-preflight-v3.json'
    auth_ready = read(auth_ready_path)
    require(auth_ready['passed'] is True and auth_ready['code_sha256'] == digest(auth.__file__)
            and all(digest(ROOT/p) == sha for p, sha in auth_ready['frozen_input_hashes'].items()),
            'Attempt authentication readiness changed')
    paths = [Path(__file__), Path(auth.__file__), Path(originals.__file__), Path(statistics.__file__),
             manager.SOURCE, final, READINESS, statistics.PROTOCOL, auth_ready_path]
    preparation_pins = {}
    for m in (auth.previous.first, auth.previous.remaining, auth.first, auth.remaining):
        prepared = m.PRE/'prepared.json'; paths.extend((m.SOURCE, prepared))
        preparation_pins.update(read(prepared)['code_hashes'])
    pins = {**plan['input_hashes'], **readiness['input_hashes'],
            **auth_ready['frozen_input_hashes'], **preparation_pins,
            **{str(p.relative_to(ROOT)): digest(p) for p in paths}}
    require(all(digest(ROOT/p) == sha for p, sha in pins.items()), 'Frozen comparison inputs changed')
    return source, identities, final, pins


def compare(output=OUTPUT):
    output = Path(output).resolve(); intent = output.with_suffix('.intent.json')
    require(not output.exists() and not intent.exists(), 'Inspect existing comparison intent/outcome before retry')
    plan = auth.coverage.actual_plan(); routes = auth.actual_routes(plan)
    refs = complete_reference_index(plan, auth.inventory(plan, routes))
    source, identities, final, pins = check_inputs(plan)
    cases, saved = make_cases(plan, routes, refs)
    require(len(cases) == 944 and sum(c['games'] for c in cases) == 26880, 'Whole canonical study required')
    write_new(intent, {'started_at': datetime.now(timezone.utc).isoformat(), 'input_hashes': pins,
        'cases': cases, 'routing_sha256': object_hash(routes), 'new_jobs': 0, 'new_games': 0,
        'purpose': 'Complete confirmation comparison; not final qualification'})
    audits = match_audits(cases, parallel_audit(cases))
    # Reuse the original full coverage gate after independent authentication and
    # raw audits, including exact episode lists and preserved original failure.
    def audited_review(ref):
        job = saved[ref['name']]
        require(audits[ref['name']]['review_sha256'] == object_hash(job['review']), 'Independent audit missing')
        return {**job, 'original_failed_handle': job.get('original_failed_handle')}
    covered = auth.coverage.require_complete_assignments(plan, list(refs.values()), audited_review)
    require(covered['recovery_shards'] == 324 and covered['recovery_games'] == 7116, 'Recovery coverage differs')
    reports = {arm: {} for arm in statistics.ARMS}; counts = {arm: Counter() for arm in statistics.ARMS}
    timings = {arm: [] for arm in statistics.ARMS}
    for row in source['rows']:
        name, arm = row['name'], row['arm']; audit = audits[name]; job = saved[name]
        evaluation = ROOT/audit['evaluation_file']
        require(digest(evaluation) == audit['evaluation_sha256'], 'Audited evaluation changed')
        reports[arm].setdefault(row['shard']['group'], []).extend(read(evaluation)['results'])
        counts[arm].update(job['review']['audit']['counts'])
        timings[arm].append({'name': name, 'job_id': job['job_id'], 'games': job['review']['games'], **job['review']['measurement']})
    result = statistics.analyze(reports, identities)
    result['confirmation_requirements_review'] = statistics.confirmation_requirements(result, read(final))
    require(all(digest(ROOT/p) == sha for p, sha in pins.items()), 'Input changed during comparison')
    for case in cases:
        require(digest(ROOT/case['receipt_file']) == case['receipt_sha256'], 'Receipt changed during comparison')
        for tree in audits[case['name']]['raw_trees']:
            tree_pin(ROOT/tree['directory'], tree['manifest_sha256'])
        audit = audits[case['name']]
        require(digest(ROOT/audit['evaluation_file']) == audit['evaluation_sha256'], 'Evaluation changed during comparison')
    costs = {arm: {'counts': dict(counts[arm]), 'per_job': timings[arm],
        'summed_job_wall_seconds': sum(t['seconds'] for t in timings[arm]),
        'cpu_seconds': sum(t['cpu_seconds'] for t in timings[arm]),
        'max_sampled_job_rss_bytes': max(t['sampled_peak_total_rss_bytes'] for t in timings[arm]),
        'scope': 'Successful canonical attempts; failed-attempt costs are additional. Summed job durations are not elapsed experiment time.'}
        for arm in statistics.ARMS}
    result.update(created_at=datetime.now(timezone.utc).isoformat(), input_hashes=pins, identities=identities,
        protocol_sha256=statistics.PROTOCOL_SHA, costs=costs, raw_receipts_reaudited=True,
        canonical_coverage={'jobs': 944, 'games': 26880, 'game_keys_sha256': plan['game_keys_sha256'],
                            'shards_by_disposition': plan['shards_by_disposition']},
        attempt_provenance={c['name']: {'backend': c['backend'], 'job_id': c['job_id'], 'stage': c['stage'],
            'receipt_file': c['receipt_file'], 'receipt_sha256': c['receipt_sha256'],
            'prior_failed_attempts': saved[c['name']].get('prior_failed_attempts', [])} for c in cases},
        original_failure_preserved=plan['original_failure_preserved'],
        parallel_raw_audit={'workers': 4, 'all_reviews_exact': True, 'jobs': audits,
                            'readiness_sha256': digest(READINESS)},
        candidate_selected=False, qualified=False, reserved_final_seeds_used=False)
    temporary = output.with_suffix('.writing.json'); write_new(temporary, result)
    os.link(temporary, output); temporary.unlink()
    return {'complete': True, 'games': 26880, 'jobs': 944, 'comparison_sha256': digest(output), 'qualified': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--output', type=Path, default=OUTPUT)
    args = parser.parse_args()
    print(json.dumps(compare(args.output) if args.execute else auth.inventory_summary(auth.inventory())), flush=True)
