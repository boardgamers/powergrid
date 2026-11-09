"""Offline stress-plan, transport, frozen-loader and compact-outcome tests.

Synthetic games/models are explicit local test doubles, never production
checkpoints or reported evidence. No legacy serving globals are modified.
"""
from collections import Counter, defaultdict
import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest import mock

import torch

import replica_stress_rollout_v1 as r


def observation(players=2, actions=2):
    return dict(schema='multimap-graph-v1', **{'global': [0.] * 273},
        players=[[0.] * 80 for _ in range(players)], nodes=[[0.] * 36 for _ in range(3)],
        actions=[[0.] * 34 for _ in range(actions)], actionCity=[-1] * actions,
        relations=[[[0.] * 3 for _ in range(3)] for _ in range(4)], prior=[0.] * actions)


def terminal(spec):
    counts = {name: dict.fromkeys(r.PHASES, 0) for name in r.CONTROLLERS}
    seats = [dict.fromkeys(r.PHASES, 0) for _ in range(spec['players'])]
    for seat, name in enumerate(spec['controllers']):
        for phase in r.PHASES:
            controller = name if name in ('reference', 'teacherV2') or phase in r.LEARNED_PHASES else (
                'fixedV2' if name in r.EXPERT_MODELS else 'fixedV1')
            counts[controller][phase] += 1
            seats[seat][phase] += 1
        if name in r.MODELS:
            counts['fixedV2' if name in r.EXPERT_MODELS else 'fixedV1']['Auction'] += 1
            seats[seat]['Auction'] += 1
    reference = sum(counts['reference'].values())
    return dict(terminal=True, credit=[1 / spec['players']] * spec['players'],
        steps=sum(sum(c.values()) for c in seats), rounds=1, counts=counts, seatCounts=seats,
        publicChecks=dict(hiddenInvariant=reference, referenceAtomicLegal=reference,
            expertAtomicLegal=0, fullMenuPrior=sum(sum(counts[name].values()) for name in r.MODELS)))


def outcome(spec):
    state = terminal(spec)
    return dict(spec=copy.deepcopy(spec), terminal=True, credit=state['credit'][spec['focalSeat']],
        allSeatCredit=state['credit'], steps=state['steps'], rounds=state['rounds'],
        counts=state['counts'], seatCounts=state['seatCounts'], publicChecks=state['publicChecks'],
        policyRequests={name: sum(state['counts'][name].values()) for name in r.MODELS},
        referenceRequests=sum(state['counts']['reference'].values()), featureMs=0., inferenceMs=0.,
        referenceMs=0., seconds=0.)


def choose(**criteria):
    return next(s for s in r.plans() if all(s[key] == value for key, value in criteria.items()))


class GreedyModel(torch.nn.Module):
    def __init__(self, name):
        super().__init__()
        self.name = name
        self.index = r.MODELS.index(name)
        self._replica_stress_role = name
        self.layer = torch.nn.Linear(1, 1)
        self.calls = []
        self.actions = []

    def forward(self, tensors):
        assert not self.training and not torch.is_grad_enabled()
        self.calls.append(len(tensors['global']))
        # All real scores below -1e9: a legacy finite padding sentinel cannot
        # safely mask these. Deliberately offer huge/NaN padded logits.
        logits = torch.full(tensors['actionMask'].shape, -3e12)
        logits[:, self.index] = -2e12
        logits[~tensors['actionMask']] = float('nan')
        return logits, torch.zeros(len(logits))


class Bridge:
    instances = []
    mutate = None
    end_mutate = None

    def __init__(self, argv, **kwargs):
        assert str(argv[-1]).endswith('replica_stress_game_v1.cjs')
        self.closed = False
        self.requests = []
        self.instances.append(self)

    def close(self):
        self.closed = True

    def call(self, request):
        self.requests.append(copy.deepcopy(request))
        if request['op'] == 'start':
            assert set(request) == {'op', 'spec'}
            self.spec = request['spec']
            self.events = [(seat, name, phase) for seat, name in enumerate(self.spec['controllers'])
                for phase in r.PHASES if name == 'reference' or (name in r.MODELS and phase in r.LEARNED_PHASES)]
            self.index = 0
        elif request['op'] == 'step':
            name = self.events[self.index][1]
            if name == 'reference':
                assert set(request) == {'op', 'response'}
                assert request['response']['move'] == {'name': 'test'}
            else:
                assert set(request) == {'op', 'index'}
                assert request['index'] == r.MODELS.index(name)
            self.index += 1
        else:
            raise AssertionError('Labels/training/sampling are forbidden')
        if self.index == len(self.events):
            state = terminal(self.spec)
            if self.end_mutate:
                self.end_mutate(state)
            return state
        seat, name, phase = self.events[self.index]
        state = dict(terminal=False, kind='reference' if name == 'reference' else 'policy',
            controller=name, seat=seat, phase=phase, revision=self.index)
        if name == 'reference':
            state['request'] = dict(player=seat, revision=self.index, requestId=f'test-{self.index}',
                state=dict(seed='secret', powerPlantsDeck=[], hiddenLog=[], currentBid=0,
                    options={key: self.spec[key] for key in ('map', 'variant', 'fastBid')},
                    players=[dict(lastMove=None, bid=0) for _ in range(self.spec['players'])],
                    phase=phase, currentPlayers=[seat]))
        else:
            state.update(observation=observation(self.spec['players'], len(r.MODELS) + self.spec['focalSeat']), featureMs=.25)
        if self.mutate:
            self.mutate(state)
        return state


class Reference:
    instances = []

    def __init__(self, *args):
        self.closed = False
        self.instances.append(self)

    def close(self):
        self.closed = True

    def decide(self, request):
        assert not self.closed
        return dict(requestId=request['requestId'], revision=request['revision'], move={'name': 'test'})


class ReplicaStressRollout(unittest.TestCase):
    def setUp(self):
        Bridge.instances, Reference.instances = [], []
        Bridge.mutate = Bridge.end_mutate = None
        self.models = {name: GreedyModel(name) for name in r.MODELS}
        self.models['expert24'].layer.eval()
        self.modes = [(m, m.training) for model in self.models.values() for m in model.modules()]
        self.threads = torch.get_num_threads()

    def collect(self, tasks, workers=6):
        with mock.patch.object(r, 'LineProcess', Bridge), mock.patch.object(r, 'ReferenceProcess', Reference):
            return r.collect(tasks, workers, models=self.models)

    def restored(self):
        self.assertTrue(all(p.closed for p in Bridge.instances + Reference.instances))
        self.assertEqual(torch.get_num_threads(), self.threads)
        self.assertTrue(all(m.training == before for m, before in self.modes))

    def test_exact_counts_pairing_namespace_and_eight_deal_extension(self):
        prod, smoke = r.plans(), r.plans(True)
        self.assertEqual((len(prod),len(smoke)),(15360,198))
        self.assertEqual(Counter(t['panel'] for t in prod),dict(strong=7680,mixed=7680))
        self.assertEqual(Counter(t['policy'] for t in prod),dict(replica1=5120,replica2=5120,ppo2=5120))
        self.assertEqual(len({t['seed'] for t in prod}),1280)
        self.assertEqual(len({t['seed'] for t in smoke}),16)
        self.assertFalse({t['seed'] for t in prod}&{t['seed'] for t in smoke})
        self.assertEqual({(t['map'],t['players'],t['variant'],t['fastBid']) for t in smoke},set(r.SMOKE_SCOPES))
        cells=list(dict.fromkeys(t['cell'] for t in prod))
        for tasks in (prod,smoke):
            r.validate_tasks(tasks);groups=defaultdict(list)
            for t in tasks:
                groups[t['seed']].append(t)
                weak=['ppo0','ppo1','ppo2','teacherV2']+(['reference'] if t['map']=='Germany' else [])
                for seat,c in enumerate(t['controllers']):
                    i=cells.index(t['cell'])+t['deal']+(seat-t['focalSeat']+t['players'])%t['players']-1
                    expected=t['policy'] if seat==t['focalSeat'] else (
                        ('reference' if t['map']=='Germany' else 'expert24') if t['panel']=='strong' else
                        'expert24' if i%2==0 else weak[i//2%len(weak)])
                    self.assertEqual(c,expected)
                    if seat!=t['focalSeat']:self.assertNotIn(c,('replica1','replica2'))
            for batch in groups.values():
                self.assertEqual(len(batch),batch[0]['players']*3)
                for i in range(0,len(batch),3):
                    arms=batch[i:i+3];seat=arms[0]['focalSeat']
                    self.assertEqual([a['policy'] for a in arms],list(r.POLICIES))
                    self.assertEqual(len({tuple(a['controllers'][:seat]+a['controllers'][seat+1:]) for a in arms}),1)

    def test_node_python_all_15558_specs_agree(self):
        script="const fs=require('fs'),x=require('./ai/multimap/replica_stress_game_v1.cjs');" \
               "JSON.parse(fs.readFileSync(0,'utf8')).forEach(s=>{x.validateSpec(s);});console.log('15558 ok');"
        result=subprocess.run(['node','-e',script],input=json.dumps(r.plans()+r.plans(True)),cwd=r.ROOT,
            text=True,capture_output=True,timeout=60,check=True)
        self.assertEqual(result.stdout.strip(),'15558 ok')

    def test_rejected_scope_types_roles_namespace_and_aliases(self):
        spec=r.plans(True)[0]
        for patch in ({'policy':'expert24'},{'policy':'ppo0'},{'map':'Italy'},{'map':'Benelux'},
                      {'deal':1},{'deal':True},{'maxSteps':4000.0},{'smoke':1},{'players':2.0},
                      {'fastBid':0},{'focalSeat':False},{'seed':'final:0'},{'training':False},
                      {'controllers':['replica1','replica2']}):
            with self.subTest(patch=patch),self.assertRaises(ValueError):r.validate_tasks([dict(spec,**patch)])
        outside=choose(map='USA',players=2)
        outside=dict(outside,smoke=True,seed=outside['seed'].replace(r.NAMESPACE,r.NAMESPACE+':smoke'))
        with self.assertRaises(ValueError):r.validate_tasks([outside])
        for tasks in ([],[spec,spec],[spec,r.plans()[0]]):
            with self.assertRaises(ValueError):r.validate_tasks(tasks)
        for workers in (True,0,7,1.0):
            with self.assertRaises(ValueError):self.collect([spec],workers)
        self.models['replica1'],self.models['replica2']=self.models['replica2'],self.models['replica1']
        with self.assertRaisesRegex(ValueError,'roles swapped'):self.collect([spec])
        self.models=dict.fromkeys(r.MODELS,self.models['expert24'])
        with self.assertRaises(ValueError):self.collect([spec])

    def test_distinct_synthetic_models_route_six_roles_greedily_without_rng_or_labels(self):
        tasks=[choose(map='USA',panel='strong',players=3,policy=p,focalSeat=seat)
               for p in r.POLICIES for seat in (0,1,2)]
        tasks.append(choose(map='Germany',panel='strong',players=2))
        for name in (*r.FROZEN,'teacherV2'):
            tasks.append(next(t for t in r.plans() if t['panel']=='mixed' and name in t['controllers'] and t not in tasks))
        before=torch.random.get_rng_state().clone();results=self.collect(tasks)
        self.assertEqual([v['spec'] for v in results],tasks)
        self.assertTrue(all(m.calls for m in self.models.values()))
        self.assertTrue(torch.equal(before,torch.random.get_rng_state()))
        for out in results:
            r.validate_outcome(out,out['spec'])
            self.assertEqual(out['publicChecks']['expertAtomicLegal'],0)
            self.assertFalse({'rows','trace','request','observation','expertIndex'}&set(out))
        self.restored()

    def test_worker_count_invariant_and_compact_routing_counts(self):
        tasks=[choose(map='USA',panel='strong',players=3,policy=p) for p in r.POLICIES]
        a,b=self.collect(tasks,1),self.collect(tasks,3)
        for out in a+b:
            for k in ('seconds','featureMs','referenceMs','inferenceMs'):out.pop(k)
        self.assertEqual(a,b);self.restored()
        t=terminal(tasks[0]);t['counts']['replica1']['Resources']=1
        with self.assertRaises(ValueError):r._terminal(t,tasks[0])

    def test_fail_closed_observations_reference_outputs_and_counter_poison(self):
        tasks=[choose(map='USA',panel='strong',players=2)]
        for change in [lambda s:s.update(expertRequired=False),lambda s:s.update(controller='expert24'),
                       lambda s:s.update(phase='Resources'),lambda s:s.update(revision=True),
                       lambda s:s['observation'].update(targets=[1,0]),
                       lambda s:s['observation']['prior'].__setitem__(0,float('nan')),
                       lambda s:s['observation']['actionCity'].__setitem__(0,.5)]:
            Bridge.mutate=staticmethod(change)
            with self.assertRaises(ValueError):self.collect(tasks)
            self.restored()
        Bridge.mutate=None
        Bridge.end_mutate=staticmethod(lambda t:t['publicChecks'].update(expertAtomicLegal=1))
        with self.assertRaises(ValueError):self.collect(tasks)
        self.restored();Bridge.end_mutate=None
        germany=[choose(map='Germany',panel='strong',players=2,focalSeat=1)]
        with mock.patch.object(Reference,'decide',return_value={'index':0,'move':{}}):
            with self.assertRaises(ValueError):self.collect(germany)
        self.restored()

    def test_public_terminal_typed_caps_and_model_nan(self):
        spec=choose(map='USA',panel='strong',players=2)
        for change in [lambda s:s.update(steps=4001),lambda s:s.update(rounds=True),
                       lambda s:s.update(credit=[True,False]),lambda s:s.update(credit=[.6,.4]),
                       lambda s:s['counts']['replica1'].update(Auction=True),
                       lambda s:s['publicChecks'].update(expertAtomicLegal=1)]:
            t=terminal(spec);change(t)
            with self.assertRaises(ValueError):r._terminal(t,spec)
        with mock.patch.object(self.models['replica1'],'forward',return_value=(torch.full((1,6),float('nan')),torch.zeros(1))):
            with self.assertRaisesRegex(ValueError,'Nonfinite'):self.collect([spec],1)
        self.restored()

    def test_frozen_protocol_after_mutation_and_old_guards_stay_unmodified(self):
        import stress_rollout as old
        old_before=copy.deepcopy(old.PROTOCOL)
        for key,value in [('fitting',0),('selection',True),('dealsPerCell',4),('games',15361)]:
            with mock.patch.dict(r.PROTOCOL,{key:value}):
                with self.assertRaisesRegex(ValueError,'Frozen'):r.plans()
        with self.assertRaises(ValueError):old.validate_tasks([r.plans(True)[0]])
        self.assertEqual(old.PROTOCOL,old_before)
        self.assertIsNot(r._counts.__globals__,old._counts.__globals__)

    def test_fresh_import_rejects_mutated_pin_without_touching_sources(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);shutil.copyfile(r.__file__,root/Path(r.__file__).name)
            for name in r.FROZEN_SOURCES:shutil.copyfile(r.HERE/name,root/name)
            protocol_path=root/'replica-stress-protocol-v1.json'
            shutil.copyfile(r.HERE/protocol_path.name,protocol_path)
            env=dict(os.environ,PYTHONPATH=str(r.HERE))
            def launch():
                script='import sys; sys.path.insert(0,sys.argv[1]); import stress_rollout; sys.path.pop(0); import replica_stress_rollout_v1'
                return subprocess.run([sys.executable,'-B','-c',script,str(r.HERE)],cwd=root,
                    env=env,text=True,capture_output=True,timeout=30)
            good=launch();self.assertEqual(good.returncode,0,good.stderr)
            protocol=copy.deepcopy(r.PROTOCOL);protocol['replicas'][1]['update']=24
            protocol_path.write_text(json.dumps(protocol))
            result=launch()
            self.assertNotEqual(result.returncode,0);self.assertIn('Frozen replica stress protocol',result.stderr)

    def test_complete_configs_bind_unchanged_original_and_each_replica_with_six_workers(self):
        import builtins, types
        calls=[]
        def expert(smoke,**kwargs):
            calls.append(('expert',smoke,kwargs));return {'complete':'original'}
        class Replica:
            def __init__(self,number):self.number=number;self.protocol={'replica':number}
            def config(self,smoke,*,protocol,**kwargs):
                assert protocol==self.protocol
                calls.append(('replica'+str(self.number),smoke,kwargs))
                return {'complete':'replica'+str(self.number)}
        def old(smoke,protocol):return {'complete':'ppo'+str(protocol['replica'])}
        modules={'expert_ppo':SimpleNamespace(config=expert),
                 'expert_replicas_v1':SimpleNamespace(Replica=Replica),
                 'ppo':SimpleNamespace(config=old,make_protocol=lambda n:{'replica':n})}
        def importing(name,*args,**kwargs):
            return modules[name] if name in modules else builtins.__import__(name,*args,**kwargs)
        namespace=dict(r.__dict__,__builtins__=dict(vars(builtins),__import__=importing))
        bound=types.FunctionType(r.serving_configs.__code__,namespace,'serving_configs',r.serving_configs.__defaults__)
        configs=bound('retained','retained-python')
        self.assertEqual(set(configs),set(r.MODELS))
        self.assertEqual(calls,[(name,False,dict(artifact='retained',reference_python='retained-python',workers=6))
                                for name in ('expert','replica1','replica2')])


    def test_ppo0_complete_historical_config_is_git_pinned_not_copied_from_checkpoint(self):
        import hashlib
        from ppo import config, make_protocol
        current=config(False,make_protocol(0))  # Pure source/generator hashing; no models or games.
        serving={name:{'fixture':name} for name in r.MODELS};serving['ppo0']=current
        expected=r._saved_configs(serving)
        history=r.PROTOCOL['ppo0HistoricalTraining']
        self.assertEqual(history['sourceGit'],'a3b492b650dec51c34b6f9322d87088b1e863f0e')
        for name,sha in expected['ppo0']['sourceFiles'].items():
            raw=subprocess.check_output(['git','show',history['sourceGit']+':ai/multimap/'+name],cwd=r.ROOT)
            self.assertEqual(hashlib.sha256(raw).hexdigest(),sha)
        self.assertEqual(sorted(name for name in current['sourceFiles'] if
            current['sourceFiles'][name]!=expected['ppo0']['sourceFiles'][name]),['ppo.py','rollout.py'])
        for key in set(current)-{'sourceFiles'}:self.assertEqual(current[key],expected['ppo0'][key])
        self.assertEqual(expected['ppo1'],serving['ppo1'])
        with mock.patch.object(r,'serving_configs',return_value=serving):
            provenance=r.model_provenance()
        self.assertEqual(provenance['ppo0']['config'],current)
        self.assertEqual(provenance['ppo0']['checkpointConfig'],expected['ppo0'])
        self.assertNotIn('servingConfig',provenance['ppo0'])
        self.assertEqual(provenance['ppo0']['historicalTrainingSource'],history)
        altered=copy.deepcopy(serving);altered['ppo0']['sourceFiles']['ppo.py']='arbitrary'
        with self.assertRaises(ValueError):r._saved_configs(altered)
        altered=copy.deepcopy(serving);altered['ppo0']['sourceFiles']['model.py']='arbitrary'
        with self.assertRaises(ValueError):r._saved_configs(altered)


class Loaders(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.pins={p['name']:p for p in r.model_pins()}
        self.paths={name:self.root/(name+'.pt') for name in r.MODELS}
        for name,path in self.paths.items():path.write_bytes(name.encode())
        self.meta={name:SimpleNamespace(commit_hash=p['revision'],size=self.paths[name].stat().st_size) for name,p in self.pins.items()}
        self.models={name:GreedyModel(name) for name in r.MODELS}
        self.configs={name:dict(identity=name,complete=True) for name in r.MODELS}
        from residual import SCHEMA
        self.saved={name:dict(schema=r.EXPERT_SCHEMA if name in r.EXPERT_MODELS else SCHEMA,
            update=p['update'],width=64,bound=16 if name in r.EXPERT_MODELS else 8,
            config=self.configs[name],**(dict(stage='train',priorAsActionFeature=True) if name in r.EXPERT_MODELS else {}))
            for name,p in self.pins.items()}
        urls={r.hf_hub_url(p['repo'],p['path'],revision=p['revision']):n for n,p in self.pins.items()}
        remote={(p['repo'],p['path'],p['revision']):n for n,p in self.pins.items()}
        self.events=[];actual_digest=r.digest
        def meta(url):
            name=urls[url];self.events.append(('metadata',name));return self.meta[name]
        def download(repo,path,*,revision):
            name=remote[repo,path,revision];self.events.append(('download',name));return self.paths[name]
        def sha(path):
            p=Path(path);return self.pins[p.stem]['sha256'] if p in self.paths.values() else actual_digest(p)
        def load(path):
            name=Path(path).stem;return self.models[name],self.saved[name]
        self.patches=[mock.patch.object(r,'get_hf_file_metadata',side_effect=meta),
            mock.patch.object(r,'hf_hub_download',side_effect=download),mock.patch.object(r,'digest',side_effect=sha),
            mock.patch.object(r,'model_configs',return_value=self.configs),
            mock.patch.object(r,'load_expert',side_effect=load),mock.patch.object(r,'load_old',side_effect=load)]
        self.mocks=[p.start() for p in self.patches]
    def tearDown(self):
        for p in reversed(self.patches):p.stop()
        self.tmp.cleanup()

    def test_metadata_all_six_before_any_download_and_full_configs(self):
        actual=r.load_models('artifact','reference-python')
        self.assertEqual(actual,self.models)
        self.assertEqual(self.events,[('metadata',n) for n in r.MODELS]+[('download',n) for n in r.MODELS])
        self.mocks[3].assert_called_once_with('artifact','reference-python')
        self.assertTrue(all(not m.training and not any(p.requires_grad for p in m.parameters()) for m in actual.values()))

    def test_retained_local_expert_and_replicas_are_size_hash_verified_no_cache_assumption(self):
        local={name:self.paths[name] for name in r.EXPERT_MODELS}
        r.prefetch(local_checkpoints=local)
        self.assertEqual(self.events,[('metadata',n) for n in r.MODELS]+[('download',n) for n in r.FROZEN])
        swapped=dict(local,replica1=local['replica2'])
        with self.assertRaisesRegex(ValueError,'hash|size'):r.load_models(local_checkpoints=swapped)
        with self.assertRaises(ValueError):r.load_models(local_checkpoints={'ppo2':self.paths['ppo2']})
        self.paths['expert24'].write_bytes(b'wrong size')
        with self.assertRaisesRegex(ValueError,'size/hash'):r.load_models(local_checkpoints=local)

    def test_every_metadata_size_and_revision_rejected_before_any_download(self):
        for name in r.MODELS:
            meta=self.meta[name];size=meta.size
            for bad in (None,-1,0,True,1.0,16*1024**2+1):
                meta.size=bad
                with self.subTest(name=name,bad=bad),self.assertRaises(ValueError):r.load_models()
                self.mocks[1].assert_not_called();self.mocks[4].assert_not_called()
            meta.size=size;meta.commit_hash='main'
            with self.assertRaises(ValueError):r.load_models()
            meta.commit_hash=self.pins[name]['revision']

    def test_role_full_config_update_width_bound_finite_strict_for_every_model(self):
        for name in r.MODELS:
            original=copy.deepcopy(self.saved[name])
            for patch in ({'update':True},{'update':99},{'width':64.0},{'bound':True},{'config':{'wrong':name}},{'schema':'wrong'}):
                self.saved[name]=dict(original,**patch)
                with self.subTest(name=name,patch=patch),self.assertRaises(ValueError):r.load_models()
            self.saved[name]=original
        with torch.no_grad():self.models['replica2'].layer.weight.fill_(float('nan'))
        with self.assertRaisesRegex(ValueError,'nonfinite'):r.load_models()

    def test_frozen_legacy_pool_rejected_before_metadata(self):
        changed=copy.deepcopy(r.POOL);changed['members'][2]['update']=16
        with mock.patch.object(r,'POOL',changed),self.assertRaises(ValueError):r.load_models()
        self.mocks[0].assert_not_called()


if __name__=='__main__':unittest.main()
