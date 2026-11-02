"""Independent fixed-policy study audit; small pinned outcomes, no trajectories."""
import argparse
from collections import defaultdict
import hashlib
import itertools
import json
import math
from pathlib import Path
import subprocess

import numpy as np
from huggingface_hub import HfApi,hf_hub_download
from data import ROOT,atomic_json,digest,generator_digest
from audit_ppo import require,equal

REPO='coyotte508/powergrid-ai-multimap-v1'
REVISION='5e94e37dc32638d27dea10b475731b874feebefd'
RUN='multimap-ppo8-opponents-20261102-v1'
JOB='6ae8dccac78863f9c630e490'
SOURCE='6f5a5e01e062c6b7c6d5b4dd99dff13829620c11'
PREFIX=f'runs/{RUN}/'


def expected_plan(p):
    tasks=[]
    for m,n,v,f,style in itertools.product(p['maps'],p['players'],p['variants'],p['fastBids'],p['opponents']):
        cell=f'{m}|{n}|{v}|{int(f)}'
        for deal in range(p['dealsPerCellAndOpponent']):
            seed=f"{p['seedNamespace']}:{cell}:{style}:{deal}"
            for seat in range(n):
                spec=dict(map=m,players=n,variant=v,fastBid=f,cell=cell,seed=seed,deal=deal,focalSeat=seat,opponentStyle=style,maxSteps=p['maxSteps'])
                for policy in p['policies']:tasks.append(dict(spec=spec,policy=policy))
    return tasks


def key(r):return r['spec']['seed'],r['spec']['focalSeat'],r['policy']


def verify(records,tasks):
    expected={key(r):r for r in tasks};actual={}
    require(len(expected)==len(tasks),'Duplicate planned task')
    for r in records:
        k=key(r);require(k in expected and k not in actual,'Duplicate/unplanned outcome')
        equal(r['spec'],expected[k]['spec'],'spec')
        require(r['terminal'] is True and 'error' not in r,'Failed/nonterminal outcome')
        require(type(r['credit']) in (int,float) and math.isfinite(r['credit']) and any(math.isclose(r['credit'],c,abs_tol=1e-12,rel_tol=0) for c in [0]+[1/n for n in range(1,r['spec']['players']+1)]),'Invalid credit')
        require(type(r['steps']) is int and 0<r['steps']<=r['spec']['maxSteps'],'Capped steps')
        require(type(r['rounds']) is int and 0<r['rounds']<=r['steps'],'Invalid rounds')
        require(type(r['decisions']) is int and 0<=r['decisions']<=r['steps'],'Invalid decision count')
        for name in ('featureMs','tensorModelMs','seconds'):
            require(math.isfinite(r[name]) and r[name]>=0,'Invalid timing')
        actual[k]=r
    require(set(actual)==set(expected),'Incomplete coverage')
    return actual


def paired_statistics(records,resamples=10000,seed=20261102608):
    cells=defaultdict(lambda:defaultdict(lambda:defaultdict(list)))
    for r in records:
        s=r['spec'];cells[(s['cell'],s['opponentStyle'])][s['seed']][r['policy']].append(r['credit'])
    keys=sorted(cells);values=[]
    for cell in keys:
        deals=[]
        for game_seed,policies in sorted(cells[cell].items()):
            require(set(policies)=={'selected','teacher'},'Unpaired deal')
            n=int(cell[0].split('|')[1])
            require(all(len(v)==n for v in policies.values()),'Missing seat in paired cluster')
            deals.append([math.fsum(policies[p])/n for p in ('selected','teacher')])
            if cell[1]=='geographic':require(math.isclose(math.fsum(policies['teacher']),1,abs_tol=1e-12),'Homogeneous teacher population not zero-sum')
        require(len(deals)==4,'Expected four deals per cell/opponent')
        values.append(deals)
    values=np.array(values);differences=values[:,:,0]-values[:,:,1]
    rng=np.random.Generator(np.random.PCG64(seed))
    draws=rng.integers(0,4,size=(resamples,len(keys),4))
    boot=differences[np.arange(len(keys))[None,:,None],draws].mean(2)
    groups={'all':list(range(len(keys)))}
    for field,position in (('map',0),('players',1)):
        for value in sorted({c[0].split('|')[position] for c in keys}):
            groups[f'{field}:{value}']=[i for i,c in enumerate(keys) if c[0].split('|')[position]==value]
    for style in sorted({c[1] for c in keys}):groups['opponent:'+style]=[i for i,c in enumerate(keys) if c[1]==style]
    for m in sorted({c[0].split('|')[0] for c in keys}):
        for n in range(2,7):groups[f'mapPlayers:{m}|{n}']=[i for i,c in enumerate(keys) if c[0].split('|')[:2]==[m,str(n)]]
    for style in sorted({c[1] for c in keys}):
        for n in range(2,7):groups[f'opponentPlayers:{style}|{n}']=[i for i,c in enumerate(keys) if c[1]==style and c[0].split('|')[1]==str(n)]
    report={}
    for label,indices in groups.items():
        if not indices:continue
        point=values[indices].mean(axis=(0,1));difference=float(point[0]-point[1])
        interval=np.quantile(boot[:,indices].mean(1),[.025,.975]).tolist()
        # Unbiased stratum sample variance avoids the n-1/n variance deficit of
        # a naive within-stratum percentile bootstrap with only four clusters.
        se=float(np.sqrt(differences[indices].var(axis=1,ddof=1).sum()/4)/len(indices))
        report[label]=dict(selected=float(point[0]),teacher=float(point[1]),difference=difference,
            pairedBootstrap95=interval,unbiasedStratifiedPairedSE=se,approximateNormal95=[difference-1.96*se,difference+1.96*se],
            strata=len(indices),independentDeals=4*len(indices),pairedSeats=sum(4*int(keys[i][0].split('|')[1]) for i in indices))
    return report


def audit(output):
    api=HfApi();require(api.inspect_job(job_id=JOB).status.stage=='COMPLETED','Job incomplete')
    info=api.model_info(REPO,revision=REVISION,files_metadata=True);require(info.private and info.sha==REVISION,'Wrong repository pin')
    metadata={s.rfilename[len(PREFIX):]:s for s in info.siblings if s.rfilename.startswith(PREFIX)}
    expected={'artifacts.json','status.json','study/plan.json','study/games.jsonl','study/summary.json'}
    require(set(metadata)==expected,'Unexpected study files')
    total=sum(s.size for s in metadata.values());require(total<=128*1024**2,'Audit download budget exceeded')
    mp=hf_hub_download(REPO,PREFIX+'artifacts.json',revision=REVISION);raw=Path(mp).read_bytes()
    require(hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==metadata['artifacts.json'].blob_id,'Manifest Git blob mismatch')
    manifest=json.loads(raw)
    require(set(manifest)==expected-{'artifacts.json'},'Bad artifact coverage')
    files={}
    for name,sha in manifest.items():
        p=Path(hf_hub_download(REPO,PREFIX+name,revision=REVISION));require(digest(p)==sha and p.stat().st_size==metadata[name].size,'Artifact hash/size mismatch');files[name]=p
        if metadata[name].lfs:require(metadata[name].lfs.sha256==sha,'HF LFS hash mismatch')
    plan=json.loads(files['study/plan.json'].read_text());protocol=plan['protocol']
    frozen=subprocess.check_output(['git','show',f'{SOURCE}:ai/multimap/opponent-study-v1.json'],cwd=ROOT)
    equal(protocol,json.loads(frozen),'frozen protocol');require(plan['smoke'] is False,'Smoke is not full study')
    require(plan['generatorDigest']==generator_digest(),'Engine/generator changed')
    for name,sha in plan['servingFiles'].items():
        original=subprocess.check_output(['git','show',f'{SOURCE}:ai/multimap/{name}'],cwd=ROOT)
        require(hashlib.sha256(original).hexdigest()==sha,'Serving source hash mismatch')
        require(digest(Path(__file__).parent/name)==sha,'Replay serving source changed')
    tasks=expected_plan(protocol);equal(plan['tasks'],tasks,'plan');require(len(tasks)==11520,'Incorrect budget')
    records=[json.loads(line) for line in files['study/games.jsonl'].read_text().splitlines()]
    actual=verify(records,tasks);stats=paired_statistics(records)
    stored=json.loads(files['study/summary.json'].read_text())
    equal({k:{name:stats[k][name] for name in ('selected','teacher','difference')} for k in stored['groups']},stored['groups'],'summary groups')
    for name,value in dict(games=11520,pairs=5760,independentDeals=1440,failures=0,qualified=False).items():equal(stored[name],value,name)
    status=json.loads(files['status.json'].read_text());require(status['stage']=='complete' and 'error' not in status,'Failed status')
    equal(status['result'],stored,'status summary');equal(status['protocol'],protocol,'status protocol')
    # Keep the frozen model pin and validate sparse independent engine replays.
    pin=protocol['checkpoint'];checkpoint=hf_hub_download(pin['repo'],pin['path'],revision=pin['revision'])
    require(digest(checkpoint)==pin['sha256']==plan['checkpointSha256'],'Wrong policy pin')
    from opponent_study import initialize,one_game
    initialize(checkpoint);replays=[]
    for i,m in enumerate(protocol['maps']):
        for j in range(3):
            n=protocol['players'][(i+j)%5];style=protocol['opponents'][j]
            choices=[t for t in tasks if t['spec']['map']==m and t['spec']['players']==n and t['spec']['opponentStyle']==style and t['policy']=='selected']
            task=min(choices,key=lambda t:hashlib.sha256(json.dumps(t,sort_keys=True).encode()).hexdigest())
            replay=one_game(task);original=actual[key(task)]
            for field in ('terminal','credit','steps','rounds'):equal(replay[field],original[field],'replay '+field)
            replays.append(dict(seed=task['spec']['seed'],seat=task['spec']['focalSeat'],matched=True))
    require(len(replays)==18,'Replay coverage')
    report=dict(repo=REPO,revision=REVISION,run=RUN,jobId=JOB,sourceCommit=SOURCE,auditorSha256=digest(Path(__file__)),artifactManifestSha256=digest(mp),
        artifactsVerified=len(manifest),artifactBytes=total,checkpoint=pin,games=11520,pairedComparisons=5760,independentDeals=1440,
        failures=0,completePlanVerified=True,sourceHashesVerified=True,homogeneousGeographicZeroSumVerified=True,
        groups=stats,replays=replays,qualified=False,
        uncertainty=dict(method='Paired independent-deal clusters, stratified by configuration and opponent; all seats kept together',
            resamples=10000,seed=20261102608,clustersPerStratum=4,intervalLevel=.95,
            caveat='Percentile bootstrap can be optimistic with four clusters/stratum; unbiased stratified paired SE and approximate-normal interval are also reported. Neither adjusts for multiple subgroup comparisons. Fixed checkpoint/heuristic populations, not human strength or final qualification.'))
    atomic_json(output,report)
    print(json.dumps(dict(output=str(output),aggregate=stats['all'],replays=len(replays)),indent=2))
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',default='ai/multimap/opponent-results-v1.json');a=p.parse_args();audit(a.output)
