#!/usr/bin/env bash
set -euo pipefail
players=${1:?Specify player count 2–6}
[[ "$players" =~ ^[2-6]$ ]]
shard=$((players - 2))
version=${DATA_VERSION:-multiplayer-teacher-v2-strong-pilot}
games=${GAMES:-24}
[[ "$version" =~ ^[a-zA-Z0-9_-]+$ ]]
[[ "$games" =~ ^[0-9]+$ ]]
(( games >= 8 * players && games % (4 * players) == 0 ))
[[ "$shard" =~ ^[0-9]+$ ]]
hf jobs run --detach --flavor cpu-performance --timeout "${JOB_TIMEOUT:-6h}" \
  --secrets HF_TOKEN \
  --env HF_DATA_REPO=coyotte508/powergrid-ai-training-v1 \
  --env TEACHER_OPPONENTS=search_geo --env OPPONENT_SEARCH_SAMPLES=16 \
  --env SHARD="$shard" --env GAMES="$games" --env DATA_WORKERS=24 --env SEARCH_SAMPLES=48 --env GEOGRAPHY=1 --env FEATURE_REVISION=4.0-multiplayer --env PLAYER_COUNT="$players" --env DATA_VERSION="$version" --env INCLUDE_ALL_PHASES=1 \
  --label project=powergrid-ai --label stage="$version-$shard" \
  -- pytorch/pytorch:2.6.0-cuda12.4-cudnn9-runtime bash -lc '
set -euo pipefail
python -m pip install --quiet --timeout 120 --retries 5 huggingface_hub==2.0.0
mkdir -p /workspace
python -c "import urllib.request,tarfile; urllib.request.urlretrieve(\"https://nodejs.org/dist/v24.14.0/node-v24.14.0-linux-x64.tar.xz\",\"/tmp/node.tar.xz\");tarfile.open(\"/tmp/node.tar.xz\").extractall(\"/opt\")"
export PATH=/opt/node-v24.14.0-linux-x64/bin:$PATH
python -c "from huggingface_hub import hf_hub_download;import tarfile;p=hf_hub_download(\"coyotte508/powergrid-ai-training-v1\",\"strong-source-v29.tgz\",repo_type=\"dataset\",revision=\"a30fdb26474d2d78a4803f396c8888f9d974a371\");tarfile.open(p).extractall(\"/workspace\")"
cd /workspace
node --test ai/test.cjs ai/strong/test.cjs
python -u ai/strong/generate-search-data.py
'
