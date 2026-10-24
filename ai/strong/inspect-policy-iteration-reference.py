"""Describe verified parent cells without treating a partial grid as qualification."""
import argparse
import importlib.util
from pathlib import Path

from strategic_collection import ROOT, read, write, digest
from policy_iteration_development import PROTOCOL, verify_local


def module(name, file):
    spec = importlib.util.spec_from_file_location(name, ROOT/'ai/strong'/file)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    assert not args.output.exists(), 'Preserve earlier diagnostics'
    grid = module('reference_grid', 'manage-policy-iteration-development-grid.py')
    compare = module('reference_comparison', 'compare-policy-iteration-development.py')
    plan, protocol = grid.require_plan('parent'), read(PROTOCOL)
    final_path = ROOT/'ai/strong/final-protocol-multiplayer.json'
    assert digest(final_path) == protocol['final_protocol_sha256']
    final = read(final_path)
    floors = {(op['name'],int(n)):value['minimum_win_rate'] for op in final['opponents'] for n,value in op['counts'].items()}
    groups, provenance, pending = {}, {}, []
    for row in plan['shards']:
        directory = grid.manager.VERIFIED/row['case']
        if not (directory/'verified.json').exists():
            pending.append(row['case'])
            continue
        record = read(directory/'verified.json')
        guard = grid.matching_guard(grid.manager.GUARDS/(row['case']+'.json'), row, plan)
        assert record['verified'] and record['job_id'] == guard['job_id']
        assert record['source'] == plan['source'] and record['model_pin'] == plan['model_pin']
        assert record['protocol_sha256'] == digest(PROTOCOL)
        for file, sha in record['artifacts'].items():
            assert digest(directory/file) == sha
        summary = verify_local(directory,'parent',row['players'],row['opponent'],row['start'],row['end'],
                               'development',plan['model_pin'],plan['source'])
        assert summary == record['summary']
        cell = row['opponent']+'/'+str(row['players'])+'p'
        groups.setdefault(cell,[]).extend(read(directory/'evaluation.json')['results'])
        provenance[row['case']] = {'job_id':record['job_id'],'revision':record['revision'],'prefix':record['prefix'],
                                  'verified_sha256':digest(directory/'verified.json')}
    complete, incomplete, deficits, uncertain_rules = {}, {}, [], []
    for screen in protocol['screens']:
        n,opponent = screen['players'],screen['opponent']
        cell = opponent+'/'+str(n)+'p';rows=groups.get(cell,[])
        if len(rows) != screen['games']:
            incomplete[cell] = {'verified_games':len(rows),'required_games':screen['games']}
            continue
        assert {r['episode'] for r in rows} == set(range(screen['games']))
        assert {r['gameSeed'] for r in rows} == {protocol['seed_template'].format(players=n)+'-'+str(i) for i in range(16)}
        summary = compare.absolute(rows,protocol)
        floor = floors.get(('frozen_a260' if opponent=='a260' else opponent,n))
        summary['chance'] = 1/n
        summary['final_point_floor_for_orientation_only'] = floor
        summary['development_point_below_final_floor'] = floor is not None and summary['overall']['win_rate'] < floor
        summary['overall_interval_excludes_chance'] = summary['overall']['deal_bootstrap_95_interval'][0] > 1/n
        if summary['development_point_below_final_floor']:
            deficits.append(cell)
        summary['rules_not_excluding_chance'] = [rule for rule,stats in summary['by_rules'].items()
                                                if stats['deal_bootstrap_95_interval'][0] <= 1/n]
        uncertain_rules += [cell+'/'+rule for rule in summary['rules_not_excluding_chance']]
        complete[cell] = summary
    report = {'complete_parent_reference':not pending,'planned_shards':108,'verified_shards':len(provenance),
              'planned_games':6720,'verified_games':sum(len(rows) for rows in groups.values()),
              'source':plan['source'],'parent_pin':plan['model_pin'],'protocol_sha256':digest(PROTOCOL),
              'final_protocol_sha256':digest(final_path),'provenance':provenance,
              'complete_cells':complete,'incomplete_cells':incomplete,'pending_verification':pending,
              'development_point_deficits':deficits,'rule_intervals_not_excluding_chance':uncertain_rules,
              'independent_deals_per_complete_cell':16,'qualification_eligible':False,'reserved_final_seeds_used':False,
              'scope':'Parent development diagnostic only. Summaries require all16 paired deals in a cell;incomplete cells remain listed without a strength summary. Final protocol floors are orientation only:final held-out deals and larger sample counts are unspent. Marginal intervals are exploratory,not simultaneous guarantees. No candidate comparison or promotion is possible from this report.'}
    assert report['verified_games'] <= report['planned_games']
    write(args.output,report)
    print({k:report[k] for k in ['complete_parent_reference','verified_shards','verified_games','development_point_deficits','rule_intervals_not_excluding_chance']})


if __name__ == '__main__':
    main()
