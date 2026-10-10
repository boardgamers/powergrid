"""All labels retained, with whole-deal splits and balanced root weights."""
from collections import Counter
import gzip
import json
from pathlib import Path
import numpy as np


def load_rows(directory, protocol):
    rows = []
    for n in range(2, 7):
        path = Path(directory) / f'{n}p'
        verified = json.loads((path / 'verified.json').read_text())
        pin = protocol['data'][str(n)]
        assert verified['revision'] == pin['revision']
        assert verified['sha256'] == pin['sha256']
        assert verified['roots'] == pin['roots']
        assert verified['no_deal_split_leakage'] and verified['truncated'] == 0
        with gzip.open(path / 'labels.jsonl.gz', 'rt') as f:
            batch = [json.loads(line) for line in f]
        assert len(batch) == pin['roots']
        assert dict(Counter(r['split'] for r in batch)) == pin['root_splits']
        assert all(r['players'] == n for r in batch)
        rows.extend(batch)
    assert len(set(r['rootId'] for r in rows)) == len(rows)
    groups = {}
    for r in rows:
        key = r['players'], r['mode'], r['deal']
        assert r['split'] in ['train', 'validation']
        assert groups.setdefault(key, r['split']) == r['split'], 'Whole-deal split leakage'
        assert r['guidance']['truncated'] == 0 and r['guidance']['samples'] == 64
    return rows


def balanced_weights(rows):
    counts = Counter((r['players'], r['mode'], r['deal']) for r in rows)
    families, deals = {}, {}
    for n, mode, deal in counts:
        families.setdefault(n, set()).add(mode)
        deals.setdefault((n, mode), set()).add(deal)
    assert set(families) == set(range(2, 7)) and all(len(x) == 4 for x in families.values())
    weights = np.array([1 / (len(families) * len(families[r['players']]) *
        len(deals[r['players'], r['mode']]) * counts[r['players'], r['mode'], r['deal']]) for r in rows], np.float32)
    assert np.isclose(weights.sum(), 1) and np.all(weights > 0)
    return weights


def arrays(rows):
    n, candidates = len(rows), max(len(r['actions']) for r in rows)
    state = np.asarray([r['state'] + [1.] for r in rows], np.float32)
    actions = np.zeros((n, candidates, 100), np.float32)
    mask = np.zeros((n, candidates), bool)
    target = np.zeros((n, candidates), np.float32)
    parent = np.array([r['model_proposal'] for r in rows], np.int64)
    for i, r in enumerate(rows):
        m = len(r['actions'])
        assert len(r['state']) == 1215 and m > 1
        assert all(a['name'] == 'DiscardPowerPlant' for a in r['legal'])
        actions[i, :m], mask[i, :m] = r['actions'], True
        target[i, :m] = [r['guidance']['values'][str(j)] for j in range(m)]
    assert np.isfinite(state).all() and np.isfinite(actions).all() and np.isfinite(target).all()
    return dict(state=state, actions=actions, mask=mask, target=target, parent=parent,
                weights=balanced_weights(rows))


def metrics(scores, data, rows, margin):
    scores = np.asarray(scores)
    mask, target, parent, weights = [data[k] for k in ['mask', 'target', 'parent', 'weights']]
    index = np.arange(len(rows))
    best = np.where(mask, scores, -1e9).argmax(1)
    choices = np.where(scores[index, best] - scores[index, parent] > margin, best, parent)
    gain = target[index, choices] - target[index, parent]
    regret = np.where(mask, target, -1e9).max(1) - target[index, choices]
    def group(ids):
        w = weights[ids] / weights[ids].sum()
        return {'roots': len(ids), 'weighted_simulated_gain': float(w @ gain[ids]),
                'weighted_simulated_regret': float(w @ regret[ids]),
                'changed': int(np.count_nonzero(choices[ids] != parent[ids]))}
    return {**group(index), 'by_players': {str(n): group(np.array([i for i, r in enumerate(rows) if r['players'] == n])) for n in range(2, 7)},
            'by_rules': {v + ('/sealed' if s else '/open'): group(np.array([i for i,r in enumerate(rows) if r['variant'] == v and r['sealed'] == s])) for v in ['original','recharged'] for s in [False,True]},
            'scope': 'Conditional label returns, not whole-game win rates.'}
