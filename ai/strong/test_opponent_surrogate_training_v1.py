"""Real-record tensor/metric checks and forward-only model checks; no gradients."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import torch
from strategic_collection import ROOT, read
from model_opponent_surrogate_v1 import OpponentSurrogate, from_checkpoint
from opponent_surrogate_training_v1 import compact, inputs, input_digest, validate_arrays, metrics, group_weights, load_bundle, SCHEMA

ACTUAL = ROOT/'ai/runs/opponent-surrogate-runtime-collected-v1/opponent-surrogate-runtime-v1-2p-0-1/artifacts/games'
spec = importlib.util.spec_from_file_location('surrogate_trainer_test', Path(__file__).with_name('train-opponent-surrogate-v1.py'))
trainer = importlib.util.module_from_spec(spec); spec.loader.exec_module(trainer)


def actual_rows():
    rows = []
    for folder in sorted(ACTUAL.glob('game-*')):
        q = read(folder/'contract.json')
        for line in (folder/'opponent-decisions.jsonl').read_text().splitlines():
            rows.append((json.loads(line), q))
    return rows


def packed_data():
    rows = [compact(r, q) for r, q in actual_rows()]
    return {k: np.asarray([r[k] for r in rows], dtype=dtype) for k, (dtype, _) in SCHEMA.items()}


class PublicInputsTests(unittest.TestCase):
    def test_all_real_hf_records_pack_without_changing_public_inputs_or_targets(self):
        original = actual_rows(); data = packed_data(); validate_arrays(data)
        self.assertEqual(len(original), 382)
        for i, (row, _) in enumerate(original):
            legal = data['legal_indices'][i][data['mask'][i]]
            self.assertEqual(legal[data['target'][i]], row['target'])
            np.testing.assert_array_equal(data['state'][i], np.asarray(row['observation']['state'], np.float32))
            np.testing.assert_array_equal(data['actions'][i][data['mask'][i]], np.asarray(row['observation']['actions'], np.float32)[legal])
        with self.assertRaisesRegex(AssertionError, '60'):
            group_weights(data)  # A two-player calibration is not a training corpus.

    def test_teacher_results_and_secrets_cannot_enter_tensor_inputs(self):
        row, q = actual_rows()[0]; before = inputs(row['observation'])
        changed = copy.deepcopy(row)
        changed['teacher'] = {'result': {'values': {'0': 999}}, 'options': {'seed': 'different'}}
        changed['request'] = {'state': {'seed': 'private', 'currentBid': 999}}
        changed['terminal_outcome'] = 'win'; changed['arena_opponent_identity'] = 'different'
        changed['observation']['teacher'] = 'different'; changed['observation']['prior'] = 'different'
        after = inputs(changed['observation'])
        self.assertEqual(input_digest(before), input_digest(after))
        for k in before: np.testing.assert_array_equal(before[k], after[k])

    def test_outside_shortlist_target_and_corrupt_candidates_are_rejected(self):
        row, q = next((r, q) for r, q in actual_rows() if len(r['observation']['actions']) > 6)
        bad = copy.deepcopy(row)
        bad['target'] = next(i for i, a in enumerate(bad['observation']['actions']) if not a[100])
        with self.assertRaises(AssertionError): compact(bad, q)
        bad = copy.deepcopy(row); bad['observation']['actions'][0][100] = .5
        with self.assertRaises(AssertionError): inputs(bad['observation'])
        bad = copy.deepcopy(row); bad['observation']['state'][0] = float('nan')
        with self.assertRaises(AssertionError): inputs(bad['observation'])


class MetricsTests(unittest.TestCase):
    def test_perfect_choices_have_zero_teacher_regret_and_shift_invariant_nll(self):
        data = packed_data(); logits = np.zeros(data['mask'].shape)
        logits[np.arange(len(logits)), data['target']] = 8
        a, b = metrics(logits, data), metrics(logits + 100, data)
        self.assertEqual(a, b)
        self.assertEqual(a['agreement'], 1)
        self.assertTrue(all(g['teacher_sample_regret'] == 0 for g in a['groups'].values()))
        self.assertGreater(a['macro_nll'], 0)

    def test_group_weighting_equalizes_uneven_group_counts_and_ignores_forced_rows(self):
        groups = np.repeat(np.arange(60), np.arange(1, 61))
        groups = np.append(groups, 0)
        mask = np.ones((len(groups), 6), bool); mask[-1, 1:] = False
        weights = group_weights({'group': groups, 'mask': mask})
        self.assertEqual(weights[-1], 0)
        np.testing.assert_allclose(np.bincount(groups, weights=weights), np.full(60, (len(groups)-1)/60), rtol=1e-7)


class ModelAndBoundaryTests(unittest.TestCase):
    def test_forward_masks_and_candidate_permutation_with_nonzero_random_weights(self):
        torch.manual_seed(19); model = OpponentSurrogate().eval()
        with torch.no_grad(): model.score[-1].weight.normal_(0, .02)
        data = packed_data(); sample = slice(0, 20)
        state = torch.from_numpy(data['state'][sample]); actions = torch.from_numpy(data['actions'][sample]); mask = torch.from_numpy(data['mask'][sample])
        before = {k: v.clone() for k, v in model.state_dict().items()}
        permutation = torch.tensor([5, 3, 1, 0, 4, 2])
        with torch.inference_mode():
            scores = model(state, actions, mask)
            permuted = model(state, actions[:, permutation], mask[:, permutation])
        torch.testing.assert_close(permuted, scores[:, permutation], rtol=0, atol=0)
        self.assertTrue((scores[~mask] == -1e9).all())
        self.assertTrue(mask[torch.arange(len(mask)), scores.argmax(1)].all())
        self.assertTrue(all(torch.equal(v, model.state_dict()[k]) for k, v in before.items()))
        self.assertEqual(sum(p.numel() for p in model.parameters()), 433217)

    def test_gradients_rejected_before_cuda_or_data_access_on_host(self):
        with patch.dict(os.environ, {}, clear=True), patch.object(trainer.torch.cuda, 'is_available') as gpu:
            with self.assertRaisesRegex(AssertionError, 'HF Jobs only'):
                trainer.main(Path('/missing-data'), Path('/must-not-create'), False)
            gpu.assert_not_called()

    def test_random_weight_export_matches_on_all_real_runtime_records(self):
        # Forward/export checks only: these random weights are never optimized,
        # uploaded or treated as a trained opponent model.
        torch.manual_seed(23); model = OpponentSurrogate().eval()
        with torch.no_grad(): model.score[-1].weight.normal_(0, .02)
        cp = {'architecture': 'opponent_surrogate_v1', 'model_args': {}, 'feature_revision': '4.3-strategic-correction',
              'state_dim': 1217, 'action_dim': 101, 'max_candidates': 6, 'state_dict': model.state_dict(),
              'random_weight_fixture': True, 'trained': False, 'qualification_eligible': False}
        spec = importlib.util.spec_from_file_location('surrogate_export_test', Path(__file__).with_name('export-opponent-surrogate-v1.py'))
        exporter = importlib.util.module_from_spec(spec); spec.loader.exec_module(exporter)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); torch.save(cp, root/'random.pt')
            exporter.export(root/'random.pt', root/'exported')
            proof = exporter.verify(root/'exported', {'runtime': packed_data()}, batch_size=37)
            self.assertEqual(proof['positions'], 382)
            self.assertEqual(proof['exact_choices'], 382)
            self.assertLess(proof['max_absolute_logit_error'], 1e-10)
            derivative = torch.load(root/'exported/inference64.pt', weights_only=True)
            self.assertTrue(all(torch.equal(v, derivative['state_dict'][k]) for k, v in cp['state_dict'].items()))
        bad = {**cp, 'feature_revision': 'incorrect'}
        with self.assertRaises(AssertionError): from_checkpoint(bad)

    def test_training_loader_rejects_test_inclusion_before_loading_arrays(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)
            (path/'data-check.json').write_text(json.dumps({'complete': True, 'collection_games': 2560,
                'prepared_games': 2240, 'split_games': {'train': 1920, 'validation': 320},
                'test_records_included': True}))
            with patch('opponent_surrogate_training_v1.np.load') as load:
                with self.assertRaises(AssertionError): load_bundle(path, {})
                load.assert_not_called()


if __name__ == '__main__': unittest.main()
