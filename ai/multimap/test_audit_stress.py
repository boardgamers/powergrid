"""Standalone stdlib-only adversarial audit tests; synthetic games are NOT evidence.

Run: python3 -B -m unittest discover -s ai/multimap -p test_audit_stress.py
No serving analysis/planner, models, downloads, launch, or engine is invoked.
The full 640-batch fixture uses separately implemented statistics.mean/variance
as its saved-summary oracle; the auditor uses fsum and its own sample variance.
"""
from collections import defaultdict
from contextlib import contextmanager
import copy
import hashlib
import json
import math
from pathlib import Path
import statistics
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import audit_stress as a


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, separators=(',', ':'), allow_nan=False) + '\n')


def outcome(task):
    """Varied seat/phase counts, learned forced moves, ties and paired covariance."""
    s = copy.deepcopy(task)
    ci = a.MAPS.index(s['map']) * 20 + (s['players'] - 2) * 4 + 2 * (s['variant'] == 'recharged') + s['fastBid']
    n, deal, focal = s['players'], s['deal'], s['focalSeat']
    counts = {c: dict.fromkeys(a.PHASES, 0) for c in a.CONTROLLERS}
    seats = []
    for seat, controller in enumerate(s['controllers']):
        counter = {p: 2 + (ci + deal + seat + j) % 3 for j, p in enumerate(a.PHASES)}
        seats.append(counter)
        for phase, actions in counter.items():
            if controller in a.MODELS:
                fixed = 'fixedV2' if controller == 'expert24' else 'fixedV1'
                learned = actions - 1 if phase in ('Auction', 'Building') else 0
                counts[controller][phase] += learned
                counts[fixed][phase] += actions - learned
            else:
                counts[controller][phase] += actions
    if s['panel'] == 'strong' and s['map'] != 'Germany' and s['policy'] == 'expert24':
        winner = (ci + 2 * deal) % n
        winners = [winner] if (ci + deal) % 5 else [winner, (winner + 1) % n]
    else:
        code = (ci + 3 * deal + focal) % 7
        if code == 6:
            winners = list(range(n))
        elif code < (4 if s['policy'] == 'expert24' else 2):
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


def oracle_estimate(strata):
    means = [statistics.mean(v) for v in strata.values()]
    mean = statistics.mean(means)
    se = (math.sqrt(sum(statistics.variance(v) / len(v) for v in strata.values())) / len(strata)
          if all(len(v) > 1 for v in strata.values()) else None)
    return dict(mean=mean, standardError=se, cells=len(strata), independentDeals=sum(map(len, strata.values())),
        approximateNormal95=None if se is None else [mean - 1.96 * se, mean + 1.96 * se],
        twoPrimaryBonferroniNormal975=None if se is None else [mean - 2.241402727604947 * se, mean + 2.241402727604947 * se])


def oracle_summary(games, panel):
    """Separate test oracle, not the auditor or frozen study arithmetic."""
    pairs = defaultdict(dict)
    for g in games:
        s = g['spec']
        pairs[s['cell'], s['deal'], s['focalSeat']][s['policy']] = g
    table = defaultdict(lambda: defaultdict(list))
    occupancy = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    for (cell, deal, seat), arms in pairs.items():
        row = (arms['expert24']['credit'], arms['ppo2']['credit'])
        table[cell][deal].append(row)
        names = arms['expert24']['spec']['controllers']
        strong = sum(name in ('expert24', 'reference') for i, name in enumerate(names) if i != seat)
        occupancy[str(strong)][cell][deal].append(row)

    def scores(cells):
        answer = {}
        for label in ('expert24', 'ppo2', 'pairedDifference'):
            strata = {}
            for c, deals in cells.items():
                strata[c] = []
                for rows in deals.values():
                    values = [x if label == 'expert24' else y if label == 'ppo2' else x - y for x, y in rows]
                    strata[c].append(statistics.mean(values))
            answer[label] = oracle_estimate(strata)
        return answer

    subsets = {'allMaps': list(table)}
    for c in table:
        m, n, v, f = c.split('|')
        for label in ('map:' + m, 'players:' + n, 'rule:' + v + '|' + f, 'mapPlayers:' + m + '|' + n):
            subsets.setdefault(label, []).append(c)
    subgroups = {label: scores({c: table[c] for c in cs}) for label, cs in subsets.items()}
    primary = subgroups['allMaps']['pairedDifference']
    reciprocal = []
    for c in table:
        if c.split('|')[1] != '2':
            continue
        for d in range(4):
            rows = [pairs[c, d, seat] for seat in (0, 1)]
            reciprocal.append(dict(cell=c, deal=d, opponent=rows[0]['expert24']['spec']['controllers'][1],
                expert24ByFocalSeat=[r['expert24']['credit'] for r in rows],
                ppo2ByFocalSeat=[r['ppo2']['credit'] for r in rows],
                allSeatCredits={p: [r[p]['allSeatCredit'] for r in rows] for p in a.POLICIES}))
    germany = None
    if panel == 'strong':
        germany = dict(benchmark=.29, newlyPlayedReferenceControlGames=0,
            selectedMinusNeutral=oracle_estimate({c: [statistics.mean(x for x, _ in rows) - 1 / int(c.split('|')[1])
                for rows in ds.values()] for c, ds in table.items() if c.startswith('Germany|')}),
            note='Analytical all-reference 1/n neutrality, not an additional played control; smoke grid is not balanced.')
    passed = primary['twoPrimaryBonferroniNormal975'][0] > 0 and all(
        subgroups['map:' + m]['pairedDifference']['mean'] >= -.05 for m in a.MAPS)
    return dict(schema='multimap-stress-summary-v1', panel=panel, smoke=False, games=len(games), failures=0,
        primary=primary, subgroups=subgroups, strongOpponentOccupancy={k: scores(v) for k, v in occupancy.items()},
        reciprocalTwoPlayerGames=256, reciprocalTwoPlayerOutcomes=reciprocal,
        GermanyAnalyticalReferenceBenchmark=germany, homogeneousExpertDealControls=240 if panel == 'strong' else 0,
        cellDealMeans={c: {str(d): dict(expert24=statistics.mean(x for x, _ in rows),
                                       ppo2=statistics.mean(y for _, y in rows)) for d, rows in ds.items()}
                       for c, ds in table.items()},
        panelResearchProgressionGate=passed, bothPanelsRequired=True, caveats=list(a.CAVEATS),
        qualified=False, qualificationEligible=False, reservedFinalSeedsUsed=False)


def snapshot(root, panel):
    tasks = a.expected_tasks(panel)
    games = [outcome(t) for t in tasks]
    summary = oracle_summary(games, panel)
    protocol = a.read(a.HERE / 'stress-protocol-v1.json')
    identity = dict(schema='multimap-stress-identity-v1', protocol=protocol, panel=panel, smoke=False,
        tasks=tasks, expertIdentity={'fixtureRuntimeIdentity': 'externally verified by caller'},
        sourceFiles={n: hashlib.sha256((a.HERE / n).read_bytes()).hexdigest() for n in a.SOURCE_NAMES},
        workers=6, threads=1, collector='lockstep-central-torch-child-processes',
        fitting=False, selection=False, qualificationEligible=False, reservedFinalSeedsUsed=False)
    write(root / 'study/plan.json', identity)
    write(root / 'study/summary.json', summary)
    offset = 0
    for i, batch in enumerate(a.expected_batches(panel)):
        write(root / f'study/batch-{i:03}.json', dict(schema='multimap-stress-batch-v1', index=i,
            taskSha256=a.task_hash(batch), games=games[offset:offset + len(batch)]))
        offset += len(batch)
    stages = ['runtime-ready', *(f'batches-{i}' for i in range(16, 321, 16)), 'complete']
    status = dict(run=f'multimap-stress-20261103-v1-{panel}', workflow='stress', panel=panel, smoke=False,
        workers=6, sourceRevision=a.SOURCE_REVISION, sourceSha256=a.SOURCE_SHA256,
        sourceRepo='coyotte508/powergrid-ai-training-v1', sourcePath='multimap/multimap-stress-20261103-v1/source.tgz',
        protocol=protocol, qualified=False, qualificationEligible=False, reservedFinalSeedsUsed=False,
        stage='complete', receipts=[dict(stage=s, revision=f'{i + 1:040x}') for i, s in enumerate(stages)], result=summary)
    write(root / 'status.json', status)
    write(root / 'protocol.json', protocol)
    write(root / 'environment.json', {'fixtureOnly': 'source/runtime audit is external'})
    write(root / 'recovery.json', {'fixtureOnly': 'reference audit is external'})
    write(root / 'artifacts.json', {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                                  for p in root.rglob('*.json')})
    return games


@contextmanager
def changed(root, name, change):
    path = root / name
    original = path.read_bytes()
    value = json.loads(original)
    change(value)
    write(path, value)
    try:
        yield root
    finally:
        path.write_bytes(original)


class PlanAndArithmetic(unittest.TestCase):
    def test_full_literal_plan_matches_both_prelaunch_hashes(self):
        roots = []
        for panel in a.PANELS:
            tasks = a.expected_tasks(panel)
            self.assertEqual(len(tasks), 2560)
            self.assertEqual(a.task_hash(tasks), a.PLAN_HASHES[panel])
            self.assertEqual(len(a.expected_batches(panel)), 320)
            self.assertEqual({len(v) for v in a.expected_batches(panel)}, {4, 6, 8, 10, 12})
            self.assertEqual(len({(t['seed'], t['focalSeat'], t['policy']) for t in tasks}), 2560)
            self.assertEqual({t['map'] for t in tasks}, {'Germany', 'USA', 'France', 'UK & Ireland'})
            self.assertEqual({t['players'] for t in tasks}, {2, 3, 4, 5, 6})
            roots.append({t['seed'] for t in tasks})
        self.assertEqual(len(roots[0] | roots[1]), 640)
        self.assertFalse(roots[0] & roots[1])

    def test_planner_refuses_nonproduction_scopes(self):
        for panel in ('smoke', 'train', 'selection', 'final', 'Italy', 'Benelux', True, None):
            with self.subTest(panel=panel), self.assertRaises(ValueError):
                a.expected_tasks(panel)

    def test_independent_literal_mixed_rotation(self):
        # Germany ci=0, deal=1 gives weak ppo0 in both reciprocal seats.
        tasks = a.expected_batches('mixed')[1]
        self.assertEqual([t['controllers'] for t in tasks],
                         [['expert24', 'ppo0'], ['ppo2', 'ppo0'], ['ppo0', 'expert24'], ['ppo0', 'ppo2']])
        # Germany 6p original/0 ci=16,d=1: the weak rotation includes reference.
        target = next(t for t in a.expected_tasks('mixed') if t['cell'] == 'Germany|6|original|0'
                      and t['deal'] == 1 and t['focalSeat'] == 2 and t['policy'] == 'expert24')
        self.assertEqual(target['controllers'], ['expert24', 'ppo0', 'expert24', 'teacherV2', 'expert24', 'reference'])

    def test_four_deal_ddof1_not_population_variance(self):
        r = a.estimate({'a': [0, 1, 0, 1], 'b': [.5, .5, .5, .5]})
        self.assertEqual(r['mean'], .5)
        self.assertAlmostEqual(r['standardError'], math.sqrt(1 / 48), places=15)
        self.assertEqual(r['independentDeals'], 8)
        self.assertAlmostEqual(r['approximateNormal95'][0], .5 - 1.96 / math.sqrt(48))
        self.assertAlmostEqual(r['twoPrimaryBonferroniNormal975'][0], .5 - 2.241402727604947 / math.sqrt(48))

    def test_no_random_cell_variance_or_raw_deal_weighting(self):
        r = a.estimate({'a': [0, 0], 'b': [1, 1, 1, 1]})
        self.assertEqual(r['mean'], .5)
        self.assertEqual(r['standardError'], 0)
        self.assertNotEqual(r['mean'], 4 / 6)

    def test_paired_covariance_not_independent_arm_variance(self):
        left, right = [.25, .5, .75, 1], [0, .25, .5, .75]
        paired = a.estimate({'cell': [x - y for x, y in zip(left, right)]})
        self.assertEqual(paired['mean'], .25)
        self.assertEqual(paired['standardError'], 0)
        self.assertGreater(a.estimate({'cell': left})['standardError'], 0)

    def test_occupancy_unequal_counts_and_singleton_no_interval(self):
        r = a.estimate({'a': [0, 1], 'b': [.5] * 4})
        self.assertEqual(r['standardError'], .25)
        r = a.estimate({'a': [0], 'b': [1, 1, 1, 1]})
        self.assertEqual(r['mean'], .5)
        self.assertIsNone(r['standardError'])
        self.assertIsNone(r['approximateNormal95'])
        self.assertIsNone(r['twoPrimaryBonferroniNormal975'])

    def test_invalid_cluster_observations(self):
        for values in ({}, {'a': []}, {'a': [True, 1]}, {'a': [0, float('nan')]},
                       {'a': [-1.01, 0]}, {'a': [0, 1.01]}):
            with self.subTest(values=values), self.assertRaises(ValueError):
                a.estimate(values)

    def test_gate_strict_zero_and_map_boundary(self):
        def summary(lower, minimum):
            return dict(primary={'twoPrimaryBonferroniNormal975': [lower, 1]},
                subgroups={'map:' + m: {'pairedDifference': {'mean': minimum}} for m in a.MAPS})
        self.assertFalse(a.panel_gate(summary(0, 0))['passed'])
        self.assertTrue(a.panel_gate(summary(1e-16, -.05))['passed'])
        self.assertFalse(a.panel_gate(summary(.1, -.05000000000000001))['passed'])
        self.assertFalse(a.panel_gate(summary(-1e-16, 1))['passed'])

    def test_combined_gate_truth_table_and_no_pooled_interval(self):
        # Isolate the combined decision after the full-snapshot tests exercise
        # both independent validations. Neither panel can rescue the other.
        cases = [(.1, .2, 0., True), (.1, 0., 0., False),
                 (0., .2, 0., False), (.1, -.01, 0., False),
                 (.1, .2, -.05, True), (.1, .2, -.05000000000000001, False)]
        for strong_lower, mixed_lower, minimum, passed in cases:
            reports = []
            for lower in (strong_lower, mixed_lower):
                reports.append(dict(counts=dict(games=2560, batches=320),
                    gate=dict(adjustedLower=lower, minimumMapPairedMean=minimum,
                              passed=lower > 0 and minimum >= -.05)))
            with self.subTest(case=(strong_lower, mixed_lower, minimum)):
                with tempfile.TemporaryDirectory() as tmp, mock.patch.object(a, 'audit_panel', side_effect=reports):
                    result = a.audit_both(Path(tmp) / 'strong', Path(tmp) / 'mixed')
                self.assertEqual(result['gate']['passed'], passed)
                self.assertEqual(result['gate']['adjustedLowerByPanel'],
                                 dict(strong=strong_lower, mixed=mixed_lower))
                self.assertNotIn('pooled', result)

    def test_strict_comparator_schema_types_and_tolerance(self):
        a.equal({'x': .123}, {'x': .123 + 1e-14})
        for left, right in [({'x': 1, 'extra': 0}, {'x': 1}), ({'x': 1.}, {'x': 1}),
                            ({'x': False}, {'x': 0}), ({'x': 0}, {'x': False}),
                            ({'x': .123}, {'x': .123 + 1e-9}), ({'x': float('inf')}, {'x': 1.})]:
            with self.assertRaises(ValueError):
                a.equal(left, right)

    def test_json_duplicate_nonfinite_and_overflow_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'x.json'
            for text in ('{"x":1,"x":2}', '{"x":NaN}', '{"x":Infinity}', '{"x":-Infinity}', '{"x":1e999}'):
                path.write_text(text)
                with self.subTest(text=text), self.assertRaises(ValueError):
                    a.read(path)

    def test_import_is_standard_library_only(self):
        code = "import audit_stress,sys; assert not {'torch','huggingface_hub','stress_study','stress_rollout'} & sys.modules.keys()"
        result = subprocess.run([sys.executable, '-B', '-c', code], cwd=a.HERE, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)


class OutcomeValidation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tasks = a.expected_tasks('strong')

    def bad(self, change, task=None):
        task = task or self.tasks[0]
        game = outcome(task)
        change(game)
        with self.assertRaises(ValueError):
            a.validate_outcome(game, task)

    def test_realistic_forced_moves_and_ties_valid(self):
        for panel in a.PANELS:
            for batch in a.expected_batches(panel)[::19]:
                for task in batch:
                    a.validate_outcome(outcome(task), task)

    def test_nonterminal_cap_and_rounds(self):
        for key, value in [('terminal', False), ('terminal', 1), ('steps', 4001), ('steps', True),
                           ('rounds', 0), ('rounds', 5000), ('rounds', 1.)]:
            with self.subTest(key=key, value=value):
                self.bad(lambda r: r.__setitem__(key, value))

    def test_invalid_credits_and_focal_binding(self):
        for credit in ([.6, .4], [0, 0], [1], [True, 0], [float('nan'), 0]):
            self.bad(lambda r: r.__setitem__('allSeatCredit', credit))
        self.bad(lambda r: r.__setitem__('credit', 1 - r['credit']))
        self.bad(lambda r: r.__setitem__('credit', True))

    def test_timing_and_extra_payload_schema(self):
        for k, v in [('seconds', -1), ('featureMs', float('inf')), ('inferenceMs', True),
                     ('observations', []), ('error', None), ('expertRows', [])]:
            self.bad(lambda r: r.__setitem__(k, v))
        self.bad(lambda r: r.pop('rounds'))

    def test_integer_counters_and_exact_schemas(self):
        for v in (True, -1, 1., '1'):
            self.bad(lambda r: r['counts']['expert24'].__setitem__('Auction', v))
        self.bad(lambda r: r['counts'].pop('ppo0'))
        self.bad(lambda r: r['seatCounts'][0].pop('Building'))
        self.bad(lambda r: r['seatCounts'].pop())

    def test_tampered_totals(self):
        self.bad(lambda r: r.__setitem__('steps', r['steps'] + 1))
        self.bad(lambda r: r['seatCounts'][0].__setitem__('Auction', r['seatCounts'][0]['Auction'] + 1))

    def test_actual_seat_routing_even_when_global_totals_match(self):
        def swap(r):
            r['seatCounts'][0], r['seatCounts'][1] = r['seatCounts'][1], r['seatCounts'][0]
        self.bad(swap)

    def test_learned_fixed_phase_or_wrong_fixed_teacher(self):
        def wrong_fixed(r):
            r['counts']['fixedV2']['Resources'] -= 1
            r['counts']['fixedV1']['Resources'] += 1
        self.bad(wrong_fixed)
        def learned(r):
            r['counts']['fixedV2']['Resources'] -= 1
            r['counts']['expert24']['Resources'] += 1
        self.bad(learned)

    def test_unassigned_controller_and_non_germany_reference(self):
        def wrong(r):
            r['counts']['expert24']['Auction'] -= 1
            r['counts']['reference']['Auction'] += 1
        task = next(t for t in self.tasks if t['map'] == 'USA')
        self.bad(wrong, task)
        self.bad(lambda r: r['counts']['ppo0'].__setitem__('Auction', 1))

    def test_public_label_and_request_counters(self):
        for key in ('hiddenInvariant', 'referenceAtomicLegal', 'fullMenuPrior', 'expertAtomicLegal'):
            self.bad(lambda r: r['publicChecks'].__setitem__(key, r['publicChecks'][key] + 1))
        self.bad(lambda r: r['policyRequests'].__setitem__('expert24', r['policyRequests']['expert24'] + 1))
        self.bad(lambda r: r.__setitem__('referenceRequests', r['referenceRequests'] + 1))
        self.bad(lambda r: r['publicChecks'].__setitem__('expertAtomicLegal', False))


class FullSnapshots(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.roots = {p: Path(cls.tmp.name) / p for p in a.PANELS}
        cls.games = {p: snapshot(cls.roots[p], p) for p in a.PANELS}

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def bad_file(self, name, change, panel='mixed', regex=None):
        with changed(self.roots[panel], name, change):
            with self.assertRaisesRegex(ValueError, regex or '.'):
                a.audit_panel(self.roots[panel], panel)

    def bad_summary(self, change, panel='mixed'):
        root = self.roots[panel]
        with changed(root, 'study/summary.json', change):
            saved = a.read(root / 'study/summary.json')
            with changed(root, 'status.json', lambda s: s.__setitem__('result', saved)):
                with self.assertRaisesRegex(ValueError, 'Saved summary'):
                    a.audit_panel(root, panel)

    def test_complete_fullgrid_two_panel_audit(self):
        result = a.audit_both(self.roots['strong'], self.roots['mixed'])
        self.assertTrue(result['bothPanelsComplete'])
        self.assertEqual(result['counts'], dict(games=5120, batches=640, independentDeals=640))
        self.assertEqual(result['rootSeparation']['overlap'], 0)
        self.assertEqual(result['gate']['passed'], all(r['gate']['passed'] for r in result['panels'].values()))
        for p, report in result['panels'].items():
            self.assertEqual(report['integrity']['snapshotFiles'], 327)
            self.assertEqual(report['integrity']['manifestFiles'], 326)
            self.assertFalse(report['integrity']['artifactHashesVerifiedHere'])
            self.assertEqual(report['counts']['games'], 2560)
            self.assertEqual(report['scheduledCoverage']['gamesByPolicy'], {'expert24': 1280, 'ppo2': 1280})
            self.assertEqual(report['scheduledCoverage']['gamesByMap'], dict.fromkeys(a.MAPS, 640))
            self.assertEqual(report['scheduledCoverage']['gamesByPlayers'], {'2': 256, '3': 384, '4': 512, '5': 640, '6': 768})
            self.assertEqual(sum(v['games'] for v in report['scheduledCoverage']['strongOpponentOccupancy'].values()), 2560)
            self.assertEqual(report['integrity']['counters']['nonGermanyReferenceRequests'], 0)
            self.assertEqual(report['integrity']['counters']['expertLabels'], 0)
            self.assertGreater(report['integrity']['counters']['ties'], 0)
            self.assertFalse(report['qualified'])
            a.equal(oracle_summary(self.games[p], p), report['summary'])

    def test_equal_80_cell_weights_not_raw_2560_game_average(self):
        summary = a.recompute_summary(self.games['mixed'], 'mixed')
        raw = statistics.mean(g['credit'] for g in self.games['mixed'] if g['spec']['policy'] == 'expert24')
        actual = summary['subgroups']['allMaps']['expert24']['mean']
        self.assertNotAlmostEqual(actual, raw, places=6)
        cells = defaultdict(list)
        for g in self.games['mixed']:
            if g['spec']['policy'] == 'expert24':
                cells[g['spec']['cell']].append(g['credit'])
        self.assertAlmostEqual(actual, statistics.mean(statistics.mean(v) for v in cells.values()), places=15)

    def test_every_cell_deal_averages_all_focal_seats(self):
        summary = a.recompute_summary(self.games['mixed'], 'mixed')
        for cell, deals in summary['cellDealMeans'].items():
            for deal, arms in deals.items():
                for policy, value in arms.items():
                    rows = [g for g in self.games['mixed'] if g['spec']['cell'] == cell and
                            g['spec']['deal'] == int(deal) and g['spec']['policy'] == policy]
                    self.assertEqual(len(rows), int(cell.split('|')[1]))
                    self.assertAlmostEqual(value, statistics.mean(g['credit'] for g in rows), places=15)

    def test_analytical_and_homogeneous_controls_are_not_added_games(self):
        summary = a.recompute_summary(self.games['strong'], 'strong')
        benchmark = summary['GermanyAnalyticalReferenceBenchmark']
        self.assertAlmostEqual(benchmark['benchmark'], .29, places=15)
        self.assertEqual(benchmark['newlyPlayedReferenceControlGames'], 0)
        self.assertEqual(summary['homogeneousExpertDealControls'], 240)
        self.assertEqual(summary['games'], 2560)
        for m in a.MAPS[1:]:
            estimate = summary['subgroups']['map:' + m]['expert24']
            self.assertAlmostEqual(estimate['mean'], .29, places=15)
            self.assertAlmostEqual(estimate['standardError'], 0, places=15)
        self.assertTrue(any('not an unbiased estimator' in c for c in summary['caveats']))
        self.assertTrue(any('unadjusted' in c for c in summary['caveats']))

    def test_missing_batch_and_complete_status_cannot_hide_partial(self):
        path = self.roots['mixed'] / 'study/batch-319.json'
        original = path.read_bytes()
        path.unlink()
        try:
            with self.assertRaisesRegex(ValueError, 'missing/extra'):
                a.audit_panel(self.roots['mixed'], 'mixed')
            with self.assertRaises(ValueError):
                a.audit_both(self.roots['strong'], self.roots['mixed'])
        finally:
            path.write_bytes(original)

    def test_duplicate_missing_reordered_games(self):
        for change in (lambda b: b['games'].__setitem__(1, b['games'][0]),
                       lambda b: b['games'].pop(), lambda b: b['games'].reverse()):
            self.bad_file('study/batch-000.json', change)

    def test_batch_hash_index_schema(self):
        for key, value in [('index', True), ('index', 1), ('taskSha256', '0' * 64),
                           ('schema', 'stale-v0'), ('extra', None)]:
            self.bad_file('study/batch-000.json', lambda b: b.__setitem__(key, value))

    def test_nonterminal_and_counter_tamper_full_snapshot(self):
        self.bad_file('study/batch-000.json', lambda b: b['games'][0].__setitem__('terminal', False))
        self.bad_file('study/batch-000.json', lambda b: b['games'][0]['publicChecks'].__setitem__('fullMenuPrior', 0))

    def test_foreign_smoke_map_policy_seed_and_plan(self):
        for key, value in [('smoke', True), ('smoke', 0), ('map', 'Italy'), ('policy', 'ppo1'),
                           ('seed', 'old-final-root'), ('panel', 'strong'), ('selection', False)]:
            self.bad_file('study/batch-000.json', lambda b: b['games'][0]['spec'].__setitem__(key, value))
        self.bad_file('study/plan.json', lambda p: p['tasks'][0].__setitem__('seed', 'foreign-root'))
        self.bad_file('study/plan.json', lambda p: p['tasks'].pop())
        self.bad_file('study/plan.json', lambda p: p.__setitem__('fitting', True))

    def test_paired_nonfocal_assignment_corruption(self):
        self.bad_file('study/batch-000.json', lambda b: b['games'][1]['spec']['controllers'].__setitem__(1, 'teacherV2'))

    def test_extra_stale_files_and_empty_directory_rejected(self):
        root = self.roots['mixed']
        for name in ('study/batch-000.json.tmp', 'study/batch-320.json', 'study/old-summary.json', 'extra.json', 'model.pt'):
            path = root / name
            path.write_text('{}')
            try:
                with self.subTest(name=name), self.assertRaises(ValueError):
                    a.audit_panel(root, 'mixed')
            finally:
                path.unlink()
        path = root / 'empty'
        path.mkdir()
        try:
            with self.assertRaises(ValueError):
                a.audit_panel(root, 'mixed')
        finally:
            path.rmdir()

    def test_symlink_snapshot_and_artifacts_rejected(self):
        link = Path(self.tmp.name) / 'alias'
        link.symlink_to(self.roots['mixed'], target_is_directory=True)
        try:
            with self.assertRaises(ValueError):
                a.audit_panel(link, 'mixed')
        finally:
            link.unlink()
        path = self.roots['mixed'] / 'study/batch-000.json'
        original = path.read_bytes()
        path.unlink()
        path.symlink_to(self.roots['strong'] / 'study/batch-000.json')
        try:
            with self.assertRaisesRegex(ValueError, 'symlink'):
                a.audit_panel(self.roots['mixed'], 'mixed')
        finally:
            path.unlink()
            path.write_bytes(original)

    def test_manifest_missing_foreign_and_hash_schema(self):
        self.bad_file('artifacts.json', lambda m: m.pop('study/batch-000.json'))
        self.bad_file('artifacts.json', lambda m: m.__setitem__('study/batch-320.json', '0' * 64))
        self.bad_file('artifacts.json', lambda m: m.__setitem__('study/batch-000.json', 'not-a-hash'))

    def test_source_identity_schema_protocol_and_metadata_payloads(self):
        self.bad_file('study/plan.json', lambda p: p['sourceFiles'].pop('stress_study.py'))
        self.bad_file('study/plan.json', lambda p: p.__setitem__('expertIdentity', {}))
        self.bad_file('study/plan.json', lambda p: p.__setitem__('threads', 2))
        self.bad_file('protocol.json', lambda p: p.__setitem__('dealsPerCell', 5))
        self.bad_file('environment.json', lambda p: p.clear())
        self.bad_file('recovery.json', lambda p: p.clear())

    def test_summary_numeric_tamper_and_stale_result_even_if_status_agrees(self):
        self.bad_summary(lambda s: s['primary'].__setitem__('mean', s['primary']['mean'] + .001))
        self.bad_summary(lambda s: s['primary'].__setitem__('standardError', 0))
        self.bad_summary(lambda s: s['subgroups']['players:6']['pairedDifference'].__setitem__('mean', .9))
        self.bad_summary(lambda s: s['subgroups']['rule:original|1']['ppo2'].__setitem__('standardError', .9))
        self.bad_summary(lambda s: s['subgroups']['mapPlayers:France|4']['expert24'].__setitem__('mean', .9))
        self.bad_summary(lambda s: s['strongOpponentOccupancy']['1']['pairedDifference'].__setitem__('cells', 999))
        self.bad_summary(lambda s: s['cellDealMeans']['USA|6|recharged|1']['3'].__setitem__('expert24', .99))

    def test_summary_missing_extra_and_wrong_type_keycoverage(self):
        self.bad_summary(lambda s: s['subgroups'].pop('mapPlayers:France|2'))
        self.bad_summary(lambda s: s['strongOpponentOccupancy'].__setitem__('5', {}))
        self.bad_summary(lambda s: s['cellDealMeans'].pop('Germany|2|original|0'))
        self.bad_summary(lambda s: s.__setitem__('games', 2560.))
        self.bad_summary(lambda s: s.__setitem__('failures', False))
        self.bad_summary(lambda s: s.__setitem__('extra', 0))
        self.bad_summary(lambda s: s['primary'].pop('twoPrimaryBonferroniNormal975'))

    def test_reciprocal_allseat_vectors_and_opponent_checked(self):
        self.bad_summary(lambda s: s['reciprocalTwoPlayerOutcomes'][0].__setitem__('opponent', 'teacherV2'))
        self.bad_summary(lambda s: s['reciprocalTwoPlayerOutcomes'][0]['allSeatCredits']['expert24'][0].reverse())
        self.bad_summary(lambda s: s['reciprocalTwoPlayerOutcomes'].pop())

    def test_homogeneous_symmetry_corruption_is_locally_valid_but_rejected(self):
        # Batch80 starts USA. Alter only one focal rotation's valid terminal vector.
        def change(batch):
            row = batch['games'][2]
            row['allSeatCredit'] = [0., 1.]
            row['credit'] = row['allSeatCredit'][row['spec']['focalSeat']]
            # Original fixture has [1,0] here; low-level validity alone is insufficient.
            a.validate_outcome(row, a.expected_batches('strong')[80][2])
        self.bad_file('study/batch-080.json', change, panel='strong', regex='symmetry')
        self.bad_file('study/batch-080.json', lambda b: b['games'][2].__setitem__('rounds', 2),
                      panel='strong', regex='symmetry')

    def test_control_benchmark_and_gate_tampering(self):
        self.bad_summary(lambda s: s.__setitem__('homogeneousExpertDealControls', 0), panel='strong')
        self.bad_summary(lambda s: s['GermanyAnalyticalReferenceBenchmark'].__setitem__('benchmark', .25), panel='strong')
        self.bad_summary(lambda s: s['GermanyAnalyticalReferenceBenchmark'].__setitem__('newlyPlayedReferenceControlGames', 320), panel='strong')
        self.bad_summary(lambda s: s.__setitem__('panelResearchProgressionGate', not s['panelResearchProgressionGate']))
        self.bad_summary(lambda s: s.__setitem__('bothPanelsRequired', False))
        self.bad_summary(lambda s: s.__setitem__('qualified', True))
        self.bad_summary(lambda s: s.__setitem__('caveats', []))

    def test_status_result_mismatch_and_callback_complete_without_result(self):
        self.bad_file('status.json', lambda s: s['result']['primary'].__setitem__('mean', .9), regex='status.result')
        self.bad_file('status.json', lambda s: s.pop('result'))

    def test_noncomplete_error_resume_original_job_status_rejected(self):
        for key, value in [('stage', 'batches-320'), ('stage', 'failed'), ('error', None), ('resume', {}),
                           ('run', 'multimap-stress-20261103-v1-mixed-r1'), ('smoke', True), ('workers', 5),
                           ('sourceRevision', '0' * 40), ('qualified', True), ('reservedFinalSeedsUsed', True)]:
            self.bad_file('status.json', lambda s: s.__setitem__(key, value))

    def test_checkpoint_receipt_coverage_order_and_revision(self):
        self.bad_file('status.json', lambda s: s['receipts'].pop())
        self.bad_file('status.json', lambda s: s['receipts'].reverse())
        self.bad_file('status.json', lambda s: s['receipts'][1].__setitem__('revision', s['receipts'][0]['revision']))
        self.bad_file('status.json', lambda s: s['receipts'][1].__setitem__('revision', 'main'))

    def test_both_requires_complete_separate_panel_roots(self):
        with self.assertRaises(ValueError):
            a.audit_both(self.roots['strong'], self.roots['strong'])
        with self.assertRaises(ValueError):
            a.audit_both(Path(self.tmp.name), self.roots['mixed'])
        with self.assertRaises(ValueError):
            a.audit_both(self.roots['mixed'], self.roots['strong'])
        with changed(self.roots['mixed'], 'status.json', lambda s: s.__setitem__('stage', 'batches-320')):
            with self.assertRaises(ValueError):
                a.audit_both(self.roots['strong'], self.roots['mixed'])

    def test_recompute_rejects_partial_duplicate_or_reordered_rows(self):
        rows = self.games['mixed']
        for bad in (rows[:-1], [rows[0], *rows[:-1]], rows[::-1]):
            with self.assertRaises(ValueError):
                a.recompute_summary(bad, 'mixed')


if __name__ == '__main__':
    unittest.main()
