"""Independently aggregate derived events and check whole-turn conservation.

Does not rerun inference or reclassify the immutable original game outcomes.
"""
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / 'ai/runs/resource-plan-consistency-v1'


def read(path):
    return json.loads(path.read_text())


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def game_id(row):
    return row['players'], row['opponent'], row['episode']


assessment = read(RUN / 'assessment.json')
events, stats = defaultdict(dict), defaultdict(Counter)
with (RUN / 'transitions.jsonl').open() as stream:
    for line in stream:
        row = json.loads(line)
        key = game_id(row)
        assert row['decision'] not in events[key]
        events[key][row['decision']] = row
        assert row['decision'] == row['previous_decision'] + 1
        changed = row['expected_remainder'] != row['new_counts']
        assert changed == row['count_change']
        assert not row['order_only_change'] or not changed
        assert all(type(x) is int and x >= 0 for x in row['expected_remainder'] + row['new_counts'])
        assert row['early_pass'] == (sum(row['expected_remainder']) > 0 and sum(row['new_counts']) == 0)
        counts = stats[key]
        counts['transitions'] += 1
        for field in ('count_change', 'next_move_change', 'order_only_change', 'remainder_available',
                      'sampling_seed_changed', 'early_pass'):
            counts[field] += int(row[field])
        gap = row['selected_minus_remainder_credit']
        assert (gap is not None) == row['remainder_available']
        if changed:
            counts['changed_remainder_available'] += int(gap is not None)
            counts['changed_remainder_missing'] += int(gap is None)
            counts['changed_comparable_tied'] += int(gap is not None and abs(gap) < 1e-12)
            counts['changed_comparable_gap_at_most_one_eighth'] += int(gap is not None and gap <= 0.125 + 1e-12)

visited = defaultdict(set)
with (RUN / 'turns.jsonl').open() as stream:
    for line in stream:
        row = json.loads(line)
        key = game_id(row)
        start, end = row['first_decision'], row['last_decision']
        assert row['searches'] == end - start + 1 - int(row['forced_final_pass'])
        current = row['initial_counts']
        actual = [0, 0, 0, 0]
        for decision in range(start + 1, end + 1 - int(row['forced_final_pass'])):
            event = events[key][decision]
            assert event['round'] == row['round'] and decision not in visited[key]
            visited[key].add(decision)
            purchase = [a - b for a, b in zip(current, event['expected_remainder'])]
            assert sum(purchase) == 1 and set(purchase) <= {0, 1}
            actual = [a + b for a, b in zip(actual, purchase)]
            current = event['new_counts']
        if row['forced_final_pass']:
            # Only a final atomic purchase can remain when the next menu has
            # no search. Its still-feasible plan must then consist of Pass.
            assert sum(current) == 1 and set(current) <= {0, 1}
            actual = [a + b for a, b in zip(actual, current)]
        else:
            assert current == [0, 0, 0, 0]
        assert actual == row['executed_counts']
        delta = [a - b for a, b in zip(actual, row['initial_counts'])]
        assert delta == row['count_delta']
        expected = 'exact'
        if any(delta):
            expected = 'mixed' if min(delta) < 0 < max(delta) else 'shortfall' if max(delta) <= 0 else 'excess'
        assert row['category'] == expected
        assert row['initial_nonzero'] == (sum(row['initial_counts']) > 0)
        counts = stats[key]
        counts['turns'] += 1
        counts['search_decisions'] += row['searches']
        counts['initial_nonzero_turns'] += int(row['initial_nonzero'])
        counts['changed_turns'] += int(expected != 'exact')
        counts['turn_' + expected] += 1
        counts['forced_final_pass'] += int(row['forced_final_pass'])
assert all(visited[key] == set(rows) for key, rows in events.items())

total, cells, outcomes = Counter(), defaultdict(Counter), defaultdict(Counter)
games = read(RUN / 'games.json')
for game in games:
    key = game_id(game)
    counter = stats.pop(key)
    counter['games'] = 1
    assert counter == Counter(game['counts'])
    outcome = 'better' if game['win'] > game['control_win'] else 'worse' if game['win'] < game['control_win'] else 'equal'
    assert outcome == game['paired_outcome']
    cell = f"{game['players']}p/{game['opponent']}/{game['variant']}/{'sealed' if game['sealed'] else 'open'}"
    total.update(counter)
    cells[cell].update(counter)
    outcomes[outcome].update(counter)
assert not stats and len(games) == 1680
assert total == Counter(assessment['totals'])
assert len(cells) == 108 and set(cells) == set(assessment['cells'])
assert all(counts == Counter(assessment['cells'][cell]) for cell, counts in cells.items())
assert all(counts == Counter(assessment['paired_outcomes'][name]) for name, counts in outcomes.items())

archive = read(ROOT / 'ai/runs/resource-replanning-development-complete-evidence-v1/manifest.json')
inputs = read(RUN / 'inputs.json')
assert len(inputs) == assessment['input_files_verified'] == 1734
assert all(archive[name] == value for name, value in inputs.items())
assert {str(p.relative_to(ROOT)) for p in (ROOT / 'ai/runs/resource-replanning-development-collected-v1').glob(
    '*/artifacts/evaluation/evaluation.json')} <= set(inputs)

replay = read(RUN / 'replays.json')
assert replay['complete'] and replay['original_games_replayed'] == len(assessment['examples']) == 3
assert replay['assessment_sha256'] == digest(RUN / 'assessment.json')
assert all(result['originalTerminalExact'] for result in replay['results'])
result = {'complete': True, 'all_game_cell_and_outcome_aggregates_recomputed': True,
          'all_transition_count_vectors_conserve_executed_purchases': True,
          'forced_passes_have_no_unfulfilled_immediate_remainder': True,
          'turns': total['turns'], 'transitions': total['transitions'], 'games': len(games),
          'input_archive_hashes_match': len(inputs), 'original_games_replayed': 3,
          'replayed_learner_moves': sum(r['learnerMoves'] for r in replay['results']),
          'replayed_purchase_transitions_without_opponent_moves': sum(r['purchaseTransitions'] for r in replay['results']),
          'original_terminal_outcomes_exact': True, 'new_strength_games': 0,
          'source_sha256': digest(Path(__file__)), 'assessment_sha256': digest(RUN / 'assessment.json'),
          'replays_sha256': digest(RUN / 'replays.json'), 'qualification_eligible': False,
          'scope': 'Independent derived-event conservation and aggregation; original hash-verified receipts and completed-screen verifier supply source integrity. Three deterministic original-game replays validate all legal learner moves, candidate purchases, public inventories and terminal outcomes in those games. No causal benefit or policy improvement established.'}
(RUN / 'independent-audit.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result))
