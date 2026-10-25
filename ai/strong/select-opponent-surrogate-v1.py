"""Freeze validation-only single/ensemble selection from independently audited HF models."""
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from strategic_collection import ROOT, read, write, digest
from opponent_surrogate_policy_v1 import SEEDS, SurrogatePolicy, make_policy, ensemble_scores
from opponent_surrogate_training_v1 import load_bundle, metrics
from opponent_surrogate_training_verification_v1 import same, validate_metrics

STRONG = ROOT/'ai/strong'
DESIGN = STRONG/'opponent-surrogate-selection-design-v1.json'
TRAINING_DESIGN = STRONG/'opponent-surrogate-training-design-v1.json'
TRAINING_RESULT = STRONG/'opponent-surrogate-training-results-v1.json'
COLLECTED = ROOT/'ai/runs/opponent-surrogate-training-full-collected-v1'
OUT = ROOT/'ai/runs/opponent-surrogate-selection-v1'
TIE_TOLERANCE = 1e-10


def code_hashes():
    return {str(p.relative_to(ROOT)): digest(p) for p in [Path(__file__), DESIGN,
        STRONG/'opponent_surrogate_policy_v1.py', STRONG/'opponent_surrogate_training_v1.py',
        STRONG/'opponent_surrogate_training_verification_v1.py']}


def prerequisites():
    assert TRAINING_RESULT.exists(), 'All four original HF training seeds must be independently verified before selection'
    result = read(TRAINING_RESULT)
    assert result == read(COLLECTED/'verified.json')
    assert result['verified'] and result['authoritative_status'] == 'COMPLETED'
    assert result['test_labels_used'] is False and result['qualification_eligible'] is False
    assert set(result['seeds']) == set(map(str, SEEDS))
    assert all(digest(ROOT/name) == sha for name, sha in result['code_hashes'].items())
    artifacts = COLLECTED/'artifacts'
    assert digest(artifacts/'manifest.json') == result['evidence']['manifest_sha256']
    assert all(digest(artifacts/name) == sha for name, sha in read(artifacts/'manifest.json').items())
    design = read(DESIGN); assert design['training_design_sha256'] == digest(TRAINING_DESIGN)
    assert design['test_labels_used_for_selection'] is False
    assert design['numerical_tie_tolerance'] == TIE_TOLERANCE
    folder = ROOT/'ai/runs/opponent-surrogate-training-data-v1'
    if not folder.exists(): folder = COLLECTED/'recovered-data/data'
    data, report = load_bundle(folder, read(TRAINING_DESIGN))
    assert digest(folder/'data-check.json') == result['data_check_sha256']
    assert report['collection_index_sha256'] == result['collection_index_sha256']
    return result, design, data, folder


def member_pins(result):
    return [{'seed': seed, 'path': f'{seed}/derivative/inference64.onnx',
             'sha256': result['seeds'][str(seed)]['files']['inference64.onnx'],
             'checkpoint_sha256': result['seeds'][str(seed)]['best_checkpoint_sha256']} for seed in SEEDS]


def selection(scores, data, order):
    assert set(scores) == set(order) and len(scores) == len(order) == 6
    reports = {key: metrics(scores[key], data) for key in order}
    for report in reports.values(): validate_metrics(report, data)
    best = min(reports[key]['macro_nll'] for key in order)
    chosen = next(key for key in order if reports[key]['macro_nll'] <= best + TIE_TOLERANCE)
    return chosen, reports


def verify_frozen():
    assert (OUT/'frozen.json').exists(), 'Freeze validation-only selection before reading held-out test records'
    frozen = read(OUT/'frozen.json'); report = read(OUT/'selection.json'); policy = read(OUT/'policy.json')
    assert frozen['complete'] and frozen['learned_surrogate_selected'] is True, 'No learned validation improvement: keep the test split closed'
    assert frozen['selection_sha256'] == digest(OUT/'selection.json')
    assert frozen['policy_sha256'] == digest(OUT/'policy.json') == report['policy_sha256']
    assert frozen['design_sha256'] == digest(DESIGN) == report['design_sha256']
    assert report['training_result_sha256'] == digest(TRAINING_RESULT)
    assert report['code_hashes'] == code_hashes() and report['test_labels_used'] is False
    assert frozen['selection'] == report['selected'] and report['selected'] != 'economic-prior'
    assert report['validation_scores_sha256'] == digest(OUT/'validation-scores.npz')
    result, design, data, _ = prerequisites()
    with np.load(OUT/'validation-scores.npz', allow_pickle=False) as saved:
        chosen, metrics_report = selection(dict(saved), data['validation'], design['candidate_order'])
    assert chosen == report['selected']; same(metrics_report, report['candidates'])
    pins = member_pins(result)
    expected = make_policy(pins if chosen == 'ensemble-4' else [p for p in pins if chosen == f"seed-{p['seed']}"])
    assert policy == expected
    return frozen, report, policy


def main():
    result, design, data, data_folder = prerequisites()
    assert not OUT.exists(), 'Preserve the original selection outcome; inspect any partial run before retrying'
    hashes = code_hashes(); OUT.mkdir()
    write(OUT/'intent.json', {'started_at': datetime.now(timezone.utc).isoformat(),
        'training_result_sha256': digest(TRAINING_RESULT), 'code_hashes': hashes, 'test_labels_used': False})
    validation = data['validation']; pins = member_pins(result)
    policies = {'economic-prior': make_policy([]), **{f"seed-{p['seed']}": make_policy([p]) for p in pins},
                'ensemble-4': make_policy(pins)}
    scores = {key: SurrogatePolicy(policy, COLLECTED/'artifacts').scores(validation)
              for key, policy in policies.items() if key != 'ensemble-4'}
    scores['ensemble-4'] = ensemble_scores([scores[f'seed-{s}'] for s in SEEDS], validation['mask'])
    chosen, reports = selection(scores, validation, design['candidate_order'])
    for seed in SEEDS: same(reports[f'seed-{seed}'], result['seeds'][str(seed)]['behaviour']['validation'])
    np.savez(OUT/'validation-scores.npz', **scores)
    write(OUT/'policy.json', policies[chosen])
    baseline = reports['economic-prior']; learned = chosen != 'economic-prior'
    review = {'complete': True, 'selected': chosen, 'learned_surrogate_selected': learned,
        'candidate_order': design['candidate_order'], 'candidates': reports,
        'adverse_selected_groups_nll': [g for g, v in reports[chosen]['groups'].items() if v['nll'] > baseline['groups'][g]['nll']],
        'selected_macro_nll_delta_from_prior': reports[chosen]['macro_nll'] - baseline['macro_nll'],
        'policy_sha256': digest(OUT/'policy.json'), 'validation_scores_sha256': digest(OUT/'validation-scores.npz'),
        'design_sha256': digest(DESIGN), 'training_result_sha256': digest(TRAINING_RESULT),
        'data_check_sha256': digest(data_folder/'data-check.json'), 'code_hashes': hashes,
        'test_labels_used': False, 'gradients': False, 'qualification_eligible': False,
        'scope': 'Validation-selected imitation policy; metrics used for selection are not unbiased held-out performance or playing strength.'}
    assert hashes == code_hashes(); write(OUT/'selection.json', review)
    write(OUT/'frozen.json', {'complete': True, 'selection': chosen, 'learned_surrogate_selected': learned,
        'selection_sha256': digest(OUT/'selection.json'), 'policy_sha256': digest(OUT/'policy.json'),
        'design_sha256': digest(DESIGN), 'test_labels_used': False, 'qualification_eligible': False})
    print({key: review[key] for key in ('selected', 'learned_surrogate_selected', 'selected_macro_nll_delta_from_prior')})


if __name__ == '__main__': main()
