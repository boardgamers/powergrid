"""Compare batching on all 2,553 saved serving positions and old target moves."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import time

from bucketed_inference_v1 import predict_bucketed, padded_actions


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def write(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def run(package, fixtures_file, reference_file, output):
    manifest = read(package / 'manifest.json')
    assert all(digest(package / name) == sha for name, sha in manifest['files'].items())
    fixtures = [json.loads(line) for line in fixtures_file.open()]
    reference = [json.loads(line) for line in reference_file.open()]
    assert len(fixtures) == len(reference) == 2553
    assert [row['fixture_index'] for row in reference] == list(range(2553))
    assert all(row['response']['modelSha256'] == manifest['model_sha256'] for row in reference)
    output.mkdir(parents=True, exist_ok=False)
    status = {'stage': 'running', 'pid': os.getpid(), 'started_at': datetime.now(timezone.utc).isoformat(),
              'runner_sha256': digest(__file__), 'candidate_sha256': digest(Path(__file__).with_name('bucketed_inference_v1.py')),
              'manifest_sha256': digest(package / 'manifest.json'), 'fixtures_sha256': digest(fixtures_file),
              'reference_sha256': digest(reference_file), 'new_games': 0, 'new_hf_jobs': 0,
              'policy_adopted': False, 'gradients': False, 'qualification_eligible': False,
              'reserved_final_seeds_used': False}
    write(output / 'status.json', status)
    sys.path.insert(0, str(package / 'ai/strong'))
    from hybrid_search import Model, Node, predict_batch
    model = Model(package / 'policy.onnx', threads=1)
    node = None
    try:
        node = Node(str(package / 'ai/strong/population-hybrid-policy.cjs'))
        prepared = [node.call({**fixture['request'], 'op': 'prepare', 'featureRevision': '4.3-strategic-correction'}) for fixture in fixtures]
        rows = [item['observation'] for item in prepared]
        write(output / 'preparation.json', {'positions': len(rows), 'observations_sha256': hashlib.sha256(json.dumps(rows, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest(), 'baseline_padded_actions': padded_actions(rows), 'bucketed_padded_actions': padded_actions(sorted(rows, key=lambda row: len(row['actions'])))})
        began = time.perf_counter()
        baseline = predict_batch(model, rows)
        baseline_seconds = time.perf_counter() - began
        began = time.perf_counter()
        candidate = predict_bucketed(predict_batch, model, rows)
        candidate_seconds = time.perf_counter() - began
        write(output / 'choices.json', {'baseline': baseline, 'bucketed': candidate})
        assert baseline == candidate
        counts = Counter()
        for index, (fixture, expected, item, choice) in enumerate(zip(fixtures, reference, prepared, candidate)):
            move = item['moves'][choice]
            assert move == expected['response']['move'], f'Prior target move changed at {index}'
            assert move in fixture['legal']
            state = fixture['request']['state']
            counts[str(len(state['players'])) + 'p/' + state['options']['variant'] + ('/sealed' if state['options'].get('fastBid') else '/open')] += 1
        assert all(digest(package / name) == sha for name, sha in manifest['files'].items())
        status.update(stage='complete', positions=2553, all_batch_choices_exact=True, all_prior_target_moves_exact=True, by_cell=dict(counts), baseline_seconds=baseline_seconds, bucketed_seconds=candidate_seconds, scope='All saved canonical serving positions, unchanged float64 model. Local action parity only; single baseline-then-candidate timing is order-biased, not a speed claim or a new AMD8840U benchmark. No current policy or active experiment changed.')
    except BaseException as error:
        status.update(stage='failed', error=type(error).__name__ + ': ' + str(error))
        raise
    finally:
        if node is not None:
            node.close()
        status['finished_at'] = datetime.now(timezone.utc).isoformat()
        status['output_hashes'] = {p.name: digest(p) for p in output.iterdir() if p.is_file() and p.name != 'status.json'}
        write(output / 'status.json', status)
    print({k: status[k] for k in ['stage', 'positions', 'all_batch_choices_exact', 'all_prior_target_moves_exact', 'baseline_seconds', 'bucketed_seconds', 'by_cell']}, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    for flag in ['package', 'fixtures', 'reference', 'output']:
        parser.add_argument('--' + flag, type=Path, required=True)
    args = parser.parse_args()
    run(args.package.resolve(), args.fixtures.resolve(), args.reference.resolve(), args.output.resolve())
