"""Observe the four fixed trainers, evaluate final checkpoints once, compare both seeds."""
import json
from pathlib import Path
import sys

from huggingface_hub import HfApi, hf_hub_download
from huggingface_hub.errors import EntryNotFoundError
from five_plant_screen import ROOT, REPO, read, digest, prepare, load_module

base = load_module('population_execution', 'population-coordinator.py')
TERMINAL = {'COMPLETED', 'CANCELED', 'ERROR', 'DELETED'}
DONE = {'collected', 'training_failed', 'validation_failed', 'launch_unknown', 'screen_failed', 'collection_failed'}


class Coordinator(base.Coordinator):
    # Keep the tested durable persistence, subprocess capture and bounded observation loop.
    def __init__(self):
        self.api = HfApi()
        self.config = read(ROOT / 'ai/strong/five-plant-coordinator-config-v1.json')
        self.protocol = read(ROOT / 'ai/strong/five-plant-ablation-protocol-v1.json')
        assert set(self.config['training_jobs']) == set(self.protocol['runs'])
        self.root = ROOT / 'ai/runs/five-plant-coordinator-v1'
        self.root.mkdir(parents=True, exist_ok=True)
        self.prefix = self.config['output_prefix']
        identity = {'training_jobs': self.config['training_jobs'], 'parent_job': self.config['parent_job'],
                    'protocol_sha256': digest(ROOT / 'ai/strong/five-plant-ablation-protocol-v1.json'),
                    'config_sha256': digest(ROOT / 'ai/strong/five-plant-coordinator-config-v1.json')}
        try:
            revision = self.api.model_info(REPO).sha
            self.state = read(hf_hub_download(REPO, self.prefix + '/state.json', revision=revision))
        except EntryNotFoundError:
            self.state = {**identity, 'started_at': base.now(), 'qualification_eligible': False,
                'events': [], 'entries': {'parent': {'phase': 'evaluating', 'job_id': self.config['parent_job']},
                    **{k: {'phase': 'waiting_training'} for k in self.config['training_jobs']}}}
        if any(self.state.get(k) != v for k, v in identity.items()):
            raise ValueError('Recovered state belongs to another frozen experiment')

    def advance(self, key):
        entry = self.state['entries'][key]
        if entry['phase'] in DONE:
            return
        directory = self.root / key
        if entry['phase'] == 'waiting_training':
            stage = self.api.inspect_job(job_id=self.config['training_jobs'][key]).status.stage
            entry['training_stage'] = stage
            if stage not in TERMINAL:
                return
            if stage != 'COMPLETED':
                entry.update(phase='training_failed', error=stage)
                self.persist({'stage': 'training_failed', 'key': key, 'status': stage})
                return
            # The final wrapper uploads its complete report only after update19.
            # Never discover intermediate checkpoints or choose internal best.
            revision = self.api.model_info(REPO).sha
            try:
                prepare(key, revision, directory, self.protocol)
            except (ValueError, AssertionError) as error:
                entry.update(phase='validation_failed', revision=revision, error=str(error))
                self.persist({'stage': 'validation_failed', 'key': key, 'error': str(error)})
                return
            entry.update(phase='validated', revision=revision)
            self.persist({'stage': 'final_checkpoint_validated', 'key': key, 'revision': revision})
        if entry['phase'] == 'validated':
            # Persist intent before a POST. If this upload fails, retain intent in
            # memory and refuse blind submission on the following cycle.
            entry['phase'] = 'launching'
            self.persist({'stage': 'launch_intent', 'key': key, 'revision': entry['revision']})
            try:
                stdout = self.command([sys.executable, 'ai/strong/launch-five-plant-screen.py',
                    key, entry['revision']], directory / 'launch.log')
                launched = json.loads(stdout)
                assert launched['key'] == key and launched['model_revision'] == entry['revision']
                assert launched['stage'] == 'launched' and len(launched['job_id']) == 24
                entry.update(phase='evaluating', job_id=launched['job_id'])
            except Exception as error:
                entry.update(phase='launch_unknown', error=str(error))
                self.persist({'stage': 'launch_unknown', 'key': key, 'error': str(error)})
                return
            self.persist({'stage': 'screen_launched', 'key': key, 'job_id': entry['job_id']})
        elif entry['phase'] == 'launching':
            entry.update(phase='launch_unknown', error='Recovered an unresolved launch intent; reconcile before any retry')
            self.persist({'stage': 'launch_unknown', 'key': key})
            return
        if entry['phase'] == 'evaluating':
            stage = self.api.inspect_job(job_id=entry['job_id']).status.stage
            entry['screen_stage'] = stage
            if stage not in TERMINAL:
                return
            if stage != 'COMPLETED':
                entry.update(phase='screen_failed', error=stage)
                self.persist({'stage': 'screen_failed', 'key': key, 'status': stage})
                return
            revision = self.api.model_info(REPO).sha
            try:
                self.collect(key, revision)
            except RuntimeError as error:
                entry.update(phase='collection_failed', result_revision=revision, error=str(error))
                self.persist({'stage': 'collection_failed', 'key': key, 'error': str(error)})
                return
            entry.update(phase='collected', result_revision=revision)
            self.persist({'stage': 'screen_collected', 'key': key, 'result_revision': revision})

    def collect(self, key, revision):
        self.command([sys.executable, 'ai/strong/collect-five-plant-screen.py', key,
                      revision, str(self.root / key)], self.root / key / 'collection.log')

    def cycle(self):
        for key in self.state['entries']:
            try:
                self.advance(key)
            except Exception as error:
                # An observation failure leaves its existing handle/intent intact
                # and does not prevent observing the other independent runs.
                print(json.dumps({'stage': 'observation_error', 'key': key,
                                  'type': type(error).__name__, 'message': str(error)[:500]}), flush=True)
        phases = {k: v['phase'] for k, v in self.state['entries'].items()}
        if all(v == 'collected' for v in phases.values()) and not self.state.get('comparison'):
            # Recovery only needs state.json. Rehydrate exact pinned artifacts
            # before comparison; collection never starts a game or a job.
            for key, entry in self.state['entries'].items():
                self.collect(key, entry['result_revision'])
            self.command([sys.executable, 'ai/strong/compare-five-plant-screens.py', str(self.root),
                          '--output', str(self.root / 'comparison.json')], self.root / 'comparison.log')
            self.state['comparison'] = 'comparison.json'
            self.persist({'stage': 'comparison_ready'})
        if all(v in DONE for v in phases.values()):
            success = all(v == 'collected' for v in phases.values()) and bool(self.state.get('comparison'))
            self.state['outcome'] = 'completed' if success else 'needs_attention'
            self.persist({'stage': 'coordinator_finished', 'outcome': self.state['outcome']})
            return True
        observed = {k: {f: v.get(f) for f in ['phase', 'training_stage', 'screen_stage', 'job_id']}
                    for k, v in self.state['entries'].items()}
        if observed != self.state.get('last_observation'):
            self.state['last_observation'] = observed
            self.persist({'stage': 'observation_changed'})
        print(json.dumps({'stage': 'waiting', 'phases': phases}), flush=True)
        return False


if __name__ == '__main__':
    sys.exit(Coordinator().run())
