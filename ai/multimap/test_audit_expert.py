"""Offline adversarial tests for independent expert-v2 audit (no cache/network)."""
import copy
import math
import unittest

import audit_expert as a


def fixture(task=None):
    s = copy.deepcopy(task or a.expected_plan('confirmation')[0])
    counts = {actor: dict.fromkeys(a.PHASES, 0) for actor in a.CONTROLLERS}
    for actor in s['opponents']:
        if actor == 'learner':
            actor = 'focalTeacher' if s.get('focalTeacher') else 'warmupExpert' if s['split'] == 'warmup' else actor
        if actor in ('reference', 'focalTeacher'):
            for p in a.PHASES:
                counts[actor][p] += 1
        else:
            counts[actor]['Auction'] += 2
            counts[actor]['Building'] += 1
            fixed = 'fixedV1' if actor in a.FROZEN else 'fixedV2'
            for p in ('Resources', 'Bureaucracy'):
                counts[fixed][p] += 1
    totals = {actor: sum(v.values()) for actor,v in counts.items()}
    labels = dict.fromkeys(a.PHASES, 0)
    if s['map'] == 'Germany' and s['split'] in ('warmup','train'):
        labels = dict(counts['warmupExpert' if s['split'] == 'warmup' else 'learner'])
    credits = [int(i == s['focalSeat']) for i in range(s['players'])]
    return dict(spec=s, terminal=True, credit=1, allSeatCredit=credits, steps=sum(totals.values()), rounds=1,
        counts=counts, expertCounts=labels,
        publicChecks=dict(hiddenInvariant=totals['reference']+sum(labels.values()),
            referenceAtomicLegal=totals['reference'], expertAtomicLegal=sum(labels.values()),
            fullMenuPrior=sum(totals[k] for k in ('learner','warmupExpert','self',*a.FROZEN))),
        decisions=totals['learner']+totals['warmupExpert'], referenceRequests=totals['reference']+sum(labels.values()),
        expertRequests=sum(labels.values()), featureMs=0., inferenceMs=0., referenceMs=0., seconds=0.)


def scores(value=.3, **changes):
    maps = dict.fromkeys(a.TRAIN_MAPS, value); maps.update(changes)
    return dict(failures=0, maps=maps, macroCredit=sum(maps.values())/4)


def stages(*values):
    return list(zip(('initial','warmup','8','16','24','32'), values or [scores() for _ in range(6)]))


class Plans(unittest.TestCase):
    def test_counts(self):
        self.assertEqual([len(a.expected_plan(s)) for s in ('warmup','selection','confirmation')], [160,320,960])
        self.assertEqual(len(a.expected_plan('train',1)),80)

    def test_training_scope(self):
        tasks = [s for u in range(1,33) for s in a.expected_plan('train',u)]
        self.assertEqual(len({s['seed'] for s in tasks}),2560)
        self.assertEqual({s['map'] for s in tasks},set(a.TRAIN_MAPS))
        self.assertTrue(all(s['seed'].startswith(a.NAMESPACE+':train:') for s in tasks))

    def test_forbidden_namespaces(self):
        for split,update,teacher in [('final',0,False),('train',0,False),('train',33,False),
                                     ('selection',1,False),('warmup',0,True),('train',1,True)]:
            with self.subTest(split=split,update=update), self.assertRaises(ValueError):
                a.expected_plan(split,update,teacher)

    def test_no_cross_split_leakage(self):
        t = [fixture(a.expected_plan('train',1)[0])]
        with self.assertRaises(ValueError):
            a.check_disjoint(t,t,[])
        with self.assertRaises(ValueError):
            a.check_disjoint(t+t,[],[])

    def test_no_heldout_training(self):
        r = fixture(a.expected_plan('train',1)[0]); r['spec']['map'] = 'Italy'
        with self.assertRaises(ValueError):
            a.check_disjoint([r],[],[])

    def test_replay_coverage(self):
        tasks = a.replay_tasks()
        self.assertEqual({s['map'] for s in tasks},set(a.MAPS))
        self.assertEqual({s['players'] for s in tasks},set(range(2,7)))
        self.assertEqual(len({(s['variant'],s['fastBid']) for s in tasks}),4)


class Outcomes(unittest.TestCase):
    def bad(self, change, task=None):
        r = fixture(task); spec = copy.deepcopy(r['spec']); change(r)
        with self.assertRaises(ValueError):
            a.validate_outcome(r,spec)

    def test_valid_all_modes(self):
        tasks = [a.expected_plan('warmup')[0],a.expected_plan('train',1)[0],
                 a.expected_plan('train',2)[0],a.expected_plan('selection',teacher=True)[0],
                 a.expected_plan('confirmation')[0],a.expected_plan('confirmation',teacher=True)[-1]]
        for task in tasks:
            a.validate_outcome(fixture(task),task)

    def test_full_spec_and_opponents(self):
        self.bad(lambda r:r['spec']['opponents'].__setitem__(1,'self'))
        self.bad(lambda r:r['spec'].__setitem__('seed','old-dataset-root'))
        self.bad(lambda r:r['spec'].__setitem__('smoke',0))

    def test_missing_error_or_trace(self):
        self.bad(lambda r:r.pop('rounds'))
        self.bad(lambda r:r.__setitem__('error','failed'))
        self.bad(lambda r:r.__setitem__('observations',[]))

    def test_no_nonterminal_or_cap(self):
        self.bad(lambda r:r.__setitem__('terminal',False))
        self.bad(lambda r:r.__setitem__('steps',4001))
        self.bad(lambda r:r.__setitem__('rounds',0))

    def test_no_nonfinite(self):
        self.bad(lambda r:r.__setitem__('seconds',float('nan')))
        self.bad(lambda r:r.__setitem__('credit',float('inf')))

    def test_credit_vector(self):
        self.bad(lambda r:r.__setitem__('allSeatCredit',[.6,.4]))
        self.bad(lambda r:r.__setitem__('allSeatCredit',[0,0]))
        self.bad(lambda r:r.__setitem__('allSeatCredit',[1]))
        self.bad(lambda r:r.__setitem__('credit',0))
        r = fixture(); r['allSeatCredit']=[.5,.5];r['credit']=.5
        a.validate_outcome(r,r['spec'])

    def test_counter_integer_and_schema(self):
        self.bad(lambda r:r['counts']['learner'].__setitem__('Auction',True))
        self.bad(lambda r:r['counts']['learner'].__setitem__('Auction',-1))
        self.bad(lambda r:r['counts']['learner'].pop('Resources'))
        self.bad(lambda r:r['counts'].pop('fixedV1'))

    def test_counter_total(self):
        self.bad(lambda r:r.__setitem__('steps',r['steps']+1))

    def test_fixed_phase_routing(self):
        def mutate(r):
            r['counts']['learner']['Auction']-=1;r['counts']['learner']['Resources']+=1
        self.bad(mutate)

    def test_missing_required_reference_phase(self):
        def mutate(r):
            r['counts']['reference']['Resources']-=1;r['counts']['fixedV2']['Resources']+=1
            r['publicChecks']['referenceAtomicLegal']-=1;r['publicChecks']['hiddenInvariant']-=1
            r['referenceRequests']-=1
        self.bad(mutate)

    def test_absent_fixed_controller(self):
        def mutate(r):
            r['counts']['fixedV2']['Resources']-=1;r['counts']['fixedV1']['Resources']+=1
        self.bad(mutate)

    def test_absent_frozen_or_self(self):
        for actor in ('self','ppo0','warmupExpert','focalTeacher'):
            def mutate(r):
                r['counts']['learner']['Auction']-=1;r['counts'][actor]['Auction']+=1
            self.bad(mutate)

    def test_no_eval_labels(self):
        self.bad(lambda r:r['expertCounts'].__setitem__('Auction',1))

    def test_required_germany_train_labels(self):
        self.bad(lambda r:r['expertCounts'].__setitem__('Auction',0),a.expected_plan('train',1)[0])

    def test_no_other_map_labels(self):
        task = next(s for s in a.expected_plan('train',1) if s['map']=='USA')
        self.bad(lambda r:r['expertCounts'].__setitem__('Auction',1),task)

    def test_public_counters_and_requests(self):
        for name in ('hiddenInvariant','referenceAtomicLegal','expertAtomicLegal','fullMenuPrior'):
            self.bad(lambda r:r['publicChecks'].__setitem__(name,r['publicChecks'][name]+1))
        for name in ('decisions','referenceRequests','expertRequests'):
            self.bad(lambda r:r.__setitem__(name,r[name]+1))

    def test_duplicate_and_missing_games(self):
        s=a.expected_plan('confirmation')[0];r=fixture(s)
        with self.assertRaises(ValueError):a.verify_outcomes([r,r],[s,s])
        with self.assertRaises(ValueError):a.verify_outcomes([],[s])

    def test_parity_checks_all_seats_and_rounds(self):
        s=a.expected_plan('confirmation')[0];r=fixture(s);t=fixture(dict(s,focalTeacher=True))
        # Construct a routed teacher counter from exact initial game, not a new game.
        t.update({k:copy.deepcopy(r[k]) for k in ('allSeatCredit','credit','steps','rounds','referenceRequests','expertRequests','expertCounts')})
        for p in a.PHASES:t['counts']['focalTeacher'][p]=r['counts']['learner'][p]+r['counts']['fixedV2'][p]
        a.initial_parity([r],[t])
        t['rounds']+=1
        with self.assertRaises(ValueError):a.initial_parity([r],[t])


class Statistics(unittest.TestCase):
    def test_equal_cell_not_game_weight(self):
        rows=[]
        for n,credit in ((2,1),(6,0)):
            rows += [dict(spec=dict(cell=f'Germany|{n}|original|0'),credit=credit) for _ in range(n)]
        self.assertEqual(a.summary(rows)['macroCredit'],.5)
        self.assertNotEqual(a.summary(rows)['macroCredit'],sum(r['credit'] for r in rows)/len(rows))

    def test_unbiased_fixed_cell_deal_variance(self):
        r=a.stratified_estimate({'a':[0,1],'b':[.5,.5]})
        self.assertEqual(r['mean'],.5)
        self.assertEqual(r['standardError'],.25) # (.5/2 + 0/2)/4, NOT population variance
        self.assertEqual(r['approximateNormal95'],[.5-1.96*.25,.5+1.96*.25])

    def test_fixed_cells_not_random_cell_variation(self):
        self.assertEqual(a.stratified_estimate({'a':[0,0],'b':[1,1]})['standardError'],0)

    def test_no_single_deal_variance(self):
        with self.assertRaises(ValueError):a.stratified_estimate({'a':[.5]})

    def test_complete_allseat_clusters(self):
        s=a.expected_plan('confirmation')[0]
        with self.assertRaises(ValueError):a.deal_table([fixture(s)])
        with self.assertRaises(ValueError):a.deal_table([fixture(s),fixture(s)])

    def test_paired_covariance_not_independent_arms(self):
        selected=[.2,.8];teacher=[.1,.7]
        r=a.stratified_estimate({'a':[x-y for x,y in zip(selected,teacher)]})
        self.assertAlmostEqual(r['mean'],.1)
        self.assertAlmostEqual(r['standardError'],0)


class Selection(unittest.TestCase):
    def test_earliest_tie_including_fallback(self):
        self.assertEqual(a.choose_selection(stages())[0],'initial')
        self.assertEqual(a.choose_selection(stages(scores(),*[scores(.4)]*5))[0],'warmup')

    def test_germany_guard(self):
        base=scores(); candidate=scores(.9,Germany=.299)
        self.assertFalse(a.eligible(candidate,base))
        self.assertTrue(a.eligible(scores(.9,Germany=.3),base))

    def test_other_map_guard(self):
        self.assertTrue(a.eligible(scores(.9,USA=.25),scores()))
        self.assertFalse(a.eligible(scores(.9,USA=.249),scores()))

    def test_failures_and_bad_maps(self):
        s=scores();s['failures']=1;self.assertFalse(a.eligible(s,scores()))
        s=scores();s['maps']['Italy']=.9;self.assertFalse(a.eligible(s,scores()))

    def test_confirmation_cannot_select(self):
        with self.assertRaises(ValueError):a.choose_selection(stages()+[('confirmation',scores(.99))])


class Resume(unittest.TestCase):
    def test_nested_optimizer_change_rejected(self):
        import torch
        x={'state':{0:{'exp_avg':torch.tensor([1.])}},'param_groups':[{'lr':.0001}]}
        a.tensor_equal(x,copy.deepcopy(x))
        y=copy.deepcopy(x);y['state'][0]['exp_avg'][0]+=1
        with self.assertRaises(ValueError):a.tensor_equal(x,y)

    def test_exact_tensor_bits(self):
        import torch
        with self.assertRaises(ValueError):a.tensor_equal(torch.tensor([0.]),torch.tensor([-0.]))

    def test_resume_retraining_or_reselection_rejected(self):
        old=dict(stage='train',update=32,optimizer={'state':{'x':1}},bestUpdate=24,bestStage='train',
                 bestSha256=a.BEST_SHA,bestArtifact=b'invalid',confirmations={},result=None,torchRng=None)
        final=copy.deepcopy(old);final['update']=33
        with self.assertRaises(ValueError):a.verify_resume(old,final)
        final=copy.deepcopy(old);final['bestUpdate']=32
        with self.assertRaises(ValueError):a.verify_resume(old,final)
        final=copy.deepcopy(old);final['optimizer']['state']['x']=2
        with self.assertRaises(ValueError):a.verify_resume(old,final)

    def test_serving_drift_forbidden(self):
        with self.assertRaises(ValueError):a.local_difference('ai/multimap/expert_rollout.py','a','b')
        with self.assertRaises(ValueError):a.local_difference('ai/multimap/launch.py','a','b')
        self.assertIsNotNone(a.local_difference('ai/multimap/README.md','a','b'))

    def test_private_helper_namespace(self):
        def f():return len([])
        copied=a.reuse(f,len=lambda _:7)
        self.assertEqual(copied(),7);self.assertEqual(f(),0)


if __name__ == '__main__':
    unittest.main()
