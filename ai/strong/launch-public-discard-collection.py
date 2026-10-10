"""Launch the frozen, outcome-unfiltered public-discard collection on HF Jobs."""
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import subprocess
from five_plant_screen import ROOT, read, write, digest

source = read(ROOT / 'ai/strong/public-discard-source-v1.json')
protocol = ROOT / 'ai/strong/public-discard-collection-protocol-v1.json'
out = ROOT / 'ai/runs/public-discard-collection-launch-v1'
out.mkdir(exist_ok=False)
record = {'stage': 'launch_intent', 'created_at': datetime.now(timezone.utc).isoformat(),
    'protocol_sha256': digest(protocol), 'source_revision': source['revision'],
    'source_sha256': source['sha256'], 'qualification_eligible': False}
write(out / 'intent.json', record)
command = ['hf', 'jobs', 'run', '--detach', '--flavor', 'cpu-performance', '--timeout', '2h',
    '--secrets', 'HF_TOKEN', '--label', 'project=powergrid-ai', '--label', 'stage=public-discard-collection-v1']
for k, v in {'SOURCE_ARCHIVE': source['archive'], 'SOURCE_REVISION': source['revision'],
             'SOURCE_SHA256': source['sha256'], 'HF_HUB_DISABLE_PROGRESS_BARS': '1'}.items():
    command += ['--env', k + '=' + v]
command += ['--', 'pytorch/pytorch:2.6.0-cuda12.4-cudnn9-runtime', 'bash', '-lc', '''
set -euo pipefail
python -m pip install --quiet --timeout 120 --retries 5 huggingface_hub==2.0.0 onnxruntime==1.30.0 numpy==2.4.6
mkdir -p /workspace
python - <<'PY'
import urllib.request,tarfile,os,hashlib,json
from pathlib import Path
from huggingface_hub import hf_hub_download
urllib.request.urlretrieve("https://nodejs.org/dist/v24.14.0/node-v24.14.0-linux-x64.tar.xz","/tmp/node.tar.xz")
with tarfile.open("/tmp/node.tar.xz") as file:file.extractall("/opt")
p=hf_hub_download("coyotte508/powergrid-ai-training-v1",os.environ['SOURCE_ARCHIVE'],repo_type='dataset',revision=os.environ['SOURCE_REVISION'])
assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==os.environ['SOURCE_SHA256']
with tarfile.open(p) as file:file.extractall('/workspace')
protocol=json.loads(Path('/workspace/ai/strong/public-discard-collection-protocol-v1.json').read_text())
pin=protocol['model'];model=Path(hf_hub_download(protocol['repo'],pin['path'],revision=pin['revision']))
assert hashlib.sha256(model.read_bytes()).hexdigest()==pin['sha256']
Path('/workspace/ai/runs').mkdir(exist_ok=True)
Path('/workspace/ai/runs/discard-parent.onnx').write_bytes(model.read_bytes())
PY
export PATH=/opt/node-v24.14.0-linux-x64/bin:$PATH
cd /workspace
node --test ai/strong/test-capture-public-discard.cjs
python -u ai/strong/collect-public-discards.py ai/runs/discard-parent.onnx ai/runs/public-discard-collection-v1 --upload
''']
try:
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=True)
    (out / 'launch.log').write_text(result.stdout + result.stderr)
    ids = set(re.findall(r'\b[0-9a-f]{24}\b', result.stdout))
    if len(ids) != 1:
        raise ValueError('Ambiguous launch result: inspect actual jobs before any retry')
    record.update(stage='launched', job_id=ids.pop())
except BaseException as error:
    record.update(stage='launch_unknown', error=type(error).__name__ + ': ' + str(error))
    raise
finally:
    write(out / 'intent.json', record)
write(ROOT / 'ai/strong/public-discard-collection-status-v1.json', record)
print(json.dumps(record))
