#!/usr/bin/env bash
set -euo pipefail
hf jobs run --detach --flavor cpu-performance --timeout 2h \
  --secrets HF_TOKEN \
  --env HF_MODEL_REPO=coyotte508/powergrid-ai-germany-v1 \
  --label project=powergrid-ai --label stage=b20-guided-search-screening \
  -- pytorch/pytorch:2.6.0-cuda12.4-cudnn9-runtime bash -lc '
set -euo pipefail
python -m pip install --quiet huggingface_hub onnxruntime
mkdir -p /workspace
python -c "import urllib.request,tarfile; urllib.request.urlretrieve(\"https://nodejs.org/dist/v24.14.0/node-v24.14.0-linux-x64.tar.xz\",\"/tmp/node.tar.xz\");tarfile.open(\"/tmp/node.tar.xz\").extractall(\"/opt\")"
export PATH=/opt/node-v24.14.0-linux-x64/bin:$PATH
python -c "from huggingface_hub import hf_hub_download;import tarfile;p=hf_hub_download(\"coyotte508/powergrid-ai-training-v1\",\"strong-source-v6.tgz\",repo_type=\"dataset\");tarfile.open(p).extractall(\"/workspace\")"
cd /workspace
python -c "from huggingface_hub import hf_hub_download; hf_hub_download(\"coyotte508/powergrid-ai-germany-v1\",\"runs/strong-league-v2-b/best.onnx\",revision=\"f9dfad5bde9862bc41aa42d77d9622621d70e8ce\",local_dir=\"models\")"
python ai/strong/evaluate.py models/runs/strong-league-v2-b/best.onnx --opponent search --search-samples 16 --games 96 --workers 24 --seed strong-search-screening-v1 --output evaluation.json
python -c "import os;from huggingface_hub import HfApi;HfApi().upload_file(repo_id=os.environ[\"HF_MODEL_REPO\"],path_or_fileobj=\"evaluation.json\",path_in_repo=\"runs/b20-guided-search-screening/evaluation.json\")"
'
