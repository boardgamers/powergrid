"""Describe the completed model-only grid and freeze two bounded replay pairs.

All models/cells/rules are retained. Terminal categories are descriptive and can
overlap; the two outcome-selected replay pairs are not a new strength estimate.
"""
import argparse
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np
from strategic_collection import ROOT, read, write, digest
from policy_iteration_development import PROTOCOL, SOURCE


def module(name, file):
    spec = importlib.util.spec_from_file_location(name,ROOT/'ai/strong'/file)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


full = module('complete_model_comparison','compare-policy-iteration-development.py')
terminal = module('terminal_metrics','analyze-search-transfer-outcomes.py')


def identity(row):
    return row['gameSeed'],row['seat'],row['variant'],row['sealed']


def failures(rows):
    counts = Counter(losses=0,sole_wins=0,shared_wins=0,capacity_below_winner_powered=0,
        cities_below_winner_powered=0,unused_nominal_potential=0,powered_tie_cash_loss=0,
        powered_cash_tie_city_loss=0)
    for row in rows:
        players,seat = row['final']['players'],row['seat']
        best = max((p['powered'],p['money'],p['cities']) for p in players)
        winners = [i for i,p in enumerate(players) if (p['powered'],p['money'],p['cities']) == best]
        assert row['win'] == (1/len(winners) if seat in winners else 0)
        if row['win']:
            counts['sole_wins' if row['win'] == 1 else 'shared_wins'] += 1
            continue
        counts['losses'] += 1
        me = players[seat]
        counts['capacity_below_winner_powered'] += me['capacity'] < best[0]
        counts['cities_below_winner_powered'] += me['cities'] < best[0]
        counts['unused_nominal_potential'] += min(me['capacity'],me['cities']) > me['powered']
        counts['powered_tie_cash_loss'] += me['powered'] == best[0] and me['money'] < best[1]
        counts['powered_cash_tie_city_loss'] += (me['powered'],me['money']) == best[:2] and me['cities'] < best[2]
    return dict(counts)


def describe(rows):
    return {'games':len(rows),'win_share':sum(r['win'] for r in rows)/len(rows),
        'failures':failures(rows),'means':{name:float(np.mean([terminal.metrics(r)[name] for r in rows]))
            for name in terminal.metrics(rows[0])},
        'mean_move_counts':{name:float(np.mean([r['policyMoves'].get(name,0) for r in rows]))
            for name in sorted(set().union(*(r['policyMoves'] for r in rows)))}}


def main(output):
    frozen_path = ROOT/'ai/strong/policy-iteration-development-comparison-v2.json'
    frozen = read(frozen_path)
    assert digest(frozen_path) == 'b85e900c30b70d523d8e2beb4e8ecf9f3bdb1a03c14924b0041ec45b3c422cb2'
    assert frozen['full_comparison_complete'] and frozen['games'] == 33600
    assert frozen['source'] == read(SOURCE) and frozen['protocol_sha256'] == digest(PROTOCOL)
    assert not output.exists()
    output.mkdir(parents=True)
    protocol = read(PROTOCOL)
    raw,absolute,contrasts = {},{},{}
    for key in protocol['models']:
        pin,rows,provenance = full.load_arm(key)
        assert pin == frozen['pins'][key] and provenance == frozen['provenance'][key]
        raw[key] = rows
        absolute[key] = {}
        for cell,games in rows.items():
            views = {'overall':games,**full.rule_views(games)}
            absolute[key][cell] = {name:describe(part) for name,part in views.items()}
            for name,part in views.items():
                expected = frozen['absolute'][key][cell]['overall'] if name == 'overall' else frozen['absolute'][key][cell]['by_rules'][name]
                assert abs(absolute[key][cell][name]['win_share']-expected['win_rate']) < 1e-12
        print({'verified_model':key,'games':sum(map(len,rows.values()))},flush=True)
    for key in protocol['models']:
        if key == 'parent':
            continue
        contrasts[key] = {}
        for cell,rows in raw[key].items():
            left = {'overall':rows,**full.rule_views(rows)}
            right = {'overall':raw['parent'][cell],**full.rule_views(raw['parent'][cell])}
            contrasts[key][cell] = {}
            for name in left:
                result = terminal.paired_changes(left[name],right[name],protocol)
                result['candidate_failures'] = failures(left[name])
                result['parent_failures'] = failures(right[name])
                result.pop('raw_failures');result.pop('search_failures')
                for metric in result['terminal_changes'].values():
                    metric['mean_candidate_minus_parent'] = metric.pop('mean_search_minus_raw')
                expected = frozen['comparisons'][key+'-minus-parent'][cell]
                expected = expected['overall'] if name == 'overall' else expected['by_rules'][name]
                assert abs(result['terminal_changes']['win_credit']['mean_candidate_minus_parent']-expected['win_share_difference']) < 1e-12
                contrasts[key][cell][name] = result
    assessment = {'comparison_sha256':digest(frozen_path),'games':33600,'models':protocol['models'],
        'cells':27,'independent_deals_per_cell':16,'absolute':absolute,'contrasts':contrasts,
        'source':frozen['source'],'pins':frozen['pins'],'code_hashes':{str(p.relative_to(ROOT)):digest(p)
            for p in [Path(__file__),ROOT/'ai/strong/analyze-search-transfer-outcomes.py',
                ROOT/'ai/strong/compare-policy-iteration-development.py']},
        'new_games':0,'gradients':False,'candidate_selected':False,'qualification_eligible':False,
        'reserved_final_seeds_used':False,
        'scope':'Complete, already verified model-only grid. All five models, 27 cells and four rule views retained. Terminal deficits and overlapping failure counts do not identify causal decisions. Whole-deal marginal bootstrap intervals are exploratory, without multiplicity correction. This is not a new strength evaluation.'}
    write(output/'assessment.json',assessment)
    requested,pairs = {},[]
    specifications = [
        ('2p-recharged-open-unused', 'search_geo/2p','recharged/open',
         lambda me,win: min(me['cities'],me['capacity']) > me['powered']),
        ('6p-recharged-sealed-city-limited', 'search_geo/6p','recharged/sealed',
         lambda me,win: me['cities'] < win[0] <= me['capacity']),
    ]
    for label,cell,rule,condition in specifications:
        rows = full.rule_views(raw['frozen-1'][cell])[rule]
        candidates = []
        for row in rows:
            me = row['final']['players'][row['seat']]
            winner = max((p['powered'],p['money'],p['cities']) for p in row['final']['players'])
            if row['win'] == 0 and condition(me,winner):
                candidates.append(row)
        rank = lambda r: hashlib.sha256(json.dumps(['weak-cell-economy-v1',*identity(r)],separators=(',',':')).encode()).hexdigest()
        chosen = min(candidates,key=rank)
        pair = {}
        for key in ['parent','frozen-1']:
            expected = next(r for r in raw[key][cell] if identity(r) == identity(chosen))
            name = key+'-'+label+'-episode-'+str(expected['episode'])
            requested[name] = {'model':key,'expected':expected,'opponent':'search_geo'}
            pair[key] = name
        pairs.append({'label':label,'cell':cell,'rule':rule,'eligible_examples':len(candidates),
            'selection_hash':rank(chosen),'cases':pair})
    assert len(requested) == 4
    write(output/'selection.json',{'assessment_sha256':digest(output/'assessment.json'),
        'source':frozen['source'],'pins':{k:frozen['pins'][k] for k in ['parent','frozen-1']},
        'pairs':pairs,'requested':requested,'selector_sha256':digest(__file__),
        'selection':'One hash-ranked current-model loss from each of two explicit descriptive cohorts; replay the matched parent too. Four diagnostic games, outcome-selected, not strength estimates or training labels.',
        'qualification_eligible':False,'reserved_final_seeds_used':False})
    print({'complete_games_described':33600,'bounded_replays_selected':len(requested),'pairs':pairs},flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--output',type=Path,required=True)
    main(parser.parse_args().output.resolve())
