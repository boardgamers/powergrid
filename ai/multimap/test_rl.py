import copy
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
import torch
from data import Bridge
from residual import ResidualPolicy, PROTOCOL, row, batch, save, load
from rollout import plans, collect
from ppo import optimize, eligible, run


class ResidualTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(1);torch.manual_seed(508)
        bridge=Bridge('game_rl.cjs')
        try:
            state=bridge.call({'op':'start','spec':plans('smoke')[0]})
            cls.example=row(state['observation'])
        finally:bridge.close()

    def test_zero_prior_padding_bounds_and_permutations(self):
        a=copy.deepcopy(self.example);model=ResidualPolicy(16)
        logits,value=model(batch([a]))
        self.assertTrue(torch.equal(logits[0],a['prior']))
        self.assertTrue(((value>=0)&(value<=1)).all())
        with torch.no_grad():model.network.action[-1].weight.fill_(.02)
        b=copy.deepcopy(a);perm=torch.randperm(len(a['actions']))
        for k in ('actions','actionCity','targets','prior'):b[k]=a[k][perm]
        x=model(batch([a]));y=model(batch([b]))
        torch.testing.assert_close(x[0][:,perm],y[0])
        self.assertTrue(((x[0][0]-a['prior']).abs()<=model.bound).all())
        node_perm=torch.randperm(len(a['nodes']));inverse=torch.argsort(node_perm)
        b=copy.deepcopy(a);b['nodes']=a['nodes'][node_perm];b['relations']=a['relations'][:,node_perm][:,:,node_perm]
        b['actionCity']=torch.where(a['actionCity']>=0,inverse[a['actionCity'].clamp_min(0)],a['actionCity'])
        torch.testing.assert_close(x[0],model(batch([b]))[0],atol=1e-6,rtol=1e-5)
        b=copy.deepcopy(a)
        for k in ('actions','actionCity','targets','prior'):b[k]=torch.cat([b[k],b[k]])
        padded=model(batch([a,b]))
        torch.testing.assert_close(padded[0][0,:len(a['actions'])],x[0][0])
        self.assertTrue((padded[0][0,len(a['actions']):]==-1e9).all())

    def test_splits_and_selection_floor(self):
        train=plans('train',1);later=plans('train',2);selection=plans('selection');confirmation=plans('confirmation')
        groups=[{s['seed'] for s in x} for x in (train,later,selection,confirmation)]
        for i,a in enumerate(groups):
            for b in groups[i+1:]:self.assertFalse(a&b)
        self.assertEqual(len(train),80);self.assertEqual(len(selection),320);self.assertEqual(len(confirmation),960)
        with patch.dict(PROTOCOL,{'gamesPerCellPerUpdate':2}):self.assertEqual(len(plans('train',1)),160)
        self.assertTrue(all(s['map'] in PROTOCOL['trainMaps'] for s in train+selection))
        with self.assertRaises(ValueError):plans('final')
        self.assertFalse(eligible(dict(failures=0,maps={'a':.2}),dict(maps={'a':.5})))
        self.assertFalse(eligible(dict(failures=1,maps={'a':1}),dict(maps={'a':.5})))

    def test_real_rollout_weights_logprobs_and_gradients(self):
        model=ResidualPolicy(16)
        tasks=[dict(s,seed=s['seed'].replace(':train:',':unit-rollout:')) for s in plans('train',1)[:2]]
        rows,games=collect(model,tasks,workers=2,training=True,seed=39)
        self.assertEqual(len(games),2)
        self.assertAlmostEqual(sum(r['weight'] for r in rows),2)
        self.assertTrue(all(r['return'] in [g['credit'] for g in games] for r in rows))
        for selected in (rows[:5],rows[-5:]):
            logits,_=model(batch(selected));logps=logits.log_softmax(-1)
            for i,r in enumerate(selected):self.assertAlmostEqual(float(logps[i,r['chosen']].detach()),r['oldLog'],places=5)
        optimizer=torch.optim.AdamW(model.parameters(),lr=PROTOCOL['learningRate'])
        before=copy.deepcopy(model.state_dict())
        result=optimize(model,optimizer,rows,1)
        self.assertGreater(result['optimizerSteps'],0)
        self.assertTrue(all(torch.isfinite(p).all() for p in model.parameters()))
        self.assertTrue(any(not torch.equal(before[k],v) for k,v in model.state_dict().items()))

    def test_caps_and_ram_budget_fail_without_rewards(self):
        model=ResidualPolicy(16);task=plans('train',1)[0]
        with self.assertRaisesRegex(RuntimeError,'capped'):
            collect(model,[dict(task,maxSteps=1)],workers=1,training=True)
        with patch.dict(PROTOCOL,{'maxRolloutRows':1}), self.assertRaises(MemoryError):
            collect(model,[task],workers=1,training=True)

    def test_exact_interrupted_smoke_resume(self):
        torch.manual_seed(508);base=ResidualPolicy(16)
        with tempfile.TemporaryDirectory() as temp, patch('ppo.warm_start',side_effect=lambda _:copy.deepcopy(base)):
            root=Path(temp)
            run('unused',root/'full',smoke=True)
            def interrupt(stage):
                if stage=='update-1':raise RuntimeError('simulated interruption')
            with self.assertRaisesRegex(RuntimeError,'simulated interruption'):
                run('unused',root/'resume',smoke=True,callback=interrupt)
            # Simulate an interrupted next update: best replaced but last not
            # yet committed. Recovery must undo it using last's embedded bytes.
            save(root/'resume/best.pt',base,update=999)
            run('unused',root/'resume',smoke=True)
            a=torch.load(root/'full/last.pt',weights_only=True)
            b=torch.load(root/'resume/last.pt',weights_only=True)
            for k in a['state_dict']:torch.testing.assert_close(a['state_dict'][k],b['state_dict'][k],atol=0,rtol=0)
            self.assertEqual(a['bestUpdate'],b['bestUpdate'])
            self.assertTrue(a['optimizer']['state'])
            best_a,meta_a=load(root/'full/best.pt');best_b,meta_b=load(root/'resume/best.pt')
            self.assertEqual(meta_a['update'],meta_b['update'])
            for k,v in best_a.state_dict().items():torch.testing.assert_close(v,best_b.state_dict()[k],atol=0,rtol=0)


if __name__=='__main__':unittest.main()
