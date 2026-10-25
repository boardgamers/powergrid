"""Describe within-turn plan changes in the complete, rejected resource screen.

Reads immutable receipts only. No engine, inference, HF jobs or policy selection.
"""
import argparse
from collections import Counter, defaultdict
from fractions import Fraction
import hashlib
import json
from pathlib import Path


RESOURCES = ('coal', 'oil', 'garbage', 'uranium')
PASS = {'name': 'Pass', 'data': True}
ROOT = Path(__file__).resolve().parents[2]
BASE = Path('ai/runs/resource-replanning-development-collected-v1')
MANIFEST = Path('ai/runs/resource-replanning-development-complete-evidence-v1/manifest.json')
DESCRIPTOR = Path('ai/strong/resource-replanning-development-complete-evidence-v1.json')
DESIGN = Path('ai/strong/resource-plan-consistency-design-v1.json')


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def counts(actions):
    assert actions and actions[-1] == PASS
    result = [0] * 4
    for move in actions[:-1]:
        assert move['name'] == 'BuyResource'
        result[RESOURCES.index(move['data']['resource'])] += 1
    return result


def snapshot(plan):
    """The zero-purchase candidate leaves the public inventory/cash untouched."""
    bundles = plan['bundles']
    zero = next(i for i, bundle in enumerate(bundles) if bundle['counts'] == [0] * 4)
    receipt = plan['receipts'][zero]
    assert receipt['sample'] == 0 and receipt['actionIndex'] == zero
    assert receipt['resourceTurn']['counts'] == [0] * 4
    assert receipt['resourceTurn']['cost'] == 0
    return receipt['resourceTurn']['afterPurchases']


def compact(row):
    plan = row['resourcePlan']
    if plan is None:
        return {'decision': row['decision'], 'round': row['round'], 'move': row['move'], 'plan': None}
    assert row['phase'] == 'resources' and row['move'] == plan['firstMove']
    selected = plan['bundles'][plan['selected']]
    assert selected['actions'] == plan['actions'] and selected['counts'] == counts(plan['actions'])
    assert plan['actions'][0] == row['move'] and not plan['search']['truncated']
    assert row['search'] == plan['search']
    return {'decision': row['decision'], 'round': row['round'], 'move': row['move'],
            'plan': {'counts': selected['counts'], 'actions': plan['actions'],
                     'seed': plan['search']['seed'], 'before': snapshot(plan),
                     'means': plan['search']['meanCredits'],
                     'candidate_counts': [bundle['counts'] for bundle in plan['bundles']]}}


def transition(previous, current):
    """Only compare adjacent search requests, before the same buyer passes."""
    assert previous['plan'] is not None and current['plan'] is not None
    assert current['decision'] == previous['decision'] + 1
    assert previous['round'] == current['round']
    assert previous['move']['name'] == 'BuyResource'
    p, q = previous['plan'], current['plan']
    resource = RESOURCES.index(previous['move']['data']['resource'])
    remainder = list(p['counts'])
    remainder[resource] -= 1
    assert min(remainder) >= 0 and counts(p['actions'][1:]) == remainder
    expected_stock = list(p['before']['stock'])
    expected_market = list(p['before']['market'])
    expected_stock[resource] += 1
    expected_market[resource] -= 1
    assert q['before']['stock'] == expected_stock
    assert q['before']['market'] == expected_market
    assert 0 <= q['before']['money'] < p['before']['money']
    remainder_id = ','.join(map(str, remainder))
    selected_id = ','.join(map(str, q['counts']))
    present = remainder in q['candidate_counts']
    assert present == (remainder_id in q['means'])
    gap = None if not present else q['means'][selected_id] - q['means'][remainder_id]
    assert gap is None or gap >= -1e-12
    changed = remainder != q['counts']
    next_changed = p['actions'][1] != current['move']
    return {'previous_decision': previous['decision'], 'decision': current['decision'],
            'round': current['round'], 'expected_remainder': remainder,
            'new_counts': q['counts'], 'count_change': changed,
            'next_move_change': next_changed,
            'order_only_change': not changed and p['actions'][1:] != q['actions'],
            'remainder_available': present, 'sampling_seed_changed': p['seed'] != q['seed'],
            'selected_minus_remainder_credit': gap,
            'early_pass': current['move'] == PASS and sum(remainder) > 0}


def finish_turn(rows):
    assert rows and rows[0]['plan'] is not None and rows[-1]['move'] == PASS
    assert len({r['round'] for r in rows}) == 1
    assert [r['decision'] for r in rows] == list(range(rows[0]['decision'], rows[-1]['decision'] + 1))
    actual = counts([r['move'] for r in rows])
    intended = rows[0]['plan']['counts']
    delta = [a - b for a, b in zip(actual, intended)]
    category = ('exact' if not any(delta) else 'shortfall' if max(delta) <= 0
                else 'excess' if min(delta) >= 0 else 'mixed')
    return {'round': rows[0]['round'], 'first_decision': rows[0]['decision'],
            'last_decision': rows[-1]['decision'], 'initial_counts': intended,
            'executed_counts': actual, 'count_delta': delta, 'category': category,
            'initial_nonzero': sum(intended) > 0, 'searches': sum(r['plan'] is not None for r in rows),
            'forced_final_pass': rows[-1]['plan'] is None}


def terminal_credit(record):
    terminal = record['terminal']
    scores = [tuple(p[k] for k in ('powered', 'money', 'cities')) for p in terminal['final']['players']]
    best = max(scores)
    value = Fraction(1, scores.count(best)) if scores[terminal['seat']] == best else Fraction(0)
    assert float(value) == terminal['win'] == terminal['value'][terminal['seat']]
    return value


def event_counts(event):
    result = Counter(transitions=1)
    for key in ('count_change', 'next_move_change', 'order_only_change', 'remainder_available',
                'sampling_seed_changed', 'early_pass'):
        result[key] = int(event[key])
    if event['count_change']:
        gap = event['selected_minus_remainder_credit']
        result['changed_remainder_missing'] = int(gap is None)
        result['changed_remainder_available'] = int(gap is not None)
        result['changed_comparable_tied'] = int(gap is not None and abs(gap) < 1e-12)
        result['changed_comparable_gap_at_most_one_eighth'] = int(gap is not None and gap <= 0.125 + 1e-12)
    return result


def turn_counts(turn):
    return Counter(turns=1, initial_nonzero_turns=int(turn['initial_nonzero']),
                   changed_turns=int(turn['category'] != 'exact'),
                   **{f"turn_{turn['category']}": 1},
                   forced_final_pass=int(turn['forced_final_pass']))


def analyze(output):
    output.mkdir(parents=True, exist_ok=False)
    manifest = json.loads((ROOT / MANIFEST).read_text())
    descriptor = json.loads((ROOT / DESCRIPTOR).read_text())
    design = json.loads((ROOT / DESIGN).read_text())
    assert digest(ROOT / MANIFEST) == descriptor['manifest_sha256']
    assert design['input_archive_revision'] == descriptor['revision']
    assert descriptor['complete'] and descriptor['games'] == 3360
    inputs = {}

    def read_json(path):
        relative = str(path.relative_to(ROOT))
        value = path.read_bytes()
        sha = hashlib.sha256(value).hexdigest()
        assert manifest[relative] == sha, relative
        inputs[relative] = sha
        return json.loads(value)

    reports = {}
    for path in sorted((ROOT / BASE).glob('*/artifacts/evaluation/evaluation.json')):
        report = read_json(path)
        c = report['config']
        assert report['all_complete'] and not report['errors']
        assert not report['game_caps'] and not report['rollout_caps']
        key = c['arm'], c['players'], c['opponent']
        assert key not in reports
        reports[key] = path.parent, report
    assert len(reports) == 54
    totals, cells, outcomes, games, examples = Counter(), defaultdict(Counter), defaultdict(Counter), [], {}

    def keep_example(kind, row):
        identity = [row['players'], row['opponent'], row['episode'], row['round'],
                    row.get('decision', row.get('first_decision'))]
        key = hashlib.sha256(canonical(identity).encode()).hexdigest()
        if kind not in examples or key < examples[kind]['selection_sha256']:
            examples[kind] = {'selection_sha256': key, **row}

    with (output / 'transitions.jsonl').open('x') as events_file, (output / 'turns.jsonl').open('x') as turns_file:
        for (arm, n, opponent), (folder, report) in sorted(reports.items()):
            if arm != 'resource-filter':
                continue
            _, control = reports['filter', n, opponent]
            controls = {r['episode']: r for r in control['results']}
            assert len(report['results']) == 16 * n and set(controls) == {r['episode'] for r in report['results']}
            for record in report['results']:
                episode, terminal = record['episode'], record['terminal']
                reference = controls[episode]
                for key in ('gameSeed', 'playerCount', 'variant', 'sealed', 'seat'):
                    assert terminal[key] == reference['terminal'][key]
                difference = terminal_credit(record) - terminal_credit(reference)
                paired_outcome = 'better' if difference > 0 else 'worse' if difference < 0 else 'equal'
                cell = f"{n}p/{opponent}/{terminal['variant']}/{'sealed' if terminal['sealed'] else 'open'}"
                metadata = {'players': n, 'opponent': opponent, 'variant': terminal['variant'],
                            'sealed': terminal['sealed'], 'episode': episode, 'seat': terminal['seat'],
                            'paired_outcome': paired_outcome}
                current_turn, previous, stats = [], None, Counter(games=1)
                path = folder / f'decisions-{episode}.jsonl'
                hasher = hashlib.sha256()
                decision_count = 0
                with path.open('rb') as stream:
                    for line in stream:
                        hasher.update(line)
                        raw = json.loads(line)
                        decision_count += 1
                        assert raw['decision'] == decision_count
                        if raw['resourcePlan'] is not None:
                            row = compact(raw)
                            stats['search_decisions'] += 1
                            if current_turn:
                                event = {**metadata, **transition(previous, row)}
                                stats.update(event_counts(event))
                                events_file.write(canonical(event) + '\n')
                                if event['count_change']:
                                    keep_example('changed_plan', event)
                                if event['early_pass']:
                                    keep_example('early_pass', event)
                            current_turn.append(row)
                            previous = row
                        elif current_turn:
                            row = compact(raw)
                            assert row['move'] == PASS and row['round'] == previous['round']
                            assert row['decision'] == previous['decision'] + 1
                            current_turn.append(row)
                        else:
                            continue
                        if current_turn[-1]['move'] == PASS:
                            turn = {**metadata, **finish_turn(current_turn)}
                            stats.update(turn_counts(turn))
                            turns_file.write(canonical(turn) + '\n')
                            if turn['category'] == 'shortfall':
                                keep_example('first_bundle_shortfall', turn)
                            current_turn, previous = [], None
                assert not current_turn
                assert decision_count == record['decisions']
                sha = hasher.hexdigest()
                relative = str(path.relative_to(ROOT))
                assert sha == manifest[relative] == record['decision_receipt_sha256']
                inputs[relative] = sha
                totals.update(stats)
                cells[cell].update(stats)
                outcomes[paired_outcome].update(stats)
                games.append({**metadata, 'win': float(terminal_credit(record)),
                              'control_win': float(terminal_credit(reference)), 'counts': dict(stats)})
            print(canonical({'completed_cell': f'{n}p/{opponent}', 'games': totals['games'],
                             'search_decisions': totals['search_decisions']}), flush=True)
    assert totals['games'] == 1680 and totals['search_decisions'] == 69624
    assert len(cells) == 108
    assessment = {'complete': True, 'design_sha256': digest(ROOT / DESIGN),
                  'analyzer_sha256': digest(Path(__file__)), 'input_archive': {
                      key: descriptor[key] for key in ('repo', 'revision', 'archive_path', 'archive_sha256', 'manifest_sha256')},
                  'totals': dict(totals), 'cells': dict(sorted(cells.items())),
                  'paired_outcomes': dict(outcomes), 'examples': examples,
                  'input_files_verified': len(inputs), 'new_games': 0, 'new_hf_jobs': 0,
                  'gradients': False, 'qualification_eligible': False, 'reserved_final_seeds_used': False,
                  'interpretation': design['interpretation']}
    for name, value in [('assessment.json', assessment), ('games.json', games), ('inputs.json', inputs)]:
        (output / name).write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n')
    print(canonical({'complete': True, 'totals': totals}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--output', type=Path, required=True)
    analyze(parser.parse_args().output)
