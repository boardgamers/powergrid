"""Exercise submission uncertainty and exclusive original-handle ownership."""
import fcntl
import importlib.util
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

spec = importlib.util.spec_from_file_location('development_hf', Path(__file__).with_name('manage-public-policy-development-hf-v1.py'))
job = importlib.util.module_from_spec(spec); spec.loader.exec_module(job)


class OriginalSubmissionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name)
        self.source = {'archive': 'test.tgz', 'revision': 'a'*40, 'sha256': 'b'*64,
                       'source_manifest_sha256': 'c'*64, 'flavor': 'cpu-upgrade', 'timeout': '1h'}
        self.api = Mock()
        self.api.run_job.return_value = SimpleNamespace(id='d'*24)

    def test_intent_precedes_submission_and_secrets_not_saved(self):
        def submitted(**kwargs):
            intent = job.read(self.path/'launch.json')
            self.assertEqual(intent['stage'], 'launch_intent')
            self.assertEqual(intent['source'], self.source)
            self.assertEqual(kwargs['secrets'], {'HF_TOKEN': 'private-test-token'})
            self.assertEqual(kwargs['env']['SOURCE_REVISION'], self.source['revision'])
            self.assertEqual(kwargs['command'], ['bash', '-lc', job.BOOTSTRAP])
            return SimpleNamespace(id='d'*24)
        self.api.run_job.side_effect = submitted
        result = job.launch_once(self.api, self.path, self.source, 'private-test-token')
        self.assertEqual(result['job_id'], 'd'*24)
        self.assertNotIn('private-test-token', (self.path/'launch.json').read_text())

    def test_original_handle_returned_without_resubmission(self):
        first = job.launch_once(self.api, self.path, self.source, 'secret')
        second = job.launch_once(self.api, self.path, self.source, 'secret')
        self.assertEqual(first, second); self.assertEqual(self.api.run_job.call_count, 1)

    def test_ambiguous_submission_is_not_retried(self):
        self.api.run_job.side_effect = TimeoutError('observation ended')
        with self.assertRaises(TimeoutError): job.launch_once(self.api, self.path, self.source, 'secret')
        self.assertEqual(job.read(self.path/'launch.json')['stage'], 'launch_unknown')
        with self.assertRaisesRegex(AssertionError, 'original uncertain'):
            job.launch_once(self.api, self.path, self.source, 'secret')
        self.assertEqual(self.api.run_job.call_count, 1)

    def test_changed_source_cannot_reuse_original_guard(self):
        job.launch_once(self.api, self.path, self.source, 'secret')
        changed = {**self.source, 'sha256': 'e'*64}
        with self.assertRaisesRegex(AssertionError, 'original uncertain'):
            job.launch_once(self.api, self.path, changed, 'secret')
        self.assertEqual(self.api.run_job.call_count, 1)

    def test_concurrent_owner_cannot_submit(self):
        with (self.path/'.launch.lock').open('a') as owner:
            fcntl.flock(owner, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaises(BlockingIOError): job.launch_once(self.api, self.path, self.source, 'secret')
        self.api.run_job.assert_not_called()
        self.assertFalse((self.path/'launch.json').exists())


if __name__ == '__main__': unittest.main()
