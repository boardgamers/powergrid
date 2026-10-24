"""Store evidence snapshots as one verified file instead of duplicating HF trees."""
import hashlib
from pathlib import Path
import tarfile

from huggingface_hub import HfApi, hf_hub_download
from strategic_collection import read, digest


def upload_evidence(directory, repo='coyotte508/powergrid-ai-germany-v1'):
    directory = Path(directory)
    expected = read(directory/'manifest.json')
    expected['manifest.json'] = digest(directory/'manifest.json')
    assert {str(p.relative_to(directory)) for p in directory.rglob('*') if p.is_file()} == set(expected)
    assert all(digest(directory/name) == sha for name, sha in expected.items())
    archive = directory.with_suffix('.tgz')
    assert not archive.exists(), 'Inspect any previous upload outcome before retrying'
    with tarfile.open(archive, 'w:gz') as bundle:
        for name in sorted(expected):
            path = directory/name
            assert not path.is_symlink()
            info = bundle.gettarinfo(path, arcname=name)
            info.uid = info.gid = info.mtime = 0
            info.uname = info.gname = ''
            with path.open('rb') as stream:
                bundle.addfile(info, stream)
    with tarfile.open(archive) as bundle:
        assert {m.name for m in bundle.getmembers()} == set(expected)
        for member in bundle.getmembers():
            assert member.isfile()
            assert hashlib.sha256(bundle.extractfile(member).read()).hexdigest() == expected[member.name]
    path = 'archives/'+archive.name
    commit = HfApi().upload_file(repo_id=repo, path_or_fileobj=archive, path_in_repo=path)
    sha = digest(archive)
    assert digest(hf_hub_download(repo, path, revision=commit.oid)) == sha
    return {'repo': repo, 'revision': commit.oid, 'archive_path': path,
            'archive_sha256': sha, 'manifest_sha256': expected['manifest.json'],
            'archived_files': len(expected), 'format': 'tar.gz', 'remote_archive_verified': True}
