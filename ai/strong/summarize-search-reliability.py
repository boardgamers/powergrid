"""Describe teacher ranking stability using independent search repetitions."""
import argparse
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path


def summarize(path):
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    assert len(rows) == 60 and len({r['fixtureIndex'] for r in rows}) == 60
    expected = {(n, variant, sealed, action) for n in range(2, 7)
                for variant in ['original', 'recharged'] for sealed in [False, True]
                for action in ['ChoosePowerPlant', 'Bid', 'Build']}
    assert {tuple(r['cell']) for r in rows} == expected
    details = []
    for row in rows:
        a, b = row['batches']
        assert [a['batch'], b['batch']] == ['a', 'b']
        assert set(a['sampleOutcomes']) == set(b['sampleOutcomes'])
        for batch in [a, b]:
            assert batch['truncated'] == 0, 'Capped search cannot establish target reliability'
            assert len(batch['sampleOutcomes']) * 48 == batch['evaluations']
            for k, v in batch['sampleOutcomes'].items():
                assert len(v) == 48 and all(x is not None and 0 <= x <= 1 for x in v)
                assert sum(v) == batch['values'][k]
        winner = str(a['index'])
        alternatives = [k for k in a['values'] if k != winner]
        assert alternatives
        # Rival selected using only discovery batch A; evaluate its gap on fresh B.
        rival = max(alternatives, key=lambda k: (a['values'][k], -int(k)))
        diffs = [x - y for x, y in zip(b['sampleOutcomes'][winner], b['sampleOutcomes'][rival])]
        gap = sum(diffs) / len(diffs)
        policy_disagreements = []
        for batch in [a, b]:
            policy_winners = []
            for parity in [0, 1]:
                totals = {k: sum(v[parity::2]) for k, v in batch['sampleOutcomes'].items()}
                high = max(totals.values())
                policy_winners.append({k for k, v in totals.items() if v == high})
            policy_disagreements.append(not bool(policy_winners[0] & policy_winners[1]))
        details.append({
            'fixtureIndex': row['fixtureIndex'], 'cell': row['cell'], 'round': row['round'],
            'same_selected_action': a['index'] == b['index'],
            'a_winner_is_b_co_winner': b['values'][winner] == max(b['values'].values()),
            'a_all_actions_tied': len(set(a['values'].values())) == 1,
            'b_all_actions_tied': len(set(b['values'].values())) == 1,
            'a_winner': int(winner), 'a_runner_up': int(rival),
            'discovery_gap': (a['values'][winner] - a['values'][rival]) / 48,
            'confirmation_gap': gap,
            # One-sided Hoeffding bound for independent bounded differences [-1,1].
            # Marginal per-position diagnostic, not simultaneous or a strength gate.
            'confirmation_95_hoeffding_lower': gap - math.sqrt(2 * math.log(20) / 48),
            'disjoint_continuation_policy_winner_sets': sum(policy_disagreements),
        })
    groups = defaultdict(list)
    for r in details:
        n, variant, sealed, action = r['cell']
        for key in ['overall', f'players/{n}', f'rules/{variant}/{"sealed" if sealed else "open"}', f'action/{action}']:
            groups[key].append(r)
    def aggregate(group):
        return {'positions': len(group),
                **{k: sum(r[k] for r in group) for k in [
                    'same_selected_action', 'a_winner_is_b_co_winner', 'a_all_actions_tied',
                    'b_all_actions_tied', 'disjoint_continuation_policy_winner_sets']},
                'positive_discovery_gap': sum(r['discovery_gap'] > 0 for r in group),
                'positive_confirmation_gap': sum(r['confirmation_gap'] > 0 for r in group),
                'negative_confirmation_gap': sum(r['confirmation_gap'] < 0 for r in group),
                'positive_confirmation_hoeffding_lower': sum(r['confirmation_95_hoeffding_lower'] > 0 for r in group)}
    return {'input_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'groups': {k: aggregate(v) for k, v in groups.items()}, 'positions': details,
            'limitations': 'One reused development position per cell; no game-strength inference. Policy-subset comparisons also vary sampled scenarios. Confirmation rival fixed using batch A; bounds marginal, not simultaneous.'}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('results', type=Path)
    p.add_argument('--output', required=True, type=Path)
    a = p.parse_args()
    result = summarize(a.results)
    a.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result['groups'], indent=2))
