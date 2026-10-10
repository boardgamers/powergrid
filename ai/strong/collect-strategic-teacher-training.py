"""Verify every paired label before it can enter a gradient-training dataset."""
import argparse
from collections import Counter
import gzip
import json
import math
from pathlib import Path
import re
import numpy as np
from huggingface_hub import hf_hub_download
from strategic_training_labels import ROOT,PROTOCOL,SOURCE,read,write,digest,load_roots,get_model,Node,prepare,prefix

def collect(n,source_mode,mode,start,end,revision):
    assert re.fullmatch('[a-f0-9]{40}',revision)
    p=read(PROTOCOL);source=read(SOURCE);assert mode in p['modes']
    roots=load_roots(p,n,source_mode,start,end);by_id={r['rootId']:r for r in roots}
    remote=prefix(n,source_mode,mode,start,end)
    status_path=Path(hf_hub_download(p['repo'],remote+'/label-check.json',revision=revision));s=read(status_path)
    expected={'status':'complete','players':n,'source_mode':source_mode,'mode':mode,'deal_start':start,'deal_end':end,
        'protocol_sha256':digest(PROTOCOL),'source_revision':source['revision'],'source_sha256':source['sha256'],
        'model_sha256':p['model']['sha256'],'roots_sha256':p['roots_sha256'],'trained':False,'qualification_eligible':False,
        'positions':len(roots),'searches':2*len(roots),'samples':p['samples'],'game_truncations':0,'nested_truncations':0,
        'root_splits':dict(Counter(r['split'] for r in roots))}
    for key,value in expected.items():assert s[key]==value,key
    assert set(s['artifacts'])=={'labels.jsonl.gz'}
    labels=Path(hf_hub_download(p['repo'],remote+'/labels.jsonl.gz',revision=revision));assert digest(labels)==s['artifacts']['labels.jsonl.gz']
    model=get_model(p);node=Node('strong/strategic-continuations.cjs');options={};seen=set();stats={};evaluations=0
    timing={k:0. for k in ['engine_seconds','policy_seconds']}
    try:
        with gzip.open(labels,'rt') as f:
            for line in f:
                row=json.loads(line);root=by_id[row['rootId']];key=(row['rootId'],row['batch'])
                assert key not in seen and row['batch'] in p['batches'];seen.add(key)
                if root['rootId'] not in options:options[root['rootId']]=prepare(node,model,root)
                opts=options[root['rootId']]
                assert row['options']==opts and row['model_proposal']==root['model_proposal'] and row['mode']==mode
                assert row['public_root_sha256']==root['public_root_sha256'] and row['split']==root['split']
                assert row['root_metadata']=={k:root[k] for k in ['players','mode','deal','split','variant','sealed','decision','teacherRootIndex']}
                assert row['samples']==p['samples'] and row['seed']=='strategic-teacher-public-v1-'+root['rootId']+'-'+row['batch']
                assert row['usable'] and not row['outer_truncations'] and not row['qualification_eligible']
                assert row['nested_search']=={'decisions':0,'evaluations':0,'truncated':0}
                count=p['samples']*len(opts);assert len(row['rollouts'])==count
                assert {r['env'] for r in row['rollouts']}==set(range(count))
                outcomes={str(a):[None]*p['samples'] for a in opts};pairs=set();neural_decisions=0
                expected_roles=['neural' if mode=='neural' or seat==root['request']['player'] else 'economic' for seat in range(n)]
                for r in row['rollouts']:
                    pair=(r['sample'],r['actionIndex']);assert pair not in pairs;pairs.add(pair)
                    assert 0<=pair[0]<p['samples'] and pair[1] in opts
                    assert r['env']==pair[0]*len(opts)+opts.index(pair[1]) and not r['truncated'] and 0<=r['steps']<=2400
                    assert any(math.isclose(r['value'],credit,abs_tol=1e-12) for credit in [0]+[1/k for k in range(1,n+1)])
                    assert r['roles']==expected_roles and r['searchStats']=={'decisions':0,'evaluations':0,'truncated':0}
                    assert all(type(v)==int and v>=0 for v in r['policyDecisions'].values())
                    assert sum(r['policyDecisions'].values())==r['steps'] and not r['policyDecisions']['search_geo'] and not r['policyDecisions']['heuristic']
                    if mode=='neural':assert not r['policyDecisions']['economic']
                    neural_decisions+=r['policyDecisions']['neural'];outcomes[str(pair[1])][pair[0]]=r['value']
                assert outcomes==row['sample_outcomes']
                baseline=outcomes[str(root['model_proposal'])]
                advantages={str(a):[v-b for v,b in zip(outcomes[str(a)],baseline)] for a in opts}
                assert advantages==row['paired_advantages_over_proposal']
                assert neural_decisions==row['timing']['policy_decisions']
                for k in timing:
                    assert math.isfinite(row['timing'][k]) and row['timing'][k]>=0;timing[k]+=row['timing'][k]
                stats[key]={a:float(np.mean(xs)) for a,xs in advantages.items()};evaluations+=count
    finally:node.close()
    assert seen=={(r['rootId'],b) for r in roots for b in p['batches']} and evaluations==s['evaluations']
    for k in timing:assert math.isclose(timing[k],s[k],abs_tol=1e-8)
    confirmed={split:[] for split in ['train','validation']}
    for root in roots:
        a,b=stats[root['rootId'],'a'],stats[root['rootId'],'b'];proposal=str(root['model_proposal'])
        chosen=max(a,key=lambda x:(a[x],x==proposal,-int(x)))
        confirmed[root['split']].append(b[chosen])
    summary={k:s[k] for k in ['players','source_mode','mode','deal_start','deal_end','positions','searches','samples','evaluations',
        'root_splits','game_truncations','nested_truncations','engine_seconds','policy_seconds','seconds']}
    summary['a_selected_b_mean_advantage']={split:float(np.mean(xs)) for split,xs in confirmed.items() if xs}
    summary['scope']='Conditional simulation targets and independent-batch diagnostic, not whole-game playing strength.'
    out=ROOT/f'ai/runs/strategic-teacher-training-verified-v1/{n}p-{source_mode}-{mode}-{start}-{end}'
    out.mkdir(parents=True,exist_ok=False);(out/'label-check.json').write_bytes(status_path.read_bytes());(out/'labels.jsonl.gz').write_bytes(labels.read_bytes())
    saved={'verified':True,'revision':revision,'prefix':remote,'source_revision':source['revision'],'source_sha256':source['sha256'],
        'protocol_sha256':digest(PROTOCOL),'roots_sha256':p['roots_sha256'],'summary':summary,
        'artifacts':{q.name:digest(q) for q in out.iterdir() if q.is_file()},'qualification_eligible':False}
    write(out/'verified.json',saved);print(summary)

if __name__=='__main__':
    p=argparse.ArgumentParser(__doc__);p.add_argument('players',type=int,choices=range(2,7))
    p.add_argument('source_mode',choices=['economic','snapshot0']);p.add_argument('mode',choices=['neural','neural_economic'])
    p.add_argument('start',type=int);p.add_argument('end',type=int);p.add_argument('revision');a=p.parse_args()
    collect(a.players,a.source_mode,a.mode,a.start,a.end,a.revision)
