"""Serial versus concurrent fixed-batch inference in identical full continuations."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
import gzip
import hashlib
import json
import os
from pathlib import Path
import time

from huggingface_hub import HfApi
from strategic_collection import ROOT, read, write, digest, get_model
import sealed_belief_teacher as teacher

PROTOCOL = ROOT/'ai/strong/policy-iteration-inference-profile-protocol-v2.json'


@contextmanager
def fixed_batches(threads):
    """A process-local diagnostic wrapper; no frozen source file is modified."""
    assert threads in [1, 4]
    original = teacher.predict_batch
    assert original.__module__ == 'sealed_belief_teacher'
    pool = ThreadPoolExecutor(max_workers=threads) if threads > 1 else None
    transcript = hashlib.sha256()
    stats = {'calls': 0, 'decisions': 0}

    def predict(model, rows, batch_size=64):
        assert batch_size == 64
        if pool is None or len(rows) <= 64:
            choices = original(model, rows, batch_size)
        else:
            parts = [rows[start:start+64] for start in range(0, len(rows), 64)]
            choices = [index for result in pool.map(lambda part: original(model, part, 64), parts) for index in result]
        stats['calls'] += 1
        stats['decisions'] += len(choices)
        transcript.update(json.dumps(choices, separators=(',', ':')).encode() + b'\n')
        return choices

    teacher.predict_batch = predict
    try:
        yield stats
    finally:
        teacher.predict_batch = original
        if pool is not None:
            pool.shutdown()
        stats['choice_transcript_sha256'] = transcript.hexdigest()


def comparable(row):
    result = {k: v for k, v in row.items() if k != 'timing'}
    result['rollouts'] = sorted(result['rollouts'], key=lambda r: r['env'])
    return result


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--small', action='store_true')
    parser.add_argument('--upload', action='store_true')
    args = parser.parse_args()
    p = read(PROTOCOL)
    base = read(ROOT/'ai/strong/policy-iteration-teacher-protocol-v2.json')
    assert digest(ROOT/'ai/strong/policy-iteration-teacher-protocol-v2.json') == p['teacher_protocol_sha256']
    assert digest(ROOT/base['roots']['file']) == base['roots']['sha256']
    with gzip.open(ROOT/base['roots']['file'], 'rt') as f:
        roots = {r['rootId']: r for r in map(json.loads, f) if r['rootId'] in p['root_ids']}
    assert set(roots) == set(p['root_ids'])
    model = get_model(base)
    node = teacher.Node('strong/sealed-belief-continuations.cjs')
    args.output.mkdir(parents=True, exist_ok=False)
    samples = 2 if args.small else 96
    records = []
    started = time.monotonic()
    try:
        with gzip.open(args.output/'continuations.jsonl.gz', 'wt') as f:
            for rid in p['root_ids']:
                root = roots[rid]
                options = teacher.prepare(node, model, root)
                for mode in base['modes']:
                    outputs, stats = {}, {}
                    for threads in ([1, 4] if root['players'] == 2 else [4, 1]):
                        with fixed_batches(threads) as trace:
                            row = teacher.evaluate(model, root, options, mode, 'a', samples, 24, belief='policy')
                        assert row['usable']
                        outputs[threads], stats[threads] = row, trace
                    assert comparable(outputs[1]) == comparable(outputs[4])
                    assert stats[1] == stats[4], 'A policy decision changed inside the continuation'
                    record = {'rootId': rid, 'players': root['players'], 'mode': mode, 'samples': samples,
                              'rollouts_per_condition': len(outputs[1]['rollouts']), 'all_outcomes_identical': True,
                              'choice_trace': stats[1], 'serial': outputs[1]['timing'], 'concurrent': outputs[4]['timing'],
                              'wall_speedup': outputs[1]['timing']['seconds']/outputs[4]['timing']['seconds'],
                              'policy_speedup': outputs[1]['timing']['policy_seconds']/outputs[4]['timing']['policy_seconds']}
                    records.append(record)
                    f.write(json.dumps({'record': record, 'serial': outputs[1], 'concurrent': outputs[4]}) + '\n')
                    f.flush()
                    print(record, flush=True)
    finally:
        node.close()
    report = {'passed': True, 'small': args.small, 'protocol_sha256': digest(PROTOCOL), 'model_sha256': model.sha256,
              'source_revision': os.environ.get('SOURCE_REVISION'), 'source_sha256': os.environ.get('SOURCE_SHA256'),
              'records': records, 'rollouts': sum(2*r['rollouts_per_condition'] for r in records),
              'total_seconds': time.monotonic() - started, 'cpu_count': os.cpu_count(),
              'affinity_count': len(os.sched_getaffinity(0)), 'artifacts': {'continuations.jsonl.gz': digest(args.output/'continuations.jsonl.gz')},
              'gradients': False, 'qualification_eligible': False}
    write(args.output/'profile.json', report)
    if args.upload:
        assert not args.small
        HfApi().upload_folder(repo_id=base['repo'], folder_path=args.output, path_in_repo='runs/policy-iteration-inference-hf-profile-v2')
    print({'passed': True, 'rollouts': report['rollouts']}, flush=True)


if __name__ == '__main__':
    main()
