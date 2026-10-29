"""Prepare/publish a real final source only after complete reviewed selection.

No job-submission API or game execution. Preparation archives the reviewed
selection, freezes candidate bytes and builds the original final schedule.
Unknown preparation/publication outcomes require inspection, never blind retry.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import shutil
import tarfile

from huggingface_hub import HfApi, hf_hub_download
import current_auction_final_selection_v1 as selection
from policy_iteration_evidence_archive import upload_evidence
from public_policy_final_audit_v1 import PROTOCOL_SHA, digest, finite, read, require, same, schedule
from selected_public_policy_final_collection_v1 import checked_tree
from selected_public_policy_final_dispatch_v1 import durable_write, final_bootstrap, validate_release
import selected_public_policy_final_source_v1 as source_builder

ROOT = selection.ROOT
OUT = ROOT / 'ai/runs/selected-public-policy-final-prepared-v1'
REPO = 'coyotte508/powergrid-ai-training-v1'
SOURCE_NAME = 'strong-source-selected-public-policy-final-v1.tgz'


def now(): return datetime.now(timezone.utc).isoformat()


def resources(comparison, confirmation_source):
    """Use all completed selected-arm costs; never use partial outcomes."""
    require(comparison['complete'] is True and comparison['games'] == 26880, 'Complete comparison required for allocation')
    arm = selection.ARM; rows = {r['name']: r for r in confirmation_source['rows'] if r['arm'] == arm}
    measured = comparison['costs'][arm]['per_job']
    require(len(measured) == len(rows) == 672 and {m['name'] for m in measured} == set(rows),
            'Incomplete or duplicated selected-policy cost records')
    require(len({m['job_id'] for m in measured}) == len(rows), 'Duplicate original cost handles')
    sizing = confirmation_source['sizing']
    require(sizing['flavor'] == 'cpu-upgrade' and sizing['workers'] == 4
            and sizing['search_workers'] == 4 and sizing['inference_threads'] == 1, 'Unmeasured concurrency')
    per_count = {str(n): sizing['per_game_seconds'][arm] for n in range(2, 7)}
    peak = sizing['sampled_peak_rss_bytes']
    finite(peak); finite(per_count['2'])
    require(peak > 0 and per_count['2'] > 0, 'Missing complete-pilot costs')
    for item in measured:
        row = rows[item['name']]; shard = row['shard']
        require(item['job_id'] == comparison['provenance'][item['name']]['job_id']
                and item['games'] == shard['games'], 'Cost belongs to another original job')
        finite(item['seconds']); finite(item['sampled_peak_total_rss_bytes'])
        require(item['seconds'] > 0 and item['sampled_peak_total_rss_bytes'] > 0, 'Missing measured costs')
        n = str(shard['players'])
        per_count[n] = max(per_count[n], item['seconds']/item['games'])
        peak = max(peak, item['sampled_peak_total_rss_bytes'])
    require(2*peak < .8*32*1024**3, 'Measured memory requires a new resource design')
    allocation = {}; workers = {}; estimates = {}
    for shard in schedule():
        seconds = 900 + 2*per_count[str(shard['players'])]*shard['games']
        hours = math.ceil(seconds/(.75*3600))
        require(hours <= 24, 'Measured final shard exceeds one day; redesign resources before admission')
        allocation[shard['name']] = {'flavor': 'cpu-upgrade', 'timeout': f'{hours}h'}
        workers[shard['name']] = 4
        estimates[shard['name']] = seconds
    return {'allocation': allocation, 'workers': workers, 'projected_seconds_with_margin': estimates,
        'per_count_seconds_per_game': per_count, 'sampled_peak_bytes': peak,
        'runtime_multiplier': 2, 'setup_allowance_seconds': 900, 'timeout_utilization': .75,
        'memory_margin': 2, 'max_active_jobs': 64,
        'scope': 'Planning allowances from all complete selected-arm costs plus original endpoint pilots; not upper-bound guarantees.'}


def readiness(review_path):
    review_path = Path(review_path).resolve()
    proof = selection.verify(review_path)
    require(proof['ready_for_candidate_freeze'] is True and not proof['final_launch_admitted'], 'Selection review not admitted')
    require(review_path.is_relative_to(ROOT), 'Review must be stored in the research checkout')
    comparison = read(ROOT / selection.COMPARISON)
    allocation = resources(comparison, read(ROOT / selection.SOURCE))
    paths = [review_path, Path(__file__).resolve(), Path(selection.__file__).resolve(), Path(source_builder.__file__).resolve(),
        ROOT / selection.COMPARISON, ROOT / selection.SOURCE, ROOT / selection.TECHNICAL, ROOT / selection.BINDING,
        ROOT / selection.EXPORT, ROOT / selection.EXPORT_AUDIT,
        ROOT / 'ai/strong/public_policy_selected_final_job_v1.py', ROOT / 'ai/strong/selected_public_policy_final_dispatch_v1.py',
        ROOT / 'ai/strong/selected_public_policy_final_collection_v1.py', ROOT / 'ai/strong/selected_public_policy_final_streaming_v1.py',
        ROOT / 'ai/strong/policy_iteration_evidence_archive.py', ROOT / 'ai/strong/manage-current-auction-runtime-v1.py',
        ROOT / 'ai/strong/current-full-serving-results-evidence-v1.json', ROOT / 'ai/strong/current-engine-export-evidence-v1.json']
    pins = {}
    for group in (comparison['input_hashes'], read(ROOT / selection.EXPORT)['input_hashes'],
                  {str(p.relative_to(ROOT)): digest(p) for p in paths}):
        for name, sha in group.items():
            require(name not in pins or pins[name] == sha, 'Conflicting evidence pin: ' + name)
            pins[name] = sha
    selection.pinned_files(ROOT, pins)
    return {'checked_at': now(), 'selection': proof, 'review_path': str(review_path.relative_to(ROOT)),
            'resources': allocation, 'input_hashes': pins, 'qualified': False, 'reserved_final_seeds_used': False}


def prepare(review_path):
    ready = readiness(review_path)  # Must fail before creating a directory or API client on an incomplete study.
    require(not OUT.exists(), 'Inspect existing preparation and upload outcomes; do not overwrite')
    api = HfApi(); model_repo = 'coyotte508/powergrid-ai-germany-v1'
    require(api.model_info(model_repo).private, 'Selection evidence must remain private')
    archive_name = 'selected-public-policy-final-selection-v1'
    require(not api.file_exists(model_repo, 'archives/'+archive_name+'.tgz'), 'Inspect existing remote selection archive')
    OUT.mkdir(); durable_write(OUT/'intent.json', {'stage': 'prepare_after_review', 'readiness': ready,
        'automatic_retries': False, 'new_games': 0}, exclusive=True)
    evidence_dir = OUT/archive_name; evidence_dir.mkdir(); manifest = {}
    copies = {'selection-review.json': ROOT/ready['review_path'],
        'confirmation-comparison.json': ROOT/selection.COMPARISON, 'confirmation-source.json': ROOT/selection.SOURCE,
        'target-proof.json': ROOT/selection.TECHNICAL, 'target-native-binding.json': ROOT/selection.BINDING,
        'native-export-proof.json': ROOT/selection.EXPORT, 'native-export-audit.json': ROOT/selection.EXPORT_AUDIT,
        'target-recovery.json': ROOT/'ai/strong/current-full-serving-results-evidence-v1.json',
        'export-recovery.json': ROOT/'ai/strong/current-engine-export-evidence-v1.json'}
    for name, path in copies.items():
        with path.open('rb') as src, (evidence_dir/name).open('xb') as dst: shutil.copyfileobj(src, dst)
        require(digest(evidence_dir/name) == digest(path), 'Selection evidence changed during copy')
        manifest[name] = digest(path)
    durable_write(evidence_dir/'readiness.json', ready, exclusive=True)
    manifest['readiness.json'] = digest(evidence_dir/'readiness.json')
    durable_write(evidence_dir/'manifest.json', manifest, exclusive=True)
    durable_write(OUT/'selection-upload-intent.json', {'stage': 'upload_intent', 'manifest_sha256': digest(evidence_dir/'manifest.json')}, exclusive=True)
    archive = upload_evidence(evidence_dir)
    durable_write(OUT/'selection-archive.json', archive, exclusive=True)
    selection.pinned_files(ROOT, ready['input_hashes'])
    candidate = {'status': 'selected', 'frozen_at': now(), 'identity': ready['selection']['selected_identity'],
        'protocol_sha256': PROTOCOL_SHA,
        'selection_evidence': {k: archive[k] for k in ('repo', 'revision', 'archive_path', 'archive_sha256')}}
    durable_write(OUT/'candidate.json', candidate, exclusive=True)
    artifact = ROOT/'ai/runs/current-auction-grid-prepared-v1/source/artifact'
    built = source_builder.build(artifact, 'policies/conservative_population.json', OUT/'candidate.json',
                                 ready['resources']['workers'], OUT/'bundle')
    require(built['identity'] == candidate['identity'] and built['jobs'] == 320 and built['games'] == 20160,
            'Prepared source differs from admitted policy/coverage')
    selection.pinned_files(ROOT, ready['input_hashes'])
    result = {'prepared': True, 'readiness': ready, 'selection_archive': archive,
        'candidate_sha256': digest(OUT/'candidate.json'), 'bundle_prepared_sha256': digest(OUT/'bundle/prepared.json'),
        'source_manifest_sha256': built['source_manifest_sha256'], 'qualified': False,
        'reserved_final_seeds_used': False, 'jobs_submitted': 0}
    durable_write(OUT/'prepared.json', result, exclusive=True)
    return {'prepared': True, 'source_published': False, 'jobs_submitted': 0, 'qualified': False}


def checked_preparation(prepared, ready):
    """Recheck actual candidate, artifact and every control before publication."""
    require(same(ready['selection'], prepared['readiness']['selection'])
            and same(ready['resources'], prepared['readiness']['resources'])
            and same(ready['input_hashes'], prepared['readiness']['input_hashes']), 'Selection or allocation changed')
    require(digest(OUT/'candidate.json') == prepared['candidate_sha256']
            and digest(OUT/'bundle/prepared.json') == prepared['bundle_prepared_sha256'], 'Candidate/source preparation changed')
    built = read(OUT/'bundle/prepared.json')
    require(built['source_manifest_sha256'] == prepared['source_manifest_sha256'], 'Builder manifest differs')
    source, pins = checked_tree(OUT/'bundle/source', 'source-manifest.json', prepared['source_manifest_sha256'])
    require(digest(source/'candidate.json') == prepared['candidate_sha256'], 'Bundled candidate changed')
    candidate = read(source/'candidate.json'); identity = ready['selection']['selected_identity']
    expected_archive = {k: prepared['selection_archive'][k]
                        for k in ('repo', 'revision', 'archive_path', 'archive_sha256')}
    require(same(candidate['selection_evidence'], expected_archive), 'Candidate selection archive differs')
    require(selection.artifact_identity(source/'artifact', 'policies/conservative_population.json') == identity,
            'Bundled complete policy differs from reviewed identity')
    require(source_builder.source_files(source/'artifact') == built['inputs']['artifact_files'], 'Builder artifact differs')
    require(digest(source/source_builder.ENTRY) == built['inputs']['entry_sha256']
            == digest(ROOT/'ai/strong'/source_builder.ENTRY), 'Bundled job entry differs')
    plan = read(source/'final-plan.json')
    require(digest(source/'final-plan.json') == built['plan_sha256']
            and same(plan['identity'], identity) and plan['candidate_sha256'] == prepared['candidate_sha256'],
            'Published plan differs from selection')
    created_at = read(source/plan['rows'][0]['contract'])['created_at']
    expected, rows = source_builder.controls((source/'candidate.json').read_bytes(), identity,
        'policies/conservative_population.json', ready['resources']['workers'], created_at)
    require(same(plan['rows'], rows) and same(built['rows'], rows), 'Final worker allocation/controls changed')
    for name, value in expected.items():
        require(same(read(source/name), value), 'Final control differs: ' + name)
    return source, pins, plan


def bootstrap_text():
    reference_script = ROOT/'ai/strong/manage-current-auction-runtime-v1.py'
    spec = importlib.util.spec_from_file_location('unchanged_final_bootstrap_setup', reference_script)
    original = importlib.util.module_from_spec(spec); spec.loader.exec_module(original)
    return final_bootstrap(original.BOOTSTRAP)


def publish():
    require((OUT/'prepared.json').exists(), 'Complete reviewed preparation is required')
    require(not any((OUT/n).exists() for n in ('source-upload-intent.json', 'source-upload-receipt.json', 'release.json')),
            'Inspect existing source publication outcome; never upload blindly again')
    prepared = read(OUT/'prepared.json'); ready = readiness(ROOT/prepared['readiness']['review_path'])
    source, pins, plan = checked_preparation(prepared, ready)
    bootstrap = bootstrap_text()
    # Structural check before upload; the actual immutable revision and
    # admission digest replace these placeholders only after verified upload.
    validate_release({'version': 1, 'admission_sha256': '0'*64,
        'source': {'repo': REPO, 'revision': '0'*40, 'archive': SOURCE_NAME,
                   'sha256': '0'*64, 'source_manifest_sha256': prepared['source_manifest_sha256']},
        'plan': plan, 'allocation': ready['resources']['allocation'],
        'bootstrap_sha256': hashlib.sha256(bootstrap.encode()).hexdigest()}, bootstrap)
    selection_archive = prepared['selection_archive']
    local = hf_hub_download(selection_archive['repo'], selection_archive['archive_path'], revision=selection_archive['revision'])
    require(digest(local) == selection_archive['archive_sha256'], 'Immutable selection archive mismatch')
    archive = OUT/SOURCE_NAME; require(not archive.exists(), 'Inspect existing source tarball')
    selection.pinned_files(ROOT, ready['input_hashes'])
    with archive.open('xb') as archive_stream, tarfile.open(fileobj=archive_stream, mode='w:gz') as bundle:
        for name in sorted(set(pins)|{'source-manifest.json'}):
            path = source/name; info = bundle.gettarinfo(path, arcname=name)
            info.uid = info.gid = info.mtime = 0; info.uname = info.gname = ''
            with path.open('rb') as stream: bundle.addfile(info, stream)
    expected = {**pins, 'source-manifest.json': prepared['source_manifest_sha256']}
    with tarfile.open(archive, 'r:gz') as bundle:
        members = bundle.getmembers()
        require(len(members) == len(expected) and {m.name for m in members} == set(expected), 'Source archive file set differs')
        for member in members:
            require(member.isfile(), 'Source archive member is not a regular file')
            with bundle.extractfile(member) as stream:
                require(hashlib.file_digest(stream, 'sha256').hexdigest() == expected[member.name],
                        'Source archive member differs')
    api = HfApi()
    require(api.dataset_info(REPO).private and not api.file_exists(REPO, SOURCE_NAME, repo_type='dataset'),
            'Inspect existing remote source or nonprivate repository')
    durable_write(OUT/'source-upload-intent.json', {'created_at': now(), 'archive': SOURCE_NAME, 'sha256': digest(archive)}, exclusive=True)
    commit = api.upload_file(repo_id=REPO, repo_type='dataset', path_or_fileobj=archive, path_in_repo=SOURCE_NAME)
    reference = {'repo': REPO, 'revision': commit.oid, 'archive': SOURCE_NAME,
                 'sha256': digest(archive), 'source_manifest_sha256': prepared['source_manifest_sha256']}
    durable_write(OUT/'source-upload-receipt.json', reference, exclusive=True)
    require(digest(hf_hub_download(REPO, SOURCE_NAME, repo_type='dataset', revision=commit.oid)) == reference['sha256'],
            'Published source hash differs')
    selection.pinned_files(ROOT, ready['input_hashes'])
    with (OUT/'bootstrap.sh').open('x') as stream: stream.write(bootstrap)
    admission = {'version': 1, 'created_at': now(), 'readiness': ready,
        'candidate_sha256': prepared['candidate_sha256'], 'selection_archive': selection_archive,
        'source': reference, 'resources': ready['resources'], 'prepared_sha256': digest(OUT/'prepared.json'),
        'original_only': True, 'automatic_retries': False, 'max_active_jobs': 64,
        'jobs_submitted': 0, 'qualified': False, 'reserved_final_seeds_used': False}
    durable_write(OUT/'admission.json', admission, exclusive=True)
    release = {'version': 1, 'admission_sha256': digest(OUT/'admission.json'), 'source': reference,
        'plan': plan, 'allocation': ready['resources']['allocation'],
        'bootstrap_sha256': hashlib.sha256(bootstrap.encode()).hexdigest()}
    validate_release(release, bootstrap)
    durable_write(OUT/'release.json', release, exclusive=True)
    return {'source_published': True, 'revision': commit.oid, 'jobs_submitted': 0, 'qualified': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('operation', choices=('check', 'prepare', 'publish'))
    parser.add_argument('--review', type=Path)
    args = parser.parse_args()
    if args.operation != 'publish': require(args.review is not None, 'Supply the explicit completed-results review')
    if args.operation == 'check':
        ready = readiness(args.review)
        result = {'ready_for_candidate_freeze': True, 'review_path': ready['review_path'],
                  'comparison_sha256': ready['selection']['comparison_sha256'],
                  'jobs_submitted': 0, 'candidate_created': False, 'qualified': False}
    else:
        result = prepare(args.review) if args.operation == 'prepare' else publish()
    print(json.dumps(result))
