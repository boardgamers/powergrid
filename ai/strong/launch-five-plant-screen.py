"""Launch one pinned development evaluation with a persistent no-duplicate intent."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]
p = argparse.ArgumentParser(__doc__)
p.add_argument('key')
p.add_argument('revision')
a = p.parse_args()
protocol = json.loads((ROOT / 'ai/strong/five-plant-ablation-protocol-v1.json').read_text())
assert a.key in ['parent', *protocol['runs']]
assert re.fullmatch('[0-9a-f]{40}', a.revision)
if a.key == 'parent':
    assert a.revision == protocol['initial']['validation']['parent_revision']
source = json.loads((ROOT / 'ai/strong/five-plant-screen-source-v1.json').read_text())
directory = ROOT / 'ai/runs/five-plant-screen-launches-v1'
directory.mkdir(exist_ok=True)
path = directory / (a.key + '.json')
record = {'key': a.key, 'model_revision': a.revision, 'stage': 'launch_intent',
          'created_at': datetime.now(timezone.utc).isoformat(),
          'source_revision': source['revision'], 'source_sha256': source['sha256']}
with path.open('x') as file:
    json.dump(record, file, indent=2)
command = ['hf', 'jobs', 'run', '--detach', '--flavor', 'cpu-performance', '--timeout', '3h',
           '--secrets', 'HF_TOKEN', '--label', 'project=powergrid-ai',
           '--label', 'stage=five-plant-screen-v1-' + a.key]
for k, v in {'SCREEN_KEY': a.key, 'MODEL_REVISION': a.revision,
             'SOURCE_ARCHIVE': source['archive'], 'SOURCE_REVISION': source['revision'],
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
python -m unittest discover -s ai/strong -p 'test_five_plant_screen.py'
python -u ai/strong/five_plant_screen.py "$SCREEN_KEY" "$MODEL_REVISION" "ai/runs/five-plant-screen-v1-$SCREEN_KEY" --upload
''']
try:
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=True)
    (directory / (a.key + '.launch.log')).write_text(result.stdout + result.stderr)
    ids = set(re.findall(r'\b[0-9a-f]{24}\b', result.stdout))
    if len(ids) != 1:
        raise ValueError('Ambiguous launch response; reconcile before any retry')
    record.update(stage='launched', job_id=ids.pop())
except BaseException as error:
    record.update(stage='launch_unknown', error=type(error).__name__ + ': ' + str(error))
    raise
finally:
    path.write_text(json.dumps(record, indent=2) + '\n')
print(json.dumps(record))
