#!/usr/bin/env bash
set -euo pipefail
shard=${1:?Specify numeric shard}
[[ "$shard" =~ ^[0-9]+$ ]]
hf jobs run --detach --flavor cpu-performance --timeout 2h \
  --secrets HF_TOKEN \
  --env HF_DATA_REPO=coyotte508/powergrid-ai-training-v1 \
  --env SHARD="$shard" --env GAMES=256 --env DATA_WORKERS=24 --env SEARCH_SAMPLES=12 --env DATA_VERSION=search-teacher-v2 --env INCLUDE_ALL_PHASES=1 \
  --label project=powergrid-ai --label stage="search-teacher-v2-$shard" \
  -- pytorch/pytorch:2.6.0-cuda12.4-cudnn9-runtime bash -lc '
set -euo pipefail
python -m pip install --quiet huggingface_hub
mkdir -p /workspace
python -c "import urllib.request,tarfile; urllib.request.urlretrieve(\"https://nodejs.org/dist/v24.14.0/node-v24.14.0-linux-x64.tar.xz\",\"/tmp/node.tar.xz\");tarfile.open(\"/tmp/node.tar.xz\").extractall(\"/opt\")"
export PATH=/opt/node-v24.14.0-linux-x64/bin:$PATH
python -c "from huggingface_hub import hf_hub_download;import tarfile;p=hf_hub_download(\"coyotte508/powergrid-ai-training-v1\",\"strong-source-v6.tgz\",repo_type=\"dataset\");tarfile.open(p).extractall(\"/workspace\")"
cd /workspace
node --test ai/test.cjs ai/strong/test.cjs
python -u ai/strong/generate-search-data.py
'
