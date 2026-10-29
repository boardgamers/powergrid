"""Resume ownership and original-handle safety; all remote operations mocked."""
from contextlib import ExitStack
import importlib.util
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch


spec = importlib.util.spec_from_file_location('network_resume', Path(__file__).with_name('coordinate-current-auction-network-resume-v1.py'))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class NetworkResumeTests(unittest.TestCase):
    def setUp(self):
        self.owner_module = m.original_owner()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.old = self.root / 'old'
        self.old.mkdir()
        self.jobs = self.root / 'jobs'
        (self.jobs / 'one').mkdir(parents=True)
        self.guard = self.jobs / 'one/launch.json'
        self.guard.write_text(json.dumps({'stage': 'launched', 'job_id': 'a' * 24}))
        (self.root / 'code.py').write_text('original frozen code')
        (self.root / 'resume.py').write_text('synthetic resume source')
        (self.root / 'initial.json').write_text(json.dumps({'verified_jobs': 1, 'jobs': [{'job_id': 'a' * 24, 'verified': True}]}))
        self.state = {'pid': 999999999, 'stage': 'stopped_for_inspection',
                      'failure_type': 'ConnectError', 'failure': '[Errno -2] Name or service not known',
                      'code_hashes': {'code.py': m.digest(self.root / 'code.py')},
                      'source_sha256': 'b' * 64, 'recovery_rule': 'unchanged'}
        self.review = {'ready_for_deliberate_resume': True, 'original_jobs_only': True,
                       'automatic_restarts': False, 'reserved_final_seeds_used': False,
                       'input_hashes': {}, 'original_guard_hashes': {},
                       'submitted_jobs': 1, 'original_handles': ['a' * 24],
                       'initial_collection': 'initial.json', 'audited_jobs': 1}
        self.manager = SimpleNamespace(OUT=self.jobs,
            recovery=SimpleNamespace(complete_data=lambda j: j.get('verified')),
            admitted=Mock(), source_checked=Mock(return_value={'games': 26880, 'rows': [{}] * 944, 'max_active_jobs': 64}),
            collect=Mock(), launch=Mock())
        self.save_review()
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        for key, value in [('ROOT', self.root), ('OLD_OUT', self.old), ('OUT', self.root / 'new'),
                           ('REVIEW', self.root / 'review.json'), ('__file__', str(self.root / 'resume.py'))]:
            self.stack.enter_context(patch.object(m, key, value))

    def save_review(self):
        (self.old / 'state.json').write_text(json.dumps(self.state))
        self.review['input_hashes'] = {n: m.digest(self.root / n) for n in ('old/state.json', 'initial.json')}
        self.review['original_guard_hashes'] = {'jobs/one/launch.json': m.digest(self.guard)}
        (self.root / 'review.json').write_text(json.dumps(self.review))

    def owner_for_main(self):
        owner = self.owner_module
        owner.ROOT = self.root
        owner.manager_module = lambda: self.manager
        self.stack.enter_context(patch.object(m, 'original_owner', return_value=owner))
        self.stack.enter_context(patch.object(m.signal, 'signal'))
        self.stack.enter_context(patch('sys.argv', ['test', '--start-reviewed']))
        return owner

    def test_valid_original_reconciliation(self):
        review, old = m.checked_review(self.manager)
        self.assertEqual(review['original_handles'], ['a' * 24])
        self.assertEqual(old, self.state)
        self.manager.admitted.assert_called_once()

    def test_live_prior_owner_rejected(self):
        self.state['pid'] = os.getpid()
        self.save_review()
        with self.assertRaisesRegex(AssertionError, 'exited'):
            m.checked_review(self.manager)

    def test_changed_frozen_input_rejected(self):
        (self.root / 'code.py').write_text('changed')
        with self.assertRaises(AssertionError):
            m.checked_review(self.manager)

    def test_unknown_original_submission_rejected(self):
        (self.jobs / 'two').mkdir()
        (self.jobs / 'two/launch.json').write_text('{}')
        with self.assertRaisesRegex(AssertionError, 'unknown submissions'):
            m.checked_review(self.manager)

    def test_ambiguous_launch_intent_rejected(self):
        self.guard.write_text(json.dumps({'stage': 'intent', 'job_id': 'a' * 24}))
        self.save_review()
        with self.assertRaisesRegex(AssertionError, 'Ambiguous submission'):
            m.checked_review(self.manager)

    def test_pause_marker_prevents_resume(self):
        (self.old / 'STOP').touch()
        with self.assertRaisesRegex(AssertionError, 'pause'):
            m.checked_review(self.manager)

    def test_other_failure_is_not_implicitly_admitted(self):
        self.state['failure_type'] = 'ValueError'
        self.save_review()
        with self.assertRaises(AssertionError):
            m.checked_review(self.manager)

    def test_missing_deliberate_review_rejected(self):
        self.review['ready_for_deliberate_resume'] = False
        self.save_review()
        with self.assertRaises(AssertionError):
            m.checked_review(self.manager)

    def test_existing_resume_state_never_restarted(self):
        owner = self.owner_for_main()
        m.OUT.mkdir()
        (m.OUT / 'state.json').write_text('preserve')
        with self.assertRaisesRegex(AssertionError, 'never automatically restart'):
            m.main()
        self.assertEqual((m.OUT / 'state.json').read_text(), 'preserve')
        self.manager.collect.assert_not_called()
        self.manager.launch.assert_not_called()

    def test_collection_failure_stops_without_submitting_or_changing_old_state(self):
        self.owner_for_main()
        self.manager.collect.side_effect = ValueError('incomplete original evidence')
        original = (self.old / 'state.json').read_bytes()
        with self.assertRaisesRegex(ValueError, 'incomplete original'):
            m.main()
        saved = json.loads((m.OUT / 'state.json').read_text())
        self.assertEqual(saved['stage'], 'stopped_for_inspection')
        self.assertEqual(saved['failure_type'], 'ValueError')
        self.assertEqual((self.old / 'state.json').read_bytes(), original)
        self.manager.launch.assert_not_called()


if __name__ == '__main__':
    unittest.main()
