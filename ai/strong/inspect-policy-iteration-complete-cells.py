"""Interim diagnosis using every cell complete in all five arms at a fixed cutoff.

Never rank/select candidates, aggregate an incomplete grid, alter the coordinator,
or replace its required full comparison. All four rule views and adverse results
are retained. Cell inclusion depends only on artifact availability, not outcomes.
"""
import argparse
from datetime import datetime, timezone
import importlib.util
from pathlib import Path
import time

from strategic_collection import ROOT, read, write, digest
from policy_iteration_development import PROTOCOL, SOURCE, verify_local

SPEC = importlib.util.spec_from_file_location('full_comparison', ROOT/'ai/strong/compare-policy-iteration-development.py')
full = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(full)


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    assert not args.output.exists()
    protocol = read(PROTOCOL)
    keys = protocol['models']
    assert set(keys) == {'parent', 'frozen-0', 'frozen-1', 'public-0', 'public-1'}
    plans = {key: full.grid.require_plan(key) for key in keys}
    cutoff = time.time()-2  # Exclude a verified.json that is currently being written.
    cells, coverage = [], {}
    for cell in protocol['screens']:
        name = cell['opponent']+'/'+str(cell['players'])+'p'
        missing = {}
        for key, plan in plans.items():
            rows = [r for r in plan['shards'] if r['players'] == cell['players'] and r['opponent'] == cell['opponent']]
            assert len(rows) == 4
            missing[key] = [r['case'] for r in rows if not (
                (full.grid.manager.VERIFIED/r['case']/'verified.json').exists()
                and (full.grid.manager.VERIFIED/r['case']/'verified.json').stat().st_mtime < cutoff)]
        coverage[name] = {'complete_in_all_arms': not any(missing.values()), 'missing_at_cutoff': missing}
        if coverage[name]['complete_in_all_arms']:
            cells.append(cell)
    assert cells and len(cells) < len(protocol['screens']), 'Use the full comparator once all cells are available'
    code = [Path(__file__), ROOT/'ai/strong/compare-policy-iteration-development.py',
            ROOT/'ai/strong/policy_iteration_development.py', ROOT/'ai/strong/compare-population-screens.py',
            ROOT/'ai/strong/arena_statistics.py', PROTOCOL, SOURCE]
    hashes = {str(p.relative_to(ROOT)): digest(p) for p in code}
    reports, provenance = {}, {}
    for key, plan in plans.items():
        reports[key], provenance[key] = {}, {}
        for cell in cells:
            name = cell['opponent']+'/'+str(cell['players'])+'p'
            merged = []
            for row in plan['shards']:
                if row['players'] != cell['players'] or row['opponent'] != cell['opponent']:
                    continue
                directory = full.grid.manager.VERIFIED/row['case']
                record = read(directory/'verified.json')
                guard = full.grid.matching_guard(full.grid.manager.GUARDS/(row['case']+'.json'), row, plan)
                assert record['verified'] and record['job_id'] == guard['job_id']
                assert record['source'] == plan['source'] and record['model_pin'] == plan['model_pin']
                assert record['model_pin_sha256'] == plan['model_pin_sha256']
                assert record['protocol_sha256'] == digest(PROTOCOL) and record['flavor'] == plan['flavor']
                for file, sha in record['artifacts'].items():
                    assert digest(directory/file) == sha
                actual = verify_local(directory, key, row['players'], row['opponent'], row['start'], row['end'],
                                      'development', plan['model_pin'], plan['source'])
                assert actual == record['summary']
                merged.extend(read(directory/'evaluation.json')['results'])
                provenance[key][row['case']] = {'job_id': record['job_id'], 'revision': record['revision'],
                    'prefix': record['prefix'], 'verified_sha256': digest(directory/'verified.json'),
                    'evaluation_sha256': digest(directory/'evaluation.json')}
            assert len(merged) == cell['games']
            assert {r['gameSeed'] for r in merged} == {protocol['seed_template'].format(players=cell['players'])+'-'+str(i)
                                                      for i in protocol['deal_offsets']}
            assert {r['episode'] for r in merged} == set(range(cell['games']))
            reports[key][name] = merged
        print({'arm': key, 'complete_cells_verified': len(cells)}, flush=True)
    comparisons = [(key, 'parent') for key in keys if key != 'parent']
    comparisons += [('public-0', 'frozen-0'), ('public-1', 'frozen-1'),
                    ('frozen-1', 'frozen-0'), ('public-1', 'public-0')]
    output = {'interim_diagnostic': True, 'full_comparison_complete': False,
        'candidate_selected': False, 'qualification_eligible': False, 'reserved_final_seeds_used': False,
        'cutoff_utc': datetime.fromtimestamp(cutoff, timezone.utc).isoformat(), 'coverage': coverage,
        'complete_cells': [c['opponent']+'/'+str(c['players'])+'p' for c in cells],
        'games_per_arm': sum(c['games'] for c in cells), 'games': len(keys)*sum(c['games'] for c in cells),
        'independent_deals_per_cell': 16, 'source': read(SOURCE), 'protocol_sha256': digest(PROTOCOL),
        'pins': {key: plan['model_pin'] for key, plan in plans.items()}, 'provenance': provenance,
        'code_hashes': hashes,
        'absolute': {key: {cell: full.absolute(rows, protocol) for cell, rows in reports[key].items()} for key in keys},
        'comparisons': {left+'-minus-'+right: {cell: full.contrast(rows, reports[right][cell], protocol)
            for cell, rows in reports[left].items()} for left, right in comparisons},
        'scope': 'Interim complete-cell diagnosis only. Inclusion requires all 16 deals, all seats and all '
            'four rule combinations in all five arms before inspecting outcomes. Every ready opponent/count '
            'cell and adverse rule view is retained. No aggregate grid score, ranking, candidate selection '
            'or replacement for the full comparison. Deal-bootstrap intervals are exploratory marginal '
            'intervals, not simultaneous guarantees, and repeated interim looks are not new independent tests.'}
    assert all(digest(ROOT/name) == sha for name, sha in hashes.items())
    write(args.output, output)
    print({'complete_cells': output['complete_cells'], 'games': output['games'], 'full_comparison_complete': False})


if __name__ == '__main__':
    main()
