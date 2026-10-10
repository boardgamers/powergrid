"""Counterexamples for the diagnostic verifier and discovery/confirmation split."""
import hashlib
import importlib.util
import itertools
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('summary', Path(__file__).with_name('summarize-neural-continuations.py'))
summary = importlib.util.module_from_spec(spec)
spec.loader.exec_module(summary)


class SummaryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.neural = self.root / 'neural'
        self.control = self.root / 'control'
        self.neural.mkdir()
        self.control.mkdir()
        neural, control = [], []
        cells = itertools.product(['original', 'recharged'], [False, True], ['ChoosePowerPlant', 'Bid', 'Build'])
        for index, (variant, sealed, action) in enumerate(cells):
            for batch in ['a', 'b']:
                winner = 0 if batch == 'a' else 1
                result = self.result(winner, 48)
                result['winnerSet'] = [winner]
                row = {'fixtureIndex': index, 'cell': [2, variant, sealed, action], 'batch': batch,
                       'samples': 48, 'continuation': 'neural', 'result': result, 'root_model_proposal': 2}
                neural.append(row)
                for policy in ['mixed', 'economic', 'heuristic']:
                    control.append({**row, 'continuation': policy, 'samples': 384, 'result': self.result(1, 384)})
        np = self.neural / 'results-2p.jsonl'
        cp = self.control / 'results-2p.jsonl'
        for p, rows in [(np, neural), (cp, control)]:
            p.write_text(''.join(json.dumps(r)+'\n' for r in rows))
        self.manifest_path = np.with_suffix('.manifest.json')
        self.manifest = {'fixture_sha256': summary.FIXTURE_SHA, 'model_sha256': summary.MODEL_SHA,
                         'output_sha256': hashlib.sha256(np.read_bytes()).hexdigest(),
                         'players': 2, 'positions': 12, 'searches': 24, 'samples': 48, 'max_steps': 2400,
                         'truncated': 0, 'evaluations': 24*2*48, 'engine_seconds': 1, 'policy_seconds': 1}
        self.manifest_path.write_text(json.dumps(self.manifest))
        (self.control / 'manifest-2p.json').write_text(json.dumps({
            'fixture_sha256': summary.FIXTURE_SHA, 'output_sha256': hashlib.sha256(cp.read_bytes()).hexdigest(),
            'truncated': 0}))

    @staticmethod
    def result(winner, samples):
        outcomes = {str(i): [int(i == winner)] * samples for i in range(2)}
        return {'sampleOutcomes': outcomes, 'values': {k: sum(v) for k, v in outcomes.items()},
                'evaluations': 2*samples, 'truncated': 0}

    def test_confirmation_does_not_reselect_winner(self):
        result = summary.summarize(self.neural, self.control, [2])
        g = result['groups']['overall']
        self.assertEqual(g['disjoint_neural_winner_sets'], 12)
        self.assertEqual(g['root_proposal_in_shortlist'], 0)
        self.assertEqual(g['confirmation']['neural']['mean_gap'], -1)
        self.assertTrue(all(r['neural_a_choice'] == 0 and r['mixed_a_choice'] == 1 for r in result['positions']))

    def test_capped_or_wrong_model_reports_fail(self):
        for field, value in [('truncated', 1), ('model_sha256', 'wrong')]:
            self.manifest_path.write_text(json.dumps({**self.manifest, field: value}))
            with self.assertRaises(AssertionError):
                summary.summarize(self.neural, self.control, [2])


if __name__ == '__main__':
    unittest.main()
