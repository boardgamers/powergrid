import unittest
import json
import tempfile
from pathlib import Path
from types import SimpleNamespace
import numpy as np
from train_nomination_discount_v1 import metrics
from collect_auction_discount_teacher_v2 import metadata
from collect_nomination_training_v1 import independent_metrics, snapshot


class TrainingTests(unittest.TestCase):
    def test_bounded_status_can_be_refreshed(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'state.json'
            snapshot(path,{'stage':'SCHEDULING'})
            snapshot(path,{'stage':'RUNNING'})
            self.assertEqual(json.loads(path.read_text()),{'stage':'RUNNING'})
            self.assertEqual([p.name for p in Path(folder).iterdir()],['state.json'])
    def setUp(self):
        self.d={'proposal_index':np.array([0]),'mask':np.array([[True,True,True,False]]),
            'old_mask':np.array([[True,True,False,False]]),'target':np.array([[0.,-.2,.3,0.]]),
            'target_a':np.array([[0.,-.1,.2,0.]]),'target_b':np.array([[0.,-.3,.4,0.]]),
            'precision':np.ones((1,4))}
    def test_zero_correction_keeps_parent(self):
        r=metrics(np.zeros((1,4)),self.d,np.array([0]),True,.025)
        self.assertEqual(r['changes'],0);self.assertAlmostEqual(r['mean_simulated_regret'],.3)
    def test_all_legal_can_use_previously_missing_action(self):
        scores=np.array([[0.,-.2,.3,99.]])
        all_=metrics(scores,self.d,np.array([0]),True,.025);old=metrics(scores,self.d,np.array([0]),False,.025)
        self.assertEqual(all_['changes'],1);self.assertEqual(old['changes'],0)
        self.assertAlmostEqual(all_['mean_simulated_regret'],0.)
    def test_negative_change_reported(self):
        r=metrics(np.array([[0.,1.,0.,0.]]),self.d,np.array([0]),True,.025)
        self.assertEqual(r['negative_changes'],1);self.assertLess(r['mean_simulated_advantage'],0)
    def test_independent_audit_penalizes_disagreeing_seeds(self):
        scores=np.array([[[0.,0.,.1,99.]],[[0.,0.,.1,99.]],[[0.,0.,.1,99.]],[[0.,0.,-.3,99.]]])
        r=independent_metrics(scores,self.d,np.array([0]),True,.025)
        self.assertEqual(r['changes'],0)
        self.assertAlmostEqual(r['mean_simulated_regret'],.3)
    def test_independent_audit_records_negative_selected_action(self):
        scores=np.repeat(np.array([[[0.,1.,0.,99.]]]),4,axis=0)
        r=independent_metrics(scores,self.d,np.array([0]),True,.025)
        self.assertEqual(r['changes'],1);self.assertEqual(r['negative_changes'],1)
        self.assertAlmostEqual(r['mean_simulated_advantage'],-.2)
    def test_independent_audit_coverage_masks(self):
        scores=np.repeat(np.array([[[0.,-.2,.3,99.]]]),4,axis=0)
        old=independent_metrics(scores,self.d,np.array([0]),False,.025)
        full=independent_metrics(scores,self.d,np.array([0]),True,.025)
        self.assertEqual(old['changes'],0);self.assertEqual(full['changes'],1)
        self.assertAlmostEqual(full['mean_simulated_regret'],0)
    def test_bulk_metadata_rejects_changed_xet_identity(self):
        r={'path':'x','xet_hash':'a'*64,'bytes':10}
        api=SimpleNamespace(get_bucket_paths_info=lambda *a:[SimpleNamespace(path='x',xet_hash='b'*64,size=10)])
        with self.assertRaises(AssertionError):metadata(api,[r])
    def test_bulk_metadata_rejects_missing_objects(self):
        api=SimpleNamespace(get_bucket_paths_info=lambda *a:[])
        with self.assertRaises(AssertionError):metadata(api,[{'path':'x'}])
    def test_bulk_metadata_binds_all_objects(self):
        entries=[{'path':str(i),'xet_hash':str(i)*64,'bytes':i} for i in (1,2)]
        api=SimpleNamespace(get_bucket_paths_info=lambda *a:[SimpleNamespace(path=r['path'],xet_hash=r['xet_hash'],size=r['bytes']) for r in entries[::-1]])
        self.assertEqual(set(metadata(api,entries)),{'1','2'})


if __name__=='__main__':unittest.main()
