"""Storage lifecycle tests using synthetic final-job transport fixtures only."""
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import selected_public_policy_final_collection_v1 as collector
import selected_public_policy_final_streaming_v1 as stream
import test_selected_public_policy_final_collection_v1 as fixtures


class StreamingAuditTests(unittest.TestCase):
    def setUp(self):
        self.f = fixtures.FinalCollectionTests()
        self.f.setUp(); self.addCleanup(self.f.doCleanups)
        self.scratch = self.f.root/'scratch'
        self.receipt = self.f.root/'reviews/collected.json'

    def invoke(self, *, receipt=None, purpose='initial_collection', raw_error=None):
        with patch.object(collector,'artifact_identity',return_value=self.f.identity), \
             patch.object(collector,'audit_shard',return_value=deepcopy(self.f.audit),side_effect=raw_error):
            return stream.audit_archive(self.f.archive,self.f.source,self.f.release,self.f.launch,
                self.f.evidence,self.f.bootstrap,hf_stage='COMPLETED',scratch_root=self.scratch,
                receipt=receipt or self.receipt,purpose=purpose,minimum_free_bytes=0)

    def workdirs(self):
        return list(self.scratch.glob('original-final-audit-*'))

    def test_success_keeps_original_and_durable_review_removes_only_own_copy(self):
        self.scratch.mkdir(); sentinel=self.scratch/'unrelated';sentinel.write_text('preserve')
        before=collector.digest(self.f.archive)
        result=self.invoke();saved=json.loads(self.receipt.read_text())
        self.assertTrue(result['temporary_extraction_removed']);self.assertTrue(result['archive_retained'])
        self.assertEqual(before,collector.digest(self.f.archive))
        self.assertEqual(saved['review_sha256'],stream.object_hash(saved['review']))
        self.assertEqual(result['receipt_sha256'],collector.digest(self.receipt))
        self.assertFalse(saved['qualified']);self.assertFalse(self.workdirs())
        self.assertEqual(sentinel.read_text(),'preserve')

    def test_raw_audit_failure_preserves_original_and_scratch(self):
        before=collector.digest(self.f.archive)
        with self.assertRaisesRegex(ValueError,'missing decision'):
            self.invoke(raw_error=ValueError('missing decision'))
        self.assertFalse(self.receipt.exists());self.assertEqual(collector.digest(self.f.archive),before)
        work=self.workdirs();self.assertEqual(len(work),1)
        self.assertTrue((work[0]/'evidence/manifest.json').exists())
        failure=json.loads((work[0]/'failure.json').read_text())
        self.assertFalse(failure['audit_receipt_published']);self.assertFalse(failure['automatic_retries'])

    def test_insufficient_disk_rejects_before_extracting(self):
        with patch.object(stream.shutil,'disk_usage',return_value=SimpleNamespace(free=0)), \
             patch.object(stream,'extract_verified') as extract:
            with self.assertRaisesRegex(ValueError,'Insufficient free space'):self.invoke()
        extract.assert_not_called();self.assertFalse(self.receipt.exists())
        self.assertTrue((self.workdirs()[0]/'failure.json').exists())

    def test_receipt_write_failure_cannot_delete_extraction(self):
        real=stream.durable_write
        def write(path,value,**kwargs):
            if Path(path)==self.receipt:raise OSError('synthetic receipt disk failure')
            return real(path,value,**kwargs)
        with patch.object(stream,'durable_write',side_effect=write):
            with self.assertRaisesRegex(OSError,'receipt disk failure'):self.invoke()
        self.assertFalse(self.receipt.exists())
        self.assertTrue((self.workdirs()[0]/'evidence/manifest.json').exists())

    def test_cleanup_failure_keeps_committed_receipt_and_cannot_restart(self):
        with patch.object(stream.shutil,'rmtree',side_effect=OSError('synthetic cleanup failure')):
            with self.assertRaisesRegex(OSError,'cleanup failure'):self.invoke()
        self.assertTrue(self.receipt.exists())
        failure=json.loads((self.workdirs()[0]/'failure.json').read_text())
        self.assertTrue(failure['audit_receipt_published'])
        before=collector.digest(self.receipt)
        with patch.object(stream,'verify_artifacts') as verify:
            with self.assertRaisesRegex(ValueError,'existing audit receipt'):self.invoke()
        verify.assert_not_called();self.assertEqual(collector.digest(self.receipt),before)

    def test_separate_independent_audit_rechecks_raw_archive(self):
        real=stream.verify_artifacts
        with patch.object(stream,'verify_artifacts',wraps=real) as verify:
            first=self.invoke()
            second=self.invoke(receipt=self.f.root/'reviews/independent.json',purpose='independent_final_audit')
        self.assertEqual(verify.call_count,2)
        self.assertEqual(first['review_sha256'],second['review_sha256'])
        self.assertFalse(self.workdirs())

    def test_archive_mutation_prevents_publication_and_cleanup(self):
        real=stream.verify_artifacts
        def mutate(*args,**kwargs):
            result=real(*args,**kwargs)
            self.f.archive.write_bytes(self.f.archive.read_bytes()+b'changed')
            return result
        with patch.object(stream,'verify_artifacts',side_effect=mutate):
            with self.assertRaisesRegex(ValueError,'archive changed during audit'):self.invoke()
        self.assertFalse(self.receipt.exists());self.assertTrue(self.workdirs())

    def test_receipt_cannot_be_deleted_with_scratch_or_written_into_source(self):
        for path in (self.scratch/'lost.json',self.f.source/'frozen.json'):
            with self.assertRaisesRegex(ValueError,'outlive scratch|frozen source'):
                self.invoke(receipt=path)
            self.assertFalse(path.exists())


if __name__ == '__main__':unittest.main()
