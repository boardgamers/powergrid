"""Continue the frozen grid after two explicitly reviewed bootstrap retries.

This owner can only collect selected attempts and submit previously unsubmitted
rows. It cannot create another retry, alter policies, or select a candidate.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import importlib.util
import json
import os
from pathlib import Path
import signal
import time

from huggingface_hub import HfApi
from public_policy_development_job_v1 import read,digest

ROOT=Path(__file__).resolve().parents[2]


def module(name,filename):
    spec=importlib.util.spec_from_file_location(name,Path(__file__).with_name(filename))
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value


def admit_selected(source,manager,api):
    guards=[];pending=[];verified=0
    for row in source['rows']:
        folder=manager.execution_folder(row['name']);path=folder/'launch.json'
        if not path.exists():
            assert row['name'] not in manager.recovery.TARGETS,'Explicit retry operation must finish first'
            continue
        guard=read(path);manager.guard_checked(source,row,guard)
        item={'name':row['name'],'job_id':guard['job_id'],'directory':str(folder.relative_to(ROOT)),
            'guard_sha256':digest(path),'retry_of':guard.get('retry_of')}
        if (folder/'verified.json').exists():
            manager.cached_checked(source,row,folder);verified+=1
            item['verified_sha256']=digest(folder/'verified.json')
        else:pending.append(guard['job_id'])
        guards.append(item)
    assert len({r['job_id'] for r in guards})==len(guards)
    with ThreadPoolExecutor(max_workers=8) as pool:
        statuses=dict(zip(pending,pool.map(lambda handle:api.inspect_job(job_id=handle).status.stage,pending)))
    assert all(s in ('SCHEDULING','RUNNING','COMPLETED') for s in statuses.values()),'Inspect failed/unknown selected attempt; do not retry'
    assert sum(s!='COMPLETED' for s in statuses.values())<=64
    return guards,statuses,verified


def tick(manager,coordinator,state,source):
    coordinator.check_pins(state)
    result=manager.collect()
    coordinator.write_state(state,stage='audited_selected_development_attempts',development_verified=result['verified_jobs'])
    if result['complete']:return True
    coordinator.check_pins(state)
    launched=manager.launch(execute=True,limit=64)
    submitted=sum((manager.execution_folder(r['name'])/'launch.json').exists() for r in source['rows'])
    coordinator.write_state(state,stage='waiting_for_selected_development_attempts',development_submitted=submitted,
        total_hf_attempts=submitted+2,active_at_submission=launched['active_jobs'])
    return False


def main():
    parser=argparse.ArgumentParser(__doc__);parser.add_argument('--start',action='store_true',required=True);parser.parse_args()
    manager=module('attempt_manager','manage-conservative-auction-attempts-v1.py')
    assert not manager.OWNER.exists(),'Inspect original owner outcome; never restart automatically'
    with manager.exclusive_execution() as previous:
        manager.tests_checked();source=manager.source_checked()
        guards,statuses,verified=admit_selected(source,manager,HfApi())
        old_path=ROOT/'ai/runs/conservative-auction-development-coordinator-recovery-v3/state.json'
        pins={**previous['code_hashes'],**{str((ROOT/'ai/strong'/name).relative_to(ROOT)):digest(ROOT/'ai/strong'/name)
            for name in (*manager.TEST_PINS,'conservative-auction-bootstrap-recovery-v1.json','node-runtime-cache-v1.json',
                         'conservative_auction_analysis_v2.py')}}
        coordinator=module('unchanged_owner_primitives','coordinate-conservative-auction-development-v2.py')
        coordinator.OUT=manager.OWNER;manager.OWNER.mkdir()
        signal.signal(signal.SIGTERM,coordinator.stop);signal.signal(signal.SIGINT,coordinator.stop)
        predecessor={'previous_owner_state':previous,'previous_state_sha256':digest(old_path),
            'selected_guards':guards,'uncached_selected_statuses':statuses,'source_sha256':digest(manager.SOURCE),
            'failed_original_attempts':read(manager.recovery.APPROVAL)['allowed_retries'],
            'bootstrap_recovery_sha256':digest(manager.recovery.APPROVAL),'tests_sha256':digest(manager.TEST_RESULT),
            'reviewed_reason':'Exactly two original Node downloads failed before evaluation. Their failed guards remain unchanged; separate explicit attempts use the same release from a verified immutable HF cache. Continue unchanged policies, schedules and source.',
            'automatic_retries':False}
        manager.write_new(manager.OWNER/'predecessor.json',predecessor)
        state={'pid':os.getpid(),'started_at':coordinator.now(),'stage':'reviewed_attempts_admitted',
            'code_hashes':pins,'pilots_verified':4,'development_verified':verified,'development_submitted':len(guards),
            'development_expected':648,'total_hf_attempts':len(guards)+2,'failed_original_attempts':2,
            'development_source_sha256':digest(manager.SOURCE),'original_pilots':previous['original_pilots'],
            'predecessor_sha256':digest(manager.OWNER/'predecessor.json'),
            'bootstrap_recovery_sha256':digest(manager.recovery.APPROVAL),
            'new_gradients':0,'qualified':False,'reserved_final_seeds_used':False,
            'max_active_development_jobs':64,'automatic_restarts':False,'automatic_retries':False}
        coordinator.write_state(state)
        try:
            while not tick(manager,coordinator,state,source):time.sleep(45)
            coordinator.check_pins(state)
            coordinator.write_state(state,stage='complete',result_sha256=digest(manager.RESULT),completed_games=10080,
                next_action='Run compare-conservative-auction-attempts-v1.py; complete independent raw audit before any selection. No automatic qualification.')
        except BaseException as error:
            coordinator.write_state(state,stage='stopped_for_inspection',failure_type=type(error).__name__,failure=str(error),
                next_action='Inspect failed or interrupted selected attempts. Preserve guards; never restart or retry automatically.')
            raise


if __name__=='__main__':main()
