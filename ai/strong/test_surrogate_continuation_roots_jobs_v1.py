"""Remote-work boundaries: changed source, invalid scope and uncertain submissions."""
import importlib.util
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from strategic_collection import ROOT, write, digest


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT/'ai/strong'/filename)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module


job = load('root_job_test', 'surrogate-continuation-roots-job-v1.py')
launcher = load('root_launch_test', 'launch-surrogate-continuation-roots-runtime-v1.py')


class BoundaryTests(unittest.TestCase):
    def test_invalid_scope_never_downloads_or_uploads(self):
        with patch.object(job, 'hf_hub_download') as download, patch.object(job, 'upload_evidence') as upload:
            for args in [(3, 0, 1, 'runtime'), (2, 1, 2, 'runtime'), (6, 0, 3, 'root'), (6, 0, 1, 'unknown')]:
                with self.assertRaises(AssertionError): job.main(*args)
            download.assert_not_called(); upload.assert_not_called()

    def test_changed_source_rejected_before_output_or_network(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); (root/'changed.txt').write_text('changed')
            manifest = root/'surrogate-continuation-roots-source-manifest.json'
            write(manifest, {'changed.txt': '0'*64})
            env = {'PROTOCOL_SHA256': digest(job.PROTOCOL), 'SOURCE_MANIFEST_SHA256': digest(manifest)}
            with patch.object(job, 'ROOT', root), patch.dict(job.os.environ, env), patch.object(job, 'hf_hub_download') as download:
                with self.assertRaises(AssertionError): job.main(2, 0, 1, 'runtime')
                download.assert_not_called(); self.assertFalse((root/'ai/runs').exists())

    def exercise_guard(self, fail):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); replacements = {key: root/(key+'.json') for key in ['SOURCE', 'PROTOCOL', 'PREFLIGHT', 'LAYOUT', 'PLAN']}
            replacements['GUARDS'] = root/'guards'
            for key in ['SOURCE', 'PROTOCOL', 'PREFLIGHT', 'LAYOUT']: write(replacements[key], {'fixture': key})
            plan = {'players': [2, 6], 'jobs': 2, 'max_concurrent': 2, 'collection_admitted': False,
                    'flavor': 'cpu-upgrade', 'timeout_hours': 4,
                    'source_descriptor_sha256': digest(replacements['SOURCE']), 'protocol_sha256': digest(replacements['PROTOCOL']),
                    'preflight_sha256': digest(replacements['PREFLIGHT']), 'layout_check_sha256': digest(replacements['LAYOUT']),
                    'launcher_sha256': digest(launcher.__file__), 'bootstrap_source_sha256': digest(launcher.old.__file__),
                    'bootstrap_sha256': launcher.hashlib.sha256(launcher.BOOTSTRAP.encode()).hexdigest()}
            write(replacements['PLAN'], plan)
            source = {'archive': 'fixture.tgz', 'revision': 'fixture-revision', 'sha256': '1'*64,
                      'manifest_sha256': '2'*64, 'manifest_files': 1469}
            calls = []

            class Api:
                def run_job(self, **kwargs):
                    calls.append(kwargs)
                    if fail: raise TimeoutError('simulated submission observation timeout')
                    return SimpleNamespace(id='original-fixture-job')

                def inspect_job(self, job_id):
                    assert job_id == 'original-fixture-job'
                    return SimpleNamespace(status=SimpleNamespace(stage='RUNNING'))

            with patch.multiple(launcher, **replacements), patch.object(launcher, 'prerequisites', return_value=(source, {}, {})), \
                    patch.object(launcher, 'HfApi', Api), patch.object(launcher, 'get_token', return_value='fixture-secret'):
                if fail:
                    with self.assertRaises(TimeoutError): launcher.launch(2, True)
                    record = json.loads((root/'guards/surrogate-continuation-runtime-v1-2p-0-1.json').read_text())
                    self.assertEqual(record['stage'], 'launch_unknown')
                    with self.assertRaises(AssertionError): launcher.launch(2, True)
                else:
                    launcher.launch(2, True); launcher.launch(2, True)
                self.assertEqual(len(calls), 1)
                self.assertNotIn('HF_TOKEN', calls[0]['env'])
                self.assertEqual(calls[0]['secrets'], {'HF_TOKEN': 'fixture-secret'})

    def test_existing_live_handle_is_reused(self): self.exercise_guard(False)

    def test_observation_timeout_is_not_resubmitted(self): self.exercise_guard(True)


if __name__ == '__main__': unittest.main()
