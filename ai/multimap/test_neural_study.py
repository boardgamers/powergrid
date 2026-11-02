"""Pure offline tests: synthetic outcomes and mock services, never an old-neural game."""
from collections import Counter, defaultdict
import copy
import json
import math
from pathlib import Path
import signal
import tempfile
import types
import unittest
from unittest import mock

import neural_study as study
import job_neural as job

SHA = 'a' * 64


def outcome(task, credit=None):
    """Synthetic bookkeeping fixture, NOT a played game or empirical result."""
    n, seat = task['spec']['players'], task['spec']['focalSeat']
    if task['policy'] == 'reference':
        vector = [1.0] + [0.0] * (n - 1)
    else:
        credit = .4 if credit is None else credit
        vector = [(1 - credit) / (n - 1)] * n
        vector[seat] = credit
    ppo = task['policy'] in study.CANDIDATES
    fixed = task['policy'] == 'teacher'
    return dict(schema=study.OUTCOME_SCHEMA, identitySha256=SHA, **copy.deepcopy(task),
        terminal=True, credit=vector[seat], allSeatCredit=vector, steps=1 + int(ppo) + int(fixed),
        rounds=1, decisions=dict(ppo=int(ppo), reference=1),
        counts=dict(ppo={'Auction': 1} if ppo else {}, reference={'Building': 1},
                    fixed={'Resources': 1} if fixed else {}), hiddenChecks=1, seconds=.01)


def failure(task):
    return dict(schema=study.OUTCOME_SCHEMA, identitySha256=SHA, **copy.deepcopy(task),
                terminal=False, credit=0.0, decisions=dict(ppo=0, reference=0), seconds=.01,
                error=dict(type='TimeoutError', code='response-timeout'))


class PlanTests(unittest.TestCase):
    def test_exact_balance_and_pairing(self):
        tasks = study.plan()
        self.assertEqual(len(tasks), 1920)
        self.assertEqual(len({study.key(t) for t in tasks}), 1920)
        self.assertEqual(Counter(t['policy'] for t in tasks), dict.fromkeys(study.PROTOCOL['policies'], 320))
        self.assertEqual(len({t['spec']['cell'] for t in tasks}), 20)
        self.assertEqual(len({t['spec']['seed'] for t in tasks}), 80)
        by_cell = defaultdict(set)
        by_deal = defaultdict(list)
        for task in tasks:
            s = task['spec']
            by_cell[s['cell']].add(s['seed'])
            by_deal[s['seed']].append(task)
            self.assertEqual(s['map'], 'Germany')
            self.assertEqual(s['maxSteps'], 4000)
            self.assertEqual(s['focalPolicy'], 'selected' if task['policy'] in study.CANDIDATES else task['policy'])
        self.assertEqual({len(v) for v in by_cell.values()}, {4})
        for values in by_deal.values():
            n = values[0]['spec']['players']
            self.assertEqual(len(values), n * 6)
            self.assertEqual({t['spec']['focalSeat'] for t in values}, set(range(n)))
            for policy in study.PROTOCOL['policies']:
                self.assertEqual(sum(t['policy'] == policy for t in values), n)

    def test_fresh_and_smoke_namespaces(self):
        tasks, smoke = study.plan(), study.plan(True)
        self.assertEqual(len(smoke), 12)
        self.assertFalse({t['spec']['seed'] for t in tasks} & {t['spec']['seed'] for t in smoke})
        self.assertTrue(all(t['spec']['seed'].startswith('pg-multimap-neural-screen-20261102-v1:') for t in tasks))
        previous = ['pg-multimap-reference-preflight-v1']
        for name in ('protocol.json', 'ppo-protocol-v1.json', 'opponent-study-v1.json'):
            protocol = json.loads((study.HERE / name).read_text())
            previous.extend(protocol[k] for k in ('seedNamespace', 'finalSeedNamespace') if k in protocol)
        for task in tasks + smoke:
            self.assertFalse(any(task['spec']['seed'].startswith(p + ':') for p in previous))
            self.assertNotIn('final', task['spec']['seed'])
        self.assertFalse(study.PROTOCOL['fitting'])
        self.assertFalse(study.PROTOCOL['selection'])
        self.assertFalse(study.PROTOCOL['qualificationEligible'])

    def test_pins_reference_and_every_candidate(self):
        pool = study.validate_protocol()
        self.assertEqual({m['name']: m['update'] for m in pool['members']}, {'ppo0': 8, 'ppo1': 16, 'ppo2': 12})
        self.assertEqual(pool['ensemble']['weights'], [1, 1, 1])
        self.assertEqual(study.PROTOCOL['reference']['runtimeManifestSha256'],
                         'fc135130689140b6fd72a76e6e14c59a7fea59717b858d330bac0c7f6aad93df')
        self.assertEqual(study.PROTOCOL['reference']['policySha256'],
                         '3b492c71ac5653ac7c41dfefd1c397e74e14df6f57629a455c61c8e45f55f52a')
        self.assertEqual(study.PROTOCOL['reference']['engineRelease'], '2.0.19')
        self.assertEqual(study.PROTOCOL['authoritativeEngineRelease'], '2.0.22')
        self.assertTrue(study.PROTOCOL['reference']['allPhases'])
        self.assertEqual(study.PROTOCOL['workers'], 6)
        self.assertEqual(study.PROTOCOL['uploadEveryGames'], 120)
        with mock.patch.dict(study.PROTOCOL, candidatePoolSha256='0' * 64):
            with self.assertRaisesRegex(ValueError, 'candidate pool'):
                study.validate_protocol()
        with mock.patch.dict(study.PINS, model=dict(study.PINS['model'], sha256='0' * 64)):
            with self.assertRaisesRegex(ValueError, 'reference identity'):
                study.validate_protocol()

    def test_actual_worker_count_is_part_of_identity(self):
        one = study.identity(True, versions={'offline': True}, workers=1)
        six = study.identity(True, versions={'offline': True}, workers=6)
        self.assertNotEqual(study.object_sha(one), study.object_sha(six))
        self.assertEqual(one['tasks'], six['tasks'])
        self.assertIn('ai/multimap/reference_game.cjs', one['sourceFiles'])
        self.assertIn('ai/multimap/reference_recover.py', one['sourceFiles'])
        self.assertIn('ai/requirements-serve.txt', one['sourceFiles'])
        for count in (0, 7, True):
            with self.assertRaisesRegex(ValueError, '1..6'):
                study.run('unused', workers=count)


class CreditTests(unittest.TestCase):
    def test_all_six_and_correct_independent_deal_denominators(self):
        tasks = study.plan()
        records = [outcome(t) for t in tasks]
        for record, task in zip(records, tasks):
            study.validate_record(record, task, SHA)
        summary = study.summarize(records, tasks)
        self.assertEqual(summary['games'], 1920)
        self.assertEqual(summary['independentDeals'], 80)
        self.assertEqual(len(summary['cells']), 120)
        self.assertEqual(set(summary['policies']), set(study.PROTOCOL['policies']))
        self.assertFalse(summary['qualified'])
        self.assertFalse(summary['qualification_eligible'])
        self.assertFalse(summary['baselineViolations'])
        self.assertEqual(len(summary['allReferenceControl']), 80)
        self.assertTrue(all(x['passed'] and x['focalCreditSum'] == 1 for x in summary['allReferenceControl']))
        self.assertAlmostEqual(summary['policies']['reference']['gameMeanCredit'], .25)
        self.assertAlmostEqual(summary['policies']['reference']['macroCellCredit'], .29)
        ppo = summary['policies']['ppo0']
        self.assertEqual(ppo['games'], 320)
        self.assertAlmostEqual(ppo['macroCellCredit'], .4)
        self.assertAlmostEqual(ppo['pairedDealDifferences']['reference']['mean'], .11)
        self.assertEqual(ppo['pairedDealDifferences']['reference']['independentDeals'], 80)
        self.assertEqual(ppo['pairedDealDifferences']['teacher']['mean'], 0)
        self.assertEqual(ppo['pairedDealDifferences']['teacher']['dealStandardError'], 0)
        self.assertTrue(all(c['independentDeals'] == 4 for c in summary['cells']))

    def test_failed_game_is_zero_in_denominator_not_terminal_reward(self):
        tasks = study.plan()
        records = [outcome(t) for t in tasks]
        records[0] = failure(tasks[0])
        study.validate_record(records[0], tasks[0], SHA)
        summary = study.summarize(records, tasks)
        self.assertEqual(summary['failures'], 1)
        self.assertTrue(summary['qualificationStopped'])
        self.assertEqual(summary['policies']['ppo0']['games'], 320)
        self.assertAlmostEqual(summary['policies']['ppo0']['gameMeanCredit'], .4 * 319 / 320)
        self.assertEqual(summary['policies']['ppo0']['pairedDealDifferences']['reference']['independentDeals'], 80)
        self.assertNotIn('allSeatCredit', records[0])
        self.assertNotIn('steps', records[0])

    def test_baseline_inconsistency_and_partial_coverage(self):
        tasks = study.plan(True)
        records = [outcome(t) for t in tasks]
        record = next(r for r in records if r['policy'] == 'reference')
        record['allSeatCredit'] = [0., 1.]
        record['credit'] = record['allSeatCredit'][record['spec']['focalSeat']]
        report = study.summarize(records, tasks)
        self.assertEqual(len(report['baselineViolations']), 1)
        self.assertTrue(report['qualificationStopped'])
        report = study.summarize(records[:1], tasks)
        self.assertFalse(report['complete'])
        self.assertEqual(len(report['policies']), 6)
        self.assertIsNone(report['policies']['ppo0']['macroCellCredit'])
        self.assertEqual(report['policies']['reference']['games'], 0)
        self.assertEqual(report['plannedGames'], 12)
        self.assertEqual(report['plannedIndependentDeals'], 1)


class ResumeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.tasks = study.plan(True)
        self.path = self.directory / 'games.jsonl'

    def test_partial_last_line_recovered_and_duplicate_rejected(self):
        record = outcome(self.tasks[0])
        line = study.canonical(record) + '\n'
        self.path.write_text(line + '{"spec":')
        records, seen = study.read_existing(self.path, self.tasks, SHA)
        self.assertEqual(records, [record])
        self.assertEqual(seen, {study.key(record)})
        self.assertEqual(self.path.read_text(), line)
        self.path.write_text(line + line)
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            study.read_existing(self.path, self.tasks, SHA)
        self.path.write_text(line + '{bad-json}\n')
        with self.assertRaises(ValueError):
            study.read_existing(self.path, self.tasks, SHA)
        self.assertTrue(self.path.read_text().endswith('{bad-json}\n'))

    def test_full_identity_guard_including_sources_environment_pins_and_workers(self):
        frozen = study.identity(True, versions={'offline': True})
        sha = study.prepare_output(self.directory, frozen)
        self.assertEqual(sha, study.object_sha(frozen))
        self.assertEqual(study.prepare_output(self.directory, frozen), sha)
        for field in ('protocol', 'candidatePool', 'tasks', 'generatorDigest', 'sourceFiles', 'runtimeVersions', 'execution'):
            changed = copy.deepcopy(frozen)
            changed[field] = 'changed'
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'identity'):
                study.prepare_output(self.directory, changed)
        (self.directory / 'plan.json').unlink()
        self.path.write_text('')
        with self.assertRaisesRegex(ValueError, 'without'):
            study.prepare_output(self.directory, frozen)

    def test_outcome_validation_rejects_tampering_and_no_hidden_states(self):
        good = outcome(self.tasks[0])
        invalid = [dict(good, identitySha256='b' * 64), dict(good, credit=float('nan')),
                   dict(good, credit=-1), dict(good, credit=1.01), dict(good, observation={}),
                   dict(good, terminal=False), dict(good, spec=dict(good['spec'], maxSteps=2)),
                   dict(good, spec=dict(good['spec'], fastBid=0)),
                   dict(good, allSeatCredit=[0, 0]), dict(good, steps=4001),
                   dict(good, hiddenChecks=0), dict(good, counts={'ppo': {}, 'reference': {}, 'fixed': {}})]
        for bad in invalid:
            with self.subTest(fields=bad.keys()), self.assertRaises(ValueError):
                study.validate_record(bad, self.tasks[0], SHA)
        bad = failure(self.tasks[0]); bad['credit'] = .5
        with self.assertRaises(ValueError):
            study.validate_record(bad, self.tasks[0], SHA)
        self.path.write_text('x' * (study.MAX_LINE + 1))
        with self.assertRaisesRegex(ValueError, 'Oversized'):
            study.read_existing(self.path, self.tasks, SHA)

    def test_failures_remain_committed_and_budget_is_enforced(self):
        self.path.write_text(study.canonical(failure(self.tasks[0])) + '\n')
        records, done = study.read_existing(self.path, self.tasks, SHA)
        self.assertEqual(done, {study.key(self.tasks[0])})
        self.assertFalse(records[0]['terminal'])
        with mock.patch.dict(study.PROTOCOL, studyArtifactMaxBytes=1):
            with self.assertRaisesRegex(ValueError, 'budget'):
                study.artifact_budget(self.directory)
        (self.directory / 'link').symlink_to(self.path)
        with self.assertRaisesRegex(ValueError, 'symlink'):
            study.artifact_budget(self.directory)


class MockLoopTests(unittest.TestCase):
    def mock_bridge(self, task, *, reference_phases=('Resources', 'Powering')):
        seat = task['spec']['focalSeat']
        actor = seat if task['policy'] == 'reference' else 1 - seat
        requests = [dict(requestId=str(i), revision=i, player=actor,
                         state=dict(seed='secret', powerPlantsDeck=[], hiddenLog=[])) for i, _ in enumerate(reference_phases)]
        views = [dict(terminal=False, kind='reference', phase=p, request=r) for p, r in zip(reference_phases, requests)]
        ppo = task['policy'] in study.CANDIDATES
        if ppo:
            views.insert(1, dict(terminal=False, kind='ppo', phase='Auction', observation={'public': True}))
        final = outcome(task)
        final['counts']['reference'] = dict(Counter(reference_phases))
        final['hiddenChecks'] = len(reference_phases)
        final['steps'] = len(reference_phases) + int(ppo) + int(task['policy'] == 'teacher')
        views.append({k: final[k] for k in ('terminal', 'steps', 'rounds', 'counts', 'hiddenChecks') } | {'credit': final['allSeatCredit']})
        bridge = mock.Mock()
        bridge.call.side_effect = views
        reference = mock.Mock()
        reference.decide.side_effect = lambda r: dict(requestId=r['requestId'], revision=r['revision'], move={'type': 'mock'})
        return bridge, reference, requests

    def test_each_candidate_routes_indices_and_reference_moves_without_state_storage(self):
        for policy in study.CANDIDATES:
            task = next(t for t in study.plan(True) if t['policy'] == policy)
            bridge, reference, requests = self.mock_bridge(task)
            models = {p: object() for p in study.CANDIDATES}
            choose = mock.Mock(return_value=2)
            record = study.play_game(task, bridge, reference, models, SHA, choose)
            self.assertTrue(record['terminal'], record)
            study.validate_record(record, task, SHA)
            self.assertEqual(reference.decide.call_args_list, [mock.call(r) for r in requests])
            choose.assert_called_once_with(models[policy], {'public': True})
            calls = [c.args[0] for c in bridge.call.call_args_list]
            self.assertEqual(calls[0], dict(op='start', spec=task['spec']))
            self.assertEqual(sum('index' in c for c in calls), 1)
            self.assertEqual(sum('response' in c for c in calls), 2)
            self.assertNotIn('observation', record)
            self.assertNotIn('request', record)
            bridge.close.assert_not_called()  # persistent worker, not per-game processes
            reference.close.assert_not_called()

    def test_reference_controls_every_phase_and_teacher_never_uses_model(self):
        for policy in ('teacher', 'reference'):
            task = next(t for t in study.plan(True) if t['policy'] == policy)
            phases = ('Setup', 'Auction', 'Resources', 'Building', 'Powering')
            bridge, reference, requests = self.mock_bridge(task, reference_phases=phases)
            choose = mock.Mock(side_effect=AssertionError('Control must not use PPO'))
            record = study.play_game(task, bridge, reference, {}, SHA, choose)
            self.assertTrue(record['terminal'], record)
            self.assertEqual(reference.decide.call_count, 5)
            self.assertEqual(record['decisions']['ppo'], 0)
            choose.assert_not_called()
            self.assertFalse(any('index' in c.args[0] for c in bridge.call.call_args_list))

    def test_cap_and_bad_actor_fail_explicitly_without_fabricated_terminal_reward(self):
        task = study.plan(True)[0]
        bridge, reference, _ = self.mock_bridge(task)
        bridge.call.side_effect = RuntimeError('Reference game capped; private secret must not be serialized')
        record = study.play_game(task, bridge, reference, {}, SHA)
        self.assertFalse(record['terminal'])
        self.assertEqual(record['credit'], 0)
        self.assertEqual(record['error']['code'], 'nonterminal-cap')
        self.assertNotIn('private secret', json.dumps(record))
        self.assertNotIn('allSeatCredit', record)
        study.validate_record(record, task, SHA)
        teacher = next(t for t in study.plan(True) if t['policy'] == 'teacher')
        bridge.call.side_effect = [dict(terminal=False, kind='ppo', observation={})]
        record = study.play_game(teacher, bridge, reference, {}, SHA)
        self.assertFalse(record['terminal'])
        reference.decide.assert_not_called()

    def test_terminal_credit_is_validated_not_repaired(self):
        task = study.plan(True)[0]
        bridge, reference, _ = self.mock_bridge(task)
        terminal = dict(terminal=True, credit=[0, 0], steps=1, rounds=1,
                        counts={'ppo': {}, 'reference': {}, 'fixed': {'Setup': 1}}, hiddenChecks=0)
        bridge.call.side_effect = [terminal]
        record = study.play_game(task, bridge, reference, {}, SHA)
        self.assertFalse(record['terminal'])
        self.assertEqual(record['credit'], 0)
        self.assertNotIn('steps', record)

    def test_persistent_worker_loads_all_models_once_and_closes_on_error(self):
        fake_reference = types.SimpleNamespace(close=mock.Mock())
        fake_bridge = types.SimpleNamespace(close=mock.Mock())
        models = dict.fromkeys(study.CANDIDATES, object())
        with mock.patch('candidates.load_candidates', return_value=models) as load, \
                mock.patch('torch.set_num_interop_threads'), \
                mock.patch.object(study, 'ReferenceProcess', return_value=fake_reference) as reference, \
                mock.patch.object(study, 'LineProcess', return_value=fake_bridge):
            runtime = study.WorkerRuntime('fixture-artifact', 'fixture-python')
            self.assertEqual(set(runtime.models), set(study.CANDIDATES))
            load.assert_called_once_with(list(study.CANDIDATES))
            reference.assert_called_once_with('fixture-artifact', 'fixture-python')  # verify defaults to true
            runtime.close(); runtime.close()
            fake_bridge.close.assert_called_once()
            fake_reference.close.assert_called_once()
        fake_reference.close.reset_mock()
        with mock.patch('candidates.load_candidates', return_value=models), \
                mock.patch('torch.set_num_interop_threads'), \
                mock.patch.object(study, 'ReferenceProcess', return_value=fake_reference), \
                mock.patch.object(study, 'LineProcess', side_effect=RuntimeError('mock startup failure')):
            with self.assertRaisesRegex(RuntimeError, 'startup'):
                study.WorkerRuntime('fixture-artifact', 'fixture-python')
            fake_reference.close.assert_called_once()

    def test_worker_finally_cleanup_on_done_and_failed_game(self):
        task = study.plan(True)[0]
        for result in (outcome(task), failure(task)):
            runtime = types.SimpleNamespace(bridge=object(), reference=object(), models={}, close=mock.Mock())
            incoming, outgoing = mock.Mock(), mock.Mock()
            incoming.get.side_effect = [task, None]
            with mock.patch.object(study, 'WorkerRuntime', return_value=runtime), \
                    mock.patch.object(study, 'play_game', return_value=result), mock.patch.object(study.signal, 'signal'):
                study.worker_main(incoming, outgoing, 'artifact', 'python', SHA)
            runtime.close.assert_called_once()
            outgoing.put.assert_called_once_with(('outcome', result))

    def test_dedicated_process_group_killed_even_if_leader_already_exited(self):
        process = types.SimpleNamespace(process=types.SimpleNamespace(pid=123456), close=mock.Mock())
        with mock.patch.object(study.os, 'killpg') as kill:
            study.close_process(process)
        self.assertEqual(kill.call_args_list, [mock.call(123456, signal.SIGTERM), mock.call(123456, signal.SIGKILL)])
        process.close.assert_called_once()


class CoordinatorTests(unittest.TestCase):
    """Exercise the collector with synthetic processes/queues, no services started."""
    class Context:
        def __init__(self, failing=False):
            self.children = []
            self.results = []
            self.failing = failing
            self.queued = 0
            self.queue_count = 0

        def Queue(self, maxsize):
            self.queue_count += 1
            context = self
            incoming = self.queue_count == 1
            class FakeQueue:
                def put(self, task):
                    if task is None:
                        next(c for c in context.children if c.alive).alive = False
                        return
                    context.queued += 1
                    record = failure(task) if context.failing and context.queued == 1 else outcome(task)
                    record['identitySha256'] = context.identity_sha
                    context.results.append(('outcome', record))

                def get(self, timeout=None):
                    if incoming:
                        raise AssertionError('Mock workers are not actually started')
                    return context.results.pop(0)

                def close(self):
                    pass

                def cancel_join_thread(self):
                    pass
            return FakeQueue()

        def Process(self, target, args, name):
            self.identity_sha = args[-1]
            class FakeProcess:
                alive = False
                pid = 1

                @property
                def exitcode(self):
                    return None if self.alive else 0

                def start(self):
                    self.alive = True

                def is_alive(self):
                    return self.alive

                def terminate(self):
                    self.alive = False

                def kill(self):
                    self.alive = False

                def join(self, timeout):
                    pass
            child = FakeProcess()
            self.children.append(child)
            return child

    def test_complete_resume_skips_workers_and_recovers_partial_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            context = self.Context()
            with mock.patch.object(study.multiprocessing, 'get_context', return_value=context) as spawn, \
                    mock.patch.object(study, 'runtime_versions', return_value={'offline': True}), \
                    mock.patch.object(study, 'budget'), mock.patch('builtins.print'):
                callback = mock.Mock()
                report = study.run(root / 'study', artifact=root / 'reference/artifact',
                                   workers=2, smoke=True, callback=callback)
                self.assertTrue(report['complete'])
                self.assertEqual(report['games'], 12)
                spawn.assert_called_once_with('spawn')
                self.assertEqual(context.queued, 12)
                self.assertTrue(all(not c.alive for c in context.children))
                path = root / 'study/games.jsonl'
                with path.open('a') as file:
                    file.write('{"partial":')
                repeated = study.run(root / 'study', artifact=root / 'reference/artifact', workers=2, smoke=True)
                self.assertTrue(repeated['complete'])
                self.assertEqual(context.queued, 12)
                self.assertTrue(path.read_bytes().endswith(b'\n'))
                self.assertEqual(callback.call_args_list, [mock.call('planned'), mock.call('games-12'), mock.call('screen-complete')])
                with self.assertRaisesRegex(ValueError, 'identity'):
                    study.run(root / 'study', artifact=root / 'reference/artifact', workers=3, smoke=True)

    def test_failure_snapshot_and_immutable_no_retry(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            context = self.Context(failing=True)
            with mock.patch.object(study.multiprocessing, 'get_context', return_value=context), \
                    mock.patch.object(study, 'runtime_versions', return_value={'offline': True}), \
                    mock.patch.object(study, 'budget'), mock.patch('builtins.print'):
                with self.assertRaisesRegex(RuntimeError, 'explicit failures'):
                    study.run(root / 'study', artifact=root / 'reference/artifact', workers=2, smoke=True)
                report = json.loads((root / 'study/summary.json').read_text())
                self.assertEqual(report['failures'], 1)
                self.assertEqual(report['games'], 2)
                self.assertFalse(report['complete'])
                self.assertTrue(report['qualificationStopped'])
                self.assertTrue(all(not c.alive for c in context.children))
                with self.assertRaisesRegex(RuntimeError, 'Saved failures'):
                    study.run(root / 'study', artifact=root / 'reference/artifact', workers=2, smoke=True)
                self.assertEqual(context.queued, 2)


class JobTests(unittest.TestCase):
    def test_immutable_pin_and_whitelist_guards(self):
        for revision in ('main', 'a' * 39, 'g' * 40, '../escape'):
            with self.assertRaises(ValueError):
                job.immutable_revision(revision)
        self.assertEqual(job.immutable_revision('f' * 40), 'f' * 40)
        for name in ('../escape', '/absolute', 'a/b', ''):
            with self.assertRaises(ValueError):
                job.safe_run(name)
        manifest = {'study/plan.json': SHA, 'study/games.jsonl': SHA, 'status.json': SHA}
        self.assertEqual(set(job.validate_manifest(manifest)), {'study/plan.json', 'study/games.jsonl'})
        for name in ('../escape', '/study/plan.json', 'study/hidden.json', 'model.pt', 'artifact/fixtures/roots.jsonl'):
            with self.assertRaises(ValueError):
                job.validate_manifest(dict(manifest, **{name: SHA}))
        with self.assertRaises(ValueError):
            job.validate_manifest({'study/plan.json': 'wrong'})

    def test_no_bulky_uploads_or_nested_cache_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / 'status.json').write_text('{}\n')
            self.assertEqual(set(job.compact_files(base)), {'status.json'})
            (base / 'secret.pt').write_bytes(b'not a real checkpoint')
            with self.assertRaisesRegex(ValueError, 'bulky'):
                job.compact_files(base)
        with self.assertRaisesRegex(ValueError, 'separate'):
            job.separate_paths('/tmp/synthetic-output', '/tmp/synthetic-output/cache')
        job.separate_paths('/tmp/synthetic-output', '/tmp/synthetic-reference', '/tmp/synthetic-venv')

    def test_resume_hash_checks_before_restore_without_network(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'source'; source.mkdir()
            plan = source / 'plan.json'; plan.write_text('{}\n')
            games = source / 'games.jsonl'; games.write_text('{"synthetic":true}\n')
            manifest = source / 'artifacts.json'
            pins = {'study/plan.json': study.digest(plan), 'study/games.jsonl': study.digest(games)}
            manifest.write_text(json.dumps(pins))
            files = {'artifacts.json': manifest, 'study/plan.json': plan, 'study/games.jsonl': games}
            def download(repo, name, **kwargs):
                self.assertEqual(kwargs['revision'], 'f' * 40)
                return str(files[name.removeprefix('runs/previous/')])
            def size(repo, name, revision, **kwargs):
                return files[name.removeprefix('runs/previous/')].stat().st_size
            with mock.patch('huggingface_hub.hf_hub_download', side_effect=download), \
                    mock.patch.object(job, 'remote_size', side_effect=size):
                base = root / 'output'
                receipt = job.restore_resume('private/repo', 'previous', 'f' * 40, base, root / 'cache')
                self.assertEqual(receipt['files'], pins)
                self.assertEqual((base / 'study/plan.json').read_bytes(), plan.read_bytes())
                pins['study/games.jsonl'] = '0' * 64
                manifest.write_text(json.dumps(pins))
                with self.assertRaisesRegex(ValueError, 'hash/size'):
                    job.restore_resume('private/repo', 'previous', 'f' * 40, root / 'bad', root / 'cache')

    def test_remote_size_guard_and_separate_environment_versions(self):
        with mock.patch('huggingface_hub.get_hf_file_metadata') as metadata:
            metadata.return_value = types.SimpleNamespace(commit_hash='f' * 40, size=999)
            with self.assertRaisesRegex(ValueError, 'size/revision'):
                job.remote_size('private/repo', 'file', 'f' * 40, maximum=10)
            metadata.return_value = types.SimpleNamespace(commit_hash='e' * 40, size=1)
            with self.assertRaisesRegex(ValueError, 'size/revision'):
                job.remote_size('private/repo', 'file', 'f' * 40)
        reference = dict(python=[3, 12, 8], numpy='2.5.3', onnxruntime='1.30.0')
        with mock.patch.object(study.subprocess, 'check_output', side_effect=[json.dumps(reference), 'v22.15.0\n']):
            versions = study.runtime_versions('mock-reference-python')
            self.assertEqual(versions['candidate']['numpy'], '2.2.6')
            self.assertEqual(versions['reference']['numpy'], '2.5.3')
        reference['numpy'] = '2.2.6'
        with mock.patch.object(study.subprocess, 'check_output', return_value=json.dumps(reference)):
            with self.assertRaisesRegex(ValueError, 'reference environment'):
                study.runtime_versions('mock-reference-python')


if __name__ == '__main__':
    unittest.main()
