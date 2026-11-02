import copy
import hashlib
import json
import os
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
import torch
from data import Bridge
from residual import ResidualPolicy, PROTOCOL, row, batch, save, load
from rollout import plans, collect
from ppo import config, make_protocol, optimize, eligible, run


class ReplicaProtocolTests(unittest.TestCase):
    def test_only_rng_settings_change_and_copies_are_independent(self):
        frozen=json.loads((Path(__file__).parent/'ppo-protocol-v1.json').read_text())
        self.assertEqual(make_protocol(),frozen)
        self.assertEqual(make_protocol(0),frozen)
        self.assertEqual(config(False),config(False,make_protocol()))
        for replica in (1,2,99):
            protocol=make_protocol(replica)
            self.assertEqual(protocol['seed'],508+replica)
            self.assertEqual(protocol['seedNamespace'],f"{frozen['seedNamespace']}:replica-{replica}")
            self.assertEqual({k for k in frozen if protocol[k]!=frozen[k]},{'seed','seedNamespace'})
        copied=make_protocol(1)
        copied['trainMaps'].append('not a map')
        copied['warmStart']['sha256']='not a checkpoint'
        copied['priorTemperatures']['openBid']=999
        self.assertEqual(PROTOCOL,frozen)
        self.assertEqual(make_protocol(),frozen)
        # The factory uses the frozen file, not a caller-patched shared recipe.
        with patch.dict(PROTOCOL,{'updates':999}):self.assertEqual(make_protocol(),frozen)

    def test_bad_replicas_fail_closed(self):
        for replica in (-1,100,1000,True,False,1.0,'1',None,[],{}):
            with self.subTest(replica=replica), self.assertRaisesRegex(ValueError,'integer from 0 to 99'):
                make_protocol(replica)

    def test_default_plans_are_unchanged(self):
        # Canonical JSON hashes of the original v1 plans (before replica support).
        fixtures=[
            ('train',1,80,'71cd07366301bed893b4b35b764b93a1d589aff5691f7251373f8fd99b99fe16'),
            ('train',16,80,'33269a3ed0d131021e62cbb1efdb6a85c85dd4f8d1b32c5a8d011d2442973308'),
            ('selection',0,320,'4c41118f403a5eeeaeeb15e8586f22189c24f666a504e92872457f0a0e6f8cf0'),
            ('confirmation',0,960,'99877c2585b18c2e610b1af82d4014853add64783d9907a63f185bf8cabaa45f'),
            ('smoke',0,480,'e74ee0f194a0b2adb3962188bffe328f4785f0e7a5e40db932a5258a542c8e00'),
        ]
        for split,update,count,sha in fixtures:
            with self.subTest(split=split,update=update):
                plan=plans(split,update)
                self.assertEqual(plan,plans(split,update,protocol=make_protocol()))
                self.assertEqual(len(plan),count)
                self.assertEqual(hashlib.sha256(json.dumps(plan,sort_keys=True).encode()).hexdigest(),sha)

    def test_replicas_and_splits_have_disjoint_deals_with_same_schedule(self):
        seen=set()
        splits=[('train',update) for update in range(1,17)]+[('selection',0),('confirmation',0),('smoke',0)]
        for replica in (0,1,2):
            protocol=make_protocol(replica)
            for split,update in splits:
                with self.subTest(replica=replica,split=split,update=update):
                    plan=plans(split,update,protocol=protocol)
                    seeds={s['seed'] for s in plan}
                    self.assertFalse(seen&seeds)
                    seen.update(seeds)
                    normalized=[dict(s,seed=s['seed'].replace(protocol['seedNamespace'],PROTOCOL['seedNamespace'],1)) for s in plan]
                    self.assertEqual(normalized,plans(split,update))
        self.assertEqual(len(plans('train',1,deals=2,protocol=make_protocol(2))),160)

    def test_source_and_replica_mismatch_still_block_recovery(self):
        with tempfile.TemporaryDirectory() as temp, patch('ppo.warm_start') as warm:
            path=Path(temp)/'config.json'
            identity=config(False,make_protocol(1))
            path.write_text(json.dumps(identity))
            with self.assertRaisesRegex(RuntimeError,'config/source mismatch'):
                run('unused',temp,replica=2)
            identity['sourceFiles']['ppo.py']='0'*64
            path.write_text(json.dumps(identity))
            with self.assertRaisesRegex(RuntimeError,'config/source mismatch'):
                run('unused',temp,replica=1)
            warm.assert_not_called()


class ReplicaJobTests(unittest.TestCase):
    def test_job_records_and_passes_replica_without_changing_warm_start(self):
        import job_ppo
        for value in (None,'1','2'):
            replica=int(value or '0')
            with self.subTest(replica=replica), tempfile.TemporaryDirectory() as temp:
                env=dict(RUN_ID='unit-replica',MODEL_REPO='private/unit',RUN_DIR=temp,SOURCE_REVISION='unit',SOURCE_SHA256='unit')
                if value is not None:env['REPLICA']=value
                with patch.dict(os.environ,env,clear=True), patch('job_ppo.HfApi') as api, \
                     patch('job_ppo.subprocess.run'), patch('job_ppo.hf_hub_download',return_value='warm.pt') as download, \
                     patch('job_ppo.digest',return_value=PROTOCOL['warmStart']['sha256']), \
                     patch('job_ppo.train',return_value=dict(selectedUpdate=0)) as train:
                    api.return_value.model_info.return_value.private=True
                    api.return_value.upload_folder.return_value.oid='unit-upload'
                    job_ppo.run()
                    train.assert_called_once()
                    self.assertEqual(train.call_args.args,('warm.pt',Path(temp)/'ppo'))
                    self.assertEqual(train.call_args.kwargs['replica'],replica)
                    warm=PROTOCOL['warmStart']
                    download.assert_called_once_with(warm['repo'],warm['path'],revision=warm['revision'])
                    status=json.loads((Path(temp)/'status.json').read_text())
                    self.assertEqual(status['replica'],replica)
                    self.assertEqual(status['protocol'],make_protocol(replica))

    def test_job_rejects_invalid_replica_before_remote_work(self):
        import job_ppo
        for value in ('','no','1.5','-1','100'):
            with self.subTest(value=value), patch.dict(os.environ,dict(RUN_ID='unit',MODEL_REPO='unit',REPLICA=value),clear=True), \
                 patch('job_ppo.HfApi') as api, self.assertRaises(ValueError):
                job_ppo.run()
            api.assert_not_called()


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
        self.check_interrupted_resume(0)

    def test_exact_interrupted_replica_smoke_resume(self):
        self.check_interrupted_resume(2)

    def check_interrupted_resume(self,replica):
        # Identical graph warm start in both replicas; only rollout RNG/deals vary.
        torch.manual_seed(508);base=ResidualPolicy(16)
        options={'replica':replica} if replica else {}  # Also exercise the legacy default.
        with tempfile.TemporaryDirectory() as temp, patch('ppo.warm_start',side_effect=lambda _:copy.deepcopy(base)):
            root=Path(temp)
            full_result=run('unused',root/'full',smoke=True,**options)
            def interrupt(stage):
                if stage=='update-1':raise RuntimeError('simulated interruption')
            with self.assertRaisesRegex(RuntimeError,'simulated interruption'):
                run('unused',root/'resume',smoke=True,callback=interrupt,**options)
            committed=torch.load(root/'resume/last.pt',weights_only=True)
            self.assertEqual(committed['update'],1)
            self.assertTrue(committed['optimizer']['state'])
            self.assertEqual(committed['config']['protocol'],make_protocol(replica))
            # Simulate an interrupted next update: best replaced but last not
            # yet committed. Recovery must undo it using last's embedded bytes.
            save(root/'resume/best.pt',base,update=999)
            run('unused',root/'resume',smoke=True,stop_after=1,**options)
            self.assertEqual((root/'resume/best.pt').read_bytes(),committed['bestArtifact'])
            torch.rand(10)  # Recovery must not depend on the process's current RNG.
            resumed_result=run('unused',root/'resume',smoke=True,**options)
            a=torch.load(root/'full/last.pt',weights_only=True)
            b=torch.load(root/'resume/last.pt',weights_only=True)
            torch.testing.assert_close(a['state_dict'],b['state_dict'],atol=0,rtol=0)
            torch.testing.assert_close(a['optimizer'],b['optimizer'],atol=0,rtol=0)
            torch.testing.assert_close(a['torchRng'],b['torchRng'],atol=0,rtol=0)
            for key in ('bestUpdate','bestScore','baseline','config'):
                self.assertEqual(a[key],b[key])
            self.assertEqual(full_result,resumed_result)
            self.assertEqual([{k:v for k,v in r.items() if k!='seconds'} for r in a['history']],
                             [{k:v for k,v in r.items() if k!='seconds'} for r in b['history']])
            best_a,meta_a=load(root/'full/best.pt');best_b,meta_b=load(root/'resume/best.pt')
            self.assertEqual(meta_a['update'],meta_b['update'])
            torch.testing.assert_close(best_a.state_dict(),best_b.state_dict(),atol=0,rtol=0)
            for name in ('selection-plan.json','confirmation-plan.json'):
                plan=json.loads((root/'resume'/name).read_text())
                self.assertTrue(all(s['seed'].startswith(make_protocol(replica)['seedNamespace']+':') for s in plan))


if __name__=='__main__':unittest.main()
