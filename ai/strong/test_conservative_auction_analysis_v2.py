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
import conservative_auction_analysis_v2 as analysis

spec = importlib.util.spec_from_file_location('comparison_cli', Path(__file__).with_name('compare-conservative-auction-development-v2.py'))
cli = importlib.util.module_from_spec(spec); spec.loader.exec_module(cli)


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
            for d in range(8):
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

    def test_complete_10080_games_and_no_selection(self):
        result = analysis.analyze(self.reports, self.ids)
        self.assertEqual(result['games'], 10080)
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
                 lambda rows: rows[0].update(episode=64)]
        for edit in edits:
            with self.subTest(edit=edit), self.assertRaises(ValueError):
                analysis.validate_grid(self.edited(edit), self.ids)

    def test_missing_arm_cell_or_identity_rejected(self):
        r = dict(self.reports); r.pop('conservative_dual')
        with self.assertRaises(ValueError): analysis.validate_grid(r, self.ids)
        r = {a: dict(cells) for a, cells in self.reports.items()}; r['filter'].pop('rush/6p')
        with self.assertRaises(ValueError): analysis.validate_grid(r, self.ids)
        ids = deepcopy(self.ids); ids['conservative_dual']['settings']['minimum_advantage'] = '0'
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
        negative = result['all_cell_directions']['conservative_dual_minus_conservative_population']['negative']
        self.assertEqual(len(negative), 6*5)  # Every 2p opponent, overall and four rules.
        self.assertTrue(all(v['difference'] == -1 for v in negative))

    def test_bootstrap_preserves_shared_whole_deals(self):
        def winners(arm, n, d, rule, seat):
            return {seat if arm != 'filter' and d % 2 == 0 else (seat+1) % n}
        result = analysis.analyze(synthetic_grid(self.p, self.ids, winners), self.ids)
        independent_rng = np.random.default_rng(15125)
        sampled = independent_rng.integers(8, size=(10000, 5, 8))
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
        dual = result['search_equal_count']['conservative_dual_minus_conservative_population']
        self.assertEqual(dual['paired_whole_deal_95_interval'], [0, 0])

    def test_asynchronous_receipt_order_cannot_change_statistics(self):
        shuffled = {a: {c: list(rows) for c, rows in cells.items()} for a, cells in self.reports.items()}
        rng = random.Random(7)
        for cells in shuffled.values():
            for rows in cells.values(): rng.shuffle(rows)
        self.assertEqual(analysis.analyze(shuffled, self.ids), analysis.analyze(self.reports, self.ids))


class CompletionAdmissionTests(unittest.TestCase):
    def fixture(self):
        # Small synthetic job index for admission arithmetic only; not actual receipts.
        rows = [{'name': f'job{i}', 'shard': {'games': 3360}} for i in range(3)]
        jobs = [{'name': r['name'], 'row': r, 'job_id': format(i+1, '024x'), 'verified': True,
                 'stage': 'COMPLETED', 'review': {'games': 3360, 'audit': {'all_receipts_verified': True,
                 'reserved_final_seeds_used': False, 'counts': {'rollout_caps': 0}}}} for i, r in enumerate(rows)]
        return {'rows': rows}, {'complete': True, 'verified_jobs': 3, 'expected_jobs': 3, 'jobs': jobs,
                              'qualified': False, 'reserved_final_seeds_used': False}

    def test_incomplete_failed_duplicate_or_wrong_source_jobs_rejected(self):
        source, report = self.fixture(); self.assertEqual(len(cli.completion_index(source, report)), 3)
        edits = [lambda r: r.update(complete=False), lambda r: r['jobs'].pop(),
                 lambda r: r['jobs'][0].update(stage='ERROR'), lambda r: r['jobs'][0].update(verified=False),
                 lambda r: r['jobs'][1].update(job_id=r['jobs'][0]['job_id']),
                 lambda r: r['jobs'][1].update(name=r['jobs'][0]['name']),
                 lambda r: r['jobs'][0]['review']['audit']['counts'].update(rollout_caps=1),
                 lambda r: r['jobs'][0]['review'].update(games=3359),
                 lambda r: r['jobs'][0].update(row={'name': 'other'})]
        for edit in edits:
            r = deepcopy(report); edit(r)
            with self.subTest(edit=edit), self.assertRaises(ValueError): cli.completion_index(source, r)

    def test_cli_refuses_live_partial_execution_without_side_effects(self):
        with tempfile.TemporaryDirectory() as tmp:
            owner = Path(tmp)/'owner.json'; owner.write_text(json.dumps({'stage': 'waiting_for_original_pilots'}))
            output = Path(tmp)/'result.json'
            with patch.object(cli, 'OWNER', owner), patch.object(cli, 'manager_module') as manager:
                with self.assertRaisesRegex(ValueError, 'Wait for complete'): cli.compare(output)
                manager.assert_not_called()
            self.assertFalse(output.exists()); self.assertFalse(output.with_suffix('.intent.json').exists())

    def test_existing_intent_requires_inspection_not_retry(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)/'result.json'; output.with_suffix('.intent.json').write_text('{}')
            with patch.object(cli, 'manager_module') as manager:
                with self.assertRaisesRegex(ValueError, 'Inspect existing'): cli.compare(output)
                manager.assert_not_called()

    def test_archive_bytes_and_internal_manifest_must_both_match(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp)/'case.tgz'; manifest = b'{"game.json": "synthetic-only"}'
            with tarfile.open(archive, 'w:gz') as bundle:
                info = tarfile.TarInfo('manifest.json'); info.size = len(manifest)
                bundle.addfile(info, io.BytesIO(manifest))
            evidence = {'repo': 'coyotte508/powergrid-ai-germany-v1', 'archive_path': 'archives/case.tgz',
                'remote_archive_verified': True, 'revision': 'a'*40,
                'archive_sha256': cli.digest(archive), 'manifest_sha256': hashlib.sha256(manifest).hexdigest()}
            with patch.object(cli, 'hf_hub_download', return_value=str(archive)) as download:
                cli.immutable_archive(evidence, 'case')
                download.assert_called_once_with(evidence['repo'], evidence['archive_path'], revision='a'*40)
                for field in ('archive_sha256', 'manifest_sha256', 'revision', 'archive_path'):
                    broken = {**evidence, field: 'b'*64}
                    with self.subTest(field=field), self.assertRaises(ValueError): cli.immutable_archive(broken, 'case')

    def test_duplicate_archive_manifests_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp)/'case.tgz'
            with tarfile.open(archive, 'w:gz') as bundle:
                for _ in range(2):
                    info = tarfile.TarInfo('manifest.json'); info.size = 2
                    bundle.addfile(info, io.BytesIO(b'{}'))
            evidence = {'repo': 'coyotte508/powergrid-ai-germany-v1', 'archive_path': 'archives/case.tgz',
                'remote_archive_verified': True, 'revision': 'a'*40,
                'archive_sha256': cli.digest(archive), 'manifest_sha256': hashlib.sha256(b'{}').hexdigest()}
            with patch.object(cli, 'hf_hub_download', return_value=str(archive)):
                with self.assertRaisesRegex(ValueError, 'duplicate'): cli.immutable_archive(evidence, 'case')


if __name__ == '__main__': unittest.main()
