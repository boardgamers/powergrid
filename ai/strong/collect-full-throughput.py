"""Verify completed CPU/H200 probes and compare the prescribed full updates."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import shutil

from huggingface_hub import HfApi, hf_hub_download
import torch

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('throughput', Path(__file__).with_name('benchmark-full-training.py'))
benchmark = importlib.util.module_from_spec(spec)
spec.loader.exec_module(benchmark)
REPO = 'coyotte508/powergrid-ai-germany-v1'


def collect(revision, output):
    if not re.fullmatch('[0-9a-f]{40}', revision):
        raise ValueError('Pin an immutable artifact revision')
    protocol_path = ROOT / 'ai/strong/full-throughput-protocol-v1.json'
    protocol = json.loads(protocol_path.read_text())
    jobs = json.loads((ROOT / 'ai/strong/full-throughput-status-v1.json').read_text())['jobs']
    api = HfApi()
    for job in jobs.values():
        if api.inspect_job(job_id=job['job_id']).status.stage != 'COMPLETED':
            raise ValueError('Wait for both existing jobs to complete; do not restart them')
    output.mkdir(parents=True, exist_ok=True)
    result = {'artifact_revision': revision, 'platforms': {}, 'qualification_eligible': False,
        'limitations': protocol['limitations']}
    for flavor, config in protocol['platforms'].items():
        run = config['env']['RUN_NAME']
        folder = output / flavor
        folder.mkdir(exist_ok=True)
        hashes = {}
        for name in ['throughput.json', 'metrics.json', 'latest.pt', 'schema.json']:
            file = folder / name
            shutil.copyfile(hf_hub_download(REPO, f'runs/{run}/{name}', revision=revision), file)
            hashes[name] = hashlib.sha256(file.read_bytes()).hexdigest()
        report = json.loads((folder / 'throughput.json').read_text())
        metrics = json.loads((folder / 'metrics.json').read_text())
        checkpoint = torch.load(folder / 'latest.pt', map_location='cpu', weights_only=True)
        expected = {'status': 'complete', 'flavor': flavor, 'run': run, 'tf32': False,
            'runtime_sha256': protocol['runtime_sha256'], 'metrics_sha256': hashes['metrics.json'],
            'protocol_sha256': hashlib.sha256(protocol_path.read_bytes()).hexdigest()}
        for key, value in expected.items():
            if report.get(key) != value:
                raise ValueError('Throughput provenance mismatch: ' + key)
        expected_checkpoint = {'update': 2, 'architecture': 'multiplayer_ordered', 'feature_revision': '4.0-multiplayer',
            'mixed_player_counts': True, 'async_rollout': True, 'training_device': config['env']['TRAIN_DEVICE'],
            'snapshot_admission': 'periodic_anchor', 'snapshot_interval': 5, 'snapshot_updates': [-1],
            'opponent_mode': 'population_heterogeneous', 'frozen_opponents': protocol['frozen_opponents'],
            'initial_checkpoint': protocol['initial']['path'], 'initial_revision': protocol['initial']['revision'],
            'initial_sha256': protocol['initial']['sha256']}
        for key, value in expected_checkpoint.items():
            if checkpoint.get(key) != value:
                raise ValueError('Checkpoint provenance mismatch: ' + key)
        schema = json.loads((folder / 'schema.json').read_text())
        if schema['seed'] != int(protocol['common_env']['TRAIN_SEED']) or schema['run'] != run:
            raise ValueError('Wrong seed or run')
        summary = benchmark.summarize(metrics)
        if summary != report['training']:
            raise ValueError('Stored timings disagree with raw metrics')
        result['platforms'][flavor] = {'job_id': jobs[flavor]['job_id'], 'hashes': hashes,
            'processor': report['processor'], 'visible_logical_cpus': report['logical_cpus'], 'gpu': report['gpu'],
            'total_seconds': report['total_seconds'], 'training': summary,
            'gpu_utilization_mean_percent': report.get('gpu_utilization_mean_percent'),
            'cpu_seconds_including_reaped_children': report['cpu_seconds_including_reaped_children']}
    parent = json.loads((ROOT / 'ai/strong/population-heterogeneous-u9-checkpoint-v1.json').read_text())['checkpoint']
    original = Path(hf_hub_download(REPO, f'runs/{parent["run"]}/metrics.json', revision=parent['revision']))
    if hashlib.sha256(original.read_bytes()).hexdigest() != parent['hashes']['metrics.json']:
        raise ValueError('Original runtime reference changed')
    shutil.copyfile(original, output / 'original-metrics.json')
    rows = [r for r in json.loads(original.read_text()) if r.get('stage') == 'train' and r['update'] < 3]
    result['original_reference'] = {'revision': parent['revision'], 'metrics_sha256': parent['hashes']['metrics.json'],
        'training': benchmark.summarize(rows)}
    timings = {k: v['training']['median_update_seconds'] for k, v in result['platforms'].items()}
    result['observed_median_ratios'] = {
        'optimized_cpu_over_h200': timings['cpu-performance'] / timings['h200'],
        'original_over_optimized_cpu': result['original_reference']['training']['median_update_seconds'] / timings['cpu-performance']}
    (output / 'summary.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'timings_seconds': timings, 'ratios': result['observed_median_ratios']}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('revision')
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    collect(args.revision, args.output.resolve())
