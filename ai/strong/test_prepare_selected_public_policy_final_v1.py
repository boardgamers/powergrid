"""Synthetic control/transport tests only: no games, models or real API calls."""
from contextlib import ExitStack
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import policy_iteration_evidence_archive as archive_helper
import prepare_selected_public_policy_final_v1 as prep
import selected_public_policy_final_source_v1 as builder
from public_policy_final_contract_v1 import fingerprint


class ResourceTests(unittest.TestCase):
    def setUp(self):
        self.source = prep.read(prep.ROOT/prep.selection.SOURCE)
        rows = [r for r in self.source['rows'] if r['arm'] == prep.selection.ARM]
        self.comparison = {'complete': True, 'games': 26880, 'provenance': {},
                           'costs': {prep.selection.ARM: {'per_job': []}}}
        for i, row in enumerate(rows):
            job_id = f'{i:024x}'
            self.comparison['provenance'][row['name']] = {'job_id': job_id}
            self.comparison['costs'][prep.selection.ARM]['per_job'].append({
                'name': row['name'], 'job_id': job_id, 'games': row['shard']['games'],
                'seconds': row['shard']['games']*10, 'sampled_peak_total_rss_bytes': 1024**3})

    def test_all_selected_jobs_size_unchanged_final_schedule(self):
        result = prep.resources(self.comparison, self.source)
        self.assertEqual(len(result['workers']), 320)
        self.assertEqual(set(result['workers'].values()), {4})
        six = next(s for s in prep.schedule() if s['players'] == 6)
        self.assertEqual(result['allocation'][six['name']]['timeout'], '13h')
        row = next(r for r in self.source['rows'] if r['arm'] == prep.selection.ARM and r['players'] == 6)
        measurement = next(m for m in self.comparison['costs'][prep.selection.ARM]['per_job'] if m['name'] == row['name'])
        measurement['seconds'] = measurement['games']*200
        result = prep.resources(self.comparison, self.source)
        self.assertEqual(result['allocation'][six['name']]['timeout'], '15h')
        self.assertEqual(sum(s['games'] for s in prep.schedule()), 20160)

    def test_missing_duplicate_or_wrong_original_costs_rejected(self):
        original = deepcopy(self.comparison)
        mutations = [lambda c: c.update(complete=False),
            lambda c: c['costs'][prep.selection.ARM]['per_job'].pop(),
            lambda c: c['costs'][prep.selection.ARM]['per_job'].__setitem__(0, c['costs'][prep.selection.ARM]['per_job'][1]),
            lambda c: c['costs'][prep.selection.ARM]['per_job'][0].update(job_id='f'*24),
            lambda c: c['costs'][prep.selection.ARM]['per_job'][0].update(games=1),
            lambda c: c['costs'][prep.selection.ARM]['per_job'][0].update(seconds=float('nan'))]
        for change in mutations:
            value = deepcopy(original); change(value)
            with self.subTest(change=mutations.index(change)), self.assertRaises(ValueError):
                prep.resources(value, self.source)

    def test_unmeasured_concurrency_memory_and_excessive_duration_rejected(self):
        for field, value in (('workers', 8), ('sampled_peak_rss_bytes', 16*1024**3),
                             ('per_game_seconds', {prep.selection.ARM: 1000})):
            source = deepcopy(self.source); source['sizing'][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                prep.resources(self.comparison, source)


class EarlyGateTests(unittest.TestCase):
    def test_incomplete_study_rejected_before_output_or_network(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(prep, 'OUT', Path(temp)/'never-created'), \
             patch.object(prep.selection, 'read', return_value={'stage': 'waiting_for_original_confirmation_jobs'}) as reader, \
             patch.object(prep, 'HfApi') as api:
            with self.assertRaisesRegex(ValueError, 'Wait for all original'):
                prep.prepare(Path(temp)/'absent-review.json')
            self.assertFalse(prep.OUT.exists()); api.assert_not_called()
            self.assertEqual(reader.call_count, 1)


class PreparationTests(unittest.TestCase):
    """Use real controls, manifests, tar archive and release verification.

    The substantive positive selection and artifact identity are synthetic;
    all HF traffic goes to an isolated local fake. No actual candidate exists.
    """
    def setUp(self):
        self.stack = ExitStack(); self.addCleanup(self.stack.close)
        self.root = Path(self.stack.enter_context(tempfile.TemporaryDirectory()))
        self.out = self.root/'prepared'; self.remote = self.root/'fake-remote'; self.remote.mkdir()
        self.remote_files = {}; self.uploads = []; self.private = True; self.existing = False
        self.fail_source_upload = False; self.bad_source_download = False
        self.identity = {'policySha256': '1'*64, 'runtimeManifestSha256': '2'*64,
            'modelSha256': '3'*64, 'featureRevision': '4.3-strategic-correction',
            'backend': 'opponent-auction-v1', 'opponentPolicySha256': '4'*64,
            'settings': {'arm': 'auction', 'samples': 8, 'workers': 4, 'threads': 1, 'max_steps': 2400,
                         'population_modes': ['neural_population'], 'minimum_advantage': '1/8'}}
        (self.root/'pin').write_text('synthetic frozen input')
        self.ready = {'checked_at': 'synthetic', 'selection': {'selected_identity': self.identity},
            'review_path': 'review.json', 'input_hashes': {'pin': prep.digest(self.root/'pin')},
            'resources': {'workers': {s['name']: 4 for s in prep.schedule()},
                          'allocation': {s['name']: {'flavor': 'cpu-upgrade', 'timeout': '13h'} for s in prep.schedule()}},
            'qualified': False, 'reserved_final_seeds_used': False}
        for name in ('review.json', prep.selection.COMPARISON, prep.selection.SOURCE, prep.selection.TECHNICAL,
                     prep.selection.BINDING, prep.selection.EXPORT, prep.selection.EXPORT_AUDIT,
                     'ai/strong/current-full-serving-results-evidence-v1.json',
                     'ai/strong/current-engine-export-evidence-v1.json'):
            p = self.root/name; p.parent.mkdir(parents=True, exist_ok=True); p.write_text('{"synthetic":true}')
        (self.root/'ai/strong'/builder.ENTRY).write_text('# synthetic, never executed\n')
        bootstrap = prep.bootstrap_text()  # Read the real frozen setup; no process or job execution.
        self.api = SimpleNamespace(model_info=lambda *a: SimpleNamespace(private=self.private),
            dataset_info=lambda *a: SimpleNamespace(private=self.private), file_exists=lambda *a, **k: self.existing,
            upload_file=self.upload)
        for target, name, value in ((prep, 'ROOT', self.root), (prep, 'OUT', self.out),
            (prep, 'readiness', lambda p: deepcopy(self.ready)), (prep, 'HfApi', lambda: self.api),
            (prep, 'hf_hub_download', self.download), (prep, 'bootstrap_text', lambda: bootstrap),
            (archive_helper, 'HfApi', lambda: self.api), (archive_helper, 'hf_hub_download', self.download),
            (prep.selection, 'artifact_identity', lambda *a: self.identity), (builder, 'build', self.build)):
            self.stack.enter_context(patch.object(target, name, value))

    def upload(self, **args):
        name = args['path_in_repo']; self.uploads.append(name)
        if self.fail_source_upload and name == prep.SOURCE_NAME:
            raise TimeoutError('synthetic unknown upload outcome')
        path = self.remote/str(len(self.uploads)); shutil.copyfile(args['path_or_fileobj'], path)
        self.remote_files[name] = path
        return SimpleNamespace(oid=f'{len(self.uploads):040x}')

    def download(self, repo, name, **kwargs):
        if self.bad_source_download and name == prep.SOURCE_NAME:
            return self.root/'pin'
        return self.remote_files[name]

    def build(self, artifact, descriptor, candidate_path, workers, output):
        source = output/'source'; (source/'artifact').mkdir(parents=True)
        (source/'artifact/synthetic').write_text('no model, engine or execution')
        shutil.copyfile(candidate_path, source/'candidate.json')
        shutil.copyfile(self.root/'ai/strong'/builder.ENTRY, source/builder.ENTRY)
        files, rows = builder.controls(candidate_path.read_bytes(), self.identity, descriptor, workers, prep.now())
        (source/'controls').mkdir()
        for name, value in files.items(): builder.save(source/name, value)
        sha = prep.digest(candidate_path)
        plan = {'version': 1, 'candidate_sha256': sha, 'identity': self.identity, 'protocol_sha256': prep.PROTOCOL_SHA,
                'run_fingerprint': fingerprint(sha, self.identity), 'rows': rows, 'jobs': 320, 'games': 20160}
        builder.save(source/'final-plan.json', plan)
        builder.save(source/'source-manifest.json', builder.source_files(source))
        built = {'source_manifest_sha256': prep.digest(source/'source-manifest.json'),
                 'plan_sha256': prep.digest(source/'final-plan.json'), 'rows': rows,
                 'inputs': {'artifact_files': builder.source_files(source/'artifact'),
                            'entry_sha256': prep.digest(source/builder.ENTRY)},
                 'identity': self.identity, 'jobs': 320, 'games': 20160}
        builder.save(output/'prepared.json', built); return built

    def prepare(self): return prep.prepare(self.root/'review.json')

    def reseal_test_source(self):
        """Model a freshly hashed but semantically wrong builder output."""
        source = self.out/'bundle/source'; (source/'source-manifest.json').unlink()
        builder.save(source/'source-manifest.json', builder.source_files(source))
        built = prep.read(self.out/'bundle/prepared.json')
        built['source_manifest_sha256'] = prep.digest(source/'source-manifest.json')
        built['plan_sha256'] = prep.digest(source/'final-plan.json')
        built['rows'] = prep.read(source/'final-plan.json')['rows']
        prep.durable_write(self.out/'bundle/prepared.json', built)
        saved = prep.read(self.out/'prepared.json'); saved['source_manifest_sha256'] = built['source_manifest_sha256']
        saved['bundle_prepared_sha256'] = prep.digest(self.out/'bundle/prepared.json')
        prep.durable_write(self.out/'prepared.json', saved)

    def test_complete_mocked_flow_binds_original_schedule_and_uploaded_bytes(self):
        self.assertFalse(self.prepare()['source_published'])
        result = prep.publish(); release = prep.read(self.out/'release.json')
        self.assertEqual(result['jobs_submitted'], 0); self.assertFalse(result['qualified'])
        self.assertEqual(len(self.uploads), 2)
        self.assertEqual(release['plan']['games'], 20160)
        self.assertEqual(len(prep.validate_release(release, (self.out/'bootstrap.sh').read_text())), 320)
        self.assertEqual(release['source']['sha256'], prep.digest(self.remote_files[prep.SOURCE_NAME]))
        self.assertEqual(release['admission_sha256'], prep.digest(self.out/'admission.json'))
        with self.assertRaisesRegex(ValueError, 'never upload blindly'): prep.publish()
        self.assertEqual(len(self.uploads), 2)

    def test_nonprivate_or_existing_evidence_blocks_before_preparation(self):
        for private, exists in ((False, False), (True, True)):
            self.private, self.existing = private, exists
            with self.subTest(private=private), self.assertRaises(ValueError): self.prepare()
            self.assertFalse(self.out.exists()); self.assertFalse(self.uploads)

    def test_unknown_selection_upload_preserves_intent_and_prevents_retry(self):
        with patch.object(prep, 'upload_evidence', side_effect=TimeoutError('synthetic')) as upload:
            with self.assertRaises(TimeoutError): self.prepare()
            with self.assertRaisesRegex(ValueError, 'existing preparation'): self.prepare()
            self.assertEqual(upload.call_count, 1)
        self.assertTrue((self.out/'selection-upload-intent.json').exists())
        self.assertFalse((self.out/'candidate.json').exists())

    def test_unknown_source_upload_preserves_intent_and_prevents_retry(self):
        self.prepare(); self.fail_source_upload = True
        with self.assertRaises(TimeoutError): prep.publish()
        with self.assertRaisesRegex(ValueError, 'never upload blindly'): prep.publish()
        self.assertEqual(len(self.uploads), 2)
        self.assertTrue((self.out/'source-upload-intent.json').exists())
        self.assertFalse((self.out/'source-upload-receipt.json').exists())
        self.assertFalse((self.out/'release.json').exists())

    def test_failed_download_keeps_successful_upload_receipt_without_release(self):
        self.prepare(); self.bad_source_download = True
        with self.assertRaisesRegex(ValueError, 'Published source hash'): prep.publish()
        self.assertTrue((self.out/'source-upload-receipt.json').exists())
        self.assertFalse((self.out/'release.json').exists())
        with self.assertRaisesRegex(ValueError, 'never upload blindly'): prep.publish()
        self.assertEqual(len(self.uploads), 2)

    def test_changed_candidate_rejected_before_download_or_upload(self):
        self.prepare(); (self.out/'candidate.json').write_text('{}')
        with patch.object(prep, 'hf_hub_download') as download, self.assertRaisesRegex(ValueError, 'preparation changed'):
            prep.publish()
        download.assert_not_called(); self.assertEqual(len(self.uploads), 1)

    def test_rehashed_wrong_worker_control_is_rejected(self):
        self.prepare(); source = self.out/'bundle/source'
        row = prep.read(source/'final-plan.json')['rows'][0]; job = prep.read(source/row['job'])
        job['workers'] = 8; prep.durable_write(source/row['job'], job); self.reseal_test_source()
        with self.assertRaisesRegex(ValueError, 'Final control differs'): prep.publish()
        self.assertEqual(len(self.uploads), 1)

    def test_rehashed_wrong_plan_allocation_is_rejected(self):
        self.prepare(); source = self.out/'bundle/source'; plan = prep.read(source/'final-plan.json')
        plan['rows'][0]['workers'] = 8; prep.durable_write(source/'final-plan.json', plan); self.reseal_test_source()
        with self.assertRaisesRegex(ValueError, 'worker allocation'): prep.publish()
        self.assertEqual(len(self.uploads), 1)

    def test_invalid_timeout_blocks_before_network_or_tarball(self):
        self.ready['resources']['allocation'][prep.schedule()[0]['name']]['timeout'] = '25h'
        self.prepare()
        with patch.object(prep, 'hf_hub_download') as download, self.assertRaisesRegex(ValueError, 'Invalid timeout'):
            prep.publish()
        download.assert_not_called(); self.assertFalse((self.out/prep.SOURCE_NAME).exists())

    def test_readiness_changed_after_preparation_blocks_publication(self):
        self.prepare(); self.ready['input_hashes']['pin'] = 'a'*64
        with self.assertRaisesRegex(ValueError, 'Selection or allocation changed'): prep.publish()
        self.assertEqual(len(self.uploads), 1)

    def test_different_selection_archive_rejected_before_network(self):
        self.prepare(); saved = prep.read(self.out/'prepared.json')
        saved['selection_archive']['revision'] = 'a'*40
        prep.durable_write(self.out/'prepared.json', saved)
        with patch.object(prep, 'hf_hub_download') as download, self.assertRaisesRegex(ValueError, 'selection archive differs'):
            prep.publish()
        download.assert_not_called(); self.assertEqual(len(self.uploads), 1)

    def test_existing_source_tarball_is_preserved_without_upload(self):
        self.prepare(); archive = self.out/prep.SOURCE_NAME; archive.write_bytes(b'original partial archive')
        with self.assertRaisesRegex(ValueError, 'existing source tarball'): prep.publish()
        self.assertEqual(archive.read_bytes(), b'original partial archive')
        self.assertEqual(len(self.uploads), 1)


if __name__ == '__main__': unittest.main()
