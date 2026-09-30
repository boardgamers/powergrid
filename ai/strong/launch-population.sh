#!/usr/bin/env bash
set -euo pipefail
hf jobs run --detach --flavor l4x4 --timeout 3h \
  --secrets HF_TOKEN \
  --env HF_MODEL_REPO=coyotte508/powergrid-ai-germany-v1 \
  --env RUN_NAME=strong-league-v1 --env UPDATES=300 --env EVAL_EVERY=20 \
  --env ENVS=128 --env WORKERS=8 --env BATCH_SIZE=512 --env ROLLOUT_SAMPLES=8000 \
  --label project=powergrid-ai --label stage=strong-league-v1 \
  -- pytorch/pytorch:2.6.0-cuda12.4-cudnn9-runtime bash -lc '
set -euo pipefail
python -m pip install --quiet huggingface_hub onnx
mkdir -p /workspace
python -c "import urllib.request,tarfile; urllib.request.urlretrieve(\"https://nodejs.org/dist/v24.14.0/node-v24.14.0-linux-x64.tar.xz\",\"/tmp/node.tar.xz\");tarfile.open(\"/tmp/node.tar.xz\").extractall(\"/opt\")"
export PATH=/opt/node-v24.14.0-linux-x64/bin:$PATH
python -c "from huggingface_hub import hf_hub_download;import tarfile;p=hf_hub_download(\"coyotte508/powergrid-ai-training-v1\",\"strong-source-v2.tgz\",repo_type=\"dataset\");tarfile.open(p).extractall(\"/workspace\")"
cd /workspace
node --test ai/test.cjs ai/strong/test.cjs
python -u ai/strong/population.py
'
