"""Exactly replay bounded changed-outcome examples from the five-player diagnosis.

Hash-select at most one win lost and one win gained per rule and model. These
outcome-selected examples explain failures; they are never strength estimates.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import tarfile
import time

from huggingface_hub import hf_hub_download
from strategic_collection import ROOT, read, write, digest, get_model

sys.path.insert(0, str(ROOT/'ai'))
from infer import Model
from pool import EnginePool
from feature_contract import model_revision


def identity(row):
    return row['gameSeed'], row['seat'], row['variant'], row['sealed']


def main(diagnosis, output):
    report = read(diagnosis)
    snapshot = ROOT/report['snapshot_path']
    assert digest(snapshot) == report['snapshot_sha256']
    original = read(snapshot)
    assert not report['candidate_selected'] and not report['reserved_final_seeds_used']
    for name, sha in report['code_hashes'].items():
        assert digest(ROOT/name) == sha
    source = read(ROOT/'ai/strong/policy-iteration-development-source-v2.json')
    assert source == original['source']
    prepared = ROOT/'ai/runs/policy-iteration-trained-8840u-prepared-v2'
    manifest = read(prepared/'manifest.json')
    assert manifest['source'] == source and manifest['training_verified']
    archive = hf_hub_download('coyotte508/powergrid-ai-training-v1', source['archive'],
                              repo_type='dataset', revision=source['revision'])
    assert digest(archive) == source['sha256']
    runtime_source = prepared/'frozen-source'
    output.mkdir(parents=True, exist_ok=False)
    runtime = output/'runtime'
    shutil.copytree(runtime_source/'engine', runtime/'engine')
    (runtime/'ai/strong').mkdir(parents=True)
    shutil.copy2(runtime_source/'ai/core.cjs', runtime/'ai/core.cjs')
    for path in (runtime_source/'ai/strong').glob('*.cjs'):
        shutil.copy2(path, runtime/'ai/strong'/path.name)
    runtime_hashes = {str(p.relative_to(runtime)): digest(p)
                      for p in runtime.rglob('*') if p.is_file()}
    with tarfile.open(archive) as bundle:
        members = {m.name.removeprefix('./'): m for m in bundle.getmembers()}
        for name, sha in runtime_hashes.items():
            assert members[name].isfile()
            assert hashlib.sha256(bundle.extractfile(members[name]).read()).hexdigest() == sha, name
    trace_source = ROOT/'ai/strong/trace-public-game.cjs'
    trace_script = runtime/'ai/strong/diagnostic-trace.cjs'
    shutil.copy2(trace_source, trace_script)
    models = {'parent': get_model(read(ROOT/'ai/strong/policy-iteration-labels-protocol-v2.json'))}
    for key, item in manifest['models'].items():
        assert item['pin'] == original['pins'][key]
        model = Model(prepared/('local-package-'+key)/'policy.onnx')
        assert model.sha256 == item['pin']['files']['inference64.onnx']
        models[key] = model
    assert models['parent'].sha256 == original['pins']['parent']['files']['inference64.onnx']
    raw = {}
    for key in models:
        raw[key] = {}
        for case, proof in original['provenance'][key].items():
            if '-5p-legacy-' not in case:
                continue
            directory = ROOT/'ai/runs/policy-iteration-development-verified-v2'/case
            assert digest(directory/'evaluation.json') == proof['evaluation_sha256']
            assert digest(directory/'verified.json') == proof['verified_sha256']
            for row in read(directory/'evaluation.json')['results']:
                assert identity(row) not in raw[key]
                raw[key][identity(row)] = row
        assert len(raw[key]) == 320
    pairs, requested = [], {}
    for key, cells in report['comparisons'].items():
        for rule, view in cells['legacy/5p']['by_rules'].items():
            for direction, changed in view['changed_outcomes'].items():
                if not changed:
                    continue
                rank = lambda r: hashlib.sha256(json.dumps(
                    ['legacy-replay-v1', r['game_seed'], r['seat'], r['variant'], r['sealed']],
                    separators=(',', ':')).encode()).hexdigest()
                row = min(changed, key=rank)
                identity_key = row['game_seed'], row['seat'], row['variant'], row['sealed']
                chosen = {}
                for arm in ['parent', key]:
                    expected = raw[arm][identity_key]
                    name = arm+'-episode-'+str(expected['episode'])
                    requested[name] = {'model': arm, 'expected': expected}
                    chosen[arm] = name
                pairs.append({'model': key, 'rule': rule, 'direction': direction,
                              'selection_hash': rank(row), 'cases': chosen})
    assert 0 < len(pairs) <= 32 and len(requested) <= 64
    write(output/'selection.json', {'diagnosis_sha256': digest(diagnosis), 'pairs': pairs,
        'requested': requested, 'selection': 'One hash-ranked example per model/rule/outcome-direction; '
            'explicitly outcome-selected diagnostic examples, never a win-rate estimate.',
        'models': {k: m.sha256 for k, m in models.items()}, 'source': source,
        'runtime_hashes': runtime_hashes, 'trace_script_sha256': digest(trace_source),
        'replay_script_sha256': digest(Path(__file__)), 'reserved_final_seeds_used': False})
    prior_options, prior_path = os.environ.get('NODE_OPTIONS'), os.environ.get('PG_TRACE_PATH')
    assert not prior_options, 'Inspect external Node preloads before diagnostic replay'
    results = {}
    try:
        for name, request in requested.items():
            expected, model = request['expected'], models[request['model']]
            trace = output/(name+'.jsonl')
            trace.touch(exist_ok=False)
            os.environ['NODE_OPTIONS'] = '--require '+str(trace_script)
            os.environ['PG_TRACE_PATH'] = str(trace)
            seed = expected['gameSeed'].rsplit('-', 1)[0]
            assert seed == 'policy-iteration-development-v2-5p'
            pool = EnginePool(1, seed=seed, script=str(runtime/'ai/strong/bridge.cjs'))
            ended = []
            start = time.perf_counter()
            try:
                response = pool.call({'op': 'reset', 'n': 1, 'playerCount': 5,
                    'offset': expected['episode'], 'mode': 'legacy', 'arenaSeed': seed,
                    'featureRevisions': {'learner': model_revision(model)}})
                ended.extend(response['ended'])
                while response['observations'][0] is not None:
                    observation = response['observations'][0]
                    action, _ = model.predict(observation['state'], observation['actions'])
                    response = pool.call({'op': 'step', 'actions': [action]})
                    ended.extend(response['ended'])
            finally:
                pool.close()
            assert len(ended) == 1
            keys = ['episode', 'gameSeed', 'truncated', 'value', 'playerCount', 'variant',
                    'sealed', 'steps', 'roles', 'policyMoves', 'searchStats', 'final']
            differences = [k for k in keys if ended[0][k] != expected[k]]
            results[name] = {'exact_terminal_replay': not differences, 'differences': differences,
                'actual': ended[0], 'trace_sha256': digest(trace),
                'moves_logged': sum(1 for _ in trace.open()), 'seconds': time.perf_counter()-start}
            write(output/'replays.json', results)
            print({'case': name, 'exact_terminal_replay': not differences,
                   'moves_logged': results[name]['moves_logged']}, flush=True)
            assert not differences, 'Replay differs from frozen evaluation; stop diagnosis'
    finally:
        for name, value in [('NODE_OPTIONS', prior_options), ('PG_TRACE_PATH', prior_path)]:
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
    assert all(digest(runtime/name) == sha for name, sha in runtime_hashes.items())
    write(output/'assessment.json', {'exact_replays': len(results), 'pairs': len(pairs),
        'all_terminal_replays_match': all(r['exact_terminal_replay'] for r in results.values()),
        'source': source, 'selection_sha256': digest(output/'selection.json'),
        'results_sha256': digest(output/'replays.json'), 'new_strength_games': 0,
        'gradients': False, 'hf_jobs_submitted': 0, 'candidate_selected': False,
        'qualification_eligible': False, 'reserved_final_seeds_used': False})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--diagnosis', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    main(args.diagnosis.resolve(), args.output.resolve())
