"""Offline preflight guards. Synthetic rows are not real-service evidence."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, Mock
from types import SimpleNamespace

import torch
import preflight_expert_replicas_v1 as p
from expert_replicas_v1 import Replica
from expert_ppo import DEFAULT_ARTIFACT


class PreflightTests(unittest.TestCase):
    def test_exact_rejects_structural_numeric_and_tensor_changes(self):
        p.exact({'state': torch.tensor([1.,2.]), 'rng': (1, [3])},
                {'state': torch.tensor([1.,2.]), 'rng': (1, [3])})
        for left,right in ((1,True),(1,1.),([1],(1,)),({'a':1},{}),
                           (torch.tensor([1.]),torch.tensor([1.000001])),
                           (torch.tensor([1]),torch.tensor([1.]))):
            with self.subTest(left=left):
                with self.assertRaises(ValueError):p.exact(left,right)

    def test_full_smoke_schedule_both_namespaces(self):
        roots=[]
        for i in (1,2):
            files=p.game_files(Replica(i));tasks=[s for rows in files.values() for s in rows]
            self.assertEqual(sum(map(len,files.values())),66)
            self.assertEqual(set(files),{'warmup.json','train-1.json','train-2.json',
                'selection-0.json','selection-teacher.json','selection-warmup.json','selection-1.json','selection-2.json',
                'confirmation-selected.json','confirmation-teacher.json'})
            self.assertTrue(all(s['smoke'] is True and ':smoke:' in s['seed'] for s in tasks))
            self.assertEqual({s['players'] for s in tasks},{2})
            self.assertEqual({(s['variant'],s['fastBid']) for s in tasks},{('original',False)})
            self.assertEqual({s['map'] for s in tasks},{'Germany','USA','France','UK & Ireland'})
            roots.append({s['seed'] for s in tasks})
        self.assertFalse(roots[0]&roots[1])

    def test_existing_and_outside_outputs_rejected_before_models(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(p,'checkpoint_metadata',side_effect=AssertionError('download')):
            with self.assertRaises(ValueError):p.preflight(tmp)
            with self.assertRaises(ValueError):p.preflight(Path(tmp)/'multimap-outside')
            with self.assertRaises(ValueError):p.preflight(DEFAULT_ARTIFACT)

    def test_all_model_metadata_checked_before_download(self):
        pins=[Replica(1).protocol['warmStart'],*Replica(1).protocol['opponentPool']]
        api=Mock();api.model_info.return_value.private=True;calls=[]
        def meta(url,**kwargs):
            index=len(calls);calls.append(url)
            return SimpleNamespace(commit_hash=pins[index]['revision'],size=16*1024**2+1 if index==3 else 1)
        with patch('huggingface_hub.HfApi',return_value=api),patch('huggingface_hub.get_hf_file_metadata',side_effect=meta), \
             patch('huggingface_hub.get_token',return_value='unit-only'),patch('huggingface_hub.hf_hub_download') as download:
            with self.assertRaisesRegex(ValueError,'size/revision'):p.checkpoint_metadata()
            self.assertEqual(len(calls),4);download.assert_not_called()

    def test_private_metadata_revision_and_actual_hash_checks(self):
        pins=[Replica(1).protocol['warmStart'],*Replica(1).protocol['opponentPool']]
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'warm.pt';path.write_bytes(b'x')
            api=Mock();api.model_info.return_value.private=True
            metadata=[SimpleNamespace(commit_hash=pin['revision'],size=1) for pin in pins]
            with patch('huggingface_hub.HfApi',return_value=api), \
                 patch('huggingface_hub.get_hf_file_metadata',side_effect=metadata), \
                 patch('huggingface_hub.get_token',return_value='unit-only'), \
                 patch('huggingface_hub.hf_hub_download',return_value=str(path)) as download:
                with self.assertRaisesRegex(ValueError,'Warm-start bytes'):p.checkpoint_metadata()
                self.assertEqual(download.call_count,1)
            api.model_info.return_value.private=False
            with patch('huggingface_hub.HfApi',return_value=api),patch('huggingface_hub.get_hf_file_metadata') as meta, \
                 patch('huggingface_hub.hf_hub_download') as download:
                with self.assertRaisesRegex(ValueError,'Private'):p.checkpoint_metadata()
                meta.assert_not_called();download.assert_not_called()

    def test_only_canonical_smoke_outcomes_and_no_eval_labels(self):
        spec=Replica(1).plans('selection',smoke=True,protocol=Replica(1).protocol)[0]
        record=dict(spec=copy.deepcopy(spec),terminal=True,allSeatCredit=[1,0],credit=1,
                    expertCounts=dict(Auction=0,Building=0,Resources=0,Bureaucracy=0),expertRequests=0,
                    **dict.fromkeys(p.TIMINGS,0.))
        with patch('expert_rollout._terminal',return_value=1):
            p.validate_outcome(record,spec)
            changed=copy.deepcopy(record);changed['spec']['seed']='bad'
            with self.assertRaises(ValueError):p.validate_outcome(changed,spec)
            changed=copy.deepcopy(record);changed['expertCounts']['Auction']=1;changed['expertRequests']=1
            with self.assertRaisesRegex(ValueError,'Evaluation expert'):p.validate_outcome(changed,spec)
            changed=copy.deepcopy(record);changed['seconds']=float('inf')
            with self.assertRaisesRegex(ValueError,'timings'):p.validate_outcome(changed,spec)

    def test_compare_requires_complete_same_file_sets(self):
        with tempfile.TemporaryDirectory() as tmp:
            one=Path(tmp)/'a';two=Path(tmp)/'b';one.mkdir();two.mkdir();(one/'extra.tmp').write_text('{}')
            with self.assertRaisesRegex(ValueError,'file coverage'):p.compare_execution(one,two,Replica(1))


if __name__=='__main__':unittest.main()
