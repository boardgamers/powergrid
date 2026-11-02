"""Vectorized Node environments, central batched inference, RAM-only trajectories."""
from concurrent.futures import ThreadPoolExecutor
import itertools
import math
import time
import torch
from data import Bridge
from residual import PROTOCOL, row, batch


def plans(split,update=0,deals=None,protocol=PROTOCOL):
    if split not in ('train','selection','confirmation','smoke'):
        raise ValueError('Unknown split; final seeds are reserved')
    maps=protocol['trainMaps']
    if split in ('confirmation','smoke'):maps=maps+protocol['transferMaps']
    count=deals if deals is not None else (protocol['gamesPerCellPerUpdate'] if split=='train' else protocol.get(split+'DealsPerCell',1))
    tasks=[]
    for ci,(m,n,v,f) in enumerate(itertools.product(maps,protocol['players'],protocol['variants'],protocol['fastBids'])):
        cell=f'{m}|{n}|{v}|{int(f)}'
        for deal in range(count):
            seed=f"{protocol['seedNamespace']}:{split}:{update if split=='train' else 0}:{cell}:{deal}"
            seats=[(ci+update-1)%n] if split=='train' else range(n)
            for seat in seats:
                style=protocol['opponentStyles'][(ci+update)%len(protocol['opponentStyles'])] if split=='train' else protocol['evaluationOpponent']
                tasks.append(dict(map=m,players=n,variant=v,fastBid=f,cell=cell,seed=seed,split=split,deal=deal,
                                  focalSeat=seat,opponentStyle=style,maxSteps=protocol['maxSteps']))
    return tasks


def collect(model,tasks,workers=6,training=False,seed=508,protocol=PROTOCOL):
    """Any engine error/cap fails the batch; no invented losses or omitted outcomes."""
    torch.set_num_threads(1)
    model.eval()
    generator=torch.Generator().manual_seed(seed)
    bridges=[];samples=[];outcomes=[]
    pending=iter(tasks);live={};requests={};total_rows=0
    def assign(i):
        spec=next(pending,None)
        if spec is not None:
            live[i]=dict(spec=spec,trace=[],relations=None,decisions=0,featureMs=0.,inferenceMs=0.,start=time.monotonic())
            requests[i]={'op':'start','spec':spec}
        else:live.pop(i,None)
    def call(item):
        i,request=item
        return i,bridges[i].call(request)
    try:
        for _ in range(min(workers,len(tasks))):bridges.append(Bridge('game_rl.cjs'))
        for i in range(len(bridges)):assign(i)
        with ThreadPoolExecutor(max_workers=max(1,len(bridges))) as pool, torch.inference_mode():
            while requests:
                answers=list(pool.map(call,sorted(requests.items())))
                requests={};observations=[];slots=[]
                for i,state in answers:
                    episode=live[i]
                    if state['terminal']:
                        credit=state['credit'][episode['spec']['focalSeat']]
                        assert math.isfinite(credit) and 0<=credit<=1
                        if training:
                            assert episode['trace'], 'No learned decisions in training episode'
                            for r in episode['trace']:
                                r['return']=credit;r['weight']=1/len(episode['trace'])
                            samples.extend(episode['trace'])
                        outcomes.append(dict(spec=episode['spec'],terminal=True,credit=credit,steps=state['steps'],rounds=state['rounds'],
                            decisions=episode['decisions'],featureMs=episode['featureMs'],inferenceMs=episode['inferenceMs'],seconds=time.monotonic()-episode['start']))
                        assign(i)
                    else:
                        assert state['phase'] in protocol['learnedPhases']
                        r=row(state['observation'],episode['relations'])
                        if episode['relations'] is None:episode['relations']=r['relations']
                        observations.append(r);slots.append(i)
                        episode['featureMs']+=state['featureMs'];episode['decisions']+=1
                if observations:
                    begin=time.perf_counter()
                    logits,values=model(batch(observations))
                    logps=logits.log_softmax(-1)
                    actions=torch.multinomial(logps.exp(),1,generator=generator).squeeze(-1) if training else logits.argmax(-1)
                    elapsed=1000*(time.perf_counter()-begin)
                    for j,i in enumerate(slots):
                        action=int(actions[j]);requests[i]={'op':'step','index':action}
                        live[i]['inferenceMs']+=elapsed/len(slots)
                        if training:
                            r=observations[j]
                            r.update(chosen=action,oldLog=float(logps[j,action]),oldValue=float(values[j]))
                            live[i]['trace'].append(r);total_rows+=1
                            if total_rows>protocol['maxRolloutRows']:raise MemoryError('Rollout RAM row budget exceeded')
    finally:
        for bridge in bridges:bridge.close()
    assert len(outcomes)==len(tasks)
    return samples,outcomes


def summary(outcomes):
    cells={}
    for r in outcomes:
        assert r['terminal']
        cells.setdefault(r['spec']['cell'],[]).append(r['credit'])
    cells={k:sum(v)/len(v) for k,v in cells.items()}
    maps={m:sum(v for k,v in cells.items() if k.split('|')[0]==m)/sum(k.split('|')[0]==m for k in cells)
          for m in sorted({k.split('|')[0] for k in cells})}
    return dict(games=len(outcomes),failures=0,macroCredit=sum(cells.values())/len(cells),cells=cells,maps=maps)
