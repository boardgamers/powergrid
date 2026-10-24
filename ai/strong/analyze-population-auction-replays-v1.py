"""Describe verified saved-policy replays; no policy selection or intervention."""
from collections import Counter
import gzip
import json
from pathlib import Path

from strategic_collection import ROOT, read, write, digest

BASE = ROOT / 'ai/runs/population-auction-regression-replays-v1'


def analyze():
    assessment, selection = read(BASE / 'assessment.json'), read(BASE / 'selection.json')
    assert assessment['all_terminal_replays_match'] and assessment['replays'] == 14
    assert assessment['selection_sha256'] == digest(BASE / 'selection.json')
    cases, requests, decisions = {}, {}, {}
    for key, entry in selection['requested'].items():
        folder = BASE / key
        proof = assessment['results'][key]
        assert proof == read(folder / 'result.json') and proof['completed']
        assert digest(folder / 'economy.jsonl') == proof['trace_sha256']
        assert digest(folder / 'public-roots.jsonl.gz') == proof['public_roots_sha256']
        assert digest(folder / 'decisions.jsonl') == entry['reference']['decision_receipt_sha256']
        with gzip.open(folder / 'public-roots.jsonl.gz', 'rt') as handle:
            roots = [json.loads(line) for line in handle]
        moves = [json.loads(line) for line in (folder / 'decisions.jsonl').read_text().splitlines()]
        trace = [json.loads(line) for line in (folder / 'economy.jsonl').read_text().splitlines()]
        assert len(roots) == len(moves) == proof['learner_decisions']
        assert len(trace) == proof['moves_logged']
        requests[key], decisions[key] = roots, moves
        seat = entry['reference']['terminal']['seat']
        plant_purchases, round_end, changes = [], {}, []
        aggression = Counter()
        for root, move in zip(roots, moves):
            assert root['decision'] == move['decision']
            search = move['search']
            if not search or move['index'] == move['modelProposal']:
                continue
            assert not move['filterApplied']
            chosen, baseline = str(move['index']), str(move['modelProposal'])
            proposed = root['moves'][move['modelProposal']]
            category = 'other'
            if move['move']['name'] == 'Bid':
                if proposed['name'] == 'Bid':
                    category = 'bid_higher' if move['move']['data'] > proposed['data'] else 'bid_lower'
                elif proposed['name'] == 'Pass':
                    category = 'bid_instead_of_pass'
            elif move['move']['name'] == 'Pass' and proposed['name'] == 'Bid':
                category = 'pass_instead_of_bid'
            elif move['move']['name'] == 'ChoosePowerPlant':
                category = 'nominate_instead_of_pass' if proposed['name'] == 'Pass' else 'different_plant'
            elif move['move']['name'] == 'Pass' and proposed['name'] == 'ChoosePowerPlant':
                category = 'pass_instead_of_nominate'
            aggression[category] += 1
            deltas = [a-b for a, b in zip(search['sampleOutcomes'][chosen], search['sampleOutcomes'][baseline])]
            changes.append({'decision': move['decision'], 'round': move['round'], 'category': category,
                            'chosen': move['move'], 'model': proposed,
                            'mean_credit_margin': search['meanCredits'][chosen]-search['meanCredits'][baseline],
                            'better_worlds': sum(v > 0 for v in deltas),
                            'worse_worlds': sum(v < 0 for v in deltas),
                            'equal_worlds': sum(v == 0 for v in deltas)})
        for index, move in enumerate(trace):
            before, after = move['before']['players'][seat], move['after']['players'][seat]
            spent = after['totalSpentPlants'] - before['totalSpentPlants']
            if spent:
                assert spent > 0
                old = {p['number'] for p in before['plants']}
                plant_purchases.append({'root_move': index + 1, 'round': move['before']['round'],
                                        'price': spent, 'cash_before_resolution': before['money'],
                                        'cash_after_resolution': after['money'],
                                        'new_plants': [p for p in after['plants'] if p['number'] not in old]})
            r = str(move['before']['round'])
            round_end[r] = {'after_phase': move['after']['phase'], 'next_round': move['after']['round'],
                            'focal': after, 'opponents': [p for i,p in enumerate(move['after']['players']) if i != seat]}
        terminal = entry['reference']['terminal']
        cases[key] = {'win': terminal['win'], 'final_round': terminal['final']['round'],
                      'focal_final': terminal['final']['players'][seat],
                      'final_economy': trace[-1]['after']['players'][seat],
                      'plant_purchases': plant_purchases, 'round_end': round_end,
                      'search_changes': changes, 'change_categories': dict(aggression),
                      'observed_trace_sha256': proof['trace_sha256']}
    pairs = []
    for pair in selection['pairs']:
        left, right = pair['cases']
        shared = 0
        first = None
        for lroot, rroot, lmove, rmove in zip(requests[left], requests[right], decisions[left], decisions[right]):
            assert lroot['request'] == rroot['request'] and lroot['moves'] == rroot['moves']
            assert lroot['modelProposal'] == rroot['modelProposal']
            if lmove['move'] != rmove['move']:
                assert lmove['decision'] == rmove['decision']
                assert rmove['search'] and not rmove['filterApplied']
                assert lmove['index'] == rmove['modelProposal']
                first = {'decision': lmove['decision'], 'round': lmove['round'],
                         'filter': lmove['move'], 'auction': rmove['move'],
                         'auction_search': rmove['search'],
                         'public_root': rroot, 'shared_state_verified': True}
                break
            shared += 1
        assert first is not None
        pairs.append({**pair, 'identical_prior_learner_decisions': shared, 'first_divergence': first,
                      'terminal_difference': cases[right]['win'] - cases[left]['win']})
    output = {'assessment_sha256': digest(BASE / 'assessment.json'),
              'selection_sha256': digest(BASE / 'selection.json'), 'analyzer_sha256': digest(__file__),
              'cases': cases, 'pairs': pairs,
              'limitations': [
                  'Outcome-selected examples from the exploratory screen, not a strength estimate.',
                  'All subsequent learner decisions follow the original saved policy trajectory; the terminal difference is not the causal effect of the first differing move.',
                  'World credits and action margins are simulated scores, not calibrated win probabilities.',
                  'Traces include actual opponent moves for diagnosis; policy roots are separately verified public observations with hidden bids/deck removed.',
              ], 'new_hf_jobs': 0, 'new_strength_games': 0, 'gradients': False,
              'qualification_eligible': False, 'reserved_final_seeds_used': False}
    assert not (BASE / 'analysis.json').exists()
    write(BASE / 'analysis.json', output)
    compact = []
    for pair in pairs:
        first = pair['first_divergence']
        compact.append({'pair': pair['label'], 'first_round': first['round'],
                        'first_decision': first['decision'], 'filter': first['filter'], 'auction': first['auction'],
                        'sides': {key: {field: cases[key][field] for field in
                                       ['win', 'final_round', 'focal_final', 'change_categories', 'plant_purchases']}
                                  for key in pair['cases']}})
    print(json.dumps(compact, indent=2))


if __name__ == '__main__':
    analyze()
