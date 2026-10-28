"""Submission guard tests use a fake API and never contact HF."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

from public_policy_development_job_v1 import digest

ROOT=Path(__file__).resolve().parents[2]
path=Path(__file__).with_name('manage-resource-turn-runtime-v1.py')
spec=importlib.util.spec_from_file_location('resource_runtime_manager_tested',path)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


class FakeApi:
    def __init__(self,error=None,handle='a'*24):self.calls=[];self.error=error;self.handle=handle
    def run_job(self,**kwargs):
        self.calls.append(kwargs)
        if self.error:raise self.error
        return SimpleNamespace(id=self.handle)


class Guards(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.folder=Path(self.temp.name)
        self.row={'file':'case.job.json','job':{'name':'runtime-case','control':False},'job_spec_sha256':'d'*64}
        self.source={'rows':[self.row],'flavor':'cpu-upgrade','timeout':'4h',
            'archive':'source.tgz','revision':'b'*40,'sha256':'c'*64,'source_manifest_sha256':'e'*64}
        self.api=FakeApi()
    def tearDown(self):self.temp.cleanup()
    def launch(self,api=None,source=None,row=None):
        return m.launch_once(api or self.api,self.folder,source or self.source,row or self.row,'unit-test-token')
    def test_exact_repeated_request_never_resubmits(self):
        first=self.launch();self.assertEqual(first,self.launch());self.assertEqual(len(self.api.calls),1)
        self.assertEqual(first['stage'],'launched');self.assertEqual(first['job_id'],'a'*24)
        self.assertNotIn('unit-test-token',(self.folder/'launch.json').read_text())
        self.assertEqual(self.api.calls[0]['secrets'],{'HF_TOKEN':'unit-test-token'})
    def test_unknown_outcome_is_preserved_and_not_retried(self):
        api=FakeApi(RuntimeError('synthetic unknown transport outcome'))
        with self.assertRaises(RuntimeError):self.launch(api=api)
        self.assertEqual(m.read(self.folder/'launch.json')['stage'],'launch_unknown')
        with self.assertRaises(AssertionError):self.launch(api=api)
        self.assertEqual(len(api.calls),1)
    def test_prior_intent_is_not_submitted(self):
        m.save(self.folder/'launch.json',{'stage':'launch_intent'})
        with self.assertRaises(AssertionError):self.launch()
        self.assertFalse(self.api.calls)
    def test_unadmitted_row_is_rejected(self):
        row=deepcopy(self.row);row['file']='other.job.json'
        with self.assertRaises(AssertionError):self.launch(row=row)
        self.assertFalse(self.api.calls);self.assertFalse((self.folder/'launch.json').exists())
    def test_existing_source_cannot_change(self):
        self.launch();source=deepcopy(self.source);source['revision']='f'*40
        with self.assertRaises(AssertionError):self.launch(source=source)
        self.assertEqual(len(self.api.calls),1)
    def test_invalid_returned_handle_is_unknown(self):
        api=FakeApi(handle='invalid')
        with self.assertRaises(AssertionError):self.launch(api=api)
        self.assertEqual(m.read(self.folder/'launch.json')['stage'],'launch_unknown')
        with self.assertRaises(AssertionError):self.launch(api=api)
        self.assertEqual(len(api.calls),1)
    def test_local_control_cannot_be_submitted(self):
        self.row['job']['control']=True
        with self.assertRaises(AssertionError):self.launch()
        self.assertFalse(self.api.calls)
    def test_exact_bootstrap_and_public_environment(self):
        self.launch();request=self.api.calls[0]
        self.assertEqual(request['command'],['bash','-lc',m.BOOTSTRAP])
        self.assertEqual(request['env'],m.environment(self.source,self.row))
        self.assertNotIn('HF_TOKEN',request['env'])
        self.assertNotIn('urllib.request.urlretrieve(',m.BOOTSTRAP)
        cache=m.read(m.CACHE)
        self.assertIn(cache['revision'],m.BOOTSTRAP);self.assertIn(cache['sha256'],m.BOOTSTRAP)
        self.assertIn('/workspace/source/resource_turn_runtime_job_v1.py',m.BOOTSTRAP)


if __name__=='__main__':
    assert not m.TEST.exists(),'Preserve previous test receipt before rerunning changed code'
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(Guards)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    m.save(m.TEST,{'passed':result.wasSuccessful(),'tests':result.testsRun,'new_hf_jobs':0,
        'code_hashes':{str(p.relative_to(ROOT)):digest(p) for p in (Path(__file__).resolve(),path.resolve(),
            ROOT/'ai/strong/conservative_auction_bootstrap_recovery_v1.py',m.CACHE,
            ROOT/'ai/strong/prepare-resource-turn-runtime-v1.py',ROOT/'ai/strong/resource_turn_runtime_job_v1.py')}})
    raise SystemExit(0 if result.wasSuccessful() else 1)
