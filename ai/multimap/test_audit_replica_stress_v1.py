"""Independent stdlib synthetic tests: NEVER model/game/job evaluation evidence.

No network, torch or serving imports. AST-extracted serving planning/summary
functions are compared ONLY as test oracles; the auditor imports none of them.
Node validates all specs without constructing or playing a game.
Run: python3 -B -m unittest discover -s ai/multimap -p test_audit_replica_stress_v1.py
"""
import ast
from collections import Counter, defaultdict
from contextlib import contextmanager
import copy
import hashlib
import itertools
import json
import math
from pathlib import Path
import statistics
import subprocess
import tempfile
import unittest
from unittest import mock

import audit_replica_stress_v1 as a


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, separators=(',', ':'), allow_nan=False) + '\n')


def field_paths(value, field, path=()):
    """All literal serialized occurrences, including repeated/aliased objects."""
    result = []
    if isinstance(value, dict):
        for key, child in value.items():
            if key == field:
                result.append((*path, key))
            result.extend(field_paths(child, field, (*path, key)))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            result.extend(field_paths(child, field, (*path, index)))
    return result


def serving_planner():
    """Test-only extraction: no import, model initialization, network or games."""
    protocol = a.protocol()
    ns = dict(PROTOCOL=protocol, MAPS=a.MAPS, PANELS=a.PANELS, POLICIES=a.POLICIES,
              NAMESPACE=a.NAMESPACE, FROZEN=a.PPO_MODELS, SMOKE_SCOPES=a.SMOKE_SCOPES,
              itertools=itertools, _protocol=lambda: protocol,
              SPEC_FIELDS=set(a.expected_tasks('strong')[0]))
    tree = ast.parse((a.HERE / 'replica_stress_rollout_v1.py').read_text())
    selected = [n for n in tree.body if isinstance(n, ast.FunctionDef) and
                n.name in ('_controllers', 'plans', '_validate_spec')]
    exec(compile(ast.Module(body=selected, type_ignores=[]), '<test-serving-planner>', 'exec'), ns)
    return ns['plans']


def serving_summary(games, panel):
    ns = dict(PROTOCOL=a.protocol(), POLICIES=a.POLICIES, defaultdict=defaultdict,
        math=math, statistics=statistics, canonical=a.canonical,
        plan=lambda panel, smoke: a.expected_tasks(panel, smoke=smoke),
        validate_outcome=a.validate_outcome)
    tree = ast.parse((a.HERE / 'replica_stress_study_v1.py').read_text())
    selected = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in ('estimate', 'analyze')]
    exec(compile(ast.Module(body=selected, type_ignores=[]), '<test-serving-summary>', 'exec'), ns)
    return ns['analyze'](games, panel)


def outcome(task):
    """Synthetic varied actions, forced fixed moves, winners, ties and covariance."""
    s = copy.deepcopy(task)
    ci = a.MAPS.index(s['map']) * 20 + (s['players'] - 2) * 4 + 2 * (s['variant'] == 'recharged') + s['fastBid']
    n, deal, focal = s['players'], s['deal'], s['focalSeat']
    counts = {c: dict.fromkeys(a.PHASES, 0) for c in a.CONTROLLERS}
    seats = []
    for seat, controller in enumerate(s['controllers']):
        counter = {phase: 2 + (ci + deal + seat + j) % 3 for j, phase in enumerate(a.PHASES)}
        seats.append(counter)
        for phase, actions in counter.items():
            if controller in a.MODELS:
                fixed = 'fixedV2' if controller in a.EXPERT_MODELS else 'fixedV1'
                learned = actions - 1 if phase in ('Auction', 'Building') else 0
                counts[controller][phase] += learned
                counts[fixed][phase] += actions - learned
            else:
                counts[controller][phase] += actions
    code = (ci + 3 * deal + focal) % 7
    if code == 6:
        winners = list(range(n))
    elif code < {'replica1': 4, 'replica2': 1, 'ppo2': 2}[s['policy']]:
        winners = [focal]
    else:
        winners = [(focal + 1 + (ci + deal) % (n - 1)) % n]
    credits = [1 / len(winners) if seat in winners else 0 for seat in range(n)]
    requests = {c: sum(counts[c].values()) for c in a.MODELS}
    references = sum(counts['reference'].values())
    return dict(spec=s, terminal=True, credit=credits[focal], allSeatCredit=credits,
        steps=sum(sum(c.values()) for c in seats), rounds=1 + deal,
        counts=counts, seatCounts=seats,
        publicChecks=dict(hiddenInvariant=references, referenceAtomicLegal=references,
                          fullMenuPrior=sum(requests.values()), expertAtomicLegal=0),
        policyRequests=requests, referenceRequests=references,
        featureMs=.125 * (focal + 1), inferenceMs=.25, referenceMs=.5 if references else 0., seconds=1.5)


def fixture_provenance():
    """FAKE configs with real pinned source maps, NOT provenance/checkpoints."""
    frozen = a.protocol()
    historical = frozen['ppo0HistoricalTraining']
    current_sources = {name: frozen['frozenSources'][name] for name in historical['sourceFiles']}
    out = {}
    for name in a.MODELS:
        expert = name in a.EXPERT_MODELS
        config = dict(protocol={'fixtureOnly': True}, smoke=False, generatorDigest='1' * 64,
                      sourceFiles={'fixture.py': '2' * 64} if expert else dict(current_sources))
        if expert:
            config.update(schema='multimap-expert-replica-identity-v1' if name.startswith('replica') else
                'multimap-expert-training-identity-v2', engineDependencies={'fixture': '1'},
                referenceSourceFiles={'fixture.py': '3' * 64}, referenceManifestSha256='4' * 64,
                referenceFiles=1, runtimeVersions={'fixture': '1'}, execution={'workers': 6},
                sourcePins={'fixtureOnly': True})
        if name.startswith('replica'):
            config.update(replica=int(name[-1]), replicaStudy={'fixtureOnly': True})
        out[name] = dict(pin=a.MODEL_PINS[name], config=config,
            role='focal-only' if name.startswith('replica') else
                 'shared-focal-control-and-opponent' if name == 'ppo2' else 'opponent-only')
    out['ppo0'].update(checkpointConfig=copy.deepcopy(dict(out['ppo0']['config'],
        sourceFiles=historical['sourceFiles'])), historicalTrainingSource=copy.deepcopy(historical))
    return out


def manifest(root):
    value = {p.relative_to(root).as_posix(): a.digest(p) for p in root.rglob('*')
             if p.is_file() and p.name != 'artifacts.json'}
    write(root / 'artifacts.json', value)
    return value


def fixture_snapshot(root, panel, *, batch_count=640, saved_summary=None):
    protocol = a.protocol()
    identity = dict(schema='multimap-replica-stress-identity-v1', protocol=protocol, panel=panel,
        smoke=False, tasks=a.expected_tasks(panel), modelProvenance=fixture_provenance(),
        sourceFiles={name: 'a' * 64 for name in a.SOURCE_NAMES}, frozenSources=protocol['frozenSources'],
        workers=6, threads=1, collector='lockstep-central-torch-child-processes', fitting=False,
        selection=False, qualificationEligible=False, reservedFinalSeedsUsed=False)
    group = 'multimap-replica-stress-20261109-v1'
    status = dict(run=group + '-' + panel, workflow='replica-stress-v1', group=group,
        panel=panel, smoke=False, segment=1, slot=panel, workers=6, protocol=protocol,
        sourceRepo='coyotte508/powergrid-ai-training-v1', sourcePath=f'multimap/{group}/source.tgz',
        sourceRevision='c' * 40, sourceCommit='d' * 40, sourceSha256='e' * 64,
        qualified=False, qualificationEligible=False, reservedFinalSeedsUsed=False,
        stage='complete' if batch_count == 640 else 'failed',
        receipts=[dict(stage=label, revision=f'{i+1:040x}') for i, label in enumerate(
            ['runtime-ready', *(f'batches-{n}' for n in range(16, batch_count+1, 16))])])
    if batch_count != 640:
        status['error'] = {'code': 'replica-stress-job-stopped'}
    games = []
    for index, tasks in enumerate(a.expected_batches(panel)[:batch_count]):
        rows = [outcome(t) for t in tasks]
        games.extend(rows)
        write(root / f'study/batch-{index:03}.json', dict(schema='multimap-replica-stress-batch-v1',
            index=index, taskSha256=a.task_hash(tasks), games=rows))
    if batch_count == 640:
        saved = serving_summary(games, panel) if saved_summary is None else saved_summary
        write(root / 'study/summary.json', saved)
        status['result'] = saved
    for name, value in (('study/plan.json', identity), ('status.json', status), ('protocol.json', protocol),
                        ('environment.json', {'fixtureOnly': True}), ('recovery.json', {'fixtureOnly': True})):
        write(root / name, value)
    manifest(root)
    return games


def receipt_test_double(report):
    """UNIT TEST DOUBLE, not genuine evidence. Never use on a real artifact."""
    return dict(schema='multimap-replica-stress-external-integrity-v1',
        **copy.deepcopy(report['integrityBinding']), evidenceSha256='7' * 64,
        jobBudgetEvidenceSha256='8' * 64, checks={c: True for c in a.EXTERNAL_CHECKS},
        modelProjection=copy.deepcopy(report['expectedModelProjection']))


class PlanTests(unittest.TestCase):
    def test_all_15360_production_and_198_smoke_specs_match_python_and_js(self):
        plan = serving_planner()
        actual = plan(False)
        self.assertEqual(len(actual), 15360)
        for smoke in (False, True):
            for panel in a.PANELS:
                self.assertEqual([t for t in plan(smoke) if t['panel'] == panel],
                                 a.expected_tasks(panel, smoke=smoke))
        actual += plan(True)
        self.assertEqual(len(actual), 15558)
        for task in actual:
            plan.__globals__['_validate_spec'](task)
        script = """const fs=require('fs'); const g=require('./ai/multimap/replica_stress_game_v1.cjs');
          const tasks=JSON.parse(fs.readFileSync(0,'utf8'));
          for(const t of tasks) g.validateSpec(t);
          console.log(tasks.length);"""
        proc = subprocess.run(['node', '-e', script], input=json.dumps(actual), text=True,
            capture_output=True, cwd=a.HERE.parent.parent, check=True)
        self.assertEqual(proc.stdout.strip(), '15558')

    def test_literal_counts_roots_and_shared_control(self):
        roots = []
        for panel in a.PANELS:
            tasks = a.expected_tasks(panel)
            self.assertEqual(Counter(t['policy'] for t in tasks), dict.fromkeys(a.POLICIES, 2560))
            self.assertEqual(len({t['cell'] for t in tasks}), 80)
            self.assertEqual(set(t['deal'] for t in tasks), set(range(8)))
            roots.append(set(t['seed'] for t in tasks))
            for batch in a.expected_batches(panel):
                self.assertEqual(len(batch), 3 * batch[0]['players'])
                for i in range(0, len(batch), 3):
                    trio = batch[i:i+3]
                    focal = trio[0]['focalSeat']
                    self.assertEqual(len({t['seed'] for t in trio}), 1)
                    lineups = [[c for j, c in enumerate(t['controllers']) if j != focal] for t in trio]
                    self.assertEqual(lineups[0], lineups[1])
                    self.assertEqual(lineups[1], lineups[2])
                    self.assertFalse(set(lineups[0]) & {'replica1', 'replica2'})
        self.assertEqual([len(r) for r in roots], [640, 640])
        self.assertFalse(roots[0] & roots[1])
        self.assertTrue(all(s.startswith(a.NAMESPACE + ':') for r in roots for s in r))

    def test_actual_deal_not_modulo_four(self):
        tasks = a.expected_tasks('mixed')
        before = next(t for t in tasks if t['deal'] == 0)
        after = next(t for t in tasks if t['cell'] == before['cell'] and t['deal'] == 4)
        # Find an odd ordinal, where floor(i/2) differs after four deals.
        changed = 0
        for t in tasks:
            if t['deal'] < 4:
                continue
            ci = a.MAPS.index(t['map']) * 20 + (t['players'] - 2) * 4 + 2 * (t['variant'] == 'recharged') + t['fastBid']
            weak = ['ppo0', 'ppo1', 'ppo2', 'teacherV2'] + (['reference'] if t['map'] == 'Germany' else [])
            for seat in range(t['players']):
                if seat == t['focalSeat']:
                    continue
                i = ci + t['deal'] + ((seat - t['focalSeat'] + t['players']) % t['players'] - 1)
                expected = 'expert24' if i % 2 == 0 else weak[(i // 2) % len(weak)]
                self.assertEqual(t['controllers'][seat], expected)
                if i % 2 and weak[((i-4)//2) % len(weak)] != expected:
                    changed += 1
        self.assertGreater(changed, 0)
        self.assertEqual(before['deal'], 0)
        self.assertEqual(after['deal'], 4)

    def test_smoke_exact_scopes_and_rejected_production(self):
        planner = serving_planner()
        for panel in a.PANELS:
            tasks = a.expected_tasks(panel, smoke=True)
            self.assertEqual(tasks, [t for t in planner(True) if t['panel'] == panel])
            self.assertEqual(len(tasks), 99)
            self.assertEqual(len(a.expected_batches(panel, smoke=True)), 8)
            self.assertEqual({(t['map'], t['players'], t['variant'], t['fastBid']) for t in tasks}, set(a.SMOKE_SCOPES))
            self.assertTrue(all(':smoke:' in t['seed'] and t['deal'] == 0 for t in tasks))
            with self.assertRaises(ValueError):
                a.recompute_summary([outcome(t) for t in tasks], panel)

    def test_pins_and_protocol_frozen(self):
        frozen = a.protocol()
        self.assertEqual(frozen['expertOpponent'], a.MODEL_PINS['expert24'])
        self.assertEqual(frozen['replicas'], [a.MODEL_PINS['replica1'], a.MODEL_PINS['replica2']])
        self.assertEqual(a.MODEL_PINS['ppo2']['update'], 12)
        self.assertEqual(a.MODEL_PINS['ppo2']['revision'], 'af87f0b46382e4f06d420f339fd1a65a4ba9ef45')
        self.assertEqual(len(a.CONTROLLERS), 10)


class ProvenanceTests(unittest.TestCase):
    def test_real_source_pins_and_historical_full_config_mapping_without_checkpoints(self):
        frozen = a.protocol()
        history = frozen['ppo0HistoricalTraining']
        self.assertEqual(history, a.PPO0_HISTORICAL_TRAINING)
        self.assertEqual(history['sourceGit'], 'a3b492b650dec51c34b6f9322d87088b1e863f0e')
        self.assertEqual(len(history['sourceFiles']), 11)
        original = {}
        for name, expected in history['sourceFiles'].items():
            original[name] = subprocess.run(['git', 'show', history['sourceGit'] + ':ai/multimap/' + name],
                cwd=a.HERE, check=True, capture_output=True).stdout
            self.assertEqual(hashlib.sha256(original[name]).hexdigest(), expected, name)
        # Read-only verification of ALL current old modules, not an import or edit.
        for name, sha in frozen['frozenSources'].items():
            self.assertEqual(a.digest(a.HERE / name), sha, name)
        self.assertEqual(sorted(name for name, sha in history['sourceFiles'].items()
                                if sha != frozen['frozenSources'][name]), ['ppo.py', 'rollout.py'])

        # Execute only pure config constructors extracted from the authenticated
        # original Git object and current PPO source. No torch/checkpoint/game.
        protocol = a.read(a.HERE / 'ppo-protocol-v1.json')
        root = a.HERE.parent.parent
        generator_ns = dict(ROOT=root, hashlib=hashlib, json=json, digest=a.digest)
        tree = ast.parse(original['data.py'].decode())
        generator_function = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'generator_digest']
        exec(compile(ast.Module(body=generator_function, type_ignores=[]), '<original-generator-hashes>', 'exec'), generator_ns)
        common = dict(PROTOCOL=protocol, Path=Path, __file__=str(a.HERE / 'ppo.py'),
                      generator_digest=generator_ns['generator_digest'])
        old_ns = dict(common, digest=lambda path: hashlib.sha256(original[path.name]).hexdigest())
        tree = ast.parse(original['ppo.py'].decode())
        selected = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'config']
        exec(compile(ast.Module(body=selected, type_ignores=[]), '<original-ppo-config>', 'exec'), old_ns)
        original_config = old_ns['config'](False)
        current_ns = dict(common, digest=a.digest, copy=copy, _FROZEN_PROTOCOL=protocol)
        tree = ast.parse((a.HERE / 'ppo.py').read_text())
        selected = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in ('config', 'make_protocol')]
        exec(compile(ast.Module(body=selected, type_ignores=[]), '<current-ppo-config>', 'exec'), current_ns)
        serving = {name: record['config'] for name, record in fixture_provenance().items()}
        for number in range(3):
            serving[f'ppo{number}'] = current_ns['config'](False, current_ns['make_protocol'](number))
        before = copy.deepcopy(serving)
        ns = dict(PROTOCOL=frozen, FROZEN_SOURCES=frozen['frozenSources'], copy=copy,
                  DEFAULT_ARTIFACT=None, DEFAULT_REFERENCE_PYTHON=None, _protocol=lambda: frozen,
                  serving_configs=lambda *args: serving,
                  model_pins=lambda: [a.MODEL_PINS[n] for n in a.MODELS])
        tree = ast.parse((a.HERE / 'replica_stress_rollout_v1.py').read_text())
        selected = [n for n in tree.body if isinstance(n, ast.FunctionDef) and
                    n.name in ('_saved_configs', 'model_provenance')]
        exec(compile(ast.Module(body=selected, type_ignores=[]), '<serving-config-mapping>', 'exec'), ns)
        provenance = ns['model_provenance']()
        self.assertEqual(serving, before)  # Historical reconstruction cannot mutate runtime.
        self.assertEqual(provenance['ppo0']['config'], serving['ppo0'])
        self.assertEqual(provenance['ppo0']['checkpointConfig'], original_config)
        self.assertEqual(provenance['ppo0']['historicalTrainingSource'], history)
        projection = a._model_projection(provenance)
        for name in a.MODELS:
            expected = original_config if name == 'ppo0' else serving[name]
            self.assertEqual(projection[name]['configSha256'], a.task_hash(expected), name)
            if name != 'ppo0':
                self.assertEqual(set(provenance[name]), {'pin', 'role', 'config'})
        self.assertNotEqual(projection['ppo0']['configSha256'], a.task_hash(serving['ppo0']))

    def test_protocol_canonical_and_raw_pins_reject_forgery_or_reformatting(self):
        self.assertEqual(a.PROTOCOL_SHA256, '99d6e0e4eac7808f2de8c335361c5611ae4a93edfe8778b30dbe4139fb265d69')
        self.assertEqual(a.PROTOCOL_FILE_SHA256, '1ca5a8fd0979f785cec0656a8738fbc7d5b92f9eb70a9729e0c26ec7916477d3')
        original = (a.HERE / 'replica-stress-protocol-v1.json').read_bytes()
        self.assertEqual(hashlib.sha256(original).hexdigest(), a.PROTOCOL_FILE_SHA256)
        self.assertEqual(a.task_hash(a.protocol()), a.PROTOCOL_SHA256)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'replica-stress-protocol-v1.json'
            path.write_bytes(original + b'\n')
            with mock.patch.object(a, 'HERE', Path(directory)), self.assertRaisesRegex(ValueError, 'protocol bytes'):
                a.protocol()
            forged = json.loads(original)
            forged['ppo0HistoricalTraining']['sourceFiles']['ppo.py'] = '0' * 64
            write(path, forged)
            with mock.patch.object(a, 'HERE', Path(directory)), self.assertRaises(ValueError):
                a.protocol()
            # Even a mocked byte-hash oracle cannot bypass the canonical pin.
            with mock.patch.object(a, 'HERE', Path(directory)), mock.patch.object(a, 'digest', return_value=a.PROTOCOL_FILE_SHA256):
                with self.assertRaisesRegex(ValueError, 'protocol changed'):
                    a.protocol()

    def test_forged_training_exception_rejected_even_when_checkpoint_matches(self):
        mutations = [
            lambda h: h.__setitem__('sourceGit', '0' * 40),
            lambda h: h['sourceFiles'].__setitem__('ppo.py', '0' * 64),
            lambda h: h['sourceFiles'].__setitem__('rollout.py', '0' * 64),
            lambda h: h['sourceFiles'].__setitem__('model.py', '0' * 64),
            lambda h: h['sourceFiles'].pop('data.py'),
            lambda h: h['sourceFiles'].__setitem__('extra.py', '0' * 64),
            lambda h: h.__setitem__('nonservingDifferences', ['ppo.py']),
            lambda h: h.__setitem__('nonservingDifferences', ['model.py', 'ppo.py', 'rollout.py']),
            lambda h: h.__setitem__('nonservingDifferences', ['rollout.py', 'ppo.py']),
            lambda h: h.__setitem__('extra', True),
        ]
        for index, mutate in enumerate(mutations):
            with self.subTest(mutation=index):
                provenance = fixture_provenance()
                record = provenance['ppo0']
                mutate(record['historicalTrainingSource'])
                record['checkpointConfig']['sourceFiles'] = copy.deepcopy(record['historicalTrainingSource']['sourceFiles'])
                with self.assertRaisesRegex(ValueError, 'historical training provenance'):
                    a._model_projection(provenance)

    def test_current_serving_sources_must_be_exact_frozen_eleven(self):
        for model in a.PPO_MODELS:
            for name in a.PPO0_HISTORICAL_TRAINING['sourceFiles']:
                with self.subTest(model=model, source=name):
                    provenance = fixture_provenance()
                    provenance[model]['config']['sourceFiles'][name] = '0' * 64
                    with self.assertRaisesRegex(ValueError, 'current PPO serving sources'):
                        a._model_projection(provenance)
            for action in ('missing', 'extra', 'historical'):
                with self.subTest(model=model, action=action):
                    provenance = fixture_provenance()
                    sources = provenance[model]['config']['sourceFiles']
                    if action == 'missing':
                        sources.pop('data.py')
                    elif action == 'extra':
                        sources['extra.py'] = '0' * 64
                    else:
                        sources.update(a.PPO0_HISTORICAL_TRAINING['sourceFiles'])
                    with self.assertRaisesRegex(ValueError, 'current PPO serving sources'):
                        a._model_projection(provenance)

    def test_checkpoint_config_must_equal_entire_current_config_except_sources(self):
        mutations = [
            lambda c: c.__setitem__('generatorDigest', '0' * 64),
            lambda c: c.__setitem__('smoke', 0),
            lambda c: c['protocol'].__setitem__('fixtureOnly', 1),
            lambda c: c.__setitem__('extra', True),
            lambda c: c.pop('protocol'),
            lambda c: c['sourceFiles'].__setitem__('ppo.py', a.protocol()['frozenSources']['ppo.py']),
            lambda c: c['sourceFiles'].pop('game.cjs'),
        ]
        for index, mutate in enumerate(mutations):
            with self.subTest(mutation=index):
                provenance = fixture_provenance()
                mutate(provenance['ppo0']['checkpointConfig'])
                with self.assertRaisesRegex(ValueError, 'complete checkpoint config'):
                    a._model_projection(provenance)
        provenance = fixture_provenance()
        provenance['ppo0']['checkpointConfig'] = copy.deepcopy(provenance['ppo0']['config'])
        with self.assertRaisesRegex(ValueError, 'complete checkpoint config'):
            a._model_projection(provenance)

    def test_no_other_model_may_claim_historical_or_extra_provenance(self):
        for model in a.MODELS:
            for field in ('checkpointConfig', 'historicalTrainingSource', 'extra'):
                with self.subTest(model=model, field=field):
                    provenance = fixture_provenance()
                    if model == 'ppo0' and field != 'extra':
                        provenance[model].pop(field)  # Both are mandatory on PPO0.
                    else:
                        provenance[model][field] = {}
                    with self.assertRaisesRegex(ValueError, 'Model provenance schema'):
                        a._model_projection(provenance)
            provenance = fixture_provenance()
            provenance[model]['config']['extra'] = True
            with self.assertRaisesRegex(ValueError, 'Complete current serving config schema'):
                a._model_projection(provenance)


class OutcomeTests(unittest.TestCase):
    def setUp(self):
        self.tasks = a.expected_batches('mixed')[168]
        self.rows = [outcome(t) for t in self.tasks]
        self.batch = dict(schema='multimap-replica-stress-batch-v1', index=168,
                          taskSha256=a.task_hash(self.tasks), games=self.rows)

    def test_valid_ties_forced_actions_and_counters(self):
        a.verify_batch(self.batch, 168, self.tasks)
        for panel in a.PANELS:
            for tasks in a.expected_batches(panel)[::79]:
                for task in tasks:
                    a.validate_outcome(outcome(task), task)

    def test_missing_arm_duplicate_ppo_and_extra_rows(self):
        for mutate in (lambda b: b['games'].pop(), lambda b: b['games'].append(b['games'][2]),
                       lambda b: b['games'].__setitem__(1, b['games'][2])):
            batch = copy.deepcopy(self.batch)
            mutate(batch)
            with self.assertRaises(ValueError):
                a.verify_batch(batch, 168, self.tasks)

    def test_namespaces_types_hidden_and_routing(self):
        mutations = [
            lambda g: g['spec'].__setitem__('seed', g['spec']['seed'].replace(':mixed:', ':strong:')),
            lambda g: g['spec'].__setitem__('seed', 'pg-multimap-stress-20261103-v1:bad'),
            lambda g: g['spec'].__setitem__('fastBid', int(g['spec']['fastBid'])),
            lambda g: g['spec'].__setitem__('players', float(g['spec']['players'])),
            lambda g: g['spec'].__setitem__('smoke', True),
            lambda g: g['spec'].__setitem__('controllers', list(reversed(g['spec']['controllers']))),
            lambda g: g.__setitem__('terminal', 1),
            lambda g: g.__setitem__('credit', True),
            lambda g: g.__setitem__('seconds', float('inf')),
            lambda g: g.__setitem__('rounds', 0),
            lambda g: g['publicChecks'].__setitem__('hiddenInvariant', True),
            lambda g: g['publicChecks'].__setitem__('expertAtomicLegal', 1),
            lambda g: g['policyRequests'].__setitem__('replica1', 999),
            lambda g: g['counts']['replica1'].__setitem__('Resources', 1),
            lambda g: g['counts']['fixedV2'].__setitem__('Building', 0),
            lambda g: g['seatCounts'][0].__setitem__('Auction', 999),
            lambda g: g.__setitem__('state', {}),
            lambda g: g['allSeatCredit'].__setitem__(0, .123),
        ]
        for index, mutate in enumerate(mutations):
            with self.subTest(mutation=index):
                game = copy.deepcopy(self.rows[0])
                mutate(game)
                with self.assertRaises(ValueError):
                    a.validate_outcome(game, self.tasks[0])

    def test_all_raw_keys_forbidden_at_any_depth(self):
        for key in a.FORBIDDEN:
            with self.assertRaises(ValueError):
                a.compact_json({'metadata': [{'more': {key: []}}]})


class MathTests(unittest.TestCase):
    def test_paired_covariance_not_independent_arm_se(self):
        control = [0., 1.] * 4
        same = control[:]
        opposite = [1-x for x in control]
        self.assertEqual(statistics.mean(same), statistics.mean(opposite))
        zero = a.estimate({'c': [x-y for x, y in zip(same, control)]})
        varying = a.estimate({'c': [x-y for x, y in zip(opposite, control)]})
        self.assertEqual(zero['standardError'], 0)
        self.assertGreater(varying['standardError'], 0)
        self.assertAlmostEqual(varying['standardError'], math.sqrt(statistics.variance([-1, 1]*4) / 8))
        self.assertNotAlmostEqual(varying['standardError'], math.sqrt(2 * statistics.variance(control) / 8))

    def test_eight_deals_equal_eighty_cells_and_four_z(self):
        strata = {str(c): [((c+3*d) % 11 - 5) / 10 for d in range(8)] for c in range(80)}
        result = a.estimate(strata, primary=True)
        mean = statistics.mean(statistics.mean(v) for v in strata.values())
        se = math.sqrt(sum(statistics.variance(v) / 8 for v in strata.values())) / 80
        self.assertAlmostEqual(result['mean'], mean)
        self.assertAlmostEqual(result['standardError'], se)
        self.assertEqual(result['independentDeals'], 640)
        self.assertAlmostEqual(result['approximateNormal95'][1], mean + 1.96*se)
        self.assertAlmostEqual(result['fourPrimaryBonferroniNormal9875'][0], mean - 2.4977054744123737*se)
        self.assertEqual(a.estimate({'small': [1., 1.], 'large': [0.] * 8})['mean'], .5)
        with self.assertRaises(ValueError):
            a.estimate({'c': [0.] * 8}, primary=True)

    def test_sparse_occupancy_uses_analytic_weights_not_fake_games(self):
        table = {'one': {3: dict(replica1=.5, replica2=0., ppo2=0.)},
                 'two': {1: dict(replica1=.5, replica2=0., ppo2=0.),
                         7: dict(replica1=.5, replica2=0., ppo2=0.)}}
        result = a._occupancy_scores(table)['replica1MinusPpo2']
        self.assertEqual(result['mean'], .5)
        self.assertEqual(result['independentDeals'], 16)
        self.assertEqual(result['selectedDeals'], 3)
        self.assertEqual(result['selectedDealsByCell'], {'one': 1, 'two': 2})
        expected = math.sqrt(statistics.variance([4.] + [0.]*7)/8 +
                             statistics.variance([2.]*2 + [0.]*6)/8) / 2
        self.assertAlmostEqual(result['standardError'], expected)
        self.assertNotIn('fourPrimaryBonferroniNormal9875', result)

    def test_n_one_and_zero_se_caveat(self):
        self.assertIsNone(a.estimate({'c': [1.]})['standardError'])
        self.assertIsNone(a.estimate({'c': [1.]})['approximateNormal95'])
        self.assertEqual(a.estimate({'c': [1.] * 8})['approximateNormal95'], [1., 1.])
        self.assertTrue(any('zero estimated SE' in s for s in a.CAVEATS))
        self.assertTrue(any('not unbiased' in s for s in a.CAVEATS))
        self.assertTrue(any('does not require independence' in s for s in a.CAVEATS))


class SnapshotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        cls.roots = {p: cls.root / p for p in a.PANELS}
        cls.games = {p: fixture_snapshot(cls.roots[p], p) for p in a.PANELS}
        cls.reports = {p: a.audit_panel(cls.roots[p], p) for p in a.PANELS}

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    @contextmanager
    def changed(self, name, mutate, *, panel='strong', rehash=True):
        root = self.roots[panel]
        path = root / name
        old, old_manifest = path.read_bytes(), (root / 'artifacts.json').read_bytes()
        try:
            value = a.read(path)
            mutate(value)
            write(path, value)
            if rehash:
                manifest(root)
            yield root
        finally:
            path.write_bytes(old)
            (root / 'artifacts.json').write_bytes(old_manifest)

    def test_both_json_complete_still_no_strength(self):
        result = a.report_all(self.roots, statuses={'strong': 'COMPLETED', 'mixed': 'ERROR Job timeout'})
        self.assertTrue(result['bothPanelsComplete'])
        self.assertFalse(result['strengthStatisticsReleased'])
        self.assertIsNone(result['primaryContrasts'])
        self.assertEqual(result['counts']['games'], 15360)
        for panel in a.PANELS:
            self.assertNotIn('summary', result['panels'][panel])
            self.assertEqual(result['panels'][panel]['status'], 'integrity-pending')
            self.assertEqual(result['panels'][panel]['counts']['gamesByPolicy']['ppo2'], 2560)
        self.assertEqual(result['panels']['mixed']['operationalStatus'], 'ERROR Job timeout')

    def test_test_double_external_attestation_releases_all_four_together(self):
        receipts = {p: receipt_test_double(self.reports[p]) for p in a.PANELS}
        result = a.report_all(self.roots, integrity=receipts)
        self.assertTrue(result['strengthStatisticsReleased'])
        self.assertEqual(len(result['primaryContrasts']), 4)
        self.assertEqual(result['counts']['games'], 15360)
        for p in a.PANELS:
            summary = result['panels'][p]['summary']
            self.assertLess(summary['primary']['replica2MinusPpo2']['mean'], 0)
            self.assertGreater(summary['primary']['replica1MinusPpo2']['mean'], 0)
            self.assertEqual(len(summary['subgroups']), 114)
            self.assertEqual(len(summary['cellDealMeans']), 80)
            self.assertEqual(summary['reciprocalTwoPlayerGames'], 768)
            self.assertNotIn('homogeneousExpertDealControls', summary)
            self.assertFalse(summary['betweenReplicaSpread']['trainingVarianceEstimate'])
            self.assertNotIn('fourPrimaryBonferroniNormal9875', summary['subgroups']['map:USA']['replica1MinusPpo2'])
            for replica in a.POLICIES[:2]:
                # Independent sample-variance oracle, before any saved-summary formatting.
                means = summary['cellDealMeans']
                differences = {c: [d[replica]-d['ppo2'] for d in ds.values()] for c, ds in means.items()}
                se = math.sqrt(sum(statistics.variance(v)/8 for v in differences.values())) / 80
                self.assertAlmostEqual(summary['primary'][replica+'MinusPpo2']['standardError'], se)

    def test_only_four_adjusted_fields_in_joint_json_and_exact_runner_summary(self):
        key = 'fourPrimaryBonferroniNormal9875'
        receipts = {p: receipt_test_double(self.reports[p]) for p in a.PANELS}
        result = json.loads(a.canonical(a.report_all(self.roots, integrity=receipts)))
        expected_paths = {('panels', p, 'summary', 'primary', replica + 'MinusPpo2', key)
                          for p in a.PANELS for replica in a.POLICIES[:2]}
        self.assertEqual(set(field_paths(result, key)), expected_paths)
        self.assertEqual(len(field_paths(result, key)), 4)
        self.assertFalse(result['winnerSelection'])
        self.assertFalse(result['automaticProgression'])
        self.assertFalse(result['pooledInference'])
        for panel in a.PANELS:
            independent = a.recompute_summary(self.games[panel], panel)
            runner = serving_summary(self.games[panel], panel)
            a.equal(runner, a._runner_summary(independent))
            self.assertEqual(set(field_paths(runner, key)),
                             {('primary', p, key) for p in a.POLICIES[:2]})
            self.assertEqual(len(runner['subgroups']), 114)
            self.assertEqual(set(independent['watchpoints']), set(a.WATCHPOINTS))
            self.assertEqual(set(runner['watchpoints']), set(a.WATCHPOINTS))
            for watchpoint in a.WATCHPOINTS:
                self.assertEqual(independent['watchpoints'][watchpoint], independent['subgroups'][watchpoint])
            for replica in a.POLICIES[:2]:
                pointer = result['primaryContrasts'][panel + ':' + replica + 'MinusPpo2']
                self.assertEqual(pointer, '/panels/' + panel + '/summary/primary/' + replica + 'MinusPpo2')
                target = result
                for part in pointer.lstrip('/').split('/'):
                    target = target[part]
                self.assertIn(key, target)
            for group in ('subgroups', 'strongOpponentOccupancy', 'watchpoints'):
                for scores in runner[group].values():
                    for estimate in scores.values():
                        self.assertIn('approximateNormal95', estimate)
                        self.assertNotIn(key, estimate)
            for estimate in runner['subgroups']['allMaps'].values():
                self.assertEqual(estimate['independentDeals'], 640)
            for scores in runner['strongOpponentOccupancy'].values():
                for estimate in scores.values():
                    self.assertEqual(estimate['independentDeals'], 8 * estimate['cells'])
                    self.assertEqual(estimate['selectedDeals'], sum(estimate['selectedDealsByCell'].values()))
                    self.assertTrue(all(1 <= k <= 8 for k in estimate['selectedDealsByCell'].values()))
            if panel == 'strong':
                for estimate in runner['GermanyAnalyticalReferenceBenchmark']['replicaMinusNeutral'].values():
                    self.assertIn('approximateNormal95', estimate)
                    self.assertNotIn(key, estimate)

    def test_adjusted_nonprimary_fields_or_missing_primary_are_rejected(self):
        key = 'fourPrimaryBonferroniNormal9875'
        mutations = [
            lambda s: s['subgroups']['allMaps']['replica1MinusPpo2'].__setitem__(key, [0, 1]),
            lambda s: s['subgroups']['allMaps']['ppo2'].__setitem__(key, None),
            lambda s: s['subgroups']['cell:Germany|2|original|0']['replica1'].__setitem__(key, [0, 1]),
            lambda s: s['strongOpponentOccupancy']['1']['replica1MinusPpo2'].__setitem__(key, [0, 1]),
            lambda s: s['watchpoints'][a.WATCHPOINTS[0]]['replica2MinusPpo2'].__setitem__(key, [0, 1]),
            lambda s: s['GermanyAnalyticalReferenceBenchmark']['replicaMinusNeutral']['replica1'].__setitem__(key, [0, 1]),
            lambda s: s['primary']['replica1'].pop(key),
        ]
        for index, mutate in enumerate(mutations):
            with self.subTest(mutation=index), self.changed('study/summary.json', mutate) as root:
                saved = a.read(root / 'study/summary.json')
                # Keep status/manifest self-consistent: rejection must come from
                # independent exact schema/math recomputation, not a stale copy.
                with self.changed('status.json', lambda s: s.__setitem__('result', saved)):
                    with self.assertRaisesRegex(ValueError, 'Saved versus independent summary'):
                        a.audit_panel(root, 'strong')

    def test_saved_config_projection_and_complete_current_runtime_binding(self):
        for panel in a.PANELS:
            root = self.roots[panel]
            provenance = a.read(root / 'study/plan.json')['modelProvenance']
            report = self.reports[panel]
            self.assertEqual(report['integrityBinding']['runtimeIdentitySha256'], a.task_hash(dict(
                modelProvenance=provenance, environment=a.read(root / 'environment.json'),
                recovery=a.read(root / 'recovery.json'))))
            self.assertEqual(report['expectedModelProjection']['ppo0']['configSha256'],
                             a.task_hash(provenance['ppo0']['checkpointConfig']))
            self.assertNotEqual(report['expectedModelProjection']['ppo0']['configSha256'],
                                a.task_hash(provenance['ppo0']['config']))
            receipt = receipt_test_double(report)
            receipt['modelProjection']['ppo0']['configSha256'] = a.task_hash(provenance['ppo0']['config'])
            with self.assertRaisesRegex(ValueError, 'Decoded fixed model/config projection'):
                a.validate_integrity(receipt, report)
            # The externally attested runtime hash must include the WHOLE record,
            # not a projection containing only checkpointConfig or current config.
            receipt = receipt_test_double(report)
            provenance['ppo0'].pop('checkpointConfig')
            provenance['ppo0'].pop('historicalTrainingSource')
            receipt['runtimeIdentitySha256'] = a.task_hash(dict(modelProvenance=provenance,
                environment=a.read(root / 'environment.json'), recovery=a.read(root / 'recovery.json')))
            with self.assertRaisesRegex(ValueError, 'runtimeIdentitySha256'):
                a.validate_integrity(receipt, report)

    def test_no_completed_subset_inference(self):
        result = a.report_all({'strong': self.roots['strong'], 'mixed': None},
            integrity={'strong': receipt_test_double(self.reports['strong'])}, statuses={'mixed': 'FAILED'})
        self.assertFalse(result['strengthStatisticsReleased'])
        self.assertNotIn('summary', result['panels']['strong'])
        self.assertEqual(result['panels']['mixed']['status'], 'missing')
        self.assertEqual(result['panels']['mixed']['operationalStatus'], 'FAILED')
        self.assertEqual(result['counts']['games'], 7680)

    def test_receipt_schema_evidence_checks_and_binding(self):
        report = self.reports['strong']
        mutations = [
            lambda r: r.pop('evidenceSha256'),
            lambda r: r.__setitem__('evidenceSha256', 'not-evidence'),
            lambda r: r.__setitem__('manifestSha256', '0'*64),
            lambda r: r.__setitem__('sourceIdentitySha256', '0'*64),
            lambda r: r.__setitem__('runtimeIdentitySha256', '0'*64),
            lambda r: r.__setitem__('fullTaskSha256', '0'*64),
            lambda r: r.__setitem__('panel', 'mixed'),
            lambda r: r['checks'].__setitem__(a.EXTERNAL_CHECKS[0], 1),
            lambda r: r['checks'].pop(a.EXTERNAL_CHECKS[-1]),
            lambda r: r['modelProjection']['replica2'].__setitem__('update', 24),
            lambda r: r['modelProjection']['ppo2'].__setitem__('configSha256', '0'*64),
            lambda r: r['committedBatchSha256'].__setitem__('study/batch-000.json', '0'*64),
        ]
        for mutate in mutations:
            receipt = receipt_test_double(report)
            mutate(receipt)
            with self.assertRaises(ValueError):
                a.validate_integrity(receipt, report)
        with self.assertRaises(ValueError):
            a.validate_integrity({'allChecksPassed': True}, report)

    def test_manifest_summary_and_raw_adversaries(self):
        mutations = [
            ('study/batch-000.json', lambda r: r['games'].append(r['games'][2]), True),
            ('study/batch-000.json', lambda r: r['games'].pop(1), True),
            ('study/batch-000.json', lambda r: r['games'][0]['publicChecks'].__setitem__('hiddenInvariant', 0), True),
            ('study/batch-000.json', lambda r: r['games'][0].__setitem__('seconds', 99.), False),
            ('study/summary.json', lambda r: r['primary']['replica1'].__setitem__('mean', 1.), True),
            ('study/summary.json', lambda r: r.__setitem__('rows', []), True),
            ('study/plan.json', lambda r: r.__setitem__('smoke', True), True),
            ('study/plan.json', lambda r: r['tasks'][0].__setitem__('fastBid', 0), True),
            ('study/plan.json', lambda r: r['modelProvenance']['replica1']['pin'].__setitem__('revision', '0'*40), True),
            ('environment.json', lambda r: r.__setitem__('trajectory', []), True),
            ('status.json', lambda r: r.__setitem__('segment', True), True),
        ]
        for name, mutate, rehash in mutations:
            with self.subTest(name=name), self.changed(name, mutate, rehash=rehash) as root:
                with self.assertRaises(ValueError):
                    a.audit_panel(root, 'strong')

    def test_extra_stale_missing_gap_and_symlink(self):
        root = self.roots['strong']
        for name in ('study/rows.json', 'study/batch-000.json.tmp', 'artifacts.json.tmp', '.hidden'):
            path = root / name
            try:
                path.write_text('{}')
                with self.assertRaises(ValueError):
                    a.audit_panel(root, 'strong')
            finally:
                path.unlink()
        path = root / 'study/batch-001.json'
        backup = path.read_bytes()
        old_manifest = (root / 'artifacts.json').read_bytes()
        try:
            path.unlink()
            manifest(root)
            with self.assertRaises(ValueError):
                a.audit_panel(root, 'strong')
            path.symlink_to(root / 'study/batch-000.json')
            with self.assertRaises(ValueError):
                a.audit_panel(root, 'strong')
        finally:
            path.unlink(missing_ok=True)
            path.write_bytes(backup)
            (root / 'artifacts.json').write_bytes(old_manifest)

    def test_manifest_limits_and_duplicate_nonfinite_json(self):
        root = self.roots['strong']
        with mock.patch.object(a, 'LIMIT', 100):
            with self.assertRaises(ValueError):
                a.audit_panel(root, 'strong')
        path = root / 'artifacts.json'
        backup = path.read_bytes()
        try:
            path.write_bytes(b' ' * (65536+1))
            with self.assertRaises(ValueError):
                a.audit_panel(root, 'strong')
        finally:
            path.write_bytes(backup)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'bad.json'
            for text in ('{"a":1,"a":2}', '{"a":NaN}', '{"a":Infinity}', '{"a":1e999}'):
                path.write_text(text)
                with self.assertRaises(ValueError):
                    a.read(path)

    def test_crosspanel_root_and_source_mismatch(self):
        with self.assertRaises(ValueError):
            a.report_all({'strong': self.roots['strong'], 'mixed': self.roots['strong']})
        with self.assertRaises(ValueError):
            a.report_all({'strong': self.roots['strong']})
        with self.changed('study/batch-000.json', lambda r: r['games'][0]['spec'].__setitem__('seed',
                r['games'][0]['spec']['seed'].replace(':mixed:', ':strong:')), panel='mixed') as root:
            with self.assertRaises(ValueError):
                a.audit_panel(root, 'mixed')
        receipts = {p: receipt_test_double(self.reports[p]) for p in a.PANELS}
        receipts['mixed']['jobBudgetEvidenceSha256'] = '9'*64
        with self.assertRaises(ValueError):
            a.report_all(self.roots, integrity=receipts)

    def test_no_neutral_credit_symmetry_assertion(self):
        summary = a.recompute_summary(self.games['strong'], 'strong')
        means = summary['cellDealMeans']
        self.assertTrue(any(abs(d['replica1'] - 1/int(c.split('|')[1])) > .1
            for c, ds in means.items() if not c.startswith('Germany|') for d in ds.values()))
        self.assertEqual(summary['GermanyAnalyticalReferenceBenchmark']['benchmark'], .29)
        self.assertEqual(summary['GermanyAnalyticalReferenceBenchmark']['newlyPlayedReferenceControlGames'], 0)


class PartialAndResumeTests(unittest.TestCase):
    def test_partial_failed_counts_and_no_stats(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'partial'
            games = fixture_snapshot(root, 'strong', batch_count=3)
            report = a.report_all(dict(strong=root, mixed=None), statuses={'strong': 'ERROR Job timeout'})
            self.assertEqual(report['panels']['strong']['status'], 'incomplete')
            self.assertEqual(report['panels']['strong']['workerStage'], 'failed')
            self.assertEqual(report['counts']['games'], len(games))
            self.assertFalse(report['strengthStatisticsReleased'])
            self.assertNotIn('summary', report['panels']['strong'])

    def test_committed_prefix_exact_but_uncommitted_timing_can_replay(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'resume'
            fixture_snapshot(root, 'strong', batch_count=2)
            original = a.read(root / 'artifacts.json')
            original.pop('study/batch-001.json')  # Only batch zero was remotely committed.
            status = a.read(root / 'status.json')
            status.update(run='multimap-replica-stress-20261109-v1-recovery-strong', segment=2,
                slot='recovery', resume=dict(run='multimap-replica-stress-20261109-v1-strong', revision='f'*40,
                    manifestSha256='6'*64, totalBytes=1000,
                    files={n: s for n, s in original.items() if n.startswith('study/')},
                    allFileHashes=original, transaction=dict(committedBatches=1, committedGames=6,
                        complete=False, planSha256=original['study/plan.json'])))
            write(root / 'status.json', status)
            path = root / 'study/batch-001.json'
            replay = a.read(path)
            replay['games'][0]['seconds'] += 10
            write(path, replay)
            manifest(root)
            report = a.audit_panel(root, 'strong')
            self.assertEqual(report['counts']['batches'], 2)
            self.assertEqual(report['counts']['games'], 12)
            path = root / 'study/batch-000.json'
            changed = a.read(path)
            changed['games'][0]['seconds'] += 1
            write(path, changed)
            manifest(root)
            with self.assertRaisesRegex(ValueError, 'Committed prefix changed'):
                a.audit_panel(root, 'strong')

    def test_invalid_keeps_observed_counts_and_failure_visible(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'invalid'
            fixture_snapshot(root, 'mixed', batch_count=2)
            path = root / 'study/batch-000.json'
            record = a.read(path)
            record['games'][0]['terminal'] = False
            write(path, record)
            manifest(root)
            result = a.report_all(dict(strong=None, mixed=root), statuses={'mixed': 'ERROR'})
            self.assertEqual(result['panels']['mixed']['status'], 'invalid-or-incomplete')
            self.assertEqual(result['panels']['mixed']['counts']['games'], 12)
            self.assertFalse(result['panels']['mixed']['counts']['verified'])
            self.assertIsNone(result['primaryContrasts'])
            self.assertEqual(result['panels']['mixed']['operationalStatus'], 'ERROR')


if __name__ == '__main__':
    unittest.main()
