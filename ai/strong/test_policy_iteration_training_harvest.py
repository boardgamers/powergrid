"""Protect automatic collection boundaries without jobs, gradients, or weights."""
from copy import deepcopy
import hashlib
import importlib.util
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from strategic_collection import ROOT

SPEC = importlib.util.spec_from_file_location('training_harvest', ROOT/'ai/strong/harvest-policy-iteration-training.py')
harvest = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(harvest)


class TrainingHarvestContracts(unittest.TestCase):
    def handoff(self):
        jobs = {'frozen': '1'*24, 'public': '2'*24}
        return {'stage': 'both_jobs_submitted', 'execute': True, 'local_gradients': False,
                'qualification_eligible': False, 'reserved_final_seeds_used': False,
                'labels_complete': True, 'label_shards_verified': 948, 'jobs_submitted': jobs,
                'launch_evidence': {head: {'head_type': head, 'job_id': job,
                    'remote_archive_verified': True, 'qualification_eligible': False} for head, job in jobs.items()}}

    def test_only_complete_archived_submission_handoff_is_ready(self):
        state = self.handoff()
        self.assertTrue(harvest.upstream_ready(state))
        for stage in harvest.WAIT_STAGES:
            self.assertFalse(harvest.upstream_ready({**state, 'stage': stage}))
        mutations = [('stage', 'stopped_with_error'), ('stage', 'wait_window_ended'),
                     ('labels_complete', False), ('label_shards_verified', 947),
                     ('execute', False), ('local_gradients', True),
                     ('qualification_eligible', True), ('reserved_final_seeds_used', True)]
        for field, value in mutations:
            with self.subTest(field=field, value=value), self.assertRaises(AssertionError):
                harvest.upstream_ready({**state, field: value})
        for bad in [{'frozen': '1'*24}, {'frozen': '1'*24, 'public': '1'*24},
                    {'frozen': 'not-a-job-id', 'public': '2'*24}]:
            with self.assertRaises(AssertionError):
                harvest.upstream_ready({**state, 'jobs_submitted': bad})
        for field, value in [('job_id', '3'*24), ('remote_archive_verified', False),
                             ('head_type', 'public'), ('qualification_eligible', True)]:
            bad = deepcopy(state)
            bad['launch_evidence']['frozen'][field] = value
            with self.subTest(field=field), self.assertRaises(AssertionError):
                harvest.upstream_ready(bad)

    def test_guard_must_match_exact_job_source_data_and_recipe(self):
        state = self.handoff()
        design = {'seeds': [12101, 12102, 12103, 12104]}
        data_pin, source = {'fixture': 'data'}, {'fixture': 'source'}
        guard = {'stage': 'launched', 'job_id': '1'*24, 'head_type': 'frozen',
                 'seeds': design['seeds'], 'source': source, 'data_pin': data_pin,
                 'flavor': 'l4x1', 'timeout_hours': 3, 'qualification_eligible': False,
                 'bootstrap_sha256': hashlib.sha256(harvest.BOOTSTRAP.encode()).hexdigest()}
        harvest.guard_matches(guard, 'frozen', state, design, data_pin, source)
        for field, value in [('stage', 'launch_unknown'), ('job_id', '2'*24), ('head_type', 'public'),
                             ('source', {}), ('data_pin', {}), ('seeds', [12101]),
                             ('flavor', 'cpu-upgrade'), ('timeout_hours', 1),
                             ('bootstrap_sha256', '0'*64), ('qualification_eligible', True)]:
            with self.subTest(field=field), self.assertRaises(AssertionError):
                harvest.guard_matches({**guard, field: value}, 'frozen', state, design, data_pin, source)

    def test_changed_verifier_or_missing_proof_cannot_be_archived(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root/'verification.py'
            path.write_text('original')
            expected = {'verification.py': harvest.digest(path)}
            with patch.object(harvest, 'ROOT', root):
                harvest.check_code(expected)
                path.write_text('changed')
                with self.assertRaises(AssertionError):
                    harvest.check_code(expected)
            with patch.object(harvest, 'VERIFIED', root/'missing'):
                with self.assertRaises(FileNotFoundError):
                    harvest.verify_outputs('frozen', {}, {}, {})


if __name__ == '__main__':
    unittest.main()
