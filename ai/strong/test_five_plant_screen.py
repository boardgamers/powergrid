"""Reject invalid development evidence before trusting the ablation comparison."""
import copy
import unittest
from five_plant_screen import load_module, summarize

verify = load_module('screen_verifier_test', 'collect-population-screen.py').verify_report


class ScreenEvidenceTest(unittest.TestCase):
    def setUp(self):
        self.screen = {'players': 2, 'opponent': 'economic_capacity_v1', 'games': 8}
        self.evaluation = {'seed_template': 'ablation-test-{players}p', 'deal_offsets': [0],
                           'bootstrap_seed': 10031, 'bootstrap_replicates': 20000}
        self.pin = {'hashes': {'latest.onnx': 'model-hash'}}
        self.report = {'model_sha256': 'model-hash', 'model_feature_revision': '4.1-five-plants-zero-inputs',
            'encoder_feature_revision': '4.1-five-plants-zero-inputs', 'player_count': 2, 'games': 8,
            'paired_seats': True, 'candidate_search_samples': 0, 'candidate_geographic_search': False,
            'candidate_search_scope': 'all', 'candidate_search_model_proposal': True,
            'seed': 'ablation-test-2p', 'deal_offset': 0, 'search_max_steps': 2400,
            'opponent_sha256': None, 'opponent': 'economic_capacity_v1', 'truncated': 0, 'win_rate': .5,
            'results': [{'gameSeed': 'ablation-test-2p-0', 'variant': variant, 'sealed': sealed,
                         'seat': seat, 'roles': ['learner', 'economic_capacity_v1'] if seat == 0 else ['economic_capacity_v1', 'learner'],
                         'playerCount': 2, 'win': .5, 'value': [.5, .5], 'truncated': False, 'searchStats': {}}
                        for variant in ['original', 'recharged'] for sealed in [False, True] for seat in range(2)]}

    def check(self, report):
        return verify(report, self.screen, self.pin, self.evaluation, '4.1-five-plants-zero-inputs')

    def test_control_requires_its_own_encoder(self):
        self.check(self.report)
        wrong = copy.deepcopy(self.report)
        wrong['encoder_feature_revision'] = '4.1-five-plants'
        with self.assertRaises(ValueError):
            self.check(wrong)

    def test_reject_wrong_model_or_opponent(self):
        for key, value in [('model_sha256', 'different'), ('opponent', 'economic')]:
            wrong = copy.deepcopy(self.report)
            wrong[key] = value
            with self.assertRaises(ValueError):
                self.check(wrong)

    def test_reject_missing_seat_rule_or_wrong_deal(self):
        wrong = copy.deepcopy(self.report)
        wrong['results'][-1] = wrong['results'][0]
        with self.assertRaises(ValueError):
            self.check(wrong)
        wrong = copy.deepcopy(self.report)
        for row in wrong['results']:
            row['gameSeed'] = 'another-seed'
        with self.assertRaises(ValueError):
            self.check(wrong)

    def test_reject_game_and_search_caps(self):
        for game_cap in [True, False]:
            wrong = copy.deepcopy(self.report)
            if game_cap:
                wrong['results'][0]['truncated'] = True
            else:
                wrong['results'][0]['searchStats'] = {'search_geo': {'evaluations': 1, 'decisions': 1, 'truncated': 1}}
            with self.assertRaises(ValueError):
                self.check(wrong)

    def test_repeats_are_not_independent_deals(self):
        result = summarize(self.report['results'], self.evaluation)
        self.assertEqual(result['games'], 8)
        self.assertEqual(result['independent_deals'], 1)
        self.assertEqual(result['deal_bootstrap_95_interval'], [.5, .5])


if __name__ == '__main__':
    unittest.main()
