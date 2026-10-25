"""Paired batching experiment on four saved stress roots, with every choice checked."""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import sys
import time

from bucketed_inference_v1 import predict_bucketed, padded_actions


def read(path):
    return json.loads(path.read_text())


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def semantic(row):
    row = json.loads(json.dumps(row, allow_nan=False))
    result = {key: value for key, value in row.items() if key not in ('decision', 'round', 'elapsedMs')}
    result['resourcePlan'] = {key: value for key, value in result['resourcePlan'].items() if key != 'elapsedMs'}
    return result


@contextmanager
def compare_predictions(stream, records):
    import resource_turn_search_v1 as resource
    import population_hybrid_policy as population
    saved = []
    for module in [resource, population]:
        original = module.predict_batch
        def paired(model, rows, batch_size=64, _original=original, _module=module.__name__):
            record = {'call': len(records), 'module': _module, 'rows': len(rows),
                      'batch_size': batch_size, 'counts': [len(row['actions']) for row in rows]}
            record['observations_sha256'] = hashlib.sha256(json.dumps(rows, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()
            order = ['baseline', 'bucketed'] if len(records) % 2 == 0 else ['bucketed', 'baseline']
            record['execution_order'] = order
            choices = {}
            for label in order:
                began = time.perf_counter()
                choices[label] = (_original(model, rows, batch_size=batch_size) if label == 'baseline'
                                  else predict_bucketed(_original, model, rows, batch_size=batch_size))
                record[label + '_seconds'] = time.perf_counter() - began
            record['choices'] = choices
            record['exact_choices'] = choices['baseline'] == choices['bucketed']
            record['baseline_padded_actions'] = padded_actions(rows, batch_size)
            record['bucketed_padded_actions'] = padded_actions(sorted(rows, key=lambda row: len(row['actions'])), batch_size)
            stream.write(json.dumps(record, allow_nan=False) + '\n')
            stream.flush()
            records.append(record)
            assert record['exact_choices'], 'Batch regrouping changed a choice; preserve and investigate'
            return choices['baseline']
        saved.append((module, original))
        module.predict_batch = paired
    try:
        yield
    finally:
        for module, original in saved:
            module.predict_batch = original


def run(package, output):
    manifest = read(package / 'manifest.json')
    assert all(digest(package / name) == sha for name, sha in manifest['files'].items())
    assert manifest['samples'] == 4 and manifest['max_steps'] == 2400
    sys.path.insert(0, str(package / 'ai/strong'))
    from hybrid_search import Model
    from resource_replanning_policy_v1 import ResourceReplanningPolicy
    selected = read(package / 'slow-roots.json')
    assert len(selected) == 4
    output.mkdir(parents=True, exist_ok=False)
    write(output / 'inputs.json', selected)
    status = {'stage': 'running', 'pid': os.getpid(), 'started_at': datetime.now(timezone.utc).isoformat(),
              'host': platform.node(), 'manifest_sha256': digest(package / 'manifest.json'),
              'runner_sha256': digest(__file__),
              'candidate_sha256': digest(Path(__file__).with_name('bucketed_inference_v1.py')),
              'threads': 1, 'workers': 1, 'samples': 4, 'roots': {},
              'new_arena_games': 0, 'new_hf_jobs': 0, 'gradients': False,
              'policy_adopted': False, 'qualification_eligible': False, 'reserved_final_seeds_used': False,
              'scope': 'Paired engineering comparison on four old selected stress roots, shared local HX370. Every model choice is compared; baseline choices advance the simulation. Alternating timing order reduces order bias but does not establish representative latency or target-hardware speed.'}
    write(output / 'status.json', status)
    model = Model(package / 'policy.onnx', threads=1)
    assert model.sha256 == manifest['model_sha256']
    policy = None
    try:
        policy = ResourceReplanningPolicy(model, package / 'ai/strong/population-hybrid-policy.cjs',
            arm='resource-filter', samples=4, workers=1, max_steps=2400)
        for case, entry in selected.items():
            records = []
            with (output / (case + '-calls.jsonl')).open('x') as stream, compare_predictions(stream, records):
                result = policy.choose(entry['request'])
            write(output / (case + '-result.json'), result)
            assert semantic(result) == semantic(entry['reference'])
            assert result['search']['usable'] and result['search']['truncated'] == 0
            totals = {key: sum(row[key] for row in records) for key in ('rows', 'baseline_seconds', 'bucketed_seconds', 'baseline_padded_actions', 'bucketed_padded_actions')}
            totals.update(calls=len(records), exact_all_choices=True, exact_recorded_result=True,
                          rollouts=result['search']['evaluations'], neural_decisions=result['search']['neuralDecisions'])
            status['roots'][case] = totals
            write(output / 'status.json', status)
            print({'case': case, **totals}, flush=True)
        assert all(digest(package / name) == sha for name, sha in manifest['files'].items())
        status['stage'] = 'complete'
    except BaseException as error:
        status.update(stage='failed', error=type(error).__name__ + ': ' + str(error))
        raise
    finally:
        if policy is not None:
            policy.close()
        status['finished_at'] = datetime.now(timezone.utc).isoformat()
        status['output_hashes'] = {p.name: digest(p) for p in output.iterdir() if p.is_file() and p.name != 'status.json'}
        write(output / 'status.json', status)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--package', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    run(args.package.resolve(), args.output.resolve())
