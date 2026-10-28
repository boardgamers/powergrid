"""Offline tests of admission binding and one-attempt HF launch behavior."""
import base64
from copy import deepcopy
from datetime import datetime,timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from public_policy_development_job_v1 import digest,read

ROOT=Path(__file__).resolve().parents[2]
PATH=Path(__file__).with_name('launch-resource-turn-runtime-v2.py')
spec=importlib.util.spec_from_file_location('resource_launcher_under_test',PATH)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


class FakeApi:
    def __init__(self,error=None,handle='a'*24,inspections=None):
        self.calls=[];self.error=error;self.handle=handle;self.inspections=inspections or {};self.inspected=[]
    def run_job(self,**kwargs):
        self.calls.append(kwargs)
        if self.error:raise self.error
        return SimpleNamespace(id=self.handle)
    def inspect_job(self,job_id):
        self.inspected.append(job_id);return self.inspections[job_id]


class Guards(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.folder=Path(self.temp.name)
        self.row={'file':'case-2.job.json','job':{'name':'runtime-2','control':False},'job_spec_sha256':'d'*64}
        self.row6={'file':'case-6.job.json','job':{'name':'runtime-6','control':False},'job_spec_sha256':'f'*64}
        raw=b'{"synthetic_fixtures_only":true}\n'
        self.source={'rows':[self.row,self.row6],'flavor':'cpu-upgrade','timeout':'14400s','games':32,
            'max_concurrent_jobs':2,'automatic_retries':False,'archive':'source.tgz','revision':'b'*40,
            'sha256':'c'*64,'source_manifest_sha256':'e'*64,
            'admission_base64':base64.b64encode(raw).decode(),'admission_sha256':hashlib.sha256(raw).hexdigest()}
        self.api=FakeApi()
    def tearDown(self):self.temp.cleanup()
    def launch(self,api=None,source=None,row=None):
        return m.launch_once(api or self.api,self.folder,source or self.source,row or self.row,'unit-test-token')
    def test_repeated_request_returns_original_handle(self):
        first=self.launch();self.assertEqual(first,self.launch());self.assertEqual(len(self.api.calls),1)
        self.assertEqual(first['job_id'],'a'*24)
        self.assertNotIn('unit-test-token',(self.folder/'launch.json').read_text())
        self.assertEqual(self.api.calls[0]['secrets'],{'HF_TOKEN':'unit-test-token'})
    def test_unknown_submission_is_never_retried(self):
        api=FakeApi(error=ConnectionError('synthetic lost response'))
        with self.assertRaises(ConnectionError):self.launch(api=api)
        self.assertEqual(read(self.folder/'launch.json')['stage'],'launch_unknown')
        with self.assertRaises(AssertionError):self.launch(api=api)
        self.assertEqual(len(api.calls),1)
    def test_prior_intent_prevents_submission(self):
        m.save(self.folder/'launch.json',{'stage':'launch_intent'})
        with self.assertRaises(AssertionError):self.launch()
        self.assertFalse(self.api.calls)
    def test_invalid_handle_is_unknown_and_not_retried(self):
        api=FakeApi(handle='invalid')
        with self.assertRaises(AssertionError):self.launch(api=api)
        with self.assertRaises(AssertionError):self.launch(api=api)
        self.assertEqual(len(api.calls),1)
        self.assertEqual(read(self.folder/'launch.json')['stage'],'launch_unknown')
    def test_changed_admission_cannot_reuse_guard(self):
        self.launch();changed=deepcopy(self.source);changed['admission_sha256']='0'*64
        with self.assertRaises(AssertionError):self.launch(source=changed)
        self.assertEqual(len(self.api.calls),1)
    def test_changed_source_cannot_reuse_guard(self):
        self.launch();changed=deepcopy(self.source);changed['revision']='0'*40
        with self.assertRaises(AssertionError):self.launch(source=changed)
        self.assertEqual(len(self.api.calls),1)
    def test_third_job_and_control_cannot_submit(self):
        extra=deepcopy(self.row);extra['file']='extra.job.json'
        with self.assertRaises(AssertionError):self.launch(row=extra)
        changed=deepcopy(self.source);changed['rows'].append(extra)
        with self.assertRaises(AssertionError):self.launch(source=changed)
        self.row['job']['control']=True
        with self.assertRaises(AssertionError):self.launch()
        self.assertFalse(self.api.calls)
    def test_two_jobs_have_independent_single_attempts(self):
        first=self.launch();other=self.folder/'six';other.mkdir()
        six=FakeApi(handle='b'*24)
        second=m.launch_once(six,other,self.source,self.row6,'unit-test-token')
        self.assertNotEqual(first['job_id'],second['job_id'])
        self.assertEqual(second,m.launch_once(six,other,self.source,self.row6,'unit-test-token'))
        self.assertEqual(len(self.api.calls),1);self.assertEqual(len(six.calls),1)
    def test_exact_bootstrap_admission_and_environment(self):
        self.launch();request=self.api.calls[0]
        self.assertEqual(request['command'],['bash','-lc',m.BOOTSTRAP])
        self.assertEqual(request['env'],m.environment(self.source,self.row))
        self.assertNotIn('HF_TOKEN',request['env'])
        self.assertNotIn('urllib.request.urlretrieve(',m.BOOTSTRAP)
        cache=read(m.CACHE)
        self.assertIn(cache['revision'],m.BOOTSTRAP);self.assertIn(cache['sha256'],m.BOOTSTRAP)
        self.assertIn('/workspace/source/resource_turn_runtime_job_v2.py',m.BOOTSTRAP)
        self.assertIn('--admission /workspace/runtime-admission.json',m.BOOTSTRAP)
        self.assertNotIn('resource_turn_runtime_job_v1.py',m.BOOTSTRAP)
        self.assertEqual(request['timeout'],'14400s')
    def test_bootstrap_shell_syntax(self):
        subprocess.run(['bash','-n'],input=m.BOOTSTRAP,text=True,check=True,capture_output=True)
    def test_bootstrap_materializes_exact_separate_admission(self):
        code=m.BOOTSTRAP.split("python - <<'ADMISSION'\n")[1].split('\nADMISSION\n')[0]
        path=self.folder/'admission.json'
        code=code.replace('/workspace/runtime-admission.json',str(path))
        env={**os.environ,**m.environment(self.source,self.row)}
        subprocess.run([sys.executable,'-B','-c',code],env=env,check=True,capture_output=True)
        self.assertEqual(digest(path),self.source['admission_sha256'])
        bad=self.folder/'wrong.json';code=code.replace(str(path),str(bad))
        result=subprocess.run([sys.executable,'-B','-c',code],env={**env,'RUNTIME_ADMISSION_SHA256':'0'*64},capture_output=True)
        self.assertNotEqual(result.returncode,0);self.assertFalse(bad.exists())


class Admission(unittest.TestCase):
    def setUp(self):
        self.prep=read(m.preflight.OUT/'prepared.json');self.protocol=read(m.preflight.PROTOCOL)
        self.sha='1'*64
        self.admission={'revision':'resource-turn-runtime-admission-v2',
            'source_manifest_sha256':self.prep['source_manifest_sha256'],'protocol_sha256':self.prep['protocol_sha256'],
            'all_originals_terminal':True,'original_outcomes_sha256':self.sha,'source_evidence_preserved':True,
            'scope':'runtime-only','automatic_retries':False,'qualification_eligible':False,'reserved_final_seeds_used':False,
            'job_specs':{n:digest(m.preflight.OUT/'source'/n) for n,j in self.protocol['jobs'].items() if not j['control']},
            'flavor':'cpu-upgrade','max_concurrent_jobs':2,'timeout_seconds':14400,
            'budget_review':{'original_outcomes_sha256':self.sha,'max_total_job_hours':8,
                'reason':'SYNTHETIC UNIT TEST ONLY; never an actual reviewed runtime admission.',
                'reviewed_at':datetime.now(timezone.utc).isoformat()}}
    def check(self):return m.admission_checked(self.admission,self.prep,self.protocol,self.sha)
    def test_binding_shape_can_be_checked_without_launch(self):self.assertEqual(self.check(),self.admission)
    def test_each_source_binding_is_required(self):
        for key in ('source_manifest_sha256','protocol_sha256','original_outcomes_sha256'):
            with self.subTest(key=key):
                old=self.admission[key];self.admission[key]='0'*64
                with self.assertRaises(AssertionError):self.check()
                self.admission[key]=old
    def test_exact_job_set_is_required(self):
        self.admission['job_specs'].pop(next(iter(self.admission['job_specs'])))
        with self.assertRaises(AssertionError):self.check()
    def test_scope_flags_and_synthetic_data_are_rejected(self):
        for key,value in [('all_originals_terminal',False),('source_evidence_preserved',False),
                ('automatic_retries',True),('qualification_eligible',True),('reserved_final_seeds_used',True),
                ('synthetic_fixtures_only',True),('scope','development')]:
            with self.subTest(key=key):
                old=deepcopy(self.admission);self.admission[key]=value
                with self.assertRaises(AssertionError):self.check()
                self.admission=old
    def test_review_must_bind_original_measurements(self):
        self.admission['budget_review']['original_outcomes_sha256']='0'*64
        with self.assertRaises(AssertionError):self.check()
    def test_budget_limits_and_accounting(self):
        for key,value in [('timeout_seconds',7199),('timeout_seconds',43201),('timeout_seconds',14400.0),
                ('max_concurrent_jobs',3),('flavor','a10g-large')]:
            with self.subTest(key=key):
                old=deepcopy(self.admission);self.admission[key]=value
                with self.assertRaises(AssertionError):self.check()
                self.admission=old
        self.admission['budget_review']['max_total_job_hours']=4
        with self.assertRaises(AssertionError):self.check()
    def test_reason_and_timestamp_required(self):
        self.admission['budget_review']['reason']=''
        with self.assertRaises(AssertionError):self.check()


class Outcomes(unittest.TestCase):
    def setUp(self):
        records=[]
        for name,handle in m.collector.HANDLES.items():
            records.append({'name':'pg-resource-turn-runtime-v1-'+name,'job_id':handle,
                'stage':'ERROR','outcome':'failed_preserved','verified':False})
        self.report=m.collector.summarize(records)
    def test_terminal_failures_remain_failures(self):
        self.assertEqual(len(m.terminal_summary_checked(self.report)),6)
        self.assertFalse(self.report['success_gate_passed']);self.assertEqual(self.report['verified_successful_games'],0)
    def test_invented_handle_is_rejected(self):
        self.report['jobs'][0]['job_id']='0'*24
        with self.assertRaises(AssertionError):m.terminal_summary_checked(self.report)
    def test_live_original_cannot_be_admitted_by_boolean(self):
        self.report['jobs'][0]['stage']='RUNNING'
        with self.assertRaises(AssertionError):m.terminal_summary_checked(self.report)
    def test_missing_failure_archive_cannot_be_ignored(self):
        self.report['jobs'][0]['outcome']='unverified_terminal'
        with self.assertRaises(AssertionError):m.terminal_summary_checked(self.report)
    def test_success_cannot_be_fabricated_in_summary(self):
        self.report['success_gate_passed']=True
        with self.assertRaises(AssertionError):m.terminal_summary_checked(self.report)
    def test_duplicate_original_is_rejected(self):
        self.report['jobs'][0]=deepcopy(self.report['jobs'][1])
        with self.assertRaises(AssertionError):m.terminal_summary_checked(self.report)
    def test_fresh_remote_stage_must_match(self):
        source={'rows':[{'job':{'name':r['name']},'file':r['name']+'.job.json'} for r in self.report['jobs']],
            'flavor':'cpu-upgrade','archive':'old.tgz','revision':'a'*40,'sha256':'b'*64,'source_manifest_sha256':'c'*64}
        info={r['job_id']:SimpleNamespace(status=SimpleNamespace(stage='ERROR'),
            command=['bash','-lc',m.original.BOOTSTRAP],docker_image='python:3.11-slim-bookworm',flavor='cpu-upgrade',
            environment=m.original.environment(source,row)) for r,row in zip(self.report['jobs'],source['rows'])}
        api=FakeApi(inspections=info);m.inspect_original_terminals(api,self.report,source)
        self.assertEqual(len(api.inspected),6)
        info[self.report['jobs'][0]['job_id']].status.stage='RUNNING'
        with self.assertRaises(AssertionError):m.inspect_original_terminals(api,self.report,source)
        self.assertFalse(api.calls)
    def test_actual_preparation_is_blocked_without_terminal_report_or_admission(self):
        # Current real source/preflight; no fabricated original outcomes or
        # admission can reach actual prepare. No API is allowed in this test.
        self.assertFalse(m.ADMISSION.exists())
        self.assertFalse(m.OUT.exists());self.assertFalse(m.ARCHIVE.exists());self.assertFalse(m.SOURCE.exists())
        with self.assertRaises((FileNotFoundError,AssertionError)):m.prepare()
        self.assertFalse(m.OUT.exists());self.assertFalse(m.ARCHIVE.exists());self.assertFalse(m.SOURCE.exists())


if __name__=='__main__':
    folder=m.TEST.parent
    assert not folder.exists(), 'Preserve prior test sources and outcome before another run'
    folder.mkdir();sources=[Path(__file__).resolve(),PATH.resolve(),Path(m.preflight.__file__),
        Path(m.collector.__file__),Path(m.original.__file__),m.CACHE,
        ROOT/'ai/strong/conservative_auction_bootstrap_recovery_v1.py',
        ROOT/'ai/strong/manage-public-policy-development-hf-v1.py',ROOT/'ai/strong/resource_turn_runtime_job_v2.py']
    for path in sources:shutil.copy2(path,folder/path.name)
    suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(c) for c in (Guards,Admission,Outcomes))
    with patch.object(m,'HfApi',side_effect=AssertionError('Real API disabled in offline tests')):
        result=unittest.TextTestRunner(verbosity=2).run(suite)
    m.save(m.TEST,{'passed':result.wasSuccessful(),'tests':result.testsRun,'network_calls':0,'new_hf_jobs':0,
        'new_inference':0,'new_full_game_trajectories':0,'actual_admission_created':False,
        'code_hashes':{str(path.relative_to(ROOT)):digest(path) for path in sources},
        'qualification_eligible':False,'reserved_final_seeds_used':False})
    raise SystemExit(0 if result.wasSuccessful() else 1)
