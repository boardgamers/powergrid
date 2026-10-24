import copy
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest

from strategic_collection import ROOT
from population_policy_verification import verify_decision, verify_evaluation, extract_verified, digest


class VerificationTests(unittest.TestCase):
    def test_all_80_exact_control_games_and_10207_decisions(self):
        total=decisions=0
        for n in range(2,7):
            path=ROOT/f'ai/runs/population-policy-arena-controls-v1/{n}p'
            report=json.loads((path/'evaluation.json').read_text())
            checked=verify_evaluation(path,report['config'])
            total+=checked['games'];decisions+=checked['counts']['decisions']
        self.assertEqual((total,decisions),(80,10207))

    def sample(self):
        row=json.loads((ROOT/'ai/runs/population-policy-trained-probe-v1/partition.json').read_text())
        q=json.loads((ROOT/'ai/runs/trained-hybrid-probe-v2/selected-fixtures.json').read_text())['6p-building']['fixture']['request']
        config={'players':6,'arm':'combined','samples':8,'model_sha256':row['modelSha256'],'sealed':True}
        return row,config,q['player']

    def test_actual_trained_search_receipts(self):
        fixtures=json.loads((ROOT/'ai/runs/trained-hybrid-probe-v2/selected-fixtures.json').read_text())
        for line in (ROOT/'ai/runs/population-policy-trained-probe-v1/results.jsonl').read_text().splitlines():
            case=json.loads(line);q=fixtures[case['fixture']]['fixture']['request']
            for arm,row in case['results'].items():
                verify_decision(row,{'players':len(q['state']['players']),'arm':arm,'samples':8,
                    'model_sha256':row['modelSha256'],'sealed':True},q['player'])

    def test_corrupted_search_receipts_are_rejected(self):
        row,config,seat=self.sample();verify_decision(row,config,seat)
        def change_mean(r):r['search']['meanCredits'][str(r['search']['options'][0])]+=1
        def change_choice(r):r['index']=next(i for i in r['search']['options'] if i!=r['index'])
        def bad_world(r):r['search']['worlds']['0']['roles'][seat]='rush'
        def missing_world(r):del r['search']['worlds']['0']
        def missing_credit(r):r['search']['sampleOutcomes'][str(r['search']['options'][0])][0]=None
        def invalid_credit(r):r['search']['sampleOutcomes'][str(r['search']['options'][0])][0]=float('nan')
        def bad_counts(r):r['search']['evaluations']-=1
        def wrong_phase(r):r['phase']='auction'
        def wrong_model(r):r['modelSha256']='0'*64
        def bad_belief(r):r['search']['worlds']['0']['initialBelief']['kind']='actual_hidden_bids'
        def bad_role_cycle(r):
            other=(seat+1)%6
            r['search']['worlds']['0']['roles'][other],r['search']['worlds']['1']['roles'][other]=r['search']['worlds']['1']['roles'][other],r['search']['worlds']['0']['roles'][other]
        for mutate in [change_mean,change_choice,bad_world,missing_world,missing_credit,invalid_credit,bad_counts,wrong_phase,wrong_model,bad_belief,bad_role_cycle]:
            with self.subTest(mutation=mutate.__name__):
                broken=copy.deepcopy(row);mutate(broken)
                with self.assertRaises((AssertionError,ValueError)):verify_decision(broken,config,seat)

    def test_real_deliberate_cap_is_retained_but_rejected_for_admission(self):
        row=json.loads((ROOT/'ai/runs/population-policy-trained-probe-v1/cap.json').read_text())
        _,config,seat=self.sample();config['samples']=4
        with self.assertRaises(AssertionError):verify_decision(row,config,seat,horizon=1)
        counts=verify_decision(row,config,seat,horizon=1,allow_caps=True)
        self.assertGreater(counts['rollout_caps'],0)

    def test_report_pairing_winner_and_receipt_tampering_rejected(self):
        source=ROOT/'ai/runs/population-policy-arena-controls-v1/2p'
        for mutation in ['pair','winner','receipt','missing']:
            with self.subTest(mutation=mutation),tempfile.TemporaryDirectory() as temp:
                import shutil
                target=Path(temp)/'report';shutil.copytree(source,target)
                report=json.loads((target/'evaluation.json').read_text());config=report['config']
                if mutation=='pair':report['results'][1]=copy.deepcopy(report['results'][0])
                elif mutation=='missing':report['results'].pop()
                elif mutation=='receipt':
                    receipt=target/'decisions-0.jsonl';receipt.write_text(receipt.read_text()+'\n')
                else:
                    row=report['results'][0];row['terminal']['value'].reverse();row['terminal']['win']=row['terminal']['value'][0]
                    (target/'game-0.json').write_text(json.dumps(row))
                (target/'evaluation.json').write_text(json.dumps(report))
                with self.assertRaises((AssertionError,ValueError)):verify_evaluation(target,config)

    def test_archive_hash_and_path_checks(self):
        import hashlib
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp)
            for kind in ['valid','tampered','escape','duplicate']:
                archive=base/(kind+'.tgz');name='../outside' if kind=='escape' else 'result.txt'
                manifest={name:hashlib.sha256(b'valid').hexdigest()}
                with tarfile.open(archive,'w:gz') as bundle:
                    for key,body in [('manifest.json',json.dumps(manifest).encode()),(name,b'bad' if kind=='tampered' else b'valid')]+([(name,b'valid')] if kind=='duplicate' else []):
                        info=tarfile.TarInfo(key);info.size=len(body);bundle.addfile(info,io.BytesIO(body))
                if kind=='valid':self.assertEqual(extract_verified(archive,base/'valid')['files'],2)
                else:
                    with self.assertRaises(AssertionError):extract_verified(archive,base/kind)


if __name__=='__main__':unittest.main()
