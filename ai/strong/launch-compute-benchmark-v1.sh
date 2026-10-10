#!/usr/bin/env bash
set -euo pipefail
flavor=${1:?Choose cpu-performance or h200}
case "$flavor" in
  cpu-performance) device=cpu ;;
  h200) device=cuda ;;
  *) exit 2 ;;
esac
: "${SOURCE_ARCHIVE:?Pin source archive}"
: "${SOURCE_REVISION:?Pin immutable revision}"
: "${SOURCE_SHA256:?Pin source hash}"
hf jobs run --detach --flavor "$flavor" --timeout 1h \
  --secrets HF_TOKEN --env BENCHMARK_FLAVOR="$flavor" --env BENCHMARK_DEVICE="$device" \
  --env POWERGRID_BENCHMARK_PLATFORM=hf-job \
  --env SOURCE_ARCHIVE="$SOURCE_ARCHIVE" --env SOURCE_REVISION="$SOURCE_REVISION" --env SOURCE_SHA256="$SOURCE_SHA256" \
  --label project=powergrid-ai --label stage="compute-v1-$flavor" \
  -- pytorch/pytorch:2.6.0-cuda12.4-cudnn9-runtime bash -lc '
set -euo pipefail
python -m pip install --quiet --timeout 120 --retries 5 huggingface_hub==2.0.0 numpy==2.4.6
mkdir -p /workspace
python - <<"PY"
import os, hashlib, tarfile
from pathlib import Path
from huggingface_hub import hf_hub_download
p=hf_hub_download("coyotte508/powergrid-ai-training-v1",os.environ["SOURCE_ARCHIVE"],repo_type="dataset",revision=os.environ["SOURCE_REVISION"])
assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==os.environ["SOURCE_SHA256"]
with tarfile.open(p) as t: t.extractall("/workspace")
PY
cd /workspace
python -u ai/strong/benchmark-training-compute.py \
  ai/strong/fixtures/compute-observations-v1.jsonl.gz \
  --fixtures-sha256 b83be87dddc4b151977031ac7baa8bd34a0861f3bdf1a627ede5191c530c5f6d \
  --device "$BENCHMARK_DEVICE" --threads 1 4 --batch-sizes 8 32 128 512 --repeats 15 \
  --output compute.json --upload-path "runs/population-compute-v1/$BENCHMARK_FLAVOR.json"
'
