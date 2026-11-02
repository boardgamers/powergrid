"""Private-HF phase diagnostic entry point; launcher wiring is intentionally external.

WORKFLOW=gap should invoke this file. Package the same compiled engine 2.0.22,
ai/multimap, ai/core.cjs, ai/strong/economics.cjs and ai/requirements-serve.txt.
Env: RUN_ID, MODEL_REPO (existing private multimap model repo), RUN_DIR,
SOURCE_REVISION/SOURCE_SHA256/SOURCE_PATH/DATASET_REPO, GAP_WORKERS=6 (1..6),
GAP_SMOKE=0|1, REFERENCE_CACHE, REFERENCE_VENV, RESUME_CACHE; optional paired
RESUME_RUN + immutable RESUME_REVISION. No candidate cache/download or training.
"""
import json
import os
from pathlib import Path
import re
import subprocess
import sys

import job_neural as shared_job
import reference_recover as recovery
from data import ROOT, atomic_json
from gap_study import (PROTOCOL, THREAD_ENV, artifact_budget, reuse, validate_protocol,
                       run as evaluate)

ARTIFACT_NAMES = shared_job.ARTIFACT_NAMES | {'protocol.json'}
STUDY_NAMES = shared_job.STUDY_NAMES
immutable_revision = shared_job.immutable_revision
safe_run = shared_job.safe_run
separate_paths = shared_job.separate_paths
remote_size = shared_job.remote_size
# Must remain the exact isolated-environment builder, not an upgrade of parent NumPy.
ensure_reference_environment = shared_job.ensure_reference_environment


def validate_manifest(manifest):
    return reuse(shared_job.validate_manifest, **globals())(manifest)


def compact_files(base):
    return reuse(shared_job.compact_files, **globals())(base)


def restore_resume(repo, previous, revision, base, download_cache):
    return reuse(shared_job.restore_resume, **globals())(repo, previous, revision, base, download_cache)


def recover_reference(cache):
    """Compose unchanged exact-artifact helpers, without legacy recover's PPO fetch.

    Existing complete local artifact: verify and reuse as-is, including its old
    recovery receipt/extra bytes (never delete or alter that cache). Fresh cache:
    recover ALL original manifest entries from the pinned source archive. Frozen
    training/fixture bytes are hash/loader-only; no new observations are saved.
    A partial artifact is an error requiring inspection, never a silent retry.
    """
    cache = Path(cache).resolve()
    cache.mkdir(parents=True, exist_ok=True)
    recovery.budget(cache)  # Keep legacy 512 MiB cap/identity; the artifact fits.
    artifact = cache / 'artifact'
    if artifact.is_symlink() or any(p.is_symlink() for p in artifact.rglob('*')):
        raise ValueError('Reference artifact symlinks forbidden')
    source_metadata = None
    if not artifact.exists():
        source_metadata = recovery.remote_metadata(recovery.PINS['source'])
        with recovery.memory_archive(recovery.PINS['source'], source_metadata) as archive:
            plan = recovery.inspect_archive(archive)
            recovery.budget(cache, plan['fullArtifactBytes'])
            recovery.verify_archived_members(archive, plan)
            recovery.extract_selected(archive, artifact, plan['members'], cache)
    checked = recovery.verify_artifact(artifact)  # COMPLETE unchanged manifest + descriptor/model.
    return dict(schema='multimap-phase-gap-recovery-v1',
                pins={k: recovery.PINS[k] for k in ('source', 'model')},
                runtimeManifestSha256=recovery.MANIFEST_SHA, policySha256=recovery.DESCRIPTOR_SHA,
                locallyVerifiedFiles=checked['present'], omitted=[], exactServiceReady=True,
                cacheBytes=recovery.budget(cache), diskBudgetBytes=recovery.MAX_CACHE,
                sourceDownload=source_metadata, modelSha256=recovery.PINS['model']['sha256'],
                recoveryMode='complete-unchanged-manifest-no-candidate-fetch',
                reserved_final_seeds_used=False)


def run():
    run_id = safe_run(os.environ['RUN_ID'])
    repo = os.environ['MODEL_REPO']
    if repo != PROTOCOL['modelRepo']:
        raise ValueError('Use the existing private multimap model repository')
    workers = int(os.environ.get('GAP_WORKERS', PROTOCOL['workers']))
    if workers not in PROTOCOL['allowedWorkers']:
        raise ValueError('GAP_WORKERS must be 1..6')
    if os.environ.get('GAP_SMOKE', '0') not in ('0', '1'):
        raise ValueError('GAP_SMOKE must be 0 or 1')
    smoke = os.environ.get('GAP_SMOKE', '0') == '1'
    base = Path(os.environ.get('RUN_DIR', '/tmp/multimap-gap-run'))
    cache = Path(os.environ.get('REFERENCE_CACHE', '/tmp/multimap-gap-reference'))
    venv = Path(os.environ.get('REFERENCE_VENV', '/tmp/multimap-gap-reference-venv'))
    resume_cache = Path(os.environ.get('RESUME_CACHE', '/tmp/multimap-gap-resume'))
    separate_paths(base, cache, venv, resume_cache)
    base.mkdir(parents=True, exist_ok=True)
    for name in THREAD_ENV:
        os.environ[name] = '1'
    os.environ['HF_HUB_DISABLE_XET'] = '1'
    os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
    from huggingface_hub import HfApi
    api = HfApi()
    receipts = []
    status = dict(run=run_id, workflow='gap',
                  sourceRevision=immutable_revision(os.environ['SOURCE_REVISION']),
                  sourceSha256=os.environ['SOURCE_SHA256'], sourcePath=os.environ['SOURCE_PATH'],
                  sourceRepo=os.environ['DATASET_REPO'], protocol=PROTOCOL, smoke=smoke, workers=workers,
                  fitted=False, selected=False, qualified=False, qualification_eligible=False,
                  reserved_final_seeds_used=False)
    if not re.fullmatch('[0-9a-f]{64}', status['sourceSha256']):
        raise ValueError('Invalid pinned source SHA256')
    if not api.model_info(repo).private:
        raise RuntimeError('Diagnostic artifacts must remain private')

    def upload(stage):
        if not api.model_info(repo).private:
            raise RuntimeError('Diagnostic repository is no longer private')
        status.update(stage=stage, receipts=list(receipts))
        atomic_json(base / 'status.json', status)
        manifest = compact_files(base)
        atomic_json(base / 'artifacts.json', manifest)
        artifact_budget(base)
        # Retry only the same idempotent compact snapshot, never games/outcomes.
        # Recheck privacy before every attempt; all four attempts are bounded.
        def publish():
            if not api.model_info(repo).private:
                raise RuntimeError('Diagnostic repository is no longer private')
            return api.upload_folder(repo_id=repo, folder_path=base, path_in_repo=f'runs/{run_id}',
                allow_patterns=[*manifest, 'artifacts.json'], ignore_patterns=['*.tmp'],
                commit_message=f'{run_id}: {stage}')
        result = shared_job.retry(publish)
        receipts.append(dict(stage=stage, revision=result.oid))
        print(json.dumps(dict(stage='uploaded', label=stage, revision=result.oid)), flush=True)

    try:
        validate_protocol()
        if not api.model_info(PROTOCOL['reference']['modelPin']['repo']).private:
            raise RuntimeError('Frozen reference model must remain private')
        for source_repo in {status['sourceRepo'], PROTOCOL['reference']['sourcePin']['repo']}:
            if not api.dataset_info(source_repo).private:
                raise RuntimeError('Frozen source artifacts must remain private')
        # Offline only: tests never invoke the exact service or perform a real game study.
        subprocess.run(['node', '--test', 'ai/multimap/test_gap.cjs'], cwd=ROOT, check=True)
        subprocess.run([sys.executable, '-B', '-m', 'unittest', 'discover', '-s', 'ai/multimap',
                        '-p', 'test_gap.py'], cwd=ROOT, check=True)
        if bool(os.environ.get('RESUME_RUN')) != bool(os.environ.get('RESUME_REVISION')):
            raise ValueError('Resume needs both run ID and immutable revision')
        if os.environ.get('RESUME_RUN'):
            status['resume'] = restore_resume(repo, os.environ['RESUME_RUN'], os.environ['RESUME_REVISION'], base, resume_cache)
        # Resume cache is small/whitelisted and separate. Do not delete existing reuse.
        atomic_json(base / 'protocol.json', PROTOCOL)
        python, environment = ensure_reference_environment(venv)
        environment['versions']['controllerEnvironment'] = environment['versions'].pop('candidate')
        environment['torchInferenceUsed'] = False
        atomic_json(base / 'environment.json', environment)
        atomic_json(base / 'recovery.json', recover_reference(cache))
        upload('runtime-ready')
        status['result'] = evaluate(base / 'study', artifact=cache / 'artifact', reference_python=python,
                                    workers=workers, smoke=smoke, callback=upload)
        upload('complete')
        print(json.dumps(dict(stage='complete', run=run_id, games=status['result']['games'],
                              failures=status['result']['failures'], qualified=False)), flush=True)
    except BaseException as error:
        # Exception text/tracebacks can contain public requests or moves: never persist them.
        status['error'] = dict(type=type(error).__name__[:100], code='diagnostic-job-stopped')
        status['qualificationStopped'] = True
        try:
            upload('failed')
        except Exception:
            print('Diagnostic failure upload failed; local compact artifacts preserved', file=sys.stderr)
        raise


if __name__ == '__main__':
    run()
