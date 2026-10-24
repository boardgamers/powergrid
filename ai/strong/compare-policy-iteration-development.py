"""Full fresh-game comparison of every prespecified ensemble, retaining adverse cells."""
import argparse
import importlib.util
from pathlib import Path

from strategic_collection import ROOT, read, write, digest
from policy_iteration_development import PROTOCOL, SOURCE, case_key, pin_hash, verify_local, summarize, pairs

SPEC = importlib.util.spec_from_file_location('grid_manager', ROOT/'ai/strong/manage-policy-iteration-development-grid.py')
grid = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(grid)


def load_arm(key):
    plan = grid.require_plan(key)
    protocol = read(PROTOCOL)
    reports, provenance = {}, {}
    for row in plan['shards']:
        directory = grid.manager.VERIFIED/row['case']
        record = read(directory/'verified.json')
        guard = grid.matching_guard(grid.manager.GUARDS/(row['case']+'.json'), row, plan)
        assert record['verified'] and record['job_id'] == guard['job_id']
        assert record['source'] == plan['source'] and record['model_pin'] == plan['model_pin']
        assert record['model_pin_sha256'] == plan['model_pin_sha256']
        assert record['protocol_sha256'] == digest(PROTOCOL) and record['flavor'] == plan['flavor']
        for file, sha in record['artifacts'].items():
            assert digest(directory/file) == sha
        actual = verify_local(directory, key, row['players'], row['opponent'], row['start'], row['end'],
                              'development', plan['model_pin'], plan['source'])
        assert actual == record['summary']
        cell = row['opponent']+'/'+str(row['players'])+'p'
        reports.setdefault(cell, []).extend(read(directory/'evaluation.json')['results'])
        provenance[row['case']] = {'job_id': record['job_id'], 'revision': record['revision'],
                                  'prefix': record['prefix'], 'verified_sha256': digest(directory/'verified.json')}
    assert len(provenance) == 108 and len(reports) == 27
    for cell in protocol['screens']:
        rows = reports[cell['opponent']+'/'+str(cell['players'])+'p']
        assert len(rows) == cell['games']
        assert {r['gameSeed'] for r in rows} == {protocol['seed_template'].format(players=cell['players'])+'-'+str(i)
                                               for i in protocol['deal_offsets']}
        assert {r['episode'] for r in rows} == set(range(cell['games']))
    assert sum(len(rows) for rows in reports.values()) == 6720
    return plan['model_pin'], reports, provenance


def rule_views(rows):
    return {v+('/sealed' if s else '/open'): [r for r in rows if r['variant'] == v and r['sealed'] == s]
            for v in ['original', 'recharged'] for s in [False, True]}


def absolute(rows, protocol):
    return {'overall': summarize(rows, protocol),
            'by_rules': {rule: summarize(selected, protocol) for rule, selected in rule_views(rows).items()}}


def contrast(left, right, protocol):
    def difference(a, b):
        return pairs.paired_difference(a, b, repeats=protocol['bootstrap_replicates'], seed=protocol['bootstrap_seed'])
    a, b = rule_views(left), rule_views(right)
    return {'overall': difference(left, right), 'by_rules': {rule: difference(a[rule], b[rule]) for rule in a}}


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--arm', choices=['parent', 'frozen-0', 'frozen-1', 'public-0', 'public-1'],
                        help='A complete arm summary only; full comparison requires all five arms')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    protocol = read(PROTOCOL)
    keys = [args.arm] if args.arm else protocol['models']
    pins, reports, records = {}, {}, {}
    for key in keys:
        pins[key], reports[key], records[key] = load_arm(key)
    output = {'complete_arm_summaries': keys, 'full_comparison_complete': not args.arm,
              'source': read(SOURCE), 'protocol_sha256': digest(PROTOCOL), 'pins': pins,
              'games': 6720*len(keys), 'independent_deals_per_cell': 16, 'provenance': records,
              'absolute': {key: {cell: absolute(rows, protocol) for cell, rows in reports[key].items()} for key in keys},
              'comparisons': {}, 'qualification_eligible': False, 'reserved_final_seeds_used': False,
              'scope': 'Fresh development only. Whole deals are bootstrap units. Intervals are exploratory marginal intervals, not simultaneous guarantees. All prescribed ensembles and adverse rule/count/opponent cells are retained.'}
    if not args.arm:
        comparisons = [(key, 'parent') for key in keys if key != 'parent']
        comparisons += [('public-0', 'frozen-0'), ('public-1', 'frozen-1'),
                        ('frozen-1', 'frozen-0'), ('public-1', 'public-0')]
        for left, right in comparisons:
            output['comparisons'][left+'-minus-'+right] = {
                cell: contrast(rows, reports[right][cell], protocol) for cell, rows in reports[left].items()}
        assert len(output['comparisons']) == 8 and output['games'] == protocol['planned_games_total'] == 33600
    assert not args.output.exists(), 'Keep previous comparisons intact; choose a new output path'
    write(args.output, output)
    print({'games': output['games'], 'full_comparison_complete': output['full_comparison_complete'],
           'comparisons': len(output['comparisons']), 'qualification_eligible': False})


if __name__ == '__main__':
    main()
