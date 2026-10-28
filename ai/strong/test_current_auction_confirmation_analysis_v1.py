"""In-memory synthetic arithmetic/admission tests; no simulated game evidence."""
from copy import deepcopy
from fractions import Fraction
import importlib.util
import hashlib
import io
import json
from pathlib import Path
import random
import tempfile
import tarfile
import unittest
from unittest.mock import patch

import numpy as np
import current_auction_confirmation_analysis_v1 as analysis



def identities(p):
    result = {}
    for arm, desc in p['arms'].items():
        result[arm] = {'policySha256': 'a'*64, 'runtimeManifestSha256': desc['runtime_manifest']['sha256'],
            'modelSha256': desc['model']['sha256'], 'featureRevision': desc['feature_revision'],
            'backend': desc['backend'], 'settings': deepcopy(desc['settings'])}
        if 'opponent' in desc: result[arm]['opponentPolicySha256'] = desc['opponent']['sha256']
    return result


def set_winners(record, winners):
    t = record['terminal']; n = t['playerCount']; winners = set(winners)
    t['final']['players'] = [{'powered': 10 if i in winners else 9, 'money': 1,
        'cities': 10, 'capacity': 10, 'plants': []} for i in range(n)]
    t['value'] = [float(Fraction(int(i in winners), len(winners))) for i in range(n)]
    t['win'] = t['value'][t['seat']]


def synthetic_grid(p, ids, winning=None):
    reports = {a: {} for a in analysis.ARMS}
    for arm in analysis.ARMS:
        for screen in p['screens']:
            n, opponent = screen['players'], screen['opponent']; rows = []
            for d in range(32):
                for seat in range(n):
                    for rule in range(4):
                        episode = d*4*n+seat*4+rule
                        role = 'snapshot0' if opponent == 'a260' else opponent
                        row = {'public_runtime_identity': deepcopy(ids[arm]), 'episode': episode,
                            'rollout_caps': 0, 'terminal': {'episode': episode, 'env': 0, 'seat': seat,
                            'playerCount': n, 'gameSeed': p['seed_template'].format(players=n)+'-'+str(d),
                            'variant': 'recharged' if rule % 2 else 'original', 'sealed': rule < 2,
                            'truncated': False, 'steps': 10, 'roles': ['learner' if i == seat else role for i in range(n)],
                            'final': {'round': 10}}}
                        winners = winning(arm, n, d, rule, seat) if winning else {0}
                        set_winners(row, winners); rows.append(row)
            reports[arm][f'{opponent}/{n}p'] = rows
    return reports


class AnalysisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p = analysis.protocol(); cls.ids = identities(cls.p)
        cls.reports = synthetic_grid(cls.p, cls.ids)

    def edited(self, edit):
        reports = {a: dict(cells) for a, cells in self.reports.items()}
        reports['filter']['search_geo/2p'] = deepcopy(reports['filter']['search_geo/2p'])
        edit(reports['filter']['search_geo/2p'])
        return reports

    def test_complete_26880_games_and_no_selection(self):
        result = analysis.analyze(self.reports, self.ids)
        self.assertEqual(result['games'], 26880)
        for flag in ('candidate_selected', 'qualification_eligible', 'reserved_final_seeds_used'):
            self.assertIs(result[flag], False)
        for n in range(2, 7):
            value = result['absolute']['filter'][f'search_geo/{n}p']['overall']['win_credit']
            self.assertEqual(value['exact_mean'], str(Fraction(1, n)))
        for groups in result['all_cell_directions'].values():
            self.assertEqual(len(groups['zero']), 27*5)
            self.assertEqual(groups['negative'], [])
            self.assertEqual(groups['positive'], [])

    def test_missing_duplicate_extra_and_wrong_paired_seeds_rejected(self):
        edits = [lambda rows: rows.pop(), lambda rows: rows.append(deepcopy(rows[0])),
                 lambda rows: rows.__setitem__(1, deepcopy(rows[0])),
                 lambda rows: rows[0]['terminal'].update(gameSeed='conservative-auction-runtime-v1-2p-0'),
                 lambda rows: rows[0]['terminal'].update(sealed=False),
                 lambda rows: rows[0]['terminal'].update(seat=True),
                 lambda rows: rows[0].update(episode=256)]
        for edit in edits:
            with self.subTest(edit=edit), self.assertRaises(ValueError):
                analysis.validate_grid(self.edited(edit), self.ids)

    def test_missing_arm_cell_or_identity_rejected(self):
        r = dict(self.reports); r.pop('conservative_population')
        with self.assertRaises(ValueError): analysis.validate_grid(r, self.ids)
        r = {a: dict(cells) for a, cells in self.reports.items()}; r['filter'].pop('rush/6p')
        with self.assertRaises(ValueError): analysis.validate_grid(r, self.ids)
        ids = deepcopy(self.ids); ids['conservative_population']['settings']['minimum_advantage'] = '0'
        with self.assertRaises(ValueError): analysis.validate_grid(self.reports, ids)
        r = self.edited(lambda rows: rows[0]['public_runtime_identity'].update(policySha256='b'*64))
        with self.assertRaises(ValueError): analysis.validate_grid(r, self.ids)

    def test_caps_errors_incomplete_or_invalid_terminal_rejected(self):
        edits = [lambda rows: rows[0].update(rollout_caps=1),
                 lambda rows: rows[0]['terminal'].update(truncated=True),
                 lambda rows: rows[0]['terminal'].update(steps=1601),
                 lambda rows: rows[0]['terminal'].update(roles=['learner', 'rush']),
                 lambda rows: rows[0]['terminal']['final']['players'][0].update(powered=11),
                 lambda rows: rows[0]['terminal']['final']['players'][0].update(money=True)]
        for edit in edits:
            with self.subTest(edit=edit), self.assertRaises(ValueError):
                analysis.validate_grid(self.edited(edit), self.ids)

    def test_saved_credits_cannot_override_terminal_scores(self):
        for value in (0, .5, float('nan'), float('inf'), True):
            r = self.edited(lambda rows: rows[0]['terminal'].update(win=value))
            with self.subTest(value=value), self.assertRaises(ValueError): analysis.validate_grid(r, self.ids)
        r = self.edited(lambda rows: rows[0]['terminal'].update(value=[0, 1], win=0))
        with self.assertRaises(ValueError): analysis.validate_grid(r, self.ids)

    def test_fractional_ties_and_money_city_tiebreakers(self):
        screen = next(s for s in self.p['screens'] if s['players'] == 3 and s['opponent'] == 'economic')
        row = deepcopy(self.reports['filter']['economic/3p'][0]); set_winners(row, {0, 1, 2})
        def score(): return analysis.score_record(row, 'filter', screen, self.ids['filter'], self.p)[1]
        self.assertEqual(score(), {'credit': Fraction(1, 3), 'strict': 0, 'tied': 1})
        row['terminal']['final']['players'][1]['money'] = 2
        row['terminal'].update(value=[0, 1, 0], win=0)
        self.assertEqual(score()['credit'], 0)
        row['terminal']['final']['players'][0].update(money=2, cities=11)
        row['terminal'].update(value=[1, 0, 0], win=1)
        self.assertEqual(score()['strict'], 1)

    def test_equal_player_count_weighting_and_all_adverse_views_retained(self):
        def winners(arm, n, d, rule, seat):
            win = arm == 'conservative_population' and n == 2
            return {seat if win else (seat+1) % n}
        r = synthetic_grid(self.p, self.ids, winners); result = analysis.analyze(r, self.ids)
        primary = result['search_equal_count']['conservative_population_minus_filter']
        self.assertEqual(primary['exact_difference'], '1/5')
        self.assertNotEqual(primary['win_credit_difference'], .1)  # Wrong game weighting: 2 / (2+3+4+5+6).
        for record in r['conservative_population']['search_geo/6p']:
            set_winners(record, {(record['terminal']['seat']+1)%6})
        for record in r['filter']['search_geo/6p']:
            set_winners(record, {record['terminal']['seat']})
        adverse = analysis.analyze(r, self.ids)['all_cell_directions']['conservative_population_minus_filter']['negative']
        self.assertEqual(len(adverse), 5)
        self.assertTrue(all(v['cell'] == 'search_geo/6p' and v['difference'] == -1 for v in adverse))

    def test_bootstrap_preserves_shared_whole_deals(self):
        def winners(arm, n, d, rule, seat):
            return {seat if arm != 'filter' and d % 2 == 0 else (seat+1) % n}
        result = analysis.analyze(synthetic_grid(self.p, self.ids, winners), self.ids)
        independent_rng = np.random.default_rng(281028)
        sampled = independent_rng.integers(32, size=(10000, 5, 32))
        expected = np.quantile((sampled % 2 == 0).mean(axis=(1, 2)), [.025, .975])
        value = result['search_equal_count']['conservative_population_minus_filter']
        np.testing.assert_allclose(value['paired_whole_deal_95_interval'], expected, atol=1e-15)
        key = 'conservative_population_minus_filter'
        for n in range(2, 7):
            cell = result['contrasts'][key][f'search_geo/{n}p']
            expected = np.quantile((sampled[:, n-2, :] % 2 == 0).mean(axis=1), [.025, .975]).tolist()
            for view in ('overall', *analysis.RULES):
                self.assertEqual(cell[view]['win_credit_difference']['paired_whole_deal_95_interval'], expected)
            other = result['contrasts'][key][f'economic/{n}p']
            self.assertEqual(cell, other)

    def test_asynchronous_receipt_order_cannot_change_statistics(self):
        shuffled = {a: {c: list(rows) for c, rows in cells.items()} for a, cells in self.reports.items()}
        rng = random.Random(7)
        for cells in shuffled.values():
            for rows in cells.values(): rng.shuffle(rows)
        self.assertEqual(analysis.analyze(shuffled, self.ids), analysis.analyze(self.reports, self.ids))


class ConfirmationRequirementsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        p=analysis.protocol();ids=identities(p)
        cls.final=json.loads(Path(analysis.__file__).with_name('final-protocol-multiplayer.json').read_text())
        cls.perfect=analysis.analyze(synthetic_grid(p,ids,
            lambda arm,n,d,rule,seat:{seat if arm=='conservative_population' else (seat+1)%n}),ids)

    def test_perfect_synthetic_result_still_cannot_select_or_qualify(self):
        review=analysis.confirmation_requirements(self.perfect,self.final)
        self.assertTrue(review['passed']);self.assertEqual(len(review['checks']),157)
        self.assertFalse(self.perfect['candidate_selected']);self.assertFalse(self.perfect['qualification_eligible'])

    def test_one_bad_default_bot_count_prevents_promotion(self):
        r=deepcopy(self.perfect)
        r['absolute']['conservative_population']['legacy/5p']['overall']['win_credit']['exact_mean']='89/100'
        review=analysis.confirmation_requirements(r,self.final)
        self.assertFalse(review['passed'])
        self.assertEqual([(c['requirement'],c['cell']) for c in review['failed_checks']],
                         [('unchanged_overall_point_floor','legacy/5p')])

    def test_roundoff_at_chance_does_not_pass_strict_lower_bound(self):
        r=deepcopy(self.perfect)
        r['absolute']['conservative_population']['search_geo/3p']['recharged/sealed']['win_credit']['paired_whole_deal_95_interval'][0]=np.nextafter(1/3,1)
        review=analysis.confirmation_requirements(r,self.final)
        self.assertFalse(review['passed']);self.assertEqual(len(review['failed_checks']),1)
        self.assertEqual(review['failed_checks'][0]['rules'],'recharged/sealed')

    def test_zero_primary_gain_does_not_pass(self):
        r=deepcopy(self.perfect)
        r['search_equal_count']['conservative_population_minus_filter']['paired_whole_deal_95_interval'][0]=0
        self.assertFalse(analysis.confirmation_requirements(r,self.final)['passed'])


if __name__ == '__main__': unittest.main()
