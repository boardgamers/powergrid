"""Private-HF frozen neural screen worker. No fitting or bulky artifact uploads.

Launcher integration: WORKFLOW=neural -> this file; package
ai/requirements-serve.txt as well as ai/multimap. The Torch environment keeps
NumPy 2.2.6. A separate ephemeral venv installs the unchanged serve requirements.
REFERENCE_CACHE, REFERENCE_VENV, CANDIDATE_CACHE must be outside RUN_DIR.
Immutable resumes use RESUME_RUN + RESUME_REVISION; all identity guards still run.
"""
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import time
import traceback

from data import ROOT, atomic_json, digest
from neural_study import PROTOCOL, THREAD_ENV, artifact_budget, runtime_versions, validate_protocol, run as evaluate
from reference_recover import recover, budget

ARTIFACT_NAMES = frozenset({'status.json', 'recovery.json', 'environment.json',
                           'study/plan.json', 'study/games.jsonl', 'study/summary.json'})
STUDY_NAMES = frozenset(n for n in ARTIFACT_NAMES if n.startswith('study/'))


def retry(function):
    for attempt in range(4):
        try:
            return function()
        except Exception:
            if attempt == 3:
                raise
            time.sleep((5, 15, 45)[attempt])


def immutable_revision(value):
    if not isinstance(value, str) or not re.fullmatch('[0-9a-f]{40}', value):
        raise ValueError('Resume/download requires an immutable commit revision')
    return value


def safe_run(value):
    if not isinstance(value, str) or not re.fullmatch('[A-Za-z0-9_-]+', value):
        raise ValueError('Unsafe run ID')
    return value


def validate_manifest(manifest):
    if not isinstance(manifest, dict) or 'study/plan.json' not in manifest:
        raise ValueError('Resume lacks immutable study plan')
    for name, sha in manifest.items():
        if name not in ARTIFACT_NAMES or not isinstance(sha, str) or not re.fullmatch('[0-9a-f]{64}', sha):
            raise ValueError('Unsafe/noncompact resume artifact or hash')
    return {name: sha for name, sha in manifest.items() if name in STUDY_NAMES}


def compact_files(base):
    """Whitelist, not just ignore patterns: never upload caches/models/fixtures."""
    base = Path(base)
    artifact_budget(base)
    files = {}
    for path in base.rglob('*'):
        if path.is_symlink():
            raise ValueError('No artifact symlinks')
        if not path.is_file():
            continue
        name = path.relative_to(base).as_posix()
        if name == 'artifacts.json' or (name.endswith('.tmp') and name[:-4] in ARTIFACT_NAMES):
            continue
        if name not in ARTIFACT_NAMES:
            raise ValueError('Refusing unexpected/bulky study artifact: ' + name)
        files[name] = digest(path)
    return files


def remote_size(repo, name, revision, *, repo_type='model', maximum=128 * 1024**2):
    from huggingface_hub import get_hf_file_metadata, hf_hub_url, get_token
    immutable_revision(revision)
    meta = get_hf_file_metadata(hf_hub_url(repo, name, repo_type=repo_type, revision=revision), token=get_token())
    if meta.commit_hash != revision or type(meta.size) is not int or not 0 <= meta.size <= maximum:
        raise ValueError('Immutable remote artifact size/revision rejected')
    return meta.size


def restore_resume(repo, previous, revision, base, download_cache):
    """Check immutable hashes and total advertised bytes before restoring files."""
    from huggingface_hub import hf_hub_download
    safe_run(previous)
    immutable_revision(revision)
    prefix = f'runs/{previous}/'
    remote_size(repo, prefix + 'artifacts.json', revision, maximum=64 * 1024)
    manifest_path = hf_hub_download(repo, prefix + 'artifacts.json', revision=revision, cache_dir=download_cache)
    wanted = validate_manifest(json.loads(Path(manifest_path).read_text()))
    sizes = {name: remote_size(repo, prefix + name, revision) for name in wanted}
    artifact_budget(base, sum(sizes.values()))
    for name, sha in wanted.items():
        source = Path(hf_hub_download(repo, prefix + name, revision=revision, cache_dir=download_cache))
        if source.stat().st_size != sizes[name] or digest(source) != sha:
            raise ValueError('Study resume hash/size mismatch')
        destination = Path(base).joinpath(*PurePosixPath(name).parts)
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            if digest(destination) != sha:
                raise ValueError('Conflicting local resume file; refuse overwrite')
        else:
            shutil.copyfile(source, destination)
    return dict(run=previous, revision=revision, files=wanted)


def ensure_reference_environment(directory):
    """Isolated requirements, no pip cache, bounded dedicated venv, no Torch edits."""
    directory = Path(directory)
    if directory.is_symlink():
        raise ValueError('Reference venv must not be a symlink')
    python = directory / 'bin/python'
    if not python.exists():
        if directory.exists() and any(directory.iterdir()):
            raise ValueError('Partial reference venv; inspect it rather than silently replacing')
        subprocess.run([sys.executable, '-m', 'venv', str(directory)], check=True)
        subprocess.run([str(python), '-m', 'pip', 'install', '--no-cache-dir', '--disable-pip-version-check',
                        '-r', str(ROOT / 'ai/requirements-serve.txt')], check=True)
    used = sum(p.stat().st_size for p in directory.rglob('*') if p.is_file() and not p.is_symlink())
    if used > PROTOCOL['referenceVenvMaxBytes']:
        raise ValueError('Reference venv exceeds its separate 256 MiB budget')
    versions = runtime_versions(python)
    return python, dict(versions=versions, referenceVenvBytes=used,
                        requirementsSha256=digest(ROOT / 'ai/requirements-serve.txt'))


def separate_paths(base, *caches):
    paths = [Path(base).resolve(), *(Path(p).resolve() for p in caches)]
    for i, first in enumerate(paths):
        for second in paths[i + 1:]:
            if first.is_relative_to(second) or second.is_relative_to(first):
                raise ValueError('Compact output and ephemeral caches/venv must be separate, nonnested paths')


def run():
    run_id = safe_run(os.environ['RUN_ID'])
    repo = os.environ['MODEL_REPO']
    workers = int(os.environ.get('NEURAL_WORKERS', PROTOCOL['workers']))
    if workers not in PROTOCOL['allowedWorkers']:
        raise ValueError('NEURAL_WORKERS must be 1..6')
    if os.environ.get('NEURAL_SMOKE', '0') not in ('0', '1'):
        raise ValueError('NEURAL_SMOKE must be 0 or 1')
    smoke = os.environ.get('NEURAL_SMOKE', '0') == '1'
    base = Path(os.environ.get('RUN_DIR', '/tmp/multimap-neural-run'))
    cache = Path(os.environ.get('REFERENCE_CACHE', '/tmp/multimap-neural-reference'))
    venv = Path(os.environ.get('REFERENCE_VENV', '/tmp/multimap-neural-reference-venv'))
    candidates_cache = Path(os.environ.get('CANDIDATE_CACHE', '/tmp/multimap-neural-candidates'))
    resume_cache = Path(os.environ.get('RESUME_CACHE', '/tmp/multimap-neural-resume'))
    separate_paths(base, cache, venv, candidates_cache, resume_cache)
    base.mkdir(parents=True, exist_ok=True)
    for name in THREAD_ENV:
        os.environ[name] = '1'
    os.environ['HF_HUB_DISABLE_XET'] = '1'
    os.environ['HF_HUB_CACHE'] = str(candidates_cache)
    os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
    from huggingface_hub import HfApi, hf_hub_download
    api = HfApi()
    receipts = []
    status = dict(run=run_id, sourceRevision=immutable_revision(os.environ['SOURCE_REVISION']),
                  sourceSha256=os.environ['SOURCE_SHA256'], sourcePath=os.environ['SOURCE_PATH'],
                  sourceRepo=os.environ['DATASET_REPO'], protocol=PROTOCOL,
                  smoke=smoke, workers=workers, qualified=False, qualification_eligible=False, reserved_final_seeds_used=False)
    if not re.fullmatch('[0-9a-f]{64}', status['sourceSha256']):
        raise ValueError('Invalid pinned source SHA256')
    if not api.model_info(repo).private:
        raise RuntimeError('Study artifacts must remain private')

    def upload(stage):
        if not api.model_info(repo).private:
            raise RuntimeError('Study repository is no longer private')
        status.update(stage=stage, receipts=list(receipts))
        atomic_json(base / 'status.json', status)
        manifest = compact_files(base)
        atomic_json(base / 'artifacts.json', manifest)
        artifact_budget(base)
        result = retry(lambda: api.upload_folder(repo_id=repo, folder_path=base,
            path_in_repo=f'runs/{run_id}', allow_patterns=[*manifest, 'artifacts.json'],
            ignore_patterns=['*.tmp'], commit_message=f'{run_id}: {stage}'))
        receipts.append(dict(stage=stage, revision=result.oid))
        print(json.dumps(dict(stage='uploaded', label=stage, revision=result.oid)), flush=True)

    try:
        pool = validate_protocol()
        for model_repo in {m['repo'] for m in pool['members']} | {PROTOCOL['reference']['modelPin']['repo']}:
            if not api.model_info(model_repo).private:
                raise RuntimeError('Frozen model artifacts must remain private')
        if not api.dataset_info(PROTOCOL['reference']['sourcePin']['repo']).private:
            raise RuntimeError('Frozen source artifacts must remain private')
        # All of these tests are offline. No actual old-neural screen runs in tests.
        subprocess.run(['node', '--test', 'ai/multimap/test.cjs', 'ai/multimap/test_rl.cjs',
                        'ai/multimap/test_reference.cjs'], cwd=ROOT, check=True)
        subprocess.run([sys.executable, '-B', '-m', 'unittest', 'discover', '-s', 'ai/multimap',
                        '-p', 'test_neural_study.py'], cwd=ROOT, check=True)
        if bool(os.environ.get('RESUME_RUN')) != bool(os.environ.get('RESUME_REVISION')):
            raise ValueError('Resume needs both run ID and immutable revision')
        if os.environ.get('RESUME_RUN'):
            status['resume'] = restore_resume(repo, os.environ['RESUME_RUN'], os.environ['RESUME_REVISION'], base, resume_cache)
            shutil.rmtree(resume_cache)  # dedicated download cache only, never shared HF cache
        python, environment = ensure_reference_environment(venv)
        atomic_json(base / 'environment.json', environment)
        # Full original artifact: fixtures are loader/hash-only, never new data.
        receipt = recover(cache)
        if not receipt.get('exactServiceReady') or receipt.get('runtimeManifestSha256') != PROTOCOL['reference']['runtimeManifestSha256']:
            raise RuntimeError('Exact unchanged reference loader is not ready')
        budget(cache)
        atomic_json(base / 'recovery.json', receipt)
        for pin in pool['members']:
            size = remote_size(pin['repo'], pin['path'], pin['revision'], maximum=16 * 1024**2)
            checkpoint = hf_hub_download(pin['repo'], pin['path'], revision=pin['revision'], cache_dir=candidates_cache)
            if Path(checkpoint).stat().st_size != size or digest(checkpoint) != pin['sha256']:
                raise ValueError('Wrong immutable candidate checkpoint')
        upload('runtime-ready')
        status['result'] = evaluate(base / 'study', artifact=cache / 'artifact', reference_python=python,
                                    workers=workers, smoke=smoke, callback=upload)
        upload('complete')
        print(json.dumps(dict(stage='complete', run=run_id, games=status['result']['games'],
                              failures=status['result']['failures'], qualified=False)), flush=True)
    except BaseException:
        status['error'] = traceback.format_exc()[-12000:]
        status['qualificationStopped'] = True
        try:
            upload('failed')
        except Exception:
            traceback.print_exc()
        raise


if __name__ == '__main__':
    run()
