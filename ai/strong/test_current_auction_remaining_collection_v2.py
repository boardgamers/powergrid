"""Variable-size envelopes; configuration, downloads and raw auditor mocked."""
from contextlib import ExitStack
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock,patch

import current_auction_remaining_collection_v2 as c


class RemainingCollectionTests(unittest.TestCase):
    def setUp(self):
        self.stack=ExitStack();self.addCleanup(self.stack.close)
        self.root=Path(self.stack.enter_context(TemporaryDirectory()));self.serial=0
        strong=Path(__file__).resolve().parent
        self.original=c.read(strong/'current-auction-grid-source-v1.json')
        self.decision=c.read(strong/'current-auction-resource-recovery-decision-v2.json')
        self.configuration=Mock();self.audit=Mock()
        self.stack.enter_context(patch.object(c,'reference_configuration',self.configuration))
        self.stack.enter_context(patch.object(c.original.m.base,'verify_artifacts',self.audit))
        self.build(5)

    def write(self,path,value):
        if path.exists():path.unlink()
        c.worker.save(path,value)

    def manifest(self,folder):
        self.write(folder/'manifest.json',{str(p.relative_to(folder)):c.digest(p)
            for p in sorted(folder.rglob('*')) if p.is_file() and p!=folder/'manifest.json'})

    def build(self,n):
        self.serial+=1;root=self.root/str(self.serial);root.mkdir()
        names={r['name'] for r in self.decision['fixed_recovery_rows'] if r['reason']=='never_submitted'}
        row=next(r for r in self.original['rows'] if r['name'] in names and r['players']==n)
        self.name=row['name'];self.attempt=c.worker.attempt_name(self.name)
        start=row['shard']['start']*4*n;self.eps=list(range(start,start+row['shard']['games']))
        self.expected={'attempt_id':self.attempt,'row':row,'original_source':self.original,'command':['frozen-command'],
            'context':{'attempt_id':self.attempt,'decision_sha256':c.worker.base.DECISION_SHA,
                'source_descriptor_sha256':c.worker.base.SOURCE_SHA,'original_row_sha256':c.worker.base.object_hash(row),'original_row':row},
            'admission_sha256':'a'*64,'first_recovery_result_sha256':'b83b2dfa755d3bc0ea6500461a6ca8166724c6ce2b6071dab282798378a91940'}
        self.configuration.return_value=self.expected;self.audit.return_value={'games':len(self.eps),'raw_audit':'mocked'}
        self.folder=root/'final';self.supervisor=self.folder/'supervisor';self.supervisor.mkdir(parents=True)
        self.raw=self.folder/'raw';self.evaluation=self.raw/'job/evaluation';self.evaluation.mkdir(parents=True)
        self.write(self.folder/'attempt.json',self.expected);self.write(self.supervisor/'context.json',self.expected['context'])
        self.result={'stage':'child_exited','attempt_id':self.attempt,'child_returncode':0,'retained_episodes':self.eps,
            'expected_episodes':len(self.eps),'checkpoints':2,'raw_audited':False,'qualified':False,'automatic_retries':False}
        self.status={'stage':'child_complete_pending_independent_audit','attempt_id':self.attempt,'original_name':self.name,
            'original_failed_handle':None,'qualified':False,'reserved_final_seeds_used':False,'automatic_retries':False,'supervisor':self.result}
        self.write(self.folder/'run-status.json',self.status);self.write(self.supervisor/'supervisor-result.json',self.result)
        for ep in self.eps:
            self.write(self.evaluation/f'game-{ep}.json',{'synthetic_episode':ep})
            (self.evaluation/f'decisions-{ep}.jsonl').write_text('{"synthetic":true}\n')
        self.manifest(self.raw);self.checkpoints={};self.transports=[]
        for serial,batch in enumerate((self.eps[:len(self.eps)//2],self.eps[len(self.eps)//2:]),1):
            name=f'{self.attempt}-checkpoint-{serial:04d}';folder=root/name;folder.mkdir();hashes={}
            for ep in batch:
                hashes[str(ep)]={}
                for filename in (f'game-{ep}.json',f'decisions-{ep}.jsonl'):
                    shutil.copyfile(self.evaluation/filename,folder/filename);hashes[str(ep)][filename]=c.digest(folder/filename)
            self.write(folder/'checkpoint.json',{'version':2,'context':self.expected['context'],'episodes':batch,
                'pair_hashes':hashes,'raw_audited':False,'execution_complete':False,'qualified':False});self.manifest(folder)
            evidence=self.evidence(name,c.digest(folder/'manifest.json'))
            self.write(self.supervisor/(name+'.receipt.json'),{'context_sha256':c.digest(self.supervisor/'context.json'),
                'evidence':evidence,'episodes':batch,'raw_audited':False,'qualified':False})
            self.write(self.supervisor/(name+'.upload-intent.json'),{'manifest_sha256':evidence['manifest_sha256'],'automatic_retries':False})
            self.transports.append({'directory':name,'evidence':evidence,'manifest_sha256':evidence['manifest_sha256'],
                'started_at':'2026-10-29T10:00:00+00:00','finished_at':'2026-10-29T10:00:01+00:00',
                'child_live_before_upload':True,'child_live_after_upload':True})
            self.checkpoints[evidence['archive_path']]=folder
        self.write(self.folder/'checkpoint-transports.json',self.transports)
        self.evidence_result=self.evidence(self.attempt+'-final','e'*64);self.seal()
        self.reader=Mock(side_effect=lambda evidence:self.checkpoints[evidence['archive_path']])

    def evidence(self,name,sha):
        return {'repo':c.worker.base.retention.REPO,'archive_path':'archives/'+name+'.tgz','revision':'a'*40,
            'archive_sha256':'b'*64,'manifest_sha256':sha,'remote_archive_verified':True}

    def seal(self):
        self.manifest(self.folder);self.evidence_result['manifest_sha256']=c.digest(self.folder/'manifest.json')

    def collect(self):
        return c.audit_envelope(self.folder,self.evidence_result,Path('/mock/bundle'),'c'*64,Path('/mock/source'),self.name,self.reader)

    def test_actual_2_3_5_6_player_row_sizes_bind_all_pairs_before_raw_audit(self):
        for n in (2,3,5,6):
            self.build(n);result=self.collect()
            self.assertEqual(result['games'],len(self.eps));self.assertEqual(result['retained_episodes'],self.eps)
            self.assertEqual(result['first_recovery_result_sha256'],self.expected['first_recovery_result_sha256'])
            self.assertIsNone(result['original_failed_handle']);self.assertFalse(result['qualified'])
            self.assertEqual(self.reader.call_count,2)
            self.assertEqual(self.audit.call_args.args[2],self.expected['row'])

    def test_changed_first_grant_is_rejected(self):
        config=c.read(self.folder/'attempt.json');config['first_recovery_result_sha256']='f'*64
        self.write(self.folder/'attempt.json',config);self.seal()
        with self.assertRaisesRegex(ValueError,'binding differs'):self.collect()
        self.reader.assert_not_called()

    def test_wrong_canonical_name_is_not_accepted_as_another_shard(self):
        self.status['original_name']='another-shard';self.write(self.folder/'run-status.json',self.status);self.seal()
        with self.assertRaisesRegex(ValueError,'did not complete'):self.collect()

    def test_failed_original_child_stays_failed(self):
        self.status['stage']='failed_preserved';self.write(self.folder/'run-status.json',self.status);self.seal()
        with self.assertRaisesRegex(ValueError,'did not complete'):self.collect()

    def test_missing_episode_cannot_hide_behind_matching_report_count(self):
        self.result['retained_episodes']=self.eps[:-1];self.write(self.supervisor/'supervisor-result.json',self.result)
        self.write(self.folder/'run-status.json',self.status);self.seal()
        with self.assertRaisesRegex(ValueError,'retained coverage'):self.collect()

    def test_retention_after_exit_only_is_rejected(self):
        for t in self.transports:t['child_live_after_upload']=False
        self.write(self.folder/'checkpoint-transports.json',self.transports);self.seal()
        with self.assertRaisesRegex(ValueError,'while original child'):self.collect()

    def test_ambiguous_upload_intent_is_preserved_as_failure(self):
        self.write(self.supervisor/'unknown.upload-intent.json',{});self.seal()
        with self.assertRaisesRegex(ValueError,'ambiguous checkpoint'):self.collect()

    def test_unverified_archive_is_rejected(self):
        path=next(self.supervisor.glob('*.receipt.json'));r=c.read(path);r['evidence']['remote_archive_verified']=False
        self.write(path,r);self.seal()
        with self.assertRaisesRegex(ValueError,'Unverified or foreign'):self.collect()

    def test_final_raw_bytes_must_match_checkpoint_bytes(self):
        self.write(self.evaluation/f'game-{self.eps[0]}.json',{'changed':True});self.manifest(self.raw);self.seal()
        with self.assertRaisesRegex(ValueError,'final original bytes differ'):self.collect()

    def test_duplicate_transport_records_are_rejected(self):
        self.write(self.folder/'checkpoint-transports.json',[self.transports[0],self.transports[0]]);self.seal()
        with self.assertRaisesRegex(ValueError,'Duplicate checkpoint transport'):self.collect()

    def test_wrong_independent_raw_audit_count_is_rejected(self):
        self.audit.return_value={'games':1}
        with self.assertRaisesRegex(ValueError,'audited game count'):self.collect()

    def test_original_raw_legality_failure_is_not_swallowed(self):
        self.audit.side_effect=ValueError('Illegal original action')
        with self.assertRaisesRegex(ValueError,'Illegal original action'):self.collect()


if __name__=='__main__':unittest.main()
