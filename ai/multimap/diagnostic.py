"""Phase substitution and 8840U tensor-inference timing; no training data retained."""
import argparse
import concurrent.futures
import json
import multiprocessing
from pathlib import Path
import platform
import statistics
import time

import torch
from data import Bridge, PROTOCOL, atomic_json, digest, specs
from model import GraphPolicy, collate, tensor_row

MODEL=None
PHASES=['Color Selection','Region Selection','Order','Auction','Resources','Building','Bureaucracy','Game End']


def initialize(checkpoint):
    global MODEL
    torch.set_num_threads(1)
    saved=torch.load(checkpoint,map_location='cpu',weights_only=True)
    MODEL=GraphPolicy(saved['width']).eval()
    MODEL.load_state_dict(saved['state_dict'])


def play(task):
    spec,seat,policy=task
    bridge=Bridge(); timings=[]
    start=time.monotonic()
    result=dict(spec=spec,seat=seat,policy=policy,terminal=False,credit=0.)
    try:
        state=bridge.call({'op':'start','spec':dict(spec,focalSeat=seat)})
        with torch.inference_mode():
            while not state['terminal']:
                phase=PHASES[state['observation']['global'][:8].index(1)]
                if policy=='all' or policy==phase:
                    begin=time.perf_counter()
                    logits,_=MODEL(collate([tensor_row(state['observation'])]))
                    index=int(logits[0].argmax())
                    timings.append(1000*(time.perf_counter()-begin))
                    state=bridge.call({'op':'step','index':index})
                else:
                    state=bridge.call({'op':'step','teacher':'geographic'})
        result.update(terminal=True,credit=state['credit'][seat],steps=state['steps'],rounds=state['rounds'])
    except Exception as error:
        result['error']=str(error)
    finally:
        bridge.close()
    result['seconds']=time.monotonic()-start
    result['inferenceMs']=timings
    return result


def run(checkpoint,output,workers=4):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    policies=['teacher','all','Auction','Resources','Building','Bureaucracy']
    # Fresh diagnostic deals; transfer results are NOT used to tune the successor.
    plan=[s for s in specs('development',1) if s['map'] in PROTOCOL['trainMaps'] and s['players']==4]
    for s in plan:s['seed']=s['seed'].replace(':development:',':phase-diagnostic-v1:')
    tasks=[(s,seat,policy) for s in plan for seat in range(4) for policy in policies]
    atomic_json(output/'plan.json',dict(checkpointSha256=digest(checkpoint),tasks=tasks))
    results=[]
    with concurrent.futures.ProcessPoolExecutor(max_workers=workers,mp_context=multiprocessing.get_context('spawn'),initializer=initialize,initargs=(str(checkpoint),)) as pool:
        with (output/'games.jsonl').open('w') as file:
            for r in pool.map(play,tasks,chunksize=1):
                results.append(r);file.write(json.dumps(r)+'\n');file.flush()
                if len(results)%24==0:print(json.dumps(dict(done=len(results),total=len(tasks))),flush=True)
    report=dict(checkpointSha256=digest(checkpoint),machine=platform.node(),python=platform.python_version(),torch=torch.__version__,threadsPerWorker=1,workers=workers,
                games=len(results),failures=sum(not r['terminal'] for r in results),policies={})
    for policy in policies:
        rows=[r for r in results if r['policy']==policy]
        times=sorted(t for r in rows for t in r['inferenceMs'])
        report['policies'][policy]=dict(games=len(rows),winCredit=sum(r['credit'] for r in rows)/len(rows),
            requests=len(times),tensorAndModelMsMedian=statistics.median(times) if times else None,
            tensorAndModelMsP95=times[int(.95*len(times))] if times else None,
            perMap={m:sum(r['credit'] for r in rows if r['spec']['map']==m)/sum(r['spec']['map']==m for r in rows) for m in PROTOCOL['trainMaps']})
    report['caveat']='Diagnostic screen: four-player training maps, one independent deal per configuration, all seats. Timings include tensor conversion+forward only, not JS/IPC/platform latency. Four concurrent processes.'
    atomic_json(output/'summary.json',report)
    print(json.dumps(report,indent=2),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--checkpoint',required=True);p.add_argument('--output',required=True);p.add_argument('--workers',type=int,default=4)
    a=p.parse_args();run(a.checkpoint,a.output,a.workers)
