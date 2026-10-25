"""Immutable HF source/data recovery for the opponent imitation training stage."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import time

from huggingface_hub import hf_hub_download
from strategic_collection import ROOT, read, write, digest
from population_policy_verification import extract_verified
from opponent_surrogate_training_v1 import load_bundle

STRONG = ROOT/'ai/strong'
DESIGN = STRONG/'opponent-surrogate-training-design-v1.json'
DATA_PIN = STRONG/'opponent-surrogate-training-data-v1.json'
SOURCE = STRONG/'opponent-surrogate-training-source-v1.json'
SOURCE_FILES = ['ai/infer.py', 'ai/pool.py'] + ['ai/strong/'+name for name in (
    'strategic_collection.py', 'feature_contract.py', 'arena_statistics.py',
    'population_policy_verification.py', 'policy_iteration_evidence_archive.py',
    'model_opponent_surrogate_v1.py', 'opponent_surrogate_training_v1.py',
    'opponent-surrogate-training-design-v1.json', 'train-opponent-surrogate-v1.py',
    'export-opponent-surrogate-v1.py', 'opponent_surrogate_hf_v1.py',
    'benchmark-opponent-surrogate-training-v1.py')]

BOOTSTRAP = r'''
set -euo pipefail
python -m pip install --quiet --timeout 120 --retries 5 huggingface_hub==2.0.0 onnxruntime==1.30.0 onnx==1.23.1 numpy==2.4.6
mkdir -p /workspace
python - <<'INNER'
import os,hashlib,tarfile
from pathlib import Path
from huggingface_hub import hf_hub_download
file=hf_hub_download('coyotte508/powergrid-ai-training-v1',os.environ['SOURCE_ARCHIVE'],repo_type='dataset',revision=os.environ['SOURCE_REVISION'])
assert hashlib.sha256(Path(file).read_bytes()).hexdigest()==os.environ['SOURCE_SHA256']
with tarfile.open(file) as bundle:bundle.extractall('/workspace',filter='data')
INNER
cd /workspace
python -u ai/strong/opponent_surrogate_hf_v1.py "$MODE"
'''


def source_check():
    manifest = ROOT/'opponent-surrogate-training-source-manifest.json'
    if os.environ.get('SOURCE_MANIFEST_SHA256'):
        assert digest(manifest) == os.environ['SOURCE_MANIFEST_SHA256']
    files = read(manifest)
    assert set(files) in (set(SOURCE_FILES), set(SOURCE_FILES) | {str(DATA_PIN.relative_to(ROOT))})
    assert all(digest(ROOT/name) == sha for name, sha in files.items())
    assert read(DESIGN)['parameters'] == 433217
    return files


def recover_data():
    pin = read(DATA_PIN); design = read(DESIGN)
    assert pin['complete'] and pin['remote_archive_verified'] and pin['test_records_included'] is False
    assert pin['design_sha256'] == digest(DESIGN)
    assert pin['collection_protocol_sha256'] == design['collection_protocol_sha256']
    assert pin['data_check_sha256'] == os.environ['DATA_CHECK_SHA256']
    archive = Path(hf_hub_download(pin['repo'], pin['archive_path'], revision=pin['revision']))
    assert digest(archive) == pin['archive_sha256']
    folder = ROOT/'ai/runs/opponent-surrogate-training-data-recovered-v1'
    if not folder.exists(): extract_verified(archive, folder)
    assert digest(folder/'manifest.json') == pin['manifest_sha256']
    assert all(digest(folder/name) == sha for name, sha in read(folder/'manifest.json').items())
    data_path = folder/'data'
    assert digest(data_path/'data-check.json') == pin['data_check_sha256']
    data, report = load_bundle(data_path, design)
    assert report['collection_index_sha256'] == pin['collection_index_sha256']
    return data_path, data, report


def main(mode):
    files = source_check()
    if mode == 'check-source':
        for name in ('train-opponent-surrogate-v1.py', 'export-opponent-surrogate-v1.py', 'benchmark-opponent-surrogate-training-v1.py'):
            spec = importlib.util.spec_from_file_location('check_' + name.replace('-', '_'), STRONG/name)
            module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        print(json.dumps({'files': len(files), 'source_valid': True, 'gradients': False})); return
    assert mode in ('calibration', 'full') and DATA_PIN.exists()
    assert os.environ['POWERGRID_HF_TRAINING'] == '1' and os.environ['DESIGN_SHA256'] == digest(DESIGN)
    assert os.environ.get('CUBLAS_WORKSPACE_CONFIG') == ':4096:8'
    began = time.monotonic(); data_path, data, report = recover_data()
    recovery_seconds = time.monotonic() - began
    name = 'benchmark-opponent-surrogate-training-v1.py' if mode == 'calibration' else 'train-opponent-surrogate-v1.py'
    spec = importlib.util.spec_from_file_location('surrogate_hf_entry', STRONG/name)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    output = ROOT/f'ai/runs/opponent-surrogate-training-{mode}-v1'
    if mode == 'calibration': module.main(data, report, output, recovery_seconds)
    else:
        # The trainer validates/reloads the same immutable bundle and saves all
        # four seeds, their exports and failure evidence.
        del data
        module.main(data_path, output, True)
    assert files == source_check(), 'Source changed while executing the HF job'


if __name__ == '__main__':
    p = argparse.ArgumentParser(__doc__); p.add_argument('mode', choices=['check-source', 'calibration', 'full'])
    main(p.parse_args().mode)
