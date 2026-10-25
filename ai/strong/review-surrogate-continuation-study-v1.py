"""Review the complete immutable fidelity study and freeze a fresh strength screen.

No inference, games, training, policy promotion or HF submissions occur here.
Descriptive subgroup summaries never change the pre-specified primary endpoint.
"""
import argparse
from collections import defaultdict
from copy import deepcopy
from datetime import datetime, timezone
from fractions import Fraction
import json
from pathlib import Path
import statistics

from public_policy_final_audit_v1 import digest, read, PROTOCOL_SHA

ROOT = Path(__file__).resolve().parents[2]
STRONG = ROOT/'ai/strong'
REVIEW = STRONG/'surrogate-continuation-study-review-v1.json'
PROTOCOL = STRONG/'conservative-auction-development-protocol-v1.json'
NOTE = ROOT/'ai/SURROGATE-FIDELITY-2026-10-25.md'
POPULATION = 'neural_population'
SURROGATE = 'surrogate_opponent_v1'


def write_new(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False); stream.write('\n')


def rational(value): return Fraction(*value['exact'])
def number(value): return {'exact': [value.numerator, value.denominator], 'value': float(value)}


def summarize(groups):
    metrics = {mode: {key: number(sum((rational(g['metrics'][mode][key]) for g in groups), Fraction())/len(groups))
                     for key in groups[0]['metrics'][mode]} for mode in (POPULATION, SURROGATE)}
    delta = rational(metrics[SURROGATE]['absolute_margin_error'])-rational(metrics[POPULATION]['absolute_margin_error'])
    return {'groups': len(groups), 'roots': sum(g['roots'] for g in groups), 'metrics': metrics,
            'surrogate_minus_population_error': number(delta)}


def main():
    assert not any(p.exists() for p in (REVIEW, PROTOCOL, NOTE)), 'Preserve the original completed-study decision'
    evidence_path = STRONG/'surrogate-continuation-study-complete-evidence-v1.json'
    index_path = STRONG/'surrogate-continuation-study-results-v1.json'
    comparison_path = STRONG/'surrogate-continuation-study-comparison-v1.json'
    evidence, index, comparison = map(read, (evidence_path, index_path, comparison_path))
    assert evidence['complete'] and evidence['all_original_jobs_audited'] and evidence['remote_archive_verified']
    assert evidence['jobs'] == evidence['roots'] == index['jobs'] == index['roots'] == 480
    assert evidence['caps'] == index['caps'] == comparison['caps'] == 0
    assert evidence['terminal_credits_independently_recomputed'] == comparison['continuations'] == 23040
    assert digest(index_path) == evidence['index_sha256'] and digest(comparison_path) == evidence['comparison_sha256']
    groups = comparison['primary']['groups']; assert len(groups) == 60
    whole = summarize(list(groups.values()))
    assert whole['metrics'] == comparison['primary']['macro']
    assert whole['surrogate_minus_population_error'] == comparison['primary']['surrogate_minus_population_error']
    descriptive = {}
    for dimension, index_part in (('players', 0), ('rule', 1), ('phase', 2)):
        subsets = defaultdict(list)
        for key, group in groups.items(): subsets[key.split('/')[index_part]].append(group)
        descriptive[dimension] = {key: summarize(values) for key, values in sorted(subsets.items())}
    counts = {'better': 0, 'worse': 0, 'equal': 0}
    for group in groups.values():
        delta = rational(group['surrogate_minus_population_error'])
        counts['better' if delta < 0 else 'worse' if delta > 0 else 'equal'] += 1
    assert sum(counts.values()) == 60
    timing = {}
    for mode in (POPULATION, SURROGATE, 'reference_opponent_v1'):
        rows = [r['modes'][mode] for r in evidence['measurements'].values()]; assert len(rows) == 480
        timing[mode] = {'median_seconds_per_16_continuations': statistics.median(r['seconds'] for r in rows),
                       'maximum_seconds_per_16_continuations': max(r['seconds'] for r in rows),
                       'total_cpu_hours': sum(r['cpu_seconds'] for r in rows)/3600,
                       'sampled_peak_total_rss_bytes': max(r['sampled_peak_total_rss_bytes'] for r in rows)}
    review = {'created_at': datetime.now(timezone.utc).isoformat(), 'complete': True,
        'evidence_descriptor_sha256': digest(evidence_path), 'index_sha256': digest(index_path),
        'comparison_sha256': digest(comparison_path), 'script_sha256': digest(__file__),
        'archive': {k: evidence[k] for k in ('repo', 'revision', 'archive_path', 'archive_sha256', 'manifest_sha256')},
        'primary': whole, 'whole_deal_uncertainty': comparison['whole_deal_uncertainty'],
        'descriptive_subgroups': descriptive, 'group_error_directions': counts,
        'all_adverse_groups': comparison['primary']['adverse_groups'], 'by_prior_bids': comparison['by_prior_bids'],
        'timing': timing, 'physical_reference_work': evidence['physical_reference_work'],
        'decision': 'Do not replace the existing opponent population or claim improved continuation fidelity. Test conservative auction overrides against the filtered policy, with a separate dual-population arm to measure whether additional opponent scenarios help actual play.',
        'training_decision': 'Do not extend the same surrogate training recipe or distill these fixed two-action diagnostic values. The trained ensemble is retained as an experimental secondary population, not promoted as the default.',
        'limitations': ['Only two independent deals per player count and eight worlds per action.',
            'The reference is a particular strong search opponent, not optimal play or a human population.',
            'Higher tie-aware preference agreement is secondary and does not establish better action-margin accuracy.',
            'No economic-prior-only arm: this study cannot isolate the learned residual contribution.',
            'Fidelity is not full-game strength. Future focal search is still approximated by filtered-model continuations.',
            'Timing is from shared HF jobs, not 8840U serving latency.'],
        'new_hf_jobs': 0, 'new_games': 0, 'gradient_updates': 0, 'candidate_selected': False,
        'qualification_eligible': False, 'reserved_final_seeds_used': False}
    write_new(REVIEW, review)

    previous = read(STRONG/'population-hybrid-development-protocol-v1.json')
    base = ROOT/'ai/runs/public-policy-development-job-preflight-v1/source/artifact'
    filtered, dual = read(base/'policy-filter.json'), read(base/'policy.json')
    single = deepcopy(dual); single['settings']['population_modes'] = [POPULATION]
    assert dual['settings']['minimum_advantage'] == single['settings']['minimum_advantage'] == '1/8'
    assert dual['settings']['population_modes'] == [POPULATION, SURROGATE]
    assert digest(base/'manifest.json') == dual['runtime_manifest']['sha256'] == filtered['runtime_manifest']['sha256']
    assert all(digest(base/name) == sha for name, sha in read(base/'manifest.json').items())
    arms = {'filter': filtered, 'conservative_population': single, 'conservative_dual': dual}
    screens = []
    for old in previous['screens']:
        row = {k: old[k] for k in ('players', 'opponent', 'model_path', 'revision', 'sha256') if k in old}
        row.update(deals=8, games=32*row['players']); screens.append(row)
    assert len(screens) == len({(r['players'], r['opponent']) for r in screens}) == 27
    assert sum(r['games'] for r in screens) == 3360
    assert {r['players'] for r in screens if r['opponent'] == 'search_geo'} == set(range(2, 7))
    assert digest(STRONG/'final-protocol-multiplayer.json') == PROTOCOL_SHA
    portable = read(STRONG/'public-policy-development-hf-evidence-v1.json')
    assert portable['complete'] and portable['review']['exact_local_comparison'] and portable['archive']['remote_archive_verified']
    protocol = {'version': 1, 'created_at': review['created_at'],
        'purpose': 'Fresh whole-game development comparison of conservative auction search and opponent-population coverage. No final candidate selection or qualification.',
        'decision_sha256': digest(REVIEW), 'fidelity_evidence': review['archive'],
        'portable_source': {k: portable['source'][k] for k in ('repo', 'revision', 'archive', 'sha256', 'source_manifest_sha256')},
        'portable_hf_evidence': portable['archive'], 'base_runtime_manifest_sha256': digest(base/'manifest.json'),
        'model_pin': previous['model_pin'], 'arms': arms,
        'seed_template': 'conservative-auction-development-v1-{players}p',
        'runtime_seed_template': 'conservative-auction-runtime-v1-{players}p',
        'deal_offsets': list(range(8)), 'screens': screens,
        'planned_games_per_arm': 3360, 'planned_games_total': 10080,
        'game_max_steps': 1600, 'reference_search': previous['reference_search'],
        'primary': 'For each conservative arm minus filter, equal-weight mean terminal win-credit difference over the five search_geo player counts. Every deal includes all seats and four rules.',
        'secondary': 'Dual minus population; all 27 count/opponent cells, every rule/count cell, strict win credits, override counts, CPU/wall costs and all regressions. No retrospective rule routing.',
        'uncertainty': {'method': 'Paired whole-deal bootstrap, resampling eight deals within each player count; retain all seats, rules, arms and opponents together.',
                        'replicates': 10000, 'seed': 15125,
                        'interpretation': 'Exploratory 95% intervals for both predeclared contrasts. No multiplicity-adjusted or final qualification claim; eight deals per cell remains limited.'},
        'search_semantics': {'minimum_advantage': '1/8', 'samples_per_population': 8,
            'rationale': 'Retain the engineering recipe specified before the complete fidelity study; no threshold/budget fitting to these results.',
            'selection': 'Strict pooled terminal-credit advantage above 1/8 and nonnegative advantage in every included population; model favored on ties. Exact rational credits. These are screening rules, not calibrated confidence.',
            'scope': 'Auctions only. Both search arms retain the same strict-loss-filtered model outside auctions.',
            'candidate_menu': 'Existing public shortlist plus model move, unchanged order and strict-loss exclusions.',
            'hidden_information': 'All players money is public. Hidden sealed bids and future deck excluded; use existing public inference and matched sampled worlds.',
            'focal_continuation': 'Frozen-1 with strict loss filter; future live search is approximated, not recursively solved.',
            'opponent_identity': 'Never provided to the learner; arena opponent names are evaluator metadata only.'},
        'runtime_pilots': [{'arm': arm, 'players': n, 'opponent': 'search_geo', 'deals': 1, 'games': 4*n}
                           for arm in ('conservative_population', 'conservative_dual') for n in (2, 6)],
        'runtime_pilot_games': 64,
        'admission': 'First validate the exact descriptors/controls in a clean frozen source and complete actual HF endpoint whole-deal runtime pilots. Pilot results are excluded from strength. Freeze hardware/concurrency/shards/timeouts from measured complete-game costs before launching the development grid.',
        'execution': 'Use the already verified standalone public policy and portable development wrapper, preserving every base runtime byte. Do not reuse legacy search_scope translation.',
        'caps_and_failures': 'Preserve every original handle and partial receipt. No retries after observation timeouts, no truncated-outcome scoring, no survivor-only aggregates. Every planned cell and arm required before interpretation.',
        'promotion': 'No automatic promotion. Review full paired outcomes and all adverse cells, then separately freeze any larger confirmation or final candidate. Final protocol/thresholds/seeds remain unchanged.',
        'new_hf_jobs': 0, 'grid_admitted': False, 'final_protocol_sha256': PROTOCOL_SHA,
        'qualification_eligible': False, 'reserved_final_seeds_used': False}
    assert sum(r['games'] for r in protocol['runtime_pilots']) == 64
    assert all(r['games'] == 4*r['players']*len(protocol['deal_offsets']) for r in screens)
    write_new(PROTOCOL, protocol)

    lines = ['# Power Grid opponent-model fidelity — 25 October 2026', '',
        '**Decision: do not replace the existing opponent mixture. Test conservative auction search in fresh full games, with learned-opponent coverage as a separate experimental arm.**', '',
        'All 480 original positions / 23,040 continuations completed and passed independent terminal-credit auditing. Zero outer or nested caps. Coverage: Germany, 2–6 players, all four rules, plant choice/bidding/building; 160 originating games but only two independent deals per count.', '',
        '| Pre-specified metric | Existing mixture | Learned opponent |', '|---|---:|---:|',
        '| Absolute action-margin error | 16.79 pp | 17.33 pp |',
        '| Absolute per-action credit error | 20.92 pp | 21.48 pp |',
        '| Three-way preference agreement, including ties | 48.22% | 53.14% |', '',
        'The primary learned-minus-mixture error difference is **+0.541 pp**, exploratory 95% whole-deal interval **[−1.234, +2.316] pp**. Lower is better. This does not establish improved continuation fidelity. All 60 groups are retained: 23 improve, 29 worsen, eight tie. Higher preference agreement is secondary and includes ties.', '',
        '| Players | Mixture margin error | Learned margin error | Difference |', '|---|---:|---:|---:|']
    for count, group in descriptive['players'].items():
        a = group['metrics'][POPULATION]['absolute_margin_error']['value']*100
        b = group['metrics'][SURROGATE]['absolute_margin_error']['value']*100
        lines.append(f'| {count} | {a:.2f} pp | {b:.2f} pp | {b-a:+.2f} pp |')
    lines += ['', 'Descriptively, bidding error improves by 0.99 pp; plant-choice error worsens by 2.30 pp and building by 0.31 pp. These summaries do not authorize phase/rule-specific routing. Among the 43 roots with prior sealed bids (eight represented groups), error worsens by 2.64 pp; those conditional subsets are not a matched causal comparison.', '',
        'The teacher is a particular search policy, not optimal or human play. There is no economic-prior-only arm, so learned residual benefit is not isolated. Fixed two-action diagnostic outcomes are not training labels. The two-deal uncertainty estimates are exploratory and cannot certify a deployment policy.', '',
        'Reference continuations used 54,396,368 physical nested evaluations / 160.67 CPU hours. The learned model used 1.90 CPU hours and the existing mixture 1.53. Median time per 16 continuations was 314.88s / 4.93s / 4.99s respectively on shared HF hardware. Those are neither whole-policy nor 8840U latencies.', '',
        '## Next experiment, frozen before new game outcomes', '',
        'Compare the filtered frozen-1 model, conservative auction search with the existing population, and the same conservative search with both populations. Keep the existing eight-world, strict 1/8-margin recipe and require nonnegative advantage in each included population. No learned-only replacement, threshold fitting or retrospective rule routing.', '',
        'The fixed development design has **10,080 games: three arms × 27 count/opponent cells × eight full paired deals** (3,360 games/arm). All counts, seats and four rules are included. First run 64 separate HF runtime-pilot games across the two search arms and 2p/6p against search. These are excluded from strength; the full grid is not admitted or launched yet.', '',
        'The primary endpoint is the paired mean win-credit improvement against search, equally weighting 2–6 players. Report both conservative contrasts, dual-minus-population, every opponent/rule/count regression and paired whole-deal intervals. No automatic promotion; the original final gate and unused reserved seeds remain mandatory.', '',
        'Do not extend unchanged surrogate training: its validation best was near epoch 9, later epochs overfit, and this completed fidelity study supplies no overall improvement. This is a reason to change this particular approach, not evidence of a general Power Grid AI plateau.', '',
        '## Evidence', '',
        '- Complete immutable study: HF `'+evidence['revision']+'`, archive SHA256 `'+evidence['archive_sha256']+'`.',
        '- All group and root metrics: `strong/surrogate-continuation-study-comparison-v1.json`.',
        '- Machine-readable review: `strong/surrogate-continuation-study-review-v1.json`.',
        '- Frozen next design: `strong/conservative-auction-development-protocol-v1.json`.',
        '- Actual HF portability smoke passed eight games / 1,607 exact public decisions; this is engineering evidence only.', '']
    with NOTE.open('x') as stream: stream.write('\n'.join(lines))
    print(json.dumps({'complete_review': True, 'primary_error_difference': whole['surrogate_minus_population_error'],
                      'fresh_design_games': 10080, 'pilot_games': 64, 'grid_admitted': False, 'new_hf_jobs': 0}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__); parser.add_argument('--freeze', action='store_true', required=True)
    parser.parse_args(); main()
