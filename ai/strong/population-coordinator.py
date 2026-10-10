"""Durable HF execution of the frozen population checkpoint/screen protocol.

No training changes, arbitrary checkpoint selection, retries of ambiguous job
launches, relaxed export tolerances, or final qualification happen here.
"""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

import torch
from huggingface_hub import HfApi, hf_hub_download, snapshot_download
from huggingface_hub.errors import EntryNotFoundError

ROOT = Path(__file__).resolve().parents[2]
REPO = 'coyotte508/powergrid-ai-germany-v1'
DONE = {'collected', 'validation_failed', 'screen_failed', 'launch_unknown'}
LIVE = {'CREATED', 'SCHEDULING', 'STARTING', 'RUNNING', 'PENDING', 'QUEUED'}


def now():
    return datetime.now(timezone.utc).isoformat()


def matching_checkpoint_update(metrics, checkpoint_update, scheduled=(9, 19)):
    updates = [r['update'] for r in metrics if r.get('stage') == 'train']
    if not updates or updates[-1] not in scheduled:
        return None
    # save(best) can temporarily upload new metrics with the previous latest.pt.
    if updates != list(range(updates[-1] + 1)) or checkpoint_update != updates[-1]:
        return None
    return checkpoint_update


class Coordinator:
    def __init__(self):
        self.api = HfApi()
        self.config = json.loads((ROOT / 'ai/strong/population-coordinator-config-v1.json').read_text())
        self.protocol = json.loads((ROOT / 'ai/strong/population-training-protocol-v1.json').read_text())
        self.root = ROOT / 'ai/runs/population-coordinator-v1'
        self.root.mkdir(parents=True, exist_ok=True)
        self.prefix = self.config['output_prefix']
        # Recover a terminated coordinator's evidence before considering any launch.
        try:
            revision = self.api.model_info(REPO).sha
            hf_hub_download(REPO, self.prefix + '/state.json', revision=revision)
            recovered = Path(snapshot_download(REPO, revision=revision,
                allow_patterns=[self.prefix + '/*'])) / self.prefix
            shutil.copytree(recovered, self.root, dirs_exist_ok=True)
        except EntryNotFoundError:
            pass
        state = self.root / 'state.json'
        self.state = json.loads(state.read_text()) if state.exists() else {
            'protocol_sha256': hashlib.sha256((ROOT / 'ai/strong/population-training-protocol-v1.json').read_bytes()).hexdigest(),
            'started_at': now(), 'checkpoints': {}, 'comparisons': {}, 'training_jobs': self.config['training_jobs'],
            'qualification_eligible': False, 'events': []}
        if (self.state['training_jobs'] != self.config['training_jobs'] or
            self.state['protocol_sha256'] != hashlib.sha256((ROOT / 'ai/strong/population-training-protocol-v1.json').read_bytes()).hexdigest()):
            raise ValueError('Recovered coordinator belongs to a different frozen experiment')
        self.parent = ROOT / self.config['parent_path']
        self.fixtures = ROOT / self.config['fixture_path']
        if hashlib.sha256(self.fixtures.read_bytes()).hexdigest() != self.config['fixture_sha256']:
            raise ValueError('Full serving fixture hash mismatch')
        self.checked = {arm: set() for arm in self.config['training_jobs']}

    def persist(self, event):
        self.state['updated_at'] = now()
        self.state['events'].append({'time': now(), **event})
        file = self.root / 'state.json'
        tmp = file.with_suffix('.tmp')
        tmp.write_text(json.dumps(self.state, indent=2) + '\n')
        tmp.replace(file)
        self.api.upload_folder(repo_id=REPO, folder_path=self.root,
            path_in_repo=self.prefix, ignore_patterns=['*.pt', '*.onnx', '*.tmp'])
        print(json.dumps(event), flush=True)

    def command(self, argv, log, env=None):
        result = subprocess.run(argv, cwd=ROOT, env=env, capture_output=True, text=True)
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text(result.stdout + result.stderr)
        if result.returncode:
            raise RuntimeError(f'{argv[1]} failed (exit {result.returncode}); see {log.name}')
        return result.stdout

    def consider_revision(self, arm, revision):
        if revision in self.checked[arm]:
            return None
        run = self.protocol['arms'][arm]['run']
        try:
            metrics = json.loads(Path(hf_hub_download(REPO, f'runs/{run}/metrics.json', revision=revision)).read_text())
            updates = [x['update'] for x in metrics if x.get('stage') == 'train']
            latest = updates[-1] if updates else -1
            key = f'{arm}-u{latest}'
            if latest not in self.protocol['checkpoint_updates'] or key in self.state['checkpoints']:
                self.checked[arm].add(revision)
                return latest
            file = hf_hub_download(REPO, f'runs/{run}/latest.pt', revision=revision)
            checkpoint = torch.load(file, map_location='cpu', weights_only=True)
            update = matching_checkpoint_update(metrics, checkpoint.get('update'))
        except EntryNotFoundError:
            self.checked[arm].add(revision)
            return None
        self.checked[arm].add(revision)
        if update is None:
            return latest
        key = f'{arm}-u{update}'
        self.state['checkpoints'][key] = {'arm': arm, 'update': update,
            'revision': revision, 'phase': 'selected', 'screens': {}}
        self.persist({'stage': 'checkpoint_selected', 'key': key, 'revision': revision})
        return latest

    def advance_checkpoint(self, key):
        entry = self.state['checkpoints'][key]
        directory = self.root / key
        if entry['phase'] == 'selected':
            try:
                self.command([sys.executable, 'ai/strong/prepare-population-screen.py',
                    entry['arm'], str(entry['update']), entry['revision'], str(directory),
                    '--fixtures', str(self.fixtures)], directory / 'prepare.log')
            except RuntimeError as error:
                entry.update(phase='validation_failed', error=str(error))
                self.persist({'stage': 'validation_failed', 'key': key, 'error': str(error)})
                return
            entry['phase'] = 'validated'
            self.persist({'stage': 'checkpoint_validated', 'key': key})
        if entry['phase'] == 'validated':
            for plan in json.loads((directory / 'screen-plan.json').read_text()):
                name = plan['run']
                if name in entry['screens']:
                    if 'job_id' in entry['screens'][name]:
                        continue
                    # A previous POST may have succeeded. Never retry it blind.
                    entry.update(phase='launch_unknown', error=f'Unresolved launch: {name}')
                    self.persist({'stage': 'launch_unknown', 'key': key, 'run': name})
                    return
                entry['screens'][name] = {'phase': 'launching', 'time': now()}
                self.persist({'stage': 'launch_intent', 'key': key, 'run': name})
                try:
                    stdout = self.command(plan['argv'], directory / (name + '.launch.log'),
                        {**os.environ, **plan['env']})
                    ids = set(re.findall(r'\b[0-9a-f]{24}\b', stdout))
                    if len(ids) != 1:
                        raise RuntimeError('Ambiguous job launch response')
                    entry['screens'][name] = {'job_id': ids.pop(), 'phase': 'launched', 'time': now()}
                except RuntimeError as error:
                    entry.update(phase='launch_unknown', error=str(error))
                    self.persist({'stage': 'launch_unknown', 'key': key, 'run': name, 'error': str(error)})
                    return
                self.persist({'stage': 'screen_launched', 'key': key, 'run': name,
                    'job_id': entry['screens'][name]['job_id']})
            entry['phase'] = 'evaluating'
            self.persist({'stage': 'screens_running', 'key': key})
        if entry['phase'] == 'evaluating':
            complete = True
            active = False
            failures = []
            for screen in entry['screens'].values():
                status = self.api.inspect_job(job_id=screen['job_id']).status.stage
                screen['observed_stage'] = status
                if status != 'COMPLETED':
                    complete = False
                    if status in LIVE:
                        active = True
                    else:
                        failures.append(f'{screen["job_id"]}: {status}')
            if failures and not active:
                entry.update(phase='screen_failed', error='; '.join(failures))
                self.persist({'stage': 'screen_failed', 'key': key, 'error': entry['error']})
                return
            if complete:
                revision = self.api.model_info(REPO).sha
                try:
                    self.command([sys.executable, 'ai/strong/collect-population-screen.py',
                        str(directory), revision], directory / 'collect.log')
                except RuntimeError as error:
                    entry.update(phase='screen_failed', error=str(error))
                    self.persist({'stage': 'collection_failed', 'key': key, 'error': str(error)})
                    return
                entry.update(phase='collected', result_revision=revision)
                self.persist({'stage': 'screen_collected', 'key': key, 'result_revision': revision})

    def compare_ready(self):
        for update in self.protocol['checkpoint_updates']:
            if str(update) in self.state['comparisons']:
                continue
            keys = [f'{arm}-u{update}' for arm in self.protocol['arms']]
            if not all(self.state['checkpoints'].get(key, {}).get('phase') == 'collected' for key in keys):
                continue
            argv = [sys.executable, 'ai/strong/compare-population-screens.py',
                '--parent', str(self.parent), '--update', str(update),
                '--output', str(self.root / f'comparison-u{update}.json')]
            for arm in self.protocol['arms']:
                argv += ['--' + arm, str(self.root / f'{arm}-u{update}')]
            self.command(argv, self.root / f'comparison-u{update}.log')
            self.state['comparisons'][str(update)] = f'comparison-u{update}.json'
            self.persist({'stage': 'comparison_ready', 'update': update})

    def cycle(self):
        revision = self.api.model_info(REPO).sha
        statuses = {}
        for arm, job in self.config['training_jobs'].items():
            statuses[arm] = self.api.inspect_job(job_id=job).status.stage
            latest = self.consider_revision(arm, revision)
            pending = [u for u in self.protocol['checkpoint_updates'] if f'{arm}-u{u}' not in self.state['checkpoints']]
            # Recover a scheduled checkpoint missed while offline, including from
            # a best-upload commit whose old latest.pt cannot match its metrics.
            if pending and ((latest is not None and latest > min(pending)) or statuses[arm] not in LIVE):
                earliest = datetime.fromisoformat(self.config['earliest_commit'])
                for commit in self.api.list_repo_commits(REPO):
                    if commit.created_at < earliest:
                        break
                    self.consider_revision(arm, commit.commit_id)
                    if all(f'{arm}-u{u}' in self.state['checkpoints'] for u in self.protocol['checkpoint_updates']):
                        break
        self.state['training_stages'] = statuses
        for key in list(self.state['checkpoints']):
            self.advance_checkpoint(key)
        self.compare_ready()
        required = {f'{arm}-u{u}' for arm in self.protocol['arms'] for u in self.protocol['checkpoint_updates']}
        all_terminal = all(v not in LIVE for v in statuses.values())
        finished = required <= self.state['checkpoints'].keys() and all(
            self.state['checkpoints'][key]['phase'] in DONE for key in required)
        if all_terminal and not required <= self.state['checkpoints'].keys():
            missing = sorted(required - self.state['checkpoints'].keys())
            if self.state.get('missing_checkpoints') != missing:
                self.state['missing_checkpoints'] = missing
                self.persist({'stage': 'missing_checkpoints', 'keys': missing})
            # Finish observing screens already launched even if a trainer failed
            # before producing all its scheduled checkpoints.
            finished = all(e['phase'] in DONE for e in self.state['checkpoints'].values())
        if finished:
            success = (required <= self.state['checkpoints'].keys()
                and all(self.state['checkpoints'][k]['phase'] == 'collected' for k in required)
                and set(self.state['comparisons']) == {str(u) for u in self.protocol['checkpoint_updates']})
            self.state['outcome'] = 'completed' if success else 'needs_attention'
            self.persist({'stage': 'coordinator_finished', 'outcome': self.state['outcome'],
                'comparisons': self.state['comparisons']})
            return True
        observation = {'training': statuses,
            'screens': {k: {n: s.get('observed_stage', s.get('phase')) for n, s in e.get('screens', {}).items()}
                for k, e in self.state['checkpoints'].items()}}
        if observation != self.state.get('last_observation'):
            self.state['last_observation'] = observation
            self.persist({'stage': 'observation_changed'})
        print(json.dumps({'stage': 'waiting', 'training': statuses,
            'checkpoints': {k: v['phase'] for k, v in self.state['checkpoints'].items()}}), flush=True)
        return False

    def run(self):
        started = time.monotonic()
        self.persist({'stage': 'coordinator_started'})
        while time.monotonic() - started < self.config['max_hours'] * 3600:
            try:
                if self.cycle():
                    return 0 if self.state['outcome'] == 'completed' else 1
            except Exception as error:
                # Read failures do not imply termination and never justify a new
                # job. In-memory launch intents are retained for safe recovery.
                print(json.dumps({'stage': 'observation_error', 'type': type(error).__name__,
                    'message': str(error)[:500]}), flush=True)
            time.sleep(self.config['poll_seconds'])
        self.persist({'stage': 'coordinator_timeout'})
        return 2


if __name__ == '__main__':
    sys.exit(Coordinator().run())
