import copy
import math
import unittest
from audit_opponents import expected_plan,verify,paired_statistics


class OpponentAuditTests(unittest.TestCase):
    def fixture(self):
        protocol=dict(maps=['Germany'],players=[2],variants=['original'],fastBids=[False],opponents=['geographic'],dealsPerCellAndOpponent=4,seedNamespace='audit-unit',maxSteps=4000,policies=['selected','teacher'])
        tasks=expected_plan(protocol)
        records=[dict(t,terminal=True,credit=float(t['spec']['focalSeat']==0),steps=20,rounds=2,decisions=5,featureMs=1.,tensorModelMs=2.,seconds=.1) for t in tasks]
        return tasks,records

    def test_coverage_zero_control_and_determinism(self):
        tasks,records=self.fixture();self.assertEqual(len(verify(records,tasks)),16)
        a=paired_statistics(records,resamples=1000);b=paired_statistics(records,resamples=1000)
        self.assertEqual(a,b)
        self.assertEqual(a['all']['difference'],0)
        self.assertEqual(a['all']['pairedBootstrap95'],[0.,0.])
        self.assertEqual(a['all']['unbiasedStratifiedPairedSE'],0)

    def test_unbiased_cluster_standard_error(self):
        tasks,records=self.fixture()
        for r in records:
            if r['policy']=='selected':r['credit']=[1.,.5,0.,.5][r['spec']['deal']]
        a=paired_statistics(records,resamples=1000)['all']
        self.assertAlmostEqual(a['difference'],0)
        self.assertAlmostEqual(a['unbiasedStratifiedPairedSE'],math.sqrt(1/24))
        self.assertEqual(a['pairedSeats'],8)
        self.assertEqual(a['independentDeals'],4)

    def test_invalid_outcomes_and_missing_pairs_rejected(self):
        tasks,records=self.fixture()
        for rows in (records[:-1],records+[records[0]]):
            with self.assertRaises(RuntimeError):verify(rows,tasks)
        for changes in ({'terminal':False},{'credit':float('nan')},{'credit':-1},{'steps':4001}):
            bad=copy.deepcopy(records);bad[0].update(changes)
            with self.assertRaises(RuntimeError):verify(bad,tasks)
        with self.assertRaises(RuntimeError):paired_statistics(records[:-1],resamples=100)


if __name__=='__main__':unittest.main()
