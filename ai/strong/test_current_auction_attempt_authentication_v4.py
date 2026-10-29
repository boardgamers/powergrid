"""Retain existing provenance attacks and bind explicit failed-attempt history."""
from copy import deepcopy
import unittest
from unittest.mock import patch

import current_auction_attempt_authentication_v4 as a
import test_current_auction_attempt_authentication_v3 as old_tests

old_tests.a = a
BucketBindingTests = old_tests.BucketBindingTests
RoutingTests = old_tests.RoutingTests


class FailureHistoryTests(unittest.TestCase):
    def fixture(self):
        f = BucketBindingTests(); f.setUp()
        prior = [{'job_id': 'd'*24, 'attempt_id': 'old-retained-attempt', 'stage': 'ERROR',
                  'terminal_sha256': 'a'*64, 'log_sha256': 'b'*64}]
        f.reference['backend'] = 'bucket_failed_v3'
        f.controls['admitted_failure_history'] = deepcopy(prior)
        for value in (f.review, f.guard, f.expected['control'], f.receipt['status']):
            value['prior_failed_attempts'] = deepcopy(prior)
        f.expected['control']['reason'] = 'failed_transport_recovery'
        return f

    def test_exact_failure_is_bound_without_erasing_original_status(self):
        f = self.fixture(); before = deepcopy(f.guard)
        self.assertIsNone(f.verify()); self.assertEqual(f.guard, before)
        self.assertEqual(f.review['prior_failed_attempts'][0]['stage'], 'ERROR')

    def test_each_failure_history_copy_must_match_admitted_record(self):
        for field in ('review', 'guard', 'expected', 'receipt', 'controls'):
            f = self.fixture()
            target = getattr(f, field)
            if field == 'expected': target = target['control']
            if field == 'receipt': target = target['status']
            key = 'admitted_failure_history' if field == 'controls' else 'prior_failed_attempts'
            target[key][0]['job_id'] = 'e'*24
            with self.subTest(field=field), self.assertRaises(ValueError): f.verify()

    def test_failure_recovery_cannot_claim_never_submitted(self):
        f = self.fixture(); f.expected['control']['reason'] = 'never_submitted'
        with self.assertRaisesRegex(ValueError, 'failure history'): f.verify()
        f = self.fixture()
        for value in (f.review, f.guard, f.expected['control'], f.receipt['status']):
            value['prior_failed_attempts'] = []
        with self.assertRaisesRegex(ValueError, 'failure history'): f.verify()

    def test_ordinary_backend_cannot_accept_failure_recovery(self):
        f = self.fixture(); f.reference['backend'] = 'bucket_remaining_v3'
        with self.assertRaisesRegex(ValueError, 'failure history'): f.verify()

    def test_routing_cannot_replace_another_original_backend(self):
        plan = a.coverage.actual_plan(); routes = a.prior_routing.actual_routes(plan)
        _, rows = a.failed.plan(); routes[rows[0]['name']] = 'bucket_remaining_v3'
        with patch.object(a.prior_routing, 'actual_routes', return_value=routes):
            with self.assertRaisesRegex(ValueError, 'replace another backend'): a.actual_routes(plan)

    def test_changed_failure_decision_rejected(self):
        plan = a.coverage.actual_plan(); decision = deepcopy(a.read(a.failed.DECISION))
        decision['rows'][0]['prior_failed_attempts'][0]['log_sha256'] = '0'*64
        original = a.read
        with patch.object(a, 'read', side_effect=lambda path: decision if path == a.failed.DECISION else original(path)):
            with self.assertRaisesRegex(ValueError, 'rows/history'): a.actual_routes(plan)


if __name__ == '__main__': unittest.main()
