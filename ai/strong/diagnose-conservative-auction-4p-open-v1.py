"""Post-hoc description of all saved pairs in the adverse 4p/open cell.

No simulations, inference, tuning, training or job APIs. Reconcile the complete
audited comparison and hash-check every original receipt read. Associations in
these eight deals cannot identify a causal bad action or prove a recurring flaw.
"""
from collections import Counter
from datetime import datetime, timezone
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import statistics

ROOT = Path(__file__).resolve().parents[2]
COMPARISON = ROOT / 'ai/strong/conservative-auction-development-comparison-with-attempts-v1.json'
COMPARISON_SHA = '2d2e469a073e3cd71a919da6a137042cfb5fd2ea14d6fb0491997d06eee77e37'
RAW = ROOT / 'ai/runs/conservative-auction-development-hf-v2'
OUTPUT = ROOT / 'ai/strong/conservative-auction-4p-open-diagnostic-v1.json'
SPENDING = ('totalSpentPlants', 'totalSpentResources', 'totalSpentCities', 'totalSpentConnections')


def digest(path):
    with Path(path).open('rb') as stream: return hashlib.file_digest(stream, 'sha256').hexdigest()


def read(path): return json.loads(Path(path).read_text())


def checked(path, sha):
    assert digest(path) == sha, 'Changed archived input: ' + str(path)
    return path


def receipt(path, record):
    decisions = []; override_counts = Counter(); margins = []; observed = None
    for line in path.open():
        row = json.loads(line); q = row['publicRequest']; state = q['state']; player = q['player']
        own = state['players'][player]; assert own['id'] == player
        assert row['decision'] == len(decisions) + 1
        assert row['move'] == row['arenaMoves'][row['index']] == row['publicResponse']['move']
        changed = row['index'] != row['modelProposal'] and not row['filterApplied']
        if changed:
            assert row['phase'] == 'auction' and row['search']['truncated'] == 0
            selection = row['search']['selection']
            assert selection['selected'] == row['index'] and selection['baseline'] == row['modelProposal']
            margin = Fraction(selection['pairedMeanMargins'][str(row['index'])])
            assert margin > Fraction(1, 8)
            margins.append(margin)
            override_counts[row['arenaMoves'][row['modelProposal']]['name'] + ' -> ' + row['move']['name']] += 1
        decisions.append({'decision': row['decision'], 'round': row['round'], 'phase': row['phase'],
            'request': q, 'move': row['move'], 'model_move': row['arenaMoves'][row['modelProposal']],
            'is_search_override': changed})
        observed = {'last_request_round': row['round'], 'last_request_phase': row['phase'],
                    'last_move': row['move'], 'cities': len(own['cities']),
                    'money_before_last_move': own['money'], **{k: own[k] for k in SPENDING}}
    assert len(decisions) == record['decisions']
    assert sum(override_counts.values()) == record['search_changes']
    return decisions, {'search_overrides': sum(override_counts.values()),
        'override_types': dict(override_counts), 'override_margins': dict(Counter(str(v) for v in margins)),
        'last_observed_learner': observed}


def first_divergence(left, right):
    for a, b in zip(left, right):
        if a['request'] != b['request']:
            return {'kind': 'different_public_input_before_different_move',
                    'filter_decision': a['decision'], 'search_decision': b['decision']}
        if a['move'] != b['move']:
            state = b['request']['state']; own = state['players'][b['request']['player']]
            assert b['is_search_override'] and b['model_move'] == a['move']
            return {'kind': 'same_input_search_override', 'decision': a['decision'],
                'round': a['round'], 'phase': a['phase'], 'filter_move': a['move'], 'search_move': b['move'],
                'money': own['money'], 'cities': len(own['cities']),
                'public_state_sha256': hashlib.sha256(json.dumps(state, sort_keys=True).encode()).hexdigest()}
    return {'kind': 'identical_recorded_moves' if len(left) == len(right) else 'different_recorded_lengths',
            'filter_decisions': len(left), 'search_decisions': len(right)}


def main():
    assert not OUTPUT.exists(), 'Inspect original diagnostic instead of overwriting it'
    comparison = read(checked(COMPARISON, COMPARISON_SHA)); pairs = {}; inputs = {}; archives = {}
    for arm, short in (('filter', 'filter'), ('conservative_population', 'pop')):
        for deal in range(8):
            name = f'pg-conservative-dev-v2-{short}-search_geo-4p-{deal:02d}'
            provenance = comparison['provenance'][name]; folder = RAW / name / 'artifacts/job/evaluation'
            archives[name] = provenance['evidence']
            evaluation = checked(folder / 'evaluation.json', provenance['raw_input_hashes']['evaluation.json'])
            inputs[str(evaluation.relative_to(ROOT))] = digest(evaluation)
            data = read(evaluation); assert data['passed'] and data['all_complete'] and not data['errors']
            selected = [r for r in data['results'] if r['episode'] % 4 == 2]
            assert len(selected) == 4
            for record in selected:
                ep = record['episode']; t = record['terminal']; seat = t['seat']
                assert ep // 16 == deal and ep // 4 % 4 == seat
                assert t['variant'] == 'original' and t['sealed'] is False and t['playerCount'] == 4
                assert not t['truncated'] and record['rollout_caps'] == 0
                assert t['gameSeed'] == f'conservative-auction-development-v1-4p-{deal}'
                assert record['public_runtime_identity'] == comparison['identities'][arm]
                trace = folder / f'decisions-{ep}.jsonl'; expected = provenance['raw_input_hashes'][trace.name]
                assert record['decision_receipt_sha256'] == expected
                checked(trace, expected); inputs[str(trace.relative_to(ROOT))] = expected
                decisions, diagnostic = receipt(trace, record)
                scores = [tuple(p[k] for k in ('powered', 'money', 'cities')) for p in t['final']['players']]
                credit = Fraction(int(scores[seat] == max(scores)), scores.count(max(scores)))
                assert float(credit) == t['win']
                pairs.setdefault(ep, {})[arm] = {'credit': str(credit), 'final': t['final'],
                    'learner_final': t['final']['players'][seat], 'trace': decisions, **diagnostic}
    assert len(pairs) == 32 and set(pairs) == set(range(2, 128, 4))
    records = []; outcomes = Counter(); per_deal = [Fraction() for _ in range(8)]
    for ep, pair in sorted(pairs.items()):
        a, b = pair['filter'], pair['conservative_population']
        delta = Fraction(b['credit']) - Fraction(a['credit']); per_deal[ep // 16] += delta
        group = 'improved' if delta > 0 else 'regressed' if delta < 0 else 'unchanged'
        outcomes[group] += 1
        divergence = first_divergence(a.pop('trace'), b.pop('trace'))
        records.append({'episode': ep, 'deal': ep // 16, 'seat': ep // 4 % 4, 'group': group,
            'credit_difference': str(delta), 'first_divergence': divergence, 'arms': pair,
            'search_minus_filter_spending': {k: b['last_observed_learner'][k] - a['last_observed_learner'][k] for k in SPENDING},
            'search_minus_filter_final': {k: b['learner_final'][k] - a['learner_final'][k] for k in ('cities','powered','money','capacity')},
            'search_minus_filter_rounds': b['final']['round'] - a['final']['round']})
    totals = {a: sum((Fraction(r['arms'][a]['credit']) for r in records), Fraction()) for a in ('filter','conservative_population')}
    for arm, total in totals.items():
        expected = comparison['absolute'][arm]['search_geo/4p']['original/open']['win_credit']['exact_mean']
        assert total / 32 == Fraction(expected)
    expected_difference = comparison['contrasts']['conservative_population_minus_filter']['search_geo/4p']['original/open']['win_credit_difference']
    assert sum(per_deal, Fraction()) / 32 == Fraction(expected_difference['exact_mean'])
    groups = {}
    for group in ('regressed', 'improved', 'unchanged'):
        rows = [r for r in records if r['group'] == group]
        groups[group] = {'pairs': len(rows),
            'first_divergence_kinds': dict(Counter(r['first_divergence']['kind'] for r in rows)),
            'mean_spending_differences': {k: statistics.mean(r['search_minus_filter_spending'][k] for r in rows) for k in SPENDING},
            'mean_final_differences': {k: statistics.mean(r['search_minus_filter_final'][k] for r in rows) for k in ('cities','powered','money','capacity')},
            'mean_round_difference': statistics.mean(r['search_minus_filter_rounds'] for r in rows),
            'mean_search_overrides': statistics.mean(r['arms']['conservative_population']['search_overrides'] for r in rows)}
    assert all(digest(ROOT / p) == sha for p, sha in inputs.items())
    result = {'created_at': datetime.now(timezone.utc).isoformat(), 'comparison_sha256': COMPARISON_SHA,
        'analyzer_sha256': digest(__file__), 'scope': 'Post-hoc complete historical search_geo/4p original/open cell; 32 paired games per arm, eight independent deals.',
        'paired_games': 32, 'raw_games': 64, 'independent_deals': 8, 'outcomes': dict(outcomes),
        'win_credits': {a: str(v) for a, v in totals.items()}, 'net_credit_difference': str(sum(per_deal, Fraction())),
        'per_deal_net_credits': [str(v) for v in per_deal], 'existing_paired_comparison': expected_difference,
        'groups': groups, 'records': records, 'input_hashes': inputs, 'raw_archives': archives,
        'interpretation': 'Descriptive, selected after observing the negative cell. Spending and final-score differences combine all downstream consequences and opponent reactions; they do not identify a causal action or prove a systematic defect. Keep the independent confirmation and policy frozen.',
        'new_games': 0, 'new_inference': 0, 'new_hf_jobs': 0, 'new_gradients': 0,
        'policy_changed': False, 'qualification_eligible': False, 'reserved_final_seeds_used': False}
    with OUTPUT.open('x') as stream: json.dump(result, stream, indent=2, allow_nan=False); stream.write('\n')
    print(json.dumps({k: result[k] for k in ('outcomes','win_credits','per_deal_net_credits','groups')}), flush=True)


if __name__ == '__main__': main()
