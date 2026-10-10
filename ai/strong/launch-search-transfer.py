"""Launch guarded HF search48 probes, then admit full jobs from verified timings."""
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
p=argparse.ArgumentParser(__doc__);p.add_argument('key',choices=['parent','10101','10102'])
p.add_argument('case',choices=['heuristic-2p','search_geo-2p','a260-3p']);p.add_argument('--smoke',action='store_true');a=p.parse_args()
source=read(ROOT/'ai/strong/search-transfer-source-v1.json')
assert all(sha(ROOT/k)==v for k,v in source['overlays'].items())
preflight=read(ROOT/'ai/strong/search-transfer-local-preflight-v1.json')
assert preflight['source_revision']==source['revision'] and preflight['source_sha256']==source['sha256']
assert preflight['frozen_package_passed'] and preflight['routing']['all_menu_indices_match']
assert preflight['routing']['outside_search_proposals_preserved'] and preflight['baseline']['all_baseline_contracts_passed']
protocol=read(ROOT/'ai/strong/search-transfer-protocol-v1.json');timeout_hours=4
if a.smoke:assert a.key==protocol['smoke']['model']
else:
    profile=read(ROOT/'ai/strong/search-transfer-runtime-profile-v1.json')
    assert profile['source_revision']==source['revision'] and profile['source_sha256']==source['sha256'] and profile['verified']
    assert profile['game_truncations']==profile['search_truncations']==0
    admission=profile['admission'][a.case];timeout_hours=admission['timeout_hours']
    assert admission['admitted'] and 4<=timeout_hours<=12
    assert admission['projected_shard_seconds']<=.75*timeout_hours*3600
suffix=('smoke-' if a.smoke else '')+a.key+'-'+a.case
directory=ROOT/'ai/runs/search-transfer-launches-v1';directory.mkdir(exist_ok=True);path=directory/(suffix+'.json')
record={'key':a.key,'case':a.case,'smoke':a.smoke,'stage':'launch_intent','timeout_hours':timeout_hours,
    'created_at':datetime.now(timezone.utc).isoformat(),'source_revision':source['revision'],'source_sha256':source['sha256'],
    'protocol_sha256':source['protocol_sha256'],'qualification_eligible':False}
if not a.smoke:
    record['runtime_admission']=admission
    record['runtime_profile_sha256']=sha(ROOT/'ai/strong/search-transfer-runtime-profile-v1.json')
with path.open('x') as f:json.dump(record,f,indent=2)
command=['hf','jobs','run','--detach','--flavor','cpu-performance','--timeout',f'{timeout_hours}h','--secrets','HF_TOKEN',
    '--label','project=powergrid-ai','--label','stage=search-transfer-v1-'+suffix]
for k,v in {'MODEL_KEY':a.key,'CASE_ID':a.case,'SMOKE':'1' if a.smoke else '0',
    'SOURCE_ARCHIVE':source['archive'],'SOURCE_REVISION':source['revision'],'SOURCE_SHA256':source['sha256'],
    'HF_HUB_DISABLE_PROGRESS_BARS':'1'}.items():command+=['--env',k+'='+v]
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
args=()
if [ "$SMOKE" = 1 ]; then args+=(--smoke); fi
python -u ai/strong/search_transfer.py "$MODEL_KEY" "$CASE_ID" "ai/runs/search-transfer-run" "${args[@]}" --upload
''']
try:
    r=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,check=True)
    (directory/(suffix+'.log')).write_text(r.stdout+r.stderr)
    ids=set(re.findall(r'\b[0-9a-f]{24}\b',r.stdout))
    if len(ids)!=1:raise RuntimeError('Ambiguous launch; inspect existing jobs before retry')
    record.update(stage='launched',job_id=ids.pop())
except BaseException as e:
    record.update(stage='launch_unknown',error=type(e).__name__+': '+str(e));raise
finally:path.write_text(json.dumps(record,indent=2)+'\n')
print(record)
