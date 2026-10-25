"""Independent complete-cost evidence boundary and shared-prior accounting."""
from copy import deepcopy
from fractions import Fraction
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from strategic_collection import ROOT, read

spec = importlib.util.spec_from_file_location('cost_archive_test', ROOT/'ai/strong/collect-surrogate-continuation-cost-evidence-v1.py')
archive = importlib.util.module_from_spec(spec); spec.loader.exec_module(archive)


class EvidenceTests(unittest.TestCase):
    def test_independent_tie_credit_checks_final_scores(self):
        row = {'truncated': False, 'value': 1/3, 'diagnostic': {'terminal': [
            {'powered': 16, 'money': 21, 'cities': 16} for _ in range(3)]}}
        self.assertEqual(archive.independent_credit(row, 2, 3), Fraction(1, 3))
        for field in ('value', 'terminal'):
            bad = deepcopy(row)
            if field == 'value': bad['value'] = 1
            else: bad['diagnostic']['terminal'][2]['cities'] = 15
            with self.assertRaises(AssertionError): archive.independent_credit(bad, 2, 3)

    def test_actual_reference_records_and_shared_prior_accounting(self):
        folder = ROOT/'ai/runs/surrogate-continuation-cost-collected-v1'
        checked = 0
        for path in folder.glob('*/artifacts/reference_opponent_v1/result.json'):
            result = read(path); intent = read(path.parent/'intent.json'); root = read(path.parent/'root.json')
            q = root['identity']
            for row in result['rows']: archive.independent_credit(row, q['seat'], q['players']); checked += 1
            work = archive.work_counts(result, intent['workers'])
            self.assertEqual(work['row_attributed_prior_evaluations'], 2*work['prior_evaluations_once_per_worker_world'])
            bad = deepcopy(result); bad['rows'][1]['diagnostic']['priorSearchStats']['evaluations'] += 1
            with self.assertRaises(AssertionError): archive.work_counts(bad, intent['workers'])
        self.assertGreaterEqual(checked, 16*8)

    def test_partial_calibration_cannot_create_archive(self):
        with tempfile.TemporaryDirectory() as temp:
            missing = Path(temp)/'missing-index.json'
            with patch.object(archive.manager, 'INDEX', missing), patch.object(archive, 'upload_evidence') as upload:
                with self.assertRaisesRegex(AssertionError, 'All 24'): archive.main(True)
                upload.assert_not_called()


if __name__ == '__main__': unittest.main()
