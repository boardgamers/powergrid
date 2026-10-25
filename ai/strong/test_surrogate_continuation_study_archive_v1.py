"""Independent outcome accounting and complete-corpus archival boundaries."""
from copy import deepcopy
from fractions import Fraction
import importlib.util
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from strategic_collection import ROOT, read

spec = importlib.util.spec_from_file_location('study_archive_test', ROOT/'ai/strong/archive-surrogate-continuation-study-v1.py')
a = importlib.util.module_from_spec(spec); spec.loader.exec_module(a)


class ArchiveTests(unittest.TestCase):
    def test_lexicographic_score_and_fractional_ties_recomputed(self):
        players = [{'powered': 9, 'money': 30, 'cities': 10}, {'powered': 9, 'money': 30, 'cities': 10},
                   {'powered': 8, 'money': 100, 'cities': 14}]
        row = {'truncated': False, 'value': .5, 'diagnostic': {'terminal': players}}
        self.assertEqual(a.terminal_credit(row, 0, 3), Fraction(1, 2))
        row['value'] = 0; self.assertEqual(a.terminal_credit(row, 2, 3), 0)
        row['value'] = 1
        with self.assertRaises(AssertionError): a.terminal_credit(row, 2, 3)
        players[0]['powered'] = 11
        with self.assertRaises(AssertionError): a.terminal_credit(row, 0, 3)

    def test_all_48_saved_engine_outcomes_and_capped_rows(self):
        folder = ROOT/'ai/runs/surrogate-continuation-job-preflight-v1'
        count = 0; last = None
        for mode in a.manager.job.MODES:
            root = read(folder/mode/'root.json'); q = root['identity']
            for row in read(folder/mode/'result.json')['rows']:
                self.assertIsNotNone(a.terminal_credit(row, q['seat'], q['players'])); count += 1; last = row
        self.assertEqual(count, 48)
        row = deepcopy(last); row.update(truncated=True, value=None); row['diagnostic']['terminal'] = None
        self.assertIsNone(a.terminal_credit(row, 0, 2))
        row['value'] = 0
        with self.assertRaises(AssertionError): a.terminal_credit(row, 0, 2)

    def test_partial_study_cannot_create_output_or_upload(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            with patch.object(a.manager, 'INDEX', root/'missing.json'), patch.object(a, 'OUT', root/'archive'), patch.object(a, 'upload_evidence') as upload:
                with self.assertRaisesRegex(AssertionError, 'all 480 original'): a.main(True)
                upload.assert_not_called(); self.assertFalse((root/'archive').exists())


if __name__ == '__main__': unittest.main()
