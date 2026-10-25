"""Submission/receipt failure boundaries without contacting HF or simulating games."""
from copy import deepcopy
import importlib.util
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch, Mock

from strategic_collection import ROOT, read, write, digest

spec = importlib.util.spec_from_file_location('selected_manager_test', ROOT/'ai/strong/manage-surrogate-continuation-selected-cost-v1.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)


class ManagerTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory(); self.addCleanup(self.temp.cleanup); self.root = Path(self.temp.name)
        for key, path in [('GUARDS', 'guards'), ('COLLECTED', 'collected'), ('RESULT', 'result.json'), ('PLAN', 'plan.json')]:
            p = patch.object(m, key, self.root/path); p.start(); self.addCleanup(p.stop)
        self.source = {key: 'a'*64 for key in ('sha256', 'manifest_sha256', 'study_inputs_sha256', 'runtime_inputs_sha256', 'surrogate_policy_sha256')}
        self.source.update(revision='b'*40, archive='source.tgz', manifest_files=1486)
        self.plan = {'admission': {'flavor': 'cpu-upgrade', 'timeout_hours': 2}}
        write(m.PLAN, self.plan)
        p = patch.object(m, 'admission', return_value=(self.plan, self.source)); p.start(); self.addCleanup(p.stop)
        p = patch.object(m, 'get_token', return_value='test-fixture-secret'); p.start(); self.addCleanup(p.stop)
        self.api = Mock()
        p = patch.object(m, 'HfApi', return_value=self.api); p.start(); self.addCleanup(p.stop)
        self.job_id = 'c'*24
        self.api.run_job.return_value = SimpleNamespace(id=self.job_id)
        self.api.inspect_job.return_value = SimpleNamespace(status=SimpleNamespace(stage='RUNNING'))

    def guard(self): return m.GUARDS/(m.runner.CASE+'.json')

    def test_allowance_uses_completed_costs_without_admitting_study(self):
        evidence = read(m.builder.COST); a = m.allowance(evidence)
        self.assertEqual(a['timeout_hours'], 2); self.assertEqual(a['max_concurrent'], 1)
        self.assertAlmostEqual(a['historical_mixture_max_seconds'], 14.245794248010497, places=4)
        self.assertLess(a['memory_allowance_bytes'], 32e9)
        bad = deepcopy(evidence); bad['caps'] = 1
        with self.assertRaises(AssertionError): m.allowance(bad)
        for value in (float('nan'), 100000.):
            bad = deepcopy(evidence); next(iter(bad['measurements'].values()))['modes']['neural_population']['seconds'] = value
            with self.assertRaises(AssertionError): m.allowance(bad)

    def test_dry_run_performs_no_network_or_guard_creation(self):
        result = m.launch(False)
        self.assertFalse(result['execute']); self.api.run_job.assert_not_called(); self.api.inspect_job.assert_not_called()
        self.assertFalse(m.GUARDS.exists())

    def test_successful_submission_binds_exact_source_and_private_secret(self):
        self.assertEqual(m.launch(True)['job_id'], self.job_id)
        guard = read(self.guard()); self.assertEqual(guard['source'], self.source); self.assertEqual(guard['stage'], 'launched')
        kwargs = self.api.run_job.call_args.kwargs
        self.assertEqual(kwargs['env']['SURROGATE_POLICY_SHA256'], self.source['surrogate_policy_sha256'])
        self.assertEqual(kwargs['env']['RUNTIME_INPUTS_SHA256'], self.source['runtime_inputs_sha256'])
        self.assertEqual(kwargs['timeout'], '2h'); self.assertEqual(kwargs['flavor'], 'cpu-upgrade')
        self.assertNotIn('test-fixture-secret', self.guard().read_text())
        self.assertNotIn('HF_TOKEN', kwargs['env'])
        self.assertIn('surrogate_continuation_selected_cost_v1.py', kwargs['command'][-1])

    def test_unknown_submission_is_never_retried_and_error_is_redacted(self):
        self.api.run_job.side_effect = TimeoutError('possibly submitted with test-fixture-secret')
        with self.assertRaises(TimeoutError): m.launch(True)
        self.assertEqual(read(self.guard())['stage'], 'launch_unknown')
        self.assertNotIn('test-fixture-secret', self.guard().read_text())
        before = digest(self.guard())
        with self.assertRaisesRegex(AssertionError, 'original uncertain'): m.launch(True)
        self.assertEqual(before, digest(self.guard())); self.assertEqual(self.api.run_job.call_count, 1)

    def test_existing_failed_job_or_observation_error_never_replaces_handle(self):
        m.launch(True); before = digest(self.guard())
        self.api.inspect_job.return_value.status.stage = 'ERROR'
        self.assertEqual(m.launch(True)['authoritative_status'], 'ERROR')
        self.api.inspect_job.side_effect = TimeoutError('observation only')
        with self.assertRaises(TimeoutError): m.launch(True)
        self.assertEqual(before, digest(self.guard())); self.assertEqual(self.api.run_job.call_count, 1)

    def test_pending_collection_has_no_download_or_completed_result(self):
        m.launch(True)
        with patch.object(m, 'hf_hub_download') as download:
            result = m.collect(); download.assert_not_called()
        self.assertEqual(result['authoritative_status'], 'RUNNING'); self.assertFalse(m.RESULT.exists())
        self.api.fetch_job_logs.assert_not_called()

    def test_ambiguous_or_failed_evidence_preserves_logs_and_cannot_verify(self):
        m.launch(True); self.api.inspect_job.return_value.status.stage = 'COMPLETED'
        bad = {'status': {'case': m.runner.CASE, 'stage': 'failed'}, 'evidence': {'repo': 'wrong-repository'}}
        for lines in ([repr(bad), repr(bad)], [repr(bad)]):
            self.api.fetch_job_logs.return_value = lines
            with patch.object(m, 'hf_hub_download') as download:
                with self.assertRaises(AssertionError): m.collect()
                download.assert_not_called()
            self.assertFalse(m.RESULT.exists()); self.assertEqual((m.COLLECTED/'job.log').read_text(), '\n'.join(lines))
        self.assertEqual(self.api.run_job.call_count, 1)


if __name__ == '__main__': unittest.main()
