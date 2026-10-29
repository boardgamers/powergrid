"""Fresh original-archive audit and complete frozen final qualification.

No submissions, model calls, game execution, training, policy selection or
deployment. Never assess partial games or resume an interrupted audit blindly.
"""
from concurrent.futures import ProcessPoolExecutor, as_completed
import hashlib
import json
from pathlib import Path
import tarfile

import manage_selected_public_policy_final_v1 as manager
from public_policy_final_audit_v1 import (
    PROTOCOL_SHA, artifact_identity, assess_final_games, digest, protocol, read, require, same,
)
from public_policy_final_contract_v1 import object_hash
from selected_public_policy_final_dispatch_v1 import durable_write
from selected_public_policy_final_streaming_v1 import audit_archive

ROOT = manager.ROOT
OUT = ROOT/'ai/runs/selected-public-policy-final-assessment-v1'
RESULT = ROOT/'ai/strong/selected-public-policy-final-assessment-v1.json'
TARGET = ROOT/'ai/runs/current-full-serving-8840u-prepared-v1'
COLLECTED_TARGET = ROOT/'ai/runs/current-full-serving-8840u-collected-v1'


def standalone_proof(identity):
    """Check saved original package/target bindings without replay or inference."""
    prepared = read(TARGET/'prepared.json')
    launch_path = ROOT/'ai/strong/current-full-serving-8840u-launch-v1.json'
    launch = read(launch_path); status_path = COLLECTED_TARGET/'output/status.json'; status = read(status_path)
    technical_path = ROOT/manager.preparation.selection.TECHNICAL; technical = read(technical_path)
    package = TARGET/'package'; manifest_path = package/'benchmark-manifest.json'
    manifest = read(manifest_path); arm = manager.preparation.selection.ARM
    require(launch['stage'] == 'launched' and launch['host'] == 'minipc' and status['pid'] == launch['pid']
            and status['stage'] == 'completed' and status['passed'] is True
            and '8840U' in status['processor'], 'Missing original completed target process')
    require(prepared['positions'] == manifest['positions'] == 2553
            and prepared['requests'] == manifest['requests'] == status['completed_requests'] == 5106,
            'Incomplete original standalone replay')
    require(digest(status_path) == technical['status_sha256']
            and digest(manifest_path) == prepared['manifest_sha256'] == launch['manifest_sha256']
            == status['manifest_sha256'] == technical['manifest_sha256'], 'Standalone/target manifest binding changed')
    require(same(manifest['identities'][arm], identity) and same(technical['identities'][arm], identity)
            and artifact_identity(package/'artifact', f'policies/{arm}.json') == identity,
            'Standalone package is not the selected complete policy')
    require(digest(package/'benchmark.py') == manifest['runner_sha256'] == prepared['runner_sha256'] == launch['runner_sha256']
            and digest(package/'cases.jsonl') == prepared['cases_sha256'] == launch['cases_sha256'],
            'Standalone runner or original fixtures changed')
    files = manifest['files']
    require(set(files)|{'benchmark-manifest.json'} == {str(p.relative_to(package)) for p in package.rglob('*') if p.is_file()},
            'Standalone file set changed')
    manager.preparation.selection.pinned_files(package, files)
    archive = TARGET/'package.tgz'
    require(digest(archive) == prepared['package_sha256'] == launch['package_sha256']
            and archive.stat().st_size == prepared['package_bytes'] == launch['package_bytes'], 'Original standalone archive changed')
    expected = {**files, 'benchmark-manifest.json': prepared['manifest_sha256']}
    with tarfile.open(archive, 'r:gz') as bundle:
        members = bundle.getmembers()
        require(len(members) == len(expected) and {m.name for m in members} == set(expected), 'Standalone archive file set differs')
        for member in members:
            require(member.isfile(), 'Invalid standalone archive member')
            with bundle.extractfile(member) as stream:
                require(hashlib.file_digest(stream, 'sha256').hexdigest() == expected[member.name], 'Standalone archive bytes differ')
    pins = {str(p.relative_to(ROOT)): digest(p) for p in (TARGET/'prepared.json', launch_path, status_path,
        technical_path, manifest_path, archive)}
    pins.update({str((package/name).relative_to(ROOT)): sha for name, sha in files.items()})
    return {'verified': True, 'identity': identity, 'package_sha256': prepared['package_sha256'],
        'package_manifest_sha256': prepared['manifest_sha256'], 'original_target_pid': launch['pid'],
        'processor': status['processor'], 'selected_policy_positions': 2553, 'original_total_requests': 5106,
        'input_hashes': pins, 'new_inference_calls': 0, 'new_games': 0}


def complete_originals(context):
    collection_path = manager.OUT/'collection-results.json'; collection = read(collection_path)
    require(collection['complete'] is True and collection['verified_jobs'] == collection['submitted_jobs'] == 320
            and collection['completed_games'] == 20160 and collection['qualified'] is False,
            'Wait for all original final jobs and complete initial audits')
    require(collection['release_sha256'] == object_hash(context['release'])
            and collection['context_sha256'] == object_hash(context), 'Complete collection belongs to another admission')
    launches = manager.originals(context)
    rows = context['release']['plan']['rows']; names = {r['name'] for r in rows}
    require(set(launches) == set(collection['originals']) == names, 'Missing original final jobs')
    tasks = []; pins = {str(collection_path.relative_to(ROOT)): digest(collection_path)}
    for row in rows:
        name = row['name']; launch = launches[name]; saved = manager.collected(context, launch)
        require(saved is not None and same(saved, collection['originals'][name]), 'Initial original audit changed')
        directory = manager.OUT/'originals'/name
        for path in (directory/'review.json', directory/'collected.json', directory/'evidence.json',
                     manager.OUT/'dispatch/jobs'/(name+'.json')):
            pins[str(path.relative_to(ROOT))] = digest(path)
        tasks.append({'name': name, 'launch': launch, 'evidence': saved['evidence'],
            'archive': str(directory/'original.tgz'), 'source_root': context['source_root'],
            'release': context['release'], 'bootstrap': context['bootstrap'],
            'initial_review_sha256': read(directory/'review.json')['review_sha256'],
            'receipt': str(OUT/'reviews'/(name+'.json')), 'scratch': str(OUT/'scratch')})
    return tasks, pins


def independent_one(task):
    result = audit_archive(task['archive'], task['source_root'], task['release'], task['launch'],
        task['evidence'], task['bootstrap'], hf_stage='COMPLETED', scratch_root=task['scratch'],
        receipt=task['receipt'], purpose='independent_final_audit')
    require(result['review_sha256'] == task['initial_review_sha256'], 'Fresh raw audit differs from original collection')
    return {'name': task['name'], **result}


def assess_receipts(context, tasks, results, standalone):
    """Only complete, separately produced and bound raw audits reach statistics."""
    names = {r['name'] for r in context['release']['plan']['rows']}
    require(len(tasks) == len(results) == len(names) == 320 and {t['name'] for t in tasks} == set(results) == names,
            'Incomplete separate final audit')
    identity = context['release']['plan']['identity']
    require(standalone['verified'] is True and same(standalone['identity'], identity)
            and standalone['selected_policy_positions'] == 2553, 'Missing selected standalone target proof')
    audited = []; originals = {}
    for task in tasks:
        name = task['name']; result = results[name]; path = Path(task['receipt']); receipt = read(path)
        require(result['name'] == name and result['receipt'] == str(path) and result['receipt_sha256'] == digest(path),
                'Fresh audit receipt changed')
        require(receipt['purpose'] == 'independent_final_audit' and receipt['qualified'] is False
                and receipt['release_sha256'] == object_hash(context['release'])
                and receipt['launch_sha256'] == object_hash(task['launch']), 'Not a separate bound final audit')
        review = receipt['review']
        require(object_hash(review) == receipt['review_sha256'] == result['review_sha256'] == task['initial_review_sha256'],
                'Independent raw audit differs from initial collection')
        require(review['verified'] is True and review['qualified'] is False and review['name'] == name
                and review['job_id'] == task['launch']['job_id'] and review['original_hf_stage'] == 'COMPLETED'
                and review['games'] == task['launch']['row']['shard']['games']
                and review['release_sha256'] == receipt['release_sha256']
                and review['launch_sha256'] == receipt['launch_sha256']
                and same(review['identity'], identity) and same(receipt['evidence'], task['evidence'])
                and same(review['evidence'], task['evidence'])
                and receipt['original_archive_sha256'] == task['evidence']['archive_sha256'],
                'Fresh audit belongs to another original job, policy or archive')
        require(review['provenance']['candidate_sha256'] == context['release']['plan']['candidate_sha256']
                and same(review['audit']['expected'], task['launch']['row']['shard']), 'Executed candidate or shard differs')
        audited.append(review['audit'])
        originals[name] = {'job_id': review['job_id'], 'games': review['games'], 'evidence': task['evidence'],
            'fresh_receipt_sha256': result['receipt_sha256'], 'review_sha256': result['review_sha256']}
    strength = assess_final_games(audited, identity)
    require(strength['games'] == 20160 and strength['shards'] == 320 and strength['protocol_sha256'] == PROTOCOL_SHA,
            'Strength assessment changed scope')
    require(strength['strength_passed'] is (len(strength['errors']) == 0), 'Contradictory strength assessment')
    return {'complete': True, 'created_at': manager.preparation.now(), 'qualified': False,
        'qualification_verified': False,
        'verdict': 'strength_passed' if strength['strength_passed'] else 'strength_failed', 'identity': identity,
        'candidate_sha256': context['release']['plan']['candidate_sha256'], 'protocol_sha256': PROTOCOL_SHA,
        'release_sha256': object_hash(context['release']), 'admission_sha256': context['release']['admission_sha256'],
        'independent_raw_audit': {'jobs': 320, 'games': 20160, 'all_reviews_exact': True, 'workers': 4},
        'strength': strength, 'standalone_target': standalone, 'originals': originals,
        'scope': protocol()['scope'], 'reserved_final_seeds_used': True,
        'new_games_by_assessment': 0, 'new_inference_calls': 0, 'deployed': False,
        'qualification_basis': 'Strength and receipt accounting only until run() revalidates the actual substantive selection/admission, native/export/8840U evidence and original standalone package.',
        'limitations': ['Germany with public money and the frozen opponent/seed protocol only.',
            'Confidence intervals are per comparison, not a simultaneous family-wide guarantee.',
            'Value calibration for player analysis and browser execution are not established.',
            'Target timings describe the recorded fixture distribution, excluding platform queueing.']}


def run():
    context = manager.admission()  # Incomplete confirmation stops before any output or worker pool.
    require((manager.OUT/'collection-results.json').is_file(), 'Wait for all original final jobs and complete initial audits')
    require(not OUT.exists() and not RESULT.exists(), 'Inspect existing final assessment; no blind audit replay')
    with manager.operation(context):
        tasks, collection_pins = complete_originals(context)
        require(not OUT.exists() and not RESULT.exists(), 'Inspect existing final assessment; no blind audit replay')
        standalone = standalone_proof(context['release']['plan']['identity'])
        paths = [Path(__file__).resolve(), ROOT/'ai/strong/arena_statistics.py']
        pins = {}
        for group in (context['input_hashes'], collection_pins, standalone['input_hashes'],
                      {str(p.relative_to(ROOT)): digest(p) for p in paths}):
            for name, sha in group.items():
                require(name not in pins or pins[name] == sha, 'Conflicting final evidence pin: '+name)
                pins[name] = sha
        manager.preparation.selection.pinned_files(ROOT, pins)
        OUT.mkdir(); (OUT/'reviews').mkdir()
        durable_write(OUT/'intent.json', {'stage': 'separate_full_original_audit', 'created_at': manager.preparation.now(),
            'context_sha256': object_hash(context), 'input_hashes': pins, 'workers': 4,
            'automatic_retries': False, 'new_games': 0}, exclusive=True)
        results = {}; pool = ProcessPoolExecutor(max_workers=4)
        try:
            futures = {pool.submit(independent_one, task): task['name'] for task in tasks}
            for future in as_completed(futures):
                result = future.result(); require(result['name'] == futures[future], 'Crossed parallel audit result')
                results[result['name']] = result
                durable_write(OUT/'progress.json', {'checked_at': manager.preparation.now(), 'audited_jobs': len(results),
                    'expected_jobs': 320, 'results': results, 'qualified': False})
                print(json.dumps({'independently_audited': len(results), 'expected': 320}), flush=True)
            pool.shutdown(wait=True)
            manager.preparation.selection.pinned_files(ROOT, pins)
            report = assess_receipts(context, tasks, results, standalone)
            # Revalidate substantive selection and target/export admission after
            # the long fresh audit, without re-executing policy or target jobs.
            require(same(manager.admission(), context), 'Admission/technical proof changed during final audit')
            manager.preparation.selection.pinned_files(ROOT, pins)
            report.update(qualification_verified=True, qualified=report['strength']['strength_passed'],
                verdict='passed' if report['strength']['strength_passed'] else 'failed',
                qualification_basis='Complete frozen strength gate plus revalidated substantive selection/admission, full native/export/actual-8840U evidence and the identical standalone package. Raw strength subreport alone is not sufficient.')
            report['input_hashes'] = pins
            durable_write(RESULT, report, exclusive=True)
            durable_write(OUT/'completed.json', {'result_sha256': digest(RESULT), 'qualified': report['qualified'],
                'verdict': report['verdict'], 'new_games': 0}, exclusive=True)
            return {k: report[k] for k in ('complete', 'qualified', 'verdict', 'independent_raw_audit')}
        except BaseException as error:
            pool.shutdown(wait=True, cancel_futures=True)
            durable_write(OUT/'failure.json', {'stage': 'stopped_for_inspection', 'failure_type': type(error).__name__,
                'returned_audits': len(results), 'successful_receipts_and_failed_scratch_preserved': True,
                'automatic_retries': False, 'qualified': False}, exclusive=True)
            raise


if __name__ == '__main__': print(json.dumps(run()), flush=True)
