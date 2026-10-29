"""Pack integrity and bounded submission tests; no real HF calls or games."""
from contextlib import ExitStack
import fcntl
import json
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import Mock,patch

import manage_current_auction_bucket_remaining_v3 as m


class PackTests(unittest.TestCase):
    def setUp(self):
        self.stack=ExitStack();self.addCleanup(self.stack.close)
        self.root=Path(self.stack.enter_context(TemporaryDirectory()));self.pack=self.root/'pack';self.pack.mkdir()
        self.dest=self.root/'selected';self.name=m.first.NAME;self.attempt=m.first.ATTEMPT
        self.row=self.pack/'rows'/self.attempt;self.row.mkdir(parents=True)
        original=m.first.PRE/'bundle'
        for name in m.packer.COMMON:shutil.copyfile(original/name,self.pack/name)
        for name in m.packer.ROW_FILES:shutil.copyfile(original/name,self.row/name)
        m.save(self.pack/'index.json',{'version':3,'scope':'untouched_fixed_confirmation_rows',
            'automatic_job_retries':False,'rows':{self.name:{'attempt_id':self.attempt,'bundle_manifest_sha256':m.digest(self.row/'manifest.json')}}})
        self.sha=m.manifest(self.pack)

    def select(self):return m.packer.materialize(self.pack,self.sha,self.name,self.dest)

    def rewrite(self,path,value):path.unlink();m.save(path,value)

    def test_materialized_bundle_matches_prepared_manifest_byte_for_byte(self):
        sha=self.select();self.assertEqual(sha,m.digest(m.first.PRE/'bundle/manifest.json'))
        self.assertEqual(m.worker.base.tree(self.dest,'manifest.json',sha),m.read(self.row/'manifest.json'))

    def test_foreign_row_cannot_materialize(self):
        with self.assertRaisesRegex(ValueError,'outside prepared'):m.packer.materialize(self.pack,self.sha,'other',self.dest)
        self.assertFalse(self.dest.exists())

    def test_control_cannot_select_another_canonical_game(self):
        p=self.row/'control.json';control=m.read(p);control['original_name']='another-game';self.rewrite(p,control)
        p=self.row/'manifest.json';pins=m.read(p);pins['control.json']=m.digest(self.row/'control.json');self.rewrite(p,pins)
        p=self.pack/'index.json';index=m.read(p);index['rows'][self.name]['bundle_manifest_sha256']=m.digest(self.row/'manifest.json');self.rewrite(p,index)
        self.sha=m.manifest(self.pack)
        with self.assertRaisesRegex(ValueError,'cannot retry'):self.select()
        self.assertFalse(self.dest.exists())

    def test_tampered_row_manifest_rejected_before_copy(self):
        (self.row/'manifest.json').write_text('{}')
        with self.assertRaises(ValueError):self.select()
        self.assertFalse(self.dest.exists())

    def test_tampered_shared_worker_rejected_before_copy(self):
        (self.pack/m.worker.ENTRY).write_text('bad source')
        with self.assertRaises(ValueError):self.select()
        self.assertFalse(self.dest.exists())

    def test_rebound_index_attempt_rejected(self):
        p=self.pack/'index.json';index=m.read(p);index['rows'][self.name]['attempt_id']='other';self.rewrite(p,index);self.sha=m.manifest(self.pack)
        with self.assertRaisesRegex(ValueError,'mismatch'):self.select()

    def test_missing_admission_rejected_even_with_valid_outer_hash(self):
        (self.row/'admission.json').unlink();self.sha=m.manifest(self.pack)
        with self.assertRaisesRegex(ValueError,'Incomplete'):self.select()

    def test_existing_destination_not_overwritten(self):
        self.dest.mkdir();(self.dest/'important').write_text('preserve')
        with self.assertRaisesRegex(ValueError,'Destination'):self.select()
        self.assertEqual((self.dest/'important').read_text(),'preserve')

    def test_destination_cannot_mutate_verified_pack(self):
        self.dest=self.pack/'selected'
        with self.assertRaisesRegex(ValueError,'Destination'):self.select()
        self.assertFalse(self.dest.exists())

    def test_default_pack_run_does_not_execute_games(self):
        with patch.object(m.worker,'run',return_value={'valid':True,'execute':False}) as run:
            result=m.packer.run(self.pack,self.sha,self.name,self.dest,self.root/'source',self.root/'output')
        self.assertFalse(result['execute']);self.assertFalse(run.call_args.kwargs['execute'])
        self.assertFalse((self.root/'output').exists())


class ManagerTests(unittest.TestCase):
    def setUp(self):
        self.stack=ExitStack();self.addCleanup(self.stack.close)
        self.folder=Path(self.stack.enter_context(TemporaryDirectory()))/'hf'
        original,rows=m.plan();self.rows=rows;self.row=rows[0]
        self.stack.enter_context(patch.object(m,'plan',return_value=(original,rows)))
        self.source={'revision':'a'*40,'sha256':'b'*64,'manifest_sha256':'c'*64}
        self.env={'SOURCE_SHA256':'d'*64,'SUPERVISOR_SHA256':'b'*64}
        self.stack.enter_context(patch.object(m,'public_environment',return_value=self.env))
        self.api=Mock();self.api.run_job.return_value=SimpleNamespace(id='e'*24)

    def launch(self):return m.launch_once(self.api,self.folder,self.source,self.row,'test-secret-never-recorded')

    def remote(self,guard):return {'id':guard['job_id'],'dockerImage':m.first.IMAGE,'flavor':'cpu-upgrade','timeout':86400,
        'command':['bash','-lc',m.bootstrap()],'arguments':[],'environment':self.env,
        'labels':{'name':m.attempt(self.row['name'])},'status':{'stage':'RUNNING'},'secrets':{'HF_TOKEN':'test-secret-never-recorded'}}

    def test_single_launch_binds_frozen_row_and_prepared_source(self):
        g=self.launch();kwargs=self.api.run_job.call_args.kwargs
        self.assertEqual(kwargs['timeout'],'24h');self.assertEqual(kwargs['flavor'],'cpu-upgrade')
        self.assertEqual(g['source'],self.source);self.assertEqual(g['original_name'],self.row['name'])
        self.assertEqual(g['prior_failed_attempts'],[]);self.assertFalse(g['automatic_job_retries'])
        self.assertNotIn('test-secret',(self.folder/'launch.json').read_text())

    def test_repeat_reuses_handle_without_submission(self):
        original=self.launch();self.assertEqual(self.launch(),original);self.api.run_job.assert_called_once()

    def test_intent_without_handle_never_retries(self):
        self.folder.mkdir();m.save(self.folder/'launch-intent.json',{'unknown':True})
        with self.assertRaisesRegex(ValueError,'Unresolved launch'):self.launch()
        self.api.run_job.assert_not_called()

    def test_response_timeout_preserves_intent_and_blocks_second_call(self):
        self.api.run_job.side_effect=TimeoutError()
        with self.assertRaises(TimeoutError):self.launch()
        with self.assertRaisesRegex(ValueError,'Unresolved launch'):self.launch()
        self.api.run_job.assert_called_once();self.assertFalse((self.folder/'launch.json').exists())

    def test_concurrent_launcher_rejected(self):
        self.folder.mkdir()
        with (self.folder/'.launch.lock').open('a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            with self.assertRaises(BlockingIOError):self.launch()
        self.api.run_job.assert_not_called()

    def test_wrong_effective_timeout_hardware_or_image_rejected(self):
        guard=self.launch()
        for k,v in [('timeout',10800),('flavor','a10g-large'),('dockerImage','other')]:
            raw=self.remote(guard);raw[k]=v
            with self.assertRaisesRegex(ValueError,'allocation'):m.bind_remote(raw,guard,self.source,self.row)

    def test_changed_command_environment_or_handle_rejected(self):
        guard=self.launch()
        for k,v in [('command',['different']),('environment',{}),('id','f'*24)]:
            raw=self.remote(guard);raw[k]=v
            with self.assertRaises(ValueError):m.bind_remote(raw,guard,self.source,self.row)

    def test_saved_intent_tampering_prevents_handle_reuse(self):
        self.launch();p=self.folder/'launch-intent.json';r=m.read(p);r['original_name']='other';p.unlink();m.save(p,r)
        with self.assertRaisesRegex(ValueError,'binding'):self.launch()
        self.api.run_job.assert_called_once()

    def test_unknown_stage_remains_observation_error(self):
        guard=self.launch();raw=self.remote(guard);raw['status']['stage']='UNKNOWN'
        with self.assertRaisesRegex(ValueError,'Unknown HF'):m.bind_remote(raw,guard,self.source,self.row)

    def test_status_projection_excludes_credentials_and_full_environment(self):
        guard=self.launch();r=m.bind_remote(self.remote(guard),guard,self.source,self.row)
        self.assertTrue(r['public_configuration_verified']);self.assertNotIn('environment',r);self.assertNotIn('secrets',r)
        self.assertNotIn('test-secret',json.dumps(r))

    def test_default_cycle_has_no_api_or_launch_side_effects(self):
        with patch.object(m,'source_checked',return_value=self.source),patch.object(m,'HfApi') as api:
            result=m.cycle()
        self.assertFalse(result['execute']);api.assert_not_called();self.assertFalse(self.folder.exists())

    def test_capacity_includes_still_running_original_jobs(self):
        records={self.rows[0]['name']:{'stage':'RUNNING'},self.rows[1]['name']:{'stage':'COMPLETED'}}
        self.assertEqual(m.choose(self.rows,records,62,64),[self.rows[2]])
        self.assertEqual(m.choose(self.rows,records,63,64),[])
        with self.assertRaisesRegex(ValueError,'capacity'):m.choose(self.rows,records,64,64)

    def test_failed_or_unknown_attempt_blocks_new_dispatch(self):
        for stage in ('ERROR','UNKNOWN','CANCELED'):
            with self.assertRaisesRegex(ValueError,'blocks dispatch'):m.choose(self.rows,{self.row['name']:{'stage':stage}},0,64)

    def test_foreign_record_or_negative_limit_rejected(self):
        with self.assertRaisesRegex(ValueError,'Foreign'):m.choose(self.rows,{'other':{'stage':'RUNNING'}},0,1)
        with self.assertRaisesRegex(ValueError,'Invalid'):m.choose(self.rows,{},0,-1)

    def test_waiting_collection_never_downloads_or_audits(self):
        value=m.collect_one(self.api,self.folder,self.source,self.row,{'stage':'RUNNING'})
        self.assertEqual(value['stage'],'RUNNING');self.api.fetch_job_logs.assert_not_called();self.assertFalse(self.folder.exists())


if __name__=='__main__':unittest.main()
