"""Archive verified train/validation data and prepare an isolated HF Python package."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile

from huggingface_hub import HfApi, hf_hub_download
from strategic_collection import ROOT, read, write, digest
from opponent_surrogate_training_v1 import load_bundle
from opponent_surrogate_hf_v1 import SOURCE_FILES, DESIGN, DATA_PIN, SOURCE
from policy_iteration_evidence_archive import upload_evidence

DATA = ROOT/'ai/runs/opponent-surrogate-training-data-v1'
INDEX = ROOT/'ai/strong/opponent-surrogate-collection-results-v1.json'


def complete_data():
    assert INDEX.exists(), 'Complete fresh collection required before training packaging'
    index = read(INDEX)
    assert index['complete'] and index['games'] == 2560 and index['twins'] == 640
    assert index['split_games'] == {'train': 1920, 'validation': 320, 'test': 320}
    data, report = load_bundle(DATA, read(DESIGN))
    assert report['collection_index_sha256'] == digest(INDEX)
    assert report['preparer_sha256'] == digest(Path(__file__).with_name('prepare-opponent-surrogate-training-v1.py'))
    assert report['tensorizer_sha256'] == digest(Path(__file__).with_name('opponent_surrogate_training_v1.py'))
    return data, report


def archive_data():
    _, report = complete_data()
    assert not DATA_PIN.exists()
    output = ROOT/'ai/runs/opponent-surrogate-training-data-archive-v1'
    assert not output.exists() and not output.with_suffix('.tgz').exists()
    output.mkdir(); shutil.copytree(DATA, output/'data')
    write(output/'manifest.json', {str(p.relative_to(output)): digest(p) for p in sorted(output.rglob('*')) if p.is_file()})
    evidence = upload_evidence(output)
    pin = {**evidence, 'complete': True, 'design_sha256': digest(DESIGN),
           'data_check_sha256': digest(DATA/'data-check.json'), 'collection_index_sha256': digest(INDEX),
           'collection_protocol_sha256': report['collection_protocol_sha256'],
           'split_rows': report['split_rows'], 'split_games': report['split_games'],
           'unpacked_bytes': sum(p.stat().st_size for p in output.rglob('*') if p.is_file()),
           'test_records_included': False, 'gradients': False, 'qualification_eligible': False}
    write(DATA_PIN, pin); print({'data_pin': str(DATA_PIN), 'revision': pin['revision'], 'unpacked_bytes': pin['unpacked_bytes']})


def package(output, code_only=False):
    if not code_only:
        complete_data(); pin = read(DATA_PIN)
        assert pin['design_sha256'] == digest(DESIGN) and pin['data_check_sha256'] == digest(DATA/'data-check.json')
        assert pin['collection_index_sha256'] == digest(INDEX) and pin['remote_archive_verified']
        assert not SOURCE.exists()
    output = output.resolve(); output.mkdir(parents=True, exist_ok=False)
    names = SOURCE_FILES + ([] if code_only else [str(DATA_PIN.relative_to(ROOT))])
    for name in names:
        target = output/name; target.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(ROOT/name, target)
    manifest = {name: digest(output/name) for name in names}
    write(output/'opponent-surrogate-training-source-manifest.json', manifest)
    result = subprocess.run([sys.executable, '-B', 'ai/strong/opponent_surrogate_hf_v1.py', 'check-source'],
                            cwd=output, check=True, capture_output=True, text=True)
    assert json.loads(result.stdout.strip())['source_valid']
    assert all(digest(output/name) == sha for name, sha in manifest.items())
    check = {'source_valid': True, 'code_only': code_only, 'files': manifest,
             'manifest_sha256': digest(output/'opponent-surrogate-training-source-manifest.json'),
             'isolated_import_log': result.stdout, 'gradients': False, 'qualification_eligible': False}
    check_path = output.parent/(output.name+'-check.json'); write(check_path, check)
    if code_only:
        print({'code_only': True, 'source_valid': True, 'files': len(manifest), 'training_admitted': False}); return check
    archive = output.with_suffix('.tgz'); assert not archive.exists()
    with tarfile.open(archive, 'w:gz') as bundle:
        for name in sorted([*manifest, 'opponent-surrogate-training-source-manifest.json']):
            path = output/name; info = bundle.gettarinfo(path, arcname=name)
            info.uid = info.gid = info.mtime = 0; info.uname = info.gname = ''
            with path.open('rb') as f: bundle.addfile(info, f)
    intent = {'stage': 'upload_intent', 'archive': archive.name, 'sha256': digest(archive),
              'manifest_sha256': check['manifest_sha256'], 'data_pin_sha256': digest(DATA_PIN)}
    write(output.parent/(output.name+'-upload.json'), intent)
    commit = HfApi().upload_file(repo_id='coyotte508/powergrid-ai-training-v1', repo_type='dataset',
                               path_or_fileobj=archive, path_in_repo=archive.name)
    assert digest(hf_hub_download('coyotte508/powergrid-ai-training-v1', archive.name, repo_type='dataset', revision=commit.oid)) == digest(archive)
    descriptor = {**intent, 'stage': 'uploaded', 'revision': commit.oid, 'remote_archive_verified': True,
                  'files': manifest, 'bytes': archive.stat().st_size, 'design_sha256': digest(DESIGN),
                  'data_check_sha256': pin['data_check_sha256'], 'data_pin': pin,
                  'package_check_sha256': digest(check_path), 'gradients': False, 'qualification_eligible': False}
    write(SOURCE, descriptor); write(output.parent/(output.name+'-upload.json'), descriptor)
    print({'source_revision': descriptor['revision'], 'source_sha256': descriptor['sha256']}); return descriptor


if __name__ == '__main__':
    p = argparse.ArgumentParser(__doc__); sub = p.add_subparsers(dest='operation', required=True)
    sub.add_parser('archive-data')
    s = sub.add_parser('source'); s.add_argument('output', type=Path); s.add_argument('--code-only', action='store_true')
    a = p.parse_args()
    if a.operation == 'archive-data': archive_data()
    else: package(a.output, a.code_only)
