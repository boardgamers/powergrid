"""Offline assessment of completed sealed targets and original learning curves."""
from collections import defaultdict
from fractions import Fraction as F
from pathlib import Path

from run_sealed_target_quality_v1 import read, save, digest, now, choose

ROOT = Path(__file__).resolve().parents[2]


def main():
    report = ROOT/'ai/strong/sealed-target-quality-complete-v1.json'
    complete = read(report); assert complete['complete'] and complete['rollouts'] == 6160 and complete['caps'] == 0
    raw = ROOT/'ai/runs/sealed-target-quality-v1/collected'; roots = read(raw/'roots.json')
    modes = ['neural_population', 'reference_opponent_v1']; details = []; rows = []
    for i, (root, result) in enumerate(zip(roots, complete['reports'])):
        assert root['rootId'] == result['rootId']; bank = {}
        for mode in modes:
            for begin in (4, 32):
                p = raw/f'root-{i:02d}-{mode}-{begin}.json'
                assert digest(p) == result['raw_files'][p.name]
                scores = defaultdict(list)
                for row in read(p)['rows']:
                    vals = [tuple(p[k] for k in ('powered', 'money', 'cities')) for p in row['diagnostic']['terminal']]
                    seat = root['request']['player']; own = vals[seat]; best = max(vals)
                    win = F(1, vals.count(best)) if own == best else F(0)
                    rank = sum((F(1) if own > v else F(1, 2) if own == v else F(0)
                                for j, v in enumerate(vals) if j != seat), F()) / (len(vals)-1)
                    scores[str(row['actionIndex'])].append((win, rank))
                bank[mode, begin] = {a: tuple(sum((v[k] for v in vs), F())/28 for k in (0, 1)) for a, vs in scores.items()}
        for begin, end in ((4, 32), (32, 4)):
            for objective, column in (('win', 0), ('opponents_outranked', 1)):
                for selector in (*modes, 'equal_mixture'):
                    means = {str(a): (bank[selector, begin][str(a)][column] if selector != 'equal_mixture'
                             else sum((bank[m, begin][str(a)][column] for m in modes), F())/2) for a in root['options']}
                    action = choose(means, root['baseline']); base = str(root['baseline'])
                    rows.append({'root': i, 'objective': objective, 'selection_begin': begin, 'selector': selector,
                        'action': int(action), 'overridden': action != base, 'selection_margin': str(means[action]-means[base]),
                        'heldout_win_margins': {m: str(bank[m, end][action][0]-bank[m, end][base][0]) for m in modes}})
        root_rows = [r for r in rows if r['root'] == i and r['objective'] == 'win']
        details.append({'rootId': root['rootId'], 'players': root['players'], 'variant': root['variant'],
            'cross_fit_mean_margins': {sel: {mode: str(sum((F(r['heldout_win_margins'][mode]) for r in root_rows if r['selector'] == sel), F())/2)
                for mode in modes} for sel in (*modes, 'equal_mixture')}})
    summaries = {}
    for objective in ('win', 'opponents_outranked'):
        summaries[objective] = {}
        for selector in (*modes, 'equal_mixture'):
            selected = [r for r in rows if r['objective'] == objective and r['selector'] == selector]
            means = {mode: sum((F(r['heldout_win_margins'][mode]) for r in selected), F())/len(selected) for mode in modes}
            if objective == 'win':
                assert {m: str(v) for m, v in means.items()} == complete['summary'][selector]['mean_heldout_margins']
            summaries[objective][selector] = {'overrides': sum(r['overridden'] for r in selected),
                'mean_heldout_win_margins': {m: str(v) for m, v in means.items()},
                'root_sign_counts': {m: {name: sum((v > 0 if name == 'positive' else v < 0 if name == 'negative' else v == 0)
                    for v in [sum((F(r['heldout_win_margins'][m]) for r in selected if r['root'] == i), F())/2 for i in range(10)])
                    for name in ('positive', 'zero', 'negative')} for m in modes}}
    curves = []
    for folder in sorted((ROOT/'ai/runs/nomination-discount-training-collected-v1').iterdir()):
        if not (folder/'raw/history.json').exists(): continue
        audit = read(folder/'audit.json'); history_path = folder/'raw/history.json'
        receipt = read(folder/'receipt.json'); manifest = read(folder/'raw/manifest.json')
        assert digest(folder/'raw/manifest.json') == receipt['manifest_sha256']
        assert digest(history_path) == manifest['history.json'] and audit['independently_audited']
        for seed, history in read(history_path).items():
            first, last = history[0], history[-1]
            assert first['epoch'] == 0 and last['epoch'] == 120
            curves.append({'arm': folder.name, 'seed': int(seed), 'history_sha256': digest(history_path),
                'train_mse_start': first['train']['weighted_mse'], 'train_mse_end': last['train']['weighted_mse'],
                'validation_mse_start': first['validation']['weighted_mse'], 'validation_mse_end': last['validation']['weighted_mse'],
                'validation_advantage_end': last['validation']['mean_simulated_advantage']})
    assert len(curves) == 16
    save(ROOT/'ai/strong/target-generalization-analysis-v1.json', {'created_at': now(), 'complete': True,
        'sealed_report_sha256': digest(report), 'sealed_seconds': complete['seconds'], 'sealed_roots': details,
        'sealed_summary': summaries, 'diagnostic_rows': rows, 'training_curves': curves,
        'fits_improving_train_but_worsening_validation_mse': sum(r['train_mse_end'] < r['train_mse_start'] and r['validation_mse_end'] > r['validation_mse_start'] for r in curves),
        'interpretation': 'Weak transfer of conditional sealed-bid targets on ten roots, with no convincing gain from expensive reference-selected actions. Opponents-outranked objective is retrospective, not a selected training target; it provides no clear rescue. All sixteen historical fits overfit by final epoch. These findings do not establish universal absence of bidding improvements or a causal diagnosis of neural representation.',
        'next_step': 'Bounded HF learner-class probe on already verified current-engine nomination data: fixed regularized tree learners, whole-deal internal tuning, legacy validation used only after fit. This is distinct from adding epochs to the closed neural candidate iteration.',
        'new_games': 0, 'new_gradients': 0, 'qualified': False, 'reserved_final_seeds_used': False})


if __name__ == '__main__': main()
