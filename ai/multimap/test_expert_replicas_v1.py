"""Offline replica scope, byte-identity, and transaction adversarial checks."""
import copy
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
import itertools
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import torch

import expert_ppo as trainer
import expert_rollout as rollout
import expert_replicas_v1 as adapter
import job_expert
import job_expert_replicas_v1 as worker
from expert_policy import ExpertPolicy, load
from expert_replicas_v1 import Replica, protocol_for, BASE, HERE, STUDY, SOURCES, FROZEN_SOURCES, CRITICAL_PROTOCOL
from test_expert_training import synthetic_collect, equal
from data import ROOT, atomic_json, digest


class ReplicaTests(unittest.TestCase):
    def test_only_rng_and_evaluation_scope_differ(self):
        for r in (1, 2):
            p = protocol_for(r)
            self.assertEqual({k for k in p if p[k] != BASE[k]}, {'seed', 'seedNamespace', 'transferMaps'})
        for bad in (0, 3, True, '1', None):
            with self.assertRaises(ValueError): protocol_for(bad)
        self.assertNotEqual(protocol_for(1)['seed'], protocol_for(2)['seed'])

    def test_every_protocol_override_and_type_coercion_is_rejected(self):
        for r in (1, 2):
            replica = Replica(r)
            # Includes priors, hyperparameters, reference/model pins, scope,
            # outcome flags, and every other original recipe field, not merely
            # the three deliberately changed replica fields.
            for key, old in replica.protocol.items():
                if type(old) is bool:
                    changed = not old
                elif type(old) in (int, float):
                    changed = old + 1
                elif isinstance(old, str):
                    changed = old + '-changed'
                elif isinstance(old, list):
                    changed = old + ['changed']
                else:
                    changed = dict(old, changed=True)
                with self.subTest(replica=r, field=key):
                    with self.assertRaises(ValueError):
                        replica.plans('train', 1, protocol=dict(replica.protocol, **{key: changed}))
                    with self.assertRaises(ValueError):
                        replica.config(True, dict(replica.protocol, **{key: changed}))
            for key, value in [('selectionDealsPerCell', True), ('workers', '6'),
                               ('priorAsActionFeature', 1), ('selectionGermanyNonregression', 1),
                               ('qualificationEligible', 0), ('reservedFinalSeedsUsed', 0)]:
                with self.subTest(replica=r, coercion=key):
                    with self.assertRaises(ValueError):
                        replica.plans('train', 1, protocol=dict(replica.protocol, **{key: value}))
        self.assertEqual(trainer.make_protocol(), BASE)

    def test_disjoint_scopes_counts_and_old_guards(self):
        all_roots = set()
        for r in (1, 2):
            replica = Replica(r); p = replica.protocol
            for smoke in (False, True):
                for split, update in [('warmup', 0), ('selection', 0), ('confirmation', 0)] + [('train', i) for i in range(1, 33)]:
                    tasks = replica.plans(split, update, smoke=smoke, protocol=p)
                    roots = {s['seed'] for s in tasks}
                    self.assertFalse(all_roots & roots); all_roots |= roots
                    self.assertTrue({s['map'] for s in tasks} <= set(BASE['trainMaps']))
                    if not smoke:
                        self.assertEqual(len(tasks), {'warmup':160, 'train':80, 'selection':320, 'confirmation':640}[split])
                    mode = split if split in ('train', 'warmup') else 'evaluation'
                    replica.validate_tasks(tasks[:1], mode, mode != 'evaluation', p)
                    with self.assertRaises(ValueError): rollout.validate_tasks(tasks[:1], mode, mode != 'evaluation')
            with self.assertRaises(ValueError): replica.plans('train', 1, protocol=BASE)
            with self.assertRaises(ValueError): replica.plans('final', protocol=p)
            for field, value in [('seedNamespace', BASE['seedNamespace']), ('residualBound', 8), ('transferMaps', ['Italy'])]:
                with self.assertRaises(ValueError): replica.plans('train', 1, protocol=dict(p, **{field:value}))
            old = rollout.plans('confirmation')[0]
            with self.assertRaises(ValueError): replica.validate_tasks([old], 'train', True, p)
            other = Replica(3-r); task = other.plans('train', 1, protocol=other.protocol)[0]
            with self.assertRaises(ValueError): replica.validate_tasks([task], 'train', True, p)
        self.assertEqual(trainer.make_protocol(), BASE)

    def test_bridge_is_byte_identical_except_protocol_binding(self):
        old = (HERE / 'expert_game.cjs').read_bytes()
        new = (HERE / 'replica_game_v1.cjs').read_bytes()
        self.assertEqual(new, old.replace(b"const protocol = require('./expert-protocol-v2.json');",
                                         b"const protocol = require('./replica_protocol_v1.cjs')(process.argv[2]);"))
        for name, sha in STUDY['frozenSources'].items(): self.assertEqual(digest(HERE/name), sha)

    def test_javascript_scope_and_python_protocol_agree(self):
        for r in (1, 2):
            replica = Replica(r)
            tasks = []
            for smoke in (False, True):
                schedule = [('warmup', 0), ('selection', 0), ('confirmation', 0)]
                schedule += [('train', update) for update in range(1, 33)]
                for split, update in schedule:
                    planned = replica.plans(split, update, smoke=smoke, protocol=replica.protocol)
                    mode = split if split in ('warmup', 'train') else 'evaluation'
                    replica.validate_tasks(planned, mode, mode != 'evaluation', replica.protocol)
                    tasks.extend(planned)
            production = [s for s in tasks if not s['smoke']]
            self.assertEqual(len(production), 160 + 2560 + 320 + 640)
            self.assertEqual(len({json.dumps(s, sort_keys=True) for s in tasks}), len(tasks))
            self.assertEqual({s['map'] for s in production}, set(BASE['trainMaps']))
            self.assertEqual({s['players'] for s in production}, {2, 3, 4, 5, 6})
            self.assertEqual({(s['variant'], s['fastBid']) for s in production},
                             set(itertools.product(BASE['variants'], BASE['fastBids'])))
            code = """process.argv[2]=process.argv[1]; const g=require('./ai/multimap/replica_game_v1.cjs');
const assert=require('node:assert/strict');
const tasks=JSON.parse(require('fs').readFileSync(0,'utf8'));
const other='pg-multimap-expert-replicas-v1-r'+(3-Number(process.argv[2]));
for(const s of tasks){
    g.validateSpec(s);
    if(['selection','confirmation'].includes(s.split))g.validateSpec({...s,focalTeacher:true});
    for(const bad of [
        {...s,seed:s.seed.replace(g.protocol.seedNamespace,other)},
        {...s,seed:s.seed.replace(g.protocol.seedNamespace,'pg-multimap-expert-ppo-20261102-v2')},
        {...s,seed:'pg-multimap-final:'+s.seed},
        {...s,map:'Italy'}, {...s,map:'Benelux'}, {...s,split:'final'},
        {...s,smoke:Number(s.smoke)}, {...s,players:String(s.players)},
        {...s,fastBid:Number(s.fastBid)}, {...s,focalTeacher:1}
    ]) assert.throws(()=>g.validateSpec(bad));
}
console.log(JSON.stringify({protocol:g.protocol,accepted:tasks.length}));"""
            result = json.loads(subprocess.check_output(['node', '-e', code, str(r)],
                                input=json.dumps(tasks), text=True, cwd=ROOT, timeout=60))
            self.assertEqual(result['protocol'], replica.protocol)
            self.assertEqual(result['accepted'], len(tasks))

    def test_config_preserves_original_checks_and_binds_replica_sources(self):
        replica = Replica(1)
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(trainer, 'verify_artifact', return_value={'present':1}), \
             mock.patch.object(trainer, 'runtime_versions', return_value={'stub':True}), \
             mock.patch.object(trainer, 'engine_dependencies', return_value={}):
            path = Path(tmp); (path/'manifest.json').write_text('{}')
            identity = replica.config(True, replica.protocol, artifact=path, workers=6)
            self.assertEqual(identity['replica'], 1)
            self.assertEqual(identity['protocol'], replica.protocol)
            self.assertIn('ai/multimap/replica_game_v1.cjs', identity['sourceFiles'])
            self.assertIn('ai/multimap/expert_policy.py', identity['sourceFiles'])
            with self.assertRaises(ValueError): replica.config(True, BASE, artifact=path, workers=6)
            with mock.patch.object(trainer, 'MANIFEST_SHA', 'changed'):
                with self.assertRaisesRegex(ValueError, 'pins differ'):
                    replica.config(True, replica.protocol, artifact=path, workers=6)
        with self.assertRaises(ValueError):
            replica.plans('train', 1, protocol=dict(replica.protocol, selectionDealsPerCell=True))

    def test_all_source_hashes_participate_and_resume_drift_is_rejected(self):
        expected = {
            'expert-replicas-protocol-v1.json', 'expert_replicas_v1.py',
            'replica_game_v1.cjs', 'replica_protocol_v1.cjs', 'job_expert_replicas_v1.py',
            'test_expert_replicas_v1.py', 'launch_expert_replicas_v1.py',
            'test_launch_expert_replicas_v1.py', 'preflight_expert_replicas_v1.py',
            'test_preflight_expert_replicas_v1.py',
        }
        self.assertEqual(set(SOURCES), expected)
        self.assertEqual(len(SOURCES), len(expected))
        with tempfile.TemporaryDirectory() as tmp, ExitStack() as stack:
            root = Path(tmp); artifact = root/'artifact'; artifact.mkdir()
            atomic_json(artifact/'manifest.json', {})
            stack.enter_context(mock.patch.object(trainer, 'verify_artifact', return_value={'present': 1}))
            stack.enter_context(mock.patch.object(trainer, 'runtime_versions', return_value={'stub': True}))
            stack.enter_context(mock.patch.object(trainer, 'engine_dependencies', return_value={}))
            candidates = stack.enter_context(mock.patch.object(trainer, 'load_candidates', return_value={}))
            stack.enter_context(mock.patch.object(trainer, 'warm_start', side_effect=lambda p: ExpertPolicy(8)))
            stack.enter_context(mock.patch.dict(os.environ, {'EXPERT_WORKERS': '6'}))
            replica = Replica(1); replica.collect = synthetic_collect
            identity = replica.config(True, replica.protocol, artifact=artifact, workers=6)
            for name in SOURCES:
                self.assertEqual(identity['sourceFiles']['ai/multimap/' + name], digest(HERE/name))
            self.assertNotIn('ai/multimap/expert-replicas-preflight-v1.json', identity['sourceFiles'])
            self.assertIn('ai/multimap/job_neural.py', identity['sourceFiles'])
            self.assertIsNone(replica.run('mock', root/'out', True, stop_after=0, artifact=artifact))
            candidates.reset_mock()
            replica.collect = mock.Mock(side_effect=AssertionError('Collection before immutable resume check'))
            for name in SOURCES:
                def changed(path, target=HERE/name):
                    return '0'*64 if Path(path) == target else digest(path)
                with self.subTest(source=name), mock.patch.object(adapter, 'digest', side_effect=changed):
                    altered = replica.config(True, replica.protocol, artifact=artifact, workers=6)
                    self.assertNotEqual(altered, identity)
                    self.assertEqual(altered['sourceFiles']['ai/multimap/' + name], '0'*64)
                    with self.assertRaisesRegex(RuntimeError, 'mismatch'):
                        replica.run('mock', root/'out', True, artifact=artifact)
            with mock.patch.object(trainer, 'runtime_versions', return_value={'stub': 'drift'}):
                with self.assertRaisesRegex(RuntimeError, 'mismatch'):
                    replica.run('mock', root/'out', True, artifact=artifact)
            with mock.patch.dict(os.environ, {'EXPERT_WORKERS': '5'}):
                with self.assertRaisesRegex(RuntimeError, 'mismatch'):
                    replica.run('mock', root/'out', True, artifact=artifact)
            altered = copy.deepcopy(STUDY); altered['qualificationEligible'] = True
            atomic_json(root/'changed-protocol.json', altered)
            with mock.patch.object(adapter, 'PROTOCOL_PATH', root/'changed-protocol.json'):
                with self.assertRaises(ValueError):
                    replica.run('mock', root/'out', True, artifact=artifact)
            # A stale persisted protocol identity is rejected independently of
            # the live protocol and unchanged live source/runtime hashes.
            saved = json.loads((root/'out/config.json').read_text())
            saved['replicaStudy']['analysis']['winnerSelection'] = True
            atomic_json(root/'out/config.json', saved)
            with self.assertRaisesRegex(RuntimeError, 'mismatch'):
                replica.run('mock', root/'out', True, artifact=artifact)
            candidates.assert_not_called(); replica.collect.assert_not_called()

    def test_exact_resume_and_cross_replica_config_rejection(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(trainer, 'load_candidates', return_value={}), \
             mock.patch.object(trainer, 'warm_start', side_effect=lambda p: ExpertPolicy(8)):
            root = Path(tmp); replica = Replica(1)
            # Real model/optimizer/checkpoint transactions, synthetic compact games.
            replica.collect = synthetic_collect
            replica.config = lambda *a, **kw: {'replica':1}
            complete = replica.run('mock', root/'a', True)
            self.assertIsNone(replica.run('mock', root/'b', True, stop_after=1))
            (root/'b/best.pt').write_bytes(b'uncommitted candidate')
            self.assertEqual(replica.run('mock', root/'b', True), complete)
            _, a = load(root/'a/last.pt'); _, b = load(root/'b/last.pt')
            for key in ('state_dict', 'optimizer', 'torchRng', 'history', 'bestArtifact', 'bestSha256', 'result'):
                equal(self, a[key], b[key])
            replica.collect = mock.Mock(side_effect=AssertionError('Repeated committed collection'))
            self.assertEqual(replica.run('mock', root/'b', True), complete)
            other = Replica(2); other.config = lambda *a, **kw: {'replica':2}
            with self.assertRaisesRegex(RuntimeError, 'mismatch'): other.run('mock', root/'b', True)

    def test_confirmation_resume_only_advances_inherited_initialization_rng(self):
        class Interrupted(Exception):
            pass
        with tempfile.TemporaryDirectory() as tmp, \
             mock.patch.object(trainer, 'load_candidates', return_value={}), \
             mock.patch.object(trainer, 'warm_start', side_effect=lambda p: ExpertPolicy(8)):
            root = Path(tmp); replica = Replica(1)
            replica.config = lambda *a, **kw: {'replica': 1}
            replica.collect = synthetic_collect
            complete = replica.run('mock', root/'complete', True)
            _, expected = load(root/'complete/last.pt')
            for boundary in ('confirmation-selected', 'confirmation-teacher'):
                output = root/boundary
                def interrupt(label):
                    if label == boundary:
                        raise Interrupted()
                replica.collect = synthetic_collect
                with self.assertRaises(Interrupted):
                    replica.run('mock', output, True, callback=interrupt)
                _, paused = load(output/'last.pt')
                committed = set(paused['confirmations'])
                self.assertEqual(committed, {'selected'} if boundary.endswith('selected') else {'selected', 'teacher'})
                # Frozen run reloads best unconditionally, even after one/both
                # confirmations committed. Its constructor consumes exactly one
                # ExpertPolicy initialization; do NOT alter the frozen loader.
                torch.set_rng_state(paused['torchRng'])
                load(output/'best.pt')
                expected_rng = torch.get_rng_state().clone()
                calls = []
                def collect(*args, **kwargs):
                    calls.append(copy.deepcopy(args[1]))
                    return synthetic_collect(*args, **kwargs)
                replica.collect = collect
                with mock.patch.object(trainer, 'optimize', side_effect=AssertionError('Repeated PPO')) as ppo, \
                     mock.patch.object(trainer, 'warmup_optimize', side_effect=AssertionError('Repeated warmup')) as warmup:
                    self.assertEqual(replica.run('mock', output, True), complete)
                    ppo.assert_not_called(); warmup.assert_not_called()
                self.assertEqual(len(calls), 1 if boundary.endswith('selected') else 0)
                for tasks in calls:
                    self.assertTrue(all(s['split'] == 'confirmation' and s['focalTeacher'] is True for s in tasks))
                _, resumed = load(output/'last.pt')
                self.assertTrue(torch.equal(resumed['torchRng'], expected_rng))
                self.assertFalse(torch.equal(resumed['torchRng'], expected['torchRng']))
                # All training/optimizer/history/outcomes are unchanged. This
                # exception is initialization-only, AFTER training and selection;
                # update-boundary resumes retain the exact-RNG assertion above.
                self.assertEqual(set(expected), set(resumed))
                for key in set(expected) - {'torchRng'}:
                    equal(self, resumed[key], expected[key])
                for path in (root/'complete').glob('*.json'):
                    self.assertEqual(json.loads(path.read_text()), json.loads((output/path.name).read_text()))


class WorkerTests(unittest.TestCase):
    @staticmethod
    def environment(root, replica=1, segment=1):
        return dict(EXPERT_REPLICA=str(replica), REPLICA_SEGMENT=str(segment),
                    EXPERT_WORKERS='6', EXPERT_SMOKE='0', RUN_ID=f'group-r{replica}',
                    RUN_DIR=str(root/'run'), REFERENCE_CACHE=str(root/'ref'),
                    REFERENCE_VENV=str(root/'venv'), RESUME_CACHE=str(root/'resume'),
                    REPLICA_MODEL_CACHE=str(root/'models'), HF_HUB_CACHE=str(root/'models'),
                    MODEL_REPO=BASE['modelRepo'], DATASET_REPO='private-source',
                    SOURCE_REVISION='a'*40, SOURCE_SHA256='b'*64, SOURCE_PATH='source.tgz')

    def test_cache_is_set_before_transitive_import_only_for_executable(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = dict(os.environ, PYTHONPATH=str(HERE), HF_HUB_CACHE=str(Path(tmp)/'old'),
                       REPLICA_MODEL_CACHE=str(Path(tmp)/'models'), EXPERT_REPLICA='invalid')
            code = """import os
import job_expert_replicas_v1
print(os.environ['HF_HUB_CACHE'])
"""
            result = subprocess.check_output([sys.executable, '-B', '-c', code], env=env, text=True, cwd=ROOT)
            self.assertEqual(result.strip(), env['HF_HUB_CACHE'])
            code = """import runpy
try: runpy.run_module('job_expert_replicas_v1',run_name='__main__')
except RuntimeError: pass
from huggingface_hub.constants import HF_HUB_CACHE
print(HF_HUB_CACHE)
"""
            result = subprocess.check_output([sys.executable, '-B', '-c', code], env=env, text=True, cwd=ROOT)
            self.assertEqual(result.strip(), env['REPLICA_MODEL_CACHE'])

    def test_worker_scope_segments_private_bindings_and_fixed_error(self):
        old = (job_expert.compact_json, job_expert.compact_files, job_expert.run,
               copy.deepcopy(job_expert.PROTOCOL), set(job_expert.FORBIDDEN_JSON))
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for r in (1, 2):
                for segment in (1, 2):
                    env = self.environment(root, r, segment)
                    if segment == 2:
                        env.update(RUN_ID=f'group-continuation-r{r}', RESUME_RUN=f'group-r{r}', RESUME_REVISION='a'*40)
                    execute = mock.Mock(return_value='ok')
                    with mock.patch.dict(os.environ, env, clear=True), \
                         mock.patch('huggingface_hub.constants.HF_HUB_CACHE', env['HF_HUB_CACHE']), \
                         mock.patch.object(worker, 'bind', return_value=execute) as binding:
                        self.assertEqual(worker.run(), 'ok')
                        self.assertIs(binding.call_args.args[0], job_expert.run)
                        self.assertEqual(binding.call_args.kwargs['PROTOCOL'], protocol_for(r))
                        self.assertIs(binding.call_args.kwargs['compact_json'], worker.compact_json)
                        self.assertIs(binding.call_args.kwargs['compact_files'], worker.compact_files)
                        execute.assert_called_once_with()
                        execute.side_effect = ValueError('RAW_REQUEST_PACKET_DO_NOT_LOG')
                        with self.assertRaisesRegex(RuntimeError, '^Replica training stopped;') as error:
                            worker.run()
                        self.assertTrue(error.exception.__suppress_context__)
                        self.assertNotIn('RAW_REQUEST_PACKET', str(error.exception))
            bad = [dict(EXPERT_REPLICA='true'), dict(EXPERT_WORKERS='5'), dict(EXPERT_WORKERS='06'),
                   dict(EXPERT_SMOKE='1'), dict(REPLICA_SEGMENT='0'), dict(REPLICA_SEGMENT='3'),
                   dict(RUN_ID='group-r2'), dict(RUN_ID='group-continuation-r1'),
                   dict(RESUME_RUN='group-r1'), dict(RESUME_REVISION='a'*40),
                   dict(REPLICA_SEGMENT='2'),
                   dict(REPLICA_SEGMENT='2', RUN_ID='group-continuation-r1', RESUME_RUN='group-r2', RESUME_REVISION='a'*40),
                   dict(REPLICA_SEGMENT='2', RUN_ID='group-continuation-r1', RESUME_RUN='other-r1', RESUME_REVISION='a'*40),
                   dict(REPLICA_SEGMENT='2', RUN_ID='group-continuation-continuation-r1', RESUME_RUN='group-continuation-r1', RESUME_REVISION='a'*40),
                   dict(REPLICA_SEGMENT='2', RUN_ID='group-continuation-r1', RESUME_RUN='group-r1', RESUME_REVISION='main')]
            for patch in bad:
                env = dict(self.environment(root), **patch)
                with self.subTest(patch=patch), mock.patch.dict(os.environ, env, clear=True), \
                     mock.patch.object(worker, 'bind') as binding:
                    with self.assertRaises(RuntimeError): worker.run()
                    binding.assert_not_called()
        self.assertEqual(old, (job_expert.compact_json, job_expert.compact_files, job_expert.run,
                               job_expert.PROTOCOL, job_expert.FORBIDDEN_JSON))

    def test_every_cache_pair_must_be_separate_before_delegate_or_download(self):
        keys = ('RUN_DIR', 'REFERENCE_CACHE', 'REFERENCE_VENV', 'RESUME_CACHE', 'REPLICA_MODEL_CACHE')
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(worker, 'bind') as binding:
            root = Path(tmp)
            for first, second in itertools.combinations(keys, 2):
                for nested in ('', '/nested'):
                    env = self.environment(root); env[second] = env[first] + nested
                    with self.subTest(first=first, second=second, nested=nested), \
                         mock.patch.dict(os.environ, env, clear=True):
                        with self.assertRaisesRegex(ValueError, 'separate, nonnested'):
                            worker._run()
            env = self.environment(root)
            with mock.patch.dict(os.environ, env, clear=True), \
                 mock.patch('huggingface_hub.constants.HF_HUB_CACHE', str(root/'wrong')):
                with self.assertRaisesRegex(ValueError, 'dedicated startup cache'): worker._run()
            binding.assert_not_called()

    def test_strict_compact_json_and_private_artifact_binding(self):
        self.assertEqual(worker.FORBIDDEN_JSON,
                         job_expert.FORBIDDEN_JSON | {'response', 'state', 'move', 'rows', 'trajectory'})
        for key in worker.FORBIDDEN_JSON:
            for value in ([], {}, 'packet', 1):
                with self.subTest(key=key, value=value):
                    with self.assertRaises(ValueError): worker.compact_json({'nested': [{key: value}]})
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            atomic_json(root/'history.json', {})
            with self.assertRaises(ValueError): worker.compact_files(root)
            (root/'history.json').unlink(); (root/'expert').mkdir()
            # The frozen integer metric is not a raw row payload; bytes remain
            # unchanged, and booleans/structured values are never exempted.
            path = root/'expert/history.json'
            atomic_json(path, [{'optimization': {'rows': 12, 'optimizerSteps': 2}}])
            before = path.read_bytes()
            self.assertEqual(worker.compact_files(root), {'expert/history.json': digest(path)})
            self.assertEqual(path.read_bytes(), before)
            for value in ([], {}, True, -1, '12'):
                atomic_json(path, [{'optimization': {'rows': value}}])
                with self.assertRaises(ValueError): worker.compact_files(root)
            for key in worker.FORBIDDEN_JSON - {'rows'}:
                atomic_json(path, [{'optimization': {'rows': 12, key: 'packet'}}])
                with self.assertRaises(ValueError): worker.compact_files(root)
            atomic_json(path, [{'rows': 12}])
            with self.assertRaises(ValueError): worker.compact_files(root)

    def test_preserves_four_metadata_checks_and_single_original_test_discovery(self):
        with tempfile.TemporaryDirectory() as tmp, ExitStack() as stack:
            root = Path(tmp); env = self.environment(root)
            stack.enter_context(mock.patch.dict(os.environ, env, clear=True))
            stack.enter_context(mock.patch('huggingface_hub.constants.HF_HUB_CACHE', env['HF_HUB_CACHE']))
            api = stack.enter_context(mock.patch('huggingface_hub.HfApi')).return_value
            api.model_info.return_value.private = api.dataset_info.return_value.private = True
            api.upload_folder.return_value.oid = 'c'*40
            tests = stack.enter_context(mock.patch.object(job_expert.subprocess, 'run'))
            stack.enter_context(mock.patch.object(job_expert.shared, 'ensure_reference_environment', return_value=('python', {})))
            stack.enter_context(mock.patch.object(job_expert, 'recover_reference', return_value={}))
            events = []
            def size(repo, name, revision, **kwargs):
                events.append(('size', name)); return 1
            def download(repo, name, **kwargs):
                events.append(('download', name)); return root/'checkpoint.pt'
            stack.enter_context(mock.patch.object(job_expert.shared, 'remote_size', side_effect=size))
            stack.enter_context(mock.patch('huggingface_hub.hf_hub_download', side_effect=download))
            stack.enter_context(mock.patch.object(job_expert, 'digest', return_value=BASE['warmStart']['sha256']))
            replica = Replica(1); replica.run = mock.Mock(return_value={'qualified': False})
            stack.enter_context(mock.patch.object(worker, 'Replica', return_value=replica))
            worker.run()
            self.assertEqual([kind for kind, _ in events], ['size']*4 + ['download'])
            self.assertEqual([name for _, name in events[:4]],
                             [pin['path'] for pin in [BASE['warmStart'], *BASE['opponentPool']]])
            self.assertEqual(tests.call_count, 2)
            self.assertEqual(tests.call_args_list[1].args[0][-1], 'test_expert*.py')
            self.assertEqual(replica.run.call_args.kwargs['smoke'], False)
            status = json.loads((root/'run/status.json').read_text())
            self.assertEqual(status['workers'], 6)
            self.assertEqual(status['protocol'], protocol_for(1))


class IndependentPinTests(unittest.TestCase):
    def test_preimport_json_edits_fail_in_fresh_python_and_javascript_processes(self):
        cases = [('valid', copy.deepcopy(STUDY), None)]
        for key in CRITICAL_PROTOCOL:
            value = copy.deepcopy(STUDY); del value[key]
            cases.append(('missing-' + key, value, None))
        for key, replacement in [('schema', 'changed'), ('baseProtocol', 'protocol.json'),
                                  ('frozenSources', {}), ('frozenSources', None),
                                  ('transferMaps', ['Italy', 'Benelux']),
                                  ('qualificationEligible', True), ('reservedFinalSeedsUsed', True),
                                  ('qualificationEligible', 0), ('reservedFinalSeedsUsed', 0)]:
            value = copy.deepcopy(STUDY); value[key] = replacement
            cases.append(('changed-' + key + '-' + str(replacement), value, None))
        for name in FROZEN_SOURCES:
            value = copy.deepcopy(STUDY); del value['frozenSources'][name]
            cases.append(('removed-pin-' + name, value, None))
        value = copy.deepcopy(STUDY); value['frozenSources']['expert_ppo.py'] = '0'*64
        cases.append(('replaced-source-pin', value, None))
        for replica in (0, 1):
            for key, replacement in [('id', 3), ('id', str(replica + 1)),
                                      ('seed', 917), ('seedNamespace', BASE['seedNamespace'])]:
                value = copy.deepcopy(STUDY); value['replicas'][replica][key] = replacement
                cases.append((f'replica-{replica}-{key}-{replacement}', value, None))
        value = copy.deepcopy(STUDY); value['replicas'][0]['id'] = True
        cases.append(('boolean-replica-id', value, None))
        value = copy.deepcopy(STUDY); value['replicas'].reverse()
        cases.append(('replicas-swapped', value, None))
        for section in ('budget', 'counts', 'analysis'):
            for key, old in STUDY[section].items():
                replacement = not old if type(old) is bool else old + 1 if type(old) in (int, float) else 'changed'
                value = copy.deepcopy(STUDY); value[section][key] = replacement
                cases.append((section + '-' + key, value, None))
        for section, key, replacement in [('budget', 'workers', '6'), ('budget', 'replicas', True),
                                           ('analysis', 'winnerSelection', 0), ('analysis', 'pooledInference', 0)]:
            value = copy.deepcopy(STUDY); value[section][key] = replacement
            cases.append(('coercion-' + section + '-' + key, value, None))
        # Even a rewritten frozen protocol plus a matching attacker-supplied
        # hash must not establish a new baseline at import in either runtime.
        altered_base = copy.deepcopy(BASE)
        altered_base.update(priorFloor=-8, residualBound=8, learningRate=.01,
                            transferMaps=['Italy'], qualificationEligible=True)
        cases.append(('changed-base-bytes', copy.deepcopy(STUDY), altered_base))
        value = copy.deepcopy(STUDY)
        value['frozenSources']['expert-protocol-v2.json'] = __import__('hashlib').sha256(
            json.dumps(altered_base).encode()).hexdigest()
        cases.append(('rewritten-base-and-pin', value, altered_base))
        python = """try:
 import expert_replicas_v1 as replica
 for r in (1,2): replica.protocol_for(r)
except ValueError:
 print('REJECTED')
else:
 print('ACCEPTED')
"""
        javascript = """try {const p=require(process.argv[1]);p('1');p('2');console.log('ACCEPTED');}
catch(error){console.log('REJECTED');}"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for index, (_, value, base) in enumerate(cases):
                folder = root/str(index); folder.mkdir()
                for name in set(FROZEN_SOURCES) | {'expert_replicas_v1.py', 'replica_game_v1.cjs', 'replica_protocol_v1.cjs'}:
                    shutil.copyfile(HERE/name, folder/name)
                (folder/'expert-replicas-protocol-v1.json').write_text(json.dumps(value))
                if base is not None:
                    (folder/'expert-protocol-v2.json').write_text(json.dumps(base))

            def examine(index):
                folder = root/str(index)
                environment = dict(os.environ, PYTHONPATH=str(folder) + os.pathsep + str(HERE),
                                   PYTHONDONTWRITEBYTECODE='1', OMP_NUM_THREADS='1',
                                   MKL_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1')
                commands = [[sys.executable, '-B', '-c', python],
                            ['node', '-e', javascript, str(folder/'replica_protocol_v1.cjs')]]
                return [subprocess.run(command, cwd=ROOT, env=environment, text=True,
                                       capture_output=True, timeout=60) for command in commands]

            # Separate interpreter/module caches for every edited JSON; no
            # mutation of workspace files and no downloads or game processes.
            with ThreadPoolExecutor(max_workers=2) as pool:
                for (name, _, _), processes in zip(cases, pool.map(examine, range(len(cases)))):
                    expected = 'ACCEPTED' if name == 'valid' else 'REJECTED'
                    for language, process in zip(('Python', 'JavaScript'), processes):
                        with self.subTest(case=name, language=language):
                            self.assertEqual(process.returncode, 0, process.stderr)
                            self.assertEqual(process.stdout.strip(), expected, process.stderr)


if __name__ == '__main__': unittest.main()
