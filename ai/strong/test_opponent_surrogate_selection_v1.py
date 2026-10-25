"""Real public-record inference and synthetic selection/held-out boundaries, without gradients."""
import copy
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import torch
from strategic_collection import ROOT, read, write, digest
from model_opponent_surrogate_v1 import OpponentSurrogate, from_checkpoint
from opponent_surrogate_policy_v1 import SEEDS, SurrogatePolicy, make_policy, log_probabilities, ensemble_scores
from opponent_surrogate_training_v1 import SCHEMA
from test_opponent_surrogate_training_v1 import actual_rows, packed_data
from test_opponent_surrogate_training_verification_v1 import synthetic_data


def load(name):
    spec = importlib.util.spec_from_file_location(name.replace('-', '_'), Path(__file__).with_name(name+'.py'))
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module


selection = load('select-opponent-surrogate-v1')
heldout = load('evaluate-opponent-surrogate-heldout-v1')
exporter = load('export-opponent-surrogate-v1')
ORDER = read(selection.DESIGN)['candidate_order']


def synthetic_scores(data):
    n = len(data['target'])
    scores = {key: np.zeros((n, 6)) for key in ORDER}
    scores['seed-14101'][np.arange(n), data['target']] = 4.
    scores['ensemble-4'] = ensemble_scores([scores[f'seed-{s}'] for s in SEEDS], data['mask'])
    return scores


class InferenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(1)
        cls.temp = tempfile.TemporaryDirectory(); cls.root = Path(cls.temp.name)
        cls.pins = []; cls.models = []; cls.data = packed_data()
        cls.observations = [row['observation'] for row, _ in actual_rows()]
        for seed in SEEDS:
            with torch.random.fork_rng(devices=[]):
                torch.manual_seed(seed); model = OpponentSurrogate()
                with torch.no_grad(): model.score[-1].weight.normal_(0, .02)
            cp = {'architecture': 'opponent_surrogate_v1', 'model_args': {}, 'feature_revision': '4.3-strategic-correction',
                  'state_dim': 1217, 'action_dim': 101, 'max_candidates': 6, 'state_dict': model.state_dict(),
                  'random_untrained_fixture': True, 'qualification_eligible': False}
            folder = cls.root/str(seed); folder.mkdir(); torch.save(cp, folder/'random.pt')
            exporter.export(folder/'random.pt', folder/'derivative')
            cls.pins.append({'seed': seed, 'path': f'{seed}/derivative/inference64.onnx',
                             'sha256': digest(folder/'derivative/inference64.onnx'), 'checkpoint_sha256': digest(folder/'random.pt')})
            cls.models.append(from_checkpoint(torch.load(folder/'derivative/inference64.pt', weights_only=True)).eval())

    @classmethod
    def tearDownClass(cls): cls.temp.cleanup()

    def test_single_and_ensemble_match_checkpoint_choices_on_all_real_records(self):
        expected = []
        with torch.inference_mode():
            tensors = [torch.from_numpy(self.data[k]) for k in ('state', 'actions', 'mask')]
            expected = [model(*tensors).numpy() for model in self.models]
        for i, pin in enumerate(self.pins):
            policy = SurrogatePolicy(make_policy([pin]), self.root)
            actual = policy.scores(self.data, batch_size=37)
            np.testing.assert_allclose(actual, expected[i], atol=1e-10, rtol=1e-10)
            np.testing.assert_array_equal(actual.argmax(1), expected[i].argmax(1))
            legal = self.data['legal_indices'][np.arange(382), expected[i].argmax(1)]
            self.assertEqual(policy.predict_batch(self.observations), legal.tolist())
        policy = SurrogatePolicy(make_policy(self.pins), self.root)
        torch_probabilities = np.mean([torch.softmax(torch.from_numpy(s).masked_fill(~tensors[2], -torch.inf), dim=1).numpy() for s in expected], axis=0)
        actual = policy.scores(self.data, batch_size=19)
        np.testing.assert_allclose(np.where(self.data['mask'], np.exp(actual), 0), torch_probabilities, atol=1e-10, rtol=1e-10)
        legal = self.data['legal_indices'][np.arange(382), torch_probabilities.argmax(1)]
        self.assertEqual(policy.predict_batch(self.observations), legal.tolist())

    def test_hidden_metadata_and_teacher_values_cannot_change_inference(self):
        policy = SurrogatePolicy(make_policy(self.pins), self.root)
        before = self.observations[:20]; after = copy.deepcopy(before)
        for row in after:
            row.update(teacher={'seed': 'secret', 'values': {'0': 999}}, privateDeck=[999], hiddenBids=[999],
                       terminalOutcome='win', arenaOpponent='different')
        self.assertEqual(policy.predict_batch(before), policy.predict_batch(after))
        self.assertEqual(policy.predict_batch([]), [])

    def test_file_and_checkpoint_pins_and_shortlist_contract_fail_closed(self):
        bad = copy.deepcopy(self.pins[0]); bad['sha256'] = '0'*64
        with self.assertRaises(AssertionError): SurrogatePolicy(make_policy([bad]), self.root)
        bad = copy.deepcopy(self.pins[0]); bad['checkpoint_sha256'] = '0'*64
        with self.assertRaises(AssertionError): SurrogatePolicy(make_policy([bad]), self.root)
        bad = copy.deepcopy(self.pins[0]); bad['path'] = '../outside.onnx'
        with self.assertRaises(AssertionError): SurrogatePolicy(make_policy([bad]), self.root)
        policy = SurrogatePolicy(make_policy([]), self.root)
        bad = copy.deepcopy(self.observations[0]); bad['actions'][0][100] = .5
        with self.assertRaises(AssertionError): policy.predict_batch([bad])
        bad_data = {k: v.copy() for k, v in self.data.items()}; bad_data['mask'][0] = False
        with self.assertRaises(AssertionError): policy.scores(bad_data)

    def test_stable_probability_mixture_and_forced_choices(self):
        mask = np.array([[True, True, False], [True, False, False]])
        a = np.array([[10000., -10000., 1e100], [10000., 1e100, 1e100]])
        b = a.copy(); b[0, :2] = [-10000., 10000.]
        logp = ensemble_scores([a, a, b, b], mask)
        np.testing.assert_allclose(np.where(mask, np.exp(logp), 0), [[.5, .5, 0], [1, 0, 0]], atol=1e-14)
        self.assertEqual(logp.argmax(1).tolist(), [0, 0])
        self.assertTrue(np.isfinite(log_probabilities(a, mask)).all())


class SelectionTests(unittest.TestCase):
    def test_selection_uses_macro_validation_nll_and_prior_wins_exact_ties(self):
        data = synthetic_data(); scores = synthetic_scores(data)
        chosen, reports = selection.selection(scores, data, ORDER)
        self.assertEqual(chosen, 'seed-14101')
        self.assertLess(reports[chosen]['macro_nll'], reports['economic-prior']['macro_nll'])
        tied = {key: np.zeros_like(scores[key]) for key in ORDER}
        self.assertEqual(selection.selection(tied, data, ORDER)[0], 'economic-prior')
        tied['seed-14101'][np.arange(len(data['target'])), data['target']] = 1e-12
        tied['ensemble-4'] = ensemble_scores([tied[f'seed-{s}'] for s in SEEDS], data['mask'])
        self.assertEqual(selection.selection(tied, data, ORDER)[0], 'economic-prior')

    def test_absent_training_and_unfrozen_or_prior_selection_prevent_test_access(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch.object(selection, 'TRAINING_RESULT', root/'missing.json'), patch.object(selection, 'load_bundle') as loader:
                with self.assertRaisesRegex(AssertionError, 'all four|All four'): selection.main()
                loader.assert_not_called()
            with patch.object(heldout.selection, 'OUT', root/'missing'), patch.object(heldout.manager, 'verified_receipt') as raw:
                with self.assertRaisesRegex(AssertionError, 'Freeze validation'): heldout.prepare()
                raw.assert_not_called()
            folder = root/'prior'; folder.mkdir(); write(folder/'frozen.json', {'complete': True, 'learned_surrogate_selected': False})
            write(folder/'selection.json', {}); write(folder/'policy.json', {})
            with patch.object(heldout.selection, 'OUT', folder), patch.object(heldout.manager, 'verified_receipt') as raw:
                with self.assertRaisesRegex(AssertionError, 'No learned validation'): heldout.prepare()
                raw.assert_not_called()

    def test_resealed_frozen_policy_cannot_switch_seed_or_selected_candidate(self):
        data = synthetic_data(); scores = synthetic_scores(data)
        chosen, reports = selection.selection(scores, data, ORDER)
        result = {'seeds': {str(s): {'files': {'inference64.onnx': str(s)}, 'best_checkpoint_sha256': str(s)} for s in SEEDS}}
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp); training_result = folder/'training-result.json'; write(training_result, result)
            np.savez(folder/'validation-scores.npz', **scores)
            policy = make_policy([selection.member_pins(result)[0]]); write(folder/'policy.json', policy)
            report = {'selected': chosen, 'candidates': reports, 'policy_sha256': digest(folder/'policy.json'),
                      'design_sha256': digest(selection.DESIGN), 'training_result_sha256': digest(training_result),
                      'validation_scores_sha256': digest(folder/'validation-scores.npz'), 'code_hashes': selection.code_hashes(),
                      'test_labels_used': False}
            def seal():
                write(folder/'selection.json', report)
                write(folder/'frozen.json', {'complete': True, 'learned_surrogate_selected': True, 'selection': report['selected'],
                    'selection_sha256': digest(folder/'selection.json'), 'policy_sha256': report['policy_sha256'],
                    'design_sha256': digest(selection.DESIGN)})
            seal()
            with patch.object(selection, 'OUT', folder), patch.object(selection, 'TRAINING_RESULT', training_result), \
                 patch.object(selection, 'prerequisites', return_value=(result, read(selection.DESIGN), {'validation': data}, folder)):
                selection.verify_frozen()
                wrong = make_policy([selection.member_pins(result)[1]]); write(folder/'policy.json', wrong)
                report['policy_sha256'] = digest(folder/'policy.json'); seal()
                with self.assertRaises(AssertionError): selection.verify_frozen()
                report['selected'] = 'seed-14102'; seal()
                with self.assertRaises(AssertionError): selection.verify_frozen()


class HeldoutTests(unittest.TestCase):
    def test_complete_synthetic_test_bundle_rejects_wrong_deal_extra_split_and_changed_freeze(self):
        identities = [(n, r, deal, seat, episode, (seat+1) % n, phase)
                      for n, r, deal, seat, episode in sorted(heldout.expected_games()) for phase in range(3)]
        ids = np.array(identities, np.int64); nrows = len(ids)
        data = {k: np.zeros((nrows, *shape), dtype=dtype) for k, (dtype, shape) in SCHEMA.items()}
        data['identity'] = ids
        data['state'][:, -1] = 1; data['state'][:, :6] = np.arange(6)[None] < ids[:, 0, None]
        data['mask'][:] = True; data['actions'][:, :, 100] = 1
        data['legal_indices'][:] = np.arange(6)
        data['group'][:] = (ids[:, 0]-2)*12 + ids[:, 1]*3 + ids[:, 6]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); folder = root/'data'; (folder/'test').mkdir(parents=True)
            frozen = root/'frozen'; frozen.mkdir(); write(frozen/'frozen.json', {'synthetic_fixture': True})
            write(folder/'collection-index.json', {'synthetic_fixture': True}); write(folder/'intent.json', {'synthetic_fixture': True})
            for key, values in data.items(): np.save(folder/'test'/(key+'.npy'), values)
            np.save(folder/'seen-train-inputs.npy', np.zeros(nrows, bool))
            report = {'complete': True, 'games': 320, 'rows': nrows, 'model_selection_allowed': False,
                      'selection_frozen_sha256': digest(frozen/'frozen.json'),
                      'preparer_sha256': digest(heldout.__file__), 'collection_index_sha256': digest(folder/'collection-index.json'),
                      'test_rows_with_exact_training_inputs': 0}
            def seal():
                report['files'] = {str(p.relative_to(folder)): digest(p) for p in folder.rglob('*')
                                   if p.is_file() and p.name != 'data-check.json'}
                write(folder/'data-check.json', report)
            seal()
            with patch.object(heldout, 'DATA', folder), patch.object(heldout.selection, 'OUT', frozen), \
                 patch.object(heldout.selection, 'verify_frozen'), patch.object(heldout.manager, 'INDEX', folder/'collection-index.json'):
                loaded, _, _ = heldout.load_test(); self.assertEqual(len(loaded['target']), 960)
                bad = ids.copy(); bad[0, 2] = 27; np.save(folder/'test/identity.npy', bad); seal()
                with self.assertRaises(AssertionError): heldout.load_test()
                np.save(folder/'test/identity.npy', ids); seal()
                (folder/'train').mkdir(); np.save(folder/'train/target.npy', np.array([0])); seal()
                with self.assertRaises(AssertionError): heldout.load_test()
                (folder/'train/target.npy').unlink(); (folder/'train').rmdir(); seal()
                write(frozen/'frozen.json', {'synthetic_fixture': 'changed'})
                with patch.object(heldout.np, 'load') as arrays:
                    with self.assertRaises(AssertionError): heldout.load_test()
                    arrays.assert_not_called()

    def test_expected_test_games_cover_all_counts_rules_seats_and_only_reserved_test_deals(self):
        games = heldout.expected_games(); self.assertEqual(len(games), 320)
        self.assertEqual({r[2] for r in games}, {28, 29, 30, 31})
        for n in range(2, 7):
            self.assertEqual(len([g for g in games if g[0] == n]), 16*n)

    def test_overlap_diagnostic_does_not_drop_rows_from_primary_test_metrics(self):
        data = synthetic_data(); all_scores = synthetic_scores(data)
        scores = {'selected': all_scores['seed-14101'], 'economic-prior': all_scores['economic-prior']}
        seen = np.arange(len(data['target'])) % 2 == 0
        report = heldout.compare(data, scores, seen)
        self.assertEqual(report['primary_all_test_rows']['selected']['rows'], len(data['target']))
        self.assertEqual(report['diagnostic_inputs_absent_from_training']['selected']['rows'], int((~seen).sum()))
        self.assertLess(report['macro_nll_delta_from_prior'], 0)
        self.assertIsNone(heldout.compare(data, scores, np.ones_like(seen))['diagnostic_inputs_absent_from_training'])


if __name__ == '__main__': unittest.main()
