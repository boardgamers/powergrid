"""Independently check the descriptive counts and fixed resource intervention."""
import itertools
import json
from pathlib import Path
import shutil

from strategic_collection import ROOT,read,write,digest
from policy_iteration_evidence_archive import upload_evidence


def fuel_capacity(player):
    best = 0
    plants = player['plants']
    for use in itertools.product([False,True],repeat=len(plants)):
        selected = [p for p,on in zip(plants,use) if on]
        need = [sum(p['cost'] for p in selected if p['type'] == resource) for resource in range(5)]
        stock = [player['resources'][r] for r in ['coal','oil','garbage','uranium']]
        if all(stock[r] >= need[r] for r in range(4)) and stock[0]+stock[1]-need[0]-need[1] >= need[4]:
            best = max(best,sum(p['capacity'] for p in selected))
    return best


def main():
    full_root = ROOT/'ai/runs/complete-policy-economy-v1'
    replays = ROOT/'ai/runs/weak-cell-economy-replays-v1'
    counter = ROOT/'ai/runs/weak-cell-resource-counterfactual-v1'
    full = read(full_root/'assessment.json')
    original = read(ROOT/'ai/strong/policy-iteration-development-comparison-v2.json')
    assert full['comparison_sha256'] == digest(ROOT/'ai/strong/policy-iteration-development-comparison-v2.json')
    assert full['games'] == 33600 and full['cells'] == 27
    for name,sha in full['code_hashes'].items():assert digest(ROOT/name) == sha
    # Independently derive all absolute count views directly from the pinned raw reports.
    checked_games = 0
    for key,proofs in original['provenance'].items():
        cells = {}
        for case,proof in proofs.items():
            folder = ROOT/'ai/runs/policy-iteration-development-verified-v2'/case
            assert digest(folder/'verified.json') == proof['verified_sha256']
            receipt = read(folder/'verified.json')
            assert digest(folder/'evaluation.json') == receipt['artifacts']['evaluation.json']
            for row in read(folder/'evaluation.json')['results']:
                opponent = next(role for role in row['roles'] if role != 'learner')
                if opponent == 'snapshot0':
                    assert '-a260-' in case
                    opponent = 'a260'
                cell = opponent+'/'+str(row['playerCount'])+'p'
                cells.setdefault(cell,[]).append(row)
        assert len(cells) == 27
        for cell,rows in cells.items():
            checked_games += len(rows)
            for view,saved in full['absolute'][key][cell].items():
                chosen = rows if view == 'overall' else [r for r in rows if view == r['variant']+('/sealed' if r['sealed'] else '/open')]
                assert saved['games'] == len(chosen)
                assert abs(saved['win_share']-sum(r['win'] for r in chosen)/len(chosen)) < 1e-12
                losses = [r for r in chosen if r['win'] == 0]
                assert saved['failures']['losses'] == len(losses)
                city,capacity,unused = 0,0,0
                for row in losses:
                    me = row['final']['players'][row['seat']]
                    winner_powered = max(p['powered'] for p in row['final']['players'])
                    city += me['cities'] < winner_powered
                    capacity += me['capacity'] < winner_powered
                    unused += min(me['cities'],me['capacity']) > me['powered']
                assert saved['failures']['cities_below_winner_powered'] == city
                assert saved['failures']['capacity_below_winner_powered'] == capacity
                assert saved['failures']['unused_nominal_potential'] == unused
    assert checked_games == 33600
    replay = read(replays/'assessment.json')
    diagnosis_path = ROOT/'ai/runs/weak-cell-economy-analysis-v1.json'
    diagnosis = read(diagnosis_path)
    assert diagnosis['assessment_sha256'] == digest(replays/'assessment.json')
    assert diagnosis['analysis_sha256'] == digest(ROOT/'ai/strong/analyze-weak-cell-replays-v1.py')
    for name,result in replay['results'].items():
        assert result['exact_terminal_replay'] and result['completed']
        assert digest(replays/(name+'.jsonl')) == result['trace_sha256']
    intervention = read(counter/'assessment.json')
    protocol = read(ROOT/'ai/strong/weak-cell-resource-counterfactual-v1.json')
    assert intervention['protocol_sha256'] == digest(ROOT/'ai/strong/weak-cell-resource-counterfactual-v1.json')
    assert intervention['branches_sha256'] == digest(counter/'branches.json')
    for name,sha in intervention['code_hashes'].items():assert digest(ROOT/name) == sha
    reference = [json.loads(line) for line in (replays/(protocol['case']+'.jsonl')).open()]
    seat,index = protocol['target']['seat'],protocol['root_index']
    branches = read(counter/'branches.json')
    outcomes = {}
    for branch in branches:
        trace_path = counter/(branch['branch']+'.jsonl')
        assert digest(trace_path) == branch['trace_sha256']
        trace = [json.loads(line) for line in trace_path.open()]
        assert trace[:index] == reference[:index]
        assert trace[index]['before'] == reference[index]['before']
        assert all(a['after'] == b['before'] for a,b in zip(trace,trace[1:]))
        if branch['branch'] == 'original':
            assert digest(trace_path) == digest(replays/(protocol['case']+'.jsonl'))
        else:
            paid = []
            for row in trace[index:index+3]:
                assert row['seat'] == seat and row['action'] == {'name':'BuyResource','data':{'resource':'coal'}}
                before,after = row['before'],row['after']
                me,next_me = before['players'][seat],after['players'][seat]
                market = before['market']['coal']
                cost = market['prices'][len(market['prices'])-market['count']]
                assert me['money']-next_me['money'] == cost
                assert next_me['resources']['coal'] == me['resources']['coal']+1
                assert after['market']['coal']['count'] == market['count']-1
                paid.append(cost)
            assert paid == [5,6,6]
            assert fuel_capacity(trace[index]['before']['players'][seat]) == 18
            assert fuel_capacity(trace[index+2]['after']['players'][seat]) == 24
            assert trace[index+3]['action'] == {'name':'Pass','data':True}
        final = trace[-1]['after']
        ranks = [(p['powered'],p['money'],len(p['cities'])) for p in final['players']]
        winners = [i for i,value in enumerate(ranks) if value == max(ranks)]
        win = 1/len(winners) if seat in winners else 0
        assert branch['win'] == win == branch['result']['value'][seat]
        outcomes[branch['branch']] = {'win':win,'ranks':ranks}
    assert outcomes['original']['win'] == 0 and outcomes['buy_coal_3']['win'] == 1
    evidence = ROOT/'ai/runs/weak-cell-economy-evidence-v1'
    assert not evidence.exists();evidence.mkdir()
    sources = [p for folder in [full_root,replays,counter] for p in folder.rglob('*')
        if p.is_file() and 'runtime' not in p.relative_to(folder).parts]
    sources += [diagnosis_path,ROOT/'ai/runs/complete-policy-economy-v1.log',
        ROOT/'ai/runs/weak-cell-economy-replays-v1.log',ROOT/'ai/runs/weak-cell-economy-analysis-v1.log',
        ROOT/'ai/runs/weak-cell-resource-counterfactual-v1.log']
    sources += [ROOT/'ai/strong'/name for name in [
        'analyze-complete-policy-economy-v1.py','replay-weak-cell-economy-v1.py',
        'analyze-weak-cell-replays-v1.py','intervene-resource-bundle-v1.cjs','replay-resource-bundle-v1.py',
        'weak-cell-resource-counterfactual-v1.json','collect-weak-cell-economy-v1.py',
        'trace-public-economy.cjs','analyze-policy-iteration-economy.py','analyze-search-transfer-outcomes.py',
        'compare-policy-iteration-development.py','policy_iteration_evidence_archive.py',
        'policy-iteration-development-complete-evidence-v2.json','policy-iteration-development-source-v2.json',
        'policy-iteration-development-protocol-v2.json','policy-iteration-development-comparison-v2.json']]
    for source in sources:
        destination = evidence/source.relative_to(ROOT);destination.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(source,destination)
    summary = {'complete_grid_games_described':33600,'all_models':5,'all_cells':27,
        'independent_deals_per_cell':16,'independently_recomputed_absolute_views':True,
        'exact_diagnostic_replays':4,'continuous_root_moves':sum(r['moves_logged'] for r in replay['results'].values()),
        'two_player_recharged_open':full['absolute']['frozen-1']['search_geo/2p']['recharged/open'],
        'six_player_recharged_sealed':full['absolute']['frozen-1']['search_geo/6p']['recharged/sealed'],
        'counterfactual':{'cases':1,'branches':2,'original_full_trace_identical':True,
            'prefix_moves_identical':326,'bundle':'Three legal coal purchases before the selected resource Pass',
            'cost':17,'fuel_supported_before':18,'fuel_supported_after':24,'outcomes':outcomes,'caps':0},
        'six_player_selected_pair_entire_public_trace_identical':next(p['entire_public_traces_identical']
            for p in diagnosis['pairs'] if p['cell'] == 'search_geo/6p'),
        'interpretation':'An available-fuel purchasing omission causally changes the selected two-player loss into a win. The selected six-player loss is an unchanged parent/current trajectory with insufficient cities; it is not evidence of a new regression.',
        'next_action':'Keep the five-arm hybrid screen frozen. Check resource planning and capacity/city growth jointly in future development; do not infer a general resource-buying rule or strength gain from one selected branch.',
        'new_strength_games':0,'new_hf_jobs':0,'gradients':False,'qualification_eligible':False,'reserved_final_seeds_used':False,
        'limits':'Counts describe reused development games; categories overlap. Marginal paired intervals are exploratory. Replays and the conditional intervention are outcome-selected and reuse the actual future, so they are not fresh strength estimates, teacher targets, deployment values or causal attribution for the whole weak cell.'}
    write(evidence/'assessment.json',summary)
    write(evidence/'manifest.json',{str(p.relative_to(evidence)):digest(p) for p in evidence.rglob('*') if p.is_file()})
    receipt = upload_evidence(evidence)
    write(ROOT/'ai/strong/weak-cell-economy-evidence-v1.json',{**summary,**receipt})
    print(json.dumps({**receipt,'counterfactual':summary['counterfactual']},indent=2))


if __name__ == '__main__':
    main()
