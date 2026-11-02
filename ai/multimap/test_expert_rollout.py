"""Offline transport/plan tests; synthetic terminal games are test doubles only."""
import copy
import sys
import unittest
from unittest import mock
import torch

import expert_rollout as r
from expert_policy import ExpertPolicy
from test_expert_policy import fixture

PHASES = ('Auction', 'Resources', 'Building', 'Bureaucracy')
CONTROLLERS = ('learner', 'warmupExpert', 'reference', 'self', *r.FROZEN, 'fixedV2', 'fixedV1', 'focalTeacher')


def terminal(spec):
    counts = {c: dict.fromkeys(PHASES, 0) for c in CONTROLLERS}
    expert = dict.fromkeys(PHASES, 0)
    label = spec['map'] == 'Germany' and spec['split'] in ('train', 'warmup')
    name = 'focalTeacher' if spec.get('focalTeacher') else 'warmupExpert' if spec['split'] == 'warmup' else 'learner'
    counts[name]['Auction'] = 1
    counts['fixedV2']['Bureaucracy'] = 1
    expert['Auction'] = int(label)
    return dict(terminal=True, credit=[1., 0.], steps=2, rounds=1, counts=counts, expertCounts=expert,
        publicChecks=dict(hiddenInvariant=int(label), referenceAtomicLegal=0, expertAtomicLegal=int(label),
                          fullMenuPrior=int(not spec.get('focalTeacher'))))


class Bridge:
    instances = []
    mutate = None
    def __init__(self, *args, **kwargs):
        self.closed = False; self.labeled = False; self.instances.append(self)
    def close(self): self.closed = True
    def call(self, request):
        op = request['op']
        if op == 'start':
            self.spec = request['spec']
            if self.spec.get('focalTeacher'): return terminal(self.spec)
            row = fixture()
            obs = {k: (v.tolist() if torch.is_tensor(v) else v) for k, v in row.items() if k in r.OBSERVATION_FIELDS}
            obs['schema'] = 'multimap-graph-v1'
            required = self.spec['map'] == 'Germany' and self.spec['split'] in ('train', 'warmup')
            state = dict(terminal=False, kind='learner', seat=self.spec['focalSeat'], phase='Auction',
                controller='learner', expertRequired=required, observation=obs, revision=0, featureMs=0.)
            if required:
                state['request'] = dict(player=self.spec['focalSeat'], requestId='test', revision=0, state={})
            if self.mutate: self.mutate(state)
            return state
        if op == 'label':
            self.labeled = True
            return dict(labeled=True, expertIndex=1, revision=0)
        if op == 'step':
            self.action = request['index']
            if self.spec['map'] == 'Germany' and self.spec['split'] in ('train', 'warmup'):
                assert self.labeled
            return terminal(self.spec)
        raise AssertionError(op)


class Reference:
    instances = []
    def __init__(self, *args): self.closed = False; self.instances.append(self)
    def close(self): self.closed = True
    def decide(self, request): return dict(requestId=request['requestId'], revision=request['revision'], move={'name':'test'})


class RolloutTests(unittest.TestCase):
    def setUp(self):
        Bridge.instances = []; Reference.instances = []; Bridge.mutate = None
        self.model = ExpertPolicy(8)
        self.population = dict.fromkeys(r.FROZEN, self.model)
    def collect(self, tasks, mode='evaluation', workers=2):
        with mock.patch.object(r, 'LineProcess', Bridge), mock.patch.object(r, 'ReferenceProcess', Reference):
            return r.collect(self.model, tasks, workers, mode != 'evaluation', mode=mode, opponents=self.population)
    def test_plans_counts_balance_disjoint_and_population(self):
        plans = {s:r.plans(s, 1 if s=='train' else 0) for s in r.SPLITS}
        self.assertEqual({s:len(p) for s,p in plans.items()}, dict(warmup=160,train=80,selection=320,confirmation=960))
        roots = {s:{p['seed'] for p in tasks} for s,tasks in plans.items()}
        for a in roots:
            for b in roots:
                if a != b: self.assertFalse(roots[a] & roots[b])
        self.assertFalse(roots['train'] & {p['seed'] for p in r.plans('train',2)})
        self.assertEqual({p['map'] for p in plans['train']},set(r.PROTOCOL['trainMaps']))
        self.assertEqual(sum(p['opponentMode']=='reference' for p in plans['train']),10)
        self.assertTrue(all('self' not in p['opponents'] for p in plans['selection']+plans['confirmation']))
        for s,tasks in plans.items():
            self.assertFalse(roots[s] & {p['seed'] for p in r.plans(s,1 if s=='train' else 0,smoke=True)})
            r.validate_tasks(tasks,'evaluation' if s in ('selection','confirmation') else s,s in ('warmup','train'))
    def test_guards(self):
        for args in [('train',0),('train',True),('final',0),('selection',1)]:
            with self.assertRaises(ValueError): r.plans(*args)
        s=r.plans('selection',smoke=True)[0]
        r.validate_tasks([dict(s,focalTeacher=True)],'evaluation',False)
        for patch in ({'focalTeacher':1},{'seed':'final'},{'map':'Italy'},{'extra':0}):
            with self.assertRaises(ValueError): r.validate_tasks([dict(s,**patch)],'evaluation',False)
        with self.assertRaises(ValueError): r.validate_tasks([s,s],'evaluation',False)
        s=r.plans('train',1,smoke=True)[0]
        with self.assertRaises(ValueError): r.validate_tasks([dict(s,focalTeacher=False)],'train',True)
        with self.assertRaises(ValueError): r.validate_tasks(r.plans('warmup',smoke=True),'warmup',False)
    def test_warmup_expert_train_sampler_and_eval_no_labels(self):
        for mode,split in [('warmup','warmup'),('train','train'),('evaluation','selection')]:
            tasks=r.plans(split,1 if split=='train' else 0,smoke=True)
            rows,out=self.collect(tasks,mode)
            self.assertEqual(len(out),len(tasks))
            self.assertTrue(all(p.closed for p in Bridge.instances+Reference.instances))
            if mode=='evaluation': self.assertEqual(rows,[]);self.assertTrue(all(o['expertRequests']==0 for o in out))
            else:
                self.assertEqual(len(rows),len(tasks))
                self.assertTrue(all(x['weight']==1 for x in rows))
                if mode=='warmup': self.assertTrue(all(x['chosen']==x['expertIndex']==1 for x in rows))
                else: self.assertEqual(sum(x['expertIndex']>=0 for x in rows),1)
            self.assertTrue(self.model.training)
    def test_per_game_sampling_independent_of_worker_count(self):
        tasks=r.plans('train',1,smoke=True)
        a,_=self.collect(tasks,'train',1); b,_=self.collect(tasks,'train',2)
        self.assertEqual([x['chosen'] for x in a],[x['chosen'] for x in b])
    def test_failures_cleanup_and_no_eval_features_or_labels(self):
        for mutate in (lambda s:s.update(expertRequired=True),lambda s:s['observation'].update(seed='private')):
            Bridge.mutate=staticmethod(mutate)
            with self.assertRaises(ValueError): self.collect(r.plans('selection',smoke=True))
            self.assertTrue(all(x.closed for x in Bridge.instances+Reference.instances))
        Bridge.mutate=None
        with mock.patch.object(r,'_row_budget',side_effect=MemoryError('budget')):
            with self.assertRaises(MemoryError): self.collect(r.plans('train',1,smoke=True),'train')
        self.assertTrue(all(x.closed for x in Bridge.instances+Reference.instances))
    def test_phase_balanced_labels_and_terminal_counter_tampering(self):
        rows=[dict(phase='Auction',expertIndex=0) for _ in range(3)]+[dict(phase='Building',expertIndex=1)]
        r._finalize_rows(rows,.5)
        self.assertAlmostEqual(sum(x['expertWeight'] for x in rows[:3]),.5)
        self.assertEqual(rows[-1]['expertWeight'],.5)
        s=r.plans('train',1,smoke=True)[0]; good=terminal(s);r._terminal(good,s)
        for mutate in (lambda x:x.update(credit=[.75,.25]), lambda x:x['expertCounts'].update(Auction=0),
                       lambda x:x['counts']['learner'].update(Auction=1.0),lambda x:x['publicChecks'].update(hiddenInvariant=0)):
            bad=copy.deepcopy(good);mutate(bad)
            with self.assertRaises(ValueError):r._terminal(bad,s)
    def test_real_transport_timeout_kills_process_and_reader(self):
        p=r.LineProcess([sys.executable,'-u','-c','import time;time.sleep(30)'],timeout=.05)
        try:
            with self.assertRaises(TimeoutError):p.call({'op':'test'})
            self.assertIsNotNone(p.process.poll());self.assertFalse(p.reader.is_alive())
        finally:p.close()

if __name__=='__main__':unittest.main()
