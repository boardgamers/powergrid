"""Reject untrained/incomplete exports before packaging or target execution."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from strategic_collection import ROOT

SPEC = importlib.util.spec_from_file_location('trained_8840u', ROOT/'ai/strong/benchmark-policy-iteration-trained-8840u.py')
benchmark = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(benchmark)


class TrainedTargetContracts(unittest.TestCase):
    def handoff(self):
        state = {'stage': 'both_heads_verified_and_archived', 'execute': True,
                 'local_gradients': False, 'qualification_eligible': False,
                 'reserved_final_seeds_used': False, 'heads_verified': {}}
        for head, job, sha in [('frozen', '1'*24, 'a'*64), ('public', '2'*24, 'b'*64)]:
            state['heads_verified'][head] = {'head_type': head, 'job_id': job,
                'remote_archive_verified': True, 'local_gradients': False,
                'qualification_eligible': False, 'verified_sha256': sha,
                'candidate_pins': {head+'-'+str(penalty): {'pin': {
                    'key': head+'-'+str(penalty), 'training_verified': True,
                    'training_verified_sha256': sha, 'qualification_eligible': False}}
                    for penalty in [0, 1]}}
        return state

    def test_rejects_incomplete_failed_synthetic_or_unarchived_handoffs(self):
        state = self.handoff()
        benchmark.require_trained_handoff(state)
        for field, value in [('stage', 'waiting_for_training_submission'),
                             ('stage', 'stopped_with_error'), ('execute', False),
                             ('local_gradients', True), ('qualification_eligible', True),
                             ('reserved_final_seeds_used', True)]:
            with self.subTest(field=field, value=value), self.assertRaises(AssertionError):
                benchmark.require_trained_handoff({**state, field: value})
        bad = deepcopy(state)
        del bad['heads_verified']['public']
        with self.assertRaises(AssertionError):
            benchmark.require_trained_handoff(bad)
        for field, value in [('remote_archive_verified', False), ('job_id', '2'*24),
                             ('head_type', 'public'), ('verified_sha256', '0'*64)]:
            bad = deepcopy(state)
            bad['heads_verified']['frozen'][field] = value
            with self.subTest(field=field), self.assertRaises(AssertionError):
                benchmark.require_trained_handoff(bad)
        for field, value in [('synthetic_untrained', True), ('training_verified', False),
                             ('training_verified_sha256', '0'*64), ('key', 'public-1')]:
            bad = deepcopy(state)
            bad['heads_verified']['frozen']['candidate_pins']['frozen-0']['pin'][field] = value
            with self.subTest(field=field), self.assertRaises(AssertionError):
                benchmark.require_trained_handoff(bad)

    def test_not_ready_has_no_filesystem_or_network_side_effects(self):
        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            upstream = base/'upstream.json'
            upstream.write_text(json.dumps({'stage': 'waiting_for_training_submission'}))
            with patch.object(benchmark, 'UPSTREAM', upstream), \
                 patch.object(benchmark, 'PREPARED', base/'prepared'), \
                 patch.object(benchmark, 'hf_hub_download') as download, \
                 patch.object(benchmark.subprocess, 'run') as execute:
                with self.assertRaisesRegex(AssertionError, 'not ready'):
                    benchmark.prepare()
                self.assertFalse((base/'prepared').exists())
                download.assert_not_called()
                execute.assert_not_called()

    def test_existing_target_launch_is_never_repeated(self):
        with TemporaryDirectory() as tmp:
            guard = Path(tmp)/'guard.json'
            guard.write_text(json.dumps({'stage': 'launch_or_observation_unknown'}))
            with patch.object(benchmark, 'GUARD', guard), \
                 patch.object(benchmark, 'prepared_manifest') as prepared, \
                 patch.object(benchmark.subprocess, 'run') as execute:
                with self.assertRaisesRegex(AssertionError, 'do not retry'):
                    benchmark.run()
                prepared.assert_not_called()
                execute.assert_not_called()


if __name__ == '__main__':
    unittest.main()
