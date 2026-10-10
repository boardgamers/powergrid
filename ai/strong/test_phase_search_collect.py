"""Reject altered real HF phase-probe artifacts before admitting full jobs."""
import copy
import unittest

from phase_search_ablation import ROOT, PROTOCOL, read, verify, exact_control


class RealProbeContracts(unittest.TestCase):
    def setUp(self):
        self.protocol = read(PROTOCOL)
        base = ROOT/'ai/runs/phase-search-ablation-smoke-verified-v1'
        self.auction = read(base/'auction-search_geo-2p/search.json')
        self.control = read(base/'all-search_geo-2p/search.json')
        self.baseline = read(base/'all-search_geo-2p/control.json')

    def test_verified_probe_and_replay_control(self):
        result = verify(self.auction, self.protocol, 'search_geo-2p', 'auction', True)
        self.assertEqual(result['games'], 8)
        self.assertGreater(result['phase_routing']['auction']['searched'], 0)
        self.assertEqual(result['phase_routing']['building']['searched'], 0)
        self.assertTrue(exact_control(self.control, self.baseline)['all_raw_game_rows_match'])

    def test_wrong_phase_execution_and_arena_contracts_are_rejected(self):
        for fault in ['phase', 'disabled', 'decision_count', 'opportunities', 'model', 'seed', 'missing', 'horizon']:
            report = copy.deepcopy(self.auction); row = report['results'][0]
            if fault == 'phase': report['candidate_search_phases'] = 'building'
            elif fault == 'disabled': row['phaseRouting']['building']['searched'] = 1
            elif fault == 'decision_count': row['searchStats']['learner']['decisions'] += 1
            elif fault == 'opportunities': row['phaseRouting']['auction']['opportunities'] += 1
            elif fault == 'model': report['model_sha256'] = '0'*64
            elif fault == 'seed': row['gameSeed'] += '-wrong'
            elif fault == 'missing': report['results'].pop()
            else: report['search_max_steps'] = 1200
            with self.subTest(fault=fault), self.assertRaises((AssertionError, ValueError)):
                verify(report, self.protocol, 'search_geo-2p', 'auction', True)

    def test_control_requires_exact_game_rows_not_just_the_same_winner(self):
        report = copy.deepcopy(self.control)
        report['results'][0]['final']['players'][0]['money'] += 1
        with self.assertRaisesRegex(AssertionError, 'Instrumentation changed'):
            exact_control(report, self.baseline)


if __name__ == '__main__': unittest.main()
