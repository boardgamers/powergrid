"""Exercise no-duplicate launch, final-only validation and observation recovery."""
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
import five_plant_coordinator as m


class CoordinatorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.c = m.Coordinator.__new__(m.Coordinator)
        self.c.root = Path(self.temp.name)
        self.c.config = {'training_jobs': {'full': 'trainer'}}
        self.c.protocol = {}
        self.c.state = {'entries': {'full': {'phase': 'waiting_training'}}}
        self.c.api = Mock()
        self.c.api.model_info.return_value.sha = 'a' * 40
        self.c.api.inspect_job.return_value.status.stage = 'RUNNING'
        self.c.persist = Mock()
        self.c.command = Mock(return_value=json.dumps({'key': 'full', 'stage': 'launched',
            'model_revision': 'a' * 40, 'job_id': 'b' * 24}))
        self.c.collect = Mock()
        self.prepare = patch.object(m, 'prepare', return_value={}).start()
        self.addCleanup(patch.stopall)

    def test_no_intermediate_checkpoint_selection(self):
        self.c.advance('full')
        self.prepare.assert_not_called()
        self.c.command.assert_not_called()

    def test_final_validation_before_launch(self):
        self.c.api.inspect_job.side_effect = lambda job_id: SimpleNamespace(
            status=SimpleNamespace(stage='COMPLETED' if job_id == 'trainer' else 'RUNNING'))
        def launch(*args):
            self.assertEqual(self.c.state['entries']['full']['phase'], 'launching')
            self.assertEqual(self.c.persist.call_args.args[0]['stage'], 'launch_intent')
            self.prepare.assert_called_once()
            return json.dumps({'key': 'full', 'stage': 'launched', 'model_revision': 'a' * 40, 'job_id': 'b' * 24})
        self.c.command.side_effect = launch
        self.c.advance('full')
        self.c.advance('full')
        self.assertEqual(self.c.command.call_count, 1)

    def test_validation_failure_does_not_launch(self):
        self.c.api.inspect_job.return_value.status.stage = 'COMPLETED'
        self.prepare.side_effect = AssertionError('wrong update')
        self.c.advance('full')
        self.assertEqual(self.c.state['entries']['full']['phase'], 'validation_failed')
        self.c.command.assert_not_called()

    def test_unknown_post_is_never_retried(self):
        self.c.state['entries']['full'].update(phase='validated', revision='a' * 40)
        self.c.command.side_effect = RuntimeError('response lost')
        self.c.advance('full')
        self.c.advance('full')
        self.assertEqual(self.c.command.call_count, 1)
        self.assertEqual(self.c.state['entries']['full']['phase'], 'launch_unknown')

    def test_recovered_intent_is_not_submitted(self):
        self.c.state['entries']['full'].update(phase='launching', revision='a' * 40)
        self.c.advance('full')
        self.c.command.assert_not_called()
        self.assertEqual(self.c.state['entries']['full']['phase'], 'launch_unknown')

    def test_persist_failure_prevents_submission(self):
        self.c.state['entries']['full'].update(phase='validated', revision='a' * 40)
        self.c.persist.side_effect = TimeoutError('upload timeout')
        with self.assertRaises(TimeoutError):
            self.c.advance('full')
        self.c.persist.side_effect = None
        self.c.advance('full')
        self.c.command.assert_not_called()

    def test_observation_timeout_keeps_same_handle(self):
        self.c.state['entries']['full'].update(phase='evaluating', job_id='b' * 24)
        self.c.api.inspect_job.side_effect = [TimeoutError(), SimpleNamespace(status=SimpleNamespace(stage='RUNNING'))]
        self.c.cycle()
        self.c.cycle()
        self.assertEqual([x.kwargs['job_id'] for x in self.c.api.inspect_job.call_args_list], ['b' * 24] * 2)
        self.c.command.assert_not_called()

    def test_failure_does_not_abandon_live_peer(self):
        self.c.state['entries']['full']['phase'] = 'training_failed'
        self.c.state['entries']['parent'] = {'phase': 'evaluating', 'job_id': 'parent'}
        self.assertFalse(self.c.cycle())
        self.c.api.inspect_job.assert_called_once_with(job_id='parent')

    def test_existing_parent_collected_without_launch(self):
        self.c.state['entries'] = {'parent': {'phase': 'evaluating', 'job_id': 'parent'}}
        self.c.api.inspect_job.return_value.status.stage = 'COMPLETED'
        self.c.advance('parent')
        self.c.command.assert_not_called()
        self.c.collect.assert_called_once_with('parent', 'a' * 40)

    def test_unknown_stage_does_not_imply_terminal(self):
        self.c.api.inspect_job.return_value.status.stage = 'UNRECOGNIZED'
        self.c.advance('full')
        self.assertEqual(self.c.state['entries']['full']['phase'], 'waiting_training')
        self.c.state['entries']['full'].update(phase='evaluating', job_id='b' * 24)
        self.c.advance('full')
        self.assertEqual(self.c.state['entries']['full']['phase'], 'evaluating')
        self.c.command.assert_not_called()


if __name__ == '__main__':
    unittest.main()
