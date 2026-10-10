"""Single-run launcher: only protocol-listed keys; persistent intent prevents duplicates."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import subprocess

root = Path(__file__).resolve().parents[2]
p = argparse.ArgumentParser(__doc__)
p.add_argument('key')
args = p.parse_args()
protocol = json.loads((root / 'ai/strong/five-plant-ablation-protocol-v1.json').read_text())
if args.key not in protocol['runs']:
    p.error('Unknown experiment key')
source = json.loads((root / 'ai/strong/five-plant-ablation-source-v1.json').read_text())
directory = root / 'ai/runs/five-plant-ablation-launches-v1'
directory.mkdir(exist_ok=True)
record_file = directory / (args.key + '.json')
record = {'key': args.key, 'stage': 'launch_intent', 'created_at': datetime.now(timezone.utc).isoformat(),
          'source_revision': source['revision'], 'source_sha256': source['sha256']}
# An existing intent can be an ambiguous successful POST. Inspect/reconcile it;
# never retry just because a client timed out or failed parsing stdout.
with record_file.open('x') as file:
    json.dump(record, file, indent=2)
env = {**protocol['common_env'], **protocol['runs'][args.key]['env'],
       'POWERGRID_TRAINING_PLATFORM': 'hf-job', 'ABLATION_KEY': args.key,
       'SOURCE_ARCHIVE': source['archive'], 'SOURCE_REVISION': source['revision'], 'SOURCE_SHA256': source['sha256']}
command = ['hf', 'jobs', 'run', '--detach', '--flavor', 'h200', '--timeout', '6h', '--secrets', 'HF_TOKEN',
           '--label', 'project=powergrid-ai', '--label', 'stage=five-plant-ablation-v1-' + args.key]
for key, value in env.items():
    command += ['--env', key + '=' + value]
command += ['--', 'pytorch/pytorch:2.6.0-cuda12.4-cudnn9-runtime', 'bash', '-lc', '''
set -euo pipefail
python -m pip install --quiet --timeout 120 --retries 5 huggingface_hub==2.0.0 onnx==1.20.1 onnxruntime==1.30.0 numpy==2.4.6
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
python -m unittest discover -s ai/strong -p 'test_model_v4*.py'
node --test ai/strong/test-opponent-population.cjs
python -u ai/strong/run-five-plant-ablation.py
''']
try:
    result = subprocess.run(command, cwd=root, text=True, capture_output=True, check=True)
    (directory / (args.key + '.launch.log')).write_text(result.stdout + result.stderr)
    ids = set(re.findall(r'\b[0-9a-f]{24}\b', result.stdout))
    if len(ids) != 1:
        raise ValueError('Ambiguous launch output; reconcile intent before retrying')
    record.update(stage='launched', job_id=ids.pop())
except BaseException as error:
    record.update(stage='launch_unknown', error=type(error).__name__ + ': ' + str(error))
    raise
finally:
    record_file.write_text(json.dumps(record, indent=2) + '\n')
print(json.dumps(record))
