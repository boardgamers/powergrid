"""Synthetic child lifecycle with real archive/transport code and fake storage.

The admission inspector and evaluator are deliberately mocked; no game executes.
These tests verify that both child completion and child failure preserve output.
"""
import contextlib
import io
from pathlib import Path
import unittest
from unittest.mock import patch

from test_current_auction_bucket_worker_v3 import WorkerTests, SOURCE
from test_checkpoint_bucket_transport_v3 import FakeAPI
import current_auction_bucket_worker_v3 as w


class FlowTests(unittest.TestCase):
    def setUp(self):
        self.fixture=WorkerTests();self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)
        self.expected=self.fixture.inspect();self.api=FakeAPI()

    def child(self, command, evaluation, supervisor, context, upload, period, *, fail=False):
        supervisor.mkdir();w.save(supervisor/'context.json',context)
        raw=Path(self.expected['raw_output']);raw.mkdir(parents=True)
        w.save(raw/'fixture.json',{'synthetic':True,'not_game_data':True})
        w.save(raw/'manifest.json',{'fixture.json':w.digest(raw/'fixture.json')})
        checkpoint=supervisor/(self.expected['attempt_id']+'-checkpoint-0001');checkpoint.mkdir()
        w.save(checkpoint/'fixture.json',{'synthetic':True,'not_game_data':True})
        w.save(checkpoint/'manifest.json',{'fixture.json':w.digest(checkpoint/'fixture.json')})
        receipt=upload(checkpoint)
        w.save(supervisor/'fixture.receipt.json',receipt)
        result={'stage':'child_exited','attempt_id':context['attempt_id'],'child_returncode':1 if fail else 0,
            'retained_episodes':list(range(self.expected['row']['shard']['games'])),
            'expected_episodes':self.expected['row']['shard']['games'],'checkpoints':1,
            'raw_audited':False,'qualified':False,'automatic_retries':False}
        w.save(supervisor/'supervisor-result.json',result)
        if fail:raise RuntimeError('synthetic evaluator failure')
        return result

    def invoke(self, fail):
        f=self.fixture
        with patch.object(w,'inspect',return_value=self.expected),patch('huggingface_hub.HfApi',return_value=self.api),\
                patch.object(w.base,'child_live',return_value=True),\
                patch.object(w.retention,'supervise',side_effect=lambda *a:self.child(*a,fail=fail)) as run,\
                contextlib.redirect_stdout(io.StringIO()):
            try:return w.run(f.bundle,f.seal(),SOURCE,f.output,execute=True)
            finally:self.assertEqual(run.call_count,1)

    def test_success_preserves_final_bucket_output_and_defers_versioned_promotion(self):
        result=self.invoke(False)
        self.assertTrue(result['versioned_archive_pending']);self.assertFalse(result['qualified'])
        self.assertEqual(self.api.uploads,2)
        f=self.fixture;receipt=w.read(f.output/'final-bucket-receipt.json')
        folder=w.archives.download_archive(receipt,self.expected['attempt_id']+'-final',f.root/'downloaded',self.api)
        self.assertEqual(w.read(folder/'run-status.json')['stage'],'child_complete_pending_independent_audit')
        self.assertTrue((folder/'transport-ledgers'/ (self.expected['attempt_id']+'-checkpoint-0001')/'receipt.json').exists())

    def test_child_failure_remains_failure_but_final_raw_output_is_retained(self):
        with self.assertRaisesRegex(RuntimeError,'synthetic evaluator failure'):self.invoke(True)
        f=self.fixture;receipt=w.read(f.output/'final-bucket-receipt.json')
        folder=w.archives.download_archive(receipt,self.expected['attempt_id']+'-final',f.root/'failed-download',self.api)
        self.assertEqual(w.read(folder/'run-status.json')['stage'],'failed_preserved')
        self.assertTrue((folder/'raw/fixture.json').is_file())
        self.assertEqual(self.api.uploads,2)


if __name__=='__main__':unittest.main()
