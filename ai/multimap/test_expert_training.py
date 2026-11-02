"""Offline optimization, transaction and publication-boundary tests."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import torch

import expert_ppo as train
import job_expert as job
from expert_policy import ExpertPolicy, batch, load
from test_expert_policy import fixture
from data import atomic_json, digest


def equal(test, a, b):
    if torch.is_tensor(a): test.assertTrue(torch.equal(a,b))
    elif isinstance(a,dict):
        test.assertEqual(set(a),set(b))
        for k in a: equal(test,a[k],b[k])
    elif isinstance(a,(list,tuple)):
        test.assertEqual(len(a),len(b))
        for x,y in zip(a,b):equal(test,x,y)
    else:test.assertEqual(a,b)


def synthetic_collect(model,tasks,workers,training=False,*,mode='evaluation',**kwargs):
    assert training == (mode!='evaluation')
    changed=bool(model.network.action[-1].weight.detach().abs().sum())
    rows,outcomes=[],[]
    for spec in tasks:
        credit=float(changed and not spec.get('focalTeacher'))
        vector=[0.]*spec['players']; vector[spec['focalSeat'] if credit else (spec['focalSeat']+1)%spec['players']]=1.
        outcomes.append(dict(spec=spec,terminal=True,credit=credit,allSeatCredit=vector,steps=2,rounds=1,
                             featureMs=12. if spec.get('focalTeacher') else 1.,inferenceMs=0.,referenceMs=0.))
        if training:
            for phase in ('Auction','Building'):
                row=fixture()
                with torch.no_grad():logits,values=model(batch([row]));logps=logits.log_softmax(-1)
                label=1 if spec['map']=='Germany' else -1
                action=label if mode=='warmup' else int(logits.argmax())
                row.update(chosen=action,oldLog=float(logps[0,action]),oldValue=float(values[0]),phase=phase,
                           expertIndex=label,expertWeight=.5 if label>=0 else 0.,weight=.5,**{'return':credit})
                rows.append(row)
    return rows,outcomes


class TrainingTests(unittest.TestCase):
    def test_global_expert_weights_phase_balance_and_zero_label_gradient(self):
        rows=[]
        for phase,w in [('Auction',1/6)]*3+[('Building',.5)]+[('Auction',0.)]*4:
            row=fixture();row.update(weight=.25,expertWeight=w,expertIndex=1 if w else -1,phase=phase);rows.append(row)
        _,weights=train.objective_weights(rows)
        logits=torch.zeros(8,2,requires_grad=True);logps=logits.log_softmax(-1)
        full=train.expert_loss(logps,rows,weights)
        parts=[train.expert_loss(logps[i:i+2],rows[i:i+2],weights[i:i+2]) for i in range(0,8,2)]
        self.assertTrue(torch.allclose(full,sum(parts)/4));self.assertAlmostEqual(float(weights[:3].sum()),4.)
        zero=train.expert_loss(logps[4:],rows[4:],weights[4:]);zero.backward()
        self.assertEqual(float(zero.detach()),0.);self.assertEqual(float(logits.grad.abs().sum()),0.)
        rows[0]['expertIndex']=-1
        with self.assertRaises(ValueError):train.objective_weights(rows)
    def test_supervised_gradient_can_move_floor20_target_and_ppo_no_label_is_finite(self):
        torch.manual_seed(51);model=ExpertPolicy(8);spec=train.plans('warmup',smoke=True)[:1]
        rows,_=synthetic_collect(model,spec,1,True,mode='warmup')
        opt=torch.optim.AdamW(model.parameters(),lr=.003)
        def loss():return float(-model(batch(rows))[0].log_softmax(-1)[:,1].mean().detach())
        before=loss();metrics=train.warmup_optimize(model,opt,rows,epochs=4);self.assertLess(loss(),before)
        self.assertEqual(metrics['optimizerSteps'],4)
        rows,_=synthetic_collect(model,train.plans('train',1,smoke=True)[1:],1,True,mode='train')
        metrics=train.optimize(model,opt,rows,1)
        self.assertGreater(metrics['optimizerSteps'],0);self.assertEqual(metrics['expertRows'],0)
        self.assertEqual(metrics['expertCE'],0.)
    def test_selection_guards_and_terminal_not_timing_parity(self):
        baseline=dict(failures=0,maps={'Germany':.2,'USA':.5},macroCredit=.35)
        self.assertTrue(train.eligible(copy.deepcopy(baseline),baseline))
        for name,value in [('Germany',.199),('USA',.449)]:
            c=copy.deepcopy(baseline);c['maps'][name]=value;self.assertFalse(train.eligible(c,baseline))
        s=train.plans('selection',smoke=True)[0];model=ExpertPolicy(8)
        _,a=synthetic_collect(model,[s],1);_,b=synthetic_collect(model,[dict(s,focalTeacher=True)],1)
        train.assert_initial_parity(a,b);b[0]['allSeatCredit'].reverse()
        with self.assertRaises(RuntimeError):train.assert_initial_parity(a,b)
    def test_populated_optimizer_exact_resume_repairs_corrupted_best_and_no_repeat_confirmation(self):
        calls=[]
        def collect(*args,**kwargs):
            tasks=args[1];calls.append((tasks[0]['split'],tasks[0]['update']))
            return synthetic_collect(*args,**kwargs)
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(train,'config',return_value={'frozen':True}), \
             mock.patch.object(train,'load_candidates',return_value={}), mock.patch.object(train,'warm_start',side_effect=lambda p:ExpertPolicy(8)), \
             mock.patch.object(train,'collect',side_effect=collect):
            root=Path(tmp);a=root/'a';b=root/'b'
            complete=train.run('mock',a,True)
            calls.clear();self.assertIsNone(train.run('mock',b,True,stop_after=1))
            self.assertFalse(any(s=='confirmation' for s,u in calls))
            _,saved=load(b/'last.pt');self.assertTrue(saved['optimizer']['state'])
            (b/'best.pt').write_bytes(b'uncommitted corrupt prospective candidate')
            resumed=train.run('mock',b,True);self.assertEqual(resumed,complete)
            _,left=load(a/'last.pt');_,right=load(b/'last.pt')
            for key in ('state_dict','optimizer','torchRng','history','bestArtifact','bestSha256','result'):
                equal(self,left[key],right[key])
            self.assertEqual(digest(b/'best.pt'),right['bestSha256'])
            calls.clear();self.assertEqual(train.run('mock',b,True),complete);self.assertEqual(calls,[])
            with mock.patch.object(train,'config',return_value={'frozen':False}):
                with self.assertRaisesRegex(RuntimeError,'mismatch'):train.run('mock',b,True)
    def test_identity_records_actual_workers_and_worker_serving_files(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(train,'verify_artifact',return_value={'present':1}), \
             mock.patch.object(train,'runtime_versions',return_value={'stub':True}), mock.patch.object(train,'engine_dependencies',return_value={}):
            path=Path(tmp);atomic_json(path/'manifest.json',{})
            one=train.config(True,artifact=path,workers=1);two=train.config(True,artifact=path,workers=2)
            self.assertNotEqual(one,two)
            self.assertIn('ai/multimap/job_expert.py',one['sourceFiles'])
            self.assertIn('ai/multimap/expert_game.cjs',one['sourceFiles'])
            self.assertNotIn('startMethod',one['execution'])
            with self.assertRaises(ValueError):train.config(True,artifact=path,workers=7)
            with mock.patch.object(train,'MANIFEST_SHA','wrong'):
                with self.assertRaisesRegex(ValueError,'pins differ'):train.config(True,artifact=path,workers=2)
    def test_bounded_resume_checks_all_sizes_before_download_and_rejects_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);remote=root/'remote';remote.mkdir()
            names={'expert/config.json':b'{}','expert/last.pt':b'committed-test-bytes','expert/initial.pt':b'initial-test-bytes'}
            files={}
            for name,content in names.items():
                path=remote/Path(name).name;path.write_bytes(content);files[name]=path
            manifest={name:digest(path) for name,path in files.items()}
            atomic_json(remote/'manifest.json',manifest)
            events=[]
            def size(repo,name,revision,**kwargs):
                events.append(('size',name));return (remote/'manifest.json').stat().st_size if name.endswith('artifacts.json') else len(names[name.split('runs/unit/')[1]])
            def download(repo,name,**kwargs):
                events.append(('download',name));return str(remote/'manifest.json') if name.endswith('artifacts.json') else str(files[name.split('runs/unit/')[1]])
            with mock.patch.object(job.shared,'remote_size',side_effect=size), mock.patch('huggingface_hub.hf_hub_download',side_effect=download):
                restored=job.restore_resume('repo','unit','a'*40,root/'out',root/'cache')
                self.assertEqual(restored['files'],manifest)
                first=next(i for i,e in enumerate(events) if e[0]=='download' and not e[1].endswith('artifacts.json'))
                self.assertEqual(sum(e[0]=='size' for e in events[:first]),4)
                files['expert/last.pt'].write_bytes(b'wrong')
                with self.assertRaisesRegex(ValueError,'hash/size'):job.restore_resume('repo','unit','a'*40,root/'out2',root/'cache')
    def test_artifact_whitelist_resume_hash_and_no_raw_json(self):
        valid={k:'a'*64 for k in ('expert/config.json','expert/last.pt','expert/initial.pt')}
        self.assertEqual(job.validate_manifest(valid),valid)
        for patch in ({'../bad.pt':'a'*64},{'expert/replay.json':'a'*64},{'expert/last.pt':'bad'}):
            with self.assertRaises(ValueError):job.validate_manifest({**valid,**patch})
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp);atomic_json(path/'protocol.json',{'safe':True})
            self.assertEqual(set(job.compact_files(path)),{'protocol.json'})
            atomic_json(path/'protocol.json',{'nested':[{'observation':{'secret':1}}]})
            with self.assertRaises(ValueError):job.compact_files(path)
            (path/'protocol.json').unlink();(path/'leak.json').write_text('{}')
            with self.assertRaises(ValueError):job.compact_files(path)
            (path/'leak.json').unlink();(path/'protocol.json').symlink_to('/tmp')
            with self.assertRaises(ValueError):job.compact_files(path)

if __name__=='__main__':unittest.main()
