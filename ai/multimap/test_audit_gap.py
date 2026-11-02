"""Offline adversarial tests for the independent phase-gap auditor.
Run: ai/.venv/bin/python -B -m unittest discover -s ai/multimap -p test_audit_gap.py -v
"""
import copy
import math
import unittest

import audit_gap as audit


IDENTITY = 'f' * 64
SENTINEL = 'unchanged'


def sentinel():
    return SENTINEL


def phase(gaps=(0,), agreements=1, forced=0):
    histogram = [0] * 7
    for gap in gaps:
        histogram[next(i for i, bound in enumerate(audit.BOUNDS) if gap <= bound)] += 1
    return dict(multiActionDecisions=len(gaps), forcedMoves=forced,
        teacherExpertAgreement=agreements, priorGapSum=math.fsum(gaps),
        priorGapMax=max(gaps, default=0), priorGapHistogram=histogram,
        cannotOutscoreTeacherBestWithCurrentBound=sum(g > 16+1e-9 for g in gaps),
        exactFloor20=sum(g == 20 for g in gaps))


def outcome(task):
    s, arm = task['spec'], task['policy']
    counts = {a: {p: 0 for p in audit.PHASES} for a in audit.ACTORS}
    for p in audit.PHASES:
        counts['focalTeacher' if audit.controller(arm, p) == 'teacher' else 'focalReference'][p] = 1
        counts['nonfocalReference'][p] = s['players']-1
    steps = 4*s['players']
    credits = [1] + [0]*(s['players']-1)
    return dict(schema='multimap-phase-gap-outcome-v1', identitySha256=IDENTITY,
        **copy.deepcopy(task), terminal=True, seconds=0.1, credit=credits[s['focalSeat']],
        allSeatCredit=credits, steps=steps, rounds=1, counts=counts,
        decisions=dict(referenceRequests=steps, counterfactualOnly=sum(audit.controller(arm, p) == 'teacher' for p in audit.PHASES)),
        phaseCounters={p: phase() for p in audit.PHASES},
        publicChecks=dict(hiddenInvariant=steps, expertAtomicLegal=steps, fullMenuPrior=4, teacherAtomicLegal=4))


class AuditGapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tasks = audit.expected_plan()
        cls.task = cls.tasks[0]

    def test_design_and_replay_coverage(self):
        self.assertEqual(len(self.tasks), 1600)
        self.assertEqual(len({t['spec']['seed'] for t in self.tasks}), 40)
        self.assertEqual(len({t['spec']['cell'] for t in self.tasks}), 20)
        chosen = audit.replay_tasks(self.tasks)
        self.assertEqual(len(chosen), 10)
        self.assertEqual({t['policy'] for t in chosen}, set(audit.POLICIES))
        self.assertEqual({t['spec']['players'] for t in chosen}, set(range(2, 7)))
        self.assertEqual(len({(t['spec']['variant'], t['spec']['fastBid']) for t in chosen}), 4)

    def test_all_arm_routes_and_valid_records(self):
        for arm in audit.POLICIES:
            task = next(t for t in self.tasks if t['policy'] == arm)
            audit.validate_outcome(outcome(task), task, IDENTITY)
            for p in audit.PHASES:
                teacher = arm == 'teacher' or arm == 'reference-except-'+p or (arm.startswith('teacher-except-') and arm != 'teacher-except-'+p)
                self.assertEqual(audit.controller(arm, p), 'teacher' if teacher else 'reference')
        with self.assertRaises(ValueError):
            audit.controller('new-arm', 'Auction')

    def test_invalid_unequal_winner_shares(self):
        r = outcome(self.task)
        r.update(allSeatCredit=[0.2, 0.8], credit=0.2)
        with self.assertRaisesRegex(ValueError, '0 or 1/k'):
            audit.validate_outcome(r, self.task, IDENTITY)
        r.update(allSeatCredit=[0.5, 0.5], credit=0.5)
        audit.validate_outcome(r, self.task, IDENTITY)

    def test_invalid_focal_credit_nonfinite_bool_and_cap(self):
        for change in (dict(credit=0), dict(credit=True), dict(seconds=float('nan')),
                       dict(steps=4001), dict(rounds=9), dict(terminal=False),
                       dict(allSeatCredit=[True, False])):
            r = outcome(self.task)
            r.update(change)
            with self.subTest(change=change), self.assertRaises(ValueError):
                audit.validate_outcome(r, self.task, IDENTITY)

    def test_no_extra_traces_wrong_identity_or_json_types(self):
        for mutate in (lambda r: r.update(actions=[]), lambda r: r.update(identitySha256='wrong'),
                       lambda r: r['spec'].update(fastBid=0)):
            r = outcome(self.task)
            mutate(r)
            with self.assertRaises(ValueError):
                audit.validate_outcome(r, self.task, IDENTITY)

    def test_missing_duplicate_and_reference_controls(self):
        tasks = [t for t in self.tasks if t['policy'] == 'reference' and t['spec']['seed'] == self.task['spec']['seed']]
        rows = [outcome(t) for t in tasks]
        _, baseline = audit.verify_outcomes(rows, tasks, IDENTITY)
        self.assertEqual(baseline[0]['focalCreditSum'], 1)
        for changed in (rows[:-1], rows+[rows[0]]):
            with self.assertRaises(ValueError):
                audit.verify_outcomes(changed, tasks, IDENTITY)
        broken = copy.deepcopy(rows)
        broken[1].update(allSeatCredit=[0, 1], credit=1)
        with self.assertRaisesRegex(ValueError, 'Reference rotations'):
            audit.verify_outcomes(broken, tasks, IDENTITY)

    def test_reference_focal_counts_partition(self):
        tasks = [t for t in self.tasks if t['policy'] == 'reference' and t['spec']['seed'] == self.task['spec']['seed']]
        rows = [outcome(t) for t in tasks]
        for r in rows:
            r['counts']['focalReference']['Auction'] = 2
            r['counts']['nonfocalReference']['Auction'] = 0
            r['phaseCounters']['Auction'] = phase((0, 0), 2)
            r['publicChecks']['fullMenuPrior'] += 1
            r['publicChecks']['teacherAtomicLegal'] += 1
            audit.validate_outcome(r, dict(spec=r['spec'], policy=r['policy']), IDENTITY)
        with self.assertRaisesRegex(ValueError, 'partition'):
            audit.verify_outcomes(rows, tasks, IDENTITY)

    def test_strict_prior_boundary_and_exact_floor(self):
        for gap, unreachable, floor, bucket in ((16, False, False, 5),
                (16+0.5e-9, False, False, 6), (16+1e-9, False, False, 6),
                (16+2e-9, True, False, 6), (20-1e-10, True, False, 6), (20, True, True, 6)):
            result = audit.prior_diagnostic(gap)
            self.assertEqual(result[audit.UNREACHABLE], unreachable)
            self.assertEqual(result['exactFloor20'], floor)
            self.assertEqual(result['histogramIndex'], bucket)
            audit.validate_phase(phase((gap,), 0))
        for value in (-1, 21, float('nan'), True):
            with self.assertRaises(ValueError):
                audit.prior_diagnostic(value)

    def test_histogram_and_agreement_adversaries(self):
        for mutate in (lambda r: r['priorGapHistogram'].__setitem__(0, 9),
                       lambda r: r.update(teacherExpertAgreement=2),
                       lambda r: r.update(priorGapMax=3),
                       lambda r: r.update(priorGapSum=100),
                       lambda r: r.update(multiActionDecisions=True),
                       lambda r: r.update(forcedMoves=4000)):
            r = phase((0, 4), 1)
            mutate(r)
            with self.assertRaises(ValueError):
                audit.validate_phase(r)
        # Prior ties permit disagreement without positive gap.
        audit.validate_phase(phase((0, 0), 0))

    def test_unreachable_floor_and_sum_adversaries(self):
        cases = [phase((16,), 0), phase((20,), 0), phase((17, 20), 0), phase((16+0.5e-9,), 0)]
        cases[0][audit.UNREACHABLE] = 1
        cases[1]['exactFloor20'] = 0
        cases[2]['priorGapSum'] = 33  # Histogram bounds alone admit it; exact20 makes impossible.
        cases[3][audit.UNREACHABLE] = 1
        for r in cases:
            with self.assertRaises(ValueError):
                audit.validate_phase(r)
        r = phase((), 0)
        r['priorGapSum'] = 1
        with self.assertRaises(ValueError):
            audit.validate_phase(r)

    def test_actual_controller_and_counterfactual_counts(self):
        task = next(t for t in self.tasks if t['policy'] == 'teacher')
        for mutate in (lambda r: r['decisions'].update(counterfactualOnly=0),
                       lambda r: r['decisions'].update(referenceRequests=7),
                       lambda r: r['publicChecks'].update(expertAtomicLegal=7),
                       lambda r: r['counts']['focalReference'].update(Auction=1)):
            r = outcome(task)
            mutate(r)
            with self.assertRaises(ValueError):
                audit.validate_outcome(r, task, IDENTITY)

    def test_forced_teacher_not_in_diagnostic_denominators(self):
        task = next(t for t in self.tasks if t['policy'] == 'teacher')
        r = outcome(task)
        r['phaseCounters']['Auction'] = phase((), 0, 1)
        r['decisions'] = dict(referenceRequests=7, counterfactualOnly=3)
        r['publicChecks'] = dict(hiddenInvariant=7, expertAtomicLegal=7, fullMenuPrior=3, teacherAtomicLegal=3)
        audit.validate_outcome(r, task, IDENTITY)
        r['phaseCounters']['Auction']['teacherExpertAgreement'] = 1
        with self.assertRaises(ValueError):
            audit.validate_outcome(r, task, IDENTITY)

    def test_stratified_paired_statistics_analytic(self):
        result = audit.stratified_estimate([[0, 1], [1, 1]])
        self.assertEqual(result['mean'], 0.75)
        self.assertEqual(result['unbiasedStratifiedPairedSE'], 0.25)
        self.assertAlmostEqual(result['approximateNormal95'][0], 0.26)
        self.assertAlmostEqual(result['approximateNormal95'][1], 1.24)
        # Fixed between-cell heterogeneity must not become sampling variance.
        result = audit.stratified_estimate([[0, 0], [1, 1]])
        self.assertEqual(result['unbiasedStratifiedPairedSE'], 0)
        for strata in ([], [[1]], [[0, 0, 0]], [[0, float('nan')]], [[True, 0]]):
            with self.assertRaises(ValueError):
                audit.stratified_estimate(strata)

    def test_paired_arms_are_not_independent_trials(self):
        rows = [dict(**t, credit=t['spec']['deal']) for t in self.tasks]
        report = audit.paired_statistics(rows)
        self.assertEqual(report['all']['independentDeals'], 40)
        self.assertEqual(report['all']['seatsPerArm'], 160)
        self.assertEqual(len(report), 30)
        for arm in report['all']['policies'].values():
            self.assertGreater(arm['unbiasedStratifiedPairedSE'], 0)
            for contrast in arm['pairedDealDifferences'].values():
                self.assertEqual(contrast['mean'], 0)
                self.assertEqual(contrast['unbiasedStratifiedPairedSE'], 0)
        for changed in (rows[:-1], rows+[rows[0]]):
            with self.assertRaises(ValueError):
                audit.deal_table(changed)

    def test_helper_private_globals_no_monkeypatch(self):
        private = audit.reuse(sentinel, SENTINEL='private')
        self.assertEqual(private(), 'private')
        self.assertEqual(sentinel(), 'unchanged')
        old, source, reference = audit.integrity_helpers()
        self.assertEqual(source.__globals__['SOURCE'], audit.SOURCE)
        self.assertNotEqual(old.SOURCE, audit.SOURCE)
        self.assertIsNot(source.__globals__, old.__dict__)
        self.assertIsNot(reference.__globals__, old.__dict__)
        self.assertIs(source.__globals__['git_bytes'], audit.git_bytes)

    def test_only_explicit_nonserving_drift_allowed(self):
        for name in ('README.md', 'runs.json', 'launch.py', 'gap-launch-v1.json'):
            self.assertIsNotNone(audit.local_source_difference('ai/multimap/'+name, 'a', 'b'))
        for name in ('gap_study.py', 'teacher.cjs', 'reference_recover.py', 'audit_neural.py'):
            with self.assertRaises(ValueError):
                audit.local_source_difference('ai/multimap/'+name, 'a', 'b')
        self.assertIsNone(audit.local_source_difference('ai/multimap/gap_study.py', 'a', 'a'))


if __name__ == '__main__':
    unittest.main()
