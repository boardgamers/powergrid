"""Test-only controls against the actual frozen source; never execute games."""
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

import current_auction_bucket_worker_v3 as w

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT/'ai/runs/current-auction-grid-prepared-v1/source'


class WorkerTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.serial=0
        self.original=w.read(ROOT/'ai/strong/current-auction-grid-source-v1.json')
        old=w.read(ROOT/'ai/strong/current-auction-resource-recovery-decision-v2.json')
        submitted={r['name'] for r in w.read(ROOT/'ai/strong/current-auction-remaining-dispatch-v2.json')['records']}
        self.names={r['name'] for r in old['fixed_recovery_rows'] if r['reason']=='never_submitted'}-submitted
        self.build(5)

    def write(self,path,value):
        if path.exists():path.unlink()
        w.save(path,value)

    def seal(self):
        self.write(self.bundle/'manifest.json',{p.name:w.digest(p) for p in sorted(self.bundle.iterdir()) if p.name!='manifest.json'})
        return w.digest(self.bundle/'manifest.json')

    def build(self,n):
        self.serial+=1;self.bundle=self.root/f'bundle-{self.serial}';self.bundle.mkdir()
        self.row=next(r for r in self.original['rows'] if r['name'] in self.names and r['players']==n)
        for name,module in w.CODE.items():shutil.copyfile(module.__file__,self.bundle/name)
        shutil.copyfile(w.__file__,self.bundle/w.ENTRY)
        shutil.copyfile(ROOT/'ai/strong/current-auction-grid-source-v1.json',self.bundle/'original-source.json')
        self.control={'version':3,'scope':'fixed_confirmation_bucket_retention',
            'attempt_id':self.row['name'].replace('pg-current-confirm-v1-','pg-current-bucket-v3-',1).replace('_','-'),
            'original_name':self.row['name'],'original_row_sha256':w.base.object_hash(self.row),
            'prior_failed_attempts':[],'reason':'never_submitted','allocation':w.ALLOCATION,'transport':w.TRANSPORT,
            'source_descriptor_sha256':w.base.SOURCE_SHA}
        self.decision={'status':'transport_recovery_recorded_execution_not_admitted',
            'strength_outcomes_used_for_decision':False,'reserved_final_seeds_used':False,
            'source_descriptor_sha256':w.base.SOURCE_SHA,'allocation':w.ALLOCATION,'transport':w.TRANSPORT,
            'rows':[{'name':self.row['name'],**{k:self.control[k] for k in ('original_row_sha256','reason','prior_failed_attempts','attempt_id')}}],
            'test_fixture_only':True}
        self.write(self.bundle/'decision.json',self.decision)
        self.control['decision_sha256']=w.digest(self.bundle/'decision.json')
        self.write(self.bundle/'control.json',self.control);self.seal()
        self.output=self.root/f'output-{self.serial}'

    def inspect(self,execute=False):
        return w.inspect(self.bundle,self.seal(),SOURCE,self.output,execute=execute)

    def test_real_original_rows_validate_all_remaining_player_counts_without_execution(self):
        for n in (2,3,5,6):
            self.build(n);result=self.inspect()
            self.assertEqual(result['row'],self.row)
            self.assertEqual(result['context']['original_row'],self.row)
            self.assertFalse(self.output.exists())
            self.assertIn(self.row['job'],result['command'])

    def test_execute_without_admission_never_starts_evaluator(self):
        with patch.object(w.retention,'supervise') as run:
            with self.assertRaisesRegex(ValueError,'admission required'):
                w.run(self.bundle,self.seal(),SOURCE,self.output,execute=True)
            run.assert_not_called()
        self.assertFalse(self.output.exists())

    def test_default_run_only_validates(self):
        with patch.object(w.retention,'supervise') as run:
            result=w.run(self.bundle,self.seal(),SOURCE,self.output)
            self.assertFalse(result['execute']);self.assertTrue(result['valid']);run.assert_not_called()

    def test_changed_worker_bytes_rejected(self):
        with (self.bundle/w.ENTRY).open('a') as stream:stream.write('\n# modified\n')
        with self.assertRaisesRegex(ValueError,'Worker code differs'):self.inspect()

    def test_changed_resource_controls_rejected(self):
        self.control['allocation']={**w.ALLOCATION,'game_workers':8}
        self.write(self.bundle/'control.json',self.control)
        with self.assertRaisesRegex(ValueError,'settings changed'):self.inspect()

    def test_changed_row_is_rejected(self):
        self.control['original_row_sha256']='0'*64
        self.write(self.bundle/'control.json',self.control)
        with self.assertRaisesRegex(ValueError,'explicitly recorded recovery'):self.inspect()

    def test_missing_prior_failure_cannot_be_declared_recovery(self):
        self.control['reason']='failed_transport_recovery';self.decision['rows'][0]['reason']='failed_transport_recovery'
        self.write(self.bundle/'decision.json',self.decision);self.control['decision_sha256']=w.digest(self.bundle/'decision.json')
        self.write(self.bundle/'control.json',self.control)
        with self.assertRaisesRegex(ValueError,'history missing'):self.inspect()

    def test_changed_original_source_descriptor_is_rejected(self):
        original={**self.original,'revision':'a'*40};self.write(self.bundle/'original-source.json',original)
        with self.assertRaisesRegex(ValueError,'Original evaluator source changed'):self.inspect()

    def test_previous_attempt_directory_cannot_be_reused(self):
        self.output.mkdir()
        with self.assertRaisesRegex(ValueError,'previous attempt'):self.inspect()

    def test_extra_unpinned_bundle_file_is_rejected(self):
        (self.bundle/'surprise.py').write_text('raise RuntimeError()\n')
        with self.assertRaisesRegex(ValueError,'Unexpected bucket worker bundle'):self.inspect()


if __name__=='__main__':unittest.main()
