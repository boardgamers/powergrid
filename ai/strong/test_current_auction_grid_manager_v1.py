"""Exercise confirmation-only submission and original-handle preservation."""
import fcntl
import importlib.util
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

spec = importlib.util.spec_from_file_location('development_manager', Path(__file__).with_name('manage-current-auction-grid-v1.py'))
job = importlib.util.module_from_spec(spec); spec.loader.exec_module(job)


class SubmissionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup); self.path = Path(self.tmp.name)
        self.row = {'name': 'development', 'job': 'controls/development.job.json', 'arm': 'filter', 'players': 4,
                    'flavor': 'cpu-upgrade', 'timeout': '2h',
                    'shard': {'seed': 'current-auction-confirmation-v1-4p', 'players': 4, 'start': 0, 'deals': 2}}
        self.source = {'archive': 'source.tgz', 'sha256': 'a'*64, 'revision': 'b'*40,
            'source_manifest_sha256': 'c'*64, 'protocol_sha256': 'd'*64, 'rows': [self.row]}
        self.api = Mock(); self.api.run_job.return_value = SimpleNamespace(id='e'*24)

    def launch(self, source=None, row=None):
        return job.launch_once(self.api, self.path, source or self.source, row or self.row, 'private-test-token')

    def test_filter_admitted_with_development_scope_and_intent_before_api(self):
        def submit(**kwargs):
            self.assertEqual(job.read(self.path/'launch.json')['stage'], 'launch_intent')
            self.assertIn('--scope development', kwargs['command'][2])
            self.assertNotIn('--scope runtime', kwargs['command'][2])
            self.assertEqual(kwargs['env']['PILOT_JOB'], self.row['job'])
            self.assertEqual(kwargs['timeout'], '2h')
            self.assertEqual(kwargs['secrets'], {'HF_TOKEN': 'private-test-token'})
            return SimpleNamespace(id='e'*24)
        self.api.run_job.side_effect = submit
        self.assertEqual(self.launch()['job_id'], 'e'*24)
        self.assertNotIn('private-test-token', (self.path/'launch.json').read_text())

    def test_known_original_reused_and_changed_source_rejected(self):
        first = self.launch(); self.assertEqual(first, self.launch())
        with self.assertRaisesRegex(AssertionError, 'original uncertain'):
            self.launch(source={**self.source, 'sha256': 'f'*64})
        self.assertEqual(self.api.run_job.call_count, 1)

    def test_ambiguous_submission_never_retried(self):
        self.api.run_job.side_effect = TimeoutError()
        with self.assertRaises(TimeoutError): self.launch()
        self.assertEqual(job.read(self.path/'launch.json')['stage'], 'launch_unknown')
        with self.assertRaisesRegex(AssertionError, 'original uncertain'): self.launch()
        self.assertEqual(self.api.run_job.call_count, 1)

    def test_concurrent_owner_cannot_submit(self):
        with (self.path/'.launch.lock').open('a') as owner:
            fcntl.flock(owner, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaises(BlockingIOError): self.launch()
        self.api.run_job.assert_not_called()

    def test_unknown_and_pilot_seeds_are_rejected_before_api(self):
        with self.assertRaises(AssertionError): self.launch(row={**self.row, 'name': 'not-in-schedule'})
        row = {**self.row, 'shard': {'seed': 'current-auction-runtime-v1-4p'}}
        with self.assertRaises(AssertionError): self.launch(source={**self.source, 'rows': [row]}, row=row)
        self.api.run_job.assert_not_called()
        self.assertFalse((self.path/'launch.json').exists())


class BatchOperationTests(unittest.TestCase):
    def test_competing_collection_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(job, 'OUT', Path(tmp)):
            with job.exclusive_operation():
                with self.assertRaises(BlockingIOError):
                    with job.exclusive_operation(): pass

    def test_newly_finished_job_defers_submission_until_collection(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp); row = {'name': 'old'}; pending = {'name': 'pending'}
            source = {'rows': [row,pending], 'max_active_jobs': 64}
            (folder/'old').mkdir(); (folder/'old/launch.json').write_text('{}')
            test = folder/'ai/runs/current-auction-grid-manager-tests-v1.log'; test.parent.mkdir(parents=True)
            test.write_text('Ran 7 tests\nOK\n')
            with patch.object(job, 'ROOT', folder), patch.object(job, 'OUT', folder), \
                 patch.object(job, 'source_checked', return_value=source), patch.object(job, 'HfApi'), \
                 patch.object(job, 'original_status', return_value={'stage':'COMPLETED'}), \
                 patch.object(job, 'launch_once') as launch:
                result = job.launch(execute=True)
                self.assertEqual(result['awaiting_collection'], ['old'])
                self.assertEqual(result['new_jobs'], []); launch.assert_not_called()


if __name__ == '__main__': unittest.main()
