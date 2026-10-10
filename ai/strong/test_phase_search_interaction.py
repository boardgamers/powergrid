"""Check four-arm pairing, covariance and fractional terminal credits."""
import copy
import unittest

from phase_search_interaction import factorial


def games(credits):
    rows = []
    for deal, credit in enumerate(credits):
        for variant in ['original', 'recharged']:
            for sealed in [False, True]:
                for seat in range(2):
                    value = [1-credit, 1-credit]
                    value[seat] = credit
                    rows.append({'gameSeed': 'deal'+str(deal), 'playerCount': 2,
                                 'variant': variant, 'sealed': sealed, 'seat': seat,
                                 'roles': ['learner', 'economic'] if seat == 0 else ['economic', 'learner'],
                                 'value': value, 'win': credit, 'truncated': False})
    return rows


class FourArmContrasts(unittest.TestCase):
    def test_shared_arm_variation_cancels_exactly(self):
        arms = {'raw': games([0, .5, 1]), 'building': games([0, .5, 1]),
                'auction': games([1, .5, 0]), 'all': games([1, .5, 0])}
        result = factorial(arms, 2)
        for report in [result['overall'], *result['rules'].values()]:
            self.assertEqual(report['independent_deals'], 3)
            interaction = report['effects']['interaction']
            self.assertEqual(interaction['win_share_difference'], 0)
            self.assertEqual(interaction['paired_deal_bootstrap_95_interval'], [0, 0])

    def test_complementarity_and_interference_have_correct_signs(self):
        for single, combined, expected in [(0, 1, 1), (1, 0, -2)]:
            arms = {'raw': games([0, 0]), 'auction': games([single, single]),
                    'building': games([single, single]), 'all': games([combined, combined])}
            effects = factorial(arms, 2)['overall']['effects']
            self.assertEqual(effects['interaction']['win_share_difference'], expected)
            self.assertEqual(effects['interaction']['paired_deal_bootstrap_95_interval'], [expected, expected])
            self.assertEqual(effects['auction_with_building']['win_share_difference'] -
                             effects['auction_without_building']['win_share_difference'], expected)

    def test_cluster_intervals_do_not_treat_seats_as_independent(self):
        arms = {'raw': games([0, 0]), 'auction': games([0, 0]),
                'building': games([0, 1]), 'all': games([1, 0])}
        report = factorial(arms, 2)['overall']
        self.assertEqual(report['games_per_arm'], 16)
        self.assertEqual(report['independent_deals'], 2)
        self.assertEqual(report['effects']['interaction']['paired_deal_bootstrap_95_interval'], [-1, 1])
        for rows in arms.values():
            rows.reverse()
        self.assertEqual(factorial(arms, 2)['overall'], report)

    def test_rejects_incomplete_mismatched_or_invalid_games(self):
        base = {arm: games([0, .5]) for arm in ['raw', 'auction', 'building', 'all']}
        for fault in ['missing_arm', 'missing_seat', 'duplicate', 'truncated', 'different_deal', 'nan', 'wrong_credit']:
            arms = copy.deepcopy(base)
            if fault == 'missing_arm': del arms['raw']
            elif fault == 'missing_seat': arms['all'].pop()
            elif fault == 'duplicate': arms['all'].append(arms['all'][0])
            elif fault == 'truncated': arms['all'][0]['truncated'] = True
            elif fault == 'different_deal':
                for row in arms['all']: row['gameSeed'] += '-other'
            elif fault == 'nan': arms['all'][0]['value'][0] = float('nan')
            else: arms['all'][0]['win'] = 1
            with self.subTest(fault=fault), self.assertRaises(ValueError): factorial(arms, 2)


if __name__ == '__main__': unittest.main()
