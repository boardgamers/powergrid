"""Independent saved-receipt audit for eight-world auction experiments.

Uses the original fixed-pair continuation checker on every model/alternative
pair, then independently reconstructs the population-consensus selection.
"""
from fractions import Fraction
import importlib.util
from pathlib import Path

from population_policy_verification import verify_decision as verify_base
from surrogate_continuation_study_v1 import verify_result


def verify_search(row, config, seat):
    search = row['search']
    settings = config['identity']['settings']
    options = search['options']
    baseline = row['modelProposal']
    assert search['mode'] == 'opponent-auction-v1' and row['phase'] == 'auction'
    assert not row['filterApplied'] and row['filterCertificate'] is None
    assert search['samples'] == settings['samples'] == 8 and search['maxSteps'] == 2400
    assert 2 <= len(options) <= 7 and len(set(options)) == len(options) and baseline in options
    assert row['index'] in options
    components = search['components']
    modes = settings['population_modes']
    assert modes and len(set(modes)) == len(modes)
    assert [c['mode'] for c in components] == modes
    assert all(m in ('neural_population', 'surrogate_opponent_v1') for m in modes)
    means, shared_worlds, inference, rollouts = {}, {}, {'neural': 0, 'surrogate': 0}, 0
    for component in components:
        assert component['options'] == options
        assert component['samples'] == component['count'] == 8 and component['begin'] == 0
        assert len(component['rows']) == 8 * len(options)
        for i, receipt in enumerate(component['rows']):
            assert receipt['env'] == i and receipt['sample'] == i // len(options)
            assert receipt['actionIndex'] == options[i % len(options)]
            sample = receipt['sample']
            sha = receipt['diagnostic']['sampledWorldSha256']
            assert shared_worlds.setdefault(sample, sha) == sha
        component_means = {}
        for alternative in options:
            if alternative == baseline:
                continue
            pair = [baseline, alternative]
            indexed = {(r['sample'], r['actionIndex']): r for r in component['rows']}
            rows = [{**indexed[sample, action], 'env': 2 * sample + ordinal}
                    for sample in range(8) for ordinal, action in enumerate(pair)]
            decisions = {role: sum(r['policyDecisions'].get(role, 0) for r in rows)
                         for role in ('neural', 'surrogate')}
            subset = {**component, 'options': pair, 'rows': rows, 'seconds': component['elapsedMs'] / 1000,
                      'inference_decisions': decisions, 'caps': 0, 'outer_caps': 0, 'nested_caps': 0, 'usable': True}
            root = {'options': pair, 'identity': {'players': config['players'], 'seat': seat},
                    'prior_actors': search['priorActors']}
            checked = verify_result(root, subset, component['mode'], 0, 8)
            assert checked['caps'] == 0
            for ordinal, action in enumerate(pair):
                mean = sum((checked['credits'][sample, ordinal] for sample in range(8)), Fraction(0)) / 8
                assert component_means.setdefault(action, mean) == mean
        assert set(component_means) == set(options)
        assert component['caps'] == component['outer_caps'] == component['nested_caps'] == 0 and component['usable']
        counts = {role: sum(r['policyDecisions'].get(role, 0) for r in component['rows'])
                  for role in ('neural', 'surrogate')}
        assert counts == component['inference_decisions']
        for role, count in counts.items():
            inference[role] += count
        rollouts += len(component['rows'])
        means[component['mode']] = component_means
    pooled = {action: sum((means[mode][action] for mode in modes), Fraction(0)) / len(modes) for action in options}
    threshold = Fraction(settings['minimum_advantage'])
    assert 0 <= threshold <= 1 and str(threshold) == settings['minimum_advantage']
    eligible = [a for a in options if a == baseline or (
        pooled[a] - pooled[baseline] > threshold and all(means[mode][a] >= means[mode][baseline] for mode in modes))]
    choice = sorted(eligible, key=lambda a: (-pooled[a], a != baseline, options.index(a)))[0]
    selection = search['selection']
    assert selection == {
        'selected': choice, 'baseline': baseline, 'minimumAdvantage': settings['minimum_advantage'],
        'populationModes': modes, 'equalPopulationWeights': True, 'requireNonnegativeEachPopulation': True,
        'truncated': 0, 'fallbackReason': None, 'rule': 'strict-pooled-margin-with-population-consensus-v1',
        'status': 'empirical-screening-rule-not-calibrated-confidence', 'eligible': eligible,
        'meanCredits': {str(a): str(pooled[a]) for a in options},
        'pairedMeanMargins': {str(a): str(pooled[a] - pooled[baseline]) for a in options},
        'populationMeanMargins': {mode: {str(a): str(means[mode][a] - means[mode][baseline]) for a in options}
                                  for mode in modes}}
    assert row['index'] == choice
    assert search['evaluations'] == rollouts and search['truncated'] == 0 and search['usable'] is True
    assert search['neuralDecisions'] == inference['neural'] and search['surrogateDecisions'] == inference['surrogate']
    return {'rollouts': rollouts, 'rollout_caps': 0, 'neural_decisions': inference['neural'],
            'surrogate_decisions': inference['surrogate'], 'search_changes': int(choice != baseline), 'search_decisions': 1}


def verify_decision(row, config, seat, **kwargs):
    assert row['arm'] == config['arm'] == 'opponent-auction-v1'
    assert row['opponentPolicySha256'] == config['identity']['opponentPolicySha256']
    base = {**row, 'arm': 'filter', 'search': None}
    if row['search'] is not None:
        base['index'] = row['modelProposal']
        if 'arenaMoves' in row:
            base['move'] = row['arenaMoves'][base['index']]
    counts = verify_base(base, {**config, 'arm': 'filter'}, seat, **kwargs)
    if row['search'] is not None:
        counts.update(verify_search(row, config, seat))
    return counts


def verify_evaluation(directory, expected):
    path = Path(__file__).with_name('population_policy_verification.py')
    spec = importlib.util.spec_from_file_location('opponent_auction_report_base_v1', path)
    base = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(base)
    base.verify_decision = verify_decision
    return base.verify_evaluation(directory, expected)
