import copy
import unittest

from resource_plan_consistency_v1 import PASS, finish_turn, transition


def buy(resource):
    return {'name': 'BuyResource', 'data': {'resource': resource}}


def row(decision, resources, *, stock=(0, 0, 0, 0), money=20, round_number=1):
    counts = [resources.count(r) for r in ('coal', 'oil', 'garbage', 'uranium')]
    actions = [buy(r) for r in resources] + [PASS]
    return {'decision': decision, 'round': round_number, 'move': actions[0], 'plan': {
        'counts': counts, 'actions': actions, 'seed': str(decision),
        'before': {'stock': list(stock), 'market': [10 - x for x in stock], 'money': money},
        'candidate_counts': [counts], 'means': {','.join(map(str, counts)): 0.5}}}


class PlanConsistencyTests(unittest.TestCase):
    def test_consistent_purchase_is_not_a_changed_plan(self):
        a, b = row(1, ['coal', 'coal']), row(2, ['coal'], stock=(1, 0, 0, 0), money=19)
        event = transition(a, b)
        self.assertFalse(event['count_change'])
        self.assertFalse(event['next_move_change'])
        self.assertEqual(event['selected_minus_remainder_credit'], 0)

    def test_order_change_does_not_count_as_bundle_change(self):
        a = row(1, ['coal', 'coal', 'oil'])
        b = row(2, ['oil', 'coal'], stock=(1, 0, 0, 0), money=19)
        event = transition(a, b)
        self.assertFalse(event['count_change'])
        self.assertTrue(event['next_move_change'])
        self.assertTrue(event['order_only_change'])

    def test_early_pass_missing_candidate_is_not_zero_gap(self):
        a, b = row(1, ['coal', 'coal']), row(2, [], stock=(1, 0, 0, 0), money=19)
        event = transition(a, b)
        self.assertTrue(event['early_pass'])
        self.assertFalse(event['remainder_available'])
        self.assertIsNone(event['selected_minus_remainder_credit'])

    def test_invalid_adjacency_or_inventory_is_rejected(self):
        a, b = row(1, ['coal', 'coal']), row(2, ['coal'], stock=(1, 0, 0, 0), money=19)
        for key, value in [('round', 2), ('decision', 3)]:
            modified = copy.deepcopy(b)
            modified[key] = value
            with self.assertRaises(AssertionError):
                transition(a, modified)
        b['plan']['before']['market'][0] -= 1
        with self.assertRaises(AssertionError):
            transition(a, b)

    def test_forced_pass_closes_turn_and_counts_shortfall(self):
        a = row(1, ['coal', 'coal'])
        forced = {'decision': 2, 'round': 1, 'move': PASS, 'plan': None}
        turn = finish_turn([a, forced])
        self.assertEqual(turn['category'], 'shortfall')
        self.assertEqual(turn['executed_counts'], [1, 0, 0, 0])
        self.assertTrue(turn['forced_final_pass'])

    def test_complete_turn_categories_and_invalid_pass(self):
        for initial, moves, expected in [(['coal'], ['coal'], 'exact'),
                                         (['coal'], ['coal', 'coal'], 'excess'),
                                         (['coal', 'coal'], ['coal', 'oil'], 'mixed')]:
            rows = [row(1, initial)]
            for i, resource in enumerate(moves[1:], 2):
                rows.append({'decision': i, 'round': 1, 'move': buy(resource), 'plan': None})
            rows.append({'decision': len(moves) + 1, 'round': 1, 'move': PASS, 'plan': None})
            self.assertEqual(finish_turn(rows)['category'], expected)
        with self.assertRaises(AssertionError):
            finish_turn([row(1, ['coal'])])


if __name__ == '__main__':
    unittest.main()
