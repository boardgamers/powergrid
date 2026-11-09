"""Offline preflight-proof regressions; synthetic outcomes are never study evidence."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

import torch
from data import atomic_json
import preflight_replica_stress_v1 as p
import replica_stress_study_v1 as study
import replica_stress_rollout_v1 as rollout
from test_replica_stress_rollout_v1 import outcome


def identity(panel, smoke, workers, artifact, reference_python):
    return dict(schema='offline-fixture-only', panel=panel, smoke=smoke,
                workers=workers, tasks=study.plan(panel, smoke))


def collect(tasks, *args, **kwargs):
    return [outcome(s) for s in tasks]


def fake_models():
    models = {}
    for index, name in enumerate(rollout.MODELS):
        model = torch.nn.Linear(2, 2)
        with torch.no_grad():
            model.weight.fill_(index); model.bias.fill_(index + 1)
        model.eval().requires_grad_(False)
        model._replica_stress_role = name
        models[name] = model
    return models


class Fingerprints(unittest.TestCase):
    def test_all_six_exact_states_reproduce(self):
        self.assertEqual(p.model_state(fake_models()), p.model_state(fake_models()))
        self.assertEqual(set(p.model_state(fake_models())), set(rollout.MODELS))

    def test_tensor_mutation_changes_fingerprint(self):
        models = fake_models(); before = p.model_state(models)
        with torch.no_grad(): models['replica2'].weight[0, 0] += 1
        self.assertNotEqual(before, p.model_state(models))

    def test_wrong_role_alias_missing_and_nonfinite_rejected(self):
        for change in ('role', 'alias', 'missing', 'nan'):
            with self.subTest(change=change):
                models = fake_models()
                if change == 'role': models['replica1']._replica_stress_role = 'expert24'
                if change == 'alias': models['replica1'] = models['expert24']
                if change == 'missing': del models['ppo0']
                if change == 'nan':
                    with torch.no_grad(): models['replica1'].weight[0, 0] = float('nan')
                with self.assertRaises(ValueError): p.model_state(models)

    def test_training_or_gradients_rejected(self):
        for change in ('training', 'gradients', 'submodule'):
            models = fake_models()
            if change == 'training': models['ppo1'].train()
            elif change == 'submodule': models['ppo1'].add_module('child', torch.nn.Dropout())
            else: models['ppo1'].requires_grad_(True)
            with self.assertRaises(ValueError): p.model_state(models)

    def test_strict_json_bool_not_int(self):
        with self.assertRaises(ValueError): p.exact({'enabled': True}, {'enabled': 1}, 'typed')
        with self.assertRaises(ValueError): p.exact(float('nan'), float('nan'), 'finite')


class Transactions(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.runner = p.bind(study.run, identity=identity, load_models=lambda **kw: {}, collect=collect)

    def make(self, panel='strong'):
        one, two = self.root / 'one', self.root / 'two'
        self.runner(one, panel, smoke=True)
        self.assertIsNone(self.runner(two, panel, smoke=True, stop_after_batches=1))
        first = (two / 'batch-000.json').read_bytes()
        (two / 'batch-001.json.tmp').write_text('{malformed')
        self.runner(two, panel, smoke=True)
        self.assertEqual((two / 'batch-000.json').read_bytes(), first)
        self.assertFalse((two / 'batch-001.json.tmp').exists())
        return one, two, identity(panel, True, 6, None, None)

    def test_complete_99_pairs_and_private_no_work_resume(self):
        one, two, expected = self.make()
        proof = p.compare_execution(one, two, expected)
        self.assertEqual(proof['matches'], 99)
        self.assertEqual(proof['publicChecks']['expertAtomicLegal'], 0)
        self.assertTrue(all(proof['controllers'][c] > 0 for c in ('replica1', 'replica2', 'ppo2', 'reference', 'expert24')))
        done = p.bind(p.completed_resume, study=SimpleNamespace(run=self.runner))
        done(two, 'strong', study.read(two / 'summary.json'))
        self.assertIsNot(self.runner.__globals__, study.run.__globals__)
        self.assertIs(study.run.__globals__['collect'], rollout.collect)

    def test_mixed_exercises_all_ten_controllers(self):
        one, two, expected = self.make('mixed')
        proof = p.compare_execution(one, two, expected)
        self.assertTrue(all(proof['controllers'][c] > 0 for c in rollout.CONTROLLERS))

    def test_exactly_four_timing_fields_may_differ(self):
        one, two, expected = self.make()
        path = two / 'batch-000.json'; record = study.read(path)
        for game in record['games']:
            for key in p.TIMINGS: game[key] += 1.25
        atomic_json(path, record)
        self.assertEqual(p.compare_execution(one, two, expected)['matches'], 99)

    def test_valid_but_changed_outcome_is_not_exact(self):
        one, two, expected = self.make()
        path = two / 'batch-000.json'; record = study.read(path)
        game = record['games'][0]
        game['allSeatCredit'] = [1, 0]; game['credit'] = 1
        atomic_json(path, record)
        with self.assertRaisesRegex(ValueError, 'Non-timing replay mismatch'):
            p.compare_execution(one, two, expected)

    def test_missing_or_extra_file_rejected(self):
        one, two, expected = self.make()
        path = two / 'batch-007.json'; saved = path.read_bytes(); path.unlink()
        with self.assertRaisesRegex(ValueError, 'inventory'): p.compare_execution(one, two, expected)
        path.write_bytes(saved)
        (two / 'uncommitted.tmp').write_text('{}')
        with self.assertRaisesRegex(ValueError, 'inventory'): p.compare_execution(one, two, expected)

    def test_missing_arm_and_forged_summary_rejected(self):
        one, two, expected = self.make()
        path = two / 'batch-000.json'; saved = path.read_bytes(); record = study.read(path)
        record['games'].pop(); atomic_json(path, record)
        with self.assertRaises(ValueError): p.compare_execution(one, two, expected)
        path.write_bytes(saved)
        summary = study.read(two / 'summary.json'); summary['games'] = 98
        atomic_json(two / 'summary.json', summary)
        with self.assertRaisesRegex(ValueError, 'summary drift'): p.compare_execution(one, two, expected)

    def test_production_or_changed_plan_rejected(self):
        one, two, expected = self.make()
        changed = copy.deepcopy(expected); changed['smoke'] = False
        with self.assertRaisesRegex(ValueError, 'Smoke identity'): p.compare_execution(one, two, changed)
        changed = copy.deepcopy(expected); changed['tasks'][0]['deal'] = 1
        with self.assertRaisesRegex(ValueError, 'smoke tasks'): p.compare_execution(one, two, changed)

    def test_snapshot_symlink_rejected(self):
        one, two, expected = self.make()
        path = two / 'batch-007.json'; path.unlink(); path.symlink_to(one / path.name)
        with self.assertRaisesRegex(ValueError, 'symlink'): p.compare_execution(one, two, expected)


class Boundaries(unittest.TestCase):
    def test_historical_ppo0_full_config_and_all_original_git_members(self):
        names = tuple(rollout.PROTOCOL['ppo0HistoricalTraining']['sourceFiles'])
        files = {n: hashlib.sha256(('old:' + n).encode()).hexdigest() for n in names}
        historical = dict(sourceGit='a' * 40, sourceFiles=files,
                          nonservingDifferences=['ppo.py', 'rollout.py'])
        current = dict(files)
        for name in ('ppo.py', 'rollout.py'): current[name] = 'b' * 64
        config = dict(schema='offline-test-only', sourceFiles=current, untouched='exact')
        value = dict(config=config, checkpointConfig=dict(config, sourceFiles=files),
                     historicalTrainingSource=historical)
        identities = {'panel': {'modelProvenance': {'ppo0': value}}}
        commands = []
        def git(args, **kwargs):
            commands.append(args)
            return ('old:' + args[-1].split(':ai/multimap/')[1]).encode()
        verify = p.bind(p.verify_historical_ppo0,
                        rollout=SimpleNamespace(_protocol=lambda: {'ppo0HistoricalTraining': historical}),
                        subprocess=SimpleNamespace(check_output=git))
        self.assertEqual(verify(identities), historical)
        self.assertEqual(len(commands), 11)
        changed = copy.deepcopy(identities)
        changed['panel']['modelProvenance']['ppo0']['checkpointConfig']['untouched'] = 'changed'
        with self.assertRaisesRegex(ValueError, 'complete checkpoint config'): verify(changed)
        changed = copy.deepcopy(identities)
        changed['panel']['modelProvenance']['ppo0']['config']['sourceFiles']['model.py'] = 'c' * 64
        with self.assertRaisesRegex(ValueError, 'source difference'): verify(changed)
        bad_git = p.bind(verify, subprocess=SimpleNamespace(check_output=lambda *a, **kw: b'wrong source'))
        with self.assertRaisesRegex(ValueError, 'original Git'): bad_git(identities)

    def test_old_source_normalizes_ppo_relative_names_and_checks_compiled_bytes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / 'ai/multimap/model.py'; source.parent.mkdir(parents=True); source.write_bytes(b'old code')
            engine = root / 'engine/dist/index.js'; engine.parent.mkdir(parents=True); engine.write_bytes(b'compiled')
            sha = hashlib.sha256(source.read_bytes()).hexdigest()
            engine_sha = hashlib.sha256(engine.read_bytes()).hexdigest()
            commands = []
            def git(args, **kwargs):
                commands.append(args)
                return source.read_bytes()
            verify = p.bind(p.verify_old_source, ROOT=root, subprocess=SimpleNamespace(check_output=git))
            identities = {'panel': {'frozenSources': {'model.py': sha}, 'modelProvenance': {
                'ppo0': {'config': {'sourceFiles': {'model.py': sha, 'engine/dist/index.js': engine_sha}}}}}}
            self.assertEqual(verify(identities), {'ai/multimap/model.py': sha})
            self.assertEqual(commands, [['git', 'show', p.BASE_GIT + ':ai/multimap/model.py']])
            engine.write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError, 'Compiled'): verify(identities)

    def test_new_dedicated_directory_only(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); parent = root / 'ai/runs'; parent.mkdir(parents=True)
            validate = p.bind(p.output_directory, ROOT=root)
            good = parent / 'multimap-replica-stress-test'
            self.assertEqual(validate(good), good)
            for bad in (parent / 'other', root / good.name):
                with self.assertRaises(ValueError): validate(bad)
            good.mkdir()
            with self.assertRaisesRegex(ValueError, 'exists'): validate(good)
            link = parent / 'multimap-replica-stress-link'; link.symlink_to(good, target_is_directory=True)
            with self.assertRaises(ValueError): validate(link)

    def test_retained_paths_are_verified_and_not_silently_replaced(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); pins = []
            for name in rollout.EXPERT_MODELS:
                data = name.encode(); run = 'multimap-fixture-' + name
                path = root / 'ai/runs' / run / 'audit/restored/expert/best.pt'
                path.parent.mkdir(parents=True); path.write_bytes(data)
                pins.append(dict(name=name, path=f'runs/{run}/expert/best.pt', sha256=hashlib.sha256(data).hexdigest()))
            fake = SimpleNamespace(model_pins=lambda: pins, EXPERT_MODELS=rollout.EXPERT_MODELS,
                                   CHECKPOINT_MAX_BYTES=16*1024**2)
            retained = p.bind(p.retained_checkpoints, ROOT=root, rollout=fake)
            paths = retained(); self.assertEqual(set(paths), set(rollout.EXPERT_MODELS))
            paths['replica1'].write_text('changed')
            with self.assertRaisesRegex(ValueError, 'missing or changed'): retained()


if __name__ == '__main__':
    unittest.main()
