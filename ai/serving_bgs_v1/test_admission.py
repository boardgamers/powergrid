"""Offline tests only: never instantiate a real HF client or submit a job."""
import contextlib
from dataclasses import dataclass
from datetime import datetime, timezone
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('admission_launcher', Path(__file__).with_name('launch_admission.py'))
launcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launcher)


@dataclass
class Owner:
    name: str = 'fake-owner'


@dataclass
class Job:
    id: str
    owner: Owner
    created_at: datetime


class AdmissionTests(unittest.TestCase):
    def run_launcher(self, ledger, api, submit=True):
        args = ['launch_admission.py', '--submit'] if submit else ['launch_admission.py']
        source = ledger.parent / 'ai/serving_bgs_v1/admission.cjs'
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_bytes((launcher.ROOT / 'ai/serving_bgs_v1/admission.cjs').read_bytes())
        with patch.object(launcher, 'ROOT', ledger.parent), patch.object(launcher, 'LEDGER', ledger), patch.object(sys, 'argv', args), \
                patch.dict(sys.modules, {'huggingface_hub': SimpleNamespace(HfApi=lambda: api)}), \
                contextlib.redirect_stdout(io.StringIO()) as output:
            launcher.main()
        return output.getvalue()

    def test_dry_run_does_not_create_ledger_or_client(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp) / 'new'
            report = json.loads(self.run_launcher(ledger, None, False))
            self.assertFalse(ledger.exists())
            self.assertEqual(report['timeoutSeconds'], 600)
            self.assertTrue(report['noModels'] and report['noSecrets'] and report['noPorts'])

    def test_success_records_intent_before_api_and_id_before_full_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp) / 'new'
            def run_job(**spec):
                self.assertTrue((ledger / 'intent.json').is_file())
                self.assertFalse((ledger / 'receipt.json').exists())
                self.assertEqual(spec['timeout'], 600)
                self.assertEqual(spec['flavor'], 'cpu-basic')
                self.assertIsNone(spec['expose'])
                self.assertFalse(spec['ssh'])
                self.assertFalse(set(spec) & {'env', 'secrets', 'volumes'})
                self.assertEqual(spec['command'][:2], ['node', '-e'])
                return Job('fake-id', Owner(), datetime(2026, 11, 10, tzinfo=timezone.utc))
            self.run_launcher(ledger, SimpleNamespace(run_job=run_job))
            self.assertEqual(json.loads((ledger/'submitted-id.json').read_text())['jobId'], 'fake-id')
            self.assertEqual(json.loads((ledger/'receipt.json').read_text())['created_at'], '2026-11-10T00:00:00+00:00')
            with self.assertRaises(FileExistsError):
                self.run_launcher(ledger, None)

    def test_unknown_submission_consumes_slot_and_never_retries(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp) / 'new'
            calls = []
            def ambiguous(**spec):
                calls.append(1)
                raise RuntimeError('unknown outcome')
            with self.assertRaisesRegex(RuntimeError, 'unknown outcome'):
                self.run_launcher(ledger, SimpleNamespace(run_job=ambiguous))
            with self.assertRaises(FileExistsError):
                self.run_launcher(ledger, SimpleNamespace(run_job=ambiguous))
            self.assertEqual(len(calls), 1)
            self.assertTrue((ledger/'intent.json').exists())
            self.assertFalse((ledger/'submitted-id.json').exists())

    def test_exclusive_write_keeps_prior_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp) / 'record'
            launcher.exclusive(file, {'original': True})
            before = file.read_bytes()
            with self.assertRaises(FileExistsError):
                launcher.exclusive(file, {'original': False})
            self.assertEqual(file.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
