"""Checks for selection bias and corrupt/missing audit evidence."""
import copy
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('discard_collector', Path(__file__).with_name('collect-public-discard-teacher.py'))
collect = importlib.util.module_from_spec(spec)
spec.loader.exec_module(collect)


class DiscardEvidenceTest(unittest.TestCase):
    def setUp(self):
        self.protocol = {'continuations': ['economic'], 'batches': ['a', 'b'], 'samples_per_batch': 4}
        self.root = {'rootIndex': 7, 'players': 2, 'episode': 3, 'variant': 'original',
                     'sealed': False, 'round': 10, 'model_proposal': 0, 'legal': [{}, {}]}
        identity = {k: self.root[k] for k in ['rootIndex', 'players', 'episode', 'variant', 'sealed', 'round']}
        self.rows = [{**identity, 'continuation': 'economic', 'batch': batch, 'original_proposal': 0,
            'options': [0, 1], 'samples': 4, 'evaluations': 8, 'truncated': 0,
            'sample_outcomes': {'0': [1 - winner] * 4, '1': [winner] * 4},
            'values': {'0': 1 - winner, '1': winner}, 'winner_set': [winner],
            'timing': {'seconds': 1, 'engine_seconds': 1, 'policy_seconds': 0, 'policy_decisions': 0}}
            for batch, winner in [('a', 1), ('b', 0)]]

    def test_independent_batch_exposes_winners_curse(self):
        self.assertEqual(collect.verify_rows(self.rows, [self.root], self.protocol), (16, 0))
        result = collect.summarize(self.rows, self.protocol)['per_continuation']['economic']
        self.assertEqual(result['mean_apparent_proposal_regret'], .5)
        self.assertEqual(result['mean_cross_batch_selected_gain'], -.5)
        self.assertEqual(result['both_batches_agree_to_change_proposal'], 0)

    def test_missing_duplicate_or_misidentified_rows_rejected(self):
        for rows in [self.rows[:1], self.rows + self.rows[:1]]:
            with self.assertRaises(AssertionError):
                collect.verify_rows(rows, [self.root], self.protocol)
        rows = copy.deepcopy(self.rows)
        rows[0]['players'] = 3
        with self.assertRaises(AssertionError):
            collect.verify_rows(rows, [self.root], self.protocol)

    def test_cap_cannot_silently_become_a_loss_or_accepted_target(self):
        rows = copy.deepcopy(self.rows)
        rows[0]['sample_outcomes']['1'][0] = None
        with self.assertRaises(AssertionError):
            collect.verify_rows(rows, [self.root], self.protocol)
        rows[0].update(truncated=1, values=None, winner_set=[])
        self.assertEqual(collect.verify_rows(rows, [self.root], self.protocol), (16, 1))
        result = collect.summarize(rows, self.protocol)['per_continuation']['economic']
        self.assertEqual(result['valid_paired_roots'], 0)
        self.assertEqual(result['invalid_paired_roots'], 1)
        self.assertIsNone(result['mean_cross_batch_selected_gain'])


if __name__ == '__main__':
    unittest.main()
