import copy
import unittest

from opponent_auction_policy_v1 import MODES, select_action, settings_check


def component(mode, a, b):
    rows = []
    for sample, values in enumerate(zip(a, b)):
        for action, value in enumerate(values):
            terminal = None if value is None else [
                {'powered': 10 if value else 0, 'money': 0, 'cities': 10},
                {'powered': 0 if value else 10, 'money': 0, 'cities': 10}]
            rows.append({'env': len(rows), 'sample': sample, 'actionIndex': action,
                         'value': value, 'truncated': value is None,
                         'diagnostic': {'sampledWorldSha256': str(sample), 'terminal': terminal}})
    caps = sum(r['truncated'] for r in rows)
    return {'mode': mode, 'options': [0, 1], 'samples': len(a), 'begin': 0, 'count': len(a),
            'rows': rows, 'nested_caps': 0, 'outer_caps': caps, 'caps': caps, 'usable': caps == 0}


def choose(components, threshold='0'):
    return select_action(components, [0, 1], 0, 0, modes=[c['mode'] for c in components], minimum_advantage=threshold)


class AuctionSelectionTests(unittest.TestCase):
    def test_ties_and_exact_threshold_keep_model(self):
        tied = component(MODES[0], [1, 0, 0, 0], [0, 1, 0, 0])
        self.assertEqual(choose([tied])['selected'], 0)
        edge = component(MODES[0], [0] * 8, [1] + [0] * 7)
        self.assertEqual(choose([edge], '1/8')['selected'], 0)
        self.assertEqual(choose([edge], '0')['selected'], 1)

    def test_advantage_in_one_population_does_not_hide_other_regression(self):
        a = component(MODES[0], [0] * 4, [1] * 4)
        b = component(MODES[1], [1, 0, 0, 0], [0] * 4)
        result = choose([a, b])
        self.assertEqual(result['pairedMeanMargins']['1'], '3/8')
        self.assertEqual(result['selected'], 0)

    def test_clear_consensus_can_override(self):
        a = component(MODES[0], [0] * 4, [1] * 4)
        b = component(MODES[1], [0] * 4, [1, 0, 0, 0])
        self.assertEqual(choose([a, b], '1/8')['selected'], 1)

    def test_one_cap_keeps_baseline_without_partial_means(self):
        a = component(MODES[0], [0] * 4, [1] * 4)
        b = component(MODES[1], [None, 0, 0, 0], [1] * 4)
        result = choose([a, b])
        self.assertEqual(result['selected'], 0)
        self.assertEqual(result['fallbackReason'], 'incomplete-rollouts')
        self.assertNotIn('meanCredits', result)

    def test_mismatched_worlds_and_missing_rows_are_rejected(self):
        a = component(MODES[0], [0] * 4, [1] * 4)
        b = component(MODES[1], [0] * 4, [1] * 4)
        bad = copy.deepcopy(b)
        bad['rows'][0]['diagnostic']['sampledWorldSha256'] = 'different'
        with self.assertRaises(ValueError): choose([a, bad])
        b['rows'].pop()
        with self.assertRaises(ValueError): choose([a, b])

    def test_credits_are_recomputed_from_terminal_and_ties_are_exact(self):
        a = component(MODES[0], [0] * 4, [1] * 4)
        for row in a['rows']:
            row['diagnostic']['terminal'] = [{'powered': 2, 'money': 0, 'cities': 2}] * 3
            row['value'] = 1 / 3
        result = choose([a])
        self.assertEqual(result['meanCredits'], {'0': '1/3', '1': '1/3'})
        a['rows'][0]['value'] = 0
        with self.assertRaises(ValueError): choose([a])

    def test_identity_and_threshold_settings_are_explicit(self):
        for modes, threshold in [([], '0'), (['reference_opponent_v1'], '0'),
                                 ([MODES[0], MODES[0]], '0'), (list(reversed(MODES)), '0'),
                                 (list(MODES), 0.125), (list(MODES), '2/16'), (list(MODES), '-1')]:
            with self.assertRaises((ValueError, ZeroDivisionError)):
                settings_check(modes, threshold)


if __name__ == '__main__':
    unittest.main()
