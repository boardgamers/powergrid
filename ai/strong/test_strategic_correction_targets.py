import unittest
import numpy as np
import torch
from strategic_correction_targets import targets, regression_loss


def fixture():
    rows = {}
    for mode in ['neural', 'neural_economic']:
        for batch in ['a', 'b']:
            x = [.5, -.5, .5, -.5]
            if mode == 'neural_economic':
                x = [-v for v in x]
            rows[mode, batch] = {'options': [7, 11, 2], 'model_proposal': 7,
                'mode': mode, 'batch': batch, 'usable': True, 'samples': 4,
                'rootId': 'root', 'public_root_sha256': 'same-public-input',
                'seed': 'strategic-teacher-public-v1-root-'+batch,
                'paired_advantages_over_proposal': {'7': [0]*4, '11': x, '2': [.25]*4}}
    return rows


class PairedTargets(unittest.TestCase):
    def test_common_world_covariance_is_preserved(self):
        t = targets(fixture())
        np.testing.assert_array_equal(t['target'], [0, 0, .25])
        np.testing.assert_array_equal(t['variance_of_mean'], [0, 0, 0])
        self.assertEqual(t['samples'], 8)

    def test_missing_batch_and_mismatched_worlds_rejected(self):
        rows = fixture()
        del rows['neural', 'b']
        with self.assertRaises(AssertionError): targets(rows)
        rows = fixture()
        rows['neural_economic', 'b']['seed'] = 'different-worlds'
        with self.assertRaises(AssertionError): targets(rows)

    def test_noisy_negative_evidence_kept_and_downweighted(self):
        rows = fixture()
        for row in rows.values():
            row['paired_advantages_over_proposal']['11'] = [1., -1., -1., -1.]
        t = targets(rows)
        self.assertEqual(t['target'][1], -.5)
        self.assertGreater(t['variance_of_mean'][1], 0)
        self.assertGreaterEqual(t['precision'][1], .25)
        self.assertLess(t['precision'][1], 1.)

    def test_loss_ignores_padding_and_global_score_offset(self):
        # This is evaluation of a loss, with no backward pass or optimizer step.
        target = torch.tensor([[0., .25, 999.]])
        precision = torch.ones_like(target)
        mask = torch.tensor([[True, True, False]])
        proposal = torch.tensor([0])
        for score in [torch.tensor([[0., .25, 0.]]), torch.tensor([[5., 5.25, 1234.]])]:
            self.assertEqual(regression_loss(score, target, precision, mask, proposal).item(), 0.)
        self.assertGreater(regression_loss(torch.zeros_like(target), target, precision, mask, proposal), 0)


if __name__ == '__main__':
    unittest.main()
