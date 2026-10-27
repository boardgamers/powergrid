"""Forced public actions bypass inference; strategic choices retain frozen outputs."""
import copy
import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import Mock

from opponent_surrogate_policy_v1 import SurrogatePolicy
from opponent_surrogate_training_v1 import inputs

ROOT = Path(__file__).resolve().parents[2]
ARTIFACT = ROOT/'ai/runs/conservative-auction-runtime-prepared-v1/source/artifact'
FIXTURE = json.loads(Path(__file__).with_name('fixtures').joinpath('conservative-auction-forced-prior-v1.json').read_text())


class ForcedActionsTests(unittest.TestCase):
    def setUp(self):
        self.forced = copy.deepcopy(FIXTURE['forcedObservation'])
        self.policy = SurrogatePolicy.__new__(SurrogatePolicy)
        self.policy.scores = Mock(side_effect=AssertionError('Forced action reached model'))

    def test_real_forced_bid_bypasses_model_and_does_not_mutate_input(self):
        self.assertEqual(self.forced['moves'], [{'name': 'Bid', 'data': 26}])
        before = copy.deepcopy(self.forced)
        self.assertEqual(self.policy.predict_batch([self.forced]), [0])
        self.policy.scores.assert_not_called()
        self.assertEqual(self.forced, before)

    def test_forced_pass_and_observation_without_moves_bypass_model(self):
        self.forced['moves'] = [{'name': 'Pass'}]
        without_moves = copy.deepcopy(self.forced); del without_moves['moves']
        self.assertEqual(self.policy.predict_batch([self.forced, without_moves]), [0, 0])
        self.policy.scores.assert_not_called()

    def test_empty_batch_and_malformed_forced_inputs(self):
        self.assertEqual(self.policy.predict_batch([]), [])
        variants = []
        for key, value in [('featureRevision', 'wrong'), ('playerMask', [0]*6), ('moves', []), ('actions', [])]:
            bad = copy.deepcopy(self.forced); bad[key] = value; variants.append(bad)
        for field, index, value in [('state', -1, 1), ('state', 10, float('nan'))]:
            bad = copy.deepcopy(self.forced); bad[field][index] = value; variants.append(bad)
        for index, value in [(100, 1), (10, float('inf'))]:
            bad = copy.deepcopy(self.forced); bad['actions'][0][index] = value; variants.append(bad)
        for bad in variants:
            with self.subTest(bad=variants.index(bad)), self.assertRaises(AssertionError):
                self.policy.predict_batch([bad])
        self.policy.scores.assert_not_called()

    def test_training_validator_still_rejects_non_strategic_forced_rows(self):
        with self.assertRaises(AssertionError): inputs(self.forced)

    def test_all_382_saved_strategic_predictions_match_original_with_forced_rows_interleaved(self):
        folder = ROOT/'ai/runs/opponent-surrogate-runtime-collected-v1/opponent-surrogate-runtime-v1-2p-0-1/artifacts/games'
        observations = [json.loads(line)['observation'] for path in sorted(folder.glob('game-*/opponent-decisions.jsonl'))
                        for line in path.read_text().splitlines()]
        self.assertEqual(len(observations), 382)
        member_path = ARTIFACT/'ai/strong/fixtures/surrogate-continuation-selected-members-v1/policy.json'
        policy = SurrogatePolicy(json.loads(member_path.read_text()), member_path.parent)
        spec = importlib.util.spec_from_file_location('original_surrogate_runtime', ARTIFACT/'ai/strong/opponent_surrogate_policy_v1.py')
        original = importlib.util.module_from_spec(spec); spec.loader.exec_module(original)
        expected = original.SurrogatePolicy.predict_batch(policy, observations)
        before = copy.deepcopy(observations)
        mixed = [item for observation in observations for item in (self.forced, observation)] + [self.forced]
        actual = policy.predict_batch(mixed)
        self.assertEqual(actual[1::2], expected)
        self.assertEqual(actual[::2], [0]*383)
        self.assertEqual(observations, before)


if __name__ == '__main__': unittest.main()
