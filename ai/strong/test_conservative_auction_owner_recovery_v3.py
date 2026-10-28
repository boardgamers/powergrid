"""Recovery cannot erase existing jobs, bypass an audit failure or duplicate an owner."""
from copy import deepcopy
import importlib.util
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location('recovery_v3',Path(__file__).with_name('recover-conservative-auction-development-v3.py'))
recovery=importlib.util.module_from_spec(spec);spec.loader.exec_module(recovery)


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.args={'state':{'pid':1919833,'stage':'waiting_for_original_development_jobs',
            'development_submitted':360,'development_verified':296,'development_expected':648,
            'development_source_sha256':recovery.SOURCE_SHA},'state_sha':recovery.OLD_SHA,
            'process_live':False,'stop_present':False,'guard_count':360,'verified_count':296,
            'statuses':{str(i):'COMPLETED' for i in range(64)}}

    def test_reviewed_originals_admitted(self):
        recovery.admit(**self.args)

    def test_live_stopped_changed_or_missing_state_rejected(self):
        for key,value in [('process_live',True),('stop_present',True),('state_sha','changed'),('guard_count',359),('verified_count',295)]:
            with self.subTest(key=key),self.assertRaises(AssertionError):recovery.admit(**{**self.args,key:value})

    def test_failure_running_or_unknown_original_rejected(self):
        for stage in ('RUNNING','SCHEDULING','ERROR','FAILED','TIMEOUT','CANCELED','UNKNOWN'):
            states={**self.args['statuses'],'0':stage}
            with self.subTest(stage=stage),self.assertRaises(AssertionError):recovery.admit(**{**self.args,'statuses':states})
        with self.assertRaises(AssertionError):recovery.admit(**{**self.args,'statuses':{}})

    def test_different_source_stage_or_submission_count_rejected(self):
        for key,value in [('pid',123),('stage','stopped_for_inspection'),('development_source_sha256','changed'),
                          ('development_submitted',361),('development_verified',297),('development_expected',649)]:
            state=deepcopy(self.args['state']);state[key]=value
            with self.subTest(key=key),self.assertRaises(AssertionError):recovery.admit(**{**self.args,'state':state})


if __name__=='__main__':unittest.main()
