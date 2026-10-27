"""Read-only coverage/action audit of recorded-game whole-turn arena checks."""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def read(path):
    return json.loads(path.read_text())


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def audit(run):
    assessment = read(run/'assessment.json')
    assert assessment['passed'] and assessment['original_games_replayed'] == 120
    for name, expected in assessment['code_hashes'].items():
        assert digest(ROOT/'ai/strong'/name) == expected
    for name, expected in assessment['inputs'].items():
        assert digest(ROOT/name) == expected
    assert digest(run/'receipts.jsonl') == assessment['receipts_sha256']
    receipts = [json.loads(line) for line in (run/'receipts.jsonl').read_text().splitlines()]
    grouped = defaultdict(list)
    for row in receipts:
        grouped[row['arm'], row['opponent'], row['players'], row['episode']].append(row)
    expected = {(arm, opponent, n, episode)
                for arm, opponent, every_seat in [('filter', 'economic', True),
                    ('filter', 'legacy', False), ('resource-filter', 'economic', False)]
                for n in range(2, 7) for episode in range(4*(n if every_seat else 1))}
    assert set(grouped) == expected
    cases = {(c['arm'], c['opponent'], c['players'], c['episode']): c for c in assessment['cases']}
    assert len(cases) == len(assessment['cases']) == 120 and set(cases) == expected
    total_actions = total_resource_actions = purchases = 0
    for key in sorted(expected):
        arm, opponent, n, episode = key
        folder = ('ai/runs/resource-replanning-development-collected-v1/'
                  f'resource-replanning-development-v1-{arm}-{n}p-{opponent}-0-4/artifacts/evaluation/')
        name = folder+f'decisions-{episode}.jsonl'
        assert name in assessment['inputs'] and folder+'evaluation.json' in assessment['inputs']
        rows = [json.loads(line) for line in (ROOT/name).read_text().splitlines()]
        report = read(ROOT/folder/'evaluation.json')
        record = next(r for r in report['results'] if r['episode'] == episode)
        assert digest(ROOT/name) == record['decision_receipt_sha256']
        case = cases[key]
        assert case['seat'] == record['terminal']['seat'] == episode//4
        assert case['variant'] == record['terminal']['variant'] == ('recharged' if episode % 2 else 'original')
        assert case['sealed'] == record['terminal']['sealed'] == (episode % 4 < 2)
        assert case['recorded_learner_actions'] == len(rows) == record['decisions']
        covered = set()
        previous_last = previous_revision = -1
        for receipt in grouped[key]:
            first, last = receipt['first_decision'], receipt['last_decision']
            assert 1 <= first <= last <= len(rows) and first > previous_last
            previous_last = last
            response = receipt['response']
            assert response['contract'] == 'resource-turn-exchange-v1'
            assert response['identity'] == assessment['identity']
            assert response['qualification_eligible'] is False
            assert response['revision'] > previous_revision
            previous_revision = response['revision']
            assert response['requestId'] == f"{episode}:{response['revision']}"
            envelope = response['transaction']
            assert envelope['qualification_eligible'] is False and envelope['player'] == case['seat']
            actions = [row['move'] for row in rows[first-1:last]]
            assert envelope['actions'] == actions
            assert actions[-1] == {'name': 'Pass', 'data': True}
            assert all(move['name'] == 'BuyResource' for move in actions[:-1])
            counts = Counter(move['data']['resource'] for move in actions[:-1])
            assert envelope['counts'] == [counts[r] for r in ('coal', 'oil', 'garbage', 'uranium')]
            assert sum(envelope['counts']) == len(actions)-1
            assert type(envelope['cost']) is int and envelope['cost'] >= 0
            covered.update(range(first-1, last-1))
            total_resource_actions += len(actions)
        assert covered == {i for i, row in enumerate(rows) if row['move']['name'] == 'BuyResource'}
        assert len(grouped[key]) == case['resource_turns']
        assert sum(r['last_decision']-r['first_decision']+1 for r in grouped[key]) == case['resource_actions']
        purchases += len(covered)
        total_actions += len(rows)
    assert total_actions == assessment['recorded_learner_actions'] == 15838
    assert total_resource_actions == assessment['resource_actions'] == 5253
    assert len(receipts) == assessment['resource_turns'] == 1167
    assert purchases == total_resource_actions-len(receipts) == 4086
    return {'complete': True, 'original_games': 120, 'recorded_learner_actions': total_actions,
            'resource_turns': len(receipts), 'resource_actions': total_resource_actions,
            'recorded_purchases_all_covered': purchases,
            'assessment_sha256': digest(run/'assessment.json'),
            'receipts_sha256': digest(run/'receipts.jsonl'), 'auditor_sha256': digest(Path(__file__)),
            'scope': 'Independent archived-input, predetermined coverage, action-order and purchase-conservation audit; engine replay is the separate checker.',
            'new_inference': 0, 'new_full_games': 0, 'new_hf_jobs': 0,
            'qualification_eligible': False, 'reserved_final_seeds_used': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('run', type=Path)
    args = parser.parse_args()
    result = audit(args.run.resolve())
    with (args.run/'independent-audit.json').open('x') as stream:
        json.dump(result, stream, indent=2); stream.write('\n')
    print(json.dumps(result))
