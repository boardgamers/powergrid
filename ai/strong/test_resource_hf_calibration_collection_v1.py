"""Incomplete or mismatched endpoints must not become calibration evidence."""
import copy
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from strategic_collection import ROOT, read, write

spec = importlib.util.spec_from_file_location('full_resource_calibration', Path(__file__).with_name('collect-resource-hf-calibration-v1.py'))
collector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(collector)


class CalibrationCollectionTest(unittest.TestCase):
    def records(self):
        # Synthetic HF-shaped envelopes around actual complete local counts.
        # These fixtures are not remote performance/parity evidence.
        pilot = read(ROOT / 'ai/strong/resource-replanning-runtime-evidence-v1.json')
        records = {}
        for n in (2, 6):
            cell = pilot['cells'][f'{n}p-resource-filter']
            counts = cell['summary']['counts']
            records[n] = {'job_id': f'synthetic-{n}', 'source': {'test_only': True},
                          'admission_sha256': 'test-only', 'local_pilot_descriptor_sha256': 'test-only',
                          'code_hashes': {}, 'verified': True, 'authoritative_status': 'COMPLETED',
                          'case': f'resource-replanning-hf-runtime-v1-{n}p-resource-filter',
                          'strength_eligible': False, 'qualification_eligible': False,
                          'reserved_final_seeds_used': False, 'new_strength_games': 0,
                          'summary': copy.deepcopy(cell['summary']), 'runtime': cell['runtime'],
                          'parity': {'exact': True, 'games': 4 * n, 'learner_decisions': counts['decisions'],
                                     'resource_decisions': counts['resource_search_decisions'], 'resource_rollouts': counts['rollouts']},
                          'resource_latency': {'count': counts['resource_search_decisions']},
                          'evidence': {'remote_archive_verified': True, 'test_only': True}}
        return records

    def test_complete_aggregate_preserves_all_counts(self):
        result = collector.summarize(self.records())
        self.assertEqual(result['games'], 32)
        self.assertEqual(result['resource_decisions'], 1228)
        self.assertFalse(result['development_admitted'])
        self.assertFalse(result['qualification_eligible'])

    def test_missing_endpoint_does_not_inspect_or_upload(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(collector.endpoint, 'COLLECTED', Path(tmp)), \
                patch.object(collector.endpoint, 'collect') as collect, patch.object(collector, 'upload_evidence') as upload:
            for present in (False, True):
                if present:
                    path = Path(tmp) / 'resource-replanning-hf-runtime-v1-2p-resource-filter'
                    path.mkdir()
                    write(path / 'verified.json', self.records()[2])
                with self.assertRaisesRegex(AssertionError, 'both completed'):
                    collector.main(True)
                collect.assert_not_called()
                upload.assert_not_called()

    def test_rejects_incomplete_or_inconsistent_results(self):
        edits = {
            'missing': lambda rows: rows.pop(6),
            'duplicate_job': lambda rows: rows[6].update(job_id=rows[2]['job_id']),
            'wrong_source': lambda rows: rows[6].update(source={'changed': True}),
            'running': lambda rows: rows[6].update(authoritative_status='RUNNING'),
            'wrong_admission': lambda rows: rows[6].update(admission_sha256='different'),
            'parity_failed': lambda rows: rows[6]['parity'].update(exact=False),
            'wrong_games': lambda rows: rows[6]['summary'].update(games=23),
            'caps': lambda rows: rows[6]['summary']['counts'].update(rollout_caps=1),
            'wrong_rollouts': lambda rows: rows[6]['parity'].update(resource_rollouts=0),
            'strength_claim': lambda rows: rows[6].update(strength_eligible=True),
        }
        for name, edit in edits.items():
            with self.subTest(name=name):
                records = self.records()
                edit(records)
                with self.assertRaises(AssertionError):
                    collector.summarize(records)


if __name__ == '__main__':
    unittest.main()
