"""Do not confuse an interrupted waiter with permission to replace jobs."""
from copy import deepcopy
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('owner_recovery', Path(__file__).with_name('recover-conservative-auction-development-v2.py'))
recovery = importlib.util.module_from_spec(spec); spec.loader.exec_module(recovery)


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.state = {'pid': 1685160, 'stage': 'stopped_for_inspection', 'failure_type': 'KeyboardInterrupt',
            'failure': 'Owner interrupted by signal 15; preserve original submissions',
            'original_pilots': recovery.HANDLES, 'development_submitted': 0}
        self.args = dict(state=self.state, state_sha=recovery.STOPPED_SHA, process_live=False,
            stop_present=False, development_exists=False, statuses={j: 'RUNNING' for j in recovery.HANDLES})

    def test_reviewed_waiter_termination_admitted(self):
        recovery.admit(**self.args)

    def test_live_owner_stop_marker_changed_state_or_existing_development_rejected(self):
        for k, v in [('process_live', True), ('stop_present', True), ('development_exists', True), ('state_sha', 'a'*64)]:
            with self.subTest(field=k), self.assertRaises(AssertionError): recovery.admit(**{**self.args, k: v})
        for k, v in [('failure_type', 'AssertionError'), ('development_submitted', 1), ('original_pilots', [])]:
            state = deepcopy(self.state); state[k] = v
            with self.subTest(field=k), self.assertRaises(AssertionError): recovery.admit(**{**self.args, 'state': state})

    def test_failed_missing_or_extra_original_handle_rejected(self):
        for status in ('ERROR', 'CANCELED', 'TIMEOUT', 'UNKNOWN'):
            statuses = dict(self.args['statuses']); statuses[recovery.HANDLES[0]] = status
            with self.subTest(status=status), self.assertRaises(AssertionError): recovery.admit(**{**self.args, 'statuses': statuses})
        for statuses in ({}, {**self.args['statuses'], 'extra': 'RUNNING'}):
            with self.assertRaises(AssertionError): recovery.admit(**{**self.args, 'statuses': statuses})


if __name__ == '__main__': unittest.main()
