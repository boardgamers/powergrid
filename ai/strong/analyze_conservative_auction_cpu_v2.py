"""Review complete actual-8840U timings without treating a tiny fixture as a population."""
import argparse
from collections import defaultdict
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import statistics

from conservative_auction_cpu_v2 import ARMS, STAGES, read, digest

ROOT = Path(__file__).resolve().parents[2]
PREP = ROOT/'ai/runs/conservative-auction-8840u-prepared-v2'
COLLECTED = ROOT/'ai/runs/conservative-auction-8840u-collected-v2'
OUTPUT = ROOT/'ai/strong/conservative-auction-8840u-cost-review-v2.json'


def require(condition, message):
    if not condition: raise ValueError(message)


def timing_summary(cases, rows):
    expected_cells = {(n, v, s, stage) for n in range(2, 7) for v in ('original', 'recharged')
                      for s in (False, True) for stage in STAGES}
    require(len(cases) == 100 and len({c['name'] for c in cases}) == 100, 'All 100 distinct cases required')
    require({(c['players'], c['variant'], c['sealed'], c['stage']) for c in cases} == expected_cells,
            'All count/rule/stage cells required')
    for case in cases:
        require(type(case['players']) is int and type(case['sealed']) is bool, 'Malformed count/rules')
    lookup = {c['name']: c for c in cases}
    require(len(rows) == 300, 'All 300 actual target requests required')
    seen = set(); groups = {a: defaultdict(list) for a in ARMS}; cold = {}; points = {a: [] for a in ARMS}
    for row in rows:
        arm, name = row['arm'], row['case']; key = arm, name
        require(arm in ARMS and name in lookup and key not in seen, 'Unknown or duplicated actual request')
        seen.add(key); case = lookup[name]
        first = name == cases[0]['name']
        require(row['first_request'] is first, 'Wrong cold/warm classification')
        ms = row['round_trip_ms']
        require(type(ms) in (int, float) and math.isfinite(ms) and ms > 0, 'Invalid target duration')
        if first:
            total = row['cold_process_plus_request_ms']
            require(type(total) in (int, float) and math.isfinite(total) and total >= ms, 'Invalid cold total')
            cold[arm] = {'case': name, 'process_plus_request_ms': total, 'round_trip_ms': ms}
        else:
            require(row['cold_process_plus_request_ms'] is None, 'Cold duration attached to warm request')
            stage, n = case['stage'], case['players']
            for group in ('all', 'search_eligible_stages' if stage in ('choose', 'bid') else 'other_stages',
                          'stage/'+stage, f'players/{n}', f'players/{n}/stage/{stage}'):
                groups[arm][group].append(ms)
        points[arm].append({'case': name, 'players': case['players'], 'variant': case['variant'],
            'sealed': case['sealed'], 'stage': case['stage'], 'cold': first, 'round_trip_ms': ms})
    require(seen == {(a, c['name']) for a in ARMS for c in cases}, 'Incomplete target coverage')
    return {'requests': 300, 'cold': cold, 'warm': {arm: {name: {'count': len(values),
            'median_ms': statistics.median(values), 'min_ms': min(values), 'max_ms': max(values)}
            for name, values in sorted(groups[arm].items())} for arm in ARMS},
        'all_count_rule_stage_points': {a: sorted(points[a], key=lambda r: r['case']) for a in ARMS},
        'interpretation': 'One saved position per count/rule/stage, one timing per policy. Descriptive fixture costs only; no estimated deployment percentiles, confidence bounds or representative gameplay distribution. Three first requests include cold process startup and are kept separate.',
        'qualification_eligible': False, 'reserved_final_seeds_used': False}


def review(output):
    output = Path(output); require(not output.exists(), 'Preserve existing cost review')
    assessment = read(COLLECTED/'assessment.json'); target = COLLECTED/'output'; state = read(target/'status.json')
    require(assessment['complete'] is True and assessment['exact_cross_host_responses'] == 300
            and assessment['caps'] == 0, 'Complete independent cross-host audit required')
    require(state['stage'] == 'completed' and state['passed'] is True and state['completed_requests'] == 300,
            'Complete target run required')
    require('8840U' in state['processor'] and state['required_cpu'] == '8840U', 'Actual AMD8840U required')
    require(assessment['target_status_sha256'] == digest(target/'status.json'), 'Target status changed')
    require(all(digest(target/name) == sha for name, sha in state['output_hashes'].items()), 'Target receipts changed')
    package = PREP/'package'; manifest = read(package/'benchmark-manifest.json')
    require(state['manifest_sha256'] == assessment['manifest_sha256'] == digest(package/'benchmark-manifest.json'), 'Wrong benchmark source')
    require(digest(package/'cases.json') == manifest['files']['cases.json'], 'Fixture cases changed')
    cases = read(package/'cases.json'); rows = [json.loads(l) for l in (target/'receipts.jsonl').read_text().splitlines()]
    result = timing_summary(cases, rows)
    result.update(created_at=datetime.now(timezone.utc).isoformat(), processor=state['processor'],
        exact_cross_host_responses=300, source_hashes={str(p.relative_to(ROOT)): digest(p) for p in (
            Path(__file__), COLLECTED/'assessment.json', COLLECTED/'independent-audit.log',
            target/'status.json', target/'receipts.jsonl', package/'benchmark-manifest.json', package/'cases.json')})
    with output.open('x') as stream: json.dump(result, stream, indent=2, allow_nan=False); stream.write('\n')
    return {'complete': True, 'requests': 300, 'review_sha256': digest(output)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__); parser.add_argument('--output', type=Path, default=OUTPUT)
    print(json.dumps(review(parser.parse_args().output)))
