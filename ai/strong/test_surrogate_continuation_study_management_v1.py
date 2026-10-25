"""Measured admission, original handles, failure retention and complete aggregation."""
from copy import deepcopy
import importlib.util
from pathlib import Path
import tarfile
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch, Mock

from strategic_collection import ROOT, read, write, digest
from test_surrogate_continuation_analysis_v1 import fixture

spec = importlib.util.spec_from_file_location('study_management_test', ROOT/'ai/strong/manage-surrogate-continuation-study-v1.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); launcher = m.launcher


class ManagementTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.synthetic_manifest, cls.synthetic_reports = fixture()

    def setUp(self):
        self.temp = TemporaryDirectory(); self.addCleanup(self.temp.cleanup); self.root = Path(self.temp.name)
        for target, key, path in [(launcher, 'GUARDS', 'guards'), (launcher, 'PLAN', 'plan.json'),
                                  (m, 'COLLECTED', 'collected'), (m, 'INDEX', 'index.json'), (m, 'ANALYSIS', 'analysis.json')]:
            p = patch.object(target, key, self.root/path); p.start(); self.addCleanup(p.stop)
        self.manifest = deepcopy(self.synthetic_manifest); self.reports = deepcopy(self.synthetic_reports)
        self.source = {key: 'a'*64 for key in ('sha256', 'manifest_sha256', 'study_inputs_sha256', 'surrogate_policy_sha256')}
        self.source.update(revision='b'*40, archive='source.tgz', manifest_files=1486)
        self.rows = launcher.cases(self.manifest)
        self.plan = {'cases': self.rows, 'jobs': 480, 'continuations': 23040,
                     'admission': {'flavor': 'cpu-upgrade', 'timeout_hours': 3, 'max_concurrent': 2}}
        write(launcher.PLAN, self.plan)
        p = patch.object(launcher, 'admission', return_value=(self.plan, self.source, self.manifest)); p.start(); self.addCleanup(p.stop)
        p = patch.object(launcher, 'get_token', return_value='fixture-secret'); p.start(); self.addCleanup(p.stop)
        self.api = Mock(); self.next_id = 0
        def submit(**kwargs):
            self.next_id += 1; return SimpleNamespace(id=f'{self.next_id:024x}')
        self.api.run_job.side_effect = submit
        self.api.inspect_job.return_value = SimpleNamespace(status=SimpleNamespace(stage='RUNNING'))
        for target in (launcher, m):
            p = patch.object(target, 'HfApi', return_value=self.api); p.start(); self.addCleanup(p.stop)

    def test_actual_complete_root_grid_and_missing_root_rejection(self):
        actual = read(ROOT/'ai/runs/surrogate-continuation-roots-frozen-v1/roots.json')
        rows = launcher.cases(actual)
        self.assertEqual(len(rows), 480); self.assertEqual(sum(r['continuations'] for r in rows), 23040)
        actual['roots'].pop()
        with self.assertRaises(AssertionError): launcher.cases(actual)

    def test_all_count_allowance_uses_measured_selected_model_and_rejects_caps(self):
        reference = read(launcher.builder.COST)
        learned = {'complete': True, 'scope': 'selected_runtime_calibration', 'roots': 24, 'continuations': 384, 'caps': 0,
                   'measurements': {k: deepcopy(v['modes']['neural_population']) for k, v in reference['measurements'].items()}}
        # Explicit timing-input fixture; this does not claim a trained surrogate was measured.
        a = launcher.allowance(reference, learned)
        self.assertEqual(a['timeout_hours'], 3); self.assertEqual(a['max_concurrent'], 32)
        self.assertGreater(a['estimated_seconds_per_job'], 2*2314)
        for key, value in [('scope', 'local_engineering_fixture'), ('caps', 1), ('continuations', 368)]:
            bad = deepcopy(learned); bad[key] = value
            with self.assertRaises(AssertionError): launcher.allowance(reference, bad)
        bad = deepcopy(learned); next(iter(bad['measurements'].values()))['seconds'] = float('nan')
        with self.assertRaises(AssertionError): launcher.allowance(reference, bad)

    def test_missing_actual_calibration_refuses_before_outputs_or_network(self):
        with patch.object(launcher.calibration, 'RESULT', self.root/'absent.json'), patch.object(launcher.calibration, 'collect') as collect:
            with self.assertRaisesRegex(AssertionError, 'actual selected-surrogate'): launcher.prerequisites()
            collect.assert_not_called()
        self.api.run_job.assert_not_called(); self.assertFalse(launcher.GUARDS.exists())

    def test_preflight_binds_collector_code_as_well_as_launcher(self):
        frozen_dir = self.root/'frozen'; frozen_dir.mkdir(); write(frozen_dir/'frozen.json', {'fixture': True})
        source = {**self.source, 'study_inputs_sha256': digest(frozen_dir/'frozen.json'), 'root_manifest_sha256': 'd'*64}
        timing = {'verified': True, 'authoritative_status': 'COMPLETED', 'source': source}
        result_path = self.root/'timing.json'; write(result_path, timing)
        proof_path = self.root/'proof.json'
        proof = {'complete': True, 'launcher_code_hashes': launcher.dependencies(), 'collector_code_hashes': m.dependencies(),
                 'test_code_sha256': digest(Path(__file__)), 'tests': 11, 'new_hf_jobs': 0, 'fresh_scientific_continuations': 0}
        write(proof_path, proof)
        with patch.object(launcher.calibration, 'RESULT', result_path), patch.object(launcher.calibration, 'collect', return_value=timing), \
             patch.object(launcher.builder, 'FROZEN', frozen_dir), patch.object(launcher, 'PROOF', proof_path), \
             patch.object(launcher.job, 'validate_inputs', return_value=({'root_manifest_sha256': 'd'*64}, self.manifest, {}, {})), \
             patch.object(launcher.job, 'policy_digest', return_value=source['surrogate_policy_sha256']):
            self.assertEqual(launcher.prerequisites()[0], source)
            proof['collector_code_hashes'][str(Path(m.__file__).relative_to(ROOT))] = 'f'*64
            write(proof_path, proof)
            with self.assertRaises(AssertionError): launcher.prerequisites()

    def test_dry_run_and_capacity_keep_same_original_jobs(self):
        self.assertFalse(launcher.launch_ready(False)['execute']); self.api.run_job.assert_not_called()
        self.assertFalse(launcher.GUARDS.exists())
        first = launcher.launch_ready(True); self.assertEqual(first['submitted'], 2)
        before = {p.name: digest(p) for p in launcher.GUARDS.glob('*.json')}
        self.assertEqual(launcher.launch_ready(True)['submitted'], 0)
        self.assertEqual(self.api.run_job.call_count, 2)
        self.assertEqual(before, {p.name: digest(p) for p in launcher.GUARDS.glob('*.json')})
        self.assertEqual(self.api.run_job.call_args.kwargs['env']['ROOT_ID'], self.rows[1]['root_id'])
        self.assertNotIn('fixture-secret', ''.join(p.read_text() for p in launcher.GUARDS.glob('*.json')))

    def test_unknown_submission_cannot_restart_or_advance(self):
        self.api.run_job.side_effect = TimeoutError('uncertain fixture-secret')
        with self.assertRaises(TimeoutError): launcher.launch_ready(True)
        path = next(launcher.GUARDS.glob('*.json')); before = digest(path)
        self.assertEqual(read(path)['stage'], 'launch_unknown'); self.assertNotIn('fixture-secret', path.read_text())
        with self.assertRaisesRegex(AssertionError, 'uncertain'): launcher.launch_ready(True)
        self.assertEqual(before, digest(path)); self.assertEqual(self.api.run_job.call_count, 1)

    def test_failed_or_unobservable_original_job_prevents_new_submissions(self):
        launcher.launch_ready(True); self.api.inspect_job.return_value.status.stage = 'ERROR'
        with self.assertRaisesRegex(AssertionError, 'original failed'): launcher.launch_ready(True)
        self.api.inspect_job.side_effect = TimeoutError('observation')
        with self.assertRaises(TimeoutError): launcher.launch_ready(True)
        self.assertEqual(self.api.run_job.call_count, 2)

    def test_failed_job_partial_archive_is_preserved_without_verification(self):
        launcher.launch_ready(True); self.api.inspect_job.return_value.status.stage = 'ERROR'
        row = self.rows[0]; folder = self.root/'partial'; folder.mkdir()
        state = {'case': row['case'], 'stage': 'failed'}
        write(folder/'job.json', state); write(folder/'partial.json', {'original': True})
        write(folder/'manifest.json', {p.name: digest(p) for p in folder.iterdir()})
        archive = self.root/'partial.tgz'
        with tarfile.open(archive, 'w:gz') as bundle:
            for p in folder.iterdir(): bundle.add(p, arcname=p.name)
        evidence = {'repo': 'coyotte508/powergrid-ai-germany-v1', 'archive_path': f'archives/{row["case"]}.tgz',
                    'remote_archive_verified': True, 'format': 'tar.gz', 'revision': 'b'*40,
                    'archive_sha256': digest(archive), 'manifest_sha256': digest(folder/'manifest.json'), 'archived_files': 3}
        self.api.fetch_job_logs.return_value = [repr({'status': state, 'evidence': evidence})]
        with patch.object(m, 'hf_hub_download', return_value=str(archive)):
            result = m.collect_row(row, self.source, self.manifest['roots'][0])
        self.assertFalse(result['verified']); self.assertTrue(result['partial_artifacts_preserved'])
        self.assertTrue((m.COLLECTED/row['case']/'artifacts/partial.json').exists())
        self.assertFalse((m.COLLECTED/row['case']/'verified.json').exists()); self.assertFalse(m.INDEX.exists())

    def install_synthetic_index(self, capped=False):
        launcher.GUARDS.mkdir()
        if capped:
            self.reports[0].update(complete=False, caps=1, margins=None)
            self.reports[0]['mode_credits']['reference_opponent_v1'][0][0] = None
        receipts = {}
        for i, (row, report) in enumerate(zip(self.rows, self.reports)):
            write(launcher.GUARDS/(row['case']+'.json'), {'fixture': True})
            out = m.COLLECTED/row['case']; (out/'artifacts').mkdir(parents=True)
            write(out/'artifacts/paired.json', report)
            receipt = {'case': row['case'], 'job_id': f'{i:024x}',
                       'review': {'caps': report['caps'], 'paired_sha256': digest(out/'artifacts/paired.json')}}
            write(out/'verified.json', receipt); receipts[row['root_id']] = receipt
        p = patch.object(m, 'verified', side_effect=lambda row, source, root: receipts[row['root_id']])
        p.start(); self.addCleanup(p.stop)
        return receipts

    def test_full_index_calls_real_analysis_with_all_480_records(self):
        self.install_synthetic_index(); result = m.index()
        self.assertTrue(result['complete']); self.assertEqual(result['continuations'], 23040)
        comparison = read(m.ANALYSIS)
        self.assertEqual(len(comparison['paired_records']), 480)
        self.assertEqual(comparison['primary']['represented_groups'], 60)
        self.assertEqual(result['comparison_sha256_canonical'], m.job.object_hash(comparison))
        self.assertFalse(result['qualification_eligible'])

    def test_capped_index_retains_all_roots_and_suppresses_aggregate(self):
        self.install_synthetic_index(capped=True); result = m.index()
        self.assertFalse(result['complete']); self.assertTrue(result['all_jobs_verified']); self.assertEqual(result['caps'], 1)
        comparison = read(m.ANALYSIS)
        self.assertIsNone(comparison['primary']); self.assertIsNone(comparison['whole_deal_uncertainty'])
        self.assertEqual(len(comparison['paired_records']), 480)

    def test_missing_original_job_or_receipt_prevents_index_output(self):
        receipts = self.install_synthetic_index(); row = self.rows[-1]; path = launcher.GUARDS/(row['case']+'.json'); path.unlink()
        with self.assertRaisesRegex(AssertionError, 'every original planned'): m.index()
        write(path, {'fixture': True}); receipts[row['root_id']] = None
        with self.assertRaisesRegex(AssertionError, 'every original paired root'): m.index()
        self.assertFalse(m.INDEX.exists()); self.assertFalse(m.ANALYSIS.exists())


if __name__ == '__main__': unittest.main()
