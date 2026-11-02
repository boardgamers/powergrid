"""Fixed PPO-8 vs teacher across opponent styles. No fitting or policy selection."""
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import itertools
import json
import math
import multiprocessing
from pathlib import Path
import time
import torch
from data import Bridge, atomic_json, digest, generator_digest
from residual import load, row, batch

PROTOCOL=json.loads((Path(__file__).parent/'opponent-study-v1.json').read_text())
MODEL=None


def plan(smoke=False):
    tasks=[]
    for m,n,v,f,style in itertools.product(PROTOCOL['maps'],PROTOCOL['players'],PROTOCOL['variants'],PROTOCOL['fastBids'],PROTOCOL['opponents']):
        if smoke and (n!=2 or v!='original' or f):continue
        cell=f'{m}|{n}|{v}|{int(f)}'
        for deal in range(1 if smoke else PROTOCOL['dealsPerCellAndOpponent']):
            seed=f"{PROTOCOL['seedNamespace']}{':smoke' if smoke else ''}:{cell}:{style}:{deal}"
            for seat in range(n):
                spec=dict(map=m,players=n,variant=v,fastBid=f,cell=cell,seed=seed,deal=deal,
                          focalSeat=seat,opponentStyle=style,maxSteps=PROTOCOL['maxSteps'])
                for policy in PROTOCOL['policies']:tasks.append(dict(spec=spec,policy=policy))
    return tasks


def initialize(checkpoint):
    global MODEL
    torch.set_num_threads(1)
    MODEL,saved=load(checkpoint);MODEL.eval()
    assert saved['update']==PROTOCOL['checkpoint']['selectedUpdate']
    assert saved['config']['generatorDigest']==generator_digest()
    # Training scheduling can evolve, but serving semantics must be identical.
    for name in ('model.py','features.cjs','teacher.cjs','game.cjs','game_rl.cjs','residual.py','ppo-protocol-v1.json'):
        assert digest(Path(__file__).parent/name)==saved['config']['sourceFiles'][name],name


def one_game(task):
    spec=task['spec'];bridge=Bridge('game_rl.cjs');began=time.monotonic()
    result=dict(task,terminal=False,credit=0.,decisions=0,featureMs=0.,tensorModelMs=0.)
    try:
        settings=dict(spec,focalTeacher=True) if task['policy']=='teacher' else spec
        state=bridge.call({'op':'start','spec':settings})
        with torch.inference_mode():
            while not state['terminal']:
                result['featureMs']+=state['featureMs']
                begin=time.perf_counter();logits,_=MODEL(batch([row(state['observation'])]));index=int(logits[0].argmax())
                result['tensorModelMs']+=1000*(time.perf_counter()-begin);result['decisions']+=1
                state=bridge.call({'op':'step','index':index})
        credit=state['credit'][spec['focalSeat']]
        assert math.isfinite(credit) and 0<=credit<=1
        assert 0<state['steps']<=spec['maxSteps']
        result.update(terminal=True,credit=credit,steps=state['steps'],rounds=state['rounds'])
    except Exception as error:
        # Explicit evaluation failure, not a fabricated training reward.
        result['error']=str(error)
    finally:bridge.close()
    result['seconds']=time.monotonic()-began
    return result


def key(record):return (record['spec']['seed'],record['spec']['focalSeat'],record['policy'])


def summarize(records):
    cells={}
    for r in records:
        s=r['spec'];c=cells.setdefault((s['cell'],s['opponentStyle']),{})
        c.setdefault(r['policy'],[]).append(r)
    rows=[]
    for (cell,style),policies in sorted(cells.items()):
        if set(policies)!=set(PROTOCOL['policies']):raise ValueError('Unpaired cell')
        for policy,items in policies.items():
            rows.append(dict(cell=cell,map=cell.split('|')[0],players=int(cell.split('|')[1]),opponent=style,policy=policy,
                             games=len(items),credit=sum(r['credit'] for r in items)/len(items),failures=sum(not r['terminal'] for r in items)))
    groups={'all':rows}
    for field in ('map','players','opponent'):
        for value in sorted({r[field] for r in rows}):groups[f'{field}:{value}']=[r for r in rows if r[field]==value]
    result={}
    for group,entries in groups.items():
        scores={p:sum(r['credit'] for r in entries if r['policy']==p)/sum(r['policy']==p for r in entries) for p in PROTOCOL['policies']}
        result[group]=dict(**scores,difference=scores['selected']-scores['teacher'])
    return dict(games=len(records),pairs=len(records)//2,independentDeals=len({r['spec']['seed'] for r in records}),
                failures=sum(not r['terminal'] for r in records),groups=result,qualified=False,
                note='Frozen-policy robustness screen, fixed heuristic opponent populations. Paired all-seat repeats are not independent deals. No neural reference or final qualification.')


def read_existing(path,tasks):
    expected={key(t):t for t in tasks}
    if len(expected)!=len(tasks):raise ValueError('Duplicate planned task')
    if not path.exists():return [],set()
    data=path.read_bytes()
    if data and not data.endswith(b'\n'):
        # An interrupted last JSONL write is uncommitted; replay that one task.
        data=data[:data.rfind(b'\n')+1]
        temp=path.with_suffix('.tmp');temp.write_bytes(data);temp.replace(path)
    records=[json.loads(line) for line in data.splitlines()];seen=set()
    for r in records:
        k=key(r)
        if k in seen or k not in expected or r['spec']!=expected[k]['spec']:raise ValueError('Invalid/duplicate saved task')
        if not math.isfinite(r['credit']) or not 0<=r['credit']<=1:raise ValueError('Invalid evaluation credit')
        if not r['terminal'] and r['credit']!=0:raise ValueError('Failure must have zero credit')
        seen.add(k)
    return records,seen


def run(checkpoint,output,workers=6,smoke=False,callback=None):
    if digest(checkpoint)!=PROTOCOL['checkpoint']['sha256']:raise ValueError('Wrong frozen study policy')
    output=Path(output);output.mkdir(parents=True,exist_ok=True);tasks=plan(smoke)
    identity=dict(protocol=PROTOCOL,smoke=smoke,tasks=tasks,checkpointSha256=digest(checkpoint),generatorDigest=generator_digest(),
                  servingFiles={name:digest(Path(__file__).parent/name) for name in ('opponent_study.py','game_rl.cjs','residual.py','model.py','data.py')})
    plan_path=output/'plan.json'
    if plan_path.exists() and json.loads(plan_path.read_text())!=identity:raise ValueError('Study source/plan mismatch')
    atomic_json(plan_path,identity)
    records,done=read_existing(output/'games.jsonl',tasks)
    with ProcessPoolExecutor(max_workers=workers,mp_context=multiprocessing.get_context('spawn'),initializer=initialize,initargs=(str(checkpoint),)) as pool:
        futures=[pool.submit(one_game,t) for t in tasks if key(t) not in done]
        with (output/'games.jsonl').open('a') as file:
            for future in as_completed(futures):
                r=future.result();records.append(r);file.write(json.dumps(r)+'\n');file.flush()
                if len(records)%240==0 or len(records)==len(tasks):
                    print(json.dumps(dict(stage='opponent-study',done=len(records),total=len(tasks),failures=sum(not x['terminal'] for x in records))),flush=True)
                    if callback:callback(f'games-{len(records)}')
    assert len(records)==len(tasks)
    report=summarize(records);atomic_json(output/'summary.json',report)
    if report['failures']:raise RuntimeError(f"Opponent study has {report['failures']} failed games; all outcomes retained")
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--checkpoint',required=True);p.add_argument('--output',required=True);p.add_argument('--workers',type=int,default=6);p.add_argument('--smoke',action='store_true')
    a=p.parse_args();print(json.dumps(run(a.checkpoint,a.output,a.workers,a.smoke),indent=2))
