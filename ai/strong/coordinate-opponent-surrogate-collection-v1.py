"""Execute the fixed collection plan without duplicate jobs or silent retries."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
import fcntl
import importlib.util
import os
from pathlib import Path
import time

from strategic_collection import ROOT,read,write,digest

spec=importlib.util.spec_from_file_location('surrogate_collection_manager',Path(__file__).with_name('manage-opponent-surrogate-collection-v1.py'))
manager=importlib.util.module_from_spec(spec);spec.loader.exec_module(manager)
launcher=manager.launcher
OUT=ROOT/'ai/runs/opponent-surrogate-collection-coordinator-v1'


def dependencies():
    return {**manager.code_hashes(),str(Path(__file__).relative_to(ROOT)):digest(__file__)}


def cycle(plan,state,save):
    cases=[r['case'] for r in plan['shards']]
    guards={p.stem:read(p) for p in launcher.GUARDS.glob('*.json')}
    assert set(guards)<=set(cases)
    assert all(g['stage']=='launched' and g['plan_sha256']==digest(launcher.PLAN) for g in guards.values())
    assert len({g['job_id'] for g in guards.values()})==len(guards)
    verified={case for case in cases if manager.verified_receipt(case) is not None}
    assert verified<=set(guards)
    with ThreadPoolExecutor(max_workers=4) as pool:
        statuses=list(pool.map(manager.inspect,[case for case in guards if case not in verified]))
    write(OUT/'latest-status.json',{'checked_at':datetime.now(timezone.utc).isoformat(),'jobs':statuses})
    ready=[r['case'] for r in statuses if r['authoritative_status']=='COMPLETED']
    with ThreadPoolExecutor(max_workers=2) as pool:collected=list(pool.map(manager.collect,ready))
    failures=[r for r in statuses if r['authoritative_status'] not in manager.ACTIVE|{'COMPLETED'}]
    state.update(stage='collecting',jobs_submitted=len(guards),jobs_verified=len(verified)+sum(r.get('verified',False) for r in collected),failed_jobs=failures)
    save()
    assert not failures, 'Inspect original failed/unknown jobs; no automatic replacements'
    if state['jobs_verified']==len(cases):
        state['stage']='indexing';save()
        if not manager.INDEX.exists():manager.index()
        result=read(manager.INDEX)
        assert result['complete'] and result['games']==2560 and result['twins']==640
        assert result['plan_sha256']==digest(launcher.PLAN) and result['protocol_sha256']==digest(launcher.PROTOCOL)
        assert set(result['cases'])==set(cases) and all(digest(ROOT/name)==sha for name,sha in result['code_hashes'].items())
        assert all(digest(manager.COLLECTED/case/'verified.json')==r['verified_sha256'] for case,r in result['cases'].items())
        state.update(stage='collection_complete',index_sha256=digest(manager.INDEX));save();return True
    active=sum(r['authoritative_status'] in manager.ACTIVE for r in statuses)
    limit=plan['admission']['max_in_flight'];assert active<=limit
    for case in [case for case in cases if case not in guards][:limit-active]:
        state.update(stage='launching',launching_case=case);save();launcher.launch(case,True)
    state.update(stage='waiting_for_jobs',jobs_submitted=len(list(launcher.GUARDS.glob('*.json'))));save()
    print({k:state[k] for k in ('stage','jobs_submitted','jobs_verified')},flush=True)
    return False


def main(execute,interval,max_hours):
    assert interval>=60 and max_hours>0
    plan=read(launcher.PLAN);launcher.admission(plan['shards'][0]['case'])
    if not execute:
        print({'jobs':len(plan['shards']),'games':plan['games'],'twins':plan['twins'],'admission':plan['admission'],'execute':False});return
    OUT.mkdir(parents=True,exist_ok=True)
    with (OUT/'coordinator.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        state={'pid':os.getpid(),'started_at':datetime.now(timezone.utc).isoformat(),'plan_sha256':digest(launcher.PLAN),
               'code_hashes':dependencies(),'stage':'starting','automatic_job_retries':False,'remote_cancellations_allowed':False,
               'gradients':False,'qualification_eligible':False,'reserved_final_seeds_used':False}
        if (OUT/'state.json').exists():
            old=read(OUT/'state.json');assert old['plan_sha256']==state['plan_sha256'] and old['code_hashes']==state['code_hashes']
        def save():
            state['updated_at']=datetime.now(timezone.utc).isoformat()
            temporary=OUT/'state.tmp.json';write(temporary,state);temporary.replace(OUT/'state.json')
        deadline=time.monotonic()+max_hours*3600
        try:
            while time.monotonic()<deadline:
                assert digest(launcher.PLAN)==state['plan_sha256'] and dependencies()==state['code_hashes']
                if cycle(plan,state,save):return
                time.sleep(min(interval,max(0,deadline-time.monotonic())))
            state['stage']='observation_window_ended';save()
        except BaseException as error:
            state.update(stage='stopped_with_error',error=type(error).__name__+': '+str(error));save();raise


if __name__=='__main__':
    p=argparse.ArgumentParser(__doc__);p.add_argument('--execute',action='store_true')
    p.add_argument('--interval-seconds',type=int,default=180);p.add_argument('--max-hours',type=float,default=48)
    a=p.parse_args();main(a.execute,a.interval_seconds,a.max_hours)
