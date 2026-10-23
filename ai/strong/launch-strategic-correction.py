"""Guarded HF GPU training, admitted only by a complete frozen data/source check."""
from datetime import datetime, timezone
import json
import re
import subprocess
from strategic_collection import ROOT, read, write, digest


def main():
    source = read(ROOT/'ai/strong/strategic-correction-source-v1.json')
    check = read(ROOT/'ai/strong/strategic-correction-source-preflight-v1.json')
    assert check['passed'] and not check['code_only'] and check['gradients'] == 0
    assert check['source_revision'] == source['revision'] and check['source_sha256'] == source['sha256']
    assert check['data_preflight']['passed'] and check['data_preflight']['roots'] == 1920
    assert check['parent_preflight']['positions'] == 2553
    assert check['parent_preflight']['parent_tensors_unchanged']
    assert check['parent_preflight']['parent_actions_and_values_preserved']
    assert check['parent_preflight']['native_export_serving_parity']['all_actions_match']
    assert check['arena_preflight']['passed'] and check['arena_preflight']['total_games'] == 160
    assert check['arena_preflight']['game_truncations'] == 0
    assert check['overlays'] == source['overlays']
    assert all(digest(ROOT/name) == sha for name, sha in source['overlays'].items())
    design = read(ROOT/'ai/strong/strategic-correction-design-v1.json')
    manifest = read(ROOT/'ai/strong/strategic-teacher-training-results-v1.json')
    assert manifest['all_shards_verified'] and manifest['verified_shards'] == 160
    assert source['design_sha256'] == check['design_sha256'] == check['data_preflight']['design_sha256']
    assert source['data_manifest_sha256'] == check['manifest_sha256'] == check['data_preflight']['manifest_sha256']
    directory = ROOT/'ai/runs/strategic-correction-launch-v1'
    directory.mkdir(exist_ok=True)
    guard = directory/'launch.json'
    record = {'stage': 'launch_intent', 'created_at': datetime.now(timezone.utc).isoformat(),
        'source_revision': source['revision'], 'source_sha256': source['sha256'],
        'design_sha256': source['design_sha256'], 'data_manifest_sha256': source['data_manifest_sha256'],
        'flavor': 'l4x1', 'timeout_hours': 3, 'seeds': design['seeds'], 'qualification_eligible': False}
    with guard.open('x') as stream:
        json.dump(record, stream, indent=2)
    command = ['hf', 'jobs', 'run', '--detach', '--flavor', 'l4x1', '--timeout', '3h',
        '--secrets', 'HF_TOKEN', '--label', 'project=powergrid-ai', '--label', 'stage=strategic-correction-v1']
    for name, value in {'SOURCE_ARCHIVE': source['archive'], 'SOURCE_REVISION': source['revision'],
        'SOURCE_SHA256': source['sha256'], 'DESIGN_SHA256': source['design_sha256'],
        'DATA_MANIFEST_SHA256': source['data_manifest_sha256'], 'POWERGRID_HF_TRAINING': '1',
        'HF_HUB_DISABLE_PROGRESS_BARS': '1'}.items():
        command += ['--env', name+'='+value]
    command += ['--', 'pytorch/pytorch:2.6.0-cuda12.4-cudnn9-runtime', 'bash', '-lc', '''
set -euo pipefail
python -m pip install --quiet --timeout 120 --retries 5 huggingface_hub==2.0.0 onnxruntime==1.30.0 onnx==1.23.1 numpy==2.4.6
mkdir -p /workspace
python - <<'PY'
import urllib.request,tarfile,os,hashlib
from pathlib import Path
from huggingface_hub import hf_hub_download
urllib.request.urlretrieve('https://nodejs.org/dist/v24.14.0/node-v24.14.0-linux-x64.tar.xz','/tmp/node.tar.xz')
with tarfile.open('/tmp/node.tar.xz') as bundle: bundle.extractall('/opt')
path=hf_hub_download('coyotte508/powergrid-ai-training-v1',os.environ['SOURCE_ARCHIVE'],repo_type='dataset',revision=os.environ['SOURCE_REVISION'])
assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==os.environ['SOURCE_SHA256']
with tarfile.open(path) as bundle: bundle.extractall('/workspace',filter='data')
PY
export PATH=/opt/node-v24.14.0-linux-x64/bin:$PATH
cd /workspace
node --test ai/strong/test-strategic-correction-features.cjs
python ai/strong/test_model_strategic.py
python ai/strong/test_strategic_correction_targets.py
python -u ai/strong/train-strategic-correction.py ai/strong/strategic-teacher-training-results-v1.json ai/runs/strategic-correction-v1 --upload
''']
    try:
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=True)
        (directory/'launch.log').write_text(result.stdout+result.stderr)
        ids = set(re.findall(r'\b[0-9a-f]{24}\b', result.stdout))
        assert len(ids) == 1, 'Ambiguous launch: reconcile existing jobs before any retry'
        record.update(stage='launched', job_id=ids.pop())
    except BaseException as error:
        record.update(stage='launch_unknown', error=type(error).__name__+': '+str(error))
        raise
    finally:
        write(guard, record)
    print(record)


if __name__ == '__main__':
    main()
