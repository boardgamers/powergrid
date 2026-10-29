"""Verified, resumable checkpoint storage without one Git commit per upload.

This module has no game, job-submission or bucket-creation API. Bucket objects
are mutable: receipts pin both downloaded SHA-256 and Xet identity. They are not
a substitute for the final versioned evidence archive or independent game audit.
The existing v2 workers do not import this unadmitted transport.
"""
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import tempfile
import time

import httpx2 as httpx


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def save(path, value):
    """A completed exclusive JSON write, durably linked into its directory."""
    path = Path(path)
    fd, name = tempfile.mkstemp(prefix='.pending-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as stream:
            json.dump(value, stream, indent=2, allow_nan=False)
            stream.write('\n'); stream.flush(); os.fsync(stream.fileno())
        os.link(name, path)
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try: os.fsync(directory)
        finally: os.close(directory)
    finally:
        os.unlink(name)


def transient(error):
    status = getattr(getattr(error, 'response', None), 'status_code', None)
    return status in (408, 429, 500, 502, 503, 504) or isinstance(error, httpx.TransportError)


def diagnostic(error):
    # Error bodies/URLs can contain credentials. Persist only class and status.
    return {'type': type(error).__name__,
        'http_status': getattr(getattr(error, 'response', None), 'status_code', None)}


class BucketTransport:
    def __init__(self, api, *, upload_attempts=3, read_attempts=3, sleep=time.sleep):
        require(type(upload_attempts) is int and 1 <= upload_attempts <= 4, 'Invalid upload bound')
        require(type(read_attempts) is int and 1 <= read_attempts <= 4, 'Invalid read bound')
        self.api, self.upload_attempts, self.read_attempts, self.sleep = api, upload_attempts, read_attempts, sleep

    def observe(self, operation):
        for attempt in range(self.read_attempts):
            try: return operation()
            except Exception as error:
                if not transient(error) or attempt + 1 == self.read_attempts: raise
                self.sleep(2 ** (attempt + 1))

    def private(self, bucket):
        require(self.observe(lambda: self.api.bucket_info(bucket)).private is True, 'Bucket must stay private')

    def metadata(self, bucket, path):
        entries = self.observe(lambda: list(self.api.get_bucket_paths_info(bucket, [path])))
        require(len(entries) <= 1, 'Duplicate remote objects')
        if not entries: return None
        obj = entries[0]
        require(obj.path == path and type(obj.size) is int and obj.size >= 0
            and re.fullmatch('[a-f0-9]{64}', obj.xet_hash or ''), 'Invalid remote object identity')
        return obj

    def verify(self, expected):
        """Read only. Independent callers can revalidate a saved receipt."""
        bucket, path = expected['bucket'], expected['path']
        self.private(bucket)
        obj = self.metadata(bucket, path)
        require(obj is not None, 'Previously recorded object is missing')
        require(obj.size == expected['bytes'], 'Remote size changed')
        if 'xet_hash' in expected:
            require(obj.xet_hash == expected['xet_hash'], 'Remote Xet identity changed')
        with tempfile.TemporaryDirectory(prefix='pg-bucket-verify-') as folder:
            target = Path(folder)/'archive.tgz'
            def download():
                target.unlink(missing_ok=True)
                self.api.download_bucket_files(bucket, [(obj, target)], raise_on_missing_files=True)
            self.observe(download)
            require(target.is_file() and not target.is_symlink()
                and target.stat().st_size == expected['bytes']
                and digest(target) == expected['archive_sha256'], 'Downloaded archive differs')
        after = self.metadata(bucket, path)
        require(after is not None and after.xet_hash == obj.xet_hash and after.size == obj.size,
            'Object changed during verification')
        self.private(bucket)
        return obj.xet_hash

    @contextmanager
    def locked(self, ledger):
        ledger.mkdir(parents=True, exist_ok=True)
        with (ledger/'.lock').open('a') as stream:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            try: yield
            finally: fcntl.flock(stream, fcntl.LOCK_UN)

    def retain(self, archive, *, bucket, prefix, manifest_sha256, ledger):
        archive, ledger = Path(archive), Path(ledger)
        require(archive.is_file() and not archive.is_symlink(), 'Archive must be a regular file')
        require(re.fullmatch('[A-Za-z0-9_-]+/[A-Za-z0-9_-]+', bucket), 'Invalid bucket')
        require(isinstance(prefix, str) and prefix == str(PurePosixPath(prefix))
            and all(re.fullmatch('[a-zA-Z0-9_-]+', p) for p in prefix.split('/')), 'Unsafe prefix')
        require(re.fullmatch('[a-f0-9]{64}', manifest_sha256), 'Missing manifest pin')
        sha = digest(archive)
        expected = {'storage': 'hf_bucket', 'bucket': bucket, 'path': prefix+'/'+sha+'.tgz',
            'archive_sha256': sha, 'manifest_sha256': manifest_sha256, 'bytes': archive.stat().st_size,
            'server_versioning': False, 'max_application_upload_calls': self.upload_attempts}
        with self.locked(ledger):
            intent = ledger/'intent.json'; receipt = ledger/'receipt.json'
            if intent.exists(): require(read(intent) == expected, 'Resume inputs differ from original intent')
            else:
                require(not receipt.exists() and not list(ledger.glob('upload-*.json')), 'Orphan transport evidence')
                save(intent, expected)
            if receipt.exists():
                result = read(receipt)
                require(all(result.get(k) == v for k, v in expected.items()), 'Receipt intent differs')
                self.verify(result)  # A deleted/corrupt saved object must never be silently repaired.
                return result
            self.private(bucket)
            calls = sorted(ledger.glob('upload-*.json'))
            require([p.name for p in calls] == [f'upload-{i:02d}.json' for i in range(1, len(calls)+1)],
                'Missing upload call record')
            attempts = len(calls)
            last_error = None
            if attempts:
                outcome = ledger/f'outcome-{attempts:02d}.json'
                if outcome.exists(): last_error = read(outcome)
            while True:
                obj = self.metadata(bucket, expected['path'])
                if obj is not None:
                    xet = self.verify(expected)
                    require(digest(archive) == sha, 'Local archive changed during transport')
                    result = {**expected, 'xet_hash': xet, 'download_verified': True,
                        'application_upload_calls': attempts,
                        'reconciled_upload_error_or_interruption': bool(attempts and
                            (last_error is None or not last_error.get('acknowledged'))),
                        'raw_audited': False, 'qualified': False}
                    save(receipt, result)
                    return result
                if last_error is not None:
                    require(last_error['acknowledged'] or last_error['transient'],
                        'Permanent upload error; inspect original intent')
                require(attempts < self.upload_attempts, 'Upload budget exhausted; inspect original intent')
                if attempts: self.sleep(min(2 ** attempts, 8))
                self.private(bucket)
                require(digest(archive) == sha, 'Local archive changed before upload')
                # Recheck after backoff. Never overwrite an existing, unverified object.
                if self.metadata(bucket, expected['path']) is not None: continue
                attempts += 1
                save(ledger/f'upload-{attempts:02d}.json', {'intent_sha256': digest(intent),
                    'application_upload_call': attempts, 'remote_absent_before_call': True})
                try:
                    self.api.batch_bucket_files(bucket, add=[(archive, expected['path'])])
                except Exception as error:
                    last_error = {'acknowledged': False, 'transient': transient(error), 'error': diagnostic(error)}
                else:
                    last_error = {'acknowledged': True, 'transient': False}
                save(ledger/f'outcome-{attempts:02d}.json', last_error)
                # Even a non-retryable error can have committed bytes. Observe and
                # verify that exact path before deciding whether another call is safe.
