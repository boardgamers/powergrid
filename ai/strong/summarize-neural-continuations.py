"""Verify completed neural-continuation shards and compare matched teacher samples."""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path

MODEL_SHA = 'd3d2ee88a0940f079a4b38879c8154dbab55951abc7b295a7db17bdf22e52c5f'
FIXTURE_SHA = '855b34ad7f07665dfcb012a673147f0780820a9e7560fda268a9a39478c60ff4'


def winner_set(outcomes):
    values = {k: sum(v[:48]) for k, v in outcomes.items()}
    return {int(k) for k, v in values.items() if v == max(values.values())}


def summarize(neural_dir, control_dir, counts):
    neural, controls = defaultdict(dict), defaultdict(dict)
    artifacts, timings = {}, {}
    for n in counts:
        path = neural_dir / f'results-{n}p.jsonl'
        manifest = json.loads(path.with_suffix('.manifest.json').read_text())
        sha = hashlib.sha256(path.read_bytes()).hexdigest()
        assert sha == manifest['output_sha256']
        assert manifest['fixture_sha256'] == FIXTURE_SHA and manifest['model_sha256'] == MODEL_SHA
        assert manifest['players'] == n and manifest['positions'] == 12 and manifest['searches'] == 24
        assert manifest['samples'] == 48 and manifest['max_steps'] == 2400
        assert manifest['truncated'] == 0, 'Capped continuations require an explicit audit, not ranking'
        rows = [json.loads(line) for line in path.read_text().splitlines()]
        assert len(rows) == 24
        evaluations = 0
        for row in rows:
            key, batch = row['fixtureIndex'], row['batch']
            assert row['cell'][0] == n and batch in ['a', 'b'] and batch not in neural[key]
            assert row['continuation'] == 'neural' and row['samples'] == 48
            result = row['result']
            assert result['truncated'] == 0
            assert result['evaluations'] == len(result['sampleOutcomes']) * 48
            for k, v in result['sampleOutcomes'].items():
                assert len(v) == 48 and all(x is not None and 0 <= x <= 1 for x in v)
                assert sum(v) == result['values'][k]
            assert set(result['winnerSet']) == winner_set(result['sampleOutcomes'])
            evaluations += result['evaluations']
            neural[key][batch] = row
        assert evaluations == manifest['evaluations']
        old_path = control_dir / f'results-{n}p.jsonl'
        old_manifest = json.loads((control_dir / f'manifest-{n}p.json').read_text())
        assert hashlib.sha256(old_path.read_bytes()).hexdigest() == old_manifest['output_sha256']
        assert old_manifest['fixture_sha256'] == FIXTURE_SHA and old_manifest['truncated'] == 0
        for row in [json.loads(line) for line in old_path.read_text().splitlines()]:
            key = row['fixtureIndex']
            policy_key = row['continuation'], row['batch']
            assert policy_key not in controls[key]
            controls[key][policy_key] = row
        artifacts[str(n)] = sha
        timings[str(n)] = {k: manifest[k] for k in ['engine_seconds', 'policy_seconds', 'evaluations']}
    assert len(neural) == 12 * len(counts) and set(neural) == set(controls)
    expected = {(n, v, s, a) for n in counts for v in ['original', 'recharged'] for s in [False, True]
                for a in ['ChoosePowerPlant', 'Bid', 'Build']}
    assert {tuple(v['a']['cell']) for v in neural.values()} == expected
    details = []
    for key, runs in sorted(neural.items()):
        assert set(runs) == {'a', 'b'}
        a, b = runs['a'], runs['b']
        assert a['cell'] == b['cell'] and a['root_model_proposal'] == b['root_model_proposal']
        options = list(a['result']['sampleOutcomes'])
        assert set(options) == set(b['result']['sampleOutcomes'])
        for policy in ['mixed', 'economic', 'heuristic']:
            for batch in ['a', 'b']:
                old = controls[key][policy, batch]
                assert old['cell'] == a['cell']
                assert set(old['result']['sampleOutcomes']) == set(options)
        aw, bw = [set(r['result']['winnerSet']) for r in [a, b]]
        cw = winner_set(controls[key]['mixed', 'a']['result']['sampleOutcomes'])
        proposal = a['root_model_proposal']

        def select(winners):
            # Fixed discovery-only tie handling: retain the incumbent when tied,
            # otherwise preserve the reference shortlist order. Never peek at B.
            return proposal if proposal in winners else next(int(i) for i in options if int(i) in winners)

        learned, mixed = select(aw), select(cw)
        confirmations = {}
        for policy in ['neural', 'mixed', 'economic', 'heuristic']:
            result = b['result'] if policy == 'neural' else controls[key][policy, 'b']['result']
            xs = result['sampleOutcomes']
            confirmations[policy] = sum(x-y for x, y in zip(xs[str(learned)][:48], xs[str(mixed)][:48])) / 48
        details.append({'fixtureIndex': key, 'cell': a['cell'],
                        'disjoint_neural_winner_sets': not bool(aw & bw),
                        'same_unique_neural_winner': len(aw) == len(bw) == 1 and aw == bw,
                        'all_neural_actions_tied_a': len(aw) == len(options),
                        'root_proposal_in_shortlist': proposal in {int(i) for i in options},
                        'neural_a_choice': learned, 'mixed_a_choice': mixed,
                        'confirmation_gap_neural_choice_minus_mixed_choice': confirmations})
    groups = defaultdict(list)
    for row in details:
        n, variant, sealed, action = row['cell']
        rule = f'{variant}/{"sealed" if sealed else "open"}'
        for k in ['overall', f'players/{n}', f'action/{action}', f'rules/{rule}',
                  f'players/{n}/rules/{rule}', f'players/{n}/action/{action}']:
            groups[k].append(row)
    aggregate = {}
    for key, rows in groups.items():
        aggregate[key] = {'positions': len(rows), **{metric: sum(r[metric] for r in rows) for metric in [
            'disjoint_neural_winner_sets', 'same_unique_neural_winner', 'all_neural_actions_tied_a',
            'root_proposal_in_shortlist']},
            'different_discovery_choices': sum(r['neural_a_choice'] != r['mixed_a_choice'] for r in rows),
            'confirmation': {policy: {
                'mean_gap': sum(r['confirmation_gap_neural_choice_minus_mixed_choice'][policy] for r in rows)/len(rows),
                'positive_positions': sum(r['confirmation_gap_neural_choice_minus_mixed_choice'][policy] > 0 for r in rows),
                'negative_positions': sum(r['confirmation_gap_neural_choice_minus_mixed_choice'][policy] < 0 for r in rows),
            } for policy in ['neural', 'mixed', 'economic', 'heuristic']}}
    return {'groups': aggregate, 'positions': details, 'artifact_sha256': artifacts, 'timing': timings,
            'limitations': 'Reused development fixtures, descriptive only. Better target stability or continuation return is not proof of actual playing strength. Continuation-policy preferences may reverse.'}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('neural_dir', type=Path)
    p.add_argument('control_dir', type=Path)
    p.add_argument('--players', type=int, choices=range(2, 7), nargs='+', default=[2, 3, 4, 5, 6])
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    assert len(set(args.players)) == len(args.players)
    result = summarize(args.neural_dir, args.control_dir, args.players)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result['groups'], indent=2))
