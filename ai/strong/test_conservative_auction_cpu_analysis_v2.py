"""Synthetic timing arithmetic only; never actual target performance evidence."""
from copy import deepcopy
import random
import unittest
from unittest.mock import patch

import analyze_conservative_auction_cpu_v2 as analysis


class TimingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = [{'name': f'{n}-{v}-{s}-{stage}', 'players': n, 'variant': v, 'sealed': s, 'stage': stage}
            for n in range(2, 7) for v in ('original', 'recharged') for s in (False, True) for stage in analysis.STAGES]
        cls.rows = [{'arm': arm, 'case': c['name'], 'first_request': i == 0,
            'round_trip_ms': 1000 if i == 0 else 100 if c['stage'] in ('choose', 'bid') else 5,
            'cold_process_plus_request_ms': 2000 if i == 0 else None}
            for arm in analysis.ARMS for i, c in enumerate(cls.cases)]

    def test_cold_is_separate_and_every_rule_count_point_is_retained(self):
        r = analysis.timing_summary(self.cases, self.rows)
        self.assertEqual(r['requests'], 300)
        for arm in analysis.ARMS:
            self.assertEqual(r['warm'][arm]['all']['count'], 99)
            self.assertEqual(r['warm'][arm]['search_eligible_stages']['count'], 39)
            self.assertEqual(r['warm'][arm]['search_eligible_stages']['median_ms'], 100)
            self.assertEqual(r['warm'][arm]['other_stages']['median_ms'], 5)
            self.assertEqual(r['cold'][arm]['process_plus_request_ms'], 2000)
            self.assertEqual(len(r['all_count_rule_stage_points'][arm]), 100)
        self.assertFalse(r['qualification_eligible'])

    def test_missing_duplicate_and_wrong_cell_coverage_rejected(self):
        for rows in (self.rows[:-1], [self.rows[0], *self.rows[:-1]]):
            with self.assertRaises(ValueError): analysis.timing_summary(self.cases, rows)
        cases = deepcopy(self.cases); cases[-1]['sealed'] = not cases[-1]['sealed']
        with self.assertRaises(ValueError): analysis.timing_summary(cases, self.rows)

    def test_invalid_costs_or_fake_warmup_rejected(self):
        for field, value in [('round_trip_ms', float('nan')), ('round_trip_ms', -1), ('round_trip_ms', True),
                             ('first_request', False), ('cold_process_plus_request_ms', 1)]:
            rows = deepcopy(self.rows); rows[0][field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ValueError): analysis.timing_summary(self.cases, rows)

    def test_receipt_arrival_order_does_not_affect_review(self):
        rows = deepcopy(self.rows); random.Random(5).shuffle(rows)
        self.assertEqual(analysis.timing_summary(self.cases, rows), analysis.timing_summary(self.cases, self.rows))

    def test_unfinished_cross_host_audit_cannot_produce_cost_claims(self):
        with patch.object(analysis, 'read', return_value={'complete': False}), patch.object(analysis, 'timing_summary') as summarize:
            with self.assertRaisesRegex(ValueError, 'independent cross-host'): analysis.review('/tmp/powergrid-unfinished-cost-review-never-written.json')
            summarize.assert_not_called()


if __name__ == '__main__': unittest.main()
