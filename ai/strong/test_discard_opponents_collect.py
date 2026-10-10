"""Exercise variable deal counts and reject altered real arena records."""
import copy
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from discard_opponents_screen import collect
from arena_statistics import win_summary

ROOT=Path(__file__).resolve().parents[2]


class ArenaAdmission(unittest.TestCase):
    def test_verified_hf_smoke_is_not_a_full_or_different_model_shard(self):
        spec=importlib.util.spec_from_file_location('saved_opponent_collector',ROOT/'ai/strong/collect-discard-opponents.py')
        verifier=importlib.util.module_from_spec(spec);spec.loader.exec_module(verifier)
        source=ROOT/'ai/runs/discard-opponents-smoke-verified-v1/2p'
        self.assertEqual(sum(x['games'] for x in verifier.verify_local(source,'10102',2,True).values()),32)
        for key,n,smoke in [('10102',2,False),('parent',2,True),('10102',6,True)]:
            with self.assertRaises((AssertionError,ValueError)):verifier.verify_local(source,key,n,smoke)
        with tempfile.TemporaryDirectory() as directory:
            target=Path(directory)/'shard';shutil.copytree(source,target)
            path=target/'search_geo.json';bad=json.loads(path.read_text())
            bad['results'][0]['searchStats']['search_geo']['truncated']=1
            path.write_text(json.dumps(bad))
            with self.assertRaises(AssertionError):verifier.verify_local(target,'10102',2,True)

    def test_real_sixteen_and_eight_deal_reports(self):
        original=json.loads((ROOT/'ai/runs/discard-correction-screen-verified-v1/parent/economic-2p.json').read_text())
        pin=json.loads((ROOT/'ai/strong/discard-correction-screen-models-v1.json').read_text())['parent']
        protocol={'opponents':{'economic':16},'seed_template':'discard-correction-games-v1-{players}p',
            'bootstrap_replicates':100,'bootstrap_seed':3}
        with tempfile.TemporaryDirectory() as directory:
            out=Path(directory);path=out/'economic.json'
            path.write_text(json.dumps(original))
            self.assertEqual(collect(out,protocol,pin,2)['economic']['independent_deals'],16)
            shorter=copy.deepcopy(original);shorter['results']=[r for r in shorter['results'] if r['episode']<64]
            shorter.update(games=64,win_rate=win_summary(shorter['results'])['win_rate'])
            path.write_text(json.dumps(shorter));protocol['opponents']['economic']=8
            self.assertEqual(collect(out,protocol,pin,2)['economic']['independent_deals'],8)
            for fault in ['cap','seed','model','missing']:
                bad=copy.deepcopy(shorter)
                if fault=='cap':bad['results'][0]['truncated']=True
                elif fault=='seed':bad['results'][0]['gameSeed']='unprescribed'
                elif fault=='model':bad['model_sha256']='wrong'
                else:bad['results'].pop()
                path.write_text(json.dumps(bad))
                with self.assertRaises((AssertionError,ValueError)):collect(out,protocol,pin,2)


if __name__=='__main__':unittest.main()
