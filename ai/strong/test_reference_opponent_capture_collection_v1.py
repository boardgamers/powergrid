"""Validate archived-ready real capture rows and reject privacy/target corruption."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('capture_collector', Path(__file__).with_name('collect-reference-opponent-capture-v1.py'))
collector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(collector)


class CaptureCollectionTest(unittest.TestCase):
    def test_complete_real_two_player_case(self):
        folder = collector.RUN / '2p-0'
        result = collector.audit_case(folder, 2, 0, collector.read(folder / 'verified.json'))
        self.assertEqual(result['teacher_rows'], 50)
        self.assertEqual(result['public_replays'], 6)

    def test_privacy_and_teacher_corruptions(self):
        with (collector.RUN / '2p-0/opponent-decisions.jsonl').open() as stream:
            row = json.loads(stream.readline())
        collector.verify_row(row, 0, 2, 0)
        edits = [lambda r:r.update(target=len(r['observation']['moves'])),
                 lambda r:r['request']['state'].update(powerPlantsDeck=[{'number':3}]),
                 lambda r:r['request']['state'].update(hiddenLog=[{'secret':True}]),
                 lambda r:r['request']['state']['players'][0].update(bid=1),
                 lambda r:r['request']['state']['options'].update(showMoney=False),
                 lambda r:r['observation']['state'].__setitem__(0, float('nan')),
                 lambda r:r['teacher']['options'].update(samples=8),
                 lambda r:r['teacher']['result'].update(truncated=1),
                 lambda r:r['teacher']['result'].update(winEstimate=2),
                 lambda r:r.update(qualification_eligible=True)]
        for edit in edits:
            bad = copy.deepcopy(row)
            edit(bad)
            with self.assertRaises(AssertionError):
                collector.verify_row(bad, 0, 2, 0)

    def test_partial_probe_never_uploads_or_creates_archive(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            collector.write(root / 'status.json', {'stage':'running'})
            with patch.object(collector, 'RUN', root), patch.object(collector, 'upload_evidence') as upload:
                for archive in (False, True):
                    with self.assertRaisesRegex(AssertionError, 'all twenty'):
                        collector.main(archive)
                upload.assert_not_called()
                self.assertEqual([p.name for p in root.iterdir()], ['status.json'])


if __name__ == '__main__':
    unittest.main()
