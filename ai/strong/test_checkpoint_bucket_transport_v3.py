"""Fault-injected storage contract tests; no network or game execution."""
import hashlib
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest

import httpx2 as httpx

from checkpoint_bucket_transport_v3 import BucketTransport, read


def failure(status):
    response = httpx.Response(status, request=httpx.Request('POST', 'https://example.invalid/upload'))
    return httpx.HTTPStatusError('injected error', request=response.request, response=response)


class FakeAPI:
    def __init__(self):
        self.private = True
        self.objects = {}
        self.uploads = 0
        self.faults = []
        self.read_faults = []
        self.download_faults = []
        self.corrupt_download = False
        self.change_on_download = False

    def bucket_info(self, bucket):
        return SimpleNamespace(private=self.private)

    def get_bucket_paths_info(self, bucket, paths):
        if self.read_faults: raise self.read_faults.pop(0)
        return [SimpleNamespace(path=p, size=len(self.objects[p]),
            xet_hash=hashlib.sha256(b'xet'+self.objects[p]).hexdigest()) for p in paths if p in self.objects]

    def batch_bucket_files(self, bucket, *, add):
        self.uploads += 1
        mode = self.faults.pop(0) if self.faults else None
        if mode == 'before': raise failure(503)
        if mode == 'rate': raise failure(429)
        if mode == 'permanent': raise failure(403)
        source, path = add[0]
        self.objects[path] = Path(source).read_bytes()
        if mode == 'after': raise failure(500)
        if mode == 'interrupt': raise KeyboardInterrupt()
        if mode == 'native': raise RuntimeError('native transport lost acknowledgement')

    def download_bucket_files(self, bucket, files, *, raise_on_missing_files):
        if self.download_faults: raise self.download_faults.pop(0)
        obj, path = files[0]
        body = self.objects[obj.path]
        Path(path).write_bytes(b'x'*len(body) if self.corrupt_download else body)
        if self.change_on_download: self.objects[obj.path] = b'y'*len(body)


class TransportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.archive = self.root/'archive.tgz'
        self.archive.write_bytes(b'existing frozen evidence archive')
        self.api = FakeAPI()
        self.sleeps = []
        self.transport = BucketTransport(self.api, sleep=self.sleeps.append)
        self.options = {'bucket': 'owner/private', 'prefix': 'attempt/checkpoint-0001',
            'manifest_sha256': 'a'*64, 'ledger': self.root/'ledger'}

    def retain(self):
        return self.transport.retain(self.archive, **self.options)

    def test_success_and_restart_reverify_without_upload(self):
        receipt = self.retain()
        self.assertTrue(receipt['download_verified'])
        self.assertFalse(receipt['server_versioning'])
        self.assertFalse(receipt['raw_audited'])
        self.assertEqual(self.retain(), receipt)
        self.assertEqual(self.api.uploads, 1)

    def test_server_error_after_commit_reconciles_without_reupload(self):
        self.api.faults = ['after']
        receipt = self.retain()
        self.assertTrue(receipt['reconciled_upload_error_or_interruption'])
        self.assertEqual(self.api.uploads, 1)

    def test_unknown_native_error_with_committed_bytes_reconciles(self):
        self.api.faults = ['native']
        self.assertTrue(self.retain()['download_verified'])
        self.assertEqual(self.api.uploads, 1)

    def test_transient_failure_before_commit_retries_same_bytes(self):
        self.api.faults = ['rate', 'before']
        receipt = self.retain()
        self.assertEqual(receipt['application_upload_calls'], 3)
        self.assertEqual(list(self.api.objects.values()), [self.archive.read_bytes()])
        self.assertEqual(self.sleeps, [2, 4])

    def test_upload_budget_survives_restart(self):
        self.api.faults = ['before']*6
        for _ in range(2):
            with self.assertRaisesRegex(ValueError, 'budget exhausted'): self.retain()
        self.assertEqual(self.api.uploads, 3)
        self.assertFalse((self.options['ledger']/'receipt.json').exists())

    def test_permanent_failure_is_not_retried(self):
        self.api.faults = ['permanent']
        for _ in range(2):
            with self.assertRaisesRegex(ValueError, 'Permanent'): self.retain()
        self.assertEqual(self.api.uploads, 1)

    def test_crash_after_commit_resumes_without_second_upload(self):
        self.api.faults = ['interrupt']
        with self.assertRaises(KeyboardInterrupt): self.retain()
        self.assertTrue(self.retain()['reconciled_upload_error_or_interruption'])
        self.assertEqual(self.api.uploads, 1)

    def test_observation_timeout_does_not_trigger_write(self):
        self.api.read_faults = [httpx.ReadTimeout('injected')]*3
        with self.assertRaises(httpx.ReadTimeout): self.retain()
        self.assertEqual(self.api.uploads, 0)
        self.assertTrue(self.retain()['download_verified'])

    def test_download_retry_never_reuploads(self):
        self.api.download_faults = [httpx.ReadTimeout('injected')]
        self.assertTrue(self.retain()['download_verified'])
        self.assertEqual(self.api.uploads, 1)

    def test_corrupt_download_is_not_accepted_or_overwritten(self):
        self.api.corrupt_download = True
        for _ in range(2):
            with self.assertRaisesRegex(ValueError, 'Downloaded archive differs'): self.retain()
        self.assertEqual(self.api.uploads, 1)
        self.assertFalse((self.options['ledger']/'receipt.json').exists())

    def test_remote_change_during_download_is_rejected(self):
        self.api.change_on_download = True
        with self.assertRaisesRegex(ValueError, 'changed during verification'): self.retain()
        self.assertEqual(self.api.uploads, 1)

    def test_existing_corrupt_object_is_not_overwritten(self):
        sha = hashlib.sha256(self.archive.read_bytes()).hexdigest()
        self.api.objects[self.options['prefix']+'/'+sha+'.tgz'] = b'z'*len(self.archive.read_bytes())
        with self.assertRaisesRegex(ValueError, 'Downloaded archive differs'): self.retain()
        self.assertEqual(self.api.uploads, 0)

    def test_saved_receipt_rejects_missing_remote_without_healing(self):
        self.retain(); self.api.objects.clear()
        with self.assertRaisesRegex(ValueError, 'missing'): self.retain()
        self.assertEqual(self.api.uploads, 1)

    def test_saved_receipt_rejects_same_size_modified_object(self):
        receipt = self.retain()
        self.api.objects[receipt['path']] = b'z'*receipt['bytes']
        with self.assertRaisesRegex(ValueError, 'Xet identity changed'): self.retain()

    def test_resume_cannot_change_source_or_manifest(self):
        self.retain()
        self.archive.write_bytes(b'other archive')
        with self.assertRaisesRegex(ValueError, 'Resume inputs differ'): self.retain()
        self.assertEqual(self.api.uploads, 1)

    def test_public_bucket_never_receives_archive(self):
        self.api.private = False
        with self.assertRaisesRegex(ValueError, 'private'): self.retain()
        self.assertEqual(self.api.uploads, 0)

    def test_existing_owner_excludes_competing_uploader(self):
        with self.transport.locked(self.options['ledger']):
            with self.assertRaises(BlockingIOError): self.retain()
        self.assertEqual(self.api.uploads, 0)

    def test_path_traversal_rejected_before_network(self):
        self.options['prefix'] = '../other'
        with self.assertRaisesRegex(ValueError, 'Unsafe prefix'): self.retain()
        self.assertEqual(self.api.uploads, 0)

    def test_upload_intent_written_before_network(self):
        original = self.api.batch_bucket_files
        def observed(*args, **kwargs):
            self.assertTrue((self.options['ledger']/'intent.json').exists())
            self.assertTrue(read(self.options['ledger']/'upload-01.json')['remote_absent_before_call'])
            return original(*args, **kwargs)
        self.api.batch_bucket_files = observed
        self.retain()


if __name__ == '__main__': unittest.main()
