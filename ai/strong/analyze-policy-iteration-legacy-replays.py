"""Describe policy divergences and final-round decisions in exact diagnostic replays.

The preload records learner moves; legacy bot moves call an internal function
and are not traced. Do not present these observations as a complete cash ledger.
"""
import argparse
from collections import Counter
import json
from pathlib import Path

from strategic_collection import ROOT, read, write, digest


def player(state, seat):
    p = state['players'][seat]
    return {**p, 'cities': len(p['cities'])}


def describe(trace, expected):
    seat = expected['seat']
    assert trace and all(row['seat'] == seat for row in trace)
    assert len(trace) == sum(expected['policyMoves'].values())
    actual_counts = Counter(row['action']['name'] for row in trace)
    assert dict(actual_counts) == expected['policyMoves']
    rounds = {}
    for row in trace:
        before, after = row['before'], row['after']
        view = rounds.setdefault(str(before['round']), {}).setdefault(before['phase'], {
            'first_observed': player(before, seat), 'actions': []})
        view['last_observed_after'] = player(after, seat)
        view['actions'].append(row['action'])
    last = str(expected['final']['round'])
    return {'learner_moves': len(trace), 'root_game_steps': expected['steps'],
            'legacy_actions_recorded': False, 'rounds': rounds, 'final_round': rounds.get(last),
            'terminal': expected['final']['players'][seat], 'win_credit': expected['win']}


def main(directory, output):
    assert not output.exists()
    assessment = read(directory/'assessment.json')
    assert assessment['all_terminal_replays_match'] and not assessment['reserved_final_seeds_used']
    assert digest(directory/'selection.json') == assessment['selection_sha256']
    assert digest(directory/'replays.json') == assessment['results_sha256']
    selection, replays = read(directory/'selection.json'), read(directory/'replays.json')
    assert digest(ROOT/'ai/strong/trace-public-game.cjs') == selection['trace_script_sha256']
    assert digest(ROOT/'ai/strong/replay-policy-iteration-legacy-diagnosis.py') == selection['replay_script_sha256']
    traces, games = {}, {}
    for name, request in selection['requested'].items():
        path = directory/(name+'.jsonl')
        assert digest(path) == replays[name]['trace_sha256'] and replays[name]['exact_terminal_replay']
        traces[name] = [json.loads(line) for line in path.open()]
        games[name] = describe(traces[name], request['expected'])
    comparisons, counts = [], {}
    for pair in selection['pairs']:
        candidate_name, parent_name = pair['cases'][pair['model']], pair['cases']['parent']
        candidate, parent = traces[candidate_name], traces[parent_name]
        first = None
        for index, (a, b) in enumerate(zip(candidate, parent)):
            if a != b:
                first = {'learner_move_index': index, 'same_observed_state': a['before'] == b['before'],
                         'candidate_phase': a['before']['phase'], 'parent_phase': b['before']['phase'],
                         'candidate_round': a['before']['round'], 'parent_round': b['before']['round'],
                         'candidate_action': a['action'], 'parent_action': b['action'],
                         'candidate_before': a['before'], 'parent_before': b['before']}
                break
        assert first and first['same_observed_state'], 'Investigate a divergence before the first different learner action'
        assert first['candidate_action'] != first['parent_action']
        counts.setdefault(pair['model'], {}).setdefault(pair['direction'], Counter())[first['candidate_phase']] += 1
        comparisons.append({**pair, 'first_divergence': first,
                            'candidate_final_round': games[candidate_name]['final_round'],
                            'parent_final_round': games[parent_name]['final_round']})
    write(output, {'assessment_sha256': digest(directory/'assessment.json'),
        'selection_sha256': digest(directory/'selection.json'), 'source': assessment['source'],
        'exact_replays': assessment['exact_replays'], 'pairs': comparisons, 'games': games,
        'first_divergence_counts': counts, 'new_strength_games': 0, 'candidate_selected': False,
        'qualification_eligible': False, 'reserved_final_seeds_used': False,
        'analysis_code_sha256': digest(Path(__file__)),
        'scope': 'Outcome-selected examples from reused five-player legacy development games. '
            'All terminal outputs exactly replay. First different learner choices share the same '
            'observed state, but this does not attribute the final result to that one choice. '
            'Only learner moves are traced; observations between them include opponent effects. '
            'Phase snapshots are not a complete cash ledger, and these selected examples provide '
            'neither phase-ablation evidence nor a strength estimate.'})
    print({'exact_replays': assessment['exact_replays'], 'pairs': len(comparisons),
           'first_divergence_counts': counts})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    main(args.directory.resolve(), args.output.resolve())
