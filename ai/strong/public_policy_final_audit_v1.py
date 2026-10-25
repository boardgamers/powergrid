"""Read-only final-game audit for the exact standalone public policy.

This module neither launches games nor selects/qualifies a candidate. It checks
raw game/decision receipts and the unchanged multiplayer strength requirements.
Final launch admission, export parity and complete-policy target CPU evidence
remain separate mandatory parts of qualification.
"""
from collections import Counter
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path

from arena_statistics import validate_pairs, win_summary
from opponent_auction_policy_v1 import settings_check
from opponent_auction_verification_v1 import verify_decision as verify_auction
from population_policy_verification import verify_decision as verify_population
from public_policy_arena_v1 import validate_response, wire_json
from public_policy_runtime_v1 import checked_path, encode, sha256

PROTOCOL_SHA = '7f0336c8784faf8f18e046b95b88e0ab1be7c2de1c0ec4d3eec96f0a415286ce'


def read(path):
    return json.loads(Path(path).read_text())


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def require(ok, message):
    if not ok:
        raise ValueError(message)


def same(a, b):
    return encode(a) == encode(b)


def integer(value, low=0):
    require(type(value) is int and value >= low, 'Invalid integer')


def finite(value):
    require(type(value) in (int, float) and math.isfinite(value) and value >= 0, 'Invalid duration/value')


def protocol(path=None):
    path = Path(path) if path else Path(__file__).with_name('final-protocol-multiplayer.json')
    require(digest(path) == PROTOCOL_SHA, 'Final protocol changed')
    return read(path)


def schedule():
    """Enumerate existing reserved names only; never consume or execute seeds."""
    p = protocol()
    result = []
    for opponent in p['opponents']:
        for count, spec in opponent['counts'].items():
            n = int(count)
            require(spec['games'] == 4 * n * opponent['independent_deals_per_count'], 'Invalid paired-deal specification')
            for start in range(0, opponent['independent_deals_per_count'], 4):
                result.append({'name': f"{p['seed_prefix']}-{opponent['name']}-{n}p-{start//4:02}",
                    'group': f"{opponent['name']}/{n}p", 'players': n, 'start': start, 'deals': 4,
                    'seed': f"{p['seed_prefix']}-{n}p", 'opponent': 'a260' if 'model_path' in opponent else opponent['name'],
                    'opponent_sha256': opponent.get('model_sha256'), 'games': 16*n})
    require(len(result) == 320 and sum(s['games'] for s in result) == 20160, 'Final schedule changed')
    return result


def validate_identity(identity):
    fields = {'policySha256', 'runtimeManifestSha256', 'modelSha256', 'featureRevision', 'backend', 'settings'}
    auction = identity.get('backend') == 'opponent-auction-v1'
    if auction:
        fields.add('opponentPolicySha256')
    require(set(identity) == fields, 'Incomplete or unexpected complete-policy identity')
    for name in fields - {'featureRevision', 'backend', 'settings'}:
        sha256(identity[name])
    require(identity['featureRevision'] == '4.3-strategic-correction', 'Unsupported feature contract')
    require(identity['backend'] in ('population-v1', 'opponent-auction-v1'), 'Unsupported backend')
    settings = identity['settings']
    expected = {'arm', 'samples', 'workers', 'threads', 'max_steps'}
    if auction:
        expected.update(('population_modes', 'minimum_advantage'))
    require(set(settings) == expected, 'Missing or unexpected selected settings')
    integer(settings['samples'], 4)
    require(settings['samples'] in range(4, 65, 4), 'Unbalanced sample budget')
    for key in ('workers', 'threads'):
        integer(settings[key], 1)
        require(settings[key] <= 32, 'Unsupported concurrency')
    require(type(settings['max_steps']) is int and settings['max_steps'] == 2400, 'Incomplete simulation horizon')
    if auction:
        require(settings['arm'] == 'auction' and settings['samples'] == 8,
                'Opponent-aware saved-pair verifier currently admits eight worlds only')
        settings_check(settings['population_modes'], settings['minimum_advantage'])
    else:
        require(settings['arm'] in ('model', 'filter', 'auction', 'building', 'combined'), 'Unsupported population arm')
    return identity


def artifact_identity(root, descriptor='policy.json'):
    """Validate the actual artifact without importing it or running inference."""
    root = Path(root).resolve()
    spec_path = checked_path(root, descriptor)
    spec = read(spec_path)
    require(type(spec['version']) is int and spec['version'] == 1, 'Unsupported artifact')
    manifest_path = checked_path(root, spec['runtime_manifest']['path'])
    require(digest(manifest_path) == spec['runtime_manifest']['sha256'], 'Changed runtime manifest')
    manifest = read(manifest_path)
    require(bool(manifest), 'Empty runtime manifest')
    for name, sha in manifest.items():
        require(digest(checked_path(root, name)) == sha256(sha), 'Changed runtime file: '+name)
    for name in ('ai/strong/public_policy_arena_v1.py', 'ai/strong/public_policy_runtime_v1.py'):
        require(name in manifest, 'Missing standalone execution path')
    require(manifest.get(spec['model']['path']) == spec['model']['sha256'], 'Unpinned focal model')
    identity = {'policySha256': digest(spec_path), 'runtimeManifestSha256': digest(manifest_path),
                'modelSha256': spec['model']['sha256'], 'featureRevision': spec['feature_revision'],
                'backend': spec['backend'], 'settings': spec['settings']}
    if spec['backend'] == 'opponent-auction-v1':
        require(manifest.get(spec['opponent']['path']) == spec['opponent']['sha256'], 'Unpinned opponent policy')
        identity['opponentPolicySha256'] = spec['opponent']['sha256']
    return validate_identity(identity)


def audit_terminal(record, expected):
    n = expected['players']; episode = record['episode']; integer(episode)
    require(type(n) is int and n in range(2, 7), 'Unsupported player count')
    start, end = expected['start']*4*n, (expected['start']+expected['deals'])*4*n
    require(start <= episode < end, 'Episode outside frozen shard')
    t = record['terminal']; seat = episode//4 % n
    require(same([t['episode'], t['env'], t['seat'], t['playerCount']], [episode, 0, seat, n]), 'Wrong episode/seat/count')
    require(t['gameSeed'] == expected['seed']+'-'+str(episode//(4*n)), 'Wrong exact deal seed')
    require(t['variant'] == ('recharged' if episode % 2 else 'original') and t['sealed'] is (episode % 4 < 2), 'Wrong rule pairing')
    integer(record['rollout_caps'])
    require(t['truncated'] is False and record['rollout_caps'] == 0, 'Incomplete game or search')
    integer(t['steps'], 1); require(t['steps'] <= 1600, 'Exceeded game horizon')
    role = 'snapshot0' if expected['opponent'] == 'a260' else expected['opponent']
    require(t['roles'] == ['learner' if i == seat else role for i in range(n)], 'Wrong opponent/learner roles')
    final = t['final']; integer(final['round'], 1)
    require(len(final['players']) == n, 'Missing terminal players')
    scores = []
    for player in final['players']:
        for key in ('powered', 'cities', 'money', 'capacity'):
            integer(player[key])
        require(player['powered'] <= min(player['capacity'], player['cities']), 'Impossible powered-city count')
        require(len(player['plants']) <= (4 if n == 2 else 3), 'Too many plants')
        scores.append(tuple(player[k] for k in ('powered', 'money', 'cities')))
    best = max(scores)
    credits = [float(Fraction(int(score == best), scores.count(best))) for score in scores]
    require(len(t['value']) == n, 'Wrong terminal value count')
    for value in t['value']:
        finite(value)
    require(t['value'] == credits, 'Wrong recomputed terminal credits')
    require(type(t['win']) in (int, float) and t['win'] == credits[seat], 'Wrong learner credit')
    require(set(t['searchStats']) == ({'search_geo'} if role == 'search_geo' else set()), 'Missing/extra independent-search diagnostics')
    for stats in t['searchStats'].values():
        require(set(stats) == {'decisions', 'evaluations', 'truncated'}, 'Invalid independent-search counters')
        for key, value in stats.items():
            integer(value)
        require(stats['truncated'] == 0 and stats['decisions'] > 0 and stats['evaluations'] > 0, 'Independent search absent or capped')
    return t


def audit_public_decision(row, identity, episode, seat, ordinal):
    request, response = row['publicRequest'], row['publicResponse']
    require(type(row['decision']) is int and row['decision'] == ordinal, 'Skipped decision receipt')
    require(request['requestId'] == f'{episode}:{ordinal}' and same(request['revision'], ordinal)
            and same(request['player'], seat), 'Stale/wrong public request')
    state = request['state']
    require(state['seed'] == 'secret' and state['powerPlantsDeck'] == [] and not state.get('hiddenLog')
            and 'powerPlantDeckAfterStep3' not in state, 'Private state in policy input')
    if state['options']['fastBid']:
        require(all(p['bid'] == 0 for p in state['players']), 'Private sealed bids in policy input')
    choice = validate_response(response, request, row['arenaMoves'], row['arenaPlayerOrder'], identity)
    require(choice == row['index'] and all(wire_json(row[k]) == wire_json(v) for k, v in response['decision'].items()),
            'Public response differs from stored decision')


def audit_shard(directory, expected, identity, *, reserved):
    """Audit every saved receipt; caller must supply the frozen expected shard."""
    validate_identity(identity)
    require(type(reserved) is bool, 'Explicit seed purpose required')
    if reserved:
        require(expected in schedule(), 'Shard is not in the unchanged final schedule')
    else:
        require('reserved' not in expected['seed'].lower(), 'Engineering audit cannot relabel reserved seeds')
    directory = Path(directory); report = read(directory/'evaluation.json'); config = report['config']
    require(report['passed'] is True and report['all_complete'] is True and not report['errors']
            and report['validation_error'] is None, 'Incomplete or failed report')
    require(report['qualification_eligible'] is False and report['reserved_final_seeds_used'] is reserved,
            'Report seed-purpose/qualification flags disagree')
    for key in ('players', 'start', 'deals', 'seed', 'opponent', 'opponent_sha256'):
        require(same(config[key], expected[key]), 'Wrong shard configuration: '+key)
    settings = identity['settings']
    arm = 'opponent-auction-v1' if identity['backend'] == 'opponent-auction-v1' else settings['arm']
    require(same(config['identity'], identity), 'Wrong full policy identity')
    require(config['arm'] == arm and config['model_sha256'] == identity['modelSha256']
            and same(config['samples'], settings['samples']) and same(config['search_workers'], settings['workers']),
            'Selected policy settings changed')
    n = expected['players']; episodes = set(range(expected['start']*4*n, (expected['start']+expected['deals'])*4*n))
    records = report['results']
    require(report['completed_games'] == report['expected_games'] == len(records) == len(episodes)
            and {r['episode'] for r in records} == episodes, 'Missing/duplicate episodes')
    require(report['game_caps'] == report['rollout_caps'] == 0, 'Capped report')
    finite(report['seconds'])
    totals = Counter(); terminals = []; hashes = {'evaluation.json': digest(directory/'evaluation.json')}
    verify = verify_auction if arm == 'opponent-auction-v1' else verify_population
    for record in records:
        episode = record['episode']; terminal = audit_terminal(record, expected); terminals.append(terminal)
        require(same(read(directory/f'game-{episode}.json'), record), 'Separate game receipt differs')
        require(same(record['public_runtime_identity'], identity), 'Game used another policy')
        receipt = directory/f'decisions-{episode}.jsonl'
        require(digest(receipt) == record['decision_receipt_sha256'], 'Changed decision receipts')
        hashes[receipt.name] = digest(receipt); hashes[f'game-{episode}.json'] = digest(directory/f'game-{episode}.json')
        counts = Counter(); moves = Counter(); elapsed = 0.; previous_round = 0
        with receipt.open() as stream:
            for ordinal, line in enumerate(stream, 1):
                row = json.loads(line)
                audit_public_decision(row, identity, episode, terminal['seat'], ordinal)
                integer(row['round'], 1)
                require(previous_round <= row['round'] <= terminal['final']['round'], 'Out-of-order round')
                previous_round = row['round']
                counts.update(verify(row, {**config, 'sealed': terminal['sealed']}, terminal['seat']))
                moves[row['move']['name']] += 1; elapsed += row['elapsedMs']
        for key in ('decisions', 'root_filter_overrides', 'rollouts', 'rollout_caps', 'neural_decisions', 'search_changes'):
            integer(record[key])
            require(record[key] == counts[key], 'Wrong saved counter: '+key)
        require(terminal['policyMoves'] == dict(moves), 'Move conservation failed')
        finite(record['seconds']); require(elapsed <= record['seconds']*1000+1, 'Impossible game timing')
        totals.update(counts)
    validate_pairs(terminals, n)
    return {'audit_version': 1, 'all_receipts_verified': True, 'identity': identity, 'expected': expected,
            'counts': dict(totals), 'terminals': terminals, 'input_hashes': hashes,
            'reserved_final_seeds_used': reserved, 'qualification_eligible': False}


def assess_final_games(audited, identity):
    """Strength gate only. Raw audits must be produced by audit_shard above."""
    validate_identity(identity)
    planned = {s['name']: s for s in schedule()}
    seen = set(); groups = {}; counts = {}
    for shard in audited:
        require(shard['audit_version'] == 1 and shard['all_receipts_verified'] is True
                and shard['reserved_final_seeds_used'] is True and shard['qualification_eligible'] is False,
                'Missing reserved raw-receipt audit')
        require(same(shard['identity'], identity), 'Mixed final policies')
        expected = shard['expected']; name = expected['name']
        require(name not in seen and expected == planned.get(name), 'Duplicate or unexpected final shard')
        seen.add(name)
        groups.setdefault(expected['group'], []).extend(shard['terminals'])
        counts.setdefault(expected['group'], Counter()).update(shard['counts'])
    require(seen == set(planned), 'Missing final shards')
    errors = []; evaluations = {}; p = protocol()
    for opponent in p['opponents']:
        for count, spec in opponent['counts'].items():
            n = int(count); key = f"{opponent['name']}/{n}p"
            # A fixed bootstrap RNG must see a fixed deal order regardless of
            # asynchronous shard completion or receipt presentation order.
            rows = sorted(groups[key], key=lambda row: row['episode'])
            validate_pairs(rows, n)
            require(len(rows) == spec['games'] and {r['episode'] for r in rows} == set(range(spec['games'])), 'Missing exact final episodes')
            require({r['gameSeed'] for r in rows} == {f"{p['seed_prefix']}-{n}p-{i}" for i in range(spec['games']//(4*n))}, 'Wrong exact final deal set')
            summary = win_summary(rows)
            if summary['win_rate'] < spec['minimum_win_rate']:
                errors.append(key+': minimum win rate failed')
            interval = summary['seed_bootstrap_95_interval']
            if interval is None or interval[0] <= 1/n:
                errors.append(key+': overall lower bound does not exceed chance')
            by_rules = {}
            for variant in ('original', 'recharged'):
                for sealed in (False, True):
                    label = variant+('/sealed' if sealed else '/open')
                    group = win_summary([r for r in rows if r['variant'] == variant and r['sealed'] is sealed])
                    by_rules[label] = group
                    if group['seed_bootstrap_95_interval'] is None or group['seed_bootstrap_95_interval'][0] <= 1/n:
                        errors.append(key+'/'+label+': lower bound does not exceed chance')
            require(counts[key]['rollout_caps'] == 0, 'Capped candidate continuations')
            if identity['settings']['arm'] not in ('model', 'filter'):
                require(counts[key]['search_decisions'] > 0 and counts[key]['rollouts'] > 0, 'Selected candidate search never executed')
            evaluations[key] = {'overall': summary, 'by_rules': by_rules, 'candidate_counts': dict(counts[key])}
    return {'strength_passed': not errors, 'errors': errors, 'evaluations': evaluations,
            'games': sum(len(rows) for rows in groups.values()), 'shards': len(seen),
            'identity': identity, 'protocol_sha256': PROTOCOL_SHA,
            'qualified': False, 'qualification_eligible': False,
            'remaining_qualification_requirements': ['frozen candidate/launch admission',
                'checkpoint/export parity for all 2553 fixtures',
                'same complete policy on actual AMD 8840U across all counts',
                'standalone extracted-package verification'],
            'scope': 'Read-only complete raw-game strength gate; never sufficient alone for candidate qualification.'}
