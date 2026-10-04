#!/usr/bin/env bash
set -euo pipefail
hf jobs run --detach --flavor a10g-large --timeout 4h \
  --secrets HF_TOKEN \
  --env HF_MODEL_REPO=coyotte508/powergrid-ai-germany-v1 \
  --env INIT_CHECKPOINT=runs/strong-league-v2-a/best.pt --env INIT_REVISION=b38515c29e57826de05b55b645c29591e4a886bf --env ANCHOR_POLICY=initial --env ALLOW_URANIUM39_TRANSFER=1 \
  --env RUN_NAME=strong-refine-a260-v1 --env TRAIN_SEED=412 --env LR=.00005 --env ENTROPY=.005 --env ANCHOR=.03 --env UPDATES=80 --env EVAL_EVERY=10 \
  --env ENVS=128 --env WORKERS=8 --env BATCH_SIZE=512 \
  --label project=powergrid-ai --label stage=strong-refine-a260-v1 \
  -- pytorch/pytorch:2.6.0-cuda12.4-cudnn9-runtime bash -lc '
set -euo pipefail
python -m pip install --quiet huggingface_hub onnx
mkdir -p /workspace
python -c "import urllib.request,tarfile; urllib.request.urlretrieve(\"https://nodejs.org/dist/v24.14.0/node-v24.14.0-linux-x64.tar.xz\",\"/tmp/node.tar.xz\");tarfile.open(\"/tmp/node.tar.xz\").extractall(\"/opt\")"
export PATH=/opt/node-v24.14.0-linux-x64/bin:$PATH
python -c "from huggingface_hub import hf_hub_download;import tarfile;p=hf_hub_download(\"coyotte508/powergrid-ai-training-v1\",\"strong-source-v12.tgz\",repo_type=\"dataset\");tarfile.open(p).extractall(\"/workspace\")"
cd /workspace
node --test ai/test.cjs ai/strong/test.cjs
python -u ai/strong/train.py
'
