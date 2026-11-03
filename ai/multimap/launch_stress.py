"""Package once; launch the two frozen stress panels as private bounded jobs.

Never edits the frozen generic launcher or serving modules. Source/credentials
remain separately pinned; secrets are never included in receipts or commands.
"""
import argparse
import json
from pathlib import Path
import shlex
import subprocess

from huggingface_hub import HfApi, get_token
from data import ROOT, atomic_json, digest
from launch import package, check_local_storage, DATASET, MODEL, IMAGE
from job_neural import safe_run
from stress_study import PROTOCOL, identity, ARTIFACT, REFERENCE_PYTHON

BOOTSTRAP = r'''
import os,subprocess,tarfile,hashlib,json
from pathlib import Path
from huggingface_hub import hf_hub_download,get_hf_file_metadata,hf_hub_url,get_token
rev=os.environ['SOURCE_REVISION'];name=os.environ['SOURCE_PATH'];repo=os.environ['DATASET_REPO']
meta=get_hf_file_metadata(hf_hub_url(repo,name,repo_type='dataset',revision=rev),token=get_token())
assert meta.commit_hash==rev and type(meta.size) is int and 0<meta.size<128*1024**2,'Source metadata rejected'
p=hf_hub_download(repo,name,repo_type='dataset',revision=rev)
assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==os.environ['SOURCE_SHA256'],'Source hash mismatch'
root=Path('/tmp/multimap-source');root.mkdir(exist_ok=True)
with tarfile.open(p) as t:
    assert sum(m.size for m in t.getmembers())<256*1024**2,'Expanded source budget'
    t.extractall(root,filter='data')
manifest=json.loads((root/'source-manifest.json').read_text())
assert {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}==set(manifest['files'])|{'source-manifest.json'},'Source member coverage'
for name,sha in manifest['files'].items():
    file=root/name
    assert not file.is_symlink() and file.is_relative_to(root) and hashlib.sha256(file.read_bytes()).hexdigest()==sha,'Source member hash'
os.chdir(root);os.environ['PATH']=str(root/'runtime')+':'+os.environ['PATH'];os.environ['PYTHONPATH']=str(root/'ai/multimap')
subprocess.run(['python','-m','pip','install','--no-cache-dir','--disable-pip-version-check','--extra-index-url','https://download.pytorch.org/whl/cpu','-r','ai/multimap/requirements-cpu.txt'],check=True)
os.execvp('python',['python','-u','-B','ai/multimap/job_stress.py'])
'''


def launch(group, directory):
    safe_run(group);directory=Path(directory).resolve()
    if directory.parent!=(ROOT/'ai/runs').resolve() or directory.name!=group or not group.startswith('multimap-'):
        raise ValueError('Use dedicated ai/runs/multimap-* group directory')
    if subprocess.check_output(['git','status','--porcelain','--untracked-files=normal'],cwd=ROOT,text=True).strip():
        raise RuntimeError('Commit all source/preflight before launch')
    preflight=json.loads((ROOT/'ai/multimap/stress-preflight-v1.json').read_text())
    if not preflight['allChecksPassed'] or preflight['protocolSha256']!=digest(ROOT/'ai/multimap/stress-protocol-v1.json'):
        raise ValueError('Pinned real-service preflight required')
    for panel in PROTOCOL['panels']:
        current=identity(panel,True,6,ARTIFACT,REFERENCE_PYTHON)
        if current!=preflight['smokeIdentities'][panel]:raise ValueError('Preflight source/runtime identity changed')
    check_local_storage(directory)
    api=HfApi();token=get_token()
    if not token or not api.model_info(MODEL).private or not api.dataset_info(DATASET).private:
        raise RuntimeError('Private repositories and existing credentials required')
    source_path=f'multimap/{group}/source.tgz'
    if api.file_exists(DATASET,source_path,repo_type='dataset'):raise ValueError('Group source already published; inspect receipts, never relaunch blindly')
    for panel in PROTOCOL['panels']:
        if api.file_exists(MODEL,f'runs/{group}-{panel}/status.json'):raise ValueError('Panel already exists')
    archive,commit=package(directory)
    upload=api.upload_file(repo_id=DATASET,repo_type='dataset',path_or_fileobj=archive,path_in_repo=source_path,
                           commit_message=f'{group}: frozen population stress source {commit}')
    source=dict(sourceCommit=commit,sourcePath=source_path,sourceRevision=upload.oid,sourceSha256=digest(archive),
                sourceBytes=archive.stat().st_size,protocolSha256=digest(ROOT/'ai/multimap/stress-protocol-v1.json'))
    atomic_json(directory/'source.json',source)
    command=['bash','-lc','python -m pip install --no-cache-dir --disable-pip-version-check huggingface_hub==1.29.0 && python -c '+shlex.quote(BOOTSTRAP)]
    records=[]
    for panel in PROTOCOL['panels']:
        run=group+'-'+panel;out=ROOT/'ai/runs'/run
        if out.exists():raise ValueError('Panel launch output already exists; inspect before retry')
        env=dict(RUN_ID=run,MODEL_REPO=MODEL,DATASET_REPO=DATASET,SOURCE_PATH=source['sourcePath'],
                 SOURCE_REVISION=source['sourceRevision'],SOURCE_SHA256=source['sourceSha256'],
                 STRESS_PANEL=panel,STRESS_WORKERS='6',STRESS_SMOKE='0',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',
                 OPENBLAS_NUM_THREADS='1',PYTHONUNBUFFERED='1',PYTHONDONTWRITEBYTECODE='1',HF_HUB_DISABLE_PROGRESS_BARS='1')
        intent=dict(run=run,group=group,panel=panel,sourceCommit=commit,env=env,image=IMAGE,flavor='cpu-upgrade',timeout='3h',
                    plannedGames=2560,plannedDealClusters=320,selectedCheckpointSha256=PROTOCOL['selected']['sha256'],
                    preflightSha256=digest(ROOT/'ai/multimap/stress-preflight-v1.json'),qualified=False,reservedFinalSeedsUsed=False)
        atomic_json(out/'intent.json',intent)
        job=api.run_job(image=IMAGE,command=command,env=env,secrets={'HF_TOKEN':token},flavor='cpu-upgrade',
                        timeout='3h',name=run,labels={'project':'powergrid-multimap','stage':'stress-v1','panel':panel})
        record=dict(intent,jobId=job.id,url=f'https://huggingface.co/jobs/coyotte508/{job.id}')
        atomic_json(out/'launch.json',record);records.append(record)
        atomic_json(directory/'launches.json',records)
        print(json.dumps(record,indent=2),flush=True)
    return records


def continue_panel(receipt_path, new_run, *, revision=None, missing_panel=None):
    """Explicit recovery using the original HF command/source, never repack.

    Resume a stopped panel with an immutable snapshot, or submit an unsubmitted
    peer after a partial two-panel launch. An existing local intent is a blocker:
    inspect uncertain API submissions rather than accidentally duplicating jobs.
    """
    import ast
    from job_neural import immutable_revision, remote_size
    from huggingface_hub import hf_hub_download
    receipt=json.loads(Path(receipt_path).read_text());safe_run(new_run)
    if bool(revision)==bool(missing_panel):raise ValueError('Choose immutable resume OR missing peer')
    if not new_run.startswith('multimap-'):raise ValueError('Use a multimap run ID')
    out=ROOT/'ai/runs'/new_run
    if out.exists():raise ValueError('Existing intent/output: inspect possible submission, never blindly retry')
    api=HfApi();old=api.inspect_job(job_id=receipt['jobId'])
    if (old.environment!=receipt['env'] or old.docker_image!=receipt['image'] or old.flavor!=receipt['flavor']):
        raise ValueError('Original HF job differs from launch receipt')
    original=subprocess.check_output(['git','show',receipt['sourceCommit']+':ai/multimap/launch_stress.py'],cwd=ROOT,text=True)
    nodes=[n.value for n in ast.parse(original).body if isinstance(n,ast.Assign) and
           any(isinstance(t,ast.Name) and t.id=='BOOTSTRAP' for t in n.targets)]
    if len(nodes)!=1:raise ValueError('Original bootstrap constant missing')
    command=['bash','-lc','python -m pip install --no-cache-dir --disable-pip-version-check huggingface_hub==1.29.0 && python -c '+shlex.quote(ast.literal_eval(nodes[0]))]
    if old.command!=command or old.arguments:raise ValueError('Original execution command drift')
    if not api.model_info(MODEL).private or not api.dataset_info(DATASET).private:raise RuntimeError('Private repositories required')
    if api.file_exists(MODEL,f'runs/{new_run}/status.json'):raise ValueError('Output run already published')
    env=dict(receipt['env'],RUN_ID=new_run)
    inherited={}
    if revision:
        immutable_revision(revision)
        if old.status.stage not in ('ERROR','CANCELED'):raise ValueError('Only stopped jobs may resume')
        # Check all compact metadata before submission. The unchanged worker
        # verifies downloaded hashes and source/runtime/full-task identity.
        from job_stress import validate_manifest
        prefix='runs/'+receipt['run']+'/'
        remote_size(MODEL,prefix+'artifacts.json',revision,maximum=64*1024)
        m=json.loads(Path(hf_hub_download(MODEL,prefix+'artifacts.json',revision=revision)).read_text())
        inherited=validate_manifest(m)
        sizes=[remote_size(MODEL,prefix+n,revision,maximum=64*1024**2) for n in inherited]
        if sum(sizes)>64*1024**2:raise ValueError('Resume compact budget exceeded')
        env.update(RESUME_RUN=receipt['run'],RESUME_REVISION=revision)
    else:
        if missing_panel not in ('strong','mixed') or missing_panel==receipt['panel']:
            raise ValueError('Missing peer must be the other frozen panel')
        env['STRESS_PANEL']=missing_panel
    token=get_token()
    if not token:raise RuntimeError('Existing credentials required')
    intent={k:v for k,v in receipt.items() if k not in ('jobId','url')}
    intent.update(run=new_run,panel=env['STRESS_PANEL'],env=env,recoveryFromJob=receipt['jobId'],
                  resumeRevision=revision,inheritedFileHashes=inherited,sourceArchiveReusedExactly=True)
    atomic_json(out/'intent.json',intent)
    new=api.run_job(image=receipt['image'],command=command,env=env,secrets={'HF_TOKEN':token},
        flavor=receipt['flavor'],timeout='3h',name=new_run,labels={'project':'powergrid-multimap','stage':'stress-v1','panel':env['STRESS_PANEL']})
    record=dict(intent,jobId=new.id,url=f'https://huggingface.co/jobs/coyotte508/{new.id}')
    atomic_json(out/'launch.json',record);print(json.dumps(record,indent=2));return record


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--group');p.add_argument('--output')
    p.add_argument('--continue-launch');p.add_argument('--run-id');p.add_argument('--resume-revision')
    p.add_argument('--missing-panel',choices=['strong','mixed'])
    a=p.parse_args()
    if a.continue_launch:
        if a.group or a.output or not a.run_id:p.error('Recovery requires --run-id, not --group/--output')
        continue_panel(a.continue_launch,a.run_id,revision=a.resume_revision,missing_panel=a.missing_panel)
    else:
        if not a.group or not a.output or a.run_id or a.resume_revision or a.missing_panel:p.error('New launch requires --group and --output only')
        launch(a.group,a.output)
