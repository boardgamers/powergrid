"""Check real trained hybrid continuations and local cost, without strength claims.

Uses existing serving fixtures, never new training, HF jobs or final-test games.
All models and every cap are retained; no model or search budget is selected.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import platform
import shutil
import time

from strategic_collection import ROOT, read, write, digest, get_model
from hybrid_search import HybridSearch, Model, Node, model_revision, predict_batch, public_seed
import hybrid_search


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    spec = importlib.util.spec_from_file_location('trained_benchmark',
        ROOT/'ai/strong/benchmark-policy-iteration-trained-8840u.py')
    benchmark = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(benchmark)
    manifest = benchmark.prepared_manifest()
    assert manifest['training_verified'] and not manifest['synthetic_untrained']
    frozen = benchmark.PREPARED/'frozen-source'
    for name in ['ai/infer.py', 'ai/pool.py', 'ai/strong/feature_contract.py']:
        assert digest(ROOT/name) == digest(frozen/name), name
    code = [Path(__file__), ROOT/'ai/strong/hybrid_search.py', ROOT/'ai/pool.py',
            ROOT/'ai/infer.py', ROOT/'ai/strong/feature_contract.py',
            ROOT/'ai/strong/hybrid-continuations.cjs']
    hashes = {str(p.relative_to(ROOT)): digest(p) for p in code}
    args.output.mkdir(parents=True, exist_ok=False)
    runtime = args.output.resolve()/'runtime'
    shutil.copytree(frozen/'engine', runtime/'engine')
    (runtime/'ai/strong').mkdir(parents=True)
    shutil.copy2(frozen/'ai/core.cjs', runtime/'ai/core.cjs')
    for path in (frozen/'ai/strong').glob('*.cjs'):
        shutil.copy2(path, runtime/'ai/strong'/path.name)
    runtime_hashes = {str(p.relative_to(runtime)): digest(p)
                      for p in runtime.rglob('*') if p.is_file()}
    assert all(digest(frozen/name) == sha for name, sha in runtime_hashes.items())
    assert not (runtime/'ai/strong/hybrid-continuations.cjs').exists()
    shutil.copy2(ROOT/'ai/strong/hybrid-continuations.cjs', runtime/'ai/strong/hybrid-continuations.cjs')
    # Both Node and EnginePool accept an absolute script path. The adapter's
    # relative imports now resolve only inside the frozen engine snapshot.
    worker = str(runtime/'ai/strong/hybrid-continuations.cjs')
    hybrid_search.WORKER = worker
    fixtures = [json.loads(line) for line in (benchmark.PREPARED/'fixtures.jsonl').open()]
    assert len(fixtures) == 2553
    models = {'parent': get_model(read(ROOT/'ai/strong/policy-iteration-labels-protocol-v2.json'))}
    for key, info in manifest['models'].items():
        path = benchmark.PREPARED/('local-package-'+key)/'policy.onnx'
        assert digest(path) == info['pin']['files']['inference64.onnx']
        models[key] = Model(path)
    report = {'contracts_passed': False, 'all_searches_usable': False,
        'models': {key: model.sha256 for key, model in models.items()},
        'trained_manifest_sha256': digest(benchmark.PREPARED/'manifest.json'),
        'fixture_sha256': manifest['fixtures_sha256'], 'code_hashes': hashes,
        'frozen_runtime_hashes': runtime_hashes, 'runtime_source': manifest['source'],
        'budgets': [1, 8], 'workers': 4, 'max_steps': 2400,
        'batch_checks': {}, 'search_checks': [], 'selected_fixtures': {},
        'host': platform.node(), 'processor': next(line.split(':', 1)[1].strip()
            for line in Path('/proc/cpuinfo').read_text().splitlines() if line.startswith('model name')),
        'gradients': False, 'hf_jobs_submitted': 0, 'candidate_selected': False,
        'qualification_eligible': False, 'reserved_final_seeds_used': False,
        'scope': 'Existing-fixture integration and local timing only. Eighty rule/phase/count cells '
                 'for batched inference; four endpoint Recharged/sealed bid/building positions '
                 'for full continuations. No fresh whole-game strength or AMD8840U timing claim.'}
    node = Node(worker)
    started = time.perf_counter()
    try:
        cells, selected = {}, {}
        for index, fixture in enumerate(fixtures):
            q = fixture['request']; state = q['state']; n = len(state['players'])
            cell = n, state['options']['variant'], bool(state['options']['fastBid']), state['phase']
            cells.setdefault(cell, q)
            if n not in [2, 6] or cell[1:3] != ('recharged', True) or len(fixture['legal']) < 2:
                continue
            names = {move['name'] for move in fixture['legal']}
            phase = 'bid' if 'Bid' in names else 'building' if 'Build' in names else None
            if phase is None or (n, phase) in selected:
                continue
            prepared = node.call({**q, 'op': 'prepare', 'featureRevision': '4.3-strategic-correction'})
            if phase == 'bid' and not prepared['prior']:
                continue
            selected[n, phase] = (index, fixture, prepared)
        assert len(cells) == 80
        assert set(selected) == {(n, phase) for n in [2, 6] for phase in ['bid', 'building']}
        write(args.output/'selected-fixtures.json', {f'{n}p-{phase}': {'fixture_index': index,
            'fixture': fixture} for (n, phase), (index, fixture, _) in selected.items()})
        for key, model in models.items():
            revision = model_revision(model)
            rows = []
            for q in cells.values():
                prepared = node.call({**q, 'op': 'prepare', 'featureRevision': revision})
                rows += [prepared['observation'], *[p['encoded'] for p in prepared['prior']]]
            serial = [model.predict(row['state'], row['actions'])[0] for row in rows]
            assert serial == predict_batch(model, rows) == predict_batch(model, rows, 1)
            report['batch_checks'][key] = {'positions': len(rows), 'cells': 80,
                'counts': [2, 3, 4, 5, 6], 'serial_and_batched_actions_identical': True}
            print({'model': key, 'batch_positions_verified': len(rows)}, flush=True)
            for (n, phase), (index, fixture, reference) in selected.items():
                q = fixture['request']
                current = node.call({**q, 'op': 'prepare', 'featureRevision': revision})
                assert current['moves'] == fixture['legal'] == reference['moves']
                assert public_seed(current) == public_seed(reference)
                report['selected_fixtures'][f'{n}p-{phase}'] = index
                previous = None
                for budget in report['budgets']:
                    with HybridSearch(model, samples=budget, workers=4) as search:
                        result = search.choose(q)
                    detail = result['search']
                    assert detail is not None and result['move'] == fixture['legal'][result['index']]
                    assert result['modelProposal'] in detail['options']
                    assert detail['evaluations'] == budget * len(detail['options']) * 2
                    assert detail['usable'] == (detail['truncated'] == 0)
                    if not detail['usable']:
                        assert result['index'] == result['modelProposal']
                        assert detail['fallbackReason'] == 'incomplete-rollouts' and 'meanCredits' not in detail
                    if previous:
                        a, b = previous['search'], detail
                        assert a['seed'] == b['seed'] and a['options'] == b['options']
                        assert previous['modelProposal'] == result['modelProposal']
                        for mode in a['modes']:
                            for action, values in a['sampleOutcomes'][mode].items():
                                assert values == b['sampleOutcomes'][mode][action][:len(values)]
                    row = {'model': key, 'players': n, 'phase': phase, 'fixture_index': index,
                           'samples_per_mode': budget, 'result': result}
                    report['search_checks'].append(row)
                    with (args.output/'search-results.jsonl').open('a') as stream:
                        stream.write(json.dumps(row, allow_nan=False)+'\n')
                    print({'model': key, 'players': n, 'phase': phase, 'samples': budget,
                           'seconds': round(result['elapsedMs']/1000, 3),
                           'rollouts': detail['evaluations'], 'caps': detail['truncated']}, flush=True)
                    previous = result
        assert len(report['search_checks']) == 40
        assert all(digest(ROOT/path) == sha for path, sha in hashes.items())
        assert all(digest(runtime/path) == sha for path, sha in runtime_hashes.items())
        report['contracts_passed'] = True
        report['all_searches_usable'] = all(row['result']['search']['usable'] for row in report['search_checks'])
    finally:
        node.close()
        report['seconds'] = time.perf_counter()-started
        write(args.output/'assessment.json', report)
    print({'contracts_passed': report['contracts_passed'], 'search_cases': len(report['search_checks']),
           'all_searches_usable': report['all_searches_usable'], 'qualification_eligible': False}, flush=True)


if __name__ == '__main__':
    main()
