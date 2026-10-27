"""Exercise original-job ownership, immutable admission, and measurements."""
import fcntl
import importlib.util
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

spec = importlib.util.spec_from_file_location('runtime_pilots', Path(__file__).with_name('manage-conservative-auction-runtime-v2.py'))
job = importlib.util.module_from_spec(spec); spec.loader.exec_module(job)


class SubmissionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name)
        self.row = {'name': 'pilot', 'arm': 'conservative_dual', 'execute_pilot': True, 'job': 'pilot.job.json'}
        self.source = {'archive': 'test.tgz', 'revision': 'a'*40, 'sha256': 'b'*64,
            'source_manifest_sha256': 'c'*64, 'protocol_sha256': 'f'*64,
            'flavor': 'cpu-upgrade', 'timeout': '5h', 'rows': [self.row]}
        self.api = Mock(); self.api.run_job.return_value = SimpleNamespace(id='d'*24)

    def launch(self, source=None, row=None):
        return job.launch_once(self.api, self.path, source or self.source, row or self.row, 'private-test-token')

    def test_intent_before_api_and_no_persisted_token(self):
        def submitted(**kwargs):
            self.assertEqual(job.read(self.path/'launch.json')['stage'], 'launch_intent')
            self.assertEqual(kwargs['secrets'], {'HF_TOKEN': 'private-test-token'})
            self.assertEqual(kwargs['env']['PILOT_JOB'], self.row['job'])
            self.assertEqual(kwargs['env']['PROTOCOL_SHA256'], self.source['protocol_sha256'])
            self.assertEqual(kwargs['command'], ['bash', '-lc', job.BOOTSTRAP])
            return SimpleNamespace(id='d'*24)
        self.api.run_job.side_effect = submitted
        self.assertEqual(self.launch()['job_id'], 'd'*24)
        self.assertNotIn('private-test-token', (self.path/'launch.json').read_text())

    def test_known_original_is_never_resubmitted(self):
        first = self.launch(); self.assertEqual(self.launch(), first)
        self.assertEqual(self.api.run_job.call_count, 1)

    def test_unknown_original_cannot_be_retried(self):
        self.api.run_job.side_effect = TimeoutError()
        with self.assertRaises(TimeoutError): self.launch()
        self.assertEqual(job.read(self.path/'launch.json')['stage'], 'launch_unknown')
        with self.assertRaisesRegex(AssertionError, 'original uncertain'): self.launch()
        self.assertEqual(self.api.run_job.call_count, 1)

    def test_different_source_rejected_for_same_guard(self):
        self.launch()
        with self.assertRaisesRegex(AssertionError, 'original uncertain'):
            self.launch(source={**self.source, 'sha256': 'e'*64})
        self.assertEqual(self.api.run_job.call_count, 1)

    def test_concurrent_owner_cannot_submit(self):
        with (self.path/'.launch.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaises(BlockingIOError): self.launch()
        self.api.run_job.assert_not_called()

    def test_validation_only_row_cannot_submit(self):
        row = {**self.row, 'execute_pilot': False}
        with self.assertRaises(AssertionError): self.launch(source={**self.source, 'rows': [row]}, row=row)
        self.api.run_job.assert_not_called()
        self.assertFalse((self.path/'launch.json').exists())

    def test_measurements_must_be_complete_positive_and_finite(self):
        state = {'stage': 'complete', 'qualified': False, 'reserved_final_seeds_used': False,
            'measurement': {'seconds': 10., 'cpu_seconds': 35., 'sampled_peak_total_rss_bytes': 10000,
                'memory_samples': 50, 'memory_sampling_period_seconds': .2, 'includes_startup_and_validation': True}}
        job.check_measurement(state)
        for value in (0, -1, float('nan'), float('inf')):
            with self.subTest(value=value), self.assertRaises(AssertionError):
                job.check_measurement({**state, 'measurement': {**state['measurement'], 'seconds': value}})
        with self.assertRaises(AssertionError): job.check_measurement({**state, 'stage': 'failed'})


if __name__ == '__main__': unittest.main()
