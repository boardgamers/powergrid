"""One owner for the already admitted complete paired continuation study.

Does not prepare training, choose models, change roots or retry uncertain work.
Stop this local process first if the user requests no further study submissions.
"""
import argparse
from datetime import datetime, timezone
import fcntl
import importlib.util
import os
from pathlib import Path
import time

from strategic_collection import ROOT, read, write, digest

STRONG = ROOT/'ai/strong'
spec = importlib.util.spec_from_file_location('study_coordinator_manager', STRONG/'manage-surrogate-continuation-study-v1.py')
manager = importlib.util.module_from_spec(spec); spec.loader.exec_module(manager)
launcher = manager.launcher
OUT = ROOT/'ai/runs/surrogate-continuation-study-coordinator-v1'
PROOF = ROOT/'ai/runs/surrogate-continuation-study-coordinator-preflight-v1.json'


def dependencies():
    return {**manager.dependencies(), str(Path(__file__).relative_to(ROOT)): digest(__file__)}


def now(): return datetime.now(timezone.utc).isoformat()


def initial_state(plan):
    assert plan['jobs'] == 480 and plan['continuations'] == 23040
    assert not list(launcher.GUARDS.glob('*.json')), 'Existing submissions have an original owner; inspect it before coordinating'
    assert not manager.INDEX.exists() and not manager.ANALYSIS.exists()
    return {'pid': os.getpid(), 'started_at': now(), 'stage': 'ready', 'running_operation': None,
            'plan_sha256': digest(launcher.PLAN), 'code_hashes': dependencies(),
            'jobs_planned': 480, 'continuations_planned': 23040, 'jobs_submitted': 0, 'jobs_verified': 0,
            'caps': 0, 'failed_jobs': [], 'automatic_retries': False, 'remote_cancellations_allowed': False,
            'gradients': False, 'qualification_eligible': False, 'reserved_final_seeds_used': False}


class Coordinator:
    def __init__(self, state, out=OUT): self.state, self.out = state, Path(out)

    def save(self, **updates):
        self.state.update(updates, updated_at=now())
        temporary = self.out/'state.tmp.json'; write(temporary, self.state); temporary.replace(self.out/'state.json')

    def operation(self, name, function):
        assert self.state['running_operation'] is None, 'Reconcile the original operation before another attempt'
        self.save(stage=name, running_operation=name)
        try:
            result = function()
            assert dependencies() == self.state['code_hashes'] and digest(launcher.PLAN) == self.state['plan_sha256']
            self.save(running_operation=None)
            return result
        except BaseException as error:
            self.save(stage='stopped_for_inspection', failure_type=type(error).__name__)
            raise

    def tick(self):
        assert self.state['running_operation'] is None, 'Interrupted operation: inspect the same original handles, never replace them'
        assert dependencies() == self.state['code_hashes'], 'Pinned study management changed'
        assert digest(launcher.PLAN) == self.state['plan_sha256'], 'Fixed study admission changed'
        result = self.operation('collecting', manager.collect_ready)
        assert 0 <= result['jobs_verified'] <= result['jobs_submitted'] <= self.state['jobs_planned']
        self.save(jobs_submitted=result['jobs_submitted'], jobs_verified=result['jobs_verified'],
                  caps=result['caps'], failed_jobs=result['failed_jobs'])
        assert not result['failed_jobs'], 'Inspect original failed jobs; preserve partial evidence and never auto-replace'
        if result['jobs_verified'] == self.state['jobs_planned']:
            index = self.operation('indexing', manager.index)
            assert index['all_jobs_verified'] and index['jobs'] == 480 and index['continuations'] == 23040
            assert index['caps'] == result['caps'] and index['complete'] is (result['caps'] == 0)
            self.save(stage='complete' if index['complete'] else 'complete_with_caps',
                      index_sha256=digest(manager.INDEX), comparison_sha256=digest(manager.ANALYSIS))
            return True
        launched = self.operation('submitting', lambda: launcher.launch_ready(True))
        assert result['jobs_submitted'] <= launched['original_jobs'] <= self.state['jobs_planned']
        self.save(stage='waiting_for_original_jobs', jobs_submitted=launched['original_jobs'])
        return False


def main(execute=False, interval_seconds=180, max_hours=48):
    assert 60 <= interval_seconds <= 3600 and 0 < max_hours <= 72
    plan, _, _ = launcher.admission()  # Actual training selection and HF timing are mandatory.
    if not execute:
        print({'execute': False, 'jobs': plan['jobs'], 'continuations': plan['continuations'],
               'max_concurrent': plan['admission']['max_concurrent'], 'automatic_retries': False}); return
    proof = read(PROOF)
    assert proof['complete'] and proof['code_hashes'] == dependencies() and proof['tests'] >= 8
    assert proof['new_hf_jobs'] == proof['fresh_scientific_continuations'] == 0
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT/'.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        assert not (OUT/'state.json').exists(), 'Inspect the original coordinator instead of replacing it'
        state = initial_state(plan); controller = Coordinator(state, OUT); controller.save()
        deadline = time.monotonic()+max_hours*3600
        try:
            while time.monotonic() < deadline:
                complete = controller.tick()
                print({k: state[k] for k in ('stage', 'jobs_submitted', 'jobs_verified', 'caps')}, flush=True)
                if complete: return
                time.sleep(min(interval_seconds, max(0, deadline-time.monotonic())))
            controller.save(stage='observation_window_ended')
        except BaseException as error:
            controller.save(stage='stopped_for_inspection', failure_type=type(error).__name__); raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__); parser.add_argument('--execute', action='store_true')
    parser.add_argument('--interval-seconds', type=int, default=180); parser.add_argument('--max-hours', type=float, default=48)
    args = parser.parse_args(); main(args.execute, args.interval_seconds, args.max_hours)
