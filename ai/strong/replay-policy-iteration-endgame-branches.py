"""Single-decision endgame diagnostics with byte-identical original controls."""
import argparse
from collections import Counter
import json
import os
from pathlib import Path
import sys

from strategic_collection import ROOT, read, write, digest, get_model
sys.path.insert(0, str(ROOT/'ai'))
from infer import Model
from pool import EnginePool
from feature_contract import model_revision

PROTOCOL = ROOT/'ai/strong/policy-iteration-endgame-counterfactual-protocol-v1.json'


def main(output):
    protocol = read(PROTOCOL)
    original_analysis = ROOT/'ai/runs/policy-iteration-economy-analysis-v1.json'
    assert digest(original_analysis) == protocol['source_analysis_sha256']
    reference_root = ROOT/'ai/runs/policy-iteration-economy-replays-v1'
    previous = ROOT/'ai/runs/policy-iteration-legacy-replays-v1'
    selection = read(previous/'selection.json')
    assert digest(previous/'selection.json') == protocol['selection_sha256']
    assert protocol['source'] == selection['source']
    runtime = previous/'runtime'
    assert all(digest(runtime/name) == sha for name, sha in selection['runtime_hashes'].items())
    prepared = ROOT/'ai/runs/policy-iteration-trained-8840u-prepared-v2'
    models = {'parent': get_model(read(ROOT/'ai/strong/policy-iteration-labels-protocol-v2.json'))}
    for key in selection['models']:
        if key != 'parent': models[key] = Model(prepared/('local-package-'+key)/'policy.onnx')
        assert models[key].sha256 == selection['models'][key]
    code = [Path(__file__), PROTOCOL, ROOT/'ai/strong/trace-public-economy.cjs',
            ROOT/'ai/strong/intervene-endgame-build.cjs']
    hashes = {str(p.relative_to(ROOT)): digest(p) for p in code}
    output.mkdir(parents=True, exist_ok=False)
    environment = ['NODE_OPTIONS', 'PG_TRACE_PATH', 'PG_DIAGNOSTIC_RUNTIME', 'PG_ENDGAME_BRANCH']
    old = {key: os.environ.get(key) for key in environment}
    assert not old['NODE_OPTIONS']
    results = []
    try:
        os.environ['PG_DIAGNOSTIC_RUNTIME'] = str(runtime)
        os.environ['NODE_OPTIONS'] = ' '.join('--require '+str(ROOT/'ai/strong'/name)
            for name in ['trace-public-economy.cjs', 'intervene-endgame-build.cjs'])
        for case in protocol['cases']:
            expected = selection['requested'][case['name']]['expected']
            model = models[case['model']]
            reference_path = reference_root/(case['name']+'.jsonl')
            assert digest(reference_path) == case['reference_trace_sha256']
            reference = [json.loads(line) for line in reference_path.open()]
            indices = [i for i,r in enumerate(reference) if r['seat'] == case['seat'] and
                       r['before']['round'] == case['round'] and r['action'] == case['original']]
            assert len(indices) == 1
            index = indices[0]
            for branch in protocol['branches']:
                trace = output/(case['name']+'-'+branch+'.jsonl')
                trace.touch(exist_ok=False)
                os.environ['PG_TRACE_PATH'] = str(trace)
                os.environ['PG_ENDGAME_BRANCH'] = json.dumps({**case, 'branch': branch})
                seed = expected['gameSeed'].rsplit('-', 1)[0]
                assert seed == 'policy-iteration-development-v2-5p'
                pool = EnginePool(1, seed=seed, script=str(runtime/'ai/strong/bridge.cjs'))
                ended = []
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
                intervention_path = Path(str(trace)+'.intervention.json')
                intervention = read(intervention_path)
                assert intervention['applied'] == 1 and intervention['branch'] == branch
                actual = [json.loads(line) for line in trace.open()]
                assert actual[:index] == reference[:index], 'Prefix changed before intervention'
                assert actual[index]['before'] == reference[index]['before']
                assert actual[index]['action'] == intervention['replacement']
                assert len(actual) == ended[0]['steps'] <= protocol['max_steps']
                assert all(a['after'] == b['before'] for a,b in zip(actual, actual[1:]))
                if branch == 'original':
                    assert digest(trace) == digest(reference_path), 'Original full trace changed'
                    for key in ['episode', 'gameSeed', 'truncated', 'value', 'playerCount', 'variant',
                                'sealed', 'steps', 'roles', 'policyMoves', 'searchStats', 'final']:
                        assert ended[0][key] == expected[key], key
                results.append({'name':case['name'], 'model':case['model'], 'branch':branch,
                    'original_win':expected['win'], 'win':ended[0]['value'][case['seat']],
                    'truncated':ended[0]['truncated'], 'identical_prefix_moves':index,
                    'trace_sha256':digest(trace), 'intervention_sha256':digest(intervention_path),
                    'result':ended[0]})
                write(output/'branches.json', results)
            print({'case':case['name'], 'outcomes':{r['branch']:r['win'] for r in results if r['name']==case['name']}}, flush=True)
    finally:
        for key,value in old.items():
            if value is None: os.environ.pop(key,None)
            else: os.environ[key]=value
    assert len(results) == protocol['branch_games']
    assert all(digest(ROOT/name)==sha for name,sha in hashes.items())
    assert all(digest(runtime/name)==sha for name,sha in selection['runtime_hashes'].items())
    counts = {}
    for case in protocol['cases']:
        original,changed = [next(r for r in results if r['name']==case['name'] and r['branch']==b)
                            for b in ['original','pass']]
        label = ('capped' if changed['truncated'] else
                 'gain' if changed['win']>original['win'] else
                 'loss' if changed['win']<original['win'] else 'unchanged')
        counts.setdefault(case['model'],Counter())[label]+=1
    write(output/'assessment.json', {'games':len(results), 'cases':len(protocol['cases']),
        'original_controls_with_identical_full_traces':len(protocol['cases']),
        'all_branch_prefixes_identical':True, 'all_state_transitions_continuous':True,
        'truncations':sum(r['truncated'] for r in results), 'diagnostic_changes':counts,
        'code_hashes':hashes, 'source':protocol['source'], 'protocol_sha256':digest(PROTOCOL),
        'branches_sha256':digest(output/'branches.json'), 'new_strength_games':0,
        'gradients':False,'candidate_selected':False,'qualification_eligible':False,
        'reserved_final_seeds_used':False,'scope':protocol['purpose'],
        'note':'Arena policyMoves counts the model proposals; the full trace records executed moves after intervention. Do not treat proposal counters as executed-action counts in the changed branch.'})
    print({'games':len(results),'diagnostic_changes':counts,'truncations':sum(r['truncated'] for r in results)})


if __name__ == '__main__':
    parser=argparse.ArgumentParser(__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    main(args.output.resolve())
