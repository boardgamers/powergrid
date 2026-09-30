#!/usr/bin/env bash
set -euo pipefail
revision=${1:?Pin completed original stronger-opponent dataset revision}
[[ "$revision" =~ ^[0-9a-f]{40}$ ]]
hf jobs run --detach --flavor cpu-performance --timeout 3h \
  --secrets HF_TOKEN \
  --env HF_DATA_REPO=coyotte508/powergrid-ai-training-v1 \
  --env REPAIR_INPUT_REVISION="$revision" \
  --env REPAIR_INPUT_VERSION=multiplayer-teacher-v2-strong \
  --env REPAIR_OUTPUT_VERSION=multiplayer-teacher-v2-strong-repaired \
  --env DATA_WORKERS=24 \
  --label project=powergrid-ai --label stage=strong-teacher-horizon-repair \
  -- pytorch/pytorch:2.6.0-cuda12.4-cudnn9-runtime bash -lc '
set -euo pipefail
python -m pip install --quiet --timeout 120 --retries 5 huggingface_hub==2.0.0
mkdir -p /workspace
python -c "import urllib.request,tarfile; urllib.request.urlretrieve(\"https://nodejs.org/dist/v24.14.0/node-v24.14.0-linux-x64.tar.xz\",\"/tmp/node.tar.xz\");tarfile.open(\"/tmp/node.tar.xz\").extractall(\"/opt\")"
export PATH=/opt/node-v24.14.0-linux-x64/bin:$PATH
python -c "from huggingface_hub import hf_hub_download;import tarfile;p=hf_hub_download(\"coyotte508/powergrid-ai-training-v1\",\"strong-source-v33.tgz\",repo_type=\"dataset\",revision=\"be9262485a29f38dd5c7f0f8442909d70bb98b94\");tarfile.open(p).extractall(\"/workspace\")"
cd /workspace
node --test ai/test.cjs ai/strong/test.cjs
python -u ai/strong/repair-teacher-dataset.py
'
