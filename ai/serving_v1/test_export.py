"""Bounded offline engineering tests; no games, study replays, or training.

See requirements-export.txt to install pinned ONNX dependencies in /tmp only.
Tests use the ONNX package's standard-op ReferenceEvaluator, NOT Python ORT.
The actual Node production runtime is tested separately against offline outputs.
Private checkpoint cases skip if files/dependencies/pinned runtime are absent;
no tests download anything. Actual exports are created only in temporary dirs.
"""
import contextlib
import copy
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

try:
    from . import export_onnx as e
    from . import worker as w
    from .test_worker import CHECKPOINTS, observation
except ImportError:
    import export_onnx as e
    import worker as w
    from test_worker import CHECKPOINTS, observation

HAS_DEPS = all(importlib.util.find_spec(name) is not None for name in ('torch', 'onnx', 'numpy'))


class PortableExportTests(unittest.TestCase):
    def test_contract_is_all_ten_inputs_and_both_outputs(self):
        self.assertEqual(set(e.INPUT_NAMES), {'global', 'players', 'nodes', 'relations', 'actions',
                                            'actionCity', 'prior', 'nodeMask', 'playerMask', 'actionMask'})
        self.assertEqual(e.OUTPUT_NAMES, ('logits', 'value'))
        self.assertEqual(e.CONTRACT['actionCity'], (7, (1, 'A')))
        self.assertEqual(e.CONTRACT['relations'], (1, (1, 4, 'N', 'N')))
        self.assertNotIn('global', e.DYNAMIC_AXES)
        self.assertNotIn('value', e.DYNAMIC_AXES)
        self.assertTrue(all(0 not in axes for axes in e.DYNAMIC_AXES.values()))
        self.assertEqual(w.validate_observation(e.sample_observation()), 5)

    def test_exclusive_bundle_never_replaces_or_adds_to_existing_directory(self):
        artifacts = {'replica1.onnx': b'one', 'replica2.onnx': b'two', 'export-manifest.json': b'{}\n'}
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'new/onnx'
            e.write_bundle(output, artifacts)
            self.assertEqual({p.name: p.read_bytes() for p in output.iterdir()}, artifacts)
            for same_or_different in (artifacts, dict(artifacts, **{'replica1.onnx': b'changed'})):
                with self.assertRaises(FileExistsError):
                    e.write_bundle(output, same_or_different)
                self.assertEqual({p.name: p.read_bytes() for p in output.iterdir()}, artifacts)
            empty = Path(directory) / 'empty'
            empty.mkdir()
            with self.assertRaises(FileExistsError):
                e.write_bundle(empty, artifacts)
            self.assertEqual(list(empty.iterdir()), [])

    def test_paths_reject_symlinks_and_traversal(self):
        artifacts = {'replica1.onnx': b'one', 'replica2.onnx': b'two', 'export-manifest.json': b'{}\n'}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'actual').mkdir()
            (root / 'link').symlink_to(root / 'actual', target_is_directory=True)
            for output in (root / 'link/onnx', root / 'link', root / 'actual/../unsafe'):
                with self.subTest(path=output), self.assertRaises((ValueError, OSError)):
                    e.write_bundle(output, artifacts)
            self.assertEqual(list((root / 'actual').iterdir()), [])
            with self.assertRaises(ValueError):
                e.write_bundle(root / 'bad-keys', {'../checkpoint.pt': b'replacement'})
            self.assertFalse((root / 'bad-keys').exists())

    def test_fixture_contract_has_public_observations_and_unique_ids_only(self):
        good = [{'id': 'fixture-1', 'observation': observation()}]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'fixtures.json'
            path.write_bytes(e.json_bytes(good))
            self.assertEqual(e.read_fixtures(path), good)
            cases = [[], {}, good * 2, [{'id': '', 'observation': observation()}],
                     [{'id': 'x', 'observation': observation(), 'labels': [1]}],
                     [{'id': 'x', 'observation': dict(observation(), value=0)}]]
            for value in cases:
                path.write_bytes(e.json_bytes(value))
                with self.assertRaises(ValueError):
                    e.read_fixtures(path)

    def test_direct_reference_rejects_non_normalized_or_invalid_fixtures_before_inference(self):
        good = dict(id='fixture-1', observation=observation())
        cases = [None, {}, [], (good,), [good] * 2, [good] * 257,
                 [dict(good, id='')], [dict(good, id='x' * 257)], [dict(good, id=True)],
                 [dict(good, labels=[1])], [dict(good, rawG={})], [dict(good, seed=1)],
                 [dict(good, map='Germany')], [dict(good, observation=dict(observation(), targets=[1]))]]
        for value in cases:
            with self.subTest(value_type=type(value).__name__), \
                    patch.object(e, 'verify_manifest_identity', side_effect=AssertionError('must not load/infer')):
                with self.assertRaises(ValueError):
                    e.reference_results({}, value)

    def test_fixture_file_binding_hashes_the_exact_single_read(self):
        good = [dict(id='fixture-1', observation=observation())]
        raw = b' \n' + e.json_bytes(good) + b' \n'
        with patch.object(w, 'safe_read', return_value=raw) as read:
            fixtures, digest = e._read_fixture_input('fixtures.json')
        read.assert_called_once_with('fixtures.json', e.MAX_FIXTURE_BYTES)
        self.assertEqual(fixtures, good)
        self.assertEqual(digest, w.sha256(raw))
        self.assertNotEqual(digest, w.sha256(w.canonical(good)))

    def test_js_fixture_envelope_accepts_only_public_metadata(self):
        fixture = dict(id='engine-fixture', map='Germany', players=2, variant='original',
                       fastBid=False, kind='nomination', observation=observation())
        payload = dict(schema='pg-serving-engineering-fixtures-v1', namespace='pg-serving-prototype-v1',
                       fixtures=[fixture])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'fixtures.json'
            path.write_bytes(e.json_bytes(payload))
            normalized = e.read_fixtures(path)
            self.assertEqual(normalized, [dict(id=fixture['id'], observation=fixture['observation'])])
            cases = [dict(payload, schema='wrong'), dict(payload, namespace='old-study'),
                     dict(payload, labels=[1]), dict(payload, fixtures=[fixture, fixture])]
            for key, value in (('map', None), ('players', True), ('players', 3), ('variant', 'other'),
                               ('fastBid', 0), ('kind', 'hidden'), ('rawG', {}), ('seed', 1), ('labels', [1])):
                cases.append(dict(payload, fixtures=[dict(fixture, **{key: value})]))
            for invalid in cases:
                path.write_bytes(e.json_bytes(invalid))
                with self.assertRaises(ValueError):
                    e.read_fixtures(path)

    def test_cli_requires_both_explicit_roles_and_output_or_reference(self):
        for argv in ([], ['--replica1-checkpoint', 'one', '--output', 'out'],
                     ['--replica2-checkpoint', 'two', '--output', 'out'],
                     ['--replica1-checkpoint', 'one', '--replica2-checkpoint', 'two'],
                     ['--replica1-checkpoint', 'one', '--replica2-checkpoint', 'two',
                      '--reference-fixtures', 'fixtures']):
            with patch.object(e, 'load_policies', side_effect=AssertionError('must not load')), \
                    contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as error:
                    e.main(argv)
                self.assertEqual(error.exception.code, 2)


@unittest.skipUnless(HAS_DEPS, 'Offline Torch/ONNX dependencies unavailable; no download attempted')
class ActualExportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import numpy as np
        import torch
        import onnx
        from onnx.reference import ReferenceEvaluator
        if ('.'.join(map(str, sys.version_info[:3])) != w.RUNTIMES['python'] or
                torch.__version__ != w.RUNTIMES['torch'] or np.__version__ != w.RUNTIMES['numpy']):
            raise unittest.SkipTest('Pinned frozen CPU runtime unavailable')
        if not all(path.is_file() for path in CHECKPOINTS.values()):
            raise unittest.SkipTest('Private pinned checkpoints absent; no download attempted')
        e.export_dependencies()
        cls.np, cls.torch, cls.onnx, cls.ReferenceEvaluator = np, torch, onnx, ReferenceEvaluator
        cls.source_before = {path: w.safe_read(path, 793281) for path in CHECKPOINTS.values()}
        cls.policies = e.load_policies(CHECKPOINTS['replica1'], CHECKPOINTS['replica2'])
        cls.before = {role: {key: value.clone() for key, value in p.model.state_dict().items()}
                      for role, p in cls.policies.items()}
        cls.artifacts = e.bundle(cls.policies)
        cls.models = {role: e.validate_onnx(cls.artifacts[f'{role}.onnx']) for role in e.ROLES}

    @classmethod
    def tearDownClass(cls):
        for path, raw in cls.source_before.items():
            if w.safe_read(path, 793281) != raw:
                raise AssertionError('Source checkpoint was modified')
        for role, policy in cls.policies.items():
            e.check_policy(policy)
            for key, value in policy.model.state_dict().items():
                if not cls.torch.equal(cls.before[role][key], value):
                    raise AssertionError('Frozen in-memory parameter was modified')

    def test_both_explicit_identities_export_manifest_and_model_contract(self):
        manifest = json.loads(self.artifacts['export-manifest.json'])
        self.assertEqual(manifest['schema'], 'pg-replica-onnx-export-v1')
        self.assertEqual(manifest['sourceManifestSha256'], w.sha256(w.MANIFEST.read_bytes()))
        self.assertEqual(manifest['exporter']['opset'], 17)
        self.assertFalse(manifest['exporter']['dynamo'])
        self.assertFalse(manifest['exporter']['externalData'])
        self.assertEqual(set(manifest['replicas']), set(e.ROLES))
        for role in e.ROLES:
            raw = self.artifacts[f'{role}.onnx']
            self.assertEqual(manifest['replicas'][role], dict(file=f'{role}.onnx', bytes=len(raw),
                             sha256=w.sha256(raw), checkpointSha256=w.REPLICAS[role]['sha256']))
            model = self.models[role]
            self.assertEqual([v.name for v in model.graph.input], list(e.INPUT_NAMES))
            self.assertEqual([v.name for v in model.graph.output], list(e.OUTPUT_NAMES))
            self.onnx.checker.check_model(model, full_check=True)
            # Whole ExpertPolicy, not the bare network: residual Tanh and value Sigmoid.
            self.assertIn('Tanh', {node.op_type for node in model.graph.node})
            self.assertIn('Sigmoid', {node.op_type for node in model.graph.node})
        self.assertNotEqual(manifest['replicas']['replica1']['sha256'],
                            manifest['replicas']['replica2']['sha256'])
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'onnx'
            e.write_bundle(output, self.artifacts)
            self.assertEqual({p.name: p.read_bytes() for p in output.iterdir()}, self.artifacts)

    def test_actual_dynamic_dimensions_float32_logits_value_and_first_argmax(self):
        for role, policy in self.policies.items():
            runner = self.ReferenceEvaluator(self.models[role])
            # ONNX 1.17 ReferenceEvaluator GatherElements uses np.choose, which
            # cannot handle N=64 with NumPy 2.2.6. N=63 still tests independent
            # dynamic axes and max P/A. N=64 must also be checked with Node ORT,
            # not by patching ONNX, model code, or this evaluator's operators.
            for players, nodes, actions in ((2, 1, 2), (4, 8, 37), (6, 63, 4096)):
                with self.subTest(role=role, players=players, nodes=nodes, actions=actions):
                    obs = observation(players, nodes, actions, seed=nodes + actions)
                    inputs = e.tensor_inputs(policy, obs)
                    with self.torch.inference_mode():
                        logits, value = policy.model(inputs)
                    actual_logits, actual_value = runner.run(list(e.OUTPUT_NAMES),
                                                              {k: v.numpy() for k, v in inputs.items()})
                    self.assertEqual(actual_logits.shape, (1, actions))
                    self.assertEqual(actual_value.shape, (1,))
                    self.assertEqual(actual_logits.dtype, self.np.float32)
                    self.assertEqual(actual_value.dtype, self.np.float32)
                    self.np.testing.assert_allclose(actual_logits, logits.numpy(), rtol=2e-5, atol=2e-5)
                    self.np.testing.assert_allclose(actual_value, value.numpy(), rtol=2e-5, atol=2e-5)
                    self.assertEqual(int(actual_logits[0].argmax()), policy.choose(obs))

    def test_first_argmax_ties_and_repeat_export_are_deterministic(self):
        obs = observation(actions=5)
        obs['actions'] = [obs['actions'][0][:] for _ in range(5)]
        obs['actionCity'] = [-1] * 5
        obs['prior'] = [0.0] * 5
        for role, policy in self.policies.items():
            inputs = e.tensor_inputs(policy, obs)
            logits, _ = self.ReferenceEvaluator(self.models[role]).run(
                list(e.OUTPUT_NAMES), {k: v.numpy() for k, v in inputs.items()})
            self.assertEqual(logits[0].tolist(), [float(logits[0, 0])] * 5)
            self.assertEqual(int(logits[0].argmax()), 0)
            self.assertEqual(policy.choose(obs), 0)
            self.assertEqual(e.export_policy(policy), self.artifacts[f'{role}.onnx'])

    def test_masks_prior_features_and_residual_preserved(self):
        for role, policy in self.policies.items():
            inputs = e.tensor_inputs(policy, observation(4, 8, 37))
            inputs['nodeMask'][0, -2:] = False
            inputs['playerMask'][0, -1:] = False
            inputs['actionMask'][0, -3:] = False
            runner = self.ReferenceEvaluator(self.models[role])
            for prior in ([0.0] * 37, [0.0] + [-20.0] * 36):
                inputs['prior'][0] = self.torch.tensor(prior, dtype=self.torch.float32)
                with self.torch.inference_mode():
                    expected = policy.model(inputs)
                actual = runner.run(list(e.OUTPUT_NAMES), {k: v.numpy() for k, v in inputs.items()})
                for got, want in zip(actual, expected):
                    self.np.testing.assert_allclose(got, want.numpy(), rtol=2e-5, atol=2e-5)
                self.assertTrue(self.np.all(actual[0][0, -3:] == -1e9))
                residual = actual[0][0, :-3] - inputs['prior'][0, :-3].numpy()
                self.assertTrue(self.np.all(self.np.abs(residual) <= 16.0))

    def test_checker_rejects_external_data_custom_ops_and_contract_changes(self):
        external = copy.deepcopy(self.models['replica1'])
        tensor = external.graph.initializer[0]
        tensor.data_location = self.onnx.TensorProto.EXTERNAL
        tensor.external_data.add(key='location', value='/must/not/read')
        custom = copy.deepcopy(self.models['replica1'])
        custom.graph.node[0].domain = 'untrusted.custom'
        renamed = copy.deepcopy(self.models['replica1'])
        renamed.graph.input[0].name = 'wrong-name'
        fixed = copy.deepcopy(self.models['replica1'])
        fixed.graph.input[1].type.tensor_type.shape.dim[1].dim_value = 2
        for model in (external, custom, renamed, fixed):
            with self.assertRaises(ValueError):
                e.validate_onnx(model.SerializeToString())

    def test_swapped_roles_rejected_before_export_or_output(self):
        with self.assertRaises(ValueError):
            e.load_policies(CHECKPOINTS['replica2'], CHECKPOINTS['replica1'])
        with self.assertRaises(ValueError):
            e.bundle(dict(replica1=self.policies['replica2'], replica2=self.policies['replica1']))

    def test_changed_loaded_policies_rejected_before_export_and_reference_without_repair(self):
        cases = {
            'finite-weight': lambda m: next(m.parameters()).add_(0.125),
            'bound': lambda m: setattr(m, 'bound', 8),
            'width': lambda m: setattr(m, 'width', 32),
            'network-width': lambda m: setattr(m.network, 'width', 32),
        }
        for name, mutate in cases.items():
            with self.subTest(mutation=name):
                policy = copy.copy(self.policies['replica1'])
                policy.model = copy.deepcopy(policy.model)  # Fault-injection copy only.
                policy.assert_unchanged()
                original = policy._loaded_fingerprint
                with self.torch.no_grad():
                    mutate(policy.model)
                changed = policy._model_fingerprint()
                policies = dict(self.policies, replica1=policy)
                fixtures = [dict(id='same-input', observation=observation())]
                with patch.object(self.torch.onnx, 'export', side_effect=AssertionError('must not export')), \
                        patch.object(e, 'tensor_inputs', side_effect=AssertionError('must not infer')):
                    for operation in (lambda: e.export_policy(policy),
                                      lambda: e.reference_results(policies, fixtures)):
                        with self.assertRaises(ValueError):
                            operation()
                        self.assertEqual(policy._model_fingerprint(), changed)
                        self.assertEqual(policy._loaded_fingerprint, original)
                self.policies['replica1'].assert_unchanged()

    def test_export_and_reference_check_after_execution_without_repair(self):
        for operation in ('export', 'reference'):
            with self.subTest(operation=operation):
                policy = copy.copy(self.policies['replica1'])
                policy.model = copy.deepcopy(policy.model)
                if operation == 'export':
                    def changed_export(*args, **kwargs):
                        policy.model.bound = 8

                    with patch.object(self.torch.onnx, 'export', side_effect=changed_export), \
                            self.assertRaises(ValueError):
                        e.export_policy(policy)
                else:
                    original_forward = policy.model.forward

                    def changed_forward(inputs):
                        result = original_forward(inputs)
                        policy.model.bound = 8
                        return result

                    with patch.object(policy.model, 'forward', side_effect=changed_forward), \
                            self.assertRaises(ValueError):
                        e.reference_results(dict(self.policies, replica1=policy),
                                            [dict(id='same-input', observation=observation())])
                self.assertEqual(policy.model.bound, 8)
                with self.assertRaises(ValueError):
                    policy.assert_unchanged()
                self.policies['replica1'].assert_unchanged()

    def test_reference_json_and_reference_only_cli(self):
        fixtures = [{'id': 'public-shape-only', 'observation': observation()}]
        fixtures_before = copy.deepcopy(fixtures)
        policies_before = {role: p._model_fingerprint() for role, p in self.policies.items()}
        reference = e.reference_results(self.policies, fixtures)
        self.assertEqual(fixtures, fixtures_before)
        for role, policy in self.policies.items():
            policy.assert_unchanged()
            self.assertEqual(policy._model_fingerprint(), policies_before[role])
        self.assertEqual(reference['fixturesInputSha256'], w.sha256(w.canonical(fixtures)))
        self.assertEqual(reference['fixturesInputHashMode'], 'python-canonical-normalized-json-v1')
        changed = copy.deepcopy(fixtures)
        changed[0]['observation']['global'][0] += 0.125  # Same ID/count, different input.
        other = e.reference_results(self.policies, changed)
        self.assertNotEqual(other['fixturesInputSha256'], reference['fixturesInputSha256'])
        self.assertEqual(reference['schema'], 'pg-replica-pytorch-reference-v1')
        self.assertEqual(reference['sourceManifestSha256'], w.sha256(w.MANIFEST.read_bytes()))
        item = reference['fixtures'][0]
        self.assertEqual(item['id'], fixtures[0]['id'])
        self.assertEqual(item['actionCount'], 5)
        for role, policy in self.policies.items():
            result = item['replicas'][role]
            self.assertEqual(set(result), {'logits', 'value', 'index'})
            self.assertEqual(len(result['logits']), 5)
            self.assertEqual(result['index'], policy.choose(fixtures[0]['observation']))
            self.assertEqual(result['index'], result['logits'].index(max(result['logits'])))
        with tempfile.TemporaryDirectory() as directory:
            source, output = Path(directory) / 'fixtures.json', Path(directory) / 'reference.json'
            source.write_bytes(e.json_bytes(fixtures))
            args = [sys.executable, '-B', str(Path(e.__file__)),
                    '--replica1-checkpoint', str(CHECKPOINTS['replica1']),
                    '--replica2-checkpoint', str(CHECKPOINTS['replica2']),
                    '--reference-fixtures', str(source), '--reference-output', str(output)]
            # Remove /tmp ONNX deps: reference-only mode must not import ONNX.
            env = dict(os.environ)
            env.pop('PYTHONPATH', None)
            run = subprocess.run(args, capture_output=True, timeout=60, env=env)
            self.assertEqual(run.returncode, 0, run.stderr.decode())
            expected_cli = dict(reference, fixturesInputSha256=w.sha256(source.read_bytes()),
                                fixturesInputHashMode='raw-file-bytes')
            self.assertEqual(json.loads(output.read_bytes()), expected_cli)
            self.assertNotEqual(expected_cli['fixturesInputSha256'], reference['fixturesInputSha256'])
            before = output.read_bytes()
            run = subprocess.run(args, capture_output=True, timeout=60, env=env)
            self.assertEqual(run.returncode, 1)
            self.assertEqual(output.read_bytes(), before)
            # Versioned JS fixture envelope has the same direct model result;
            # metadata is not fed to the expert or copied into reference rows.
            wrapped = dict(schema='pg-serving-engineering-fixtures-v1', namespace='pg-serving-prototype-v1',
                           fixtures=[dict(fixtures[0], map='Germany', players=2, variant='recharged',
                                          fastBid=True, kind='Building')])
            source.write_bytes(e.json_bytes(wrapped))
            wrapped_output = Path(directory) / 'wrapped-reference.json'
            args[-1] = str(wrapped_output)
            run = subprocess.run(args, capture_output=True, timeout=60, env=env)
            self.assertEqual(run.returncode, 0, run.stderr.decode())
            expected_wrapped = dict(reference, fixturesInputSha256=w.sha256(source.read_bytes()),
                                    fixturesInputHashMode='raw-file-bytes')
            self.assertEqual(json.loads(wrapped_output.read_bytes()), expected_wrapped)
            self.assertNotEqual(expected_wrapped['fixturesInputSha256'], expected_cli['fixturesInputSha256'])


if __name__ == '__main__':
    unittest.main()
