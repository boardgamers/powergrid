"""Public states visited by fixed changing policies, with exact capture twins."""
import argparse
from collections import Counter
import gzip,hashlib,json,os,sys,time
from pathlib import Path
from huggingface_hub import HfApi,hf_hub_download
from strategic_collection import ROOT,read,write,digest,request_hash
from arena_statistics import validate_pairs
sys.path.insert(0,str(ROOT/'ai'))
from infer import Model,Node
from pool import EnginePool
from feature_contract import model_revision

PROTOCOL=ROOT/'ai/strong/policy-iteration-collection-protocol-v2.json'
SOURCE=ROOT/'ai/strong/policy-iteration-collection-source-v2.json'


def models(p,key):
    result={}
    for k in {key,'parent'}:
        pin=p['models'][k];path=Path(hf_hub_download(pin['repo'],pin['prefix']+'/inference64.onnx',revision=pin['revision']))
        assert digest(path)==pin['files']['inference64.onnx'];result[k]=Model(path,threads=1)
        assert model_revision(result[k])==pin['feature_revision']
    return result


def seed_for(p,n,key,opponent,smoke):
    return p['smoke_seed_template' if smoke else 'seed_template'].format(players=n,behavior=key,opponent=opponent)


def prefix(n,key,opponent,smoke):return f"runs/policy-iteration-collection-v2-{'smoke-' if smoke else ''}{n}p-{key}-{opponent}"


def verify_games(rows,p,n,key,opponent,smoke):
    deals=1 if smoke else p['deals'];assert len(rows)==deals*4*n
    validate_pairs(rows,n);assert {r['episode'] for r in rows}==set(range(deals*4*n))
    for r in rows:
        assert r['gameSeed']==seed_for(p,n,key,opponent,smoke)+'-'+str(r['episode']//(4*n))
        assert r['seat']==r['episode']//4%n and r['variant']==('recharged' if r['episode']%2 else 'original')
        assert r['sealed']==(r['episode']%4<2) and not r['truncated'] and r['steps']<=1600
        assert r['roles']==['learner' if i==r['seat'] else opponent for i in range(n)]
        assert not r['searchStats'] and r['win']==r['value'][r['seat']]


def run(n,key,opponent,out,smoke=False,upload=False,plain_script='ai/strong/policy-iteration-bridge.cjs'):
    p=read(PROTOCOL);assert n in p['players'] and key in p['behaviors'] and opponent in p['opponents']
    assert not os.environ.get('NODE_OPTIONS');nets=models(p,key);out.mkdir(parents=True,exist_ok=False)
    games=(1 if smoke else p['deals'])*4*n;started=time.monotonic();control=capture=None
    status={'status':'running','players':n,'behavior':key,'opponent':opponent,'smoke':smoke,
        'protocol_sha256':digest(PROTOCOL),'source_revision':os.environ.get('SOURCE_REVISION'),'source_sha256':os.environ.get('SOURCE_SHA256'),
        'model_sha256':nets[key].sha256,'parent_sha256':nets['parent'].sha256,
        'trained':False,'labels_generated':False,'qualification_eligible':False}
    try:
        control=EnginePool(min(p['workers'],games),script=plain_script)
        os.environ['NODE_OPTIONS']='--require '+str(ROOT/'ai/strong/capture-policy-iteration.cjs')
        try:capture=EnginePool(min(p['workers'],games),script='ai/strong/policy-iteration-bridge.cjs')
        finally:os.environ.pop('NODE_OPTIONS',None)
        reset={'op':'reset','n':games,'playerCount':n,'mode':opponent,'arenaSeed':seed_for(p,n,key,opponent,smoke),
            'featureRevisions':{'learner':p['models'][key]['feature_revision'],'snapshot0':p['models']['parent']['feature_revision']}}
        tick=time.monotonic();left,right=control.call(reset),capture.call(reset);engine_seconds=time.monotonic()-tick
        results=[];ordinals=Counter();counts=Counter();index=decisions=0;policy_seconds=0.;trajectory=hashlib.sha256();last=time.monotonic()
        with gzip.open(out/'roots.jsonl.gz','wt') as output:
            while True:
                assert left['ended']==right['ended'];results.extend(left['ended'])
                assert len(left['observations'])==len(right['observations'])==games
                if not any(left['observations']):assert left==right;break
                actions=[None]*games
                for i,(a,b) in enumerate(zip(left['observations'],right['observations'])):
                    if a is None:assert b is None;continue
                    root=b.pop('strategicRoot',None)
                    # During preflight, compare the metadata-only bridge change to
                    # the original historical bridge as well as capture twins.
                    actor=b['actor']
                    if 'actor' not in a:
                        assert plain_script=='ai/strong/bridge.cjs';b_without_actor={k:v for k,v in b.items() if k!='actor'}
                        assert a==b_without_actor
                    else:assert a==b
                    role=b['roles'][actor];assert role in ['learner','snapshot0']
                    model_key=key if role=='learner' else 'parent'
                    assert b['featureRevision']==p['models'][model_key]['feature_revision']
                    tick=time.monotonic();choice=nets[model_key].predict(b['state'],b['actions'])[0]
                    policy_seconds+=time.monotonic()-tick;actions[i]=choice;decisions+=1
                    trajectory.update(json.dumps([b,choice],sort_keys=True).encode())
                    if root and role=='learner':
                        episode=b['episode'];seat=episode//4%n;assert actor==seat==root['request']['player']
                        deal=episode//(4*n);ordinal=ordinals[episode]
                        parent=choice if key=='parent' else nets['parent'].predict(b['state'][:1216],[v[:100] for v in b['actions']])[0]
                        split='validation' if deal in p['validation_deals'] else 'train'
                        assert len(root['legal'])==len(b['actions'])
                        root.update(rootId=f'policy-v2:{n}:{key}:{opponent}:{episode}:{ordinal}',rootIndex=index,
                            players=n,behavior=key,mode=opponent,episode=episode,ordinal=ordinal,deal=deal,split=split,
                            gameSeed=seed_for(p,n,key,opponent,smoke)+'-'+str(deal),variant=b['variant'],sealed=b['sealed'],round=b['round'],
                            public_root_sha256=request_hash(root['request']),model_proposal=parent,model_move=root['legal'][parent],
                            behavior_proposal=choice,behavior_move=root['legal'][choice])
                        output.write(json.dumps(root)+'\n');index+=1;ordinals[episode]+=1;counts[root['decision'],split]+=1
                tick=time.monotonic();left=control.call({'op':'step','actions':actions});right=capture.call({'op':'step','actions':actions})
                engine_seconds+=time.monotonic()-tick
                if time.monotonic()-last>=45:
                    output.flush();print({'completed_games':len(results),'games':games,'roots':index,'seconds':time.monotonic()-started},flush=True);last=time.monotonic()
        rows=[{**r,'seat':r['roles'].index('learner'),'win':r['value'][r['roles'].index('learner')]} for r in results]
        verify_games(rows,p,n,key,opponent,smoke);assert index>0
        write(out/'games.json',rows)
        status.update(status='complete',games=games,engine_game_runs=2*games,roots=index,games_with_roots=len(ordinals),
            root_counts={kind:{split:counts[kind,split] for split in ['train','validation']} for kind in ['nomination','bid','building']},
            all_twin_controls_match=True,trajectory_sha256=trajectory.hexdigest(),decisions=decisions,
            engine_seconds=engine_seconds,policy_seconds=policy_seconds,seconds=time.monotonic()-started,game_truncations=0)
    except BaseException as e:status.update(status='failed',error=type(e).__name__+': '+str(e));raise
    finally:
        if control:control.close()
        if capture:capture.close()
        status['artifacts']={f.name:digest(f) for f in out.iterdir() if f.is_file()};write(out/'collection-check.json',status)
        if upload:HfApi().upload_folder(repo_id=p['repo'],folder_path=out,path_in_repo=prefix(n,key,opponent,smoke))
    print(status,flush=True)


def verify(out,n,key,opponent,smoke=False):
    p=read(PROTOCOL);s=read(out/'collection-check.json');nets=models(p,key);rows=read(out/'games.json')
    verify_games(rows,p,n,key,opponent,smoke)
    expected={'status':'complete','players':n,'behavior':key,'opponent':opponent,'smoke':smoke,'protocol_sha256':digest(PROTOCOL),
        'model_sha256':nets[key].sha256,'parent_sha256':nets['parent'].sha256,'games':len(rows),'engine_game_runs':2*len(rows),
        'all_twin_controls_match':True,'game_truncations':0,'trained':False,'labels_generated':False,'qualification_eligible':False}
    for k,v in expected.items():assert s[k]==v,k
    assert set(s['artifacts'])=={'games.json','roots.jsonl.gz'}
    for name,sha in s['artifacts'].items():assert digest(out/name)==sha
    node=Node('strong/worker.cjs');index=0;ordinals=Counter();counts=Counter();by_game={r['episode']:r for r in rows};changed=0
    try:
        with gzip.open(out/'roots.jsonl.gz','rt') as f:
            for r in map(json.loads,f):
                ep=r['episode'];game=by_game[ep];ordinal=ordinals[ep];deal=ep//(4*n)
                split='validation' if deal in p['validation_deals'] else 'train'
                assert r['rootId']==f'policy-v2:{n}:{key}:{opponent}:{ep}:{ordinal}'
                assert r['rootIndex']==index and r['ordinal']==ordinal and r['deal']==deal and r['split']==split
                assert r['players']==n and r['behavior']==key and r['mode']==opponent
                for field in ['gameSeed','variant','sealed']:assert r[field]==game[field]
                state,seat=r['request']['state'],r['request']['player'];assert seat==game['seat']
                assert state['options']['showMoney'] and len(state['players'])==n and state['round']==r['round']
                assert state['options']['variant']==r['variant'] and bool(state['options']['fastBid'])==r['sealed']
                assert not state['powerPlantsDeck'] and not state['hiddenLog'] and state['seed']=='secret'
                assert 'powerPlantDeckAfterStep3' not in state and 'automation' not in state
                assert all(player['lastMove'] is None for player in state['players'])
                if r['sealed']:assert state['currentBid']==0 and all(not player['bid'] for player in state['players'])
                assert request_hash(r['request'])==r['public_root_sha256']
                x=node.call({**r['request'],'featureRevision':p['models'][key]['feature_revision']})
                assert x['moves']==r['legal']
                kind=next((kind for name,kind in [('ChoosePowerPlant','nomination'),('Bid','bid'),('Build','building')] if any(m['name']==name for m in x['moves'])),None)
                assert len(x['moves'])>1 and r['decision']==kind
                assert nets[key].predict(x['state'],x['actions'])[0]==r['behavior_proposal']
                parent_x=node.call({**r['request'],'featureRevision':p['models']['parent']['feature_revision']}) if key!='parent' else x
                assert parent_x['moves']==r['legal'] and parent_x['state']==x['state'][:1216] and parent_x['actions']==[a[:100] for a in x['actions']]
                assert nets['parent'].predict(parent_x['state'],parent_x['actions'])[0]==r['model_proposal']
                assert r['behavior_move']==r['legal'][r['behavior_proposal']] and r['model_move']==r['legal'][r['model_proposal']]
                changed+=r['behavior_proposal']!=r['model_proposal'];index+=1;ordinals[ep]+=1;counts[kind,split]+=1
    finally:node.close()
    assert index==s['roots'] and len(ordinals)==s['games_with_roots']
    assert s['root_counts']=={kind:{split:counts[kind,split] for split in ['train','validation']} for kind in ['nomination','bid','building']}
    return {'games':len(rows),'roots':index,'public_behavior_and_parent_proposals_verified':index,
        'behavior_disagreements_with_parent':changed,'root_counts':s['root_counts'],'seconds':s['seconds'],
        'engine_seconds':s['engine_seconds'],'policy_seconds':s['policy_seconds'],'qualification_eligible':False}


if __name__=='__main__':
    p=argparse.ArgumentParser(__doc__);p.add_argument('players',type=int,choices=range(2,7));p.add_argument('behavior',choices=['parent','11101','11102'])
    p.add_argument('opponent',choices=['economic','snapshot0']);p.add_argument('output',type=Path)
    p.add_argument('--smoke',action='store_true');p.add_argument('--verify',action='store_true');p.add_argument('--upload',action='store_true');a=p.parse_args()
    if a.verify:print(json.dumps(verify(a.output,a.players,a.behavior,a.opponent,a.smoke)))
    else:run(a.players,a.behavior,a.opponent,a.output,a.smoke,a.upload)
