#!/usr/bin/env bash
set -euo pipefail
players=${1:?Specify player count 2–6}
[[ "$players" =~ ^[2-6]$ ]]
hf jobs run --detach --flavor cpu-performance --timeout 6h \
  --secrets HF_TOKEN --env PLAYER_COUNT="$players" --env HF_MODEL_REPO=coyotte508/powergrid-ai-germany-v1 \
  --label project=powergrid-ai --label stage="teacher-reliability-v2-${players}p" \
  -- pytorch/pytorch:2.6.0-cuda12.4-cudnn9-runtime bash -lc '
set -euo pipefail
python -m pip install --quiet --timeout 120 --retries 5 huggingface_hub==2.0.0
mkdir -p /workspace
python -c "import urllib.request,tarfile; urllib.request.urlretrieve(\"https://nodejs.org/dist/v24.14.0/node-v24.14.0-linux-x64.tar.xz\",\"/tmp/node.tar.xz\");tarfile.open(\"/tmp/node.tar.xz\").extractall(\"/opt\")"
export PATH=/opt/node-v24.14.0-linux-x64/bin:$PATH
python -c "from huggingface_hub import hf_hub_download;import tarfile;p=hf_hub_download(\"coyotte508/powergrid-ai-training-v1\",\"strong-source-v36.tgz\",repo_type=\"dataset\",revision=\"d07e072058ee877112d609280980fc806ee8ce28\");tarfile.open(p).extractall(\"/workspace\")"
cd /workspace
node --test ai/strong/test-search-samples.cjs ai/strong/test-search-horizon.cjs
python -u ai/strong/audit-search-budgets.py
'
