"""Resource-only diagnosis of an immutable, possibly incomplete collection cycle.

Reads measured costs and provenance, never game outcomes or strength aggregates.
Does not submit jobs or change any frozen resource/policy configuration.
"""
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import statistics

from public_policy_development_job_v1 import digest, read
from public_policy_final_contract_v1 import object_hash

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT/'ai/strong/current-auction-grid-source-v1.json'
JOBS = ROOT/'ai/runs/current-auction-grid-hf-v1'
MEASURES = ('seconds', 'cpu_seconds', 'sampled_peak_total_rss_bytes', 'memory_samples')


def review(cycle_path):
    source, cycle = read(SOURCE), read(cycle_path)
    assert cycle['complete'] is False and cycle['qualified'] is False
    assert cycle['new_jobs'] == cycle['new_games'] == 0
    rows = {r['name']: r for r in source['rows']}
    assert len(rows) == cycle['expected_jobs'] == 944
    states = {}; costs = []; pins = {str(SOURCE.relative_to(ROOT)): digest(SOURCE),
        str(cycle_path.relative_to(ROOT)): digest(cycle_path),
        str(Path(__file__).relative_to(ROOT)): digest(__file__)}
    for observed in cycle['audited_originals']:
        name = observed['name']; row = rows[name]; folder = JOBS/name
        receipt = folder/('verified-terminal-recovery-v1.json' if observed['stage'] == 'ERROR' else 'verified.json')
        saved = read(receipt); guard = read(folder/'launch.json')
        assert saved['verified'] and saved['job_id'] == observed['job_id'] == guard['job_id']
        assert saved['row'] == guard['row'] == row and guard['stage'] == 'launched'
        assert saved['evidence'] == observed['evidence'] and saved['evidence']['remote_archive_verified']
        assert saved['source_sha256'] == digest(SOURCE)
        assert guard['source_fingerprint'] == object_hash(source)
        assert saved['guard_sha256'] == digest(folder/'launch.json')
        manifest = folder/'artifacts/manifest.json'; measured = folder/'artifacts/measurement.json'
        assert digest(manifest) == observed['evidence']['manifest_sha256']
        assert digest(measured) == read(manifest)['measurement.json']
        raw = read(measured); measurement = raw['measurement']
        assert raw['case'] == name and raw['scope'] == 'development'
        assert raw['experiment_protocol_sha256'] == source['protocol_sha256']
        assert raw['measured_entry_sha256'] == source['measured_entry_sha256']
        assert raw['provenance']['shard'] == row['shard'] and raw['provenance']['identity'] == row['identity']
        assert raw['provenance']['source_revision'] == source['revision']
        assert raw['provenance']['source_archive_sha256'] == source['sha256']
        assert saved['review']['measurement'] == measurement and saved['review']['games'] == row['shard']['games']
        assert measurement['memory_sampling_period_seconds'] == .2 and measurement['includes_startup_and_validation']
        assert all(type(measurement[k]) in (int, float) and math.isfinite(measurement[k]) and measurement[k] > 0 for k in MEASURES)
        assert observed['stage'] in ('COMPLETED', 'ERROR')
        if observed['stage'] == 'ERROR':
            recovery = saved['review']['recovery']
            assert recovery['all_original_games_retained'] and recovery['raw_records_changed'] is False and recovery['new_games'] == 0
        assert name not in states; states[name] = 'audited'
        for path in (receipt, folder/'launch.json', manifest, measured): pins[str(path.relative_to(ROOT))] = digest(path)
        deadline = int(row['timeout'][:-1])*3600; assert row['timeout'].endswith('h')
        costs.append({'name': name, 'job_id': observed['job_id'], 'arm': row['arm'],
            'players': row['players'], 'opponent': row['shard']['opponent'], 'games': row['shard']['games'],
            'original_hf_stage': observed['stage'], 'timeout_seconds': deadline,
            'measurement': {k: measurement[k] for k in MEASURES},
            'measured_wall_seconds_per_game_at_frozen_concurrency': measurement['seconds']/row['shard']['games'],
            'measurement_fraction_of_job_timeout': measurement['seconds']/deadline})
    for category, key in [('failed', 'failed_originals'), ('active', 'active_originals'), ('deferred', 'deferred_terminals')]:
        for observed in cycle[key]:
            name = observed.get('name', observed.get('row', {}).get('name'))
            assert name in rows and name not in states
            guard_path = JOBS/name/'launch.json'; guard = read(guard_path)
            assert guard['job_id'] == observed['job_id'] and guard['row'] == rows[name]
            assert guard['source_fingerprint'] == object_hash(source)
            pins[str(guard_path.relative_to(ROOT))] = digest(guard_path); states[name] = category
    for name in cycle['unsubmitted_jobs']:
        assert name in rows and name not in states and not (JOBS/name/'launch.json').exists()
        states[name] = 'unsubmitted'
    assert set(states) == set(rows) and len(costs) == cycle['verified_jobs']
    grouped = defaultdict(list)
    for item in costs: grouped[(item['arm'], item['players'], item['opponent'])].append(item)
    summaries = []
    for key in sorted({(r['arm'], r['players'], r['shard']['opponent']) for r in rows.values()}):
        selected = [r for r in rows.values() if (r['arm'], r['players'], r['shard']['opponent']) == key]
        group = grouped[key]; counts = Counter(states[r['name']] for r in selected)
        summary = {'arm': key[0], 'players': key[1], 'opponent': key[2],
            'planned_jobs': len(selected), 'planned_games': sum(r['shard']['games'] for r in selected),
            'coverage': {k: counts[k] for k in ('audited', 'failed', 'active', 'deferred', 'unsubmitted')},
            'complete_cost_coverage': counts['audited'] == len(selected), 'completed_cost_summary': None}
        if group:
            summary['completed_cost_summary'] = {
                'jobs': len(group), 'games': sum(r['games'] for r in group),
                'median_wall_seconds': statistics.median(r['measurement']['seconds'] for r in group),
                'max_wall_seconds': max(r['measurement']['seconds'] for r in group),
                'max_wall_seconds_per_game_at_frozen_concurrency': max(r['measured_wall_seconds_per_game_at_frozen_concurrency'] for r in group),
                'median_accounted_cpu_seconds_per_wall_second': statistics.median(r['measurement']['cpu_seconds']/r['measurement']['seconds'] for r in group),
                'max_sampled_peak_total_rss_bytes': max(r['measurement']['sampled_peak_total_rss_bytes'] for r in group),
                'max_measurement_fraction_of_job_timeout': max(r['measurement_fraction_of_job_timeout'] for r in group)}
        summaries.append(summary)
    return {'created_at': datetime.now(timezone.utc).isoformat(), 'purpose': 'resource_only_incomplete_confirmation_diagnosis',
        'cycle': str(cycle_path.relative_to(ROOT)), 'cycle_checked_at': cycle['checked_at'],
        'cycle_sha256': digest(cycle_path), 'source_sha256': digest(SOURCE),
        'collection_counts': dict(Counter(states.values())), 'audited_games': sum(r['games'] for r in costs),
        'completed_measurement_wall_hours': sum(r['measurement']['seconds'] for r in costs)/3600,
        'completed_measurement_cpu_hours': sum(r['measurement']['cpu_seconds'] for r in costs)/3600,
        'original_pilot_sizing': source['sizing'], 'groups': summaries, 'cost_records': costs,
        'failed_originals': cycle['failed_originals'], 'active_originals': cycle['active_originals'],
        'input_hashes': pins, 'assumptions_and_limits': [
            'Completed measurements are conditional on completion. Failed and unfinished jobs remain explicit; no uncensored runtime bound is estimated.',
            'Wall seconds per game is amortized job cost at frozen concurrency, not serial game latency.',
            'Measurement excludes at least archive upload and platform queueing; its fraction of the hard timeout understates full job occupancy.',
            'Memory is sampled process RSS, not total container peak; CPU/wall is accounted CPU concurrency, not hardware utilization percent.',
            'No game outcomes, wins, value scores, model rankings or strength aggregates are examined by this resource review.',
            'No deadline, frozen source, policy, worker count, seeds, acceptance threshold or job schedule is changed or admitted.'],
        'new_hf_jobs': 0, 'new_games': 0, 'new_policy_calls': 0, 'resource_change_admitted': False,
        'candidate_selected': False, 'qualified': False, 'reserved_final_seeds_used': False,
        'previous_goal_turn_classification': 'progress', 'current_goal_turn_classification': 'progress', 'goal_status': 'active'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--cycle', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(); assert not args.output.exists(), 'Preserve earlier diagnosis snapshots'
    report = review(args.cycle.resolve())
    with args.output.open('x') as stream: json.dump(report, stream, indent=2, allow_nan=False); stream.write('\n')
    print(json.dumps({k: report[k] for k in ('cycle_checked_at', 'collection_counts', 'audited_games', 'completed_measurement_wall_hours', 'resource_change_admitted')}))
