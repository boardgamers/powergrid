"""Reject recovery actions that could duplicate work or replace saved results."""
import copy
import importlib.util
from pathlib import Path
import unittest

path = Path(__file__).with_name('recover-policy-iteration-development.py')
spec = importlib.util.spec_from_file_location('development_recovery', path)
recovery = importlib.util.module_from_spec(spec)
spec.loader.exec_module(recovery)


class RecoveryControls(unittest.TestCase):
    def setUp(self):
        self.guard = {'stage': 'launched', 'mode': 'development', 'job_id': 'original',
                      'qualification_eligible': False, 'source': {'sha256': 'frozen'}}

    def test_reviewed_terminal_failure_is_allowed(self):
        recovery.replacement_allowed(self.guard, 'ERROR', copy.deepcopy(self.guard), [])

    def test_live_completed_and_unknown_jobs_are_rejected(self):
        for status in ['SCHEDULING', 'RUNNING', 'COMPLETED', 'CANCELED', 'UNKNOWN', None]:
            with self.subTest(status=status), self.assertRaises(AssertionError):
                recovery.replacement_allowed(self.guard, status, self.guard, [])

    def test_a_replacement_cannot_be_replaced_again(self):
        changed = {**self.guard, 'job_id': 'replacement', 'replaces_job_id': 'original'}
        with self.assertRaises(AssertionError):
            recovery.replacement_allowed(self.guard, 'ERROR', changed, [])

    def test_existing_artifacts_are_preserved(self):
        with self.assertRaises(AssertionError):
            recovery.replacement_allowed(self.guard, 'ERROR', self.guard, ['evaluation.json'])

    def test_changed_source_and_non_development_run_are_rejected(self):
        changed = {**self.guard, 'source': {'sha256': 'different'}}
        with self.assertRaises(AssertionError):
            recovery.replacement_allowed(self.guard, 'ERROR', changed, [])
        final = {**self.guard, 'mode': 'final'}
        with self.assertRaises(AssertionError):
            recovery.replacement_allowed(final, 'ERROR', final, [])


if __name__ == '__main__':
    unittest.main()
