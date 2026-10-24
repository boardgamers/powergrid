import copy
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from strategic_collection import ROOT,read,digest,write
from population_hybrid_development import PROTOCOL,contract,expected_config,make_plan,validate_plan,runtime_admission


class DevelopmentTests(unittest.TestCase):
    def load(self,name):
        spec=importlib.util.spec_from_file_location(name,ROOT/'ai/strong'/name)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        return module

    def test_all_27_cells_and_five_arms_preserved_at_every_partition(self):
        protocol=read(PROTOCOL)
        for step in [1,2,4]:
            plan=make_plan(protocol,{'protocol_sha256':digest(PROTOCOL)},
                {'admitted':True,'deals_per_shard':step})
            self.assertEqual(plan['planned_games'],8400)
            self.assertEqual(len(plan['shards']),135*4//step)
            for arm in protocol['arms']:
                self.assertEqual(sum(row['games'] for row in plan['shards'] if row['arm']==arm),1680)
            seen={(r['players'],r['opponent']) for r in plan['shards']}
            self.assertEqual(len(seen),27)

    def test_incomplete_duplicate_and_changed_grids_rejected(self):
        protocol=read(PROTOCOL);plan=make_plan(protocol,{'protocol_sha256':digest(PROTOCOL)},
            {'admitted':True,'deals_per_shard':4})
        for kind in ['missing','duplicate','games','phase']:
            value=copy.deepcopy(plan)
            if kind=='missing':value['shards'].pop()
            elif kind=='duplicate':value['shards'][-1]=copy.deepcopy(value['shards'][0])
            elif kind=='games':value['shards'][0]['games']-=1
            else:value['shards'][0]['arm']='unplanned'
            with self.subTest(kind=kind),self.assertRaises(AssertionError):validate_plan(value,protocol)

    def test_invalid_cells_offsets_and_unplanned_arms_rejected(self):
        protocol=read(PROTOCOL)
        for args in [('combined',4,'a260',0,4),('combined',3,'economic_capacity_v1',0,4),
                     ('combined',2,'legacy',1,3),('combined',2,'legacy',0,5),('unknown',2,'legacy',0,4)]:
            with self.subTest(args=args),self.assertRaises(AssertionError):contract(protocol,*args)
        self.assertEqual(expected_config(protocol,'auction',3,'a260',2,4)['opponent_sha256'],
            '9b46db558669a0c3085412fe2544359eda55ed9f092dffb67bead6af3c409ecd')

    def test_admission_requires_both_complete_verified_endpoint_pilots(self):
        # A missing six-player result is not inferred from the faster two-player pilot.
        import population_hybrid_development as module
        real=module.read
        def incomplete(path):
            if str(path).endswith('population-hybrid-runtime-v2-6p/verified.json'):
                raise FileNotFoundError('six-player pilot not verified')
            return real(path)
        with patch.object(module,'read',incomplete),self.assertRaises(FileNotFoundError):runtime_admission()

    def test_clean_output_lifecycle_nonzero_deal_boundary_and_failure_receipt(self):
        spec=importlib.util.spec_from_file_location('population_job',ROOT/'ai/strong/population-hybrid-development-job.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        class ReachedEvaluator(Exception):pass
        commands=[]
        def stop(command,**kwargs):commands.append(command);raise ReachedEvaluator('intentional preflight stop')
        model=ROOT/'ai/runs/policy-iteration-trained-8840u-prepared-v2/local-package-frozen-1/policy.onnx'
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);self.assertFalse((root/'ai/runs').exists())
            with patch.object(module,'ROOT',root),patch.object(module,'hf_hub_download',return_value=str(model)),\
                 patch.object(module.subprocess,'Popen',side_effect=stop),\
                 patch.object(module,'upload_evidence',return_value={'preflight_only':True}),\
                 patch.dict(os.environ,{'PROTOCOL_SHA256':digest(PROTOCOL),'SOURCE_REVISION':'preflight','SOURCE_SHA256':'0'*64}),\
                 patch('sys.stdout',new=io.StringIO()),self.assertRaises(ReachedEvaluator):
                module.run('combined',6,'search_geo',2,4)
            self.assertEqual(len(commands),1);cmd=commands[0]
            def option(name):return cmd[cmd.index(name)+1]
            self.assertEqual((option('--start'),option('--deals'),option('--players')),('2','2','6'))
            self.assertEqual(option('--seed'),'population-hybrid-development-v1-6p')
            out=root/'ai/runs/population-hybrid-development-v1-combined-6p-search_geo-2-4'
            self.assertTrue((out/'manifest.json').exists())
            check=read(out/'development-check.json')
            self.assertEqual(check['stage'],'failed')
            self.assertTrue(check['error'].startswith('ReachedEvaluator:'))

    def test_submission_guard_prevents_duplicate_even_after_uncertain_failure(self):
        module=self.load('manage-population-hybrid-development.py')
        protocol=read(PROTOCOL)
        plan=make_plan(protocol,{'protocol_sha256':digest(PROTOCOL)},
            {'admitted':True,'deals_per_shard':4,'flavor':'cpu-upgrade','timeout_hours':12})
        source={'archive':'test.tgz','revision':'1'*40,'sha256':'2'*64};row=plan['shards'][0]
        for failure in [False,True]:
            with self.subTest(failure=failure),tempfile.TemporaryDirectory() as temp:
                root=Path(temp);plan_path=root/'plan.json';write(plan_path,plan)
                fake=type('Result',(),{'stdout':'Job 0123456789abcdef01234567','stderr':''})()
                with patch.object(module,'admission',return_value=(plan,source,row)),\
                     patch.object(module,'PLAN',plan_path),patch.object(module,'GUARDS',root/'guards'),\
                     patch.object(module,'get_token',return_value='test-secret'),\
                     patch.object(module.subprocess,'run',side_effect=RuntimeError('uncertain submission') if failure else None,return_value=fake) as run:
                    if failure:
                        with self.assertRaises(RuntimeError):module.launch(row['case'],True)
                    else:self.assertEqual(module.launch(row['case'],True)['job_id'],'0123456789abcdef01234567')
                    guard=read(root/'guards'/(row['case']+'.json'))
                    self.assertEqual(guard['stage'],'launch_unknown' if failure else 'launched')
                    with self.assertRaises(FileExistsError):module.launch(row['case'],True)
                    self.assertEqual(run.call_count,1)
                    self.assertNotIn('test-secret',(root/'guards'/(row['case']+'.json')).read_text())

    def test_coordinator_respects_existing_slots_and_stops_on_uncertain_guards(self):
        module=self.load('coordinate-population-hybrid-development.py')
        protocol=read(PROTOCOL)
        plan=make_plan(protocol,{'protocol_sha256':digest(PROTOCOL)},
            {'admitted':True,'deals_per_shard':4,'max_in_flight':32})
        plan['dependency_hashes']={}
        class EndObservation(Exception):pass
        for uncertain in [False,True]:
            with self.subTest(uncertain=uncertain),tempfile.TemporaryDirectory() as temp:
                root=Path(temp);guards=root/'guards';guards.mkdir();plan_path=root/'plan.json';write(plan_path,plan)
                for i,row in enumerate(plan['shards'][:16]):
                    write(guards/(row['case']+'.json'),{'stage':'launch_unknown' if uncertain and i==0 else 'launched',
                        'job_id':f'{i:024x}','plan_sha256':digest(plan_path)})
                def inspect(case):return {'case':case,'authoritative_status':'RUNNING'}
                def launch(case,execute):
                    self.assertTrue(execute);self.assertFalse((guards/(case+'.json')).exists())
                    record={'stage':'launched','job_id':f'{len(list(guards.glob("*.json"))):024x}',
                        'plan_sha256':digest(plan_path)}
                    write(guards/(case+'.json'),record);return record
                with patch.object(module,'ROOT',root),patch.object(module,'PLAN',plan_path),\
                     patch.object(module.manager,'GUARDS',guards),patch.object(module.manager,'verified_receipt',return_value=None),\
                     patch.object(module.manager,'inspect',side_effect=inspect),patch.object(module.manager,'collect') as collect,\
                     patch.object(module.manager,'launch',side_effect=launch) as launcher,\
                     patch.object(module.time,'sleep',side_effect=EndObservation),patch('sys.stdout',new=io.StringIO()),\
                     self.assertRaises(AssertionError if uncertain else EndObservation):
                    module.main(True,300,48)
                self.assertEqual(launcher.call_count,0 if uncertain else 16)
                self.assertEqual(len(list(guards.glob('*.json'))),16 if uncertain else 32)
                collect.assert_not_called()

    def test_comparison_pairs_whole_deals_and_retains_adverse_rules(self):
        module=self.load('compare-population-hybrid-development.py')
        left=[];right=[]
        for deal in range(4):
            for variant in ['original','recharged']:
                for sealed in [False,True]:
                    for seat in range(6):
                        common={'gameSeed':'fresh-'+str(deal),'variant':variant,'sealed':sealed,
                            'seat':seat,'truncated':False}
                        left.append({**common,'win':float(variant=='original')})
                        right.append({**common,'win':float(variant=='recharged')})
        overall=module.pairs.paired_difference(left,right,repeats=100)
        self.assertEqual(overall['independent_deals'],4)
        self.assertEqual(overall['win_share_difference'],0)
        a,b=module.rule_views(left),module.rule_views(right)
        self.assertEqual(module.pairs.paired_difference(a['recharged/sealed'],b['recharged/sealed'],repeats=100)['win_share_difference'],-1)
        with self.assertRaises(ValueError):module.pairs.paired_difference(left[:-1],right,repeats=100)
        with self.assertRaises(ValueError):module.pairs.paired_difference(left+[left[0]],right,repeats=100)


if __name__=='__main__':unittest.main()
