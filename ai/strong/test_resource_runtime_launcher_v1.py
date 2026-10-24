"""Exercise remote-submission boundaries without network access or job creation."""
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

spec = importlib.util.spec_from_file_location('resource_runtime_launcher',
    Path(__file__).with_name('launch-resource-replanning-runtime-v1.py'))
launcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launcher)


def synthetic_pilot():
    return {'cells': {f'{n}p-resource-filter': {
        'runtime': {'seconds': 1200, 'cpu_seconds': 6400,
                    'sampled_peak_total_rss_bytes': 7_000_000_000},
        'raw_evaluation_bytes': 10_000_000} for n in (2, 6)}}


class RuntimeLauncherTest(unittest.TestCase):
    def test_incomplete_pilot_cannot_prepare_or_submit(self):
        with tempfile.TemporaryDirectory() as temp, \
                patch.object(launcher, 'PILOT', Path(temp) / 'missing.json'), \
                patch.object(launcher, 'HfApi', side_effect=AssertionError('No remote call allowed')) as api:
            for call in (lambda: launcher.prepare('cpu-upgrade', 1),
                         lambda: launcher.launch(2, True), lambda: launcher.launch(6, True)):
                with self.assertRaisesRegex(AssertionError, 'complete local 64-game / 16-replay'):
                    call()
            api.assert_not_called()
            self.assertEqual(list(Path(temp).iterdir()), [])

    def test_invalid_endpoint_is_rejected_before_reading_inputs(self):
        with patch.object(launcher, 'prerequisites') as prerequisites:
            for value in (True, 3, 5, '2'):
                with self.assertRaises(AssertionError):
                    launcher.launch(value, True)
            prerequisites.assert_not_called()

    def test_measured_budget_has_cpu_memory_and_storage_headroom(self):
        pilot = synthetic_pilot()
        self.assertEqual(launcher.measured_admission(pilot, 'cpu-upgrade', 1)
                         ['estimated_timeout_floor_seconds'], 3300)
        edits = [
            lambda cell: cell['runtime'].update(sampled_peak_total_rss_bytes=17_000_000_000),
            lambda cell: cell['runtime'].update(seconds=2000),
            lambda cell: cell['runtime'].update(cpu_seconds=20_000),
            lambda cell: cell.update(raw_evaluation_bytes=13_000_000_000),
        ]
        for edit in edits:
            bad = copy.deepcopy(pilot)
            edit(bad['cells']['6p-resource-filter'])
            with self.assertRaises(AssertionError):
                launcher.measured_admission(bad, 'cpu-upgrade', 1)
        for flavor, hours in [('cpu-basic', 1), ('cpu-upgrade', True), ('cpu-upgrade', 0)]:
            with self.assertRaises(AssertionError):
                launcher.measured_admission(pilot, flavor, hours)

    def test_duplicate_and_ambiguous_submissions_are_not_retried(self):
        with tempfile.TemporaryDirectory() as temp, contextlib.ExitStack() as stack:
            directory = Path(temp)
            for name in ('SOURCE', 'PILOT', 'PREFLIGHT', 'PROTOCOL'):
                path = directory / (name + '.json')
                path.write_text('{}\n')
                stack.enter_context(patch.object(launcher, name, path))
            stack.enter_context(patch.object(launcher, 'ADMISSION', directory / 'admission.json'))
            stack.enter_context(patch.object(launcher, 'GUARDS', directory / 'guards'))
            archive = directory / 'source.tgz'
            archive.write_bytes(b'synthetic test fixture, not a runnable source')
            source = {'repo': 'synthetic', 'revision': 'synthetic', 'archive': archive.name,
                      'sha256': launcher.digest(archive), 'manifest_sha256': 'synthetic'}
            stack.enter_context(patch.object(launcher, 'prerequisites',
                                            return_value=(synthetic_pilot(), source, {})))
            stack.enter_context(patch.object(launcher, 'get_token', return_value='test-only-token'))
            stack.enter_context(patch.object(launcher, 'hf_hub_download', return_value=str(archive)))
            api = Mock()
            api.run_job.return_value = SimpleNamespace(id='000000000000000000000001')
            api.inspect_job.return_value = SimpleNamespace(status=SimpleNamespace(stage='COMPLETED'))
            stack.enter_context(patch.object(launcher, 'HfApi', return_value=api))
            stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
            launcher.prepare('cpu-upgrade', 1)
            launcher.launch(2, False)
            api.run_job.assert_not_called()
            launcher.launch(2, True)
            with self.assertRaises(FileExistsError):
                launcher.launch(2, True)
            self.assertEqual(api.run_job.call_count, 1)
            api.run_job.side_effect = TimeoutError('Injected unknown submission')
            with self.assertRaises(TimeoutError):
                launcher.launch(6, True)
            guards = list((directory / 'guards').glob('*.json'))
            self.assertEqual(len(guards), 2)
            statuses = {json.loads(path.read_text())['players']: json.loads(path.read_text())['stage']
                        for path in guards}
            self.assertEqual(statuses, {2: 'launched', 6: 'launch_unknown'})
            with self.assertRaisesRegex(AssertionError, 'Reconcile an unresolved submission'):
                launcher.launch(6, True)
            self.assertEqual(api.run_job.call_count, 2)
            self.assertTrue(all('test-only-token' not in path.read_text() for path in guards))

    def test_bootstrap_shell_syntax(self):
        subprocess.run(['bash', '-n'], input=launcher.BOOTSTRAP, text=True, check=True)


if __name__ == '__main__':
    unittest.main()
