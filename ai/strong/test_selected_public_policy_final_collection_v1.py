"""Synthetic transport receipts only; no games, inference, HF calls or final seeds.

Use the actual source-control producer, wrapper lifecycle and execution-binding
audit. Mock only subprocess execution, artifact identity and the raw-game audit:
these tests establish collection bindings, never raw-game/strength evidence.
"""
from copy import deepcopy
from contextlib import redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import shutil
import tarfile
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import public_policy_selected_final_job_v1 as job
import selected_public_policy_final_collection_v1 as collect
import selected_public_policy_final_source_v1 as source
from public_policy_final_contract_v1 import admit, fingerprint, object_hash


class FinalCollectionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name); self.source = self.root / 'source'; self.source.mkdir()
        self.identity = {'policySha256': '1'*64, 'runtimeManifestSha256': '2'*64,
            'modelSha256': '3'*64, 'opponentPolicySha256': '4'*64,
            'featureRevision': '4.3-strategic-correction', 'backend': 'opponent-auction-v1',
            'settings': {'arm':'auction','samples':8,'workers':4,'threads':1,'max_steps':2400,
                         'population_modes':['neural_population'],'minimum_advantage':'1/8'}}
        candidate = {'status':'selected','frozen_at':'2026-10-29T01:00:00+00:00',
            'identity':self.identity,'protocol_sha256':source.PROTOCOL_SHA,
            'selection_evidence':{'repo':'coyotte508/powergrid-ai-germany-v1','revision':'5'*40,
                'archive_path':'archives/synthetic-collection-test.tgz','archive_sha256':'6'*64}}
        data = json.dumps(candidate).encode(); (self.source / 'candidate.json').write_bytes(data)
        files, rows = source.controls(data, self.identity, 'policy.json',
            {s['name']:4 for s in source.schedule()}, '2026-10-29T02:00:00+00:00')
        self.row = rows[0]; self.name = self.row['name']
        (self.source / 'controls').mkdir()
        for key in ('job','contract'): job.write(self.source / self.row[key], files[self.row[key]])
        self.runner = self.source / 'artifact/ai/strong/public_policy_final_runner_v1.py'
        self.runner.parent.mkdir(parents=True); self.runner.write_text('# synthetic, never executed\n')
        job.write(self.source / 'artifact/policy.json', {})
        (self.source / job.ENTRY).write_text('# synthetic wrapper identity\n')
        plan = {'version':1,'candidate_sha256':collect.digest(self.source / 'candidate.json'),
            'identity':self.identity,'protocol_sha256':source.PROTOCOL_SHA,
            'run_fingerprint':fingerprint(collect.digest(self.source / 'candidate.json'), self.identity),
            'rows':rows,'jobs':320,'games':20160}
        job.write(self.source / 'final-plan.json', plan)
        job.write(self.source / job.MANIFEST, {str(p.relative_to(self.source)):collect.digest(p)
            for p in self.source.rglob('*') if p.is_file()})
        self.bootstrap = 'synthetic collection test, never executed'
        self.release = {'version':1,'admission_sha256':'7'*64,
            'source':{'repo':'coyotte508/powergrid-ai-training-v1','revision':'8'*40,
                'archive':'synthetic-collection-source.tgz','sha256':'9'*64,
                'source_manifest_sha256':collect.digest(self.source / job.MANIFEST)},
            'plan':plan,'allocation':{r['name']:{'flavor':'cpu-upgrade','timeout':'5h'} for r in rows},
            'bootstrap_sha256':hashlib.sha256(self.bootstrap.encode()).hexdigest()}
        self.launch = {'stage':'launched','name':self.name,'job_id':'a'*24,
                       'release_sha256':object_hash(self.release),'row':self.row}
        self.folder = self.root / self.name
        contract = job.read(self.source / self.row['contract'])
        self.binding = {**admit(contract,candidate,plan['candidate_sha256'],self.identity),
            'contract_sha256':collect.digest(self.source / self.row['contract']),
            'runner_sha256':collect.digest(self.runner),'purpose':'final'}
        self.audit = {'audit_version':1,'all_receipts_verified':True,'identity':self.identity,
            'expected':self.row['shard'],'counts':{'decisions':123},'terminals':[],
            'input_hashes':{},'reserved_final_seeds_used':True,'qualification_eligible':False}
        args = SimpleNamespace(source=self.source,job=self.row['job'],output=self.folder,
            manifest_sha256=self.release['source']['source_manifest_sha256'],execute=True,upload=False,
            source_revision=self.release['source']['revision'],source_archive_sha256=self.release['source']['sha256'])

        def fake_runner(command, **kwargs):
            if '--execute' not in command: return
            evaluation = self.folder / 'evaluation'; evaluation.mkdir()
            shutil.copyfile(self.source / 'candidate.json', evaluation / 'candidate.json')
            shutil.copyfile(self.source / self.row['contract'], evaluation / 'contract.json')
            job.write(evaluation / 'evaluation.json', {'passed':True,'all_complete':True,'errors':[],
                'config':{'workers':self.row['workers'],'descriptor':'policy.json'},
                'completed_games':self.row['shard']['games'],'game_caps':0,'rollout_caps':0,
                'reserved_final_seeds_used':True,'execution_binding':self.binding})
            job.write(evaluation / 'audit.json', {**self.audit,'execution_binding':self.binding})

        with redirect_stdout(io.StringIO()), patch.object(job,'__file__',str(self.source / job.ENTRY)), patch.object(job.subprocess,'run',side_effect=fake_runner):
            job.run(args)
        self.archive = self.root / 'original.tgz'
        self.seal()

    def seal(self):
        pins = {str(p.relative_to(self.folder)):collect.digest(p) for p in self.folder.rglob('*')
                if p.is_file() and p.name != 'manifest.json'}
        job.write(self.folder / 'manifest.json', pins)
        with tarfile.open(self.archive, 'w:gz') as bundle:
            for name in sorted(set(pins) | {'manifest.json'}): bundle.add(self.folder/name, arcname=name)
        self.evidence = {'repo':'coyotte508/powergrid-ai-germany-v1','revision':'b'*40,
            'archive_path':f'archives/{self.name}.tgz','archive_sha256':collect.digest(self.archive),
            'manifest_sha256':collect.digest(self.folder / 'manifest.json'),
            'archived_files':len(pins)+1,'format':'tar.gz','remote_archive_verified':True}

    def invoke(self, audit=None, hf_stage='COMPLETED'):
        with patch.object(collect,'artifact_identity',return_value=self.identity), patch.object(collect,'audit_shard',
                return_value=deepcopy(self.audit), side_effect=audit) as raw:
            result = collect.verify_artifacts(self.folder,self.source,self.release,self.launch,
                                             self.evidence,self.archive,self.bootstrap,hf_stage=hf_stage)
        raw.assert_called_once_with(self.folder/'evaluation', self.row['shard'], self.identity, reserved=True)
        return result

    def change_status(self, **changes):
        p=self.folder/'job-status.json';s=job.read(p);s.update(changes);job.write(p,s);self.seal()

    def test_actual_wrapper_output_binds_original_source_and_launch(self):
        before={str(p.relative_to(self.root)):collect.digest(p) for p in self.root.rglob('*') if p.is_file()}
        result=self.invoke()
        self.assertTrue(result['verified']);self.assertFalse(result['qualified'])
        self.assertFalse(result['selection_and_launch_admission_verified_by_this_function'])
        self.assertEqual(result['execution_binding'],self.binding)
        self.assertEqual(result['job_id'],self.launch['job_id'])
        self.assertEqual(before,{str(p.relative_to(self.root)):collect.digest(p) for p in self.root.rglob('*') if p.is_file()})

    def test_ambiguous_or_wrong_release_launch_rejected(self):
        self.launch['stage']='launch_unknown'
        with self.assertRaisesRegex(ValueError,'unambiguous'):self.invoke()
        self.launch['stage']='launched';self.launch['release_sha256']='c'*64
        with self.assertRaisesRegex(ValueError,'another release'):self.invoke()

    def test_changed_archive_and_extracted_files_rejected(self):
        self.archive.write_bytes(self.archive.read_bytes()+b'changed')
        with self.assertRaisesRegex(ValueError,'Archive hash'):self.invoke()
        self.seal();(self.folder/'job-spec.json').write_text('{}')
        with self.assertRaisesRegex(ValueError,'File hash'):self.invoke()

    def test_wrong_revision_or_archive_identity_rejected(self):
        self.evidence['revision']='main'
        with self.assertRaisesRegex(ValueError,'Unpinned'):self.invoke()
        self.evidence['revision']='b'*40;self.evidence['archive_path']='archives/another.tgz'
        with self.assertRaisesRegex(ValueError,'Wrong original'):self.invoke()

    def test_failed_job_stays_failed_even_with_valid_archive(self):
        self.change_status(stage='failed')
        before=collect.digest(self.archive)
        with self.assertRaisesRegex(ValueError,'Incomplete'):self.invoke()
        self.assertEqual(collect.digest(self.archive),before)

    def test_remote_error_or_running_status_is_never_relabelled(self):
        for stage in ('ERROR','RUNNING','SCHEDULING','CANCELED'):
            with self.assertRaisesRegex(ValueError,'Original HF job not completed'):
                self.invoke(hf_stage=stage)

    def test_executed_game_workers_and_descriptor_match_source(self):
        path=self.folder/'evaluation/evaluation.json';original=job.read(path)
        for key,value in [('workers',2),('descriptor','another-policy.json')]:
            report=deepcopy(original);report['config'][key]=value;job.write(path,report)
            self.change_status(evaluation_sha256=collect.digest(path))
            with self.assertRaisesRegex(ValueError,'worker allocation or descriptor'):self.invoke()

    def test_wrong_source_provenance_rejected_after_resealing(self):
        status=job.read(self.folder/'job-status.json');p=status['provenance'];p['source_revision']='c'*40
        self.change_status(provenance=p)
        with self.assertRaisesRegex(ValueError,'wrong original'):self.invoke()

    def test_replaced_candidate_not_hidden_by_new_archive_hash(self):
        (self.folder/'evaluation/candidate.json').write_text('{}');self.seal()
        with self.assertRaisesRegex(ValueError,'candidate/contract'):self.invoke()

    def test_independent_raw_audit_must_match_saved_audit(self):
        changed={**self.audit,'counts':{'decisions':122}}
        with self.assertRaisesRegex(ValueError,'Independent raw audit'):
            self.invoke(audit=lambda *a,**k:changed)

    def test_raw_audit_failure_propagates_without_recovery_or_writes(self):
        before=collect.digest(self.archive)
        with self.assertRaisesRegex(ValueError,'missing decision'):
            self.invoke(audit=ValueError('missing decision'))
        self.assertEqual(collect.digest(self.archive),before)

    def test_execution_contract_binding_is_independently_recomputed(self):
        p=self.folder/'evaluation/evaluation.json';report=job.read(p)
        report['execution_binding']['runner_sha256']='d'*64;job.write(p,report)
        self.change_status(evaluation_sha256=collect.digest(p))
        with self.assertRaisesRegex(ValueError,'binding differs'):self.invoke()

    def test_archive_duplicate_and_symlink_members_rejected(self):
        for link in (False, True):
            self.seal()
            with tarfile.open(self.archive,'r:gz') as bundle:
                members=[(e,bundle.extractfile(e).read()) for e in bundle.getmembers()]
            with tarfile.open(self.archive,'w:gz') as bundle:
                for entry,data in members:
                    if link and entry.name=='job-spec.json':
                        entry.type=tarfile.SYMTYPE;entry.linkname='../escape';entry.size=0;bundle.addfile(entry)
                    else:bundle.addfile(entry,io.BytesIO(data))
                if not link:bundle.add(self.folder/'job-spec.json',arcname='job-spec.json')
            self.evidence['archive_sha256']=collect.digest(self.archive)
            with self.assertRaisesRegex(ValueError,'archive members|Non-regular'):self.invoke()

    def test_symlink_or_extra_extracted_file_rejected(self):
        p=self.folder/'extra';p.symlink_to(self.source/'candidate.json')
        with self.assertRaisesRegex(ValueError,'Symlink'):self.invoke()
        p.unlink();p.write_text('unmanifested')
        with self.assertRaisesRegex(ValueError,'file set differs'):self.invoke()

    def test_source_change_during_raw_audit_is_detected(self):
        def mutate(*a,**k):
            (self.source/job.ENTRY).write_text('changed during audit')
            return self.audit
        with self.assertRaisesRegex(ValueError,'File hash'):self.invoke(audit=mutate)

    def test_noncanonical_manifest_path_rejected(self):
        manifest=self.folder/'manifest.json';pins=job.read(manifest);pins['../outside']='a'*64;job.write(manifest,pins)
        with self.assertRaisesRegex(ValueError,'Noncanonical'):
            collect.checked_tree(self.folder,'manifest.json',collect.digest(manifest))


if __name__ == '__main__':unittest.main()
