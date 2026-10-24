import copy
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from strategic_collection import read, digest

spec = importlib.util.spec_from_file_location('storage_recovery_test', Path(__file__).with_name('recover-population-hybrid-storage-v1.py'))
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)


class StorageRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.guard = read(r.FAILED / 'original-guard.json')
        self.status = read(r.FAILED / 'job-status.json')
        self.remote = read(r.FAILED / 'remote-artifact-check.json')
        self.report = read(r.FAILED / 'artifacts/evaluation/evaluation.json')
        self.review = {'completed_records': 79, 'failed_episode': 36,
                       'saved_failed_prefix_decisions': 14, 'full_cell_verified': False}

    def gate(self, **changes):
        args = dict(original=self.guard, canonical=self.guard, status=self.status,
                    remote=self.remote, reviewed=self.review, present=False, stage='stopped_with_error')
        args.update(changes)
        r.replacement_allowed(**args)

    def test_actual_partial_records_and_receipts(self):
        checked = r.review_partial()
        self.assertEqual(checked['completed_records'], 79)
        self.assertGreater(checked['completed_decisions_checked'], 1000)
        self.assertFalse(checked['full_cell_verified'])
        self.gate(reviewed=checked)

    def test_partial_contract_rejects_complete_missing_changed_or_capped_reports(self):
        for key, value in [('all_complete', True), ('errors', []), ('completed_games', 80),
                           ('rollout_caps', 1), ('game_caps', 1), ('reserved_final_seeds_used', True)]:
            changed = {**self.report, key: value}
            with self.subTest(key=key), self.assertRaises(AssertionError):
                r.partial_contract(changed, self.guard)
        changed = copy.deepcopy(self.report)
        changed['results'][0]['episode'] = 36
        with self.assertRaises(AssertionError):
            r.partial_contract(changed, self.guard)
        changed = copy.deepcopy(self.report)
        changed['config']['samples'] = 4
        with self.assertRaises(AssertionError):
            r.partial_contract(changed, self.guard)

    def test_gate_rejects_live_unknown_wrong_job_changed_guard_and_missing_evidence(self):
        for stage in ['RUNNING', 'SCHEDULING', 'COMPLETED', 'CANCELED', None]:
            with self.subTest(stage=stage), self.assertRaises(AssertionError):
                self.gate(status={**self.status, 'stage': stage})
        for change in [dict(present=True), dict(stage='waiting_for_jobs'),
                       dict(status={**self.status, 'job_id': 'other'}),
                       dict(canonical={**self.guard, 'created_at': 'changed'}),
                       dict(remote={**self.remote, 'exists': False}),
                       dict(remote={**self.remote, 'path': 'other'}),
                       dict(reviewed={**self.review, 'full_cell_verified': True}),
                       dict(original={**self.guard, 'replaces_job_id': 'previous'},
                            canonical={**self.guard, 'replaces_job_id': 'previous'})]:
            with self.subTest(change=change), self.assertRaises(AssertionError):
                self.gate(**change)

    def test_parity_ignores_only_execution_time_and_receipt_digest(self):
        for record in self.report['results']:
            changed = copy.deepcopy(record)
            changed['seconds'] += 1
            changed['decision_receipt_sha256'] = 'time-dependent'
            r.same_record(record, changed)
            rows = [json.loads(line) for line in (r.FAILED / f"artifacts/evaluation/decisions-{record['episode']}.jsonl").read_text().splitlines()]
            for row in rows:
                r.same_decision(row, {**row, 'elapsedMs': row['elapsedMs'] + 1})
            with self.assertRaises(AssertionError):
                r.same_record(record, {**record, 'decisions': record['decisions'] + 1})
            with self.assertRaises(AssertionError):
                r.same_decision(rows[0], {**rows[0], 'index': rows[0]['index'] + 1})
            searched = next(row for row in rows if row['search'])
            changed = copy.deepcopy(searched)
            option = str(changed['search']['options'][0])
            changed['search']['sampleOutcomes'][option][0] = 0.123456789
            with self.assertRaises(AssertionError):
                r.same_decision(searched, changed)

    def test_coordinator_checks_parity_on_collection_and_saved_receipt(self):
        admission = {'recovery_adapter_sha256': digest(Path(r.__file__)),
                     'recovery_core_sha256': digest(Path(r.core.__file__))}
        for operation in ['collect', 'verified_receipt']:
            fake = SimpleNamespace(manager=SimpleNamespace(
                collect=lambda case: {'case': case, 'verified': True},
                verified_receipt=lambda case: {'case': case, 'verified': True}))
            def main(**kwargs):
                self.assertEqual(kwargs, {'execute': True, 'interval': 300, 'max_hours': 48})
                getattr(fake.manager, operation)('unrelated-case')
                getattr(fake.manager, operation)(r.CASE)
            fake.main = main
            with self.subTest(operation=operation), patch.object(r, 'read', return_value=admission), \
                    patch.object(r, 'module', return_value=fake), \
                    patch.object(r, 'verify_repeated_games', side_effect=AssertionError('parity differs')) as parity:
                with self.assertRaisesRegex(AssertionError, 'parity differs'):
                    r.coordinate()
                parity.assert_called_once_with({'case': r.CASE, 'verified': True})


if __name__ == '__main__':
    unittest.main()
