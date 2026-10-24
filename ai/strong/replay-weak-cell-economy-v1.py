"""Four fixed diagnostic replays with a public economy observer, no new HF jobs."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

from strategic_collection import ROOT, read, write, digest, get_model
sys.path.insert(0,str(ROOT/'ai'))
from infer import Model
from pool import EnginePool
from feature_contract import model_revision


def worker(output,case):
    selection = read(output/'selection.json')
    request = selection['requested'][case]
    expected,key = request['expected'],request['model']
    runtime = output/'runtime'
    provenance = read(output/'runtime-provenance.json')
    assert all(digest(runtime/name) == sha for name,sha in provenance['runtime_hashes'].items())
    assert digest(__file__) == provenance['runner_sha256']
    observer = ROOT/'ai/strong/trace-public-economy.cjs'
    assert digest(observer) == provenance['observer_sha256']
    model = get_model(read(ROOT/'ai/strong/policy-iteration-labels-protocol-v2.json')) if key == 'parent' else Model(
        ROOT/'ai/runs/policy-iteration-trained-8840u-prepared-v2/local-package-frozen-1/policy.onnx',threads=1)
    assert model.sha256 == selection['pins'][key]['files']['inference64.onnx']
    assert not os.environ.get('NODE_OPTIONS')
    trace = output/(case+'.jsonl')
    trace.touch(exist_ok=False)
    os.environ['NODE_OPTIONS'] = '--require '+str(observer)
    os.environ['PG_TRACE_PATH'] = str(trace)
    os.environ['PG_DIAGNOSTIC_RUNTIME'] = str(runtime)
    seed = expected['gameSeed'].rsplit('-',1)[0]
    assert seed == f"policy-iteration-development-v2-{expected['playerCount']}p"
    pool = EnginePool(1,seed=seed,script=str(runtime/'ai/strong/bridge.cjs'))
    ended = []
    start = time.perf_counter()
    write(output/(case+'.process.json'),{'pid':os.getpid(),'node_pid':pool.processes[0].pid,
        'case':case,'started_at_unix':time.time(),'selection_sha256':digest(output/'selection.json'),
        'runtime_provenance_sha256':digest(output/'runtime-provenance.json')})
    result = {'case':case,'exact_terminal_replay':False,'completed':False}
    try:
        response = pool.call({'op':'reset','n':1,'playerCount':expected['playerCount'],
            'offset':expected['episode'],'mode':request['opponent'],'arenaSeed':seed,
            'featureRevisions':{'learner':model_revision(model)}})
        ended.extend(response['ended'])
        while response['observations'][0] is not None:
            row = response['observations'][0]
            action,_ = model.predict(row['state'],row['actions'])
            response = pool.call({'op':'step','actions':[action]})
            ended.extend(response['ended'])
        assert len(ended) == 1
        fields = ['episode','gameSeed','truncated','value','playerCount','variant','sealed',
            'steps','roles','policyMoves','searchStats','final']
        differences = [name for name in fields if ended[0][name] != expected[name]]
        result.update(actual=ended[0],differences=differences,trace_sha256=digest(trace),
            moves_logged=sum(1 for _ in trace.open()),seconds=time.perf_counter()-start,
            exact_terminal_replay=not differences)
        assert not differences,'Observer replay differs from verified evaluation'
        assert result['moves_logged'] == expected['steps'],'Observer missed root moves or logged simulations'
        result['completed'] = True
    except BaseException as error:
        result['error'] = type(error).__name__+': '+str(error)
        raise
    finally:
        pool.close()
        result.update(seconds=time.perf_counter()-start,finished_at_unix=time.time())
        write(output/(case+'.result.json'),result)
    print({'case':case,'exact_terminal_replay':True,'root_moves':result['moves_logged'],
        'seconds':result['seconds']},flush=True)


def run(selection_path,output):
    selection = read(selection_path)
    assert len(selection['requested']) == 4 and len(selection['pairs']) == 2
    assert not selection['qualification_eligible'] and not selection['reserved_final_seeds_used']
    assert digest(selection_path.parent/'assessment.json') == selection['assessment_sha256']
    assert digest(ROOT/'ai/strong/analyze-complete-policy-economy-v1.py') == selection['selector_sha256']
    previous = ROOT/'ai/runs/policy-iteration-legacy-replays-v1'
    old = read(previous/'selection.json')
    assert old['source'] == selection['source']
    output.mkdir(parents=True,exist_ok=False)
    shutil.copy2(selection_path,output/'selection.json')
    runtime = output/'runtime'
    for name,sha in old['runtime_hashes'].items():
        source = previous/'runtime'/name
        assert digest(source) == sha
        destination = runtime/name
        destination.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(source,destination)
    provenance = {'runtime_hashes':old['runtime_hashes'],'source':selection['source'],
        'previous_selection_sha256':digest(previous/'selection.json'),
        'runner_sha256':digest(__file__),'observer_sha256':digest(ROOT/'ai/strong/trace-public-economy.cjs'),
        'no_policy_or_engine_changes':True}
    write(output/'runtime-provenance.json',provenance)
    processes,streams = {},{}
    try:
        for case in selection['requested']:
            stream = (output/(case+'.log')).open('x')
            streams[case] = stream
            processes[case] = subprocess.Popen([sys.executable,__file__,'worker','--output',str(output),'--case',case],
                stdout=stream,stderr=subprocess.STDOUT,cwd=ROOT)
            write(output/(case+'.launch.json'),{'case':case,'pid':processes[case].pid,
                'selection_sha256':digest(output/'selection.json'),'runner_sha256':digest(__file__)})
        while True:
            codes = {case:p.poll() for case,p in processes.items()}
            status = {'pid':os.getpid(),'updated_at_unix':time.time(),'exit_codes':codes,
                'active':sum(code is None for code in codes.values()),
                'completed':sum(code == 0 for code in codes.values()),
                'failed':[case for case,code in codes.items() if code not in [None,0]],
                'automatic_retries':False,'new_hf_jobs':0,'qualification_eligible':False}
            write(output/'status.json',status)
            if not status['active']:
                break
            time.sleep(5)
        assert not status['failed'],status
        results = {case:read(output/(case+'.result.json')) for case in selection['requested']}
        assert all(r['completed'] and r['exact_terminal_replay'] for r in results.values())
        assert all(digest(runtime/name) == sha for name,sha in provenance['runtime_hashes'].items())
        write(output/'assessment.json',{'replays':4,'all_terminal_replays_match':True,
            'all_root_moves_logged':True,'selection_sha256':digest(output/'selection.json'),
            'runtime_provenance_sha256':digest(output/'runtime-provenance.json'),
            'results':results,'new_strength_games':0,'new_hf_jobs':0,'gradients':False,
            'qualification_eligible':False,'reserved_final_seeds_used':False,
            'scope':'Four frozen, outcome-selected full-game replays. The exact reference terminal results and every root move must match. No fresh strength or causal intervention.'})
        print({'exact_replays':4,'all_root_moves_logged':True},flush=True)
    finally:
        for stream in streams.values():
            stream.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('stage',choices=['run','worker'])
    parser.add_argument('--selection',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--case')
    args = parser.parse_args()
    if args.stage == 'worker':
        worker(args.output.resolve(),args.case)
    else:
        run(args.selection.resolve(),args.output.resolve())
