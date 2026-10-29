from copy import deepcopy
import fcntl
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import subprocess
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import selected_public_policy_final_dispatch_v1 as dispatch
import selected_public_policy_final_source_v1 as source


class FinalDispatchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)/'ledger'; self.bootstrap = 'echo synthetic transport test only'
        identity = {'policySha256': '1'*64, 'runtimeManifestSha256': '2'*64, 'modelSha256': '3'*64,
            'featureRevision': '4.3-strategic-correction', 'backend': 'opponent-auction-v1', 'opponentPolicySha256': '4'*64,
            'settings': {'arm': 'auction', 'samples': 8, 'workers': 4, 'threads': 1, 'max_steps': 2400,
                'population_modes': ['neural_population'], 'minimum_advantage': '1/8'}}
        candidate = {'status': 'selected', 'frozen_at': '2026-10-29T01:00:00+00:00', 'identity': identity,
            'protocol_sha256': source.PROTOCOL_SHA, 'selection_evidence': {'repo': 'coyotte508/powergrid-ai-germany-v1',
                'revision': '5'*40, 'archive_path': 'archives/synthetic-dispatch-test.tgz', 'archive_sha256': '6'*64}}
        data = json.dumps(candidate).encode(); workers = {s['name']: 4 for s in source.schedule()}
        _, rows = source.controls(data, identity, 'policies/conservative_population.json', workers, '2026-10-29T02:00:00+00:00')
        candidate_sha = hashlib.sha256(data).hexdigest()
        self.release = {'version': 1, 'admission_sha256': '7'*64,
            'source': {'repo': 'coyotte508/powergrid-ai-training-v1', 'revision': '8'*40,
                'archive': 'synthetic-final-source.tgz', 'sha256': '9'*64, 'source_manifest_sha256': 'a'*64},
            'plan': {'version': 1, 'candidate_sha256': candidate_sha, 'identity': identity,
                'protocol_sha256': source.PROTOCOL_SHA, 'run_fingerprint': dispatch.fingerprint(candidate_sha, identity),
                'rows': rows, 'jobs': 320, 'games': 20160},
            'allocation': {r['name']: {'flavor': 'cpu-upgrade', 'timeout': '5h'} for r in rows},
            'bootstrap_sha256': hashlib.sha256(self.bootstrap.encode()).hexdigest()}
        self.name, self.other = rows[0]['name'], rows[1]['name']
        self.api = Mock(); self.api.run_job.return_value = SimpleNamespace(id='b'*24)

    def launch(self, *, release=None, name=None):
        return dispatch.dispatch_once(self.api, self.root, self.release if release is None else release,
            name or self.name, 'synthetic-private-test-token', self.bootstrap)

    def test_exact_transport_and_durable_intent_precede_api(self):
        actual_sync = dispatch.os.fsync
        with patch.object(dispatch.os, 'fsync', wraps=actual_sync) as synced:
            def submit(**kw):
                self.assertGreaterEqual(synced.call_count, 4)
                receipt = dispatch.read(self.root/'jobs'/(self.name+'.json'))
                self.assertEqual(receipt['stage'], 'launch_intent')
                self.assertEqual(kw['command'], ['bash', '-lc', self.bootstrap])
                self.assertEqual(kw['env']['FINAL_JOB'], self.release['plan']['rows'][0]['job'])
                self.assertEqual(kw['env']['SOURCE_REVISION'], '8'*40)
                self.assertEqual(kw['secrets'], {'HF_TOKEN': 'synthetic-private-test-token'})
                return SimpleNamespace(id='b'*24)
            self.api.run_job.side_effect = submit
            first = self.launch()
        self.assertEqual(first, self.launch()); self.assertEqual(self.api.run_job.call_count, 1)
        self.assertFalse(list((self.root/'jobs').glob('*.pending')))

    def test_ambiguous_submission_blocks_same_and_other_shards(self):
        self.api.run_job.side_effect = TimeoutError('synthetic-private-test-token')
        with self.assertRaises(dispatch.SubmissionUncertain) as caught:
            self.launch()
        self.assertNotIn('synthetic-private-test-token', str(caught.exception))
        for name in (self.name, self.other):
            with self.assertRaisesRegex(ValueError, 'Unresolved original'):
                self.launch(name=name)
        self.assertEqual(self.api.run_job.call_count, 1)
        receipt = (self.root/'jobs'/(self.name+'.json')).read_text()
        self.assertNotIn('synthetic-private-test-token', receipt)
        self.assertEqual(json.loads(receipt)['stage'], 'launch_unknown')

    def test_invalid_return_handle_is_preserved_as_unknown(self):
        self.api.run_job.return_value = SimpleNamespace(id='not-a-job')
        with self.assertRaises(dispatch.SubmissionUncertain): self.launch()
        with self.assertRaisesRegex(ValueError, 'Unresolved original'): self.launch()
        self.assertEqual(self.api.run_job.call_count, 1)

    def test_crash_after_remote_creation_cannot_resubmit(self):
        original_write = dispatch.durable_write
        def fail_receipt(path, value, **kw):
            if value.get('stage') == 'launched': raise OSError('simulated disk failure')
            return original_write(path, value, **kw)
        with patch.object(dispatch, 'durable_write', side_effect=fail_receipt):
            with self.assertRaises(OSError): self.launch()
        self.assertEqual(dispatch.read(self.root/'jobs'/(self.name+'.json'))['stage'], 'launch_intent')
        with self.assertRaisesRegex(ValueError, 'Unresolved original'): self.launch()
        self.assertEqual(self.api.run_job.call_count, 1)

    def test_partial_receipt_blocks_dispatch(self):
        self.launch(); (self.root/'jobs'/(self.name+'.json.pending')).write_text('{')
        with self.assertRaisesRegex(ValueError, 'Unfinished receipt'): self.launch(name=self.other)
        self.assertEqual(self.api.run_job.call_count, 1)

    def test_new_release_cannot_reuse_reserved_namespace(self):
        self.launch(); changed = deepcopy(self.release); changed['source']['sha256'] = 'c'*64
        with self.assertRaisesRegex(ValueError, 'another release'): self.launch(release=changed)
        self.assertEqual(self.api.run_job.call_count, 1)

    def test_competing_owner_is_rejected(self):
        self.root.mkdir()
        with (self.root/'.dispatch.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaises(BlockingIOError): self.launch()
        self.api.run_job.assert_not_called()

    def test_unknown_shard_missing_schedule_or_changed_bootstrap_never_submits(self):
        with self.assertRaisesRegex(ValueError, 'Unknown final shard'): self.launch(name='unexpected')
        altered = deepcopy(self.release); altered['plan']['rows'].pop()
        with self.assertRaises(ValueError): self.launch(release=altered)
        altered = deepcopy(self.release); altered['bootstrap_sha256'] = 'c'*64
        with self.assertRaisesRegex(ValueError, 'Bootstrap changed'): self.launch(release=altered)
        self.api.run_job.assert_not_called(); self.assertFalse(self.root.exists())

    def test_changed_search_identity_cannot_reuse_candidate_fingerprint(self):
        altered = deepcopy(self.release); altered['plan']['identity']['settings']['workers'] = 8
        with self.assertRaisesRegex(ValueError, 'Candidate fingerprint'): self.launch(release=altered)
        self.api.run_job.assert_not_called()

    def test_corrupt_original_receipt_is_not_overwritten(self):
        self.launch(); p = self.root/'jobs'/(self.name+'.json'); p.write_text('{')
        with self.assertRaises(json.JSONDecodeError): self.launch()
        self.assertEqual(p.read_text(), '{'); self.assertEqual(self.api.run_job.call_count, 1)

    def test_thirteen_and_twenty_four_hour_allocations_are_forwarded_exactly(self):
        for timeout in ('13h', '24h'):
            release = deepcopy(self.release)
            release['allocation'][self.name]['timeout'] = timeout
            dispatch.dispatch_once(self.api, self.root/timeout, release, self.name,
                                   'synthetic-private-test-token', self.bootstrap)
            self.assertEqual(self.api.run_job.call_args.kwargs['timeout'], timeout)
        self.assertEqual(self.api.run_job.call_count, 2)

    def test_invalid_or_over_day_timeouts_never_submit(self):
        for timeout in ('0h', '25h', '13.5h', '24hh', '1d', '999h'):
            release = deepcopy(self.release)
            release['allocation'][self.name]['timeout'] = timeout
            with self.subTest(timeout=timeout), self.assertRaisesRegex(ValueError, 'Invalid timeout'):
                self.launch(release=release)
        self.api.run_job.assert_not_called()


class BootstrapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        p = Path(__file__).with_name('manage-current-auction-runtime-v1.py')
        spec = importlib.util.spec_from_file_location('unchanged_bootstrap_reference', p)
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        cls.reference = module.BOOTSTRAP

    def test_exact_exercised_setup_and_final_entry(self):
        value = dispatch.final_bootstrap(self.reference)
        setup = value.split('python -u -B /workspace/source/public_policy_selected_final_job_v1.py')[0]
        self.assertEqual(hashlib.sha256(setup.encode()).hexdigest(), dispatch.SETUP_SHA256)
        self.assertNotIn('public_policy_measured_job_v1.py', value)
        self.assertNotIn('PILOT_JOB', value)
        self.assertIn('--job "$FINAL_JOB"', value)
        self.assertIn('--execute --upload', value)
        subprocess.run(['bash', '-n'], input=value, text=True, check=True, capture_output=True)

    def test_modified_setup_or_ambiguous_entry_rejected(self):
        for changed in (self.reference.replace('numpy==2.4.6', 'numpy'), self.reference+self.reference,
                        self.reference.replace('public_policy_measured_job_v1.py', 'unexpected.py')):
            with self.assertRaises(ValueError): dispatch.final_bootstrap(changed)


if __name__ == '__main__': unittest.main()
