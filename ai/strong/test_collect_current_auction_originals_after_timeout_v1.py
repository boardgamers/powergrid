"""Synthetic collection tests. No job submission, simulation, or inference."""
from contextlib import ExitStack
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import collect_current_auction_originals_after_timeout_v1 as c


class TimeoutCollectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.jobs = self.root / 'jobs'
        self.out = self.root / 'collection'
        self.jobs.mkdir()
        (self.out / 'failures').mkdir(parents=True)
        self.source_path = self.root / 'source.json'
        self.source_path.write_text('{}')
        self.archive = self.root / 'original.tgz'
        self.archive.write_bytes(b'original compressed bytes')
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        for obj, name, value in [(c, 'OUT', self.out), (c.m, 'OUT', self.jobs),
                (c.m, 'SOURCE', self.source_path)]:
            self.stack.enter_context(patch.object(obj, name, value))
        self.api = Mock(spec=['fetch_job_logs'])
        self.download = self.stack.enter_context(patch.object(c, 'hf_hub_download', return_value=str(self.archive)))
        self.extract = self.stack.enter_context(patch.object(c, 'extract_verified',
            side_effect=lambda archive, dest: dest.mkdir()))
        self.verify = self.stack.enter_context(patch.object(c.m.base, 'verify_artifacts', return_value={'games': 16}))

    def row(self, name='original', stage='COMPLETED'):
        row = {'name': name, 'shard': {'games': 16}}
        folder = self.jobs / name
        folder.mkdir()
        guard = {'job_id': name + '-handle', 'row': row}
        (folder / 'launch.json').write_text(json.dumps(guard))
        status = {'name': name, 'job_id': guard['job_id'], 'stage': stage}
        evidence = {'repo': 'coyotte508/powergrid-ai-germany-v1',
            'archive_path': 'archives/' + name + '.tgz', 'remote_archive_verified': True,
            'revision': 'a' * 40, 'archive_sha256': c.digest(self.archive)}
        receipt = {'case': name, 'status': {}, 'evidence': evidence}
        return row, folder, status, receipt

    def test_missing_receipt_preserves_failed_original_without_download_or_verification(self):
        row, folder, status, receipt = self.row(stage='ERROR')
        self.api.fetch_job_logs.return_value = ['{"game_progress":"9/16"}']
        saved, failure = c.collect_terminal(self.api, {'rows': [row]}, row, status)
        self.assertIsNone(saved)
        self.assertEqual(failure['stage'], 'ERROR')
        self.assertEqual(failure['receipt_count'], 0)
        self.assertFalse(failure['verified'])
        self.assertFalse((folder / 'verified.json').exists())
        self.assertTrue((folder / 'original-recovery-collection.log').exists())
        self.download.assert_not_called()
        self.verify.assert_not_called()

    def test_ambiguous_receipts_are_not_chosen_arbitrarily(self):
        row, folder, status, receipt = self.row()
        self.api.fetch_job_logs.return_value = [json.dumps(receipt)] * 2
        saved, failure = c.collect_terminal(self.api, {}, row, status)
        self.assertIsNone(saved)
        self.assertEqual(failure['receipt_count'], 2)
        self.download.assert_not_called()

    def test_changed_log_preserves_both_observations(self):
        row, folder, status, receipt = self.row()
        (folder / 'original-recovery-collection.log').write_text('first observation')
        self.api.fetch_job_logs.return_value = [json.dumps(receipt)]
        saved, failure = c.collect_terminal(self.api, {}, row, status)
        self.assertIsNone(saved)
        self.assertEqual(failure['category'], 'changed_original_log')
        self.assertEqual((folder / 'original-recovery-collection.log').read_text(), 'first observation')
        self.assertTrue((self.out / 'failures/original.changed.log').exists())
        self.download.assert_not_called()

    def test_complete_original_uses_existing_raw_verifier_and_original_identity(self):
        row, folder, status, receipt = self.row()
        source = {'rows': [row]}
        self.api.fetch_job_logs.return_value = [json.dumps(receipt)]
        saved, failure = c.collect_terminal(self.api, source, row, status)
        self.assertIsNone(failure)
        self.assertTrue(c.m.recovery.complete_data(saved))
        self.assertEqual(saved['job_id'], status['job_id'])
        self.assertEqual(saved['guard_sha256'], c.digest(folder / 'launch.json'))
        self.verify.assert_called_once_with(folder / 'artifacts', source, row, receipt['evidence'])
        self.assertEqual(json.loads((folder / 'verified.json').read_text()), saved)

    def test_wrong_archive_hash_cannot_reach_raw_audit(self):
        row, folder, status, receipt = self.row()
        receipt['evidence']['archive_sha256'] = '0' * 64
        self.api.fetch_job_logs.return_value = [json.dumps(receipt)]
        saved, failure = c.collect_terminal(self.api, {}, row, status)
        self.assertIsNone(saved)
        self.assertFalse(failure['verified'])
        self.verify.assert_not_called()
        self.extract.assert_not_called()

    def test_foreign_archive_is_rejected_before_download(self):
        row, folder, status, receipt = self.row()
        receipt['evidence']['archive_path'] = 'archives/other.tgz'
        self.api.fetch_job_logs.return_value = [json.dumps(receipt)]
        saved, failure = c.collect_terminal(self.api, {}, row, status)
        self.assertIsNone(saved)
        self.download.assert_not_called()

    def test_rejected_raw_data_is_retained_and_never_marked_verified(self):
        row, folder, status, receipt = self.row()
        self.api.fetch_job_logs.return_value = [json.dumps(receipt)]
        self.verify.side_effect = AssertionError('incomplete raw games')
        saved, failure = c.collect_terminal(self.api, {}, row, status)
        self.assertIsNone(saved)
        self.assertFalse((folder / 'verified.json').exists())
        self.assertTrue((folder / 'artifacts').exists())
        self.assertTrue(self.archive.exists())
        self.assertEqual(failure['failure_type'], 'AssertionError')

    def test_failure_does_not_prevent_other_original_collection_or_become_success(self):
        bad = self.row('bad', 'ERROR')
        good = self.row('good')
        active = self.row('active', 'RUNNING')
        rows = [bad[0], good[0], active[0], {'name': 'unsubmitted'}]
        statuses = {r[0]['name']: r[2] for r in [bad, good, active]}
        logs = {bad[2]['job_id']: ['partial'], good[2]['job_id']: [json.dumps(good[3])]}
        self.api.fetch_job_logs.side_effect = lambda job_id, follow: logs[job_id]
        def cached(folder, source, row):
            path = folder / 'verified.json'
            return json.loads(path.read_text()) if path.exists() else None
        with patch.object(c.m, 'cached', side_effect=cached), patch.object(c.m.base,
                'original_status', side_effect=lambda api, source, row: statuses[row['name']]):
            report = c.cycle(self.api, {'rows': rows}, 8)
            self.assertEqual(report['verified_jobs'], 1)
            self.assertEqual(len(report['failed_originals']), 1)
            self.assertEqual(len(report['active_originals']), 1)
            self.assertEqual(report['unsubmitted_jobs'], ['unsubmitted'])
            self.assertFalse(report['complete'])
            self.assertFalse(report['qualified'])
            self.assertEqual(report['new_jobs'], 0)
            self.assertEqual(report['new_games'], 0)
            calls = self.api.fetch_job_logs.call_count
            repeated = c.cycle(self.api, {'rows': rows}, 8)
            self.assertEqual(self.api.fetch_job_logs.call_count, calls)
            self.assertEqual(len(repeated['failed_originals']), 1)
            (bad[1] / 'original-recovery-collection.log').write_text('changed failure evidence')
            with self.assertRaises(AssertionError):
                c.cycle(self.api, {'rows': rows}, 8)

    def test_partial_error_archive_cannot_use_normal_completion_verifier(self):
        row, folder, status, receipt = self.row(stage='ERROR')
        self.api.fetch_job_logs.return_value = [json.dumps(receipt)]
        with patch.object(c.m.recovery, 'prepare', side_effect=ValueError('partial originals')) as recover:
            saved, failure = c.collect_terminal(self.api, {}, row, status)
        self.assertIsNone(saved)
        self.assertFalse(failure['verified'])
        self.assertTrue((folder / 'preserved-terminal-error-v1.json').exists())
        self.assertFalse((folder / 'verified-terminal-recovery-v1.json').exists())
        self.verify.assert_not_called()
        recover.assert_called_once()

    def test_terminal_limit_defers_collection_without_omitting_jobs(self):
        first = self.row('first')
        second = self.row('second')
        self.api.fetch_job_logs.return_value = [json.dumps(first[3])]
        statuses = {r[0]['name']: r[2] for r in [first, second]}
        with patch.object(c.m, 'cached', return_value=None), patch.object(c.m.base,
                'original_status', side_effect=lambda api, source, row: statuses[row['name']]):
            report = c.cycle(self.api, {'rows': [first[0], second[0]]}, 1)
        self.assertEqual(report['verified_jobs'], 1)
        self.assertEqual(report['deferred_terminals'], [second[2]])
        self.assertFalse(report['complete'])

    def test_live_original_owner_blocks_admission(self):
        state = {'stage': 'stopped_for_inspection', 'failure_type': 'AssertionError',
            'failure': 'Preserve missing/ambiguous original archive; never resubmit', 'pid': os.getpid()}
        with patch.object(c, 'read', return_value=state), patch.object(c.m, 'admitted') as admitted:
            with self.assertRaisesRegex(AssertionError, 'Original owner must have exited'):
                c.admission()
        admitted.assert_not_called()


if __name__ == '__main__':
    unittest.main()
