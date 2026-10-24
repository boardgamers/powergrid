"""Research-only model/filter/population-search arms; no job submission."""
from pathlib import Path
import time

import numpy as np
from hybrid_search import Model, Node, EnginePool, model_revision, predict_batch, public_seed

ARMS = ('model', 'filter', 'auction', 'building', 'combined')


class PopulationPolicy:
    def __init__(self, model, worker, *, arm, samples=8, workers=1, max_steps=2400):
        if arm not in ARMS or type(samples) is not int or samples not in range(4, 65, 4):
            raise ValueError('Invalid policy arm or unbalanced population budget')
        if type(workers) is not int or not 1 <= workers <= 32:
            raise ValueError('Invalid worker count')
        if type(max_steps) is not int or not 1 <= max_steps <= 2400:
            raise ValueError('Invalid continuation horizon')
        worker = Path(worker).resolve()
        if not worker.is_file():
            raise ValueError('Missing pinned policy worker')
        self.model, self.arm, self.samples = model, arm, samples
        self.workers, self.max_steps, self.worker = workers, max_steps, str(worker)
        self.revision = model_revision(model)
        self.node, self.pool, self.pool_size = Node(str(worker)), None, 0

    def close(self):
        if self.pool is not None:
            self.pool.close()
            self.pool = None
        if self.node is not None:
            self.node.close()
            self.node = None

    def choose(self, request):
        start = time.perf_counter()
        q = {'state': request['state'], 'player': request['player'], 'featureRevision': self.revision}
        root = self.node.call({**q, 'op': 'prepare'})
        proposal = predict_batch(self.model, [root['observation']])[0]
        moves, proof = root['moves'], root['lossFilter']
        enabled = self.arm != 'model'
        filtered = enabled and proposal in proof['forbidden']
        baseline = proof['passIndex'] if filtered else proposal
        names = {move['name'] for move in moves}
        phase = 'auction' if names & {'ChoosePowerPlant', 'Bid'} else 'building' if 'Build' in names else None
        result = {'index': baseline, 'move': moves[baseline], 'modelProposal': proposal,
                  'modelSha256': self.model.sha256, 'featureRevision': self.revision,
                  'arm': self.arm, 'phase': phase, 'filterApplied': filtered,
                  'filterCertificate': proof['certificate'] if enabled else None,
                  'search': None, 'qualification_eligible': False}
        def finish():
            return {**result, 'elapsedMs': 1000 * (time.perf_counter() - start)}
        if len(moves) < 2 or phase is None or self.arm in ('model', 'filter'):
            return finish()
        if self.arm != 'combined' and self.arm != phase:
            return finish()
        options = list(dict.fromkeys([*root['options'], baseline]))
        options = [index for index in options if index not in proof['forbidden']]
        assert baseline in options
        if len(options) < 2:
            return finish()
        seed = public_seed(root)
        prior_choices = predict_batch(self.model, [p['encoded'] for p in root['prior']])
        neural = {str(p['actor']): p['encoded']['moves'][i] for p, i in zip(root['prior'], prior_choices)}
        count = self.samples * len(options)
        size = min(self.workers, count)
        if self.pool is None or self.pool_size != size:
            if self.pool is not None:
                self.pool.close()
            self.pool = EnginePool(size, script=self.worker)
            self.pool_size = size
        response = self.pool.call({**q, 'op': 'reset', 'mode': 'neural_population', 'belief': 'policy',
            'endgameFilter': True, 'neuralBeliefs': neural, 'samples': self.samples, 'maxSteps': self.max_steps,
            'seed': seed, 'n': count, 'options': options})
        ended = list(response['ended'])
        decisions = 0
        while any(o is not None for o in response['observations']):
            live = [i for i, o in enumerate(response['observations']) if o is not None]
            rows = [response['observations'][i] for i in live]
            if any(r['roles'][r['actor']] != 'neural' for r in rows):
                raise ValueError('Unexpected neural actor')
            actions = [None] * count
            for i, choice in zip(live, predict_batch(self.model, rows)):
                actions[i] = choice
            decisions += len(rows)
            response = self.pool.call({'op': 'step', 'actions': actions})
            ended.extend(response['ended'])
        if len(ended) != count or {r['env'] for r in ended} != set(range(count)):
            raise ValueError('Incomplete or duplicate continuation results')
        outcomes = {str(index): [None] * self.samples for index in options}
        worlds, truncated, overrides = {}, 0, 0
        for row in ended:
            sample, choice = divmod(row['env'], len(options))
            if (row['sample'] != sample or row['actionIndex'] != options[choice]
                    or row['roles'][q['player']] != 'neural'
                    or row['searchStats'] != {'decisions': 0, 'evaluations': 0, 'truncated': 0}
                    or sum(row['policyDecisions'].values()) != row['steps']
                    or not 0 <= row['steps'] <= self.max_steps
                    or (row['value'] is None) != row['truncated']
                    or (row['value'] is not None and not 0 <= row['value'] <= 1)):
                raise ValueError('Invalid terminal continuation')
            world = {'roles': row['roles'], 'initialBelief': row['initialBelief']}
            if sample in worlds and worlds[sample] != world:
                raise ValueError('Candidate actions used different worlds')
            worlds[sample] = world
            outcomes[str(options[choice])][sample] = row['value']
            truncated += int(row['truncated'])
            overrides += row['filterOverrides']
        from collections import Counter
        for seat in range(len(q['state']['players'])):
            if seat != q['player']:
                if Counter(w['roles'][seat] for w in worlds.values()) != {
                        role: self.samples // 4 for role in ['neural', 'economic', 'legacy', 'rush']}:
                    raise ValueError('Unbalanced opponent population')
        detail = {'options': options, 'samples': self.samples, 'mode': 'neural_population',
                  'seed': seed, 'evaluations': count, 'truncated': truncated, 'neuralDecisions': decisions,
                  'maxSteps': self.max_steps, 'sampleOutcomes': outcomes, 'worlds': worlds,
                  'continuationFilterOverrides': overrides, 'usable': truncated == 0,
                  'valueStatus': 'simulated-terminal-credits-not-calibrated-win-probabilities'}
        if truncated:
            detail['fallbackReason'] = 'incomplete-rollouts'
        else:
            means = {index: float(np.mean(outcomes[str(index)])) for index in options}
            selected = max(options, key=lambda index: (means[index], index == baseline, -options.index(index)))
            result.update(index=selected, move=moves[selected])
            detail['meanCredits'] = {str(index): value for index, value in means.items()}
        result['search'] = detail
        return finish()
