"""Resource-screen coverage, measured budgets and submission boundary checks."""
import contextlib
import copy
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

spec = importlib.util.spec_from_file_location('resource_development_launcher', Path(__file__).with_name('launch-resource-replanning-development-v1.py'))
launcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launcher)


def measurements(seconds=1200):
    return {str(n): {'runtime': {'seconds': seconds, 'cpu_seconds': 6400,
                                'sampled_peak_total_rss_bytes': 7_000_000_000},
                    'raw_evaluation_bytes': 10_000_000} for n in (2, 6)}


def hardware():
    return {'flavor': 'cpu-upgrade', 'vcpus': 8, 'ram_gb': 32, 'disk_gb': 50}


@contextlib.contextmanager
def synthetic_launch(max_in_flight=2):
    with tempfile.TemporaryDirectory() as temp, contextlib.ExitStack() as stack:
        folder = Path(temp)
        for name in ('SOURCE', 'CALIBRATION'):
            path = folder / (name + '.json')
            path.write_text('{}\n')
            stack.enter_context(patch.object(launcher, name, path))
        stack.enter_context(patch.object(launcher, 'PLAN', folder / 'plan.json'))
        stack.enter_context(patch.object(launcher, 'GUARDS', folder / 'guards'))
        archive = folder / 'source.tgz'
        archive.write_bytes(b'Synthetic test fixture; not a runnable source')
        source = {'repo': 'test-only', 'revision': 'test-only', 'archive': archive.name,
                  'sha256': launcher.digest(archive), 'manifest_sha256': 'test-only'}
        stack.enter_context(patch.object(launcher, 'prerequisites', return_value=(source, {'admission': {'hardware': hardware()}}, measurements())))
        stack.enter_context(patch.object(launcher, 'get_token', return_value='test-only-token'))
        stack.enter_context(patch.object(launcher, 'hf_hub_download', return_value=str(archive)))
        api = Mock()
        api.run_job.return_value = SimpleNamespace(id='000000000000000000000001')
        api.inspect_job.return_value = SimpleNamespace(status=SimpleNamespace(stage='COMPLETED'))
        stack.enter_context(patch.object(launcher, 'HfApi', return_value=api))
        stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
        launcher.prepare(max_in_flight)
        yield folder, api, launcher.read(launcher.PLAN)


class ResourceDevelopmentLauncherTest(unittest.TestCase):
    def test_missing_calibration_never_prepares_or_submits(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(launcher, 'CALIBRATION', Path(temp) / 'absent.json'), \
                patch.object(launcher, 'HfApi') as api:
            for call in (lambda: launcher.prepare(16), lambda: launcher.launch('any-case', True)):
                with self.assertRaisesRegex(AssertionError, 'Both complete HF endpoints'):
                    call()
            api.assert_not_called()
            self.assertEqual(list(Path(temp).iterdir()), [])

    def test_budget_splits_whole_deals_instead_of_shortening_search(self):
        for seconds, deals, hours in [(1200, 4, 4), (5000, 2, 8), (10000, 1, 8)]:
            result = launcher.measured_admission(measurements(seconds), hardware(), 16)
            self.assertEqual((result['deals_per_shard'], result['timeout_hours']), (deals, hours))
            self.assertEqual((result['samples'], result['workers'], result['search_workers']), (8, 8, 1))
        with self.assertRaisesRegex(AssertionError, 'new execution plan'):
            launcher.measured_admission(measurements(50000), hardware(), 16)
        bad = measurements()
        bad['6']['runtime']['sampled_peak_total_rss_bytes'] = 17_000_000_000
        with self.assertRaisesRegex(AssertionError, 'memory headroom'):
            launcher.measured_admission(bad, hardware(), 16)
        bad = measurements()
        bad['6']['raw_evaluation_bytes'] = 4_000_000_000
        self.assertEqual(launcher.measured_admission(bad, hardware(), 16)['deals_per_shard'], 2)
        for limit in (0, 33, True):
            with self.assertRaises(AssertionError):
                launcher.measured_admission(measurements(), hardware(), limit)

    def test_complete_plan_cannot_drop_or_duplicate_cells(self):
        with synthetic_launch() as (_, api, plan):
            self.assertEqual(len(plan['shards']), 54)
            for arm in ('filter', 'resource-filter'):
                cells = [row for row in plan['shards'] if row['arm'] == arm]
                self.assertEqual(sum(row['games'] for row in cells), 1680)
                self.assertEqual({row['players'] for row in cells}, {2, 3, 4, 5, 6})
                self.assertEqual(len(cells), 27)
            protocol = launcher.read(launcher.PROTOCOL)
            for step, shards in ((1, 216), (2, 108), (4, 54)):
                partition = copy.deepcopy(plan)
                partition['admission']['deals_per_shard'] = step
                partition['shards'] = launcher.case_rows(protocol, step)
                launcher.validate_plan(partition, protocol)
                self.assertEqual(len(partition['shards']), shards)
                self.assertEqual(sum(row['games'] for row in partition['shards']), 3360)
            for edit in (lambda p: p['shards'].pop(), lambda p: p['shards'].append(p['shards'][0]),
                         lambda p: p['shards'][0].update(start=1), lambda p: p.update(planned_games=100)):
                bad = copy.deepcopy(plan)
                edit(bad)
                with self.assertRaises(AssertionError):
                    launcher.validate_plan(bad, protocol)
            api.run_job.assert_not_called()

    def test_dry_run_duplicates_and_unknown_submission(self):
        with synthetic_launch() as (folder, api, plan):
            first, second, third = [row['case'] for row in plan['shards'][:3]]
            launcher.launch(first, False)
            api.run_job.assert_not_called()
            with self.assertRaisesRegex(AssertionError, 'outside the complete fixed experiment'):
                launcher.launch('not-a-planned-case', True)
            launcher.launch(first, True)
            self.assertEqual(api.run_job.call_args.kwargs['env']['ARM'], 'resource-filter')
            with self.assertRaises(FileExistsError):
                launcher.launch(first, True)
            self.assertEqual(api.run_job.call_count, 1)
            api.run_job.side_effect = TimeoutError('Injected ambiguous submission')
            with self.assertRaises(TimeoutError):
                launcher.launch(second, True)
            self.assertEqual(launcher.read(launcher.GUARDS / (second + '.json'))['stage'], 'launch_unknown')
            for case in (second, third):
                with self.assertRaisesRegex(AssertionError, 'Reconcile unresolved'):
                    launcher.launch(case, True)
            self.assertEqual(api.run_job.call_count, 2)
            self.assertTrue(all('test-only-token' not in path.read_text() for path in launcher.GUARDS.glob('*.json')))

    def test_active_limit_and_failed_job_stop_new_submissions(self):
        with synthetic_launch(1) as (_, api, plan):
            first, second = [row['case'] for row in plan['shards'][:2]]
            launcher.launch(first, True)
            for stage, message in [('RUNNING', 'occupy all admitted'), ('ERROR', 'Review failed')]:
                api.inspect_job.return_value.status.stage = stage
                with self.assertRaisesRegex(AssertionError, message):
                    launcher.launch(second, True)
            self.assertEqual(api.run_job.call_count, 1)
            self.assertEqual(len(list(launcher.GUARDS.glob('*.json'))), 1)

    def test_source_bootstrap_and_development_invocation(self):
        self.assertIn('assert len(files)==1484', launcher.BOOTSTRAP)
        self.assertNotIn('--runtime-pilot', launcher.BOOTSTRAP)
        self.assertEqual(launcher.BOOTSTRAP.count(launcher.NEW_COMMAND), 1)
        subprocess.run(['bash', '-n'], input=launcher.BOOTSTRAP, text=True, check=True)


if __name__ == '__main__':
    unittest.main()
