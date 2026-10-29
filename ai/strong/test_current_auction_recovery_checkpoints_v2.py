"""Retention tests with synthetic records/transport; no simulations or inference."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

import current_auction_recovery_checkpoints_v2 as c


def context():
    row = {'players': 2, 'identity': {'policy': 'frozen'},
        'shard': {'players': 2, 'start': 0, 'deals': 1, 'games': 8,
            'seed': 'current-auction-confirmation-v1-2p'}}
    return {'attempt_id': 'test-recovery-v2', 'decision_sha256': 'a'*64,
        'source_descriptor_sha256': 'b'*64, 'original_row': row,
        'original_row_sha256': hashlib.sha256(json.dumps(row, sort_keys=True, separators=(',', ':')).encode()).hexdigest()}


class RetentionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name); self.evaluation = self.root/'evaluation'; self.evaluation.mkdir()
        self.out = self.root/'supervisor'; self.remote = self.root/'mock-remote'; self.remote.mkdir()
        self.ctx = context(); self.upload = Mock(side_effect=self.transport)

    def transport(self, folder):
        # Synthetic transport deliberately copies bytes independently so a killed
        # child's later file loss cannot masquerade as durable retention.
        shutil.copytree(folder, self.remote/folder.name)
        return {'repo': c.REPO, 'revision': 'c'*40, 'archive_path': 'archives/'+folder.name+'.tgz',
            'archive_sha256': 'd'*64, 'manifest_sha256': c.digest(folder/'manifest.json'),
            'remote_archive_verified': True}

    def pair(self, episode=0, directory=None, **changes):
        directory = directory or self.evaluation
        decisions = directory/f'decisions-{episode}.jsonl'
        decisions.write_text('{"decision":1}\n{"decision":2}\n')
        game = {'episode': episode, 'decisions': 2, 'decision_receipt_sha256': c.digest(decisions),
            'public_runtime_identity': self.ctx['original_row']['identity'],
            'terminal': {'episode': episode, 'playerCount': 2, 'gameSeed': 'current-auction-confirmation-v1-2p-'+str(episode//8),
                'seat': episode//4 % 2, 'variant': 'recharged' if episode % 2 else 'original',
                'sealed': episode % 4 < 2, 'truncated': False}, **changes}
        (directory/f'game-{episode}.json').write_text(json.dumps(game))
        return game

    def keeper(self): return c.Checkpoints(self.out, self.ctx, self.upload)

    def test_partial_game_write_waits_then_archives_once(self):
        game = self.pair(); path = self.evaluation/'game-0.json'; path.write_text('{"episode":')
        k = self.keeper(); self.assertIsNone(k.capture(self.evaluation)); self.upload.assert_not_called()
        path.write_text(json.dumps(game)); receipt = k.capture(self.evaluation)
        self.assertEqual(receipt['episodes'], [0]); self.assertFalse(receipt['raw_audited'])
        self.assertFalse(receipt['qualified']); self.assertIsNone(k.capture(self.evaluation, full_recheck=True))
        self.assertEqual(self.upload.call_count, 1)

    def test_unfinished_receipts_wait_for_the_bound_bytes(self):
        self.pair(); p = self.evaluation/'decisions-0.jsonl'; original = p.read_bytes(); p.write_bytes(original[:-4])
        k = self.keeper(); self.assertIsNone(k.capture(self.evaluation)); self.upload.assert_not_called()
        p.write_bytes(original); self.assertEqual(k.capture(self.evaluation)['episodes'], [0])

    def test_concurrent_game_replacement_is_not_sealed(self):
        self.pair(); k = self.keeper(); original = c.copy_stable
        def changing(source, target):
            value = original(source, target)
            if source.name == 'game-0.json': source.write_text(source.read_text()+' ')
            return value
        with patch.object(c, 'copy_stable', side_effect=changing):
            self.assertIsNone(k.capture(self.evaluation))
        self.upload.assert_not_called(); self.assertEqual(k.capture(self.evaluation)['episodes'], [0])

    def test_changed_completed_policy_is_rejected(self):
        self.pair(public_runtime_identity={'policy': 'different'}); k = self.keeper()
        with self.assertRaisesRegex(ValueError, 'Different frozen policy'): k.capture(self.evaluation)
        self.upload.assert_not_called()

    def test_unplanned_episode_is_rejected(self):
        self.pair(8); k = self.keeper()
        with self.assertRaisesRegex(ValueError, 'Unexpected/duplicate'): k.capture(self.evaluation)
        self.upload.assert_not_called()

    def test_symlink_to_receipts_is_rejected(self):
        self.pair(); p = self.evaluation/'decisions-0.jsonl'; p.rename(self.root/'external')
        p.symlink_to(self.root/'external'); k = self.keeper()
        with self.assertRaisesRegex(ValueError, 'never a symlink'): k.capture(self.evaluation)
        self.upload.assert_not_called()

    def test_retained_files_cannot_change_or_be_replaced(self):
        self.pair(); k = self.keeper(); k.capture(self.evaluation)
        p = self.evaluation/'decisions-0.jsonl'; p.write_text(p.read_text()+'\n')
        with self.assertRaisesRegex(ValueError, 'Previously retained file changed'): k.capture(self.evaluation)
        self.assertEqual(self.upload.call_count, 1)

    def test_capped_terminal_evidence_is_retained_not_outcome_filtered(self):
        game = self.pair(rollout_caps=1); game['terminal']['truncated'] = True
        (self.evaluation/'game-0.json').write_text(json.dumps(game)); k = self.keeper()
        receipt = k.capture(self.evaluation); self.assertEqual(receipt['episodes'], [0])
        self.assertFalse(receipt['raw_audited']); self.assertFalse(receipt['qualified'])

    def test_ambiguous_upload_keeps_intent_and_cannot_retry(self):
        self.pair(); k = self.keeper()
        def unknown(folder):
            self.transport(folder)
            raise ConnectionError('Unknown upload response')
        self.upload.side_effect = unknown
        with self.assertRaises(ConnectionError): k.capture(self.evaluation)
        self.assertEqual(len(list(self.out.glob('*.upload-intent.json'))), 1)
        self.assertFalse(list(self.out.glob('*.receipt.json')))
        with self.assertRaisesRegex(ValueError, 'never retry'): k.capture(self.evaluation)
        self.assertEqual(self.upload.call_count, 1)
        with self.assertRaises(FileExistsError): self.keeper()

    def test_unverified_transport_cannot_issue_a_retention_receipt(self):
        self.pair(); k = self.keeper()
        self.upload.side_effect = lambda folder: {**self.transport(folder), 'remote_archive_verified': False}
        with self.assertRaisesRegex(ValueError, 'upload not verified'): k.capture(self.evaluation)
        self.assertFalse(list(self.out.glob('*.receipt.json')))

    def child_command(self):
        fixture = self.root/'fixture'; fixture.mkdir(); self.pair(directory=fixture)
        return [sys.executable, '-B', '-c',
            'import pathlib,shutil,sys,time; src=pathlib.Path(sys.argv[1]); dst=pathlib.Path(sys.argv[2]); '
            '[shutil.copyfile(p,dst/p.name) for p in src.iterdir()]; time.sleep(5)', str(fixture), str(self.evaluation)]

    def test_hard_killed_child_keeps_original_checkpoint_bytes(self):
        command = self.child_command()
        def persist_and_kill(folder):
            evidence = self.transport(folder)
            pid = json.loads((self.out/'child-started.json').read_text())['pid']
            os.kill(pid, signal.SIGKILL)
            return evidence
        self.upload.side_effect = persist_and_kill
        result = c.supervise(command, self.evaluation, self.out, self.ctx, self.upload, .02)
        self.assertEqual(result['child_returncode'], -signal.SIGKILL)
        self.assertEqual(result['retained_episodes'], [0]); self.assertFalse(result['raw_audited'])
        shutil.rmtree(self.evaluation)
        archived = next(self.remote.iterdir()); manifest = json.loads((archived/'manifest.json').read_text())
        self.assertTrue(all(c.digest(archived/name) == sha for name,sha in manifest.items()))
        self.assertTrue((archived/'decisions-0.jsonl').exists()); self.assertEqual(self.upload.call_count, 1)

    def test_upload_failure_stops_live_child_without_restart(self):
        command = self.child_command(); self.upload.side_effect = ConnectionError('Unknown upload')
        with self.assertRaises(ConnectionError):
            c.supervise(command, self.evaluation, self.out, self.ctx, self.upload, .02)
        pid = json.loads((self.out/'child-started.json').read_text())['pid']
        with self.assertRaises(ProcessLookupError): os.kill(pid, 0)
        result = json.loads((self.out/'supervisor-result.json').read_text())
        self.assertEqual(result['stage'], 'stopped_for_inspection'); self.assertFalse(result['qualified'])
        self.assertEqual(self.upload.call_count, 1)

    def test_context_and_original_row_are_bound_before_creating_output(self):
        for changes in ({'original_row_sha256': '0'*64}, {'attempt_id': '../escape'}, {'unexpected': 'not allowed'}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                c.Checkpoints(self.out, {**self.ctx, **changes}, self.upload)
            self.assertFalse(self.out.exists())


if __name__ == '__main__': unittest.main()
