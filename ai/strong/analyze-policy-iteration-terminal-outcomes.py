"""Diagnose terminal changes in the fixed, already verified complete-cell snapshot.

No new games, interim peeking, candidate selection, or causal phase attribution.
Retain every complete cell, rule view and ensemble from the input snapshot.
"""
import argparse
from collections import Counter
import importlib.util
from pathlib import Path

import numpy as np

from strategic_collection import ROOT, read, write, digest
from policy_iteration_development import PROTOCOL, SOURCE


def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT/'ai/strong'/filename)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


terminal = module('terminal_metrics', 'analyze-search-transfer-outcomes.py')
full = module('full_comparison', 'compare-policy-iteration-development.py')


def identity(row):
    return row['gameSeed'], row['seat'], row['variant'], row['sealed']


def describe(candidate, parent, protocol, expected):
    result = terminal.paired_changes(candidate, parent, protocol)
    result['parent_failures'] = result.pop('raw_failures')
    result['candidate_failures'] = result.pop('search_failures')
    for metric in result['terminal_changes'].values():
        metric['mean_candidate_minus_parent'] = metric.pop('mean_search_minus_raw')
    assert result['games_per_arm'] == expected['games_per_model']
    assert result['independent_deals'] == expected['independent_deals'] == 16
    win = result['terminal_changes']['win_credit']['mean_candidate_minus_parent']
    assert abs(win-expected['win_share_difference']) < 1e-12
    result['means'] = {
        key: {name: float(np.mean([terminal.metrics(row)[name] for row in rows]))
              for name in terminal.metrics(rows[0])}
        for key, rows in [('parent', parent), ('candidate', candidate)]}
    move_names = sorted(set().union(*(row['policyMoves'] for row in candidate+parent)))
    result['mean_policy_move_counts'] = {
        key: {name: float(np.mean([row['policyMoves'].get(name, 0) for row in rows]))
              for name in move_names}
        for key, rows in [('parent', parent), ('candidate', candidate)]}
    a, b = {identity(r): r for r in candidate}, {identity(r): r for r in parent}
    changed = {'lost_win_credit': [], 'gained_win_credit': []}
    for k in sorted(a):
        delta = a[k]['win']-b[k]['win']
        if delta:
            changed['gained_win_credit' if delta > 0 else 'lost_win_credit'].append({
                'game_seed': k[0], 'seat': k[1], 'variant': k[2], 'sealed': k[3],
                'win_credit_change': delta,
                'parent': terminal.metrics(b[k]), 'candidate': terminal.metrics(a[k])})
    result['changed_outcomes'] = changed
    return result


def main(snapshot_path, output):
    assert not output.exists(), 'Preserve existing evidence'
    snapshot = read(snapshot_path)
    protocol = read(PROTOCOL)
    assert snapshot['interim_diagnostic'] and not snapshot['full_comparison_complete']
    assert snapshot['protocol_sha256'] == digest(PROTOCOL)
    assert snapshot['source'] == read(SOURCE)
    assert not snapshot['reserved_final_seeds_used'] and not snapshot['candidate_selected']
    assert set(snapshot['absolute']) == set(protocol['models'])
    for name, sha in snapshot['code_hashes'].items():
        assert digest(ROOT/name) == sha
    rows = {}
    for key in protocol['models']:
        plan = full.grid.require_plan(key)
        planned = {r['case']: r for r in plan['shards']}
        rows[key] = {}
        for case, record in snapshot['provenance'][key].items():
            directory = full.grid.manager.VERIFIED/case
            assert digest(directory/'verified.json') == record['verified_sha256']
            assert digest(directory/'evaluation.json') == record['evaluation_sha256']
            verified = read(directory/'verified.json')
            assert verified['verified'] and verified['job_id'] == record['job_id']
            assert verified['source'] == snapshot['source']
            assert verified['model_pin'] == snapshot['pins'][key] == plan['model_pin']
            for name, sha in verified['artifacts'].items():
                assert digest(directory/name) == sha
            shard = planned[case]
            guard = full.grid.matching_guard(full.grid.manager.GUARDS/(case+'.json'), shard, plan)
            assert guard['job_id'] == record['job_id']
            cell = shard['opponent']+'/'+str(shard['players'])+'p'
            assert cell in snapshot['complete_cells']
            rows[key].setdefault(cell, []).extend(read(directory/'evaluation.json')['results'])
        assert set(rows[key]) == set(snapshot['complete_cells'])
        for cell, games in rows[key].items():
            assert len(games) == snapshot['absolute'][key][cell]['overall']['games']
            assert len(games) == len({identity(row) for row in games})
            assert not any(row['truncated'] for row in games)
        assert sum(map(len, rows[key].values())) == snapshot['games_per_arm']
    comparisons = {}
    for key in protocol['models']:
        if key == 'parent':
            continue
        comparisons[key] = {}
        for cell in snapshot['complete_cells']:
            expected = snapshot['comparisons'][key+'-minus-parent'][cell]
            candidate, parent = rows[key][cell], rows['parent'][cell]
            candidate_views, parent_views = full.rule_views(candidate), full.rule_views(parent)
            comparisons[key][cell] = {
                'overall': describe(candidate, parent, protocol, expected['overall']),
                'by_rules': {rule: describe(candidate_views[rule], parent_views[rule], protocol,
                                            expected['by_rules'][rule]) for rule in candidate_views}}
        print({'model': key, 'cells': len(comparisons[key])}, flush=True)
    code = [Path(__file__), ROOT/'ai/strong/analyze-search-transfer-outcomes.py',
            ROOT/'ai/strong/compare-policy-iteration-development.py']
    write(output, {
        'snapshot_path': str(snapshot_path.relative_to(ROOT)), 'snapshot_sha256': digest(snapshot_path),
        'snapshot_cutoff_utc': snapshot['cutoff_utc'], 'snapshot_provenance': snapshot['provenance'],
        'complete_cells': snapshot['complete_cells'], 'games': snapshot['games'],
        'independent_deals_per_cell': 16, 'comparisons': comparisons,
        'code_hashes': {str(p.relative_to(ROOT)): digest(p) for p in code},
        'new_games': 0, 'gradients': False, 'candidate_selected': False,
        'full_comparison_complete': False, 'qualification_eligible': False,
        'reserved_final_seeds_used': False,
        'scope': 'Descriptive paired terminal diagnosis on the fixed already verified complete-cell '
                 'snapshot. All four models, nineteen cells and all rule views retained. Whole-deal '
                 'bootstrap intervals are exploratory marginal intervals, without multiplicity '
                 'correction. Failure categories overlap. Terminal differences and move counts '
                 'cannot identify causal decisions; game lengths and opponent responses can change. '
                 'No new games, new interim win-rate look, candidate selection or qualification.'})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--snapshot', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    main(args.snapshot.resolve(), args.output.resolve())
