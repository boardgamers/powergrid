"""Isolated source imports, measured admission and nonduplicating launch boundaries."""
import copy
import importlib.util
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from strategic_collection import ROOT, read, write, digest


def load(name):
    spec = importlib.util.spec_from_file_location(name.replace('-', '_'), Path(__file__).with_name(name+'.py'))
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module


package = load('package-opponent-surrogate-training-v1')
launcher = load('launch-opponent-surrogate-training-v1')
benchmark = load('benchmark-opponent-surrogate-training-v1')


class PackagingTests(unittest.TestCase):
    def test_isolated_package_imports_every_runtime_entry_and_detects_corruption(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)/'source'; check = package.package(root, True)
            self.assertTrue(check['source_valid']); self.assertEqual(len(check['files']), 14)
            file = root/'ai/strong/model_opponent_surrogate_v1.py'
            file.write_text(file.read_text()+'\n# changed\n')
            result = subprocess.run([sys.executable, '-B', 'ai/strong/opponent_surrogate_hf_v1.py', 'check-source'],
                                    cwd=root, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)

    def test_incomplete_collection_prevents_archive_and_network_calls(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(package, 'INDEX', Path(temp)/'absent.json'), \
             patch.object(package, 'upload_evidence') as upload, patch.object(package, 'HfApi') as api:
            with self.assertRaisesRegex(AssertionError, 'Complete fresh collection'):
                package.archive_data()
            upload.assert_not_called(); api.assert_not_called()


class RuntimeAdmissionTests(unittest.TestCase):
    def test_measured_timeout_includes_all_fixed_seeds_epochs_and_exports(self):
        design = read(launcher.DESIGN)
        report = {'stage': 'complete', 'runtime_calibration_only': True, 'warmup_updates': 16, 'measured_updates': 128,
                  'exact_export_positions': 12000, 'recovery_seconds': 20., 'peak_host_rss_bytes': 4_000_000_000,
                  'peak_gpu_allocated_bytes': 3_000_000_000, 'gpu_total_bytes': 24_000_000_000,
                  'mean_update_seconds': .02, 'train_nonforced_rows': 10000, 'initialization_seconds': 1.,
                  'export_seconds': 100., 'evaluation_seconds': {'train': 2., 'validation': 1.}}
        report['full_four_seed_estimated_seconds'] = 4*(1 + math.ceil(10000/2048)*80*.02 + 81 + 4 + 100)
        pin = {'split_rows': {'train': 10000, 'validation': 2000}}
        self.assertEqual(launcher.measured_timeout(report, pin)['timeout_hours'], 1)
        for field, value in [('peak_host_rss_bytes', 14_000_000_000), ('peak_gpu_allocated_bytes', 23_000_000_000),
                             ('exact_export_positions', 11999), ('full_four_seed_estimated_seconds', 1.)]:
            bad = copy.deepcopy(report); bad[field] = value
            with self.assertRaises(AssertionError): launcher.measured_timeout(bad, pin)

    def test_unprepared_source_refuses_before_hf_calls(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(launcher, 'SOURCE', Path(temp)/'absent.json'), \
             patch.object(launcher, 'HfApi') as api:
            with self.assertRaisesRegex(AssertionError, 'must be packaged'):
                launcher.launch('calibration', True)
            api.assert_not_called()

    def test_full_training_requires_completed_gpu_calibration_before_any_submission(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(launcher, 'CALIBRATION', Path(temp)/'missing'), \
             patch.object(launcher, 'prerequisites', return_value=({}, {'unpacked_bytes': 1000}, {})), \
             patch.object(launcher, 'HfApi') as api, patch.object(launcher, 'get_token') as token:
            with self.assertRaisesRegex(AssertionError, 'original HF GPU calibration'):
                launcher.launch('full', True)
            api.assert_not_called(); token.assert_not_called()

    def test_existing_job_reused_and_uncertain_submission_never_retried(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); guards = root/'guards'; guards.mkdir()
            source = root/'source.json'; write(source, {'verified': True})
            pin = {'unpacked_bytes': 1_000_000}
            hardware = SimpleNamespace(name='l4x1', cpu='8 vCPU', ram='30 GB', ephemeral_storage='400 GB',
                                       accelerator=SimpleNamespace(model='L4', vram='24 GB'))
            original = {'stage': 'launched', 'source_sha256': digest(source), 'job_id': 'original-handle'}
            write(guards/'calibration.json', original)
            with patch.object(launcher, 'SOURCE', source), patch.object(launcher, 'GUARDS', guards), \
                 patch.object(launcher, 'prerequisites', return_value=({}, pin, {})), \
                 patch.object(launcher, 'get_token', return_value='test-only-placeholder'), patch.object(launcher, 'HfApi') as api:
                api.return_value.list_jobs_hardware.return_value = [hardware]
                api.return_value.inspect_job.return_value = SimpleNamespace(status=SimpleNamespace(stage='RUNNING'))
                value = launcher.launch('calibration', True)
                self.assertEqual(value['existing_job_id'], 'original-handle')
                api.return_value.run_job.assert_not_called()
                write(guards/'calibration.json', {**original, 'stage': 'launch_unknown'})
                with self.assertRaises(AssertionError): launcher.launch('calibration', True)
                api.return_value.run_job.assert_not_called()

    def test_calibration_gradients_cannot_start_locally(self):
        with patch.dict(os.environ, {}, clear=True), patch.object(benchmark.torch.cuda, 'is_available') as cuda:
            with self.assertRaisesRegex(AssertionError, 'HF GPU calibration only'):
                benchmark.main({}, {}, Path('/must-not-create'), 0)
            cuda.assert_not_called()


if __name__ == '__main__': unittest.main()
