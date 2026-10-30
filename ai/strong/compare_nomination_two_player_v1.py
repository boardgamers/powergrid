"""Paired descriptive comparison of the five audited original 2p/search shards."""
from collections import defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path

from arena_statistics import validate_pairs
from run_nomination_minipc_v1 import read, save, digest

ROOT = Path(__file__).resolve().parents[2]
STRONG = ROOT/'ai/strong'
OUT = STRONG/'nomination-discount-two-player-results-v1.json'


def locations(arm):
    name = f'pg-nom-dev-v1-{arm}-search-geo-2p'
    if arm == 'parent':
        folder = ROOT/'ai/runs/nomination-discount-minipc-v1'
        return folder/'collected'/name, folder/'audit.json'
    if arm == 'd1-all1':
        folder = ROOT/'ai/runs/nomination-discount-development-collected-v1'/name
        return folder/'raw', folder/'audit.json'
    folder = ROOT/'ai/runs/nomination-discount-minipc-batch-v1'
    return folder/'collected'/name, folder/(name+'.audit.json')


def main():
    assert not OUT.exists(), 'Preserve original comparison'
    protocol_path = STRONG/'nomination-discount-development-protocol-v1.json'
    protocol = read(protocol_path); rows = {}; proofs = {}
    for arm in protocol['arms']:
        raw, audit_path = locations(arm); audit = read(audit_path)
        assert audit['independently_audited'] and audit['caps'] == 0 and audit['games'] == 32
        assert audit['protocol_sha256'] == digest(protocol_path)
        assert audit['auditor_sha256'] == digest(STRONG/'audit_nomination_development_v1.py')
        assert audit['raw_manifest_sha256'] == digest(raw/'manifest.json')
        assert all(digest(raw/n) == h for n, h in read(raw/'manifest.json').items())
        evaluation = read(raw/'evaluation/evaluation.json')
        assert evaluation['all_complete'] and evaluation['passed'] and not evaluation['errors']
        assert evaluation['config']['identity'] == protocol['identities'][arm]
        terminals = [r['terminal'] for r in evaluation['results']]
        validate_pairs(terminals, 2)
        by_key = {(r['gameSeed'], r['variant'], r['sealed'], r['seat']): r for r in terminals}
        assert len(by_key) == len(terminals) == 32
        rows[arm] = by_key
        proofs[arm] = {'audit_path': str(audit_path.relative_to(ROOT)), 'audit_sha256': digest(audit_path),
                       'raw_manifest_sha256': digest(raw/'manifest.json'), 'worker_seconds': audit['seconds']}
    parent = rows['parent']; summaries = {}
    for arm, records in rows.items():
        assert records.keys() == parent.keys()
        deals = defaultdict(list); cells = {}; gains = losses = ties = 0; changed_final = 0
        pairs = []
        for key in sorted(records):
            game = records[key]; baseline = parent[key]; delta = game['win']-baseline['win']
            deals[key[0]].append(delta); gains += delta > 0; losses += delta < 0; ties += delta == 0
            changed_final += game['final'] != baseline['final']
            pairs.append({'seed': key[0], 'variant': key[1], 'sealed': key[2], 'seat': key[3],
                          'credit': game['win'], 'parent_credit': baseline['win'], 'difference': delta})
        for variant in ('original', 'recharged'):
            for sealed in (False, True):
                selected = [p for p in pairs if p['variant'] == variant and p['sealed'] == sealed]
                cells[variant+('/sealed' if sealed else '/open')] = {
                    'games': len(selected), 'win_credit': sum(r['credit'] for r in selected),
                    'parent_win_credit': sum(r['parent_credit'] for r in selected),
                    'paired_difference': sum(r['difference'] for r in selected)/len(selected)}
        assert len(deals) == 4 and all(len(v) == 8 for v in deals.values())
        summaries[arm] = {'games': 32, 'independent_deals': 4, 'win_credit': sum(r['win'] for r in records.values()),
            'win_rate': sum(r['win'] for r in records.values())/32,
            'paired_win_rate_difference': sum(sum(v) for v in deals.values())/32,
            'gained_games': gains, 'lost_games': losses, 'unchanged_credit_games': ties,
            'different_final_state_games': changed_final,
            'deal_mean_differences': {k: sum(v)/len(v) for k, v in sorted(deals.items())},
            'rule_cells': cells, 'pairs': pairs}
    result = {'created_at': datetime.now(timezone.utc).isoformat(), 'complete': True, 'games': 160,
        'protocol_sha256': digest(protocol_path), 'analysis_sha256': digest(__file__), 'proofs': proofs,
        'arms': summaries, 'interpretation': 'Four independent deals with all seats/rules. Differences of one game do not establish superiority. Keep all arms for wider-count screening; no selection or qualification.',
        'qualified': False, 'reserved_final_seeds_used': False}
    save(OUT, result)
    print({arm: {k: s[k] for k in ('win_credit', 'paired_win_rate_difference', 'gained_games', 'lost_games', 'deal_mean_differences')} for arm, s in summaries.items()})


if __name__ == '__main__': main()
