"""Independently verify every public-discard rollout and summarize guidance stability."""
import argparse
from collections import Counter
import hashlib
import itertools
import json
import math
from pathlib import Path
import re
from huggingface_hub import hf_hub_download

ROOT = Path(__file__).resolve().parents[2]
def read(path):
    return json.loads(Path(path).read_text())
def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def write(path, data):
    Path(path).write_text(json.dumps(data, indent=2) + '\n')


def verify_rows(rows, roots, protocol):
    by_id = {r['rootIndex']: r for r in roots}
    assert len(by_id) == len(roots)
    expected = set(itertools.product(by_id, protocol['continuations'], protocol['batches']))
    seen = set()
    for row in rows:
        key = row['rootIndex'], row['continuation'], row['batch']
        assert key in expected and key not in seen, 'Unexpected/duplicate rollout row'
        seen.add(key)
        root = by_id[row['rootIndex']]
        for k in ['players', 'episode', 'variant', 'sealed', 'round']:
            assert row[k] == root[k], 'Root identity mismatch: ' + k
        assert row['original_proposal'] == root['model_proposal']
        assert row['options'] == list(range(len(root['legal'])))
        assert row['samples'] == protocol['samples_per_batch']
        assert row['evaluations'] == len(root['legal']) * row['samples']
        outcomes = row['sample_outcomes']
        assert set(outcomes) == {str(a) for a in row['options']}
        for values in outcomes.values():
            assert len(values) == row['samples']
            assert all(v is None or (isinstance(v, (int, float)) and not isinstance(v, bool)
                       and math.isfinite(v) and 0 <= v <= 1) for v in values)
        caps = sum(v is None for values in outcomes.values() for v in values)
        assert row['truncated'] == caps
        values = None if caps else {a: sum(xs) / row['samples'] for a, xs in outcomes.items()}
        winners = [] if caps else [int(a) for a, v in values.items() if v == max(values.values())]
        assert row['values'] == values and row['winner_set'] == winners, 'Incorrect derived target'
        assert all(math.isfinite(v) and v >= 0 for v in row['timing'].values())
        assert row['timing']['policy_decisions'] >= 0
    assert seen == expected, 'Missing roots/policies/independent batches'
    return sum(r['evaluations'] for r in rows), sum(r['truncated'] for r in rows)


def chosen(row):
    """Retain the model proposal on a best-action tie; otherwise stable action order."""
    return row['original_proposal'] if row['original_proposal'] in row['winner_set'] else min(row['winner_set'])


def summarize(rows, protocol):
    by_key = {(r['rootIndex'], r['continuation'], r['batch']): r for r in rows}
    ids = sorted({r['rootIndex'] for r in rows})
    output = {'positions': len(ids), 'per_continuation': {}, 'between_continuations': {}}
    for policy in protocol['continuations']:
        pairs = [(by_key[i, policy, 'a'], by_key[i, policy, 'b']) for i in ids]
        valid = [(a, b) for a, b in pairs if not (a['truncated'] or b['truncated'])]
        crossfit = []
        apparent = []
        for a, b in valid:
            proposal = str(a['original_proposal'])
            crossfit.append(((b['values'][str(chosen(a))] - b['values'][proposal]) +
                             (a['values'][str(chosen(b))] - a['values'][proposal])) / 2)
            apparent.append(sum(max(r['values'].values()) - r['values'][proposal] for r in [a, b]) / 2)
        output['per_continuation'][policy] = {
            'valid_paired_roots': len(valid), 'invalid_paired_roots': len(pairs) - len(valid),
            'exact_winner_set_agreement': sum(a['winner_set'] == b['winner_set'] for a, b in valid),
            'winner_sets_overlap': sum(bool(set(a['winner_set']) & set(b['winner_set'])) for a, b in valid),
            'same_selected_action': sum(chosen(a) == chosen(b) for a, b in valid),
            'both_batches_agree_to_change_proposal': sum(chosen(a) == chosen(b) != a['original_proposal'] for a, b in valid),
            'tied_batch_winners': sum(len(r['winner_set']) > 1 for pair in valid for r in pair),
            'mean_apparent_proposal_regret': sum(apparent) / len(apparent) if apparent else None,
            'mean_cross_batch_selected_gain': sum(crossfit) / len(crossfit) if crossfit else None,
            'per_root_cross_batch_gain': {str(a['rootIndex']): g for (a, _), g in zip(valid, crossfit)},
        }
    for left, right in itertools.combinations(protocol['continuations'], 2):
        pairs = [(by_key[i, left, b], by_key[i, right, b]) for i in ids for b in protocol['batches']]
        valid = [(a, b) for a, b in pairs if not (a['truncated'] or b['truncated'])]
        output['between_continuations'][left + '_vs_' + right] = {
            'valid_root_batches': len(valid),
            'disjoint_winner_sets': sum(not (set(a['winner_set']) & set(b['winner_set'])) for a, b in valid),
            'different_selected_actions': sum(chosen(a) != chosen(b) for a, b in valid)}
    return output


def main():
    p = argparse.ArgumentParser(__doc__)
    p.add_argument('players', type=int, choices=range(2, 7))
    p.add_argument('revision')
    p.add_argument('output', type=Path)
    a = p.parse_args()
    assert re.fullmatch('[a-f0-9]{40}', a.revision)
    protocol_path = ROOT / 'ai/strong/public-discard-teacher-protocol-v1.json'
    protocol = read(protocol_path)
    source = read(ROOT / 'ai/strong/public-discard-teacher-source-v1.json')
    dataset = protocol['dataset']
    raw = Path(hf_hub_download(protocol['repo'], dataset['path'], revision=dataset['revision']))
    assert digest(raw) == dataset['sha256']
    all_roots = [json.loads(line) for line in raw.read_text().splitlines()]
    assert len(all_roots) == dataset['roots']
    roots = [r for r in all_roots if r['players'] == a.players]
    out = a.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    prefix = f'runs/public-discard-teacher-v1-{a.players}p'
    def fetch(name):
        assert Path(name).name == name
        contents = Path(hf_hub_download(protocol['repo'], prefix + '/' + name, revision=a.revision)).read_bytes()
        (out / name).write_bytes(contents)
    fetch('audit-check.json')
    status = read(out / 'audit-check.json')
    expected = {'status': 'complete', 'players': a.players, 'positions': len(roots), 'smoke': False,
        'protocol_sha256': digest(protocol_path), 'source_revision': source['revision'],
        'source_sha256': source['sha256'], 'dataset_sha256': dataset['sha256'],
        'model_sha256': protocol['model']['sha256'], 'trained': False, 'qualification_eligible': False}
    for key, value in expected.items():
        assert status[key] == value, key
    assert set(status['artifact_sha256']) == {'rows.jsonl'}
    fetch('rows.jsonl')
    assert digest(out / 'rows.jsonl') == status['artifact_sha256']['rows.jsonl']
    rows = [json.loads(line) for line in (out / 'rows.jsonl').read_text().splitlines()]
    evaluations, caps = verify_rows(rows, roots, protocol)
    assert evaluations == status['evaluations'] == protocol['rollouts_by_player_count'][str(a.players)]
    assert caps == status['truncated'] and len(rows) == status['searches']
    for field in ['engine_seconds', 'policy_seconds', 'policy_decisions']:
        assert sum(r['timing'][field] for r in rows) == status[field]
    summary = summarize(rows, protocol)
    summary['rules'] = {str(variant) + '-' + ('sealed' if sealed else 'open'):
        summarize([r for r in rows if r['variant'] == variant and r['sealed'] == sealed], protocol)
        for variant, sealed in sorted({(r['variant'], r['sealed']) for r in rows})}
    summary['scope'] = ('Descriptive, equal weight per collected root. Winner ties preserve the original '
        'proposal; otherwise lowest legal index. Cross-batch gain selects on a and measures on b, then '
        'reverses and averages. These are public-belief continuation returns, not actual playing '
        'strength. Roots from the same game-deal family are dependent. No promotion or training labels approved.')
    summary['qualification_eligible'] = False
    write(out / 'summary.json', summary)
    write(out / 'verified.json', {'revision': a.revision, 'prefix': prefix, 'players': a.players,
        'positions': len(roots), 'evaluations': evaluations, 'truncated': caps,
        'all_artifacts_recomputed': True, 'qualification_eligible': False,
        'sha256': {name: digest(out / name) for name in ['audit-check.json', 'rows.jsonl', 'summary.json']}})
    print({'players': a.players, 'positions': len(roots), 'evaluations': evaluations, 'truncated': caps,
        'continuations': {k: {f: v[f] for f in ['same_selected_action', 'both_batches_agree_to_change_proposal',
                            'mean_cross_batch_selected_gain']} for k, v in summary['per_continuation'].items()}})


if __name__ == '__main__':
    main()
