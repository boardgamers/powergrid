"""Launch both frozen inference conditions once; never retry an ambiguous POST."""
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]
source = json.loads((ROOT / 'ai/strong/sealed-menu-source-v1.json').read_text())
protocol = json.loads((ROOT / 'ai/strong/sealed-menu-protocol-v1.json').read_text())
file = ROOT / 'ai/runs/sealed-menu-pair-launch-v1.json'
record = {'stage': 'launch_intent', 'created_at': datetime.now(timezone.utc).isoformat(),
          'source_revision': source['revision'], 'source_sha256': source['sha256'],
          'conditions': ['control', 'expanded'], 'games': 15040, 'trained': False}
with file.open('x') as stream:
    json.dump(record, stream, indent=2)
command = ['hf', 'jobs', 'run', '--detach', '--flavor', protocol['execution']['flavor'],
           '--timeout', protocol['execution']['timeout'], '--secrets', 'HF_TOKEN',
           '--label', 'project=powergrid-ai', '--label', 'stage=sealed-menu-pair-v1']
for k, v in {'SOURCE_ARCHIVE': source['archive'], 'SOURCE_REVISION': source['revision'],
             'SOURCE_SHA256': source['sha256'], 'HF_HUB_DISABLE_PROGRESS_BARS': '1'}.items():
    command += ['--env', k + '=' + v]
command += ['--', 'pytorch/pytorch:2.6.0-cuda12.4-cudnn9-runtime', 'bash', '-lc', '''
set -euo pipefail
python -m pip install --quiet --timeout 120 --retries 5 huggingface_hub==2.0.0 onnxruntime==1.30.0 numpy==2.4.6
mkdir -p /workspace
python - <<'PY'
import urllib.request, tarfile, os, hashlib
from pathlib import Path
from huggingface_hub import hf_hub_download
urllib.request.urlretrieve("https://nodejs.org/dist/v24.14.0/node-v24.14.0-linux-x64.tar.xz", "/tmp/node.tar.xz")
with tarfile.open("/tmp/node.tar.xz") as t: t.extractall("/opt")
p=hf_hub_download("coyotte508/powergrid-ai-training-v1",os.environ["SOURCE_ARCHIVE"],repo_type="dataset",revision=os.environ["SOURCE_REVISION"])
assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==os.environ["SOURCE_SHA256"]
with tarfile.open(p) as t: t.extractall("/workspace")
PY
export PATH=/opt/node-v24.14.0-linux-x64/bin:$PATH
cd /workspace
python -u ai/strong/run-sealed-menu-pair.py
''']
try:
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=True)
    (ROOT / 'ai/runs/sealed-menu-pair-launch-v1.log').write_text(result.stdout + result.stderr)
    ids = set(re.findall(r'\b[0-9a-f]{24}\b', result.stdout))
    if len(ids) != 1: raise ValueError('Ambiguous launch response; reconcile before retry')
    record.update(stage='launched', job_id=ids.pop())
except BaseException as error:
    record.update(stage='launch_unknown', error=type(error).__name__ + ': ' + str(error))
    raise
finally:
    file.write_text(json.dumps(record, indent=2) + '\n')
    (ROOT / 'ai/strong/sealed-menu-status-v1.json').write_text(json.dumps(record, indent=2) + '\n')
print(json.dumps(record))
