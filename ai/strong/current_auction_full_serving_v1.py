"""Full fixed-fixture serving validation for both unchanged confirmation policies.

No selection, training or final-seed execution. Search continuations are counted
as search work, never described as zero simulation. Original receipts survive
any failure; this runner cannot retry or submit jobs.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time

ARMS = ('filter', 'conservative_population')
RUNTIME_SHA = 'fc135130689140b6fd72a76e6e14c59a7fea59717b858d330bac0c7f6aad93df'
FIXTURE_SHA = 'f1c97bf909e38e5df372a89d169d80f5a6f24c00dccefacd60b10b767f1fcfa0'
COUNTS = {'2':349,'3':427,'4':527,'5':609,'6':641}


def read(p): return json.loads(Path(p).read_text())
def digest(p):
    with Path(p).open('rb') as f: return hashlib.file_digest(f, 'sha256').hexdigest()
def wire(x): return json.dumps(x, separators=(',', ':'), allow_nan=False)
def object_hash(x): return hashlib.sha256(wire(x).encode()).hexdigest()
def write(p, value):
    p = Path(p); temp = p.with_suffix(p.suffix+'.tmp')
    temp.write_text(json.dumps(value, indent=2, allow_nan=False)+'\n'); temp.replace(p)


def validate_case(c, index):
    assert c['index'] == index
    q = c['request']; g = q['state']; n = len(g['players']); seat = q['player']
    assert n in range(2,7) and type(seat) is int and 0<=seat<n and seat in g['currentPlayers']
    assert c['players'] == n and c['stage'] == g['phase']
    assert g['map']['name'] == 'Germany' and g['options']['showMoney'] is True
    assert g['options']['variant'] in ('original','recharged') and type(g['options']['fastBid']) is bool
    assert c['variant']==g['options']['variant'] and c['sealed'] is g['options']['fastBid']
    assert g['seed'] == 'secret' and g['powerPlantsDeck'] == [] and g['hiddenLog'] == []
    assert 'powerPlantDeckAfterStep3' not in g and 'automation' not in g
    assert all(p['lastMove'] is None and (not g['options']['fastBid'] or p['bid'] == 0) for p in g['players'])
    assert c['legal'] and c['player_order'] == [(seat+i)%n for i in range(n)]
    assert isinstance(q['requestId'],str) and type(q['revision']) is int
    assert isinstance(c['original_line_sha256'],str) and len(c['original_line_sha256']) == 64


def cases(package):
    counts=Counter(); seen=set(); total=0
    with (package/'cases.jsonl').open() as f:
        for index,line in enumerate(f):
            c=json.loads(line); validate_case(c,index)
            assert c['request']['requestId'] not in seen
            seen.add(c['request']['requestId']); counts[str(c['players'])]+=1;total+=1
            yield c
    assert total==2553 and dict(counts)==COUNTS


def checked_package(package):
    m=read(package/'benchmark-manifest.json')
    assert m['runtime_manifest_sha256']==RUNTIME_SHA and m['original_fixture_sha256']==FIXTURE_SHA
    assert m['arms']==list(ARMS) and m['positions']==2553 and m['requests']==5106
    assert m['runner_sha256']==digest(__file__)
    assert digest(package/'artifact/manifest.json')==RUNTIME_SHA
    assert all(digest(package/n)==h for n,h in m['files'].items())
    assert sum(1 for _ in cases(package))==2553
    return m


def dependencies(package):
    sys.path.insert(0,str(package/'artifact/ai/strong'))
    sys.path.insert(0,str(package))
    from public_policy_arena_v1 import PublicPolicyProcess
    from public_policy_final_audit_v1 import artifact_identity
    from current_auction_cpu_v1 import verify_response
    return PublicPolicyProcess,artifact_identity,verify_response


def run(package,output):
    manifest=checked_package(package)
    assert not output.exists() and not output.is_relative_to(package/'artifact')
    cpu=next(l.split(':',1)[1].strip() for l in Path('/proc/cpuinfo').read_text().splitlines() if l.startswith('model name'))
    assert '8840U' in cpu and not os.environ.get('NODE_OPTIONS')
    process_type,identity,verify=dependencies(package);artifact=package/'artifact'
    identities={a:identity(artifact,f'policies/{a}.json') for a in ARMS};assert identities==manifest['identities']
    import numpy,onnxruntime,huggingface_hub
    output.mkdir(parents=True,exist_ok=False)
    state={'stage':'running','pid':os.getpid(),'started_at':datetime.now(timezone.utc).isoformat(),
        'processor':cpu,'host':platform.node(),'python':platform.python_version(),
        'numpy':numpy.__version__,'onnxruntime':onnxruntime.__version__,'huggingface_hub':huggingface_hub.__version__,
        'node':subprocess.check_output(['node','--version'],text=True).strip(),
        'manifest_sha256':digest(package/'benchmark-manifest.json'),'completed_requests':0,'expected_requests':5106,
        'new_hf_jobs':0,'new_full_evaluation_games':0,'gradient_updates':0,'candidate_selected':False,
        'qualified':False,'reserved_final_seeds_used':False,
        'scope':'All 2553 original public fixtures, both frozen confirmation policies on actual 8840U. Fixed-position serving and latency only; search continuations counted. No strength or checkpoint parity claim.'}
    write(output/'status.json',state);start=time.perf_counter();cpu0=os.times();counts={a:Counter() for a in ARMS}
    try:
        with (output/'receipts.jsonl').open('x') as receipts:
            for arm in ARMS:
                with (output/(arm+'.stderr.log')).open('x') as stderr:
                    cold=time.perf_counter();process=process_type(artifact,f'policies/{arm}.json',stderr)
                    try:
                        for c in cases(package):
                            before=wire(c['request']);begin=time.perf_counter();response=process.call(c['request']);end=time.perf_counter()
                            assert before==wire(c['request'])
                            counts[arm].update(verify(c,arm,response,identities[arm]))
                            r={'arm':arm,'index':c['index'],'request_sha256':object_hash(c['request']),
                                'players':c['players'],'stage':c['stage'],'response':response,
                                'round_trip_ms':1000*(end-begin),
                                'cold_process_plus_request_ms':1000*(end-cold) if c['index']==0 else None}
                            receipts.write(wire(r)+'\n');receipts.flush();state['completed_requests']+=1
                            state.update(current_arm=arm,current_fixture=c['index']);write(output/'status.json',state)
                            if c['index']%25==0:print(json.dumps({'arm':arm,'completed_requests':state['completed_requests']}),flush=True)
                    finally:process.close()
        assert state['completed_requests']==5106 and all(v.get('rollout_caps',0)==0 for v in counts.values())
        checked_package(package);state.update(stage='completed',passed=True)
    except BaseException as error:
        state.update(stage='failed',passed=False,failure_type=type(error).__name__,failure=str(error));raise
    finally:
        cpu1=os.times();state.update(seconds=time.perf_counter()-start,cpu_seconds=sum(cpu1[:4])-sum(cpu0[:4]),
            counts={a:dict(c) for a,c in counts.items()},finished_at=datetime.now(timezone.utc).isoformat())
        state['output_hashes']={p.name:digest(p) for p in output.iterdir() if p.is_file() and p.name!='status.json'}
        write(output/'status.json',state)


def audit(package,output):
    manifest=checked_package(package);state=read(output/'status.json')
    assert state['stage']=='completed' and state['passed'] and '8840U' in state['processor']
    assert state['completed_requests']==5106 and state['manifest_sha256']==digest(package/'benchmark-manifest.json')
    assert set(state['output_hashes'])=={'receipts.jsonl',*(a+'.stderr.log' for a in ARMS)}
    assert all(digest(output/n)==h for n,h in state['output_hashes'].items())
    _,identity,verify=dependencies(package);artifact=package/'artifact'
    identities={a:identity(artifact,f'policies/{a}.json') for a in ARMS};assert identities==manifest['identities']
    import numpy as np
    counts={a:Counter() for a in ARMS};times={a:{} for a in ARMS};cold={}
    with (output/'receipts.jsonl').open() as f:
        for arm in ARMS:
            for c in cases(package):
                r=json.loads(next(f));assert r['arm']==arm and r['index']==c['index']
                assert r['players']==c['players'] and r['stage']==c['stage'] and r['request_sha256']==object_hash(c['request'])
                counts[arm].update(verify(c,arm,r['response'],identities[arm]))
                elapsed=r['round_trip_ms'];assert np.isfinite(elapsed) and elapsed>=0
                if c['index']==0:
                    cold[arm]=r['cold_process_plus_request_ms'];assert np.isfinite(cold[arm]) and cold[arm]>=elapsed
                else:
                    assert r['cold_process_plus_request_ms'] is None
                    rule=c['request']['state']['options'];key=f"{c['players']}p/{rule['variant']}/{'sealed' if rule['fastBid'] else 'open'}/{c['stage']}"
                    times[arm].setdefault(key,[]).append(elapsed)
        assert f.read()==''
    assert {a:dict(c) for a,c in counts.items()}==state['counts']
    assert all(c.get('rollout_caps',0)==0 for c in counts.values())
    timings={a:{k:{'positions':len(v),'median_ms':float(np.median(v)),'p95_ms':float(np.percentile(v,95)),
                    'max_ms':max(v)} for k,v in values.items()} for a,values in times.items()}
    return {'complete':True,'requests':5106,'positions_per_policy':2553,'all_moves_legal':True,
        'identities':identities,'counts':state['counts'],'processor':state['processor'],'cold_ms':cold,
        'warm_timings_by_count_rule_phase':timings,'status_sha256':digest(output/'status.json'),
        'manifest_sha256':digest(package/'benchmark-manifest.json'),'scope':state['scope'],
        'candidate_selected':False,'qualified':False,'reserved_final_seeds_used':False}


if __name__=='__main__':
    p=argparse.ArgumentParser(__doc__);p.add_argument('operation',choices=['run','audit']);p.add_argument('--package',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    result=globals()[args.operation](args.package.resolve(),args.output.resolve())
    if result is not None:print(json.dumps(result),flush=True)
