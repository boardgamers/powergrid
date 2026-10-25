"""Package the unchanged engine plus isolated fresh-root capture code."""
import argparse
from pathlib import Path
import shutil
import tarfile

from huggingface_hub import HfApi, hf_hub_download
from strategic_collection import ROOT, read, write, digest
from surrogate_continuation_roots_v1 import PROTOCOL

STRONG = ROOT/'ai/strong'
PREP = ROOT/'ai/runs/surrogate-continuation-roots-source-prepared-v1'
PREFLIGHT = ROOT/'ai/runs/surrogate-continuation-roots-preflight-v1/status.json'
SOURCE = STRONG/'surrogate-continuation-roots-source-v1.json'
ARCHIVE = ROOT/'ai/runs/strong-source-surrogate-continuation-roots-v1.tgz'
FILES = ['surrogate_continuation_roots_v1.py', 'surrogate-continuation-protocol-v1.json',
         'test_surrogate_continuation_roots_v1.py', 'preflight-surrogate-continuation-roots-v1.py',
         'surrogate-continuation-roots-job-v1.py', 'build-surrogate-continuation-roots-source-v1.py']


def prerequisites():
    proof = read(PREFLIGHT)
    assert proof['stage'] == 'complete' and proof['complete_games'] == 2 and proof['paired_executions'] == 4
    assert proof['caps'] == 0 and proof['runtime_unchanged'] and proof['resealed_duplicate_rejected']
    assert all(digest(ROOT/name) == sha for name, sha in proof['code_hashes'].items())
    assert all(digest(PREFLIGHT.parent/f'{n}p'/name) == sha for n, case in proof['cases'].items() for name, sha in case['files'].items())
    return proof


def prepare():
    proof = prerequisites()
    assert not any(path.exists() for path in (PREP, SOURCE, ARCHIVE)), 'Inspect earlier preparation; never overwrite'
    base = read(STRONG/'opponent-surrogate-collection-protocol-v1.json')['base_source']
    original = ROOT/'ai/runs'/base['archive']; assert digest(original) == base['sha256']
    layout = PREP/'layout'; layout.mkdir(parents=True)
    with tarfile.open(original) as bundle:
        members = bundle.getmembers()
        assert len(members) == len({m.name for m in members}) == base['files'] == 1463
        assert all(m.isfile() and not Path(m.name).is_absolute() and '..' not in Path(m.name).parts for m in members)
        bundle.extractall(layout, filter='data')
    before = {str(path.relative_to(layout)): digest(path) for path in layout.rglob('*') if path.is_file()}
    assert before == proof['runtime_hashes'] and not (layout/'ai/runs').exists()
    added = {}
    for name in FILES:
        path = STRONG/name; relative = str(path.relative_to(ROOT)); assert relative not in before
        shutil.copy2(path, layout/relative); added[relative] = digest(path)
    manifest = {**before, **added}; assert all(digest(layout/name) == sha for name, sha in manifest.items())
    manifest_path = layout/'surrogate-continuation-roots-source-manifest.json'; write(manifest_path, manifest)
    with tarfile.open(ARCHIVE, 'w:gz') as bundle:
        for name in sorted([*manifest, manifest_path.name]): bundle.add(layout/name, arcname=name, recursive=False)
    result = {'repo': base['repo'], 'archive': ARCHIVE.name, 'sha256': digest(ARCHIVE), 'bytes': ARCHIVE.stat().st_size,
              'manifest_sha256': digest(manifest_path), 'manifest_files': len(manifest), 'unchanged_base_files': len(before),
              'base': base, 'new_files': added, 'protocol_sha256': digest(PROTOCOL), 'preflight_sha256': digest(PREFLIGHT),
              'collection_admitted': False, 'runtime_admitted': False, 'gradients': False, 'qualification_eligible': False}
    write(PREP/'prepared.json', result)
    print({k: result[k] for k in ('archive', 'sha256', 'manifest_files', 'unchanged_base_files')})


def upload():
    prerequisites(); prepared = read(PREP/'prepared.json')
    assert not SOURCE.exists() and digest(ARCHIVE) == prepared['sha256']
    assert digest(PROTOCOL) == prepared['protocol_sha256'] and digest(PREFLIGHT) == prepared['preflight_sha256']
    assert all(digest(ROOT/name) == sha for name, sha in prepared['new_files'].items())
    with (PREP/'upload-intent.json').open('x') as stream:
        stream.write('{"purpose":"One private source upload; reconcile uncertain outcomes before retrying."}\n')
    commit = HfApi().upload_file(repo_id=prepared['repo'], repo_type='dataset', path_or_fileobj=ARCHIVE, path_in_repo=ARCHIVE.name)
    write(PREP/'upload-receipt.json', {'revision': commit.oid, 'sha256': prepared['sha256']})
    assert digest(hf_hub_download(prepared['repo'], ARCHIVE.name, repo_type='dataset', revision=commit.oid)) == prepared['sha256']
    write(SOURCE, {**prepared, 'revision': commit.oid, 'remote_archive_verified': True})
    print({'revision': commit.oid, 'sha256': prepared['sha256'], 'remote_archive_verified': True})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__); parser.add_argument('operation', choices=['prepare', 'upload'])
    globals()[parser.parse_args().operation]()
