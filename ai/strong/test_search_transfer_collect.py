"""Admission rejects changes to real complete-game contracts and outcomes."""
import copy
import unittest
from search_transfer import ROOT,PROTOCOL,read,verify


class Contracts(unittest.TestCase):
    def test_real_raw_baseline_and_invalid_conditions(self):
        protocol=read(PROTOCOL);case=protocol['cases'][0]
        raw=read(ROOT/'ai/runs/discard-opponents-verified-v1/parent-2p/heuristic.json')
        self.assertEqual(verify(raw,protocol,'parent',case,False)['games'],128)
        with self.assertRaises(AssertionError):verify(raw,protocol,'parent',case,True)
        for fault in ['budget','model','missing','cap','reference','seed','search-cap']:
            bad=copy.deepcopy(raw)
            if fault=='budget':bad['candidate_search_samples']=16
            elif fault=='model':bad['model_sha256']='wrong'
            elif fault=='missing':bad['results'].pop()
            elif fault=='cap':bad['results'][0]['truncated']=True
            elif fault=='reference':bad['opponent']='rush'
            elif fault=='seed':bad['results'][0]['gameSeed']='unprescribed'
            else:bad['results'][0]['searchStats']={'learner':{'decisions':1,'evaluations':48,'truncated':1}}
            with self.subTest(fault=fault),self.assertRaises((AssertionError,ValueError)):
                verify(bad,protocol,'parent',case,False)


if __name__=='__main__':unittest.main()
