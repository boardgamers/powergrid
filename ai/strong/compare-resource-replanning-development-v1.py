"""Complete resource ablation with equal-count summaries and whole-deal pairs."""
import argparse
from collections import Counter
import json
from pathlib import Path

import numpy as np
from strategic_collection import ROOT, read, write, digest
from resource_development_v1 import validate, verify_pins
from policy_iteration_development import summarize

import importlib.util

spec = importlib.util.spec_from_file_location('resource_screen_manager', Path(__file__).with_name('manage-resource-replanning-development-v1.py'))
manager = importlib.util.module_from_spec(spec)
spec.loader.exec_module(manager)
pairs = manager.module('resource_paired_statistics', 'compare-population-screens.py')
OUTPUT = ROOT / 'ai/strong/resource-replanning-development-comparison-v1.json'


def rule_views(rows):
    return {v + ('/sealed' if s else '/open'): [r for r in rows if r['variant'] == v and r['sealed'] is s]
            for v in ('original', 'recharged') for s in (False, True)}


def validate_grid(reports, protocol):
    validate(protocol)
    assert set(reports) == set(protocol['arms'])
    cells = {f'{r["opponent"]}/{r["players"]}p': r for r in protocol['screens']}
    for arm, actual in reports.items():
        assert set(actual) == set(cells), 'All 27 cells are required for each arm'
        for name, screen in cells.items():
            n = screen['players']
            prefix = protocol['seed_template'].format(players=n)
            expected = {(f'{prefix}-{d}', v, s, seat) for d in range(4)
                        for v in ('original', 'recharged') for s in (False, True) for seat in range(n)}
            rows = actual[name]
            assert len(rows) == screen['games']
            assert {(r['gameSeed'], r['variant'], r['sealed'], r['seat']) for r in rows} == expected
            assert all(type(r['sealed']) is bool and type(r['seat']) is int and r['truncated'] is False
                       and type(r['win']) in (int, float) and np.isfinite(r['win']) and 0 <= r['win'] <= 1 for r in rows)
        assert sum(map(len, actual.values())) == 1680


def equal_count_summary(reports, opponent, protocol):
    # Each count has four independent deals. All its seats and rules stay together.
    deltas, counts = [], {}
    for n in range(2, 7):
        cell = f'{opponent}/{n}p'
        arms = {arm: {d: np.mean([r['win'] for r in reports[arm][cell] if r['gameSeed'] == d])
                     for d in sorted({r['gameSeed'] for r in reports[arm][cell]})} for arm in protocol['arms']}
        assert set(arms['filter']) == set(arms['resource-filter']) and len(arms['filter']) == 4
        differences = [arms['resource-filter'][d] - arms['filter'][d] for d in sorted(arms['filter'])]
        deltas.append(differences)
        counts[str(n)] = {'deal_differences': dict(zip(sorted(arms['filter']), differences)),
                          'win_share_difference': float(np.mean(differences)), 'weight': .2}
    delta = np.asarray(deltas)
    rng = np.random.default_rng(protocol['bootstrap_seed'])
    bootstrap = np.zeros(protocol['bootstrap_replicates'])
    for count in delta:
        bootstrap += count[rng.integers(4, size=(len(bootstrap), 4))].mean(1) / 5
    return {'win_share_difference': float(delta.mean()), 'player_counts': counts,
            'paired_deal_bootstrap_95_interval': np.quantile(bootstrap, [.025, .975]).tolist(),
            'independent_deals_per_count': 4, 'unit': 'Resample whole deals independently within each count, then average the five count means equally.'}


def analyze(reports, protocol):
    validate_grid(reports, protocol)
    absolute = {arm: {cell: {'overall': summarize(rows, protocol),
                'by_rules': {rule: summarize(selected, protocol) for rule, selected in rule_views(rows).items()}}
                for cell, rows in cells.items()} for arm, cells in reports.items()}
    contrasts = {}
    def paired(left, right):
        return pairs.paired_difference(left, right, repeats=protocol['bootstrap_replicates'], seed=protocol['bootstrap_seed'])
    for cell, rows in reports['resource-filter'].items():
        other = reports['filter'][cell]
        a, b = rule_views(rows), rule_views(other)
        contrasts[cell] = {'overall': paired(rows, other), 'by_rules': {r: paired(a[r], b[r]) for r in a}}
    return {'absolute': absolute, 'resource_minus_filter': contrasts,
            'primary_search_equal_count': equal_count_summary(reports, 'search_geo', protocol),
            'secondary_economic_equal_count': equal_count_summary(reports, 'economic', protocol)}


def latency(values):
    return {'count': len(values), 'p50_ms': float(np.percentile(values, 50)) if values else None,
            'p95_ms': float(np.percentile(values, 95)) if values else None, 'max_ms': max(values) if values else None}


def compare(output):
    assert not output.exists(), 'Do not overwrite a completed comparison'
    launcher = manager.launcher
    plan, protocol = read(launcher.PLAN), read(launcher.PROTOCOL)
    launcher.validate_plan(plan, protocol)
    # Refuse a partial grid before expensive raw receipt reads or output writes.
    for row in plan['shards']:
        assert (manager.COLLECTED / row['case'] / 'verified.json').exists(), 'All resource shards must verify first'
    hashes = {**manager.code_hashes(), str(Path(__file__).relative_to(ROOT)): digest(__file__),
              str(Path(pairs.__file__).relative_to(ROOT)): digest(pairs.__file__),
              'ai/strong/policy_iteration_development.py': digest(ROOT / 'ai/strong/policy_iteration_development.py')}
    reports = {arm: {} for arm in protocol['arms']}
    measurements = {arm: {'counts': Counter(), 'decisions': [], 'resources': [], 'runtime': []} for arm in protocol['arms']}
    provenance = {}
    for row in plan['shards']:
        checked = manager.verified_receipt(row['case'], full=True)
        assert checked is not None
        folder = manager.COLLECTED / row['case']
        evaluation = folder / 'artifacts/evaluation'
        cell = f'{row["opponent"]}/{row["players"]}p'
        records = read(evaluation / 'evaluation.json')['results']
        reports[row['arm']].setdefault(cell, []).extend(r['terminal'] for r in records)
        measured = measurements[row['arm']]
        measured['counts'].update(checked['summary']['counts'])
        measured['runtime'].append({'case': row['case'], **checked['runtime']})
        for record in records:
            with (evaluation / f'decisions-{record["episode"]}.jsonl').open() as stream:
                for line in stream:
                    decision = json.loads(line)
                    measured['decisions'].append(decision['elapsedMs'])
                    if decision.get('resourcePlan') is not None:
                        measured['resources'].append(decision['elapsedMs'])
        provenance[row['case']] = {'job_id': checked['job_id'], 'verified_sha256': digest(folder / 'verified.json'), 'evidence': checked['evidence']}
    assert len({r['job_id'] for r in provenance.values()}) == len(plan['shards'])
    analysis = analyze(reports, protocol)
    costs = {}
    for arm, data in measurements.items():
        assert len(data['decisions']) == data['counts']['decisions']
        assert len(data['resources']) == data['counts']['resource_search_decisions']
        assert data['counts']['rollout_caps'] == 0
        costs[arm] = {'counts': dict(data['counts']), 'decision_latency': latency(data['decisions']),
                     'resource_latency': latency(data['resources']), 'per_shard_runtime': data['runtime'],
                     'timing_scope': 'Parallel HF jobs with eight game workers; not AMD8840U serving latency.'}
    verify_pins(protocol)
    assert all(digest(ROOT / name) == sha for name, sha in hashes.items())
    result = {'complete': True, 'games': 3360, 'independent_deals_per_cell': 4, **analysis, 'costs': costs,
              'source': plan['source'], 'protocol_sha256': digest(launcher.PROTOCOL), 'plan_sha256': digest(launcher.PLAN),
              'code_hashes': hashes, 'provenance': provenance, 'candidate_selected': False,
              'qualification_eligible': False, 'reserved_final_seeds_used': False,
              'scope': 'All two arms, 27 count/opponent cells, four rules and every adverse result. Exploratory four-deal intervals; no automatic promotion or rule/count routing. Requires fresh confirmation and exact selected-policy target benchmark.'}
    with output.open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write('\n')
    return {'complete': True, 'games': 3360, 'comparison_sha256': digest(output)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--output', type=Path, default=OUTPUT)
    print(compare(parser.parse_args().output.resolve()))
