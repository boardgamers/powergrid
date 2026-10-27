"""Predeclared development statistics; no simulations, selection or job APIs.

The CLI must independently audit raw receipts first. This layer additionally
checks complete pairing and recomputes credits from terminal scores. Synthetic
unit-test records exercise statistics only and are never strength evidence.
"""
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path

import numpy as np

PROTOCOL = Path(__file__).with_name('conservative-auction-development-protocol-v2.json')
PROTOCOL_SHA = '51b845f4a57c3131475e24267fbbb08eb624c391aa6a8e6a4f5d5c6b8ac718ee'
ARMS = ('filter', 'conservative_population', 'conservative_dual')
CONTRASTS = (('conservative_population', 'filter'), ('conservative_dual', 'filter'),
             ('conservative_dual', 'conservative_population'))
RULES = ('original/sealed', 'recharged/sealed', 'original/open', 'recharged/open')
REPLICATES = 10000
BOOTSTRAP_SEED = 15125


def require(condition, message):
    if not condition:
        raise ValueError(message)


def protocol():
    raw = PROTOCOL.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == PROTOCOL_SHA, 'Frozen protocol changed')
    return json.loads(raw)


def integer(value, low=0):
    require(type(value) is int and value >= low, 'Invalid integer')


def same(a, b):
    return json.dumps(a, sort_keys=True, allow_nan=False) == json.dumps(b, sort_keys=True, allow_nan=False)


def validate_identities(identities, p):
    require(set(identities) == set(ARMS), 'All three exact identities required')
    for arm in ARMS:
        identity, spec = identities[arm], p['arms'][arm]
        expected = {'backend': spec['backend'], 'featureRevision': spec['feature_revision'],
                    'modelSha256': spec['model']['sha256'],
                    'runtimeManifestSha256': spec['runtime_manifest']['sha256'],
                    'settings': spec['settings'], 'policySha256': identity['policySha256']}
        sha = identity['policySha256']
        require(isinstance(sha, str) and len(sha) == 64 and all(c in '0123456789abcdef' for c in sha),
                'Invalid descriptor hash')
        if 'opponent' in spec:
            expected['opponentPolicySha256'] = spec['opponent']['sha256']
        require(same(identity, expected), 'Changed model, runtime, settings or opponent identity')


def score_record(record, arm, screen, identity, p):
    """Independent terminal-score calculation, including lexicographic ties."""
    require(same(record['public_runtime_identity'], identity), 'Mixed policy identities')
    integer(record['rollout_caps'])
    require(record['rollout_caps'] == 0, 'Capped continuation')
    t = record['terminal']; n = screen['players']; episode = record['episode']
    integer(episode)
    require(episode < 32*n, 'Unexpected episode/deal')
    deal, seat, rule = episode//(4*n), episode//4 % n, episode % 4
    for key, value in (('episode', episode), ('env', 0), ('seat', seat), ('playerCount', n)):
        require(type(t[key]) is int and t[key] == value, 'Wrong episode/seat/player count')
    require(t['gameSeed'] == p['seed_template'].format(players=n)+'-'+str(deal), 'Wrong exact seed')
    require(t['variant'] == ('recharged' if rule % 2 else 'original')
            and t['sealed'] is (rule < 2), 'Wrong rule pairing')
    require(t['truncated'] is False, 'Incomplete game')
    integer(t['steps'], 1); require(t['steps'] <= p['game_max_steps'], 'Game horizon exceeded')
    role = 'snapshot0' if screen['opponent'] == 'a260' else screen['opponent']
    require(t['roles'] == ['learner' if i == seat else role for i in range(n)], 'Wrong opponents/roles')
    final = t['final']; integer(final['round'], 1)
    require(len(final['players']) == n, 'Missing terminal players')
    scores = []
    for player in final['players']:
        for key in ('powered', 'money', 'cities', 'capacity'):
            integer(player[key])
        require(player['powered'] <= min(player['capacity'], player['cities']), 'Impossible powered cities')
        require(len(player['plants']) <= (4 if n == 2 else 3), 'Too many plants')
        scores.append(tuple(player[k] for k in ('powered', 'money', 'cities')))
    best = max(scores); winners = scores.count(best)
    credits = [Fraction(int(score == best), winners) for score in scores]
    require(len(t['value']) == n, 'Wrong credit count')
    for actual, expected in zip(t['value'], credits):
        require(type(actual) in (int, float) and math.isfinite(actual) and actual == float(expected),
                'Forged or nonfinite terminal credit')
    credit = credits[seat]
    require(type(t['win']) in (int, float) and math.isfinite(t['win']) and t['win'] == float(credit),
            'Wrong learner credit')
    return (deal, rule, seat), {'credit': credit, 'strict': Fraction(int(credit == 1)),
                              'tied': Fraction(int(0 < credit < 1))}


def validate_grid(reports, identities):
    p = protocol(); validate_identities(identities, p)
    screens = {f"{s['opponent']}/{s['players']}p": s for s in p['screens']}
    require(set(reports) == set(ARMS), 'All three arms required')
    scored = {arm: {} for arm in ARMS}
    for arm in ARMS:
        require(set(reports[arm]) == set(screens), 'All 27 cells required for every arm')
        for cell, screen in screens.items():
            rows = reports[arm][cell]; n = screen['players']; seen = {}
            require(len(rows) == screen['games'] == 32*n, 'Missing/extra games')
            for record in rows:
                key, value = score_record(record, arm, screen, identities[arm], p)
                require(key not in seen, 'Duplicate paired game')
                seen[key] = value
            expected = {(d, r, s) for d in range(8) for r in range(4) for s in range(n)}
            require(set(seen) == expected, 'Incomplete paired deals')
            scored[arm][cell] = seen
    require(sum(len(rows) for cells in scored.values() for rows in cells.values()) == 10080,
            'Wrong total game count')
    return scored, screens


def bootstrap_indices():
    # One shared draw for all arms/opponents/rules at a player count. Never
    # resample individual seats or independently resample the compared policies.
    return np.random.default_rng(BOOTSTRAP_SEED).integers(0, 8, size=(REPLICATES, 5, 8))


def deal_means(scored, metric='credit', rule=None):
    return tuple(sum((v[metric] for (d, r, _), v in sorted(scored.items())
                      if d == deal and (rule is None or r == rule)), Fraction()) /
                 sum(d == deal and (rule is None or r == rule) for d, r, _ in scored)
                 for deal in range(8))


def estimate(values, n, indices):
    mean = sum(values, Fraction())/8
    sample = np.asarray([float(v) for v in values])[indices[:, n-2, :]].mean(axis=1)
    return {'mean': float(mean), 'exact_mean': str(mean),
            'deal_means': [float(v) for v in values],
            'paired_whole_deal_95_interval': np.quantile(sample, [.025, .975]).tolist()}


def contrast_name(left, right):
    return left+'_minus_'+right


def analyze(reports, identities):
    scored, screens = validate_grid(reports, identities)
    indices = bootstrap_indices(); absolute = {a: {} for a in ARMS}
    contrasts = {contrast_name(*pair): {} for pair in CONTRASTS}
    regressions = {key: {'negative': [], 'zero': [], 'positive': []} for key in contrasts}
    means = {}
    for cell, screen in screens.items():
        n = screen['players']
        for arm in ARMS:
            views = {}
            for name, rule in [('overall', None), *zip(RULES, range(4))]:
                metrics = {metric: deal_means(scored[arm][cell], metric, rule)
                           for metric in ('credit', 'strict', 'tied')}
                means[arm, cell, name] = metrics
                views[name] = {'games': 32*n if rule is None else 8*n,
                               'win_credit': estimate(metrics['credit'], n, indices),
                               'strict_win_rate': estimate(metrics['strict'], n, indices),
                               'tied_win_rate': estimate(metrics['tied'], n, indices)}
            absolute[arm][cell] = views
        for left, right in CONTRASTS:
            key = contrast_name(left, right); views = {}
            for name in ('overall', *RULES):
                differences = {metric: tuple(a-b for a, b in zip(means[left, cell, name][metric],
                                                               means[right, cell, name][metric]))
                               for metric in ('credit', 'strict')}
                views[name] = {'win_credit_difference': estimate(differences['credit'], n, indices),
                               'strict_win_rate_difference': estimate(differences['strict'], n, indices)}
                sign = sum(differences['credit'], Fraction())
                regressions[key]['negative' if sign < 0 else 'positive' if sign > 0 else 'zero'].append(
                    {'cell': cell, 'rules': name, 'difference': float(sign/8)})
            contrasts[key][cell] = views
    primary = {}
    for left, right in CONTRASTS:
        deltas = [tuple(a-b for a, b in zip(means[left, f'search_geo/{n}p', 'overall']['credit'],
                                           means[right, f'search_geo/{n}p', 'overall']['credit']))
                  for n in range(2, 7)]
        exact = sum((sum(v, Fraction())/8 for v in deltas), Fraction())/5
        samples = sum(np.asarray([float(v) for v in values])[indices[:, i, :]].mean(axis=1)/5
                      for i, values in enumerate(deltas))
        primary[contrast_name(left, right)] = {
            'role': 'secondary' if right != 'filter' else 'primary',
            'win_credit_difference': float(exact), 'exact_difference': str(exact),
            'paired_whole_deal_95_interval': np.quantile(samples, [.025, .975]).tolist(),
            'per_count': {str(n): {'weight': .2, **estimate(deltas[n-2], n, indices)} for n in range(2, 7)}}
    return {'complete': True, 'games': 10080, 'games_per_arm': 3360, 'cells_per_arm': 27,
            'independent_deals_per_count': 8, 'absolute': absolute, 'contrasts': contrasts,
            'search_equal_count': primary, 'all_cell_directions': regressions,
            'uncertainty': {'replicates': REPLICATES, 'seed': BOOTSTRAP_SEED,
                'indices_sha256': hashlib.sha256(indices.astype('<i8').tobytes()).hexdigest(),
                'method': 'Paired whole-deal resampling within each player count; shared indices across arms, opponents, seats and rules.',
                'interpretation': 'Exploratory marginal 95% intervals with eight deals per count; no multiplicity adjustment or qualification claim.'},
            'candidate_selected': False, 'qualification_eligible': False, 'reserved_final_seeds_used': False}
