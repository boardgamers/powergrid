"""No HF submissions: exercise recovery admission, ordering and exclusive views."""
import importlib.util
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock,patch


def load(name,file):
    s=importlib.util.spec_from_file_location(name,Path(__file__).with_name(file));m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

m=load('recovery_manager','manage-current-auction-confirmation-recovery-v1.py')
owner=load('recovery_owner','coordinate-current-auction-confirmation-recovery-v1.py')


class RecoveryManagerTests(unittest.TestCase):
    def test_newly_completed_or_error_original_defers_all_submissions(self):
        for stage in ('COMPLETED','ERROR'):
            with tempfile.TemporaryDirectory() as tmp:
                folder=Path(tmp);row={'name':'old'};pending={'name':'pending'};(folder/'old').mkdir();(folder/'old/launch.json').write_text('{}')
                source={'rows':[row,pending],'max_active_jobs':64}
                with patch.object(m,'OUT',folder),patch.object(m,'source_checked',return_value=source),patch.object(m,'admitted'),patch.object(m,'cached',return_value=None),patch.object(m,'HfApi'),patch.object(m.base,'original_status',return_value={'stage':stage}),patch.object(m.base,'launch_once') as launch:
                    result=m.launch_batch(True)
                    self.assertEqual(result['awaiting_collection'],['old']);launch.assert_not_called()

    def test_unadmitted_recovery_never_launches(self):
        with patch.object(m,'source_checked',return_value={'max_active_jobs':64}),patch.object(m,'admitted',side_effect=AssertionError('unadmitted')),patch.object(m,'HfApi') as api:
            with self.assertRaises(AssertionError):m.launch_batch(True)
            api.assert_not_called()

    def test_original_handles_are_never_relaunched(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp);row={'name':'old'};pending={'name':'pending'};(folder/'old').mkdir();(folder/'old/launch.json').write_text('{}')
            source={'rows':[row,pending],'max_active_jobs':64}
            with patch.object(m,'OUT',folder),patch.object(m,'source_checked',return_value=source),patch.object(m,'admitted'),patch.object(m,'cached',return_value={'stage':'ERROR'}),patch.object(m,'HfApi'),patch.object(m,'get_token',return_value='test-only'),patch.object(m.base,'launch_once',return_value={'job_id':'a'*24}) as launch:
                result=m.launch_batch(True)
                self.assertEqual(result['remaining_unsubmitted'],0)
                self.assertEqual(launch.call_count,1);self.assertEqual(launch.call_args.args[3],pending)

    def test_ambiguous_normal_and_recovered_receipts_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp);(folder/'verified.json').write_text('{}');(folder/'verified-terminal-recovery-v1.json').write_text('{}')
            with self.assertRaises(AssertionError):m.verified_path(folder)

    def test_original_error_uses_separate_evaluation_view(self):
        folder=Path('/tmp/synthetic')
        self.assertEqual(m.evaluation_directory(folder,{'stage':'ERROR'}),folder/'terminal-recovery-v1/evaluation')
        self.assertEqual(m.evaluation_directory(folder,{'stage':'COMPLETED'}),folder/'artifacts/job/evaluation')

    def test_collection_failure_never_submits_more(self):
        manager=SimpleNamespace(collect=Mock(side_effect=ValueError('missing terminal')),launch=Mock())
        with patch.object(owner,'check_pins'):
            with self.assertRaises(ValueError):owner.tick(manager,{})
        manager.launch.assert_not_called()

    def test_owner_requires_explicit_admission_before_state_creation(self):
        with tempfile.TemporaryDirectory() as tmp:
            ready=Path(tmp)/'ready.json';ready.write_text('{"passed":true,"input_hashes":{}}');out=Path(tmp)/'owner'
            manager=SimpleNamespace(admitted=Mock(side_effect=ValueError('not admitted')),source_checked=Mock())
            with patch.object(owner,'READINESS',ready),patch.object(owner,'OUT',out),patch.object(owner,'manager_module',return_value=manager),patch('sys.argv',['test','--start']):
                with self.assertRaises(ValueError):owner.main()
            self.assertFalse(out.exists());manager.source_checked.assert_not_called()

    def test_stop_marker_blocks_all_actions(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(owner,'OUT',Path(tmp)):
            (Path(tmp)/'STOP').touch();manager=SimpleNamespace(collect=Mock(),launch=Mock())
            with self.assertRaises(KeyboardInterrupt):owner.tick(manager,{'code_hashes':{}})
            manager.collect.assert_not_called();manager.launch.assert_not_called()

    def test_admitted_owner_starts_and_completes_without_external_actions(self):
        # Exercise startup using the actual manager interface, including its
        # original-pilot dependency, without running a collector or HF job.
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); ready=root/'ready.json'; out=root/'owner'
            files={'ready.json':{'passed':True,'input_hashes':{}},
                   'old.json':{'pid':999999999,'stage':'stopped_for_inspection'},
                   'source.json':{},'admission.json':{},'result.json':{},
                   'pilots.json':{'complete':True,'verified_jobs':4}}
            for name,data in files.items():(root/name).write_text(json.dumps(data))
            admission={'stopped_owner_state':'old.json','rule':m.recovery.RULE}
            source={'games':26880,'max_active_jobs':64,'rows':[{}]}
            with patch.object(owner,'ROOT',root),patch.object(owner,'READINESS',ready),patch.object(owner,'OUT',out),patch.object(owner,'manager_module',return_value=m),patch.object(owner,'tick',return_value=True) as tick,patch.object(owner.signal,'signal'),patch.object(m,'admitted',return_value=admission),patch.object(m,'source_checked',return_value=source),patch.object(m,'SOURCE',root/'source.json'),patch.object(m,'ADMISSION',root/'admission.json'),patch.object(m,'RESULT',root/'result.json'),patch.object(m.pilots,'RESULT',root/'pilots.json'),patch.object(m,'collect') as collect,patch.object(m,'launch') as launch,patch('sys.argv',['test','--start']):
                owner.main()
            saved=json.loads((out/'state.json').read_text())
            self.assertEqual(saved['stage'],'complete')
            self.assertEqual(saved['original_owner_pid'],999999999)
            self.assertEqual(saved['completed_games'],26880)
            self.assertIn('admission.json',saved['code_hashes'])
            tick.assert_called_once();collect.assert_not_called();launch.assert_not_called()


if __name__=='__main__':unittest.main()
