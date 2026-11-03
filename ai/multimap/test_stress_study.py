"""Offline transaction/statistics/job guards. Synthetic games are NOT evidence."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import stress_study as s
import stress_rollout as rollout
import job_stress as job
from data import atomic_json, digest


def outcome(spec):
    spec=copy.deepcopy(spec);counts={c:dict.fromkeys(rollout.PHASES,0) for c in rollout.CONTROLLERS}
    seats=[]
    for controller in spec['controllers']:
        seats.append(dict.fromkeys(rollout.PHASES,1))
        for phase in rollout.PHASES:
            actor=controller
            if controller in rollout.MODELS and phase in ('Resources','Bureaucracy'):
                actor='fixedV2' if controller=='expert24' else 'fixedV1'
            counts[actor][phase]+=1
    requests={c:sum(counts[c].values()) for c in rollout.MODELS}
    ref=sum(counts['reference'].values())
    credits=[1]+[0]*(spec['players']-1)
    return dict(spec=spec,terminal=True,credit=credits[spec['focalSeat']],allSeatCredit=credits,
        steps=4*spec['players'],rounds=1,counts=counts,seatCounts=seats,
        publicChecks=dict(hiddenInvariant=ref,referenceAtomicLegal=ref,fullMenuPrior=sum(requests.values()),expertAtomicLegal=0),
        policyRequests=requests,referenceRequests=ref,featureMs=0.,inferenceMs=0.,referenceMs=0.,seconds=0.)


def fake_identity(panel,smoke,workers,artifact,reference_python):
    return dict(schema='unit-only',panel=panel,smoke=smoke,workers=workers,tasks=s.plan(panel,smoke))


class Design(unittest.TestCase):
    def test_frozen_panel_sizes_and_independent_roots(self):
        strong=s.plan('strong');mixed=s.plan('mixed')
        self.assertEqual(len(strong),2560);self.assertEqual(len(mixed),2560)
        self.assertEqual(len(s.batches(strong)),320)
        self.assertFalse({x['seed'] for x in strong}&{x['seed'] for x in mixed})
        self.assertEqual({x['map'] for x in strong},set(s.PROTOCOL['maps']))
        self.assertEqual({len(x) for x in s.batches(strong)},{4,6,8,10,12})
    def test_smoke_all_counts_rules_maps_no_production(self):
        for panel in ('strong','mixed'):
            tasks=s.plan(panel,True)
            self.assertEqual(len(tasks),60);self.assertEqual(len(s.batches(tasks)),8)
            self.assertEqual({t['players'] for t in tasks},set(range(2,7)))
            self.assertEqual({(t['variant'],t['fastBid']) for t in tasks},{('original',False),('original',True),('recharged',False),('recharged',True)})
            self.assertTrue(all(':smoke:' in t['seed'] for t in tasks))
    def test_actual_new_source_hashes_and_runtime_identity_participate(self):
        with mock.patch.object(s,'expert_config',return_value={'runtime':'A'}):
            first=s.identity('strong',True,6,s.ARTIFACT,s.REFERENCE_PYTHON)
        self.assertEqual(first['sourceFiles'],{name:digest(s.HERE/name) for name in s.SOURCE_NAMES})
        self.assertIn('preflight_stress.py',first['sourceFiles'])
        with mock.patch.object(s,'expert_config',return_value={'runtime':'B'}):
            second=s.identity('strong',True,6,s.ARTIFACT,s.REFERENCE_PYTHON)
        self.assertNotEqual(first,second)
        real_digest=s.digest
        with mock.patch.object(s,'expert_config',return_value={'runtime':'A'}),mock.patch.object(s,'digest',side_effect=lambda p:'changed' if Path(p).name=='stress_game.cjs' else real_digest(p)):
            self.assertNotEqual(first,s.identity('strong',True,6,s.ARTIFACT,s.REFERENCE_PYTHON))
    def test_unknown_panel_and_nonboolean_smoke(self):
        for args in [('Italy',False),('strong',1)]:
            with self.assertRaises(ValueError):s.plan(*args)
    def test_equal_cell_unbiased_variance_bonferroni(self):
        r=s.estimate({'a':[0,1],'b':[.5,.5]})
        self.assertEqual(r['mean'],.5);self.assertEqual(r['standardError'],.25)
        self.assertLess(r['twoPrimaryBonferroniNormal975'][0],r['approximateNormal95'][0])
        self.assertEqual(s.estimate({'a':[0,0],'b':[1,1]})['standardError'],0)
    def test_single_deal_smoke_has_no_uncertainty_or_gate(self):
        games=[outcome(x) for x in s.plan('strong',True)]
        report=s.analyze(games,'strong',True)
        self.assertIsNone(report['primary']['standardError'])
        self.assertFalse(report['panelResearchProgressionGate'])
        self.assertEqual(report['homogeneousExpertDealControls'],3)
    def test_complete_paired_full_grid_statistics(self):
        report=s.analyze([outcome(x) for x in s.plan('strong')],'strong')
        self.assertEqual(report['primary']['mean'],0)
        self.assertAlmostEqual(report['subgroups']['allMaps']['expert24']['mean'],.29)
        self.assertEqual(report['primary']['independentDeals'],320)
        self.assertEqual(report['GermanyAnalyticalReferenceBenchmark']['selectedMinusNeutral']['mean'],0)
        self.assertEqual(len(report['reciprocalTwoPlayerOutcomes']),64)
        self.assertTrue(all(x['expert24ByFocalSeat']==[1,0] for x in report['reciprocalTwoPlayerOutcomes']))
    def test_homogeneous_symmetry_is_required_not_strength(self):
        games=[outcome(x) for x in s.plan('strong',True)]
        target=next(r for r in games if r['spec']['map']=='USA' and r['spec']['policy']=='expert24' and r['spec']['focalSeat']==1)
        target['rounds']=2
        with self.assertRaisesRegex(ValueError,'symmetry'):s.analyze(games,'strong',True)
    def test_no_partial_or_reordered_outcomes(self):
        games=[outcome(x) for x in s.plan('mixed',True)]
        with self.assertRaises(ValueError):s.analyze(games[:-1],'mixed',True)
        with self.assertRaises(ValueError):s.analyze(list(reversed(games)),'mixed',True)
    def test_batch_hash_fields_and_counter_poison(self):
        tasks=s.batches(s.plan('mixed',True))[0]
        record=dict(schema='multimap-stress-batch-v1',index=0,taskSha256=s.task_hash(tasks),games=[outcome(t) for t in tasks])
        s.verify_batch(record,0,tasks)
        for k,v in [('index',True),('taskSha256','wrong'),('extra',1)]:
            bad=copy.deepcopy(record);bad[k]=v
            with self.assertRaises(ValueError):s.verify_batch(bad,0,tasks)
        record['games'][0]['publicChecks']['expertAtomicLegal']=1
        with self.assertRaises(ValueError):s.verify_batch(record,0,tasks)


class Transactions(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.patches=[mock.patch.object(s,'identity',side_effect=fake_identity),mock.patch.object(s,'load_models',return_value={'unit':True}),
                      mock.patch.object(s,'collect',side_effect=lambda tasks,*a,**k:[outcome(t) for t in tasks])]
        self.mocks=[p.start() for p in self.patches]
    def tearDown(self):
        for p in reversed(self.patches):p.stop()
        self.tmp.cleanup()
    def test_exact_interrupted_resume_no_repeated_batches(self):
        uninterrupted=self.root/'one';resumed=self.root/'two'
        one=s.run(uninterrupted,'mixed',smoke=True)
        self.assertIsNone(s.run(resumed,'mixed',smoke=True,stop_after_batches=2))
        before=[digest(resumed/f'batch-{i:03}.json') for i in range(2)]
        self.mocks[-1].reset_mock()
        two=s.run(resumed,'mixed',smoke=True)
        self.assertEqual(self.mocks[-1].call_count,6);self.assertEqual(one,two)
        self.assertEqual(before,[digest(resumed/f'batch-{i:03}.json') for i in range(2)])
        self.assertEqual({p.name:digest(p) for p in uninterrupted.iterdir()},{p.name:digest(p) for p in resumed.iterdir()})
        self.mocks[-1].reset_mock();self.mocks[-2].reset_mock()
        self.assertEqual(two,s.run(resumed,'mixed',smoke=True))
        self.mocks[-1].assert_not_called();self.mocks[-2].assert_not_called()
    def test_resume_rejects_wrong_panel_source_workers(self):
        s.run(self.root,'mixed',smoke=True,stop_after_batches=1)
        for kwargs in [dict(panel='strong'),dict(panel='mixed',workers=2)]:
            with self.assertRaisesRegex(ValueError,'identity'):s.run(self.root,smoke=True,**kwargs)
    def test_runtime_source_or_task_identity_change_rejects_resume(self):
        s.run(self.root,'mixed',smoke=True,stop_after_batches=1)
        for key in ('runtime','sourceFiles','protocol','tasks'):
            def changed(*args,**kwargs):
                value=fake_identity(*args,**kwargs);value[key]='changed';return value
            self.mocks[0].side_effect=changed
            with self.assertRaisesRegex(ValueError,'identity'):s.run(self.root,'mixed',smoke=True)
        self.mocks[0].side_effect=fake_identity
    def test_orphan_plan_temporary_write_is_not_consumed(self):
        (self.root/'plan.json.tmp').write_text('{incomplete')
        self.assertIsNone(s.run(self.root,'mixed',smoke=True,stop_after_batches=0))
        self.assertFalse((self.root/'plan.json.tmp').exists())
        self.assertEqual(s.read(self.root/'plan.json')['tasks'],s.plan('mixed',True))
    def test_corrupt_saved_counter_is_rejected(self):
        s.run(self.root,'mixed',smoke=True,stop_after_batches=1)
        p=self.root/'batch-000.json';r=s.read(p);r['games'][0]['steps']+=1;atomic_json(p,r)
        with self.assertRaises(ValueError):s.run(self.root,'mixed',smoke=True)
    def test_noncontiguous_or_orphan_artifacts_rejected(self):
        s.run(self.root,'mixed',smoke=True,stop_after_batches=2)
        (self.root/'batch-000.json').unlink()
        with self.assertRaisesRegex(ValueError,'Noncontiguous'):s.run(self.root,'mixed',smoke=True)
        (self.root/'plan.json').unlink()
        with self.assertRaisesRegex(ValueError,'without frozen'):s.run(self.root,'mixed',smoke=True)
    def test_interrupted_temporary_batch_is_never_consumed(self):
        s.run(self.root,'mixed',smoke=True,stop_after_batches=1)
        (self.root/'batch-001.json.tmp').write_text('{uncommitted')
        result=s.run(self.root,'mixed',smoke=True)
        self.assertEqual(result['games'],60)
        self.assertFalse((self.root/'batch-001.json.tmp').exists())
    def test_summary_cannot_select_or_hide_partial_data(self):
        s.run(self.root,'mixed',smoke=True)
        p=self.root/'summary.json';r=s.read(p);r['qualified']=True;atomic_json(p,r)
        with self.assertRaisesRegex(ValueError,'summary mismatch'):s.run(self.root,'mixed',smoke=True)
    def test_collection_failure_not_retried_or_committed(self):
        self.mocks[-1].side_effect=RuntimeError('unit transport stopped')
        with self.assertRaises(RuntimeError):s.run(self.root,'mixed',smoke=True)
        self.assertEqual(self.mocks[-1].call_count,1)
        self.assertEqual([p.name for p in self.root.iterdir()],['plan.json'])


class Worker(unittest.TestCase):
    def test_whitelist_no_raw_data_or_unbounded_filenames(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);atomic_json(p/'protocol.json',{'safe':True})
            self.assertEqual(set(job.compact_files(p)),{'protocol.json'})
            atomic_json(p/'protocol.json',{'nested':[{'observation':{}}]})
            with self.assertRaises(ValueError):job.compact_files(p)
        for extra in ['study/batch-320.json','../secret','study/model.pt']:
            with self.assertRaises(ValueError):job.validate_manifest({'study/plan.json':'a'*64,extra:'b'*64})
    def test_known_temps_never_uploaded_and_raw_packets_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);atomic_json(p/'study/plan.json',{'safe':True})
            (p/'study/batch-000.json.tmp').write_text('{partial')
            self.assertEqual(set(job.compact_files(p)),{'study/plan.json'})
            for payload in [{'state':{'secret':1}},{'move':{'name':'Bid'}},{'rows':[]},{'response':{'requestId':'bad'}}]:
                atomic_json(p/'study/batch-000.json',payload)
                with self.assertRaises(ValueError):job.compact_files(p)
    def test_resume_metadata_before_payloads_and_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);remote=p/'remote';remote.mkdir();files={}
            for name,data in [('study/plan.json',b'{}'),('study/batch-000.json',b'{"unit":true}')]:
                f=remote/Path(name).name;f.write_bytes(data);files[name]=f
            atomic_json(remote/'manifest.json',{n:digest(f) for n,f in files.items()});events=[]
            def size(repo,name,revision,**kwargs):
                events.append(('size',name));return (remote/'manifest.json').stat().st_size if name.endswith('artifacts.json') else files[name.split('runs/unit/')[1]].stat().st_size
            def download(repo,name,**kwargs):
                events.append(('download',name));return str(remote/'manifest.json') if name.endswith('artifacts.json') else str(files[name.split('runs/unit/')[1]])
            with mock.patch.object(job.shared,'remote_size',side_effect=size),mock.patch('huggingface_hub.hf_hub_download',side_effect=download):
                job.restore_resume('repo','unit','a'*40,p/'out',p/'cache')
                first=next(i for i,e in enumerate(events) if e[0]=='download' and not e[1].endswith('artifacts.json'))
                self.assertEqual(sum(e[0]=='size' for e in events[:first]),3)
                files['study/batch-000.json'].write_text('bad')
                with self.assertRaisesRegex(ValueError,'hash/size'):job.restore_resume('repo','unit','a'*40,p/'out2',p/'cache')
    def test_json_duplicate_and_nonfinite_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'x.json'
            for value in ['{"x":1,"x":2}','{"x":NaN}']:
                p.write_text(value)
                with self.assertRaises(ValueError):s.read(p)
    def test_budget_and_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)
            with self.assertRaises(ValueError):s.artifact_budget(p,64*1024**2+1)
            (p/'bad').symlink_to('/tmp')
            with self.assertRaises(ValueError):job.compact_files(p)
    def test_resume_submission_reuses_original_source_and_no_repackage(self):
        import launch_stress as launch
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);receipt=root/'launch.json';manifest=root/'manifest.json'
            env=dict(RUN_ID='multimap-unit-strong',STRESS_PANEL='strong',SOURCE_REVISION='b'*40,SOURCE_SHA256='c'*64)
            original=dict(run=env['RUN_ID'],panel='strong',sourceCommit='a'*40,jobId='unit-old',
                env=env,image='unit-image',flavor='cpu-upgrade')
            atomic_json(receipt,original);atomic_json(manifest,{'study/plan.json':'d'*64})
            import shlex
            command=['bash','-lc','python -m pip install --no-cache-dir --disable-pip-version-check huggingface_hub==1.29.0 && python -c '+shlex.quote(launch.BOOTSTRAP)]
            api=mock.Mock();api.inspect_job.return_value=SimpleNamespace(environment=env,docker_image='unit-image',
                flavor='cpu-upgrade',command=command,arguments=[],status=SimpleNamespace(stage='ERROR'))
            api.model_info.return_value.private=True;api.dataset_info.return_value.private=True
            api.file_exists.return_value=False;api.run_job.return_value=SimpleNamespace(id='unit-new')
            with mock.patch.object(launch,'ROOT',root),mock.patch.object(launch,'HfApi',return_value=api),\
                 mock.patch.object(launch,'get_token',return_value='unit-secret-not-printed'),\
                 mock.patch.object(launch.subprocess,'check_output',return_value=Path(launch.__file__).read_text()),\
                 mock.patch('job_neural.remote_size',return_value=1),\
                 mock.patch('huggingface_hub.hf_hub_download',return_value=str(manifest)),\
                 mock.patch.object(launch,'package',side_effect=AssertionError('must not repack')):
                with mock.patch('builtins.print'):
                    result=launch.continue_panel(receipt,'multimap-unit-resumed',revision='e'*40)
                self.assertEqual(result['env']['SOURCE_SHA256'],env['SOURCE_SHA256'])
                self.assertEqual(result['env']['RESUME_REVISION'],'e'*40)
                self.assertEqual(api.run_job.call_args.kwargs['command'],command)
                self.assertNotIn('unit-secret-not-printed',json.dumps(result))
                with self.assertRaises(ValueError):launch.continue_panel(receipt,'multimap-unit-resumed',revision='e'*40)
                with mock.patch('builtins.print'):
                    peer=launch.continue_panel(receipt,'multimap-unit-mixed',missing_panel='mixed')
                self.assertEqual(peer['env']['STRESS_PANEL'],'mixed')
                self.assertNotIn('RESUME_REVISION',peer['env'])
    def test_bootstrap_dispatch_and_manifest_verification(self):
        from launch_stress import BOOTSTRAP
        self.assertIn('ai/multimap/job_stress.py',BOOTSTRAP)
        self.assertIn("set(manifest['files'])",BOOTSTRAP)
        self.assertNotIn('job_expert.py',BOOTSTRAP)


if __name__=='__main__':unittest.main()
