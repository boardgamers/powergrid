"""Offline synthetic bookkeeping tests. No exact service, network, or real study games."""
from collections import Counter, defaultdict
import copy
import json
from pathlib import Path
import pickle
import signal
import tempfile
import types
import unittest
from unittest import mock

import gap_study as study
import job_gap as job

SHA = 'a' * 64


def outcome(task):
    """Synthetic fixture, emphatically NOT a played game or empirical result."""
    spec = task['spec']
    vector = [1.] + [0.] * (spec['players'] - 1)
    counts = {k: dict.fromkeys(study.PHASES, 0) for k in study.ACTORS}
    phases, teacher_phases = {}, 0
    for phase in study.PHASES:
        teacher = study.controller(task['policy'], phase) == 'teacher'
        teacher_phases += teacher
        counts['focalTeacher' if teacher else 'focalReference'][phase] = 3
        counts['nonfocalReference'][phase] = 1
        phases[phase] = dict(multiActionDecisions=2, forcedMoves=1, teacherExpertAgreement=1,
            priorGapSum=20, priorGapMax=20, priorGapHistogram=[1, 0, 0, 0, 0, 0, 1],
            cannotOutscoreTeacherBestWithCurrentBound=1, exactFloor20=1)
    requests = 16 - teacher_phases
    return dict(schema=study.OUTCOME_SCHEMA, identitySha256=SHA, **copy.deepcopy(task),
        terminal=True, credit=vector[spec['focalSeat']], allSeatCredit=vector,
        steps=16, rounds=1, counts=counts, phaseCounters=phases,
        publicChecks=dict(hiddenInvariant=requests, expertAtomicLegal=requests, fullMenuPrior=8, teacherAtomicLegal=8),
        decisions=dict(referenceRequests=requests, counterfactualOnly=2 * teacher_phases), seconds=.01)


def failure(task):
    return dict(schema=study.OUTCOME_SCHEMA, identitySha256=SHA, **copy.deepcopy(task), terminal=False,
        credit=0., decisions=dict(referenceRequests=0, counterfactualOnly=0), seconds=.01,
        error=dict(type='TimeoutError', code='response-timeout'))


class PlanTests(unittest.TestCase):
    def test_exact_plan_pairing_and_disjoint_smoke(self):
        tasks, smoke = study.plan(), study.plan(True)
        self.assertEqual(len(tasks), 1600)
        self.assertEqual(len({study.key(t) for t in tasks}), 1600)
        self.assertEqual(Counter(t['policy'] for t in tasks), dict.fromkeys(study.PROTOCOL['policies'], 160))
        self.assertEqual(len({t['spec']['cell'] for t in tasks}), 20)
        self.assertEqual(len({t['spec']['seed'] for t in tasks}), 40)
        self.assertEqual(len(smoke), 20)
        self.assertEqual(len({t['spec']['seed'] for t in smoke}), 1)
        self.assertFalse({t['spec']['seed'] for t in smoke} & {t['spec']['seed'] for t in tasks})
        cells, deals = defaultdict(set), defaultdict(list)
        for task in tasks:
            s = task['spec']
            self.assertEqual(s['focalPolicy'], task['policy'])
            cells[s['cell']].add(s['seed'])
            deals[s['seed']].append(task)
        self.assertEqual({len(v) for v in cells.values()}, {2})
        for rows in deals.values():
            n = rows[0]['spec']['players']
            self.assertEqual(len(rows), 10 * n)
            self.assertEqual(Counter(t['policy'] for t in rows), dict.fromkeys(study.PROTOCOL['policies'], n))
            self.assertEqual({t['spec']['focalSeat'] for t in rows}, set(range(n)))
        previous = ['pg-multimap-reference-preflight-v1']
        for name in ('protocol.json', 'ppo-protocol-v1.json', 'neural-study-v1.json', 'opponent-study-v1.json'):
            p = json.loads((study.HERE / name).read_text())
            previous += [p[k] for k in ('seedNamespace', 'smokeNamespace', 'finalSeedNamespace') if k in p]
        self.assertTrue(all(not any(t['spec']['seed'].startswith(p + ':') for p in previous) for t in tasks + smoke))
        with self.assertRaises(ValueError):
            study.plan('smoke')

    def test_phase_routing_pins_and_guards(self):
        study.validate_protocol()
        for arm in study.PROTOCOL['policies']:
            for phase in study.PHASES:
                teacher = arm == 'teacher' or arm == f'reference-except-{phase}' or (
                    arm.startswith('teacher-except-') and arm != f'teacher-except-{phase}')
                self.assertEqual(study.controller(arm, phase), 'teacher' if teacher else 'reference')
        with self.assertRaises(ValueError):
            study.controller('ppo0', 'Auction')
        for name in ('fitting', 'selection', 'qualificationEligible', 'reservedFinalSeedsUsed'):
            self.assertFalse(study.PROTOCOL[name])
        with mock.patch.dict(study.PROTOCOL, dealsPerCell=4), self.assertRaises(ValueError):
            study.validate_protocol()
        with mock.patch.dict(study.PINS, model=dict(study.PINS['model'], sha256='0' * 64)), self.assertRaises(ValueError):
            study.validate_protocol()

    def test_source_and_worker_identity_no_old_module_mutations(self):
        original = dict(vars(study.shared))
        one = study.identity(True, versions={'offline': True}, workers=1)
        six = study.identity(True, versions={'offline': True}, workers=6)
        self.assertNotEqual(study.object_sha(one), study.object_sha(six))
        self.assertEqual(one['tasks'], six['tasks'])
        self.assertEqual(original, vars(study.shared))
        self.assertNotIn('candidatePool', one)
        self.assertFalse(one['execution']['torchInferenceUsed'])
        for name in ('gap-protocol-v1.json', 'gap_game.cjs', 'gap_study.py', 'job_gap.py', 'test_gap.py',
                     'test_gap.cjs', 'neural_study.py', 'job_neural.py', 'reference_game.cjs', 'game_rl.cjs',
                     'reference_recover.py', 'reference_evaluate.py', 'teacher.cjs', 'data.py'):
            self.assertIn('ai/multimap/' + name, one['sourceFiles'])
        self.assertIn('engine/dist/index.js', one['sourceFiles'])
        self.assertIn('ai/strong/economics.cjs', one['sourceFiles'])
        self.assertEqual(pickle.loads(pickle.dumps(study.worker_main)), study.worker_main)
        for n in (True, 0, 7):
            with self.assertRaisesRegex(ValueError, '1..6'):
                study.run('unused', workers=n)


class CounterTests(unittest.TestCase):
    def test_equal_credit_support_and_reference_terminal_counts(self):
        tasks = study.plan(True)
        records = [outcome(t) for t in tasks]
        bad = copy.deepcopy(records[0])
        bad.update(allSeatCredit=[.25, .75], credit=.25)
        with self.assertRaisesRegex(ValueError, 'share credit equally'):
            study.validate_record(bad, tasks[0], SHA)
        report = study.summarize(records, tasks)
        self.assertTrue(report['allReferenceControl'][0]['sameTerminalCounts'])
        records[-10]['rounds'] += 1  # Reference, other focal seat, identical credit vector.
        report = study.summarize(records, tasks)
        self.assertEqual(len(report['baselineViolations']), 1)
        self.assertTrue(report['qualificationStopped'])
        self.assertFalse(report['allReferenceControl'][0]['passed'])

    def test_terminal_counters_and_all_arms_summary(self):
        tasks = study.plan()
        records = [outcome(t) for t in tasks]
        for t, r in zip(tasks, records):
            study.validate_record(r, t, SHA)
        report = study.summarize(records, tasks)
        self.assertEqual(report['games'], 1600)
        self.assertEqual(report['plannedIndependentDeals'], 40)
        self.assertEqual(len(report['cells']), 200)
        self.assertEqual(set(report['policies']), set(study.PROTOCOL['policies']))
        self.assertEqual(len(report['allReferenceControl']), 40)
        self.assertFalse(report['baselineViolations'])
        self.assertAlmostEqual(report['policies']['reference']['macroCellCredit'], .29)
        self.assertAlmostEqual(report['policies']['reference']['gameMeanCredit'], .25)
        for phases in report['phaseDiagnostics'].values():
            for row in phases.values():
                self.assertEqual(row['multiActionDecisions'], 320)
                self.assertEqual(row['forcedMoves'], 160)
                self.assertEqual(row['agreementRate'], .5)
                self.assertEqual(row['meanPriorGap'], 10)
                self.assertEqual(row['exactFloor20'], 160)
        self.assertFalse(report['qualified'])
        self.assertFalse(report['fitted'])
        self.assertFalse(report['selected'])
        self.assertIn('exactly 16', report['priorBoundExplanation'])

    def test_counter_schema_tampering_and_zero_failure_not_reward(self):
        t = study.plan(True)[1]
        good = outcome(t)
        variants = [dict(good, identitySha256='b' * 64), dict(good, credit=float('nan')),
                    dict(good, state={}), dict(good, trajectory=[]), dict(good, steps=17),
                    dict(good, spec=dict(good['spec'], fastBid=0)), dict(good, terminal=False)]
        for path, value in [
            (('counts', 'focalReference', 'Auction'), 1),
            (('phaseCounters', 'Auction', 'multiActionDecisions'), 3),
            (('phaseCounters', 'Auction', 'teacherExpertAgreement'), 2),
            (('phaseCounters', 'Auction', 'forcedMoves'), 0),
            (('phaseCounters', 'Auction', 'priorGapHistogram'), [2, 0, 0, 0, 0, 0, 0]),
            (('phaseCounters', 'Auction', 'priorGapSum'), 0),
            (('phaseCounters', 'Auction', 'priorGapMax'), 19),
            (('phaseCounters', 'Auction', 'cannotOutscoreTeacherBestWithCurrentBound'), 0),
            (('phaseCounters', 'Auction', 'exactFloor20'), 0),
            (('decisions', 'counterfactualOnly'), 0),
            (('publicChecks', 'hiddenInvariant'), 0),
            (('publicChecks', 'fullMenuPrior'), True),
        ]:
            r = copy.deepcopy(good)
            target = r
            for part in path[:-1]:
                target = target[part]
            target[path[-1]] = value
            variants.append(r)
        for r in variants:
            with self.subTest(r=r), self.assertRaises(ValueError):
                study.validate_record(r, t, SHA)
        failed = failure(t)
        study.validate_record(failed, t, SHA)
        self.assertNotIn('allSeatCredit', failed)
        self.assertNotIn('phaseCounters', failed)
        with self.assertRaises(ValueError):
            study.validate_record(dict(failed, credit=.5), t, SHA)
        tasks = study.plan(True)
        rows = [outcome(t) for t in tasks]
        rows[1] = failure(tasks[1])
        report = study.summarize(rows, tasks)
        self.assertEqual(report['failures'], 1)
        self.assertTrue(report['qualificationStopped'])
        self.assertEqual(report['phaseDiagnostics']['teacher']['Auction']['terminalGames'], 1)
        self.assertEqual(report['policies']['teacher']['games'], 2)
        self.assertEqual(report['policies']['teacher']['gameMeanCredit'], 0)

    def test_allreference_control_violation_and_partial_coverage(self):
        tasks = study.plan(True)
        rows = [outcome(t) for t in tasks]
        rows[0]['allSeatCredit'] = [0., 1.]
        rows[0]['credit'] = 0.
        report = study.summarize(rows, tasks)
        self.assertEqual(len(report['baselineViolations']), 1)
        self.assertTrue(report['qualificationStopped'])
        partial = study.summarize(rows[:1], tasks)
        self.assertFalse(partial['complete'])
        self.assertEqual(len(partial['policies']), 10)
        self.assertIsNone(partial['policies']['reference']['macroCellCredit'])


class ResumeTests(unittest.TestCase):
    def test_partial_write_only_recovery_and_strict_identity(self):
        task = study.plan(True)[0]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            frozen = study.identity(True, versions={'offline': True}, workers=2)
            sha = study.prepare_output(root, frozen)
            self.assertEqual(sha, study.prepare_output(root, frozen))
            for field in ('protocol', 'tasks', 'sourceFiles', 'execution', 'runtimeVersions', 'generatorDigest'):
                bad = dict(frozen, **{field: 'changed'})
                with self.assertRaisesRegex(ValueError, 'identity'):
                    study.prepare_output(root, bad)
            r = outcome(task)
            r['identitySha256'] = sha
            line = study.canonical(r) + '\n'
            path = root / 'games.jsonl'
            path.write_text(line + '{"partial":')
            records, done = study.read_existing(path, [task], sha)
            self.assertEqual(records, [r])
            self.assertEqual(done, {study.key(task)})
            self.assertEqual(path.read_text(), line)
            path.write_text(line + line)
            with self.assertRaisesRegex(ValueError, 'duplicate'):
                study.read_existing(path, [task], sha)
            path.write_text(line + '{bad}\n')
            with self.assertRaises(ValueError):
                study.read_existing(path, [task], sha)
            (root / 'plan.json').unlink()
            with self.assertRaisesRegex(ValueError, 'without'):
                study.prepare_output(root, frozen)

    def test_symlink_and_size_safety(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'bad').symlink_to(root / 'nonexistent')
            with self.assertRaisesRegex(ValueError, 'symlink'):
                study.artifact_budget(root)
            (root / 'bad').unlink()
            with self.assertRaisesRegex(ValueError, '128 MiB'):
                study.artifact_budget(root, 128 * 1024**2 + 1)


class ServiceTests(unittest.TestCase):
    def test_counterfactual_calls_on_every_focal_multi_action_even_teacher(self):
        for task in study.plan(True)[:10]:
            expected = outcome(task)
            events = []
            for phase in study.PHASES:
                actual = study.controller(task['policy'], phase)
                for multi in (True, True, False):
                    if not multi and actual == 'teacher':
                        continue
                    events.append(dict(terminal=False, kind='reference', phase=phase,
                        actualController=actual, focalComparison=multi,
                        request=dict(player=task['spec']['focalSeat'], requestId='mock', revision=len(events), state={})))
                events.append(dict(terminal=False, kind='reference', phase=phase, actualController='reference',
                    focalComparison=False, request=dict(player=1, requestId='mock', revision=len(events), state={})))
            terminal = dict(terminal=True, credit=expected['allSeatCredit'],
                **{k: expected[k] for k in ('steps', 'rounds', 'counts', 'phaseCounters', 'publicChecks')})
            bridge, reference = mock.Mock(), mock.Mock()
            bridge.call.side_effect = events + [terminal]
            reference.decide.return_value = {'move': 'opaque-test-only'}
            result = study.play_game(task, bridge, reference, SHA)
            self.assertTrue(result['terminal'], result)
            self.assertEqual(result['decisions'], expected['decisions'])
            self.assertEqual(reference.decide.call_count, expected['decisions']['referenceRequests'])
            self.assertEqual(bridge.call.call_count, len(events) + 1)
            study.validate_record(result, task, SHA)

    def test_timeout_cap_and_sensitive_exception_not_persisted(self):
        task = study.plan(True)[0]
        for error, code in [(TimeoutError('SENSITIVE_STATE'), 'response-timeout'),
                            (ValueError('capped SENSITIVE_STATE'), 'nonterminal-cap'),
                            (RuntimeError('SENSITIVE_STATE'), 'game-or-policy-error')]:
            bridge = mock.Mock()
            bridge.call.side_effect = error
            result = study.play_game(task, bridge, mock.Mock(), SHA)
            study.validate_record(result, task, SHA)
            self.assertEqual(result['credit'], 0)
            self.assertFalse(result['terminal'])
            self.assertEqual(result['error']['code'], code)
            self.assertNotIn('SENSITIVE_STATE', study.canonical(result))

    def test_worker_cleanup_and_no_candidate_path(self):
        reference = mock.Mock()
        with mock.patch.object(study, 'validate_protocol'), \
                mock.patch.object(study, 'ReferenceProcess', return_value=reference), \
                mock.patch.object(study, 'LineProcess', side_effect=RuntimeError('startup')), \
                mock.patch.object(study.shared, 'close_process') as close:
            with self.assertRaises(RuntimeError):
                study.WorkerRuntime('artifact', 'python')
            self.assertIn(mock.call(reference), close.call_args_list)
        task = study.plan(True)[0]
        for result in (outcome(task), failure(task)):
            runtime = types.SimpleNamespace(bridge=object(), reference=object(), models=None, close=mock.Mock())
            incoming, outgoing = mock.Mock(), mock.Mock()
            incoming.get.side_effect = [task, None]
            with mock.patch.object(study, 'WorkerRuntime', return_value=runtime), \
                    mock.patch.object(study, 'play_game', return_value=result), mock.patch.object(study.shared.signal, 'signal'):
                study.worker_main(incoming, outgoing, 'artifact', 'python', SHA)
            runtime.close.assert_called_once()
            outgoing.put.assert_called_once_with(('outcome', result))
        with self.assertRaises(ValueError):
            study._worker_play(task, object(), object(), {'ppo': object()}, SHA)


class CoordinatorTests(unittest.TestCase):
    class Context:
        def __init__(self, failing=False):
            self.children, self.results = [], []
            self.failing, self.queued, self.queue_count = failing, 0, 0

        def Queue(self, maxsize):
            self.queue_count += 1
            context, incoming = self, self.queue_count == 1
            class Queue:
                def put(self, task):
                    if task is None:
                        next(c for c in context.children if c.alive).alive = False
                        return
                    context.queued += 1
                    r = failure(task) if context.failing and context.queued == 1 else outcome(task)
                    r['identitySha256'] = context.identity_sha
                    context.results.append(('outcome', r))
                def get(self, timeout=None):
                    if incoming:
                        raise AssertionError('Synthetic workers must not run')
                    return context.results.pop(0)
                def close(self):
                    pass
                def cancel_join_thread(self):
                    pass
            return Queue()

        def Process(self, target, args, name):
            self.identity_sha = args[-1]
            class Process:
                alive, pid = False, 1
                @property
                def exitcode(self):
                    return None if self.alive else 0
                def start(self):
                    self.alive = True
                def is_alive(self):
                    return self.alive
                def terminate(self):
                    self.alive = False
                kill = terminate
                def join(self, timeout):
                    pass
            p = Process()
            self.children.append(p)
            return p

    def test_generic_collector_resume_actual_workers_and_fail_closed(self):
        for failing in (False, True):
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                context = self.Context(failing)
                with mock.patch.object(study.shared.multiprocessing, 'get_context', return_value=context), \
                        mock.patch.object(study, 'runtime_versions', return_value={'offline': True}), \
                        mock.patch.object(study, 'budget'), mock.patch('builtins.print'):
                    def run(workers=2):
                        return study.run(root / 'study', artifact=root / 'reference/artifact', workers=workers, smoke=True)
                    if failing:
                        with self.assertRaisesRegex(RuntimeError, 'explicit failures'):
                            run()
                        report = json.loads((root / 'study/summary.json').read_text())
                        self.assertEqual(report['failures'], 1)
                        self.assertEqual(report['games'], 2)
                        with self.assertRaisesRegex(RuntimeError, 'Saved failures'):
                            run()
                        self.assertEqual(context.queued, 2)
                    else:
                        report = run()
                        self.assertTrue(report['complete'])
                        self.assertEqual(report['games'], 20)
                        path = root / 'study/games.jsonl'
                        with path.open('a') as file:
                            file.write('{"partial":')
                        self.assertTrue(run()['complete'])
                        self.assertEqual(context.queued, 20)
                        self.assertTrue(path.read_bytes().endswith(b'\n'))
                        with self.assertRaisesRegex(ValueError, 'identity'):
                            run(3)
                    self.assertTrue(all(not c.alive for c in context.children))


class JobTests(unittest.TestCase):
    def test_snapshot_retries_never_repeat_evaluation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            env = dict(RUN_ID='offline-unit-gap', MODEL_REPO=study.PROTOCOL['modelRepo'],
                DATASET_REPO='offline/source', SOURCE_PATH='synthetic.tgz', SOURCE_REVISION='f' * 40,
                SOURCE_SHA256=SHA, RUN_DIR=str(root / 'output'), REFERENCE_CACHE=str(root / 'cache'),
                REFERENCE_VENV=str(root / 'venv'), RESUME_CACHE=str(root / 'resume'), GAP_SMOKE='1', GAP_WORKERS='2')
            api = mock.Mock()
            api.model_info.return_value = api.dataset_info.return_value = types.SimpleNamespace(private=True)
            api.upload_folder.side_effect = [TimeoutError(), TimeoutError(),
                types.SimpleNamespace(oid='unit-runtime'), types.SimpleNamespace(oid='unit-complete')]
            with mock.patch.dict(job.os.environ, env, clear=True), \
                    mock.patch('huggingface_hub.HfApi', return_value=api), \
                    mock.patch.object(job.subprocess, 'run'), \
                    mock.patch.object(job.shared_job.time, 'sleep') as sleep, \
                    mock.patch.object(job, 'ensure_reference_environment', return_value=(
                        root / 'venv/bin/python', {'versions': {'candidate': {'offline': True}}})), \
                    mock.patch.object(job, 'recover_reference', return_value={'offline': True}), \
                    mock.patch.object(job, 'evaluate', return_value={'games': 20, 'failures': 0}) as evaluate, \
                    mock.patch('builtins.print'):
                job.run()
            evaluate.assert_called_once()
            self.assertEqual(api.upload_folder.call_count, 4)
            self.assertEqual([call.args[0] for call in sleep.call_args_list], [5, 15])
            self.assertTrue(all(c.kwargs['path_in_repo'] == 'runs/offline-unit-gap'
                                for c in api.upload_folder.call_args_list))
            self.assertEqual(json.loads((root / 'output/status.json').read_text())['stage'], 'complete')

    def test_whitelist_private_pins_and_no_bulky_paths(self):
        for bad in ('main', 'g' * 40, '../escape'):
            with self.assertRaises(ValueError):
                job.immutable_revision(bad)
        for bad in ('../escape', '/absolute', 'a/b', ''):
            with self.assertRaises(ValueError):
                job.safe_run(bad)
        manifest = {'study/plan.json': SHA, 'study/games.jsonl': SHA, 'protocol.json': SHA}
        self.assertEqual(set(job.validate_manifest(manifest)), {'study/plan.json', 'study/games.jsonl'})
        for bad in ('model.pt', 'hidden.json', 'artifact/fixtures/data.jsonl', '../escape'):
            with self.assertRaises(ValueError):
                job.validate_manifest(dict(manifest, **{bad: SHA}))
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'protocol.json').write_text('{}\n')
            self.assertEqual(set(job.compact_files(root)), {'protocol.json'})
            (root / 'model.pt').write_bytes(b'synthetic')
            with self.assertRaisesRegex(ValueError, 'bulky'):
                job.compact_files(root)
        with self.assertRaisesRegex(ValueError, 'separate'):
            job.separate_paths('/tmp/synthetic-output', '/tmp/synthetic-output/cache')
        self.assertIs(job.ensure_reference_environment, job.shared_job.ensure_reference_environment)

    def test_immutable_resume_hash_size_before_restore(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan = root / 'plan.json'; plan.write_text('{}\n')
            manifest = root / 'manifest.json'
            manifest.write_text(json.dumps({'study/plan.json': study.digest(plan)}))
            files = {'artifacts.json': manifest, 'study/plan.json': plan}
            def download(repo, name, **kwargs):
                self.assertEqual(kwargs['revision'], 'f' * 40)
                return str(files[name.removeprefix('runs/previous/')])
            def size(repo, name, revision, **kwargs):
                return files[name.removeprefix('runs/previous/')].stat().st_size
            with mock.patch('huggingface_hub.hf_hub_download', side_effect=download), \
                    mock.patch.object(job, 'remote_size', side_effect=size):
                receipt = job.restore_resume('private/repo', 'previous', 'f' * 40, root / 'output', root / 'cache')
                self.assertEqual(receipt['files']['study/plan.json'], study.digest(plan))
                manifest.write_text(json.dumps({'study/plan.json': '0' * 64}))
                with self.assertRaisesRegex(ValueError, 'hash/size'):
                    job.restore_resume('private/repo', 'previous', 'f' * 40, root / 'bad', root / 'cache')

    def test_reuse_existing_exact_artifact_never_downloads_or_deletes_ppo(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp)
            (cache / 'artifact').mkdir()
            extra = cache / 'ppo.pt'; extra.write_bytes(b'untouched-synthetic-legacy-cache-extra')
            receipt = cache / 'recovery.json'; receipt.write_text('{"legacy":"untouched"}\n')
            with mock.patch.object(job.recovery, 'verify_artifact', return_value={'present': 123, 'missing': []}) as verify, \
                    mock.patch.object(job.recovery, 'remote_metadata') as remote:
                result = job.recover_reference(cache)
            verify.assert_called_once_with(cache / 'artifact')
            remote.assert_not_called()
            self.assertEqual(set(result['pins']), {'source', 'model'})
            self.assertEqual(result['runtimeManifestSha256'], study.MANIFEST_SHA)
            self.assertTrue(result['exactServiceReady'])
            self.assertEqual(extra.read_bytes(), b'untouched-synthetic-legacy-cache-extra')
            self.assertEqual(receipt.read_text(), '{"legacy":"untouched"}\n')


if __name__ == '__main__':
    unittest.main()
