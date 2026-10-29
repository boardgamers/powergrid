"""Check mixed-attempt selection plumbing using saved evidence, without play."""
from pathlib import Path
import json
from unittest.mock import patch

import current_auction_final_selection_v2 as gate

ROOT = gate.ROOT
OUT = ROOT/'ai/runs/current-auction-final-selection-preflight-v2'
REPORT = ROOT/'ai/strong/current-auction-final-selection-preflight-v2.json'


def main():
    gate.require(not OUT.exists() and not REPORT.exists(), 'Inspect existing preflight intent/outcome')
    plan = gate.auth.coverage.actual_plan(); routes = gate.auth.actual_routes(plan)
    found = gate.auth.inventory(plan, routes)
    gate.require(not found['complete'], 'This preflight requires actual incomplete coverage')
    log = ROOT/'ai/runs/current-auction-final-selection-tests-v2-first.log'
    gate.require('Ran 22 tests' in log.read_text() and log.read_text().rstrip().endswith('OK'), 'Tests incomplete')
    c = gate.comparison_tool
    _, identities, _, pins = c.check_inputs(plan)
    prior_path = ROOT/'ai/strong/current-auction-attempt-comparison-preflight-v3.json'
    prior = gate.read(prior_path)
    gate.require(prior['passed'] and prior['all_saved_full_reviews_exact'], 'Prior integration proof incomplete')
    gate.pinned_files(ROOT, prior['input_hashes'])
    names = set(prior['independent_audits'])
    subset = {**plan, 'slots': [s for s in plan['slots'] if s['name'] in names]}
    refs = {r['name']: r for r in found['available']}
    cases, saved = c.make_cases(subset, routes, refs)
    audits = c.match_audits(cases, list(prior['independent_audits'].values()))
    for case in cases:
        trees, evaluation = gate.expected_evidence(case, saved[case['name']])
        audit = audits[case['name']]
        gate.require(trees == audit['raw_trees'] and evaluation == audit['evaluation_file'],
                     'New selection paths differ from existing independent audit')
    # Check bytes, not gameplay: re-use the completed independent raw audits.
    gate.check_audited_files(cases, audits)
    paths = [Path(__file__), Path(gate.__file__), ROOT/'ai/strong/test_current_auction_final_selection_v2.py',
             ROOT/'ai/strong/test_current_auction_final_selection_v1.py', Path(gate.original.__file__), log, prior_path]
    pins.update({str(p.relative_to(ROOT)): gate.digest(p) for p in paths})
    OUT.mkdir()
    c.write_new(OUT/'intent.json', {'input_hashes': pins, 'cases': cases, 'new_games': 0,
                                 'new_policy_calls': 0, 'raw_reaudits': 0})
    with patch.object(gate, 'read', wraps=gate.read) as outcomes, \
         patch.object(c, 'check_inputs') as inputs, patch.object(c, 'make_cases') as make_cases, \
         patch.object(gate, 'check_technical') as technical:
        try: gate.verify(OUT/'NO-ACTUAL-SELECTION-REVIEW.json')
        except ValueError as error:
            rejection = str(error)
            gate.require(rejection == 'Incomplete recovery coverage; do not read outcomes', 'Unexpected refusal')
        else: raise ValueError('Unfinished actual study admitted')
        for fn in (outcomes, inputs, make_cases, technical): fn.assert_not_called()
    hashes = gate.check_technical(identities)
    gate.pinned_files(ROOT, pins)
    report = {'passed': True, 'checked_at': gate.auth.failed.now(), 'tests_passed': 22,
        'code_sha256': gate.digest(gate.__file__), 'input_hashes': pins,
        'incomplete_actual_study_rejected': rejection, 'outcome_reads_before_rejection': 0,
        'existing_audit_bindings_checked': len(cases), 'existing_audit_games': sum(c['games'] for c in cases),
        'backends_checked': [c['backend'] for c in cases], 'raw_reaudits': 0,
        'failure_backend_real_completion_pending': not any(r['backend']=='bucket_failed_v3' for r in found['available']),
        'existing_target_requests_checked': 5106, 'existing_native_positions_checked': 2553,
        'technical_hashes': hashes, 'inventory': gate.auth.inventory_summary(found),
        'original_scientific_gate_sha256': gate.BASE_GATE_SHA,
        'scope': 'Selection engineering only; positive full-grid tests are synthetic. Actual partial study rejected. Existing raw audit bindings and full technical proof accepted; no complete-study selection admitted.',
        'new_hf_jobs': 0, 'new_games': 0, 'new_policy_calls': 0,
        'candidate_selected': False, 'final_launch_admitted': False, 'qualified': False,
        'reserved_final_seeds_used': False}
    c.write_new(REPORT, report)
    print(json.dumps({k: report[k] for k in ('passed','tests_passed','existing_audit_bindings_checked',
        'existing_target_requests_checked','raw_reaudits','new_games','failure_backend_real_completion_pending')}), flush=True)


if __name__ == '__main__': main()
