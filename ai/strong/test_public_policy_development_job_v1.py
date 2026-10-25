"""Admission/failure tests; actual artifact execution is checked separately."""
import argparse
import copy
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import public_policy_development_job_v1 as job


class DevelopmentJobTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)/'source'; self.root.mkdir()
        self.artifact = self.root/'artifact'; (self.artifact/'ai/strong').mkdir(parents=True)
        (self.root/job.ENTRY).write_text('# pinned wrapper test bytes\n')
        (self.artifact/'ai/strong/public_policy_final_runner_v1.py').write_text('# dry admission test\n')
        job.write(self.artifact/'policy.json', {})
        self.candidate = {'status': 'engineering', 'selection_evidence': None, 'identity': {'test': True}}
        job.write(self.root/'candidate.json', self.candidate)
        self.contract = {'purpose': 'engineering', 'launch_authorization': None, 'identity': {'test': True},
                         'candidate_sha256': job.digest(self.root/'candidate.json'),
                         'shard': {'name': 'test', 'start': 4, 'games': 8}}
        job.write(self.root/'contract.json', self.contract)
        self.spec = {'version': 1, 'artifact': 'artifact', 'descriptor': 'policy.json', 'workers': 4,
                     'candidate': 'candidate.json', 'contract': 'contract.json', 'opponent_model': None}
        job.write(self.root/'job.json', self.spec)
        self.args = argparse.Namespace(source=self.root, job='job.json', output=Path(self.tmp.name)/'output',
            manifest_sha256='', source_revision=None, source_archive_sha256=None, execute=False, upload=False)
        self.pin()
        self.file_patch = patch.object(job, '__file__', str(self.root/job.ENTRY)); self.file_patch.start()
        self.addCleanup(self.file_patch.stop)

    def pin(self):
        job.write(self.root/job.MANIFEST, {str(p.relative_to(self.root)): job.digest(p)
            for p in self.root.rglob('*') if p.is_file() and p.name != job.MANIFEST})
        self.args.manifest_sha256 = job.digest(self.root/job.MANIFEST)

    def test_default_only_runs_frozen_admission(self):
        with patch.object(job.subprocess, 'run') as launch:
            job.run(self.args)
        self.assertEqual(launch.call_count, 1)
        command = launch.call_args.args[0]
        self.assertNotIn('--execute', command)
        self.assertEqual(command[command.index('--artifact')+1], str(self.artifact))
        self.assertEqual(command[command.index('--contract')+1], str(self.root/'contract.json'))
        self.assertFalse(self.args.output.exists())

    def test_changed_bytes_extra_files_and_bad_manifest_rejected(self):
        (self.artifact/'policy.json').write_text('changed')
        with self.assertRaisesRegex(ValueError, 'bytes changed'): job.configuration(self.args)
        self.pin(); (self.root/'extra.py').write_text('unmanifested')
        with self.assertRaisesRegex(ValueError, 'file set changed'): job.configuration(self.args)
        self.pin(); self.args.manifest_sha256 = 'a'*64
        with self.assertRaisesRegex(ValueError, 'manifest changed'): job.configuration(self.args)

    def test_symlink_and_escaping_path_rejected(self):
        external = Path(self.tmp.name)/'external.json'; job.write(external, self.candidate)
        (self.root/'candidate.json').unlink(); (self.root/'candidate.json').symlink_to(external)
        self.pin()
        with self.assertRaisesRegex(ValueError, 'escapes|Symlink'): job.configuration(self.args)
        (self.root/'candidate.json').unlink(); job.write(self.root/'candidate.json', self.candidate)
        self.spec['candidate'] = '../external.json'; job.write(self.root/'job.json', self.spec); self.pin()
        with self.assertRaisesRegex(ValueError, 'Noncanonical'): job.configuration(self.args)

    def test_final_purpose_rejected_before_runner(self):
        self.contract['purpose'] = 'final'; job.write(self.root/'contract.json', self.contract); self.pin()
        with patch.object(job.subprocess, 'run') as launch:
            with self.assertRaisesRegex(ValueError, 'development execution only'): job.run(self.args)
        launch.assert_not_called(); self.assertFalse(self.args.output.exists())

    def test_output_cannot_modify_frozen_source(self):
        for path in (self.root/'runs', self.root, self.root.parent):
            self.args.output = path
            with self.assertRaisesRegex(ValueError, 'outside the frozen source'): job.configuration(self.args)

    def test_changed_candidate_contract_rejected(self):
        self.candidate['identity'] = {'test': False}; job.write(self.root/'candidate.json', self.candidate); self.pin()
        with self.assertRaisesRegex(ValueError, 'Candidate bytes changed'): job.configuration(self.args)
        self.contract['candidate_sha256'] = job.digest(self.root/'candidate.json')
        job.write(self.root/'contract.json', self.contract); self.pin()
        with self.assertRaisesRegex(ValueError, 'identity mismatch'): job.configuration(self.args)

    def test_failed_execution_keeps_receipts_and_cannot_restart(self):
        self.args.execute = True
        with patch.object(job.subprocess, 'run', side_effect=[None, subprocess.CalledProcessError(2, ['original'])]):
            with self.assertRaises(subprocess.CalledProcessError): job.run(self.args)
        status = job.read(self.args.output/'job-status.json')
        self.assertEqual(status['stage'], 'failed'); self.assertFalse(status['automatic_retries'])
        pins = job.read(self.args.output/'manifest.json')
        self.assertTrue(all(job.digest(self.args.output/name) == sha for name, sha in pins.items()))
        before = {p.name: job.digest(p) for p in self.args.output.iterdir()}
        with patch.object(job.subprocess, 'run') as launch:
            with self.assertRaises(FileExistsError): job.run(self.args)
        self.assertEqual(launch.call_count, 1)
        self.assertNotIn('--execute', launch.call_args.args[0])
        self.assertEqual(before, {p.name: job.digest(p) for p in self.args.output.iterdir()})

    def test_upload_requires_pinned_source_and_explicit_execution(self):
        self.args.upload = True
        with self.assertRaisesRegex(ValueError, 'source revision'): job.configuration(self.args)
        self.args.source_revision = 'a'*40; self.args.source_archive_sha256 = 'b'*64
        with self.assertRaisesRegex(ValueError, 'Validation-only'): job.configuration(self.args)
        self.args.execute = True
        self.assertEqual(job.configuration(self.args)[4]['source_revision'], 'a'*40)


if __name__ == '__main__':
    unittest.main()
