"""Independent integrity/coverage checks for public opponent-behaviour records."""
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import re
import subprocess

import numpy as np
from strategic_collection import read, digest
from population_policy_verification import integer, finite, MOVES
from opponent_surrogate_collection_v1 import contract


def verify_row(row, ordinal, q):
    n, seat, rule = q['players'], q['focal_seat'], q['rule']
    assert row['ordinal']==ordinal and row['qualification_eligible'] is False
    integer(row['seat']);assert row['seat']<n and row['seat']!=seat
    assert row['playerCount']==n and row['variant']==('recharged' if rule%2 else 'original')
    assert row['sealed'] is (rule<2)
    request=row['request'];state=request['state']
    assert request['player']==row['seat'] and len(state['players'])==n
    assert state['options']['showMoney'] is True and state['options']['map']=='Germany'
    assert state['options']['variant']==row['variant'] and state['options']['fastBid'] is row['sealed']
    assert state['seed']=='secret' and state['powerPlantsDeck']==state['hiddenLog']==[]
    assert 'powerPlantDeckAfterStep3' not in state and 'automation' not in state
    assert row['round']==state['round'] and row['phase']==state['phase']
    for p in state['players']:
        integer(p['money']);assert p['lastMove'] is None
    if row['sealed']:
        assert state['currentBid']==0 and all(p['bid']==0 for p in state['players'])
    assert re.fullmatch('[a-f0-9]{64}',row['publicRootSha256'])
    o=row['observation']
    assert o['featureRevision']=='4.3-strategic-correction'
    assert len(o['state'])==1217 and np.isfinite(o['state']).all()
    assert len(o['actions'])==len(o['moves'])>1
    assert all(len(a)==101 and np.isfinite(a).all() for a in o['actions'])
    assert o['playerOrder'][0]==row['seat'] and set(o['playerOrder'])==set(range(n))
    assert o['playerMask']==[1]*n+[0]*(6-n)
    integer(row['target']);assert row['target']<len(o['moves'])
    options,result=row['teacher']['options'],row['teacher']['result']
    assert options['samples']==16 and options['candidates']==6 and options['geography'] is True
    assert options.get('maxSteps',2400)==2400 and options.get('continuation','mixed')=='mixed'
    assert isinstance(options['seed'],str) and options['seed'].startswith('arena-search-')
    assert result['index']==row['target'] and result['action']==o['moves'][row['target']]
    assert result.get('truncated',0)==0
    integer(result['evaluations'])
    if result['evaluations']:
        values=result['values']
        assert result['evaluations']==16*len(values)
        for key,value in values.items():
            assert str(int(key))==key and 0<=int(key)<len(o['moves'])
            finite(value);assert value<=16
        assert values[str(row['target'])]==max(values.values())
        assert result['winEstimate']==values[str(row['target'])]/16
    finite(row['teacher']['elapsedMs'])
    names={m['name'] for m in o['moves']}
    assert names & {'ChoosePowerPlant','Bid','Build'}
    phase='building' if 'Build' in names else 'bid' if 'Bid' in names else 'plant'
    return phase,result['evaluations'],row['teacher']['elapsedMs']


def verify_game(folder, q, result):
    expected={'contract.json','opponent-decisions.jsonl','focal-decisions.jsonl',
              'terminal.json','verification.json','verification.log'}
    assert {p.name for p in folder.iterdir()}==expected|{'verified.json'}
    assert read(folder/'contract.json')==q
    assert read(folder/'verified.json')==result and all(result[k]==v for k,v in q.items())
    assert result['complete'] is True and result['caps']==0 and result['twin_exact'] is q['twin']
    assert set(result['files'])==expected
    assert all(digest(folder/name)==sha for name,sha in result['files'].items())
    assert re.fullmatch('[a-f0-9]{64}',result['trajectory_sha256'])
    finite(result['seconds']);assert result['seconds']>0
    n,seat=q['players'],q['focal_seat']
    terminal=read(folder/'terminal.json')
    assert terminal['env']==0 and terminal['episode']==q['episode'] and terminal['playerCount']==n
    assert terminal['gameSeed']==q['seed']+'-'+str(q['deal'])
    assert terminal['variant']==('recharged' if q['rule']%2 else 'original') and terminal['sealed'] is (q['rule']<2)
    assert terminal['roles']==['learner' if i==seat else 'search_geo' for i in range(n)]
    assert terminal['truncated'] is False and 0<terminal['steps']<=1600
    scores=[tuple(p[k] for k in ('powered','money','cities')) for p in terminal['final']['players']]
    assert len(scores)==n
    for score in scores:
        for value in score: integer(value)
        assert score[0]<=score[2]
    best=max(scores)
    assert terminal['value']==[1/scores.count(best) if score==best else 0 for score in scores]
    focal_moves=Counter();focal_rows=0
    with (folder/'focal-decisions.jsonl').open() as stream:
        for i,line in enumerate(stream):
            row=json.loads(line)
            assert row['decision']==i and row['move']['name'] in MOVES
            integer(row['index']);integer(row['model_proposal'])
            assert type(row['filter_applied']) is bool
            if row['filter_applied']:
                assert row['move']=={'name':'Pass','data':True} and row['index']!=row['model_proposal']
            else: assert row['index']==row['model_proposal']
            focal_moves[row['move']['name']]+=1
            focal_rows+=1
    assert dict(focal_moves)==terminal['policyMoves'] and focal_rows==result['focal_decisions']
    totals=Counter(decisions=0,evaluations=0,truncated=0);phases={};latencies=[]
    with (folder/'opponent-decisions.jsonl').open() as stream:
        for i,line in enumerate(stream):
            phase,evaluations,ms=verify_row(json.loads(line),i,q)
            totals.update(decisions=1,evaluations=evaluations)
            phases.setdefault(phase,[]).append(i);latencies.append(ms)
    verification=read(folder/'verification.json')
    assert verification==read(folder/'verification.log')
    assert dict(totals)==terminal['searchStats']['search_geo']==verification['totals']
    assert totals['decisions']==result['teacher_rows']==verification['rows']>0
    assert totals['evaluations']==result['teacher_rollouts']
    selected=sorted({i for indices in phases.values() for i in (indices[0],indices[-1])})
    assert verification['public_replays']==selected and len(selected)==result['public_replays']
    assert verification['public_inputs_and_targets_verified'] is True and verification['qualification_eligible'] is False
    assert result['phase_rows']==verification['phase_rows']=={k:len(v) for k,v in phases.items()}
    assert sum(latencies)<=result['seconds']*1000
    return {'episode':q['episode'],'players':n,'rule':q['rule'],'seat':seat,'deal':q['deal'],
            'split':q['split'],'twin':q['twin'],'teacher_rows':totals['decisions'],
            'teacher_rollouts':totals['evaluations'],'public_replays':len(selected),'focal_decisions':focal_rows,
            'phase_rows':result['phase_rows'],'teacher_call_p50_ms':float(np.percentile(latencies,50)),
            'teacher_call_p95_ms':float(np.percentile(latencies,95)),'seconds':result['seconds']}


def verify_artifacts(folder, protocol, source, players, start, end, mode, evidence):
    manifest=read(folder/'manifest.json')
    assert {str(p.relative_to(folder)) for p in folder.rglob('*') if p.is_file()}==set(manifest)|{'manifest.json'}
    assert all(digest(folder/name)==sha for name,sha in manifest.items())
    assert digest(folder/'manifest.json')==evidence['manifest_sha256']
    assert len(manifest)+1==evidence['archived_files']
    job=read(folder/'job.json');state=read(folder/'games/status.json');intent=read(folder/'games/intent.json')
    assert job['case']==f'opponent-surrogate-{mode}-v1-{players}p-{start}-{end}'
    assert job['stage']==state['stage']=='complete' and intent['stage']=='running'
    assert not state['errors'] and intent['cases']=={} and intent['errors']==[]
    for k,v in {'players':players,'start':start,'end':end,'mode':mode}.items():
        assert job[k]==state[k]==intent[k]==v
    for row in (job,state,intent):
        assert row['protocol_sha256']==source['protocol_sha256']
        for key in ('gradients','qualification_eligible','reserved_final_seeds_used'):assert row[key] is False
    assert job['automatic_retries'] is False
    assert job['source_revision']==source['revision'] and job['source_sha256']==source['sha256']
    assert job['source_manifest_sha256']==source['manifest_sha256']
    assert job['job_runner_sha256']==source['new_files']['ai/strong/opponent-surrogate-collection-job-v1.py']
    assert state['runner_sha256']==intent['runner_sha256']==source['new_files']['ai/strong/opponent_surrogate_collection_v1.py']
    assert state['model_sha256']==intent['model_sha256']==protocol['focal']['model']['files']['inference64.onnx']
    assert state['workers']==intent['workers']==protocol['workers']==8
    assert state['tasks']==intent['tasks'] and state['pid']==intent['pid']
    assert state['started_at']==intent['started_at']
    contracts=[contract(protocol,players,deal,seat,rule,mode)
               for deal in range(start,end) for seat in range(players) for rule in range(4)]
    assert set(state['cases'])=={str(q['episode']) for q in contracts}
    assert len(state['tasks'])==len(contracts)
    for task,q in zip(state['tasks'],contracts):
        assert {k:task[k] for k in ('players','deal','seat','rule','mode')}=={
            'players':players,'deal':q['deal'],'seat':q['focal_seat'],'rule':q['rule'],'mode':mode}
        # HF Hub resolves the named download to a content-addressed cache blob.
        # The pinned content hash above, rather than its local filename, identifies it.
        assert task['runtime']=='/workspace' and Path(task['model']).is_absolute()
        assert task['model']==state['tasks'][0]['model']
        assert task['output']==f"/workspace/ai/runs/{job['case']}/games/game-{q['episode']}"
    cells=[verify_game(folder/'games'/f"game-{q['episode']}",q,state['cases'][str(q['episode'])]) for q in contracts]
    assert job['games']==len(cells) and job['caps']==0
    assert job['teacher_rows']==state['teacher_rows']==sum(c['teacher_rows'] for c in cells)
    assert job['public_replays']==state['public_replays']==sum(c['public_replays'] for c in cells)
    assert job['twin_games']==state['twin_games']==sum(c['twin'] for c in cells)
    runtime=job['runtime']
    for key in ('seconds','cpu_seconds','sampled_peak_total_rss_bytes','memory_samples'):
        finite(runtime[key]);assert runtime[key]>0
    assert runtime['memory_sampling_period_seconds']==.2
    assert runtime['seconds']>=state['seconds']>=max(c['seconds'] for c in cells)>0
    return {'complete':True,'games':len(cells),'teacher_rows':job['teacher_rows'],
            'teacher_rollouts':sum(c['teacher_rollouts'] for c in cells),'public_replays':job['public_replays'],
            'twin_games':job['twin_games'],'cells':cells,'runtime':runtime,
            'raw_evidence_bytes':sum(p.stat().st_size for p in folder.rglob('*') if p.is_file()),
            'split_games':dict(Counter(c['split'] for c in cells)),
            'training_rows':sum(c['teacher_rows'] for c in cells if c['split']=='train'),
            'caps':0,'mode':mode,'training_eligible':any(c['split']=='train' for c in cells),'qualification_eligible':False}


def replay_public_teachers(artifacts, runtime, output, workers=8):
    """Re-encode all remote examples locally and recompute each recorded replay."""
    output.mkdir(exist_ok=True)
    folders=sorted((artifacts/'games').glob('game-*'))
    def replay(folder):
        dest=output/(folder.name+'.json')
        if not dest.exists():
            with (output/(folder.name+'.log')).open('w') as log:
                subprocess.run(['node',str(runtime/'ai/strong/verify-opponent-surrogate-collection-v1.cjs'),
                                str(runtime),str(folder/'opponent-decisions.jsonl'),str(folder/'contract.json'),str(dest)],
                               stdout=log,stderr=subprocess.STDOUT,check=True)
        assert read(dest)==read(folder/'verification.json')
        return {'episode':read(folder/'contract.json')['episode'],'sha256':digest(dest),
                'public_replays':len(read(dest)['public_replays'])}
    with ThreadPoolExecutor(max_workers=workers) as pool:return list(pool.map(replay,folders))
