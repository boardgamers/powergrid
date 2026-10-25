"""One-shot progression from complete opponent data to audited HF training.

Owns at most one calibration and one full four-seed training job. No automatic
retries, local gradients, test-split selection or continuation/strength jobs.
"""
import argparse
from datetime import datetime, timezone
import fcntl
import importlib.util
import os
from pathlib import Path
import re
import subprocess
import sys
import time

from huggingface_hub import HfApi
from strategic_collection import ROOT, read, write, digest
from opponent_surrogate_hf_v1 import SOURCE_FILES

STRONG = ROOT/'ai/strong'
ACTIONS = ('prepare_data', 'archive_data', 'package_source', 'launch_calibration',
           'collect_calibration', 'launch_full', 'collect_full', 'select_validation')
FAILURES = {'ERROR', 'FAILED', 'CANCELED', 'CANCELLED', 'DELETED', 'TIMEOUT'}


def now(): return datetime.now(timezone.utc).isoformat()


def paths(home=ROOT):
    home = Path(home); runs = home/'ai/runs'; strong = home/'ai/strong'
    return {'home': home, 'out': runs/'opponent-surrogate-training-coordinator-v1',
            'collection': strong/'opponent-surrogate-collection-results-v1.json',
            'data': runs/'opponent-surrogate-training-data-v1',
            'data_archive': runs/'opponent-surrogate-training-data-archive-v1',
            'data_pin': strong/'opponent-surrogate-training-data-v1.json',
            'package': runs/'opponent-surrogate-training-source-v1',
            'source': strong/'opponent-surrogate-training-source-v1.json',
            'guards': runs/'opponent-surrogate-training-launches-v1',
            'calibration': runs/'opponent-surrogate-training-runtime-collected-v1',
            'collected': runs/'opponent-surrogate-training-full-collected-v1',
            'training_result': strong/'opponent-surrogate-training-results-v1.json',
            'selection': runs/'opponent-surrogate-selection-v1'}


def code_hashes():
    spec = importlib.util.spec_from_file_location('training_coordinator_prepare', STRONG/'prepare-opponent-surrogate-training-v1.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    names = set(SOURCE_FILES) | {f'ai/strong/{name}' for name in (
        Path(__file__).name, 'prepare-opponent-surrogate-training-v1.py',
        'package-opponent-surrogate-training-v1.py', 'launch-opponent-surrogate-training-v1.py',
        'collect-opponent-surrogate-training-v1.py', 'opponent_surrogate_training_verification_v1.py',
        'select-opponent-surrogate-v1.py', 'opponent-surrogate-selection-design-v1.json',
        'opponent_surrogate_policy_v1.py')}
    return {**module.manager.code_hashes(), **{name: digest(ROOT/name) for name in sorted(names)}}


def artifact(action, p):
    return {'prepare_data': p['data']/'data-check.json', 'archive_data': p['data_pin'],
            'package_source': p['source'], 'launch_calibration': p['guards']/'calibration.json',
            'collect_calibration': p['calibration']/'verified.json', 'launch_full': p['guards']/'full.json',
            'collect_full': p['training_result'], 'select_validation': p['selection']/'frozen.json'}[action]


def command(action, p):
    arguments = {
        'prepare_data': ['prepare-opponent-surrogate-training-v1.py', str(p['data'])],
        'archive_data': ['package-opponent-surrogate-training-v1.py', 'archive-data'],
        'package_source': ['package-opponent-surrogate-training-v1.py', 'source', str(p['package'])],
        'launch_calibration': ['launch-opponent-surrogate-training-v1.py', 'calibration', '--execute'],
        'collect_calibration': ['launch-opponent-surrogate-training-v1.py', 'collect-calibration'],
        'launch_full': ['launch-opponent-surrogate-training-v1.py', 'full', '--execute'],
        'collect_full': ['collect-opponent-surrogate-training-v1.py'],
        'select_validation': ['select-opponent-surrogate-v1.py']}[action]
    return [sys.executable, '-u', '-B', 'ai/strong/'+arguments[0], *arguments[1:]]


def execute_command(argv, logfile, home):
    with Path(logfile).open('x') as log:
        subprocess.run(argv, cwd=home, stdout=log, stderr=subprocess.STDOUT, check=True,
                       env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1', 'HF_HUB_DISABLE_PROGRESS_BARS': '1'})


def initial_state(p):
    # This coordinator is a new owner, not a recovery shortcut for unknown work.
    for name in ('data', 'data_archive', 'package', 'data_pin', 'source', 'guards', 'calibration',
                 'collected', 'training_result', 'selection'):
        assert not p[name].exists(), f'Existing {name}: inspect its original owner/receipt before coordinating'
    for name in ('data_archive', 'package'):
        assert not p[name].with_suffix('.tgz').exists(), 'Existing upload evidence must be reconciled'
    return {'pid': os.getpid(), 'started_at': now(), 'updated_at': now(), 'stage': 'waiting_for_complete_collection',
            'code_hashes': code_hashes(), 'completed_actions': {}, 'running_action': None,
            'jobs': {}, 'automatic_retries': False, 'remote_cancellations_allowed': False,
            'gradient_location': 'HF Jobs only', 'maximum_new_jobs': 2,
            'test_labels_used_for_selection': False, 'qualification_eligible': False, 'reserved_final_seeds_used': False}


class Coordinator:
    def __init__(self, p, state, runner=execute_command, inspector=None):
        self.p = p; self.state = state; self.runner = runner
        self.inspector = inspector or (lambda job_id: HfApi().inspect_job(job_id=job_id).status.stage)

    def save(self, **updates):
        self.state.update(updates, updated_at=now())
        temp = self.p['out']/'state.tmp.json'; write(temp, self.state); temp.replace(self.p['out']/'state.json')

    def tick(self):
        assert self.state['code_hashes'] == code_hashes(), 'Pinned training/collection code changed; stop before another action'
        assert self.state['running_action'] is None, 'Interrupted/failed action: reconcile original outcome, never auto-retry'
        done = self.state['completed_actions']
        assert list(done) == list(ACTIONS[:len(done)])
        for action, receipt in done.items():
            assert digest(artifact(action, self.p)) == receipt['sha256'], 'Completed evidence changed'
        if len(done) == len(ACTIONS):
            frozen = read(self.p['selection']/'frozen.json')
            assert frozen['complete'] and frozen['test_labels_used'] is False
            self.save(stage='complete', selected=frozen['selection'], learned_surrogate_selected=frozen['learned_surrogate_selected'])
            return True
        action = ACTIONS[len(done)]
        if action == 'prepare_data':
            if not self.p['collection'].exists():
                self.save(stage='waiting_for_complete_collection'); return False
            index = read(self.p['collection'])
            assert index['complete'] and index['games'] == 2560 and index['twins'] == 640
            assert len(index['cases']) == 40 and index['split_games'] == {'train': 1920, 'validation': 320, 'test': 320}
            self.state['collection_index_sha256'] = digest(self.p['collection'])
        if action in ('collect_calibration', 'collect_full'):
            mode = 'calibration' if action == 'collect_calibration' else 'full'
            guard = read(self.p['guards']/(mode+'.json'))
            assert guard['stage'] == 'launched' and guard['mode'] == mode and re.fullmatch('[a-f0-9]{24}', guard['job_id'])
            try: stage = self.inspector(guard['job_id'])
            except Exception as error:
                # An observation error does not replace or rerun the original job.
                self.save(stage='waiting_for_job_observation', observation_error_type=type(error).__name__)
                return False
            self.state['jobs'][mode] = {'job_id': guard['job_id'], 'authoritative_status': stage, 'checked_at': now()}
            assert stage not in FAILURES, f'Original {mode} job ended {stage}; preserve evidence and inspect it'
            if stage != 'COMPLETED':
                self.save(stage='waiting_for_'+mode); return False
        output = artifact(action, self.p)
        assert not output.exists(), 'Another owner created this output; reconcile rather than repeating work'
        argv = command(action, self.p); logfile = self.p['out']/(action+'.log')
        self.save(stage='executing', running_action=action, current_command=argv)
        print({'action': action, 'stage': 'starting'}, flush=True)
        try:
            self.runner(argv, logfile, self.p['home'])
            assert self.state['code_hashes'] == code_hashes()
            assert output.is_file(), f'{action} did not produce its required verified evidence'
            if action.startswith('launch_'):
                guard = read(output)
                assert guard['stage'] == 'launched' and re.fullmatch('[a-f0-9]{24}', guard['job_id'])
            done[action] = {'path': str(output.relative_to(self.p['home'])), 'sha256': digest(output), 'finished_at': now()}
            self.save(stage='ready', running_action=None)
        except BaseException as error:
            self.save(stage='action_failed', failure_type=type(error).__name__)
            raise
        print({'action': action, 'stage': 'complete'}, flush=True)
        return False


def main(execute=False, interval_seconds=180, max_hours=48):
    assert 10 <= interval_seconds <= 3600 and 0 < max_hours <= 72
    p = paths(); hashes = code_hashes()
    if not execute:
        # Read-only. Do not create files or instantiate a network client.
        print({'execute': False, 'actions': list(ACTIONS), 'pinned_code_files': len(hashes),
               'complete_collection_required': True, 'gradients': 'HF Jobs only', 'maximum_new_jobs': 2,
               'full_training_requires_measured_calibration': True, 'automatic_retries': False})
        return
    p['out'].mkdir(parents=True, exist_ok=True)
    with (p['out']/'.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        assert not (p['out']/'state.json').exists(), 'Inspect the original coordinator instead of replacing it'
        state = initial_state(p); assert hashes == state['code_hashes']
        controller = Coordinator(p, state); controller.save()
        deadline = time.monotonic()+max_hours*3600
        try:
            while time.monotonic() < deadline:
                before = len(state['completed_actions'])
                if controller.tick():
                    print({'stage': 'complete', 'selected': state['selected'], 'learned_surrogate_selected': state['learned_surrogate_selected']}, flush=True)
                    return
                if len(state['completed_actions']) == before:
                    print({'stage': state['stage'], 'completed_actions': before, 'jobs': state['jobs']}, flush=True)
                    time.sleep(interval_seconds)
            controller.save(stage='observation_deadline_reached')
        except BaseException as error:
            controller.save(stage='stopped_for_inspection', failure_type=type(error).__name__)
            raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__); parser.add_argument('--execute', action='store_true')
    parser.add_argument('--interval-seconds', type=int, default=180); parser.add_argument('--max-hours', type=float, default=48)
    args = parser.parse_args(); main(args.execute, args.interval_seconds, args.max_hours)
