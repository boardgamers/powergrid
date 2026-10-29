"""Submission/remote-binding failure tests; all HF operations mocked."""
from contextlib import ExitStack
import fcntl
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import manage_current_auction_first_bucket_v3 as m


class ManagerTests(unittest.TestCase):
    def setUp(self):
        self.stack=ExitStack();self.addCleanup(self.stack.close)
        self.folder=Path(self.stack.enter_context(TemporaryDirectory()))/'hf'
        self.source={'revision':'a'*40,'sha256':'b'*64,'manifest_sha256':'c'*64}
        self.env={'SOURCE_SHA256':'d'*64,'SUPERVISOR_SHA256':'b'*64}
        original,row=m.plan()
        self.stack.enter_context(patch.object(m,'plan',return_value=(original,row)))
        self.stack.enter_context(patch.object(m,'public_environment',return_value=self.env))
        self.api=Mock();self.api.run_job.return_value=SimpleNamespace(id='e'*24)

    def launch(self):return m.launch_once(self.api,self.folder,self.source,'mock-secret-never-logged')

    def remote(self,guard):
        return {'id':guard['job_id'],'dockerImage':m.IMAGE,'flavor':'cpu-upgrade','timeout':86400,
            'command':['bash','-lc',m.bootstrap()],'arguments':[],'environment':dict(self.env),
            'labels':{'name':m.ATTEMPT},'status':{'stage':'RUNNING'},
            'secrets':{'HF_TOKEN':'mock-secret-never-logged'}}

    def test_single_attempt_uses_exact_allocation_and_original_failure_link(self):
        guard=self.launch();kwargs=self.api.run_job.call_args.kwargs
        self.assertEqual(kwargs['timeout'],'24h');self.assertEqual(kwargs['flavor'],'cpu-upgrade')
        self.assertEqual(kwargs['command'],['bash','-lc',m.bootstrap()])
        self.assertEqual(guard['prior_failed_attempts'],[])
        self.assertEqual(guard['original_name'],m.NAME)
        self.assertFalse(guard['automatic_job_retries'])
        self.assertNotIn('mock-secret', (self.folder/'launch.json').read_text())
        self.assertTrue((self.folder/'launch-intent.json').exists())

    def test_repeat_returns_exact_handle_without_resubmission(self):
        first=self.launch();self.assertEqual(self.launch(),first);self.api.run_job.assert_called_once()

    def test_unknown_launch_intent_blocks_submission(self):
        self.folder.mkdir();m.save(self.folder/'launch-intent.json',{'unknown':True})
        with self.assertRaisesRegex(ValueError,'Unresolved launch'):self.launch()
        self.api.run_job.assert_not_called()

    def test_api_failure_preserves_intent_and_cannot_retry(self):
        self.api.run_job.side_effect=TimeoutError('mock response timeout')
        with self.assertRaises(TimeoutError):self.launch()
        with self.assertRaisesRegex(ValueError,'Unresolved launch'):self.launch()
        self.api.run_job.assert_called_once();self.assertFalse((self.folder/'launch.json').exists())

    def test_lock_prevents_competing_submission(self):
        self.folder.mkdir()
        with (self.folder/'.launch.lock').open('a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            with self.assertRaises(BlockingIOError):self.launch()
        self.api.run_job.assert_not_called()

    def test_default_launch_validates_without_api_or_output(self):
        with patch.object(m,'source_checked',return_value=self.source),patch.object(m,'HfApi') as api:
            value=m.launch()
        self.assertFalse(value['execute']);self.assertEqual(value['admitted_games'],16)
        api.assert_not_called();self.assertFalse(self.folder.exists())

    def test_remote_wrong_effective_timeout_or_hardware_is_rejected(self):
        guard=self.launch()
        for key,value in [('timeout',10800),('flavor','a10g-large'),('dockerImage','other')]:
            with self.subTest(key=key):
                raw=self.remote(guard);raw[key]=value
                with self.assertRaisesRegex(ValueError,'allocation differs'):m.bind_remote(raw,guard,self.source)

    def test_remote_changed_source_command_or_handle_is_rejected(self):
        guard=self.launch()
        for key,value in [('environment',{'SOURCE_SHA256':'f'*64}),('command',['bash','-lc','echo wrong']),('id','f'*24)]:
            with self.subTest(key=key):
                raw=self.remote(guard);raw[key]=value
                with self.assertRaises(ValueError):m.bind_remote(raw,guard,self.source)

    def test_remote_status_is_whitelisted_and_never_exposes_environment_or_secrets(self):
        guard=self.launch();result=m.bind_remote(self.remote(guard),guard,self.source)
        self.assertEqual(result['timeout_seconds'],86400);self.assertTrue(result['public_configuration_verified'])
        self.assertNotIn('environment',result);self.assertNotIn('secrets',result)
        self.assertNotIn('mock-secret',str(result))

    def test_running_collection_does_not_fetch_logs_or_generate_results(self):
        with patch.object(m,'OUT',self.folder),patch.object(m,'source_checked',return_value=self.source),\
             patch.object(m,'check',return_value={'stage':'RUNNING','job_id':'e'*24}),patch.object(m,'HfApi') as api:
            value=m.collect()
        self.assertEqual(value['stage'],'RUNNING');api.assert_not_called()
        self.assertFalse((self.folder/'original.log').exists())


    def test_unknown_returned_handle_preserves_intent_without_retry(self):
        self.api.run_job.return_value=SimpleNamespace(id='unknown')
        with self.assertRaisesRegex(ValueError,'Unknown handle'):self.launch()
        with self.assertRaisesRegex(ValueError,'Unresolved launch'):self.launch()
        self.api.run_job.assert_called_once()

    def test_changed_saved_launch_intent_cannot_reuse_handle(self):
        self.launch();path=self.folder/'launch-intent.json';value=m.read(path)
        value['original_name']='another-row';path.unlink();m.save(path,value)
        with self.assertRaisesRegex(ValueError,'Launch binding differs'):self.launch()
        self.api.run_job.assert_called_once()

    def test_unknown_remote_stage_is_not_a_failed_job(self):
        guard=self.launch();raw=self.remote(guard);raw['status']['stage']='NETWORK_UNKNOWN'
        with self.assertRaisesRegex(ValueError,'Unknown HF stage'):m.bind_remote(raw,guard,self.source)

    def test_multiple_final_bucket_receipts_are_not_accepted(self):
        import json
        self.folder.mkdir();log=self.folder/'original.log'
        row=json.dumps({'attempt_id':m.ATTEMPT,'bucket_final_evidence':{}})
        log.write_text(row+'\n'+row+'\n')
        with self.assertRaisesRegex(ValueError,'Missing/ambiguous final'):m.read_final(log)


if __name__=='__main__':unittest.main()
