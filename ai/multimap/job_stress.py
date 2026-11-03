"""Private bounded HF worker; frozen population evaluation, never optimization."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import types

# Set before importing huggingface_hub transitively. Importing this module in
# offline tests must not redirect the user's/shared cache.
if __name__ == '__main__':
    os.environ['HF_HUB_CACHE'] = os.environ.get('STRESS_MODEL_CACHE', '/tmp/multimap-stress-models')

from data import ROOT, atomic_json, digest
from stress_study import PROTOCOL, artifact_budget, run as evaluate, read
from job_gap import recover_reference
import job_neural as shared

STUDY_NAMES = {'study/plan.json', 'study/summary.json'} | {f'study/batch-{i:03}.json' for i in range(320)}
NAMES = STUDY_NAMES | {'status.json', 'protocol.json', 'environment.json', 'recovery.json'}
FORBIDDEN = {'observation', 'observations', 'request', 'response', 'state', 'move', 'rows', 'actions',
             'state_dict', 'trajectory', 'trajectories', 'trace'}


def compact_json(value):
    if isinstance(value,dict):
        if FORBIDDEN & set(value):
            raise ValueError('Raw decision/optimization payload forbidden')
        for v in value.values(): compact_json(v)
    elif isinstance(value,list):
        for v in value: compact_json(v)


def validate_manifest(manifest):
    if not isinstance(manifest,dict) or 'study/plan.json' not in manifest:
        raise ValueError('Resume lacks frozen study identity')
    if any(n not in NAMES or not isinstance(h,str) or not re.fullmatch('[0-9a-f]{64}',h) for n,h in manifest.items()):
        raise ValueError('Unexpected resume file/hash')
    return {n:h for n,h in manifest.items() if n in STUDY_NAMES}


def compact_files(base):
    base=Path(base); artifact_budget(base); result={}
    for p in base.rglob('*'):
        if p.is_symlink(): raise ValueError('Artifact symlink forbidden')
        if not p.is_file(): continue
        n=p.relative_to(base).as_posix()
        if n=='artifacts.json' or (n.endswith('.tmp') and n[:-4] in NAMES): continue
        if n not in NAMES: raise ValueError('Unexpected artifact filename')
        compact_json(read(p)); result[n]=digest(p)
    return result


def restore_resume(repo, previous, revision, base, cache):
    # The generic transport/hash restorer is unchanged; only a private binding
    # gets the new filename whitelist and tighter budget. No serving guards rebound.
    f=shared.restore_resume
    namespace=dict(f.__globals__,validate_manifest=validate_manifest,artifact_budget=artifact_budget)
    return types.FunctionType(f.__code__,namespace,f.__name__,f.__defaults__,f.__closure__)(repo,previous,revision,base,cache)


def run():
    run_id=shared.safe_run(os.environ['RUN_ID']);repo=os.environ['MODEL_REPO']
    panel=os.environ['STRESS_PANEL'];workers=int(os.environ.get('STRESS_WORKERS','6'))
    flag=os.environ.get('STRESS_SMOKE','0')
    if repo!=PROTOCOL['modelRepo'] or panel not in PROTOCOL['panels'] or flag not in ('0','1') or not 1<=workers<=6:
        raise ValueError('Frozen job scope rejected')
    base=Path(os.environ.get('RUN_DIR','/tmp/multimap-stress-run'))
    cache=Path(os.environ.get('REFERENCE_CACHE','/tmp/multimap-stress-reference'))
    venv=Path(os.environ.get('REFERENCE_VENV','/tmp/multimap-stress-reference-venv'))
    resume=Path(os.environ.get('RESUME_CACHE','/tmp/multimap-stress-resume'))
    models=Path(os.environ.get('STRESS_MODEL_CACHE','/tmp/multimap-stress-models'))
    shared.separate_paths(base,cache,venv,resume,models)
    base.mkdir(parents=True,exist_ok=True)
    for k in ('OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS'):os.environ[k]='1'
    os.environ['HF_HUB_DISABLE_PROGRESS_BARS']='1';os.environ['HF_HUB_DISABLE_XET']='1'
    from huggingface_hub import HfApi
    from expert_policy import PROTOCOL as expert_protocol
    api=HfApi();receipts=[]
    status=dict(run=run_id,workflow='stress',panel=panel,smoke=flag=='1',workers=workers,
        sourceRevision=shared.immutable_revision(os.environ['SOURCE_REVISION']),sourceSha256=os.environ['SOURCE_SHA256'],
        sourceRepo=os.environ['DATASET_REPO'],sourcePath=os.environ['SOURCE_PATH'],protocol=PROTOCOL,
        qualified=False,qualificationEligible=False,reservedFinalSeedsUsed=False)
    if not re.fullmatch('[0-9a-f]{64}',status['sourceSha256']): raise ValueError('Invalid source hash')
    def upload(stage):
        status.update(stage=stage,receipts=list(receipts))
        atomic_json(base/'status.json',status)
        manifest=compact_files(base);atomic_json(base/'artifacts.json',manifest);artifact_budget(base)
        def publish():
            if not api.model_info(repo).private: raise RuntimeError('Private artifacts required')
            return api.upload_folder(repo_id=repo,folder_path=base,path_in_repo=f'runs/{run_id}',
                allow_patterns=[*manifest,'artifacts.json'],commit_message=f'{run_id}: {stage}')
        result=shared.retry(publish)
        receipts.append(dict(stage=stage,revision=result.oid))
        print(json.dumps(dict(stage='uploaded',label=stage,revision=result.oid)),flush=True)
    try:
        for name in {repo,PROTOCOL['selected']['repo'],expert_protocol['reference']['modelPin']['repo']}:
            if not api.model_info(name).private: raise RuntimeError('Private model repositories required')
        for name in {status['sourceRepo'],expert_protocol['reference']['sourcePin']['repo']}:
            if not api.dataset_info(name).private: raise RuntimeError('Private source repositories required')
        subprocess.run(['node','--test','ai/multimap/test_stress.cjs'],cwd=ROOT,check=True)
        subprocess.run([sys.executable,'-B','-m','unittest','discover','-s','ai/multimap','-p','test_stress*.py'],cwd=ROOT,check=True)
        if bool(os.environ.get('RESUME_RUN'))!=bool(os.environ.get('RESUME_REVISION')):raise ValueError('Incomplete resume pin')
        if os.environ.get('RESUME_RUN'):
            status['resume']=restore_resume(repo,os.environ['RESUME_RUN'],os.environ['RESUME_REVISION'],base,resume)
        atomic_json(base/'protocol.json',PROTOCOL)
        python,env=shared.ensure_reference_environment(venv);atomic_json(base/'environment.json',env)
        atomic_json(base/'recovery.json',recover_reference(cache))
        upload('runtime-ready')
        status['result']=evaluate(base/'study',panel,artifact=cache/'artifact',reference_python=python,
                                  workers=workers,smoke=flag=='1',callback=upload)
        upload('complete')
        print(json.dumps(dict(stage='complete',run=run_id,panel=panel,games=status['result']['games'],qualified=False)),flush=True)
    except BaseException as error:
        status['error']=dict(type=type(error).__name__[:100],code='stress-job-stopped')
        try:upload('failed')
        except Exception:print('Failure snapshot unavailable; local files retained',file=sys.stderr)
        raise RuntimeError('Stress evaluation stopped; inspect fixed-code status and committed batches') from None


if __name__=='__main__':run()
