"""Check complete public ledgers and describe the two fixed weak-cell examples."""
import argparse
from collections import Counter
import importlib.util
import json
from pathlib import Path

from strategic_collection import ROOT,read,write,digest

spec = importlib.util.spec_from_file_location('economy_metrics',ROOT/'ai/strong/analyze-policy-iteration-economy.py')
economy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(economy)


def main(directory,output):
    assert not output.exists()
    assessment = read(directory/'assessment.json')
    assert assessment['replays'] == 4 and assessment['all_terminal_replays_match'] and assessment['all_root_moves_logged']
    assert digest(directory/'selection.json') == assessment['selection_sha256']
    assert digest(directory/'runtime-provenance.json') == assessment['runtime_provenance_sha256']
    selection = read(directory/'selection.json')
    games = {}
    for name,request in selection['requested'].items():
        expected = request['expected'];seat = expected['seat']
        result = assessment['results'][name]
        trace_path = directory/(name+'.jsonl')
        assert digest(trace_path) == result['trace_sha256']
        trace = [json.loads(line) for line in trace_path.open()]
        assert len(trace) == expected['steps'] == result['moves_logged']
        assert all(a['after'] == b['before'] for a,b in zip(trace,trace[1:]))
        assert Counter(row['action']['name'] for row in trace if row['seat'] == seat) == expected['policyMoves']
        assert not any(row['legacy'] for row in trace),'This fixed opponent is search, not legacy'
        last = trace[-1]['after']
        assert last['phase'] == 'Game End' and last['round'] == expected['final']['round']
        for actual,saved in zip(last['players'],expected['final']['players']):
            assert {k:actual[k] for k in ['money','powered','capacity']} == {k:saved[k] for k in ['money','powered','capacity']}
            assert len(actual['cities']) == saved['cities']
            assert [p['number'] for p in actual['plants']] == saved['plants']
            assert actual['powerable'] == actual['powered']
        phases = {}
        for index,row in enumerate(trace):
            if row['seat'] != seat:
                continue
            round_number,phase = str(row['before']['round']),row['before']['phase']
            target = phases.setdefault(round_number,{}).setdefault(phase,{'actions':[],'first_root':index,
                'before_first':row['before']['players'][seat]})
            target['actions'].append(row['action'])
            target['last_root'] = index
            target['after_last'] = row['after']['players'][seat]
            target['market_after_last'] = row['after']['market']
        resources = phases[str(last['round'])]['Resources']
        assert resources['actions'][-1] == {'name':'Pass','data':True}
        trigger = [(i,row) for i,row in enumerate(trace)
            if max(len(p['cities']) for p in row['before']['players']) < row['before']['citiesToEndGame']
                <= max(len(p['cities']) for p in row['after']['players'])]
        assert len(trigger) == 1
        index,row = trigger[0]
        me = last['players'][seat]
        games[name] = {'model':request['model'],'episode':expected['episode'],'seat':seat,
            'win':expected['win'],'final_round':last['round'],'final_player':me,
            'final_opponents':[p for i,p in enumerate(last['players']) if i != seat],
            'trace_sha256':digest(trace_path),'root_moves':len(trace),'rounds':phases,
            'last_resources':resources,
            'fuel_supported_capacity_after_resource_turn':resources['after_last']['fuelSupportedCapacity'],
            'unused_nominal_output':max(0,min(len(me['cities']),me['capacity'])-me['powered']),
            'individually_impossible_plants_even_ignoring_cost':economy.blocked_plants(
                resources['after_last'],resources['market_after_last']),
            'first_end_threshold':{'root_index':index,'seat':row['seat'],'learner':row['seat'] == seat,
                'action':row['action'],'before':row['before'],'after':row['after']}}
    pairs = []
    for pair in selection['pairs']:
        a,b = [games[pair['cases'][key]] for key in ['parent','frozen-1']]
        pairs.append({**pair,'entire_public_traces_identical':a['trace_sha256'] == b['trace_sha256'],
            'terminal':{key:{'win':games[name]['win'],'cities':len(games[name]['final_player']['cities']),
                'powered':games[name]['final_player']['powered'],'capacity':games[name]['final_player']['capacity'],
                'money':games[name]['final_player']['money'],
                'fuel_at_last_resources':games[name]['fuel_supported_capacity_after_resource_turn']}
                for key,name in pair['cases'].items()}})
    write(output,{'games':games,'pairs':pairs,'replays':4,'all_root_moves_and_state_transitions_verified':True,
        'assessment_sha256':digest(directory/'assessment.json'),'selection_sha256':digest(directory/'selection.json'),
        'analysis_sha256':digest(__file__),'helper_sha256':digest(ROOT/'ai/strong/analyze-policy-iteration-economy.py'),
        'source':selection['source'],'new_strength_games':0,'gradients':False,
        'qualification_eligible':False,'reserved_final_seeds_used':False,
        'scope':'Four outcome-selected diagnostic replays. Full public ledger continuity and terminal states verified. Fuel fields use the pinned engine function. Individual plant infeasibility ignores price/storage and is not a joint-fuel affordability solver. Phase snapshots describe decisions, not causal importance or generalized prevalence.'})
    print(json.dumps({'replays':4,'pairs':pairs},indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--directory',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    main(args.directory.resolve(),args.output.resolve())
