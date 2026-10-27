"""Exercise development-only submission and original-handle preservation."""
import fcntl
import importlib.util
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

spec = importlib.util.spec_from_file_location('development_manager', Path(__file__).with_name('manage-conservative-auction-development-v2.py'))
job = importlib.util.module_from_spec(spec); spec.loader.exec_module(job)


class SubmissionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup); self.path = Path(self.tmp.name)
        self.row = {'name': 'development', 'job': 'controls/development.job.json', 'arm': 'filter',
                    'flavor': 'cpu-upgrade', 'timeout': '2h',
                    'shard': {'seed': 'conservative-auction-development-v1-4p'}}
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
        row = {**self.row, 'shard': {'seed': 'conservative-auction-runtime-v1-4p'}}
        with self.assertRaises(AssertionError): self.launch(source={**self.source, 'rows': [row]}, row=row)
        self.api.run_job.assert_not_called()
        self.assertFalse((self.path/'launch.json').exists())


if __name__ == '__main__': unittest.main()
