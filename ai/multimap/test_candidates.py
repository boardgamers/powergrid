import copy
import unittest
from unittest.mock import patch
import torch
from candidates import EqualLogitEnsemble,POOL,load_candidates
from data import Bridge
from residual import ResidualPolicy,row,batch
from rollout import plans


class CandidateTests(unittest.TestCase):
    def test_frozen_members_and_rejected_names(self):
        self.assertEqual([p['update'] for p in POOL['members']],[8,16,12])
        self.assertEqual(POOL['ensemble']['weights'],[1,1,1])
        with patch('candidates.hf_hub_download') as download:
            for names in ([],['unknown'],['ppo0','ppo0']):
                with self.assertRaises(ValueError):load_candidates(names)
            download.assert_not_called()

    def test_mean_mask_bounds_and_action_permutation(self):
        torch.set_num_threads(1);torch.manual_seed(508)
        bridge=Bridge('game_rl.cjs')
        try:r=row(bridge.call({'op':'start','spec':plans('smoke')[0]})['observation'])
        finally:bridge.close()
        members=[ResidualPolicy(16) for _ in range(3)]
        with torch.no_grad():
            for i,m in enumerate(members):m.network.action[-1].weight.fill_((i-1)*.03)
        ensemble=EqualLogitEnsemble(members).eval();b=batch([r])
        x=ensemble(b);individual=[m(b) for m in members]
        torch.testing.assert_close(x[0],torch.stack([a[0] for a in individual]).mean(0))
        self.assertTrue(((x[0][0]-r['prior']).abs()<=8+1e-5).all())
        perm=torch.randperm(len(r['actions']));other=copy.deepcopy(r)
        for k in ('actions','actionCity','prior','targets'):other[k]=r[k][perm]
        torch.testing.assert_close(x[0][:,perm],ensemble(batch([other]))[0])
        for k in ('actions','actionCity','prior','targets'):other[k]=torch.cat([other[k],other[k]])
        padded=ensemble(batch([r,other]))[0]
        torch.testing.assert_close(x[0][0],padded[0,:len(r['actions'])])
        self.assertTrue((padded[0,len(r['actions']):]==-1e9).all())
        with self.assertRaises(ValueError):EqualLogitEnsemble([])
        with self.assertRaises(ValueError):EqualLogitEnsemble([ResidualPolicy(16),ResidualPolicy(32)])


if __name__=='__main__':unittest.main()
