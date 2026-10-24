"""Grid coverage and paired-statistic contracts, no job submission."""
from copy import deepcopy
import importlib.util
import unittest

from strategic_collection import ROOT, read
from policy_iteration_development import PROTOCOL


def load(name, file):
    spec = importlib.util.spec_from_file_location(name, ROOT/'ai/strong'/file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


grid = load('tested_grid', 'manage-policy-iteration-development-grid.py')
comparison = load('tested_comparison', 'compare-policy-iteration-development.py')


class GridContracts(unittest.TestCase):
    def test_prescribed_grid_covers_every_deal_once_for_every_arm(self):
        protocol = read(PROTOCOL)
        for arm in protocol['models']:
            rows = grid.cells(protocol, arm)
            self.assertEqual(len(rows), 108)
            self.assertEqual(sum(row['games'] for row in rows), 6720)
            for cell in protocol['screens']:
                selected = [r for r in rows if r['players'] == cell['players'] and r['opponent'] == cell['opponent']]
                self.assertEqual([i for r in selected for i in range(r['start'], r['end'])], list(range(16)))
        bad = deepcopy(protocol)
        bad['screens'].append(bad['screens'][0])
        with self.assertRaises(AssertionError):
            grid.cells(bad, 'parent')

    def test_paired_comparison_keeps_adverse_rules_and_deal_units(self):
        protocol = read(PROTOCOL)
        left, right = [], []
        for deal in range(16):
            for seat in range(2):
                for variant in ['original', 'recharged']:
                    for sealed in [False, True]:
                        row = {'gameSeed': 'synthetic-'+str(deal), 'seat': seat, 'variant': variant,
                               'sealed': sealed, 'truncated': False}
                        left.append({**row, 'win': float(sealed)})
                        right.append({**row, 'win': float(not sealed)})
        result = comparison.contrast(left, right, protocol)
        self.assertEqual(result['overall']['independent_deals'], 16)
        self.assertEqual(result['overall']['games_per_model'], 128)
        self.assertEqual(result['overall']['win_share_difference'], 0.)
        self.assertEqual(result['by_rules']['original/open']['paired_deal_bootstrap_95_interval'], [-1., -1.])
        self.assertEqual(result['by_rules']['recharged/sealed']['paired_deal_bootstrap_95_interval'], [1., 1.])
        for bad in [right[:-1], right+[right[0]], [{**right[0], 'truncated': True}]+right[1:]]:
            with self.assertRaises(ValueError):
                comparison.contrast(left, bad, protocol)


if __name__ == '__main__':
    unittest.main()
