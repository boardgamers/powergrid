"""Failure/recovery tests; never contact HF or launch actual jobs."""
import importlib.util
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

spec = importlib.util.spec_from_file_location('coordinator', Path(__file__).with_name('population-coordinator.py'))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class CoordinatorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.c = m.Coordinator.__new__(m.Coordinator)
        self.c.root = Path(self.temp.name)
        self.c.fixtures = self.c.root / 'fixtures.jsonl'
        self.c.config = {'training_jobs': {'control': 'trainer'},
            'earliest_commit': '2026-10-10T09:18:00+00:00'}
        self.c.protocol = {'arms': {'control': {'run': 'train'}}, 'checkpoint_updates': [9, 19]}
        self.c.state = {'checkpoints': {}, 'comparisons': {}}
        self.c.api = Mock()
        self.c.api.model_info.return_value.sha = 'a' * 40
        self.c.api.inspect_job.return_value.status.stage = 'RUNNING'
        self.c.api.list_repo_commits.return_value = []
        self.c.persist = Mock()
        self.c.command = Mock()
        self.c.checked = {'control': set()}

    def entry(self, phase='validated', screens=None):
        e = {'arm': 'control', 'update': 9, 'revision': 'a' * 40,
            'phase': phase, 'screens': screens or {}}
        self.c.state['checkpoints']['control-u9'] = e
        d = self.c.root / 'control-u9'
        d.mkdir()
        (d / 'screen-plan.json').write_text(json.dumps([
            {'run': 'arena', 'argv': ['bash', 'launch.sh'], 'env': {}}]))
        return e

    def test_rejects_metrics_from_newer_checkpoint_upload(self):
        metrics = [{'stage': 'train', 'update': u} for u in range(10)]
        self.assertIsNone(m.matching_checkpoint_update(metrics, 8))
        self.assertEqual(m.matching_checkpoint_update(metrics, 9), 9)
        self.assertIsNone(m.matching_checkpoint_update(metrics + [metrics[-1]], 9))
        self.assertIsNone(m.matching_checkpoint_update(metrics[1:], 9))

    def test_recorded_job_not_relaunched(self):
        e = self.entry(screens={'arena': {'job_id': 'b' * 24}})
        self.c.advance_checkpoint('control-u9')
        self.assertEqual(e['phase'], 'evaluating')
        self.c.command.assert_not_called()
        self.c.api.inspect_job.assert_called_once_with(job_id='b' * 24)

    def test_unresolved_launch_intent_requires_attention(self):
        e = self.entry(screens={'arena': {'phase': 'launching'}})
        self.c.advance_checkpoint('control-u9')
        self.assertEqual(e['phase'], 'launch_unknown')
        self.c.command.assert_not_called()

    def test_validation_failure_never_launches(self):
        e = self.entry(phase='selected')
        self.c.command.side_effect = RuntimeError('export mismatch')
        self.c.advance_checkpoint('control-u9')
        self.assertEqual(e['phase'], 'validation_failed')
        self.assertEqual(self.c.command.call_count, 1)
        self.assertIn('prepare-population-screen.py', self.c.command.call_args.args[0][1])
        self.assertFalse(e['screens'])

    def test_ambiguous_response_never_retried(self):
        e = self.entry()
        self.c.command.return_value = 'response lost'
        self.c.advance_checkpoint('control-u9')
        self.c.advance_checkpoint('control-u9')
        self.assertEqual(e['phase'], 'launch_unknown')
        self.assertEqual(self.c.command.call_count, 1)

    def test_persisted_intent_precedes_submission(self):
        e = self.entry()
        def launch(*args):
            self.assertEqual(e['screens']['arena']['phase'], 'launching')
            self.assertEqual(self.c.persist.call_args.args[0]['stage'], 'launch_intent')
            return 'Job: ' + 'b' * 24
        self.c.command.side_effect = launch
        self.c.advance_checkpoint('control-u9')
        self.assertEqual(e['screens']['arena']['job_id'], 'b' * 24)
        self.assertEqual(e['phase'], 'evaluating')

    def test_timeout_observes_same_job_next_cycle(self):
        e = self.entry(phase='evaluating', screens={'arena': {'job_id': 'b' * 24}})
        self.c.api.inspect_job.side_effect = [TimeoutError('read timeout'),
            SimpleNamespace(status=SimpleNamespace(stage='RUNNING'))]
        with self.assertRaises(TimeoutError):
            self.c.advance_checkpoint('control-u9')
        self.c.advance_checkpoint('control-u9')
        self.assertEqual(e['phase'], 'evaluating')
        self.assertEqual([c.kwargs['job_id'] for c in self.c.api.inspect_job.call_args_list], ['b' * 24] * 2)
        self.c.command.assert_not_called()

    def test_missing_checkpoint_does_not_abandon_running_screen(self):
        e = self.entry(phase='evaluating', screens={'arena': {'job_id': 'b' * 24}})
        self.c.api.inspect_job.side_effect = lambda job_id: SimpleNamespace(
            status=SimpleNamespace(stage='ERROR' if job_id == 'trainer' else 'RUNNING'))
        self.c.consider_revision = Mock(return_value=9)
        self.c.compare_ready = Mock()
        self.assertFalse(self.c.cycle())
        self.assertEqual(self.c.state['missing_checkpoints'], ['control-u19'])
        e['phase'] = 'screen_failed'
        self.assertTrue(self.c.cycle())
        self.assertEqual(self.c.state['outcome'], 'needs_attention')

    def test_failed_screen_does_not_abandon_live_peers(self):
        e = self.entry(phase='evaluating', screens={
            'first': {'job_id': 'bad'}, 'second': {'job_id': 'live'}})
        self.c.api.inspect_job.side_effect = lambda job_id: SimpleNamespace(
            status=SimpleNamespace(stage='ERROR' if job_id == 'bad' else 'RUNNING'))
        self.c.advance_checkpoint('control-u9')
        self.assertEqual(e['phase'], 'evaluating')
        self.c.api.inspect_job.side_effect = lambda job_id: SimpleNamespace(
            status=SimpleNamespace(stage='ERROR' if job_id == 'bad' else 'COMPLETED'))
        self.c.advance_checkpoint('control-u9')
        self.assertEqual(e['phase'], 'screen_failed')
        self.c.command.assert_not_called()

    def test_all_collected_requires_both_comparisons(self):
        self.c.consider_revision = Mock(return_value=19)
        self.c.compare_ready = Mock()
        for u in [9, 19]:
            self.c.state['checkpoints'][f'control-u{u}'] = {'phase': 'collected'}
        self.c.state['comparisons'] = {'9': 'a', '19': 'b'}
        self.assertTrue(self.c.cycle())
        self.assertEqual(self.c.state['outcome'], 'completed')

    def test_immutable_history_recovers_scheduled_update(self):
        self.c.protocol['checkpoint_updates'] = [9]
        self.c.api.list_repo_commits.return_value = [SimpleNamespace(
            commit_id='c' * 40, created_at=m.datetime.fromisoformat('2026-10-10T10:00:00+00:00'))]
        def consider(arm, revision):
            if revision == 'c' * 40:
                self.c.state['checkpoints']['control-u9'] = {'phase': 'collected'}
                return 9
            return 19
        self.c.consider_revision = Mock(side_effect=consider)
        self.c.compare_ready = Mock()
        self.c.state['comparisons']['9'] = 'done'
        self.assertTrue(self.c.cycle())
        self.assertEqual(self.c.consider_revision.call_args_list[-1].args, ('control', 'c' * 40))


if __name__ == '__main__':
    unittest.main()
