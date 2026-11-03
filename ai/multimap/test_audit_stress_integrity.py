"""Offline metadata/content/replay guards; synthetic data is not evidence."""
import copy
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch,Mock

import audit_stress_integrity as a
from data import atomic_json,digest
from test_stress_study import outcome


class Integrity(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.out=self.root/'audit';self.prefix='runs/multimap-stress-20261103-v1-mixed/'
        self.files={}
        for name in a.NAMES:
            p=self.root/'remote'/name;atomic_json(p,{'value':name});self.files[name]=p
        self.manifest={n:digest(p) for n,p in self.files.items()}
        m=self.root/'remote/artifacts.json';atomic_json(m,self.manifest);self.files['artifacts.json']=m
        self.entries=[NS(path=self.prefix+n,size=p.stat().st_size,blob_id=a.git_blob(p.read_bytes()),lfs=None) for n,p in self.files.items()]
        self.api=Mock();self.api.list_repo_tree.return_value=self.entries
        self.remote=Mock();self.remote.describe.return_value=NS(size=m.stat().st_size);self.remote.get.return_value=m
    def fetch(self):
        return a.fetch_panel('mixed','a'*40,self.out,self.api)
    def patches(self):
        return patch.object(a,'RemoteFiles',return_value=self.remote),patch('huggingface_hub.hf_hub_download',side_effect=lambda repo,name,**kw:str(self.files[name[len(self.prefix):]]))
    def test_complete_bounded_snapshot(self):
        first,second=self.patches()
        with first,second as download:
            report=self.fetch();self.assertEqual(report['files'],327);self.assertEqual(download.call_count,327)
            download.reset_mock();self.fetch();download.assert_not_called()
        self.assertEqual(report['bytes'],sum(e.size for e in self.entries))
        self.assertTrue(report['metadataFirst'])
    def test_all_metadata_before_payload_download(self):
        self.entries[-1].size=a.LIMIT+1
        first,second=self.patches()
        with first,second as download:
            with self.assertRaisesRegex(ValueError,'sizes'):self.fetch()
            download.assert_not_called()
    def test_total_budget_before_payload_download(self):
        for entry in self.entries:entry.size=300000
        first,second=self.patches()
        with first,second as download:
            with self.assertRaisesRegex(ValueError,'Total panel'):self.fetch()
            download.assert_not_called()
    def test_manifest_missing_foreign_and_bad_hash(self):
        for change in ('missing','foreign','bad'):
            m=dict(self.manifest)
            if change=='missing':m.pop('status.json')
            elif change=='foreign':m['../unwanted']='a'*64
            else:m['status.json']='bad'
            atomic_json(self.files['artifacts.json'],m)
            first,second=self.patches()
            with first,second as download:
                with self.assertRaises(ValueError):self.fetch()
                download.assert_not_called()
    def test_remote_coverage_duplicate_and_foreign(self):
        original=copy.deepcopy(self.entries)
        for kind in ('missing','duplicate','foreign'):
            entries=copy.deepcopy(original)
            if kind=='missing':entries.pop()
            elif kind=='duplicate':entries[-1]=entries[0]
            else:entries[-1].path=self.prefix+'unexpected'
            with self.assertRaises(ValueError):a.snapshot_metadata(self.manifest,entries,self.prefix)
    def test_corrupt_payload_hash_is_rejected(self):
        self.files['status.json'].write_text('{"wrong":true}')
        first,second=self.patches()
        with first,second:
            with self.assertRaisesRegex(ValueError,'Artifact content'):self.fetch()
    def test_wrong_git_blob_is_rejected(self):
        next(e for e in self.entries if e.path.endswith('/status.json')).blob_id='0'*40
        first,second=self.patches()
        with first,second:
            with self.assertRaisesRegex(ValueError,'Git blob'):self.fetch()
    def test_restore_root_symlink_is_rejected_before_network(self):
        self.out.mkdir();(self.out/'restored').symlink_to(self.root/'remote',target_is_directory=True)
        first,second=self.patches()
        with first,second as download:
            with self.assertRaisesRegex(ValueError,'ancestor'):self.fetch()
            self.remote.describe.assert_not_called();download.assert_not_called()
    def test_nested_directory_symlink_is_rejected_before_writes(self):
        base=self.out/'restored';base.mkdir(parents=True)
        outside=self.root/'outside';outside.mkdir();(base/'study').symlink_to(outside,target_is_directory=True)
        first,second=self.patches()
        with first,second as download:
            with self.assertRaisesRegex(ValueError,'Nested restore symlink'):self.fetch()
            self.remote.describe.assert_not_called();download.assert_not_called()
        self.assertEqual(list(outside.iterdir()),[])
        self.assertEqual(list(base.iterdir()),[base/'study'])
    def test_unexpected_descendant_is_rejected_before_downloads(self):
        base=self.out/'restored';base.mkdir(parents=True);(base/'unexpected').write_text('keep')
        first,second=self.patches()
        with first,second as download:
            with self.assertRaisesRegex(ValueError,'Unexpected restore descendant'):self.fetch()
            self.remote.describe.assert_not_called();download.assert_not_called()
        self.assertEqual((base/'unexpected').read_text(),'keep')
    def test_cached_corruption_not_overwritten(self):
        dest=self.out/'restored/status.json';dest.parent.mkdir(parents=True);dest.write_text('{}')
        first,second=self.patches()
        with first,second:
            with self.assertRaisesRegex(ValueError,'Artifact content'):self.fetch()
        self.assertEqual(dest.read_text(),'{}')
    def test_only_docs_can_differ_from_source(self):
        for name in ('README.md','runs.json'):
            self.assertIsNotNone(a.local_difference('ai/multimap/'+name,'a','b'))
        for name in ('stress_rollout.py','launch_stress.py','expert_game.cjs','model.py'):
            with self.assertRaises(ValueError):a.local_difference('ai/multimap/'+name,'a','b')
        self.assertIsNone(a.local_difference('anything','same','same'))
    def test_replay_plan_is_complete_and_outcome_independent(self):
        for panel in ('strong','mixed'):
            tasks=a.replay_tasks(panel)
            self.assertEqual(len(tasks),16);self.assertEqual({s['players'] for s in tasks},set(range(2,7)))
            self.assertEqual(len({s['map'] for s in tasks}),4)
            self.assertEqual({(s['variant'],s['fastBid']) for s in tasks},{('original',False),('original',True),('recharged',False),('recharged',True)})
            self.assertEqual({s['policy'] for s in tasks},{'expert24','ppo2'})
            self.assertTrue(all(s['deal']==0 and s['focalSeat']==0 and not s['smoke'] for s in tasks))
    def test_replay_ignores_only_timings_and_checks_all_counters(self):
        base=self.root/'snapshot';tasks=a.replay_tasks('mixed');games=[outcome(s) for s in tasks]
        atomic_json(base/'study/batch-000.json',{'games':games})
        replay=copy.deepcopy(games)
        for g in replay:g['seconds']=10
        with patch('stress_rollout.load_models',return_value={}),patch('stress_rollout.collect',return_value=replay),patch('torch.use_deterministic_algorithms'):
            result=a.replay_panel('mixed',base,self.out)
            self.assertEqual(result['exactMatches'],16);self.assertEqual(result['newIndependentObservations'],0)
            replay[0]['publicChecks']['expertAtomicLegal']=1
            with self.assertRaisesRegex(ValueError,'replay terminal/counter'):a.replay_panel('mixed',base,self.out)
            replay[0]['publicChecks']['expertAtomicLegal']=0;replay.pop()
            with self.assertRaisesRegex(ValueError,'Replay count'):a.replay_panel('mixed',base,self.out)


class JobEvidence(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.receipt=a.launch_receipt();self.r=next(r for r in self.receipt['jobs'] if r['panel']=='mixed')
        import shlex
        from launch_stress import BOOTSTRAP
        command=['bash','-lc','python -m pip install --no-cache-dir --disable-pip-version-check huggingface_hub==1.29.0 && python -c '+shlex.quote(BOOTSTRAP)]
        self.job=NS(id=a.JOBS['mixed'],status=NS(stage='COMPLETED'),environment=copy.deepcopy(self.r['env']),
            docker_image=a.IMAGE,flavor='cpu-upgrade',command=command,arguments=[],started_at='start',finished_at='finish')
        self.api=Mock();self.api.inspect_job.return_value=self.job
        events=[dict(stage='uploaded',label='runtime-ready',revision='b'*40)]
        seeds={}
        for s in a.plan('mixed'):seeds[s['seed']]=seeds.get(s['seed'],0)+1
        total=0
        for i,n in enumerate(seeds.values(),1):
            total+=n;events.append(dict(stage='stress-batch',panel='mixed',batches=i,totalBatches=320,games=total))
            if i%16==0:events.append(dict(stage='uploaded',label=f'batches-{i}',revision='b'*40))
        events.extend([dict(stage='uploaded',label='complete',revision='b'*40),dict(stage='uploaded',label='complete',revision='c'*40),
            dict(stage='complete',run=self.r['run'],panel='mixed',games=2560,qualified=False)])
        self.log=['Ran 45 tests in 0.01s','','OK','ℹ tests 10','ℹ pass 10','ℹ fail 0',*[json.dumps(e) for e in events]]
        self.api.fetch_job_logs.return_value=self.log
    def test_pinned_receipt_job_source_binding_and_complete_log(self):
        report=a.verify_job('mixed',self.root,self.api)
        self.assertTrue(report['executedSourceBoundToVerifiedArchive'])
        self.assertEqual(report['launchReceiptGit'],a.LAUNCH_COMMIT)
        self.assertEqual(report['finalRevision'],'c'*40)
    def test_modified_receipt_rejected_by_git_anchor(self):
        receipt=copy.deepcopy(self.receipt);receipt['jobs'][0]['env']['SOURCE_SHA256']='0'*64
        atomic_json(self.root/'stress-launch-v1.json',receipt)
        with patch.object(a,'HERE',self.root):
            with self.assertRaisesRegex(ValueError,'pinned post-launch Git'):a.launch_receipt()
    def test_independent_complete_environment_source_binding(self):
        for key in self.r['env']:
            with self.subTest(key=key):
                receipt=copy.deepcopy(self.receipt)
                next(r for r in receipt['jobs'] if r['panel']=='mixed')['env'][key]='altered'
                with self.assertRaisesRegex(ValueError,'bound to verified source'):a.validate_launch(receipt)
        for key in self.receipt['source']:
            receipt=copy.deepcopy(self.receipt);receipt['source'][key]='altered'
            with self.assertRaises(ValueError):a.validate_launch(receipt)
        receipt=copy.deepcopy(self.receipt);receipt['jobs'][0]['jobId']='foreign'
        with self.assertRaisesRegex(ValueError,'Original job'):a.validate_launch(receipt)
    def test_receipt_and_job_matching_wrong_source_still_rejected(self):
        for key in ('SOURCE_SHA256','SOURCE_REVISION','SOURCE_PATH','DATASET_REPO'):
            receipt=copy.deepcopy(self.receipt)
            next(r for r in receipt['jobs'] if r['panel']=='mixed')['env'][key]='wrong'
            self.job.environment=copy.deepcopy(self.r['env']);self.job.environment[key]='wrong'
            # Even bypassing receipt authentication cannot substitute the executed source.
            with patch.object(a,'launch_receipt',return_value=receipt):
                with self.assertRaisesRegex(ValueError,'immutable HF job'):a.verify_job('mixed',self.root,self.api)
    def test_remote_job_id_command_and_completion_required(self):
        for attr,value in [('id','foreign'),('command',['wrong']),('environment',{}),('status',NS(stage='RUNNING'))]:
            old=getattr(self.job,attr);setattr(self.job,attr,value)
            with self.assertRaisesRegex(ValueError,'immutable HF job'):a.verify_job('mixed',self.root,self.api)
            setattr(self.job,attr,old)
    def test_log_duplicate_batch_rejected(self):
        i=next(i for i,x in enumerate(self.log) if '"batches": 319,' in x)
        self.log.insert(i,self.log[i])
        with self.assertRaisesRegex(ValueError,'ordered production'):a.verify_job('mixed',self.root,self.api)


if __name__=='__main__':unittest.main()
