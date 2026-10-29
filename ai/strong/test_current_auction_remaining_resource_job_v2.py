"""Actual tracked row metadata; synthetic first-audit proof, no game execution."""
from copy import deepcopy
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import current_auction_remaining_resource_job_v2 as w

STRONG=Path(__file__).resolve().parent


class RemainingWorkerTests(unittest.TestCase):
    def setUp(self):
        self.original=w.read(STRONG/'current-auction-grid-source-v1.json')
        self.decision=w.read(STRONG/'current-auction-resource-recovery-decision-v2.json')
        self.first_source=w.read(STRONG/'current-auction-resource-supervisor-source-v2.json')
        self.names=[r['name'] for r in self.decision['fixed_recovery_rows'] if r['reason']=='never_submitted']
        self.first=next(r for r in self.original['rows'] if r['name']==w.base.FAILED_NAME)
        self.result={'verified':True,'games':16,'original_name':w.base.FAILED_NAME,'original_failed_handle':w.base.FAILED_HANDLE,
            'attempt_id':w.base.ATTEMPT,'job_id':w.FIRST_HANDLE,'original_failure_preserved':True,'remaining_rows_admitted':False,
            'qualification_eligible':False,'qualified':False,'reserved_final_seeds_used':False,
            'source_descriptor_sha256':w.FIRST_SOURCE_SHA,'collector_sha256':w.FIRST_COLLECTOR_SHA,
            'manager_sha256':w.FIRST_MANAGER_SHA,'bundle_manifest_sha256':self.first_source['manifest_sha256'],
            'terminal':{'job_id':w.FIRST_HANDLE,'stage':'COMPLETED','timeout_seconds':86400,'flavor':'cpu-upgrade','public_configuration_verified':True},
            'review':{'games':16,'audit':{'identity':deepcopy(self.first['identity']),'all_receipts_verified':True,
                'counts':{'rollout_caps':0},'reserved_final_seeds_used':False}},'retained_episodes':list(range(80,96)),
            'checkpoint_archives':[{'episodes':list(range(80,96)),
                'evidence':self.evidence('archives/'+w.base.ATTEMPT+'-checkpoint-0001.tgz')}],
            'envelope_evidence':self.evidence('archives/'+w.base.ATTEMPT+'-final.tgz')}

    def evidence(self,path):
        return {'repo':w.base.retention.REPO,'archive_path':path,'revision':'a'*40,'archive_sha256':'b'*64,'remote_archive_verified':True}

    def gate(self):return w.first_recovery_gate(self.result,self.original,self.first_source)

    def bundle(self,with_result=False):
        tmp=TemporaryDirectory();self.addCleanup(tmp.cleanup);root=Path(tmp.name);folder=root/'bundle';folder.mkdir()
        for name,path in [(w.ENTRY,Path(w.__file__)),(w.base.ENTRY,Path(w.base.__file__)),(w.base.CORE,Path(w.base.retention.__file__)),
            ('original-source.json',STRONG/'current-auction-grid-source-v1.json'),
            ('decision.json',STRONG/'current-auction-resource-recovery-decision-v2.json'),
            ('first-recovery-source.json',STRONG/'current-auction-resource-supervisor-source-v2.json')]:
            shutil.copyfile(path,folder/name)
        if with_result:w.save(folder/'first-recovery-result.json',self.result)
        w.save(folder/'manifest.json',{p.name:w.digest(p) for p in folder.iterdir()})
        return root,folder,w.digest(folder/'manifest.json')

    def test_all_actual_323_rows_have_unique_attempt_names_and_7100_games(self):
        rows=[w.remaining_row(self.original,self.decision,name) for name in self.names]
        self.assertEqual(len(rows),323);self.assertEqual(sum(r['shard']['games'] for r in rows),7100)
        attempts=[w.attempt_name(name) for name in self.names];self.assertEqual(len(set(attempts)),323)
        self.assertNotIn(w.base.ATTEMPT,attempts);self.assertTrue(all('_' not in a for a in attempts))
        self.assertEqual({r['players'] for r in rows},{2,3,5,6})

    def test_first_recovery_and_already_audited_original_cannot_be_replayed(self):
        for name in (w.base.FAILED_NAME,self.original['rows'][0]['name']):
            with self.assertRaises(ValueError):w.remaining_row(self.original,self.decision,name)

    def test_changed_planned_seed_or_workers_is_rejected(self):
        row=next(r for r in self.original['rows'] if r['name']==self.names[0])
        row['shard']['seed']='strong-multiplayer-final-reserved-v1'
        with self.assertRaisesRegex(ValueError,'row changed'):w.remaining_row(self.original,self.decision,row['name'])
        row['shard']['seed']=f"current-auction-confirmation-v1-{row['players']}p";row['identity']['settings']['workers']=8
        with self.assertRaisesRegex(ValueError,'row changed'):w.remaining_row(self.original,self.decision,row['name'])

    def test_complete_synthetic_first_proof_passes_metadata_gate_only(self):
        self.assertTrue(self.gate())

    def test_wrong_first_handle_failed_status_or_capped_receipts_rejected(self):
        original=deepcopy(self.result)
        self.result['job_id']='c'*24
        with self.assertRaises(ValueError):self.gate()
        self.result=deepcopy(original);self.result['terminal']['stage']='ERROR'
        with self.assertRaises(ValueError):self.gate()
        self.result=deepcopy(original);self.result['review']['audit']['counts']['rollout_caps']=1
        with self.assertRaises(ValueError):self.gate()

    def test_first_checkpoint_missing_or_duplicated_game_rejected(self):
        eps=self.result['checkpoint_archives'][0]['episodes'];eps[-1]=eps[0]
        with self.assertRaisesRegex(ValueError,'omitted/duplicated'):self.gate()

    def test_changed_auditor_or_policy_cannot_grant_remaining_execution(self):
        original=deepcopy(self.result);self.result['collector_sha256']='f'*64
        with self.assertRaisesRegex(ValueError,'admitted collector'):self.gate()
        self.result=original;self.result['review']['audit']['identity']['settings']['workers']=8
        with self.assertRaisesRegex(ValueError,'changed policy'):self.gate()

    def test_execution_without_first_result_stops_before_source_or_child(self):
        root,bundle,sha=self.bundle()
        with patch.object(w.base.retention,'supervise') as child:
            with self.assertRaisesRegex(ValueError,'audited first recovery is required'):
                w.run(bundle,sha,root/'missing-source',root/'NEVER-EXECUTED',self.names[0],execute=True,upload=True)
        child.assert_not_called();self.assertFalse((root/'NEVER-EXECUTED').exists())

    def test_even_synthetic_first_result_cannot_execute_without_reviewed_admission(self):
        root,bundle,sha=self.bundle(with_result=True)
        with patch.object(w.base.retention,'supervise') as child:
            with self.assertRaisesRegex(ValueError,'reviewed remaining-grid preparation required'):
                w.run(bundle,sha,root/'missing-source',root/'NEVER-EXECUTED',self.names[0],execute=True,upload=True)
        child.assert_not_called();self.assertFalse((root/'NEVER-EXECUTED').exists())

    def test_changed_retention_helper_cannot_be_hidden_by_repacked_manifest(self):
        root,bundle,sha=self.bundle();path=bundle/w.base.CORE;path.write_text(path.read_text()+'\n# changed\n')
        pins=w.read(bundle/'manifest.json');pins[w.base.CORE]=w.digest(path)
        (bundle/'manifest.json').unlink();w.save(bundle/'manifest.json',pins)
        with self.assertRaisesRegex(ValueError,'Unpinned worker/retention code'):
            w.inspect(bundle,w.digest(bundle/'manifest.json'),root/'missing-source',root/'NEVER-EXECUTED',self.names[0],execute=True)


if __name__=='__main__':unittest.main()
