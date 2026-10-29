"""Mutation checks against an actual pilot result; no simulation."""
import copy
import unittest
from collect_auction_discount_teacher_v1 import OUT, PROTOCOL, audit, read, digest


class PilotAuditTests(unittest.TestCase):
    def setUp(self):
        self.root = read(OUT/'roots/000/root.json')
        self.result = read(OUT/'roots/000/result.json')

    def check(self):
        return audit(self.root, self.result, digest(PROTOCOL))

    def test_actual_complete_result(self):
        self.assertEqual(self.check()['rollouts'], 28)

    def test_changed_terminal_credit_rejected(self):
        self.result['continuations']['rows'][0]['value'] = 0.123
        with self.assertRaises(AssertionError): self.check()

    def test_unpaired_world_rejected(self):
        self.result['continuations']['rows'][1]['diagnostic']['sampledWorldSha256'] = '0'*64
        with self.assertRaises(AssertionError): self.check()

    def test_missing_action_rejected(self):
        self.result['continuations']['rows'].pop()
        with self.assertRaises(AssertionError): self.check()

    def test_wrong_margin_rejected(self):
        self.result['exact_summary']['pairedMeanMargins']['0'] = '99'
        with self.assertRaises(AssertionError): self.check()

    def test_wrong_source_root_rejected(self):
        self.root['request']['player'] ^= 1
        with self.assertRaises(AssertionError): self.check()

    def test_capped_result_rejected(self):
        self.result['continuations']['rows'][0]['truncated'] = True
        with self.assertRaises(AssertionError): self.check()


if __name__ == '__main__': unittest.main()
