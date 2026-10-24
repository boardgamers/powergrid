"""Capture complete public economy traces for the existing fixed replay selection."""
import argparse
import os
from pathlib import Path
import sys
import time

from strategic_collection import ROOT, read, write, digest, get_model
sys.path.insert(0, str(ROOT/'ai'))
from infer import Model
from pool import EnginePool
from feature_contract import model_revision


def main(previous, output):
    selection = read(previous/'selection.json')
    assessment = read(previous/'assessment.json')
    assert assessment['all_terminal_replays_match']
    assert digest(previous/'selection.json') == assessment['selection_sha256']
    assert digest(previous/'replays.json') == assessment['results_sha256']
    runtime = previous/'runtime'
    assert all(digest(runtime/name) == sha for name, sha in selection['runtime_hashes'].items())
    assert selection['source'] == read(ROOT/'ai/strong/policy-iteration-development-source-v2.json')
    prepared = ROOT/'ai/runs/policy-iteration-trained-8840u-prepared-v2'
    models = {'parent': get_model(read(ROOT/'ai/strong/policy-iteration-labels-protocol-v2.json'))}
    for key in selection['models']:
        if key != 'parent':
            models[key] = Model(prepared/('local-package-'+key)/'policy.onnx')
        assert models[key].sha256 == selection['models'][key]
    output.mkdir(parents=True, exist_ok=False)
    trace_script = ROOT/'ai/strong/trace-public-economy.cjs'
    code_hashes = {str(p.relative_to(ROOT)): digest(p) for p in [Path(__file__), trace_script]}
    old = {key: os.environ.get(key) for key in ['NODE_OPTIONS', 'PG_TRACE_PATH', 'PG_DIAGNOSTIC_RUNTIME']}
    assert not old['NODE_OPTIONS']
    results = {}
    try:
        os.environ['NODE_OPTIONS'] = '--require '+str(trace_script)
        os.environ['PG_DIAGNOSTIC_RUNTIME'] = str(runtime)
        for name, request in selection['requested'].items():
            expected, model = request['expected'], models[request['model']]
            trace = output/(name+'.jsonl')
            trace.touch(exist_ok=False)
            os.environ['PG_TRACE_PATH'] = str(trace)
            seed = expected['gameSeed'].rsplit('-', 1)[0]
            assert seed == 'policy-iteration-development-v2-5p'
            pool = EnginePool(1, seed=seed, script=str(runtime/'ai/strong/bridge.cjs'))
            ended = []
            started = time.perf_counter()
            try:
                response = pool.call({'op': 'reset', 'n': 1, 'playerCount': 5,
                    'offset': expected['episode'], 'mode': 'legacy', 'arenaSeed': seed,
                    'featureRevisions': {'learner': model_revision(model)}})
                ended.extend(response['ended'])
                while response['observations'][0] is not None:
                    row = response['observations'][0]
                    action, _ = model.predict(row['state'], row['actions'])
                    response = pool.call({'op': 'step', 'actions': [action]})
                    ended.extend(response['ended'])
            finally:
                pool.close()
            assert len(ended) == 1
            fields = ['episode', 'gameSeed', 'truncated', 'value', 'playerCount', 'variant',
                      'sealed', 'steps', 'roles', 'policyMoves', 'searchStats', 'final']
            differences = [k for k in fields if ended[0][k] != expected[k]]
            results[name] = {'exact_terminal_replay': not differences, 'differences': differences,
                'actual': ended[0], 'trace_sha256': digest(trace),
                'moves_logged': sum(1 for _ in trace.open()), 'seconds': time.perf_counter()-started}
            write(output/'replays.json', results)
            assert not differences, 'Enhanced observer changes the frozen outcome'
            assert results[name]['moves_logged'] == expected['steps'], 'Missing or extra root moves'
            print({'case': name, 'exact_terminal_replay': True, 'all_root_moves_logged': True}, flush=True)
    finally:
        for key, value in old.items():
            if value is None: os.environ.pop(key, None)
            else: os.environ[key] = value
    assert all(digest(ROOT/name) == sha for name, sha in code_hashes.items())
    assert all(digest(runtime/name) == sha for name, sha in selection['runtime_hashes'].items())
    write(output/'assessment.json', {'exact_replays': len(results), 'all_root_moves_logged': True,
        'all_terminal_replays_match': True, 'code_hashes': code_hashes,
        'previous': str(previous.relative_to(ROOT)), 'source': selection['source'],
        'selection_sha256': digest(previous/'selection.json'), 'results_sha256': digest(output/'replays.json'),
        'new_strength_games': 0, 'gradients': False, 'candidate_selected': False,
        'qualification_eligible': False, 'reserved_final_seeds_used': False})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--previous', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    main(args.previous.resolve(), args.output.resolve())
