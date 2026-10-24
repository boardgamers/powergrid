"""Experimental neural/economic terminal-rollout search; never launches HF jobs."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'ai'))
from infer import Model, Node
from pool import EnginePool
from feature_contract import model_revision

FORMATS = {'4.2-discard-correction': (1216, 100), '4.3-strategic-correction': (1217, 101)}
WORKER = 'strong/hybrid-continuations.cjs'
MODES = ('neural', 'neural_economic')
SCOPES = ('auction', 'building', 'combined')


def predict_batch(model, rows, batch_size=64):
    revision = model_revision(model)
    if revision not in FORMATS or not isinstance(batch_size, int) or batch_size < 1:
        raise ValueError('Unsupported model format or batch size')
    meta = model.session.get_modelmeta().custom_metadata_map
    if meta.get('powergrid.inference_precision') != 'float64':
        raise ValueError('Expected the verified float64 inference export')
    state_dim, action_dim = FORMATS[revision]
    chosen = []
    for begin in range(0, len(rows), batch_size):
        part = rows[begin:begin + batch_size]
        counts = [len(r['actions']) for r in part]
        if not all(counts):
            raise ValueError('Empty legal menu')
        actions = np.zeros((len(part), max(counts), action_dim), dtype=np.float32)
        mask = np.zeros(actions.shape[:2], dtype=bool)
        for i, row in enumerate(part):
            if (row['featureRevision'] != revision or len(row['state']) != state_dim
                    or any(len(a) != action_dim for a in row['actions'])):
                raise ValueError('Model and observation formats differ')
            actions[i, :counts[i]] = row['actions']
            mask[i, :counts[i]] = True
        states = np.asarray([r['state'] for r in part], dtype=np.float32)
        if not np.isfinite(states).all() or not np.isfinite(actions).all():
            raise ValueError('Non-finite model input')
        scores, _ = model.session.run(None, {'state': states, 'actions': actions, 'mask': mask})
        if scores.shape != mask.shape or not np.isfinite(scores[mask]).all():
            raise ValueError('Invalid legal-action scores')
        selected = scores.argmax(-1).tolist()
        if any(not 0 <= a < n for a, n in zip(selected, counts)):
            raise ValueError('Model selected padded action')
        chosen.extend(selected)
    return chosen


def public_seed(prepared):
    # Use shared public feature prefixes, not request IDs, game RNG or hidden fields.
    # Both supported formats therefore get identical worlds for the same position.
    def common(row):
        return {'state': row['state'][:1216], 'actions': [a[:100] for a in row['actions']],
                'playerOrder': row['playerOrder']}
    visible = {'observation': common(prepared['observation']), 'moves': prepared['moves'],
               'prior': [{'actor': p['actor'], 'observation': common(p['encoded']),
                          'moves': p['encoded']['moves']} for p in prepared['prior']]}
    raw = json.dumps(visible, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
    return 'hybrid-public-v1-' + hashlib.sha256(raw).hexdigest()


class HybridSearch:
    def __init__(self, model, *, samples=8, workers=4, max_steps=2400, scope='combined', modes=MODES):
        if model_revision(model) not in FORMATS:
            raise ValueError('Unsupported hybrid model')
        for value, maximum in [(samples, 64), (workers, 32), (max_steps, 2400)]:
            if type(value) is not int or not 1 <= value <= maximum:
                raise ValueError('Invalid hybrid budget')
        if scope not in SCOPES or not modes or len(set(modes)) != len(modes) or any(m not in MODES for m in modes):
            raise ValueError('Invalid hybrid scope or continuation modes')
        self.model, self.samples, self.workers = model, samples, workers
        self.max_steps, self.scope, self.modes = max_steps, scope, tuple(modes)
        self.revision = model_revision(model)
        self.node = Node(WORKER)
        self.pool = None
        self.pool_size = 0

    def close(self):
        if self.pool is not None:
            self.pool.close()
            self.pool = None
        if self.node is not None:
            self.node.close()
            self.node = None

    def __enter__(self):
        return self

    def __exit__(self, *unused):
        self.close()

    def _pool(self, count):
        size = min(self.workers, count)
        if self.pool_size != size or self.pool is None:
            if self.pool is not None:
                self.pool.close()
            self.pool = EnginePool(size, script=str(ROOT / 'ai' / WORKER))
            self.pool_size = size
        return self.pool

    def choose(self, request):
        started = time.perf_counter()
        q = {'state': request['state'], 'player': request['player'], 'featureRevision': self.revision}
        prepared = self.node.call({**q, 'op': 'prepare'})
        proposal = predict_batch(self.model, [prepared['observation']])[0]
        moves = prepared['moves']
        names = {m['name'] for m in moves}
        phase = 'auction' if names & {'ChoosePowerPlant', 'Bid'} else 'building' if 'Build' in names else None
        result = {'index': proposal, 'move': moves[proposal], 'modelProposal': proposal,
                  'modelSha256': self.model.sha256, 'featureRevision': self.revision,
                  'phase': phase, 'search': None, 'qualification_eligible': False}
        if len(moves) < 2 or phase is None or (self.scope != 'combined' and self.scope != phase):
            return {**result, 'elapsedMs': 1000 * (time.perf_counter() - started)}
        options = list(dict.fromkeys([*prepared['options'], proposal]))
        seed = public_seed(prepared)
        prior_choices = predict_batch(self.model, [p['encoded'] for p in prepared['prior']])
        neural = {str(p['actor']): p['encoded']['moves'][i] for p, i in zip(prepared['prior'], prior_choices)}
        count = self.samples * len(options)
        pool = self._pool(count)
        all_outcomes, truncated, decisions = {}, 0, 0
        for mode in self.modes:
            response = pool.call({**q, 'op': 'reset', 'n': count, 'options': options,
                                  'samples': self.samples, 'seed': seed, 'maxSteps': self.max_steps,
                                  'mode': mode, 'belief': 'policy', 'neuralBeliefs': neural if mode == 'neural' else {}})
            ended = list(response['ended'])
            while any(o is not None for o in response['observations']):
                live = [i for i, o in enumerate(response['observations']) if o is not None]
                rows = [response['observations'][i] for i in live]
                if any(r['roles'][r['actor']] != 'neural' or
                       (mode == 'neural_economic' and r['actor'] != q['player']) for r in rows):
                    raise ValueError('Unexpected neural actor')
                choices = predict_batch(self.model, rows)
                actions = [None] * count
                for i, choice in zip(live, choices):
                    actions[i] = choice
                decisions += len(choices)
                response = pool.call({'op': 'step', 'actions': actions})
                ended.extend(response['ended'])
            if len(ended) != count or {r['env'] for r in ended} != set(range(count)):
                raise ValueError('Incomplete or duplicated rollout set')
            outcomes = {str(a): [None] * self.samples for a in options}
            for r in ended:
                sample, action = divmod(r['env'], len(options))
                expected_roles = ['neural' if mode == 'neural' or i == q['player'] else 'economic'
                                  for i in range(len(q['state']['players']))]
                if (r['sample'] != sample or r['actionIndex'] != options[action] or r['roles'] != expected_roles
                        or r['searchStats'] != {'decisions': 0, 'evaluations': 0, 'truncated': 0}
                        or not 0 <= r['steps'] <= self.max_steps
                        or (r['value'] is None) != r['truncated']
                        or (r['value'] is not None and not 0 <= r['value'] <= 1)):
                    raise ValueError('Invalid terminal rollout record')
                outcomes[str(options[action])][sample] = r['value']
                truncated += int(r['truncated'])
            all_outcomes[mode] = outcomes
        search = {'options': options, 'samplesPerMode': self.samples, 'modes': list(self.modes),
                  'seed': seed, 'evaluations': count * len(self.modes), 'truncated': truncated,
                  'neuralDecisions': decisions, 'maxSteps': self.max_steps,
                  'sampleOutcomes': all_outcomes, 'usable': truncated == 0,
                  'valueStatus': 'simulated-terminal-credits-not-calibrated-win-probabilities'}
        if truncated:
            # Do not choose using biased partial outcomes or count caps as losses.
            search['fallbackReason'] = 'incomplete-rollouts'
        else:
            means = {a: float(np.mean([all_outcomes[m][str(a)] for m in self.modes])) for a in options}
            index = max(options, key=lambda a: (means[a], a == proposal, -options.index(a)))
            result.update(index=index, move=moves[index])
            search['meanCredits'] = {str(a): means[a] for a in options}
        return {**result, 'search': search, 'elapsedMs': 1000 * (time.perf_counter() - started)}


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('model', type=Path)
    parser.add_argument('--samples', type=int, default=8)
    parser.add_argument('--workers', type=int, default=4)
    parser.add_argument('--scope', choices=SCOPES, default='combined')
    args = parser.parse_args()
    with HybridSearch(Model(args.model), samples=args.samples, workers=args.workers, scope=args.scope) as search:
        for line in sys.stdin:
            request = json.loads(line)
            result = search.choose(request)
            print(json.dumps({'requestId': request.get('requestId'), **result}, allow_nan=False), flush=True)


if __name__ == '__main__':
    main()
