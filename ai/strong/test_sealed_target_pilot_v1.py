import copy
import unittest

from diagnose_sealed_decisions_v1 import resolution
from run_sealed_target_pilot_v1 import check_result


class SealedTargetAuditTests(unittest.TestCase):
    def test_price_is_second_bid_with_cyclic_priority(self):
        self.assertEqual(resolution({0: 20, 1: 15, 2: 15}, 10, 0, 3), (0, 15))
        self.assertEqual(resolution({0: 20, 1: 15, 2: 15}, 10, 1, 3), (0, 16))
        self.assertEqual(resolution({0: 20, 1: 20, 2: 15}, 10, 1, 3), (1, 20))
        self.assertEqual(resolution({0: 0, 1: 20, 2: 0}, 10, 1, 3), (1, 10))

    def fixture(self):
        root = {'options': [0, 1], 'baseline': 0, 'players': 2, 'request': {'player': 0}}
        rows = []
        for i in range(8):
            rows.append({'env': i, 'sample': i//2, 'actionIndex': i%2, 'truncated': False,
                'value': 0.5, 'searchStats': {'truncated': 0}, 'diagnostic': {
                    'priorSearchStats': {'truncated': 0}, 'sampledWorldSha256': str(i//2)*64,
                    'terminal': [{'powered': 10, 'money': 20, 'cities': 11} for _ in range(2)]}})
        result = {'options': [0, 1], 'samples': 4, 'count': 4, 'begin': 0, 'usable': True,
            'caps': 0, 'outer_caps': 0, 'nested_caps': 0, 'rows': rows, 'seconds': 1.}
        return root, result

    def test_exact_tie_credit_and_shared_worlds(self):
        root, result = self.fixture(); worlds = {}
        report = check_result(result, root, worlds)
        self.assertEqual(report['mean_credits'], {'0': '1/2', '1': '1/2'})
        self.assertEqual(report['paired_margins'], {'0': '0', '1': '0'})
        self.assertEqual(len(worlds), 4)
        self.assertEqual(check_result(result, root, worlds), report)

    def test_reject_corrupt_results(self):
        root, original = self.fixture()
        changes = [lambda d: d['rows'].pop(), lambda d: d['rows'][0].update(value=1),
            lambda d: d['rows'][0].update(truncated=True), lambda d: d.update(nested_caps=1),
            lambda d: d['rows'][0]['diagnostic'].update(sampledWorldSha256='x'*64),
            lambda d: d['rows'][1].update(actionIndex=0)]
        for change in changes:
            with self.subTest(change=change):
                result = copy.deepcopy(original); change(result)
                with self.assertRaises(AssertionError): check_result(result, root)


if __name__ == '__main__':
    unittest.main()
