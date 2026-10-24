"""Actual trained-model integration for the isolated population worker.

Existing endpoint fixtures only; no fresh strength games or model selection.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import platform
import time

from strategic_collection import ROOT, read, write, digest, get_model
from hybrid_search import Model, Node, model_revision, predict_batch, public_seed

MODES = ['neural_legacy', 'neural_rush', 'neural_population']


def main(output):
    preflight = ROOT/'ai/runs/population-hybrid-preflight-v2'
    admission = read(preflight/'admission.json')
    tests = (preflight/'tests.log').read_text()
    assert 'pass 5' in tests and 'fail 0' in tests
    runtime = preflight/'runtime'
    for name, sha in admission['base_runtime_hashes'].items():
        assert digest(runtime/name) == sha
    for name, sha in admission['new_code_hashes'].items():
        assert digest(ROOT/'ai/strong'/name) == digest(runtime/'ai/strong'/name) == sha
    assert digest(runtime/'ai/strong/hybrid-continuations.cjs') == admission['old_hybrid_sha256']
    prepared = ROOT/'ai/runs/policy-iteration-trained-8840u-prepared-v2'
    manifest = read(prepared/'manifest.json')
    assert manifest['source'] == admission['source']
    previous = ROOT/'ai/runs/trained-hybrid-probe-v2'
    fixtures = read(previous/'selected-fixtures.json')
    old_probe = read(previous/'assessment.json')
    assert old_probe['contracts_passed'] and set(fixtures) == {'2p-bid','2p-building','6p-bid','6p-building'}
    models = {'parent': get_model(read(ROOT/'ai/strong/policy-iteration-labels-protocol-v2.json'))}
    for key, item in manifest['models'].items():
        models[key] = Model(prepared/('local-package-'+key)/'policy.onnx')
        assert models[key].sha256 == item['pin']['files']['inference64.onnx']
    assert {k:m.sha256 for k,m in models.items()} == old_probe['models']
    output.mkdir(parents=True, exist_ok=False)
    node = Node(str(runtime/'ai/strong/population-hybrid-continuations.cjs'))
    all_results, seeds = [], {}
    started = time.perf_counter()
    try:
        for key, model in models.items():
            revision = model_revision(model)
            for fixture_name, fixture in fixtures.items():
                q = fixture['fixture']['request']
                prepared_root = node.call({**q,'op':'prepare','featureRevision':revision})
                assert prepared_root['moves'] == fixture['fixture']['legal']
                observations = [prepared_root['observation'],*[p['encoded'] for p in prepared_root['prior']]]
                choices = predict_batch(model, observations)
                assert choices == [model.predict(r['state'],r['actions'])[0] for r in observations]
                options = [choices[0], (choices[0]+1)%len(prepared_root['moves'])]
                assert len(set(options)) == 2
                neural = {str(p['actor']):p['encoded']['moves'][i] for p,i in zip(prepared_root['prior'],choices[1:])}
                seed = public_seed(prepared_root)
                if fixture_name in seeds: assert seeds[fixture_name] == seed
                seeds[fixture_name] = seed
                for mode in MODES:
                    begin = time.perf_counter()
                    response = node.call({**q,'op':'reset','featureRevision':revision,'mode':mode,
                        'belief':'policy','neuralBeliefs':neural if mode=='neural_population' else {},
                        'options':options,'samples':4,'n':8,'seed':seed,'maxSteps':2400})
                    ended = list(response['ended']); decisions = 0
                    while any(response['observations']):
                        live = [i for i,o in enumerate(response['observations']) if o is not None]
                        rows = [response['observations'][i] for i in live]
                        assert all(r['roles'][r['actor']]=='neural' and r['featureRevision']==revision for r in rows)
                        if mode != 'neural_population': assert all(r['actor']==q['player'] for r in rows)
                        chosen = predict_batch(model,rows)
                        actions = [None]*8
                        for i,a in zip(live,chosen): actions[i]=a
                        decisions += len(chosen)
                        response = node.call({'op':'step','actions':actions})
                        ended.extend(response['ended'])
                    assert len(ended)==8 and {r['env'] for r in ended}==set(range(8))
                    by_sample = {}
                    for row in ended:
                        sample, option = divmod(row['env'],len(options))
                        assert row['sample']==sample and row['actionIndex']==options[option]
                        assert row['roles'][q['player']]=='neural'
                        assert row['searchStats']=={'decisions':0,'evaluations':0,'truncated':0}
                        assert sum(row['policyDecisions'].values())==row['steps']<=2400
                        assert row['truncated']==(row['value'] is None)
                        assert row['value'] is None or 0 <= row['value'] <= 1
                        assert row['initialBelief']['kind']=='policy_population_v1'
                        assert {p['actor'] for p in row['initialBelief']['committed']}=={p['actor'] for p in prepared_root['prior']}
                        assert all(p['role']==row['roles'][p['actor']] for p in row['initialBelief']['committed'])
                        world = {'roles':row['roles'],'initialBelief':row['initialBelief']}
                        if sample in by_sample: assert by_sample[sample]==world
                        by_sample[sample]=world
                        if mode!='neural_population':
                            expected = 'legacy' if mode=='neural_legacy' else 'rush'
                            assert all(role==('neural' if seat==q['player'] else expected)
                                       for seat,role in enumerate(row['roles']))
                    if mode=='neural_population':
                        for seat in range(len(q['state']['players'])):
                            if seat!=q['player']:
                                assert Counter(w['roles'][seat] for w in by_sample.values())==Counter(['neural','economic','legacy','rush'])
                    result = {'model':key,'fixture':fixture_name,'fixture_index':fixture['fixture_index'],
                        'mode':mode,'options':options,'seed':seed,'samples':4,'max_steps':2400,
                        'outcomes':sorted(ended,key=lambda r:r['env']),
                        'neural_decisions':decisions,'seconds':time.perf_counter()-begin}
                    all_results.append(result)
                    with (output/'results.jsonl').open('a') as stream: stream.write(json.dumps(result,allow_nan=False)+'\n')
                    print({'model':key,'fixture':fixture_name,'mode':mode,'seconds':round(result['seconds'],3),
                           'caps':sum(r['truncated'] for r in ended)},flush=True)
    finally:
        node.close()
        write(output/'assessment.json',{'cases':len(all_results),'expected_cases':60,
            'complete':len(all_results)==60,'rollouts':sum(len(r['outcomes']) for r in all_results),
            'truncations':sum(o['truncated'] for r in all_results for o in r['outcomes']),
            'results_sha256':digest(output/'results.jsonl') if (output/'results.jsonl').exists() else None,
            'models':{key:m.sha256 for key,m in models.items()},'source':admission['source'],
            'preflight_admission_sha256':digest(preflight/'admission.json'),
            'preflight_tests_sha256':digest(preflight/'tests.log'),
            'fixture_selection_sha256':digest(previous/'selected-fixtures.json'),
            'probe_code_sha256':digest(Path(__file__)),'seconds':time.perf_counter()-started,
            'processor':next(line.split(':',1)[1].strip() for line in Path('/proc/cpuinfo').read_text().splitlines()
                             if line.startswith('model name')),'host':platform.node(),
            'new_strength_games':0,'new_hf_jobs':0,'gradients':False,'candidate_selected':False,
            'qualification_eligible':False,'reserved_final_seeds_used':False,
            'scope':'Actual five-model integration on four existing 2p/6p Recharged-sealed bid/building fixtures. '
                'Three new opponent modes, four shared worlds and two root actions; no strength comparison, '
                'weights selection, representative latency distribution or AMD8840U timing claim.'})


if __name__=='__main__':
    parser=argparse.ArgumentParser(__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    main(args.output.resolve())
