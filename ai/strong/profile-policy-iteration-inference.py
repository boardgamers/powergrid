"""Inference-only CPU concurrency probe; never changes an admitted evaluator."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import platform
import statistics
import time

import numpy as np
from strategic_collection import ROOT, read, write, digest, get_model
from sealed_belief_teacher import Node, predict_batch, REVISION


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('output')
    args = parser.parse_args()
    p = read(ROOT/'ai/strong/policy-iteration-teacher-protocol-v2.json')
    model = get_model(p)
    fixture = ROOT/'ai/strong/fixtures/multiplayer-serving-v1.jsonl'
    node = Node('strong/worker.cjs')
    rows = []
    try:
        for line in fixture.read_text().splitlines():
            request = json.loads(line)['request']
            row = node.call({**request, 'featureRevision': REVISION})
            assert 'error' not in row and row['featureRevision'] == REVISION
            rows.append(row)
    finally:
        node.close()
    assert len(rows) == 2553
    reference = predict_batch(model, rows)
    chunks = [rows[i:i+64] for i in range(0, len(rows), 64)]
    timings = {str(n): [] for n in [1, 2, 4, 8]}
    pools = {n: ThreadPoolExecutor(max_workers=n) for n in [2, 4, 8]}
    try:
        # Alternate order to reduce systematic warm-up/thermal ordering effects.
        for repeat in range(4):
            for n in ([1, 2, 4, 8] if repeat % 2 == 0 else [8, 4, 2, 1]):
                start = time.perf_counter()
                if n == 1:
                    actual = predict_batch(model, rows)
                else:
                    actual = [i for part in pools[n].map(lambda chunk: predict_batch(model, chunk), chunks) for i in part]
                elapsed = time.perf_counter() - start
                assert actual == reference, 'Parallel fixed batches changed a decision'
                timings[str(n)].append(elapsed)
                print({'threads': n, 'repeat': repeat, 'seconds': elapsed}, flush=True)
        # Compare every raw ONNX score/value, not only the selected move.
        inputs = []
        for chunk in chunks:
            counts = [len(r['actions']) for r in chunk]
            actions = np.zeros((len(chunk), max(counts), 100), dtype=np.float32)
            mask = np.zeros(actions.shape[:2], dtype=bool)
            for i, row in enumerate(chunk):
                actions[i, :counts[i]] = row['actions']
                mask[i, :counts[i]] = True
            inputs.append({'state': np.asarray([r['state'] for r in chunk], dtype=np.float32), 'actions': actions, 'mask': mask})
        raw_reference = [model.session.run(None, x) for x in inputs]
        for n, pool in pools.items():
            outputs = list(pool.map(lambda x: model.session.run(None, x), inputs))
            for expected, actual in zip(raw_reference, outputs):
                for a, b in zip(expected, actual):
                    np.testing.assert_array_equal(a, b)
    finally:
        for pool in pools.values():
            pool.shutdown()
    medians = {n: statistics.median(v) for n, v in timings.items()}
    report = {'positions': 2553, 'model_sha256': model.sha256, 'fixtures_sha256': digest(fixture),
              'feature_revision': REVISION, 'platform': platform.platform(),
              'times_seconds': timings, 'median_seconds': medians,
              'speedup': {n: medians['1']/v for n, v in medians.items()},
              'fixed_batch_size': 64, 'all_decisions_identical': True, 'all_raw_outputs_identical': True,
              'scope': 'Local CPU inference microbenchmark only, not full-game teacher throughput, HF performance, 8840U acceptance, gradients, or model strength.',
              'gradients': False, 'qualification_eligible': False}
    write(args.output, report)
    print({'speedup': report['speedup'], 'parity': True}, flush=True)


if __name__ == '__main__':
    main()
