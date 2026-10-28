"""Admission and provenance tests only; these do not play or submit games."""
from contextlib import ExitStack
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock,patch

from public_policy_development_job_v1 import read,digest,write
from public_policy_final_contract_v1 import object_hash


def load(name,filename):
    spec=importlib.util.spec_from_file_location(name,Path(__file__).with_name(filename))
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value


m=load('attempts_test_manager','manage-conservative-auction-attempts-v1.py')
c=load('attempts_test_owner','coordinate-conservative-auction-attempts-v1.py')
a=load('attempts_test_analysis','compare-conservative-auction-attempts-v1.py')
r=m.recovery


class BootstrapTests(unittest.TestCase):
    def test_only_download_is_replaced(self):
        old=m.original.BOOTSTRAP;new=r.cached_bootstrap(old,read(r.CACHE))
        before,after=old.split("urllib.request.urlretrieve('https://nodejs.org/dist/v24.14.0/node-v24.14.0-linux-x64.tar.xz','/tmp/node.tar.xz')")
        self.assertTrue(new.startswith(before) and new.endswith(after))
        self.assertEqual(new.count('node_archive=hf_hub_download'),1)
        self.assertIn(r.NODE_SHA,new)
        self.assertNotIn('urlretrieve(',new)

    def test_wrong_cache_and_ambiguous_original_rejected(self):
        for key,value in [('sha256','0'*64),('version','v24.13.0'),('revision','main'),('remote_archive_verified',False)]:
            cache=read(r.CACHE);cache[key]=value
            with self.subTest(key=key),self.assertRaises(AssertionError):r.cached_bootstrap(m.original.BOOTSTRAP,cache)
        with self.assertRaises(AssertionError):r.cached_bootstrap(m.original.BOOTSTRAP*2,read(r.CACHE))

    def test_reviewed_failures_cannot_include_evaluation(self):
        for target in r.TARGETS.values():
            log=(r.ROOT/target['log']).read_text();r.preevaluation_failure(log,target['error_kind'])
            for change in ('\n{"game_progress":1}', '\n{"case":"completed"}'):
                with self.assertRaises(AssertionError):r.preevaluation_failure(log+change,target['error_kind'])
            with self.assertRaises(AssertionError):r.preevaluation_failure(log.replace('line 4,','line 9,'),target['error_kind'])

    def test_current_approval_binds_both_original_guards(self):
        approval,bootstrap=r.checked_approval(read(m.SOURCE))
        self.assertEqual(set(approval['allowed_retries']),set(r.TARGETS))
        self.assertEqual(approval['cached_bootstrap_sha256'],r.sha_text(bootstrap))
        self.assertFalse(approval['historical_binary_checksum_available'])


class AttemptTests(unittest.TestCase):
    def setUp(self):
        self.stack=ExitStack();self.addCleanup(self.stack.close)
        self.root=Path(self.stack.enter_context(tempfile.TemporaryDirectory()))
        self.stack.enter_context(patch.object(m,'ROOT',self.root))
        self.stack.enter_context(patch.object(m,'OUT',self.root/'attempts'))
        self.stack.enter_context(patch.object(m.original,'OUT',self.root/'original'))
        m.original.OUT.mkdir()
        self.row={'name':next(iter(r.TARGETS)),'job':'fixture.json','flavor':'cpu-upgrade','timeout':'3h',
            'shard':{'seed':'conservative-auction-development-v1-5p','games':20}}
        self.source={'rows':[self.row],'archive':'source.tgz','revision':'1'*40,'sha256':'2'*64,
            'source_manifest_sha256':'3'*64,'protocol_sha256':'4'*64}
        self.approval={'allowed_retries':{name:{'job_id':target['job_id']} for name,target in r.TARGETS.items()}}
        self.stack.enter_context(patch.object(r,'checked_approval',return_value=(self.approval,'cached-bootstrap')))
        self.stack.enter_context(patch.object(m,'source_checked',return_value=self.source))
        self.stack.enter_context(patch.object(m,'tests_checked',return_value={'passed':True}))
        self.stack.enter_context(patch.object(m,'get_token',return_value='synthetic-not-a-token'))
        self.api=Mock();self.api.run_job.return_value=SimpleNamespace(id='a'*24)
        self.stack.enter_context(patch.object(m,'HfApi',return_value=self.api))

    def launch(self):return m.launch_once(self.api,m.execution_folder(self.row['name']),self.source,self.row,'synthetic-not-a-token')

    def test_retry_is_separate_and_source_unchanged(self):
        original=m.original.OUT/self.row['name'];original.mkdir();(original/'launch.json').write_text('{"preserved":true}')
        before=digest(original/'launch.json');guard=self.launch()
        self.assertEqual(before,digest(original/'launch.json'))
        self.assertEqual(guard['retry_of'],r.TARGETS[self.row['name']]['job_id'])
        self.assertEqual(guard['execution_attempt'],1)
        call=self.api.run_job.call_args.kwargs
        self.assertEqual(call['command'],['bash','-lc','cached-bootstrap'])
        self.assertEqual(call['env'],m.source_environment(self.source,self.row))
        self.assertEqual(call['flavor'],self.row['flavor']);self.assertEqual(call['timeout'],self.row['timeout'])

    def test_existing_launched_guard_does_not_submit_again(self):
        first=self.launch();self.assertEqual(first,self.launch());self.api.run_job.assert_called_once()

    def test_unknown_launch_never_resubmits(self):
        self.api.run_job.side_effect=TimeoutError('synthetic timeout')
        with self.assertRaises(TimeoutError):self.launch()
        path=m.execution_folder(self.row['name'])/'launch.json'
        self.assertEqual(read(path)['stage'],'launch_unknown')
        with self.assertRaises(AssertionError):self.launch()
        self.api.run_job.assert_called_once()

    def test_wrong_directory_rejected_before_submit(self):
        with self.assertRaises(AssertionError):m.launch_once(self.api,m.original.OUT/self.row['name'],self.source,self.row,'synthetic')
        self.api.run_job.assert_not_called()

    def test_retry_binding_and_unreviewed_attempt_rejected(self):
        guard=self.launch()
        for edit in ({'retry_of':'b'*24},{'execution_attempt':2},{'actual_bootstrap_sha256':'0'*64}):
            wrong={**guard,**edit}
            with self.assertRaises(AssertionError):m.guard_checked(self.source,self.row,wrong)
        other={**self.row,'name':'normal-unsubmitted-row'}
        with self.assertRaises(AssertionError):m.guard_checked(self.source,other,{**guard,'row':other})
        old={k:v for k,v in guard.items() if k!='bootstrap_recovery_sha256'}
        with self.assertRaises(AssertionError):m.guard_checked(self.source,self.row,old)

    def test_owner_cannot_create_missing_retry(self):
        with self.assertRaises(AssertionError):m.launch(execute=True)
        self.api.run_job.assert_not_called()

    def complete_retry_guards(self):
        for name in r.TARGETS:
            p=m.execution_folder(name)/'launch.json';p.parent.mkdir(parents=True,exist_ok=True)
            if not p.exists():write(p,{'synthetic_unread_guard':True})

    def test_selected_failure_stops_new_submissions(self):
        self.launch();self.complete_retry_guards();self.api.run_job.reset_mock()
        self.api.inspect_job.return_value=SimpleNamespace(status=SimpleNamespace(stage='ERROR'))
        with self.assertRaises(AssertionError):m.launch(execute=True)
        self.api.run_job.assert_not_called()

    def test_concurrency_cap_prevents_new_submissions(self):
        self.complete_retry_guards()
        rows=[]
        for i in range(65):
            row={**self.row,'name':f'normal-{i}'};rows.append(row)
            if i<64:
                p=m.execution_folder(row['name'])/'launch.json';p.parent.mkdir()
                write(p,{'stage':'launched','row':row,'job_id':format(i+1,'024x')})
        self.source['rows']=rows;fingerprint=object_hash(self.source)
        for row in rows[:64]:
            p=m.execution_folder(row['name'])/'launch.json';write(p,{**read(p),'source_fingerprint':fingerprint})
        self.api.inspect_job.return_value=SimpleNamespace(status=SimpleNamespace(stage='RUNNING'))
        result=m.launch(execute=True);self.assertEqual(result['active_jobs'],64)
        self.assertEqual(result['remaining_unsubmitted'],1);self.api.run_job.assert_not_called()

    def test_retry_operation_refuses_existing_attempt(self):
        self.launch();self.api.run_job.reset_mock()
        with self.assertRaises(AssertionError):m.retry_bootstrap(execute=True)
        self.api.run_job.assert_not_called()

    def test_cached_receipt_requires_actual_setup_binding(self):
        guard=self.launch();folder=m.execution_folder(self.row['name'])
        (folder/'artifacts').mkdir();write(folder/'artifacts/manifest.json',{})
        saved={'source_sha256':digest(m.SOURCE),'row':self.row,'guard_sha256':digest(folder/'launch.json'),
            'job_id':guard['job_id'],'stage':'COMPLETED','verified':True,
            'evidence':{'manifest_sha256':digest(folder/'artifacts/manifest.json')},
            'execution_setup':{'command_sha256':guard['actual_bootstrap_sha256'],
                'bootstrap_recovery_sha256':guard['bootstrap_recovery_sha256'],'api_command_and_environment_verified':True}}
        write(folder/'verified.json',saved);self.assertEqual(m.cached_checked(self.source,self.row,folder),saved)
        saved['execution_setup']['api_command_and_environment_verified']=False;write(folder/'verified.json',saved)
        with self.assertRaises(AssertionError):m.cached_checked(self.source,self.row,folder)

    def test_collection_failure_preserved_without_submission(self):
        self.launch();self.api.run_job.reset_mock()
        self.api.inspect_job.return_value=SimpleNamespace(status=SimpleNamespace(stage='ERROR'))
        self.api.fetch_job_logs.return_value=['synthetic failure']
        with self.assertRaises(RuntimeError):m.collect()
        self.assertTrue((m.execution_folder(self.row['name'])/'failure.json').exists())
        self.api.run_job.assert_not_called()

    def test_analysis_rejects_wrong_execution_folder(self):
        self.launch();folder=m.execution_folder(self.row['name']);guard=read(folder/'launch.json')
        report={'bootstrap_recovery_sha256':digest(r.APPROVAL),'failed_original_attempts':self.approval['allowed_retries'],
            'execution_index':{self.row['name']:{'directory':'wrong','job_id':guard['job_id']}},'jobs':[]}
        with patch.object(a,'ROOT',self.root),self.assertRaises(ValueError):a.checked_execution_index(m,self.source,report)


class OwnerAndAnalysisTests(unittest.TestCase):
    def test_audit_failure_prevents_launch(self):
        manager=Mock();manager.collect.side_effect=RuntimeError('invalid receipt')
        with self.assertRaises(RuntimeError):c.tick(manager,Mock(),{}, {'rows':[]})
        manager.launch.assert_not_called()

    def test_complete_collection_stops_without_launch(self):
        manager=Mock();manager.collect.return_value={'complete':True,'verified_jobs':648}
        self.assertTrue(c.tick(manager,Mock(),{}, {'rows':[]}));manager.launch.assert_not_called()

    def test_partial_results_not_analyzed(self):
        with self.assertRaises(ValueError):a.completion_index({'rows':[]},{'complete':False})

    def test_arithmetic_and_completeness_unchanged(self):
        old=load('old_analysis_for_source_check','compare-conservative-auction-development-v2.py')
        import inspect
        self.assertEqual(inspect.getsource(a.completion_index),inspect.getsource(old.completion_index))
        self.assertIs(a.statistics,old.statistics)


if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]))
    if result.wasSuccessful():
        write(m.TEST_RESULT,{'passed':True,'tests':result.testsRun,'new_hf_jobs':0,'synthetic_game_evidence':False,
            'code_hashes':{name:digest(Path(__file__).with_name(name)) for name in m.TEST_PINS}})
    sys.exit(not result.wasSuccessful())
