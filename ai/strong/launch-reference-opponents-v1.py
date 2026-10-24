"""Submit a fixed, guarded root diagnostic only after its complete runtime pilot."""
import argparse
import hashlib
import json
from pathlib import Path
import time

from huggingface_hub import HfApi, get_token, hf_hub_download
from strategic_collection import ROOT, read, write, digest

BOOTSTRAP = r'''
set -euo pipefail
apt-get update -qq
apt-get install -y --no-install-recommends libstdc++6 libgomp1 ca-certificates >/dev/null
python -m pip install --quiet --timeout 120 --retries 5 huggingface_hub==2.0.0 onnxruntime==1.30.0 numpy==2.4.6
mkdir -p /workspace
python - <<'INNER'
import urllib.request,tarfile,os,hashlib
from pathlib import Path
from huggingface_hub import hf_hub_download
urllib.request.urlretrieve('https://nodejs.org/dist/v24.14.0/node-v24.14.0-linux-x64.tar.xz','/tmp/node.tar.xz')
with tarfile.open('/tmp/node.tar.xz') as bundle:bundle.extractall('/opt',filter='data')
for kind,repo,type_ in [('SOURCE','coyotte508/powergrid-ai-training-v1','dataset'),('EVIDENCE','coyotte508/powergrid-ai-germany-v1','model')]:
    file=hf_hub_download(repo,os.environ[kind+'_ARCHIVE'],repo_type=type_,revision=os.environ[kind+'_REVISION'])
    assert hashlib.sha256(Path(file).read_bytes()).hexdigest()==os.environ[kind+'_SHA256']
    with tarfile.open(file) as bundle:bundle.extractall('/workspace',filter='data')
INNER
export PATH=/opt/node-v24.14.0-linux-x64/bin:$PATH
cd /workspace
python -u ai/strong/reference-opponent-job-v1.py "$ROOT_INDEX" --begin "$WORLD_BEGIN" --worlds "$WORLD_COUNT" --upload
'''


def main(root, begin, execute):
    strong=ROOT/'ai/strong'
    descriptor=read(strong/'reference-opponent-pilot-evidence-v1.json')
    assert descriptor['remote_archive_verified'] and descriptor['no_pilot_strength_claim']
    assert len(descriptor['controls'])==7 and len(descriptor['pilot'])==4
    admission=descriptor['admission']
    worlds=admission['worlds_per_job']
    assert worlds in (4,8,16) and begin in range(0,64,worlds)
    assert admission['jobs']==7*(64//worlds) and admission['flavor']=='cpu-basic'
    assert admission['automatic_retries'] is False and admission['timeout_hours']<=6
    local=ROOT/'ai/runs/reference-opponent-pilot-evidence-v1'
    assert digest(local.with_suffix('.tgz'))==descriptor['archive_sha256']
    manifest=read(local/'manifest.json')
    for name,sha in manifest.items():
        assert digest(local/name)==sha
        if name.startswith('ai/strong/') and name.endswith(('.py','.cjs')):
            assert digest(ROOT/name)==sha
    assert manifest['ai/strong/launch-reference-opponents-v1.py']==digest(__file__)
    assert read(local/'layout-check.json')['exit_code']==0
    source=read(strong/'population-hybrid-development-source-v1.json')
    protocol=ROOT/'ai/runs/reference-opponent-diagnostic-v1/protocol.json'
    assert descriptor['protocol_sha256']==digest(protocol)
    plan=read(strong/'population-hybrid-development-plan-v1.json')
    assert all(digest(ROOT/name)==sha for name,sha in plan['dependency_hashes'].items())
    case=f'reference-opponent-full-v1-root-{root}-worlds-{begin}-{begin+worlds}'
    record={'case':case,'root':root,'begin':begin,'worlds':worlds,'stage':'launch_intent','time':time.time(),
            'protocol_sha256':digest(protocol),'source':source,
            'pilot_evidence':{k:descriptor[k] for k in ('repo','revision','archive_path','archive_sha256')},
            'admission':admission,'bootstrap_sha256':hashlib.sha256(BOOTSTRAP.encode()).hexdigest(),
            'qualification_eligible':False,'reserved_final_seeds_used':False}
    if not execute:
        print(json.dumps({'execute':False,'case':case,'admitted':True,'timeout_hours':admission['timeout_hours']}));return
    token=get_token();assert token
    downloaded=hf_hub_download(descriptor['repo'],descriptor['archive_path'],revision=descriptor['revision'])
    assert digest(downloaded)==descriptor['archive_sha256']
    directory=ROOT/'ai/runs/reference-opponent-launches-v1';directory.mkdir(exist_ok=True)
    active=0
    for file in directory.glob('*.json'):
        previous=read(file)
        assert previous['stage']=='launched','Reconcile unresolved submissions before any further launch'
        stage=HfApi().inspect_job(job_id=previous['job_id']).status.stage
        assert stage not in ('ERROR','CANCELED','CANCELLED','DELETED'), 'Review failed jobs; no automatic continuation'
        active+=stage!='COMPLETED'
    assert active<admission['max_concurrent_jobs'],'Existing jobs fill the admitted concurrency'
    guard=directory/(case+'.json')
    with guard.open('x') as f:json.dump(record,f,indent=2)
    try:
        job=HfApi().run_job(image='python:3.11-slim-bookworm',command=['bash','-lc',BOOTSTRAP],
            flavor=admission['flavor'],timeout=f"{admission['timeout_hours']}h",name=case,
            secrets={'HF_TOKEN':token},labels={'project':'powergrid-ai','stage':'reference-opponent-v1','case':case},
            env={'SOURCE_ARCHIVE':source['archive'],'SOURCE_REVISION':source['revision'],'SOURCE_SHA256':source['sha256'],
                 'EVIDENCE_ARCHIVE':descriptor['archive_path'],'EVIDENCE_REVISION':descriptor['revision'],
                 'EVIDENCE_SHA256':descriptor['archive_sha256'],'ROOT_INDEX':str(root),
                 'WORLD_BEGIN':str(begin),'WORLD_COUNT':str(worlds),'HF_HUB_DISABLE_PROGRESS_BARS':'1'})
        record.update(stage='launched',job_id=job.id)
    except BaseException as error:
        record.update(stage='launch_unknown',error=type(error).__name__+': '+str(error));raise
    finally:write(guard,record)
    print(json.dumps({'case':case,'job_id':record['job_id']}),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(__doc__)
    parser.add_argument('root',type=int,choices=range(7));parser.add_argument('--begin',type=int,default=0)
    parser.add_argument('--execute',action='store_true')
    args=parser.parse_args();main(args.root,args.begin,args.execute)
