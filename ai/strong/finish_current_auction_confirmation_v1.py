"""Finish only the frozen confirmation queue, then compare; never select/train.

Uses the existing failure-stopping manager unchanged. An error or ambiguous
comparison intent stops the runner. No job retries or reserved evaluation.
"""
import argparse
from datetime import datetime, timezone
import os
from pathlib import Path
import time

import manage_current_auction_failed_bucket_v3 as manager
import current_auction_attempt_comparison_v4 as comparison

ROOT = manager.ROOT
OUT = ROOT/'ai/runs/current-auction-confirmation-finisher-v1'
MANAGER_SHA = '36a472a7815fa2095271beae2f4100102e170b768fbfa1bb8f80b81cba493584'


def queue_complete(state):
    batches = state['batches']
    return (state['active'] == 0 and set(batches) == {'failed_recovery', 'untouched'}
        and all(batches[name]['unsubmitted'] == 0
                and batches[name]['verified_jobs'] == batches[name]['submitted'] == count
                for name, count in (('failed_recovery', 10), ('untouched', 258))))


def finish(cycle, compare, publish, stopped, *, sleep=time.sleep, clock=time.monotonic,
           max_cycles=144, max_seconds=24*3600):
    started = clock()
    for number in range(1, max_cycles+1):
        if stopped() or clock()-started >= max_seconds:
            publish({'stage': 'stopped', 'cycles_completed': number-1}); return
        state = cycle(execute=True, launch_limit=64, collect_limit=8)
        publish({'stage': 'collecting_confirmation', 'cycles_completed': number, 'queue': state})
        if stopped():
            publish({'stage': 'stopped', 'cycles_completed': number}); return
        if queue_complete(state):
            publish({'stage': 'comparing_complete_confirmation', 'cycles_completed': number})
            result = compare()
            publish({'stage': 'complete', 'cycles_completed': number, 'comparison': result}); return
        sleep(60)
    publish({'stage': 'cycle_limit_reached', 'cycles_completed': max_cycles})


def main():
    parser=argparse.ArgumentParser(__doc__)
    parser.add_argument('--execute', action='store_true'); args=parser.parse_args()
    if not args.execute:
        print('Use --execute to finish the existing fixed queue and comparison only.'); return
    manager.require(not OUT.exists(), 'Inspect prior runner state; do not start another owner')
    manager.require(manager.digest(manager.__file__)==MANAGER_SHA, 'Frozen manager changed')
    manager.require(not (manager.OUT/'STOP.json').exists(), 'Resolve the recorded collection stop first')
    manager.require(not comparison.OUTPUT.exists() and not comparison.OUTPUT.with_suffix('.intent.json').exists(),
                    'Inspect prior comparison outcome before starting')
    OUT.mkdir()
    pins={str(p.relative_to(ROOT)):manager.digest(p) for p in
          (Path(__file__), Path(manager.__file__), Path(comparison.__file__), Path(comparison.auth.__file__))}
    base={'pid':os.getpid(), 'started_at':datetime.now(timezone.utc).isoformat(), 'input_hashes':pins,
          'scope':'Existing fixed confirmation queue and analysis only', 'new_experiments':0,
          'automatic_job_retries':False, 'candidate_selected':False, 'qualified':False,
          'reserved_final_seeds_used':False}
    manager.save(OUT/'intent.json',base)
    def publish(update):
        manager.require(all(manager.digest(ROOT/p)==sha for p,sha in pins.items()), 'Runner inputs changed')
        state={**base, **update, 'updated_at':manager.now()}
        manager.durable(OUT/'state.json',state)
        print(state['updated_at'],state['stage'],flush=True)
    publish({'stage':'starting'})
    try:
        with manager.exclusive(OUT,'owner'):
            finish(manager.cycle,comparison.compare,publish,lambda:(OUT/'STOP').exists())
    except BaseException as error:
        manager.durable(OUT/'state.json',{**base, 'stage':'failed', 'updated_at':manager.now(),
            'error_type':type(error).__name__, 'requires_inspection':True})
        raise


if __name__=='__main__':main()
