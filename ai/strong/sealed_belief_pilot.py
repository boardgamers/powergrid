"""Paired policy-belief pilot with exact reproduction of immutable old labels."""
import argparse
from collections import Counter
import gzip,json,os,time
from pathlib import Path
from huggingface_hub import HfApi,hf_hub_download
from strategic_collection import ROOT,read,write,digest,get_model,request_hash
from sealed_belief_teacher import Node,prepare,evaluate,REVISION,predict_batch

PROTOCOL=ROOT/'ai/strong/sealed-belief-pilot-protocol-v1.json'
SOURCE=ROOT/'ai/strong/sealed-belief-pilot-source-v1.json'


def load_roots(n,source_mode):
    p=read(PROTOCOL);pin=read(ROOT/'ai/strong/strategic-teacher-training-roots-v1.json')
    path=ROOT/pin['file'];assert digest(path)==p['roots_sha256']==pin['sha256']
    ids={r['rootId']:r for r in p['selected'] if r['players']==n and r['mode']==source_mode}
    assert n in p['players'] and source_mode in p['source_modes'] and ids
    with gzip.open(path,'rt') as f:roots=[r for r in map(json.loads,f) if r['rootId'] in ids]
    assert len(roots)==len(ids)
    for r in roots:
        assert all(r[k]==v for k,v in ids[r['rootId']].items())
        assert request_hash(r['request'])==r['public_root_sha256']
    return roots


def reference_rows(roots,mode,p):
    manifest=read(ROOT/'ai/strong/strategic-teacher-training-results-v1.json')
    assert digest(ROOT/'ai/strong/strategic-teacher-training-results-v1.json')=='6135dba264e18bdc0d8002ca50719bb3340f94b05e22221812864295fe651e57'
    result={};needed={r['rootId'] for r in roots}
    for key in sorted({f"{r['players']}p-{r['mode']}-{mode}-{r['deal']//2*2}-{r['deal']//2*2+2}" for r in roots}):
        case=manifest['cases'][key]
        path=Path(hf_hub_download(p['repo'],case['prefix']+'/labels.jsonl.gz',revision=case['revision']))
        assert digest(path)==case['artifacts']['labels.jsonl.gz']
        with gzip.open(path,'rt') as f:
            for row in map(json.loads,f):
                if row['rootId'] in needed:result[row['rootId'],row['batch']]=row
    assert len(result)==len(roots)*2;return result


def terminals(rows):
    return sorted([{k:v for k,v in r.items() if k!='initialBelief'} for r in rows],key=lambda r:r['env'])


def verify_rows(rows,roots,mode,p,model,node):
    reference=reference_rows(roots,mode,p);by_id={r['rootId']:r for r in roots}
    seen=set();rollouts=controls=0;belief_changes=Counter()
    for row in rows:
        rid,batch,belief=row['rootId'],row['batch'],row['belief'];key=(rid,batch,belief)
        assert rid in by_id and batch in p['batches'] and belief in p['beliefs'] and key not in seen
        seen.add(key);root=by_id[rid];old=reference[rid,batch]
        assert row['mode']==mode and row['samples']==p['samples']==48 and row['usable']
        assert not row['outer_truncations'] and row['nested_search']=={'decisions':0,'evaluations':0,'truncated':0}
        for field in ['public_root_sha256','split','seed','options','model_proposal']:
            assert row[field]==old[field],field
        assert row['root_metadata']=={k:root[k] for k in ['players','mode','deal','split','variant','sealed','decision','teacherRootIndex']}
        prep=node.call({'op':'prepare',**root['request'],'featureRevision':REVISION})
        assert prep['moves']==root['legal']
        x=prep['observation'];assert model.predict(x['state'],x['actions'])[0]==row['model_proposal']
        neural={}
        if belief=='policy' and mode=='neural':
            for item in prep['prior']:
                x=item['encoded'];index=model.predict(x['state'],x['actions'])[0]
                assert predict_batch(model,[x])[0]==index
                neural[str(item['actor'])]=x['moves'][index]
        assert row['neural_beliefs']==neural and row['prior_actors']==[x['actor'] for x in prep['prior']]
        traces=node.call({'op':'belief-traces',**root['request'],'samples':48,'seed':row['seed'],
            'mode':mode,'belief':belief,'neuralBeliefs':neural})['traces']
        outcomes={str(i):[None]*48 for i in row['options']};rollout_seen=set()
        for r in row['rollouts']:
            sample,index=r['sample'],r['actionIndex'];identity=(sample,index)
            assert identity not in rollout_seen and 0<=sample<48 and index in row['options'];rollout_seen.add(identity)
            assert r['env']==sample*len(row['options'])+row['options'].index(index)
            assert not r['truncated'] and 0<=r['value']<=1 and 0<=r['steps']<=2400
            assert r['roles']==['neural' if mode=='neural' or seat==root['request']['player'] else 'economic' for seat in range(root['players'])]
            assert r['searchStats']=={'decisions':0,'evaluations':0,'truncated':0}
            assert r['initialBelief']=={'kind':belief,'committed':traces[sample]}
            outcomes[str(index)][sample]=r['value']
        assert len(rollout_seen)==48*len(row['options']) and outcomes==row['sample_outcomes']
        proposal=row['model_proposal']
        assert row['paired_advantages_over_proposal']=={str(i):[v-b for v,b in zip(outcomes[str(i)],outcomes[str(proposal)])] for i in row['options']}
        if belief=='uniform_control':
            assert terminals(row['rollouts'])==terminals(old['rollouts']),'Control changed an archived trajectory'
            assert row['sample_outcomes']==old['sample_outcomes'];controls+=len(rollout_seen)
        else:
            belief_changes[rid]+=sum(a!=b for i in row['options'] for a,b in zip(row['sample_outcomes'][str(i)],old['sample_outcomes'][str(i)]))
        rollouts+=len(rollout_seen)
    assert seen=={(r['rootId'],batch,belief) for r in roots for batch in p['batches'] for belief in p['beliefs']}
    return {'roots':len(roots),'searches':len(rows),'rollouts':rollouts,'old_control_rollouts_identical':controls,
        'changed_policy_sample_outcomes':sum(belief_changes.values()),'game_truncations':0,'gradients':False,'qualification_eligible':False}


def verify(out,n,source_mode,mode):
    p=read(PROTOCOL);roots=load_roots(n,source_mode);model=get_model(p)
    status=read(out/'pilot-check.json');assert status['status']=='complete'
    for k,v in {'players':n,'source_mode':source_mode,'mode':mode,'protocol_sha256':digest(PROTOCOL),'model_sha256':model.sha256}.items():assert status[k]==v
    for name,sha in status['artifacts'].items():assert Path(name).name==name and digest(out/name)==sha
    with gzip.open(out/'labels.jsonl.gz','rt') as f:rows=list(map(json.loads,f))
    node=Node('strong/sealed-belief-continuations.cjs')
    try:summary=verify_rows(rows,roots,mode,p,model,node)
    finally:node.close()
    assert summary==status['summary'];return summary


def run(n,source_mode,mode,out,upload):
    p=read(PROTOCOL);assert mode in p['modes'];roots=load_roots(n,source_mode);model=get_model(p)
    out.mkdir(parents=True,exist_ok=False);node=Node('strong/sealed-belief-continuations.cjs');start=time.monotonic()
    status={'status':'running','players':n,'source_mode':source_mode,'mode':mode,'protocol_sha256':digest(PROTOCOL),
        'source_revision':os.environ.get('SOURCE_REVISION'),'source_sha256':os.environ.get('SOURCE_SHA256'),
        'model_sha256':model.sha256,'gradients':False,'qualification_eligible':False}
    rows=[]
    try:
        with gzip.open(out/'labels.jsonl.gz','wt') as f:
            for root in roots:
                options=prepare(node,model,root)
                for belief in p['beliefs']:
                    for batch in p['batches']:
                        row=evaluate(model,root,options,mode,batch,48,p['workers'],belief=belief)
                        assert row['usable'],'A capped rollout cannot be a target'
                        row['root_metadata']={k:root[k] for k in ['players','mode','deal','split','variant','sealed','decision','teacherRootIndex']}
                        f.write(json.dumps(row)+'\n');f.flush();rows.append(row)
                        print({'root':root['rootId'],'belief':belief,'batch':batch,'searches':len(rows),'seconds':time.monotonic()-start},flush=True)
        summary=verify_rows(rows,roots,mode,p,model,node)
        status.update(status='complete',summary=summary,seconds=time.monotonic()-start)
    except BaseException as e:status.update(status='failed',error=type(e).__name__+': '+str(e));raise
    finally:
        node.close();status['artifacts']={x.name:digest(x) for x in out.iterdir() if x.is_file()}
        write(out/'pilot-check.json',status)
        if upload:HfApi().upload_folder(repo_id=p['repo'],folder_path=out,path_in_repo=f'runs/sealed-belief-pilot-v1-{n}p-{source_mode}-{mode}')
    print(status,flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(__doc__);p.add_argument('players',type=int,choices=range(2,7));p.add_argument('source_mode',choices=['economic','snapshot0'])
    p.add_argument('mode',choices=['neural','neural_economic']);p.add_argument('output',type=Path);p.add_argument('--upload',action='store_true');p.add_argument('--verify',action='store_true')
    a=p.parse_args()
    if a.verify:print(json.dumps(verify(a.output,a.players,a.source_mode,a.mode)))
    else:run(a.players,a.source_mode,a.mode,a.output,a.upload)
