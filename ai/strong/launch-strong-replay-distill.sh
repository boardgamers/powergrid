#!/usr/bin/env bash
set -euo pipefail
revision=${1:?Pin audited stronger-opponent dataset revision}
mode=${2:-hard}
[[ "$revision" =~ ^[0-9a-f]{40}$ ]]
[[ "$mode" == hard || "$mode" == soft ]]
hf jobs run --detach --flavor "${HF_FLAVOR:-a10g-large}" --timeout "${JOB_TIMEOUT:-4h}" \
  --secrets HF_TOKEN \
  --env HF_DATA_REPO=coyotte508/powergrid-ai-training-v1 \
  --env HF_MODEL_REPO=coyotte508/powergrid-ai-germany-v1 \
  --env RUN_NAME="${RUN_NAME:-multiplayer-distillation-strong-replay-v1-$mode}" --env TARGET_MODE="$mode" --env TRAIN_SEED=622 --env ARCHITECTURE=multiplayer_ordered --env DATA_REVISION="$revision" --env EPOCHS="${EPOCHS:-15}" --env LR="${LR:-0.00005}" --env DATA_VERSION="${DATA_VERSION:-multiplayer-teacher-v2-strong-repaired}" --env SHARDS=5 --env DISAGREEMENT_WEIGHT=2 \
  --env INIT_CHECKPOINT=runs/multiplayer-distillation-v2-hard/best.pt --env INIT_REVISION=ab34dd266010ded1c9a6c818c721e5505dd1ddeb \
  --env REPLAY_DATA_VERSION=multiplayer-teacher-v1 --env REPLAY_DATA_REVISION=082ca1456736940ee32c96db3ad1bc4e4d0b206b \
  --label project=powergrid-ai --label stage="multiplayer-distillation-strong-replay-$mode" \
  -- pytorch/pytorch:2.6.0-cuda12.4-cudnn9-runtime bash -lc '
set -euo pipefail
python -m pip install --quiet --timeout 120 --retries 5 huggingface_hub==2.0.0 onnx==1.20.1 onnxruntime==1.30.0
mkdir -p /workspace
python -c "import urllib.request,tarfile; urllib.request.urlretrieve(\"https://nodejs.org/dist/v24.14.0/node-v24.14.0-linux-x64.tar.xz\",\"/tmp/node.tar.xz\");tarfile.open(\"/tmp/node.tar.xz\").extractall(\"/opt\")"
export PATH=/opt/node-v24.14.0-linux-x64/bin:$PATH
python -c "from huggingface_hub import hf_hub_download;import tarfile;p=hf_hub_download(\"coyotte508/powergrid-ai-training-v1\",\"strong-source-v30.tgz\",repo_type=\"dataset\",revision=\"508bc42027cae5bfeea01228b48069c8287b332a\");tarfile.open(p).extractall(\"/workspace\")"
cd /workspace
node --test ai/test.cjs ai/strong/test.cjs
python ai/strong/test_teacher_contract.py
python ai/strong/test_model_v4.py
python ai/strong/test_distill_data.py
python ai/strong/audit-teacher-dataset.py --revision "$DATA_REVISION" --version "$DATA_VERSION" --output /tmp/strong-teacher-audit.json
python -u ai/strong/distill.py
'
