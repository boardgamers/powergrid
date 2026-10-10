"""Prepare the entire verified label design; partial or overlapping grids fail."""
from collections import Counter, defaultdict
import gzip
import json
from pathlib import Path
import numpy as np
from huggingface_hub import hf_hub_download
from strategic_training_labels import ROOT, PROTOCOL, SOURCE, read, digest, get_model, Node
from strategic_correction_targets import targets, MODES, BATCHES


def expected_keys():
    return {f'{n}p-{family}-{mode}-{start}-{start+2}' for n in range(2,7)
        for family in ['economic','snapshot0'] for mode in MODES for start in range(0,16,2)}


def load(manifest, design):
    p, source = read(PROTOCOL), read(SOURCE)
    assert manifest['all_shards_verified'] and set(manifest['cases']) == expected_keys()
    assert manifest['verified_shards'] == 160 and manifest['complete_mixture_roots'] == 1920
    assert manifest['protocol_sha256'] == digest(PROTOCOL) == design['label_protocol_sha256']
    assert manifest['source_revision'] == source['revision'] and manifest['source_sha256'] == source['sha256']
    pin = read(ROOT/'ai/strong/strategic-teacher-training-roots-v1.json')
    path = ROOT/pin['file']
    if not path.exists():
        path = ROOT/pin['local_file']
    assert digest(path) == pin['sha256'] == design['roots_sha256']
    with gzip.open(path, 'rt') as f:
        root_list = list(map(json.loads, f))
    roots = {r['rootId']: r for r in root_list}
    assert len(roots) == len(root_list) == 1920
    assert Counter(r['split'] for r in root_list) == {'train':1440, 'validation':480}
    public_hashes = {s: {r['public_root_sha256'] for r in root_list if r['split'] == s} for s in ['train','validation']}
    assert not public_hashes['train'] & public_hashes['validation']
    grid = Counter((r['players'],r['mode'],r['deal'],r['variant'],r['sealed'],r['decision']) for r in root_list)
    assert set(grid.values()) == {1}
    assert set(grid) == {(n,f,d,v,s,k) for n in range(2,7) for f in ['economic','snapshot0'] for d in range(16)
        for v in ['original','recharged'] for s in [False,True] for k in ['nomination','bid','building']}
    labels = defaultdict(dict)
    for key, case in sorted(manifest['cases'].items()):
        status_file = Path(hf_hub_download(p['repo'], case['prefix']+'/label-check.json', revision=case['revision']))
        label_file = Path(hf_hub_download(p['repo'], case['prefix']+'/labels.jsonl.gz', revision=case['revision']))
        for name, file in [('label-check.json',status_file), ('labels.jsonl.gz',label_file)]:
            assert digest(file) == case['artifacts'][name]
        status = read(status_file)
        assert status['status'] == 'complete' and status['source_revision'] == source['revision']
        assert status['source_sha256'] == source['sha256'] and status['protocol_sha256'] == digest(PROTOCOL)
        assert status['model_sha256'] == p['model']['sha256'] and status['roots_sha256'] == pin['sha256']
        assert not status['game_truncations'] and not status['nested_truncations']
        assert status['positions'] == 24 and status['searches'] == 48 and status['samples'] == 48
        assert key == f"{status['players']}p-{status['source_mode']}-{status['mode']}-{status['deal_start']}-{status['deal_end']}"
        seen = set()
        with gzip.open(label_file, 'rt') as f:
            for row in map(json.loads, f):
                rid, mode, batch = row['rootId'], row['mode'], row['batch']
                root = roots[rid]
                assert mode == status['mode'] and root['players'] == status['players'] and root['mode'] == status['source_mode']
                assert status['deal_start'] <= root['deal'] < status['deal_end']
                assert root['split'] == row['split'] == ('validation' if root['deal'] in [0,4,8,12] else 'train')
                assert root['public_root_sha256'] == row['public_root_sha256'] and root['model_proposal'] == row['model_proposal']
                assert row['root_metadata'] == {k:root[k] for k in ['players','mode','deal','split','variant','sealed','decision','teacherRootIndex']}
                assert (rid,batch) not in seen and (mode,batch) not in labels[rid]
                seen.add((rid,batch))
                labels[rid][mode,batch] = {k:v for k,v in row.items() if k not in ['rollouts','sample_outcomes']}
        assert len(seen) == 48
    assert set(labels) == set(roots)
    parent = get_model(p)
    node = Node('strong/worker.cjs')
    result = []
    try:
        for root in root_list:
            rows = labels[root['rootId']]
            t = targets(rows, design['uncertainty']['noise_floor'], design['uncertainty']['minimum_weight'])
            row = node.call({**root['request'], 'featureRevision':design['feature_revision']})
            assert row['moves'] == root['legal'] and row['state'][-1] == 1
            assert parent.predict(row['state'][:1216], [a[:100] for a in row['actions']])[0] == root['model_proposal']
            options = rows[MODES[0],BATCHES[0]]['options']
            expected = {i for i,a in enumerate(row['actions']) if a[-1]} | {root['model_proposal']}
            assert set(options) == expected and t['samples'] == 96
            # Serving argmax breaks ties in legal-menu order, so training metrics do too.
            order = np.argsort(options)
            options = sorted(options)
            result.append({'rootId':root['rootId'], 'split':root['split'], 'players':root['players'],
                'decision':root['decision'], 'variant':root['variant'], 'sealed':root['sealed'],
                'source_mode':root['mode'], 'deal':root['deal'], 'state':row['state'],
                'actions':[row['actions'][i] for i in options],
                'target':t['target'][order], 'precision':t['precision'][order],
                'proposal_index':options.index(root['model_proposal'])})
    finally:
        node.close()
    return result


def arrays(rows):
    width = max(len(r['actions']) for r in rows)
    count = len(rows)
    result = {'state':np.asarray([r['state'] for r in rows],np.float32),
        'actions':np.zeros((count,width,101),np.float32), 'mask':np.zeros((count,width),bool),
        'target':np.zeros((count,width),np.float32), 'precision':np.zeros((count,width),np.float32),
        'proposal_index':np.asarray([r['proposal_index'] for r in rows],np.int64)}
    for i,r in enumerate(rows):
        n = len(r['actions'])
        for key in ['actions','target','precision']:
            result[key][i,:n] = r[key]
        result['mask'][i,:n] = True
    return result


def metrics(scores, data, rows, margin):
    proposal = data['proposal_index']
    delta = scores-scores[np.arange(len(scores)),proposal,None]
    delta = np.where(data['mask'],delta,-1e9)
    chosen = delta.argmax(1)
    chosen = np.where(delta.max(1)>margin,chosen,proposal)
    achieved = data['target'][np.arange(len(scores)),chosen]
    best = np.where(data['mask'],data['target'],-1e9).max(1)
    groups = defaultdict(list)
    for i,r in enumerate(rows):
        groups[f"{r['players']}p/{r['variant']}/{'sealed' if r['sealed'] else 'open'}"].append(i)
    return {'roots':len(rows), 'mean_simulated_regret':float((best-achieved).mean()),
        'mean_advantage_over_parent':float(achieved.mean()), 'changed_fraction':float((chosen!=proposal).mean()),
        'by_rules_count':{k:{'roots':len(ids),'mean_advantage_over_parent':float(achieved[ids].mean())}
                         for k,ids in sorted(groups.items())},
        'scope':'Fixed continuation-mixture targets; no real-game strength claim.'}
