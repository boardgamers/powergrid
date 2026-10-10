"""Exclusive HF launch guards for continuation runtime probes."""
import argparse
from datetime import datetime, timezone
import json
import re
import subprocess
from strategic_collection import ROOT, read, write, digest

p=argparse.ArgumentParser(__doc__);p.add_argument('players',type=int,choices=range(2,7))
p.add_argument('mode',choices=['neural','neural_economic','neural_search','mixed_control']);a=p.parse_args()
source=read(ROOT/'ai/strong/strategic-teacher-probe-source-v1.json')
assert digest(ROOT/'ai/strong/strategic-teacher-probe-protocol-v1.json')==source['protocol_sha256']
assert all(digest(ROOT/name)==sha for name,sha in source['overlays'].items())
preflight=read(ROOT/'ai/strong/strategic-teacher-probe-preflight-v1.json')
assert preflight['source_sha256']==source['sha256'] and preflight['frozen_package_passed']
guards=ROOT/'ai/runs/strategic-teacher-probe-launches-v1';guards.mkdir(exist_ok=True)
key=f'{a.players}p-{a.mode}';guard=guards/(key+'.json')
record={'stage':'launch_intent','created_at':datetime.now(timezone.utc).isoformat(),'players':a.players,
    'mode':a.mode,'source_revision':source['revision'],'source_sha256':source['sha256'],
    'protocol_sha256':source['protocol_sha256'],'timeout_hours':4,'qualification_eligible':False}
with guard.open('x') as f:json.dump(record,f,indent=2)
command=['hf','jobs','run','--detach','--flavor','cpu-performance','--timeout','4h','--secrets','HF_TOKEN',
    '--label','project=powergrid-ai','--label','stage=strategic-teacher-probe-v1-'+key]
for k,v in {'PLAYERS':str(a.players),'MODE':a.mode,'SOURCE_ARCHIVE':source['archive'],
    'SOURCE_REVISION':source['revision'],'SOURCE_SHA256':source['sha256'],'HF_HUB_DISABLE_PROGRESS_BARS':'1'}.items():command+=['--env',k+'='+v]
command+=['--','pytorch/pytorch:2.6.0-cuda12.4-cudnn9-runtime','bash','-lc','''
set -euo pipefail
python -m pip install --quiet --timeout 120 --retries 5 huggingface_hub==2.0.0 onnxruntime==1.30.0 numpy==2.4.6
mkdir -p /workspace
python - <<'PY'
import urllib.request,tarfile,os,hashlib
from pathlib import Path
from huggingface_hub import hf_hub_download
urllib.request.urlretrieve("https://nodejs.org/dist/v24.14.0/node-v24.14.0-linux-x64.tar.xz","/tmp/node.tar.xz")
with tarfile.open('/tmp/node.tar.xz') as f:f.extractall('/opt')
p=hf_hub_download('coyotte508/powergrid-ai-training-v1',os.environ['SOURCE_ARCHIVE'],repo_type='dataset',revision=os.environ['SOURCE_REVISION'])
assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==os.environ['SOURCE_SHA256']
with tarfile.open(p) as f:f.extractall('/workspace',filter='data')
PY
export PATH=/opt/node-v24.14.0-linux-x64/bin:$PATH
cd /workspace
python -u ai/strong/run-strategic-teacher-probe.py "$PLAYERS" "$MODE" ai/runs/strategic-teacher-probe-run --upload
''']
try:
    result=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,check=True)
    (guards/(key+'.log')).write_text(result.stdout+result.stderr)
    ids=set(re.findall(r'\b[0-9a-f]{24}\b',result.stdout));assert len(ids)==1,'Ambiguous submission; inspect existing job label'
    record.update(stage='launched',job_id=ids.pop())
except BaseException as e:
    record.update(stage='launch_unknown',error=type(e).__name__+': '+str(e));raise
finally:write(guard,record)
print(record,flush=True)
