"""Independently validate public-root, role, sample and nested-cap provenance."""
import argparse
import json
import math
from pathlib import Path
import re
from huggingface_hub import hf_hub_download
from strategic_collection import ROOT, read, write, digest, get_model
from strategic_teacher import Node, MODES, prepare

def collect(n, mode, revision):
    assert re.fullmatch('[a-f0-9]{40}',revision)
    protocol_path=ROOT/'ai/strong/strategic-teacher-probe-protocol-v1.json';p=read(protocol_path)
    source=read(ROOT/'ai/strong/strategic-teacher-probe-source-v1.json')
    roots_pin=read(ROOT/'ai/strong/strategic-teacher-probe-roots-v1.json')
    assert digest(ROOT/roots_pin['file'])==p['roots_sha256']==roots_pin['sha256']
    prefix=f'runs/strategic-teacher-probe-v1-{n}p-{mode}'
    path=Path(hf_hub_download(p['repo'],prefix+'/probe-check.json',revision=revision));status=read(path)
    expected={'status':'complete','players':n,'mode':mode,'protocol_sha256':digest(protocol_path),
        'source_revision':source['revision'],'source_sha256':source['sha256'],'model_sha256':p['model']['sha256'],
        'roots_sha256':p['roots_sha256'],'trained':False,'qualification_eligible':False,
        'game_truncations':0,'nested_truncations':0,'positions':2,'searches':4}
    for key,value in expected.items():assert status[key]==value,key
    assert set(status['artifacts'])=={'rollouts.jsonl'}
    rows_path=Path(hf_hub_download(p['repo'],prefix+'/rollouts.jsonl',revision=revision))
    assert digest(rows_path)==status['artifacts']['rollouts.jsonl']
    rows=[json.loads(line) for line in rows_path.read_text().splitlines()];assert len(rows)==4
    roots={r['rootId']:r for r in map(json.loads,(ROOT/roots_pin['file']).read_text().splitlines()) if r['players']==n}
    assert {(r['rootId'],r['batch']) for r in rows}=={(key,batch) for key in roots for batch in p['batches']}
    model=get_model(p);node=Node('strong/strategic-continuations.cjs');options={}
    try:
        for key,root in roots.items():options[key]=prepare(node,model,root)
    finally:node.close()
    evaluations=nested=0
    for row in rows:
        root=roots[row['rootId']];proposal=root['model_proposal'];opts=options[row['rootId']];samples=p['samples']
        assert row['public_root_sha256']==root['public_root_sha256'] and row['split']=='validation'
        assert row['mode']==mode and row['samples']==samples and row['options']==opts and row['model_proposal']==proposal
        assert row['seed']=='strategic-teacher-public-v1-'+root['rootId']+'-'+row['batch']
        assert row['usable'] and not row['outer_truncations'] and not row['qualification_eligible']
        assert len(row['rollouts'])==samples*len(opts)
        assert {r['env'] for r in row['rollouts']}==set(range(samples*len(opts)))
        seen=set();inner={k:0 for k in ['decisions','evaluations','truncated']};decisions=0
        outcomes={str(a):[None]*samples for a in opts}
        for r in row['rollouts']:
            assert 0<=r['sample']<samples and r['actionIndex'] in opts
            key=r['sample'],r['actionIndex'];assert key not in seen;seen.add(key)
            assert r['env']==key[0]*len(opts)+opts.index(key[1])
            assert not r['truncated'] and 0<=r['steps']<=2400
            assert any(math.isclose(r['value'],credit,abs_tol=1e-12) for credit in [0]+[1/k for k in range(1,n+1)])
            expected_roles=[('heuristic' if r['sample']%2 else 'economic') if mode=='mixed_control' else
                'neural' if mode=='neural' or seat==root['request']['player'] else
                'economic' if mode=='neural_economic' else 'search_geo' for seat in range(n)]
            assert r['roles']==expected_roles
            assert all(type(v)==int and v>=0 for v in r['policyDecisions'].values())
            assert sum(r['policyDecisions'].values())==r['steps']
            decisions+=r['policyDecisions']['neural']
            for k in inner:
                assert type(r['searchStats'][k])==int and r['searchStats'][k]>=0
                inner[k]+=r['searchStats'][k]
            assert r['searchStats']['decisions']==r['policyDecisions']['search_geo']
            if mode!='neural_search':assert not any(r['searchStats'].values())
            outcomes[str(key[1])][key[0]]=r['value']
        assert outcomes==row['sample_outcomes'] and inner==row['nested_search'] and inner['truncated']==0
        assert row['paired_advantages_over_proposal']=={str(a):[v-base for v,base in zip(outcomes[str(a)],outcomes[str(proposal)])] for a in opts}
        assert decisions==row['timing']['policy_decisions']
        for key in ['seconds','engine_seconds','policy_seconds']:
            assert math.isfinite(row['timing'][key]) and row['timing'][key]>=0
        evaluations+=len(row['rollouts']);nested+=inner['evaluations']
    assert evaluations==status['evaluations'] and nested==status['nested_evaluations']
    for key in ['engine_seconds','policy_seconds']:
        assert math.isclose(sum(r['timing'][key] for r in rows),status[key],abs_tol=1e-8)
    out=ROOT/f'ai/runs/strategic-teacher-probe-verified-v1/{n}p-{mode}';out.mkdir(parents=True,exist_ok=False)
    (out/'probe-check.json').write_bytes(path.read_bytes());(out/'rollouts.jsonl').write_bytes(rows_path.read_bytes())
    summary={k:status[k] for k in ['players','mode','positions','searches','evaluations','nested_evaluations','game_truncations',
        'nested_truncations','seconds','engine_seconds','policy_seconds']}
    saved={'verified':True,'revision':revision,'prefix':prefix,'source_revision':source['revision'],
        'source_sha256':source['sha256'],'protocol_sha256':digest(protocol_path),'summary':summary,
        'artifacts':{q.name:digest(q) for q in out.iterdir() if q.is_file()},'qualification_eligible':False}
    write(out/'verified.json',saved);print(summary)

if __name__=='__main__':
    p=argparse.ArgumentParser(__doc__);p.add_argument('players',type=int,choices=range(2,7));p.add_argument('mode',choices=MODES)
    p.add_argument('revision');a=p.parse_args();collect(a.players,a.mode,a.revision)
