"""Prevent duplicate execution across backends and misleading progress counts."""
from pathlib import Path
import tempfile
import json
import sys
from types import SimpleNamespace
from unittest.mock import patch
import unittest
from manage_nomination_minipc_v1 import unclaimed
from run_nomination_minipc_v1 import progress
import manage_nomination_minipc_batch_v1 as batch


class ReservationTests(unittest.TestCase):
    def test_each_existing_claim_rejects_launch(self):
        for suffix in ('.json', '.intent.json', '.minipc.intent.json'):
            with self.subTest(suffix=suffix), tempfile.TemporaryDirectory() as d:
                folder = Path(d); (folder/('original'+suffix)).write_text('{}')
                with self.assertRaises(AssertionError): unclaimed(folder, 'original')

    def test_unrelated_claim_does_not_block(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d); (folder/'other.intent.json').write_text('{}')
            unclaimed(folder, 'original')

    def test_progress_is_distinct_completed_games(self):
        log = '\n'.join(['noise', '{"episode":2,"complete":1,"expected":32}',
            '{"episode":2,"complete":1,"expected":32}', '{"episode":0,"complete":2,"expected":32}',
            '{"complete":true,"games":32}', '{"episode":'])
        self.assertEqual(progress(log), {'completed_games': 2, 'expected_games': 32})

    def test_empty_progress_does_not_claim_games(self):
        self.assertEqual(progress(''), {'completed_games': 0, 'expected_games': None})

    def test_queue_stops_on_first_failure_without_retrying(self):
        calls = []
        def run(root, name):
            calls.append(name)
            if len(calls) == 2: raise RuntimeError('Preserved original failure')
        fake = SimpleNamespace(checked=lambda root: ({'authorized_names': batch.NAMES}, {}), run=run)
        with tempfile.TemporaryDirectory() as d, patch.dict(sys.modules, worker=fake), patch.object(sys, 'path', sys.path.copy()):
            root = Path(d); (root/'ready.json').write_text(json.dumps({'contract_validations': batch.NAMES}))
            with self.assertRaisesRegex(RuntimeError, 'Preserved original'): batch.remote_run(root)
            self.assertEqual(calls, batch.NAMES[:2])
            state = json.loads((root/'state.json').read_text())
            self.assertEqual(state['stage'], 'failed')
            self.assertEqual(state['completed_shards'], batch.NAMES[:1])


if __name__ == '__main__': unittest.main()
