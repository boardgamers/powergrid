"""Offline collection tests with synthetic archives; no games or HF access."""
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import tarfile
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from public_policy_development_job_v1 import digest,read,write

ROOT=Path(__file__).resolve().parents[2]
PATH=Path(__file__).with_name('collect-resource-turn-runtime-v2.py')
spec=importlib.util.spec_from_file_location('corrected_resource_collector_tested',PATH)
c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)


def save(path,value):
    with path.open('x') as stream:json.dump(value,stream,indent=2);stream.write('\n')


class Tests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.jobs=self.root/'jobs';self.jobs.mkdir()
        self.patches=[]
        self.source={k:'pin-'+k for k in ('protocol_sha256','entry_sha256','artifact_descriptor_sha256',
            'artifact_manifest_sha256','revision','sha256')}
        self.source.update(flavor='cpu-upgrade',rows=[])
        self.sourcepath=self.root/'source.json'
        self.manager=SimpleNamespace(OUT=self.jobs,SOURCE=self.sourcepath,BOOTSTRAP='frozen-v4-bootstrap',
            environment=lambda source,row:{'PUBLIC_PIN':'v4'},save=save)
        for key,value in [('ROOT',self.root),('launcher',self.manager)]:
            p=patch.object(c,key,value);p.start();self.addCleanup(p.stop)
        self.downloads=0;self.audits=0;self.fetches=0

    def fixture(self,players=2,stage='RUNNING',raw=False,receipt=True):
        name=f'pg-resource-turn-runtime-v2-anchored-{players}p'
        job={'name':name,'mode':'atomic-search-anchored','players':players,'games':4*players,'workers':4,
            'seed':f'resource-turn-runtime-v2-{players}p','opponent':'search_geo','start':0,'deals':1,
            'control':False,'reference':None}
        folder=self.jobs/name;folder.mkdir()
        output=self.root/name
        row={'file':name+'.job.json','job':job,'job_spec_sha256':'job-pin'}
        guard={'stage':'launched','source':self.source,'row':row,'job_id':('a' if players==2 else 'b')*24}
        lines=[];reference=self.root/(name+'-reference')
        if raw:
            reference.mkdir();write(reference/'source-manifest.json',{})
            write(reference/'admission.json',{'synthetic_fixture_only':True})
            write(reference/'job-spec.json',job)
            self.source.update(source_manifest_sha256=digest(reference/'source-manifest.json'),
                admission_sha256=digest(reference/'admission.json'))
            row['job_spec_sha256']=digest(reference/'job-spec.json')
            provenance={k:self.source[k] for k in ('source_manifest_sha256','protocol_sha256','entry_sha256',
                'artifact_descriptor_sha256','artifact_manifest_sha256','admission_sha256')}
            provenance.update(job_spec_sha256=row['job_spec_sha256'],source_revision=self.source['revision'],
                source_archive_sha256=self.source['sha256'],job=job)
            counts={'policy_requests':10,'atomic_moves':10,'rollouts':16,'rollout_caps':0,'neural_decisions':32}
            measurement={'seconds':10,'cpu_seconds':20,'sampled_peak_total_rss_bytes':1000,'memory_samples':50,
                'memory_sampling_period_seconds':.2,'includes_startup_and_validation':True}
            status={'stage':'complete' if stage=='COMPLETED' else 'failed','case':name,'scope':'runtime-only',
                'provenance':provenance,'gradient_updates':0,'new_strength_games':0,'automatic_retries':False,
                'qualification_eligible':False,'reserved_final_seeds_used':False,'measurement':measurement,
                'counts':counts,'replay':None}
            evaluation=reference/'evaluation';evaluation.mkdir()
            config={k:job[k] for k in ('mode','players','opponent','seed','start','deals','workers')}
            config.update(artifact='/workspace/source/artifact',output=f'/workspace/output/{name}/evaluation',
                descriptor_sha256=self.source['artifact_descriptor_sha256'])
            report={'expected_games':job['games'],'completed_games':job['games'] if stage=='COMPLETED' else 1,
                'all_complete':stage=='COMPLETED','errors':[] if stage=='COMPLETED' else [{'episode':1}],
                'config':config,'results':[{'episode':i} for i in range(job['games'] if stage=='COMPLETED' else 1)]}
            write(evaluation/'evaluation.json',report)
            audit={'passed':True,'games':job['games'],'counts':counts,'paired_schedule_checked':True}
            write(evaluation/'independent-audit.json',audit)
            if stage=='COMPLETED':
                status.update(games=job['games'],evaluation_sha256=digest(evaluation/'evaluation.json'),
                    audit_sha256=digest(evaluation/'independent-audit.json'))
            else:status['failure_type']='SyntheticFailure'
            write(reference/'status.json',status)
            manifest={str(p.relative_to(reference)):digest(p) for p in reference.rglob('*') if p.is_file()}
            write(reference/'manifest.json',manifest)
            archive=folder/'synthetic.tgz'
            with tarfile.open(archive,'w:gz') as bundle:
                for name_in_archive in sorted(set(manifest)|{'manifest.json'}):
                    bundle.add(reference/name_in_archive,arcname=name_in_archive)
            evidence={'repo':'coyotte508/powergrid-ai-germany-v1','archive_path':'archives/'+name+'.tgz',
                'revision':'a'*40,'archive_sha256':digest(archive),'manifest_sha256':digest(reference/'manifest.json'),
                'archived_files':len(manifest)+1,'remote_archive_verified':True}
            if receipt:lines=[json.dumps({'case':name,'status':status,'evidence':evidence})]
        self.source['rows'].append(row);write(self.sourcepath,self.source);write(folder/'launch.json',guard)
        info=SimpleNamespace(status=SimpleNamespace(stage=stage),command=['bash','-lc',self.manager.BOOTSTRAP],
            docker_image='python:3.11-slim-bookworm',flavor='cpu-upgrade',environment={'PUBLIC_PIN':'v4'})
        def fetch(**kwargs):self.fetches+=1;return lines
        def download(*args,**kwargs):self.downloads+=1;return folder/'synthetic.tgz'
        api=SimpleNamespace(inspect_job=lambda **kwargs:info,fetch_job_logs=fetch)
        return SimpleNamespace(row=row,guard=guard,output=output,api=api,download=download,
            reference=reference,info=info,lines=lines)

    def fake_audit(self,folder,source,row,evidence,audit_directory):
        # Synthetic game records test orchestration only, never the strength or
        # semantic correctness of a policy. The real v4 auditor is already pinned.
        self.audits+=1
        assert not audit_directory.exists(),'Inspect interrupted independent audit before retrying'
        audit_directory.mkdir()
        status=c.raw_checked(folder,source,row,evidence)
        audit=read(folder/'evaluation/independent-audit.json')
        write(audit_directory/'result.json',audit)
        return {'games':row['job']['games'],'audit':audit,'measurement':status['measurement'],
            'independent_audit_sha256':digest(audit_directory/'result.json')}

    def run_one(self,f):
        with patch.object(c,'independent_audit',side_effect=self.fake_audit):
            return c.collect_one(f.api,self.source,f.row,f.guard,f.output,f.download)

    def test_live_handle_is_observed_without_download(self):
        result=self.run_one(self.fixture())
        self.assertEqual(result['outcome'],'pending');self.assertEqual(self.downloads+self.audits+self.fetches,0)

    def test_terminal_failure_is_preserved_and_never_success(self):
        f=self.fixture(stage='ERROR',raw=True);result=self.run_one(f)
        self.assertEqual(result['outcome'],'failed_preserved');self.assertFalse(result['verified'])
        self.assertEqual(result['partial_complete_games_reported'],1)
        self.assertFalse(result['partial_games_independently_audited'])
        self.assertTrue((f.output/'failure-evidence.json').exists());self.assertEqual(self.audits,0)
        # One failed original does not prevent observing the other original.
        self.assertEqual(self.run_one(self.fixture(players=6))['outcome'],'pending')

    def test_success_extracts_real_archive_and_audits_once(self):
        f=self.fixture(stage='COMPLETED',raw=True)
        first=self.run_one(f);second=self.run_one(f)
        self.assertEqual(first['outcome'],'verified_success');self.assertFalse(first['reused_audit'])
        self.assertTrue(second['reused_audit']);self.assertEqual(self.audits,1)
        self.assertEqual(self.downloads,1);self.assertEqual(self.fetches,1)

    def test_changed_cached_audit_is_rejected(self):
        f=self.fixture(stage='COMPLETED',raw=True);self.run_one(f)
        write(f.output/'independent-audit/result.json',{'passed':False})
        with self.assertRaises(AssertionError):self.run_one(f)

    def test_changed_admission_file_is_rejected(self):
        f=self.fixture(stage='COMPLETED',raw=True);self.run_one(f)
        write(f.output/'artifacts/admission.json',{'changed':True})
        with self.assertRaises(AssertionError):self.run_one(f)

    def test_admission_provenance_is_checked_beyond_file_manifest(self):
        f=self.fixture(stage='ERROR',raw=True)
        receipt=json.loads(f.lines[0]);evidence=receipt['evidence']
        status=read(f.reference/'status.json');status['provenance']['admission_sha256']='0'*64
        write(f.reference/'status.json',status)
        pins=read(f.reference/'manifest.json');pins['status.json']=digest(f.reference/'status.json')
        write(f.reference/'manifest.json',pins);evidence['manifest_sha256']=digest(f.reference/'manifest.json')
        with self.assertRaises(AssertionError):c.raw_checked(f.reference,self.source,f.row,evidence)

    def test_corrupt_archive_hash_is_rejected(self):
        f=self.fixture(stage='ERROR',raw=True)
        archive=self.jobs/f.row['job']['name']/'synthetic.tgz';archive.write_bytes(b'corrupted')
        with self.assertRaises(AssertionError):self.run_one(f)
        self.assertFalse((f.output/'artifacts').exists())

    def test_early_failure_allows_zero_samples_but_success_does_not(self):
        f=self.fixture(stage='ERROR',raw=True);evidence=json.loads(f.lines[0])['evidence']
        status=read(f.reference/'status.json')
        for key in ('cpu_seconds','sampled_peak_total_rss_bytes','memory_samples'):status['measurement'][key]=0
        for stage in ('failed','complete'):
            status['stage']=stage;write(f.reference/'status.json',status)
            pins=read(f.reference/'manifest.json');pins['status.json']=digest(f.reference/'status.json')
            write(f.reference/'manifest.json',pins);evidence['manifest_sha256']=digest(f.reference/'manifest.json')
            if stage=='failed':self.assertEqual(c.raw_checked(f.reference,self.source,f.row,evidence),status)
            else:
                with self.assertRaises(AssertionError):c.raw_checked(f.reference,self.source,f.row,evidence)

    def test_missing_or_duplicate_archive_receipt_is_unverified(self):
        for duplicate,players in [(False,2),(True,6)]:
            f=self.fixture(players=players,stage='COMPLETED',raw=True,receipt=duplicate)
            if duplicate:f.lines.append(f.lines[0])
            self.assertEqual(self.run_one(f)['outcome'],'unverified_terminal')
        self.assertEqual(self.audits+self.downloads,0)

    def test_unknown_stage_is_not_treated_as_terminal_success(self):
        result=self.run_one(self.fixture(stage='UNKNOWN'))
        self.assertEqual(result['outcome'],'unknown_stage');self.assertEqual(self.fetches,0)

    def test_remote_source_or_admission_environment_mismatch_is_rejected(self):
        f=self.fixture();f.info.environment={'PUBLIC_PIN':'changed'}
        with self.assertRaises(AssertionError):self.run_one(f)
        self.assertEqual(self.downloads+self.audits,0)

    def test_changed_remote_stage_invalidates_cached_success(self):
        f=self.fixture(stage='COMPLETED',raw=True);self.run_one(f);f.info.status.stage='ERROR'
        with self.assertRaises(AssertionError):self.run_one(f)

    def test_interrupted_log_fetch_is_not_saved_as_complete(self):
        f=self.fixture(stage='COMPLETED',raw=True)
        def interrupted(**kwargs):
            yield 'prefix'
            raise ConnectionError('synthetic observation failure')
        f.api.fetch_job_logs=interrupted
        with self.assertRaises(ConnectionError):self.run_one(f)
        self.assertFalse((f.output/'job.log').exists());self.assertEqual(self.downloads+self.audits,0)

    def test_interrupted_audit_directory_is_not_reused(self):
        f=self.fixture(stage='COMPLETED',raw=True);f.output.mkdir();(f.output/'independent-audit').mkdir()
        with self.assertRaisesRegex(AssertionError,'interrupted independent audit'):self.run_one(f)
        self.assertFalse((f.output/'verified.json').exists())

    def test_failed_job_cannot_pass_combined_gate(self):
        records=[];guards={}
        for players,stage in [(2,'ERROR'),(6,'COMPLETED')]:
            f=self.fixture(players=players,stage=stage,raw=True)
            records.append(self.run_one(f));guards[f.row['job']['name']]=f.guard
        report=c.summarize(records,self.source,guards)
        self.assertTrue(report['all_terminal']);self.assertFalse(report['complete'])
        self.assertEqual(report['verified_games'],24);self.assertEqual(report['failed_jobs_preserved'],1)

    def test_only_both_complete_jobs_pass_32_game_gate(self):
        records=[];guards={}
        for players in (2,6):
            f=self.fixture(players=players,stage='COMPLETED',raw=True)
            records.append(self.run_one(f));guards[f.row['job']['name']]=f.guard
        report=c.summarize(records,self.source,guards)
        self.assertTrue(report['complete']);self.assertEqual(report['verified_games'],32)
        self.assertFalse(report['qualification_eligible']);self.assertEqual(report['new_inference'],0)
        records[0]['review']['games']=7
        with self.assertRaises(AssertionError):c.summarize(records,self.source,guards)

    def test_duplicate_handle_cannot_pass_gate(self):
        a=self.fixture();b=self.fixture(players=6)
        records=[self.run_one(a),self.run_one(b)]
        records[1]['job_id']=records[0]['job_id']
        with self.assertRaises(AssertionError):c.summarize(records,self.source,
            {a.row['job']['name']:a.guard,b.row['job']['name']:b.guard})

    def test_guards_require_both_original_sources_and_distinct_handles(self):
        a=self.fixture();b=self.fixture(players=6)
        # Update the test's first guard to the now-complete two-row source.
        write(self.jobs/a.row['job']['name']/'launch.json',a.guard)
        self.assertEqual(len(c.guards_checked(self.source)),2)
        b.guard['job_id']=a.guard['job_id'];write(self.jobs/b.row['job']['name']/'launch.json',b.guard)
        with self.assertRaises(AssertionError):c.guards_checked(self.source)

    def test_unlaunched_guard_is_rejected(self):
        a=self.fixture();b=self.fixture(players=6)
        write(self.jobs/a.row['job']['name']/'launch.json',a.guard)
        b.guard['stage']='launch_unknown';write(self.jobs/b.row['job']['name']/'launch.json',b.guard)
        with self.assertRaises(AssertionError):c.guards_checked(self.source)

    def test_actual_audit_driver_uses_v4_and_complete_pairing(self):
        f=self.fixture(stage='COMPLETED',raw=True)
        evidence=json.loads(f.lines[0])['evidence'];auditdir=self.root/'audit-driver'
        self.manager.preflight=SimpleNamespace(OUT=self.root/'prepared')
        def fake_subprocess(command,**kwargs):
            self.assertIn('from resource_turn_full_audit_v4 import audit',command[4])
            self.assertNotIn('require_pairs=False',command[4])
            self.assertEqual(command[1:4],['-u','-B','-c'])
            self.assertEqual(command[5],str(self.root/'prepared/source/artifact'))
            write(auditdir/'result.json',read(f.reference/'evaluation/independent-audit.json'))
        with patch.object(c.subprocess,'run',side_effect=fake_subprocess):
            review=c.independent_audit(f.reference,self.source,f.row,evidence,auditdir)
        self.assertEqual(review['games'],8)

    def test_incomplete_report_rejected_before_audit_process(self):
        f=self.fixture(stage='COMPLETED',raw=True);evidence=json.loads(f.lines[0])['evidence']
        report=read(f.reference/'evaluation/evaluation.json');report['completed_games']=7
        write(f.reference/'evaluation/evaluation.json',report)
        # The archive manifest detects the changed file before any auditor starts.
        with patch.object(c.subprocess,'run',side_effect=AssertionError('Audit must not start')):
            with self.assertRaises(AssertionError):
                c.independent_audit(f.reference,self.source,f.row,evidence,self.root/'audit')
        self.assertFalse((self.root/'audit').exists())


if __name__=='__main__':
    folder=c.TEST.parent;assert not folder.exists(), 'Preserve previous tests before rerunning changed code'
    folder.mkdir();sources=[Path(__file__).resolve(),PATH.resolve(),Path(c.launcher.__file__),
        ROOT/'ai/strong/prepare-resource-turn-runtime-v2.py',ROOT/'ai/strong/resource_turn_runtime_job_v2.py',
        ROOT/'ai/strong/resource_turn_full_audit_v4.py',ROOT/'ai/strong/population_policy_verification.py']
    for path in sources:shutil.copy2(path,folder/path.name)
    with patch.object(c,'HfApi',side_effect=AssertionError('Real API disabled in offline tests')):
        result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
    save(c.TEST,{'passed':result.wasSuccessful(),'tests':result.testsRun,'network_calls':0,'new_hf_jobs':0,
        'new_inference':0,'new_full_game_trajectories':0,'synthetic_archives_only':True,
        'code_hashes':{str(path.relative_to(ROOT)):digest(path) for path in sources},
        'qualification_eligible':False,'reserved_final_seeds_used':False})
    raise SystemExit(0 if result.wasSuccessful() else 1)
