"""Sealed archives and independently checked bucket downloads; no job API."""
import gzip
import hashlib
import os
from pathlib import Path
import re
import tarfile
import tempfile

from checkpoint_bucket_transport_v3 import BucketTransport, digest, read, require
from current_auction_resource_job_v2 import tree

BUCKET = 'coyotte508/powergrid-ai-checkpoints'


def prefix(name):
    require(re.fullmatch('[a-z0-9][a-z0-9-]{1,100}', name), 'Unsafe archive name')
    return 'confirmation-v3/'+name


def checked_receipt(evidence, name):
    require(evidence['storage'] == 'hf_bucket' and evidence['bucket'] == BUCKET
        and evidence['download_verified'] is True and evidence['server_versioning'] is False,
        'Unverified or foreign bucket receipt')
    for key in ('archive_sha256', 'manifest_sha256', 'xet_hash'):
        require(re.fullmatch('[a-f0-9]{64}', evidence[key]), 'Invalid bucket content pin')
    require(evidence['path'] == prefix(name)+'/'+evidence['archive_sha256']+'.tgz', 'Foreign bucket object path')
    require(type(evidence['bytes']) is int and evidence['bytes'] > 0
        and evidence['max_application_upload_calls'] == 3
        and type(evidence['application_upload_calls']) is int and 0 <= evidence['application_upload_calls'] <= 3,
        'Invalid bounded transport receipt')
    require(evidence['raw_audited'] is False and evidence['qualified'] is False, 'Transport cannot claim a raw audit')


def archive_directory(directory):
    directory = Path(directory).resolve()
    pins = tree(directory, 'manifest.json', digest(directory/'manifest.json'))
    expected = {**pins, 'manifest.json': digest(directory/'manifest.json')}
    archive = directory.with_suffix('.tgz')
    partial = archive.with_suffix('.partial')
    require(not archive.exists() and not partial.exists(), 'Inspect existing archive or partial before rebuilding')
    with partial.open('xb') as raw:
        with gzip.GzipFile(fileobj=raw, mode='wb', filename='', mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode='w') as bundle:
                for name in sorted(expected):
                    source = directory/name
                    info = bundle.gettarinfo(source, arcname=name)
                    require(info.isfile(), 'Archive only regular files')
                    info.uid = info.gid = info.mtime = 0
                    info.uname = info.gname = ''
                    with source.open('rb') as stream: bundle.addfile(info, stream)
        raw.flush(); os.fsync(raw.fileno())
    verify_archive(partial, expected['manifest.json'])
    require(tree(directory, 'manifest.json', expected['manifest.json']) == pins, 'Source changed while archiving')
    os.link(partial, archive); partial.unlink()
    return archive


def verify_archive(archive, manifest_sha256):
    with tarfile.open(archive, 'r:gz') as bundle:
        members = bundle.getmembers(); names = [p.name for p in members]
        require(len(names) == len(set(names)) and 'manifest.json' in names, 'Ambiguous archive members')
        require(all(p.isfile() and not Path(p.name).is_absolute()
            and all(part not in ('', '.', '..') for part in p.name.split('/')) for p in members), 'Unsafe archive members')
        data = bundle.extractfile('manifest.json').read()
        require(hashlib.sha256(data).hexdigest() == manifest_sha256, 'Archive manifest changed')
        import json
        pins = json.loads(data)
        require('manifest.json' not in pins and set(pins)|{'manifest.json'} == set(names), 'Archive file set changed')
        for name, sha in {**pins, 'manifest.json': manifest_sha256}.items():
            with bundle.extractfile(name) as stream:
                require(hashlib.file_digest(stream, 'sha256').hexdigest() == sha, 'Archived bytes changed')
        return pins


def upload_directory(directory, ledgers, api):
    directory = Path(directory)
    archive = archive_directory(directory)
    receipt = BucketTransport(api).retain(archive, bucket=BUCKET, prefix=prefix(directory.name),
        manifest_sha256=digest(directory/'manifest.json'), ledger=Path(ledgers)/directory.name)
    checked_receipt(receipt, directory.name)
    return receipt


def download_archive(evidence, name, destination, api):
    """Verify actual remote bytes and extract only after all pins have passed."""
    checked_receipt(evidence, name)
    destination = Path(destination)
    require(not destination.exists(), 'Existing collected tree requires explicit reuse verification')
    destination.parent.mkdir(parents=True, exist_ok=True)
    transport = BucketTransport(api)
    transport.private(BUCKET)
    obj = transport.metadata(BUCKET, evidence['path'])
    require(obj is not None and obj.xet_hash == evidence['xet_hash'] and obj.size == evidence['bytes'],
        'Bucket object missing or changed')
    with tempfile.TemporaryDirectory(prefix='.bucket-download-', dir=destination.parent) as temporary:
        archive = Path(temporary)/'archive.tgz'
        def download():
            archive.unlink(missing_ok=True)
            api.download_bucket_files(BUCKET, [(obj, archive)], raise_on_missing_files=True)
        transport.observe(download)
        require(archive.is_file() and archive.stat().st_size == evidence['bytes']
            and digest(archive) == evidence['archive_sha256'], 'Downloaded archive changed')
        verify_archive(archive, evidence['manifest_sha256'])
        after = transport.metadata(BUCKET, evidence['path'])
        require(after is not None and after.xet_hash == obj.xet_hash and after.size == obj.size,
            'Object changed during independent collection')
        transport.private(BUCKET)
        staging = Path(temporary)/'tree'; staging.mkdir()
        with tarfile.open(archive, 'r:gz') as bundle: bundle.extractall(staging, filter='data')
        tree(staging, 'manifest.json', evidence['manifest_sha256'])
        staging.rename(destination)
    return destination
