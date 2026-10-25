"""Complete paired fidelity analysis, preserving deal clusters and world strata.

Call paired_record on independently verified raw chunks, then analyze using the
frozen fresh-root manifest. This module never chooses actions or opponent policies.
"""
from collections import Counter, defaultdict
from fractions import Fraction
from itertools import product
import math
import re

from strategic_collection import ROOT, read, digest
from surrogate_continuation_roots_v1 import PROTOCOL, PHASES, contract, object_hash
from surrogate_continuation_study_v1 import paired_root, MODES

DESIGN = ROOT/'ai/strong/surrogate-continuation-analysis-design-v1.json'
REFERENCE = 'reference_opponent_v1'
SURROGATE = 'surrogate_opponent_v1'
POPULATION = 'neural_population'
COMPARED = (SURROGATE, POPULATION)
STRATA = [[0, 4], [1, 5], [2, 6], [3, 7]]
GROUPS = {f'{n}/{rule}/{phase}' for n in range(2, 7) for rule in range(4) for phase in PHASES}


def rational(value):
    return [value.numerator, value.denominator]


def number(value):
    return {'exact': rational(value), 'value': float(value)}


def average(values):
    assert values
    return sum(values, Fraction()) / len(values)


def sign(value):
    return (value > 0) - (value < 0)


def identity_key(q):
    assert q == contract(q['players'], q['deal'], q['seat'], q['rule'], 'root')
    return q['players'], q['deal'], q['seat'], q['rule']


def group(root):
    q = root['identity']
    return f'{q["players"]}/{q["rule"]}/{root["phase"]}'


def root_id(record):
    q = record['identity']
    return f'{q["players"]}:{q["episode"]}:{record["phase"]}'


def paired_record(root, results):
    """Keep existing terminal/pairing audits, additionally verify role strata."""
    report = paired_root(root, results)
    n, seat = root['identity']['players'], root['identity']['seat']
    roles = {}
    for chunk in results[POPULATION]:
        for row in chunk['rows']:
            assert roles.setdefault(row['sample'], row['roles']) == row['roles']
    assert set(roles) == set(range(8))
    for a, b in STRATA:
        assert roles[a] == roles[b], 'Population role stratum changed between repeated worlds'
    for actor in range(n):
        expected = {'neural'} if actor == seat else {'neural', 'economic', 'legacy', 'rush'}
        assert {roles[sample][actor] for sample in range(4)} == expected
    return {**report, 'population_strata': STRATA, 'population_roles': [roles[s] for s in range(8)]}


def manifest_roots(manifest):
    assert manifest['protocol_sha256'] == digest(PROTOCOL)
    assert manifest['focal_model_sha256'] == read(PROTOCOL)['focal_model_sha256']
    assert manifest['qualification_eligible'] is manifest['reserved_final_seeds_used'] is False
    expected = {(n, d, s, r) for n in range(2, 7) for d in range(2) for s in range(n) for r in range(4)}
    games = {}
    for row in manifest['games']:
        key = identity_key(row['identity']); assert key not in games
        assert set(row['missing_phases']) <= set(PHASES)
        assert len(row['missing_phases']) == len(set(row['missing_phases']))
        games[key] = row
    assert len(games) == 160 and set(games) == expected, 'Require every original game identity'
    roots = {}; counts = Counter(); phases = defaultdict(set)
    for root in manifest['roots']:
        key = identity_key(root['identity']); rid = root_id(root)
        assert rid == root['root_id'] and rid not in roots and root['phase'] in PHASES
        assert root['case'] == games[key]['case']
        assert type(root['decision']) is int and root['decision'] >= 0
        q = root['identity']
        assert root['rank'] == object_hash([q['seed'], q['episode'], root['phase'], root['decision']])
        assert set(root['request']) == {'state', 'player'} and root['request']['player'] == q['seat']
        assert root['public_root_sha256'] == object_hash(root['request'])
        assert len(root['options']) == 2 and len(set(root['options'])) == 2
        assert all(type(i) is int and 0 <= i < len(root['moves']) for i in root['options'])
        assert len(set(root['prior_actors'])) == len(root['prior_actors'])
        assert all(type(i) is int and 0 <= i < q['players'] and i != q['seat'] for i in root['prior_actors'])
        assert root['phase'] not in phases[key]
        phases[key].add(root['phase']); roots[rid] = root; counts[group(root)] += 1
    assert 0 < len(roots) <= 480
    assert set(counts) == GROUPS and dict(counts) == manifest['phase_counts'], 'Require all 60 groups'
    for key, game in games.items():
        assert set(game['missing_phases']) == set(PHASES)-phases[key], 'Missing roots differ from frozen missing phases'
    return roots


def read_credit(value, players):
    assert isinstance(value, list) and len(value) == 2
    assert all(type(v) is int for v in value)
    assert value == [0, 1] or (value[0] == 1 and 1 <= value[1] <= players), 'Impossible terminal tie credit'
    return Fraction(*value)


def check_record(root, report):
    assert report['identity'] == root['identity'] and report['phase'] == root['phase']
    assert report['root_sha256'] == object_hash(root) and report['public_root_sha256'] == root['public_root_sha256']
    assert report['options'] == root['options'] and report['prior_bid_count'] == len(root['prior_actors'])
    assert report['qualification_eligible'] is False
    assert type(report['caps']) is int and report['caps'] >= 0
    assert type(report['complete']) is bool and report['complete'] is (report['caps'] == 0)
    assert report['population_strata'] == STRATA
    roles = report['population_roles']; n = root['identity']['players']; seat = root['identity']['seat']
    assert len(roles) == 8 and all(len(row) == n for row in roles)
    assert all(roles[a] == roles[b] for a, b in STRATA)
    for actor in range(n):
        assert {roles[s][actor] for s in range(4)} == ({'neural'} if actor == seat else {'neural', 'economic', 'legacy', 'rush'})
    worlds = {str(k): v for k, v in report['world_sha256'].items()}
    assert len(worlds) == len(report['world_sha256']) == 8 and set(worlds) == {str(i) for i in range(8)}
    assert all(re.fullmatch('[a-f0-9]{64}', v) for v in worlds.values())
    assert set(report['mode_credits']) == set(MODES)
    credits = {}; missing = 0
    for mode in MODES:
        rows = report['mode_credits'][mode]
        assert len(rows) == 8 and all(len(row) == 2 for row in rows)
        credits[mode] = []
        for row in rows:
            pair = []
            for value in row:
                if value is None: pair.append(None); missing += 1
                else: pair.append(read_credit(value, n))
            credits[mode].append(pair)
    assert missing <= report['caps']
    if report['complete']:
        assert missing == 0
        margins = {mode: average([b-a for a, b in values]) for mode, values in credits.items()}
        assert report['margins'] == {mode: rational(value) for mode, value in margins.items()}, 'Recomputed margins disagree'
    else:
        assert report['margins'] is None
    return credits


def multiplicities(count):
    """Exact two-draw empirical bootstrap in each of count independent strata."""
    for choices in product(range(3), repeat=count):
        yield [(2-j, j) for j in choices], math.prod(2 if j == 1 else 1 for j in choices)


def interval(distribution):
    """Integer probability weights; no interpolation or discarded replicates."""
    combined = Counter()
    for value, weight in distribution: combined[value] += weight
    total = sum(combined.values()); assert total > 0
    result = []
    for numerator in (1, 39):
        cumulative = 0
        for value, weight in sorted(combined.items()):
            cumulative += weight
            if 40*cumulative >= numerator*total:
                result.append(number(value)); break
    return {'level': .95, 'lower': result[0], 'upper': result[1]}


def within_root(credits):
    # 60 is the LCM of all possible terminal tie denominators for 2--6 players.
    # Integer arithmetic makes percentile ordering and ties exact.
    scaled = {mode: [int((b-a)*60) for a, b in values] for mode, values in credits.items()}
    distributions = defaultdict(list)
    for pairs, probability in multiplicities(4):
        weights = [0]*8
        for (a, b), (wa, wb) in zip(STRATA, pairs): weights[a] = wa; weights[b] = wb
        margins = {mode: Fraction(sum(w*v for w, v in zip(weights, values)), 480) for mode, values in scaled.items()}
        for mode, value in margins.items(): distributions[mode].append((value, probability))
        errors = {mode: abs(margins[mode]-margins[REFERENCE]) for mode in COMPARED}
        for mode, value in errors.items(): distributions[mode+'_absolute_error'].append((value, probability))
        distributions['surrogate_minus_population_error'].append((errors[SURROGATE]-errors[POPULATION], probability))
    standard_errors = {}
    for mode, values in scaled.items():
        variance = sum((Fraction(values[a]-values[b], 60)**2 for a, b in STRATA), Fraction())/64
        standard_errors[mode] = {'variance_exact': rational(variance), 'standard_error': math.sqrt(float(variance))}
    return {'method': 'exact paired bootstrap within four fixed opponent-role strata',
            'multiplicity_patterns': 81, 'ordered_resamples': 256, 'strata': STRATA,
            'intervals': {key: interval(values) for key, values in distributions.items()},
            'margin_standard_errors': standard_errors}


def root_metrics(credits):
    margins = {mode: average([b-a for a, b in values]) for mode, values in credits.items()}
    action_means = {mode: [average([row[i] for row in values]) for i in range(2)] for mode, values in credits.items()}
    values = {}
    for mode in COMPARED:
        delta = margins[mode]-margins[REFERENCE]
        values[mode] = {'absolute_margin_error': abs(delta), 'signed_margin_error': delta,
                        'absolute_action_credit_error': average([abs(a-b) for a, b in zip(action_means[mode], action_means[REFERENCE])]),
                        'preference_agreement': Fraction(sign(margins[mode]) == sign(margins[REFERENCE])),
                        'predicted_tie': Fraction(margins[mode] == 0),
                        'reference_tie': Fraction(margins[REFERENCE] == 0)}
    return values


def summarize(rows):
    assert rows
    by_group = defaultdict(list)
    for row in rows: by_group[row['group']].append(row)
    groups = {}
    for key, items in sorted(by_group.items()):
        groups[key] = {'roots': len(items), 'deals': sorted({r['deal'] for r in items}), 'metrics': {}}
        for mode in COMPARED:
            groups[key]['metrics'][mode] = {name: average([r['metrics'][mode][name] for r in items])
                for name in items[0]['metrics'][mode]}
        groups[key]['surrogate_minus_population_error'] = (groups[key]['metrics'][SURROGATE]['absolute_margin_error']
                                                          - groups[key]['metrics'][POPULATION]['absolute_margin_error'])
    macro = {mode: {name: average([g['metrics'][mode][name] for g in groups.values()])
                   for name in rows[0]['metrics'][mode]} for mode in COMPARED}
    return {'roots': len(rows), 'represented_groups': len(groups), 'groups': groups, 'macro': macro,
            'surrogate_minus_population_error': macro[SURROGATE]['absolute_margin_error']-macro[POPULATION]['absolute_margin_error'],
            'adverse_groups': [key for key, g in groups.items() if g['surrogate_minus_population_error'] > 0]}


def whole_deal_uncertainty(rows):
    buckets = defaultdict(list)
    for row in rows: buckets[(row['group'], row['deal'])].append(row)
    distributions = {mode: [] for mode in COMPARED}; distributions['surrogate_minus_population_error'] = []
    undefined = 0
    for pairs, probability in multiplicities(5):
        estimates = {mode: [] for mode in COMPARED}; missing = False
        for key in sorted(GROUPS):
            weights = pairs[int(key.split('/')[0])-2]
            count = sum(w*len(buckets[(key, d)]) for d, w in enumerate(weights))
            if count == 0: missing = True; break
            for mode in COMPARED:
                numerator = sum((w*sum((r['metrics'][mode]['absolute_margin_error'] for r in buckets[(key, d)]), Fraction())
                                 for d, w in enumerate(weights)), Fraction())
                estimates[mode].append(numerator/count)
        if missing: undefined += probability; continue
        means = {mode: average(values) for mode, values in estimates.items()}
        for mode, value in means.items(): distributions[mode].append((value, probability))
        distributions['surrogate_minus_population_error'].append((means[SURROGATE]-means[POPULATION], probability))
    assert sum(w for _, w in distributions[SURROGATE])+undefined == 4**5
    return {'method': 'exact whole-deal cluster bootstrap stratified by player count',
            'deals_per_count': 2, 'multiplicity_patterns': 243, 'ordered_resamples': 1024,
            'undefined_probability': number(Fraction(undefined, 1024)),
            'intervals': None if undefined else {key: interval(values) for key, values in distributions.items()},
            'limitation': 'Only two independent deals per count. No replicate is dropped or renormalized when a group is absent.'}


def serialized(value):
    if isinstance(value, Fraction): return number(value)
    if isinstance(value, dict): return {k: serialized(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)): return [serialized(v) for v in value]
    return value


def analyze(manifest, reports):
    roots = manifest_roots(manifest); ordered = {}; parsed = {}
    for report in reports:
        rid = root_id(report)
        assert rid in roots and rid not in ordered, 'Unexpected or duplicate paired root'
        parsed[rid] = check_record(roots[rid], report); ordered[rid] = report
    assert set(ordered) == set(roots), 'Require every frozen root, including incomplete ones'
    caps = sum(r['caps'] for r in ordered.values())
    result = {'complete': caps == 0, 'games': 160, 'roots': len(roots), 'groups': 60,
              'continuations': len(roots)*48, 'caps': caps,
              'manifest_sha256_canonical': object_hash(manifest), 'protocol_sha256': digest(PROTOCOL),
              'analysis_design_sha256': digest(DESIGN), 'analysis_code_sha256': digest(__file__),
              'paired_records': {rid: ordered[rid] for rid in sorted(ordered)},
              'primary': None, 'whole_deal_uncertainty': None, 'by_prior_bids': None, 'root_metrics': None,
              'qualification_eligible': False, 'reserved_final_seeds_used': False,
              'scope': read(DESIGN)['scope'],
              'limitation': read(DESIGN)['interval']}
    if caps: return result
    rows = []
    for rid in sorted(roots):
        root = roots[rid]
        rows.append({'root_id': rid, 'group': group(root), 'deal': root['identity']['deal'],
                     'prior_bid_count': len(root['prior_actors']), 'metrics': root_metrics(parsed[rid]),
                     'within_root_uncertainty': within_root(parsed[rid])})
    result['primary'] = summarize(rows)
    result['whole_deal_uncertainty'] = whole_deal_uncertainty(rows)
    result['by_prior_bids'] = {}
    for name, has_prior in (('without_prior_bids', False), ('with_prior_bids', True)):
        selected = [row for row in rows if bool(row['prior_bid_count']) == has_prior]
        result['by_prior_bids'][name] = summarize(selected) if selected else {'roots': 0, 'represented_groups': 0}
    result['root_metrics'] = rows
    return serialized(result)
