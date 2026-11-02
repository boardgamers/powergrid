"""Package a clean source revision, pin it on HF, submit one bounded CPU job.

Credentials are read from the existing HF credential store and sent ONLY through
Jobs' secret mechanism. Never serialize the JobInfo object (may carry secrets).
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile

from huggingface_hub import HfApi, get_token
from data import ROOT, atomic_json, digest

DATASET = "coyotte508/powergrid-ai-training-v1"
MODEL = "coyotte508/powergrid-ai-multimap-v1"
IMAGE = "python:3.12.8-slim-bookworm@sha256:2199a62885a12290dc9c5be3ca0681d367576ab7bf037da120e564723292a2f0"
BOOTSTRAP = r'''
import os,subprocess,tarfile,hashlib
from pathlib import Path
from huggingface_hub import hf_hub_download
p=hf_hub_download(os.environ['DATASET_REPO'],os.environ['SOURCE_PATH'],repo_type='dataset',revision=os.environ['SOURCE_REVISION'])
assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==os.environ['SOURCE_SHA256'],'Source hash mismatch'
root=Path('/tmp/multimap-source');root.mkdir(exist_ok=True)
with tarfile.open(p) as t:t.extractall(root,filter='data')
os.chdir(root)
os.environ['PATH']=str(root/'runtime')+':'+os.environ['PATH']
os.environ['PYTHONPATH']=str(root/'ai/multimap')
subprocess.run(['python','-m','pip','install','--disable-pip-version-check','--extra-index-url','https://download.pytorch.org/whl/cpu','-r','ai/multimap/requirements-cpu.txt'],check=True)
os.execvp('python',['python','-u','-B','ai/multimap/job.py'])
'''


def package(directory):
    directory = Path(directory)
    directory.mkdir(parents=True,exist_ok=True)
    stage = directory / "source"
    if stage.exists():
        raise RuntimeError("Source stage already exists; choose a new output")
    stage.mkdir()
    paths = ["ai/core.cjs", "ai/strong/economics.cjs", "ai/multimap", "engine/dist", "engine/src",
             "engine/index.ts", "engine/package.json", "engine/pnpm-lock.yaml"]
    for path in paths:
        src, dst = ROOT / path, stage / path
        dst.parent.mkdir(parents=True,exist_ok=True)
        if src.is_dir():
            shutil.copytree(src,dst,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
        else:
            shutil.copy2(src,dst)
    for name in ("lodash","seedrandom","delaunator"):
        resolved = subprocess.check_output(['node','-p',f"require.resolve('{name}/package.json',{{paths:['./engine']}})"],cwd=ROOT,text=True).strip()
        shutil.copytree(Path(resolved).parent,stage/"engine/node_modules"/name)
    node = subprocess.check_output(['node','-p','process.execPath'],text=True).strip()
    (stage/'runtime').mkdir()
    shutil.copy2(node,stage/'runtime/node')
    # Verify package independently; no symlink to the checkout's node_modules.
    subprocess.run([str(stage/'runtime/node'),'--test','ai/multimap/test.cjs'],cwd=stage,check=True)
    manifest = dict(gitCommit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
                    node=subprocess.check_output(['node','--version'],text=True).strip(),
                    files={str(p.relative_to(stage)):digest(p) for p in sorted(stage.rglob('*')) if p.is_file()})
    atomic_json(stage/'source-manifest.json',manifest)
    archive = directory/'source.tgz'
    with tarfile.open(archive,'w:gz',compresslevel=3) as tar:
        for child in sorted(stage.iterdir()):
            tar.add(child,arcname=child.name)
    return archive, manifest['gitCommit']


def launch(run_id, directory):
    directory=Path(directory).resolve()
    if not run_id.replace('-','').replace('_','').isalnum():
        raise ValueError('Unsafe run ID')
    if subprocess.check_output(['git','status','--porcelain','--untracked-files=normal'],cwd=ROOT,text=True).strip():
        raise RuntimeError('Commit source before launching; working tree must be clean')
    archive,commit=package(directory)
    api=HfApi()
    api.create_repo(MODEL,private=True,exist_ok=True)
    if not api.model_info(MODEL).private or not api.dataset_info(DATASET).private:
        raise RuntimeError('Artifact repositories must remain private')
    source_path=f'multimap/{run_id}/source.tgz'
    if api.file_exists(DATASET,source_path,repo_type='dataset'):
        raise RuntimeError('Run ID already published; do not overwrite source')
    upload=api.upload_file(repo_id=DATASET,repo_type='dataset',path_or_fileobj=archive,
                           path_in_repo=source_path,commit_message=f'{run_id}: pinned source {commit}')
    env=dict(RUN_ID=run_id,MODEL_REPO=MODEL,DATASET_REPO=DATASET,SOURCE_PATH=source_path,
             SOURCE_REVISION=upload.oid,SOURCE_SHA256=digest(archive),OMP_NUM_THREADS='4',
             MKL_NUM_THREADS='4',OPENBLAS_NUM_THREADS='1',PYTHONUNBUFFERED='1',PYTHONDONTWRITEBYTECODE='1')
    # Resolve tokens in memory; they never appear in commands, output or manifests.
    token=get_token()
    if not token:
        raise RuntimeError('Missing HF credentials')
    intent=dict(run=run_id,sourceCommit=commit,env=env,image=IMAGE,flavor='cpu-upgrade',timeout='3h')
    atomic_json(directory/'intent.json',intent)
    command=['bash','-lc',"python -m pip install --disable-pip-version-check huggingface_hub==1.29.0 && python -c "+__import__('shlex').quote(BOOTSTRAP)]
    job=api.run_job(image=IMAGE,command=command,env=env,secrets={'HF_TOKEN':token},
                    flavor='cpu-upgrade',timeout='3h',name=run_id,
                    labels={'project':'powergrid-multimap','stage':'bootstrap-v1'})
    record={**intent,'jobId':job.id,'url':f'https://huggingface.co/jobs/coyotte508/{job.id}'}
    atomic_json(directory/'launch.json',record)
    print(json.dumps(record,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--run-id',required=True)
    p.add_argument('--output',required=True)
    a=p.parse_args()
    launch(a.run_id,a.output)
