#!/usr/bin/env bash
set -euo pipefail
revision=${1:?Pin completed dataset revision}
mode=${2:-soft}
[[ "$mode" == hard || "$mode" == soft ]]
hf jobs run --detach --flavor a10g-large --timeout 3h \
  --secrets HF_TOKEN \
  --env HF_DATA_REPO=coyotte508/powergrid-ai-training-v1 \
  --env HF_MODEL_REPO=coyotte508/powergrid-ai-germany-v1 \
  --env RUN_NAME="multiplayer-distillation-v1-$mode" --env TARGET_MODE="$mode" --env TRAIN_SEED=622 --env ARCHITECTURE=multiplayer --env DATA_REVISION="$revision" --env EPOCHS=20 --env DATA_VERSION=multiplayer-teacher-v1 --env SHARDS=5 --env DISAGREEMENT_WEIGHT=2 \
  --label project=powergrid-ai --label stage="multiplayer-distillation-v1-$mode" \
  -- pytorch/pytorch:2.6.0-cuda12.4-cudnn9-runtime bash -lc '
set -euo pipefail
python -m pip install --quiet --timeout 120 --retries 5 huggingface_hub==2.0.0 onnx==1.20.1 onnxruntime==1.30.0
mkdir -p /workspace
python -c "import urllib.request,tarfile; urllib.request.urlretrieve(\"https://nodejs.org/dist/v24.14.0/node-v24.14.0-linux-x64.tar.xz\",\"/tmp/node.tar.xz\");tarfile.open(\"/tmp/node.tar.xz\").extractall(\"/opt\")"
export PATH=/opt/node-v24.14.0-linux-x64/bin:$PATH
python -c "from huggingface_hub import hf_hub_download;import tarfile;p=hf_hub_download(\"coyotte508/powergrid-ai-training-v1\",\"strong-source-v18.tgz\",repo_type=\"dataset\",revision=\"49cc1bb94678e6ede37b606ae1ce9a8cb2018c1d\");tarfile.open(p).extractall(\"/workspace\")"
cd /workspace
node --test ai/test.cjs ai/strong/test.cjs
python ai/strong/test_teacher_contract.py
python ai/strong/test_model_v4.py
python -u ai/strong/distill.py
'
