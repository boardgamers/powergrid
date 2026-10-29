"""Actual 64-world evidence plus rejection of damaged training data."""
import unittest
from prepare_auction_discount_teacher_v1 import ROOT,read,digest
from audit_auction_discount_teacher_v2 import audit


class FullTeacherAuditTests(unittest.TestCase):
    def setUp(self):
        folder=ROOT/'ai/runs/auction-discount-teacher-first-v2/roots/000'
        self.root=read(folder/'root.json');self.result=read(folder/'result.json')
        self.sha=digest(ROOT/'ai/strong/auction-discount-teacher-protocol-v2.json')
        self.identity=read(ROOT/'ai/strong/auction-discount-teacher-preflight-v2.json')['identity']

    def check(self):return audit(self.root,self.result,self.sha,self.identity)

    def test_complete_real_result(self):self.assertEqual(self.check()['rollouts'],448)

    def test_terminal_value_changed(self):
        self.result['continuations']['rows'][0]['value']=.123
        with self.assertRaises(AssertionError):self.check()

    def test_world_changed(self):
        self.result['continuations']['rows'][1]['diagnostic']['sampledWorldSha256']='0'*64
        with self.assertRaises(AssertionError):self.check()

    def test_opponent_role_unpaired(self):
        row=self.result['continuations']['rows'][1];seat=(self.root['request']['player']+1)%self.root['players']
        row['roles'][seat]='rush' if row['roles'][seat]!='rush' else 'economic'
        with self.assertRaises(AssertionError):self.check()

    def test_missing_continuation(self):
        self.result['continuations']['rows'].pop()
        with self.assertRaises(AssertionError):self.check()

    def test_validation_not_training(self):
        self.root['split']='validation' if self.root['split']=='train' else 'train'
        with self.assertRaises(AssertionError):self.check()

    def test_changed_margin(self):
        self.result['exact_summary']['pairedMeanMargins']['0']='99'
        with self.assertRaises(AssertionError):self.check()

    def test_incomplete_continuation(self):
        self.result['continuations']['rows'][0]['truncated']=True
        with self.assertRaises(AssertionError):self.check()


if __name__=='__main__':unittest.main()
