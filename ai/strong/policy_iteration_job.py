"""Immutable data recovery and admission shared by the next HF training jobs."""
import os
from pathlib import Path
import shutil

from huggingface_hub import hf_hub_download
from strategic_collection import ROOT, read, digest
from policy_iteration_data import validate_manifest, PROTOCOL, SOURCE
from policy_iteration_training import load_bundle

DESIGN = ROOT/'ai/strong/policy-iteration-training-design-v2.json'
DATA_PIN = ROOT/'ai/strong/policy-iteration-training-data-evidence-v2.json'
MANIFEST = ROOT/'ai/strong/policy-iteration-labels-results-v2.json'
FILES = {'features.npz', 'targets.npz', 'metadata.json', 'feature-check.json', 'label-manifest.json', 'data-check.json'}

BOOTSTRAP = '''
set -euo pipefail
python -m pip install --quiet --timeout 120 --retries 5 huggingface_hub==2.0.0 onnxruntime==1.30.0 onnx==1.23.1 numpy==2.4.6
mkdir -p /workspace
python - <<'INNER'
import urllib.request,tarfile,os,hashlib
from pathlib import Path
from huggingface_hub import hf_hub_download
urllib.request.urlretrieve('https://nodejs.org/dist/v24.14.0/node-v24.14.0-linux-x64.tar.xz','/tmp/node.tar.xz')
with tarfile.open('/tmp/node.tar.xz') as bundle: bundle.extractall('/opt')
path=hf_hub_download('coyotte508/powergrid-ai-training-v1',os.environ['SOURCE_ARCHIVE'],repo_type='dataset',revision=os.environ['SOURCE_REVISION'])
assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==os.environ['SOURCE_SHA256']
with tarfile.open(path) as bundle: bundle.extractall('/workspace',filter='data')
INNER
export PATH=/opt/node-v24.14.0-linux-x64/bin:$PATH
cd /workspace
python -u ai/strong/policy_iteration_job.py
python ai/strong/test_model_policy_iteration.py
python -u ai/strong/preflight-policy-iteration-model.py
python ai/strong/test_policy_iteration_training.py
python -u ai/strong/train-policy-iteration.py ai/runs/policy-iteration-training-data-v2 "ai/runs/policy-iteration-training-v2-$HEAD_TYPE" --head-type "$HEAD_TYPE" --upload
'''


def complete_inputs():
    """The incomplete-grid check precedes downloads, output creation and launch."""
    manifest, design = read(MANIFEST), read(DESIGN)
    validate_manifest(manifest, read(PROTOCOL), read(SOURCE))
    assert design['label_source'] == read(SOURCE)
    assert design['label_protocol_sha256'] == digest(PROTOCOL)
    pin = read(DATA_PIN)
    assert pin['design_sha256'] == digest(DESIGN)
    assert pin['label_manifest_sha256'] == digest(MANIFEST)
    assert pin['positions'] == 17280 and pin['split_counts'] == {'train': 12960, 'validation': 4320}
    assert set(pin['files']) == FILES
    assert pin['repo'] == design['parent']['repo']
    assert len(pin['revision']) == 40 and all(len(sha) == 64 for sha in pin['files'].values())
    return design, pin


def recover_data(directory):
    design, pin = complete_inputs()
    directory.mkdir(parents=True, exist_ok=True)
    assert {f.name for f in directory.iterdir()} <= FILES
    for file, sha in pin['files'].items():
        target = directory/file
        if not target.exists():
            cached = hf_hub_download(pin['repo'], pin['prefix']+'/'+file, revision=pin['revision'])
            assert digest(cached) == sha
            shutil.copy2(cached, target)
        assert digest(target) == sha
    assert digest(directory/'label-manifest.json') == digest(MANIFEST)
    data, metadata, report = load_bundle(directory, design)
    for file, sha in report['code'].items():
        assert digest(ROOT/file) == sha
    return data, metadata, report


def admission():
    design, data_pin = complete_inputs()
    source = read(ROOT/'ai/strong/policy-iteration-training-source-v2.json')
    check_path = ROOT/'ai/strong/policy-iteration-training-source-check-v2.json'
    check = read(check_path)
    assert check['passed'] and not check['code_only'] and not check['gradients']
    assert source['check_sha256'] == digest(check_path)
    assert source['base'] == read(SOURCE) == design['label_source']
    assert source['design_sha256'] == check['design_sha256'] == digest(DESIGN)
    assert source['data_pin_sha256'] == check['data_pin_sha256'] == digest(DATA_PIN)
    assert source['data_check_sha256'] == check['data_check_sha256'] == data_pin['files']['data-check.json']
    assert source['label_manifest_sha256'] == check['label_manifest_sha256'] == digest(MANIFEST)
    assert check['positions'] == 17280 and check['split_counts'] == {'train': 12960, 'validation': 4320}
    assert source['unchanged_base_files'] == 1434
    assert all(digest(ROOT/file) == sha for file, sha in source['overlays'].items())
    assert check['model_preflight']['complete'] and check['model_preflight']['synthetic_untrained']
    assert set(check['model_preflight']['cases']) == {'frozen-0', 'frozen-1', 'public-0', 'public-1'}
    for case in check['model_preflight']['cases'].values():
        assert case['complete'] and case['positions'] == 2553 and case['cached_positions_checked'] == 17280
        assert case['all_moves_legal'] and case['all_native_onnx_actions_equal'] and case['parent_values_preserved']
    return design, data_pin, source


def main():
    assert os.environ.get('POWERGRID_HF_TRAINING') == '1', 'Job bootstrap only'
    assert os.environ['DESIGN_SHA256'] == digest(DESIGN)
    assert os.environ['DATA_PIN_SHA256'] == digest(DATA_PIN)
    check = read(ROOT/'ai/strong/policy-iteration-training-source-check-v2.json')
    assert check['passed'] and not check['code_only'] and not check['gradients']
    assert check['data_check_sha256'] == os.environ['DATA_CHECK_SHA256']
    data, metadata, report = recover_data(ROOT/'ai/runs/policy-iteration-training-data-v2')
    assert digest(ROOT/'ai/runs/policy-iteration-training-data-v2/data-check.json') == os.environ['DATA_CHECK_SHA256']
    features = ROOT/'ai/runs/policy-iteration-features-v2'
    features.mkdir(exist_ok=False)
    for file in ['features.npz', 'metadata.json', 'feature-check.json']:
        shutil.copy2(ROOT/'ai/runs/policy-iteration-training-data-v2'/file, features/file)
    print({'data_recovered_and_verified': True, 'positions': len(metadata), 'gradients': False}, flush=True)


if __name__ == '__main__':
    main()
