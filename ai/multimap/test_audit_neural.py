"""Offline independent-statistics and adversarial-outcome tests; no neural games."""
import copy
import math
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

import audit_neural as audit

IDENTITY = 'a' * 64


def fixture():
    tasks = audit.expected_plan()
    records = []
    for task in tasks:
        s = task['spec']
        vector = [int(i == s['deal'] % s['players']) for i in range(s['players'])]
        candidate = task['policy'] in audit.POLICIES[:4]
        counts = (dict(ppo={'Auction': 1}, reference={'Auction': 2}, fixed={'Resources': 1}) if candidate
                  else dict(ppo={}, reference={'Auction': 4}, fixed={}))
        records.append(dict(schema='multimap-neural-outcome-v1', identitySha256=IDENTITY,
            **copy.deepcopy(task), terminal=True, credit=vector[s['focalSeat']], allSeatCredit=vector,
            decisions=dict(ppo=1 if candidate else 0, reference=2 if candidate else 4),
            seconds=0.5, steps=4, rounds=1, counts=counts, hiddenChecks=2 if candidate else 4))
    return tasks, records


class LocalSourceTests(unittest.TestCase):
    def test_only_explicit_nonserving_local_drift_allowed(self):
        for name in ('runs.json', 'README.md', 'launch.py'):
            self.assertIsNotNone(audit.local_source_difference('ai/multimap/' + name, 'a' * 64, 'b' * 64))
        for name in audit.SOURCE_NAMES | {'ai/core.cjs', 'ai/strong/economics.cjs',
                                         'engine/dist/index.js', 'runtime/node', 'unlisted.py'}:
            self.assertIsNone(audit.local_source_difference(name, 'a' * 64, 'a' * 64))
            with self.assertRaisesRegex(ValueError, 'Local serving/source drift'):
                audit.local_source_difference(name, 'a' * 64, 'b' * 64)


class OutcomeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tasks, cls.records = fixture()

    def corrupt(self, change, index=0):
        rows = copy.deepcopy(self.records)
        change(rows[index])
        with self.assertRaises(ValueError):
            audit.verify_outcomes(rows, self.tasks, IDENTITY)

    def test_full_plan_and_reference_controls(self):
        actual, baseline = audit.verify_outcomes(self.records, self.tasks, IDENTITY)
        self.assertEqual(len(actual), 1920)
        self.assertEqual(len(baseline), 80)
        self.assertEqual({t['spec']['players'] for t in self.tasks}, set(range(2, 7)))
        self.assertEqual(len({t['spec']['cell'] for t in self.tasks}), 20)
        self.assertEqual(len({t['spec']['seed'] for t in self.tasks}), 80)
        self.assertTrue(all(r['focalCreditSum'] == 1 for r in baseline))

    def test_missing_duplicate_and_unplanned(self):
        for rows in (self.records[:-1], self.records + [self.records[0]]):
            with self.assertRaises(ValueError):
                audit.verify_outcomes(rows, self.tasks, IDENTITY)
        self.corrupt(lambda r: r['spec'].update(seed='reserved-final:0'))

    def test_spec_smoke_and_focal_policy(self):
        self.corrupt(lambda r: r['spec'].update(seed=r['spec']['seed'] + ':smoke'))
        self.corrupt(lambda r: r['spec'].update(focalPolicy='teacher'))
        self.corrupt(lambda r: r['spec'].update(maxSteps=4001))
        self.corrupt(lambda r: r['spec'].update(fastBid=0))

    def test_identity_and_schema(self):
        self.corrupt(lambda r: r.update(identitySha256='b' * 64))
        self.corrupt(lambda r: r.update(schema='other'))
        self.corrupt(lambda r: r.update(actions=[]))
        self.corrupt(lambda r: r.update(error={'code': 'cap'}))

    def test_terminal_errors_and_caps(self):
        self.corrupt(lambda r: r.update(terminal=False))
        self.corrupt(lambda r: r.update(terminal=1))
        self.corrupt(lambda r: r.update(steps=4001))
        self.corrupt(lambda r: r.update(steps=0))
        self.corrupt(lambda r: r.update(rounds=5))

    def test_impossible_credit_vectors(self):
        for vector in ([0.2, 0.8], [0.25, 0.75], [0, 0], [1, 1], [1], [True, 0], [math.nan, 0]):
            self.corrupt(lambda r, v=vector: r.update(allSeatCredit=v, credit=v[0]))
        self.corrupt(lambda r: r.update(credit=0))
        self.corrupt(lambda r: r.update(credit=True))
        self.corrupt(lambda r: r.update(credit=math.inf))

    def test_equal_shared_win_is_legal(self):
        record = copy.deepcopy(self.records[0])
        record.update(allSeatCredit=[0.5, 0.5], credit=0.5)
        audit.validate_outcome(record, self.tasks[0], IDENTITY)
        t = next(t for t in self.tasks if t['spec']['players'] == 3 and t['policy'] == 'ppo0')
        record.update(spec=t['spec'], allSeatCredit=[1/3, 1/3, 1/3], credit=1/3)
        audit.validate_outcome(record, t, IDENTITY)

    def test_nonfinite_or_negative_timing(self):
        for x in (math.nan, math.inf, -1, True, '0'):
            self.corrupt(lambda r, x=x: r.update(seconds=x))

    def test_counts_and_hidden_checks(self):
        self.corrupt(lambda r: r['decisions'].update(ppo=2))
        self.corrupt(lambda r: r['decisions'].update(ppo=True))
        self.corrupt(lambda r: r['counts']['reference'].update(Auction=-1))
        self.corrupt(lambda r: r['counts']['reference'].update(Auction=2.0))
        self.corrupt(lambda r: r['counts']['reference'].update(secret=1))
        self.corrupt(lambda r: r.update(hiddenChecks=1))
        self.corrupt(lambda r: r.update(hiddenChecks=True))
        self.corrupt(lambda r: r['counts'].update(hidden={}))

    def test_control_routing(self):
        index = next(i for i, r in enumerate(self.records) if r['policy'] == 'teacher')
        def route(r):
            r['counts'] = dict(ppo={'Auction': 1}, reference={'Auction': 3}, fixed={})
            r['decisions'] = dict(ppo=1, reference=3)
            r['hiddenChecks'] = 3
        self.corrupt(route, index)
        self.corrupt(lambda r: r['counts'].update(ppo={'Resources': 1}))

    def test_reference_vectors_cannot_change_between_rotations(self):
        index = next(i for i, r in enumerate(self.records) if r['policy'] == 'reference')
        self.corrupt(lambda r: r.update(allSeatCredit=[0, 1], credit=0), index)

    def test_reference_terminal_counts_must_also_reproduce(self):
        index = next(i for i, r in enumerate(self.records) if r['policy'] == 'reference')
        self.corrupt(lambda r: r.update(rounds=2), index)

    def test_jsonl_never_truncates_or_repairs(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'games.jsonl'
            line = audit.canonical(self.records[0])
            for text in (line, line + '\n\n', line + ' \n'):
                path.write_text(text)
                with self.assertRaises((ValueError, TypeError)):
                    audit.read_outcomes(path)
            path.write_text(line + '\n')
            self.assertEqual(audit.read_outcomes(path), [self.records[0]])


class StatisticsTests(unittest.TestCase):
    def test_unbiased_stratified_se_hand_calculation(self):
        result = audit.stratified_estimate([[0, 1, 0, 1], [0, 0, 0, 0]])
        self.assertEqual(result['mean'], 0.25)
        self.assertAlmostEqual(result['unbiasedStratifiedPairedSE'], math.sqrt(1/48))
        self.assertAlmostEqual(result['approximateNormal95'][0], 0.25 - 1.96 * math.sqrt(1/48))
        # Dividing by n rather than n-1 would underestimate SE by sqrt(3/4).
        self.assertNotAlmostEqual(result['unbiasedStratifiedPairedSE'], 0.125)

    def test_fixed_strata_not_between_strata_variation(self):
        result = audit.stratified_estimate([[0] * 4, [1] * 4])
        self.assertEqual(result['mean'], 0.5)
        self.assertEqual(result['unbiasedStratifiedPairedSE'], 0)
        self.assertEqual(result['approximateNormal95'], [0.5, 0.5])

    def test_invalid_strata(self):
        for x in ([], [[]], [[1]], [[1, math.nan]], [[2, 0]]):
            with self.assertRaises(ValueError):
                audit.stratified_estimate(x)

    def test_pairs_and_all_six_policies(self):
        _, rows = fixture()
        stats = audit.paired_statistics(rows)
        self.assertEqual(len(stats), 30)
        self.assertEqual(stats['all']['independentDeals'], 80)
        self.assertEqual(stats['all']['seatsPerPolicy'], 320)
        for group in stats.values():
            self.assertEqual(set(group['policies']), set(audit.POLICIES))
            for p in group['policies'].values():
                for contrast in p['pairedDealDifferences'].values():
                    self.assertEqual(contrast['difference'], 0)
                    self.assertEqual(contrast['unbiasedStratifiedPairedSE'], 0)
        self.assertAlmostEqual(stats['all']['policies']['reference']['macroCellCredit'], .29)
        self.assertAlmostEqual(stats['all']['policies']['reference']['gameMeanCredit'], .25)

    def test_macro_not_seat_weighted_and_difference_direction(self):
        _, rows = fixture()
        for r in rows:
            if r['policy'] == 'ppo0' and r['spec']['cell'] == 'Germany|2|original|0':
                r['credit'] = 1
        stats = audit.paired_statistics(rows)['all']['policies']['ppo0']
        self.assertAlmostEqual(stats['macroCellCredit'], .315)
        self.assertAlmostEqual(stats['gameMeanCredit'], .2625)
        self.assertAlmostEqual(stats['pairedDealDifferences']['reference']['difference'], .025)
        self.assertEqual(stats['pairedDealDifferences']['reference']['unbiasedStratifiedPairedSE'], 0)

    def test_covariance_kept_inside_the_paired_deal(self):
        _, rows = fixture()
        for r in rows:
            if r['policy'] in ('ppo0', 'teacher') and r['spec']['cell'] == 'Germany|2|original|0':
                r['credit'] = r['spec']['deal'] % 2
        stats = audit.paired_statistics(rows)['all']['policies']['ppo0']['pairedDealDifferences']
        self.assertEqual(stats['teacher']['difference'], 0)
        self.assertEqual(stats['teacher']['unbiasedStratifiedPairedSE'], 0)
        self.assertAlmostEqual(stats['reference']['difference'], 0)
        self.assertAlmostEqual(stats['reference']['unbiasedStratifiedPairedSE'], math.sqrt(1/12)/20)

    def test_stats_reject_incomplete_pairs_and_duplicates(self):
        _, rows = fixture()
        for corrupt in (rows[:-1], rows + [rows[0]], [r for r in rows if r['policy'] != 'teacher']):
            with self.assertRaises(ValueError):
                audit.paired_statistics(corrupt)

    def test_order_invariance(self):
        _, rows = fixture()
        self.assertEqual(audit.paired_statistics(rows), audit.paired_statistics(list(reversed(rows))))

    def test_replay_selection_is_outcome_blind_and_complete(self):
        tasks = audit.expected_plan()
        first = audit.replay_tasks(tasks)
        self.assertEqual(first, audit.replay_tasks(list(reversed(tasks))))
        self.assertEqual(len(first), 12)
        self.assertEqual({r['policy'] for r in first}, set(audit.POLICIES))
        self.assertEqual({r['spec']['players'] for r in first}, set(range(2, 7)))

    def test_hash_and_strict_equality(self):
        self.assertEqual(audit.git_blob(b''), 'e69de29bb2d1d6434b8b29ae775ad8c2e48c5391')
        self.assertEqual(audit.object_sha({'b': 1, 'a': 2}), audit.object_sha({'a': 2, 'b': 1}))
        with self.assertRaises(ValueError):
            audit.equal(True, 1, 'bool is not int')
        with self.assertRaises(ValueError):
            audit.equal({'a': 1, 'extra': 2}, {'a': 1}, 'extra key')
        with self.assertRaises(ValueError):
            audit.equal(math.nan, 1, 'nonfinite')


class IntegrityTests(unittest.TestCase):
    def test_cached_file_is_rehashed_against_git_and_sha(self):
        raw = b'{"artifact":1}\n'
        entry = SimpleNamespace(size=len(raw), lfs=None, blob_id=audit.git_blob(raw))
        pin = dict(repo='offline', revision='a'*40, path='result.json', sha256=audit.sha(raw))
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'result.json'
            path.write_bytes(raw)
            self.assertEqual(audit.RemoteFiles(None).get(pin, entry, cached=path), path)
            path.write_bytes(raw.replace(b'1', b'2'))
            with self.assertRaises(ValueError):
                audit.RemoteFiles(None).get(pin, entry, cached=path)
            path.write_bytes(raw)
            entry.blob_id = 'b'*40
            with self.assertRaises(ValueError):
                audit.RemoteFiles(None).get(pin, entry, cached=path)

    def test_budget_rejected_before_a_download(self):
        entry = SimpleNamespace(size=audit.LIMIT+1, lfs=None, blob_id='b'*40)
        pin = dict(repo='offline', revision='a'*40, path='oversize')
        with self.assertRaisesRegex(ValueError, 'budget'):
            audit.RemoteFiles(None).get(pin, entry, cached='/nonexistent')

    def test_unsafe_manifest_paths(self):
        for name in ('../escape', '/absolute', 'a/../../b', 'a\\b', 'a//b', ''):
            with self.assertRaises(ValueError):
                audit.safe_name(name)
        self.assertEqual(str(audit.safe_name('engine/dist/index.js')), 'engine/dist/index.js')


if __name__ == '__main__':
    unittest.main()
