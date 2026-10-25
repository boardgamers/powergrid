"""One-owner study orchestration using synthetic statuses, never HF submissions."""
from contextlib import redirect_stdout
from io import StringIO
import importlib.util
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from strategic_collection import ROOT, read, write, digest

spec = importlib.util.spec_from_file_location('study_coord_test', ROOT/'ai/strong/coordinate-surrogate-continuation-study-v1.py')
c = importlib.util.module_from_spec(spec); spec.loader.exec_module(c)


class CoordinatorTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory(); self.addCleanup(self.temp.cleanup); self.root = Path(self.temp.name)
        for target, key, path in [(c, 'OUT', 'out'), (c.launcher, 'PLAN', 'plan.json'), (c.launcher, 'GUARDS', 'guards'),
                                  (c.manager, 'INDEX', 'index.json'), (c.manager, 'ANALYSIS', 'analysis.json')]:
            p = patch.object(target, key, self.root/path); p.start(); self.addCleanup(p.stop)
        p = patch.object(c, 'dependencies', return_value={'fixture': 'a'*64}); p.start(); self.addCleanup(p.stop)
        self.plan = {'jobs': 480, 'continuations': 23040, 'admission': {'max_concurrent': 32}}
        write(c.launcher.PLAN, self.plan); c.OUT.mkdir()
        self.state = c.initial_state(self.plan); self.controller = c.Coordinator(self.state, c.OUT); self.controller.save()
        self.collected = {'jobs_submitted': 0, 'jobs_verified': 0, 'caps': 0, 'failed_jobs': []}
        self.collect_error = None; self.launch_error = None; self.calls = []
        for target, name, fn in [(c.manager, 'collect_ready', self.collect), (c.launcher, 'launch_ready', self.launch), (c.manager, 'index', self.index)]:
            p = patch.object(target, name, side_effect=fn); p.start(); self.addCleanup(p.stop)

    def collect(self):
        self.calls.append('collect')
        if self.collect_error: raise self.collect_error
        return dict(self.collected)

    def launch(self, execute):
        self.assertTrue(execute); self.calls.append('launch')
        self.assertEqual(read(c.OUT/'state.json')['running_operation'], 'submitting')
        if self.launch_error: raise self.launch_error
        return {'original_jobs': min(480, self.collected['jobs_submitted']+32), 'submitted': 32}

    def index(self):
        self.calls.append('index')
        result = {'all_jobs_verified': True, 'jobs': 480, 'continuations': 23040,
                  'caps': self.collected['caps'], 'complete': self.collected['caps'] == 0}
        write(c.manager.INDEX, result); write(c.manager.ANALYSIS, {'fixture': True}); return result

    def test_collect_before_launch_and_complete_only_after_every_job_verifies(self):
        self.assertFalse(self.controller.tick()); self.assertEqual(self.calls, ['collect', 'launch'])
        self.assertEqual(self.state['jobs_submitted'], 32); self.assertEqual(self.state['stage'], 'waiting_for_original_jobs')
        self.collected.update(jobs_submitted=480, jobs_verified=479)
        self.assertFalse(self.controller.tick()); self.assertNotIn('index', self.calls)
        self.collected['jobs_verified'] = 480
        self.assertTrue(self.controller.tick()); self.assertEqual(self.calls[-2:], ['collect', 'index'])
        self.assertEqual(self.state['stage'], 'complete'); self.assertIsNone(self.state['running_operation'])
        self.assertEqual(self.state['comparison_sha256'], digest(c.manager.ANALYSIS))

    def test_caps_do_not_drop_unfinished_roots_and_complete_is_explicitly_capped(self):
        self.collected.update(jobs_submitted=100, jobs_verified=50, caps=1)
        self.assertFalse(self.controller.tick()); self.assertEqual(self.calls, ['collect', 'launch'])
        self.collected.update(jobs_submitted=480, jobs_verified=480)
        self.assertTrue(self.controller.tick()); self.assertEqual(self.state['stage'], 'complete_with_caps')
        self.assertFalse(read(c.manager.INDEX)['complete'])

    def test_terminal_failure_keeps_evidence_and_stops_before_submission(self):
        self.collected.update(jobs_submitted=32, jobs_verified=31, failed_jobs=[{'job_id': 'b'*24, 'authoritative_status': 'ERROR'}])
        with self.assertRaisesRegex(AssertionError, 'original failed'): self.controller.tick()
        self.assertEqual(self.calls, ['collect']); self.assertEqual(self.state['failed_jobs'], self.collected['failed_jobs'])
        self.assertFalse(c.manager.INDEX.exists())

    def test_unknown_submission_never_repeats_or_clears_interrupted_operation(self):
        self.launch_error = TimeoutError('unknown submission')
        with self.assertRaises(TimeoutError): self.controller.tick()
        self.assertEqual(self.state['stage'], 'stopped_for_inspection'); self.assertEqual(self.state['running_operation'], 'submitting')
        self.launch_error = None
        with self.assertRaisesRegex(AssertionError, 'same original handles'): self.controller.tick()
        self.assertEqual(self.calls, ['collect', 'launch'])

    def test_observation_error_is_not_remote_failure_and_never_triggers_replacement(self):
        self.collect_error = ConnectionError('observation only')
        with self.assertRaises(ConnectionError): self.controller.tick()
        self.assertEqual(self.calls, ['collect']); self.assertEqual(self.state['failed_jobs'], [])
        self.assertEqual(self.state['running_operation'], 'collecting'); self.assertFalse(self.state['remote_cancellations_allowed'])
        with self.assertRaises(AssertionError): self.controller.tick()
        self.assertEqual(self.calls, ['collect'])

    def test_changed_plan_or_management_code_refuses_before_action(self):
        with patch.object(c, 'dependencies', return_value={'fixture': 'b'*64}):
            with self.assertRaisesRegex(AssertionError, 'Pinned'): self.controller.tick()
        write(c.launcher.PLAN, {'changed': True})
        with self.assertRaisesRegex(AssertionError, 'admission changed'): self.controller.tick()
        self.assertEqual(self.calls, [])

    def test_existing_original_submissions_cannot_acquire_a_second_owner(self):
        c.launcher.GUARDS.mkdir(); write(c.launcher.GUARDS/'original.json', {'job_id': 'b'*24})
        with self.assertRaisesRegex(AssertionError, 'original owner'): c.initial_state(self.plan)
        self.assertEqual(self.calls, [])

    def test_dry_run_is_read_only_and_does_not_start_a_coordinator(self):
        missing = self.root/'dry-run-output'
        with patch.object(c, 'OUT', missing), patch.object(c.launcher, 'admission', return_value=(self.plan, {}, {})), redirect_stdout(StringIO()):
            c.main(execute=False)
        self.assertFalse(missing.exists()); self.assertEqual(self.calls, [])


if __name__ == '__main__': unittest.main()
