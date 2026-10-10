#!/usr/bin/env bash
# Matched population pilot. Run gradients only inside HF Jobs.
set -euo pipefail
arm=${1:?Choose control, homogeneous or heterogeneous}
case "$arm" in
  control) mode=mixed_search_geo ;;
  homogeneous) mode=population_homogeneous ;;
  heterogeneous) mode=population_heterogeneous ;;
  *) exit 2 ;;
esac
: "${SOURCE_ARCHIVE:?Pin archive}"
: "${SOURCE_REVISION:?Pin immutable revision}"
: "${SOURCE_SHA256:?Pin SHA256}"
extra=()
if [[ "$arm" != control ]]; then
  extra+=(--env FROZEN_OPPONENTS=ai/strong/population-opponents-v1.json)
fi
hf jobs run --detach --flavor cpu-performance --timeout 8h \
  --secrets HF_TOKEN "${extra[@]}" \
  --env HF_MODEL_REPO=coyotte508/powergrid-ai-germany-v1 \
  --env SOURCE_ARCHIVE="$SOURCE_ARCHIVE" --env SOURCE_REVISION="$SOURCE_REVISION" \
  --env SOURCE_SHA256="$SOURCE_SHA256" \
  --env INIT_CHECKPOINT=runs/multiplayer-refine-hard-v1/latest.pt \
  --env INIT_REVISION=0aeacd5b8e36ece36ba06a77ddfd7b86110d4f3a \
  --env INIT_SHA256=1f9d1c89908ab036f6e6a54facba94b352bbae005e1ac042d88c60067e895224 \
  --env ARCHITECTURE=multiplayer_ordered --env MIX_PLAYER_COUNTS=1 \
  --env OPPONENT_MODE="$mode" --env RUN_NAME="multiplayer-population-v1-$arm" \
  --env TRAIN_SEED=10021 --env PYTHONHASHSEED=0 \
  --env ASYNC_ROLLOUT=1 --env TRAIN_DEVICE=cpu --env TORCH_THREADS=4 \
  --env SNAPSHOT_ADMISSION=periodic_anchor --env SNAPSHOT_INTERVAL=5 \
  --env LR=.00005 --env ENTROPY=.005 --env ANCHOR=.03 --env ANCHOR_POLICY=initial \
  --env UPDATES=20 --env EVAL_EVERY=10 --env ENVS=240 --env WORKERS=240 --env BATCH_SIZE=512 \
  --label project=powergrid-ai --label stage="population-v1-$arm" \
  -- pytorch/pytorch:2.6.0-cuda12.4-cudnn9-runtime bash -lc '
set -euo pipefail
python -m pip install --quiet --timeout 120 --retries 5 huggingface_hub==2.0.0 onnx==1.20.1 onnxruntime==1.30.0
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
node --test ai/test.cjs ai/strong/test.cjs ai/strong/test-opponent-population.cjs
python ai/strong/test_model_v4.py
python ai/strong/test_snapshot_league.py
python ai/strong/test_frozen_population.py
python -u ai/strong/train.py
'
