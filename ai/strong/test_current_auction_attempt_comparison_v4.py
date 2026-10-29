"""Coverage, immutable archive and mixed-audit failure tests; no real games."""
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import Mock, patch

import current_auction_attempt_comparison_v4 as c


class AdmissionTests(unittest.TestCase):
    def setUp(self):
        self.plan = {'slots': [
            {'name': 'original', 'kind': 'preserved_original', 'original': {'job_id': '1'*24}},
            {'name': 'recovery', 'kind': 'first_execution', 'original': None, 'original_row_sha256': 'a'*64}],
            'first_recovery': {}}
        self.ref = {'name': 'recovery', 'backend': 'bucket_remaining_v3', 'original_row_sha256': 'a'*64,
            'original_failed_handle': None, 'stage': 'COMPLETED', 'verified': True,
            'job_id': '2'*24, 'attempt_id': 'unique-attempt', 'review_sha256': 'b'*64}
        self.found = {'complete': True, 'missing': [], 'required': 1, 'available': [self.ref]}

    def test_complete_reference_metadata_accepted_without_loading_reviews(self):
        with patch.object(c, 'read') as read:
            self.assertEqual(c.complete_reference_index(self.plan, self.found), {'recovery': self.ref})
        read.assert_not_called()

    def test_incomplete_compare_never_loads_reviews_checks_context_or_writes_intent(self):
        self.found.update(complete=False, missing=[{'name': 'recovery'}], available=[])
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)/'comparison.json'
            with patch.object(c.auth.coverage, 'actual_plan', return_value=self.plan), \
                 patch.object(c.auth, 'actual_routes', return_value={}), \
                 patch.object(c.auth, 'inventory', return_value=self.found), \
                 patch.object(c, 'check_inputs') as inputs, patch.object(c, 'make_cases') as cases, \
                 patch.object(c, 'parallel_audit') as audit, patch.object(c.statistics, 'analyze') as stats:
                with self.assertRaisesRegex(ValueError, 'Incomplete recovery coverage'):
                    c.compare(output)
            for fn in (inputs, cases, audit, stats): fn.assert_not_called()
            self.assertEqual(list(Path(tmp).iterdir()), [])

    def test_missing_duplicate_or_foreign_assignment_rejected(self):
        for refs in ([], [self.ref, self.ref], [{**self.ref, 'name': 'foreign'}]):
            with self.subTest(refs=refs), self.assertRaises(ValueError):
                c.complete_reference_index(self.plan, {**self.found, 'available': refs})

    def test_changed_row_status_pin_or_original_handle_rejected(self):
        for field, value in [('original_row_sha256', 'c'*64), ('stage', 'ERROR'), ('verified', False),
                             ('job_id', '1'*24), ('review_sha256', 'unpinned'), ('original_failed_handle', 'f'*24)]:
            found = deepcopy(self.found); found['available'][0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                c.complete_reference_index(self.plan, found)

    def test_known_original_failure_and_exact_recovery_are_preserved(self):
        self.plan['slots'][1]['kind'] = 'failed_original_recovery'
        self.ref['original_failed_handle'] = c.auth.previous.first.worker.FAILED_HANDLE
        self.plan['first_recovery'] = {k: self.ref[k] for k in ('job_id', 'attempt_id', 'original_failed_handle')}
        self.assertEqual(c.complete_reference_index(self.plan, self.found)['recovery'], self.ref)
        self.ref['job_id'] = '3'*24
        with self.assertRaisesRegex(ValueError, 'substituted'): c.complete_reference_index(self.plan, self.found)

    def test_existing_intent_prevents_repeating_comparison(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'result.json'; path.with_suffix('.intent.json').write_text('{}')
            with patch.object(c.auth.coverage, 'actual_plan') as plan:
                with self.assertRaisesRegex(ValueError, 'existing comparison'): c.compare(path)
            plan.assert_not_called()


class IndependentAuditTests(unittest.TestCase):
    def setUp(self):
        self.cases = [{'name': str(i), 'backend': backend, 'job_id': str(i)*24, 'games': 16,
            'receipt_sha256': str(i)*64, 'raw_review_sha256': 'a'*64, 'stage': stage,
            'counts': {'rollout_caps': 0, 'games': 16}} for i, (backend, stage) in
            enumerate([('original', 'ERROR'), ('retained_v2', 'COMPLETED'), ('bucket_remaining_v3', 'COMPLETED')], 1)]
        self.results = [{k: v for k, v in case.items() if k not in ('stage', 'raw_review_sha256')} |
            {'original_hf_stage': case['stage'], 'review_sha256': case['raw_review_sha256']} for case in self.cases]

    def test_all_backends_and_original_error_status_survive_reordering(self):
        result = c.match_audits(self.cases, list(reversed(self.results)))
        self.assertEqual(result['1']['original_hf_stage'], 'ERROR')
        self.assertEqual(len(result), 3)

    def test_missing_duplicate_and_foreign_audits_rejected(self):
        for values in (self.results[:2], self.results[:2]+self.results[:1],
                       self.results[:2]+[{**self.results[2], 'name': 'foreign'}]):
            with self.assertRaises(ValueError): c.match_audits(self.cases, values)

    def test_every_full_review_and_identity_field_is_bound(self):
        for field, value in [('backend', 'other'), ('job_id', 'f'*24), ('games', 15),
                             ('receipt_sha256', 'e'*64), ('review_sha256', 'e'*64),
                             ('counts', {'rollout_caps': 1}), ('original_hf_stage', 'COMPLETED')]:
            results = deepcopy(self.results); results[0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError): c.match_audits(self.cases, results)

    def test_changed_receipt_rejected_before_authentication_or_raw_audit(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'receipt.json'; path.write_text('{}')
            with patch.object(c, 'ROOT', Path(tmp)), patch.object(c, 'attempt_context') as context, \
                 patch.object(c.originals, 'audit_original') as original:
                with self.assertRaisesRegex(ValueError, 'Receipt changed'):
                    c.audit_case({'receipt_file': 'receipt.json', 'receipt_sha256': '0'*64})
            context.assert_not_called(); original.assert_not_called()

    def test_four_workers_and_failure_cancellation(self):
        pool = Mock(); pool.map.side_effect = ValueError('raw mismatch')
        with patch.object(c, 'ProcessPoolExecutor', return_value=pool) as executor:
            with self.assertRaisesRegex(ValueError, 'raw mismatch'): c.parallel_audit(self.cases)
        self.assertEqual(executor.call_args.kwargs['max_workers'], 4)
        pool.shutdown.assert_called_once_with(wait=True, cancel_futures=True)

    def test_success_returns_exact_worker_results(self):
        pool = Mock(); pool.map.return_value = iter(self.results)
        with patch.object(c, 'ProcessPoolExecutor', return_value=pool):
            self.assertEqual(c.parallel_audit(self.cases), self.results)
        pool.shutdown.assert_called_once_with(wait=True)


class CachedArchiveTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.archive = Path(self.tmp.name)/'case.tgz'; manifest = b'{"raw":"sha"}'
        with tarfile.open(self.archive, 'w:gz') as tar:
            entry = tarfile.TarInfo('manifest.json'); entry.size = len(manifest)
            tar.addfile(entry, io.BytesIO(manifest))
        self.evidence = {'repo': 'coyotte508/powergrid-ai-germany-v1', 'archive_path': 'archives/case.tgz',
            'revision': 'a'*40, 'remote_archive_verified': True, 'archive_sha256': c.digest(self.archive),
            'manifest_sha256': hashlib.sha256(manifest).hexdigest()}

    def test_cache_only_revision_pinned_lookup(self):
        with patch.object(c, 'hf_hub_download', return_value=str(self.archive)) as download:
            c.cached_archive(self.evidence, 'case')
        self.assertTrue(download.call_args.kwargs['local_files_only'])
        self.assertEqual(download.call_args.kwargs['revision'], 'a'*40)

    def test_changed_archive_or_manifest_rejected(self):
        for field in ('archive_sha256', 'manifest_sha256'):
            evidence = {**self.evidence, field: '0'*64}
            with patch.object(c, 'hf_hub_download', return_value=str(self.archive)), self.assertRaises(ValueError):
                c.cached_archive(evidence, 'case')

    def test_unpinned_revision_rejected_before_cache_lookup(self):
        with patch.object(c, 'hf_hub_download') as download, self.assertRaises(ValueError):
            c.cached_archive({**self.evidence, 'revision': 'main'}, 'case')
        download.assert_not_called()


if __name__ == '__main__': unittest.main()
