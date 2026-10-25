"""Whole-deal admission, real-record envelopes and nonduplicating coordinator checks."""
import copy
import importlib.util
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from strategic_collection import ROOT,read,write,digest
from opponent_surrogate_collection_v1 import contract

spec=importlib.util.spec_from_file_location('surrogate_coordinator_test',Path(__file__).with_name('coordinate-opponent-surrogate-collection-v1.py'))
coordinator=importlib.util.module_from_spec(spec);spec.loader.exec_module(coordinator)
manager,launcher=coordinator.manager,coordinator.launcher
protocol=read(launcher.PROTOCOL)
ACTUAL=ROOT/'ai/runs/opponent-surrogate-runtime-collected-v1/opponent-surrogate-runtime-v1-2p-0-1/artifacts'


class AdmissionTests(unittest.TestCase):
    def test_all_batch_sizes_preserve_every_game_and_split(self):
        expected={(n,d,s,r) for n in range(2,7) for d in range(32) for s in range(n) for r in range(4)}
        for batch in (1,2,4):
            rows=launcher.case_rows(protocol,batch);seen=set()
            self.assertEqual(len(rows),160//batch)
            for row in rows:
                for d in range(row['start'],row['end']):
                    for s in range(row['players']):
                        for r in range(4):
                            key=(row['players'],d,s,r);self.assertNotIn(key,seen);seen.add(key)
                            self.assertEqual(contract(protocol,*key,'collection')['split'],row['split'])
            self.assertEqual(seen,expected)

    def test_measured_limits_keep_games_whole_and_reject_insufficient_hardware(self):
        cells={str(n):{'games':4*n,'twin_games':4*n,'caps':0,'raw_evidence_bytes':100_000_000,
                      'runtime':{'seconds':1800.,'cpu_seconds':12000.,'sampled_peak_total_rss_bytes':8_000_000_000}}
               for n in (2,6)}
        plan=launcher.measured_admission(cells,32)
        self.assertEqual((plan['deals_per_shard'],plan['timeout_hours'],plan['workers']),(4,6,8))
        large=copy.deepcopy(cells)
        large['6']['raw_evidence_bytes']=12_000_000_000
        self.assertEqual(launcher.measured_admission(large,32)['deals_per_shard'],1)
        for field,value in [('sampled_peak_total_rss_bytes',17_000_000_000),('seconds',20000.)]:
            bad=copy.deepcopy(cells);bad['6']['runtime'][field]=value
            with self.assertRaises(AssertionError):launcher.measured_admission(bad,32)

    def test_missing_calibration_stops_before_plan_or_jobs(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'absent.json'
            with patch.object(launcher,'CALIBRATION',path),patch.object(launcher.runtime,'prerequisites') as source, \
                 patch.object(launcher,'HfApi') as api:
                with self.assertRaisesRegex(AssertionError,'audited and archived'):
                    launcher.prepare(32)
                source.assert_not_called();api.assert_not_called();self.assertFalse(path.exists())


class EnvelopeTests(unittest.TestCase):
    def test_real_rows_through_synthetic_collection_envelope(self):
        # This changes only outer fixture provenance. It is NOT new collection
        # data, never uploaded or eligible for a real training index.
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp)/'artifacts';shutil.copytree(ACTUAL,folder)
            row=next(r for r in launcher.case_rows(protocol,1) if r['players']==2 and r['start']==0)
            state=read(folder/'games/status.json');intent=read(folder/'games/intent.json')
            for blob in (state,intent):
                blob['mode']='collection'
                for task in blob['tasks']:
                    task['mode']='collection'
                    q=contract(protocol,2,0,task['seat'],task['rule'],'collection')
                    task['output']=f"/workspace/ai/runs/{row['case']}/games/game-{q['episode']}"
            for episode,result in state['cases'].items():
                game=folder/'games'/f'game-{episode}'
                q=contract(protocol,2,0,int(episode)//4,int(episode)%4,'collection')
                write(game/'contract.json',q)
                terminal=read(game/'terminal.json');terminal['gameSeed']=q['seed']+'-0';write(game/'terminal.json',terminal)
                result.update(q)
                result['files']={name:digest(game/name) for name in result['files']}
                write(game/'verified.json',result)
            write(folder/'games/status.json',state);write(folder/'games/intent.json',intent)
            job=read(folder/'job.json');job.update(case=row['case'],mode='collection');write(folder/'job.json',job)
            manifest={str(p.relative_to(folder)):digest(p) for p in folder.rglob('*') if p.is_file() and p.name!='manifest.json'}
            write(folder/'manifest.json',manifest)
            evidence={'manifest_sha256':digest(folder/'manifest.json'),'archived_files':len(manifest)+1}
            review=manager.verify_review(folder,row,read(launcher.SOURCE),protocol,evidence)
            self.assertEqual((review['games'],review['teacher_rows'],review['training_rows']),(8,382,382))
            self.assertEqual(review['split_games'],{'train':8})
            bad=copy.deepcopy(row);bad['split']='test'
            with self.assertRaises(AssertionError):manager.verify_review(folder,bad,read(launcher.SOURCE),protocol,evidence)


class CoordinatorTests(unittest.TestCase):
    def run_cycle(self,stage='RUNNING',guard_stage='launched'):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);guards=root/'guards';guards.mkdir()
            plan={'shards':[{'case':c} for c in ('a','b','c')],'admission':{'max_in_flight':2}}
            plan_path=root/'plan.json';write(plan_path,plan)
            for case in ('a','b'):
                write(guards/(case+'.json'),{'stage':guard_stage if case=='b' else 'launched',
                                            'job_id':case,'plan_sha256':digest(plan_path)})
            state={}
            with patch.object(launcher,'PLAN',plan_path),patch.object(launcher,'GUARDS',guards), \
                 patch.object(coordinator,'OUT',root),patch.object(manager,'verified_receipt',side_effect=lambda c: {'verified':True} if c=='a' else None), \
                 patch.object(manager,'inspect',return_value={'case':'b','job_id':'b','authoritative_status':stage}) as inspect, \
                 patch.object(manager,'collect') as collect,patch.object(launcher,'launch') as launch:
                if stage!='RUNNING' or guard_stage!='launched':
                    with self.assertRaises(AssertionError):coordinator.cycle(plan,state,lambda:None)
                    launch.assert_not_called()
                else:
                    self.assertFalse(coordinator.cycle(plan,state,lambda:None))
                    inspect.assert_called_once_with('b');collect.assert_not_called()
                    launch.assert_called_once_with('c',True)
                if guard_stage!='launched':inspect.assert_not_called()

    def test_existing_live_and_verified_jobs_are_not_relaunched(self):self.run_cycle()
    def test_failed_original_job_stops_further_submissions(self):self.run_cycle(stage='ERROR')
    def test_uncertain_submission_stops_before_remote_calls(self):self.run_cycle(guard_stage='launch_unknown')


if __name__=='__main__':unittest.main()
