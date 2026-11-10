"""Offline engineering tests: synthetic public tensors, never games or replays.

    ai/.venv/bin/python -B -m unittest discover -s ai/serving_v1 -p test_worker.py -v

Standard-library cases require no model files or Torch. Tensor tests skip only
when Torch is unavailable; private checkpoint cases also skip when absent.
"""
import copy
import importlib.util
import io
import json
import marshal
import os
from pathlib import Path
import random
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

try:
    from . import worker as w
except ImportError:
    import worker as w


CHECKPOINTS = {
    f'replica{i}': w.ROOT / f'ai/runs/multimap-expert-replicas-20261109-v1-continuation-r{i}/audit/restored/expert/best.pt'
    for i in (1, 2)
}
HAS_TORCH = importlib.util.find_spec('torch') is not None


def observation(players=2, nodes=3, actions=5, seed=19):
    rng = random.Random(seed)

    def vector(n):
        return [rng.uniform(-0.8, 0.8) for _ in range(n)]

    return dict(schema='multimap-graph-v1', **{'global': vector(273)},
                players=[vector(80) for _ in range(players)], nodes=[vector(36) for _ in range(nodes)],
                relations=[[[float(i == j) for j in range(nodes)] for i in range(nodes)] for _ in range(4)],
                actions=[vector(34) for _ in range(actions)],
                actionCity=[i % (nodes + 1) - 1 for i in range(actions)],
                prior=[0.0] + [-min(i, 20) for i in range(1, actions)])


def request(obs=None, request_id='a' * 64, replica='replica1'):
    return dict(schema='pg-replica-serving-request-v1', requestId=request_id, replica=replica,
                observation=observation() if obs is None else obs)


class FakePolicy:
    replica = 'replica1'
    checkpoint_sha256 = w.REPLICAS['replica1']['sha256']
    manifest_sha256 = 'b' * 64
    ready = w.ReplicaPolicy.ready

    def __init__(self, index=0):
        self.index = index
        self.calls = 0

    def choose(self, obs):
        self.calls += 1
        return self.index


class ObservationTests(unittest.TestCase):
    def test_valid_and_limits(self):
        for p, n, a in [(2, 1, 2), (6, 64, 4096)]:
            self.assertEqual(w.validate_observation(observation(p, n, a)), a)
        obs = observation()
        obs['global'][0] = w.FLOAT32_MAX
        self.assertEqual(w.validate_observation(obs), 5)

    def test_no_private_or_unknown_fields(self):
        for field in ('targets', 'value', 'labels', 'game', 'actionMask', 'hidden', '__proto__'):
            with self.subTest(field=field):
                obs = observation()
                obs[field] = 0
                with self.assertRaises(ValueError):
                    w.validate_observation(obs)
        for field in w.OBSERVATION_FIELDS:
            obs = observation()
            del obs[field]
            with self.assertRaises(ValueError):
                w.validate_observation(obs)

    def test_dimensions(self):
        cases = {'schema': 'old', 'global': [0] * 272, 'players': [[0] * 80],
                 'nodes': [], 'actions': [[0] * 34], 'relations': [[[0]]],
                 'actionCity': [-1], 'prior': [0]}
        for field, value in cases.items():
            with self.subTest(field=field):
                obs = observation()
                obs[field] = value
                with self.assertRaises(ValueError):
                    w.validate_observation(obs)
        for field, width in [('players', 80), ('nodes', 36), ('actions', 34)]:
            for count in {'players': (0, 1, 7), 'nodes': (0, 65), 'actions': (0, 1, 4097)}[field]:
                obs = observation()
                obs[field] = [[0] * width for _ in range(count)]
                with self.assertRaises(ValueError):
                    w.validate_observation(obs)
            obs = observation()
            obs[field][0].pop()
            with self.assertRaises(ValueError):
                w.validate_observation(obs)
        obs = observation()
        obs['relations'][0][0].pop()
        with self.assertRaises(ValueError):
            w.validate_observation(obs)

    def test_bad_numbers_and_float32_overflow(self):
        for field, path in [('global', (0,)), ('players', (0, 0)), ('nodes', (0, 0)),
                            ('actions', (0, 0)), ('relations', (0, 0, 0)), ('prior', (1,))]:
            for value in (True, False, '1', None, {}, [], float('nan'), float('inf'), -float('inf'), 1e39, 10**400):
                with self.subTest(field=field, value=str(value)[:20]):
                    obs = observation()
                    target = obs[field]
                    for index in path[:-1]:
                        target = target[index]
                    target[path[-1]] = value
                    with self.assertRaises(ValueError):
                        w.validate_observation(obs)

    def test_prior_and_indices(self):
        for value in (True, False, -2, 3, 0.0, '0'):
            obs = observation()
            obs['actionCity'][0] = value
            with self.assertRaises(ValueError):
                w.validate_observation(obs)
        for prior in ([0, -21, -1, -2, -3], [1, 0, -1, -2, -3], [-1] * 5):
            obs = observation()
            obs['prior'] = prior
            with self.assertRaises(ValueError):
                w.validate_observation(obs)


class ProtocolTests(unittest.TestCase):
    def test_strict_json(self):
        for raw in (b'{"a":1,"a":2}', b'{"x":{"a":1,"a":2}}', b'NaN', b'Infinity',
                    b'-Infinity', b'1e999', b'{} {}', b'\xff', b'\xef\xbb\xbf{}', b'{"x":1,}'):
            with self.subTest(raw=raw), self.assertRaises((ValueError, UnicodeError)):
                w.strict_json(raw)
        self.assertEqual(w.strict_json(b'{"a":1.5}'), {'a': 1.5})

    def test_request_validation(self):
        for field, value in [('schema', 'bad'), ('requestId', 'A' * 64), ('requestId', 'a' * 63),
                             ('requestId', 'a' * 64 + '\n'), ('requestId', 2), ('replica', 'replica2')]:
            msg = request()
            msg[field] = value
            with self.assertRaises(ValueError):
                w.RequestSession(FakePolicy()).handle(msg)
        for field in ('debug', 'targets', 'value'):
            msg = request()
            msg[field] = 1
            with self.assertRaises(ValueError):
                w.RequestSession(FakePolicy()).handle(msg)

    def test_duplicate_ids_and_lru_bound(self):
        policy = FakePolicy(3)
        session = w.RequestSession(policy)
        msg = request()
        first = session.handle(msg)
        self.assertEqual(session.handle(copy.deepcopy(msg)), first)
        self.assertEqual(policy.calls, 1)
        first['index'] = 999  # Returned objects cannot poison the retained response.
        self.assertEqual(session.handle(msg)['index'], 3)
        different = copy.deepcopy(msg)
        different['observation']['global'][0] += 0.25
        with self.assertRaises(ValueError):
            session.handle(different)
        for i in range(64):
            session.handle(request(request_id=f'{i:064x}'))
        self.assertEqual(len(session.cache), 64)
        self.assertNotIn('a' * 64, session.cache)
        self.assertEqual(policy.calls, 65)

    def test_bad_model_index(self):
        for index in (True, -1, 5, 0.0, '0'):
            with self.assertRaises(ValueError):
                w.RequestSession(FakePolicy(index)).handle(request())

    def run_stream(self, raw, policy=None):
        output = io.StringIO()
        code = w.serve(policy or FakePolicy(), io.BytesIO(raw), output)
        return code, [json.loads(line) for line in output.getvalue().splitlines()]

    def test_jsonl_and_eof(self):
        raw = w.canonical(request()) + b'\n'
        code, rows = self.run_stream(raw * 2)
        self.assertEqual(code, 0)
        self.assertEqual(rows[0]['schema'], 'pg-replica-serving-ready-v1')
        self.assertEqual(rows[1], rows[2])
        self.assertEqual(set(rows[1]), {'schema', 'requestId', 'replica', 'checkpointSha256', 'index', 'actionCount'})
        self.assertEqual(self.run_stream(b'')[0], 0)
        for malformed in (raw[:-1], b'\n', b'{bad}\n', b'[]\n', b'null\n', b'1e999\n'):
            code, rows = self.run_stream(malformed)
            self.assertEqual(code, 1)
            self.assertEqual(rows[-1], dict(schema='pg-replica-serving-error-v1', code='invalid-request'))
        different = request()
        different['observation']['global'][0] += 1
        code, rows = self.run_stream(raw + w.canonical(different) + b'\n' + raw)
        self.assertEqual(code, 1)
        self.assertEqual(len(rows), 3)  # Exit immediately after conflict; never process third request.

    def test_size_is_bounded_before_parse(self):
        class Bounded(io.BytesIO):
            sizes = []

            def readline(self, size=-1):
                self.sizes.append(size)
                return super().readline(size)

        stream = Bounded(b'x' * (w.MAX_LINE_BYTES + 100))
        output = io.StringIO()
        with patch.object(w, 'strict_json', side_effect=AssertionError('must not parse')):
            self.assertEqual(w.serve(FakePolicy(), stream, output), 1)
        self.assertEqual(stream.sizes, [w.MAX_LINE_BYTES + 1])
        self.assertEqual(stream.tell(), w.MAX_LINE_BYTES + 1)
        # A valid line at exactly the byte limit is accepted; one byte more fails.
        raw = w.canonical(request())
        exact = raw + b' ' * (w.MAX_LINE_BYTES - len(raw) - 1) + b'\n'
        self.assertEqual(self.run_stream(exact)[0], 0)
        self.assertEqual(self.run_stream(exact[:-1] + b' \n')[0], 1)

    def test_cli_redacts_errors_and_rejects_optimized_python(self):
        for args in ([], ['--replica', 'replica1', '--checkpoint', '/missing/SECRET-CHECKPOINT'],
                     ['--bogus', 'SECRET-INPUT']):
            run = subprocess.run([sys.executable, '-B', str(Path(w.__file__)), *args], capture_output=True, timeout=30)
            self.assertNotEqual(run.returncode, 0)
            self.assertEqual(run.stderr, b'')
            self.assertEqual(json.loads(run.stdout), dict(schema='pg-replica-serving-error-v1', code='startup-failed'))
        run = subprocess.run([sys.executable, '-O', '-B', str(Path(w.__file__))], capture_output=True, timeout=30)
        self.assertEqual(run.returncode, 1)
        self.assertEqual(run.stderr, b'')
        self.assertEqual(json.loads(run.stdout)['code'], 'startup-failed')


class IdentityTests(unittest.TestCase):
    def test_manifest_and_sources(self):
        manifest, digest = w.load_manifest()
        self.assertEqual(digest, w.sha256(w.MANIFEST.read_bytes()))
        self.assertEqual(len([p for p in manifest['sourceFiles'] if p.startswith('engine/dist/')]), 42)
        self.assertIn('engine/wrapper.ts', manifest['sourceFiles'])
        self.assertIn('engine/dist/wrapper.js', manifest['sourceFiles'])
        self.assertFalse(any(name.startswith('ai/serving_v1/') for name in manifest['sourceFiles']))
        self.assertEqual(set(w.verify_sources(manifest)), set(w.PYTHON_MODULES))
        bad = copy.deepcopy(manifest)
        bad['sourceFiles']['ai/multimap/model.py'] = '0' * 64
        with self.assertRaises(ValueError):
            w.verify_sources(bad)
        del bad['sourceFiles']['ai/multimap/model.py']
        with self.assertRaises(ValueError):
            w.verify_sources(bad)

    def test_manifest_rejects_role_and_config_changes(self):
        manifest, _ = w.load_manifest()
        for field, value in [('sha256', w.REPLICAS['replica2']['sha256']), ('configSha256', '0' * 64),
                             ('update', 32), ('bytes', 1), ('width', True)]:
            bad = copy.deepcopy(manifest)
            bad['replicas']['replica1'][field] = value
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / 'manifest.json'
                path.write_bytes(w.canonical(bad))
                with self.assertRaises(ValueError):
                    w.load_manifest(path)

    def test_full_saved_config_and_exact_types(self):
        config = dict(one=1, nested=dict(two=2, sourceFiles={'old.py': 'retained'}))
        pin = dict(update=24, configSha256=w.sha256(w.canonical(config)))
        saved = dict(w.ARCHITECTURE, config=config, update=24, state_dict={})
        w.validate_saved(saved, pin)
        bad = copy.deepcopy(saved)
        bad['config']['nested']['sourceFiles']['old.py'] = 'modified'
        with self.assertRaises(ValueError):
            w.validate_saved(bad, pin)
        for field, value in [('width', 64.0), ('bound', True), ('update', 32), ('stage', 'eval'),
                             ('priorAsActionFeature', 1), ('schema', 'other'), ('extra', None)]:
            bad = copy.deepcopy(saved)
            bad[field] = value
            with self.assertRaises(ValueError):
                w.validate_saved(bad, pin)

    def test_regular_file_size_and_ancestor_safety(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            real = root / 'real'
            real.mkdir()
            file = real / 'file'
            file.write_bytes(b'abc')
            self.assertEqual(w.safe_read(file, 3, size=3), b'abc')
            (root / 'link').symlink_to(real, target_is_directory=True)
            (root / 'direct').symlink_to(file)
            os.link(file, root / 'hardlink')
            with self.assertRaises(ValueError):
                w.safe_read(root / 'hardlink', 3)
            (root / 'hardlink').unlink()
            os.mkfifo(root / 'fifo')
            for path, limit, size in [(root / 'direct', 3, None), (root / 'link/file', 3, None),
                                       (file, 2, None), (file, 3, 2), (real, 99, None),
                                       (root / 'fifo', 3, None), (real / '../real/file', 3, None)]:
                with self.subTest(path=str(path)), self.assertRaises((ValueError, OSError)):
                    w.safe_read(path, limit, size=size)

    def test_applicable_stale_bytecode_rejected_without_deleting(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'helper.py'
            raw = b'answer = 42\n'
            path.write_bytes(raw)
            cache = Path(importlib.util.cache_from_source(str(path)))
            cache.parent.mkdir()
            header = importlib.util.MAGIC_NUMBER + struct.pack('<III', 0, int(path.stat().st_mtime), len(raw))
            wrong = header + marshal.dumps(compile(b'answer = 99\n', str(path), 'exec'))
            cache.write_bytes(wrong)
            with self.assertRaises(ValueError):
                w.authenticate_bytecode(path, raw)
            self.assertEqual(cache.read_bytes(), wrong)
            cache.write_bytes(header + marshal.dumps(compile(raw, str(path), 'exec')))
            w.authenticate_bytecode(path, raw)
            # Unchecked hash-based pyc must also be checked, not blindly trusted.
            cache.write_bytes(importlib.util.MAGIC_NUMBER + struct.pack('<I', 1) + b'0' * 8 + wrong[16:])
            with self.assertRaises(ValueError):
                w.authenticate_bytecode(path, raw)

    def test_checked_hash_bytecode_under_never_is_authenticated(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'helper.py'
            raw = b'answer = 42\n'
            path.write_bytes(raw)
            cache = Path(importlib.util.cache_from_source(str(path)))
            cache.parent.mkdir()
            wrong = (importlib.util.MAGIC_NUMBER + struct.pack('<I', 3) + b'0' * 8
                     + marshal.dumps(compile(b'answer = 99\n', str(path), 'exec')))
            cache.write_bytes(wrong)
            with patch.object(w._imp, 'check_hash_based_pycs', 'never'), self.assertRaises(ValueError):
                w.authenticate_bytecode(path, raw)
            self.assertEqual(cache.read_bytes(), wrong)
            with patch.object(w._imp, 'check_hash_based_pycs', 'default'):
                w.authenticate_bytecode(path, raw)  # CPython recompiles the mismatched checked cache.

    def test_checkpoint_hash_and_size_before_torch_load(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(w, 'frozen_runtime', side_effect=AssertionError('no load')):
            path = Path(directory) / 'fake.pt'
            for content in (b'x', b'x' * 793281):
                path.write_bytes(content)
                with self.assertRaises(ValueError):
                    w.ReplicaPolicy('replica1', path)
            with self.assertRaises(ValueError):
                w.ReplicaPolicy('expert24', path)


@unittest.skipUnless(HAS_TORCH, 'Torch is not installed; standard-library synthetic tests remain available')
class TensorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import torch
        cls.torch = torch
        torch.set_num_threads(1)
        manifest, _ = w.load_manifest()
        w.verify_sources(manifest)
        cls.expert = w.frozen_runtime()

    def policy(self):
        policy = object.__new__(w.ReplicaPolicy)
        policy._torch = self.torch
        policy._expert = self.expert
        policy.model = self.expert.ExpertPolicy().eval().requires_grad_(False)
        # Synthetic test-only policy; production captures this during authenticated load.
        policy._loaded_fingerprint = policy._model_fingerprint()
        return policy

    @staticmethod
    def fingerprint(model):
        return ({k: v.detach().clone() for k, v in model.state_dict().items()},
                [(name, module.training) for name, module in model.named_modules()],
                [(name, p.requires_grad, p.grad) for name, p in model.named_parameters()])

    def unchanged(self, model, before):
        after = self.fingerprint(model)
        self.assertEqual(before[1:], after[1:])
        self.assertEqual(set(before[0]), set(after[0]))
        for name in before[0]:
            self.assertTrue(self.torch.equal(before[0][name], after[0][name]), name)

    def test_zero_head_first_argmax_and_frozen_helpers(self):
        policy = self.policy()
        obs = observation()
        obs['prior'] = [-1, 0, 0, -20, -2]
        before = self.fingerprint(policy.model)
        for _ in range(3):
            self.assertEqual(policy.choose(obs), 1)
        self.unchanged(policy.model, before)
        with self.torch.inference_mode():
            batch = self.expert.batch([self.expert.row(obs)])
            self.assertEqual(batch['prior'].dtype, self.torch.float32)
            self.assertEqual(batch['actions'].shape, (1, 5, 34))
            self.assertTrue(batch['actionMask'].all())
            self.assertEqual(int(policy.model(batch)[0][0].argmax()), policy.choose(obs))

    def test_validation_precedes_tensor_allocation(self):
        policy = self.policy()
        obs = observation()
        obs['relations'][1][0].append(0)
        with patch.object(self.expert, 'row', side_effect=AssertionError('must not allocate')):
            with self.assertRaises(ValueError):
                policy.choose(obs)

    def test_bad_logits_and_masks(self):
        torch = self.torch
        policy = self.policy()
        obs = observation()

        class Output(torch.nn.Module):
            def __init__(self, output):
                super().__init__()
                self.output = output

            def forward(self, inputs):
                return self.output, None

        for output in (torch.zeros(5), torch.zeros(1, 4), torch.zeros(2, 5),
                       torch.zeros(1, 5, dtype=torch.float64), torch.full((1, 5), float('nan')),
                       torch.full((1, 5), float('inf'))):
            policy.model = Output(output).eval()
            # Isolate output validation on this synthetic stub, not model identity.
            policy._loaded_fingerprint = policy._model_fingerprint()
            with self.assertRaises(ValueError):
                policy.choose(obs)
        policy = self.policy()
        original = self.expert.batch

        def masked(rows):
            batch = original(rows)
            batch['actionMask'][0, 1] = False
            return batch

        with patch.object(self.expert, 'batch', side_effect=masked), self.assertRaises(ValueError):
            policy.choose(obs)
        policy.model.train()
        with self.assertRaises(ValueError):
            policy.choose(obs)

    def test_retained_fingerprint_rejects_changes_without_repair(self):
        torch = self.torch

        def reshape_parameter(model):
            layer = model.network.city[0]
            layer.weight = torch.nn.Parameter(layer.weight.flatten(), requires_grad=False)

        cases = {
            'finite-weight': lambda m: next(m.parameters()).add_(0.125),
            'bound': lambda m: setattr(m, 'bound', 8),
            'bound-type': lambda m: setattr(m, 'bound', 16.0),
            'width': lambda m: setattr(m, 'width', 32),
            'network-width': lambda m: setattr(m.network, 'width', 32),
            'mode': lambda m: m.network.train(),
            'requires-grad': lambda m: next(m.parameters()).requires_grad_(True),
            'gradient': lambda m: setattr(next(m.parameters()), 'grad', torch.zeros_like(next(m.parameters()))),
            'dtype': lambda m: m.double(),
            'shape': reshape_parameter,
            'keyset': lambda m: m.network.city[0].register_parameter('bias', None),
            'buffer': lambda m: m.register_buffer('unexpected', torch.zeros(1), persistent=False),
            'class': lambda m: m.network.city.__setitem__(1, torch.nn.Identity()),
        }
        for name, mutate in cases.items():
            with self.subTest(mutation=name):
                policy = self.policy()  # Disposable synthetic model, never a checkpoint.
                original = policy._loaded_fingerprint
                policy.assert_unchanged()
                with torch.no_grad():
                    mutate(policy.model)
                changed = policy._model_fingerprint()
                self.assertNotEqual(changed, original)
                for operation in (policy.assert_unchanged, lambda: policy.choose(observation())):
                    with self.assertRaises(ValueError):
                        operation()
                    self.assertEqual(policy._model_fingerprint(), changed)
                    self.assertEqual(policy._loaded_fingerprint, original)

    def test_choose_checks_model_after_inference_without_repair(self):
        policy = self.policy()
        original_forward = policy.model.forward

        def changed_forward(inputs):
            output = original_forward(inputs)
            policy.model.bound = 8  # Fault injection into a disposable synthetic model.
            return output

        with patch.object(policy.model, 'forward', side_effect=changed_forward), self.assertRaises(ValueError):
            policy.choose(observation())
        self.assertEqual(policy.model.bound, 8)
        with self.assertRaises(ValueError):
            policy.assert_unchanged()

    def test_nonfinite_checkpoint_weights_rejected_by_frozen_load(self):
        model = self.expert.ExpertPolicy()
        with self.torch.no_grad():
            next(model.parameters()).fill_(float('nan'))
        payload = io.BytesIO()
        self.torch.save(dict(w.ARCHITECTURE, state_dict=model.state_dict()), payload)
        payload.seek(0)
        with self.assertRaises(ValueError):
            self.expert.load(payload)

    def real_parity(self, replica):
        checkpoint = CHECKPOINTS[replica]
        if not checkpoint.is_file():
            self.skipTest('Private pinned checkpoint absent; no download attempted')
        if ('.'.join(map(str, sys.version_info[:3])) != w.RUNTIMES['python'] or
                self.torch.__version__ != w.RUNTIMES['torch']):
            self.skipTest('Pinned runtime unavailable')
        policy = w.ReplicaPolicy(replica, checkpoint)
        direct, saved = self.expert.load(checkpoint)
        direct.eval().requires_grad_(False)
        before = self.fingerprint(policy.model)
        direct_before = self.fingerprint(direct)
        self.assertEqual(saved['update'], w.REPLICAS[replica]['update'])
        self.assertEqual(w.sha256(w.canonical(saved['config'])), w.REPLICAS[replica]['configSha256'])
        for p, n, a in [(2, 1, 2), (4, 8, 37), (6, 64, 4096)]:
            obs = observation(p, n, a)
            with self.torch.inference_mode():
                logits, _ = direct(self.expert.batch([self.expert.row(obs)]))
                expected = int(logits[0].argmax().item())
            self.assertEqual(policy.choose(obs), expected)
            self.assertEqual(policy.choose(obs), expected)
        self.unchanged(policy.model, before)
        self.unchanged(direct, direct_before)
        other = 'replica2' if replica == 'replica1' else 'replica1'
        with self.assertRaises(ValueError):
            w.ReplicaPolicy(other, checkpoint)

    def test_replica1_actual_greedy_parity_and_immutability(self):
        self.real_parity('replica1')

    def test_replica2_actual_greedy_parity_and_immutability(self):
        self.real_parity('replica2')

    def test_actual_worker_persistent_transport(self):
        for replica, checkpoint in CHECKPOINTS.items():
            if not checkpoint.is_file():
                self.skipTest('Private pinned checkpoints absent; no download attempted')
            msg = request(replica=replica)
            run = subprocess.run([sys.executable, '-B', str(Path(w.__file__)), '--replica', replica,
                                  '--checkpoint', str(checkpoint)], input=(w.canonical(msg) + b'\n') * 2,
                                 capture_output=True, timeout=60)
            self.assertEqual(run.returncode, 0, run.stdout)
            self.assertEqual(run.stderr, b'')
            ready, first, second = map(json.loads, run.stdout.splitlines())
            self.assertEqual(ready['manifestSha256'], w.sha256(w.MANIFEST.read_bytes()))
            self.assertEqual(first, second)
            self.assertEqual(first['checkpointSha256'], w.REPLICAS[replica]['sha256'])
            self.assertEqual(first['index'], w.ReplicaPolicy(replica, checkpoint).choose(msg['observation']))


if __name__ == '__main__':
    unittest.main()
