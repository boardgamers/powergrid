"""Launch one pinned model's paired development games; never duplicate intents."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT=Path(__file__).resolve().parents[2]
read=lambda p:json.loads(Path(p).read_text())
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
p=argparse.ArgumentParser(__doc__);p.add_argument('key',choices=['parent','10101','10102']);a=p.parse_args()
source=read(ROOT/'ai/strong/discard-correction-screen-source-v1.json')
preflight=read(ROOT/'ai/strong/discard-correction-screen-preflight-v1.json')
assert preflight['source_revision']==source['revision'] and preflight['source_sha256']==source['sha256']
assert preflight['games']==108 and preflight['game_truncations']==0 and preflight['search_truncations']==0
assert all(sha(ROOT/name)==value for name,value in source['overlays'].items())
directory=ROOT/'ai/runs/discard-correction-screen-launches-v1';directory.mkdir(exist_ok=True)
path=directory/(a.key+'.json')
record={'key':a.key,'stage':'launch_intent','created_at':datetime.now(timezone.utc).isoformat(),
    'source_revision':source['revision'],'source_sha256':source['sha256'],
    'protocol_sha256':source['protocol_sha256'],'models_sha256':source['models_sha256'],'qualification_eligible':False}
with path.open('x') as f:json.dump(record,f,indent=2)
command=['hf','jobs','run','--detach','--flavor','cpu-performance','--timeout','4h','--secrets','HF_TOKEN',
    '--label','project=powergrid-ai','--label','stage=discard-correction-screen-v1-'+a.key]
for key,value in {'MODEL_KEY':a.key,'SOURCE_ARCHIVE':source['archive'],'SOURCE_REVISION':source['revision'],
    'SOURCE_SHA256':source['sha256'],'HF_HUB_DISABLE_PROGRESS_BARS':'1'}.items():command+=['--env',key+'='+value]
command+=['--','pytorch/pytorch:2.6.0-cuda12.4-cudnn9-runtime','bash','-lc','''
set -euo pipefail
python -m pip install --quiet --timeout 120 --retries 5 huggingface_hub==2.0.0 onnxruntime==1.30.0 numpy==2.4.6
mkdir -p /workspace
python - <<'PY'
import urllib.request,tarfile,os,hashlib
from pathlib import Path
from huggingface_hub import hf_hub_download
urllib.request.urlretrieve("https://nodejs.org/dist/v24.14.0/node-v24.14.0-linux-x64.tar.xz","/tmp/node.tar.xz")
with tarfile.open("/tmp/node.tar.xz") as f:f.extractall("/opt")
p=hf_hub_download("coyotte508/powergrid-ai-training-v1",os.environ['SOURCE_ARCHIVE'],repo_type='dataset',revision=os.environ['SOURCE_REVISION'])
assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==os.environ['SOURCE_SHA256']
with tarfile.open(p) as f:f.extractall('/workspace',filter='data')
PY
export PATH=/opt/node-v24.14.0-linux-x64/bin:$PATH
cd /workspace
python -u ai/strong/discard_correction_screen.py "$MODEL_KEY" "ai/runs/discard-correction-screen-v1-$MODEL_KEY" --upload
''']
try:
    r=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,check=True)
    (directory/(a.key+'.log')).write_text(r.stdout+r.stderr)
    ids=set(re.findall(r'\b[0-9a-f]{24}\b',r.stdout))
    if len(ids)!=1:raise RuntimeError('Ambiguous launch; inspect existing jobs before retrying')
    record.update(stage='launched',job_id=ids.pop())
except BaseException as e:
    record.update(stage='launch_unknown',error=type(e).__name__+': '+str(e));raise
finally:path.write_text(json.dumps(record,indent=2)+'\n')
print(record)
