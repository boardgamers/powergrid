"""Reviewed recovery of the interrupted owner, preserving all 360 original jobs.

The host rebooted after the last checkpoint. All 64 unaudited original handles
were completed when inspected. Audit those first, then submit only rows with no
existing guard. No source preparation, job replacement or automatic restart.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import signal
import time

from huggingface_hub import HfApi
from public_policy_development_job_v1 import read, digest
from public_policy_final_contract_v1 import object_hash

ROOT = Path(__file__).resolve().parents[2]
OLD = ROOT/'ai/runs/conservative-auction-development-coordinator-recovery-v2'
OUT = ROOT/'ai/runs/conservative-auction-development-coordinator-recovery-v3'
OLD_SHA = '63d95a1b53fb815107bda721c0599855fab5ba9b488081b9cb8bbe86dfd54005'
SOURCE_SHA = '351fc4626837c2b7a9d1374e575852abd4fbf4e3d036fbbf406d9fedfb5acafa'


def admit(state, state_sha, process_live, stop_present, guard_count, verified_count, statuses):
    assert state_sha == OLD_SHA, 'Inspect changed predecessor evidence'
    assert state['pid'] == 1919833 and state['stage'] == 'waiting_for_original_development_jobs'
    assert state['development_submitted'] == guard_count == 360
    assert state['development_verified'] == verified_count == 296
    assert state['development_expected'] == 648 and state['development_source_sha256'] == SOURCE_SHA
    assert not process_live and not stop_present, 'Do not recover a live or explicitly stopped owner'
    assert len(statuses) == 64 and all(v == 'COMPLETED' for v in statuses.values()), 'Inspect incomplete/failed/ambiguous original jobs'


def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(filename))
    value = importlib.util.module_from_spec(spec); spec.loader.exec_module(value); return value


def main():
    parser=argparse.ArgumentParser(__doc__)
    parser.add_argument('--start',action='store_true',required=True);parser.parse_args()
    assert not OUT.exists(), 'Inspect the existing recovery; never restart it automatically'
    with (OLD/'.owner.lock').open('a') as old_lock:
        fcntl.flock(old_lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        old=read(OLD/'state.json');proc=Path('/proc')/str(old['pid'])/'cmdline'
        live=proc.exists() and b'recover-conservative-auction-development-v2.py' in proc.read_bytes()
        # The prior host has rebooted; a missing PID alone must not hide another owner.
        peers=[]
        for path in Path('/proc').glob('[0-9]*/cmdline'):
            if int(path.parent.name)==os.getpid():continue
            try:
                parts=path.read_bytes().split(b'\x00')
                if any(p.endswith((b'coordinate-conservative-auction-development-v2.py',
                    b'recover-conservative-auction-development-v2.py',b'recover-conservative-auction-development-v3.py',
                    b'manage-conservative-auction-development-v2.py')) for p in parts):peers.append(path.parent.name)
            except (FileNotFoundError,PermissionError,ProcessLookupError):pass
        assert not peers, 'Another development owner or collector is live'
        assert all(digest(ROOT/name)==sha for name,sha in old['code_hashes'].items())
        tests=(ROOT/'ai/runs/conservative-auction-owner-recovery-tests-v3.log').read_text()
        assert 'Ran 4 tests' in tests and tests.rstrip().endswith('OK')
        manager=module('existing_frozen_development','manage-conservative-auction-development-v2.py')
        assert digest(manager.SOURCE)==SOURCE_SHA
        source=manager.source_checked();fingerprint=object_hash(source)
        expected={r['name']:r for r in source['rows']};guards=[];uncached=[];verified=0
        for path in sorted(manager.OUT.glob('*/launch.json')):
            guard=read(path);row=expected[path.parent.name]
            assert guard['stage']=='launched' and guard['source_fingerprint']==fingerprint and guard['row']==row
            item={'name':row['name'],'job_id':guard['job_id'],'guard_sha256':digest(path)}
            saved=path.parent/'verified.json'
            if saved.exists():
                record=read(saved)
                assert record['verified'] and record['stage']=='COMPLETED' and record['row']==row
                assert record['source_sha256']==SOURCE_SHA and record['guard_sha256']==item['guard_sha256']
                assert record['job_id']==guard['job_id']
                assert digest(path.parent/'artifacts/manifest.json')==record['evidence']['manifest_sha256']
                item.update(verified_sha256=digest(saved),status_basis='cached_original_raw_audit');verified+=1
            else:uncached.append(guard['job_id'])
            guards.append(item)
        assert len({g['job_id'] for g in guards})==len(guards)
        api=HfApi()
        with ThreadPoolExecutor(max_workers=8) as pool:
            stages=list(pool.map(lambda job:api.inspect_job(job_id=job).status.stage,uncached))
        statuses=dict(zip(uncached,stages))
        admit(old,digest(OLD/'state.json'),live,(OLD/'STOP').exists(),len(guards),verified,statuses)
        coordinator=module('unchanged_development_loop','coordinate-conservative-auction-development-v2.py')
        coordinator.OUT=OUT
        OUT.mkdir()
        with (OUT/'.owner.lock').open('a') as owner:
            fcntl.flock(owner,fcntl.LOCK_EX|fcntl.LOCK_NB)
            signal.signal(signal.SIGTERM,coordinator.stop);signal.signal(signal.SIGINT,coordinator.stop)
            boot=next(int(x.split()[1]) for x in Path('/proc/stat').read_text().splitlines() if x.startswith('btime '))
            predecessor={'previous_owner_state':old,'previous_state_sha256':OLD_SHA,'previous_log_sha256':digest(OLD.with_suffix('.log')),
                'host_boot_unix_seconds':boot,'previous_owner_absent':True,'other_owners_or_collectors':peers,
                'original_guards':guards,'uncached_original_statuses':statuses,'source_sha256':SOURCE_SHA,
                'reviewed_reason':'Host rebooted since last checkpoint; old PID absent, all pins match, all 360 guards unambiguous, 64 unaudited originals completed. Exact termination time/cause is not established.',
                'authorization':'Active human-resumed research goal; preserve all existing jobs and use unchanged audit-before-submission loop.',
                'replacement_jobs':0}
            manager.write_new(OUT/'predecessor.json',predecessor)
            pins={**old['code_hashes'],**{str((Path(__file__).parent/name).relative_to(ROOT)):digest(Path(__file__).parent/name)
                for name in (Path(__file__).name,'test_conservative_auction_owner_recovery_v3.py')}}
            state={'pid':os.getpid(),'started_at':coordinator.now(),'stage':'recovery_admitted',
                'code_hashes':pins,'pilots_verified':4,'development_verified':verified,'development_submitted':len(guards),
                'development_expected':648,'development_source_sha256':SOURCE_SHA,'original_pilots':old['original_pilots'],
                'predecessor_sha256':digest(OUT/'predecessor.json'),'new_gradients':0,'qualified':False,
                'reserved_final_seeds_used':False,'max_active_development_jobs':64,'automatic_restarts':False,'replacement_jobs':0}
            coordinator.write_state(state)
            try:
                while True:
                    if coordinator.development_tick(manager,state):break
                    time.sleep(45)
                coordinator.check_pins(state)
                coordinator.write_state(state,stage='complete',result_sha256=digest(manager.RESULT),completed_games=10080,
                    next_action='Archive and independently compare all complete outcomes; no automatic selection or qualification')
            except BaseException as error:
                coordinator.write_state(state,stage='stopped_for_inspection',failure_type=type(error).__name__,failure=str(error),
                    next_action='Inspect original evidence and handles; never restart or resubmit blindly')
                raise


if __name__=='__main__':main()
