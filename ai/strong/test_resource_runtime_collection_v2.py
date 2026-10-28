"""Failure-preserving collection controls; fake API, no jobs or simulations."""
import importlib.util
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from public_policy_development_job_v1 import digest,read,write

SPEC=importlib.util.spec_from_file_location('resource_runtime_collection_v2',
    Path(__file__).with_name('collect-resource-runtime-outcomes-v2.py'))
COLLECTOR=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(COLLECTOR)


class CollectionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.old=self.root/'original';self.old.mkdir()
        self.rootpatch=patch.object(COLLECTOR,'ROOT',self.root);self.rootpatch.start();self.addCleanup(self.rootpatch.stop)
        self.source={k:'pin-'+k for k in ('source_manifest_sha256','protocol_sha256','entry_sha256',
            'artifact_descriptor_sha256','artifact_manifest_sha256','revision','sha256')}
        self.source['flavor']='cpu-upgrade'
        self.src=self.root/'source.json';write(self.src,self.source)
        self.manager=SimpleNamespace(OUT=self.old,SOURCE=self.src,BOOTSTRAP='frozen-bootstrap',
            environment=lambda s,r:{'PUBLIC_PIN':'p'},save=self.save,verify_artifacts=self.forbidden)
        self.downloads=0

    @staticmethod
    def save(path,value):
        with path.open('x') as stream:json.dump(value,stream)

    @staticmethod
    def forbidden(*args,**kwargs):raise AssertionError('Unexpected independent audit rerun')

    def fixture(self,suffix,stage='RUNNING',raw=False,cached=False,receipt=True):
        name='pg-resource-turn-runtime-v1-'+suffix
        row={'job':{'name':name,'games':8 if suffix.endswith('2p') else 24},'job_spec_sha256':'job-pin'}
        original=self.old/name;original.mkdir()
        output=self.root/name
        guard={'stage':'launched','job_id':COLLECTOR.HANDLES[suffix],'source':self.source,'row':row}
        # The artifacts' manifests are deterministic bytes and actually checked.
        if raw:
            folder=original/'artifacts';folder.mkdir()
            write(folder/'source-manifest.json',{})
            write(folder/'job-spec.json',row['job'])
            self.source['source_manifest_sha256']=digest(folder/'source-manifest.json')
            row['job_spec_sha256']=digest(folder/'job-spec.json')
            write(self.src,self.source)
            provenance={k:self.source[k] for k in ('source_manifest_sha256','protocol_sha256','entry_sha256',
                'artifact_descriptor_sha256','artifact_manifest_sha256')}
            provenance.update(job_spec_sha256=row['job_spec_sha256'],source_revision=self.source['revision'],
                source_archive_sha256=self.source['sha256'],job=row['job'])
            status={'provenance':provenance,'case':name,'scope':'runtime-only',
                'stage':'complete' if stage=='COMPLETED' else 'failed','gradient_updates':0,
                'new_strength_games':0,'automatic_retries':False,'qualification_eligible':False,
                'reserved_final_seeds_used':False}
            write(folder/'status.json',status)
            (folder/'evaluation').mkdir()
            write(folder/'evaluation/evaluation.json',{'expected_games':row['job']['games'],
                'completed_games':1,'results':[{'episode':0}],'errors':[{'episode':1}]})
            manifest={str(p.relative_to(folder)):digest(p) for p in folder.rglob('*') if p.is_file()}
            write(folder/'manifest.json',manifest)
            archive=original/'fake-archive.bin';archive.write_bytes(b'archive already extracted for this unit test')
            evidence={'repo':'coyotte508/powergrid-ai-germany-v1','archive_path':'archives/'+name+'.tgz',
                'revision':'a'*40,'archive_sha256':digest(archive),'remote_archive_verified':True,
                'manifest_sha256':digest(folder/'manifest.json'),'archived_files':len(manifest)+1}
            if receipt:(original/'job.log').write_text(json.dumps({'case':name,'status':status,'evidence':evidence})+'\n')
            if cached:
                (original/'independent-audit').mkdir();write(original/'independent-audit/result.json',{'passed':True})
                value={'job_id':guard['job_id'],'row':row,'review':{'games':row['job']['games'],
                    'independent_audit_sha256':digest(original/'independent-audit/result.json'),
                    'audit':{'counts':{'rollout_caps':0}}},'verified':True,'evidence':evidence,
                    'source_sha256':digest(self.src)}
        write(original/'launch.json',guard)
        if cached:
            value['guard_sha256']=digest(original/'launch.json');write(original/'verified.json',value)
        info=SimpleNamespace(status=SimpleNamespace(stage=stage),command=['bash','-lc','frozen-bootstrap'],
            docker_image='python:3.11-slim-bookworm',flavor='cpu-upgrade',environment={'PUBLIC_PIN':'p'})
        api=SimpleNamespace(inspect_job=lambda **k:info,fetch_job_logs=lambda **k:[])
        def download(*args,**kwargs):
            self.downloads+=1
            return original/'fake-archive.bin'
        return row,original,output,api,download

    def run_one(self,fixture):
        row,_,output,api,download=fixture
        return COLLECTOR.collect_one(api,self.source,row,self.manager,output,download)

    def test_live_job_is_only_observed(self):
        result=self.run_one(self.fixture('whole-6p'))
        self.assertEqual(result['outcome'],'pending');self.assertEqual(self.downloads,0)

    def test_failed_raw_evidence_is_retained_without_success_audit(self):
        f=self.fixture('anchored-2p','ERROR',raw=True)
        result=self.run_one(f)
        self.assertEqual(result['outcome'],'failed_preserved')
        self.assertFalse(result['verified']);self.assertEqual(result['partial_complete_games_reported'],1)
        self.assertFalse(result['partial_games_independently_audited'])
        self.assertTrue((f[2]/'failure-evidence.json').exists())
        # A subsequent original still gets processed; no retry interface exists.
        self.assertEqual(self.run_one(self.fixture('whole-6p'))['outcome'],'pending')

    def test_cached_success_does_not_repeat_audit_or_download(self):
        result=self.run_one(self.fixture('whole-2p','COMPLETED',raw=True,cached=True))
        self.assertEqual(result['outcome'],'verified_success');self.assertTrue(result['reused_audit'])
        self.assertEqual(self.downloads,0)

    def test_mutated_cached_audit_is_rejected(self):
        f=self.fixture('whole-2p','COMPLETED',raw=True,cached=True)
        write(f[1]/'independent-audit/result.json',{'passed':False})
        with self.assertRaises(AssertionError):self.run_one(f)

    def test_missing_terminal_archive_is_not_success(self):
        result=self.run_one(self.fixture('anchored-2p','ERROR'))
        self.assertEqual(result['outcome'],'unverified_terminal');self.assertFalse(result['verified'])

    def test_mutated_raw_file_is_rejected(self):
        f=self.fixture('anchored-2p','ERROR',raw=True)
        write(f[1]/'artifacts/status.json',{'stage':'complete'})
        with self.assertRaises(AssertionError):self.run_one(f)

    def test_original_handle_cannot_be_replaced(self):
        f=self.fixture('anchored-2p');p=f[1]/'launch.json';guard=read(p)
        guard['job_id']='b'*24;write(p,guard)
        with self.assertRaises(AssertionError):self.run_one(f)

    def test_remote_provenance_mismatch_is_rejected(self):
        f=self.fixture('whole-6p');info=f[3].inspect_job()
        info.environment={'PUBLIC_PIN':'wrong'}
        with self.assertRaises(AssertionError):self.run_one(f)

    def test_unrecognized_stage_remains_unresolved(self):
        result=self.run_one(self.fixture('whole-6p','UNKNOWN'))
        self.assertEqual(result['outcome'],'unknown_stage');self.assertFalse(result['verified'])

    def test_success_audit_requires_new_directory(self):
        f=self.fixture('whole-2p','COMPLETED',raw=True)
        f[2].mkdir();(f[2]/'independent-audit').mkdir()
        with self.assertRaisesRegex(AssertionError,'interrupted independent audit'):self.run_one(f)

    def test_all_terminal_with_failure_never_passes_gate(self):
        records=[{'job_id':jid,'stage':'COMPLETED','outcome':'verified_success',
            'review':{'games':8 if name.endswith('2p') else 24}} for name,jid in COLLECTOR.HANDLES.items()]
        records[2].update(stage='ERROR',outcome='failed_preserved')
        report=COLLECTOR.summarize(records)
        self.assertTrue(report['all_originals_terminal']);self.assertFalse(report['success_gate_passed'])
        self.assertEqual(report['verified_successful_jobs'],5)
        self.assertEqual(report['verified_successful_games'],88)

    def test_duplicate_handle_cannot_satisfy_schedule(self):
        records=[{'job_id':jid,'stage':'RUNNING','outcome':'pending'} for jid in COLLECTOR.HANDLES.values()]
        records[-1]['job_id']=records[0]['job_id']
        with self.assertRaises(AssertionError):COLLECTOR.summarize(records)


if __name__=='__main__':unittest.main()
