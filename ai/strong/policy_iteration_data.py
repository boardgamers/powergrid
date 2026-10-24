"""Exact full-label coverage and paired targets for the broader training set."""
from collections import Counter, defaultdict
import gzip
import json
from pathlib import Path

import numpy as np
from huggingface_hub import hf_hub_download
from strategic_collection import ROOT, read, digest
from strategic_correction_targets import targets, MODES, BATCHES

PROTOCOL = ROOT/'ai/strong/policy-iteration-labels-protocol-v2.json'
SOURCE = ROOT/'ai/strong/policy-iteration-labels-source-v2.json'
METADATA = ['players', 'behavior', 'mode', 'deal', 'split', 'variant', 'sealed', 'decision', 'round']


def validate_manifest(manifest, p, source):
    """Fail before downloading labels when even one required shard is missing."""
    assert manifest['complete'] and not manifest['pending']
    assert manifest['source'] == source and manifest['protocol_sha256'] == digest(PROTOCOL)
    assert source['protocol_sha256'] == digest(PROTOCOL)
    assert manifest['planned_shards'] == manifest['complete_shards'] == len(p['shards']) == 948
    assert manifest['verified_root_mode_pairs'] == 34560
    assert manifest['reused_pilot'] == p['reuse_pilot']
    expected = {s['id']: s for s in p['shards']}
    assert set(manifest['cases']) == set(expected)
    for key, case in manifest['cases'].items():
        assert case['verified'] and case['source'] == source and case['shard'] == expected[key]
        assert case['summary']['roots'] == len(expected[key]['root_ids'])
        assert case['summary']['searches'] == 2*len(expected[key]['root_ids'])
        assert case['summary']['samples_per_batch'] == 96 and case['summary']['game_truncations'] == 0
        assert set(case['summary']['options_by_root']) == set(expected[key]['root_ids'])


def packed_row(row, meta, mode):
    """Keep soft paired samples, with independent arithmetic/identity checks."""
    assert row['rootId'] == meta['rootId'] and row['mode'] == mode
    assert row['public_root_sha256'] == meta['public_root_sha256']
    assert row['split'] == meta['split'] == ('validation' if meta['deal'] in [0, 4, 8, 12] else 'train')
    assert row['root_metadata'] == {k: meta[k] for k in METADATA}
    assert row['batch'] in BATCHES and row['samples'] == 96 and row['belief'] == 'policy'
    assert row['seed'] == 'strategic-teacher-public-v1-' + meta['rootId'] + '-' + row['batch']
    options = row['options']
    assert len(set(options)) == len(options) and sorted(options) == meta['options']
    assert set(row['sample_outcomes']) == set(row['paired_advantages_over_proposal']) == {str(i) for i in options}
    assert row['model_proposal'] == meta['model_proposal'] and meta['model_proposal'] in options
    assert row['usable'] and row['outer_truncations'] == 0
    assert row['nested_search'] == {'decisions': 0, 'evaluations': 0, 'truncated': 0}
    outcomes = np.asarray([row['sample_outcomes'][str(i)] for i in options], np.float64)
    assert outcomes.shape == (len(options), 96) and np.isfinite(outcomes).all()
    assert ((outcomes >= 0) & (outcomes <= 1)).all()
    paired = outcomes - outcomes[options.index(meta['model_proposal'])]
    provided = np.asarray([row['paired_advantages_over_proposal'][str(i)] for i in options], np.float64)
    np.testing.assert_array_equal(paired, provided)
    seen = set()
    focal_player = meta['episode']//4 % meta['players']
    roles = ['neural' if mode == 'neural' or seat == focal_player else 'economic' for seat in range(meta['players'])]
    # Collection has checked beliefs against the frozen engine. Here verify the
    # raw outcomes used by the target reduction, including every terminal sample.
    for terminal in row['rollouts']:
        sample, action = terminal['sample'], terminal['actionIndex']
        assert (sample, action) not in seen and 0 <= sample < 96 and action in options
        seen.add((sample, action))
        assert terminal['env'] == sample*len(options) + options.index(action)
        assert not terminal['truncated'] and 0 <= terminal['steps'] <= 2400
        assert terminal['value'] == outcomes[options.index(action), sample]
        assert terminal['roles'] == roles
        assert terminal['searchStats'] == {'decisions': 0, 'evaluations': 0, 'truncated': 0}
        assert terminal['initialBelief']['kind'] == 'policy'
    assert len(seen) == len(options)*96
    keep = {k: row[k] for k in ['rootId', 'mode', 'batch', 'public_root_sha256', 'model_proposal', 'seed', 'samples', 'usable', 'options']}
    keep['paired_advantages_over_proposal'] = {str(i): paired[j] for j, i in enumerate(options)}
    return keep


def target_arrays(bank, metadata, mask, noise_floor=.05, minimum_weight=.25):
    assert set(bank) == {m['rootId'] for m in metadata}
    n, width = mask.shape
    assert n == len(metadata)
    result = {key: np.zeros((n, width), np.float64) for key in ['target', 'precision', 'variance_of_mean', 'target_a', 'target_b']}
    for i, meta in enumerate(metadata):
        rows = bank[meta['rootId']]
        assert set(rows) == {(m, b) for m in MODES for b in BATCHES}
        t = targets(rows, noise_floor, minimum_weight)
        assert t['samples'] == 192
        options = rows[MODES[0], BATCHES[0]]['options']
        order = np.argsort(options)
        assert sorted(options) == meta['options']
        size = len(options)
        assert mask[i].tolist() == [True]*size + [False]*(width-size)
        for key in ['target', 'precision', 'variance_of_mean']:
            result[key][i, :size] = t[key][order]
        for batch in BATCHES:
            matched_worlds = np.mean([[rows[mode, batch]['paired_advantages_over_proposal'][str(j)] for j in options] for mode in MODES], axis=0)
            result['target_' + batch][i, :size] = matched_worlds.mean(1)[order]
        np.testing.assert_allclose(result['target'][i], (result['target_a'][i] + result['target_b'][i])/2, atol=1e-15, rtol=1e-15)
        parent = meta['options'].index(meta['model_proposal'])
        assert result['target'][i, parent] == result['variance_of_mean'][i, parent] == 0
    return result


def load_labels(manifest, metadata, *, local_verified=True):
    p, source = read(PROTOCOL), read(SOURCE)
    validate_manifest(manifest, p, source)
    assert len(metadata) == 17280 and len({m['rootId'] for m in metadata}) == 17280
    index = {m['rootId']: m for m in metadata}
    assert Counter(m['split'] for m in metadata) == {'train': 12960, 'validation': 4320}
    shards = []
    for old in p['reuse_pilot']:
        n, behavior, opponent, mode = old['case']
        shards.append({'id': old['id'], 'mode': mode, 'root_ids': old['root_ids'],
                       'source_revision': p['base_source']['revision'], 'source_sha256': p['base_source']['sha256'],
                       'protocol_sha256': p['pilot_protocol_sha256'], 'pilot': True, **{k: old[k] for k in ['revision', 'prefix', 'artifacts']}})
    for key, case in manifest['cases'].items():
        shards.append({'id': key, 'mode': case['shard']['mode'], 'root_ids': case['shard']['root_ids'],
                       'source_revision': source['revision'], 'source_sha256': source['sha256'],
                       'protocol_sha256': digest(PROTOCOL), 'pilot': False, **{k: case[k] for k in ['revision', 'prefix', 'artifacts']}})
    root_mode_pairs = Counter((rid, s['mode']) for s in shards for rid in s['root_ids'])
    assert root_mode_pairs == Counter((rid, mode) for rid in index for mode in MODES)
    bank = defaultdict(dict)
    rollouts = 0
    for serial, shard in enumerate(shards):
        local = ROOT/('ai/runs/policy-iteration-teacher-pilot-verified-v2' if shard['pilot'] else 'ai/runs/policy-iteration-labels-verified-v2')/shard['id']
        files = {}
        for file in ['label-check.json', 'labels.jsonl.gz']:
            path = local/file
            if not local_verified or not path.exists():
                path = Path(hf_hub_download(p['repo'], shard['prefix'] + '/' + file, revision=shard['revision']))
            assert digest(path) == shard['artifacts'][file]
            files[file] = path
        status = read(files['label-check.json'])
        assert status['status'] == 'complete' and status['source_revision'] == shard['source_revision']
        assert status['source_sha256'] == shard['source_sha256'] and status['protocol_sha256'] == shard['protocol_sha256']
        assert status['model_sha256'] == p['model']['sha256']
        assert status['stage'] == ('pilot' if shard['pilot'] else 'full')
        assert status['summary']['roots'] == len(shard['root_ids']) and status['summary']['samples_per_batch'] == 96
        seen = set()
        with gzip.open(files['labels.jsonl.gz'], 'rt') as f:
            for row in map(json.loads, f):
                rid, mode, batch = row['rootId'], row['mode'], row['batch']
                assert rid in shard['root_ids'] and mode == shard['mode']
                assert (rid, batch) not in seen and (mode, batch) not in bank[rid]
                seen.add((rid, batch))
                bank[rid][mode, batch] = packed_row(row, index[rid], mode)
                rollouts += len(row['rollouts'])
        assert seen == {(rid, batch) for rid in shard['root_ids'] for batch in BATCHES}
        if (serial+1) % 30 == 0:
            print({'label_shards_loaded': serial+1, 'planned': len(shards), 'positions_seen': len(bank)}, flush=True)
    assert set(bank) == set(index)
    assert rollouts == manifest['rollouts']
    return bank
