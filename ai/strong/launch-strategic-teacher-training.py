"""First-wave HF labels, admitted from verified matching runtime probes."""
import argparse
from collections import defaultdict
from datetime import datetime,timezone
import json
import math
from pathlib import Path
import re
import subprocess
from huggingface_hub import HfApi
from strategic_collection import ROOT,read,write,digest

def admission(n,mode,p):
    source=read(ROOT/'ai/strong/strategic-teacher-probe-source-v1.json')
    out=ROOT/f'ai/runs/strategic-teacher-probe-verified-v1/{n}p-{mode}';v=read(out/'verified.json')
    assert v['verified'] and v['source_revision']==source['revision'] and v['source_sha256']==source['sha256']
    assert v['protocol_sha256']==source['protocol_sha256'] and v['summary']['players']==n and v['summary']['mode']==mode
    for name,sha in v['artifacts'].items():assert Path(name).name==name and digest(out/name)==sha
    rows=[json.loads(line) for line in (out/'rollouts.jsonl').read_text().splitlines()]
    seconds=defaultdict(float)
    for r in rows:
        assert r['usable'] and r['samples']==2 and r['mode']==mode
        seconds[r['rootId']]+=r['timing']['seconds']
    assert len(rows)==4 and len(seconds)==2
    worst=max(seconds.values());assert math.isfinite(worst) and worst>0
    projected=120+2*worst*p['samples']/2*p['roots_per_initial_shard']
    hours=max(4,math.ceil(projected/(.75*3600)))
    return {'probe_revision':v['revision'],'probe_verified_sha256':digest(out/'verified.json'),
        'worst_probe_root_seconds':worst,'projected_seconds':projected,'timeout_hours':hours,'admitted':hours<=12,
        'scope':'Conservative linear projection, not a guarantee; first24 roots must finish before admitting remaining chunks.'}

def main():
    parser=argparse.ArgumentParser(__doc__);parser.add_argument('players',type=int,choices=range(2,7))
    parser.add_argument('source_mode',choices=['economic','snapshot0']);parser.add_argument('mode',choices=['neural','neural_economic'])
    parser.add_argument('--retry-image-pull',action='store_true')
    a=parser.parse_args();source=read(ROOT/'ai/strong/strategic-teacher-training-source-v1.json')
    protocol=ROOT/'ai/strong/strategic-teacher-training-protocol-v1.json';p=read(protocol)
    assert digest(protocol)==source['protocol_sha256'];roots=read(ROOT/'ai/strong/strategic-teacher-training-roots-v1.json')
    for name,sha in source['overlays'].items():
        path=ROOT/(roots['local_file'] if name==roots['file'] else name);assert digest(path)==sha
    check=read(ROOT/'ai/strong/strategic-teacher-training-preflight-v1.json')
    assert check['passed'] and check['source_sha256']==source['sha256']
    runtime=admission(a.players,a.mode,p);assert runtime['admitted'],'Split first wave; do not lower horizons or sample count'
    guards=ROOT/'ai/runs/strategic-teacher-training-launches-v1';guards.mkdir(exist_ok=True)
    key=f'{a.players}p-{a.source_mode}-{a.mode}-0-2';guard=guards/(key+'.json');retry={}
    image='pytorch/pytorch:2.6.0-cuda12.4-cudnn9-runtime'
    if a.retry_image_pull:
        old=read(guard);api=HfApi();status=api.inspect_job(job_id=old['job_id']).status
        assert status.stage=='ERROR' and 'ErrImagePull' in status.message and 'timeout awaiting response headers' in status.message
        assert not api.file_exists(repo_id=p['repo'],filename='runs/strategic-teacher-training-v1-'+key+'/label-check.json'), 'Existing result: inspect instead of replacing'
        retry={'retry_of_job_id':old['job_id'],'original_status':'ERROR',
            'reason':'Image pull timed out before program execution; authoritative terminal state confirmed.',
            'serving_parity_prefix':'runs/strategic-teacher-training-retry-v1/'+key}
        guard=guards/(key+'.retry-image-pull-1.json');image='python:3.11-slim-bookworm'
    record={'stage':'launch_intent','created_at':datetime.now(timezone.utc).isoformat(),'players':a.players,
        'source_mode':a.source_mode,'mode':a.mode,'deal_start':0,'deal_end':2,
        'source_revision':source['revision'],'source_sha256':source['sha256'],'protocol_sha256':digest(protocol),
        'runtime_admission':runtime,'timeout_hours':runtime['timeout_hours'],'image':image,**retry,'qualification_eligible':False}
    with guard.open('x') as f:json.dump(record,f,indent=2)
    command=['hf','jobs','run','--detach','--flavor','cpu-performance','--timeout',str(runtime['timeout_hours'])+'h',
        '--secrets','HF_TOKEN','--label','project=powergrid-ai','--label','stage=strategic-teacher-training-v1-'+key]
    for k,v in {'PLAYERS':str(a.players),'SOURCE_MODE':a.source_mode,'MODE':a.mode,'SOURCE_ARCHIVE':source['archive'],
        'SOURCE_REVISION':source['revision'],'SOURCE_SHA256':source['sha256'],'HF_HUB_DISABLE_PROGRESS_BARS':'1',
        'CPU_IMAGE_RETRY':'1' if a.retry_image_pull else '0','RUN_KEY':key}.items():command+=['--env',k+'='+v]
    command+=['--',image,'bash','-lc','''
set -euo pipefail
if [ "$CPU_IMAGE_RETRY" = 1 ]; then
  apt-get update -qq
  apt-get install -y --no-install-recommends libstdc++6 libgomp1 ca-certificates >/dev/null
fi
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
if [ "$CPU_IMAGE_RETRY" = 1 ]; then
  mkdir -p ai/runs
  python ai/strong/check-strategic-teacher-batching.py --fixtures ai/strong/fixtures/multiplayer-serving-v1.jsonl --output ai/runs/retry-serving-parity-v1.json
  python - <<'PY'
import os,json,platform
from pathlib import Path
import onnxruntime,numpy
from huggingface_hub import HfApi
p=Path('ai/runs/retry-serving-parity-v1.json');r=json.loads(p.read_text())
r['runtime']={'python':platform.python_version(),'onnxruntime':onnxruntime.__version__,'numpy':numpy.__version__,'image':'python:3.11-slim-bookworm'}
p.write_text(json.dumps(r,indent=2)+'\\n')
HfApi().upload_file(repo_id='coyotte508/powergrid-ai-germany-v1',path_or_fileobj=p,
 path_in_repo='runs/strategic-teacher-training-retry-v1/'+os.environ['RUN_KEY']+'/serving-parity.json')
PY
fi
python -u ai/strong/strategic_training_labels.py "$PLAYERS" "$SOURCE_MODE" "$MODE" 0 2 ai/runs/strategic-teacher-labels --upload
''']
    try:
        result=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,check=True)
        guard.with_suffix('.log').write_text(result.stdout+result.stderr)
        ids=set(re.findall(r'\b[0-9a-f]{24}\b',result.stdout));assert len(ids)==1,'Ambiguous launch; reconcile exact existing label'
        record.update(stage='launched',job_id=ids.pop())
    except BaseException as e:record.update(stage='launch_unknown',error=type(e).__name__+': '+str(e));raise
    finally:write(guard,record)
    print(record,flush=True)

if __name__=='__main__':main()
