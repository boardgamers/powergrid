"""Isolated stable-seed resource search; original baseline/continuation algorithm.

Only seed selection and its explicit receipts differ from the frozen chooser.
The inherited baseline uses the separately pinned corrected public worker.
"""
from collections import Counter
import time

import numpy as np
from hybrid_search import EnginePool, predict_batch, public_seed
from resource_turn_search_v1 import ResourceTurnSearch


class AnchoredResourceTurnSearch(ResourceTurnSearch):
    def choose(self,request):
        start = time.perf_counter()
        q,baseline_trace = self.baseline(request)
        root = self.node.call({**q,'op':'prepare'})
        bundles,baseline = root['bundles'],root['baseline']
        anchor = self.node.call({**q, 'op': 'anchor-prepare'})
        seed = public_seed(anchor)
        sampling = {'mode': 'turn-start-public-history-v2', 'currentSeed': public_seed(root),
                    'anchor': anchor['resourceTurnAnchor']}
        if sampling['anchor']['purchasesRewound'] == 0:
            assert seed == sampling['currentSeed']
        count = self.samples*len(bundles)
        size = min(self.workers,count)
        if self.pool is None or self.pool_size != size:
            if self.pool is not None:self.pool.close()
            self.pool = EnginePool(size,script=self.worker);self.pool_size = size
        response = self.pool.call({**q,'op':'reset','mode':'resource_population','endgameFilter':True,
            'samples':self.samples,'maxSteps':self.max_steps,'seed':seed,'n':count})
        ended = list(response['ended']);decisions = 0
        while any(o is not None for o in response['observations']):
            live = [i for i,o in enumerate(response['observations']) if o is not None]
            rows = [response['observations'][i] for i in live]
            if any(row['roles'][row['actor']] != 'neural' for row in rows):
                raise ValueError('Unexpected neural actor')
            actions = [None]*count
            for i,choice in zip(live,predict_batch(self.model,rows)):actions[i] = choice
            decisions += len(rows)
            response = self.pool.call({'op':'step','actions':actions});ended.extend(response['ended'])
        if len(ended) != count or {r['env'] for r in ended} != set(range(count)):
            raise ValueError('Missing or duplicate resource continuations')
        outcomes = {b['id']:[None]*self.samples for b in bundles}
        worlds = {};caps = 0
        for row in ended:
            sample,index = divmod(row['env'],len(bundles));bundle = bundles[index]
            if (row['sample']!=sample or row['actionIndex']!=index or row['roles'][q['player']]!='neural'
                    or row['searchStats']!={'decisions':0,'evaluations':0,'truncated':0}
                    or sum(row['policyDecisions'].values())!=row['steps']
                    or not 0 <= row['steps'] <= self.max_steps
                    or (row['value'] is None)!=row['truncated']
                    or (row['value'] is not None and not 0 <= row['value'] <= 1)
                    or row['resourceTurn']['actions']!=bundle['actions']
                    or row['resourceTurn']['counts']!=bundle['counts']
                    or row['resourceTurn']['cost']!=bundle['cost']
                    or row['resourceTurn']['bundleId']!=bundle['id']):
                raise ValueError('Invalid resource continuation receipt')
            world = {'roles':row['roles'],'initialBelief':row['initialBelief']}
            if sample in worlds and worlds[sample]!=world:raise ValueError('Unpaired candidate worlds')
            worlds[sample]=world;outcomes[bundle['id']][sample]=row['value'];caps+=int(row['truncated'])
        for seat in range(len(q['state']['players'])):
            if seat!=q['player'] and Counter(w['roles'][seat] for w in worlds.values())!={
                    role:self.samples//4 for role in ['neural','economic','legacy','rush']}:
                raise ValueError('Unbalanced opponent roles')
        selected = baseline
        means = None
        if not caps:
            means = {b['id']:float(np.mean(outcomes[b['id']])) for b in bundles}
            selected = max(range(len(bundles)),key=lambda i:(means[bundles[i]['id']],i==baseline,-i))
        return {'revision':'resource-turn-search-anchored-v2','modelSha256':self.model.sha256,
            'featureRevision':self.revision,'bundles':bundles,'baseline':baseline,
            'baselineDecisions':baseline_trace,'selected':selected,'actions':bundles[selected]['actions'],
            'firstMove':bundles[selected]['actions'][0],
            'executionContract':'Execute the complete returned resource turn. Replanning each purchase is a different policy.',
            'search':{'sampling':sampling,'samples':self.samples,'evaluations':count,'seed':seed,'maxSteps':self.max_steps,
                'neuralDecisions':decisions,'sampleOutcomes':outcomes,'worlds':worlds,
                'truncated':caps,'usable':caps==0,'meanCredits':means,
                'fallbackReason':'incomplete-rollouts' if caps else None,
                'valueStatus':'simulated-terminal-credits-not-calibrated-win-probabilities'},
            'receipts':sorted(ended,key=lambda r:r['env']),
            'elapsedMs':1000*(time.perf_counter()-start),'qualification_eligible':False}
