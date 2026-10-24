"""Run immutable full-data shards with the unchanged pilot evaluator/checker."""
import argparse
import gzip
import json
import os
import time
from pathlib import Path

from huggingface_hub import HfApi
from strategic_collection import ROOT, read, write, digest, request_hash, get_model
from policy_iteration_teacher import META, check_rows
from sealed_belief_teacher import Node, prepare, evaluate
import importlib.util

_spec = importlib.util.spec_from_file_location('fixed_batch_profile', ROOT/'ai/strong/profile-policy-iteration-continuations.py')
_profile = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_profile)
fixed_batches = _profile.fixed_batches

PROTOCOL = ROOT/'ai/strong/policy-iteration-labels-protocol-v2.json'
PREFIX = 'runs/policy-iteration-labels-v2-'


def load_roots(p, shard):
    path = ROOT/p['roots']['file']
    assert digest(path) == p['roots']['sha256']
    ids = shard['root_ids']
    assert len(set(ids)) == len(ids) and ids
    wanted = set(ids)
    found = {}
    with gzip.open(path, 'rt') as f:
        for row in map(json.loads, f):
            rid = row['rootId']
            if rid in wanted:
                assert rid not in found
                assert row['players'] == shard['players'] and row['behavior'] == shard['behavior']
                assert row['mode'] == shard['opponent']
                assert request_hash(row['request']) == row['public_root_sha256']
                assert row['split'] == ('validation' if row['deal'] in [0, 4, 8, 12] else 'train')
                assert row['gameSeed'].startswith('policy-iteration-training-v2-')
                found[rid] = row
    assert found.keys() == wanted
    return [found[rid] for rid in ids]


def find_shard(p, shard_id):
    matches = [s for s in p['shards'] if s['id'] == shard_id]
    assert len(matches) == 1
    return matches[0]


def check(out, p, shard, stage, model, roots):
    status = read(out/'label-check.json')
    assert status['status'] == 'complete'
    assert status['shard'] == shard and status['stage'] == stage
    assert status['protocol_sha256'] == digest(PROTOCOL) and status['model_sha256'] == model.sha256
    assert set(status['artifacts']) == {'labels.jsonl.gz'}
    assert digest(out/'labels.jsonl.gz') == status['artifacts']['labels.jsonl.gz']
    with gzip.open(out/'labels.jsonl.gz', 'rt') as f:
        rows = list(map(json.loads, f))
    node = Node('strong/sealed-belief-continuations.cjs')
    trace = Node('strong/policy-iteration-belief-traces.cjs')
    try:
        summary = check_rows(rows, roots, shard['mode'], stage, p, model, node, trace)
    finally:
        node.close()
        trace.close()
    assert summary == status['summary']
    return summary


def run(out, p, shard, stage, model, roots, upload=False):
    assert stage in p['samples'] and (not upload or stage == 'full')
    assert p['inference_threads'] == 4 and p['fixed_inference_batch'] == 64
    out.mkdir(parents=True, exist_ok=False)
    node = Node('strong/sealed-belief-continuations.cjs')
    trace = Node('strong/policy-iteration-belief-traces.cjs')
    status = {'status': 'running', 'shard': shard, 'stage': stage,
              'protocol_sha256': digest(PROTOCOL), 'source_revision': os.environ.get('SOURCE_REVISION'),
              'source_sha256': os.environ.get('SOURCE_SHA256'), 'model_sha256': model.sha256,
              'gradients': False, 'qualification_eligible': False}
    started = time.monotonic()
    rows = []
    try:
        with gzip.open(out/'labels.jsonl.gz', 'wt') as f:
            for root in roots:
                options = prepare(node, model, root)
                for batch in p['batches']:
                    with fixed_batches(p['inference_threads']):
                        row = evaluate(model, root, options, shard['mode'], batch, p['samples'][stage], p['workers'], belief='policy')
                    assert row['usable'], 'Truncated continuations cannot become labels'
                    row['root_metadata'] = {k: root[k] for k in META}
                    f.write(json.dumps(row) + '\n')
                    f.flush()
                    rows.append(row)
                    print({'root': root['rootId'], 'batch': batch, 'searches': len(rows),
                           'seconds': time.monotonic() - started}, flush=True)
        summary = check_rows(rows, roots, shard['mode'], stage, p, model, node, trace)
        status.update(status='complete', summary=summary, seconds=time.monotonic() - started)
    except BaseException as error:
        status.update(status='failed', error=type(error).__name__ + ': ' + str(error))
        raise
    finally:
        node.close()
        trace.close()
        status['artifacts'] = {f.name: digest(f) for f in out.iterdir() if f.is_file()}
        write(out/'label-check.json', status)
        if upload:
            HfApi().upload_folder(repo_id=p['repo'], folder_path=out, path_in_repo=PREFIX + shard['id'])
    print({'status': status['status'], 'roots': len(roots), 'rollouts': summary['rollouts']}, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('shard')
    parser.add_argument('output', type=Path)
    parser.add_argument('--verify', action='store_true')
    parser.add_argument('--upload', action='store_true')
    args = parser.parse_args()
    p = read(PROTOCOL)
    shard = find_shard(p, args.shard)
    roots = load_roots(p, shard)
    model = get_model(p)
    if args.verify:
        print(json.dumps(check(args.output, p, shard, 'full', model, roots)))
    else:
        run(args.output, p, shard, 'full', model, roots, args.upload)
