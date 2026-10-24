import copy
import importlib.util
from pathlib import Path
import unittest

from strategic_collection import ROOT, read

spec = importlib.util.spec_from_file_location('prestart_recovery_test', Path(__file__).with_name('recover-population-hybrid-prestart-v1.py'))
recovery = importlib.util.module_from_spec(spec)
spec.loader.exec_module(recovery)


class PrestartRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.guard = read(recovery.FAILED / 'original-guard.json')
        self.status = read(recovery.FAILED / 'job-status.json')
        self.remote = read(recovery.FAILED / 'remote-artifact-check.json')

    def call(self, status=None, guard=None, canonical=None, remote=None, present=False, stage='stopped_with_error'):
        recovery.replacement_allowed(guard or self.guard, canonical or self.guard,
            status or self.status, remote or self.remote, coordinator_present=present, coordinator_stage=stage)

    def test_actual_preserved_terminal_prestart_failure(self):
        self.call()

    def test_live_unknown_completed_and_started_jobs_rejected(self):
        for stage in ['SCHEDULING', 'RUNNING', 'COMPLETED', 'CANCELED', 'UNKNOWN', None]:
            with self.subTest(stage=stage), self.assertRaises(AssertionError):
                self.call(status={**self.status, 'stage': stage})
        with self.assertRaises(AssertionError):
            self.call(status={**self.status, 'started_at': '2026-10-24T17:00:00Z'})

    def test_changed_guard_wrong_job_and_repeat_replacement_rejected(self):
        with self.assertRaises(AssertionError):
            self.call(canonical={**self.guard, 'job_id': 'changed'})
        with self.assertRaises(AssertionError):
            self.call(status={**self.status, 'job_id': 'changed'})
        changed = {**self.guard, 'replaces_job_id': 'earlier'}
        with self.assertRaises(AssertionError):
            self.call(guard=changed, canonical=changed)

    def test_live_coordinator_and_existing_artifacts_rejected(self):
        with self.assertRaises(AssertionError):
            self.call(present=True)
        with self.assertRaises(AssertionError):
            self.call(stage='waiting_for_jobs')
        for key, value in [('exists', True), ('repo', 'wrong/repo'), ('path', 'another-artifact.tgz')]:
            with self.subTest(key=key), self.assertRaises(AssertionError):
                self.call(remote={**self.remote, key: value})


if __name__ == '__main__':
    unittest.main()
