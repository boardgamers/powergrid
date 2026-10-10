"""Paired public continuations. Preserve sample outcomes; never create winner labels."""
import hashlib
import json
from pathlib import Path
import sys
import time
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'ai'))
from infer import Model, Node
from pool import EnginePool
from feature_contract import model_revision

REVISION = '4.2-discard-correction'
MODES = ['neural', 'neural_economic', 'neural_search', 'mixed_control']


def predict_batch(model, rows, batch_size=64):
    assert model_revision(model) == REVISION
    assert model.session.get_modelmeta().custom_metadata_map['powergrid.inference_precision'] == 'float64'
    result = []
    for begin in range(0, len(rows), batch_size):
        part = rows[begin:begin+batch_size]
        counts = [len(r['actions']) for r in part]
        assert all(n > 0 for n in counts)
        actions = np.zeros((len(part), max(counts), 100), dtype=np.float32)
        mask = np.zeros(actions.shape[:2], dtype=bool)
        for i, row in enumerate(part):
            assert row['featureRevision'] == REVISION and len(row['state']) == 1216
            actions[i, :counts[i]] = row['actions']
            mask[i, :counts[i]] = True
        scores, _ = model.session.run(None, {'state': np.asarray([r['state'] for r in part], dtype=np.float32),
            'actions': actions, 'mask': mask})
        selected = scores.argmax(-1).tolist()
        assert all(0 <= a < n for a, n in zip(selected, counts))
        result.extend(selected)
    return result


def prepare(node, model, root):
    observation = node.call({'op': 'prepare', **root['request'], 'featureRevision': REVISION})
    assert observation['moves'] == root['legal']
    row = observation['observation']
    proposal = model.predict(row['state'], row['actions'])[0]
    assert proposal == predict_batch(model, [row])[0] == root['model_proposal']
    return list(dict.fromkeys([*observation['options'], proposal]))


def evaluate(model, root, options, mode, batch, samples, workers=24):
    assert mode in MODES and batch in ['a', 'b'] and samples > 0
    # Neither the real game seed nor any true hidden state enters the rollout RNG.
    seed = 'strategic-teacher-public-v1-' + root['rootId'] + '-' + batch
    count = samples * len(options)
    started = time.perf_counter(); policy_seconds = 0.; decisions = 0
    pool = EnginePool(min(workers, count), script='ai/strong/strategic-continuations.cjs')
    try:
        tick = time.perf_counter()
        response = pool.call({'op': 'reset', 'n': count, **root['request'], 'mode': mode,
            'options': options, 'seed': seed, 'samples': samples, 'maxSteps': 2400, 'featureRevision': REVISION})
        engine_seconds = time.perf_counter()-tick
        ended = response['ended']; last_progress = time.perf_counter()
        while any(r is not None for r in response['observations']):
            live = [i for i, r in enumerate(response['observations']) if r is not None]
            rows = [response['observations'][i] for i in live]
            assert all(r['roles'][r['actor']] == 'neural' for r in rows)
            if mode != 'neural':
                assert all(r['actor'] == root['request']['player'] for r in rows)
            tick = time.perf_counter(); chosen = predict_batch(model, rows)
            policy_seconds += time.perf_counter()-tick; decisions += len(rows)
            actions = [None]*count
            for i, a in zip(live, chosen): actions[i] = a
            tick = time.perf_counter(); response = pool.call({'op': 'step', 'actions': actions})
            engine_seconds += time.perf_counter()-tick; ended.extend(response['ended'])
            if time.perf_counter()-last_progress >= 45:
                print({'root':root['rootId'], 'mode':mode, 'batch':batch, 'rollouts':len(ended),
                    'requested':count, 'seconds':time.perf_counter()-started}, flush=True)
                last_progress = time.perf_counter()
    finally:
        pool.close()
    assert len(ended) == count and {r['env'] for r in ended} == set(range(count))
    outcomes = {str(a):[None]*samples for a in options}; seen = set()
    inner = {'decisions':0, 'evaluations':0, 'truncated':0}
    for row in ended:
        key = row['sample'], row['actionIndex']
        assert key not in seen and 0 <= key[0] < samples and key[1] in options
        seen.add(key)
        assert row['steps'] <= 2400 and (row['value'] is None) == row['truncated']
        assert row['value'] is None or 0 <= row['value'] <= 1
        outcomes[str(key[1])][key[0]] = row['value']
        for field in inner: inner[field] += row['searchStats'][field]
    outer_caps = sum(r['truncated'] for r in ended)
    proposal = root['model_proposal']; usable = not outer_caps and not inner['truncated']
    advantages = {str(a):[v-base for v, base in zip(outcomes[str(a)], outcomes[str(proposal)])]
        for a in options} if usable else None
    return {'rootId':root['rootId'], 'public_root_sha256':root['public_root_sha256'],
        'split':root['split'], 'mode':mode, 'batch':batch, 'seed':seed, 'samples':samples,
        'options':options, 'model_proposal':proposal, 'sample_outcomes':outcomes,
        'paired_advantages_over_proposal':advantages, 'outer_truncations':outer_caps,
        'nested_search':inner, 'usable':usable, 'rollouts':ended,
        'timing':{'seconds':time.perf_counter()-started, 'engine_seconds':engine_seconds,
            'policy_seconds':policy_seconds, 'policy_decisions':decisions},
        'scope':'Simulated terminal credits, not calibrated real-game values or hard winner labels.',
        'qualification_eligible':False}
