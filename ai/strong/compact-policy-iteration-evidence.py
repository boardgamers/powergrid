"""Replace duplicate checkpoint trees at HF HEAD with byte-verified tar archives.

Original pinned Git revisions remain untouched. Raw job outputs and model files
are never selected. Each addition and tree deletion is one atomic HF commit.
"""
import argparse
import hashlib
import re
import tarfile

from huggingface_hub import HfApi, CommitOperationAdd, CommitOperationDelete, hf_hub_download
from strategic_collection import ROOT, read, write, digest

REPO = 'coyotte508/powergrid-ai-germany-v1'
ALLOWED = [
    'policy-iteration-wave3-checkpoint-v2',
    'policy-iteration-wave2-checkpoint-v2',
    'policy-iteration-labels-complete-launch-evidence-v2',
    'policy-iteration-parent-reference-92-evidence-v2',
    'policy-iteration-capacity-checkpoint-v2',
    'policy-iteration-development-preparation-evidence-v2',
    'policy-iteration-labels-268-progress-evidence-v2',
    'policy-iteration-labels-159-progress-evidence-v2',
    'policy-iteration-labels-119-progress-evidence-v2',
    'policy-iteration-labels-remaining-launch-progress-v2',
    'policy-iteration-parent-grid-launch-evidence-v2',
    'strategic-correction-complete-arena-evidence-v1',
    'strategic-correction-ablation-evidence-v1',
]


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('name', choices=ALLOWED)
    args = parser.parse_args()
    directory = ROOT/'ai/runs'/args.name
    manifest = read(directory/'manifest.json')
    assert all(isinstance(sha, str) and re.fullmatch(r'[a-f0-9]{64}', sha) for sha in manifest.values()), 'Only flat file-hash manifests are admitted'
    assert all(digest(directory/file) == sha for file, sha in manifest.items())
    expected = {**manifest, 'manifest.json': digest(directory/'manifest.json')}
    output = ROOT/'ai/runs/policy-iteration-storage-compaction-v2'
    output.mkdir(exist_ok=True)
    record_path = output/(args.name+'.json')
    assert not record_path.exists(), 'Reconcile any existing compaction record before retrying'
    archive = output/(args.name+'.tgz')
    assert not archive.exists(), 'Preserve earlier archives; inspect before retrying'
    with tarfile.open(archive, 'w:gz') as bundle:
        for file in sorted(expected):
            path = directory/file
            assert path.is_file() and not path.is_symlink()
            info = bundle.gettarinfo(path, arcname=file)
            info.uid = info.gid = info.mtime = 0
            info.uname = info.gname = ''
            with path.open('rb') as stream:
                bundle.addfile(info, stream)
    with tarfile.open(archive) as bundle:
        assert {m.name for m in bundle.getmembers()} == set(expected)
        for member in bundle.getmembers():
            assert member.isfile()
            assert hashlib.sha256(bundle.extractfile(member).read()).hexdigest() == expected[member.name]
    api = HfApi()
    before = api.model_info(REPO).sha
    prefix = 'runs/'+args.name
    remote = [r for r in api.list_repo_tree(REPO, path_in_repo=prefix, recursive=True, revision=before)
              if hasattr(r, 'blob_id')]
    assert remote, 'There must be a known duplicate tree to compact'
    # A failed multi-commit upload can leave a subset; all present files must match.
    for file in remote:
        name = file.path[len(prefix)+1:]
        assert name in expected
        data = (directory/name).read_bytes()
        assert len(data) == file.size
        if file.lfs:
            assert file.lfs.sha256 == hashlib.sha256(data).hexdigest()
        else:
            assert file.blob_id == hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
    target = 'archives/'+args.name+'.tgz'
    record = {'stage': 'commit_intent', 'repo': REPO, 'name': args.name,
              'before_revision': before, 'original_prefix': prefix, 'archive_path': target,
              'archive_sha256': digest(archive), 'manifest_sha256': expected['manifest.json'],
              'archived_files': len(expected), 'head_files_removed': len(remote),
              'original_revisions_preserved': True, 'raw_job_outputs_removed': False,
              'local_manifest_matches_all_current_remote_files': True}
    write(record_path, record)
    commit = api.create_commit(repo_id=REPO, commit_message='Compact duplicate evidence '+args.name,
                              operations=[CommitOperationAdd(path_in_repo=target, path_or_fileobj=archive),
                                          CommitOperationDelete(path_in_repo=prefix, is_folder=True)])
    record.update(stage='committed', revision=commit.oid)
    write(record_path, record)
    downloaded = hf_hub_download(REPO, target, revision=commit.oid)
    assert digest(downloaded) == record['archive_sha256']
    # Prove both the compact representation and the old revision are recoverable.
    sample = next(r for r in remote if r.path.endswith('/manifest.json')) if any(r.path.endswith('/manifest.json') for r in remote) else remote[0]
    old = hf_hub_download(REPO, sample.path, revision=before)
    assert digest(old) == expected[sample.path[len(prefix)+1:]]
    record.update(stage='verified', remote_archive_verified=True, historical_revision_read_verified=True,
                  net_head_file_reduction=len(remote)-1)
    write(record_path, record)
    write(ROOT/'ai/strong'/(args.name+'-compacted.json'), record)
    print(record, flush=True)


if __name__ == '__main__':
    main()
