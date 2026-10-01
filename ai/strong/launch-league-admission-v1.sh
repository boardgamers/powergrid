#!/usr/bin/env bash
# Controlled league-admission comparison; optimization runs only on HF Jobs.
set -euo pipefail
checkpoint=${1:?Supply selected ordered-model checkpoint path}
revision=${2:?Pin its immutable model repository commit}
run=${3:?Supply a unique refinement run name}
[[ "$revision" =~ ^[0-9a-f]{40}$ ]]
[[ "$checkpoint" == runs/*/best.pt ]]
[[ "$run" =~ ^[a-zA-Z0-9_-]+$ ]]
admission=${SNAPSHOT_ADMISSION:?Choose best or periodic_anchor}
[[ "$admission" == best || "$admission" == periodic_anchor ]]
hf jobs run --detach --flavor "${HF_FLAVOR:-cpu-performance}" --timeout "${JOB_TIMEOUT:-8h}" \
  --secrets HF_TOKEN \
  --env HF_MODEL_REPO=coyotte508/powergrid-ai-germany-v1 \
  --env INIT_CHECKPOINT="$checkpoint" --env INIT_REVISION="$revision" --env ANCHOR_POLICY=initial \
  --env ARCHITECTURE=multiplayer_ordered --env MIX_PLAYER_COUNTS=1 --env OPPONENT_MODE="${OPPONENT_MODE:-mixed_search_geo}" \
  --env RUN_NAME="$run" --env TRAIN_SEED="${TRAIN_SEED:-9021}" \
  --env ASYNC_ROLLOUT="${ASYNC_ROLLOUT:-1}" --env TRAIN_DEVICE="${TRAIN_DEVICE:-cpu}" --env TORCH_THREADS="${TORCH_THREADS:-4}" \
  --env SNAPSHOT_ADMISSION="$admission" --env SNAPSHOT_INTERVAL=5 \
  --env LR=.00005 --env ENTROPY=.005 --env ANCHOR=.03 \
  --env UPDATES="${UPDATES:-20}" --env EVAL_EVERY=10 \
  --env ENVS=240 --env WORKERS="${WORKERS:-240}" --env BATCH_SIZE=512 \
  --label project=powergrid-ai --label stage="$run" \
  -- pytorch/pytorch:2.6.0-cuda12.4-cudnn9-runtime bash -lc '
set -euo pipefail
python -m pip install --quiet --timeout 120 --retries 5 huggingface_hub==2.0.0 onnx==1.20.1 onnxruntime==1.30.0
mkdir -p /workspace
python -c "import urllib.request,tarfile; urllib.request.urlretrieve(\"https://nodejs.org/dist/v24.14.0/node-v24.14.0-linux-x64.tar.xz\",\"/tmp/node.tar.xz\");tarfile.open(\"/tmp/node.tar.xz\").extractall(\"/opt\")"
export PATH=/opt/node-v24.14.0-linux-x64/bin:$PATH
python -c "from huggingface_hub import hf_hub_download;import tarfile;p=hf_hub_download(\"coyotte508/powergrid-ai-training-v1\",\"strong-source-v34.tgz\",repo_type=\"dataset\",revision=\"2c273f96562d0cc2f8c05a2735d8c0492ab77fd8\");tarfile.open(p).extractall(\"/workspace\")"
cd /workspace
node --test ai/test.cjs ai/strong/test.cjs
python ai/strong/test_teacher_contract.py
python ai/strong/test_model_v4.py
python ai/strong/test_snapshot_league.py
python ai/strong/test_multiplayer_bridge.py
python ai/strong/test_async_pool.py
python -u ai/strong/train.py
'
