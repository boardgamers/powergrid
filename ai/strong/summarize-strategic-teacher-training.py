"""Account for the entire fixed label grid and audit independent sample batches."""
from collections import defaultdict
import gzip
import json
import numpy as np
from strategic_training_labels import ROOT, PROTOCOL, SOURCE, read, write, digest


def diagnostic(rows):
    result = {}
    for split in ['train', 'validation']:
        selected = [r for r in rows if r['split'] == split]
        if not selected:
            continue
        result[split] = {'roots': len(selected)}
        for label, key in [('all', None), ('decision', 'decision'), ('players', 'players'), ('rules', 'rules')]:
            groups = defaultdict(list)
            for r in selected:
                groups[str(r[key]) if key else 'all'].append(r)
            result[split][label] = {
                name: {'roots': len(group),
                       'a_selected_b_advantage': float(np.mean([r['a_selected_b'] for r in group])),
                       'b_selected_a_advantage': float(np.mean([r['b_selected_a'] for r in group])),
                       'same_choice_fraction': float(np.mean([r['same_choice'] for r in group]))}
                for name, group in sorted(groups.items())}
    return result


def summarize():
    p, source = read(PROTOCOL), read(SOURCE)
    cases, pending, modes = {}, [], defaultdict(dict)
    pin = read(ROOT/'ai/strong/strategic-teacher-training-roots-v1.json')
    root_file = ROOT/pin['local_file']
    assert digest(root_file) == p['roots_sha256']
    with gzip.open(root_file, 'rt') as f:
        all_roots = list(map(json.loads, f))
    assert len(all_roots) == 1920
    for n in p['players']:
        for family in p['source_modes']:
            for start in range(0, p['deals'], 2):
                roots = {r['rootId']: r for r in all_roots if r['players'] == n and r['mode'] == family and start <= r['deal'] < start+2}
                assert len(roots) == 24
                for mode in p['modes']:
                    key = f'{n}p-{family}-{mode}-{start}-{start+2}'
                    folder = ROOT/'ai/runs/strategic-teacher-training-verified-v1'/key
                    if not (folder/'verified.json').exists():
                        pending.append(key)
                        continue
                    v = read(folder/'verified.json')
                    assert v['verified'] and not v['qualification_eligible']
                    assert v['source_revision'] == source['revision'] and v['source_sha256'] == source['sha256']
                    assert v['protocol_sha256'] == digest(PROTOCOL) and v['roots_sha256'] == p['roots_sha256']
                    for name, sha in v['artifacts'].items():
                        assert folder.joinpath(name).name == name and digest(folder/name) == sha
                    s = v['summary']
                    assert (s['players'], s['source_mode'], s['mode'], s['deal_start'], s['deal_end']) == (n, family, mode, start, start+2)
                    assert s['positions'] == 24 and s['searches'] == 48 and s['samples'] == 48
                    assert not s['game_truncations'] and not s['nested_truncations']
                    cases[key] = {**s, 'revision': v['revision'], 'prefix': v['prefix'],
                                  'artifacts': v['artifacts'], 'verified_sha256': digest(folder/'verified.json')}
                    seen = set()
                    with gzip.open(folder/'labels.jsonl.gz', 'rt') as f:
                        for row in map(json.loads, f):
                            identity = row['rootId'], row['batch']
                            assert identity not in seen and row['mode'] == mode
                            seen.add(identity)
                            assert mode not in modes[identity]
                            modes[identity][mode] = row
                    assert seen == {(root, batch) for root in roots for batch in p['batches']}
    complete = []
    for root_id in sorted({root for root, _ in modes}):
        if any(set(modes[root_id, batch]) != set(p['modes']) for batch in p['batches']):
            continue
        means = {}
        for batch in p['batches']:
            rows = [modes[root_id, batch][mode] for mode in p['modes']]
            a, b = rows
            assert a['options'] == b['options'] and a['model_proposal'] == b['model_proposal']
            assert a['root_metadata'] == b['root_metadata'] and a['seed'] == b['seed']
            means[batch] = {str(i): float(np.mean([
                np.asarray(r['paired_advantages_over_proposal'][str(i)]) for r in rows])) for i in a['options']}
        proposal = str(a['model_proposal'])
        choices = {batch: max(scores, key=lambda i: (scores[i], i == proposal, -int(i))) for batch, scores in means.items()}
        meta = a['root_metadata']
        complete.append({'rootId': root_id, 'split': a['split'], 'players': meta['players'],
            'decision': meta['decision'], 'rules': meta['variant']+'/'+('sealed' if meta['sealed'] else 'open'),
            'a_selected_b': means['b'][choices['a']], 'b_selected_a': means['a'][choices['b']],
            'same_choice': choices['a'] == choices['b']})
    first = [key for key in cases if key.endswith('-0-2')]
    result = {'verified_shards': len(cases), 'expected_shards': p['expected_complete_shards'],
        'all_shards_verified': not pending, 'first_wave_verified': len(first),
        'first_wave_complete': len(first) == p['expected_first_wave_shards'],
        'positions_by_mode': {mode: sum(c['positions'] for c in cases.values() if c['mode'] == mode) for mode in p['modes']},
        'complete_mixture_roots': len(complete), 'evaluations': sum(c['evaluations'] for c in cases.values()),
        'paired_mixture_diagnostic': diagnostic(complete), 'cases': cases, 'pending': pending,
        'scope': 'Equal neural/economic continuation mixture; selection on A evaluated on B and vice versa. Descriptive simulation diagnostic only, not whole-game strength or a confidence interval.',
        'protocol_sha256': digest(PROTOCOL), 'source_revision': source['revision'], 'source_sha256': source['sha256'],
        'gradients_started': False, 'qualification_eligible': False}
    write(ROOT/'ai/strong/strategic-teacher-training-results-v1.json', result)
    print({k: v for k, v in result.items() if k not in ['cases', 'pending', 'paired_mixture_diagnostic']})
    print(result['paired_mixture_diagnostic'])


if __name__ == '__main__':
    summarize()
