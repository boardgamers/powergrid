"""Selection prerequisites for complete, explicitly recovered confirmation.

Reuses unchanged scientific, adverse-review and target gates. No candidate,
source upload, job, inference, simulation or reserved evaluation is created.
"""
from collections import Counter
from pathlib import Path

import current_auction_final_selection_v1 as original
import current_auction_attempt_authentication_v4 as auth
import current_auction_attempt_comparison_v4 as comparison_tool

ROOT = original.ROOT
BASE_GATE_SHA = '58f05405f81e18ac211c40706cacfaf580808cc13ff255a3b06eccc937fa8b91'
COMPARISON = str(comparison_tool.OUTPUT.relative_to(ROOT))
ARM, CONTRAST = original.ARM, original.CONTRAST
TECHNICAL, BINDING, EXPORT, EXPORT_AUDIT = original.TECHNICAL, original.BINDING, original.EXPORT, original.EXPORT_AUDIT
statistics, protocol = original.statistics, original.protocol
read, digest, require, same = original.read, original.digest, original.require, original.same
object_hash, artifact_identity = original.object_hash, original.artifact_identity
confirmation_gate = original.confirmation_gate
reviewed_selection = original.reviewed_selection
technical_gate = original.technical_gate
pinned_files = original.pinned_files


def expected_evidence(case, saved):
    """Derive the exact raw trees independently of a comparison's claimed paths."""
    if case['backend'] == 'original':
        manager = comparison_tool.originals.manager('confirmation')
        folder = manager.OUT/case['name']
        trees = [(folder/'artifacts', saved['evidence']['manifest_sha256'])]
        evaluation = manager.evaluation_directory(folder, saved)/'evaluation.json'
    else:
        paths = auth.locations(case['name'], case['backend']); folder = paths['folder']
        bucket = case['backend'] in ('bucket_first_v3', 'bucket_remaining_v3', 'bucket_failed_v3')
        root = folder/(saved['attempt_id']+'-collected') if bucket else folder
        envelope = root/('envelope' if bucket else 'artifacts')
        trees = []
        for item in saved['checkpoint_archives']:
            evidence = item['evidence']
            name = evidence['path'].split('/')[1] if bucket else Path(evidence['archive_path']).stem
            trees.append((root/'checkpoints'/name, evidence['manifest_sha256']))
        trees.append((envelope, saved['envelope_evidence']['manifest_sha256']))
        if bucket:
            trees.append((root, saved['versioned_collection_archive']['manifest_sha256']))
        evaluation = envelope/'raw/job/evaluation/evaluation.json'
    require(all(path.resolve().is_relative_to(ROOT.resolve()) for path, _ in trees)
            and evaluation.resolve().is_relative_to(ROOT.resolve()), 'Evidence path escapes checkout')
    return ([{'directory': str(path.relative_to(ROOT)), 'manifest_sha256': sha} for path, sha in trees],
            str(evaluation.relative_to(ROOT)))


def complete_provenance(comparison, plan, cases, saved):
    """Bind every reported original/recovery audit before applying strength gates."""
    require(plan['canonical_shards'] == len(cases) == len(saved) == 944
            and plan['canonical_games'] == sum(case['games'] for case in cases) == 26880,
            'All canonical attempts required for selection')
    expected = {'jobs': 944, 'games': 26880, 'game_keys_sha256': plan['game_keys_sha256'],
                'shards_by_disposition': plan['shards_by_disposition']}
    require(same(comparison['canonical_coverage'], expected), 'Canonical coverage changed')
    require(same(comparison['original_failure_preserved'], plan['original_failure_preserved']),
            'Original timeout failure omitted/changed')
    audit = comparison['parallel_raw_audit']
    require(audit['workers'] == 4 and audit['all_reviews_exact'] is True
            and audit['readiness_sha256'] == digest(comparison_tool.READINESS)
            and isinstance(audit['jobs'], dict), 'Missing complete isolated raw audits')
    indexed = comparison_tool.match_audits(cases, list(audit['jobs'].values()))
    require(set(audit['jobs']) == set(indexed) and all(audit['jobs'][k] == v for k, v in indexed.items()),
            'Independent audit dictionary is mislabelled')
    names = {case['name'] for case in cases}
    require(set(comparison['attempt_provenance']) == names == set(saved), 'Missing/foreign attempt provenance')
    for case in cases:
        name = case['name']; job = saved[name]
        expected = {k: case[k] for k in ('backend', 'job_id', 'stage', 'receipt_file', 'receipt_sha256')}
        expected['prior_failed_attempts'] = job.get('prior_failed_attempts', [])
        require(same(comparison['attempt_provenance'][name], expected), 'Changed/erased execution provenance')
        trees, evaluation = expected_evidence(case, job)
        require(same(indexed[name]['raw_trees'], trees) and indexed[name]['evaluation_file'] == evaluation,
                'Independent audit points to different raw evidence')
    counts = {arm: Counter() for arm in statistics.ARMS}
    for slot in plan['slots']:
        counts[slot['arm']].update(saved[slot['name']]['review']['audit']['counts'])
    require(all(dict(counts[arm]) == comparison['costs'][arm]['counts'] for arm in statistics.ARMS),
            'Comparison search totals differ from original reviews')
    # The original scientific gate expects an integer audit count. Only adapt
    # this representation after all 944 full per-attempt audits are matched.
    return {**comparison, 'parallel_raw_audit': {**audit, 'jobs': len(indexed)}}


def check_audited_files(cases, audits):
    for case in cases:
        require(digest(ROOT/case['receipt_file']) == case['receipt_sha256'], 'Audited receipt changed')
        audit = audits[case['name']]
        for tree in audit['raw_trees']:
            comparison_tool.tree_pin(ROOT/tree['directory'], tree['manifest_sha256'])
        require(digest(ROOT/audit['evaluation_file']) == audit['evaluation_sha256'], 'Audited evaluation changed')


def check_technical(identities, root=ROOT):
    """Existing full native/export/8840U proof; no inference replay."""
    root = Path(root)
    technical, binding, export, audit = [read(root/p) for p in (TECHNICAL, BINDING, EXPORT, EXPORT_AUDIT)]
    hashes = {p: digest(root/p) for p in (TECHNICAL, BINDING, EXPORT, EXPORT_AUDIT)}
    technical_gate(technical, binding, export, audit, hashes, identities)
    pinned_files(root, export['input_hashes'])
    target = root/'ai/runs/current-full-serving-8840u-collected-v1'
    require(digest(target/'output/receipts.jsonl') == binding['target_receipts_sha256']
            and digest(target/'output/status.json') == technical['status_sha256'], 'Raw target evidence changed')
    require(same(read(target/'audit.json'), technical), 'Collected target audit differs')
    status = read(target/'output/status.json')
    require(status['stage'] == 'completed' and status['passed'] is True, 'Target execution incomplete')
    pinned_files(target/'output', status['output_hashes'])
    require(digest(root/'ai/runs/current-engine-export-parity-v1/receipts.jsonl') == export['receipts_sha256'],
            'Raw native/export evidence changed')
    return hashes


def verify(review_path, root=ROOT):
    root = Path(root).resolve()
    require(root == ROOT.resolve(), 'Use the complete local evidence checkout')
    require(digest(original.__file__) == BASE_GATE_SHA, 'Original scientific/technical gate changed')
    plan = auth.coverage.actual_plan(); routes = auth.actual_routes(plan)
    refs = comparison_tool.complete_reference_index(plan, auth.inventory(plan, routes))
    # No comparison/selection/technical outcomes are opened before this complete
    # reference gate. The stopped original coordinator is never rewritten.
    _, identities, _, expected_pins = comparison_tool.check_inputs(plan)
    comparison_path = root/COMPARISON; comparison_sha = digest(comparison_path)
    comparison = read(comparison_path)
    require(same(comparison['input_hashes'], expected_pins), 'Comparison does not bind exact frozen inputs')
    pinned_files(root, comparison['input_hashes'])
    cases, saved = comparison_tool.make_cases(plan, routes, refs)
    normalized = complete_provenance(comparison, plan, cases, saved)
    check_audited_files(cases, comparison['parallel_raw_audit']['jobs'])
    adverse = confirmation_gate(normalized, identities)
    review_sha = digest(review_path); review = read(review_path)
    reviewed_selection(review, comparison, comparison_sha, identities[ARM], adverse)
    technical_hashes = check_technical(identities, root)
    require(digest(comparison_path) == comparison_sha and digest(review_path) == review_sha,
            'Comparison/review changed during selection check')
    pinned_files(root, comparison['input_hashes'])
    require(all(digest(root/case['receipt_file']) == case['receipt_sha256'] for case in cases),
            'Attempt receipts changed during selection check')
    return {'ready_for_candidate_freeze': True, 'selected_identity': identities[ARM],
        'comparison_sha256': comparison_sha, 'review_sha256': review_sha, 'technical_hashes': technical_hashes,
        'adverse_cells_reviewed': len(adverse), 'jobs': 944, 'games': 26880,
        'canonical_game_keys_sha256': plan['game_keys_sha256'], 'routing_sha256': object_hash(routes),
        'original_scientific_gate_sha256': BASE_GATE_SHA, 'comparison_code_sha256': digest(comparison_tool.__file__),
        'selection_code_sha256': digest(__file__), 'candidate_created': False, 'final_launch_admitted': False,
        'qualified': False, 'reserved_final_seeds_used': False,
        'remaining': 'Archive the explicit selection review, freeze exact candidate bytes and admit immutable final execution. Independent reserved strength qualification is still required.'}
