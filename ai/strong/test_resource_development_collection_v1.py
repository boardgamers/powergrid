"""Adversarial collection, complete-grid statistics and resume boundary tests.

The artifact fixture changes only the outer identity of an archived runtime job;
it is synthetic packaging around real receipts, not a new development game.
"""
import contextlib
import copy
import importlib.util
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('resource_coordinator_test', Path(__file__).with_name('coordinate-resource-replanning-development-v1.py'))
coordinator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(coordinator)
comparison, manager, launcher = coordinator.comparison, coordinator.manager, coordinator.launcher
protocol = manager.read(launcher.PROTOCOL)


def reports():
    result = {arm: {} for arm in protocol['arms']}
    for arm in result:
        for screen in protocol['screens']:
            n = screen['players']
            result[arm][f'{screen["opponent"]}/{n}p'] = [
                {'gameSeed': protocol['seed_template'].format(players=n) + '-' + str(d),
                 'variant': v, 'sealed': s, 'seat': seat, 'truncated': False, 'win': 0.}
                for d in range(4) for v in ('original', 'recharged') for s in (False, True) for seat in range(n)]
    return result


def refresh_manifest(folder):
    manager.write(folder / 'manifest.json', {str(p.relative_to(folder)): manager.digest(p)
                  for p in sorted(folder.rglob('*')) if p.is_file() and p.name != 'manifest.json'})
    return {'manifest_sha256': manager.digest(folder / 'manifest.json'),
            'archived_files': len(manager.read(folder / 'manifest.json')) + 1}


class CompleteGridTests(unittest.TestCase):
    def test_partial_grid_refused_before_raw_reads_or_output(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            plan_path, output = root / 'plan.json', root / 'comparison.json'
            plan = {'planned_games': 3360, 'admission': {'deals_per_shard': 4},
                    'shards': launcher.case_rows(protocol, 4), 'automatic_retries': False,
                    'gradients': False, 'qualification_eligible': False, 'reserved_final_seeds_used': False}
            manager.write(plan_path, plan)
            with patch.object(launcher, 'PLAN', plan_path), patch.object(manager, 'COLLECTED', root / 'absent'), \
                    patch.object(manager, 'verified_receipt') as raw, patch.object(manager, 'HfApi') as api:
                with self.assertRaisesRegex(AssertionError, 'All resource shards must verify first'):
                    comparison.compare(output)
                raw.assert_not_called()
                api.assert_not_called()
                self.assertFalse(output.exists())

    def test_count_weights_do_not_favor_six_players_and_keep_regressions(self):
        data = reports()
        values = {2: (1., 0.), 3: (0., .5), 4: (.5, .5), 5: (0., .2), 6: (0., 1.)}
        for n, (left, right) in values.items():
            for arm, value in [('filter', left), ('resource-filter', right)]:
                for row in data[arm][f'search_geo/{n}p']:
                    row['win'] = value
        result = comparison.analyze(data, protocol)
        self.assertAlmostEqual(result['primary_search_equal_count']['win_share_difference'], .14)
        self.assertAlmostEqual(result['resource_minus_filter']['search_geo/2p']['overall']['win_share_difference'], -1.)
        self.assertEqual(len(result['resource_minus_filter']), 27)
        self.assertTrue(all(len(row['by_rules']) == 4 for row in result['resource_minus_filter'].values()))
        self.assertEqual(result['secondary_economic_equal_count']['win_share_difference'], 0.)

    def test_deal_bootstrap_keeps_all_seats_rules_together(self):
        data = reports()
        for row in data['resource-filter']['search_geo/2p']:
            if row['gameSeed'].endswith('-3'):
                row['win'] = 1.
        comparison.validate_grid(data, protocol)
        result = comparison.equal_count_summary(data, 'search_geo', protocol)
        self.assertAlmostEqual(result['win_share_difference'], .05)
        # Binomial(4, .25) / 20, rather than independently resampling 32 matches.
        self.assertEqual(result['paired_deal_bootstrap_95_interval'], [0., .15])

    def test_incomplete_duplicate_wrong_seed_and_invalid_outcome_rejected(self):
        for edit in [lambda d: d.pop('filter'), lambda d: d['filter'].pop('search_geo/6p'),
                     lambda d: d['filter']['search_geo/2p'].pop(),
                     lambda d: d['filter']['search_geo/2p'].__setitem__(1, d['filter']['search_geo/2p'][0]),
                     lambda d: d['resource-filter']['search_geo/2p'][0].update(gameSeed='runtime-only'),
                     lambda d: d['filter']['search_geo/2p'][0].update(truncated=True),
                     lambda d: d['filter']['search_geo/2p'][0].update(win=float('nan'))]:
            data = reports()
            edit(data)
            with self.assertRaises(AssertionError):
                comparison.analyze(data, protocol)


class CollectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.folder = Path(cls.temp.name) / 'artifacts'
        original = manager.ROOT / 'ai/runs/resource-replanning-hf-runtime-collected-v1/resource-replanning-hf-runtime-v1-2p-resource-filter/artifacts'
        assert original.exists(), 'Requires the already verified 2p HF artifact; no jobs are started'
        shutil.copytree(original, cls.folder)
        cls.row = next(row for row in launcher.case_rows(protocol, 1)
                       if (row['arm'], row['players'], row['opponent'], row['start']) == ('resource-filter', 2, 'search_geo', 0))
        cls.source = manager.read(launcher.SOURCE)
        case, _, expected = manager.wrapper.contract(protocol, 'resource-filter', 2, 'search_geo', 0, 1)
        expected['runtime'] = '/workspace'
        check = manager.read(cls.folder / 'resource-check.json')
        check.update(case=case, runtime_pilot=False, expected_config=expected)
        manager.write(cls.folder / 'resource-check.json', check)
        report = manager.read(cls.folder / 'evaluation/evaluation.json')
        report['config'].update(**expected, output=f'/workspace/ai/runs/{case}/evaluation')
        for row in report['results']:
            row['terminal']['gameSeed'] = expected['seed'] + '-0'
            manager.write(cls.folder / f'evaluation/game-{row["episode"]}.json', row)
        manager.write(cls.folder / 'evaluation/evaluation.json', report)
        summary = manager.verify_evaluation(cls.folder / 'evaluation', report['config'])
        manager.write(cls.folder / 'summary.json', summary)
        cls.evidence = refresh_manifest(cls.folder)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_real_decisions_survive_synthetic_development_envelope(self):
        result = manager.verify_artifacts(self.folder, self.row, self.source, protocol, self.evidence)
        self.assertEqual(result['summary']['games'], 8)
        self.assertEqual(result['summary']['counts']['decisions'], 1306)
        self.assertEqual(result['summary']['counts']['rollouts'], 41632)

    def test_resealed_wrong_identity_cannot_pass_as_development(self):
        path = self.folder / 'resource-check.json'
        original = path.read_bytes()
        edits = [lambda r: r.update(runtime_pilot=True), lambda r: r.update(source_revision='wrong'),
                 lambda r: r['expected_config'].update(seed=protocol['smoke_seed_template'].format(players=2)),
                 lambda r: r['expected_config'].update(samples=4), lambda r: r.update(qualification_eligible=True)]
        try:
            for edit in edits:
                row = json.loads(original)
                edit(row)
                manager.write(path, row)
                evidence = refresh_manifest(self.folder)
                with self.assertRaises(AssertionError):
                    manager.verify_artifacts(self.folder, self.row, self.source, protocol, evidence)
        finally:
            path.write_bytes(original)
            self.evidence = refresh_manifest(self.folder)

    def test_resealed_false_win_is_rejected_from_terminal_players(self):
        report_path = self.folder / 'evaluation/evaluation.json'
        original = report_path.read_bytes()
        report = json.loads(original)
        row = report['results'][0]
        game_path = self.folder / f'evaluation/game-{row["episode"]}.json'
        game_original = game_path.read_bytes()
        summary_path = self.folder / 'summary.json'
        summary_original = summary_path.read_bytes()
        try:
            row['terminal']['win'] = 1 - row['terminal']['win']
            manager.write(report_path, report)
            manager.write(game_path, row)
            summary = json.loads(summary_original)
            summary['report_sha256'] = manager.digest(report_path)
            manager.write(summary_path, summary)
            evidence = refresh_manifest(self.folder)
            with self.assertRaisesRegex(ValueError, 'Candidate win differs'):
                manager.verify_artifacts(self.folder, self.row, self.source, protocol, evidence)
        finally:
            report_path.write_bytes(original)
            game_path.write_bytes(game_original)
            summary_path.write_bytes(summary_original)
            self.evidence = refresh_manifest(self.folder)


class CoordinatorTests(unittest.TestCase):
    @contextlib.contextmanager
    def fixture(self, stage='RUNNING', verified=False):
        with tempfile.TemporaryDirectory() as temp, contextlib.ExitStack() as stack:
            root = Path(temp)
            guards = root / 'guards'
            guards.mkdir()
            planpath = root / 'plan.json'
            planpath.write_text('{}')
            plan = {'shards': [{'case': 'a'}, {'case': 'b'}], 'admission': {'max_in_flight': 1}}
            manager.write(guards / 'a.json', {'stage': 'launched', 'plan_sha256': manager.digest(planpath), 'job_id': 'original-job'})
            for obj, key, value in [(coordinator, 'OUT', root), (launcher, 'PLAN', planpath), (launcher, 'GUARDS', guards)]:
                stack.enter_context(patch.object(obj, key, value))
            stack.enter_context(patch.object(manager, 'verified_receipt', side_effect=lambda case: {'verified': True} if verified and case == 'a' else None))
            inspect = stack.enter_context(patch.object(manager, 'inspect', return_value={'case': 'a', 'job_id': 'original-job', 'authoritative_status': stage}))
            collect = stack.enter_context(patch.object(manager, 'collect', return_value={'case': 'a', 'verified': stage == 'COMPLETED', 'failed': stage in manager.FAILED}))
            launch = stack.enter_context(patch.object(launcher, 'launch'))
            stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
            yield plan, {}, inspect, collect, launch

    def test_live_handle_is_never_restarted(self):
        with self.fixture() as (plan, state, inspect, collect, launch):
            self.assertFalse(coordinator.cycle(plan, state, lambda: None))
            inspect.assert_called_once_with('a')
            collect.assert_not_called()
            launch.assert_not_called()

    def test_verified_completion_frees_slot_without_relaunch(self):
        with self.fixture(verified=True) as (plan, state, inspect, collect, launch):
            coordinator.cycle(plan, state, lambda: None)
            inspect.assert_not_called()
            collect.assert_not_called()
            launch.assert_called_once_with('b', True)
            self.assertEqual(state['jobs_verified'], 1)

    def test_failed_unknown_and_observation_errors_never_submit_replacement(self):
        for stage in ('ERROR', 'TIMEOUT', 'UNRECOGNIZED'):
            with self.fixture(stage) as (plan, state, inspect, collect, launch):
                with self.assertRaisesRegex(AssertionError, 'Review failed/unknown'):
                    coordinator.cycle(plan, state, lambda: None)
                launch.assert_not_called()
        with self.fixture() as (plan, state, inspect, collect, launch):
            inspect.side_effect = TimeoutError('Observation failed; remote handle remains valid')
            with self.assertRaises(TimeoutError):
                coordinator.cycle(plan, state, lambda: None)
            launch.assert_not_called()


if __name__ == '__main__':
    unittest.main()
