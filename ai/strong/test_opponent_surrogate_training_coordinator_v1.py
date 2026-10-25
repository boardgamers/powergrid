"""One-owner sequencing and no-duplicate-job controls; no real HF submissions."""
from contextlib import redirect_stdout
from io import StringIO
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from strategic_collection import ROOT, read, write

spec = importlib.util.spec_from_file_location('training_coordinator_test', ROOT/'ai/strong/coordinate-opponent-surrogate-training-v1.py')
coordinator = importlib.util.module_from_spec(spec); spec.loader.exec_module(coordinator)


class CoordinatorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.p = coordinator.paths(Path(self.temp.name)); self.p['out'].mkdir(parents=True)
        self.hash_patch = patch.object(coordinator, 'code_hashes', return_value={'fixture': 'a'*64})
        self.hash_patch.start(); self.addCleanup(self.hash_patch.stop)
        self.state = coordinator.initial_state(self.p); self.calls = []; self.observations = []
        self.remote = {'c'*24: 'RUNNING', 'f'*24: 'RUNNING'}
        self.controller = coordinator.Coordinator(self.p, self.state, runner=self.run_fake, inspector=self.inspect_fake)
        self.controller.save()

    def collection(self, complete=True):
        self.p['collection'].parent.mkdir(parents=True, exist_ok=True)
        write(self.p['collection'], {'complete': complete, 'games': 2560, 'twins': 640,
            'cases': {str(i): {} for i in range(40)}, 'split_games': {'train': 1920, 'validation': 320, 'test': 320}})

    def inspect_fake(self, job_id):
        self.observations.append(job_id); response = self.remote[job_id]
        if isinstance(response, Exception): raise response
        return response

    def run_fake(self, argv, logfile, home):
        action = self.state['running_action']; self.calls.append((action, argv))
        self.assertEqual(home, self.p['home'])
        self.assertEqual(read(self.p['out']/'state.json')['running_action'], action)
        Path(logfile).write_text('Synthetic orchestration fixture; no HF request.\n')
        value = {'fixture': action}
        if action.startswith('launch_'):
            mode = action.removeprefix('launch_')
            value = {'stage': 'launched', 'mode': mode, 'job_id': ('c' if mode == 'calibration' else 'f')*24}
        elif action == 'select_validation':
            value = {'complete': True, 'test_labels_used': False, 'selection': 'seed-14101', 'learned_surrogate_selected': True}
        output = coordinator.artifact(action, self.p); output.parent.mkdir(parents=True, exist_ok=True); write(output, value)

    def advance_to_calibration(self):
        self.collection()
        for _ in range(4): self.assertFalse(self.controller.tick())
        self.assertEqual([a for a, _ in self.calls], list(coordinator.ACTIONS[:4]))

    def test_waits_without_complete_collection_and_refuses_partial_index(self):
        for _ in range(2): self.assertFalse(self.controller.tick())
        self.assertEqual(self.calls, []); self.assertEqual(self.observations, [])
        self.collection(complete=False)
        with self.assertRaises(AssertionError): self.controller.tick()
        self.assertEqual(self.calls, [])

    def test_full_sequence_uses_two_original_handles_and_selection_last(self):
        self.advance_to_calibration()
        for _ in range(2): self.assertFalse(self.controller.tick())
        self.assertEqual(len(self.calls), 4); self.assertEqual(self.observations, ['c'*24]*2)
        self.remote['c'*24] = 'COMPLETED'
        self.assertFalse(self.controller.tick())  # Independently collect calibration.
        self.assertFalse(self.controller.tick())  # Launch full training with existing admission checks.
        self.assertEqual(self.calls[-1][0], 'launch_full')
        self.assertFalse(self.controller.tick()); self.assertEqual(self.observations[-1], 'f'*24)
        self.remote['f'*24] = 'COMPLETED'
        self.assertFalse(self.controller.tick()); self.assertFalse(self.controller.tick()); self.assertTrue(self.controller.tick())
        self.assertEqual([a for a, _ in self.calls], list(coordinator.ACTIONS))
        self.assertEqual(sum('--execute' in argv for _, argv in self.calls), 2)
        for _, argv in self.calls:
            self.assertFalse(any(Path(arg).name in ('train-opponent-surrogate-v1.py', 'benchmark-opponent-surrogate-training-v1.py') for arg in argv))
        self.assertEqual(self.state['stage'], 'complete')
        self.assertFalse(self.state['test_labels_used_for_selection'])

    def test_transient_observation_failure_never_relaunches(self):
        self.advance_to_calibration(); self.remote['c'*24] = TimeoutError('Observation only')
        self.assertFalse(self.controller.tick()); self.assertEqual(len(self.calls), 4)
        self.remote['c'*24] = 'RUNNING'
        self.assertFalse(self.controller.tick()); self.assertEqual(len(self.calls), 4)
        self.assertEqual(self.observations, ['c'*24]*2)

    def test_failed_job_stops_before_full_training(self):
        self.advance_to_calibration(); self.remote['c'*24] = 'ERROR'
        with self.assertRaisesRegex(AssertionError, 'Original calibration'): self.controller.tick()
        self.assertEqual(len(self.calls), 4)
        self.assertFalse((self.p['guards']/'full.json').exists())

    def test_uncertain_launch_preserved_without_automatic_retry(self):
        self.collection()
        for _ in range(3): self.controller.tick()
        def unknown(argv, logfile, home):
            self.calls.append(('uncertain', argv))
            path = self.p['guards']/'calibration.json'; path.parent.mkdir(parents=True)
            write(path, {'stage': 'launch_unknown', 'mode': 'calibration'})
            raise TimeoutError('Submission outcome unknown')
        self.controller.runner = unknown
        with self.assertRaises(TimeoutError): self.controller.tick()
        self.assertEqual(self.state['running_action'], 'launch_calibration')
        self.assertEqual(read(self.p['guards']/'calibration.json')['stage'], 'launch_unknown')
        with self.assertRaisesRegex(AssertionError, 'never auto-retry'): self.controller.tick()
        self.assertEqual(len(self.calls), 4)

    def test_unknown_upload_or_partial_preparation_never_repeats(self):
        self.collection(); self.controller.tick()
        def interrupted(argv, logfile, home):
            self.calls.append(('interrupted_archive', argv)); self.p['data_archive'].mkdir()
            raise ConnectionError('Original archive outcome unknown')
        self.controller.runner = interrupted
        with self.assertRaises(ConnectionError): self.controller.tick()
        with self.assertRaisesRegex(AssertionError, 'never auto-retry'): self.controller.tick()
        self.assertEqual(len(self.calls), 2)

    def test_changed_code_or_completed_artifact_stops_next_action(self):
        self.collection(); self.controller.tick()
        with patch.object(coordinator, 'code_hashes', return_value={'fixture': 'b'*64}):
            with self.assertRaisesRegex(AssertionError, 'Pinned'): self.controller.tick()
        write(self.p['data']/'data-check.json', {'tampered': True})
        with self.assertRaisesRegex(AssertionError, 'Completed evidence'): self.controller.tick()
        self.assertEqual(len(self.calls), 1)

    def test_another_owner_output_is_not_overwritten(self):
        self.collection(); path = self.p['data']/'data-check.json'; path.parent.mkdir(parents=True)
        write(path, {'other_owner': True})
        with self.assertRaisesRegex(AssertionError, 'Another owner'): self.controller.tick()
        self.assertEqual(read(path), {'other_owner': True}); self.assertEqual(self.calls, [])

    def test_dry_run_has_no_file_or_network_side_effects(self):
        with tempfile.TemporaryDirectory() as temp:
            p = coordinator.paths(temp)
            with patch.object(coordinator, 'paths', return_value=p), patch.object(coordinator, 'HfApi') as api, redirect_stdout(StringIO()):
                coordinator.main(False)
                api.assert_not_called()
            self.assertFalse(p['out'].exists()); self.assertEqual(list(Path(temp).iterdir()), [])

    def test_prior_winning_selection_finishes_without_opening_test_split(self):
        self.advance_to_calibration(); self.remote['c'*24] = self.remote['f'*24] = 'COMPLETED'
        for _ in range(3): self.controller.tick()
        original = self.controller.runner
        def prior(argv, logfile, home):
            original(argv, logfile, home)
            write(self.p['selection']/'frozen.json', {'complete': True, 'test_labels_used': False,
                  'selection': 'economic-prior', 'learned_surrogate_selected': False})
        self.controller.runner = prior; self.controller.tick()
        self.assertTrue(self.controller.tick())
        self.assertFalse(self.state['learned_surrogate_selected'])
        self.assertEqual(len(self.calls), 8)


if __name__ == '__main__': unittest.main()
