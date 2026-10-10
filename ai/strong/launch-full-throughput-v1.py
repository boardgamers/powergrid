"""Launch one frozen, complete-update throughput probe on HF Jobs."""
import argparse
import json
from pathlib import Path
import subprocess

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('flavor', choices=['cpu-performance', 'h200'])
a = p.parse_args()
root = Path(__file__).resolve().parents[2]
protocol = json.loads((root / 'ai/strong/full-throughput-protocol-v1.json').read_text())
source = json.loads((root / 'ai/strong/full-throughput-source-v1.json').read_text())
env = {**protocol['common_env'], **protocol['platforms'][a.flavor]['env'],
    'POWERGRID_BENCHMARK_PLATFORM': 'hf-job', 'BENCHMARK_FLAVOR': a.flavor,
    'SOURCE_ARCHIVE': source['archive'], 'SOURCE_REVISION': source['revision'],
    'SOURCE_SHA256': source['sha256']}
command = ['hf', 'jobs', 'run', '--detach', '--flavor', a.flavor, '--timeout', '3h', '--secrets', 'HF_TOKEN',
    '--label', 'project=powergrid-ai', '--label', 'stage=full-throughput-v1-' + a.flavor]
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
python -u ai/strong/benchmark-full-training.py
''']
subprocess.run(command, cwd=root, check=True)
