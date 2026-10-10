#!/usr/bin/env bash
# Frozen-policy audit only. Training/final qualification are separate experiments.
set -euo pipefail
players=${1:?Specify player count 2-6}
[[ "$players" =~ ^[2-6]$ ]]
: "${SOURCE_ARCHIVE:?Pin source archive}"
: "${SOURCE_REVISION:?Pin source revision}"
: "${SOURCE_SHA256:?Pin source hash}"
hf jobs run --detach --flavor cpu-performance --timeout 2h \
  --secrets HF_TOKEN --env PLAYER_COUNT="$players" \
  --env SOURCE_ARCHIVE="$SOURCE_ARCHIVE" --env SOURCE_REVISION="$SOURCE_REVISION" \
  --env SOURCE_SHA256="$SOURCE_SHA256" \
  --label project=powergrid-ai --label stage="neural-continuation-v1-${players}p" \
  -- pytorch/pytorch:2.6.0-cuda12.4-cudnn9-runtime bash -lc '
set -euo pipefail
python -m pip install --quiet --timeout 120 --retries 5 huggingface_hub==2.0.0 numpy==2.4.6 onnxruntime==1.30.0
mkdir -p /workspace
python - <<"PY"
import urllib.request, tarfile, os, hashlib
from pathlib import Path
from huggingface_hub import hf_hub_download
urllib.request.urlretrieve("https://nodejs.org/dist/v24.14.0/node-v24.14.0-linux-x64.tar.xz", "/tmp/node.tar.xz")
with tarfile.open("/tmp/node.tar.xz") as t: t.extractall("/opt")
p=hf_hub_download("coyotte508/powergrid-ai-training-v1",os.environ["SOURCE_ARCHIVE"],repo_type="dataset",revision=os.environ["SOURCE_REVISION"])
assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==os.environ["SOURCE_SHA256"]
with tarfile.open(p) as t: t.extractall("/workspace")
p=hf_hub_download("coyotte508/powergrid-ai-germany-v1","runs/multiplayer-refine-hard-v1/latest.onnx",revision="fbdf2bf24c968bff99ab2d7d9ff9a7d97047db2b")
Path("/workspace/frozen.onnx").write_bytes(Path(p).read_bytes())
PY
export PATH=/opt/node-v24.14.0-linux-x64/bin:$PATH
cd /workspace
node --test ai/strong/test-continuation-rollouts.cjs
python -u ai/strong/audit-neural-continuations.py frozen.onnx \
  --fixtures ai/strong/fixtures/teacher-reliability-v1.jsonl \
  --players "$PLAYER_COUNT" --samples 48 --workers 24 --threads 4 \
  --model-revision fbdf2bf24c968bff99ab2d7d9ff9a7d97047db2b \
  --expected-model-sha256 d3d2ee88a0940f079a4b38879c8154dbab55951abc7b295a7db17bdf22e52c5f \
  --output "results-${PLAYER_COUNT}p.jsonl" \
  --upload-repo coyotte508/powergrid-ai-germany-v1
'
