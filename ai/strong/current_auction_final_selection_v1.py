"""Read-only selection gate for the frozen current-engine auction study.

No selection is created, candidate frozen, source uploaded or job submitted.
The completed independent comparison, native export, target evidence and an
explicit adverse-cell review are prerequisites, not substitutes for final play.
"""
from collections import Counter
from fractions import Fraction
import importlib.util
from pathlib import Path

import current_auction_confirmation_analysis_v1 as statistics
from public_policy_final_audit_v1 import artifact_identity, digest, protocol, read, require, same
from public_policy_final_contract_v1 import object_hash, timestamp

ROOT = Path(__file__).resolve().parents[2]
OWNER = 'ai/runs/current-auction-network-resume-v1/state.json'
SOURCE = 'ai/strong/current-auction-grid-source-v1.json'
RESULT = 'ai/strong/current-auction-grid-results-recovered-v1.json'
COMPARISON = 'ai/strong/current-auction-confirmation-comparison-parallel-v1.json'
SOURCE_SHA = 'a4384b10eb8a4381423731bc0c315673f9214d91c1fb336aa81ef4a7102d1c5a'
ARM = 'conservative_population'
CONTRAST = ARM + '_minus_filter'
TECHNICAL = 'ai/strong/current-full-serving-8840u-results-v1.json'
BINDING = 'ai/strong/current-full-serving-export-binding-v1.json'
EXPORT = 'ai/strong/current-engine-export-parity-v1.json'
EXPORT_AUDIT = 'ai/strong/current-engine-export-audit-v1.json'


def completed_owner(owner):
    require(owner['stage'] == 'complete' and owner.get('completed_games') == 26880,
            'Wait for all original confirmation jobs before selection')
    require(owner['qualified'] is False and owner['reserved_final_seeds_used'] is False,
            'Wrong execution purpose')


def confirmation_gate(comparison, identities):
    p = statistics.protocol()
    require(comparison['complete'] is True and comparison['games'] == 26880
            and comparison['games_per_arm'] == 13440 and comparison['cells_per_arm'] == 27
            and comparison['independent_deals_per_count'] == 32, 'Incomplete confirmation coverage')
    require(comparison['candidate_selected'] is False and comparison['qualification_eligible'] is False
            and comparison['reserved_final_seeds_used'] is False, 'Wrong confirmation purpose')
    require(comparison['protocol_sha256'] == statistics.PROTOCOL_SHA, 'Confirmation protocol changed')
    statistics.validate_identities(identities, p)
    require(same(comparison['identities'], identities), 'Changed complete policy identity')
    require(comparison['raw_receipts_reaudited'] is True
            and comparison['parallel_raw_audit']['all_reviews_exact'] is True
            and comparison['parallel_raw_audit']['jobs'] == 944, 'Missing complete independent raw audit')
    require(comparison['uncertainty']['replicates'] == 10000
            and comparison['uncertainty']['seed'] == 281028, 'Changed uncertainty calculation')
    checks = statistics.confirmation_requirements(comparison, protocol())
    require(same(checks, comparison['confirmation_requirements_review']), 'Saved strength checks differ')
    require(checks['passed'], 'Confirmation strength requirements failed; final selection is not admitted')
    expected_cells = {f"{s['opponent']}/{s['players']}p" for s in p['screens']}
    views = comparison['contrasts'][CONTRAST]
    require(set(views) == expected_cells, 'Missing count/opponent comparisons')
    directions = {'negative': [], 'positive': [], 'zero': []}
    for cell, rules in views.items():
        require(set(rules) == {'overall', *statistics.RULES}, 'Missing rule comparisons')
        for rule, metrics in rules.items():
            change = Fraction(metrics['win_credit_difference']['exact_mean'])
            directions['negative' if change < 0 else 'positive' if change > 0 else 'zero'].append(
                {'cell': cell, 'rules': rule, 'difference': float(change)})
    sort = lambda xs: sorted(xs, key=lambda x: (x['cell'], x['rules']))
    require(all(same(sort(items), sort(comparison['all_cell_directions'][CONTRAST][sign]))
                for sign, items in directions.items()), 'Regression inventory differs from paired results')
    for arm, counts in ((a, comparison['costs'][a]['counts']) for a in statistics.ARMS):
        require(counts['rollout_caps'] == 0, 'Truncated confirmation search')
        if arm == ARM:
            require(counts['rollouts'] > 0 and counts['search_decisions'] > 0, 'No actual auction search')
    return sort(directions['negative'])


def reviewed_selection(review, comparison, comparison_sha, identity, adverse):
    require(set(review) == {'version', 'created_at', 'decision', 'comparison_sha256', 'identity',
                          'adverse_cells', 'rationale', 'limitations', 'qualified', 'reserved_final_seeds_used'},
            'Incomplete explicit selection review')
    require(review['version'] == 1 and review['decision'] == 'propose_conservative_population_for_reserved_evaluation',
            'Wrong research decision')
    require(review['comparison_sha256'] == comparison_sha and same(review['identity'], identity),
            'Review is not bound to this complete comparison/policy')
    require(timestamp(review['created_at']) >= timestamp(comparison['created_at']), 'Review predates complete results')
    require(review['qualified'] is False and review['reserved_final_seeds_used'] is False, 'Premature qualification')
    require(isinstance(review['rationale'], str) and review['rationale'].strip(), 'Explain selection rationale')
    require(isinstance(review['limitations'], list) and review['limitations']
            and all(isinstance(v, str) and v.strip() for v in review['limitations']), 'State remaining limitations')
    entries = review['adverse_cells']
    require(isinstance(entries, list) and len(entries) == len(adverse), 'Every adverse cell needs explicit review')
    preserved = []
    for entry in entries:
        require(set(entry) == {'cell', 'rules', 'difference', 'assessment'}
                and isinstance(entry['assessment'], str) and entry['assessment'].strip(), 'Missing adverse-cell assessment')
        preserved.append({k: entry[k] for k in ('cell', 'rules', 'difference')})
    require(same(sorted(preserved, key=lambda x: (x['cell'], x['rules'])), adverse),
            'Omitted, duplicated or changed adverse result')


def technical_gate(technical, binding, export, audit, hashes, identities):
    require(technical['complete'] is True and technical['requests'] == 5106
            and technical['positions_per_policy'] == 2553 and technical['all_moves_legal'] is True,
            'Incomplete full target validation')
    require('8840U' in technical['processor'] and same(technical['identities'], identities), 'Wrong target or policies')
    require(binding['complete'] is True and binding['requests'] == 5106
            and binding['per_policy'] == {a: 2553 for a in statistics.ARMS}
            and binding['all_target_model_proposals_match_native_checkpoint'] is True,
            'Missing full target/native binding')
    require(binding['technical_report_sha256'] == hashes[TECHNICAL]
            and binding['export_report_sha256'] == audit['report_sha256'] == hashes[EXPORT]
            and binding['export_audit_sha256'] == hashes[EXPORT_AUDIT], 'Technical proof hashes differ')
    expected_counts = {'2': 349, '3': 427, '4': 527, '5': 609, '6': 641}
    model = statistics.protocol()['model_pin']
    for value in (export, audit):
        require(value['complete'] is True and value['positions'] == 2553
                and value['by_player_count'] == expected_counts, 'Incomplete native/export validation')
        require(all(value[k] is True for k in ('all_native_onnx_actions_equal', 'finite_values',
                    'inactive_values_zero', 'values_normalized')), 'Native/export mismatch')
    require(export['all_moves_legal'] is True and audit['all_input_tensor_hashes_match'] is True
            and export['receipts_sha256'] == audit['receipts_sha256'], 'Unverified export inputs')
    for value in (binding, export, audit):
        require(value['model_sha256'] == model['files']['inference64.onnx']
                and value['checkpoint_sha256'] == model['files']['inference64.pt']
                and value['runtime_manifest_sha256'] == identities[ARM]['runtimeManifestSha256'], 'Wrong native/model/runtime')
    for arm in statistics.ARMS:
        c = technical['counts'][arm]
        require(c['decisions'] == 2553 and c['rollout_caps'] == 0, 'Incomplete or capped target execution')
        expected_views = {f'{n}p/{variant}/{auction}/{phase}' for n in range(2, 7)
                          for variant in ('original', 'recharged') for auction in ('open', 'sealed')
                          for phase in ('Auction', 'Resources', 'Building', 'Bureaucracy')}
        require(set(technical['warm_timings_by_count_rule_phase'][arm]) == expected_views,
                'Incomplete target timing coverage')
    require(technical['counts'][ARM]['search_decisions'] > 0 and technical['counts'][ARM]['rollouts'] > 0,
            'Target did not exercise the complete hybrid policy')
    for value in (technical, binding, export, audit):
        require(value['candidate_selected'] is False and value['qualified'] is False
                and value['reserved_final_seeds_used'] is False, 'Technical evidence has wrong purpose')


def pinned_files(root, pins):
    require(isinstance(pins, dict) and pins, 'Missing evidence pins')
    for name, sha in pins.items():
        path = root / name
        require(not Path(name).is_absolute() and path.resolve().is_relative_to(root.resolve())
                and path.is_file() and digest(path) == sha, 'Changed evidence file: ' + name)


def verify(review_path, root=ROOT):
    """Fail before opening outcomes while the original study is incomplete."""
    root = Path(root).resolve()
    owner = read(root / OWNER); completed_owner(owner)
    pinned_files(root, owner['code_hashes'])
    require(digest(root / SOURCE) == SOURCE_SHA, 'Frozen confirmation source changed')
    comparison = read(root / COMPARISON); source = read(root / SOURCE); originals = read(root / RESULT)
    require(owner['result_sha256'] == digest(root / RESULT) and originals['source_sha256'] == SOURCE_SHA,
            'Complete result differs from original execution')
    comparator = Path(__file__).with_name('compare-current-auction-confirmation-parallel-v1.py')
    spec = importlib.util.spec_from_file_location('complete_confirmation_selection_index', comparator)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    indexed = module.completion_index(source, originals)
    require(len(indexed) == len(comparison['provenance']) == 944, 'Wrong complete original-job coverage')
    require(set(indexed) == set(comparison['provenance']), 'Comparison omits original jobs')
    pins = comparison['input_hashes']; pinned_files(root, pins)
    for name in (OWNER, SOURCE, RESULT, 'ai/strong/compare-current-auction-confirmation-parallel-v1.py',
                 'ai/strong/current_auction_confirmation_analysis_v1.py', 'ai/strong/final-protocol-multiplayer.json'):
        require(pins.get(name) == digest(root / name), 'Comparison does not bind required input')
    require(comparison['original_hf_status_counts'] == dict(Counter(j['stage'] for j in indexed.values())),
            'Original failures omitted')
    for name, job in indexed.items():
        folder = root / 'ai/runs/current-auction-grid-hf-v1' / name; proof = comparison['provenance'][name]
        require(proof['job_id'] == job['job_id'] and proof['original_hf_stage'] == job['stage']
                and same(proof['evidence'], job['evidence']), 'Original provenance changed')
        require(digest(folder / proof['verified_file']) == proof['verified_sha256']
                and digest(folder / 'launch.json') == proof['launch_sha256'] == job['guard_sha256'], 'Original receipts changed')
        require(same(proof['raw_input_hashes'], job['review']['audit']['input_hashes']), 'Raw audit binding changed')
    artifact = root / 'ai/runs/current-auction-grid-prepared-v1/source/artifact'
    identities = {arm: artifact_identity(artifact, f'policies/{arm}.json') for arm in statistics.ARMS}
    adverse = confirmation_gate(comparison, identities)
    review = read(review_path)
    reviewed_selection(review, comparison, digest(root / COMPARISON), identities[ARM], adverse)
    technical, binding, export, audit = [read(root / p) for p in (TECHNICAL, BINDING, EXPORT, EXPORT_AUDIT)]
    hashes = {p: digest(root / p) for p in (TECHNICAL, BINDING, EXPORT, EXPORT_AUDIT)}
    technical_gate(technical, binding, export, audit, hashes, identities)
    pinned_files(root, export['input_hashes'])
    target = root / 'ai/runs/current-full-serving-8840u-collected-v1'
    require(digest(target / 'output/receipts.jsonl') == binding['target_receipts_sha256']
            and digest(target / 'output/status.json') == technical['status_sha256'], 'Raw target evidence changed')
    require(same(read(target / 'audit.json'), technical), 'Collected target audit differs')
    status = read(target / 'output/status.json')
    require(status['stage'] == 'completed' and status['passed'] is True, 'Target execution incomplete')
    pinned_files(target / 'output', status['output_hashes'])
    require(digest(root / 'ai/runs/current-engine-export-parity-v1/receipts.jsonl') == export['receipts_sha256'],
            'Raw native/export evidence changed')
    return {'ready_for_candidate_freeze': True, 'selected_identity': identities[ARM],
            'comparison_sha256': digest(root / COMPARISON), 'review_sha256': digest(review_path),
            'technical_hashes': hashes, 'adverse_cells_reviewed': len(adverse), 'jobs': 944, 'games': 26880,
            'candidate_created': False, 'final_launch_admitted': False, 'qualified': False,
            'reserved_final_seeds_used': False,
            'remaining': 'Archive the reviewed selection and freeze candidate bytes. Prepare and admit actual immutable source/allocation before dispatch. The independent final strength gate remains required.'}
