"""Exercise HF wrapper routing and failure preservation without remote effects."""
import importlib.util
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from strategic_collection import ROOT, read, write, digest

spec=importlib.util.spec_from_file_location('surrogate_job',ROOT/'ai/strong/opponent-surrogate-collection-job-v1.py')
job=importlib.util.module_from_spec(spec)
spec.loader.exec_module(job)
MODEL=ROOT/'ai/runs/policy-iteration-trained-8840u-prepared-v2/local-package-frozen-1/policy.onnx'


class JobBoundaryTest(unittest.TestCase):
    def test_routes_full_runtime_case_and_preserves_failure(self):
        class ReachedCollection(Exception): pass
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            capture=root/'ai/strong/capture-reference-opponent-v1.cjs'
            capture.parent.mkdir(parents=True)
            shutil.copy2(ROOT/'ai/strong/capture-reference-opponent-v1.cjs',capture)
            manifest=root/'opponent-surrogate-source-manifest.json'
            write(manifest,{str(capture.relative_to(root)):digest(capture)})
            env={'PROTOCOL_SHA256':digest(job.PROTOCOL),'SOURCE_MANIFEST_SHA256':digest(manifest),
                 'SOURCE_REVISION':'boundary-test-only','SOURCE_SHA256':'boundary-test-only'}
            for n in (2,6):
                with patch.dict(os.environ,env), patch.object(job,'ROOT',root), \
                     patch.object(job,'hf_hub_download',return_value=str(MODEL)) as download, \
                     patch.object(job,'run',side_effect=ReachedCollection()) as run, \
                     patch.object(job,'upload_evidence',return_value={'synthetic_boundary_receipt':True}) as upload:
                    with self.assertRaises(ReachedCollection): job.main(n,0,1,'runtime')
                    output=root/f'ai/runs/opponent-surrogate-runtime-v1-{n}p-0-1'
                    run.assert_called_once_with(root,str(MODEL),n,0,1,'runtime',output/'games',8)
                    pin=read(job.PROTOCOL)['focal']['model']
                    download.assert_called_once_with(pin['repo'],pin['prefix']+'/inference64.onnx',revision=pin['revision'])
                    status=read(output/'job.json')
                    self.assertEqual(status['stage'],'failed')
                    self.assertTrue(status['error'].startswith('ReachedCollection:'))
                    self.assertFalse(status['gradients'])
                    self.assertFalse(status['qualification_eligible'])
                    upload.assert_called_once_with(output)
                    self.assertTrue(all(digest(output/name)==sha for name,sha in read(output/'manifest.json').items()))

    def test_invalid_runtime_contract_stops_before_remote_access(self):
        invalid=[(3,0,1,'runtime'),(2,1,2,'runtime'),(6,0,2,'runtime'),(2,0,1,'final')]
        with patch.object(job,'hf_hub_download') as download, patch.object(job,'upload_evidence') as upload:
            for args in invalid:
                with self.assertRaises(AssertionError): job.main(*args)
            download.assert_not_called()
            upload.assert_not_called()


if __name__=='__main__': unittest.main()
