"""One guarded GPU job for both fixed training seeds; no local gradient steps."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT=Path(__file__).resolve().parents[2]
read=lambda p:json.loads(Path(p).read_text())
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
source=read(ROOT/'ai/strong/discard-correction-source-v1.json')
preflight=read(ROOT/'ai/strong/discard-correction-preflight-v1.json')
assert preflight['source']==source and preflight['frozen_scope_identical']
assert preflight['scope']['labels_strict_parity']==3361 and preflight['parity']['positions']==2553
assert sha(ROOT/'ai/strong/discard-correction-protocol-v1.json')==source['protocol_sha256']
assert all(sha(ROOT/name)==value for name,value in source['overlays'].items())
directory=ROOT/'ai/runs/discard-correction-launch-v1';directory.mkdir(exist_ok=True)
path=directory/'launch.json'
record={'stage':'launch_intent','created_at':datetime.now(timezone.utc).isoformat(),
    'source_revision':source['revision'],'source_sha256':source['sha256'],
    'protocol_sha256':source['protocol_sha256'],'flavor':'l4x1','seeds':[10101,10102],
    'qualification_eligible':False}
with path.open('x') as f:json.dump(record,f,indent=2)
command=['hf','jobs','run','--detach','--flavor','l4x1','--timeout','3h','--secrets','HF_TOKEN',
    '--label','project=powergrid-ai','--label','stage=discard-correction-v1']
for key,value in {'SOURCE_ARCHIVE':source['archive'],'SOURCE_REVISION':source['revision'],
    'SOURCE_SHA256':source['sha256'],'POWERGRID_HF_TRAINING':'1','HF_HUB_DISABLE_PROGRESS_BARS':'1'}.items():
    command+=['--env',key+'='+value]
command+=['--','pytorch/pytorch:2.6.0-cuda12.4-cudnn9-runtime','bash','-lc','''
set -euo pipefail
python -m pip install --quiet --timeout 120 --retries 5 huggingface_hub==2.0.0 onnxruntime==1.30.0 onnx==1.23.1 numpy==2.4.6
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
node --test ai/strong/test-discard-correction-features.cjs
python ai/strong/test_model_discard.py
python -u ai/strong/train-discard-correction.py ai/runs/discard-correction-v1 --upload
''']
try:
    r=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,check=True)
    (directory/'launch.log').write_text(r.stdout+r.stderr)
    ids=set(re.findall(r'\b[0-9a-f]{24}\b',r.stdout))
    if len(ids)!=1:raise RuntimeError('Ambiguous launch response; inspect existing jobs before any retry')
    record.update(stage='launched',job_id=ids.pop())
except BaseException as e:
    record.update(stage='launch_unknown',error=type(e).__name__+': '+str(e));raise
finally:path.write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record))
