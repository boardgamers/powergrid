"""Research-only whole resource-turn valuation; caller must execute the returned plan."""
from collections import Counter
from pathlib import Path
import time

import numpy as np
from hybrid_search import Model, Node, EnginePool, model_revision, predict_batch, public_seed


class ResourceTurnSearch:
    def __init__(self, model, worker, *, samples=8, workers=1, max_steps=2400):
        if type(samples) is not int or samples not in range(4,65,4):
            raise ValueError('Unbalanced population budget')
        if type(workers) is not int or not 1 <= workers <= 32:
            raise ValueError('Invalid worker count')
        if type(max_steps) is not int or not 1 <= max_steps <= 2400:
            raise ValueError('Invalid continuation horizon')
        self.revision = model_revision(model)
        if self.revision != '4.3-strategic-correction':
            raise ValueError('Unsupported resource model')
        self.worker = str(Path(worker).resolve())
        if not Path(self.worker).is_file():
            raise ValueError('Missing resource worker')
        self.model,self.samples,self.workers,self.max_steps = model,samples,workers,max_steps
        self.node,self.pool,self.pool_size = Node(self.worker),None,0

    def close(self):
        if self.pool is not None:
            self.pool.close();self.pool = None
        if self.node is not None:
            self.node.close();self.node = None

    def baseline(self,request):
        q = {'state':request['state'],'player':request['player'],'featureRevision':self.revision}
        response = self.node.call({**q,'op':'baseline-reset'})
        decisions = []
        while not response['done']:
            index = predict_batch(self.model,[response['observation']])[0]
            decisions.append({'index':index,'move':response['moves'][index]})
            response = self.node.call({'op':'baseline-step','index':index})
        assert response['actions'] == [row['move'] for row in decisions]
        return {**q,'baselineActions':response['actions']},decisions

    def choose(self,request):
        start = time.perf_counter()
        q,baseline_trace = self.baseline(request)
        root = self.node.call({**q,'op':'prepare'})
        bundles,baseline = root['bundles'],root['baseline']
        seed = public_seed(root)
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
        return {'revision':'resource-turn-search-v1','modelSha256':self.model.sha256,
            'featureRevision':self.revision,'bundles':bundles,'baseline':baseline,
            'baselineDecisions':baseline_trace,'selected':selected,'actions':bundles[selected]['actions'],
            'firstMove':bundles[selected]['actions'][0],
            'executionContract':'Execute the complete returned resource turn. Replanning each purchase is a different policy.',
            'search':{'samples':self.samples,'evaluations':count,'seed':seed,'maxSteps':self.max_steps,
                'neuralDecisions':decisions,'sampleOutcomes':outcomes,'worlds':worlds,
                'truncated':caps,'usable':caps==0,'meanCredits':means,
                'fallbackReason':'incomplete-rollouts' if caps else None,
                'valueStatus':'simulated-terminal-credits-not-calibrated-win-probabilities'},
            'receipts':sorted(ended,key=lambda r:r['env']),
            'elapsedMs':1000*(time.perf_counter()-start),'qualification_eligible':False}
