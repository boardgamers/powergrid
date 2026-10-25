"""Outcome-independent selection, public-state boundaries and immutable focal actions."""
from copy import deepcopy
import json
import random
import subprocess
import unittest

from strategic_collection import ROOT, read
from hybrid_search import Model
from population_hybrid_policy import PopulationPolicy
from surrogate_continuation_roots_v1 import PROTOCOL, PHASES, contract, candidate, RootSampler, object_hash

RUNTIME = ROOT/'ai/runs/population-auction-regression-replays-v1/runtime'
MODEL = ROOT/'ai/runs/policy-iteration-trained-8840u-prepared-v2/local-package-frozen-1/policy.onnx'


class RootTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = Model(MODEL, threads=1)
        cls.policy = PopulationPolicy(cls.model, RUNTIME/'ai/strong/population-hybrid-policy.cjs', arm='filter')
        cells = {}
        # Canonical fixtures contain complete engine states. Match the arena's
        # public boundary explicitly; the collector correctly rejects raw ones.
        script = """
        const fs=require('node:fs'), path=require('node:path'), runtime=process.argv[1];
        const beliefs=require(path.join(runtime,'ai/strong/sealed-policy-beliefs.cjs'));
        const {preparePolicy}=require(path.join(runtime,'ai/strong/population-hybrid-policy.cjs'));
        const cells=new Map();
        for(const line of fs.readFileSync(path.join(runtime,'ai/strong/fixtures/multiplayer-serving-v1.jsonl'),'utf8').trim().split('\\n')) {
            const f=JSON.parse(line), q=f.request, g=q.state, names=f.legal.map(m=>m.name);
            const phase=names.includes('ChoosePowerPlant')?'plant':names.includes('Bid')?'bid':names.includes('Build')?'building':null;
            const key=[g.players.length,g.options.variant,!!g.options.fastBid,phase].join('/');
            if(!phase || f.legal.length<2 || cells.has(key))continue;
            const request={state:beliefs.publicState(g,q.player),player:q.player};
            const root=preparePolicy({...request,featureRevision:'4.3-strategic-correction'});
            if(root.options.filter(i=>!root.lossFilter.forbidden.includes(i)).length<2)continue;
            cells.set(key,{request,legal:root.moves});
        }
        console.log(JSON.stringify([...cells.values()]));
        """
        fixtures = json.loads(subprocess.check_output(['node', '-e', script, str(RUNTIME)]))
        for fixture in fixtures:
            moves = fixture['legal']; state = fixture['request']['state']
            names = {m['name'] for m in moves}
            phase = 'plant' if 'ChoosePowerPlant' in names else 'bid' if 'Bid' in names else 'building' if 'Build' in names else None
            if not phase or len(moves) < 2: continue
            rule = int(state['options']['variant'] == 'recharged') + (0 if state['options'].get('fastBid') else 2)
            key = (len(state['players']), rule, phase)
            if key in cells: continue
            request = fixture['request']; receipt = cls.policy.choose(request)
            prepared = cls.policy.node.call({**request, 'op': 'prepare', 'featureRevision': '4.3-strategic-correction'})
            q = contract(len(state['players']), 0, request['player'], rule, 'preflight')
            row = candidate(request, prepared, receipt, q, 0)
            if row: cells[key] = (request, prepared, receipt, q, row)
        assert len(cells) == 60
        cls.cells = cells

    @classmethod
    def tearDownClass(cls):
        cls.policy.close()

    def test_contract_covers_all_seats_rules_and_whole_deals(self):
        p = read(PROTOCOL); games = [contract(n, deal, seat, rule, 'root') for n in p['player_counts']
            for deal in range(p['deals_per_count']) for seat in range(n) for rule in range(4)]
        self.assertEqual(len(games), p['root_collection_games'])
        self.assertEqual(len({(q['players'], q['episode']) for q in games}), 160)
        self.assertEqual(len({(q['players'], q['deal']) for q in games}), 10)
        for q in games:
            self.assertEqual(q['episode']//(4*q['players']), q['deal'])
            self.assertEqual(q['episode']//4 % q['players'], q['seat'])
            self.assertEqual(q['episode'] % 4, q['rule'])
            self.assertNotIn('opponent-surrogate-collection', q['seed'])
        for args in [(6, 2, 0, 0, 'root'), (1, 0, 0, 0, 'root'), (2, 0, 2, 0, 'root'), (2, 1, 0, 0, 'runtime')]:
            with self.assertRaises(AssertionError): contract(*args)

    def test_real_public_roots_all_60_contexts(self):
        for request, prepared, receipt, q, row in self.cells.values():
            original = object_hash([request, prepared, receipt, q])
            self.assertEqual(candidate(request, prepared, receipt, q, 0), row)
            self.assertEqual(object_hash([request, prepared, receipt, q]), original)
            self.assertEqual(row['options'][0], receipt['index'])
            alternatives = [i for i in prepared['options'] if i != receipt['index'] and i not in prepared['lossFilter']['forbidden']]
            self.assertEqual(row['options'][1], max(alternatives, key=lambda i: (prepared['observation']['actions'][i][74], -i)))
            self.assertEqual(row['public_root_sha256'], object_hash(request))
        print(json.dumps({'public_contexts': len(self.cells), 'focal_model': self.model.sha256, 'gradient_updates': 0}))

    def test_sampling_is_order_independent_and_keeps_missing_phases(self):
        base = next(iter(self.cells.values()))
        values = [candidate(*base[:4], i) for i in range(100)]
        first = RootSampler(); second = RootSampler()
        for value in values: first.add(value)
        shuffled = list(values); random.Random(18101).shuffle(shuffled)
        for value in shuffled: second.add(value)
        self.assertEqual(first.result(), second.result())
        self.assertEqual(next(iter(first.roots.values()))['decision'], min(values, key=lambda row: row['rank'])['decision'])
        self.assertEqual(len(first.result()['missing_phases']), 2)
        first.add(None)
        with self.assertRaises(AssertionError): first.add(values[0])
        empty = RootSampler(); self.assertEqual(empty.result()['missing_phases'], list(PHASES))

    def test_private_inputs_and_changed_focal_receipts_are_rejected(self):
        request, prepared, receipt, q, _ = self.cells[(6, 1, 'bid')]
        for field, value in [('seed', 'private'), ('powerPlantsDeck', [99]), ('hiddenLog', [{'private': True}]),
                             ('automation', {}), ('currentBid', 42)]:
            changed = deepcopy(request); changed['state'][field] = value
            with self.assertRaises(AssertionError): candidate(changed, prepared, receipt, q, 0)
        changed = deepcopy(receipt); changed['modelSha256'] = '0'*64
        with self.assertRaises(AssertionError): candidate(request, prepared, changed, q, 0)
        changed = deepcopy(receipt); changed['index'] = (receipt['index']+1) % len(prepared['moves'])
        with self.assertRaises(AssertionError): candidate(request, prepared, changed, q, 0)

    def test_sampling_rank_does_not_use_features_scores_or_outcomes(self):
        request, prepared, receipt, q, base = self.cells[(4, 1, 'bid')]
        altered = deepcopy(prepared)
        for i, action in enumerate(altered['observation']['actions']): action[74] = float(i)
        modified = candidate(request, altered, receipt, q, 0)
        self.assertEqual(modified['rank'], base['rank'])
        modified = deepcopy(base)
        modified['terminal_outcome'] = 'loss'; modified['teacher_scores'] = [1000]
        sampler = RootSampler(); sampler.add(base)
        other = RootSampler(); other.add(modified)
        self.assertEqual(sampler.result()['eligible'], other.result()['eligible'])
        self.assertEqual(sampler.result()['roots']['bid']['rank'], other.result()['roots']['bid']['rank'])


if __name__ == '__main__': unittest.main()
