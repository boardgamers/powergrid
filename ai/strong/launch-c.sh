#!/usr/bin/env bash
set -euo pipefail
hf jobs run --detach --flavor h200 --timeout 3h \
  --secrets HF_TOKEN \
  --env HF_MODEL_REPO=coyotte508/powergrid-ai-germany-v1 \
  --env RUN_NAME=strong-league-v2-c --env TRAIN_SEED=203 --env LR=.0001 --env ENTROPY=.025 --env ANCHOR=.003 --env UPDATES=300 --env EVAL_EVERY=20 \
  --env ENVS=128 --env WORKERS=12 --env BATCH_SIZE=512 --env ROLLOUT_SAMPLES=8000 \
  --label project=powergrid-ai --label stage=strong-league-v2-c \
  -- pytorch/pytorch:2.6.0-cuda12.4-cudnn9-runtime bash -lc '
set -euo pipefail
python -m pip install --quiet huggingface_hub onnx
mkdir -p /workspace
python -c "import urllib.request,tarfile; urllib.request.urlretrieve(\"https://nodejs.org/dist/v24.14.0/node-v24.14.0-linux-x64.tar.xz\",\"/tmp/node.tar.xz\");tarfile.open(\"/tmp/node.tar.xz\").extractall(\"/opt\")"
export PATH=/opt/node-v24.14.0-linux-x64/bin:$PATH
python -c "from huggingface_hub import hf_hub_download;import tarfile;p=hf_hub_download(\"coyotte508/powergrid-ai-training-v1\",\"strong-source-v3.tgz\",repo_type=\"dataset\");tarfile.open(p).extractall(\"/workspace\")"
cd /workspace
node --test ai/test.cjs ai/strong/test.cjs
python -u ai/strong/train.py
'
