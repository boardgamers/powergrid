"""Bounded immutable artifact/source/job/replay evidence for stress-v1.

Separate from the independent statistics auditor. No launch, optimization,
selection or new seed API is used. Existing complete reference/cache is reused.
"""
import ast
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import time

from data import ROOT, atomic_json, digest
from stress_study import read, canonical, identity, ARTIFACT, REFERENCE_PYTHON, plan, task_hash
from audit_expert import reuse
from audit_neural import RemoteFiles, git_blob, require, equal
from job_stress import NAMES, compact_json

HERE=Path(__file__).resolve().parent
SOURCE='e6e3b571eb07d1da66aec594e0ecb75b44d79e2c'
REPO='coyotte508/powergrid-ai-multimap-v1'
LAUNCH_COMMIT='f849e76ca995a063798815ba18845cbf6905fe25'
GROUP='multimap-stress-20261103-v1'
DATASET='coyotte508/powergrid-ai-training-v1'
SOURCE_REVISION='034ec3e2bda35de8e59e570bcc9cdcc20ef760d7'
SOURCE_SHA256='5231bece1d79622072ae907a8470f6e6b248409a0b8ffbc4bc305732d9b4a870'
IMAGE='python:3.12.8-slim-bookworm@sha256:2199a62885a12290dc9c5be3ca0681d367576ab7bf037da120e564723292a2f0'
JOBS={'strong':'6ae9b2e2c78863f9c63189a6','mixed':'6ae9b2e3c78863f9c63189a8'}
LIMIT=64*1024**2
TIMINGS={'featureMs','inferenceMs','referenceMs','seconds'}


def git_bytes(name):
    return subprocess.check_output(['git','show',SOURCE+':'+name],cwd=ROOT)


def expected_environment(panel):
    require(panel in JOBS,'Original panel only')
    return dict(RUN_ID=GROUP+'-'+panel,MODEL_REPO=REPO,DATASET_REPO=DATASET,
        SOURCE_PATH='multimap/'+GROUP+'/source.tgz',SOURCE_REVISION=SOURCE_REVISION,SOURCE_SHA256=SOURCE_SHA256,
        STRESS_PANEL=panel,STRESS_WORKERS='6',STRESS_SMOKE='0',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',
        OPENBLAS_NUM_THREADS='1',PYTHONUNBUFFERED='1',PYTHONDONTWRITEBYTECODE='1',HF_HUB_DISABLE_PROGRESS_BARS='1')


def validate_launch(receipt):
    source=dict(sourceCommit=SOURCE,sourcePath='multimap/'+GROUP+'/source.tgz',sourceRevision=SOURCE_REVISION,
        sourceSha256=SOURCE_SHA256,sourceBytes=48959500,
        protocolSha256='9e2931e24e33fee611c12fed2cf41f60303f170f6a2be112a7fa1a5fb110bcc1')
    equal(receipt['source'],source,'Independent frozen source pin')
    require(receipt['sourceDatasetRepo']==DATASET and receipt['resultModelRepo']==REPO,'Frozen repositories')
    require(len(receipt['jobs'])==2 and {r['panel'] for r in receipt['jobs']}==set(JOBS),'Original job coverage')
    for r in receipt['jobs']:
        panel=r['panel'];env=expected_environment(panel)
        require(r['jobId']==JOBS[panel] and r['run']==env['RUN_ID'] and r['sourceCommit']==SOURCE and
                r['image']==IMAGE and r['flavor']=='cpu-upgrade' and r['timeout']=='3h','Original job/source/image/budget')
        equal(r['env'],env,'Job environment explicitly bound to verified source')
    return receipt


def launch_receipt():
    path=HERE/'stress-launch-v1.json'
    archived=subprocess.check_output(['git','show',LAUNCH_COMMIT+':ai/multimap/stress-launch-v1.json'],cwd=ROOT)
    require(path.read_bytes()==archived,'Launch receipt differs from pinned post-launch Git commit')
    return validate_launch(read(path))


def restore_safety(base):
    base=Path(base)
    require(not any(p.is_symlink() for p in (base,*base.absolute().parents)), 'Unsafe restore ancestor')
    if not base.exists():return
    require(base.is_dir(),'Restore root must be a directory')
    for p in base.rglob('*'):
        require(not p.is_symlink(),'Nested restore symlink before writes')
        name=p.relative_to(base).as_posix()
        require((p.is_file() and name in NAMES|{'artifacts.json'}) or (p.is_dir() and name=='study'),
                'Unexpected restore descendant before writes')


def snapshot_metadata(manifest, entries, prefix):
    require(set(manifest)==NAMES, 'Complete original 326-file panel manifest required')
    require(all(isinstance(h,str) and re.fullmatch('[0-9a-f]{64}',h) for h in manifest.values()), 'Manifest hashes')
    require(len(entries)==327 and len({e.path for e in entries})==327, 'Remote file coverage')
    byname={e.path[len(prefix):]:e for e in entries if e.path.startswith(prefix)}
    require(set(byname)==NAMES|{'artifacts.json'}, 'Remote whitelist/file coverage')
    require(all(type(e.size) is int and 0<e.size<=LIMIT for e in entries), 'Remote sizes')
    require(sum(e.size for e in entries)<=LIMIT, 'Total panel byte budget before payload downloads')
    return byname


def fetch_panel(panel,revision,output,api=None):
    from huggingface_hub import HfApi,hf_hub_download
    require(panel in ('strong','mixed') and re.fullmatch('[0-9a-f]{40}',revision), 'Immutable panel pin')
    api=api or HfApi(); output=Path(output);base=output/'restored'
    restore_safety(base)
    run='multimap-stress-20261103-v1-'+panel;prefix='runs/'+run+'/'
    remote=RemoteFiles(api)
    manifest_pin=dict(repo=REPO,revision=revision,path=prefix+'artifacts.json')
    metadata=remote.describe(manifest_pin)
    require(metadata.size<=64*1024, 'Manifest size before download')
    manifest_path=remote.get(manifest_pin,metadata=metadata)
    manifest=read(manifest_path)
    entries=[e for e in api.list_repo_tree(REPO,path_in_repo=prefix.rstrip('/'),revision=revision,recursive=True) if hasattr(e,'blob_id')]
    byname=snapshot_metadata(manifest,entries,prefix)
    checksums=dict(manifest,**{'artifacts.json':digest(manifest_path)})
    restore_safety(base)
    def get(name):
        e=byname[name];dest=base/name
        require(not any(p.is_symlink() for p in (dest,*dest.absolute().parents)), 'Local artifact symlink/ancestor')
        p=dest if dest.exists() else Path(hf_hub_download(REPO,prefix+name,revision=revision))
        require(p.is_file() and p.stat().st_size==e.size and digest(p)==checksums[name], 'Artifact content/size/hash: '+name)
        if e.lfs:
            require(e.lfs.sha256==checksums[name] and e.lfs.size==e.size,'LFS metadata')
            pointer=f'version https://git-lfs.github.com/spec/v1\noid sha256:{e.lfs.sha256}\nsize {e.size}\n'.encode()
            require(git_blob(pointer)==e.blob_id,'LFS Git pointer')
        else:require(git_blob(p.read_bytes())==e.blob_id,'Git blob content')
        compact_json(read(p));dest.parent.mkdir(parents=True,exist_ok=True)
        require(not any(x.is_symlink() for x in (dest,*dest.absolute().parents)), 'Unsafe destination before copy')
        if p!=dest:shutil.copyfile(p,dest)
        return dict(path=name,bytes=e.size,sha256=checksums[name],gitBlob=e.blob_id)
    with ThreadPoolExecutor(max_workers=6) as pool:evidence=list(pool.map(get,checksums))
    require({p.relative_to(base).as_posix() for p in base.rglob('*') if p.is_file()}==set(checksums),'Restored file coverage')
    require(not any(p.is_symlink() for p in base.rglob('*')),'Restored symlinks')
    report=dict(panel=panel,run=run,repo=REPO,revision=revision,files=len(evidence),bytes=sum(e['bytes'] for e in evidence),
                manifestSha256=checksums['artifacts.json'],checks=evidence,metadataFirst=True,private=True)
    atomic_json(output/'download-verification.json',report)
    return report


def local_difference(name,archived,local):
    if archived==local:return None
    require(name in {'ai/multimap/README.md','ai/multimap/runs.json'},'Frozen source drift: '+name)
    return dict(sourceSha256=archived,localSha256=local,note='Nonserving documentation/run bookkeeping only')


def verify_runtime_source(panel,base):
    import audit_neural,audit_gap
    base=Path(base);receipt=launch_receipt();saved=read(base/'study/plan.json')
    require(receipt['source']['sourceCommit']==SOURCE,'Frozen source Git')
    for n in ('audit_neural.py','audit_gap.py','audit_expert.py'):
        require(hashlib.sha256(git_bytes('ai/multimap/'+n)).hexdigest()==digest(HERE/n),'Unchanged integrity helper')
    rebuilt=identity(panel,False,6,ARTIFACT,REFERENCE_PYTHON)
    equal(saved,rebuilt,'Complete source/runtime/task/reference identity')
    cfg=saved['expertIdentity'];env=read(base/'environment.json')
    equal(env['versions'],cfg['runtimeVersions'],'Recorded runtime versions')
    ep=read(HERE/'expert-protocol-v2.json')
    require(env['requirementsSha256']==ep['referenceRequirementsSha256'] and env['referenceVenvBytes']<=ep['referenceVenvMaxBytes'],'Reference environment requirements/budget')
    source=receipt['source'];remote=RemoteFiles(__import__('huggingface_hub').HfApi())
    pin=dict(repo=receipt['sourceDatasetRepo'],repo_type='dataset',revision=source['sourceRevision'],path=source['sourcePath'],sha256=source['sourceSha256'])
    archive=remote.get(pin,cached=ROOT/'ai/runs/multimap-stress-20261103-v1/source.tgz')
    report=reuse(audit_neural.verify_source,ROOT=ROOT,HERE=HERE,SOURCE=SOURCE,
        SOURCE_NAMES=set(cfg['sourceFiles']),git_bytes=git_bytes,local_source_difference=local_difference)(archive,cfg)
    reference=audit_gap.verify_reference(dict(ep,compressedArchiveRamMaxBytes=128*1024**2),read(base/'recovery.json'),remote)
    status=read(base/'status.json')
    expected=dict(run='multimap-stress-20261103-v1-'+panel,workflow='stress',panel=panel,smoke=False,workers=6,
        sourceRevision=source['sourceRevision'],sourceSha256=source['sourceSha256'],sourceRepo=receipt['sourceDatasetRepo'],sourcePath=source['sourcePath'],
        protocol=read(HERE/'stress-protocol-v1.json'),qualified=False,qualificationEligible=False,reservedFinalSeedsUsed=False)
    equal({k:status[k] for k in expected},expected,'Recorded source/config/status')
    require(set(status)==set(expected)|{'stage','receipts','result'} and status['stage']=='complete','Complete original status only')
    stages=['runtime-ready']+[f'batches-{i}' for i in range(16,321,16)]+['complete']
    require([r['stage'] for r in status['receipts']]==stages,'Original publication cadence')
    require(all(re.fullmatch('[0-9a-f]{40}',r['revision']) for r in status['receipts']),'Immutable publication receipts')
    return dict(panel=panel,source=report,reference=reference,fullIdentityVerified=True,
                launchReceiptGit=LAUNCH_COMMIT,launchReceiptSha256=digest(HERE/'stress-launch-v1.json'),
                identitySha256=task_hash(saved),runtimeVersions=cfg['runtimeVersions'],environment=env,remoteEvidence=remote.evidence)


def verify_job(panel,output,api=None):
    from huggingface_hub import HfApi
    api=api or HfApi();output=Path(output)
    require(panel in JOBS,'Original panel only')
    r=next(r for r in launch_receipt()['jobs'] if r['panel']==panel)
    tree=ast.parse(git_bytes('ai/multimap/launch_stress.py'))
    values=[ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='BOOTSTRAP' for t in n.targets)]
    require(len(values)==1,'Frozen bootstrap')
    command=['bash','-lc','python -m pip install --no-cache-dir --disable-pip-version-check huggingface_hub==1.29.0 && python -c '+shlex.quote(values[0])]
    job=api.inspect_job(job_id=r['jobId'])
    require(job.id==JOBS[panel] and job.status.stage=='COMPLETED' and job.environment==expected_environment(panel) and job.docker_image==IMAGE and
            job.flavor==r['flavor'] and job.command==command and not job.arguments,'Completed immutable HF job')
    log='\n'.join(api.fetch_job_logs(job_id=r['jobId'],follow=False))
    require(len(log.encode())<2*1024**2,'Bounded job log')
    require(re.search(r'Ran 45 tests in .*?\n\s*\n?OK',log) and re.search(r'(?:#|ℹ) tests 10',log) and
            re.search(r'(?:#|ℹ) pass 10',log) and re.search(r'(?:#|ℹ) fail 0',log),'HF startup 45 Python / 10 Node tests')
    marker='{"stage": "uploaded", "label": "runtime-ready"'
    require(log.count(marker)==1,'Single production boundary')
    startup,production=log.split(marker,1)
    events=[json.loads(line) for line in production.splitlines() if line.startswith('{"stage":')]
    batches=[e for e in events if e['stage']=='stress-batch']
    require([e['batches'] for e in batches]==list(range(1,321)) and batches[-1]['games']==2560,'Single ordered production batch execution')
    require(all(e['panel']==panel and e['totalBatches']==320 for e in batches),'Production panel scope')
    totals=[];total=0
    for n in Counter(s['seed'] for s in plan(panel)).values():
        total+=n;totals.append(total)
    require([e['games'] for e in batches]==totals,'Exact cumulative production game counts')
    require(all(e['stage'] in ('stress-batch','uploaded','complete') for e in events),'No production optimization events')
    uploads=[e for e in events if e['stage']=='uploaded']
    require([e['label'] for e in uploads]==[f'batches-{i}' for i in range(16,321,16)]+['complete','complete'],'Final production uploads')
    require(all(re.fullmatch('[0-9a-f]{40}',e['revision']) for e in uploads),'Immutable job upload revisions')
    require(events[-1]==dict(stage='complete',run=r['run'],panel=panel,games=2560,qualified=False),'Complete log marker')
    output.mkdir(parents=True,exist_ok=True);(output/'job.log').write_text(log)
    report=dict(jobId=r['jobId'],status=job.status.stage,startedAt=str(job.started_at),finishedAt=str(job.finished_at),
        finalRevision=uploads[-1]['revision'],batches=320,games=2560,pythonTests=45,nodeTests=10,
        sourceCommandEnvironmentVerified=True,executedSourceBoundToVerifiedArchive=True,
        launchReceiptGit=LAUNCH_COMMIT,launchReceiptSha256=digest(HERE/'stress-launch-v1.json'),
        logSha256=hashlib.sha256(log.encode()).hexdigest(),logBytes=len(log.encode()),
        startupTestBatchesAreNotProduction=True,productionOptimizationEvents=0)
    atomic_json(output/'job-verification.json',report);return report


def replay_tasks(panel):
    # Deterministic selection by scope only, before inspecting terminal outcomes.
    cells=('Germany|2|original|0','Germany|3|original|1','Germany|4|recharged|0',
           'Germany|5|recharged|1','Germany|6|original|0','USA|3|recharged|0',
           'France|3|recharged|1','UK & Ireland|4|original|1')
    tasks=[s for s in plan(panel) if s['cell'] in cells and s['deal']==0 and s['focalSeat']==0]
    require(len(tasks)==16,'Replay task coverage')
    return tasks


def replay_panel(panel,base,output):
    import torch
    from stress_rollout import load_models,collect
    began=time.monotonic();base=Path(base);output=Path(output);tasks=replay_tasks(panel)
    stored={canonical(r['spec']):r for p in sorted((base/'study').glob('batch-*.json')) for r in read(p)['games']}
    models=load_models(artifact=ARTIFACT,reference_python=REFERENCE_PYTHON)
    torch.use_deterministic_algorithms(True)
    outcomes=collect(tasks,workers=6,artifact=ARTIFACT,reference_python=REFERENCE_PYTHON,models=models)
    checks=[];controllers=Counter()
    for r,s in zip(outcomes,tasks):
        require(r['spec']==s,'Replay order/scope')
        original=stored[canonical(s)]
        left={k:v for k,v in r.items() if k not in TIMINGS};right={k:v for k,v in original.items() if k not in TIMINGS}
        require(left==right,'Exact replay terminal/counter mismatch')
        checks.append(dict(spec=s,terminalAndCountersSha256=task_hash(left)))
        controllers.update({k:sum(v.values()) for k,v in r['counts'].items()})
    require(len(outcomes)==len(tasks)==len(checks)==16,'Replay count')
    report=dict(panel=panel,games=16,exactMatches=16,checks=checks,controllerCounts=dict(controllers),
        workers=6,allFourMaps=True,allFivePlayerCounts=True,allFourRules=True,bothFocalPolicies=True,
        newIndependentObservations=0,excludedTimingFields=sorted(TIMINGS),seconds=time.monotonic()-began)
    atomic_json(output/'replay-verification.json',report);return report


def audit_evidence(panel,output):
    """Authenticate a completed original job, recover its final pin, then replay."""
    output=Path(output)
    job=verify_job(panel,output)
    download=fetch_panel(panel,job['finalRevision'],output)
    integrity=verify_runtime_source(panel,output/'restored')
    atomic_json(output/'integrity-verification.json',integrity)
    replay=replay_panel(panel,output/'restored',output)
    return dict(job=job,download=download,integrity=integrity,replay=replay)


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--panel',required=True,choices=('strong','mixed'))
    args=parser.parse_args()
    directory=ROOT/f'ai/runs/multimap-stress-20261103-v1-{args.panel}/audit'
    result=audit_evidence(args.panel,directory)
    print(json.dumps(dict(panel=args.panel,revision=result['job']['finalRevision'],
        files=result['download']['files'],bytes=result['download']['bytes'],exactReplayMatches=result['replay']['exactMatches']),indent=2))
