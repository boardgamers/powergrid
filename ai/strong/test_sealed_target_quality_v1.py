import copy
from fractions import Fraction
import unittest

from run_sealed_target_quality_v1 import check_result, choose, compare_halves


class QualityTests(unittest.TestCase):
    def fixture(self):
        root = {'options': [0, 1], 'baseline': 0, 'players': 2, 'request': {'player': 0}}
        rows = []
        for i in range(56):
            rows.append({'env': i, 'sample': 4+i//2, 'actionIndex': i % 2,
                'truncated': False, 'value': 0.5, 'roles': ['neural', 'search_geo'],
                'initialBelief': {'kind': 'test'}, 'steps': 10, 'policyDecisions': {'neural': 10},
                'searchStats': {'truncated': 0}, 'diagnostic': {
                    'priorSearchStats': {'truncated': 0}, 'sampledWorldSha256': f'{4+i//2:064x}',
                    'terminal': [{'powered': 10, 'money': 20, 'cities': 11} for _ in range(2)]}})
        result = {'mode': 'reference_opponent_v1', 'options': [0, 1], 'samples': 60, 'begin': 4,
            'count': 28, 'usable': True, 'caps': 0, 'outer_caps': 0, 'nested_caps': 0,
            'rows': rows, 'seconds': 1.}
        return root, result

    def test_nonzero_offsets_exact_credit_and_world_pairing(self):
        root, result = self.fixture(); worlds = {}
        check = check_result(result, root, 'reference_opponent_v1', 4, worlds)
        self.assertEqual(check['mean_credits'], {'0': '1/2', '1': '1/2'})
        self.assertEqual(set(worlds), set(range(4, 32)))
        check_result(result, root, 'reference_opponent_v1', 4, worlds)
        changed = copy.deepcopy(result)
        changed['rows'][0]['diagnostic']['sampledWorldSha256'] = 'f' * 64
        with self.assertRaises(AssertionError):
            check_result(changed, root, 'reference_opponent_v1', 4, worlds)

    def test_reject_wrong_offsets_missing_rows_and_caps(self):
        root, original = self.fixture()
        changes = [lambda d: d.update(begin=0), lambda d: d['rows'].pop(),
            lambda d: d['rows'][0].update(value=1), lambda d: d.update(nested_caps=1),
            lambda d: d['rows'][0].update(sample=0), lambda d: d['rows'][1].update(actionIndex=0),
            lambda d: d['rows'][1].update(roles=['neural', 'neural'])]
        for change in changes:
            with self.subTest(change=change):
                changed = copy.deepcopy(original); change(changed)
                with self.assertRaises(AssertionError):
                    check_result(changed, root, 'reference_opponent_v1', 4, {})

    def test_parent_ties_and_strict_fixed_margin(self):
        self.assertEqual(choose({'0': Fraction(1, 2), '1': Fraction(1, 2)}, 1), '1')
        self.assertEqual(choose({'0': Fraction(1, 2), '1': Fraction(21, 40)}, 0), '0')
        self.assertEqual(choose({'0': Fraction(1, 2), '1': Fraction(22, 40)}, 0), '1')
        self.assertEqual(choose({'3': Fraction(1, 2), '1': Fraction(1), '2': Fraction(1)}, 3), '1')

    def test_selection_cannot_peek_at_evaluation_half(self):
        root = {'baseline': 0}
        audits = {f'{m}-{begin}': {'mean_credits': {'0': '1/2', '1': '1' if begin == 4 else '0'}}
            for m in ('neural_population', 'reference_opponent_v1') for begin in (4, 32)}
        rows = compare_halves(root, audits)
        for row in rows:
            if row['selection_begin'] == 4:
                self.assertEqual(row['action'], 1)
                self.assertEqual(row['selection_margin'], '1/2')
                self.assertEqual(set(row['heldout_margins'].values()), {'-1/2'})
            else:
                self.assertEqual(row['action'], 0)
                self.assertEqual(set(row['heldout_margins'].values()), {'0'})


if __name__ == '__main__': unittest.main()
