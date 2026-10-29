"""Compare serial and four-process raw auditing, without touching the live owner.

Fixed workload covers normal/recovered data, filter/search and 2/3/4/5/6 players.
ABBA execution order exposes rather than hides warm-cache/order variability.
No policy calls, games, HF requests, writes to original evidence or partial wins.
"""
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime,timezone
import json
import multiprocessing
import os
from pathlib import Path
import statistics
import time

import current_auction_parallel_audit_v1 as worker
from public_policy_development_job_v1 import read,digest
from public_policy_final_contract_v1 import object_hash

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'ai/runs/current-auction-audit-parallel-profile-v1'
RESULT=ROOT/'ai/strong/current-auction-audit-parallel-profile-v1.json'
CASES=[('confirmation','pg-current-confirm-v1-filter-economic-2p-00'),
    ('confirmation','pg-current-confirm-v1-filter-heuristic-3p-20'),
    ('confirmation','pg-current-confirm-v1-filter-economic-4p-00'),
    ('confirmation','pg-current-confirm-v1-filter-economic-5p-02'),
    ('runtime','pg-current-auction-runtime-v1-pop-2p'),
    ('runtime','pg-current-auction-runtime-v1-pop-6p')]


def save(path,value):
    with path.open('x') as f:json.dump(value,f,indent=2,allow_nan=False);f.write('\n')


def now():return datetime.now(timezone.utc).isoformat()


def main():
    assert not OUT.exists() and not RESULT.exists(), 'Inspect original profile outcome; do not repeat'
    owner=read(ROOT/'ai/runs/current-auction-confirmation-recovery-v1/state.json')
    cmd=Path(f"/proc/{owner['pid']}/cmdline").read_bytes().replace(b'\0',b' ')
    assert b'coordinate-current-auction-confirmation-recovery-v1.py --start' in cmd
    assert all(digest(ROOT/n)==h for n,h in owner['code_hashes'].items())
    cases=[];sources=set();expected={}
    for kind,name in CASES:
        m=worker.manager(kind);source=m.source_checked();folder=m.OUT/name
        receipt=m.verified_path(folder) if kind=='confirmation' else folder/'verified.json'
        job=read(receipt);assert job['verified']
        cases.append({'kind':kind,'name':name,'job_id':job['job_id'],
            'source_sha256':digest(m.SOURCE),'verified_sha256':digest(receipt),
            'guard_sha256':digest(folder/'launch.json')})
        expected[name]={'review_sha256':object_hash(job['review']),'games':job['review']['games'],
            'counts':job['review']['audit']['counts'],'original_hf_stage':job['stage']}
        sources.update((m.SOURCE,receipt,folder/'launch.json',folder/'artifacts/manifest.json'))
    sources.update((Path(__file__).resolve(),Path(worker.__file__).resolve()))
    pins={**owner['code_hashes'],**{str(p.relative_to(ROOT)):digest(p) for p in sources}}
    OUT.mkdir()
    metadata={'started_at':now(),'pid':os.getpid(),'cases':cases,'expected':expected,
        'input_hashes':pins,'owner_verified_live_at_start':owner['pid'],'order':['serial','parallel4','parallel4','serial'],
        'scope':'Read-only same-verifier audit timing; not engine, inference, HF-job throughput or playing-strength evidence.',
        'new_policy_calls':0,'new_games':0,'new_hf_jobs':0,'candidate_selected':False,'reserved_final_seeds_used':False}
    save(OUT/'intent.json',metadata);measurements=[]
    for index,mode in enumerate(metadata['order']):
        cpu0=os.times();started=time.perf_counter()
        if mode=='serial':results=[worker.audit_original(c) for c in cases]
        else:
            with ProcessPoolExecutor(max_workers=4,mp_context=multiprocessing.get_context('spawn')) as pool:
                results=list(pool.map(worker.audit_original,cases))
        seconds=time.perf_counter()-started;cpu1=os.times()
        assert [r['name'] for r in results]==[c['name'] for c in cases]
        for result in results:
            assert all(result[k]==v for k,v in expected[result['name']].items())
        measurement={'index':index,'mode':mode,'seconds':seconds,'process_tree_cpu_seconds':sum(cpu1[:4])-sum(cpu0[:4]),
            'per_job':results,'games':sum(r['games'] for r in results),'all_reviews_exact':True}
        save(OUT/f'pass-{index}.json',measurement);measurements.append(measurement)
        print(json.dumps({k:v for k,v in measurement.items() if k!='per_job'}),flush=True)
    assert all(digest(ROOT/n)==h for n,h in pins.items())
    serial=[m['seconds'] for m in measurements if m['mode']=='serial']
    parallel=[m['seconds'] for m in measurements if m['mode']=='parallel4']
    cpu_model=next(line.split(':',1)[1].strip() for line in Path('/proc/cpuinfo').read_text().splitlines() if line.startswith('model name'))
    report={'passed':True,'created_at':now(),'cpu':cpu_model,'logical_cpus':os.cpu_count(),
        'cases':cases,'games_per_pass':measurements[0]['games'],'passes':measurements,
        'median_serial_seconds':statistics.median(serial),'median_parallel_seconds':statistics.median(parallel),
        'median_wall_speedup':statistics.median(serial)/statistics.median(parallel),
        'input_hashes':pins,'all_reviews_exact':True,'original_error_preserved':True,
        'new_policy_calls':0,'new_games':0,'new_hf_jobs':0,'qualified':False,'reserved_final_seeds_used':False,
        'scope':metadata['scope'],'limitations':'Six fixed artifacts, two passes per mode, mixed workloads, live collector competing for CPU/I/O, cached local data. Parallel timings include spawn/import/shutdown. Does not measure download/extraction or authorize changes to the running coordinator.'}
    save(RESULT,report)
    print(json.dumps({k:report[k] for k in ('passed','games_per_pass','median_serial_seconds','median_parallel_seconds','median_wall_speedup')}),flush=True)


if __name__=='__main__':main()
