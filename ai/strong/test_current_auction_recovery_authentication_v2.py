"""Metadata provenance attacks and incomplete-study refusal; no game execution."""
from copy import deepcopy
import json
import unittest
from unittest.mock import Mock, patch

import current_auction_recovery_authentication_v2 as a


class AuthenticationTests(unittest.TestCase):
    def setUp(self):
        self.name = 'pg-current-confirm-v1-pop-example-5p-00'
        self.attempt = 'pg-current-retained-v2-pop-example-5p-00'
        self.row = {'name':self.name,'players':5,'identity':{'synthetic_policy':'fixed'},
            'shard':{'name':self.name,'players':5,'start':0,'deals':1,'games':20,'seed':'current-auction-confirmation-v1-5p'}}
        self.source = {'manifest_sha256':'a'*64,'revision':'b'*40}
        self.reference = {'name':self.name,'original_row_sha256':a.object_hash(self.row),
            'job_id':'c'*24,'attempt_id':self.attempt,'original_failed_handle':None,
            'stage':'COMPLETED','verified':True,'review_sha256':'d'*64}
        self.guard = {'job_id':'c'*24,'attempt_id':self.attempt,'original_failed_handle':None,
            'source':self.source,'allocation':deepcopy(a.first.worker.ALLOCATION),'automatic_retries':False}
        self.controls = {'source':self.source,'source_sha256':'e'*64,'collector_sha256':'f'*64,'manager_sha256':'1'*64,
            'environment':{'SOURCE_SHA256':'2'*64},'bootstrap':'fixed original setup and new supervisor'}
        self.terminal = {'job_id':'c'*24,'attempt_id':self.attempt,'stage':'COMPLETED','public_configuration_verified':True,
            'timeout_seconds':86400,'flavor':'cpu-upgrade','image':a.first.IMAGE,
            'bootstrap_sha256':a.first.sha_text(self.controls['bootstrap']),
            'environment_sha256':a.object_hash(self.controls['environment'])}
        self.expected = {'row':self.row,'context':{'attempt_id':self.attempt},
            'bundle_manifest_sha256':'a'*64,'admission_sha256':'3'*64}
        self.evidence = {'repo':'coyotte508/powergrid-ai-germany-v1','revision':'4'*40,
            'archive_path':'archives/'+self.attempt+'-final.tgz','archive_sha256':'5'*64,'manifest_sha256':'6'*64,
            'remote_archive_verified':True}
        self.review = {'job_id':'c'*24,'attempt_id':self.attempt,'original_name':self.name,'original_failed_handle':None,
            'terminal':deepcopy(self.terminal),'source_descriptor_sha256':'e'*64,'collector_sha256':'f'*64,'manager_sha256':'1'*64,
            'bundle_manifest_sha256':'a'*64,'admission_sha256':'3'*64,'verified':True,'games':20,
            'retained_episodes':list(range(20)),'qualification_eligible':False,'qualified':False,'reserved_final_seeds_used':False,
            'envelope_evidence':self.evidence,'review':{'games':20,'audit':{'identity':self.row['identity'],
                'expected':self.row['shard'],'all_receipts_verified':True,'counts':{'rollout_caps':0},'reserved_final_seeds_used':False}}}
        self.receipt = {'attempt_id':self.attempt,'recovery_final_evidence':deepcopy(self.evidence),
            'status':{'stage':'child_complete_pending_independent_audit','original_name':self.name,'original_failed_handle':None}}

    def verify(self):
        return a.receipt_binding(self.reference,self.row,self.review,self.guard,self.terminal,self.receipt,self.expected,self.controls)

    def test_consistent_receipts_bind_without_admitting_statistics(self):
        self.assertIsNone(self.verify())
        # Both supervisors share row/context fields, even though the first uses
        # a separate control block and the remaining worker has top-level names.
        self.expected['control']={'attempt_id':self.attempt}
        self.assertIsNone(self.verify())

    def test_changed_row_or_source_seed_is_not_hidden_by_matching_name(self):
        self.row['shard']['seed']='reserved-final-seed'
        with self.assertRaisesRegex(ValueError,'canonical row'):self.verify()

    def test_another_handle_cannot_reuse_an_existing_review(self):
        self.reference['job_id']='9'*24
        with self.assertRaisesRegex(ValueError,'identity differs'):self.verify()

    def test_erasing_failed_original_identity_is_rejected(self):
        self.reference['original_failed_handle']=a.first.worker.FAILED_HANDLE
        with self.assertRaisesRegex(ValueError,'identity differs'):self.verify()

    def test_unverified_reference_cannot_use_a_verified_review(self):
        self.reference['verified']=False
        with self.assertRaisesRegex(ValueError,'Unverified'):self.verify()

    def test_effective_timeout_and_bootstrap_are_verified(self):
        for key,value in [('timeout_seconds',10800),('bootstrap_sha256','8'*64),('environment_sha256','8'*64),('stage','ERROR')]:
            original=self.terminal[key];self.terminal[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):self.verify()
            self.terminal[key]=original

    def test_changed_guard_allocation_cannot_pass_effective_remote_record(self):
        self.guard['allocation']['search_workers']=8
        with self.assertRaisesRegex(ValueError,'Launch source/allocation'):self.verify()

    def test_old_collector_or_different_admission_is_rejected(self):
        for key in ('collector_sha256','manager_sha256','source_descriptor_sha256','admission_sha256','bundle_manifest_sha256'):
            original=self.review[key];self.review[key]='7'*64
            with self.subTest(key=key),self.assertRaises(ValueError):self.verify()
            self.review[key]=original

    def test_missing_or_duplicate_game_coverage_is_rejected(self):
        self.review['retained_episodes'][-1]=0
        with self.assertRaisesRegex(ValueError,'coverage'):self.verify()

    def test_capped_or_different_policy_review_is_rejected(self):
        audit=self.review['review']['audit'];audit['counts']['rollout_caps']=1
        with self.assertRaisesRegex(ValueError,'original raw review'):self.verify()
        audit['counts']['rollout_caps']=0;audit['identity']={'another':'policy'}
        with self.assertRaisesRegex(ValueError,'original raw review'):self.verify()

    def test_final_log_must_bind_exact_immutable_archive(self):
        self.receipt['recovery_final_evidence']['revision']='9'*40
        with self.assertRaisesRegex(ValueError,'Original log'):self.verify()

    def test_archive_name_and_remote_verification_are_required(self):
        for key,value in [('remote_archive_verified',False),('archive_path','archives/foreign.tgz'),('revision','main')]:
            original=self.evidence[key];self.evidence[key]=value;self.receipt['recovery_final_evidence'][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):self.verify()
            self.evidence[key]=original;self.receipt['recovery_final_evidence'][key]=original

    def test_missing_or_duplicate_final_receipt_is_not_guessed(self):
        line=json.dumps(self.receipt)
        self.assertEqual(a.final_receipt('startup text\n'+line+'\n{"status":"done"}'),self.receipt)
        for log in ('startup only',line+'\n'+line):
            with self.assertRaisesRegex(ValueError,'Missing/ambiguous'):a.final_receipt(log)

    def test_complete_entry_rejects_before_authentication_or_source_context(self):
        plan={'slots':[{'name':self.name,'kind':'first_execution'}],'fixed_recovery_order':[self.name]}
        values={'available':[],'missing':[{'name':self.name}],'required':1,'complete':False}
        with patch.object(a.coverage,'actual_plan',return_value=plan),patch.object(a,'inventory',return_value=values),\
             patch.object(a,'context') as context,patch.object(a,'authenticate') as authenticate:
            with self.assertRaisesRegex(ValueError,'Incomplete recovery coverage'):a.authenticate_complete()
        context.assert_not_called();authenticate.assert_not_called()

    def test_foreign_row_cannot_be_loaded_before_complete_coverage(self):
        current={'original_source':{'rows':[]},'plan':{'fixed_recovery_order':[]}}
        with self.assertRaisesRegex(ValueError,'Not a fixed'):a.authenticate(self.reference,current)

    def test_premature_qualification_and_failed_child_are_rejected(self):
        self.review['qualified']=True
        with self.assertRaisesRegex(ValueError,'qualification'):self.verify()
        self.review['qualified']=False;self.receipt['status']['stage']='failed_preserved'
        with self.assertRaisesRegex(ValueError,'did not complete'):self.verify()


if __name__=='__main__':unittest.main()
