"""Run the fixed diagnostic with one infrastructure canary and seven jobs at most."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
import fcntl
import importlib.util
import os
from pathlib import Path
import time

from strategic_collection import ROOT,read,write,digest

spec=importlib.util.spec_from_file_location('reference_manager',ROOT/'ai/strong/manage-reference-opponents-v2.py')
manager=importlib.util.module_from_spec(spec);spec.loader.exec_module(manager)
OUT=ROOT/'ai/runs/reference-opponent-coordinator-v2'


def main(execute,max_hours):
    p,d,cases=manager.contract()
    if not execute:
        print({'jobs':len(cases),'canary':cases[0]['case'],'max_in_flight':7,'execute':False});return
    assert d['admission']['max_concurrent_jobs']==7
    paths=[Path(__file__),Path(manager.__file__),Path(manager.launcher.__file__),Path(manager.probe.__file__),
           manager.probe.WORKER,ROOT/'ai/strong/reference-opponent-job-v2.py']
    pins={str(file.relative_to(ROOT)):digest(file) for file in paths}
    pins.update(p['repair_dependencies'])
    OUT.mkdir(exist_ok=True)
    with (OUT/'coordinator.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        state={'pid':os.getpid(),'started_at':datetime.now(timezone.utc).isoformat(),
               'protocol_sha256':d['protocol_sha256'],'code_hashes':pins,'stage':'starting',
               'automatic_retries':False,'remote_cancellations_allowed':False,
               'qualification_eligible':False,'reserved_final_seeds_used':False}
        def save():
            state['updated_at']=datetime.now(timezone.utc).isoformat()
            temporary=OUT/'state.tmp.json';write(temporary,state);temporary.replace(OUT/'state.json')
        deadline=time.monotonic()+max_hours*3600
        last_progress=None
        try:
            while time.monotonic()<deadline:
                assert all(digest(ROOT/name)==sha for name,sha in pins.items())
                guards={file.stem:read(file) for file in manager.GUARDS.glob('*.json')}
                allowed={row['case'] for row in cases}
                assert set(guards)<=allowed
                assert all(g['stage']=='launched' for g in guards.values()),'Reconcile unresolved submission; no automatic resubmission'
                assert len({g['job_id'] for g in guards.values()})==len(guards)
                verified={case for case in allowed if manager.verified(case) is not None}
                assert verified<=set(guards)
                with ThreadPoolExecutor(max_workers=4) as pool:
                    statuses=list(pool.map(manager.inspect,[case for case in guards if case not in verified]))
                write(OUT/'latest-status.json',{'checked_at':datetime.now(timezone.utc).isoformat(),'jobs':statuses})
                failed=[s for s in statuses if s['stage'] not in ('COMPLETED','RUNNING','SCHEDULING')]
                state.update(stage='collecting',jobs_submitted=len(guards),jobs_verified=len(verified),failed_jobs=failed);save()
                assert not failed,'Remote failure retained; no new submissions, replacements, or partial comparison'
                for status in statuses:
                    if status['stage']=='COMPLETED':
                        receipt=manager.collect(status['case']);assert receipt['verified'];verified.add(status['case'])
                state['jobs_verified']=len(verified)
                if len(verified)==len(cases):
                    state.update(stage='comparison_complete',comparison=manager.compare());save()
                    print(state['comparison'],flush=True);return
                active=sum(s['stage'] in ('RUNNING','SCHEDULING') for s in statuses)
                limit=7 if cases[0]['case'] in verified else 1
                assert active<=limit
                for row in [r for r in cases if r['case'] not in guards][:limit-active]:
                    state.update(stage='launching',launching_case=row['case']);save()
                    manager.launcher.main(row['root'],row['begin'],True)
                state.update(stage='waiting_for_jobs',jobs_submitted=len(list(manager.GUARDS.glob('*.json'))),
                             canary_verified=cases[0]['case'] in verified);save()
                progress=(state['jobs_submitted'],state['jobs_verified'],state['canary_verified'])
                if progress!=last_progress:
                    print({k:state[k] for k in ('stage','jobs_submitted','jobs_verified','canary_verified')},flush=True)
                    last_progress=progress
                time.sleep(45)
            state['stage']='observation_window_ended_jobs_not_canceled';save()
        except BaseException as error:
            state.update(stage='stopped_for_review',error=type(error).__name__+': '+str(error));save();raise


if __name__=='__main__':
    parser=argparse.ArgumentParser(__doc__);parser.add_argument('--execute',action='store_true')
    parser.add_argument('--max-hours',type=float,default=12)
    args=parser.parse_args();assert 0<args.max_hours<=48
    main(args.execute,args.max_hours)
