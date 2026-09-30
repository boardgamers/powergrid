#!/usr/bin/env bash
set -euo pipefail
# name model-path revision opponent samples geography games seed
case "${4:?opponent}" in
  economic|heuristic|rush|legacy|search|search_geo) ;;
  *) echo "Unsupported opponent mode; use OPPONENT_MODEL_PATH for a frozen model" >&2; exit 2 ;;
esac
extra_env=()
if [[ -n "${OPPONENT_MODEL_PATH:-}" ]]; then
  extra_env+=(--env "OPPONENT_MODEL_PATH=$OPPONENT_MODEL_PATH" --env "OPPONENT_MODEL_REVISION=${OPPONENT_MODEL_REVISION:?pin opponent revision}")
fi
hf jobs run --detach --flavor cpu-performance --timeout 3h \
  --secrets HF_TOKEN "${extra_env[@]}" \
  --env DISABLE_SEARCH_PROPOSAL="${DISABLE_SEARCH_PROPOSAL:-0}" \
  --env HF_MODEL_REPO=coyotte508/powergrid-ai-germany-v1 --env SEARCH_SCOPE="${SEARCH_SCOPE:-all}" \
  --env RUN_NAME="${1:?name}" --env MODEL_PATH="${2:?model path}" --env MODEL_REVISION="${3:?revision}" \
  --env OPPONENT="${4:?opponent}" --env SEARCH_SAMPLES="${5:?samples}" --env GEOGRAPHY="${6:?geography}" \
  --env PLAYER_COUNT="${PLAYER_COUNT:?Specify player count}" --env DEAL_OFFSET="${DEAL_OFFSET:-0}" \
  --env GAMES="${7:?games}" --env EVAL_SEED="${8:?seed}" --env WORKERS=24 \
  --label project=powergrid-ai --label stage="$1" \
  -- pytorch/pytorch:2.6.0-cuda12.4-cudnn9-runtime bash -lc '
set -euo pipefail
python -m pip install --quiet --timeout 120 --retries 5 huggingface_hub==2.0.0 onnxruntime==1.30.0 numpy==2.4.6
mkdir -p /workspace
python -c "import urllib.request,tarfile; urllib.request.urlretrieve(\"https://nodejs.org/dist/v24.14.0/node-v24.14.0-linux-x64.tar.xz\",\"/tmp/node.tar.xz\");tarfile.open(\"/tmp/node.tar.xz\").extractall(\"/opt\")"
export PATH=/opt/node-v24.14.0-linux-x64/bin:$PATH
python -c "from huggingface_hub import hf_hub_download;import tarfile;p=hf_hub_download(\"coyotte508/powergrid-ai-training-v1\",\"strong-source-v27.tgz\",repo_type=\"dataset\", revision=\"fe12e7a6b1fec2e04b749765af73477d39ded699\");tarfile.open(p).extractall(\"/workspace\")"
cd /workspace
python -u ai/strong/arena-job.py
'
