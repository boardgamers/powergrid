"""Adversarial saved-artifact checks with synthetic fixtures; no training or jobs."""
import copy
import importlib.util
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import torch
from strategic_collection import ROOT, read, write, digest
from model_opponent_surrogate_v1 import OpponentSurrogate
from opponent_surrogate_training_v1 import metrics
import opponent_surrogate_training_verification_v1 as audit


def load(name):
    spec = importlib.util.spec_from_file_location(name.replace('-', '_'), Path(__file__).with_name(name+'.py'))
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module


collector = load('collect-opponent-surrogate-training-v1')
exporter = load('export-opponent-surrogate-v1')
DESIGN = read(ROOT/'ai/strong/opponent-surrogate-training-design-v1.json')


def synthetic_data():
    rng = np.random.default_rng(101)
    group = np.repeat(np.arange(60), 1 + np.arange(60) % 3)
    group = np.append(group, 0); n = len(group)
    mask = np.zeros((n, 6), bool); mask[:, :3] = True; mask[-1, 1:] = False
    target = np.arange(n) % 3; target[-1] = 0
    values = np.zeros((n, 6)); values[np.arange(n), target] = 1
    return {'state': rng.normal(0, .1, (n, 1217)).astype(np.float32),
            'actions': rng.normal(0, .1, (n, 6, 101)).astype(np.float32),
            'mask': mask, 'target': target, 'teacher_values': values, 'group': group}


def history_fixture(data, seed):
    count = int((data['train']['mask'].sum(1) > 1).sum())
    updates = math.ceil(count / DESIGN['batch_size'])
    baseline = {s: metrics(2 * d['actions'][:, :, 74], d) for s, d in data.items()}
    history = []
    for epoch in range(DESIGN['epochs'] + 1):
        row = {'epoch': epoch, 'updates': epoch * updates, 'seconds': float(epoch + 1),
               'training_loss': 1. if epoch else None, 'validation': copy.deepcopy(baseline['validation'])}
        if epoch in (0, DESIGN['epochs']): row['train'] = copy.deepcopy(baseline['train'])
        history.append(row)
    report = {'seed': seed, 'best_epoch': 0, 'best_validation_macro_nll': baseline['validation']['macro_nll'],
              'updates': updates * DESIGN['epochs'], 'seconds': 82., 'gpu': 'synthetic GPU fixture',
              'gpu_resident_inputs': False, 'max_allocated_bytes': 1, 'torch_version': 'synthetic fixture',
              'input_bytes': sum(d[k].nbytes for d in data.values() for k in ('state', 'actions', 'mask', 'target')),
              'training_location': 'HF Jobs', 'tf32': False,
              'train_rows': len(data['train']['target']), 'nonforced_train_rows': count,
              'validation_rows': len(data['validation']['target']), 'test_labels_used': False,
              'qualification_eligible': False}
    return history, report


def checkpoint(seed, source, pin, epoch=0):
    with torch.random.fork_rng(devices=[]):
        torch.manual_seed(seed); model = OpponentSurrogate(**DESIGN['model_args'])
    return {'architecture': 'opponent_surrogate_v1', 'model_args': DESIGN['model_args'],
            'state_dict': model.state_dict(), 'feature_revision': DESIGN['feature_revision'],
            'state_dim': 1217, 'action_dim': 101, 'max_candidates': 6, 'seed': seed, 'epoch': epoch,
            'updates': epoch, 'design_sha256': source['design_sha256'],
            'data_check_sha256': pin['data_check_sha256'], 'collection_index_sha256': pin['collection_index_sha256'],
            'training_location': 'HF Jobs', 'training_device': 'cuda', 'test_labels_used': False,
            'qualification_eligible': False,
            'purpose': 'Opponent behaviour inside simulated continuations; not a qualified focal-player policy.'}


class HistoryTests(unittest.TestCase):
    def setUp(self):
        self.data = {s: synthetic_data() for s in ('train', 'validation')}
        self.history, self.report = history_fixture(self.data, 14101)

    def test_group_counts_weighted_metrics_and_corrupt_summaries(self):
        result = self.history[0]['validation']
        audit.validate_metrics(result, self.data['validation'])
        for key in ('macro_nll', 'nll', 'agreement', 'macro_agreement', 'forced_rows'):
            bad = copy.deepcopy(result); bad[key] += .1
            with self.subTest(key=key), self.assertRaises(AssertionError):
                audit.validate_metrics(bad, self.data['validation'])
        for key, value in [('rows', 999), ('top3', -1), ('nll', float('nan')), ('teacher_sample_regret', -1)]:
            bad = copy.deepcopy(result); bad['groups']['0'][key] = value
            with self.subTest(key=key), self.assertRaises(AssertionError):
                audit.validate_metrics(bad, self.data['validation'])

    def test_all_epochs_updates_and_earliest_validation_tie_are_required(self):
        self.assertEqual(audit.verify_history(self.history, self.report, DESIGN, 14101, self.data), (0, 1))
        mutations = [lambda h, r: h.pop(1), lambda h, r: h[9].update(updates=8),
                     lambda h, r: h[9].update(seconds=0.), lambda h, r: h[1].update(training_loss=None),
                     lambda h, r: h[-1].pop('train'), lambda h, r: r.update(best_epoch=1),
                     lambda h, r: r.update(test_labels_used=True), lambda h, r: r.update(training_location='local'),
                     lambda h, r: r.update(input_bytes=1)]
        for i, mutate in enumerate(mutations):
            h, r = copy.deepcopy(self.history), copy.deepcopy(self.report); mutate(h, r)
            with self.subTest(mutation=i), self.assertRaises(AssertionError):
                audit.verify_history(h, r, DESIGN, 14101, self.data)

    def test_checkpoint_provenance_precision_and_nonfinite_weights_are_rejected(self):
        source = {'design_sha256': 'design'}; pin = {'data_check_sha256': 'data', 'collection_index_sha256': 'index'}
        cp = checkpoint(14101, source, pin)
        audit.verify_checkpoint(cp, DESIGN, source, pin, 14101, 0, 0)
        mutations = [lambda c: c.update(seed=14102), lambda c: c.update(data_check_sha256='other'),
                     lambda c: c.update(runtime_calibration_only=True), lambda c: c.update(inference_only=True),
                     lambda c: c['state_dict'].pop('context.0.bias'),
                     lambda c: c['state_dict'].update({'context.0.bias': c['state_dict']['context.0.bias'].double()}),
                     lambda c: c['state_dict']['context.0.bias'].fill_(float('nan'))]
        for i, mutate in enumerate(mutations):
            bad = copy.deepcopy(cp); mutate(bad)
            with self.subTest(mutation=i), self.assertRaises((AssertionError, RuntimeError)):
                audit.verify_checkpoint(bad, DESIGN, source, pin, 14101, 0, 0)


class ArtifactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # These temporary synthetic artifacts do not claim an HF execution.
        # load_bundle is explicitly mocked only in this test; no gradients run.
        torch.set_num_threads(1)
        cls.temp = tempfile.TemporaryDirectory(); cls.root = Path(cls.temp.name)
        cls.out = cls.root/'artifacts'; cls.out.mkdir()
        cls.data_path = cls.root/'data'; cls.data_path.mkdir()
        write(cls.data_path/'data-check.json', {'synthetic_fixture': True})
        cls.data = {s: synthetic_data() for s in ('train', 'validation')}
        cls.pin = {'design_sha256': digest(ROOT/'ai/strong/opponent-surrogate-training-design-v1.json'),
                   'data_check_sha256': digest(cls.data_path/'data-check.json'), 'collection_index_sha256': 'synthetic-index'}
        cls.source = {**cls.pin, 'revision': 'synthetic-revision', 'sha256': 'synthetic-source'}
        job = {'stage': 'complete', 'seeds': DESIGN['seeds'], 'runs': {}, 'exports': {},
               'source_revision': cls.source['revision'], 'source_sha256': cls.source['sha256'],
               'design_sha256': cls.pin['design_sha256'], 'data_check_sha256': cls.pin['data_check_sha256'],
               'training_location': 'HF Jobs', 'test_labels_used': False, 'qualification_eligible': False}
        for seed in DESIGN['seeds']:
            directory = cls.out/str(seed); directory.mkdir()
            best = checkpoint(seed, cls.source, cls.pin); latest = checkpoint(seed, cls.source, cls.pin, DESIGN['epochs'])
            latest['state_dict']['score.2.weight'].fill_(.001)  # Manual fixture perturbation, not optimization.
            torch.save(best, directory/'best.pt'); torch.save(latest, directory/'latest.pt')
            parameters = list(OpponentSurrogate(**DESIGN['model_args']).parameters())
            optimizer = {'param_groups': [{'params': list(range(len(parameters))), 'lr': DESIGN['learning_rate'] * .05,
                                          'weight_decay': DESIGN['weight_decay']}],
                         'state': {i: {'step': torch.tensor(float(DESIGN['epochs'])),
                                       'exp_avg': torch.zeros_like(p), 'exp_avg_sq': torch.zeros_like(p)}
                                   for i, p in enumerate(parameters)}}
            torch.save(optimizer, directory/'optimizer.pt')
            history, report = history_fixture(cls.data, seed)
            report['best_checkpoint_sha256'] = digest(directory/'best.pt')
            write(directory/'metrics.json', history); write(directory/'training.json', report)
            exporter.export(directory/'best.pt', directory/'derivative')
            parity = exporter.verify(directory/'derivative', cls.data)
            job['runs'][str(seed)] = report
            job['exports'][str(seed)] = {k: parity[k] for k in ('complete', 'positions', 'exact_choices', 'max_absolute_logit_error')}
            job['exports'][str(seed)]['parity_sha256'] = digest(directory/'derivative/parity.json')
        write(cls.out/'job.json', job); cls.reseal()

    @classmethod
    def tearDownClass(cls): cls.temp.cleanup()

    @classmethod
    def reseal(cls):
        write(cls.out/'manifest.json', {str(p.relative_to(cls.out)): digest(p) for p in sorted(cls.out.rglob('*'))
                                        if p.is_file() and p.name != 'manifest.json'})

    def run_audit(self):
        with patch.object(audit, 'load_bundle', return_value=(self.data, {'collection_index_sha256': self.pin['collection_index_sha256']})):
            return audit.verify(self.out, self.source, self.pin, self.data_path, self.root/'checks')

    def test_full_four_seed_forward_audit_keeps_original_artifacts_unchanged(self):
        before = read(self.out/'manifest.json'); result = self.run_audit()
        self.assertEqual(set(result['seeds']), set(map(str, DESIGN['seeds'])))
        self.assertTrue(result['verified']); self.assertFalse(result['qualification_eligible'])
        self.assertFalse(result['gradients_during_verification']); self.assertFalse(result['test_labels_used'])
        self.assertTrue(all(digest(self.out/name) == sha for name, sha in before.items()))
        for row in result['seeds'].values():
            self.assertEqual(row['best_epoch'], 0)
            self.assertAlmostEqual(row['validation_macro_nll_change_from_prior'], 0., places=10)

    def test_resealed_wrong_optimizer_step_and_missing_seed_are_rejected(self):
        path = self.out/'14101/optimizer.pt'; original = path.read_bytes()
        try:
            bad = torch.load(path, weights_only=True); bad['state'][0]['step'] -= 1
            torch.save(bad, path); self.reseal()
            with self.assertRaises(AssertionError): self.run_audit()
        finally: path.write_bytes(original); self.reseal()
        path = self.out/'manifest.json'; original = path.read_bytes()
        try:
            bad = read(path); bad.pop('14104/latest.pt'); write(path, bad)
            with self.assertRaises(AssertionError): self.run_audit()
        finally: path.write_bytes(original)

    def test_resealed_export_behaviour_claim_is_independently_recomputed(self):
        parity_path = self.out/'14101/derivative/parity.json'; job_path = self.out/'job.json'
        originals = {p: p.read_bytes() for p in (parity_path, job_path)}
        try:
            bad = read(parity_path); bad['exported_behaviour_metrics']['validation']['macro_nll'] += .1
            write(parity_path, bad); job = read(job_path)
            job['exports']['14101']['parity_sha256'] = digest(parity_path); write(job_path, job); self.reseal()
            with self.assertRaises(AssertionError): self.run_audit()
        finally:
            for p, content in originals.items(): p.write_bytes(content)
            self.reseal()


class CollectionTests(unittest.TestCase):
    def test_missing_real_source_prevents_hf_calls(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(collector.launcher, 'SOURCE', Path(tmp)/'missing'), \
             patch.object(collector, 'HfApi') as api:
            with self.assertRaisesRegex(AssertionError, 'must be packaged'): collector.main()
            api.assert_not_called()

    def test_interrupted_index_write_recovers_original_verified_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); result_path = root/'result.json'; original_write = collector.write
            result = {'verified': True, 'checked_at': 'original-time', 'job_id': 'original-handle'}
            def interrupted_write(path, value):
                if path == result_path.with_suffix('.tmp.json'): raise OSError('simulated interruption')
                original_write(path, value)
            with patch.object(collector, 'OUT', root), patch.object(collector, 'RESULT', result_path):
                with patch.object(collector, 'write', side_effect=interrupted_write):
                    with self.assertRaisesRegex(OSError, 'simulated interruption'): collector.save_result(result)
                self.assertEqual(read(root/'verified.json'), result); self.assertFalse(result_path.exists())
                collector.save_result(read(root/'verified.json'))
                self.assertEqual(read(result_path), result)
                with self.assertRaises(AssertionError): collector.save_result({**result, 'checked_at': 'changed'})


if __name__ == '__main__': unittest.main()
