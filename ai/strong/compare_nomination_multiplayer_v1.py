"""Compare all frozen arms in one fully audited multiplayer/opponent cell."""
import argparse
from collections import defaultdict
from pathlib import Path
from arena_statistics import validate_pairs
from run_nomination_minipc_v1 import read, save, digest, now

ROOT = Path(__file__).resolve().parents[2]
STRONG = ROOT/'ai/strong'


def summarize(records, parent, players):
    assert records.keys() == parent.keys()
    games = 16*players; assert len(records) == games
    pairs = []; deals = defaultdict(list)
    for key in sorted(records):
        game, baseline = records[key], parent[key]
        delta = game['win']-baseline['win']; deals[key[0]].append(delta)
        pairs.append({'seed': key[0], 'variant': key[1], 'sealed': key[2], 'seat': key[3],
            'credit': game['win'], 'parent_credit': baseline['win'], 'difference': delta,
            'different_final_state': game['final'] != baseline['final']})
    assert len(deals) == 4 and all(len(v) == 4*players for v in deals.values())
    cells = {}
    for variant in ('original', 'recharged'):
        for sealed in (False, True):
            subset = [p for p in pairs if p['variant'] == variant and p['sealed'] == sealed]
            assert len(subset) == 4*players
            cells[variant+('/sealed' if sealed else '/open')] = {
                'games': len(subset), 'win_credit': sum(p['credit'] for p in subset),
                'parent_win_credit': sum(p['parent_credit'] for p in subset),
                'paired_difference': sum(p['difference'] for p in subset)/len(subset)}
    return {'games': games, 'independent_deals': 4, 'win_credit': sum(p['credit'] for p in pairs),
        'win_rate': sum(p['credit'] for p in pairs)/games,
        'paired_win_rate_difference': sum(p['difference'] for p in pairs)/games,
        'gained_games': sum(p['difference'] > 0 for p in pairs),
        'lost_games': sum(p['difference'] < 0 for p in pairs),
        'unchanged_credit_games': sum(p['difference'] == 0 for p in pairs),
        'different_final_state_games': sum(p['different_final_state'] for p in pairs),
        'deal_mean_differences': {k: sum(v)/len(v) for k, v in sorted(deals.items())},
        'rule_cells': cells, 'pairs': pairs}


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--players', type=int, choices=(3, 4, 5, 6), required=True)
    parser.add_argument('--opponent', choices=('search_geo', 'a260'), default='search_geo')
    args = parser.parse_args(); n = args.players; slug = args.opponent.replace('_', '-')
    out = STRONG/f'nomination-discount-{n}p-{slug}-results-v1.json'
    assert not out.exists(), 'Preserve original completed comparison'
    protocol_path = STRONG/'nomination-discount-development-protocol-v1.json'
    protocol = read(protocol_path); rows = {}; proofs = {}
    for arm in protocol['arms']:
        name = f'pg-nom-dev-v1-{arm}-{slug}-{n}p'
        row = next(r for r in protocol['rows'] if r['name'] == name)
        folder = ROOT/'ai/runs/nomination-discount-development-collected-v1'/name
        raw = folder/'raw'; audit_path = folder/'audit.json'; audit = read(audit_path)
        receipt = read(folder/'receipt.json')
        assert audit['independently_audited'] and audit['caps'] == 0 and audit['games'] == 16*n
        assert audit['row'] == row and audit['protocol_sha256'] == digest(protocol_path)
        assert audit['auditor_sha256'] == digest(STRONG/'audit_nomination_development_v1.py')
        assert audit['raw_manifest_sha256'] == digest(raw/'manifest.json') == receipt['manifest_sha256']
        assert all(digest(raw/p) == h for p, h in read(raw/'manifest.json').items())
        evaluation = read(raw/'evaluation/evaluation.json')
        assert evaluation['all_complete'] and evaluation['passed'] and not evaluation['errors']
        assert evaluation['config']['identity'] == protocol['identities'][arm]
        terminals = [r['terminal'] for r in evaluation['results']]; validate_pairs(terminals, n)
        rows[arm] = {(r['gameSeed'], r['variant'], r['sealed'], r['seat']): r for r in terminals}
        assert len(rows[arm]) == len(terminals) == 16*n
        proofs[arm] = {'audit_path': str(audit_path.relative_to(ROOT)), 'audit_sha256': digest(audit_path),
            'raw_manifest_sha256': digest(raw/'manifest.json'), 'original_raw_archive': receipt,
            'worker_seconds': audit['seconds']}
    summaries = {arm: summarize(records, rows['parent'], n) for arm, records in rows.items()}
    save(out, {'created_at': now(), 'complete': True, 'players': n, 'opponent': args.opponent,
        'games': 80*n, 'protocol_sha256': digest(protocol_path), 'analysis_sha256': digest(__file__),
        'proofs': proofs, 'arms': summaries,
        'scope': 'Four independent deals with all seats/rules; descriptive development screen. No selection or qualification.',
        'qualified': False, 'reserved_final_seeds_used': False})
    print({arm: {k: s[k] for k in ('win_credit', 'win_rate', 'paired_win_rate_difference',
        'gained_games', 'lost_games', 'deal_mean_differences', 'rule_cells')} for arm, s in summaries.items()})


if __name__ == '__main__': main()
