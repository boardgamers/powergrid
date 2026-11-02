"""Private bounded HF worker for the frozen expert/PPO v2 recipe."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys

from data import ROOT, atomic_json, digest
from expert_policy import PROTOCOL
from expert_ppo import artifact_budget, run as train
from gap_study import reuse, THREAD_ENV
from job_gap import recover_reference
import job_neural as shared

NAMES = {'status.json', 'protocol.json', 'environment.json', 'recovery.json'}
TRAINING_NAMES = {'expert/' + name for name in (
    'config.json', 'history.json', 'result.json', 'initial.pt', 'warmup.pt', 'best.pt', 'last.pt',
    'selection-plan.json', 'warmup-plan.json', 'confirmation-plan.json', 'warmup.json',
    'selection-teacher.json', 'selection-warmup.json', 'confirmation-selected.json', 'confirmation-teacher.json')}
TRAINING_NAMES |= {f'expert/{prefix}-{i}.json' for i in range(33)
                   for prefix in ('train', 'train-plan', 'selection')}
NAMES |= TRAINING_NAMES
TEMP_NAMES = {str(Path(n).with_suffix('.tmp')) for n in NAMES} | {n + '.tmp' for n in NAMES}
FORBIDDEN_JSON = {'observation', 'observations', 'trace', 'trajectories', 'actions', 'request', 'state_dict'}


def validate_manifest(manifest):
    if not isinstance(manifest, dict) or not {'expert/config.json', 'expert/last.pt', 'expert/initial.pt'} <= set(manifest):
        raise ValueError('Resume lacks committed expert transaction/config')
    for name, sha in manifest.items():
        if name not in NAMES or not isinstance(sha, str) or not re.fullmatch('[0-9a-f]{64}', sha):
            raise ValueError('Unsafe/unexpected resume artifact or hash')
    return {name: sha for name, sha in manifest.items() if name in TRAINING_NAMES}


def compact_json(value):
    if isinstance(value, dict):
        if FORBIDDEN_JSON & set(value):
            raise ValueError('Raw observation/action/trajectory JSON forbidden')
        for child in value.values():
            compact_json(child)
    elif isinstance(value, list):
        for child in value:
            compact_json(child)


def compact_files(base):
    base = Path(base)
    artifact_budget(base)
    files = {}
    for path in base.rglob('*'):
        if path.is_symlink():
            raise ValueError('Artifact symlinks forbidden')
        if not path.is_file():
            continue
        name = path.relative_to(base).as_posix()
        if name == 'artifacts.json' or name in TEMP_NAMES:
            continue
        if name not in NAMES:
            raise ValueError('Unexpected expert artifact')
        if path.suffix == '.json':
            compact_json(json.loads(path.read_text()))
        files[name] = digest(path)
    return files


def restore_resume(repo, previous, revision, base, download_cache):
    # A private globals copy, never mutate the frozen worker's module bindings.
    return reuse(shared.restore_resume, validate_manifest=validate_manifest,
                 artifact_budget=artifact_budget)(repo, previous, revision, base, download_cache)


def run():
    run_id = shared.safe_run(os.environ['RUN_ID'])
    repo = os.environ['MODEL_REPO']
    if repo != PROTOCOL['modelRepo']:
        raise ValueError('Use the existing private multimap model repository')
    if os.environ.get('EXPERT_SMOKE', '0') not in ('0', '1'):
        raise ValueError('EXPERT_SMOKE must be 0 or 1')
    smoke = os.environ.get('EXPERT_SMOKE', '0') == '1'
    workers = int(os.environ.get('EXPERT_WORKERS', 2 if smoke else PROTOCOL['workers']))
    if not 1 <= workers <= 6:
        raise ValueError('EXPERT_WORKERS must be 1..6')
    base = Path(os.environ.get('RUN_DIR', '/tmp/multimap-expert-run'))
    cache = Path(os.environ.get('REFERENCE_CACHE', '/tmp/multimap-expert-reference'))
    venv = Path(os.environ.get('REFERENCE_VENV', '/tmp/multimap-expert-reference-venv'))
    resume = Path(os.environ.get('RESUME_CACHE', '/tmp/multimap-expert-resume'))
    shared.separate_paths(base, cache, venv, resume)
    base.mkdir(parents=True, exist_ok=True)
    for name in THREAD_ENV:
        os.environ[name] = '1'
    os.environ['HF_HUB_DISABLE_XET'] = '1'
    os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
    from huggingface_hub import HfApi, hf_hub_download
    api = HfApi()
    receipts = []
    status = dict(run=run_id, workflow='expert', protocol=PROTOCOL, smoke=smoke, workers=workers,
        sourceRevision=shared.immutable_revision(os.environ['SOURCE_REVISION']), sourceSha256=os.environ['SOURCE_SHA256'],
        sourcePath=os.environ['SOURCE_PATH'], sourceRepo=os.environ['DATASET_REPO'], qualified=False,
        qualificationEligible=False, reservedFinalSeedsUsed=False)
    if not re.fullmatch('[0-9a-f]{64}', status['sourceSha256']):
        raise ValueError('Invalid pinned source hash')
    if not api.model_info(repo).private:
        raise RuntimeError('Artifacts must remain private')

    def upload(stage):
        status.update(stage=stage, receipts=list(receipts))
        atomic_json(base / 'status.json', status)
        manifest = compact_files(base)
        atomic_json(base / 'artifacts.json', manifest)
        artifact_budget(base)
        def publish():
            if not api.model_info(repo).private:
                raise RuntimeError('Artifact repository is no longer private')
            return api.upload_folder(repo_id=repo, folder_path=base, path_in_repo=f'runs/{run_id}',
                allow_patterns=[*manifest, 'artifacts.json'], commit_message=f'{run_id}: {stage}')
        result = shared.retry(publish)  # Same immutable snapshot only; never retry games.
        receipts.append(dict(stage=stage, revision=result.oid))
        print(json.dumps(dict(stage='uploaded', label=stage, revision=result.oid)), flush=True)

    try:
        for name in {status['sourceRepo'], PROTOCOL['reference']['sourcePin']['repo']}:
            if not api.dataset_info(name).private:
                raise RuntimeError('Source repositories must remain private')
        for name in {PROTOCOL['warmStart']['repo'], PROTOCOL['reference']['modelPin']['repo']}:
            if not api.model_info(name).private:
                raise RuntimeError('Frozen models must remain private')
        subprocess.run(['node', '--test', 'ai/multimap/test_expert.cjs'], cwd=ROOT, check=True)
        subprocess.run([sys.executable, '-B', '-m', 'unittest', 'discover', '-s', 'ai/multimap',
                        '-p', 'test_expert*.py'], cwd=ROOT, check=True)
        if bool(os.environ.get('RESUME_RUN')) != bool(os.environ.get('RESUME_REVISION')):
            raise ValueError('Resume needs run ID and immutable revision')
        if os.environ.get('RESUME_RUN'):
            status['resume'] = restore_resume(repo, os.environ['RESUME_RUN'], os.environ['RESUME_REVISION'], base, resume)
        atomic_json(base / 'protocol.json', PROTOCOL)
        python, environment = shared.ensure_reference_environment(venv)
        atomic_json(base / 'environment.json', environment)
        atomic_json(base / 'recovery.json', recover_reference(cache))
        warm = PROTOCOL['warmStart']
        status['checkpointBytes'] = [shared.remote_size(pin['repo'], pin['path'], pin['revision'], maximum=16 * 1024**2)
                                     for pin in [warm, *PROTOCOL['opponentPool']]]
        checkpoint = hf_hub_download(warm['repo'], warm['path'], revision=warm['revision'])
        if digest(checkpoint) != warm['sha256']:
            raise ValueError('Wrong frozen warm-start bytes')
        upload('runtime-ready')
        status['result'] = train(checkpoint, base / 'expert', smoke=smoke, callback=upload,
                                 artifact=cache / 'artifact', reference_python=python)
        upload('complete')
        print(json.dumps(dict(stage='complete', run=run_id, result=status['result'])), flush=True)
    except BaseException as error:
        status['error'] = dict(type=type(error).__name__[:100], code='expert-job-stopped')
        try:
            upload('failed')
        except Exception:
            print('Failure snapshot upload failed; local artifacts preserved', file=sys.stderr)
        raise


if __name__ == '__main__':
    run()
