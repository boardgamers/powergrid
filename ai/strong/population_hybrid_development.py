"""Fixed fresh hybrid experiment contracts and measured runtime admission."""
from datetime import datetime,timezone
import math
from pathlib import Path

from strategic_collection import ROOT,read,digest
from population_policy_verification import verify_evaluation

PROTOCOL=ROOT/'ai/strong/population-hybrid-development-protocol-v1.json'
SOURCE=ROOT/'ai/strong/population-hybrid-development-source-v1.json'
PLAN=ROOT/'ai/strong/population-hybrid-development-plan-v1.json'


def case_key(arm,players,opponent,start,end):
    return f'population-hybrid-development-v1-{arm}-{players}p-{opponent}-{start}-{end}'


def contract(protocol,arm,players,opponent,start,end):
    assert arm in protocol['arms'] and players in range(2,7)
    cells=[row for row in protocol['screens'] if row['players']==players and row['opponent']==opponent]
    assert len(cells)==1
    assert type(start) is int and type(end) is int and 0<=start<end<=4
    assert end-start in [1,2,4] and start%(end-start)==0
    return cells[0]


def expected_config(protocol,arm,players,opponent,start,end,workers=8):
    cell=contract(protocol,arm,players,opponent,start,end)
    return {'players':players,'arm':arm,'opponent':opponent,
        'model_sha256':protocol['model_pin']['files']['inference64.onnx'],
        'opponent_sha256':cell.get('sha256'),
        'seed':protocol['seed_template'].format(players=players),'start':start,'deals':end-start,
        'samples':protocol['search']['samples'],'workers':workers,'search_workers':1}


def runtime_admission():
    protocol=read(PROTOCOL);source=read(ROOT/'ai/strong/population-hybrid-source-v2.json')
    probes=[]
    for n in [2,6]:
        base=ROOT/f'ai/runs/population-hybrid-runtime-collected-v2/population-hybrid-runtime-v2-{n}p'
        verified=read(base/'verified.json')
        assert verified['verified'] and verified['authoritative_status']=='COMPLETED'
        assert verified['source']==source and verified['strength_eligible'] is False
        assert verified['verifier_sha256']==digest(ROOT/'ai/strong/population_policy_verification.py')
        assert verified['collector_sha256']==digest(ROOT/'ai/strong/collect-population-hybrid-runtime.py')
        check=read(base/'artifacts/runtime-check.json')
        assert digest(base/'artifacts/runtime-check.json')==verified['runtime_check_sha256']
        assert check['model_pin']==protocol['model_pin'] and check['protocol_sha256']==digest(PROTOCOL)
        actual=verify_evaluation(base/'artifacts/evaluation',{
            'players':n,'arm':'combined','opponent':'search_geo','start':0,'deals':1,
            'seed':protocol['smoke_seed_template'].format(players=n),
            'model_sha256':protocol['model_pin']['files']['inference64.onnx'],
            'samples':8,'workers':8,'search_workers':1,'opponent_model':None,'opponent_sha256':None})
        assert actual==verified['summary']
        probes.append({'players':n,'seconds':actual['wall_seconds'],
            'verified_sha256':digest(base/'verified.json'),'job_id':verified['job_id'],
            'evidence':verified['evidence']})
    metrics=read(ROOT/'ai/runs/population-hybrid-runtime-metrics-v1.json')
    assert metrics['hardware']=={'name':'cpu-upgrade','cpu':'8 vCPU','ram':'32 GB'}
    assert metrics['job_id']==probes[1]['job_id'] and len(metrics['samples'])>=3
    assert all(row['cpu_millicores']==8000 and row['gpus']=={} for row in metrics['samples'])
    assert all(row['memory_used_bytes'] < .8*row['memory_total_bytes'] for row in metrics['samples'])
    worst=max(row['seconds'] for row in probes)
    for deals in [4,2,1]:
        projected=120+2*deals*worst
        hours=max(1,math.ceil(projected/(.75*3600)))
        if hours<=12:break
    assert hours<=12,'Further execution planning required; never shorten games or search'
    return {'admitted':True,'probes':probes,'deals_per_shard':deals,'projected_seconds':projected,
        'timeout_hours':hours,'flavor':'cpu-upgrade','workers':8,'search_workers':1,
        'max_in_flight':32,'metrics_sha256':digest(ROOT/'ai/runs/population-hybrid-runtime-metrics-v1.json'),
        'calculation':'120s setup + 2x the slower complete endpoint deal times deals per shard; reserve 25% timeout headroom. Split 4/2/1 whole deals if needed; preserve every seat/rule and fixed horizons.',
        'resource_observation':'One short live sample, retained in full: initial CPU0 then99/100%, about5.7GB/32GB. Keep the measured 8-process CPU execution; scale independent jobs, not GPU count.',
        'limitation':'Endpoint runtime pilots are not a bound on every future game. Any timeout or cap remains a failed/unverified cell; no automatic retry, truncation-based scoring or partial promotion.',
        'qualification_eligible':False,'reserved_final_seeds_used':False}


def make_plan(protocol,source,admission):
    assert admission['admitted'] and source['protocol_sha256']==digest(PROTOCOL)
    step=admission['deals_per_shard'];assert step in [1,2,4]
    rows=[]
    # Start longer search arms/counts early without changing inclusion or seeds.
    for arm in ['combined','building','auction','model','filter']:
        for cell in sorted(protocol['screens'],key=lambda row:(-row['players'],row['opponent'])):
            for start in range(0,4,step):
                n,opponent=cell['players'],cell['opponent'];end=start+step
                rows.append({'case':case_key(arm,n,opponent,start,end),'arm':arm,'players':n,
                    'opponent':opponent,'start':start,'end':end,'games':step*4*n})
    plan={'created_at':datetime.now(timezone.utc).isoformat(),'protocol_sha256':digest(PROTOCOL),
        'source':source,'admission':admission,'shards':rows,'planned_games':sum(r['games'] for r in rows),
        'qualification_eligible':False,'reserved_final_seeds_used':False}
    validate_plan(plan,protocol)
    return plan


def validate_plan(plan,protocol):
    assert plan['planned_games']==protocol['planned_games_total']==8400
    rows=plan['shards'];assert len(rows)==len({r['case'] for r in rows})
    expected={(arm,cell['players'],cell['opponent'],deal)
        for arm in protocol['arms'] for cell in protocol['screens'] for deal in protocol['deal_offsets']}
    observed=set()
    for row in rows:
        contract(protocol,row['arm'],row['players'],row['opponent'],row['start'],row['end'])
        assert row['case']==case_key(*(row[k] for k in ['arm','players','opponent','start','end']))
        assert row['games']==(row['end']-row['start'])*4*row['players']
        for deal in range(row['start'],row['end']):
            item=(row['arm'],row['players'],row['opponent'],deal);assert item not in observed;observed.add(item)
    assert observed==expected and sum(r['games'] for r in rows)==8400


def verify_job(directory,row,source,protocol):
    directory=Path(directory);check=read(directory/'development-check.json')
    assert check['stage']=='complete' and check['case']==row['case']
    assert check['source_revision']==source['revision'] and check['source_sha256']==source['sha256']
    assert check['protocol_sha256']==digest(PROTOCOL) and check['model_pin']==protocol['model_pin']
    assert check['qualification_eligible'] is check['reserved_final_seeds_used'] is False
    expected=expected_config(protocol,*(row[k] for k in ['arm','players','opponent','start','end']))
    summary=verify_evaluation(directory/'evaluation',expected)
    assert summary['games']==row['games']==check['games']
    assert summary==read(directory/'summary.json')
    return summary
