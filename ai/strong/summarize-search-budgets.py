"""Audit nested search budgets and continuation policies on matching scenarios."""
import argparse
from collections import defaultdict
import hashlib
import itertools
import json
from pathlib import Path


def summarize(directory, original):
    old_rows = [json.loads(line) for line in original.read_text().splitlines()]
    old = {r['fixtureIndex']: r for r in old_rows}
    assert len(old) == len(old_rows) == 60
    grouped = defaultdict(dict)
    evaluations = 0
    artifacts = {}
    for n in range(2, 7):
        path = directory / f'results-{n}p.jsonl'
        manifest = json.loads((directory / f'manifest-{n}p.json').read_text())
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        assert digest == manifest['output_sha256']
        assert manifest['players'] == n and manifest['positions'] == 12
        assert manifest['samples'] == 384 and manifest['search_max_steps'] == 2400
        assert manifest['fixture_sha256'] == '855b34ad7f07665dfcb012a673147f0780820a9e7560fda268a9a39478c60ff4'
        rows = [json.loads(line) for line in path.read_text().splitlines()]
        assert len(rows) == manifest['searches'] == 72
        assert manifest['truncated'] == 0, 'Incomplete continuations require a separate cap audit'
        count = 0
        for row in rows:
            i, policy, batch = row['fixtureIndex'], row['continuation'], row['batch']
            assert row['cell'] == old[i]['cell'] and row['cell'][0] == n
            assert row['samples'] == 384 and (policy, batch) not in grouped[i]
            result = row['result']
            assert result['truncated'] == 0
            assert result['evaluations'] == len(result['sampleOutcomes']) * 384
            for k, v in result['sampleOutcomes'].items():
                assert len(v) == 384 and all(x is not None and 0 <= x <= 1 for x in v)
                assert sum(v) == result['values'][k]
            assert result['values'][str(result['index'])] == max(result['values'].values())
            grouped[i][policy, batch] = result
            count += result['evaluations']
        assert count == manifest['evaluations']
        evaluations += count
        artifacts[str(n)] = digest
    expected = set(itertools.product(['mixed', 'economic', 'heuristic'], ['a', 'b']))
    assert set(grouped) == set(old)
    for i, runs in grouped.items():
        assert set(runs) == expected
        keys = set(runs['mixed', 'a']['sampleOutcomes'])
        assert all(set(r['sampleOutcomes']) == keys for r in runs.values())
        for batch in ['a', 'b']:
            mixed = runs['mixed', batch]['sampleOutcomes']
            original_batch = next(b for b in old[i]['batches'] if b['batch'] == batch)
            assert set(original_batch['sampleOutcomes']) == keys
            for k, v in mixed.items():
                assert v[:48] == original_batch['sampleOutcomes'][k], 'Nested prefix changed'
                assert v[::2] == runs['economic', batch]['sampleOutcomes'][k][::2]
                assert v[1::2] == runs['heuristic', batch]['sampleOutcomes'][k][1::2]

    def winners(result, budget):
        totals = {k: sum(v[:budget]) for k, v in result['sampleOutcomes'].items()}
        return {k for k, v in totals.items() if v == max(totals.values())}

    details = []
    for i, runs in sorted(grouped.items()):
        budgets = {}
        for policy, budget in itertools.product(['mixed', 'economic', 'heuristic'], [48, 96, 192, 384]):
            a, b = [winners(runs[policy, batch], budget) for batch in ['a', 'b']]
            budgets[f'{policy}/{budget}'] = {
                'disjoint_winner_sets': not bool(a & b),
                'same_unique_winner': len(a) == len(b) == 1 and a == b,
                'all_actions_tied_a': len(a) == len(runs[policy, 'a']['values']),
                'all_actions_tied_b': len(b) == len(runs[policy, 'b']['values']),
            }
        # Select both moves in A, then compare their expected rewards in fresh B.
        econ_choice = str(runs['economic', 'a']['index'])
        heuristic_choice = str(runs['heuristic', 'a']['index'])
        gaps = {policy: (runs[policy, 'b']['values'][econ_choice] -
                         runs[policy, 'b']['values'][heuristic_choice]) / 384
                for policy in ['economic', 'heuristic']}
        details.append({'fixtureIndex': i, 'cell': old[i]['cell'], 'budgets': budgets,
                        'economic_a_choice': int(econ_choice), 'heuristic_a_choice': int(heuristic_choice),
                        'confirmation_gaps_economic_minus_heuristic_choice': gaps,
                        'opposite_preferences_in_confirmation': gaps['economic'] > 0 and gaps['heuristic'] < 0,
                        'mixed_384_same_selected_action': runs['mixed', 'a']['index'] == runs['mixed', 'b']['index']})
    groups = defaultdict(list)
    for row in details:
        n, variant, sealed, action = row['cell']
        for key in ['overall', f'players/{n}', f'action/{action}',
                    f'rules/{variant}/{"sealed" if sealed else "open"}']:
            groups[key].append(row)
    summaries = {}
    for key, group in groups.items():
        summaries[key] = {'positions': len(group),
            'mixed_384_same_selected_action': sum(r['mixed_384_same_selected_action'] for r in group),
            'opposite_preferences_in_confirmation': sum(r['opposite_preferences_in_confirmation'] for r in group),
            'budgets': {name: {metric: sum(r['budgets'][name][metric] for r in group)
                              for metric in group[0]['budgets'][name]}
                        for name in group[0]['budgets']}}
    return {'evaluations': evaluations, 'truncated': 0, 'positions': details, 'groups': summaries,
            'artifact_sha256': artifacts, 'nested_prefix_and_policy_samples_match': True,
            'limitations': 'One reused development position per cell. Descriptive diagnostics, not proof of playing strength. Opposite continuation preferences do not identify which policy is realistic.'}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('directory', type=Path)
    p.add_argument('original', type=Path)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    result = summarize(args.directory, args.original)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result['groups']['overall'], indent=2))
