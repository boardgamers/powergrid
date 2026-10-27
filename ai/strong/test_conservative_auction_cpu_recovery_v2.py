"""Preserved-prefix recovery admission only; no requests or simulations."""
from copy import deepcopy
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('cpu_recovery', Path(__file__).with_name('recover-conservative-auction-cpu-v2.py'))
recovery = importlib.util.module_from_spec(spec); spec.loader.exec_module(recovery)


class PrefixTests(unittest.TestCase):
    def setUp(self):
        self.cases = [{'name': str(i)} for i in range(100)]
        self.rows = [{'arm': a, 'case': c['name']} for a in ('filter', 'conservative_population', 'conservative_dual') for c in self.cases][:273]
        self.args = {'rows': self.rows, 'cases': self.cases, 'original': {'pid': 1904528, 'stage': 'running', 'completed_requests': 273},
            'live': [], 'stop': False, 'status_sha': recovery.STATUS_SHA, 'prefix_sha': recovery.PREFIX_SHA}

    def test_exact_missing_suffix_only(self):
        missing = recovery.validate_prefix(**self.args)
        self.assertEqual(missing, [('conservative_dual', str(i)) for i in range(73, 100)])

    def test_live_stop_changed_evidence_or_nonprefix_rejected(self):
        variants = [('live', [1904528]), ('stop', True), ('status_sha', 'a'*64), ('prefix_sha', 'b'*64),
                    ('rows', self.rows[:-1]), ('rows', list(reversed(self.rows))), ('rows', [self.rows[0], *self.rows[:-1]])]
        for key, value in variants:
            with self.subTest(key=key), self.assertRaises(AssertionError): recovery.validate_prefix(**{**self.args, key: value})

    def test_wrong_process_count_or_failure_state_rejected(self):
        for key, value in [('pid', 1), ('completed_requests', 274), ('stage', 'failed')]:
            original = deepcopy(self.args['original']); original[key] = value
            with self.subTest(key=key), self.assertRaises(AssertionError): recovery.validate_prefix(**{**self.args, 'original': original})


if __name__ == '__main__': unittest.main()
