"""One lock-protected coordinator for the fixed hybrid grid; never retries jobs."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
import fcntl
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import time

from strategic_collection import ROOT,read,write,digest
from population_hybrid_development import PLAN,PROTOCOL,validate_plan

spec=importlib.util.spec_from_file_location('hybrid_manager',ROOT/'ai/strong/manage-population-hybrid-development.py')
manager=importlib.util.module_from_spec(spec);spec.loader.exec_module(manager)


def main(execute,interval,max_hours):
    plan=read(PLAN);validate_plan(plan,read(PROTOCOL));cases=[r['case'] for r in plan['shards']]
    assert plan['admission']['max_in_flight']==32
    if not execute:
        print({'shards':len(cases),'games':8400,'max_in_flight':32,'execute':False});return
    root=ROOT/'ai/runs/population-hybrid-development-coordinator-v1';root.mkdir(parents=True,exist_ok=True)
    with (root/'coordinator.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        state={'pid':os.getpid(),'started_at':datetime.now(timezone.utc).isoformat(),
            'plan_sha256':digest(PLAN),'code_hashes':plan['dependency_hashes'],
            'stage':'starting','automatic_job_retries':False,'remote_cancellations_allowed':False,
            'qualification_eligible':False,'reserved_final_seeds_used':False}
        def save():
            state['updated_at']=datetime.now(timezone.utc).isoformat()
            temporary=root/'state.tmp.json';write(temporary,state);temporary.replace(root/'state.json')
        deadline=time.monotonic()+max_hours*3600
        try:
            while time.monotonic()<deadline:
                assert digest(PLAN)==state['plan_sha256']
                assert all(digest(ROOT/name)==sha for name,sha in state['code_hashes'].items())
                guards={p.stem:read(p) for p in manager.GUARDS.glob('*.json')}
                assert set(guards)<=set(cases)
                assert all(g['stage']=='launched' and g['plan_sha256']==digest(PLAN) for g in guards.values()), 'Uncertain launch: reconcile the existing handle before continuing'
                assert len({g['job_id'] for g in guards.values()})==len(guards)
                verified={case for case in cases if manager.verified_receipt(case) is not None}
                assert verified<=set(guards)
                pending=[case for case in guards if case not in verified]
                with ThreadPoolExecutor(max_workers=4) as pool:statuses=list(pool.map(manager.inspect,pending))
                write(root/'latest-status.json',{'checked_at':datetime.now(timezone.utc).isoformat(),'jobs':statuses})
                ready=[row['case'] for row in statuses if row['authoritative_status'] in ['COMPLETED','ERROR']]
                with ThreadPoolExecutor(max_workers=4) as pool:collected=list(pool.map(manager.collect,ready))
                failed=[row for row in statuses if row['authoritative_status'] not in ['COMPLETED','RUNNING','SCHEDULING']]
                state.update(stage='collecting',jobs_submitted=len(guards),jobs_verified=len(verified)+sum(r.get('verified',False) for r in collected),failed_jobs=failed)
                save()
                assert not failed,'Job failure retained; no automatic replacement or partial comparison'
                if state['jobs_verified']==len(cases):
                    state['stage']='comparing';save()
                    output=ROOT/'ai/strong/population-hybrid-development-comparison-v1.json'
                    if not output.exists():
                        with (root/'comparison.log').open('w') as log:
                            subprocess.run([sys.executable,'ai/strong/compare-population-hybrid-development.py','--output',str(output)],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
                    result=read(output);assert result['complete'] and result['games']==8400 and result['plan_sha256']==digest(PLAN)
                    state.update(stage='comparison_complete',comparison_sha256=digest(output));save();return
                active=sum(row['authoritative_status'] in ['RUNNING','SCHEDULING'] for row in statuses)
                assert active<=32,'Existing live jobs exceed the fixed admission'
                for case in [c for c in cases if c not in guards][:32-active]:
                    state.update(stage='launching',launching_case=case);save()
                    record=manager.launch(case,execute=True)
                    print({'case':case,'job_id':record['job_id']},flush=True)
                state.update(stage='waiting_for_jobs',jobs_submitted=len(list(manager.GUARDS.glob('*.json'))));save()
                print({k:state[k] for k in ['stage','jobs_submitted','jobs_verified']},flush=True)
                time.sleep(min(interval,max(0,deadline-time.monotonic())))
            state['stage']='observation_window_ended';save()
        except BaseException as error:
            state.update(stage='stopped_with_error',error=type(error).__name__+': '+str(error));save();raise


if __name__=='__main__':
    parser=argparse.ArgumentParser(__doc__);parser.add_argument('--execute',action='store_true')
    parser.add_argument('--interval-seconds',type=int,default=300);parser.add_argument('--max-hours',type=float,default=48)
    args=parser.parse_args();assert args.interval_seconds>=60 and args.max_hours>0
    main(args.execute,args.interval_seconds,args.max_hours)
