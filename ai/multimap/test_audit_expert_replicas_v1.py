"""Standard-library-only synthetic/adversarial replica reporting tests.

No real jobs, models, reference service, downloads, game play or stored study
outcomes. Fake checkpoint BYTES intentionally require an EXPLICIT simulated
external auditor receipt; they are never represented as independently verified.
Run: python3 -B -m unittest discover -s ai/multimap -p 'test_audit_expert_replicas_v1.py'
"""
from collections import Counter
from contextlib import ExitStack, contextmanager
import copy
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import statistics
import subprocess
import sys
import tempfile
import unittest

import audit_expert_replicas_v1 as a


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, allow_nan=False) + '\n')


def outcome(task, mode='tie'):
    """Small legal compact counters, not a simulated Power Grid game."""
    s = copy.deepcopy(task)
    counts = {actor: dict.fromkeys(a.PHASES, 0) for actor in a.CONTROLLERS}
    for actor in s['opponents']:
        if actor == 'learner':
            actor = 'focalTeacher' if s.get('focalTeacher') else 'warmupExpert' if s['split'] == 'warmup' else actor
        if actor in ('reference', 'focalTeacher'):
            for phase in a.PHASES:
                counts[actor][phase] += 1
        else:
            for phase in ('Auction', 'Building'):
                counts[actor][phase] += 1
            fixed = 'fixedV1' if actor in a.FROZEN else 'fixedV2'
            for phase in ('Resources', 'Bureaucracy'):
                counts[fixed][phase] += 1
    totals = {actor: sum(phases.values()) for actor, phases in counts.items()}
    labels = dict.fromkeys(a.PHASES, 0)
    if s['map'] == 'Germany' and s['split'] in ('warmup', 'train'):
        labels = dict(counts['warmupExpert' if s['split'] == 'warmup' else 'learner'])
    if mode == 'tie':
        credits = [1 / s['players']] * s['players']
    elif mode == 'win':
        credits = [int(i == s['focalSeat']) for i in range(s['players'])]
    elif mode == 'lose':
        credits = [int(i == (s['focalSeat'] + 1) % s['players']) for i in range(s['players'])]
    else:
        raise ValueError('Unknown fixture mode')
    return dict(spec=s, terminal=True, credit=credits[s['focalSeat']], allSeatCredit=credits,
        steps=sum(totals.values()), rounds=1, counts=counts, expertCounts=labels,
        publicChecks=dict(hiddenInvariant=totals['reference'] + sum(labels.values()),
                          referenceAtomicLegal=totals['reference'], expertAtomicLegal=sum(labels.values()),
                          fullMenuPrior=sum(totals[k] for k in ('learner', 'warmupExpert', 'self', *a.FROZEN))),
        decisions=totals['learner'] + totals['warmupExpert'],
        referenceRequests=totals['reference'] + sum(labels.values()), expertRequests=sum(labels.values()),
        featureMs=0., inferenceMs=0., referenceMs=0., seconds=0.)


def metric(rows, update):
    n = sum(r['decisions'] for r in rows)
    result = dict(rows=n, expertRows=sum(r['expertRequests'] for r in rows),
        optimizerSteps=(4 if update else 24) * math.ceil(n / 64), loss=0., value=0., expertCE=0., gradNorm=0.)
    result.update(dict(earlyStopped=False, expertCoefficient=.5*.97**(update - 1), actor=0., entropy=0., approxKl=0.)
                  if update else dict(epochs=24))
    return result


def seal(root):
    manifest = {p.relative_to(root).as_posix(): a.digest(p) for p in root.rglob('*')
                if p.is_file() and p.name != 'artifacts.json'}
    write(root / 'artifacts.json', manifest)
    return manifest


def snapshot(root, replica, fallback=False):
    protocol = a.protocol_for(replica)
    sources = {'ai/multimap/' + n: 'a'*64 for n in (*a.BASE_SOURCE_NAMES, *a.REPLICA_SOURCE_NAMES)}
    sources.update({'ai/multimap/' + n: sha for n, sha in a.FROZEN_SOURCES.items()})
    sources['ai/multimap/expert-replicas-protocol-v1.json'] = a.digest(a.HERE / 'expert-replicas-protocol-v1.json')
    sources.update({n: 'a'*64 for n in a.ROOT_SOURCE_NAMES})
    sources['ai/requirements-serve.txt'] = protocol['referenceRequirementsSha256']
    sources.update({f'engine/dist/synthetic-{i}.js': 'b'*64 for i in range(42)})
    generator_names = {n for n in sources if n.startswith('engine/dist/')} | {'ai/core.cjs', 'ai/strong/economics.cjs'} | {
        'ai/multimap/' + n for n in ('features.cjs', 'game.cjs', 'teacher.cjs', 'protocol.json')}
    generator_digest = hashlib.sha256(json.dumps({n: sources[n] for n in generator_names}, sort_keys=True).encode()).hexdigest()
    versions = dict(candidate=dict(python=[3, 12, 8], numpy='2.2.6', torch='2.10.0+cpu', **{'huggingface-hub': '1.29.0'}),
                    reference=dict(python=[3, 12, 8], numpy='2.5.3', onnxruntime='1.30.0'), node='v24.20.0')
    config = dict(schema='multimap-expert-replica-identity-v1', replica=replica, protocol=protocol,
        replicaStudy=a.study_protocol(), smoke=False, generatorDigest=generator_digest, sourceFiles=sources,
        engineDependencies=dict(synthetic=dict(files=1, sha256='d'*64)),
        referenceSourceFiles={'synthetic.py': 'e'*64}, referenceFiles=123,
        referenceManifestSha256=protocol['reference']['runtimeManifestSha256'], runtimeVersions=versions,
        execution=dict(workers=6, collector='thread-pool-lockstep-central-torch-with-child-processes',
                       inferenceThreads=1, optimizerThreads=4, deterministicAlgorithms=True),
        sourcePins=dict(warmStart=protocol['warmStart'], opponents=protocol['opponentPool'], reference=protocol['reference']))
    write(root / 'protocol.json', protocol)
    write(root / 'expert/config.json', config)
    write(root / 'environment.json', dict(versions=versions, referenceVenvBytes=123,
        requirementsSha256=protocol['referenceRequirementsSha256']))
    write(root / 'recovery.json', dict(schema='multimap-phase-gap-recovery-v1',
        pins=dict(source=protocol['reference']['sourcePin'], model=protocol['reference']['modelPin']),
        runtimeManifestSha256=protocol['reference']['runtimeManifestSha256'], policySha256=protocol['reference']['policySha256'],
        locallyVerifiedFiles=123, omitted=[], exactServiceReady=True, cacheBytes=123,
        diskBudgetBytes=protocol['referenceCacheMaxBytes'], sourceDownload=None,
        modelSha256=protocol['reference']['modelSha256'], recoveryMode='complete-unchanged-manifest-no-candidate-fetch',
        reserved_final_seeds_used=False))
    records = {}
    for name, tasks in a.schedules(replica).items():
        improved = not fallback and (name.startswith('selection-') and name not in ('selection-0.json', 'selection-teacher.json')
                                     or name == 'confirmation-selected.json')
        games = [outcome(t, 'win' if improved else 'tie') for t in tasks]
        record = dict(games=games)
        if name == 'warmup.json':
            record['optimization'] = metric(games, 0)
        elif not name.startswith('train-'):
            record['summary'] = a.summary(games)
        records[name] = record
        write(root / 'expert' / name, record)
    for split in ('warmup', 'selection', 'confirmation'):
        write(root / f'expert/{split}-plan.json', a.expected_plan(replica, split))
    history = []
    for u in range(33):
        name = f'train-{u}.json' if u else 'warmup.json'
        if u:
            write(root / f'expert/train-plan-{u}.json', a.expected_plan(replica, 'train', u))
        games = records[name]['games']
        h = dict(stage='train' if u else 'warmup', update=u, training=a.summary(games), optimization=metric(games, u))
        if u % 8 == 0:
            h['selection'] = records[f'selection-{u if u else "warmup"}.json']['summary']
        history.append(h)
    write(root / 'expert/history.json', history)
    result = dict(selectedUpdate=0, selectedStage='initial' if fallback else 'warmup',
        selectionScore=records['selection-0.json' if fallback else 'selection-warmup.json']['summary']['macroCredit'],
        baselineSelectionScore=records['selection-0.json']['summary']['macroCredit'],
        confirmation={k: records[f'confirmation-{k}.json']['summary'] for k in ('selected', 'teacher')},
        trainedUpdates=32, warmupEpochs=24, smoke=False, **a.FLAGS,
        note='Fresh-root expert/PPO experiment. Teacher-v2 baseline is an eligible fallback; confirmation never selects.')
    write(root / 'expert/result.json', result)
    labels = ['runtime-ready', 'initial', 'warmup', *('update-' + str(u) for u in range(1, 33)),
              'confirmation-selected', 'confirmation-teacher', 'complete']
    status = dict(run=f'synthetic-not-a-real-run-r{replica}', workflow='expert', protocol=protocol,
        smoke=False, workers=6, sourceRevision='1'*40, sourceSha256='2'*64,
        sourcePath='synthetic.tgz', sourceRepo='synthetic/source', **a.FLAGS, stage='complete',
        receipts=[dict(stage=s, revision=f'{i:040x}') for i, s in enumerate(labels, 1)],
        checkpointBytes=[123]*4, result=result)
    write(root / 'status.json', status)
    for label in ('initial', 'warmup', 'best', 'last'):
        (root / f'expert/{label}.pt').write_bytes(f'NOT A TORCH CHECKPOINT: synthetic {replica} {label}'.encode())
    seal(root)


def continuation_status(status, files, first_stage):
    old = status['run']; prefix, suffix = old.rsplit('-', 1)
    status['run'] = prefix + '-continuation-' + suffix
    status['resume'] = dict(run=old, revision='a'*40, files=dict(files))
    labels = [r['stage'] for r in status['receipts']]
    status['receipts'] = [status['receipts'][0], *status['receipts'][labels.index(first_stage):]]


def simulated_external_receipt(report):
    """Mock trust boundary for tests, NOT real checkpoint/provenance evidence."""
    before = dict(copy.deepcopy(report['expectedCheckpointProjection']), result=None, confirmations={}, lastSha256='f'*64)
    return dict(schema='multimap-expert-replica-external-integrity-v1', replica=report['replica'],
        manifestSha256=report['manifestSha256'], evidenceSha256='9'*64, checks=dict.fromkeys(a.EXTERNAL_CHECKS, True),
        finalCheckpoint=copy.deepcopy(report['expectedCheckpointProjection']),
        selectionCommit=dict(revision=report.get('expectedSelectionRevision') or '8'*40, checkpointSha256='f'*64, projection=before))


def scores(value=.3, **changes):
    maps = dict.fromkeys(a.TRAIN_MAPS, value); maps.update(changes)
    return dict(failures=0, maps=maps, macroCredit=statistics.mean(maps.values()))


def stages(*values):
    return list(zip(a.STAGES, values or [scores() for _ in range(6)]))


class Plans(unittest.TestCase):
    def test_full_recipe_counts_and_both_independent_namespaces(self):
        by_replica = []
        for replica in (1, 2):
            schedule = a.schedules(replica)
            self.assertEqual(sum(map(len, schedule.values())), 6240)
            self.assertEqual(len(schedule), 42)
            self.assertEqual(len(a.expected_names()), 88)
            self.assertEqual([len(a.expected_plan(replica, s)) for s in ('warmup', 'selection', 'confirmation')], [160, 320, 640])
            train = [s for u in range(1, 33) for s in a.expected_plan(replica, 'train', u)]
            self.assertEqual(len(train), 2560)
            self.assertEqual(len({s['seed'] for s in train}), 2560)
            all_specs = [s for tasks in schedule.values() for s in tasks]
            self.assertEqual({s['map'] for s in all_specs}, set(a.TRAIN_MAPS))
            by_replica.append({s['seed'] for s in all_specs})
        self.assertFalse(by_replica[0] & by_replica[1])
        self.assertEqual(a.COUNTS['totalGames'], 12480)

    def test_literal_new_protocol_analysis_and_seed_pins(self):
        for replica, seed in ((1, 190731), (2, 827119)):
            p = a.protocol_for(replica)
            self.assertEqual(p['seed'], seed)
            self.assertEqual(p['transferMaps'], [])
            self.assertEqual(p['warmupEpochs'], 24)
            self.assertEqual(p['updates'], 32)
        self.assertFalse(a.study_protocol()['analysis']['pooledInference'])
        self.assertFalse(a.study_protocol()['analysis']['winnerSelection'])

    def test_full_plan_grid_and_pairing(self):
        for replica in (1, 2):
            tasks = a.expected_plan(replica, 'confirmation')
            counts = Counter(s['cell'] for s in tasks)
            self.assertEqual(len(counts), 80)
            self.assertEqual(len({s['seed'] for s in tasks}), 160)
            self.assertTrue(all(counts[s['cell']] == 2*s['players'] for s in tasks))
            teacher = a.expected_plan(replica, 'confirmation', teacher=True)
            self.assertEqual(tasks, [{k: v for k, v in s.items() if k != 'focalTeacher'} for s in teacher])

    def test_opponents_and_training_seat_rotation(self):
        for replica in (1, 2):
            for split in ('selection', 'confirmation'):
                for s in a.expected_plan(replica, split):
                    opponents = set(s['opponents']) - {'learner'}
                    self.assertEqual(opponents, {'reference'}) if s['map'] == 'Germany' else self.assertLessEqual(opponents, set(a.FROZEN))
            for u in range(1, 33):
                for ci, s in enumerate(a.expected_plan(replica, 'train', u)):
                    self.assertEqual(s['focalSeat'], (ci + u - 1) % s['players'])
                    self.assertEqual(s['opponentMode'] == 'reference', s['map'] == 'Germany' and (ci + u) % 2 == 0)

    def test_bad_replica_split_update_types(self):
        for replica in (0, 3, True, False, '1', 1., None):
            with self.subTest(replica=replica), self.assertRaises(ValueError):
                a.expected_plan(replica, 'selection')
        for split, update, teacher in [('final', 0, False), ('train', 0, False), ('train', 33, False),
                ('train', True, False), ('selection', 1, False), ('warmup', 0, True),
                ('train', 1, True), ('selection', 0, 1), ('selection', 0., False)]:
            with self.subTest(split=split, update=update), self.assertRaises(ValueError):
                a.expected_plan(1, split, update, teacher)

    def test_helper_is_authenticated_and_isolated(self):
        scope = a.validate_outcome.__globals__
        for name in ('NAMESPACE', 'PROTOCOL', 'expected_plan', 'summary', 'choose_selection', 'audit'):
            self.assertNotIn(name, scope)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'helper.py'
            path.write_bytes((a.HERE / 'audit_expert.py').read_bytes() + b'\n')
            with self.assertRaisesRegex(ValueError, 'helper hash'):
                a._outcome_helper(path)

    def test_import_is_standard_library_only(self):
        code = ('import sys; sys.path.insert(0, "ai/multimap"); import audit_expert_replicas_v1; '
                'assert not ({"torch","expert_ppo","expert_rollout","expert_replicas_v1","huggingface_hub","audit_expert"} & set(sys.modules))')
        subprocess.run([sys.executable, '-B', '-c', code], cwd=a.HERE.parents[1], check=True, capture_output=True)


class Outcomes(unittest.TestCase):
    def reject(self, mutation, task=None):
        task = task or a.expected_plan(1, 'confirmation')[0]
        row = outcome(task); mutation(row)
        with self.assertRaises((ValueError, TypeError)):
            a.verify_outcomes([row], [task])

    def test_valid_all_scheduled_outcomes_both_replicas(self):
        for replica in (1, 2):
            for tasks in a.schedules(replica).values():
                a.verify_outcomes([outcome(t) for t in tasks], tasks)

    def test_strict_order_duplicates_missing_extra(self):
        tasks = a.expected_plan(1, 'selection')[:2]; rows = [outcome(t) for t in tasks]
        for changed in (rows[::-1], rows[:1], rows + rows[:1], [rows[0], rows[0]]):
            with self.assertRaises(ValueError):
                a.verify_outcomes(changed, tasks)

    def test_cross_old_malformed_reserved_smoke_namespace(self):
        for seed in ('old-root', a.namespace(2) + ':confirmation:0:Germany|2|original|0:0',
                     a.namespace(1) + ':smoke:confirmation:0:Germany|2|original|0:0',
                     a.namespace(1) + ':final:0:Germany|2|original|0:0',
                     a.namespace(1) + ':confirmation:00:Germany|2|original|0:0'):
            self.reject(lambda r: r['spec'].__setitem__('seed', seed))

    def test_spec_type_and_controller_tampering(self):
        for key, value in [('smoke', 0), ('players', 2.), ('focalSeat', False), ('deal', False),
                           ('fastBid', 0), ('focalTeacher', False), ('map', 'Italy')]:
            self.reject(lambda r: r['spec'].__setitem__(key, value))
        self.reject(lambda r: r['spec']['opponents'].__setitem__(1, 'self'))

    def test_counter_types_and_totals(self):
        for value in (True, 1., -1):
            self.reject(lambda r: r['counts']['learner'].__setitem__('Auction', value))
        self.reject(lambda r: r.__setitem__('steps', r['steps'] + 1))
        self.reject(lambda r: r['counts'].pop('reference'))
        self.reject(lambda r: r['counts']['self'].__setitem__('Auction', 1))
        self.reject(lambda r: r['counts']['learner'].__setitem__('Resources', 1))

    def test_public_counters_and_requests(self):
        for key in ('hiddenInvariant', 'referenceAtomicLegal', 'expertAtomicLegal', 'fullMenuPrior'):
            self.reject(lambda r: r['publicChecks'].__setitem__(key, r['publicChecks'][key] + 1))
        for key in ('decisions', 'expertRequests', 'referenceRequests'):
            self.reject(lambda r: r.__setitem__(key, r[key] + 1))

    def test_labels_training_germany_only(self):
        for split, update in (('warmup', 0), ('train', 1)):
            task = a.expected_plan(1, split, update)[0]
            self.reject(lambda r: r['expertCounts'].__setitem__('Auction', 0), task)
        for task in (a.expected_plan(1, 'selection')[0], a.expected_plan(1, 'confirmation', teacher=True)[0],
                     next(t for t in a.expected_plan(1, 'train', 1) if t['map'] == 'USA')):
            self.reject(lambda r: r['expertCounts'].__setitem__('Auction', 1), task)

    def test_terminal_errors_nonfinite_and_credit(self):
        for key, value in [('terminal', False), ('steps', 4001), ('rounds', 0), ('seconds', float('nan')),
                           ('credit', True), ('allSeatCredit', [.6, .4]), ('error', 'failed'), ('trace', [])]:
            self.reject(lambda r: r.__setitem__(key, value))

    def test_initial_teacher_full_terminal_and_routing_parity(self):
        initial = [outcome(t) for t in a.expected_plan(1, 'selection')]
        teacher = [outcome(t) for t in a.expected_plan(1, 'selection', teacher=True)]
        a.initial_parity(initial, teacher)
        for mutation in (lambda r: r.__setitem__('rounds', 2),
                         lambda r: r.__setitem__('allSeatCredit', [1, 0]),
                         lambda r: r['counts']['focalTeacher'].__setitem__('Auction', 2)):
            modified = copy.deepcopy(teacher); mutation(modified[0])
            with self.assertRaises(ValueError):
                a.initial_parity(initial, modified)


class Selection(unittest.TestCase):
    def test_fallback_and_earliest_ties(self):
        self.assertEqual(a.choose_selection(stages())[0], 'initial')
        self.assertEqual(a.choose_selection(stages(scores(), *[scores(.4)]*5))[0], 'warmup')
        self.assertEqual(a.choose_selection(stages(scores(), scores(), *[scores(.4)]*4))[0], '8')

    def test_germany_and_other_map_regression_guard(self):
        self.assertFalse(a.eligible(scores(.9, Germany=.299), scores()))
        self.assertTrue(a.eligible(scores(.9, Germany=.3), scores()))
        self.assertTrue(a.eligible(scores(.9, USA=.25), scores()))
        self.assertFalse(a.eligible(scores(.9, USA=.249), scores()))
        self.assertEqual(a.choose_selection(stages(scores(), scores(.9, Germany=.29), *[scores()]*4))[0], 'initial')

    def test_no_confirmation_or_reordered_selection(self):
        for records in (stages() + [('confirmation', scores(1))], stages()[::-1], stages()[1:]):
            with self.assertRaises(ValueError):
                a.choose_selection(records)

    def test_failed_bad_maps_nonfinite_and_bool_rejected(self):
        for key, value in [('failures', True), ('failures', False), ('failures', 1), ('macroCredit', float('nan'))]:
            s = scores(); s[key] = value
            self.assertFalse(a.eligible(s, scores()))
        s = scores(); s['maps']['Italy'] = .9
        self.assertFalse(a.eligible(s, scores()))


class Statistics(unittest.TestCase):
    def test_rational_equal_cell_not_raw_game_estimate(self):
        rows = [outcome(t, 'win' if t['players'] == 2 else 'lose') for t in a.expected_plan(1, 'confirmation')]
        estimate = a.summary(rows)['macroCredit']
        self.assertAlmostEqual(estimate, float(Fraction(1, 5)))
        self.assertAlmostEqual(statistics.mean(r['credit'] for r in rows), float(Fraction(1, 10)))
        self.assertNotEqual(estimate, statistics.mean(r['credit'] for r in rows))

    def test_rational_cluster_se_not_game_pseudoreplication(self):
        # Cell 2p has deal means 0,1; 6p has 1/2,1/2. Equal fixed-cell
        # variance = ((1/2)/2 + 0)/2^2 = 1/16, SE=1/4.
        result = a.stratified_estimate({'Germany|2|original|0': [0, 1], 'Germany|6|original|0': [.5, .5]})
        self.assertEqual(result['mean'], float(Fraction(1, 2)))
        self.assertEqual(result['standardError'], float(Fraction(1, 4)))
        self.assertEqual(result['independentDeals'], 4)
        self.assertAlmostEqual(result['approximateNormal95'][0], .01)
        self.assertAlmostEqual(result['approximateNormal95'][1], .99)

    def test_full_grid_rational_se_uses_160_deals_not_640_games(self):
        tasks = a.expected_plan(1, 'confirmation')
        selected = [outcome(t, 'win' if t['cell'] == 'Germany|2|original|0' and t['deal'] == 1 else 'lose') for t in tasks]
        teacher = [outcome(t, 'lose') for t in a.expected_plan(1, 'confirmation', teacher=True)]
        estimate = a.statistics_report(selected, teacher)['subsets']['macro']['pairedDifference']
        self.assertEqual(estimate['mean'], float(Fraction(1, 160)))
        self.assertEqual(estimate['standardError'], float(Fraction(1, 160)))
        self.assertEqual(estimate['independentDeals'], 160)
        self.assertEqual(statistics.mean(r['credit'] for r in selected), float(Fraction(1, 320)))

    def test_fixed_cell_not_random_cell_variation(self):
        self.assertEqual(a.stratified_estimate({'a': [0, 0], 'b': [1, 1]})['standardError'], 0)

    def test_paired_covariance_not_independent_arms(self):
        selected, teacher = [.25, .75], [0., .5]
        paired = a.stratified_estimate({'a': [x - y for x, y in zip(selected, teacher)]})
        self.assertEqual(paired['mean'], .25)
        self.assertEqual(paired['standardError'], 0)
        self.assertGreater(a.stratified_estimate({'a': selected})['standardError'], 0)

    def test_reject_single_deal_missing_seats_duplicates_and_types(self):
        for strata in ({}, {'a': [.5]}, {'a': [0, 0, 0]}, {'a': [False, 1]}):
            with self.assertRaises(ValueError):
                a.stratified_estimate(strata)
        task = a.expected_plan(1, 'confirmation')[0]
        for rows in ([outcome(task)], [outcome(task), outcome(task)]):
            with self.assertRaises(ValueError):
                a.deal_table(rows)
        row = outcome(task); row['spec']['deal'] = False
        with self.assertRaises(ValueError):
            a.deal_table([row])

    def test_complete_breakdowns_and_cross_replica_pairing_rejected(self):
        selected = [outcome(t) for t in a.expected_plan(1, 'confirmation')]
        teacher = [outcome(t) for t in a.expected_plan(1, 'confirmation', teacher=True)]
        report = a.statistics_report(selected, teacher)
        self.assertEqual(len(report['subsets']), 114)
        self.assertEqual(report['subsets']['macro']['gamesPerArm'], 640)
        self.assertAlmostEqual(report['subsets']['macro']['selected']['mean'], .29)
        self.assertEqual(report['subsets']['macro']['pairedDifference']['standardError'], 0)
        self.assertEqual(report['subsets']['mapPlayers:Germany|6']['pairedDifference']['cells'], 4)
        self.assertEqual(report['subsets']['cell:Germany|2|original|0']['pairedDifference']['independentDeals'], 2)
        foreign = [outcome(t) for t in a.expected_plan(2, 'confirmation', teacher=True)]
        with self.assertRaises(ValueError):
            a.statistics_report(selected, foreign)


class FullSnapshots(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.one = Path(cls.temp.name) / 'replica1'
        cls.two = Path(cls.temp.name) / 'replica2'
        snapshot(cls.one, 1)
        snapshot(cls.two, 2, fallback=True)
        cls.report1 = a.audit_complete(cls.one, 1)
        cls.report2 = a.audit_complete(cls.two, 2)
        cls.receipt1 = simulated_external_receipt(cls.report1)
        cls.receipt2 = simulated_external_receipt(cls.report2)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    @contextmanager
    def change(self, name, mutation, *, reseal=True):
        path = self.one / name
        original = path.read_bytes()
        manifest = (self.one / 'artifacts.json').read_bytes()
        try:
            value = a.read(path); mutation(value); write(path, value)
            if reseal:
                seal(self.one)
            yield
        finally:
            path.write_bytes(original)
            (self.one / 'artifacts.json').write_bytes(manifest)

    def test_json_complete_requires_external_checks_no_strength_inference(self):
        r = self.report1
        self.assertEqual(r['status'], 'integrity-pending')
        self.assertTrue(r['jsonChecksPassed'])
        self.assertFalse(r['allChecksPassed'])
        self.assertNotIn('confirmationStatistics', r)
        self.assertEqual(r['coverage']['savedTerminalOutcomes'], 6240)
        self.assertEqual(r['coverage']['confirmationDealRoots'], 160)
        self.assertEqual(r['selectedStage'], 'warmup')
        self.assertEqual(r['selectedUpdate'], 0)

    def test_complete_both_and_fallback_are_reported_no_winner_or_pool(self):
        report = a.report_all({1: self.one, 2: self.two}, integrity={1: self.receipt1, 2: self.receipt2})
        self.assertEqual(report['statusCounts'], {'complete': 2})
        self.assertTrue(report['allReplicasComplete'])
        self.assertEqual(len(report['replicas']), 2)
        self.assertTrue(report['replicas'][1]['teacherFallback'])
        self.assertEqual(report['replicas'][1]['selectedStage'], 'initial')
        self.assertEqual(report['excludedReplicaIds'], [])
        self.assertFalse(report['winnerSelection'])
        self.assertFalse(report['pooledInference'])
        spread = report['betweenReplicaDescriptive']['subsets']['macro']
        self.assertAlmostEqual(spread['mean'], .355)
        self.assertAlmostEqual(spread['absoluteDifference'], .71)
        self.assertAlmostEqual(spread['sampleStandardDeviation'], .71 / math.sqrt(2))
        self.assertIsNone(report['betweenReplicaDescriptive']['confidenceInterval'])

    def test_incomplete_two_entry_requirement_and_no_subset_fold(self):
        for roots in ({1: self.one}, {2: self.two}, {True: self.one, 2: self.two}, {'1': self.one, 2: self.two}):
            with self.assertRaises(ValueError):
                a.report_all(roots)
        report = a.report_all({1: self.one, 2: None}, integrity={1: self.receipt1})
        self.assertEqual(report['statusCounts'], {'complete': 1, 'absent': 1})
        self.assertIsNone(report['betweenReplicaDescriptive'])
        self.assertFalse(report['strengthInferenceAvailable'])
        self.assertEqual(report['replicas'][1]['observedCounts']['missingOutcomeFiles'], 42)
        self.assertEqual(report['excludedReplicaIds'], [])

    def test_bad_manifest_missing_extra_and_symlink(self):
        with self.change('expert/result.json', lambda r: r.__setitem__('selectedUpdate', 32), reseal=False):
            with self.assertRaisesRegex(ValueError, 'Manifest content mismatch'):
                a.audit_complete(self.one, 1)
        extra = self.one / 'extra.json'
        extra.write_text('{}')
        try:
            with self.assertRaisesRegex(ValueError, 'missing/extra'):
                a.audit_complete(self.one, 1)
        finally:
            extra.unlink()
        original = (self.one / 'expert/best.pt').read_bytes()
        (self.one / 'expert/best.pt').unlink()
        try:
            with self.assertRaises(ValueError):
                a.audit_complete(self.one, 1)
            (self.one / 'expert/best.pt').symlink_to(self.one / 'expert/initial.pt')
            with self.assertRaisesRegex(ValueError, 'symlink'):
                a.audit_complete(self.one, 1)
        finally:
            (self.one / 'expert/best.pt').unlink(missing_ok=True)
            (self.one / 'expert/best.pt').write_bytes(original)

    def test_config_protocol_type_and_scope_tampering(self):
        mutations = [lambda c: c['protocol'].__setitem__('seed', 917),
                     lambda c: c['protocol'].__setitem__('transferMaps', ['Italy']),
                     lambda c: c.__setitem__('replica', True),
                     lambda c: c['execution'].__setitem__('workers', 6.),
                     lambda c: c['replicaStudy']['analysis'].__setitem__('winnerSelection', True),
                     lambda c: c['sourcePins']['warmStart'].__setitem__('sha256', '0'*64),
                     lambda c: c['sourceFiles'].__setitem__('ai/multimap/expert_ppo.py', '0'*64)]
        for mutation in mutations:
            with self.change('expert/config.json', mutation), self.assertRaises(ValueError):
                a.audit_complete(self.one, 1)
        with self.assertRaises(ValueError):
            a.audit_complete(self.one, 2)

    def test_ordered_plans_outcomes_and_history(self):
        for name, mutation in [('expert/selection-plan.json', lambda p: p.reverse()),
                ('expert/train-1.json', lambda r: r['games'].reverse()),
                ('expert/history.json', lambda h: h.reverse()),
                ('expert/history.json', lambda h: h[1].__setitem__('update', True)),
                ('expert/history.json', lambda h: h[1].__setitem__('selection', h[0]['selection']))]:
            with self.change(name, mutation), self.assertRaises(ValueError):
                a.audit_complete(self.one, 1)

    def test_recomputed_selection_result_baseline_and_history_summaries(self):
        for name, mutation in [('expert/result.json', lambda r: r.__setitem__('selectedStage', 'train')),
                ('expert/result.json', lambda r: r.__setitem__('baselineSelectionScore', .9)),
                ('expert/selection-warmup.json', lambda r: r['summary'].__setitem__('macroCredit', .8)),
                ('expert/history.json', lambda h: h[8]['selection'].__setitem__('macroCredit', .8)),
                ('expert/history.json', lambda h: h[1]['training'].__setitem__('games', 80.)),
                ('expert/confirmation-selected.json', lambda r: r['summary'].__setitem__('failures', False))]:
            with self.change(name, mutation), self.assertRaises(ValueError):
                a.audit_complete(self.one, 1)

    def test_fixed_optimization_epochs_steps_labels_and_types(self):
        for update, key, value in [(0, 'epochs', 23), (0, 'optimizerSteps', 1), (1, 'expertCoefficient', .1),
                (1, 'rows', True), (1, 'expertRows', 0), (1, 'optimizerSteps', 1), (1, 'earlyStopped', 0)]:
            with self.change('expert/history.json', lambda h: h[update]['optimization'].__setitem__(key, value)), self.assertRaises(ValueError):
                a.audit_complete(self.one, 1)

    def test_receipts_require_strict_selection_before_confirmation(self):
        def reorder(s):
            s['receipts'][3], s['receipts'][-3] = s['receipts'][-3], s['receipts'][3]
        for mutation in (reorder, lambda s: s['receipts'].pop(4),
                         lambda s: s['receipts'].append(s['receipts'][-1]),
                         lambda s: s.__setitem__('error', {'code': 'stopped'})):
            with self.change('status.json', mutation), self.assertRaises(ValueError):
                a.audit_complete(self.one, 1)

    def test_one_continuation_and_inherited_files_not_reobserved(self):
        manifest = a.read(self.one / 'artifacts.json')
        def continuation(s):
            continuation_status(s, {k: v for k, v in manifest.items() if k.startswith('expert/') and
                                'confirmation' not in k and k != 'expert/result.json'}, 'confirmation-selected')
        with self.change('status.json', continuation):
            report = a.audit_complete(self.one, 1)
            self.assertEqual(report['coverage']['savedTerminalOutcomes'], 6240)
            self.assertEqual(report['status'], 'integrity-pending')
        def foreign(s):
            continuation(s); s['resume']['run'] = s['resume']['run'][:-1] + '2'
        with self.change('status.json', foreign), self.assertRaises(ValueError):
            a.audit_complete(self.one, 1)

    def test_continuation_replayed_uncommitted_outcome_bytes_are_integrity_pending(self):
        manifest = a.read(self.one / 'artifacts.json')
        initial = {'config.json', 'initial.pt', 'best.pt', 'last.pt', 'history.json',
                   'selection-plan.json', 'selection-0.json', 'selection-teacher.json'}
        warmup = initial | {'warmup-plan.json', 'warmup.json', 'selection-warmup.json', 'warmup.pt'}
        update8 = warmup | {f'{prefix}-{u}.json' for prefix in ('train', 'train-plan') for u in range(1, 9)} | {'selection-8.json'}
        final = {name.removeprefix('expert/') for name in manifest if name.startswith('expert/')} - {'result.json'}
        # These synthetic original snapshots contain one batch's outputs beyond
        # the last commit: warmup, update 8, or one confirmation arm. The JSON
        # auditor cannot infer the boundary from these hashes or upload labels.
        for first, inherited, replayed in (
                ('warmup', warmup, ('warmup.json', 'selection-warmup.json')),
                ('update-8', update8, ('train-8.json', 'selection-8.json')),
                ('confirmation-selected', final - {'confirmation-teacher.json'}, ('confirmation-selected.json',)),
                ('confirmation-teacher', final, ('confirmation-teacher.json',))):
            files = {'expert/' + name: manifest['expert/' + name] for name in inherited}
            with self.subTest(first=first), self.change('status.json', lambda s: continuation_status(s, files, first)), ExitStack() as edits:
                for name in replayed:
                    edits.enter_context(self.change('expert/' + name, lambda r: r['games'][0].__setitem__('seconds', 1.)))
                    self.assertNotEqual(a.digest(self.one / 'expert' / name), files['expert/' + name])
                report = a.audit_complete(self.one, 1)
                self.assertEqual(report['status'], 'integrity-pending')
                self.assertTrue(report['jsonChecksPassed'])
                self.assertFalse(report['allChecksPassed'])
                self.assertFalse(report['strengthInferenceAvailable'])
                self.assertNotIn('confirmationStatistics', report)
                self.assertIn('inheritedCommittedOutputsUnchanged', report['externalChecksNeeded'])
                self.assertEqual(report['coverage']['savedTerminalOutcomes'], 6240)

    def test_continuation_config_and_initial_bytes_remain_strict(self):
        manifest = a.read(self.one / 'artifacts.json')
        files = {k: v for k, v in manifest.items() if k.startswith('expert/') and
                 'confirmation' not in k and k != 'expert/result.json'}
        for name in ('expert/config.json', 'expert/initial.pt'):
            with self.subTest(name=name), self.change('status.json', lambda s: continuation_status(s, files, 'confirmation-selected')):
                path = self.one / name; original = path.read_bytes()
                try:
                    # Config still has identical JSON values: its exact bytes,
                    # not just config semantics, must match the inherited hash.
                    path.write_bytes(original + b'\n')
                    seal(self.one)
                    with self.assertRaisesRegex(ValueError, 'Inherited immutable artifact changed: ' + name):
                        a.audit_complete(self.one, 1)
                finally:
                    path.write_bytes(original)

    def test_external_receipt_requires_inherited_committed_boundary_check(self):
        self.assertIn('inheritedCommittedOutputsUnchanged', self.report1['externalChecksNeeded'])
        for value in (None, False):
            receipt = copy.deepcopy(self.receipt1)
            if value is None:
                receipt['checks'].pop('inheritedCommittedOutputsUnchanged')
            else:
                receipt['checks']['inheritedCommittedOutputsUnchanged'] = value
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, 'All external integrity checks required'):
                a._external_gate(receipt, 1, self.report1['manifestSha256'], self.report1['expectedCheckpointProjection'])

    def test_external_receipt_must_bind_all_checks_actual_commit_and_selection(self):
        for mutation in (lambda r: r.__setitem__('manifestSha256', '0'*64),
                         lambda r: r.__setitem__('replica', True),
                         lambda r: r['checks'].__setitem__('selectionStrictlyBeforeConfirmation', False),
                         lambda r: r['checks'].pop('referenceAndFrozenModelProvenance'),
                         lambda r: r['finalCheckpoint'].__setitem__('bestUpdate', 32),
                         lambda r: r['finalCheckpoint']['baseline'].__setitem__('macroCredit', 1.),
                         lambda r: r['selectionCommit']['projection'].__setitem__('confirmations', {'selected': {}}),
                         lambda r: r['selectionCommit'].__setitem__('checkpointSha256', r['finalCheckpoint']['lastSha256'])):
            receipt = copy.deepcopy(self.receipt1); mutation(receipt)
            with self.assertRaises(ValueError):
                a._external_gate(receipt, 1, self.report1['manifestSha256'], self.report1['expectedCheckpointProjection'])

    def test_failed_status_kept_even_with_full_outcome_files(self):
        with self.change('status.json', lambda s: s.__setitem__('stage', 'failed')):
            report = a.report_all({1: self.one, 2: self.two}, statuses={1: 'TIMEOUT'})
            self.assertEqual(report['replicas'][0]['status'], 'failed')
            self.assertEqual(report['replicas'][0]['observedCounts']['observedRows'], 6240)
            self.assertNotIn('confirmationStatistics', report['replicas'][0])
            self.assertIsNone(report['betweenReplicaDescriptive'])

    def test_invalid_root_and_operational_failure_not_silently_excluded(self):
        with self.change('expert/train-1.json', lambda r: r['games'][0].__setitem__('terminal', False)):
            report = a.report_all({1: self.one, 2: self.two})
            self.assertEqual(report['replicas'][0]['status'], 'invalid')
            self.assertEqual(report['replicas'][0]['observedCounts']['nonterminalRows'], 1)
            self.assertEqual(len(report['replicas']), 2)
        report = a.report_all({1: self.one, 2: self.two}, statuses={1: 'FAILED'}, integrity={1: self.receipt1, 2: self.receipt2})
        self.assertEqual(report['replicas'][0]['status'], 'status-conflict')
        self.assertNotIn('confirmationStatistics', report['replicas'][0])
        self.assertIsNone(report['betweenReplicaDescriptive'])

    def test_operational_canceled_spellings_conflict_with_complete_snapshot(self):
        for status in ('CANCELED', 'canceled', 'CANCELLED'):
            with self.subTest(status=status):
                report = a.report_all({1: self.one, 2: self.two}, statuses={1: status},
                                      integrity={1: self.receipt1, 2: self.receipt2})
                self.assertEqual(report['replicas'][0]['status'], 'status-conflict')
                self.assertEqual(report['replicas'][0]['operationalStatus'], status)
                self.assertFalse(report['replicas'][0]['allChecksPassed'])
                self.assertNotIn('confirmationStatistics', report['replicas'][0])
                self.assertFalse(report['strengthInferenceAvailable'])
                self.assertIsNone(report['betweenReplicaDescriptive'])
                self.assertEqual(report['excludedReplicaIds'], [])

    def test_partial_counts_duplicates_and_failure_no_strength(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            task = a.expected_plan(1, 'train', 1)[0]; row = outcome(task)
            failed = dict(row, terminal=False, error='fixed-error-code')
            write(root / 'expert/train-1.json', dict(games=[row, row, failed, None]))
            write(root / 'status.json', dict(stage='update-1'))
            report = a.report_all({1: root, 2: None})
            counts = report['replicas'][0]['observedCounts']
            self.assertEqual(counts['observedRows'], 4)
            self.assertEqual(counts['duplicateTaskRows'], 2)
            self.assertEqual(counts['errorRows'], 1)
            self.assertEqual(counts['malformedRows'], 1)
            self.assertEqual(report['replicas'][0]['status'], 'incomplete')
            self.assertFalse(report['strengthInferenceAvailable'])

    def test_shared_snapshot_root_forbidden(self):
        with self.assertRaises(ValueError):
            a.report_all({1: self.one, 2: self.one})

    def test_strict_json_duplicates_nonfinite(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'bad.json'
            for text in ('{"stage":"complete","stage":"failed"}', '{"value":NaN}', '{"value":Infinity}', '{"value":1e999}'):
                path.write_text(text)
                with self.assertRaises(ValueError):
                    a.read(path)


if __name__ == '__main__':
    unittest.main()
