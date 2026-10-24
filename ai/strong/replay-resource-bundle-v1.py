"""Original-vs-three-coal diagnostic on one frozen, outcome-selected trajectory."""
import argparse
import json
import os
from pathlib import Path
import sys

from strategic_collection import ROOT,read,write,digest
sys.path.insert(0,str(ROOT/'ai'))
from infer import Model
from pool import EnginePool
from feature_contract import model_revision

PROTOCOL = ROOT/'ai/strong/weak-cell-resource-counterfactual-v1.json'


def main(output):
    protocol = read(PROTOCOL)
    base = ROOT/protocol['reference_directory']
    selection = read(base/'selection.json')
    assert digest(base/'selection.json') == protocol['selection_sha256']
    case = protocol['case']
    reference_path = base/(case+'.jsonl')
    assert digest(reference_path) == protocol['reference_trace_sha256']
    existing = read(base/(case+'.result.json'))
    assert existing['completed'] and existing['exact_terminal_replay']
    assert digest(base/(case+'.result.json')) == protocol['reference_result_sha256']
    expected = selection['requested'][case]['expected']
    reference = [json.loads(line) for line in reference_path.open()]
    index = protocol['root_index']
    assert reference[index]['action'] == {'name':'Pass','data':True}
    assert reference[index]['before']['phase'] == 'Resources'
    runtime = base/'runtime'
    hashes = read(base/'runtime-provenance.json')['runtime_hashes']
    assert all(digest(runtime/name) == sha for name,sha in hashes.items())
    output.mkdir(parents=True,exist_ok=False)
    model = Model(ROOT/'ai/runs/policy-iteration-trained-8840u-prepared-v2/local-package-frozen-1/policy.onnx',threads=1)
    assert model.sha256 == selection['pins']['frozen-1']['files']['inference64.onnx']
    code_hashes = {str(p.relative_to(ROOT)):digest(p) for p in [Path(__file__),PROTOCOL,
        ROOT/'ai/strong/trace-public-economy.cjs',ROOT/'ai/strong/intervene-resource-bundle-v1.cjs']}
    assert not os.environ.get('NODE_OPTIONS')
    os.environ['NODE_OPTIONS'] = ' '.join('--require '+str(ROOT/'ai/strong'/name)
        for name in ['trace-public-economy.cjs','intervene-resource-bundle-v1.cjs'])
    os.environ['PG_DIAGNOSTIC_RUNTIME'] = str(runtime)
    results = []
    for branch in protocol['branches']:
        trace = output/(branch+'.jsonl')
        trace.touch(exist_ok=False)
        os.environ['PG_TRACE_PATH'] = str(trace)
        os.environ['PG_RESOURCE_BRANCH'] = json.dumps({**protocol['target'],'branch':branch})
        seed = expected['gameSeed'].rsplit('-',1)[0]
        pool = EnginePool(1,seed=seed,script=str(runtime/'ai/strong/bridge.cjs'))
        write(output/(branch+'.process.json'),{'pid':os.getpid(),'node_pid':pool.processes[0].pid,
            'branch':branch,'protocol_sha256':digest(PROTOCOL)})
        ended = []
        try:
            response = pool.call({'op':'reset','n':1,'playerCount':2,'offset':expected['episode'],
                'mode':'search_geo','arenaSeed':seed,'featureRevisions':{'learner':model_revision(model)}})
            ended.extend(response['ended'])
            while response['observations'][0] is not None:
                row = response['observations'][0]
                action,_ = model.predict(row['state'],row['actions'])
                response = pool.call({'op':'step','actions':[action]})
                ended.extend(response['ended'])
        finally:
            pool.close()
        assert len(ended) == 1 and not ended[0]['truncated']
        receipt = read(Path(str(trace)+'.intervention.json'))
        assert receipt['applied'] == 1 and receipt['branch'] == branch
        actual = [json.loads(line) for line in trace.open()]
        assert actual[:index] == reference[:index]
        assert actual[index]['before'] == reference[index]['before']
        assert all(a['after'] == b['before'] for a,b in zip(actual,actual[1:]))
        assert len(actual) == ended[0]['steps']+len(receipt['purchases'])
        if branch == 'original':
            assert digest(trace) == digest(reference_path)
            for name in ['episode','gameSeed','truncated','value','playerCount','variant','sealed',
                'steps','roles','policyMoves','searchStats','final']:
                assert ended[0][name] == expected[name]
        else:
            assert [r['action'] for r in actual[index:index+3]] == [x['action'] for x in receipt['purchases']]
            assert actual[index+3]['action'] == {'name':'Pass','data':True}
        results.append({'branch':branch,'original_win':expected['win'],
            'win':ended[0]['value'][expected['seat']],'result':ended[0],'receipt':receipt,
            'identical_prefix_moves':index,'trace_sha256':digest(trace),
            'receipt_sha256':digest(Path(str(trace)+'.intervention.json'))})
        write(output/'branches.json',results)
        print({'branch':branch,'win':results[-1]['win'],'purchases':receipt['purchases'],
            'fuel_before':receipt['fuelBefore'],'fuel_after':receipt['fuelAfter']},flush=True)
    assert all(digest(ROOT/name) == sha for name,sha in code_hashes.items())
    assert all(digest(runtime/name) == sha for name,sha in hashes.items())
    write(output/'assessment.json',{'cases':1,'branches':2,'full_original_trace_identical':True,
        'prefix_moves_identical':index,'all_state_transitions_continuous':True,'caps':0,
        'outcomes':{r['branch']:r['win'] for r in results},'code_hashes':code_hashes,
        'protocol_sha256':digest(PROTOCOL),'branches_sha256':digest(output/'branches.json'),
        'new_strength_games':0,'gradients':False,'qualification_eligible':False,'reserved_final_seeds_used':False,
        'scope':protocol['scope'],
        'counter_note':'Arena counters count policy proposals; the executed trace contains three inserted legal purchases. This is not a strength-game receipt.'})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--output',type=Path,required=True)
    main(parser.parse_args().output.resolve())
