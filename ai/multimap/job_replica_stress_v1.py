"""Bounded, evaluation-only replica stress worker and immutable snapshot verifier.

No generic worker/serving guards are rebound. Cached HF snapshot -> blob links
are accepted inside the dedicated download cache; output/ledger links are not.
Only complete three-arm/all-seat batches can become remote resume authority.
"""
import copy
import json
import os
from pathlib import Path
import re
import shutil
import stat
import sys
import tempfile

# Must precede ALL transitive Hub imports, without changing caches on import.
if __name__ == '__main__':
    os.environ['HF_HUB_CACHE'] = os.environ.get('REPLICA_STRESS_MODEL_CACHE', '/tmp/replica-stress-v1-models')

from huggingface_hub import hf_hub_download
from data import ROOT, atomic_json, digest
from replica_stress_study_v1 import (PROTOCOL, artifact_budget, identity, plan, batches,
                                     verify_batch, analyze, run as evaluate)
from job_gap import recover_reference
import job_neural as shared

LIMIT = 64 * 1024**2
MANIFEST_LIMIT = 64 * 1024
GROUP = 'multimap-replica-stress-20261109-v1'
PANELS = ('strong', 'mixed')
STUDY_NAMES = {'study/plan.json', 'study/summary.json'} | {f'study/batch-{i:03}.json' for i in range(640)}
METADATA_NAMES = {'status.json', 'protocol.json', 'environment.json', 'recovery.json'}
NAMES = STUDY_NAMES | METADATA_NAMES
FORBIDDEN = {'observation', 'observations', 'request', 'requests', 'response', 'responses',
             'state', 'move', 'moves', 'rows', 'actions', 'state_dict', 'trajectory',
             'trajectories', 'trace', 'optimizer', 'gradients'}
remote_size = shared.remote_size


def require(condition, message):
    if not condition:
        raise ValueError(message)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def no_links(path):
    path = Path(path).absolute()
    require(all(not p.is_symlink() for p in (path, *path.parents)), 'Output/ledger symlink forbidden')
    return path


def read(path, maximum=LIMIT):
    path = no_links(path)
    require(path.is_file() and 0 < path.stat().st_size <= maximum, 'Unsafe/oversize JSON file')
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'Duplicate JSON key')
            result[key] = value
        return result
    def invalid(_):
        raise ValueError('Nonfinite JSON')
    return json.loads(path.read_text(), object_pairs_hook=pairs, parse_constant=invalid)


def downloaded_file(path, cache, size):
    # HF normally returns models--OWNER--REPO/snapshots/COMMIT/PATH, a symlink
    # into models--OWNER--REPO/blobs/HASH, NOT a standalone regular snapshot.
    cache = Path(cache).resolve(strict=True)
    path = Path(path).resolve(strict=True)
    require(path.is_relative_to(cache) and path.is_file(), 'Downloaded file escapes cache or is not a regular file')
    require(type(size) is int and size > 0 and path.stat().st_size == size, 'Downloaded file metadata size mismatch')
    return path


def compact_json(value):
    if isinstance(value, dict):
        require(not FORBIDDEN.intersection(value), 'Raw decision/optimization payload forbidden')
        for child in value.values():
            compact_json(child)
    elif isinstance(value, list):
        for child in value:
            compact_json(child)


def validate_manifest(manifest):
    require(isinstance(manifest, dict) and 'study/plan.json' in manifest, 'Resume lacks frozen study identity')
    require(METADATA_NAMES <= set(manifest), 'Resume missing source/runtime metadata')
    require(all(name in NAMES and isinstance(sha, str) and re.fullmatch('[0-9a-f]{64}', sha)
                for name, sha in manifest.items()), 'Unsafe/unexpected resume file/hash')
    return {name: sha for name, sha in manifest.items() if name in STUDY_NAMES}


def compact_files(base):
    base = no_links(base)
    artifact_budget(base)
    result = {}
    for path in base.rglob('*'):
        require(not path.is_symlink(), 'Artifact symlink forbidden')
        if path.is_dir():
            require(path == base / 'study', 'Unexpected artifact directory')
            continue
        require(stat.S_ISREG(path.stat().st_mode), 'Nonregular artifact forbidden')
        name = path.relative_to(base).as_posix()
        if name in ('artifacts.json', 'artifacts.json.tmp') or (name.endswith('.tmp') and name[:-4] in NAMES):
            continue
        require(name in NAMES, 'Unexpected artifact filename')
        compact_json(read(path))
        result[name] = digest(path)
    require(len((canonical(result) + '\n').encode()) <= MANIFEST_LIMIT, 'Manifest exceeds 64 KiB')
    return result


def write_manifest(base, manifest):
    payload = canonical(manifest) + '\n'
    require(len(payload.encode()) <= MANIFEST_LIMIT, 'Manifest exceeds 64 KiB')
    temporary = no_links(Path(base) / 'artifacts.json.tmp')
    temporary.write_text(payload)
    temporary.replace(no_links(Path(base) / 'artifacts.json'))
    artifact_budget(base)


def fetch_snapshot(repo, previous, revision, base, cache):
    """Metadata for EVERY member and aggregate before the first payload download."""
    shared.safe_run(previous)
    shared.immutable_revision(revision)
    base, cache = no_links(base), no_links(cache)
    shared.separate_paths(base, cache)
    prefix = 'runs/' + previous + '/'
    size = remote_size(repo, prefix + 'artifacts.json', revision, maximum=MANIFEST_LIMIT)
    manifest_file = downloaded_file(hf_hub_download(repo, prefix + 'artifacts.json', revision=revision,
                                                    cache_dir=cache), cache, size)
    manifest = read(manifest_file, MANIFEST_LIMIT)
    wanted = validate_manifest(manifest)
    sizes = {name: remote_size(repo, prefix + name, revision, maximum=LIMIT) for name in manifest}
    require(all(type(n) is int and n > 0 for n in sizes.values()) and size + sum(sizes.values()) <= LIMIT,
            'Aggregate resume metadata/artifact budget exceeded')
    artifact_budget(base, size + sum(sizes.values()))
    for name, sha in manifest.items():
        path = downloaded_file(hf_hub_download(repo, prefix + name, revision=revision, cache_dir=cache),
                               cache, sizes[name])
        require(digest(path) == sha, 'Resume artifact hash/size mismatch')
        compact_json(read(path))
        destination = no_links(base / name)
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            require(destination.is_file() and digest(destination) == sha, 'Conflicting local resume file')
        else:
            shutil.copyfile(path, destination)
    return dict(run=previous, revision=revision, manifestSha256=digest(manifest_file),
                files=wanted, allFileHashes=manifest, totalBytes=size + sum(sizes.values()))


def production_identity(preflight, panel):
    """Smoke uses the same frozen runtime; only tasks and smoke flag differ."""
    value = copy.deepcopy(preflight['smokeIdentities'][panel])
    value.update(smoke=False, tasks=plan(panel, False))
    return value


def validate_snapshot(base, source, panel, original_run, expected_identity, *, require_incomplete=True):
    """No loading models, playing games, optimizer construction, or RNG changes."""
    base = no_links(base)
    manifest = compact_files(base)
    validate_manifest(manifest)
    require(canonical(read(base / 'study/plan.json')) == canonical(expected_identity),
            'Resume full task/model/source/runtime identity mismatch')
    status = read(base / 'status.json')
    expected = dict(run=original_run, workflow='replica-stress-v1', group=source['group'], panel=panel,
                    segment=1, slot=panel, workers=6, smoke=False, protocol=PROTOCOL,
                    sourceRepo=source['sourceRepo'], sourcePath=source['sourcePath'],
                    sourceRevision=source['sourceRevision'], sourceSha256=source['sourceSha256'],
                    sourceCommit=source['sourceCommit'])
    require(canonical({k: status.get(k) for k in expected}) == canonical(expected),
            'Resume snapshot source/panel/worker identity mismatch')
    require(canonical(read(base / 'protocol.json')) == canonical(PROTOCOL), 'Resume protocol mismatch')
    frozen = expected_identity['modelProvenance']['expert24']['config']
    environment = read(base / 'environment.json')
    require(environment.get('requirementsSha256') == frozen['protocol']['referenceRequirementsSha256'] and
            canonical(environment.get('versions')) == canonical(frozen['runtimeVersions']),
            'Resume reference requirements/runtime mismatch')
    reference = frozen['protocol']['reference']
    recovery = read(base / 'recovery.json')
    expected_recovery = dict(exactServiceReady=True, runtimeManifestSha256=frozen['referenceManifestSha256'],
                            policySha256=reference['policySha256'],
                            pins=dict(source=reference['sourcePin'], model=reference['modelPin']), omitted=[])
    require(canonical({k: recovery.get(k) for k in expected_recovery}) == canonical(expected_recovery),
            'Resume reference recovery mismatch')
    groups = batches(expected_identity['tasks'])
    require(len(groups) == 640, 'Frozen production batch coverage changed')
    present = sorted(n for n in manifest if n.startswith('study/batch-'))
    require(present == [f'study/batch-{i:03}.json' for i in range(len(present))],
            'Noncontiguous committed batches')
    games = []
    for index, name in enumerate(present):
        games.extend(verify_batch(read(base / name), index, groups[index]))
    complete = len(present) == len(groups)
    if not complete:
        require(status.get('error') is None and status.get('stage') != 'failed',
                'Explicit worker/game failure requires audit, not recovery')
    if 'study/summary.json' in manifest:
        require(complete, 'Summary exists for incomplete study')
        require(canonical(read(base / 'study/summary.json')) == canonical(analyze(games, panel, False)),
                'Committed summary mismatch')
    require(status.get('stage') != 'complete' or complete, 'Status claims incomplete study complete')
    if require_incomplete:
        require(not complete, 'Complete output after job termination requires audit, not recovery')
    return dict(committedBatches=len(present), committedGames=len(games), complete=complete,
                planSha256=digest(base / 'study/plan.json'))


def restore_resume(repo, previous, revision, base, cache, *, source, panel, expected_identity):
    # Validate in a separate directory BEFORE replacing any current-job metadata.
    base, cache = no_links(base), no_links(cache)
    cache.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='verified-', dir=cache) as directory:
        checked = fetch_snapshot(repo, previous, revision, Path(directory) / 'output', cache / 'downloads')
        checked['transaction'] = validate_snapshot(Path(directory) / 'output', source, panel,
                                                  previous, expected_identity)
        for name in checked['files']:
            origin = Path(directory) / 'output' / name
            destination = no_links(base / name)
            destination.parent.mkdir(parents=True, exist_ok=True)
            if destination.exists():
                require(digest(destination) == checked['files'][name], 'Conflicting local committed batch')
            else:
                shutil.copyfile(origin, destination)
        return checked


def run():
    from huggingface_hub import HfApi
    from expert_policy import PROTOCOL as expert_protocol
    run_id = shared.safe_run(os.environ['RUN_ID'])
    panel = os.environ['REPLICA_STRESS_PANEL']
    segment = os.environ['REPLICA_STRESS_SEGMENT']
    slot = os.environ['REPLICA_STRESS_SLOT']
    require(panel in PANELS and segment in ('1', '2') and
            slot == (panel if segment == '1' else 'recovery') and
            os.environ['REPLICA_STRESS_GROUP'] == GROUP and
            run_id == GROUP + ('-' + panel if segment == '1' else '-recovery-' + panel) and
            os.environ['REPLICA_STRESS_WORKERS'] == '6' and os.environ['REPLICA_STRESS_SMOKE'] == '0' and
            os.environ['MODEL_REPO'] == PROTOCOL['modelRepo'], 'Frozen production worker scope rejected')
    previous, revision = os.environ.get('RESUME_RUN'), os.environ.get('RESUME_REVISION')
    require((segment == '2') == bool(previous) == bool(revision), 'Incomplete/unauthorized resume pin')
    require(previous is None or previous == GROUP + '-' + panel, 'Recovery must use original panel snapshot')
    base = no_links(os.environ.get('RUN_DIR', '/tmp/replica-stress-v1-run'))
    cache = no_links(os.environ.get('REFERENCE_CACHE', '/tmp/replica-stress-v1-reference'))
    venv = no_links(os.environ.get('REFERENCE_VENV', '/tmp/replica-stress-v1-reference-venv'))
    resume = no_links(os.environ.get('RESUME_CACHE', '/tmp/replica-stress-v1-resume'))
    models = no_links(os.environ.get('REPLICA_STRESS_MODEL_CACHE', '/tmp/replica-stress-v1-models'))
    shared.separate_paths(base, cache, venv, resume, models)
    base.mkdir(parents=True, exist_ok=True)
    for name in ('OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'NUMEXPR_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS'):
        os.environ[name] = '1'
    os.environ.update(HF_HUB_DISABLE_PROGRESS_BARS='1', HF_HUB_DISABLE_XET='1')
    source = dict(group=GROUP, sourceRevision=shared.immutable_revision(os.environ['SOURCE_REVISION']),
                  sourceCommit=shared.immutable_revision(os.environ['SOURCE_COMMIT']),
                  sourceSha256=os.environ['SOURCE_SHA256'], sourceRepo=os.environ['DATASET_REPO'],
                  sourcePath=os.environ['SOURCE_PATH'])
    require(re.fullmatch('[0-9a-f]{64}', source['sourceSha256']) and
            source['sourceRepo'] == 'coyotte508/powergrid-ai-training-v1' and
            source['sourcePath'] == f'multimap/{GROUP}/source.tgz', 'Invalid pinned source')
    status = dict(run=run_id, workflow='replica-stress-v1', panel=panel, smoke=False,
                  workers=6, segment=int(segment), slot=slot, protocol=PROTOCOL, **source,
                  qualified=False, qualificationEligible=False, reservedFinalSeedsUsed=False)
    api, receipts = HfApi(), []
    repo = os.environ['MODEL_REPO']
    def upload(stage):
        require(stage in ('runtime-ready', 'complete', 'failed') or
                re.fullmatch(r'batches-(?:[1-9][0-9]{0,2})', stage), 'Unexpected upload stage')
        status.update(stage=stage, receipts=list(receipts))
        atomic_json(base / 'status.json', status)
        manifest = compact_files(base)
        write_manifest(base, manifest)
        require(api.model_info(repo).private is True, 'Private artifacts required')
        result = api.upload_folder(repo_id=repo, folder_path=base, path_in_repo=f'runs/{run_id}',
                                   allow_patterns=[*manifest, 'artifacts.json'], commit_message=f'{run_id}: {stage}')
        receipts.append(dict(stage=stage, revision=shared.immutable_revision(result.oid)))
        print(json.dumps(dict(stage='uploaded', label=stage, revision=result.oid)), flush=True)
    try:
        require(api.model_info(repo).private is True and
                api.model_info(expert_protocol['reference']['modelPin']['repo']).private is True and
                api.dataset_info(source['sourceRepo']).private is True and
                api.dataset_info(expert_protocol['reference']['sourcePin']['repo']).private is True,
                'Existing private model/source repositories required')
        manifest = read(ROOT / 'source-manifest.json', 4 * 1024**2)
        require(manifest['gitCommit'] == source['sourceCommit'], 'Packaged source commit mismatch')
        python, environment = shared.ensure_reference_environment(venv)
        recovery = recover_reference(cache)
        config = identity(panel, False, 6, cache / 'artifact', python)
        preflight = read(ROOT / 'ai/multimap/replica-stress-preflight-v1.json', 4 * 1024**2)
        require(canonical(config) == canonical(production_identity(preflight, panel)),
                'Worker source/runtime/model identity differs from preflight')
        if previous:
            status['resume'] = restore_resume(repo, previous, revision, base, resume,
                                              source=source, panel=panel, expected_identity=config)
        else:
            require(not any(base.iterdir()), 'New job requires empty compact output')
        atomic_json(base / 'protocol.json', PROTOCOL)
        atomic_json(base / 'environment.json', environment)
        atomic_json(base / 'recovery.json', recovery)
        atomic_json(base / 'study/plan.json', config)
        upload('runtime-ready')
        status['result'] = evaluate(base / 'study', panel, artifact=cache / 'artifact',
                                    reference_python=python, workers=6, smoke=False, callback=upload)
        upload('complete')
        print(json.dumps(dict(stage='complete', run=run_id, panel=panel,
                              games=status['result']['games'], qualified=False)), flush=True)
    except BaseException:
        status['error'] = dict(code='replica-stress-job-stopped')
        try:
            upload('failed')
        except BaseException:
            print('Failure snapshot unavailable; local compact evidence retained', file=sys.stderr)
        raise RuntimeError('Replica stress stopped; inspect fixed-code status and committed batches') from None


if __name__ == '__main__':
    try:
        run()
    except BaseException:
        # Do not print exception types, messages, payloads, tokens, or tracebacks.
        print('Replica stress worker stopped; inspect private compact status', file=sys.stderr)
        sys.exit(1)
