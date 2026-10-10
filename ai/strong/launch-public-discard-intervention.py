"""Launch one pinned complete-game discard intervention arm; never duplicate a launch intent."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]
p = argparse.ArgumentParser(__doc__)
p.add_argument('arm', choices=['parent', 'economic', 'neural'])
a = p.parse_args()
source = json.loads((ROOT / 'ai/strong/public-discard-intervention-source-v1.json').read_text())
protocol = ROOT / 'ai/strong/public-discard-intervention-protocol-v1.json'
protocol_sha = hashlib.sha256(protocol.read_bytes()).hexdigest()
assert protocol_sha == source['protocol_sha256']
directory = ROOT / 'ai/runs/public-discard-intervention-launches-v1'
directory.mkdir(exist_ok=True)
name = a.arm
path = directory / (name + '.json')
record = {'arm': a.arm, 'stage': 'launch_intent',
    'created_at': datetime.now(timezone.utc).isoformat(), 'protocol_sha256': protocol_sha,
    'source_revision': source['revision'], 'source_sha256': source['sha256'],
    'qualification_eligible': False}
with path.open('x') as file:
    json.dump(record, file, indent=2)
command = ['hf', 'jobs', 'run', '--detach', '--flavor', 'cpu-performance', '--timeout', '4h',
    '--secrets', 'HF_TOKEN', '--label', 'project=powergrid-ai',
    '--label', 'stage=public-discard-intervention-v1-' + name]
for key, value in {'ARM': a.arm, 'SOURCE_ARCHIVE': source['archive'],
    'SOURCE_REVISION': source['revision'], 'SOURCE_SHA256': source['sha256'],
    'HF_HUB_DISABLE_PROGRESS_BARS': '1'}.items():
    command += ['--env', key + '=' + value]
command += ['--', 'pytorch/pytorch:2.6.0-cuda12.4-cudnn9-runtime', 'bash', '-lc', '''
set -euo pipefail
python -m pip install --quiet --timeout 120 --retries 5 huggingface_hub==2.0.0 onnxruntime==1.30.0 numpy==2.4.6
mkdir -p /workspace
python - <<'PY'
import urllib.request,tarfile,os,hashlib
from pathlib import Path
from huggingface_hub import hf_hub_download
urllib.request.urlretrieve("https://nodejs.org/dist/v24.14.0/node-v24.14.0-linux-x64.tar.xz","/tmp/node.tar.xz")
with tarfile.open("/tmp/node.tar.xz") as file:file.extractall("/opt")
p=hf_hub_download("coyotte508/powergrid-ai-training-v1",os.environ['SOURCE_ARCHIVE'],repo_type='dataset',revision=os.environ['SOURCE_REVISION'])
assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==os.environ['SOURCE_SHA256']
with tarfile.open(p) as file:file.extractall('/workspace')
PY
export PATH=/opt/node-v24.14.0-linux-x64/bin:$PATH
cd /workspace
node --test ai/strong/test-continuation-rollouts.cjs
python -u ai/strong/public-discard-intervention.py "$ARM" "ai/runs/public-discard-intervention-v1-${ARM}" --upload
''']
try:
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=True)
    (directory / (name + '.launch.log')).write_text(result.stdout + result.stderr)
    ids = set(re.findall(r'\b[0-9a-f]{24}\b', result.stdout))
    if len(ids) != 1:
        raise ValueError('Ambiguous launch response; inspect actual jobs before retrying')
    record.update(stage='launched', job_id=ids.pop())
except BaseException as error:
    record.update(stage='launch_unknown', error=type(error).__name__ + ': ' + str(error))
    raise
finally:
    path.write_text(json.dumps(record, indent=2) + '\n')
print(json.dumps(record))
