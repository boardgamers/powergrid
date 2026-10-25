"""Fidelity aggregation, complete-data boundaries and paired uncertainty checks."""
from collections import Counter
from copy import deepcopy
from fractions import Fraction
from itertools import product
import unittest

from strategic_collection import ROOT, read, digest
import surrogate_continuation_analysis_v1 as analysis
from surrogate_continuation_roots_v1 import PROTOCOL, PHASES, contract, object_hash
from surrogate_continuation_study_v1 import MODES, verify_chunk


def set_credits(report, mode, values):
    report['mode_credits'][mode] = [[analysis.rational(Fraction(a)), analysis.rational(Fraction(b))] for a, b in values]
    report['margins'][mode] = analysis.rational(sum((Fraction(b)-Fraction(a) for a, b in values), Fraction())/8)


def fixture():
    """Synthetic statistical fixture only; no inference or model-quality claims."""
    games = []; roots = []; reports = []
    for n in range(2, 7):
        for d, seat, rule in product(range(2), range(n), range(4)):
            q = contract(n, d, seat, rule, 'root'); case = f'synthetic-{n}'
            games.append({'identity': q, 'case': case, 'missing_phases': []})
            for phase in PHASES:
                request = {'state': {'fixture': 'synthetic'}, 'player': seat}
                root = {'identity': q, 'case': case, 'phase': phase, 'root_id': f'{n}:{q["episode"]}:{phase}',
                        'decision': 0, 'rank': object_hash([q['seed'], q['episode'], phase, 0]),
                        'request': request, 'public_root_sha256': object_hash(request),
                        'moves': [{'name': 'Pass'}, {'name': 'Fixture'}], 'options': [0, 1],
                        'prior_actors': [0] if seat and rule < 2 and phase == 'bid' else []}
                roots.append(root)
                names = ['neural', 'economic', 'legacy', 'rush']
                roles = [['neural' if p == seat else names[(s+p)%4] for p in range(n)] for s in range(8)]
                report = {'identity': q, 'phase': phase, 'root_sha256': object_hash(root),
                          'public_root_sha256': root['public_root_sha256'], 'options': [0, 1],
                          'complete': True, 'caps': 0, 'qualification_eligible': False,
                          'prior_bid_count': len(root['prior_actors']),
                          'population_roles': roles, 'population_strata': analysis.STRATA,
                          'world_sha256': {str(s): object_hash(['fixture', root['root_id'], s]) for s in range(8)},
                          'mode_credits': {}, 'margins': {}}
                for mode in MODES: set_credits(report, mode, [(0, 0)]*8)
                reports.append(report)
    manifest = {'games': games, 'roots': roots, 'phase_counts': dict(Counter(analysis.group(r) for r in roots)),
                'protocol_sha256': digest(PROTOCOL), 'focal_model_sha256': read(PROTOCOL)['focal_model_sha256'],
                'qualification_eligible': False, 'reserved_final_seeds_used': False}
    return manifest, reports


def metrics_rows(manifest, reports):
    rows = []
    for root, report in zip(manifest['roots'], reports):
        credits = analysis.check_record(root, report)
        rows.append({'group': analysis.group(root), 'deal': root['identity']['deal'],
                     'metrics': analysis.root_metrics(credits)})
    return rows


class AnalysisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.manifest, cls.reports = fixture()

    def fresh(self): return deepcopy(self.manifest), deepcopy(self.reports)

    def test_full_analysis_equal_groups_not_more_seats_and_keeps_adverse_cells(self):
        manifest, reports = self.fresh()
        for report in reports:
            if report['identity']['players'] == 6: set_credits(report, analysis.SURROGATE, [(0, 1)]*8)
        result = analysis.analyze(manifest, reports)
        self.assertTrue(result['complete']); self.assertEqual(result['continuations'], 23040)
        primary = result['primary']
        self.assertEqual(primary['surrogate_minus_population_error']['exact'], [1, 5])
        self.assertEqual(len(primary['adverse_groups']), 12)
        self.assertEqual(primary['represented_groups'], 60)
        self.assertEqual(len(result['root_metrics']), 480)
        self.assertGreater(result['by_prior_bids']['with_prior_bids']['roots'], 0)
        ci = result['whole_deal_uncertainty']['intervals']['surrogate_minus_population_error']
        self.assertEqual(ci['lower']['exact'], [1, 5]); self.assertEqual(ci['upper']['exact'], [1, 5])

    def test_exact_whole_deal_distribution_matches_binomial_hand_calculation(self):
        manifest, reports = self.fresh()
        for report in reports:
            set_credits(report, analysis.SURROGATE, [(0, 1 if report['identity']['deal'] == 0 else 0)]*8)
        rows = metrics_rows(manifest, reports)
        self.assertEqual(analysis.summarize(rows)['surrogate_minus_population_error'], Fraction(1, 2))
        result = analysis.whole_deal_uncertainty(rows)
        # Ten independent fair deal draws: exact percentile endpoints of Binomial(10,.5)/10.
        ci = result['intervals']['surrogate_minus_population_error']
        self.assertEqual(ci['lower']['exact'], [1, 5]); self.assertEqual(ci['upper']['exact'], [4, 5])
        self.assertEqual(result['undefined_probability']['exact'], [0, 1])

    def test_missing_deal_group_withholds_interval_without_reweighting(self):
        manifest, reports = self.fresh()
        remove = {r['root_id'] for r in manifest['roots'] if analysis.group(r) == '2/0/bid' and r['identity']['deal'] == 1}
        manifest['roots'] = [r for r in manifest['roots'] if r['root_id'] not in remove]
        reports = [r for r in reports if analysis.root_id(r) not in remove]
        for g in manifest['games']:
            q = g['identity']
            if (q['players'], q['deal'], q['rule']) == (2, 1, 0): g['missing_phases'] = ['bid']
        manifest['phase_counts']['2/0/bid'] -= 2
        self.assertEqual(len(analysis.manifest_roots(manifest)), 478)
        result = analysis.whole_deal_uncertainty(metrics_rows(manifest, reports))
        self.assertIsNone(result['intervals']); self.assertEqual(result['undefined_probability']['exact'], [1, 4])

    def test_world_bootstrap_preserves_balanced_roles_and_mode_action_pairing(self):
        credits = {mode: [[Fraction(0), Fraction(s%4 == 0)] for s in range(8)] for mode in MODES}
        result = analysis.within_root(credits)
        # All within-stratum duplicates agree. A naive IID bootstrap would spuriously vary the role mix.
        for mode in MODES:
            self.assertEqual(result['intervals'][mode]['lower']['exact'], [1, 4])
            self.assertEqual(result['intervals'][mode]['upper']['exact'], [1, 4])
        for mode in analysis.COMPARED:
            self.assertEqual(result['intervals'][mode+'_absolute_error']['upper']['exact'], [0, 1])
        credits = {mode: [[Fraction(0), Fraction(s == 4)] for s in range(8)] for mode in MODES}
        result = analysis.within_root(credits)
        self.assertEqual(result['margin_standard_errors'][analysis.REFERENCE]['variance_exact'], [1, 64])
        self.assertEqual(result['intervals'][analysis.REFERENCE]['lower']['exact'], [0, 1])
        self.assertEqual(result['intervals'][analysis.REFERENCE]['upper']['exact'], [1, 4])
        self.assertEqual(result['intervals']['surrogate_minus_population_error']['upper']['exact'], [0, 1])

    def test_exact_ties_signed_errors_and_action_credit_definition(self):
        credits = {analysis.REFERENCE: [[Fraction(1, 3), Fraction(1, 3)]]*8,
                   analysis.SURROGATE: [[Fraction(0), Fraction(0)]]*8,
                   analysis.POPULATION: [[Fraction(1), Fraction(0)]]*8}
        metrics = analysis.root_metrics(credits)
        self.assertEqual(metrics[analysis.SURROGATE]['preference_agreement'], 1)
        self.assertEqual(metrics[analysis.SURROGATE]['absolute_margin_error'], 0)
        self.assertEqual(metrics[analysis.SURROGATE]['absolute_action_credit_error'], Fraction(1, 3))
        self.assertEqual(metrics[analysis.POPULATION]['signed_margin_error'], -1)
        self.assertEqual(metrics[analysis.POPULATION]['preference_agreement'], 0)
        self.assertEqual(metrics[analysis.POPULATION]['absolute_action_credit_error'], Fraction(1, 2))

    def test_caps_retain_all_records_and_suppress_survivor_aggregation(self):
        for outer in (False, True):
            manifest, reports = self.fresh(); row = reports[0]
            row.update(complete=False, caps=1, margins=None)
            if outer: row['mode_credits'][analysis.REFERENCE][0][0] = None
            result = analysis.analyze(manifest, reports)
            self.assertFalse(result['complete']); self.assertEqual(result['caps'], 1)
            self.assertEqual(len(result['paired_records']), 480)
            for key in ('primary', 'whole_deal_uncertainty', 'by_prior_bids', 'root_metrics'): self.assertIsNone(result[key])

    def test_missing_duplicate_or_changed_inputs_are_rejected(self):
        for kind in ('missing_report', 'duplicate', 'missing_game', 'credit', 'margin', 'root_hash', 'roles', 'missing_phase'):
            manifest, reports = self.fresh()
            if kind == 'missing_report': reports.pop()
            elif kind == 'duplicate': reports[-1] = deepcopy(reports[0])
            elif kind == 'missing_game': manifest['games'].pop()
            elif kind == 'credit': reports[0]['mode_credits'][analysis.REFERENCE][0][0] = [1, 7]
            elif kind == 'margin': reports[0]['margins'][analysis.REFERENCE] = [1, 1]
            elif kind == 'root_hash': reports[0]['root_sha256'] = 'a'*64
            elif kind == 'roles': reports[0]['population_roles'][4][1] = 'invalid'
            else: manifest['games'][0]['missing_phases'] = ['bid']
            with self.subTest(kind=kind), self.assertRaises(AssertionError): analysis.analyze(manifest, reports)

    def test_actual_saved_preflight_pairing_and_interval_contains_point(self):
        base = ROOT/'ai/runs/surrogate-continuation-study-preflight-v1'; checked = 0
        for phase in ('plant', 'bid'):
            root = read(base/f'{phase}-reference_opponent_v1-0-8/root.json')
            results = {mode: [] for mode in MODES}
            for mode in MODES:
                for folder in sorted(base.glob(f'{phase}-{mode}-*')):
                    intent = read(folder/'intent.json')
                    results[mode].append(verify_chunk(folder, root, surrogate_sha256=intent['surrogate_policy_sha256']))
            report = analysis.paired_record(root, results); credits = analysis.check_record(root, report)
            checked += sum(len(r['rows']) for parts in results.values() for r in parts)
            result = analysis.within_root(credits)
            for mode in MODES:
                point = Fraction(*report['margins'][mode]); ci = result['intervals'][mode]
                self.assertLessEqual(Fraction(*ci['lower']['exact']), point)
                self.assertGreaterEqual(Fraction(*ci['upper']['exact']), point)
            bad = deepcopy(results)
            # Corrupt both paired actions, preserving same-world pairing but breaking role-stratum invariance.
            actor = 1-root['identity']['seat']
            old = bad[analysis.POPULATION][-1]['rows'][0]['roles'][actor]
            for row in bad[analysis.POPULATION][-1]['rows'][:2]: row['roles'][actor] = 'economic' if old != 'economic' else 'rush'
            with self.assertRaises(AssertionError): analysis.paired_record(root, bad)
        self.assertEqual(checked, 96)


if __name__ == '__main__': unittest.main()
