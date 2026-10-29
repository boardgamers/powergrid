"""Fabricated final receipts and tiny package fixtures; no games or inference."""
from contextlib import ExitStack
from copy import deepcopy
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch

import assess_selected_public_policy_final_v1 as assessment
import test_public_policy_final_audit_v1 as fixtures


class CompletenessTests(unittest.TestCase):
    def test_unfinished_confirmation_stops_before_output_or_worker_pool(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(assessment, 'OUT', Path(temp)/'no-output'), \
             patch.object(assessment.manager, 'read', return_value={'stage': 'waiting_for_original_confirmation_jobs'}) as reader, \
             patch.object(assessment, 'ProcessPoolExecutor') as pool:
            with self.assertRaisesRegex(ValueError, 'Wait for all original'): assessment.run()
            self.assertEqual(reader.call_count, 1); pool.assert_not_called(); self.assertFalse(assessment.OUT.exists())

    def test_incomplete_final_collection_cannot_open_individual_results(self):
        with patch.object(assessment, 'read', return_value={'complete': False}), \
             patch.object(assessment.manager, 'originals') as originals:
            with self.assertRaisesRegex(ValueError, 'Wait for all original final'): assessment.complete_originals({})
            originals.assert_not_called()

    def test_not_yet_run_final_cannot_create_or_halt_manager(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(assessment.manager, 'OUT', Path(temp)/'no-run'), \
             patch.object(assessment.manager, 'admission', return_value={}), patch.object(assessment.manager, 'operation') as operation:
            with self.assertRaisesRegex(ValueError, 'Wait for all original final'): assessment.run()
            operation.assert_not_called(); self.assertFalse(assessment.manager.OUT.exists())

    def test_existing_assessment_rejected_without_halting_original_manager(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); (root/'collection-results.json').write_text('{}')
            with patch.object(assessment.manager, 'OUT', root), patch.object(assessment, 'OUT', root), \
                 patch.object(assessment.manager, 'admission', return_value={}), patch.object(assessment.manager, 'operation') as operation:
                with self.assertRaisesRegex(ValueError, 'existing final assessment'): assessment.run()
                operation.assert_not_called(); self.assertFalse((root/'halt.json').exists())

    def test_independent_worker_rejects_different_raw_review(self):
        task={k:'synthetic' for k in ('name','archive','source_root','release','launch','evidence','bootstrap','scratch','receipt')}
        task['initial_review_sha256']='a'*64
        with patch.object(assessment, 'audit_archive', return_value={'review_sha256':'b'*64}):
            with self.assertRaisesRegex(ValueError, 'differs from original'): assessment.independent_one(task)


class ReceiptAssessmentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup); self.root = Path(self.tmp.name)
        self.identity = fixtures.identity(True)
        self.audits = fixtures.synthetic_audits(self.identity)
        for audit in self.audits: audit['counts'].update(search_decisions=1, rollouts=8)
        self.context = {'release': {'plan': {'identity': self.identity, 'candidate_sha256': 'a'*64,
            'rows': [{'name': a['expected']['name']} for a in self.audits]}, 'admission_sha256': 'b'*64}}
        self.standalone = {'verified': True, 'identity': self.identity, 'selected_policy_positions': 2553}
        self.tasks = []; self.results = {}; self.write_receipts()

    def write_receipts(self):
        self.tasks = []; self.results = {}
        for i, audit in enumerate(self.audits):
            name = audit['expected']['name']; path = self.root/(name+'.json')
            launch = {'job_id': f'{i:024x}', 'row': {'shard': audit['expected']}}
            evidence = {'archive_sha256': f'{i:064x}'}
            review = {'verified': True, 'qualified': False, 'name': name, 'job_id': launch['job_id'],
                'original_hf_stage': 'COMPLETED', 'games': audit['expected']['games'], 'identity': self.identity,
                'release_sha256': assessment.object_hash(self.context['release']),
                'launch_sha256': assessment.object_hash(launch), 'evidence': evidence,
                'audit': audit, 'provenance': {'candidate_sha256': 'a'*64}}
            sha = assessment.object_hash(review)
            receipt = {'purpose': 'independent_final_audit', 'qualified': False,
                'release_sha256': review['release_sha256'], 'launch_sha256': review['launch_sha256'],
                'review': review, 'review_sha256': sha, 'evidence': evidence,
                'original_archive_sha256': evidence['archive_sha256']}
            path.write_text(json.dumps(receipt))
            self.tasks.append({'name': name, 'launch': launch, 'evidence': evidence,
                'initial_review_sha256': sha, 'receipt': str(path)})
            self.results[name] = {'name': name, 'receipt': str(path), 'receipt_sha256': assessment.digest(path), 'review_sha256': sha}

    def invoke(self):
        return assessment.assess_receipts(self.context, self.tasks, self.results, self.standalone)

    def alter_receipt(self, callback, *, reconcile_review=False):
        task = self.tasks[0]; path = Path(task['receipt']); receipt = assessment.read(path); callback(receipt)
        if reconcile_review:
            sha = assessment.object_hash(receipt['review']); receipt['review_sha256'] = sha
            task['initial_review_sha256'] = sha; self.results[task['name']]['review_sha256'] = sha
        path.write_text(json.dumps(receipt)); self.results[task['name']]['receipt_sha256'] = assessment.digest(path)

    def test_all_20160_fabricated_wins_pass_strength_but_not_technical_qualification(self):
        result = self.invoke()
        self.assertTrue(result['strength']['strength_passed']); self.assertFalse(result['qualified'])
        self.assertFalse(result['qualification_verified']); self.assertEqual(result['strength']['games'], 20160)
        self.assertEqual(len(result['strength']['evaluations']), 26)

    def test_bad_rule_is_failure_despite_strong_overall_average(self):
        for audit in self.audits:
            if audit['expected']['group'] == 'search_geo/4p':
                for row in audit['terminals']:
                    if row['variant'] == 'recharged' and row['sealed']:
                        row['win'] = 0.; row['value'] = [float(i == (row['seat']+1)%4) for i in range(4)]
        self.write_receipts(); result = self.invoke()
        self.assertFalse(result['strength']['strength_passed']); self.assertFalse(result['qualified'])
        self.assertTrue(any('search_geo/4p/recharged/sealed' in e for e in result['strength']['errors']))

    def test_missing_or_duplicate_separate_audits_block_statistics(self):
        for tasks in (self.tasks[:-1], [self.tasks[0], *self.tasks[1:-1], self.tasks[0]]):
            with patch.object(assessment, 'assess_final_games') as stats, self.assertRaisesRegex(ValueError, 'Incomplete separate'):
                assessment.assess_receipts(self.context, tasks, self.results, self.standalone)
            stats.assert_not_called()

    def test_initial_audit_cannot_be_relabelled_as_independent(self):
        self.alter_receipt(lambda r: r.update(purpose='initial_collection'))
        with self.assertRaisesRegex(ValueError, 'Not a separate'): self.invoke()

    def test_fresh_review_must_equal_original_raw_audit(self):
        self.alter_receipt(lambda r: r['review'].update(games=1))
        with self.assertRaisesRegex(ValueError, 'differs from initial'): self.invoke()

    def test_wrong_original_handle_cannot_pass_even_with_rehashed_receipt(self):
        self.alter_receipt(lambda r: r['review'].update(job_id='f'*24), reconcile_review=True)
        with self.assertRaisesRegex(ValueError, 'another original job'): self.invoke()

    def test_changed_candidate_cannot_inherit_strength(self):
        self.alter_receipt(lambda r: r['review']['provenance'].update(candidate_sha256='c'*64), reconcile_review=True)
        with self.assertRaisesRegex(ValueError, 'Executed candidate'): self.invoke()

    def test_other_standalone_policy_cannot_inherit_target_proof(self):
        self.standalone['identity'] = fixtures.identity(False)
        with self.assertRaisesRegex(ValueError, 'selected standalone'): self.invoke()


class StandalonePackageTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack(); self.addCleanup(self.stack.close)
        self.root = Path(self.stack.enter_context(tempfile.TemporaryDirectory()))
        self.target = self.root/'target'; self.package = self.target/'package'; self.package.mkdir(parents=True)
        self.collected = self.root/'collected'; (self.collected/'output').mkdir(parents=True)
        (self.root/'ai/strong').mkdir(parents=True)
        self.identity = fixtures.identity(True); self.arm = assessment.manager.preparation.selection.ARM
        (self.package/'benchmark.py').write_text('# never executed')
        (self.package/'cases.jsonl').write_text('synthetic fixture metadata')
        manifest = {'positions': 2553, 'requests': 5106, 'identities': {self.arm: self.identity},
            'runner_sha256': assessment.digest(self.package/'benchmark.py'),
            'files': {p.name: assessment.digest(p) for p in self.package.iterdir()}}
        self.save(self.package/'benchmark-manifest.json', manifest)
        self.archive = self.target/'package.tgz'
        with tarfile.open(self.archive, 'w:gz') as archive:
            for p in self.package.iterdir(): archive.add(p, arcname=p.name)
        prepared = {'positions': 2553, 'requests': 5106, 'package_sha256': assessment.digest(self.archive),
            'package_bytes': self.archive.stat().st_size, 'manifest_sha256': assessment.digest(self.package/'benchmark-manifest.json'),
            'runner_sha256': manifest['runner_sha256'], 'cases_sha256': assessment.digest(self.package/'cases.jsonl')}
        self.save(self.target/'prepared.json', prepared)
        self.launch_path = self.root/'ai/strong/current-full-serving-8840u-launch-v1.json'
        self.save(self.launch_path, {**prepared, 'stage': 'launched', 'host': 'minipc', 'pid': 7})
        status_path = self.collected/'output/status.json'
        self.save(status_path, {'stage': 'completed', 'passed': True, 'pid': 7, 'processor': 'AMD 8840U synthetic',
            'completed_requests': 5106, 'manifest_sha256': prepared['manifest_sha256']})
        self.save(self.root/assessment.manager.preparation.selection.TECHNICAL, {'identities': {self.arm: self.identity},
            'status_sha256': assessment.digest(status_path), 'manifest_sha256': prepared['manifest_sha256']})
        for name, value in (('ROOT', self.root), ('TARGET', self.target), ('COLLECTED_TARGET', self.collected)):
            self.stack.enter_context(patch.object(assessment, name, value))
        self.stack.enter_context(patch.object(assessment, 'artifact_identity', return_value=self.identity))

    def save(self, path, value): path.write_text(json.dumps(value))

    def test_original_archive_package_and_target_bind_without_execution(self):
        result = assessment.standalone_proof(self.identity)
        self.assertTrue(result['verified']); self.assertEqual(result['new_inference_calls'], 0)
        self.assertEqual(result['package_sha256'], assessment.digest(self.archive))

    def test_archive_mutation_and_missing_file_rejected(self):
        self.archive.write_bytes(self.archive.read_bytes()+b'changed')
        with self.assertRaisesRegex(ValueError, 'archive changed'): assessment.standalone_proof(self.identity)
        (self.package/'cases.jsonl').unlink()
        with self.assertRaises(FileNotFoundError): assessment.standalone_proof(self.identity)

    def test_wrong_original_target_process_rejected(self):
        launch = assessment.read(self.launch_path); launch['pid'] = 8; self.save(self.launch_path, launch)
        with self.assertRaisesRegex(ValueError, 'completed target process'): assessment.standalone_proof(self.identity)


if __name__ == '__main__': unittest.main()
