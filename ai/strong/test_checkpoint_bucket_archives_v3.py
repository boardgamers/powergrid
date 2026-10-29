"""Archive and collector transport tests with a fault-injected object store."""
import io
from pathlib import Path
import tarfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import checkpoint_bucket_archives_v3 as a
import promote_bucket_evidence_v3 as promotion
from test_checkpoint_bucket_transport_v3 import TransportTests, FakeAPI


class ArchiveTests(unittest.TestCase):
    def setUp(self):
        import tempfile
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.folder = self.root/'pg-bucket-fixture-checkpoint-0001'; self.folder.mkdir()
        (self.folder/'record.json').write_text('{"existing_fixture":true}\n')
        import json
        (self.folder/'manifest.json').write_text(json.dumps({'record.json':a.digest(self.folder/'record.json')}))
        self.api = FakeAPI()

    def upload(self): return a.upload_directory(self.folder, self.root/'ledgers', self.api)

    def test_uploaded_archive_independently_downloads_to_exact_tree(self):
        evidence = self.upload()
        destination = self.root/'downloaded'/self.folder.name
        a.download_archive(evidence, self.folder.name, destination, self.api)
        self.assertEqual(a.digest(destination/'record.json'),a.digest(self.folder/'record.json'))
        self.assertEqual(a.digest(destination/'manifest.json'),evidence['manifest_sha256'])
        self.assertEqual(self.api.uploads,1)

    def test_changed_tree_refuses_archive_before_network(self):
        (self.folder/'record.json').write_text('changed')
        with self.assertRaisesRegex(ValueError,'Pinned file changed'):self.upload()
        self.assertEqual(self.api.uploads,0)

    def test_corrupted_remote_download_never_extracts(self):
        evidence = self.upload();self.api.corrupt_download=True
        destination=self.root/'extracted'
        with self.assertRaisesRegex(ValueError,'Downloaded archive changed'):
            a.download_archive(evidence,self.folder.name,destination,self.api)
        self.assertFalse(destination.exists())

    def test_missing_object_remains_missing_without_upload(self):
        evidence=self.upload();self.api.objects.clear()
        with self.assertRaisesRegex(ValueError,'missing or changed'):
            a.download_archive(evidence,self.folder.name,self.root/'extracted',self.api)
        self.assertEqual(self.api.uploads,1)

    def test_foreign_checkpoint_path_is_rejected(self):
        evidence=self.upload();evidence['path']='other/'+evidence['path']
        with self.assertRaisesRegex(ValueError,'Foreign bucket object'):
            a.download_archive(evidence,self.folder.name,self.root/'extracted',self.api)

    def test_archive_path_traversal_is_rejected_without_extracting(self):
        archive=self.root/'unsafe.tgz'
        with tarfile.open(archive,'w:gz') as bundle:
            for name,body in [('manifest.json',b'{}'),('../escape',b'bad')]:
                info=tarfile.TarInfo(name);info.size=len(body);bundle.addfile(info,io.BytesIO(body))
        import hashlib
        with self.assertRaisesRegex(ValueError,'Unsafe archive'):
            a.verify_archive(archive,hashlib.sha256(b'{}').hexdigest())
        self.assertFalse((self.root.parent/'escape').exists())

    def test_existing_archive_cannot_be_silently_rebuilt(self):
        self.upload()
        with self.assertRaisesRegex(ValueError,'Inspect existing archive'):self.upload()
        self.assertEqual(self.api.uploads,1)

    def test_unknown_promotion_keeps_intent_and_never_retries(self):
        evidence=self.upload();destination=self.root/'promotion'/self.folder.name
        a.download_archive(evidence,self.folder.name,destination,self.api)
        self.api.model_info=lambda repo:SimpleNamespace(private=True)
        self.api.file_exists=lambda *args:False
        ledger=self.root/'promotion-ledger'
        with patch.object(promotion,'upload_evidence',side_effect=ConnectionError('unknown')) as upload:
            with self.assertRaises(ConnectionError):promotion.promote(destination,evidence,ledger,self.api)
            self.assertTrue((ledger/'intent.json').is_file())
            with self.assertRaisesRegex(ValueError,'previous promotion'):promotion.promote(destination,evidence,ledger,self.api)
            self.assertEqual(upload.call_count,1)


if __name__=='__main__':unittest.main()
