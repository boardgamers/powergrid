"""Recovery-control tests. Synthetic positive source; no game/job execution."""
from contextlib import ExitStack
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

import current_auction_resource_job_v2 as w


class WorkerControlsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name); self.bundle = self.root/'bundle'; self.source = self.root/'original'
        self.bundle.mkdir(); self.source.mkdir(); self.output = self.root/'execution'
        self.stack = ExitStack(); self.addCleanup(self.stack.close)
        for name, module in [(w.ENTRY, w), (w.CORE, w.retention)]:
            shutil.copyfile(module.__file__, self.bundle/name)
        (self.source/'public_policy_measured_job_v1.py').write_text('original measured worker')
        (self.source/'public_policy_development_job_v1.py').write_text('original development worker')
        (self.source/'candidate.json').write_text('{}'); (self.source/'contract.json').write_text('{}')
        self.write(self.source/'job.json', {'workers': 4, 'candidate': 'candidate.json', 'contract': 'contract.json'})
        source_pins = {p.name: w.digest(p) for p in self.source.iterdir()}
        self.write(self.source/'source-manifest.json', source_pins)
        self.row = {'name': w.FAILED_NAME, 'players': 4, 'job': 'job.json',
            'identity': {'settings': {'workers': 4, 'threads': 1}},
            'shard': {'players': 4, 'start': 5, 'deals': 1, 'games': 16,
                'seed': 'current-auction-confirmation-v1-4p'},
            'job_spec_sha256': w.digest(self.source/'job.json'),
            'candidate_sha256': w.digest(self.source/'candidate.json'),
            'contract_sha256': w.digest(self.source/'contract.json')}
        original = {'rows': [self.row], 'source_manifest_sha256': w.digest(self.source/'source-manifest.json'),
            'measured_entry_sha256': source_pins['public_policy_measured_job_v1.py'],
            'entry_sha256': source_pins['public_policy_development_job_v1.py'],
            'revision': 'c'*40, 'sha256': 'd'*64, 'protocol_sha256': 'e'*64}
        decision = {'original_failed_handle': w.FAILED_HANDLE, 'original_audited_shards': 620,
            'original_audited_games': 19764, 'never_submitted_rows': 323,
            'status': 'resource_recovery_design_recorded_execution_not_admitted',
            'strength_outcomes_used_for_decision': False,
            'fixed_recovery_rows': [{'name': w.FAILED_NAME, 'original_row_sha256': w.object_hash(self.row)}]}
        self.write(self.bundle/'original-source.json', original); self.write(self.bundle/'decision.json', decision)
        self.stack.enter_context(patch.object(w, 'SOURCE_SHA', w.digest(self.bundle/'original-source.json')))
        self.stack.enter_context(patch.object(w, 'DECISION_SHA', w.digest(self.bundle/'decision.json')))
        self.control = {'version': 2, 'scope': 'single_original_failed_shard_technical_recovery',
            'attempt_id': w.ATTEMPT, 'original_name': w.FAILED_NAME, 'original_failed_handle': w.FAILED_HANDLE,
            'original_row_sha256': w.object_hash(self.row), 'allocation': dict(w.ALLOCATION),
            'decision_sha256': w.DECISION_SHA, 'source_descriptor_sha256': w.SOURCE_SHA}
        self.write(self.bundle/'control.json', self.control); self.seal()

    def write(self, path, obj): path.write_text(json.dumps(obj, indent=2)+'\n')

    def seal(self):
        self.write(self.bundle/'manifest.json', {p.name: w.digest(p) for p in self.bundle.iterdir() if p.name != 'manifest.json'})
        self.bundle_sha = w.digest(self.bundle/'manifest.json')

    def inspect(self, **kw): return w.inspect(self.bundle, self.bundle_sha, self.source, self.output, **kw)

    def admission(self, **changes):
        core = self.inspect()['core_files_sha256']
        value = {'passed': True, 'scope': self.control['scope'], 'core_files_sha256': core,
            'control_sha256': w.digest(self.bundle/'control.json'), 'decision_sha256': w.DECISION_SHA,
            'source_descriptor_sha256': w.SOURCE_SHA, 'new_hf_jobs': 0, 'new_games': 0,
            'qualified': False, 'reserved_final_seeds_used': False,
            'preflight_sha256': 'a'*64, 'test_log_sha256': 'b'*64, 'preparation_archive_sha256': 'c'*64, **changes}
        self.write(self.bundle/'admission.json', value); self.seal()

    def test_default_is_validation_without_output_or_execution(self):
        with patch.object(w.retention, 'supervise', side_effect=AssertionError('No execution')) as supervise:
            result = w.run(self.bundle, self.bundle_sha, self.source, self.output)
        self.assertTrue(result['valid']); self.assertFalse(result['execute']); supervise.assert_not_called()
        self.assertFalse(self.output.exists())

    def test_missing_real_admission_blocks_execution(self):
        with self.assertRaisesRegex(ValueError, 'Real prepared-control admission'):
            self.inspect(execute=True)
        self.assertFalse(self.output.exists())

    def test_commands_keep_original_case_and_disable_original_upload(self):
        self.admission(); config = self.inspect(execute=True)
        command = config['command']; dry = config['dry_command']
        self.assertIn(str(self.source/'public_policy_measured_job_v1.py'), command)
        self.assertNotIn('--upload', command); self.assertNotIn('--execute', dry)
        self.assertIn(str(self.source/'public_policy_development_job_v1.py'), dry)
        self.assertEqual(Path(config['raw_output']).name, w.FAILED_NAME)
        self.assertEqual(config['context']['original_row'], self.row)

    def test_other_shard_or_attempt_cannot_be_substituted(self):
        for key,value in [('original_name','other'), ('attempt_id','other'), ('original_failed_handle','f'*24), ('scope','remaining_rows')]:
            with self.subTest(key=key):
                self.write(self.bundle/'control.json', {**self.control, key:value}); self.seal()
                with self.assertRaises(ValueError): self.inspect()
        self.assertFalse(self.output.exists())

    def test_resource_change_is_rejected_even_with_new_control_manifest(self):
        for key,value in [('timeout','3h'), ('game_workers',8), ('search_workers',8), ('inference_threads',4), ('checkpoint_period_seconds',0)]:
            with self.subTest(key=key):
                altered = {**self.control, 'allocation':{**self.control['allocation'],key:value}}
                self.write(self.bundle/'control.json',altered);self.seal()
                with self.assertRaisesRegex(ValueError,'Effective resource controls changed'):self.inspect()

    def test_wrong_row_hash_cannot_bind_changed_identity(self):
        self.write(self.bundle/'control.json',{**self.control,'original_row_sha256':'0'*64});self.seal()
        with self.assertRaisesRegex(ValueError,'Original row changed'):self.inspect()

    def test_changed_original_source_is_rejected(self):
        (self.source/'public_policy_measured_job_v1.py').write_text('modified')
        with self.assertRaisesRegex(ValueError,'Pinned file changed'):self.inspect()

    def test_repacked_foreign_source_descriptor_is_rejected(self):
        original = w.read(self.bundle/'original-source.json');original['revision']='0'*40
        self.write(self.bundle/'original-source.json',original);self.seal()
        with self.assertRaisesRegex(ValueError,'Wrong frozen decision/source'):self.inspect()

    def test_wrong_admission_binding_is_rejected(self):
        self.admission(core_files_sha256='0'*64)
        with self.assertRaisesRegex(ValueError,'does not bind'):self.inspect(execute=True)

    def test_post_execution_or_qualified_admission_is_rejected(self):
        self.admission(new_games=16)
        with self.assertRaisesRegex(ValueError,'must precede execution'):self.inspect(execute=True)

    def test_existing_or_overlapping_output_is_rejected(self):
        self.output.mkdir()
        with self.assertRaisesRegex(ValueError,'never rerun'):self.inspect()
        self.output.rmdir(); self.output=self.source/'new-output'
        with self.assertRaisesRegex(ValueError,'overlaps'):self.inspect()

    def test_extra_or_symlinked_bundle_file_is_rejected(self):
        (self.bundle/'extra').write_text('new')
        with self.assertRaisesRegex(ValueError,'file set changed'):self.inspect()
        (self.bundle/'extra').unlink()
        p=self.bundle/'control.json';p.rename(self.root/'external');p.symlink_to(self.root/'external')
        with self.assertRaisesRegex(ValueError,'escaped|Symlink'):self.inspect()

    def test_changed_supervisor_code_cannot_be_repacked(self):
        with (self.bundle/w.ENTRY).open('a') as stream:stream.write('\n# changed\n')
        self.seal()
        with self.assertRaisesRegex(ValueError,'Supervisor code differs'):self.inspect()

    def test_final_snapshot_keeps_original_manifest_and_bytes(self):
        raw=self.root/'raw';raw.mkdir();(raw/'data').write_text('original bytes')
        self.write(raw/'manifest.json',{'data':w.digest(raw/'data')});before=w.digest(raw/'manifest.json')
        target=self.root/'envelope/raw';w.snapshot_tree(raw,target)
        self.assertEqual(w.digest(target/'manifest.json'),before)
        self.assertEqual(w.digest(target/'data'),w.digest(raw/'data'))
        with self.assertRaises(FileExistsError):w.snapshot_tree(raw,target)


if __name__=='__main__':unittest.main()
