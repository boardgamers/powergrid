"""Plan disjoint deals, launch once and independently verify each collection piece."""
import argparse
from datetime import datetime,timezone
import importlib.util
import json
import math
from pathlib import Path
import re
import subprocess
from huggingface_hub import hf_hub_download
from strategic_collection_slices import ROOT, PROTOCOL, SOURCE, read, write, digest, prefix, verify_local

spec=importlib.util.spec_from_file_location('original_manager',ROOT/'ai/strong/manage-strategic-collection.py')
old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
GUARDS=ROOT/'ai/runs/strategic-training-collection-slices-launches-v1'
def plan_path(n):return ROOT/f'ai/strong/strategic-training-collection-slices-{n}p-plan-v1.json'

def plan(n):
    source=read(SOURCE);admission=old.profile(n,'search_geo')
    assert not admission['admitted'],'Use already-admitted whole shard or explicitly justify a new plan'
    deals=read(PROTOCOL)['deals_per_shard'];assert deals==16
    size=max(k for k in range(1,5) if math.ceil((120+2*admission['probe_seconds']*k)/(.75*3600))<=12)
    pieces=[{'start':start,'end':min(start+size,deals)} for start in range(0,deals,size)]
    for r in pieces:r['timeout_hours']=max(4,math.ceil((120+2*admission['probe_seconds']*(r['end']-r['start']))/(.75*3600)))
    assert [d for r in pieces for d in range(r['start'],r['end'])]==list(range(16))
    result={'stage':'split_plan','players':n,'mode':'search_geo','smoke':False,'created_at':datetime.now(timezone.utc).isoformat(),
        'pieces':pieces,'original_admission':admission,'source_revision':source['revision'],'source_sha256':source['sha256'],
        'protocol_sha256':digest(PROTOCOL),'qualification_eligible':False,
        'scope':'All original16 deals, seats and rules; no shorter horizons or changed model.'}
    assert not plan_path(n).exists()
    # Reserve the original whole-shard slot so its old launcher cannot duplicate these games.
    guard=ROOT/f'ai/runs/strategic-training-collection-launches-v1/{n}p-search_geo.json'
    with guard.open('x') as f:json.dump(result,f,indent=2)
    write(plan_path(n),result);print(result)

def launch(n,start,end):
    source=read(SOURCE);p=read(plan_path(n));piece=next(r for r in p['pieces'] if r['start']==start and r['end']==end)
    assert p['source_sha256']==source['sha256'] and p['protocol_sha256']==digest(PROTOCOL)
    assert all(digest(ROOT/name)==sha for name,sha in source['overlays'].items())
    check=read(ROOT/'ai/strong/strategic-training-collection-slices-preflight-v1.json')
    assert check['passed'] and check['source_sha256']==source['sha256']
    GUARDS.mkdir(exist_ok=True);key=f'{n}p-search_geo-{start}-{end}';guard=GUARDS/(key+'.json')
    record={'stage':'launch_intent','created_at':datetime.now(timezone.utc).isoformat(),'players':n,'mode':'search_geo',
        **piece,'source_revision':source['revision'],'source_sha256':source['sha256'],'protocol_sha256':digest(PROTOCOL),
        'qualification_eligible':False}
    with guard.open('x') as f:json.dump(record,f,indent=2)
    command=['hf','jobs','run','--detach','--flavor','cpu-performance','--timeout',str(piece['timeout_hours'])+'h',
        '--secrets','HF_TOKEN','--label','project=powergrid-ai','--label','stage=strategic-collection-slices-v1-'+key]
    for k,v in {'PLAYERS':str(n),'START':str(start),'END':str(end),'SOURCE_ARCHIVE':source['archive'],
        'SOURCE_REVISION':source['revision'],'SOURCE_SHA256':source['sha256'],'HF_HUB_DISABLE_PROGRESS_BARS':'1'}.items():command+=['--env',k+'='+v]
    command+=['--','pytorch/pytorch:2.6.0-cuda12.4-cudnn9-runtime','bash','-lc','''
set -euo pipefail
python -m pip install --quiet --timeout 120 --retries 5 huggingface_hub==2.0.0 onnxruntime==1.30.0 numpy==2.4.6
mkdir -p /workspace
python - <<'PY'
import urllib.request,tarfile,os,hashlib
from pathlib import Path
from huggingface_hub import hf_hub_download
urllib.request.urlretrieve('https://nodejs.org/dist/v24.14.0/node-v24.14.0-linux-x64.tar.xz','/tmp/node.tar.xz')
with tarfile.open('/tmp/node.tar.xz') as f:f.extractall('/opt')
p=hf_hub_download('coyotte508/powergrid-ai-training-v1',os.environ['SOURCE_ARCHIVE'],repo_type='dataset',revision=os.environ['SOURCE_REVISION'])
assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==os.environ['SOURCE_SHA256']
with tarfile.open(p) as f:f.extractall('/workspace',filter='data')
PY
export PATH=/opt/node-v24.14.0-linux-x64/bin:$PATH
cd /workspace
python -u ai/strong/strategic_collection_slices.py "$PLAYERS" search_geo ai/runs/collection-slice "$START" "$END" --upload
''']
    try:
        result=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,check=True)
        (GUARDS/(key+'.log')).write_text(result.stdout+result.stderr)
        ids=set(re.findall(r'\b[0-9a-f]{24}\b',result.stdout));assert len(ids)==1,'Inspect existing job label; do not resubmit'
        record.update(stage='launched',job_id=ids.pop())
    except BaseException as e:record.update(stage='launch_unknown',error=type(e).__name__+': '+str(e));raise
    finally:write(guard,record)
    print(record,flush=True)

def collect(n,start,end,revision):
    assert re.fullmatch('[a-f0-9]{40}',revision)
    plan=read(plan_path(n));assert any(r['start']==start and r['end']==end for r in plan['pieces'])
    remote=prefix(n,'search_geo',False,start,end);p=read(PROTOCOL);source=read(SOURCE)
    path=Path(hf_hub_download(p['repo'],remote+'/collection-check.json',revision=revision));status=read(path)
    assert status['status']=='complete' and set(status['artifacts'])=={'games.json','roots.jsonl.gz'}
    out=ROOT/f'ai/runs/strategic-training-collection-slices-verified-v1/{n}p-search_geo-{start}-{end}'
    out.mkdir(parents=True,exist_ok=False);(out/'collection-check.json').write_bytes(path.read_bytes())
    for name,sha in status['artifacts'].items():
        path=Path(hf_hub_download(p['repo'],remote+'/'+name,revision=revision));assert digest(path)==sha;(out/name).write_bytes(path.read_bytes())
    summary=verify_local(out,n,'search_geo',start,end)
    saved={'verified':True,'players':n,'start':start,'end':end,'revision':revision,'prefix':remote,'summary':summary,
        'source_revision':source['revision'],'source_sha256':source['sha256'],'protocol_sha256':digest(PROTOCOL),
        'artifacts':{q.name:digest(q) for q in out.iterdir() if q.is_file()},'qualification_eligible':False}
    write(out/'verified.json',saved);print({k:v for k,v in summary.items() if k!='coverage'})

if __name__=='__main__':
    p=argparse.ArgumentParser(__doc__);sub=p.add_subparsers(dest='command',required=True)
    for verb in ['plan','launch','collect']:
        q=sub.add_parser(verb);q.add_argument('players',type=int,choices=range(4,7))
        if verb!='plan':q.add_argument('start',type=int);q.add_argument('end',type=int)
        if verb=='collect':q.add_argument('revision')
    a=p.parse_args()
    if a.command=='plan':plan(a.players)
    elif a.command=='launch':launch(a.players,a.start,a.end)
    else:collect(a.players,a.start,a.end,a.revision)
