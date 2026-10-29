"""Mocked HF lifecycle tests; no model/game execution or actual submissions."""
from contextlib import ExitStack
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import manage_selected_public_policy_final_v1 as manager
import selected_public_policy_final_dispatch_v1 as dispatch
import selected_public_policy_final_collection_v1 as collector
import test_selected_public_policy_final_dispatch_v1 as dispatch_fixtures
import test_selected_public_policy_final_collection_v1 as collection_fixtures
import test_prepare_selected_public_policy_final_v1 as preparation_fixtures


class AdmissionTests(unittest.TestCase):
    def test_actual_incomplete_owner_prevents_network_and_preparation_reads(self):
        with patch.object(manager, 'read', return_value={'stage': 'waiting_for_original_confirmation_jobs'}) as reader, \
             patch.object(manager, 'hf_hub_download') as download, patch.object(manager, 'HfApi') as api:
            with self.assertRaisesRegex(ValueError, 'Wait for all original'): manager.admission()
            reader.assert_called_once_with(manager.ROOT/manager.preparation.selection.OWNER)
            download.assert_not_called(); api.assert_not_called()

    def fixture(self):
        f = preparation_fixtures.PreparationTests(); f.setUp(); self.addCleanup(f.doCleanups)
        f.prepare(); manager.preparation.publish()
        root = f.root
        p = root/manager.preparation.selection.OWNER; p.parent.mkdir(parents=True, exist_ok=True)
        manager.durable_write(p, {'stage': 'complete', 'completed_games': 26880,
            'qualified': False, 'reserved_final_seeds_used': False}, exclusive=True)
        for name in ('manage_selected_public_policy_final_v1.py', 'selected_public_policy_final_dispatch_v1.py',
                     'selected_public_policy_final_streaming_v1.py', 'selected_public_policy_final_collection_v1.py',
                     'public_policy_final_audit_v1.py', 'public_policy_final_contract_v1.py',
                     'public_policy_runtime_v1.py', 'population_policy_verification.py'):
            (root/'ai/strong'/name).write_text('# synthetic dependency, never executed\n')
        stack = ExitStack(); self.addCleanup(stack.close)
        stack.enter_context(patch.object(manager, 'ROOT', root))
        stack.enter_context(patch.object(manager, 'OUT', root/'final'))
        stack.enter_context(patch.object(manager, 'hf_hub_download', f.download))
        return f

    def test_published_mocked_preparation_is_bound_to_real_controls_and_release(self):
        f = self.fixture(); context = manager.admission()
        self.assertEqual(context['max_active_jobs'], 64)
        self.assertEqual(context['release']['plan']['games'], 20160)
        self.assertFalse(manager.OUT.exists())
        self.assertEqual(len(f.uploads), 2)  # Earlier mocked publication only.

    def test_admission_cannot_change_execution_flags_or_upload_receipt(self):
        f = self.fixture(); path = f.out/'admission.json'; original = manager.read(path)
        for field, value in (('original_only', False), ('automatic_retries', True), ('max_active_jobs', 65)):
            altered = {**original, field: value}; manager.durable_write(path, altered)
            release = manager.read(f.out/'release.json'); release['admission_sha256'] = manager.digest(path)
            manager.durable_write(f.out/'release.json', release)
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'Invalid initial launch admission'):
                manager.admission()
        manager.durable_write(path, original)
        release['admission_sha256'] = manager.digest(path); manager.durable_write(f.out/'release.json', release)
        receipt = manager.read(f.out/'source-upload-receipt.json'); receipt['revision'] = 'a'*40
        manager.durable_write(f.out/'source-upload-receipt.json', receipt)
        with self.assertRaisesRegex(ValueError, 'source receipt differs'): manager.admission()


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.f = dispatch_fixtures.FinalDispatchTests(); self.f.setUp(); self.addCleanup(self.f.doCleanups)
        self.stack = ExitStack(); self.addCleanup(self.stack.close)
        self.root = self.f.root.parent; self.out = self.root/'final'
        (self.root/'pin').write_text('original runtime')
        self.context = {'version': 1, 'release': self.f.release, 'bootstrap': self.f.bootstrap,
            'source_root': str(self.root/'source'), 'input_hashes': {'pin': manager.digest(self.root/'pin')},
            'max_active_jobs': 64, 'automatic_retries': False, 'qualified': False}
        self.stack.enter_context(patch.object(manager, 'ROOT', self.root))
        self.stack.enter_context(patch.object(manager, 'OUT', self.out))
        self.stages = {}; self.events = []; self.next_id = 0
        self.api = Mock(); self.api.run_job.side_effect = self.submit
        self.api.inspect_job.side_effect = lambda **kw: SimpleNamespace(status=SimpleNamespace(stage=self.stages[kw['job_id']]))

    def submit(self, **kwargs):
        self.next_id += 1; handle = f'{self.next_id:024x}'; self.stages[handle] = 'RUNNING'
        self.events.append(('submit', kwargs['name']))
        return SimpleNamespace(id=handle)

    def seed(self, count=1):
        self.out.mkdir(exist_ok=True)
        return [dispatch.dispatch_once(self.api, self.out/'dispatch', self.f.release, row['name'],
                'synthetic-secret', self.f.bootstrap) for row in self.f.release['plan']['rows'][:count]]

    def fake_collection(self, context, api, launch, observed):
        self.events.append(('collect', launch['name']))
        return {'name': launch['name'], 'games': launch['row']['shard']['games']}

    def test_concurrency_cap_original_handles_and_collect_only(self):
        with manager.operation(self.context):
            first = manager.cycle(self.context, self.api, execute=True, token='synthetic-secret')
        self.assertEqual(first['newly_submitted'], 64); self.assertEqual(first['submitted_jobs'], 64)
        with manager.operation(self.context):
            second = manager.cycle(self.context, self.api, execute=True, token='synthetic-secret')
        self.assertEqual(second['newly_submitted'], 0); self.assertEqual(self.api.run_job.call_count, 64)
        self.assertNotIn('synthetic-secret', (self.out/'collection-state.json').read_text())

    def test_collection_precedes_new_dispatch_and_collect_mode_never_submits(self):
        launch = self.seed()[0]; self.stages[launch['job_id']] = 'COMPLETED'; self.events.clear()
        with patch.object(manager, 'collect_one', side_effect=self.fake_collection):
            result = manager.cycle(self.context, self.api, execute=False)
        self.assertEqual(result['newly_submitted'], 0); self.assertEqual(self.events, [('collect', launch['name'])])
        self.events.clear()
        with patch.object(manager, 'collect_one', side_effect=self.fake_collection):
            result = manager.cycle(self.context, self.api, execute=True, token='synthetic-secret')
        self.assertEqual(self.events[0], ('collect', launch['name']))
        self.assertEqual(result['newly_submitted'], 64)

    def test_completion_during_collection_defers_dispatch(self):
        self.seed(); self.api.inspect_job.side_effect = [SimpleNamespace(status=SimpleNamespace(stage=s))
                                                     for s in ('RUNNING', 'COMPLETED')]
        result = manager.cycle(self.context, self.api, execute=True, token='synthetic-secret')
        self.assertEqual(result['newly_submitted'], 0); self.assertEqual(len(result['awaiting_collection']), 1)
        self.assertEqual(self.api.run_job.call_count, 1)

    def test_unknown_submission_blocks_all_following_work_without_secret_leak(self):
        self.api.run_job.side_effect = TimeoutError('synthetic-secret')
        with self.assertRaises(dispatch.SubmissionUncertain), manager.operation(self.context):
            manager.cycle(self.context, self.api, execute=True, token='synthetic-secret')
        with self.assertRaisesRegex(ValueError, 'Stopped final run'), manager.operation(self.context): pass
        self.assertEqual(self.api.run_job.call_count, 1)
        self.assertNotIn('synthetic-secret', (self.out/'halt.json').read_text())

    def test_duplicate_original_handle_is_rejected_before_status_or_submission(self):
        launches = self.seed(2); second = launches[1]; second['job_id'] = launches[0]['job_id']
        manager.durable_write(self.out/'dispatch/jobs'/(second['name']+'.json'), second)
        self.api.reset_mock()
        with self.assertRaisesRegex(ValueError, 'Duplicate original handles'): manager.cycle(self.context, self.api, execute=True)
        self.api.inspect_job.assert_not_called(); self.api.run_job.assert_not_called()

    def test_read_only_status_failure_stops_without_restarting_or_replacing(self):
        self.seed(); self.api.run_job.reset_mock(); self.api.inspect_job.side_effect = ConnectionError('synthetic-secret')
        # The deliberately seeded ledger needs its original context for this test.
        manager.durable_write(self.out/'admitted-context.json', self.context, exclusive=True)
        with self.assertRaises(ConnectionError), manager.operation(self.context):
            manager.cycle(self.context, self.api, execute=True)
        self.api.run_job.assert_not_called()
        self.assertEqual(manager.read(self.out/'halt.json')['failure_type'], 'ConnectionError')

    def test_stop_marker_and_competing_operation_block(self):
        self.out.mkdir(); (self.out/'STOP').write_text('explicit stop')
        with self.assertRaisesRegex(ValueError, 'Stopped final run'), manager.operation(self.context): pass
        (self.out/'STOP').unlink()
        with manager.operation(self.context):
            with self.assertRaises(BlockingIOError), manager.operation(self.context): pass

    def test_changed_frozen_input_blocks_submission(self):
        self.out.mkdir(); (self.root/'pin').write_text('changed')
        with self.assertRaisesRegex(ValueError, 'Changed evidence file'): manager.cycle(self.context, self.api, execute=True)
        self.api.run_job.assert_not_called()

    def test_all_320_collections_preserve_game_total_without_qualification(self):
        directory = self.out/'dispatch/jobs'; directory.mkdir(parents=True)
        manager.durable_write(directory.parent/'release.json', self.f.release, exclusive=True)
        for i, row in enumerate(self.f.release['plan']['rows']):
            manager.durable_write(directory/(row['name']+'.json'), {'stage': 'launched',
                'name': row['name'], 'job_id': f'{i:024x}', 'row': row,
                'release_sha256': manager.object_hash(self.f.release)}, exclusive=True)
        with patch.object(manager, 'collected', side_effect=lambda context, launch: {
                'name': launch['name'], 'games': launch['row']['shard']['games']}):
            result = manager.cycle(self.context, self.api, execute=True)
        self.assertTrue(result['complete']); self.assertEqual(result['verified_jobs'], 320)
        self.assertEqual(result['completed_games'], 20160); self.assertFalse(result['qualified'])
        self.api.inspect_job.assert_not_called(); self.api.run_job.assert_not_called()
        self.assertTrue((self.out/'collection-results.json').exists())


class OriginalCollectionTests(unittest.TestCase):
    def setUp(self):
        self.f = collection_fixtures.FinalCollectionTests(); self.f.setUp(); self.addCleanup(self.f.doCleanups)
        self.stack = ExitStack(); self.addCleanup(self.stack.close)
        self.out = self.f.root/'manager'; self.stack.enter_context(patch.object(manager, 'OUT', self.out))
        self.stack.enter_context(patch.object(manager, 'check_pins'))
        self.stack.enter_context(patch.object(manager, 'hf_hub_download', return_value=str(self.f.archive)))
        self.stack.enter_context(patch.object(collector, 'artifact_identity', return_value=self.f.identity))
        self.stack.enter_context(patch.object(collector, 'audit_shard', return_value=deepcopy(self.f.audit)))
        self.context = {'source_root': str(self.f.source), 'release': self.f.release, 'bootstrap': self.f.bootstrap}
        self.api = Mock(); self.api.fetch_job_logs.return_value = [json.dumps({'evidence': self.f.evidence})]
        self.directory = self.out/'originals'/self.f.name; self.directory.mkdir(parents=True)
        self.observed = {'name': self.f.name, 'job_id': self.f.launch['job_id'], 'stage': 'COMPLETED'}

    def test_real_streaming_collection_preserves_original_and_binds_saved_audit(self):
        saved = manager.collect_one(self.context, self.api, self.f.launch, self.observed)
        self.assertEqual(saved['games'], self.f.row['shard']['games'])
        self.assertEqual(manager.digest(self.directory/'original.tgz'), self.f.evidence['archive_sha256'])
        self.assertEqual(saved, manager.collected(self.context, self.f.launch))
        self.assertFalse(list((self.out/'scratch').glob('original-final-audit-*')))
        self.api.run_job.assert_not_called()

    def test_terminal_failure_keeps_downloaded_original_and_does_not_audit_or_retry(self):
        with patch.object(manager, 'audit_archive') as audit:
            with self.assertRaisesRegex(ValueError, 'Original job failed'):
                manager.collect_one(self.context, self.api, self.f.launch, {**self.observed, 'stage': 'ERROR'})
            audit.assert_not_called()
        self.assertTrue((self.directory/'original.tgz').exists()); self.assertTrue((self.directory/'failure.json').exists())
        with self.assertRaisesRegex(ValueError, 'interrupted original collection'):
            manager.collect_one(self.context, self.api, self.f.launch, self.observed)
        self.assertEqual(self.api.fetch_job_logs.call_count, 1); self.api.run_job.assert_not_called()

    def test_duplicate_archive_receipts_preserve_log_and_fail_before_download(self):
        self.api.fetch_job_logs.return_value *= 2
        with patch.object(manager, 'hf_hub_download') as download:
            with self.assertRaisesRegex(ValueError, 'ambiguous original evidence'):
                manager.collect_one(self.context, self.api, self.f.launch, self.observed)
            download.assert_not_called()
        self.assertTrue((self.directory/'job.log').exists())

    def test_changed_saved_audit_is_not_silently_reused(self):
        manager.collect_one(self.context, self.api, self.f.launch, self.observed)
        (self.directory/'review.json').write_text('{}')
        with self.assertRaisesRegex(ValueError, 'Collected original binding changed'):
            manager.collected(self.context, self.f.launch)


if __name__ == '__main__': unittest.main()
