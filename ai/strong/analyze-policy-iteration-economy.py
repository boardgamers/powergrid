"""Verify complete diagnostic ledgers and describe fuel availability at game end."""
import argparse
from collections import Counter
import json
from pathlib import Path

from strategic_collection import ROOT, read, write, digest

RESOURCES = ['coal', 'oil', 'garbage', 'uranium']


def blocked_plants(player, market):
    result = []
    for plant in player['plants']:
        kind, cost = plant['type'], plant['cost']
        if kind in range(4):
            resource = RESOURCES[kind]
            available = player['resources'][resource]+market[resource]['count']
            if available < cost:
                result.append({'plant': plant['number'], 'resource': resource, 'required': cost,
                               'held': player['resources'][resource], 'market': market[resource]['count']})
        elif kind == 4:
            available = sum(player['resources'][r]+market[r]['count'] for r in ['coal', 'oil'])
            if available < cost:
                result.append({'plant': plant['number'], 'resource': 'coal/oil',
                               'required': cost, 'held_plus_market': available})
    return result


def main(directory, output):
    assert not output.exists()
    assessment = read(directory/'assessment.json')
    assert assessment['all_terminal_replays_match'] and assessment['all_root_moves_logged']
    previous = ROOT/assessment['previous']
    assert digest(previous/'selection.json') == assessment['selection_sha256']
    assert digest(directory/'replays.json') == assessment['results_sha256']
    for name, sha in assessment['code_hashes'].items():
        assert digest(ROOT/name) == sha
    selection, replays = read(previous/'selection.json'), read(directory/'replays.json')
    games = {}
    for name, request in selection['requested'].items():
        expected, seat = request['expected'], request['expected']['seat']
        path = directory/(name+'.jsonl')
        assert digest(path) == replays[name]['trace_sha256']
        trace = [json.loads(line) for line in path.open()]
        assert len(trace) == expected['steps'] == replays[name]['moves_logged']
        assert all(a['after'] == b['before'] for a, b in zip(trace, trace[1:])), 'Incomplete root-state ledger'
        assert Counter(r['action']['name'] for r in trace if not r['legacy']) == expected['policyMoves']
        assert all((not r['legacy']) == (r['seat'] == seat) for r in trace)
        last = trace[-1]['after']
        assert last['phase'] == 'Game End' and last['round'] == expected['final']['round']
        for p, e in zip(last['players'], expected['final']['players']):
            assert {k: p[k] for k in ['money', 'powered', 'capacity']} == {k:e[k] for k in ['money', 'powered', 'capacity']}
            assert len(p['cities']) == e['cities'] and [x['number'] for x in p['plants']] == e['plants']
            assert p['powerable'] == p['powered']
            assert all(isinstance(p['resources'][r], int) and p['resources'][r] >= 0 for r in RESOURCES)
        final_round = last['round']
        resource_rows = [r for r in trace if r['before']['round'] == final_round
                         and r['before']['phase'] == 'Resources' and r['seat'] == seat]
        assert resource_rows and resource_rows[-1]['action']['name'] == 'Pass'
        end_resources = resource_rows[-1]['after']
        p = end_resources['players'][seat]
        threshold_events = [r for r in trace if max(len(q['cities']) for q in r['before']['players'])
                            < r['before']['citiesToEndGame']
                            <= max(len(q['cities']) for q in r['after']['players'])]
        assert len(threshold_events) == 1
        trigger = threshold_events[0]
        me = last['players'][seat]
        games[name] = {'model': request['model'], 'episode': expected['episode'],
            'win_credit': expected['win'], 'final_round': final_round, 'seat': seat,
            'trace_sha256': digest(path), 'all_moves_and_state_transitions_verified': True,
            'final_player': me, 'final_opponents': [q for i,q in enumerate(last['players']) if i != seat],
            'fuel_limited_at_end': min(len(me['cities']), me['capacity']) > me['powered'],
            'last_resource_actions': [r['action'] for r in resource_rows],
            'last_resource_pass_player': p, 'last_resource_pass_market': end_resources['market'],
            'plants_impossible_to_fuel_from_remaining_market': blocked_plants(p, end_resources['market']),
            'end_threshold_trigger': {'seat': trigger['seat'], 'learner': trigger['seat'] == seat,
                'action': trigger['action'], 'threshold': trigger['before']['citiesToEndGame'],
                'players_after': trigger['after']['players']}}
    pair_summary = []
    for pair in selection['pairs']:
        fields = ['win_credit', 'fuel_limited_at_end', 'plants_impossible_to_fuel_from_remaining_market']
        pair_summary.append({**pair, 'details': {arm: {key:games[name][key] for key in fields}
            for arm, name in pair['cases'].items()}})
    write(output, {'exact_replays': len(games), 'pairs': pair_summary, 'games': games,
        'assessment_sha256': digest(directory/'assessment.json'),
        'selection_sha256': assessment['selection_sha256'], 'source': assessment['source'],
        'all_root_moves_and_state_transitions_verified': True, 'analysis_code_sha256': digest(Path(__file__)),
        'new_strength_games': 0, 'gradients': False, 'candidate_selected': False,
        'qualification_eligible': False, 'reserved_final_seeds_used': False,
        'scope': 'Fixed outcome-selected five-player legacy examples. Exact terminal replay and full '
            'public root-ledger continuity verified, including legacy turns. Fuel-supported capacity '
            'uses the frozen engine function. A blocked plant cannot obtain enough fuel from remaining '
            'inventory even ignoring cost and storage; the absence of a blocked plant does not prove '
            'all plants can be fueled simultaneously. No causal intervention, phase attribution, '
            'generalized frequency estimate, fresh strength games or candidate selection.'})
    print({'exact_replays': len(games), 'all_root_moves_and_state_transitions_verified': True})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    main(args.directory.resolve(), args.output.resolve())
