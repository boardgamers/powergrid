"""Small synthetic coverage partitions; review loading is mocked."""
from copy import deepcopy
import unittest
from unittest.mock import Mock

import current_auction_recovery_coverage_v2 as c


class CoverageTests(unittest.TestCase):
    def setUp(self):
        names=['preserved',c.worker.FAILED_NAME,'unsubmitted'];self.rows=[]
        for name,n,start in zip(names,(2,4,6),(0,5,1)):
            self.rows.append({'name':name,'players':n,'arm':'filter' if n==2 else 'conservative_population',
                'shard':{'name':name,'players':n,'seed':f'current-auction-confirmation-v1-{n}p',
                    'start':start,'deals':1,'games':4*n,'group':f'search/{n}'}})
        self.source={'rows':self.rows,'games':48}
        self.failed={'name':names[1],'job_id':c.worker.FAILED_HANDLE,'stage':'ERROR','verified':False,'row':self.rows[1]}
        self.cycle={'expected_jobs':3,'verified_jobs':1,'active_originals':[],'deferred_terminals':[],
            'complete':False,'qualified':False,'reserved_final_seeds_used':False,
            'audited_originals':[{'name':names[0],'job_id':'a'*24,'stage':'ERROR','evidence':{'synthetic':True}}],
            'failed_originals':[self.failed],'unsubmitted_jobs':[names[2]]}
        self.decision={'full_canonical_shards':3,'full_canonical_games':48,'original_audited_shards':1,
            'original_audited_games':8,'never_submitted_rows':1,'original_failed_handle':c.worker.FAILED_HANDLE,
            'source_sha256':c.worker.SOURCE_SHA,'strength_outcomes_used_for_decision':False,
            'original_failure_erased':False,'frozen_inputs_changed':False,'recovery_rows':2,'recovery_unique_games':40,
            'hf_completed_audited':0,'hf_error_complete_data_audited':1,
            'fixed_recovery_rows':[{'name':row['name'],'original_row_sha256':c.object_hash(row),'games':row['shard']['games'],
                'reason':'original_timeout_missing_raw_data' if i==0 else 'never_submitted',
                'original_handle':c.worker.FAILED_HANDLE if i==0 else None} for i,row in enumerate(self.rows[1:])]}

    def plan(self):return c.build_plan(self.source,self.cycle,self.decision,
        {'job_id':'1'*24,'attempt_id':c.worker.ATTEMPT,'original_failed_handle':c.worker.FAILED_HANDLE})

    def assignments(self):
        self.current_plan=self.plan();refs=[];reviews={}
        for i,slot in enumerate(s for s in self.current_plan['slots'] if s['kind']!='preserved_original'):
            ref={'name':slot['name'],'original_row_sha256':slot['original_row_sha256'],
                'original_failed_handle':c.worker.FAILED_HANDLE if i==0 else None,
                'job_id':str(i+1)*24,'attempt_id':c.worker.ATTEMPT if i==0 else f'new-attempt-{i}',
                'stage':'COMPLETED','verified':True,'review_sha256':'e'*64}
            refs.append(ref);reviews[slot['name']]={'verified':True,'original_name':slot['name'],'job_id':ref['job_id'],
                'attempt_id':ref['attempt_id'],'original_failed_handle':ref['original_failed_handle'],
                'games':len(slot['episodes']),'retained_episodes':slot['episodes'],'qualified':False,
                'reserved_final_seeds_used':False,'review':{'audit':{'all_receipts_verified':True,'counts':{'rollout_caps':0}}}}
        self.reviews=reviews;self.loader=Mock(side_effect=lambda ref:self.reviews[ref['name']]);return refs

    def complete(self,refs):return c.require_complete_assignments(self.current_plan,refs,self.loader)

    def test_partition_preserves_original_error_and_failed_job_without_double_counting(self):
        plan=self.plan()
        self.assertEqual(plan['shards_by_disposition'],{'preserved_original':1,'failed_original_recovery':1,'first_execution':1})
        self.assertEqual(plan['games_by_disposition'],{'preserved_original':8,'failed_original_recovery':16,'first_execution':24})
        self.assertEqual(plan['original_hf_status_counts'],{'ERROR':2})
        self.assertEqual(plan['original_failure_preserved'],self.failed)
        self.assertFalse(plan['submission_admitted']);self.assertFalse(plan['statistics_admitted'])

    def test_overlapping_or_omitted_original_dispositions_are_rejected(self):
        for value in (['unsubmitted','preserved'],[]):
            self.cycle['unsubmitted_jobs']=value
            with self.assertRaisesRegex(ValueError,'overlap|partition omits'):self.plan()

    def test_changed_seed_or_recovery_row_is_rejected(self):
        self.rows[1]['shard']['seed']='strong-multiplayer-final-reserved-v1'
        with self.assertRaisesRegex(ValueError,'confirmation seeds'):self.plan()
        self.rows[1]['shard']['seed']='current-auction-confirmation-v1-4p';self.rows[1]['shard']['start']=6
        with self.assertRaisesRegex(ValueError,'recovery row changed'):self.plan()

    def test_canonical_game_overlap_is_rejected_even_with_different_row_names(self):
        row=self.rows[2];row['players']=4;row['shard']={**self.rows[1]['shard'],'name':row['name']}
        self.decision['fixed_recovery_rows'][1].update(original_row_sha256=c.object_hash(row),games=16)
        with self.assertRaisesRegex(ValueError,'Overlapping canonical games'):self.plan()

    def test_complete_assignments_admit_only_further_raw_audit_and_keep_original_failure(self):
        refs=self.assignments();result=self.complete(list(reversed(refs)))
        self.assertEqual(result['recovery_games'],40);self.assertEqual(result['recovery_shards'],2)
        self.assertTrue(result['raw_reaudit_required']);self.assertFalse(result['statistics_admitted'])
        self.assertEqual(result['original_failure_preserved']['job_id'],c.worker.FAILED_HANDLE)
        self.assertEqual([args.args[0]['name'] for args in self.loader.call_args_list],self.current_plan['fixed_recovery_order'])

    def test_missing_duplicate_or_extra_assignment_rejects_before_reading_any_review(self):
        refs=self.assignments()
        for values in (refs[:1],[refs[0],refs[0]],refs+[dict(refs[0],name='foreign')]):
            with self.assertRaisesRegex(ValueError,'coverage|Duplicate'):self.complete(values)
        self.loader.assert_not_called()

    def test_original_or_reused_recovery_handle_rejects_before_review_loading(self):
        refs=self.assignments()
        for handle in ('a'*24,c.worker.FAILED_HANDLE,refs[0]['job_id']):
            values=deepcopy(refs);values[1]['job_id']=handle
            with self.assertRaisesRegex(ValueError,'Duplicate/original'):self.complete(values)
        self.loader.assert_not_called()

    def test_another_first_recovery_cannot_replace_the_admitted_attempt(self):
        refs=self.assignments();refs[0]['job_id']='9'*24
        with self.assertRaisesRegex(ValueError,'exact admitted attempt'):self.complete(refs)
        self.loader.assert_not_called()

    def test_old_original_handle_cannot_be_used_to_construct_the_first_recovery(self):
        with self.assertRaisesRegex(ValueError,'own exact admitted handle'):
            c.build_plan(self.source,self.cycle,self.decision,
                {'job_id':c.worker.FAILED_HANDLE,'attempt_id':c.worker.ATTEMPT,'original_failed_handle':c.worker.FAILED_HANDLE})

    def test_changed_row_unverified_or_running_attempt_cannot_hide_behind_full_count(self):
        refs=self.assignments()
        for key,value in [('original_row_sha256','b'*64),('verified',False),('stage','RUNNING'),('original_failed_handle',None)]:
            values=deepcopy(refs);values[0][key]=value
            with self.assertRaises(ValueError):self.complete(values)
        self.loader.assert_not_called()

    def test_missing_or_substituted_episodes_are_rejected(self):
        refs=self.assignments();review=self.reviews[refs[1]['name']]
        review['retained_episodes']=review['retained_episodes'][:-1]+[999]
        with self.assertRaisesRegex(ValueError,'planned episodes'):self.complete(refs)

    def test_loaded_wrong_identity_or_capped_receipts_do_not_pass(self):
        refs=self.assignments();review=self.reviews[refs[0]['name']]
        review['job_id']='f'*24
        with self.assertRaisesRegex(ValueError,'differs from assignment'):self.complete(refs)
        review['job_id']=refs[0]['job_id'];review['review']['audit']['counts']['rollout_caps']=1
        with self.assertRaisesRegex(ValueError,'capped recovery'):self.complete(refs)


if __name__=='__main__':unittest.main()
