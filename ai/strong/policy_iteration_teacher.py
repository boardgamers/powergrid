"""Broader paired targets with public policy beliefs and frozen-parent proposals."""
import argparse
from collections import Counter
import gzip, json, os, time
from pathlib import Path
from huggingface_hub import HfApi
from strategic_collection import ROOT, read, write, digest, get_model, request_hash
from sealed_belief_teacher import Node, prepare, evaluate, REVISION, predict_batch

PROTOCOL = ROOT/'ai/strong/policy-iteration-teacher-protocol-v2.json'
META = ['players', 'behavior', 'mode', 'deal', 'split', 'variant', 'sealed', 'decision', 'round']
case_name = lambda n, behavior, opponent, mode: f'{n}p-{behavior}-{opponent}-{mode}'
prefix = lambda stage, case: 'runs/policy-iteration-teacher-v2-' + stage + '-' + case


def load_roots(n, behavior, opponent):
    p = read(PROTOCOL); path = ROOT/p['roots']['file']
    assert digest(path) == p['roots']['sha256']
    ids = {r['rootId']: r for r in p['pilot_roots'] if r['players'] == n and r['behavior'] == behavior and r['mode'] == opponent}
    assert len(ids) == 12
    with gzip.open(path, 'rt') as f: roots = [r for r in map(json.loads, f) if r['rootId'] in ids]
    assert len(roots) == 12
    assert {(r['variant'], r['sealed'], r['decision']) for r in roots} == {
        (v, s, k) for v in p['variants'] for s in [False, True] for k in p['decisions']}
    for r in roots:
        assert all(r[k] == v for k, v in ids[r['rootId']].items())
        assert request_hash(r['request']) == r['public_root_sha256']
        assert r['split'] == ('validation' if r['deal'] in [0, 4, 8, 12] else 'train')
        assert r['gameSeed'].startswith('policy-iteration-training-v2-')
    return roots


def check_rows(rows, roots, mode, stage, p, model, node, trace_node):
    samples = p['samples'][stage]; by_id = {r['rootId']: r for r in roots}
    seen = set(); total = 0; timings = []; options_by_root = {}
    for row in rows:
        rid, batch = row['rootId'], row['batch']; key = rid, batch
        assert key not in seen and rid in by_id and batch in ['a', 'b']; seen.add(key)
        root = by_id[rid]; options = prepare(node, model, root); options_by_root[rid] = options
        assert row['options'] == options and row['model_proposal'] == root['model_proposal']
        assert row['public_root_sha256'] == root['public_root_sha256'] and row['split'] == root['split']
        assert row['root_metadata'] == {k: root[k] for k in META}
        assert row['mode'] == mode and row['belief'] == 'policy' and row['samples'] == samples
        assert row['seed'] == 'strategic-teacher-public-v1-' + rid + '-' + batch
        assert row['usable'] and row['outer_truncations'] == 0
        assert row['nested_search'] == {'decisions': 0, 'evaluations': 0, 'truncated': 0}
        q = node.call({'op': 'prepare', **root['request'], 'featureRevision': REVISION})
        neural = {}
        if mode == 'neural':
            for prior in q['prior']:
                x = prior['encoded']; choice = model.predict(x['state'], x['actions'])[0]
                assert predict_batch(model, [x])[0] == choice
                neural[str(prior['actor'])] = x['moves'][choice]
        assert row['neural_beliefs'] == neural and row['prior_actors'] == [x['actor'] for x in q['prior']]
        traces = trace_node.call({**root['request'], 'samples': samples, 'seed': row['seed'],
                                  'mode': mode, 'neuralBeliefs': neural})['traces']
        outcomes = {str(i): [None]*samples for i in options}; identities = set()
        for r in row['rollouts']:
            sample, index = r['sample'], r['actionIndex']; identity = sample, index
            assert identity not in identities and 0 <= sample < samples and index in options; identities.add(identity)
            assert r['env'] == sample*len(options) + options.index(index)
            assert not r['truncated'] and 0 <= r['value'] <= 1 and 0 <= r['steps'] <= 2400
            assert r['roles'] == ['neural' if mode == 'neural' or i == root['request']['player'] else 'economic' for i in range(root['players'])]
            assert r['searchStats'] == {'decisions': 0, 'evaluations': 0, 'truncated': 0}
            assert r['initialBelief'] == {'kind': 'policy', 'committed': traces[sample]}
            outcomes[str(index)][sample] = r['value']
        assert len(identities) == samples*len(options) and outcomes == row['sample_outcomes']
        base = outcomes[str(root['model_proposal'])]
        assert row['paired_advantages_over_proposal'] == {str(i): [v-b for v, b in zip(outcomes[str(i)], base)] for i in options}
        total += len(identities); timings.append({'rootId': rid, 'batch': batch, **row['timing']})
    assert seen == {(r['rootId'], b) for r in roots for b in ['a', 'b']}
    return {'roots': len(roots), 'searches': len(rows), 'rollouts': total, 'samples_per_batch': samples,
            'root_splits': dict(Counter(r['split'] for r in roots)), 'timings': timings,
            'options_by_root': options_by_root, 'game_truncations': 0, 'gradients': False, 'qualification_eligible': False}


def verify(out, n, behavior, opponent, mode, stage):
    p = read(PROTOCOL); roots = load_roots(n, behavior, opponent); model = get_model(p)
    status = read(out/'label-check.json'); assert status['status'] == 'complete'
    for k, v in {'players': n, 'behavior': behavior, 'opponent': opponent, 'mode': mode, 'stage': stage,
                 'protocol_sha256': digest(PROTOCOL), 'model_sha256': model.sha256}.items(): assert status[k] == v
    assert set(status['artifacts']) == {'labels.jsonl.gz'}
    for name, sha in status['artifacts'].items(): assert digest(out/name) == sha
    with gzip.open(out/'labels.jsonl.gz', 'rt') as f: rows = list(map(json.loads, f))
    node = Node('strong/sealed-belief-continuations.cjs'); trace = Node('strong/policy-iteration-belief-traces.cjs')
    try: summary = check_rows(rows, roots, mode, stage, p, model, node, trace)
    finally: node.close(); trace.close()
    assert summary == status['summary']; return summary


def run(n, behavior, opponent, mode, stage, out, upload):
    p = read(PROTOCOL); assert mode in p['modes'] and stage in p['samples']
    roots = load_roots(n, behavior, opponent); model = get_model(p); out.mkdir(parents=True, exist_ok=False)
    node = Node('strong/sealed-belief-continuations.cjs'); trace = Node('strong/policy-iteration-belief-traces.cjs')
    start = time.monotonic(); rows = []
    status = {'status': 'running', 'players': n, 'behavior': behavior, 'opponent': opponent, 'mode': mode, 'stage': stage,
              'protocol_sha256': digest(PROTOCOL), 'source_revision': os.environ.get('SOURCE_REVISION'),
              'source_sha256': os.environ.get('SOURCE_SHA256'), 'model_sha256': model.sha256,
              'gradients': False, 'qualification_eligible': False}
    try:
        with gzip.open(out/'labels.jsonl.gz', 'wt') as f:
            for root in roots:
                options = prepare(node, model, root)
                for batch in ['a', 'b']:
                    row = evaluate(model, root, options, mode, batch, p['samples'][stage], p['workers'], belief='policy')
                    assert row['usable'], 'Truncations cannot become training labels'
                    row['root_metadata'] = {k: root[k] for k in META}
                    f.write(json.dumps(row)+'\n'); f.flush(); rows.append(row)
                    print({'root': root['rootId'], 'batch': batch, 'searches': len(rows), 'seconds': time.monotonic()-start}, flush=True)
        summary = check_rows(rows, roots, mode, stage, p, model, node, trace)
        status.update(status='complete', summary=summary, seconds=time.monotonic()-start)
    except BaseException as e: status.update(status='failed', error=type(e).__name__+': '+str(e)); raise
    finally:
        node.close(); trace.close(); status['artifacts'] = {f.name: digest(f) for f in out.iterdir() if f.is_file()}
        write(out/'label-check.json', status)
        if upload: HfApi().upload_folder(repo_id=p['repo'], folder_path=out, path_in_repo=prefix(stage, case_name(n, behavior, opponent, mode)))
    print(status, flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(__doc__); p.add_argument('players', type=int, choices=range(2, 7))
    p.add_argument('behavior', choices=['parent', '11101', '11102']); p.add_argument('opponent', choices=['economic', 'snapshot0'])
    p.add_argument('mode', choices=['neural', 'neural_economic']); p.add_argument('stage', choices=['probe', 'pilot']); p.add_argument('output', type=Path)
    p.add_argument('--verify', action='store_true'); p.add_argument('--upload', action='store_true'); a = p.parse_args()
    args = a.output, a.players, a.behavior, a.opponent, a.mode, a.stage
    if a.verify: print(json.dumps(verify(*args)))
    else: run(a.players, a.behavior, a.opponent, a.mode, a.stage, a.output, a.upload)
