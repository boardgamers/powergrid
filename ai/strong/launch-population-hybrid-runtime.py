"""Submit exactly one guarded endpoint CPU runtime pilot; never the strength grid."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
import re
import subprocess

from huggingface_hub import get_token, HfApi
from strategic_collection import ROOT, read, write, digest

BOOTSTRAP='''
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
path=hf_hub_download('coyotte508/powergrid-ai-training-v1',os.environ['SOURCE_ARCHIVE'],repo_type='dataset',revision=os.environ['SOURCE_REVISION'])
assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==os.environ['SOURCE_SHA256']
with tarfile.open(path) as bundle:bundle.extractall('/workspace',filter='data')
INNER
export PATH=/opt/node-v24.14.0-linux-x64/bin:$PATH
cd /workspace
python -u ai/strong/population-hybrid-runtime-job.py "$PLAYERS"
'''


def main(players,execute):
    source=read(ROOT/'ai/strong/population-hybrid-source-v2.json')
    assert source['protocol_sha256']==digest(ROOT/'ai/strong/population-hybrid-development-protocol-v1.json')
    assert all(digest(ROOT/name)==sha for name,sha in source['overlays'].items())
    assert read(ROOT/'ai/runs/population-policy-trained-probe-v1/assessment.json')['checks_complete']
    previous=ROOT/f'ai/runs/population-hybrid-runtime-launches-v1/population-hybrid-runtime-v1-{players}p.json'
    original=read(previous)
    failed=read(ROOT/'ai/runs/population-hybrid-runtime-failures-v1/assessment.json')
    assert any(row['job_id']==original['job_id'] and row['authoritative_status']=='ERROR' for row in failed['jobs'])
    job=HfApi().inspect_job(job_id=original['job_id'])
    assert job.status.stage=='ERROR'
    assert source['layout_check']['reached_evaluation_subprocess']
    case=f'population-hybrid-runtime-v2-{players}p'
    record={'case':case,'stage':'launch_intent','created_at':datetime.now(timezone.utc).isoformat(),
        'source':source,'protocol_sha256':source['protocol_sha256'],'players':players,
        'arm':'combined','opponent':'search_geo','flavor':'cpu-upgrade','timeout_hours':6,
        'bootstrap_sha256':hashlib.sha256(BOOTSTRAP.encode()).hexdigest(),
        'qualification_eligible':False,'reserved_final_seeds_used':False,
        'replaces_job_id':original['job_id'],'original_guard_sha256':digest(previous)}
    if not execute:
        print({'case':case,'admitted':True,'execute':False});return
    env=os.environ.copy();env['HF_TOKEN']=get_token() or env.get('HF_TOKEN') or '';assert env['HF_TOKEN']
    guards=ROOT/'ai/runs/population-hybrid-runtime-launches-v2';guards.mkdir(exist_ok=True)
    guard=guards/(case+'.json')
    with guard.open('x') as stream:json.dump(record,stream,indent=2)
    cmd=['hf','jobs','run','--detach','--flavor','cpu-upgrade','--timeout','6h','--secrets','HF_TOKEN',
        '--label','project=powergrid-ai','--label','stage=population-hybrid-runtime-v2','--label','case='+case]
    for key,value in {'SOURCE_ARCHIVE':source['archive'],'SOURCE_REVISION':source['revision'],
        'SOURCE_SHA256':source['sha256'],'PROTOCOL_SHA256':source['protocol_sha256'],
        'PLAYERS':str(players),'HF_HUB_DISABLE_PROGRESS_BARS':'1'}.items():cmd+=['--env',key+'='+value]
    cmd+=['--','python:3.11-slim-bookworm','bash','-lc',BOOTSTRAP]
    try:
        run=subprocess.run(cmd,cwd=ROOT,env=env,capture_output=True,text=True,check=True)
        guard.with_suffix('.log').write_text(run.stdout+run.stderr)
        ids=set(re.findall(r'\b[a-f0-9]{24}\b',run.stdout));assert len(ids)==1,'Reconcile ambiguous submission; do not retry'
        record.update(stage='launched',job_id=ids.pop())
    except BaseException as error:
        record.update(stage='launch_unknown',error=type(error).__name__+': '+str(error));raise
    finally:write(guard,record)
    print({'case':case,'job_id':record['job_id']},flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(__doc__);parser.add_argument('players',type=int,choices=[2,6]);parser.add_argument('--execute',action='store_true')
    args=parser.parse_args();main(args.players,args.execute)
