#!/usr/bin/env bash
set -euo pipefail
hf jobs run --detach --flavor a10g-large --timeout 3h \
  --secrets HF_TOKEN \
  --env HF_MODEL_REPO=coyotte508/powergrid-ai-germany-v1 \
  --env RUN_NAME=multiplayer-pipeline-v1 --env TRAIN_SEED=621 --env LR=.00005 --env ENTROPY=.005 --env ANCHOR=.03 --env UPDATES=10 --env EVAL_EVERY=5 --env ARCHITECTURE=multiplayer --env OPPONENT_MODE=mixed_search \
  --env ENVS=120 --env WORKERS=10 --env BATCH_SIZE=512 \
  --label project=powergrid-ai --label stage=multiplayer-pipeline-v1 \
  -- pytorch/pytorch:2.6.0-cuda12.4-cudnn9-runtime bash -lc '
set -euo pipefail
python -m pip install --quiet --timeout 120 --retries 5 huggingface_hub==2.0.0 onnx==1.20.1
mkdir -p /workspace
python -c "import urllib.request,tarfile; urllib.request.urlretrieve(\"https://nodejs.org/dist/v24.14.0/node-v24.14.0-linux-x64.tar.xz\",\"/tmp/node.tar.xz\");tarfile.open(\"/tmp/node.tar.xz\").extractall(\"/opt\")"
export PATH=/opt/node-v24.14.0-linux-x64/bin:$PATH
python -c "from huggingface_hub import hf_hub_download;import tarfile;p=hf_hub_download(\"coyotte508/powergrid-ai-training-v1\",\"strong-source-v16.tgz\",repo_type=\"dataset\",revision=\"6064b1683379153e0a5dbca24903d41a972cbe0a\");tarfile.open(p).extractall(\"/workspace\")"
cd /workspace
node --test ai/test.cjs ai/strong/test.cjs ai/strong/test-v4.cjs
python ai/strong/test_model_v4.py
python ai/strong/test_multiplayer_bridge.py
python -u ai/strong/train.py
'
