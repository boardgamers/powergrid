"""Describe every sealed bid in the audited parent screen; never simulate or fit."""
from collections import defaultdict
import json
from pathlib import Path
import re
import statistics

from run_nomination_minipc_v1 import read, save, digest, now

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'ai/strong/sealed-decision-diagnostic-v1.json'


def resolution(bids, minimum, nominator, players):
    """Engine's second-price rule, with cyclic seat priority from the nominator."""
    positive = {p: b for p, b in bids.items() if b > 0}
    assert positive
    priority = lambda p: (p - nominator) % players
    winner = min(positive, key=lambda p: (-positive[p], priority(p)))
    others = {p: b for p, b in positive.items() if p != winner}
    if not others:
        return winner, minimum
    runner = min(others, key=lambda p: (-others[p], priority(p)))
    return winner, others[runner] + int(priority(runner) < priority(winner))


def describe(rows):
    bids = [r for r in rows if r['bid'] > 0]
    won = [r for r in rows if r['won']]
    lost = [r for r in bids if not r['won']]
    voluntary = [r for r in rows if not r['bid'] and r['can_bid']]
    return {'decisions': len(rows), 'bids': len(bids), 'wins': len(won),
        'forced_passes': sum(not r['can_bid'] for r in rows), 'voluntary_passes': len(voluntary),
        'won_below_submitted_bid': sum(r['price'] < r['bid'] for r in won),
        'median_bid_minus_price_on_wins': statistics.median([r['bid']-r['price'] for r in won]) if won else None,
        'wins_leave_under_10_cash': sum(r['cash']-r['price'] < 10 for r in won),
        'losses_despite_bid_at_cash_limit': sum(r['bid'] == r['cash'] for r in lost),
        'lost_bids_with_nominal_capacity_shortfall': sum(r['capacity'] < r['cities'] for r in lost),
        'voluntary_passes_with_nominal_capacity_shortfall': sum(r['capacity'] < r['cities'] for r in voluntary),
        'max_bid_roots': sum(r['bid'] == r['cash'] for r in bids),
        'bid_menu_omits_legal_values': sum(r['menu_bids'] < r['legal_bids'] for r in rows)}


def main():
    assert not OUT.exists(), 'Preserve the original diagnostic'
    proof_paths = {2: ROOT/'ai/strong/nomination-discount-two-player-results-v1.json',
        4: ROOT/'ai/strong/nomination-discount-4p-search-geo-results-v1.json',
        6: ROOT/'ai/strong/nomination-discount-6p-search-geo-results-v1.json'}
    groups = defaultdict(list); cases = []; games = []; proofs = {}
    for n, proof_path in proof_paths.items():
        comparison = read(proof_path); proof = comparison['proofs']['parent']
        assert comparison['complete'] and not comparison['reserved_final_seeds_used']
        audit_path = ROOT/proof['audit_path']; assert digest(audit_path) == proof['audit_sha256']
        audit = read(audit_path); assert audit['independently_audited'] and audit['caps'] == 0
        folder = (ROOT/'ai/runs/nomination-discount-minipc-v1/collected/pg-nom-dev-v1-parent-search-geo-2p'
                  if n == 2 else audit_path.parent/'raw')
        assert digest(folder/'manifest.json') == proof['raw_manifest_sha256']
        manifest = read(folder/'manifest.json'); evaluation_path = folder/'evaluation/evaluation.json'
        assert digest(evaluation_path) == manifest['evaluation/evaluation.json']
        evaluation = read(evaluation_path); assert evaluation['all_complete'] and evaluation['passed']
        proofs[str(n)] = {'comparison_sha256': digest(proof_path), 'raw_manifest_sha256': digest(folder/'manifest.json')}
        for result in evaluation['results']:
            terminal = result['terminal']
            if not terminal['sealed']:
                continue
            episode = result['episode']; path = folder/f'evaluation/decisions-{episode}.jsonl'
            assert digest(path) == result['decision_receipt_sha256'] == manifest[f'evaluation/decisions-{episode}.jsonl']
            with path.open() as stream:
                decisions = [json.loads(line) for line in stream]
            assert len(decisions) == result['decisions']
            game_cases = []
            for i, d in enumerate(decisions):
                q = d['publicRequest']; g = q['state']; seat = q['player']
                if not g.get('chosenPowerPlant') or d['move']['name'] not in ('Bid', 'Pass'):
                    continue
                assert g['options']['fastBid'] and g['options']['showMoney'] and seat == terminal['seat']
                assert g['currentBid'] == 0 and not g['hiddenLog'] and all(p['bid'] == 0 for p in g['players'])
                assert i+1 < len(decisions)
                after = decisions[i+1]['publicRequest']['state']
                assert after['round'] == g['round']
                assert after['log'][:len(g['log'])] == g['log'], 'Visible history must be an immutable prefix'
                submissions = {}; price = None
                for entry in after['log'][len(g['log']):]:
                    move = entry.get('move', {})
                    if move.get('name') in ('Bid', 'Pass'):
                        actor = entry['player']; assert actor not in submissions
                        submissions[actor] = move['data'] if move['name'] == 'Bid' else 0
                    match = re.fullmatch(r'.* wins the bid and pays (\d+)\.', entry.get('event', ''))
                    if match:
                        price = int(match[1]); break
                    assert move.get('name') != 'ChoosePowerPlant', 'Missed the current auction resolution'
                assert price is not None and seat in submissions
                bid = d['move']['data'] if d['move']['name'] == 'Bid' else 0
                assert submissions[seat] == bid
                winner, checked_price = resolution(submissions, g['minimunBid'], g['auctioningPlayer'], n)
                assert checked_price == price
                me = g['players'][seat]; later = after['players'][seat]
                won = winner == seat
                assert later['totalSpentPlants'] - me['totalSpentPlants'] == (price if won else 0)
                available = me['availableMoves'].get('Bid', [])
                r = {'players': n, 'variant': terminal['variant'], 'episode': episode,
                    'game_seed': terminal['gameSeed'], 'seat': seat, 'decision': d['decision'], 'round': g['round'],
                    'game_win_credit': terminal['win'], 'plant': g['chosenPowerPlant'], 'nominator': g['auctioningPlayer'],
                    'bid': bid, 'minimum': g['minimunBid'], 'can_bid': bool(available),
                    'legal_bids': len(available), 'menu_bids': sum(m['name']=='Bid' for m in d['arenaMoves']),
                    'cash': me['money'], 'cities': len(me['cities']),
                    'capacity': sum(p['citiesPowered'] for p in me['powerPlants']),
                    'winner': winner, 'price': price, 'won': won, 'revealed_bids': submissions,
                    'opponent_cash': [p['money'] for p in g['players'] if p['id'] != seat]}
                cases.append(r); game_cases.append(r)
                for key in ('all', f'{n}p/{terminal["variant"]}', f'{n}p/{terminal["variant"]}/'+('first_round' if g['round']==1 else 'later_rounds')):
                    groups[key].append(r)
            final = terminal['final']['players'][terminal['seat']]
            last_player = decisions[-1]['publicRequest']['state']['players'][terminal['seat']]
            games.append({'players': n, 'variant': terminal['variant'], 'episode': episode,
                'game_seed': terminal['gameSeed'], 'seat': terminal['seat'], 'win_credit': terminal['win'],
                'final': final, 'last_observed_spent_plants': last_player['totalSpentPlants'],
                'last_observed_spent_resources': last_player['totalSpentResources'],
                'sealed_decisions': len(game_cases), 'receipt_sha256': result['decision_receipt_sha256']})
    assert len(games) == 96
    report = {'created_at': now(), 'complete': True, 'games': games, 'cases': cases,
        'groups': {k: describe(v) for k,v in sorted(groups.items())}, 'proofs': proofs, 'analysis_sha256': digest(__file__),
        'scope': 'All 96 parent sealed games in the 2/4/6-player development screen, no outcome selection. Later public bid disclosures are used only for retrospective diagnosis. Capacity shortfall and low cash are descriptive, not proofs of bad decisions. No prices are treated as first-price bids.',
        'new_games': 0, 'new_gradients': 0, 'qualified': False, 'reserved_final_seeds_used': False}
    save(OUT, report)
    print(json.dumps(report['groups'], indent=2))


if __name__ == '__main__':
    main()
