"""Describe the completed screen, including regressions; never promote or launch."""
from collections import Counter
import json
from pathlib import Path

import numpy as np

from strategic_collection import ROOT, read, write, digest

STRONG = ROOT / 'ai/strong'
COMPARISON = STRONG / 'population-hybrid-development-comparison-v1.json'
EVIDENCE = STRONG / 'population-hybrid-development-complete-evidence-v1.json'
OUTPUT = STRONG / 'population-hybrid-development-review-v1.json'
DOCUMENT = ROOT / 'ai/HYBRID-SCREEN-2026-10-24.md'
COLLECTED = ROOT / 'ai/runs/population-hybrid-development-collected-v1'
ARMS = ['model', 'filter', 'auction', 'building', 'combined']
RULES = ['original/open', 'original/sealed', 'recharged/open', 'recharged/sealed']


def main():
    assert not OUTPUT.exists() and not DOCUMENT.exists(), 'Inspect existing review before rewriting'
    comparison, evidence = read(COMPARISON), read(EVIDENCE)
    assert evidence['remote_archive_verified'] and evidence['comparison_reproduced']
    assert evidence['comparison_sha256'] == digest(COMPARISON)
    assert comparison['complete'] and comparison['games'] == 8400
    assert not comparison['candidate_selected'] and not comparison['reserved_final_seeds_used']
    assert list(comparison['absolute']) == ARMS
    for cell in comparison['comparisons']['filter-minus-model'].values():
        assert all(v['win_share_difference'] >= 0 for v in [cell['overall'], *cell['by_rules'].values()])
    totals = {arm: Counter() for arm in ARMS}
    search_times = {arm: [] for arm in ARMS}
    changed_margins = {arm: [] for arm in ARMS}
    games = {}
    for case, provenance in comparison['provenance'].items():
        base = COLLECTED / case
        assert digest(base / 'verified.json') == provenance['verified_sha256']
        receipt = read(base / 'verified.json')
        assert receipt['job_id'] == provenance['job_id'] and receipt['evidence'] == provenance['evidence']
        row, summary = receipt['row'], receipt['summary']
        arm = row['arm']
        folder = base / 'artifacts/evaluation'
        assert digest(folder / 'evaluation.json') == summary['report_sha256']
        report = read(folder / 'evaluation.json')
        assert report['all_complete'] and report['errors'] == []
        assert report['game_caps'] == report['rollout_caps'] == 0
        totals[arm].update(summary['counts'])
        totals[arm]['games'] += summary['games']
        totals[arm]['hf_wall_seconds'] += summary['wall_seconds']
        cell = f"{row['opponent']}/{row['players']}p"
        games[arm, cell] = {r['episode']: r['terminal'] for r in report['results']}
        for result in report['results']:
            path = folder / f"decisions-{result['episode']}.jsonl"
            assert digest(path) == result['decision_receipt_sha256']
            with path.open() as handle:
                for line in handle:
                    decision = json.loads(line)
                    search = decision['search']
                    if not search:
                        continue
                    assert search['usable'] and search['truncated'] == 0
                    search_times[arm].append(decision['elapsedMs'])
                    # Auction roots cannot be changed by the endgame Build filter.
                    # Building roots that are filtered have a different baseline.
                    if decision['filterApplied']:
                        continue
                    chosen, baseline = str(decision['index']), str(decision['modelProposal'])
                    if chosen != baseline:
                        margin = search['meanCredits'][chosen] - search['meanCredits'][baseline]
                        assert margin > 0
                        changed_margins[arm].append(margin)
    assert len(games) == 135
    execution = {}
    for arm in ARMS:
        assert totals[arm]['games'] == 1680 and totals[arm]['rollout_caps'] == 0
        assert len(search_times[arm]) == totals[arm]['search_decisions']
        margins = changed_margins[arm]
        execution[arm] = {
            **dict(totals[arm]),
            'search_decision_p50_ms': float(np.median(search_times[arm])) if search_times[arm] else None,
            'search_decision_p95_ms': float(np.quantile(search_times[arm], .95)) if search_times[arm] else None,
            'search_changes_from_unfiltered_model': len(margins),
            'changes_with_mean_credit_margin_at_most_one_eighth': sum(m <= .125 + 1e-12 for m in margins),
            'runtime_scope': 'Observed HF cpu-upgrade game jobs with eight concurrent games; not 8840U latency.',
        }

    cells = sorted(comparison['absolute']['model'], key=lambda c: (int(c.split('/')[1][:-1]), c))
    table = {cell: {arm: comparison['absolute'][arm][cell] for arm in ARMS} for cell in cells}
    adverse = []
    for cell in cells:
        delta = comparison['comparisons']['auction-minus-filter'][cell]
        for view, result in [('overall', delta['overall']), *delta['by_rules'].items()]:
            if result['win_share_difference'] < 0:
                adverse.append({'cell': cell, 'view': view, **result})
    focus = []
    for cell, view in [('search_geo/4p', 'original/open'), ('search_geo/5p', 'recharged/open'),
                       ('heuristic/3p', 'overall')]:
        paired = []
        for episode, baseline in sorted(games['filter', cell].items()):
            rule = baseline['variant'] + ('/sealed' if baseline['sealed'] else '/open')
            if view != 'overall' and view != rule:
                continue
            hybrid = games['auction', cell][episode]
            assert (baseline['gameSeed'], baseline['seat'], baseline['variant'], baseline['sealed']) == (
                hybrid['gameSeed'], hybrid['seat'], hybrid['variant'], hybrid['sealed'])
            def terminal(t):
                return {'win': t['win'], 'round': t['final']['round'], **t['final']['players'][t['seat']]}
            paired.append({'episode': episode, 'deal': baseline['gameSeed'], 'seat': baseline['seat'],
                           'rule': rule, 'difference': hybrid['win'] - baseline['win'],
                           'filter': terminal(baseline), 'auction': terminal(hybrid)})
        focus.append({'cell': cell, 'view': view, 'paired_games': len(paired),
                      'worse_outcomes': sum(p['difference'] < 0 for p in paired),
                      'better_outcomes': sum(p['difference'] > 0 for p in paired), 'pairs': paired})

    decision = {
        'reference_for_further_research': 'frozen-1 plus strict endgame-loss filter',
        'auction': 'Promising, especially sealed; held for diagnosis because open-auction and heuristic-opponent regressions remain unresolved.',
        'building': 'Do not advance this implementation: point estimates fall against search_geo at every player count.',
        'combined': 'Do not advance this implementation: worse than auction-only against search_geo at every count.',
        'next_work': [
            'Replay paired auction regressions and suitable improved controls from immutable saved data; inspect bidding, candidate margins and simulated opponent behavior.',
            'Distinguish finite-world selection noise, opponent-model mismatch and future-policy approximation with separately specified diagnostics; none is established by terminal summaries.',
            'Only after addressing regressions, freeze the policy and run larger fresh all-count/all-rule confirmation. Do not retrofit routing to the favorable cells.',
            'Keep the separate resource-replanning ablation unlaunched until its source and full-game runtime admission are complete.',
            'Before final qualification, implement the exact selected-policy final adapter and repeat full target-hardware evidence; existing model-only receipts are insufficient.',
        ],
        'plateau': 'No evidence of a general ceiling. Auction improvements coexist with clear failures; more of this unchanged broad search is not justified.',
        'candidate_selected': False, 'confirmation_admitted': False, 'new_jobs': 0,
        'qualification_eligible': False, 'reserved_final_seeds_used': False,
    }
    review = {'comparison_sha256': digest(COMPARISON), 'archive': evidence,
              'reviewer_sha256': digest(Path(__file__)), 'games': 8400, 'batches': 135,
              'independent_deals_per_cell': 4, 'execution': execution, 'performance': table,
              'auction_adverse_cells': adverse, 'paired_regression_focus': focus, 'decision': decision,
              'statistics_limit': 'Four deals per cell. Whole-deal exploratory marginal intervals are coarse and not multiplicity-adjusted; repeated seats and rules are not independent deals.',
              'diagnostic_limit': 'Terminal associations and observed search margins are descriptive, not causal counterfactuals or calibrated probabilities.'}
    write(OUTPUT, review)

    lines = [
        '# Power Grid hybrid screen — 24 October 2026', '',
        'All **135 batches / 8,400 games** completed and passed verification. The unchanged',
        'comparator reproduced exactly; all raw results, decision receipts and recovery',
        'proofs are archived in the private HF repository. No final candidate was selected.', '',
        '**Decision:** continue investigating auction search, keep the filtered model as',
        'the research reference, and do not advance this building-search or combined-search',
        'implementation. Auction search has meaningful regressions that must be explained',
        'before larger confirmation. No new jobs were submitted by this review.', '',
        'Each arm has 1,680 games over Germany 2–6 players, all four rule combinations,',
        'all seats and 27 count/opponent cells. Each cell has only **four independent deals**.',
        'The table percentages include fractional credit for ties. They are exploratory.', '',
        '## Against the independent search opponent', '',
        '| Players | Model | Filter | Auction | Building | Combined |',
        '|---|---:|---:|---:|---:|---:|',
    ]
    def values(cell, view='overall'):
        return [(table[cell][arm]['overall'] if view == 'overall' else
                 table[cell][arm]['by_rules'][view])['win_rate'] for arm in ARMS]
    for n in range(2, 7):
        lines.append('| ' + str(n) + ' | ' + ' | '.join(f'{v:.1%}' for v in values(f'search_geo/{n}p')) + ' |')
    lines += ['', '## Search opponent, each rule combination', '',
              '| Players / rules | Model | Filter | Auction | Building | Combined |',
              '|---|---:|---:|---:|---:|---:|']
    for n in range(2, 7):
        for rule in RULES:
            lines.append('| ' + str(n) + ' / ' + rule + ' | ' +
                         ' | '.join(f'{v:.1%}' for v in values(f'search_geo/{n}p', rule)) + ' |')
    lines += ['', 'Auction search improves Recharged sealed point estimates at every count.',
              'However, four-player original/open falls from **81.25% to 31.25%**',
              '(8 worse paired outcomes, no better outcomes, 16 games / four deals).',
              'Five-player Recharged/open falls from **70% to 50%** (6 worse, 2 better,',
              '20 games / four deals). Three-player heuristic falls from **100% to 85.42%**',
              '(7 worse, no better, 48 games / four deals). These cannot be hidden by the',
              'overall auction gains or used to invent a retrospectively optimized rule switch.', '',
              'The strict loss filter changes no search-opponent win totals in this screen.',
              'It improves several other cells and has no negative point estimate here;',
              'this is not a guarantee of universal improvement.', '',
              '## Every count/opponent cell', '',
              '| Cell | Model | Filter | Auction | Building | Combined |',
              '|---|---:|---:|---:|---:|---:|']
    for cell in cells:
        lines.append('| ' + cell + ' | ' + ' | '.join(f'{v:.1%}' for v in values(cell)) + ' |')
    lines += ['', '## Execution and next steps', '',
              'All game and rollout cap counts are zero. Timing below is from shared HF',
              'cpu-upgrade jobs with eight concurrent games, **not AMD 8840U latency**.', '',
              '| Arm | Search decisions | Search changes | Rollouts | Search median / p95 |',
              '|---|---:|---:|---:|---:|']
    for arm in ARMS:
        e = execution[arm]
        time = ('—' if e['search_decision_p50_ms'] is None else
                f"{e['search_decision_p50_ms']/1000:.1f}s / {e['search_decision_p95_ms']/1000:.1f}s")
        lines.append(f"| {arm} | {e['search_decisions']:,} | {e['search_changes']:,} | {e['rollouts']:,} | {time} |")
    e = execution['auction']
    lines += ['', f"Of {e['search_changes_from_unfiltered_model']:,} auction changes, "
              f"{e['changes_with_mean_credit_margin_at_most_one_eighth']:,} have a simulated mean-credit "
              'advantage of at most 1/8 over the model action. That motivates checking',
              'selection noise; it does not establish the cause of any loss. Opponent',
              'mixture mismatch and approximating future search with model-only play also',
              'remain hypotheses, not measured explanations.', '',
              *[f'{i}. {text}' for i, text in enumerate(decision['next_work'], 1)], '',
              '**Progress assessment:** this is not evidence of a general plateau.',
              'Auction search offers a promising direction, but running more unchanged',
              'building/combined search or indiscriminately distilling its actions is not justified.', '',
              '## Persistent evidence', '',
              '- [Full comparison](strong/population-hybrid-development-comparison-v1.json).',
              '- [Machine-readable review, all adverse auction cells and paired terminals](strong/population-hybrid-development-review-v1.json).',
              '- [Archive descriptor](strong/population-hybrid-development-complete-evidence-v1.json).',
              f"- Private HF revision: `{evidence['revision']}`.",
              f"- Archive SHA256: `{evidence['archive_sha256']}`.",
              f"- Comparison SHA256: `{digest(COMPARISON)}`.",
              '- Final qualification protocol and reserved seeds remain unchanged and unused.', '']
    DOCUMENT.write_text('\n'.join(lines))
    print(json.dumps({'review': str(OUTPUT), 'document': str(DOCUMENT),
                      'execution': execution, 'adverse_auction_views': len(adverse),
                      'focus': [{k: v for k, v in f.items() if k != 'pairs'} for f in focus]}, indent=2))


if __name__ == '__main__':
    main()
