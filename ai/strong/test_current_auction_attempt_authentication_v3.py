"""Mixed-attempt provenance attacks; no inference, simulation or remote calls."""
from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import current_auction_attempt_authentication_v3 as a


class BucketBindingTests(unittest.TestCase):
    def setUp(self):
        self.name='pg-current-confirm-v1-pop-example-2p-00';self.attempt='pg-current-bucket-v3-pop-example-2p-00'
        self.row={'name':self.name,'players':2,'identity':{'policy':'frozen'},
            'shard':{'name':self.name,'players':2,'start':0,'deals':1,'games':8,'seed':'current-auction-confirmation-v1-2p'}}
        self.source={'manifest_sha256':'a'*64,'revision':'b'*40}
        self.reference={'name':self.name,'backend':'bucket_remaining_v3','original_row_sha256':a.object_hash(self.row),
            'original_failed_handle':None,'job_id':'c'*24,'attempt_id':self.attempt,'stage':'COMPLETED','verified':True}
        self.guard={'job_id':'c'*24,'attempt_id':self.attempt,'original_name':self.name,
            'original_row_sha256':a.object_hash(self.row),'prior_failed_attempts':[],
            'source':self.source,'allocation':deepcopy(a.first.worker.ALLOCATION),
            'transport':deepcopy(a.first.worker.TRANSPORT),'automatic_job_retries':False}
        self.controls={'source':self.source,'source_sha256':'d'*64,'manager_sha256':'e'*64,
            'collector_sha256':'f'*64,'environment':{'fixed':'source'},'bootstrap':'fixed bootstrap',
            'guard_sha256':'1'*64,'bundle_manifest_sha256':'2'*64}
        self.terminal={'job_id':'c'*24,'attempt_id':self.attempt,'stage':'COMPLETED','public_configuration_verified':True,
            'timeout_seconds':86400,'flavor':'cpu-upgrade','image':a.previous.first.IMAGE,
            'bootstrap_sha256':a.previous.first.sha_text(self.controls['bootstrap']),
            'environment_sha256':a.object_hash(self.controls['environment'])}
        self.expected={'attempt_id':self.attempt,'row':self.row,'control':{'prior_failed_attempts':[],'reason':'never_submitted'},
            'bundle_manifest_sha256':'2'*64,'admission_sha256':'3'*64}
        self.envelope={'storage':'hf_bucket','bucket':a.first.worker.archives.BUCKET,
            'download_verified':True,'server_versioning':False,'archive_sha256':'4'*64,'manifest_sha256':'5'*64,
            'xet_hash':'6'*64,'path':'confirmation-v3/'+self.attempt+'-final/'+'4'*64+'.tgz','bytes':100,
            'max_application_upload_calls':3,'application_upload_calls':1,'raw_audited':False,'qualified':False}
        self.archive={'repo':'coyotte508/powergrid-ai-germany-v1','archive_path':'archives/'+self.attempt+'-collected.tgz',
            'revision':'7'*40,'archive_sha256':'8'*64,'manifest_sha256':'9'*64,'remote_archive_verified':True,
            'format':'tar.gz','archived_files':20}
        self.review={'job_id':'c'*24,'attempt_id':self.attempt,'original_name':self.name,'prior_failed_attempts':[],
            'terminal':deepcopy(self.terminal),'launch_guard_sha256':'1'*64,'source_descriptor_sha256':'d'*64,
            'manager_sha256':'e'*64,'collector_sha256':'f'*64,'bundle_manifest_sha256':'2'*64,'admission_sha256':'3'*64,
            'verified':True,'games':8,'retained_episodes':list(range(8)),'qualification_eligible':False,'qualified':False,
            'reserved_final_seeds_used':False,'versioned_archive_pending':False,'envelope_evidence':self.envelope,
            'versioned_collection_archive':self.archive,'review':{'games':8,'audit':{'identity':self.row['identity'],
                'expected':self.row['shard'],'all_receipts_verified':True,'counts':{'rollout_caps':0},'reserved_final_seeds_used':False}}}
        self.receipt={'attempt_id':self.attempt,'bucket_final_evidence':deepcopy(self.envelope),
            'status':{'stage':'child_complete_pending_independent_audit','original_name':self.name,'prior_failed_attempts':[]}}

    def verify(self):return a.bucket_binding(self.reference,self.row,self.review,self.guard,self.terminal,self.receipt,self.expected,self.controls)

    def test_shared_pack_and_selected_row_have_distinct_valid_manifests(self):
        self.assertNotEqual(self.source['manifest_sha256'],self.expected['bundle_manifest_sha256'])
        self.assertIsNone(self.verify())
        self.reference['backend']='bucket_first_v3';self.assertIsNone(self.verify())

    def test_parent_manifest_cannot_replace_selected_row_manifest(self):
        self.review['bundle_manifest_sha256']=self.source['manifest_sha256']
        with self.assertRaisesRegex(ValueError,'selected-row'):self.verify()

    def test_seed_or_canonical_row_substitution_rejected(self):
        self.row['shard']['seed']='reserved-final-seed'
        with self.assertRaisesRegex(ValueError,'canonical'):self.verify()

    def test_unregistered_backend_and_unverified_reference_rejected(self):
        self.reference['backend']='other'
        with self.assertRaises(ValueError):self.verify()
        self.reference['backend']='bucket_first_v3';self.reference['verified']=False
        with self.assertRaises(ValueError):self.verify()

    def test_another_handle_cannot_reuse_completed_review(self):
        self.reference['job_id']='a'*24
        with self.assertRaisesRegex(ValueError,'identity'):self.verify()

    def test_invented_or_erased_failure_history_rejected(self):
        self.reference['original_failed_handle']='b'*24
        with self.assertRaises(ValueError):self.verify()
        self.reference['original_failed_handle']=None;self.guard['prior_failed_attempts']=[{'job_id':'b'*24}]
        with self.assertRaisesRegex(ValueError,'failure history'):self.verify()

    def test_changed_allocation_or_transport_rejected(self):
        self.guard['allocation']['search_workers']=8
        with self.assertRaisesRegex(ValueError,'settings'):self.verify()
        self.guard['allocation']=deepcopy(a.first.worker.ALLOCATION);self.guard['transport']['upload_attempts']=99
        with self.assertRaisesRegex(ValueError,'settings'):self.verify()

    def test_effective_terminal_binding_checked(self):
        for key,value in [('stage','ERROR'),('timeout_seconds',10800),('bootstrap_sha256','0'*64),('environment_sha256','0'*64)]:
            prior=self.terminal[key];self.terminal[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):self.verify()
            self.terminal[key]=prior

    def test_source_manager_collector_and_launch_hashes_checked(self):
        for key in ('source_descriptor_sha256','manager_sha256','collector_sha256','launch_guard_sha256','admission_sha256'):
            prior=self.review[key];self.review[key]='0'*64
            with self.subTest(key=key),self.assertRaises(ValueError):self.verify()
            self.review[key]=prior

    def test_duplicate_episode_cannot_satisfy_count(self):
        self.review['retained_episodes'][-1]=0
        with self.assertRaisesRegex(ValueError,'coverage'):self.verify()

    def test_capped_or_different_policy_audit_rejected(self):
        audit=self.review['review']['audit'];audit['counts']['rollout_caps']=1
        with self.assertRaisesRegex(ValueError,'raw review'):self.verify()
        audit['counts']['rollout_caps']=0;audit['identity']={'wrong':'policy'}
        with self.assertRaisesRegex(ValueError,'raw review'):self.verify()

    def test_unfinished_promotion_or_premature_qualification_rejected(self):
        for key in ('versioned_archive_pending','qualified','reserved_final_seeds_used'):
            self.review[key]=True
            with self.subTest(key=key),self.assertRaises(ValueError):self.verify()
            self.review[key]=False

    def test_log_must_bind_exact_original_bucket_envelope(self):
        self.receipt['bucket_final_evidence']['archive_sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'Original log'):self.verify()

    def test_failed_child_cannot_be_made_successful_by_outer_job(self):
        self.receipt['status']['stage']='failed_preserved'
        with self.assertRaisesRegex(ValueError,'did not complete'):self.verify()

    def test_versioned_archive_cannot_be_foreign_unpinned_or_unverified(self):
        for key,value in [('revision','main'),('archive_path','archives/foreign.tgz'),('remote_archive_verified',False),('manifest_sha256','bad')]:
            prior=self.archive[key];self.archive[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):self.verify()
            self.archive[key]=prior

    def test_missing_or_duplicate_final_receipt_is_not_guessed(self):
        line=json.dumps(self.receipt);self.assertEqual(a.final_receipt('startup\n'+line),self.receipt)
        for log in ('startup',line+'\n'+line):
            with self.assertRaisesRegex(ValueError,'Missing/ambiguous'):a.final_receipt(log)


class RoutingTests(unittest.TestCase):
    def setUp(self):
        self.failed=a.previous.first.worker.FAILED_NAME
        self.plan={'slots':[{'name':self.failed,'kind':'failed_original_recovery'},
            {'name':'old','kind':'first_execution'},{'name':'first','kind':'first_execution'},
            {'name':'new','kind':'first_execution'},{'name':'preserved','kind':'preserved_original'}],
            'fixed_recovery_order':[self.failed,'old','first','new']}

    def route(self,old=None,new=None):return a.routing(self.plan,['old'] if old is None else old,'first',['new'] if new is None else new)

    def test_exact_mixed_partition_keeps_original_failure_separate(self):
        self.assertEqual(self.route(),{self.failed:'timeout_v2','old':'retained_v2','first':'bucket_first_v3','new':'bucket_remaining_v3'})

    def test_overlapping_or_duplicate_routes_rejected(self):
        with self.assertRaisesRegex(ValueError,'overlapping'):self.route(new=['new','old'])
        with self.assertRaisesRegex(ValueError,'Duplicate'):self.route(old=['old','old'])

    def test_omitted_or_foreign_slot_rejected(self):
        with self.assertRaisesRegex(ValueError,'Incomplete'):self.route(new=[])
        with self.assertRaisesRegex(ValueError,'Foreign'):self.route(new=['new','foreign'])

    def test_already_audited_original_cannot_be_replayed(self):
        with self.assertRaisesRegex(ValueError,'Foreign'):self.route(new=['new','preserved'])

    def test_incomplete_study_rejects_before_context_or_review_loading(self):
        found={'available':[],'missing':[{'name':'old'}]}
        with patch.object(a.coverage,'actual_plan',return_value=self.plan),patch.object(a,'actual_routes',return_value=self.route()),\
             patch.object(a,'inventory',return_value=found),patch.object(a,'context') as context,patch.object(a,'authenticate') as loader:
            with self.assertRaisesRegex(ValueError,'Incomplete recovery coverage'):a.authenticate_complete()
        context.assert_not_called();loader.assert_not_called()

    def test_backend_substitution_rejected_before_file_read(self):
        with patch.object(a,'read') as read:
            with self.assertRaisesRegex(ValueError,'Unregistered'):a.authenticate({'name':'old','backend':'bucket_remaining_v3'},
                {'routes':{'old':'retained_v2'}})
        read.assert_not_called()

    def test_failed_attempt_stays_missing_without_loading_review(self):
        with TemporaryDirectory() as directory:
            root=Path(directory);folder=root/'job';folder.mkdir()
            (folder/'launch.json').write_text(json.dumps({'job_id':'a'*24}))
            (folder/'terminal.json').write_text(json.dumps({'job_id':'a'*24,'stage':'ERROR'}))
            plan={'slots':[{'name':'old','kind':'first_execution','original_row_sha256':'b'*64}],
                'fixed_recovery_order':['old']}
            with patch.object(a,'ROOT',root),patch.object(a,'locations',return_value={'folder':folder,'review':folder/'review.json'}):
                result=a.inventory(plan,{'old':'retained_v2'})
        self.assertEqual(result['available'],[]);self.assertFalse(result['complete'])
        self.assertEqual(result['missing'][0]['failed_handle'],'a'*24);self.assertFalse(result['review_contents_loaded'])


if __name__=='__main__':unittest.main()
