"""Offline stress-plan, transport, frozen-loader and compact-outcome tests.

Synthetic games/models are explicit local test doubles, never production
checkpoints or reported evidence. No legacy serving globals are modified.
"""
from collections import Counter, defaultdict
import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest import mock

import torch

import stress_rollout as r


def observation(players=2, actions=2):
    return dict(schema='multimap-graph-v1', **{'global': [0.] * 273},
        players=[[0.] * 80 for _ in range(players)], nodes=[[0.] * 36 for _ in range(3)],
        actions=[[0.] * 34 for _ in range(actions)], actionCity=[-1] * actions,
        relations=[[[0.] * 3 for _ in range(3)] for _ in range(4)], prior=[0.] * actions)


def terminal(spec):
    counts = {name: dict.fromkeys(r.PHASES, 0) for name in r.CONTROLLERS}
    seats = [dict.fromkeys(r.PHASES, 0) for _ in range(spec['players'])]
    for seat, name in enumerate(spec['controllers']):
        for phase in r.PHASES:
            controller = name if name in ('reference', 'teacherV2') or phase in r.LEARNED_PHASES else (
                'fixedV2' if name == 'expert24' else 'fixedV1')
            counts[controller][phase] += 1
            seats[seat][phase] += 1
        if name in r.MODELS:
            counts['fixedV2' if name == 'expert24' else 'fixedV1']['Auction'] += 1
            seats[seat]['Auction'] += 1
    reference = sum(counts['reference'].values())
    return dict(terminal=True, credit=[1 / spec['players']] * spec['players'],
        steps=sum(sum(c.values()) for c in seats), rounds=1, counts=counts, seatCounts=seats,
        publicChecks=dict(hiddenInvariant=reference, referenceAtomicLegal=reference,
            expertAtomicLegal=0, fullMenuPrior=sum(sum(counts[name].values()) for name in r.MODELS)))


def outcome(spec):
    state = terminal(spec)
    return dict(spec=copy.deepcopy(spec), terminal=True, credit=state['credit'][spec['focalSeat']],
        allSeatCredit=state['credit'], steps=state['steps'], rounds=state['rounds'],
        counts=state['counts'], seatCounts=state['seatCounts'], publicChecks=state['publicChecks'],
        policyRequests={name: sum(state['counts'][name].values()) for name in r.MODELS},
        referenceRequests=sum(state['counts']['reference'].values()), featureMs=0., inferenceMs=0.,
        referenceMs=0., seconds=0.)


def choose(**criteria):
    return next(s for s in r.plans(True) if all(s[key] == value for key, value in criteria.items()))


class GreedyModel(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.layer = torch.nn.Linear(1, 1)
        self.calls = []
        self.actions = []

    def forward(self, tensors):
        assert not self.training and not torch.is_grad_enabled()
        self.calls.append(len(tensors['global']))
        # All real scores below -1e9: a legacy finite padding sentinel cannot
        # safely mask these. Deliberately offer huge/NaN padded logits.
        logits = torch.full(tensors['actionMask'].shape, -3e12)
        logits[:, 1] = -2e12
        logits[~tensors['actionMask']] = float('nan')
        return logits, torch.zeros(len(logits))


class Bridge:
    instances = []
    mutate = None
    end_mutate = None

    def __init__(self, argv, **kwargs):
        assert str(argv[-1]).endswith('stress_game.cjs')
        self.closed = False
        self.requests = []
        self.instances.append(self)

    def close(self):
        self.closed = True

    def call(self, request):
        self.requests.append(copy.deepcopy(request))
        if request['op'] == 'start':
            assert set(request) == {'op', 'spec'}
            self.spec = request['spec']
            self.events = [(seat, name, phase) for seat, name in enumerate(self.spec['controllers'])
                for phase in r.PHASES if name == 'reference' or (name in r.MODELS and phase in r.LEARNED_PHASES)]
            self.index = 0
        elif request['op'] == 'step':
            name = self.events[self.index][1]
            if name == 'reference':
                assert set(request) == {'op', 'response'}
                assert request['response']['move'] == {'name': 'test'}
            else:
                assert set(request) == {'op', 'index'}
                assert request['index'] == 1
            self.index += 1
        else:
            raise AssertionError('Labels/training/sampling are forbidden')
        if self.index == len(self.events):
            state = terminal(self.spec)
            if self.end_mutate:
                self.end_mutate(state)
            return state
        seat, name, phase = self.events[self.index]
        state = dict(terminal=False, kind='reference' if name == 'reference' else 'policy',
            controller=name, seat=seat, phase=phase, revision=self.index)
        if name == 'reference':
            state['request'] = dict(player=seat, revision=self.index, requestId=f'test-{self.index}',
                state=dict(seed='secret', powerPlantsDeck=[], hiddenLog=[], currentBid=0,
                    options={key: self.spec[key] for key in ('map', 'variant', 'fastBid')},
                    players=[dict(lastMove=None, bid=0) for _ in range(self.spec['players'])],
                    phase=phase, currentPlayers=[seat]))
        else:
            state.update(observation=observation(self.spec['players'], self.spec['focalSeat'] + 2), featureMs=.25)
        if self.mutate:
            self.mutate(state)
        return state


class Reference:
    instances = []

    def __init__(self, *args):
        self.closed = False
        self.instances.append(self)

    def close(self):
        self.closed = True

    def decide(self, request):
        assert not self.closed
        return dict(requestId=request['requestId'], revision=request['revision'], move={'name': 'test'})


class StressRolloutTests(unittest.TestCase):
    def setUp(self):
        Bridge.instances, Reference.instances = [], []
        Bridge.mutate = Bridge.end_mutate = None
        self.models = {name: GreedyModel() for name in r.MODELS}
        self.models['ppo1'].eval()
        self.models['expert24'].layer.eval()  # Mixed child mode must survive.
        self.modes = [(m, m.training) for model in self.models.values() for m in model.modules()]
        self.threads = torch.get_num_threads()

    def collect(self, tasks, workers=3, bridge=Bridge, reference=Reference):
        with mock.patch.object(r, 'LineProcess', bridge), mock.patch.object(r, 'ReferenceProcess', reference):
            return r.collect(tasks, workers, models=self.models)

    def assert_restored(self):
        self.assertTrue(all(p.closed for p in Bridge.instances + Reference.instances))
        self.assertEqual(torch.get_num_threads(), self.threads)
        self.assertTrue(all(m.training == was for m, was in self.modes))

    def test_full_plans_pairing_rotations_and_namespaces(self):
        prod, smoke = r.plans(), r.plans(True)
        self.assertEqual((len(prod), len(smoke)), (5120, 1280))
        self.assertEqual(len({s['cell'] for s in prod}), 80)
        self.assertEqual(Counter(s['panel'] for s in prod), {'strong': 2560, 'mixed': 2560})
        self.assertFalse({s['seed'] for s in prod} & {s['seed'] for s in smoke})
        self.assertEqual({s['map'] for s in smoke}, set(r.PROTOCOL['maps']))
        self.assertEqual({s['players'] for s in smoke}, set(range(2, 7)))
        for tasks in (prod, smoke):
            r.validate_tasks(tasks)
            groups = defaultdict(list)
            for spec in tasks:
                groups[spec['seed']].append(spec)
                self.assertEqual(set(spec), r.SPEC_FIELDS)
                self.assertNotIn('Italy', spec['seed'])
                self.assertNotIn('Benelux', spec['seed'])
            self.assertEqual(len(groups), 160 if tasks is smoke else 640)
            for specs in groups.values():
                n = specs[0]['players']
                self.assertEqual(len(specs), 2 * n)
                for seat in range(n):
                    a, b = [s for s in specs if s['focalSeat'] == seat]
                    self.assertEqual([a['policy'], b['policy']], ['expert24', 'ppo2'])
                    self.assertEqual(a['controllers'][:seat] + a['controllers'][seat+1:],
                                     b['controllers'][:seat] + b['controllers'][seat+1:])
        # Compute the rotation formula independently, including every full-grid ci.
        cells = list(dict.fromkeys(s['cell'] for s in prod))
        for spec in prod:
            weak = ['ppo0', 'ppo1', 'ppo2', 'teacherV2'] + (['reference'] if spec['map'] == 'Germany' else [])
            for seat, controller in enumerate(spec['controllers']):
                if seat == spec['focalSeat']:
                    expected = spec['policy']
                elif spec['panel'] == 'strong':
                    expected = 'reference' if spec['map'] == 'Germany' else 'expert24'
                else:
                    i = cells.index(spec['cell']) + spec['deal'] + (seat-spec['focalSeat']+spec['players']) % spec['players'] - 1
                    expected = 'expert24' if i % 2 == 0 else weak[(i//2) % len(weak)]
                self.assertEqual(controller, expected)

    def test_independent_plan_guards_no_labels_or_custom_namespace(self):
        spec = r.plans(True)[0]
        for patch in ({'seed': 'final:0'}, {'map': 'Italy'}, {'map': 'Benelux'}, {'training': False},
                      {'split': 'selection'}, {'expertRequired': False}, {'focalTeacher': False}, {'deal': 1},
                      {'players': 2.0}, {'players': True}, {'focalSeat': False}, {'fastBid': 0},
                      {'smoke': 1}, {'maxSteps': 4000.0}, {'policy': 'ppo0'}, {'controllers': ['expert24'] * 2}):
            with self.subTest(patch=patch), self.assertRaises(ValueError):
                r.validate_tasks([dict(spec, **patch)])
        for tasks in ([], [spec, spec], [spec, r.plans()[0]]):
            with self.assertRaises(ValueError):
                r.validate_tasks(tasks)
        for flag in (1, 'train', None):
            with self.assertRaises(ValueError):
                r.plans(flag)
        for kwargs in ({'training': False}, {'mode': 'evaluation'}, {'seed': 0}, {'protocol': r.PROTOCOL}):
            with self.assertRaises(TypeError):
                r.collect([spec], models=self.models, **kwargs)
        with mock.patch.object(r, 'plans', side_effect=AssertionError('validator must reconstruct independently')):
            r.validate_tasks([spec])
        for workers in (True, 0, 7, 1.0):
            with self.assertRaises(ValueError):
                r.collect([spec], workers, models=self.models)
        with self.assertRaises(ValueError):
            r.collect([spec], models={name: self.models[name] for name in r.FROZEN})

    def test_batched_greedy_all_models_reference_teacher_compact_only(self):
        tasks = [choose(map='Germany', panel='strong', players=2)]
        for name in (*r.FROZEN, 'teacherV2'):
            tasks.append(next(s for s in r.plans(True) if s['panel'] == 'mixed' and name in s['controllers'] and s not in tasks))
        tasks += [choose(map='USA', panel='strong', players=3, focalSeat=seat) for seat in (0, 1, 2)]
        rng = torch.random.get_rng_state().clone()
        results = self.collect(tasks, 6)
        self.assertEqual([v['spec'] for v in results], tasks)
        self.assertTrue(all(model.calls for model in self.models.values()))
        self.assertTrue(any(size > 1 for model in self.models.values() for size in model.calls))
        self.assertTrue(Reference.instances)
        self.assertTrue(torch.equal(rng, torch.random.get_rng_state()))
        for result in results:
            r.validate_outcome(result, result['spec'])
            self.assertEqual(result['publicChecks']['expertAtomicLegal'], 0)
            for key in ('rows', 'trace', 'traces', 'request', 'observation', 'expertIndex', 'expertRequests'):
                self.assertNotIn(key, result)
        self.assert_restored()

    def test_worker_count_invariance_and_alias_models(self):
        tasks = [choose(map='USA', panel='strong', players=3, focalSeat=seat) for seat in range(3)]
        a, b = self.collect(tasks, 1), self.collect(tasks, 3)
        for result in a + b:
            for key in ('featureMs', 'inferenceMs', 'referenceMs', 'seconds'):
                result.pop(key)
        self.assertEqual(a, b)
        self.models = dict.fromkeys(r.MODELS, self.models['expert24'])
        self.collect(tasks)
        self.assert_restored()

    def test_terminal_and_persisted_counters_credit_and_routing(self):
        spec = choose(map='USA', panel='mixed', players=6)
        good = terminal(spec)
        self.assertAlmostEqual(r._terminal(good, spec), 1/6)
        alterations = [lambda x: x.update(credit=[.5, .1, .1, .1, .1, .1]),
            lambda x: x.update(credit=[True, 0, 0, 0, 0, 0]), lambda x: x.update(steps=0),
            lambda x: x.update(steps=4001), lambda x: x.update(rounds=0),
            lambda x: x['counts']['expert24'].update(Auction=1.0),
            lambda x: x['seatCounts'][0].update(Resources=-1),
            lambda x: x['seatCounts'].pop(), lambda x: x['counts'].update(learner=dict.fromkeys(r.PHASES, 0)),
            lambda x: x['publicChecks'].update(expertAtomicLegal=1),
            lambda x: x['publicChecks'].update(fullMenuPrior=0), lambda x: x.update(expertCounts={}),
            lambda x: x['counts']['reference'].update(Auction=1),
            lambda x: x['counts']['expert24'].update(Resources=1)]
        for alter in alterations:
            bad = copy.deepcopy(good)
            alter(bad)
            with self.subTest(alter=alter), self.assertRaises(ValueError):
                r._terminal(bad, spec)
        result = outcome(spec)
        r.validate_outcome(result, spec)
        for patch in ({'credit': 0}, {'seconds': float('nan')}, {'referenceRequests': True},
                      {'rows': []}, {'policyRequests': dict.fromkeys(r.MODELS, 0)}):
            with self.assertRaises(ValueError):
                r.validate_outcome(dict(result, **patch), spec)

    def test_fail_closed_policy_observations_modes_threads_and_processes(self):
        tasks = [choose(map='USA', panel='strong', players=2)]
        mutations = [lambda s: s.update(expertRequired=False), lambda s: s.update(request={}),
            lambda s: s.update(kind='learner'), lambda s: s.update(controller='ppo1'),
            lambda s: s.update(phase='Resources'), lambda s: s.update(revision=True),
            lambda s: s.update(featureMs=float('nan')), lambda s: s['observation'].update(targets=[1, 0]),
            lambda s: s['observation'].update(seed='private'), lambda s: s['observation'].update(schema='other'),
            lambda s: s['observation']['global'].__setitem__(0, float('nan')),
            lambda s: s['observation']['relations'][0][0].__setitem__(0, float('inf')),
            lambda s: s['observation']['prior'].__setitem__(0, float('nan')),
            lambda s: s['observation']['actionCity'].__setitem__(0, .5)]
        for mutate in mutations:
            Bridge.mutate = staticmethod(mutate)
            with self.subTest(mutate=mutate), self.assertRaises(ValueError):
                self.collect(tasks)
            self.assert_restored()
        Bridge.mutate = None
        Bridge.end_mutate = staticmethod(lambda s: s['publicChecks'].update(expertAtomicLegal=1))
        with self.assertRaises(ValueError):
            self.collect(tasks)
        self.assert_restored()

    def test_reference_public_bindings_identity_failure_and_cleanup(self):
        tasks = [choose(map='Germany', panel='strong', players=2, focalSeat=1, fastBid=True)]
        changes = [lambda s: s.update(controller='expert24'), lambda s: s['request'].update(player=1),
            lambda s: s['request'].update(revision=100), lambda s: s['request'].update(expert=True),
            lambda s: s['request']['state'].update(seed='private'),
            lambda s: s['request']['state'].update(powerPlantsDeck=[42]),
            lambda s: s['request']['state'].update(automation={}),
            lambda s: s['request']['state']['options'].update(map='USA'),
            lambda s: s['request']['state']['players'][0].update(bid=1)]
        for change in changes:
            Bridge.mutate = staticmethod(lambda s, change=change: change(s) if s['kind'] == 'reference' else None)
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.collect(tasks)
            self.assert_restored()
        Bridge.mutate = None
        with mock.patch.object(Reference, 'decide', side_effect=RuntimeError('reference identity failed')):
            with self.assertRaisesRegex(RuntimeError, 'identity failed'):
                self.collect(tasks)
        self.assert_restored()
        with mock.patch.object(Reference, 'decide', return_value={'index': 0, 'move': {}}):
            with self.assertRaises(ValueError):
                self.collect(tasks)
        self.assert_restored()

    def test_counter_reconciliation_not_just_total_steps(self):
        spec = choose(map='USA', panel='strong', players=2)
        # Shift a learned move into the same seat's fixed counter; standalone
        # terminal totals remain feasible but the observed policy request does not.
        def corrupt(state):
            state['counts']['expert24']['Auction'] -= 1
            state['counts']['fixedV2']['Auction'] += 1
            state['publicChecks']['fullMenuPrior'] -= 1
        bad = terminal(spec)
        corrupt(bad)
        r._terminal(bad, spec)
        Bridge.end_mutate = staticmethod(corrupt)
        with self.assertRaisesRegex(ValueError, 'request counters'):
            self.collect([spec])
        self.assert_restored()

    def test_nonfinite_model_and_full_mask_rejection(self):
        spec = choose(map='USA', panel='strong', players=2)
        with mock.patch.object(self.models['expert24'], 'forward', return_value=(torch.full((1, 2), float('nan')), torch.zeros(1))):
            with self.assertRaisesRegex(ValueError, 'Nonfinite'):
                self.collect([spec], 1)
        self.assert_restored()
        real_batch = r.batch
        def broken(rows):
            tensors = real_batch(rows)
            tensors['actionMask'][0, 0] = False
            return tensors
        with mock.patch.object(r, 'batch', side_effect=broken):
            with self.assertRaisesRegex(ValueError, 'full-menu'):
                self.collect([spec], 1)
        self.assert_restored()

    def test_cleanup_when_reference_finishes_construction_after_failure(self):
        entered, closing = threading.Event(), threading.Event()
        class RaceBridge(Bridge):
            def call(self, request):
                if request['op'] == 'start' and request['spec']['map'] != 'Germany':
                    assert entered.wait(5)
                    raise RuntimeError('parallel failure')
                return super().call(request)
            def close(self):
                super().close()
                closing.set()
        class SlowReference(Reference):
            def __init__(self, *args):
                entered.set()
                assert closing.wait(5)
                super().__init__(*args)
        tasks = [choose(map='USA', panel='strong', players=2),
                 choose(map='Germany', panel='strong', players=2, focalSeat=1)]
        with self.assertRaisesRegex(RuntimeError, 'parallel failure'):
            self.collect(tasks, 2, RaceBridge, SlowReference)
        self.assertTrue(Reference.instances)
        self.assert_restored()

    def test_cleanup_attempts_every_child_and_preserves_original_error(self):
        class BrokenClose(Bridge):
            def close(self):
                super().close()
                raise RuntimeError('close failed')
        tasks = [choose(map='USA', panel='strong', players=2, focalSeat=i) for i in (0, 1)]
        Bridge.mutate = staticmethod(lambda s: s.update(expertRequired=True))
        with self.assertRaisesRegex(ValueError, 'labels'):
            self.collect(tasks, 2, BrokenClose)
        self.assert_restored()
        Bridge.mutate = None
        with self.assertRaisesRegex(RuntimeError, 'cleanup failed'):
            self.collect(tasks, 2, BrokenClose)
        self.assert_restored()

    def test_immutable_legacy_transport_is_reused_and_timeout_reaped(self):
        from expert_rollout import LineProcess
        self.assertIs(r.LineProcess, LineProcess)
        child = r.LineProcess([sys.executable, '-u', '-c', 'import time; time.sleep(30)'], timeout=.05)
        try:
            with self.assertRaises(TimeoutError):
                child.call({'op': 'test'})
            self.assertIsNotNone(child.process.poll())
            self.assertFalse(child.reader.is_alive())
        finally:
            child.close()

    def test_real_node_offline_prior_only_homogeneous_seat_replay(self):
        class PriorOnly(torch.nn.Module):
            def forward(self, tensors):
                return tensors['prior'], torch.zeros(len(tensors['global']))
        model = PriorOnly()
        tasks = [choose(map='USA', panel='strong', players=2, policy='expert24', focalSeat=seat)
                 for seat in range(2)]
        results = r.collect(tasks, 2, models=dict.fromkeys(r.MODELS, model))
        for result in results:
            r.validate_outcome(result, result['spec'])
        for key in ('allSeatCredit', 'steps', 'rounds', 'counts', 'seatCounts', 'publicChecks',
                    'policyRequests', 'referenceRequests'):
            self.assertEqual(results[0][key], results[1][key])
        self.assertEqual(sum(result['credit'] for result in results), 1.)
        self.assertTrue(model.training)
        self.assertEqual(torch.get_num_threads(), self.threads)

    def test_node_accepts_independent_full_python_plan(self):
        # No reference/checkpoints needed; independently validate all 5,120 specs.
        script = "const fs=require('fs'),{validateSpec}=require('./ai/multimap/stress_game.cjs');" \
                 "JSON.parse(fs.readFileSync(0,'utf8')).forEach(validateSpec);console.log('ok');"
        result = subprocess.run(['node', '-e', script], input=json.dumps(r.plans() + r.plans(True)),
            cwd=r.ROOT, text=True, capture_output=True, timeout=30, check=True)
        self.assertEqual(result.stdout.strip(), 'ok')


class FrozenProtocolTests(unittest.TestCase):
    def fresh_protocol(self, directory, protocol):
        # Only the stress module/protocol are copied. All legacy helpers resolve
        # through the real source PYTHONPATH, without patched import snapshots.
        directory = Path(directory)
        shutil.copyfile(r.__file__, directory / 'stress_rollout.py')
        (directory / 'stress-protocol-v1.json').write_text(json.dumps(protocol))
        script = """
import sys
from pathlib import Path
import candidates
import stress_rollout
assert Path(stress_rollout.__file__).resolve().parent == Path.cwd()
assert Path(candidates.__file__).resolve().parent == Path(sys.argv[1])
stress_rollout._protocol()
"""
        env = dict(os.environ, PYTHONPATH=os.pathsep.join(filter(None,
            (str(r.HERE), os.environ.get('PYTHONPATH')))))
        return subprocess.run([sys.executable, '-B', '-c', script, str(r.HERE)],
            cwd=directory, env=env, text=True, capture_output=True, timeout=30)

    def test_fresh_process_accepts_prose_clarification_not_a_whole_protocol_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            for protocol in (r.PROTOCOL, dict(r.PROTOCOL, primaryAnalysis='Clarified methodology.')):
                result = self.fresh_protocol(directory, protocol)
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_fresh_process_rejects_altered_pins_flags_totals_and_budgets(self):
        changes = [
            (('selected', 'name'), 'expert23'), (('selected', 'repo'), 'other/model'),
            (('selected', 'revision'), '0' * 40), (('selected', 'path'), 'other.pt'),
            (('selected', 'sha256'), '0' * 64), (('selected', 'update'), 23),
            (('selected', 'update'), 24.0), (('selected', 'repo_type'), 'model'),
            (('oldPool',), 'other-pool.json'), (('oldPoolSha256',), '0' * 64),
            (('expertProtocol',), 'other-protocol.json'), (('expertSourceGit',), '0' * 40),
            (('modelRepo',), 'other/model'), (('allFocalSeats',), False),
            (('cellsPerPanel',), 79), (('independentDealsPerPanel',), 321),
            (('gamesPerPanel',), 2561), (('games',), 5121),
            (('studyArtifactMaxBytes',), 64 * 1024**2 + 1),
            (('referenceCacheMaxBytes',), 512 * 1024**2 + 1),
            (('referenceVenvMaxBytes',), 256 * 1024**2 + 1),
            (('uploadEveryBatches',), 17), (('excludedMaps',), []),
        ]
        changes += [((key,), value) for key in
            ('fitting', 'selection', 'qualificationEligible', 'reservedFinalSeedsUsed')
            for value in (True, 0)]
        with tempfile.TemporaryDirectory() as directory:
            for keys, value in changes:
                protocol = copy.deepcopy(r.PROTOCOL)
                target = protocol
                for key in keys[:-1]:
                    target = target[key]
                target[keys[-1]] = value
                with self.subTest(keys=keys, value=value):
                    result = self.fresh_protocol(directory, protocol)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn('Unexpected frozen stress protocol', result.stderr)


class FrozenLoaderTests(unittest.TestCase):
    def test_metadata_first_exact_hash_config_and_canonical_legacy_loader(self):
        import candidates
        import expert_ppo
        self.assertIs(r.POOL, candidates.POOL)
        self.assertIs(r.load_candidates, candidates.load_candidates)
        with tempfile.TemporaryDirectory() as directory:
            pins = {p['name']: p for p in [r.PROTOCOL['selected'], *r.POOL['members']]}
            paths = {name: Path(directory) / f'{name}.pt' for name in r.MODELS}
            for name, path in paths.items():
                path.write_bytes(name.encode())
            metadata = {name: SimpleNamespace(commit_hash=pin['revision'], size=paths[name].stat().st_size)
                        for name, pin in pins.items()}
            urls = {r.hf_hub_url(pin['repo'], pin['path'], revision=pin['revision']): name
                    for name, pin in pins.items()}
            requests = {(pin['repo'], pin['path'], pin['revision']): name for name, pin in pins.items()}
            models = {name: GreedyModel() for name in r.MODELS}
            saved = dict(schema=r.EXPERT_SCHEMA, update=24, stage='train', config={'identity': 'exact'})
            events = []
            actual_digest = r.digest
            source_files = {name: actual_digest(r.HERE / name) for name in candidates.SERVING_FILES}
            old_saved = {name: dict(update=pins[name]['update'],
                config=dict(generatorDigest='test-engine', sourceFiles=source_files)) for name in r.FROZEN}
            def digest(path):
                path = Path(path)
                return pins[path.stem]['sha256'] if path in paths.values() else actual_digest(path)
            def meta(url):
                name = urls[url]
                events.append(('metadata', name))
                return metadata[name]
            def download(repo, filename, *, revision, repo_type='model'):
                self.assertEqual(repo_type, 'model')
                name = requests[repo, filename, revision]
                events.append(('download', name))
                return str(paths[name])
            def load_old(path):
                name = Path(path).stem
                return models[name], old_saved[name]
            with mock.patch.object(r, 'get_hf_file_metadata', side_effect=meta), \
                 mock.patch.object(r, 'hf_hub_download', side_effect=download), \
                 mock.patch.object(candidates, 'hf_hub_download', side_effect=download), \
                 mock.patch.object(r, 'digest', side_effect=digest), \
                 mock.patch.object(candidates, 'digest', side_effect=digest), \
                 mock.patch.object(candidates, 'generator_digest', return_value='test-engine'), \
                 mock.patch.object(candidates, 'load', side_effect=load_old), \
                 mock.patch.object(r, 'load_expert', return_value=(models['expert24'], saved)), \
                 mock.patch.object(expert_ppo, 'config', return_value={'identity': 'exact'}) as config, \
                 mock.patch.object(r, 'load_candidates', wraps=candidates.load_candidates) as legacy:
                result = r.load_models('retained', 'reference-python')
                # All four distinct metadata sizes/revisions pass before the
                # first transfer, and each original downloader is called once.
                self.assertEqual(events, [('metadata', name) for name in r.MODELS] +
                                         [('download', name) for name in r.MODELS])
                self.assertEqual(result, models)
                self.assertTrue(all(not m.training and not any(p.requires_grad for p in m.parameters()) for m in result.values()))
                legacy.assert_called_once_with(list(r.FROZEN))
                config.assert_called_once_with(False, artifact='retained', reference_python='reference-python', workers=6)
                for bad in ({'update': 23}, {'update': True}, {'stage': 'warmup'}, {'schema': 'legacy'}, {'config': {'identity': 'other'}}):
                    with mock.patch.object(r, 'load_expert', return_value=(models['expert24'], dict(saved, **bad))):
                        with self.assertRaises(ValueError):
                            r.load_models()
                metadata['expert24'].size += 1
                with self.assertRaisesRegex(ValueError, 'Expert checkpoint size/hash mismatch'):
                    r.load_models()
                metadata['expert24'].size -= 1
                with mock.patch.object(r, 'digest', side_effect=lambda p:
                        'wrong' if Path(p) == paths['expert24'] else digest(p)):
                    with self.assertRaisesRegex(ValueError, 'Expert checkpoint size/hash mismatch'):
                        r.load_models()
                # Exercise the unchanged legacy source/hash guards too, rather
                # than substituting a fake successful load_candidates function.
                with mock.patch.object(candidates, 'digest', side_effect=lambda p:
                        'wrong' if Path(p) == paths['ppo0'] else digest(p)):
                    with self.assertRaisesRegex(ValueError, 'Candidate checkpoint hash mismatch'):
                        r.load_models()
                with mock.patch.object(candidates, 'digest', side_effect=lambda p:
                        'wrong' if Path(p) == r.HERE / candidates.SERVING_FILES[0] else digest(p)):
                    with self.assertRaisesRegex(ValueError, 'Candidate serving source changed'):
                        r.load_models()

    def test_every_checkpoint_metadata_refuses_bad_size_or_revision_before_any_download(self):
        import candidates
        pins = [r.PROTOCOL['selected'], *r.POOL['members']]
        urls = {pin['name']: r.hf_hub_url(pin['repo'], pin['path'], revision=pin['revision']) for pin in pins}
        metadata = {urls[pin['name']]: SimpleNamespace(commit_hash=pin['revision'], size=10) for pin in pins}
        with mock.patch.object(r, 'get_hf_file_metadata', side_effect=metadata.__getitem__), \
             mock.patch.object(r, 'hf_hub_download') as download, \
             mock.patch.object(candidates, 'hf_hub_download') as old_download, \
             mock.patch.object(r, 'load_candidates') as legacy, \
             mock.patch.object(r, 'load_expert') as expert:
            for pin in pins:
                meta = metadata[urls[pin['name']]]
                for value in (None, -1, 0, True, 1.0, 16 * 1024**2 + 1):
                    meta.size = value
                    with self.subTest(name=pin['name'], size=value), self.assertRaisesRegex(ValueError, '16 MiB'):
                        r.load_models()
                    download.assert_not_called()
                    old_download.assert_not_called()
                    legacy.assert_not_called()
                    expert.assert_not_called()
                meta.size = 10
                meta.commit_hash = 'main'
                with self.subTest(name=pin['name']), self.assertRaisesRegex(ValueError, 'immutable revision'):
                    r.load_models()
                download.assert_not_called()
                old_download.assert_not_called()
                legacy.assert_not_called()
                expert.assert_not_called()
                meta.commit_hash = pin['revision']

    def test_legacy_pool_must_match_its_pinned_file_before_metadata_or_download(self):
        changed = copy.deepcopy(r.POOL)
        changed['members'][0]['revision'] = 'main'
        with mock.patch.object(r, 'POOL', changed), \
             mock.patch.object(r, 'get_hf_file_metadata') as metadata, \
             mock.patch.object(r, 'hf_hub_download') as download, \
             mock.patch.object(r, 'load_candidates') as legacy:
            with self.assertRaisesRegex(ValueError, 'Frozen legacy candidate pool changed'):
                r.load_models()
            metadata.assert_not_called()
            download.assert_not_called()
            legacy.assert_not_called()


if __name__ == '__main__':
    unittest.main()
