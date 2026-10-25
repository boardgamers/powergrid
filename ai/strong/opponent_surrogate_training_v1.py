"""Compact public inputs and behaviour metrics; this module performs no gradients."""
import hashlib
from pathlib import Path

import numpy as np
from strategic_collection import read, digest

PHASES = ('plant', 'bid', 'building')
SCHEMA = {
    'state': (np.float32, (1217,)), 'actions': (np.float32, (6, 101)),
    'mask': (np.bool_, (6,)), 'target': (np.int64, ()),
    'teacher_values': (np.float64, (6,)), 'legal_indices': (np.int32, (6,)),
    'group': (np.int64, ()), 'identity': (np.int64, (7,)),
}


def inputs(observation):
    """The public encoder already computes shortlist membership in feature 100."""
    assert observation['featureRevision'] == '4.3-strategic-correction'
    state = np.asarray(observation['state'], np.float32)
    actions = np.asarray(observation['actions'], np.float32)
    assert state.shape == (1217,) and actions.ndim == 2 and actions.shape[1] == 101
    assert np.isfinite(state).all() and np.isfinite(actions).all()
    assert state[-1] == 1 and np.array_equal(state[:6], observation['playerMask'])
    assert np.isin(actions[:, 100], [0, 1]).all()
    selected = np.flatnonzero(actions[:, 100] == 1)
    assert 1 <= len(selected) <= 6
    packed = np.zeros((6, 101), np.float32)
    packed[:len(selected)] = actions[selected]
    mask = np.arange(6) < len(selected)
    legal = np.full(6, -1, np.int32); legal[:len(selected)] = selected
    return {'state': state, 'actions': packed, 'mask': mask, 'legal_indices': legal}


def compact(row, contract):
    o = row['observation']; result = inputs(o)
    chosen = np.flatnonzero(result['legal_indices'] == row['target'])
    assert len(chosen) == 1
    n, rule = contract['players'], contract['rule']
    assert row['playerCount'] == n and row['variant'] == ('recharged' if rule % 2 else 'original')
    assert row['sealed'] is (rule < 2)
    assert contract['split'] in ('train', 'validation', 'test', 'runtime', 'preflight')
    names = {m['name'] for m in o['moves']}
    phase = 2 if 'Build' in names else 1 if 'Bid' in names else 0
    assert names & {'Build', 'Bid', 'ChoosePowerPlant'}
    teacher = row['teacher']['result']; values = np.zeros(6, np.float64)
    assert teacher['index'] == row['target'] and teacher.get('truncated', 0) == 0
    selected = result['legal_indices'][result['mask']]
    if teacher['evaluations']:
        assert set(map(int, teacher['values'])) == set(selected.tolist())
        assert teacher['evaluations'] == len(selected) * 16
        values[:len(selected)] = [teacher['values'][str(i)] / 16 for i in selected]
        assert np.isfinite(values).all() and ((0 <= values) & (values <= 1)).all()
        assert values[chosen[0]] == values.max()
    else:
        assert len(selected) == 1
    result.update(target=np.int64(chosen[0]), teacher_values=values,
                  group=np.int64((n - 2) * 12 + rule * 3 + phase),
                  identity=np.asarray([n, rule, contract['deal'], contract['focal_seat'],
                                       contract['episode'], row['seat'], row['ordinal']], np.int64))
    return result


def input_digest(row):
    h = hashlib.sha256()
    for k in ('state', 'actions', 'mask'):
        h.update(np.ascontiguousarray(row[k]).tobytes())
    return h.hexdigest()


def validate_arrays(data):
    n = len(data['target']); assert n > 0 and set(data) == set(SCHEMA)
    for key, (dtype, shape) in SCHEMA.items():
        assert data[key].shape == (n, *shape) and data[key].dtype == dtype
        assert np.isfinite(data[key]).all()
    counts = data['mask'].sum(1)
    assert ((1 <= counts) & (counts <= 6)).all()
    assert np.array_equal(data['mask'], np.arange(6)[None] < counts[:, None])
    assert ((0 <= data['target']) & (data['target'] < counts)).all()
    assert (data['legal_indices'][~data['mask']] == -1).all()
    assert (data['legal_indices'][data['mask']] >= 0).all()
    assert (np.diff(data['legal_indices'], axis=1)[data['mask'][:, 1:]] > 0).all()
    assert (data['actions'][~data['mask']] == 0).all()
    assert (data['actions'][:, :, 100][data['mask']] == 1).all()
    assert ((0 <= data['teacher_values']) & (data['teacher_values'] <= 1)).all()
    assert (data['teacher_values'][~data['mask']] == 0).all()
    assert (data['state'][:, -1] == 1).all()
    ids = data['identity']; players, rules = ids[:, 0], ids[:, 1]
    assert ((2 <= players) & (players <= 6) & (0 <= rules) & (rules < 4)).all()
    assert np.array_equal(data['state'][:, :6], np.arange(6)[None] < players[:, None])
    assert ((0 <= data['group']) & (data['group'] < 60)).all()
    assert np.array_equal(data['group'] // 3, (players - 2) * 4 + rules)
    assert np.array_equal(data['teacher_values'][np.arange(n), data['target']], data['teacher_values'].max(1))
    return counts > 1


def group_weights(data):
    """Every count/rule/phase has equal weight; forced shortlists have no gradient."""
    active = data['mask'].sum(1) > 1
    sizes = np.bincount(data['group'][active], minlength=60)
    assert (sizes > 0).all(), 'All 60 count/rule/phase groups need non-forced examples'
    weights = np.zeros(len(active), np.float32)
    weights[active] = active.sum() / (60 * sizes[data['group'][active]])
    return weights


def metrics(logits, data):
    logits = np.asarray(logits, np.float64)
    assert logits.shape == data['mask'].shape and np.isfinite(logits).all()
    masked = np.where(data['mask'], logits, -np.inf)
    shifted = masked - masked.max(1, keepdims=True)
    logp = shifted - np.log(np.exp(shifted).sum(1, keepdims=True))
    ix = np.arange(len(logits)); target = data['target']; chosen = masked.argmax(1)
    active = data['mask'].sum(1) > 1
    top3 = np.argsort(-masked, axis=1, kind='stable')[:, :3]
    nll = -logp[ix, target]; correct = chosen == target
    regret = data['teacher_values'][ix, target] - data['teacher_values'][ix, chosen]
    groups = {}
    for group in sorted(set(data['group'].tolist())):
        use = (data['group'] == group) & active
        if not use.any(): continue
        groups[str(group)] = {'rows': int(use.sum()), 'nll': float(nll[use].mean()),
                             'agreement': float(correct[use].mean()),
                             'top3': float((top3[use] == target[use, None]).any(1).mean()),
                             'teacher_sample_regret': float(regret[use].mean())}
    assert groups
    return {'rows': len(ix), 'nonforced_rows': int(active.sum()), 'forced_rows': int((~active).sum()),
            'nll': float(nll[active].mean()), 'agreement': float(correct[active].mean()),
            'macro_nll': float(np.mean([g['nll'] for g in groups.values()])),
            'macro_agreement': float(np.mean([g['agreement'] for g in groups.values()])),
            'groups': groups,
            'scope': 'Imitation of sampled search behaviour. Teacher-sample regret is a diagnostic on 16-rollout labels, not independent value accuracy or full-game strength.'}


def load_bundle(folder, design):
    folder = Path(folder); report = read(folder/'data-check.json')
    assert report['complete'] and report['collection_games'] == 2560 and report['prepared_games'] == 2240
    assert report['split_games'] == {'train': 1920, 'validation': 320}
    assert report['test_records_included'] is False and report['training_eligible'] is True
    assert report['collection_protocol_sha256'] == design['collection_protocol_sha256']
    assert digest(folder/'collection-index.json') == report['collection_index_sha256']
    index = read(folder/'collection-index.json')
    assert index['complete'] and index['games'] == 2560 and index['twins'] == 640
    assert index['protocol_sha256'] == design['collection_protocol_sha256']
    assert index['split_games'] == {'train': 1920, 'validation': 320, 'test': 320}
    expected_files = {'collection-index.json'} | {f'{s}/{k}.npy' for s in ('train', 'validation') for k in SCHEMA}
    assert set(report['files']) == expected_files
    assert {str(p.relative_to(folder)) for p in folder.rglob('*') if p.is_file()} == expected_files | {'data-check.json'}
    for name, sha in report['files'].items(): assert digest(folder/name) == sha
    data = {}
    for split, deals in [('train', range(24)), ('validation', range(24, 28))]:
        data[split] = {k: np.load(folder/split/(k+'.npy'), mmap_mode='r', allow_pickle=False) for k in SCHEMA}
        d = data[split]; validate_arrays(d); group_weights(d)
        assert len(d['target']) == report['split_rows'][split]
        assert set(d['identity'][:, 2].tolist()) == set(deals)
        game_ids = {tuple(x[:5]) for x in d['identity']}
        expected = {(n, r, deal, seat, 4*(deal*n + seat)+r) for n in range(2, 7)
                    for r in range(4) for deal in deals for seat in range(n)}
        assert game_ids == expected
    assert not (folder/'test').exists()
    return data, report
