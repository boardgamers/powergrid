"""Synthetic recovery envelopes; raw engine audit and remote transport mocked."""
from pathlib import Path
import shutil
import unittest
from unittest.mock import Mock, patch

import current_auction_resource_collection_v2 as c
from test_current_auction_resource_job_v2 import WorkerControlsTests


class CollectionTests(unittest.TestCase):
    def setUp(self):
        # Reuse only the tested synthetic source/control fixture, not its tests.
        self.fixture = WorkerControlsTests('test_default_is_validation_without_output_or_execution')
        self.fixture.setUp(); self.addCleanup(self.fixture.doCleanups)
        self.fixture.admission(); f = self.fixture; self.write = f.write
        self.expected = c.reference_configuration(f.bundle,f.bundle_sha,f.source)
        self.folder=f.root/'final';self.folder.mkdir();self.supervisor=self.folder/'supervisor';self.supervisor.mkdir()
        self.raw=self.folder/'raw';self.evaluation=self.raw/'job/evaluation';self.evaluation.mkdir(parents=True)
        self.write(self.folder/'attempt.json',self.expected)
        self.write(self.supervisor/'context.json',self.expected['context'])
        self.result={'stage':'child_exited','attempt_id':c.worker.ATTEMPT,'child_returncode':0,
            'retained_episodes':list(range(80,96)),'expected_episodes':16,'checkpoints':2,
            'raw_audited':False,'qualified':False,'automatic_retries':False}
        self.status={'stage':'child_complete_pending_independent_audit','attempt_id':c.worker.ATTEMPT,
            'original_name':c.worker.FAILED_NAME,'original_failed_handle':c.worker.FAILED_HANDLE,
            'qualified':False,'reserved_final_seeds_used':False,'automatic_retries':False,'supervisor':self.result}
        self.write(self.folder/'run-status.json',self.status);self.write(self.supervisor/'supervisor-result.json',self.result)
        for ep in range(80,96):
            self.write(self.evaluation/f'game-{ep}.json',{'episode':ep})
            (self.evaluation/f'decisions-{ep}.jsonl').write_text('{"synthetic":true}\n')
        self.manifest(self.raw)
        self.checkpoints={};self.transports=[];self.receipts=[]
        for serial,start in enumerate((80,88),1):
            name=f'{c.worker.ATTEMPT}-checkpoint-{serial:04d}'
            folder=f.root/name;folder.mkdir();batch=list(range(start,start+8));hashes={}
            for ep in batch:
                names=[f'game-{ep}.json',f'decisions-{ep}.jsonl'];hashes[str(ep)]={}
                for filename in names:
                    shutil.copyfile(self.evaluation/filename,folder/filename);hashes[str(ep)][filename]=c.digest(folder/filename)
            self.write(folder/'checkpoint.json',{'version':2,'context':self.expected['context'],'episodes':batch,
                'pair_hashes':hashes,'raw_audited':False,'execution_complete':False,'qualified':False})
            self.manifest(folder)
            evidence={'repo':c.worker.retention.REPO,'archive_path':'archives/'+name+'.tgz',
                'revision':'a'*40,'archive_sha256':'b'*64,'manifest_sha256':c.digest(folder/'manifest.json'),
                'remote_archive_verified':True}
            receipt={'context_sha256':c.digest(self.supervisor/'context.json'),'evidence':evidence,
                'episodes':batch,'raw_audited':False,'qualified':False}
            self.write(self.supervisor/(name+'.receipt.json'),receipt);self.receipts.append(receipt)
            self.write(self.supervisor/(name+'.upload-intent.json'),{'manifest_sha256':evidence['manifest_sha256'],'automatic_retries':False})
            self.transports.append({'directory':name,'evidence':evidence,'manifest_sha256':evidence['manifest_sha256'],
                'started_at':'2026-10-29T09:00:00+00:00','finished_at':'2026-10-29T09:00:01+00:00',
                'child_live_before_upload':True,'child_live_after_upload':True})
            self.checkpoints[evidence['archive_path']]=folder
        self.write(self.folder/'checkpoint-transports.json',self.transports)
        self.evidence={'repo':c.worker.retention.REPO,'archive_path':'archives/'+c.worker.ATTEMPT+'-final.tgz',
            'revision':'c'*40,'archive_sha256':'d'*64,'manifest_sha256':'e'*64,'remote_archive_verified':True}
        self.seal()
        self.reader=Mock(side_effect=lambda evidence:self.checkpoints[evidence['archive_path']])
        self.audit=Mock(return_value={'games':16,'raw_audit':'mocked'})
        self.fixture.stack.enter_context(patch.object(c.original.m.base,'verify_artifacts',self.audit))

    def manifest(self,folder):
        self.write(folder/'manifest.json',{str(p.relative_to(folder)):c.digest(p)
            for p in sorted(folder.rglob('*')) if p.is_file() and p != folder/'manifest.json'})

    def seal(self):
        self.manifest(self.folder);self.evidence['manifest_sha256']=c.digest(self.folder/'manifest.json')

    def collect(self):
        f=self.fixture
        return c.audit_envelope(self.folder,self.evidence,f.bundle,f.bundle_sha,f.source,self.reader)

    def test_complete_envelope_binds_all_checkpoint_bytes_before_raw_audit(self):
        result=self.collect();self.assertTrue(result['verified']);self.assertEqual(result['games'],16)
        self.assertEqual(result['retained_episodes'],list(range(80,96)))
        self.assertFalse(result['qualified']);self.assertTrue(result['original_failure_preserved'])
        self.assertEqual(self.reader.call_count,2);self.audit.assert_called_once()
        args=self.audit.call_args.args
        self.assertEqual(args[0],self.raw);self.assertEqual(args[1],self.expected['original_source'])
        self.assertEqual(args[2],self.expected['row']);self.assertEqual(args[3]['manifest_sha256'],c.digest(self.raw/'manifest.json'))

    def test_failed_child_is_preserved_not_admitted(self):
        self.status['stage']='failed_preserved';self.write(self.folder/'run-status.json',self.status);self.seal()
        with self.assertRaisesRegex(ValueError,'did not complete'):self.collect()
        self.reader.assert_not_called();self.audit.assert_not_called()

    def test_changed_command_or_policy_context_is_rejected(self):
        attempt=c.read(self.folder/'attempt.json');attempt['command'].append('--upload')
        self.write(self.folder/'attempt.json',attempt);self.seal()
        with self.assertRaisesRegex(ValueError,'binding differs'):self.collect()
        self.audit.assert_not_called()

    def test_missing_retained_episode_is_not_hidden_by_final_raw_data(self):
        self.result['retained_episodes'].pop();self.write(self.supervisor/'supervisor-result.json',self.result)
        self.write(self.folder/'run-status.json',self.status);self.seal()
        with self.assertRaisesRegex(ValueError,'retained coverage'):self.collect()
        self.audit.assert_not_called()

    def test_uploads_only_after_child_exit_do_not_pass_retention_gate(self):
        for t in self.transports:t['child_live_after_upload']=False
        self.write(self.folder/'checkpoint-transports.json',self.transports);self.seal()
        with self.assertRaisesRegex(ValueError,'while original child'):self.collect()
        self.audit.assert_not_called()

    def test_unknown_checkpoint_intent_blocks_complete_claim(self):
        self.write(self.supervisor/'extra.upload-intent.json',{'automatic_retries':False});self.seal()
        with self.assertRaisesRegex(ValueError,'ambiguous checkpoint'):self.collect()
        self.audit.assert_not_called()

    def test_unverified_or_foreign_checkpoint_is_rejected(self):
        name=self.transports[0]['directory'];path=self.supervisor/(name+'.receipt.json')
        value=c.read(path);value['evidence']['remote_archive_verified']=False;self.write(path,value);self.seal()
        with self.assertRaisesRegex(ValueError,'Unverified or foreign'):self.collect()
        self.audit.assert_not_called()

    def test_repacked_checkpoint_cannot_change_original_final_bytes(self):
        folder=next(iter(self.checkpoints.values()));path=self.evaluation/'game-80.json';path.write_text('{"episode":999}')
        self.manifest(self.raw);self.seal()
        with self.assertRaisesRegex(ValueError,'final original bytes differ'):self.collect()
        self.audit.assert_not_called()

    def test_outer_hash_change_is_rejected_before_downloads(self):
        (self.folder/'run-status.json').write_text('{}')
        with self.assertRaisesRegex(ValueError,'Pinned file changed'):self.collect()
        self.reader.assert_not_called();self.audit.assert_not_called()

    def test_duplicate_transport_does_not_count_as_extra_retention(self):
        self.write(self.folder/'checkpoint-transports.json',[self.transports[0],self.transports[0]]);self.seal()
        with self.assertRaisesRegex(ValueError,'Duplicate checkpoint transport'):self.collect()
        self.audit.assert_not_called()

    def test_raw_legality_or_search_audit_failure_is_not_swallowed(self):
        self.audit.side_effect=ValueError('Illegal original move')
        with self.assertRaisesRegex(ValueError,'Illegal original move'):self.collect()
        self.assertEqual(self.reader.call_count,2)


if __name__=='__main__':unittest.main()
