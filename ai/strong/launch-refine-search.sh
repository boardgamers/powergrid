#!/usr/bin/env bash
set -euo pipefail
hf jobs run --detach --flavor h200 --timeout 4h \
  --secrets HF_TOKEN \
  --env HF_MODEL_REPO=coyotte508/powergrid-ai-germany-v1 \
  --env INIT_CHECKPOINT=runs/search-distillation-v3-soft/best.pt --env INIT_REVISION=45a839c001fce2fe3dd9b1f5c7a523db8ceee890 --env ANCHOR_POLICY=initial --env OPPONENT_MODE=mixed_search --env STRATEGIC_ONLY=1 \
  --env RUN_NAME=strong-refine-v1-search --env TRAIN_SEED=411 --env LR=.00005 --env ENTROPY=.005 --env ANCHOR=.05 --env UPDATES=80 --env EVAL_EVERY=10 \
  --env ENVS=128 --env WORKERS=20 --env BATCH_SIZE=512 \
  --label project=powergrid-ai --label stage=strong-refine-v1-search \
  -- pytorch/pytorch:2.6.0-cuda12.4-cudnn9-runtime bash -lc '
set -euo pipefail
python -m pip install --quiet huggingface_hub onnx
mkdir -p /workspace
python -c "import urllib.request,tarfile; urllib.request.urlretrieve(\"https://nodejs.org/dist/v24.14.0/node-v24.14.0-linux-x64.tar.xz\",\"/tmp/node.tar.xz\");tarfile.open(\"/tmp/node.tar.xz\").extractall(\"/opt\")"
export PATH=/opt/node-v24.14.0-linux-x64/bin:$PATH
python -c "from huggingface_hub import hf_hub_download;import tarfile;p=hf_hub_download(\"coyotte508/powergrid-ai-training-v1\",\"strong-source-v10.tgz\",repo_type=\"dataset\");tarfile.open(p).extractall(\"/workspace\")"
cd /workspace
node --test ai/test.cjs ai/strong/test.cjs
python -u ai/strong/train.py
'
