"""Time the unchanged trainer on HF Jobs, preserving complete-game diagnostics."""
import hashlib
import json
import os
from pathlib import Path
import resource
import runpy
import statistics
import subprocess
import threading
import time

from huggingface_hub import HfApi
import torch


def summarize(metrics):
    rows = [r for r in metrics if r.get('stage') == 'train']
    if [r['update'] for r in rows] != [0, 1, 2]:
        raise ValueError('Require all three complete updates')
    for r in rows:
        if (r['episodes'] != 240 or r['truncated']
                or set(r['by_player_count']) != set('23456')
                or any(x['episodes'] != 48 or x['truncated'] for x in r['by_player_count'].values())
                or sum(r['opponent_seats'].values()) != 960
                or not r.get('search_rollouts_reported')
                or not r.get('search_stats')
                or any(s['truncated'] for s in r['search_stats'].values())):
            raise ValueError('Incomplete or truncated training batch')
    names = ['seconds', 'rollout_seconds', 'policy_seconds', 'engine_seconds', 'samples']
    summaries = []
    for r in rows:
        summaries.append({'update': r['update'], **{k: r[k] for k in names},
            'optimization_seconds': r['seconds'] - r['rollout_seconds'],
            'search_stats': r['search_stats'], 'opponent_seats': r['opponent_seats'],
            'by_player_count': r['by_player_count']})
    return {'complete_games': sum(r['episodes'] for r in rows), 'updates': summaries,
        'median_update_seconds': statistics.median(r['seconds'] for r in rows),
        'median_rollout_seconds': statistics.median(r['rollout_seconds'] for r in rows),
        'median_optimization_seconds': statistics.median(r['seconds'] - r['rollout_seconds'] for r in rows),
        'games_per_minute_during_updates': 60 * 720 / sum(r['seconds'] for r in rows)}


def cpu_time():
    return sum(x.ru_utime + x.ru_stime for x in [
        resource.getrusage(resource.RUSAGE_SELF), resource.getrusage(resource.RUSAGE_CHILDREN)])


def main():
    if os.environ.get('POWERGRID_BENCHMARK_PLATFORM') != 'hf-job':
        raise ValueError('Full gradient timing runs only on HF Jobs')
    protocol = json.loads(Path('ai/strong/full-throughput-protocol-v1.json').read_text())
    flavor = os.environ['BENCHMARK_FLAVOR']
    for key, expected in {**protocol['common_env'], **protocol['platforms'][flavor]['env']}.items():
        if os.environ.get(key) != expected:
            raise ValueError('Benchmark configuration mismatch: ' + key)
    for path, expected in protocol['runtime_sha256'].items():
        if hashlib.sha256(Path(path).read_bytes()).hexdigest() != expected:
            raise ValueError('Runtime hash mismatch: ' + path)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    cpu_model = next((line.split(':', 1)[1].strip() for line in Path('/proc/cpuinfo').read_text().splitlines()
        if line.startswith('model name')), 'unknown')
    output = Path('ai/runs') / os.environ['RUN_NAME']
    output.mkdir(parents=True, exist_ok=True)
    report = {'flavor': flavor, 'run': os.environ['RUN_NAME'], 'torch_version': torch.__version__,
        'logical_cpus': os.cpu_count(), 'processor': cpu_model,
        'gpu': torch.cuda.get_device_name() if torch.cuda.is_available() else None,
        'tf32': False, 'protocol_sha256': hashlib.sha256(Path('ai/strong/full-throughput-protocol-v1.json').read_bytes()).hexdigest(),
        'runtime_sha256': protocol['runtime_sha256'], 'qualification_eligible': False,
        'interpretation': protocol['limitations']}
    print(json.dumps({'stage': 'full_throughput_start', **report}), flush=True)
    start, cpu_start = time.perf_counter(), cpu_time()
    stop = threading.Event()
    samples = []
    def monitor():
        while not stop.is_set():
            try:
                query = subprocess.run(['nvidia-smi', '--query-gpu=utilization.gpu,memory.used',
                    '--format=csv,noheader,nounits'], capture_output=True, text=True, timeout=5)
                if query.returncode == 0:
                    utilization, memory = [float(x.strip()) for x in query.stdout.strip().splitlines()[0].split(',')]
                    samples.append({'seconds': time.perf_counter() - start, 'utilization_percent': utilization, 'memory_mib': memory})
            except (FileNotFoundError, ValueError, subprocess.TimeoutExpired):
                pass
            stop.wait(5)
    monitor_thread = threading.Thread(target=monitor, daemon=True)
    if os.environ['TRAIN_DEVICE'] == 'cuda':
        monitor_thread.start()
    error = None
    try:
        runpy.run_path('ai/strong/train.py', run_name='__main__')
        metrics_path = output / 'metrics.json'
        report['metrics_sha256'] = hashlib.sha256(metrics_path.read_bytes()).hexdigest()
        report['training'] = summarize(json.loads(metrics_path.read_text()))
        report['status'] = 'complete'
    except Exception as caught:
        report.update(status='failed', error=type(caught).__name__ + ': ' + str(caught))
        error = caught
    finally:
        stop.set()
        if monitor_thread.is_alive():
            monitor_thread.join(timeout=6)
        report.update(total_seconds=time.perf_counter() - start, cpu_seconds_including_reaped_children=cpu_time() - cpu_start,
            gpu_samples=samples)
        if samples:
            report['gpu_utilization_mean_percent'] = statistics.mean(s['utilization_percent'] for s in samples)
            report['gpu_memory_peak_sampled_mib'] = max(s['memory_mib'] for s in samples)
        result = output / 'throughput.json'
        result.write_text(json.dumps(report, indent=2) + '\n')
        HfApi().upload_file(path_or_fileobj=result, path_in_repo=f'runs/{os.environ["RUN_NAME"]}/throughput.json',
            repo_id=os.environ['HF_MODEL_REPO'])
        print(json.dumps({'stage': 'full_throughput_finished', 'status': report['status'],
            'total_seconds': report['total_seconds'], 'training': report.get('training')}), flush=True)
    if error is not None:
        raise error


if __name__ == '__main__':
    main()
