#!/usr/bin/env bash
# Orchestrates only the frozen development screen; no optimizer runs here.
set -euo pipefail
: "${SOURCE_ARCHIVE:?Pin archive}"
: "${SOURCE_REVISION:?Pin immutable revision}"
: "${SOURCE_SHA256:?Pin SHA256}"
hf jobs run --detach --flavor cpu-basic --timeout 12h \
  --secrets HF_TOKEN \
  --env SOURCE_ARCHIVE="$SOURCE_ARCHIVE" --env SOURCE_REVISION="$SOURCE_REVISION" \
  --env SOURCE_SHA256="$SOURCE_SHA256" --env OMP_NUM_THREADS=1 --env MKL_NUM_THREADS=1 \
  --label project=powergrid-ai --label stage=population-coordinator-v1 \
  -- pytorch/pytorch:2.6.0-cuda12.4-cudnn9-runtime bash -lc '
set -euo pipefail
python -m pip install --quiet --timeout 120 --retries 5 huggingface_hub==2.0.0 onnxruntime==1.30.0 numpy==2.4.6
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
PY
export PATH=/opt/node-v24.14.0-linux-x64/bin:$PATH
cd /workspace
python -m unittest discover -s ai/strong -p test_population_coordinator.py -v
python -u ai/strong/population-coordinator.py
'
