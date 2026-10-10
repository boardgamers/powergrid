"""Launch one frozen numerical-repair screen, preserving a no-duplicate intent."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import subprocess
from inference64_screen import ROOT, config, read, write, digest, PROTOCOL

p = argparse.ArgumentParser(__doc__)
p.add_argument('cohort', choices=['five-plant', 'population'])
p.add_argument('key')
a = p.parse_args()
config(a.cohort, a.key)
source = read(ROOT / f'ai/strong/inference64-screen-source-v1-{a.cohort}.json')
directory = ROOT / 'ai/runs/inference64-screen-launches-v1'
directory.mkdir(exist_ok=True)
name = a.cohort + '-' + a.key
path = directory / (name + '.json')
record = {'cohort': a.cohort, 'key': a.key, 'stage': 'launch_intent',
    'created_at': datetime.now(timezone.utc).isoformat(), 'protocol_sha256': digest(PROTOCOL),
    'source_revision': source['revision'], 'source_sha256': source['sha256']}
with path.open('x') as file:
    json.dump(record, file, indent=2)
command = ['hf', 'jobs', 'run', '--detach', '--flavor', 'cpu-performance', '--timeout', '4h',
    '--secrets', 'HF_TOKEN', '--label', 'project=powergrid-ai',
    '--label', 'stage=inference64-screen-v1-' + name]
for key, value in {'COHORT': a.cohort, 'SCREEN_KEY': a.key, 'SOURCE_ARCHIVE': source['archive'],
    'SOURCE_REVISION': source['revision'], 'SOURCE_SHA256': source['sha256'],
    'HF_HUB_DISABLE_PROGRESS_BARS': '1'}.items():
    command += ['--env', key + '=' + value]
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
python -m unittest discover -s ai/strong -p 'test_five_plant_screen.py'
python -u ai/strong/inference64_screen.py "$COHORT" "$SCREEN_KEY" "ai/runs/inference64-screen-v1-$COHORT-$SCREEN_KEY" --upload
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
    write(path, record)
print(json.dumps(record))
