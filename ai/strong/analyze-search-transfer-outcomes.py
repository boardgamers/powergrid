"""Describe paired terminal changes; these are not causal phase attributions."""
import argparse
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

from search_transfer import ROOT, PROTOCOL, read, write, digest, summarize_run, module

checks = module('outcome_summary_check', 'collect-discard-correction-screen.py')


def metrics(row):
    me = row['final']['players'][row['seat']]
    others = [p for i, p in enumerate(row['final']['players']) if i != row['seat']]
    return {'win_credit': row['win'], 'round': row['final']['round'],
            'cities': me['cities'], 'powered': me['powered'], 'capacity': me['capacity'], 'cash': me['money'],
            'powered_gap': me['powered']-max(p['powered'] for p in others),
            'capacity_gap': me['capacity']-max(p['capacity'] for p in others),
            'unused_nominal_potential': max(0, min(me['cities'], me['capacity'])-me['powered'])}


def failure_counts(rows):
    losses = [r for r in rows if r['win'] == 0]
    result = Counter(losses=len(losses), shared_wins=sum(0 < r['win'] < 1 for r in rows),
                     sole_wins=sum(r['win'] == 1 for r in rows))
    for r in losses:
        me = r['final']['players'][r['seat']]
        winner = max((p for i, p in enumerate(r['final']['players']) if i != r['seat']),
                     key=lambda p: (p['powered'], p['money']))
        if me['capacity'] < winner['powered']: result['capacity_below_winner_powered'] += 1
        if me['cities'] < winner['powered']: result['cities_below_winner_powered'] += 1
        if me['powered'] == winner['powered'] and me['money'] < winner['money']: result['powered_tie_cash_loss'] += 1
        if min(me['capacity'], me['cities']) > me['powered']: result['unused_nominal_potential'] += 1
    return dict(result)


def paired_changes(guided, raw, protocol):
    key = lambda r: (r['gameSeed'], r['seat'], r['variant'], r['sealed'])
    a, b = {key(r): r for r in guided}, {key(r): r for r in raw}
    assert len(a) == len(guided) == len(b) == len(raw) and a.keys() == b.keys()
    by_deal = defaultdict(list); transitions = Counter()
    for k in sorted(a):
        ma, mb = metrics(a[k]), metrics(b[k]); by_deal[k[0]].append({m: ma[m]-mb[m] for m in ma})
        category = lambda x: 'loss' if x == 0 else ('sole_win' if x == 1 else 'shared_win')
        transitions[category(b[k]['win'])+'->'+category(a[k]['win'])] += 1
    names = list(metrics(guided[0]))
    values = np.array([[sum(r[m] for r in rows)/len(rows) for m in names] for rows in by_deal.values()])
    assert len({len(rows) for rows in by_deal.values()}) == 1
    rng = np.random.default_rng(protocol['bootstrap_seed'])
    draws = values[rng.integers(len(values), size=(protocol['bootstrap_replicates'], len(values)))].mean(axis=1)
    changes = {name: {'mean_search_minus_raw': float(values[:, i].mean()),
                     'paired_deal_bootstrap_95_interval': np.quantile(draws[:, i], [.025, .975]).tolist()}
               for i, name in enumerate(names)}
    return {'games_per_arm': len(guided), 'independent_deals': len(by_deal), 'outcome_transitions': dict(transitions),
            'terminal_changes': changes, 'raw_failures': failure_counts(raw), 'search_failures': failure_counts(guided)}


def main(cases):
    protocol = read(PROTOCOL); source = read(ROOT/'ai/strong/search-transfer-source-v1.json')
    known = {c['id']: c for c in protocol['cases']}; assert cases and set(cases) <= set(known)
    output, provenance = {}, {}
    for key in protocol['models']:
        output[key], provenance[key] = {}, {}
        for name in cases:
            out = ROOT/f'ai/runs/search-transfer-verified-v1/{key}-{name}'; saved = read(out/'verified.json')
            assert saved['key'] == key and saved['case'] == name and not saved['smoke'] and saved['verified']
            assert saved['source_revision'] == source['revision'] and saved['source_sha256'] == source['sha256']
            assert saved['protocol_sha256'] == digest(PROTOCOL)
            for file, sha in saved['artifacts'].items(): assert Path(file).name == file and digest(out/file) == sha
            checked = summarize_run(out, protocol, key, known[name]); checks.same_summary(checked, saved['summary'])
            guided, raw = read(out/'search.json')['results'], read(out/'baseline.json')['results']
            summary = {'overall': paired_changes(guided, raw, protocol), 'rules': {}}
            for variant in ['original', 'recharged']:
                for sealed in [False, True]:
                    select = lambda rows: [r for r in rows if r['variant'] == variant and r['sealed'] == sealed]
                    summary['rules'][variant+('/sealed' if sealed else '/open')] = paired_changes(select(guided), select(raw), protocol)
            assert abs(summary['overall']['terminal_changes']['win_credit']['mean_search_minus_raw']-
                       checked['search_minus_raw']['overall']['win_share_difference']) < 1e-12
            output[key][name] = summary
            provenance[key][name] = {'revision': saved['revision'], 'prefix': saved['prefix'],
                                    'verified_sha256': digest(out/'verified.json')}
    result = {'cases': cases, 'models': output, 'provenance': provenance, 'protocol_sha256': digest(PROTOCOL),
              'scope': 'Descriptive paired terminal outcomes on reused development deals. Failure categories overlap; unused nominal potential can reflect fuel shortage. These are not causal phase diagnoses, calibrated player scores or qualification evidence. Whole-deal marginal bootstrap intervals, no multiplicity correction.',
              'qualification_eligible': False}
    write(ROOT/'ai/strong/search-transfer-terminal-analysis-v1.json', result)
    print({k: {c: r['overall']['terminal_changes'] for c, r in cells.items()} for k, cells in output.items()})


if __name__ == '__main__':
    p = argparse.ArgumentParser(__doc__)
    p.add_argument('--cases', nargs='+', default=['heuristic-2p', 'search_geo-2p'])
    main(p.parse_args().cases)
