"""Bounded read-only live progress/metrics; never collects, retries or cancels."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
from pathlib import Path
import signal
import statistics

from huggingface_hub import HfApi
from strategic_collection import ROOT, read, write, digest

PLAN = ROOT / 'ai/strong/population-hybrid-development-plan-v1.json'
GUARDS = ROOT / 'ai/runs/population-hybrid-development-launches-v1'
OUTPUT = ROOT / 'ai/runs/population-hybrid-live-runtime-v1'


def inspect(case):
    plan = read(PLAN)
    rows = [row for row in plan['shards'] if row['case'] == case]
    assert len(rows) == 1
    guard = read(GUARDS / (case + '.json'))
    assert guard['stage'] == 'launched' and guard['plan_sha256'] == digest(PLAN)
    assert guard['row'] == rows[0] and guard['source'] == plan['source']
    api = HfApi()
    job = api.inspect_job(job_id=guard['job_id'])
    progress = []
    for line in api.fetch_job_logs(job_id=guard['job_id'], follow=False, tail=200):
        try:
            row = json.loads(line)
        except (ValueError, TypeError):
            continue
        if isinstance(row, dict) and {'episode', 'completed', 'total', 'seconds', 'caps', 'truncated'} <= set(row):
            assert row['total'] == rows[0]['games'] and 1 <= row['completed'] <= row['total']
            progress.append({key: row[key] for key in ['episode', 'completed', 'total', 'seconds', 'caps', 'truncated']})
    result = {'case': case, 'job_id': guard['job_id'], 'authoritative_status': job.status.stage,
              'checked_at': datetime.now(timezone.utc).isoformat(),
              'created_at': str(job.created_at), 'started_at': str(job.started_at),
              'running_seconds': job.durations.running_secs,
              'flavor': job.flavor, 'configured_timeout_hours': plan['admission']['timeout_hours'],
              'guard_sha256': digest(GUARDS / (case + '.json')), 'progress': progress}
    if progress:
        assert len({r['episode'] for r in progress}) == len(progress)
        last = max(progress, key=lambda r: r['completed'])
        result.update(last_progress=last,
                      observed_completed_caps=sum(r['caps'] for r in progress),
                      observed_truncated=sum(r['truncated'] for r in progress),
                      observed_game_seconds_median=statistics.median(r['seconds'] for r in progress),
                      observed_game_seconds_max=max(r['seconds'] for r in progress))
        if job.status.stage == 'RUNNING' and job.durations.running_secs:
            estimate = job.durations.running_secs * last['total'] / last['completed']
            result['crude_total_seconds_at_completed_rate'] = estimate
            result['rate_exceeds_configured_timeout'] = estimate > 3600 * plan['admission']['timeout_hours']
            result['projection_limit'] = 'Censored, ordered, concurrent games; completed-game rate is only a timeout-risk indicator, not a reliable ETA or proof of eventual timeout.'
    return result


def metrics(result, count):
    assert type(count) is int and 0 <= count <= 30
    if not count or result['authoritative_status'] != 'RUNNING':
        return
    samples = []
    stream = HfApi().fetch_job_metrics(job_id=result['job_id'])
    previous_handler = signal.getsignal(signal.SIGALRM)
    def expired(*args):
        raise TimeoutError('Bounded metrics observation ended')
    signal.signal(signal.SIGALRM, expired)
    signal.alarm(40)
    try:
        for sample in stream:
            samples.append({key: sample[key] for key in ['cpu_usage_pct', 'cpu_millicores',
                'memory_used_bytes', 'memory_total_bytes', 'rx_bps', 'tx_bps', 'gpus', 'replica']})
            if len(samples) == count:
                break
    except Exception as error:
        result['metrics_observation_error'] = type(error).__name__ + ': ' + str(error)
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, previous_handler)
        stream.close()
    result['metrics'] = samples
    if len(samples) > 1:
        # Keep every raw frame; the first can report an initialization zero.
        result['cpu_percent_median_after_first_frame'] = statistics.median(s['cpu_usage_pct'] for s in samples[1:])
        result['memory_bytes_max'] = max(s['memory_used_bytes'] for s in samples)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('cases', nargs='+')
    parser.add_argument('--metrics-count', type=int, default=0,
                        help='Sample only the first requested live job, at most 30 frames / 40s.')
    args = parser.parse_args()
    assert len(args.cases) <= 8 and len(set(args.cases)) == len(args.cases)
    assert 0 <= args.metrics_count <= 30
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(inspect, args.cases))
    metrics(results[0], args.metrics_count)
    OUTPUT.mkdir(exist_ok=True)
    path = OUTPUT / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '-observation.json')
    assert not path.exists()
    write(path, {'observer_sha256': digest(Path(__file__)), 'plan_sha256': digest(PLAN),
                 'purpose': 'Read-only execution progress; no result collection or strength selection.',
                 'jobs': results, 'new_hf_jobs': 0, 'remote_mutations': False,
                 'qualification_eligible': False, 'reserved_final_seeds_used': False})
    print(json.dumps({'saved': str(path), 'jobs': [{k: v for k, v in result.items()
        if k not in ['progress', 'metrics']} for result in results]}, indent=2))
