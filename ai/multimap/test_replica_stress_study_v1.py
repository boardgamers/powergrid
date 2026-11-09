"""Offline three-arm transactions and clustered-statistics fixtures; not study evidence."""
import copy
import json
import math
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import replica_stress_study_v1 as s
import replica_stress_rollout_v1 as rollout
from test_replica_stress_rollout_v1 import outcome
from data import atomic_json, digest


def fake_identity(panel,smoke,workers,artifact,reference_python):
    return dict(schema='unit-only',panel=panel,smoke=smoke,workers=workers,tasks=s.plan(panel,smoke))


def winner(spec, win):
    result=outcome(spec)
    seat=spec['focalSeat'] if win else (spec['focalSeat']+1)%spec['players']
    credit=[int(i==seat) for i in range(spec['players'])]
    result.update(credit=credit[spec['focalSeat']],allSeatCredit=credit)
    return result


class Design(unittest.TestCase):
    def assert_primary_family_only(self,report):
        key='fourPrimaryBonferroniNormal9875'
        def paths(value,prefix=()):
            if isinstance(value,dict):
                for name,item in value.items():
                    if name==key:yield prefix+(name,)
                    yield from paths(item,prefix+(name,))
            elif isinstance(value,list):
                for i,item in enumerate(value):yield from paths(item,prefix+(i,))
        self.assertEqual(set(paths(report)),{('primary',p,key) for p in ('replica1','replica2')})
        for scores in report['subgroups'].values():
            for value in scores.values():self.assertIn('approximateNormal95',value)

    def test_production_smoke_counts_roots_whole_batches(self):
        for panel in ('strong','mixed'):
            tasks=s.plan(panel)
            self.assertEqual(len(tasks),7680);self.assertEqual(len(s.batches(tasks)),640)
            self.assertEqual({len(b) for b in s.batches(tasks)},{6,9,12,15,18})
            smoke=s.plan(panel,True)
            self.assertEqual(len(smoke),99);self.assertEqual(len(s.batches(smoke)),8)
            self.assertEqual({t['players'] for t in smoke},set(range(2,7)))
            self.assertTrue(all(':smoke:' in t['seed'] for t in smoke))
        self.assertFalse({t['seed'] for t in s.plan('strong')}&{t['seed'] for t in s.plan('mixed')})

    def test_equal_cell_ddof1_and_four_comparison_multiplicity(self):
        value=s.estimate({'a':[0,1],'b':[.5,.5]})
        self.assertEqual(value['mean'],.5);self.assertEqual(value['standardError'],.25)
        self.assertEqual(value['fourPrimaryBonferroniNormal9875'],[.5-2.4977054744123737*.25,.5+2.4977054744123737*.25])
        self.assertLess(value['fourPrimaryBonferroniNormal9875'][0],value['approximateNormal95'][0])
        self.assertEqual(s.estimate({'a':[0]*8,'b':[1]*8})['standardError'],0)
        with self.assertRaises(ValueError):s.estimate({'a':[0]})
        self.assertIsNone(s.estimate({'a':[0]},smoke=True)['standardError'])
        self.assertIsNone(s.estimate({'a':[0,1]},smoke=True)['fourPrimaryBonferroniNormal9875'])
        for bad in ({},{'a':[]},{'a':[True,0]},{'a':[float('nan'),0]}):
            with self.assertRaises(ValueError):s.estimate(bad)

    def test_all_arms_paired_covariance_is_used_not_independent_standard_errors(self):
        games=[]
        for spec in s.plan('mixed'):
            win=spec['deal']%2==0
            if spec['policy']=='replica2':win=not win
            games.append(winner(spec,win))
        report=s.analyze(games,'mixed')
        self.assert_primary_family_only(report)
        self.assertGreater(report['subgroups']['allMaps']['replica1']['standardError'],0)
        self.assertEqual(report['primary']['replica1']['mean'],0)
        self.assertEqual(report['primary']['replica1']['standardError'],0)
        self.assertAlmostEqual(report['primary']['replica2']['standardError'],math.sqrt(1/(7*80)))
        self.assertEqual(report['sharedPpo2Games'],2560)
        self.assertEqual(report['primary']['replica1']['independentDeals'],640)
        self.assertFalse(report['winnerSelection']);self.assertFalse(report['automaticProgression'])
        self.assertNotIn('panelResearchProgressionGate',report)
        sparse=False
        for scores in report['strongOpponentOccupancy'].values():
            for value in scores.values():
                sparse |= 1 in value['selectedDealsByCell'].values()
                self.assertIsNotNone(value['standardError'])
                self.assertEqual(value['independentDeals'],8*value['cells'])
        self.assertTrue(sparse)

    def test_cell_weighting_not_player_count_weighting_and_no_old_homogeneous_assertion(self):
        games=[]
        for spec in s.plan('strong'):
            win=(spec['players']==2 if spec['policy']=='replica1' else
                 spec['map']=='Germany' if spec['policy']=='replica2' else False)
            games.append(winner(spec,win))
        report=s.analyze(games,'strong')
        self.assert_primary_family_only(report)
        self.assertAlmostEqual(report['primary']['replica1']['mean'],.2)
        self.assertAlmostEqual(report['primary']['replica2']['mean'],.25)
        self.assertEqual(len([k for k in report['subgroups'] if k.startswith('cell:')]),80)
        self.assertEqual(len([k for k in report['subgroups'] if k.startswith('mapPlayers:')]),20)
        self.assertEqual(len(report['reciprocalTwoPlayerOutcomes']),128)
        self.assertEqual(report['GermanyAnalyticalReferenceBenchmark']['benchmark'],.29)
        self.assertEqual(report['GermanyAnalyticalReferenceBenchmark']['newlyPlayedReferenceControlGames'],0)
        self.assertNotIn('homogeneousExpertDealControls',report)
        self.assertEqual(set(report['watchpoints']),set(s.PROTOCOL['watchpoints']))
        for key,value in report['watchpoints'].items():self.assertEqual(value,report['subgroups'][key])

    def test_seat_then_deal_aggregation_and_smoke_descriptive_only(self):
        games=[]
        for spec in s.plan('strong'):
            games.append(winner(spec,spec['policy']!='ppo2' and spec['focalSeat']==0))
        report=s.analyze(games,'strong')
        self.assertAlmostEqual(report['primary']['replica1']['mean'],.29)
        for panel in ('strong','mixed'):
            report=s.analyze([outcome(t) for t in s.plan(panel,True)],panel,True)
            self.assert_primary_family_only(report)
            self.assertEqual(report['games'],99);self.assertEqual(report['sharedPpo2Games'],33)
            self.assertTrue(report['descriptiveOnly'])
            self.assertEqual(set(report['watchpoints']),{'cell:Germany|2|recharged|1','cell:USA|3|recharged|1'})
            for p in ('replica1','replica2'):
                self.assertIsNone(report['primary'][p]['standardError'])
                self.assertIsNone(report['primary'][p]['approximateNormal95'])
                self.assertIsNone(report['primary'][p]['fourPrimaryBonferroniNormal9875'])

    def test_no_missing_arm_duplicate_control_or_partial_production_inference(self):
        tasks=s.plan('mixed',True);games=[outcome(t) for t in tasks]
        for bad in (games[:-1],list(reversed(games)),games+[games[2]],games[:1]+games[2:]):
            with self.assertRaises(ValueError):s.analyze(bad,'mixed',True)
        with self.assertRaises(ValueError):s.analyze(games,'mixed')
        tasks=s.batches(tasks)[0]
        record=dict(schema='multimap-replica-stress-batch-v1',index=0,taskSha256=s.task_hash(tasks),games=[outcome(t) for t in tasks])
        s.verify_batch(record,0,tasks)
        for k,v in [('index',True),('taskSha256','wrong'),('extra',1)]:
            bad=copy.deepcopy(record);bad[k]=v
            with self.assertRaises(ValueError):s.verify_batch(bad,0,tasks)
        for bad in (tasks[:-1],tasks+[tasks[2]],tasks[::3]):
            forged=dict(record,taskSha256=s.task_hash(bad),games=[outcome(t) for t in bad])
            with self.assertRaises(ValueError):s.verify_batch(forged,0,bad)
        record['games'][0]['publicChecks']['expertAtomicLegal']=1
        with self.assertRaises(ValueError):s.verify_batch(record,0,tasks)

    def test_fixed_source_identity_list_and_full_six_provenance(self):
        expected=('replica-stress-protocol-v1.json','replica_stress_game_v1.cjs','replica_stress_rollout_v1.py',
            'replica_stress_study_v1.py','job_replica_stress_v1.py','launch_replica_stress_v1.py',
            'preflight_replica_stress_v1.py','test_replica_stress_v1.cjs','test_replica_stress_rollout_v1.py',
            'test_replica_stress_study_v1.py','test_job_replica_stress_v1.py','test_launch_replica_stress_v1.py',
            'test_preflight_replica_stress_v1.py')
        self.assertEqual(s.SOURCE_NAMES,expected)
        # Missing planned peer files are never silently omitted by real identity.
        provenance={name:dict(pin={'name':name},config={'runtime':'A'}) for name in rollout.MODELS}
        with mock.patch.object(s,'model_provenance',return_value=provenance),mock.patch.object(s,'digest',side_effect=lambda p:'unit:'+Path(p).name):
            first=s.identity('strong',True,6,s.ARTIFACT,s.REFERENCE_PYTHON)
            self.assertEqual(set(first['sourceFiles']),set(expected))
            self.assertEqual(first['modelProvenance'],provenance)
            provenance['replica2']['config']['runtime']='B'
            second=s.identity('strong',True,6,s.ARTIFACT,s.REFERENCE_PYTHON)
            self.assertEqual(second['modelProvenance']['replica2']['config']['runtime'],'B')
        self.assertEqual(set(rollout.model_pins()[2]),{'name','id','repo','revision','path','sha256','update'})

    def test_independent_old_hashes_budget_and_protocol_flags(self):
        import subprocess,hashlib
        for name,sha in rollout.FROZEN_SOURCES.items():
            raw=subprocess.check_output(['git','show','6a7cdc6:ai/multimap/'+name],cwd=rollout.ROOT)
            self.assertEqual(hashlib.sha256(raw).hexdigest(),sha)
            self.assertEqual(digest(rollout.HERE/name),sha)
        self.assertEqual(s.PROTOCOL['jobBudget'],dict(initialHours=dict(strong=6,mixed=3),recoveryHours=3,maxRecoveryJobs=1,maxJobs=3,maxTotalJobHours=12))
        replay=[t for t in rollout.plans() if any(all(t[k]==v for k,v in scope.items())
                for scope in s.PROTOCOL['postRunReplayScopes'])]
        self.assertEqual(len(replay),48)
        self.assertEqual(s.PROTOCOL['postRunReplayGames'],48)
        self.assertEqual(s.PROTOCOL['replayTimingExceptions'],['featureMs','inferenceMs','referenceMs','seconds'])
        self.assertEqual(s.PROTOCOL['checkpointAggregateMaxBytes'],6*16*1024**2)
        self.assertEqual(s.PROTOCOL['sourceArchiveMaxBytes'],128*1024**2)
        self.assertEqual(s.PROTOCOL['sourceExpandedMaxBytes'],256*1024**2)
        for k in ('fitting','selection','qualificationEligible','reservedFinalSeedsUsed'):self.assertIs(s.PROTOCOL[k],False)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            with self.assertRaises(ValueError):s.artifact_budget(root,64*1024**2+1)
            (root/'bad').symlink_to('/tmp')
            with self.assertRaises(ValueError):s.artifact_budget(root)
        for args in [('other',False),('mixed',1)]:
            with self.assertRaises(ValueError):s.plan(*args)


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
        executions=0
        for panel in ('strong','mixed'):
            uninterrupted=self.root/(panel+'-one');resumed=self.root/(panel+'-two')
            one=s.run(uninterrupted,panel,smoke=True)
            self.assertIsNone(s.run(resumed,panel,smoke=True,stop_after_batches=1))
            before=digest(resumed/'batch-000.json')
            executions+=sum(len(call.args[0]) for call in self.mocks[-1].call_args_list)
            self.mocks[-1].reset_mock()
            two=s.run(resumed,panel,smoke=True)
            self.assertEqual(self.mocks[-1].call_count,7);self.assertEqual(one,two)
            self.assertEqual(before,digest(resumed/'batch-000.json'))
            self.assertEqual({p.name:digest(p) for p in uninterrupted.iterdir()},{p.name:digest(p) for p in resumed.iterdir()})
            executions+=sum(len(call.args[0]) for call in self.mocks[-1].call_args_list)
            self.mocks[-1].reset_mock();self.mocks[-2].reset_mock()
            self.assertEqual(two,s.run(resumed,panel,smoke=True))
            self.mocks[-1].assert_not_called();self.mocks[-2].assert_not_called()
        self.assertEqual(executions,396)
    def test_partial_three_arm_batch_never_committed_or_counted(self):
        s.run(self.root,'mixed',smoke=True,stop_after_batches=1)
        before=digest(self.root/'batch-000.json')
        self.mocks[-1].side_effect=lambda tasks,*a,**k:[outcome(t) for t in tasks[:-1]]
        with self.assertRaises(ValueError):s.run(self.root,'mixed',smoke=True)
        self.assertFalse((self.root/'batch-001.json').exists())
        self.mocks[-1].side_effect=lambda tasks,*a,**k:[outcome(t) for t in tasks]
        result=s.run(self.root,'mixed',smoke=True)
        self.assertEqual(result['games'],99);self.assertEqual(before,digest(self.root/'batch-000.json'))
    def test_output_rejects_reference_or_model_cache_nesting_before_collection(self):
        with self.assertRaisesRegex(ValueError,'nonnested'):
            s.run(self.root,'mixed',smoke=True,artifact=self.root/'retained')
        self.mocks[-1].assert_not_called()
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
        self.assertEqual(result['games'],99)
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


if __name__=='__main__':unittest.main()
