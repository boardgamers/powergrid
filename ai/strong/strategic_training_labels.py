"""HF counterfactual targets with separate world samples and whole-deal splits."""
import argparse
from collections import Counter
import gzip
import json
import os
from pathlib import Path
import time
from huggingface_hub import HfApi
from strategic_collection import ROOT, read, write, digest, get_model, request_hash
from strategic_teacher import Node, prepare, evaluate

PROTOCOL=ROOT/'ai/strong/strategic-teacher-training-protocol-v1.json'
SOURCE=ROOT/'ai/strong/strategic-teacher-training-source-v1.json'
def prefix(n,source_mode,mode,start,end):return f'runs/strategic-teacher-training-v1-{n}p-{source_mode}-{mode}-{start}-{end}'

def load_roots(p,n,source_mode,start,end):
    assert n in p['players'] and source_mode in p['source_modes'] and 0<=start<end<=16
    pin=read(ROOT/'ai/strong/strategic-teacher-training-roots-v1.json')
    path=ROOT/pin['file']
    if not path.exists():path=ROOT/pin['local_file']
    assert digest(path)==pin['sha256']==p['roots_sha256']
    with gzip.open(path,'rt') as f:
        rows=[r for r in map(json.loads,f) if r['players']==n and r['mode']==source_mode and start<=r['deal']<end]
    expected={(d,v,s,k) for d in range(start,end) for v in ['original','recharged'] for s in [False,True]
        for k in ['nomination','bid','building']}
    assert len(rows)==len(expected) and {(r['deal'],r['variant'],r['sealed'],r['decision']) for r in rows}==expected
    assert len({r['rootId'] for r in rows})==len(rows)
    for r in rows:
        assert request_hash(r['request'])==r['public_root_sha256']
        assert r['split']==('validation' if r['deal'] in [0,4,8,12] else 'train')
    return rows

def run(n,source_mode,mode,start,end,out,upload=False):
    p=read(PROTOCOL);assert mode in p['modes']
    roots=load_roots(p,n,source_mode,start,end);model=get_model(p)
    out=Path(out).resolve();out.mkdir(parents=True,exist_ok=False);begin=time.monotonic()
    status={'status':'running','players':n,'source_mode':source_mode,'mode':mode,'deal_start':start,'deal_end':end,
        'protocol_sha256':digest(PROTOCOL),'source_revision':os.environ.get('SOURCE_REVISION'),
        'source_sha256':os.environ.get('SOURCE_SHA256'),'model_sha256':model.sha256,'roots_sha256':p['roots_sha256'],
        'trained':False,'qualification_eligible':False,'scope':'Paired simulated action advantages, not real-game probabilities or winner labels.'}
    node=Node('strong/strategic-continuations.cjs');count=evaluations=0;engine_seconds=policy_seconds=0.
    try:
        with gzip.open(out/'labels.jsonl.gz','wt') as f:
            for root in roots:
                options=prepare(node,model,root)
                for batch in p['batches']:
                    row=evaluate(model,root,options,mode,batch,p['samples'],p['workers'])
                    row['root_metadata']={k:root[k] for k in ['players','mode','deal','split','variant','sealed','decision','teacherRootIndex']}
                    assert row['usable'], 'Capped evidence cannot become targets'
                    f.write(json.dumps(row)+'\n');f.flush();count+=1;evaluations+=len(row['rollouts'])
                    engine_seconds+=row['timing']['engine_seconds'];policy_seconds+=row['timing']['policy_seconds']
                    print({'root':root['rootId'],'decision':root['decision'],'batch':batch,
                        'completed_searches':count,'requested_searches':len(roots)*2,'seconds':time.monotonic()-begin},flush=True)
        assert count==2*len(roots)
        status.update(status='complete',positions=len(roots),searches=count,evaluations=evaluations,samples=p['samples'],
            root_splits=dict(Counter(r['split'] for r in roots)),game_truncations=0,nested_truncations=0,
            engine_seconds=engine_seconds,policy_seconds=policy_seconds,seconds=time.monotonic()-begin)
    except BaseException as e:
        status.update(status='failed',error=type(e).__name__+': '+str(e));raise
    finally:
        node.close();status['artifacts']={q.name:digest(q) for q in out.iterdir() if q.is_file()}
        write(out/'label-check.json',status)
        if upload:HfApi().upload_folder(repo_id=p['repo'],folder_path=out,path_in_repo=prefix(n,source_mode,mode,start,end))
        print(status,flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(__doc__);p.add_argument('players',type=int,choices=range(2,7))
    p.add_argument('source_mode',choices=['economic','snapshot0']);p.add_argument('mode',choices=['neural','neural_economic'])
    p.add_argument('start',type=int);p.add_argument('end',type=int);p.add_argument('output',type=Path)
    p.add_argument('--upload',action='store_true');a=p.parse_args();run(a.players,a.source_mode,a.mode,a.start,a.end,a.output,a.upload)
