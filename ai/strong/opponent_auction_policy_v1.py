"""Auction-only research chooser over the existing verified continuation paths.

Settings must be explicit. This implementation does not select a research recipe,
use arena opponent identity, or claim a calibrated confidence/win probability.
"""
from fractions import Fraction
import time

from population_hybrid_policy import PopulationPolicy
from surrogate_opponent_continuations_v1 import SurrogateContinuationProbe

MODES = ('neural_population', 'surrogate_opponent_v1')


def settings_check(modes, minimum_advantage):
    if (not isinstance(modes, (list, tuple)) or not modes or len(set(modes)) != len(modes)
            or tuple(mode for mode in MODES if mode in modes) != tuple(modes)):
        raise ValueError('Expected an ordered nonempty subset of the two public opponent populations')
    if not isinstance(minimum_advantage, str):
        raise ValueError('Minimum advantage must be an exact rational string')
    threshold = Fraction(minimum_advantage)
    if not 0 <= threshold <= 1 or str(threshold) != minimum_advantage:
        raise ValueError('Expected a canonical advantage between zero and one')
    return threshold


def select_action(components, options, baseline, seat, *, modes, minimum_advantage):
    """Equal-weight population means; keep baseline on ties/weak/disputed gains.

    Recompute exact tie credits from terminal players. A candidate must have a
    strictly larger pooled margin than the configured threshold and a nonnegative
    margin in every included population. These are empirical screening rules,
    not a confidence interval. No incomplete continuation can support an override.
    """
    threshold = settings_check(modes, minimum_advantage)
    if not options or len(set(options)) != len(options) or baseline not in options:
        raise ValueError('Invalid candidate menu or missing model baseline')
    if [component['mode'] for component in components] != list(modes):
        raise ValueError('Missing, repeated or reordered population results')
    sizes = {component['samples'] for component in components}
    if len(sizes) != 1 or next(iter(sizes)) not in range(4, 65, 4):
        raise ValueError('Unequal or unbalanced world budgets')
    samples = next(iter(sizes))
    all_credits, worlds, caps = {}, {}, 0
    for component in components:
        if (component['options'] != options or component['begin'] != 0
                or component['count'] != samples or len(component['rows']) != samples * len(options)):
            raise ValueError('Incomplete action/world coverage')
        mode = component['mode']
        scores = {action: [] for action in options}
        local_caps = 0
        for i, row in enumerate(component['rows']):
            sample, ordinal = divmod(i, len(options))
            action = options[ordinal]
            if row['env'] != i or row['sample'] != sample or row['actionIndex'] != action:
                raise ValueError('Missing or reordered continuation')
            digest = row['diagnostic']['sampledWorldSha256']
            if worlds.setdefault(sample, digest) != digest:
                raise ValueError('Candidate/population comparisons use different initial sampled worlds')
            terminal = row['diagnostic']['terminal']
            if row['truncated']:
                if terminal is not None or row['value'] is not None:
                    raise ValueError('A capped continuation cannot have a terminal score')
                local_caps += 1
                scores[action].append(None)
            else:
                if not isinstance(terminal, list) or not 2 <= len(terminal) <= 6 or not 0 <= seat < len(terminal):
                    raise ValueError('Invalid terminal player list')
                ranked = [tuple(player[k] for k in ('powered', 'money', 'cities')) for player in terminal]
                if any(type(v) is not int or v < 0 for score in ranked for v in score):
                    raise ValueError('Invalid terminal score')
                best = max(ranked)
                credit = Fraction(1, ranked.count(best)) if ranked[seat] == best else Fraction(0)
                if row['value'] != float(credit):
                    raise ValueError('Saved value differs from terminal credit')
                scores[action].append(credit)
        if (component['nested_caps'] != 0 or component['outer_caps'] != local_caps
                or component['caps'] != local_caps or component['usable'] != (local_caps == 0)):
            raise ValueError('Inconsistent continuation cap report')
        caps += local_caps
        all_credits[mode] = scores
    result = {'selected': baseline, 'baseline': baseline, 'minimumAdvantage': minimum_advantage,
              'populationModes': list(modes), 'equalPopulationWeights': True,
              'requireNonnegativeEachPopulation': True, 'truncated': caps,
              'fallbackReason': 'incomplete-rollouts' if caps else None,
              'rule': 'strict-pooled-margin-with-population-consensus-v1',
              'status': 'empirical-screening-rule-not-calibrated-confidence'}
    if caps:
        return result
    means = {mode: {a: sum(values, Fraction(0)) / samples for a, values in scores.items()}
             for mode, scores in all_credits.items()}
    pooled = {a: sum((means[mode][a] for mode in modes), Fraction(0)) / len(modes) for a in options}
    margins = {a: pooled[a] - pooled[baseline] for a in options}
    population_margins = {mode: {a: means[mode][a] - means[mode][baseline] for a in options} for mode in modes}
    eligible = [a for a in options if a == baseline or (margins[a] > threshold and
                all(population_margins[mode][a] >= 0 for mode in modes))]
    selected = max(eligible, key=lambda a: (pooled[a], a == baseline, -options.index(a)))
    result.update(selected=selected, eligible=eligible,
                  meanCredits={str(a): str(pooled[a]) for a in options},
                  pairedMeanMargins={str(a): str(margins[a]) for a in options},
                  populationMeanMargins={mode: {str(a): str(v) for a, v in values.items()}
                                         for mode, values in population_margins.items()})
    return result


class OpponentAuctionPolicy:
    def __init__(self, model, surrogate, worker, *, modes, minimum_advantage,
                 samples, workers, max_steps, surrogate_sha256):
        settings_check(modes, minimum_advantage)
        self.model, self.modes = model, tuple(modes)
        self.minimum_advantage, self.samples, self.max_steps = minimum_advantage, samples, max_steps
        self.surrogate_sha256 = surrogate_sha256
        self.base = PopulationPolicy(model, worker, arm='filter', samples=samples,
                                     workers=workers, max_steps=max_steps)
        self.node, self.revision = self.base.node, self.base.revision
        self.probe = SurrogateContinuationProbe(model, surrogate, workers=workers)

    def close(self):
        self.probe.close()
        self.base.close()

    def choose(self, request):
        begin = time.perf_counter()
        result = {**self.base.choose(request), 'arm': 'opponent-auction-v1',
                  'opponentPolicySha256': self.surrogate_sha256}
        if result['phase'] != 'auction':
            return result
        q = {'state': request['state'], 'player': request['player'], 'featureRevision': self.revision}
        root = self.node.call({**q, 'op': 'prepare'})
        baseline = result['index']
        options = [i for i in dict.fromkeys([*root['options'], baseline]) if i not in root['lossFilter']['forbidden']]
        if len(options) < 2:
            return result
        assert baseline in options and not result['filterApplied']
        components = []
        for mode in self.modes:
            probe = self.probe.run(request, options, mode=mode, samples=self.samples, max_steps=self.max_steps)
            # Shared transport comparisons remove elapsedMs, retaining every
            # logical continuation field and allowing cold/warm exact parity.
            components.append({**{k: v for k, v in probe.items() if k != 'seconds'},
                               'elapsedMs': 1000 * probe['seconds']})
        selected = select_action(components, options, baseline, request['player'],
                                 modes=self.modes, minimum_advantage=self.minimum_advantage)
        index = selected['selected']
        result.update(index=index, move=root['moves'][index], elapsedMs=1000 * (time.perf_counter() - begin),
                      search={'mode': 'opponent-auction-v1', 'samples': self.samples, 'maxSteps': self.max_steps,
                              'options': options, 'priorActors': [p['actor'] for p in root['prior']],
                              'selection': selected, 'components': components,
                              'evaluations': sum(len(component['rows']) for component in components),
                              'neuralDecisions': sum(component['inference_decisions']['neural'] for component in components),
                              'surrogateDecisions': sum(component['inference_decisions']['surrogate'] for component in components),
                              'truncated': selected['truncated'], 'usable': selected['truncated'] == 0,
                              'valueStatus': 'simulated-terminal-credits-not-calibrated-win-probabilities'})
        return result
