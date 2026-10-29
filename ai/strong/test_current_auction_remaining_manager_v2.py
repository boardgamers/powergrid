"""Durable dispatch/failure behavior, without remote jobs or game execution."""
from contextlib import ExitStack
from copy import deepcopy
import fcntl
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import manage_current_auction_remaining_v2 as m


class RemainingManagerTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack(); self.addCleanup(self.stack.close)
        self.root = Path(self.stack.enter_context(TemporaryDirectory()))
        self.original, self.rows = m.plan(); self.row = self.rows[0]
        self.folder = self.root/'jobs'/m.worker.attempt_name(self.row['name'])
        self.source = {'revision':'a'*40,'sha256':'b'*64,'manifest_sha256':'c'*64}
        source_path = self.root/'synthetic-source.json'; m.durable(source_path,self.source)
        self.stack.enter_context(patch.object(m,'SOURCE',source_path))
        self.env = {'SOURCE_SHA256':'d'*64,'SUPERVISOR_SHA256':'b'*64}
        self.stack.enter_context(patch.object(m,'public_environment',return_value=self.env))
        self.api = Mock(); self.api.run_job.return_value = SimpleNamespace(id='e'*24)

    def launch(self): return m.launch_once(self.api,self.folder,self.source,self.row,'mock-secret-never-logged')

    def remote(self, guard, stage='RUNNING'):
        return {'id':guard['job_id'],'dockerImage':m.first.IMAGE,'flavor':'cpu-upgrade','timeout':86400,
            'command':['bash','-lc',m.bootstrap()],'arguments':[],'environment':dict(self.env),
            'labels':{'name':guard['attempt_id']},'status':{'stage':stage},
            'secrets':{'HF_TOKEN':'mock-secret-never-logged'}}

    def test_single_attempt_uses_exact_resources_and_frozen_first_audit(self):
        guard = self.launch(); options = self.api.run_job.call_args.kwargs
        self.assertEqual(options['timeout'],'24h'); self.assertEqual(options['flavor'],'cpu-upgrade')
        self.assertEqual(options['command'],['bash','-lc',m.bootstrap()])
        self.assertEqual(guard['first_recovery_result_sha256'],m.FIRST_RESULT_SHA)
        self.assertIsNone(guard['original_failed_handle']); self.assertFalse(guard['automatic_retries'])
        self.assertNotIn('mock-secret',(self.folder/'launch.json').read_text())
        self.assertNotIn('mock-secret',(self.folder/'launch-intent.json').read_text())

    def test_same_guard_is_reused_without_resubmission(self):
        first = self.launch(); self.assertEqual(self.launch(),first); self.api.run_job.assert_called_once()

    def test_intent_without_handle_blocks_any_resubmission(self):
        self.folder.mkdir(parents=True); m.durable(self.folder/'launch-intent.json',{'unknown':True})
        with self.assertRaisesRegex(ValueError,'Unresolved launch'): self.launch()
        self.api.run_job.assert_not_called()

    def test_response_timeout_preserves_intent_and_forbids_retry(self):
        self.api.run_job.side_effect = TimeoutError('mock observation timeout')
        with self.assertRaises(TimeoutError): self.launch()
        with self.assertRaisesRegex(ValueError,'Unresolved launch'): self.launch()
        self.api.run_job.assert_called_once(); self.assertFalse((self.folder/'launch.json').exists())

    def test_competing_launch_cannot_pass_lock(self):
        self.folder.mkdir(parents=True)
        with (self.folder/'.launch.lock').open('a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            with self.assertRaises(BlockingIOError): self.launch()
        self.api.run_job.assert_not_called()

    def test_default_cycle_validates_without_network_or_output(self):
        with patch.object(m,'OUT',self.root/'absent'), patch.object(m,'source_checked',return_value=self.source), patch.object(m,'HfApi') as api:
            result = m.cycle()
        self.assertFalse(result['execute']); api.assert_not_called(); self.assertFalse((self.root/'absent').exists())

    def test_original_or_first_recovery_row_cannot_launch(self):
        row = next(r for r in self.original['rows'] if r['name']==m.worker.base.FAILED_NAME)
        with self.assertRaisesRegex(ValueError,'Only fixed'): m.launch_once(self.api,self.folder,self.source,row,'mock')
        self.api.run_job.assert_not_called(); self.assertFalse(self.folder.exists())

    def test_changed_row_cannot_reuse_an_admitted_name(self):
        row = deepcopy(self.row); row['shard']['seed']='changed-seed'
        with self.assertRaisesRegex(ValueError,'Only fixed'): m.binding(self.source,row)

    def test_remote_allocation_must_be_actual_twenty_four_hours_cpu(self):
        guard = self.launch()
        for key,value in [('timeout',10800),('flavor','a10g-large'),('dockerImage','wrong')]:
            raw = self.remote(guard); raw[key]=value
            with self.subTest(key=key), self.assertRaisesRegex(ValueError,'allocation differs'): m.bind_remote(raw,guard,self.source,self.row)

    def test_remote_source_command_name_handle_and_unknown_stage_rejected(self):
        guard = self.launch()
        for key,value in [('environment',{}),('command',['false']),('id','f'*24),('labels',{'name':'foreign'}),('status',{'stage':'UNKNOWN'})]:
            raw = self.remote(guard); raw[key]=value
            with self.subTest(key=key), self.assertRaises(ValueError): m.bind_remote(raw,guard,self.source,self.row)

    def test_all_waiting_stages_are_live_without_logs_or_secret_output(self):
        guard = self.launch()
        for stage in m.WAITING:
            status = m.bind_remote(self.remote(guard,stage),guard,self.source,self.row)
            self.assertEqual(m.collect_one(self.api,self.folder,self.source,self.row,status),status)
            self.assertNotIn('environment',status); self.assertNotIn('secrets',status); self.assertNotIn('mock-secret',str(status))
        self.api.fetch_job_logs.assert_not_called()

    def test_capacity_and_order_follow_all_fixed_rows_not_results(self):
        records = {r['name']:{'stage':'RUNNING'} for r in self.rows[:63]}
        self.assertEqual(m.dispatch_plan(self.rows,records,64),self.rows[63:64])
        records[self.rows[63]['name']]={'stage':'STARTING'}
        self.assertEqual(m.dispatch_plan(self.rows,records,64),[])
        records[self.rows[0]['name']]={'stage':'COMPLETED'}
        self.assertEqual(m.dispatch_plan(self.rows,records,64),self.rows[64:65])

    def test_failed_or_oversubscribed_or_foreign_state_never_dispatches(self):
        for records in ({self.row['name']:{'stage':'ERROR'}}, {'foreign':{'stage':'RUNNING'}},
                        {r['name']:{'stage':'RUNNING'} for r in self.rows[:65]}):
            with self.assertRaises(ValueError): m.dispatch_plan(self.rows,records,64)
        for limit in (-1,65,True):
            with self.assertRaises(ValueError): m.dispatch_plan(self.rows,{},limit)

    def test_changed_saved_guard_or_intent_is_rejected_without_api_retry(self):
        guard = self.launch(); guard['first_recovery_result_sha256']='f'*64
        m.durable(self.folder/'launch.json',guard)
        with self.assertRaisesRegex(ValueError,'binding differs'): self.launch()
        self.api.run_job.assert_called_once()

    def test_remote_observation_timeout_keeps_saved_handle_for_next_cycle(self):
        with patch.object(m,'OUT',self.root), patch.object(m,'source_checked',return_value=self.source), \
             patch.object(m,'HfApi',return_value=self.api), patch.object(m,'get_token',return_value='mock'), \
             patch.object(m,'check_one',side_effect=TimeoutError('temporary')):
            with self.assertRaises(TimeoutError): m.cycle(True,1,0)
        guard = m.checked_guard(self.folder,self.source,self.row)
        self.assertEqual(guard['job_id'],'e'*24); self.assertFalse((self.root/'STOP.json').exists())
        with patch.object(m,'OUT',self.root), patch.object(m,'source_checked',return_value=self.source), \
             patch.object(m,'HfApi',return_value=self.api), patch.object(m,'check_one',return_value={'stage':'RUNNING','job_id':'e'*24}):
            result = m.cycle(True,0,0)
        self.assertEqual(result['submitted'],1); self.api.run_job.assert_called_once()

    def test_raw_audit_failure_blocks_following_submissions_and_preserves_stop(self):
        self.launch(); self.api.run_job.reset_mock()
        with patch.object(m,'OUT',self.root), patch.object(m,'source_checked',return_value=self.source), \
             patch.object(m,'HfApi',return_value=self.api), patch.object(m,'check_one',return_value={'stage':'COMPLETED','job_id':'e'*24}), \
             patch.object(m,'collect_one',side_effect=ValueError('invalid original raw evidence')):
            with self.assertRaises(ValueError): m.cycle(True,64,4)
        self.api.run_job.assert_not_called(); self.assertEqual(m.read(self.root/'STOP.json')['job_id'],'e'*24)

    def test_failed_terminal_without_final_archive_keeps_log_and_no_review(self):
        guard = self.launch(); self.api.fetch_job_logs.return_value=['{"partial":true}']
        status = m.bind_remote(self.remote(guard,'ERROR'),guard,self.source,self.row)
        with self.assertRaisesRegex(ValueError,'Missing/ambiguous'): m.collect_one(self.api,self.folder,self.source,self.row,status)
        self.assertTrue((self.folder/'original.log').exists()); self.assertEqual(m.read(self.folder/'terminal.json')['stage'],'ERROR')
        self.assertFalse((self.folder/'review.json').exists())

    def test_preexisting_stop_or_unknown_directory_cannot_launch(self):
        with patch.object(m,'OUT',self.root), patch.object(m,'source_checked',return_value=self.source), patch.object(m,'HfApi',return_value=self.api):
            m.durable(self.root/'STOP.json',{'preserved':True})
            with self.assertRaisesRegex(ValueError,'Dispatch stopped'): m.cycle(True,64,0)
            (self.root/'STOP.json').unlink(); (self.root/'jobs/foreign').mkdir(parents=True)
            with self.assertRaisesRegex(ValueError,'Unknown job directory'): m.cycle(True,64,0)
        self.api.run_job.assert_not_called()


if __name__ == '__main__': unittest.main()
