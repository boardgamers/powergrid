"""Fixed-action diagnostic continuations with separate focal and opponent inference."""
from pathlib import Path
import time

from hybrid_search import Node, EnginePool, predict_batch, public_seed, model_revision
from strategic_collection import ROOT, digest

WORKER = ROOT/'ai/strong/surrogate-opponent-continuations-v1.cjs'
MODES = ('neural_population', 'reference_opponent_v1', 'surrogate_opponent_v1')


class SurrogateContinuationProbe:
    def __init__(self, focal, surrogate, *, workers=1):
        assert model_revision(focal) == '4.3-strategic-correction'
        assert type(workers) is int and 1 <= workers <= 32
        self.focal, self.surrogate, self.workers = focal, surrogate, workers
        self.node = Node(str(WORKER)); self.pool = None; self.size = 0

    def close(self):
        if self.pool is not None: self.pool.close(); self.pool = None
        if self.node is not None: self.node.close(); self.node = None

    def run(self, request, options, *, mode, samples=4, begin=0, count=None, max_steps=2400):
        assert mode in MODES and type(samples) is int and 1 <= samples <= 64
        count = samples - begin if count is None else count
        assert type(begin) is int and type(count) is int and 0 <= begin < samples and 0 < count <= samples - begin
        assert type(max_steps) is int and 1 <= max_steps <= 2400
        if mode == 'neural_population': assert samples % 4 == 0
        q = {'state': request['state'], 'player': request['player'], 'featureRevision': '4.3-strategic-correction'}
        root = self.node.call({**q, 'op': 'prepare'})
        assert options and len(set(options)) == len(options)
        assert all(type(i) is int and 0 <= i < len(root['moves']) and i not in root['lossFilter']['forbidden'] for i in options)
        arguments = {'neuralBeliefs': {}}
        if mode == 'neural_population':
            choices = predict_batch(self.focal, [p['encoded'] for p in root['prior']])
            arguments['neuralBeliefs'] = {str(p['actor']): p['encoded']['moves'][i] for p, i in zip(root['prior'], choices)}
        elif mode == 'reference_opponent_v1': arguments['referenceOpponent'] = 'search_geo'
        else:
            assert self.surrogate is not None
            choices = self.surrogate.predict_batch([p['encoded'] for p in root['prior']])
            bids = {str(p['actor']): p['encoded']['moves'][i] for p, i in zip(root['prior'], choices)}
            arguments['surrogateBeliefs'] = [bids for _ in range(samples)]
        n = count * len(options); size = min(n, self.workers)
        if self.pool is None or self.size != size:
            if self.pool is not None: self.pool.close()
            self.pool = EnginePool(size, script=str(WORKER)); self.size = size
        start = time.perf_counter(); decisions = {'neural': 0, 'surrogate': 0}; ended = []
        response = self.pool.call({**q, **arguments, 'op': 'reset', 'mode': mode, 'belief': 'policy',
            'endgameFilter': True, 'samples': samples, 'seed': public_seed(root), 'maxSteps': max_steps,
            'options': options, 'n': n, 'offset': begin * len(options)})
        while True:
            ended.extend(response['ended']); live = [i for i, row in enumerate(response['observations']) if row is not None]
            if not live: break
            actions = [None] * n
            assert all(response['observations'][i]['roles'][response['observations'][i]['actor']] in decisions for i in live)
            for role in decisions:
                ids = [i for i in live if response['observations'][i]['roles'][response['observations'][i]['actor']] == role]
                observations = [response['observations'][i] for i in ids]
                if not ids: continue
                if role == 'neural': choices = predict_batch(self.focal, observations)
                else:
                    assert mode == 'surrogate_opponent_v1' and self.surrogate is not None
                    choices = self.surrogate.predict_batch(observations)
                assert len(choices) == len(ids)
                for i, choice in zip(ids, choices): actions[i] = choice
                decisions[role] += len(ids)
            response = self.pool.call({'op': 'step', 'actions': actions})
        ended.sort(key=lambda row: row['env'])
        assert len(ended) == n and [row['env'] for row in ended] == list(range(n))
        worlds = {}
        for i, row in enumerate(ended):
            assert row['sample'] == begin + i // len(options) and row['actionIndex'] == options[i % len(options)]
            assert row['truncated'] is (row['diagnostic']['terminal'] is None)
            assert sum(row['policyDecisions'].values()) == row['steps']
            world = {k: row[k] for k in ('roles', 'initialBelief')}
            world['sampledWorldSha256'] = row['diagnostic']['sampledWorldSha256']
            assert worlds.setdefault(row['sample'], world) == world
            if mode != 'neural_population':
                role = 'surrogate' if mode == 'surrogate_opponent_v1' else 'search_geo'
                assert row['roles'] == ['neural' if seat == q['player'] else role for seat in range(len(q['state']['players']))]
            if mode != 'reference_opponent_v1':
                assert row['searchStats'] == row['diagnostic']['priorSearchStats'] == {'decisions': 0, 'evaluations': 0, 'truncated': 0}
            if row['truncated']: assert row['value'] is None
            else:
                scores = [(p['powered'], p['money'], p['cities']) for p in row['diagnostic']['terminal']]
                assert len(scores) == len(q['state']['players'])
                assert all(all(type(v) is int and v >= 0 for v in score) for score in scores)
                best = max(scores); expected = 1 / scores.count(best) if scores[q['player']] == best else 0
                assert row['value'] == expected
        assert sum(r['policyDecisions']['neural'] for r in ended) == decisions['neural']
        assert sum(r['policyDecisions'].get('surrogate', 0) for r in ended) == decisions['surrogate']
        outer_caps = sum(r['truncated'] for r in ended)
        nested_caps = sum(r['searchStats']['truncated'] + r['diagnostic']['priorSearchStats']['truncated'] for r in ended)
        return {'mode': mode, 'options': options, 'samples': samples, 'begin': begin, 'count': count,
            'rows': ended, 'inference_decisions': decisions, 'seconds': time.perf_counter()-start,
            'caps': outer_caps + nested_caps, 'outer_caps': outer_caps, 'nested_caps': nested_caps,
            'usable': outer_caps + nested_caps == 0, 'worker_sha256': digest(WORKER),
            'qualification_eligible': False,
            'scope': 'Fixed-action simulated continuations. No action selection, calibrated win probability or playing-strength qualification.'}
